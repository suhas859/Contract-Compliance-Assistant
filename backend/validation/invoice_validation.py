from backend.retrieval.retriever import Retriever
from backend.validation.checks.contract_period_check import validate_contract_dates
from backend.validation.checks.payment_amount_check import validate_amount
from backend.validation.checks.payment_terms_check import validate_payment_terms
from backend.validation.checks.supplier_check import validate_supplier
from backend.validation.checks.tax_id_check import validate_tax_id
from backend.validation.contract_parser import ContractParser
from backend.validation.invoice_parser import InvoiceParser
from backend.validation.models import ComplianceReport, Finding, FindingStatus
from backend.validation.policy_rules import PolicyRules


class InvoiceValidationEngine:
    """
    Validates an invoice against its governing contract. Parses the
    invoice, retrieves the governing contract, then delegates each rule
    to its own module under checks/ -- this class only orchestrates.

    Only checks the invoice against the contract -- doesn't re-audit
    whether the contract itself is well-formed (e.g. has all its
    required clauses). That's a separate Contract Review concern.
    """

    def __init__(self, retriever: Retriever | None = None):
        self.invoice_parser = InvoiceParser()
        self.contract_parser = ContractParser()
        self.retriever = retriever or Retriever()
        self.policy_rules = PolicyRules(self.retriever)

    ##############################################################

    def validate_invoice(self, invoice_pdf_path: str) -> ComplianceReport:

        # -----------------------------
        # Parse invoice
        # -----------------------------
        invoice = self.invoice_parser.parse(invoice_pdf_path)

        report = ComplianceReport(
            document_name=invoice_pdf_path
        )

        contract_id = invoice.get("contract_id")

        if not contract_id:
            report.findings.append(
                Finding(
                    status=FindingStatus.FAIL,
                    description="Invoice does not contain a Contract ID.",
                    citation="Invoice",
                    category="contract_lookup",
                )
            )
            return report

        # -----------------------------
        # Retrieve governing contract
        # -----------------------------
        chunks = self.retriever.get_contract_by_id(contract_id)

        if not chunks:
            report.findings.append(
                Finding(
                    status=FindingStatus.FAIL,
                    description=f"No contract found for {contract_id}.",
                    citation=contract_id,
                    category="contract_lookup",
                )
            )
            return report

        contract_text = "\n".join(chunk.text for chunk in chunks)

        contract = self.contract_parser.parse(contract_text)

        # -----------------------------
        # Run validations
        # -----------------------------
        report.findings.extend(validate_supplier(invoice, contract))
        report.findings.extend(validate_tax_id(invoice, contract))
        report.findings.extend(validate_contract_dates(invoice, contract))
        report.findings.extend(validate_amount(invoice, contract, self.policy_rules))
        report.findings.extend(validate_payment_terms(invoice, contract, self.policy_rules))

        return report
