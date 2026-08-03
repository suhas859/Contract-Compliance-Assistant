from datetime import datetime

from backend.validation.models import Finding, FindingStatus


def validate_contract_dates(invoice: dict, contract: dict) -> list[Finding]:

    try:
        invoice_date = datetime.strptime(invoice["invoice_date"], "%Y-%m-%d")
        start = datetime.strptime(contract["validity_start"], "%Y-%m-%d")
        end = datetime.strptime(contract["validity_end"], "%Y-%m-%d")

    except Exception:
        return [
            Finding(
                status=FindingStatus.WARNING,
                description="Unable to verify contract validity dates.",
                citation=contract.get("contract_id", "Contract"),
                category="contract_period",
            )
        ]

    if start <= invoice_date <= end:
        return [
            Finding(
                status=FindingStatus.PASS,
                description="Invoice date falls within contract validity.",
                citation=contract["contract_id"],
                category="contract_period",
            )
        ]

    return [
        Finding(
            status=FindingStatus.FAIL,
            description="Invoice date is outside contract validity.",
            citation=contract["contract_id"],
            category="contract_period",
        )
    ]
