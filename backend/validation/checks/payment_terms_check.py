from datetime import datetime, timedelta

from backend.validation.models import Finding, FindingStatus
from backend.validation.policy_rules import PolicyRules


def validate_payment_terms(invoice: dict, contract: dict, policy_rules: PolicyRules) -> list[Finding]:

    invoice_date_str = invoice.get("invoice_date")
    due_date_str = invoice.get("due_date")

    if not invoice_date_str or not due_date_str:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description=(
                    "Unable to verify payment terms -- invoice date or "
                    "due date is missing."
                ),
                citation=contract.get("contract_id", "Contract"),
                category="payment_terms",
            )
        ]

    try:
        invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d")
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")

    except ValueError:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description=(
                    "Unable to verify payment terms -- invoice date or "
                    "due date is malformed."
                ),
                citation=contract.get("contract_id", "Contract"),
                category="payment_terms",
            )
        ]

    # The contract's own payment terms (e.g. "Net 30 from invoice
    # date") override the policy default. Not every contract states
    # one (some are invoiced upfront), so fall back to the policy's
    # standard term, also read live rather than hardcoded.
    contract_term_days = contract.get("payment_term_days")

    if contract_term_days is not None:
        term_days = contract_term_days
        citation = f"{contract.get('contract_id', 'Contract')}, Payment Terms"
    elif policy_rules.has_policy():
        term_days = policy_rules.get_default_payment_term_days()
        citation = policy_rules.get_source_label()
    else:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description=(
                    "Unable to verify payment terms -- the contract does "
                    "not specify payment terms and no policy is available."
                ),
                citation=contract.get("contract_id", "Contract"),
                category="payment_terms",
            )
        ]

    expected_due_date = invoice_date + timedelta(days=term_days)

    if due_date == expected_due_date:
        return [
            Finding(
                status=FindingStatus.PASS,
                description=f"Due date is consistent with Net {term_days} payment terms.",
                citation=citation,
                category="payment_terms",
            )
        ]

    return [
        Finding(
            status=FindingStatus.WARNING,
            description=(
                f"Due date ({due_date_str}) does not match the "
                f"expected Net {term_days} due date "
                f"({expected_due_date.date()}) from the invoice date."
            ),
            citation=citation,
            category="payment_terms",
        )
    ]
