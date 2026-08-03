from backend.validation.models import Finding, FindingStatus


def validate_supplier(invoice: dict, contract: dict) -> list[Finding]:

    invoice_vendor = invoice.get("vendor")
    contract_supplier = contract.get("supplier")

    if not invoice_vendor or not contract_supplier:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description="Supplier information could not be verified.",
                citation=contract.get("contract_id", "Contract"),
                category="supplier_match",
            )
        ]

    if invoice_vendor.lower().strip() == contract_supplier.lower().strip():
        return [
            Finding(
                status=FindingStatus.PASS,
                description="Supplier matches the governing contract.",
                citation=contract["contract_id"],
                category="supplier_match",
            )
        ]

    return [
        Finding(
            status=FindingStatus.FAIL,
            description=(
                f"Invoice supplier '{invoice_vendor}' does not "
                f"match contract supplier '{contract_supplier}'."
            ),
            citation=contract["contract_id"],
            category="supplier_match",
        )
    ]
