from backend.validation.models import Finding, FindingStatus


def validate_tax_id(invoice: dict, contract: dict) -> list[Finding]:

    invoice_tax_id = invoice.get("tax_id")
    contract_tax_id = contract.get("tax_id")

    if not invoice_tax_id or not contract_tax_id:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description="Tax ID information could not be verified.",
                citation=contract.get("contract_id", "Contract"),
                category="tax_id_match",
            )
        ]

    if invoice_tax_id.strip() == contract_tax_id.strip():
        return [
            Finding(
                status=FindingStatus.PASS,
                description="Tax ID matches the governing contract.",
                citation=contract["contract_id"],
                category="tax_id_match",
            )
        ]

    return [
        Finding(
            status=FindingStatus.FAIL,
            description=(
                f"Invoice tax ID '{invoice_tax_id}' does not "
                f"match contract tax ID '{contract_tax_id}'."
            ),
            citation=contract["contract_id"],
            category="tax_id_match",
        )
    ]
