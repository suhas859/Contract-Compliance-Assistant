from dataclasses import dataclass, field
from enum import Enum


class FindingStatus(str, Enum):
    PASS = "Pass"
    WARNING = "Warning"
    FAIL = "Fail"


@dataclass
class Finding:
    """
    A single compliance check result. Every validation check (contract
    vs. policies, invoice vs. contract, invoice vs. policies) produces
    a list of these, regardless of which check generated them -- this
    is the common shape the rest of the pipeline (aggregation, API
    response, UI rendering) depends on.
    """
    status: FindingStatus
    description: str          # human-readable explanation, e.g.
                               # "Contract lacks the mandatory data
                               #  privacy clause required by POL-SEC-002"
    citation: str              # source reference, e.g. "POL-SEC-002" or
                               # "CTR-2026-0088, Section 5"
    category: str               # e.g. "mandatory_clause", "approval_threshold",
                                 # "supplier_match", "payment_tolerance"


@dataclass
class ComplianceReport:
    """
    Aggregated result of a full validation run (Contract Review or
    Invoice Validation). overall_status is derived from the findings:
    any Fail -> "Non-Compliant", any Warning (no Fail) -> "Partially
    Compliant", all Pass -> "Compliant".
    """
    document_name: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        if any(f.status == FindingStatus.FAIL for f in self.findings):
            return "Non-Compliant"
        if any(f.status == FindingStatus.WARNING for f in self.findings):
            return "Partially Compliant"
        return "Compliant"

    def to_dict(self) -> dict:
        """Shape for the API response / UI rendering."""
        return {
            "document": self.document_name,
            "status": self.overall_status,
            "findings": [
                {
                    "status": f.status.value,
                    "description": f.description,
                    "citation": f.citation,
                    "category": f.category,
                }
                for f in self.findings
            ],
        }