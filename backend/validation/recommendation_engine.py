from backend.llm.llm_provider import LLMProvider

PROMPT_TEMPLATE = """You are a compliance assistant. Based ONLY on the findings below \
from an invoice compliance check, write a short, specific, actionable recommendation \
for resolving each issue. Do not invent any facts not present in the findings below.

FINDINGS REQUIRING ACTION:
{findings_text}

Write one recommendation per line, each starting with "- ". Do not add any other text."""


def generate_recommendations(llm: LLMProvider, validation: dict) -> list[str]:
    """
    The "LLM Reasoning Layer" from the project spec: generates
    recommendations grounded strictly in this validation's own
    Warning/Fail findings -- the LLM never sees anything beyond what's
    already been determined by the deterministic checks, so it can't
    invent a violation that wasn't actually found.

    Falls back to the static per-category recommendations if the LLM
    call fails (model unavailable, network error, etc.), so the
    report's Recommendations section is never empty or broken.
    """
    findings = validation.get("findings", [])
    actionable = [f for f in findings if f.get("status") in {"Warning", "Fail"}]

    if not actionable:
        return []

    findings_text = "\n".join(
        f"- [{f.get('status')}] {f.get('description', '')} (Source: {f.get('citation') or 'N/A'})"
        for f in actionable
    )

    try:
        reply = llm.generate(PROMPT_TEMPLATE.format(findings_text=findings_text))
        lines = [line.strip(" -") for line in reply.splitlines() if line.strip(" -")]
        return lines or _fallback_recommendations(actionable)
    except Exception:
        return _fallback_recommendations(actionable)


def _fallback_recommendations(actionable_findings: list[dict]) -> list[str]:
    from backend.chat.validation_presentation import RECOMMENDATIONS

    categories = {f.get("category") for f in actionable_findings}
    return [
        recommendation
        for category, recommendation in RECOMMENDATIONS.items()
        if category in categories
    ]
