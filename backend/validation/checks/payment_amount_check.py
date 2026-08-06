from backend.validation.models import Finding, FindingStatus
from backend.validation.policy_rules import PolicyRules


def validate_amount(invoice: dict, contract: dict, policy_rules: PolicyRules) -> list[Finding]:

    invoice_amount = invoice.get("amount")
    contract_value = contract.get("contract_value")

    if invoice_amount is None or contract_value is None:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description="Unable to verify invoice amount.",
                citation=contract.get("contract_id", "Contract"),
                category="payment_amount",
            )
        ]

    if invoice_amount <= contract_value:
        return [
            Finding(
                status=FindingStatus.PASS,
                description="Invoice amount is within contract value.",
                citation=contract["contract_id"],
                category="payment_amount",
            )
        ]

    # Tolerance % is read from the live policy text, not hardcoded -- a
    # policy revision changes this without a code change.
    tolerance_pct = policy_rules.get_invoice_tolerance_pct()
    tolerance_cap = contract_value * (1 + tolerance_pct / 100)

    citation = policy_rules.get_source_label()

    if invoice_amount <= tolerance_cap:
        return [
            Finding(
                status=FindingStatus.PASS,
                description=(
                    f"Invoice amount exceeds contract value but is within "
                    f"the {tolerance_pct:g}% tolerance."
                ),
                citation=citation,
                category="payment_amount",
            )
        ]

    return [
        Finding(
            status=FindingStatus.WARNING,
            description=(
                f"Invoice amount exceeds contract value by more than "
                f"the {tolerance_pct:g}% tolerance without an "
                f"amendment on file."
            ),
            citation=citation,
            category="payment_amount",
        )
    ]
