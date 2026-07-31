import re

from backend.retrieval.retriever import Retriever
from backend.validation.models import Finding, FindingStatus, ComplianceReport
#from backend.validation.llm_provider import LLMProvider
#from backend.validation.policy_rules import get_approval_thresholds

CONTRACT_VALUE_PATTERN = re.compile(r"Total Contract Value:\s*\$?([\d,]+(?:\.\d+)?)")
# Matches either "Approved by:" (already-executed contracts) or
# "Submitted by:" (drafts pending review, per contracts_for_review/)
# a draft has no approver yet, only a submitter proposing it.
SUBMITTER_PATTERN = re.compile(r"(?:Approved by|Submitted by):\s*[^,]+,\s*(.+?)(?:\s+Date:|\n|$)")

ROLE_RANK = {
    "department manager": 0,
    "director": 1,
    "vp of procurement": 2,
    "cfo": 3,
}


def extract_contract_value(contract_text: str) -> float | None:
    match = CONTRACT_VALUE_PATTERN.search(contract_text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _required_tier_for_value(value: float, thresholds: list[dict]) -> dict:
    """
    thresholds is sorted ascending by max_value (None = unbounded,
    treated as the last/highest tier). Returns the first tier whose
    max_value the given value falls under.
    """
    sorted_tiers = sorted(thresholds, key=lambda t: (t["max_value"] is None, t["max_value"]))
    for tier in sorted_tiers:
        if tier["max_value"] is None or value < tier["max_value"]:
            return tier
    return sorted_tiers[-1]


def _role_rank(role_text: str) -> int | None:
    role_text = role_text.lower()
    for role, rank in ROLE_RANK.items():
        if role in role_text:
            return rank
    return None


def check_approval_threshold(contract_text: str, retriever: Retriever, llm: LLMProvider) -> Finding | None:
    """
    Compares contract value against the approval threshold table --
    extracted dynamically from the actual Procurement Policy text via
    get_approval_thresholds(), not hardcoded. If the policy is revised,
    this picks up the new numbers automatically on the next call (see
    policy_rules.py for the caching/fallback behavior).
    """
    value = extract_contract_value(contract_text)
    if value is None:
        return None

    thresholds = get_approval_thresholds(retriever, llm)
    required_tier = _required_tier_for_value(value, thresholds)
    required_approver = required_tier["approver"]
    legal_review_required = required_tier.get("legal_review_required", False)

    match = SUBMITTER_PATTERN.search(contract_text)
    stated_role = match.group(1).strip() if match else None
    legal_review_mentioned = bool(re.search(r"legal review", contract_text, re.IGNORECASE))

    if stated_role is None:
        return Finding(
            status=FindingStatus.WARNING,
            description=f"Contract value is ${value:,.0f}, requiring {required_approver} approval, "
                        f"but no submitter/approver role could be identified in the contract text.",
            citation="POL-PROC-001",
            category="approval_threshold",
        )

    if legal_review_required and not legal_review_mentioned:
        return Finding(
            status=FindingStatus.FAIL,
            description=(
                f"Contract value is ${value:,.0f}, requiring mandatory Legal Review per POL-PROC-001, "
                f"but no legal review is documented in the contract."
            ),
            citation="POL-PROC-001",
            category="approval_threshold",
        )

    required_rank = _role_rank(required_approver)
    stated_rank = _role_rank(stated_role)

    if stated_rank is None or required_rank is None:
        status = FindingStatus.WARNING
        description = (
            f"Contract value is ${value:,.0f}, requiring {required_approver} approval, but the "
            f"submitter's role ('{stated_role}') doesn't match a recognized approval tier."
        )
    elif stated_rank >= required_rank:
        status = FindingStatus.PASS
        description = (
            f"Contract value (${value:,.0f}) requires {required_approver} approval; submitter role "
            f"('{stated_role}') meets or exceeds this tier."
        )
    else:
        status = FindingStatus.FAIL
        description = (
            f"Contract value is ${value:,.0f}, requiring {required_approver} approval per POL-PROC-001, "
            f"but was only submitted at the '{stated_role}' level."
        )

    return Finding(status=status, description=description, citation="POL-PROC-001", category="approval_threshold")


CLAUSE_CHECK_SYSTEM_PROMPT = """You check whether a contract contains
specific required clauses, based ONLY on the policy excerpts provided --
do not use outside knowledge of what contracts typically contain.

For each clause type below, determine if the contract satisfies it:
- mandatory_clauses: scope of work, payment terms, contract validity period,
  termination conditions, liability/indemnification
- data_privacy: a data privacy/confidentiality clause meeting the
  requirements in the provided policy excerpt (only required if the
  contract involves data access -- use your judgment based on the
  contract's scope of work)

Respond with ONLY a JSON object, no other text:
{
  "findings": [
    {
      "status": "Pass" | "Warning" | "Fail",
      "clause": "short identifier, e.g. scope_of_work, data_privacy, termination",
      "citation": "policy/SOP document ID this is based on"
    }
  ]
}

Keep this terse -- one short clause identifier per finding, no long
explanations. A separate step will generate detailed descriptions later."""


def check_clauses_llm(contract_text: str, retriever: Retriever, llm: LLMProvider, top_k: int = 3) -> list[Finding]:
    queries = [
        "mandatory clauses required in a supplier contract",
        "data privacy and confidentiality clause requirements",
    ]
    chunks = []
    seen = set()
    for q in queries:
        for r in retriever.retrieve(q, top_k=top_k, doc_type_filter=["policy", "sop"]):
            if r.text not in seen:
                chunks.append(r)
                seen.add(r.text)

    if not chunks:
        return [Finding(
            status=FindingStatus.WARNING,
            description="No relevant policy documents could be retrieved for clause checking.",
            citation="",
            category="retrieval_gap",
        )]

    context_block = "\n\n".join(f"[{c.doc_id or c.source}]\n{c.text}" for c in chunks)
    user_prompt = f"CONTRACT TEXT:\n{contract_text}\n\nPOLICY EXCERPTS:\n{context_block}"

    raw_findings = llm.generate_findings(CLAUSE_CHECK_SYSTEM_PROMPT, user_prompt)

    findings = []
    for rf in raw_findings:
        try:
            findings.append(Finding(
                status=FindingStatus(rf["status"]),
                description=f"Clause check: {rf.get('clause', 'unknown')}",
                citation=rf.get("citation", ""),
                category="mandatory_clause",
            ))
        except (KeyError, ValueError):
            continue
    return findings


def review_contract(contract_text: str, document_name: str, retriever: Retriever, llm: LLMProvider) -> ComplianceReport:
    report = ComplianceReport(document_name=document_name)

    approval_finding = check_approval_threshold(contract_text, retriever, llm)
    if approval_finding:
        report.findings.append(approval_finding)

    report.findings.extend(check_clauses_llm(contract_text, retriever, llm))

    return report