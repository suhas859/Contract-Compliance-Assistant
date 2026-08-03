from datetime import datetime

from backend.retrieval.retriever import Retriever
from backend.validation.contract_parser import ContractParser
from backend.validation.invoice_parser import InvoiceParser
from backend.validation.models import (
    ComplianceReport,
    Finding,
    FindingStatus,
)


class InvoiceValidationEngine:
    """
    Validates an invoice against its governing contract.
    """

    def __init__(self):
        self.invoice_parser = InvoiceParser()
        self.contract_parser = ContractParser()
        self.retriever = Retriever()

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
        report.findings.extend(
            self.validate_supplier(invoice, contract)
        )

        report.findings.extend(
            self.validate_contract_dates(invoice, contract)
        )

        report.findings.extend(
            self.validate_amount(invoice, contract)
        )

        return report

    ##############################################################

    def validate_supplier(self, invoice, contract):

        findings = []

        invoice_vendor = invoice.get("vendor")
        contract_supplier = contract.get("supplier")

        if not invoice_vendor or not contract_supplier:
            findings.append(
                Finding(
                    status=FindingStatus.WARNING,
                    description="Supplier information could not be verified.",
                    citation=contract.get("contract_id", "Contract"),
                    category="supplier_match",
                )
            )
            return findings

        if invoice_vendor.lower().strip() == contract_supplier.lower().strip():

            findings.append(
                Finding(
                    status=FindingStatus.PASS,
                    description="Supplier matches the governing contract.",
                    citation=contract["contract_id"],
                    category="supplier_match",
                )
            )

        else:

            findings.append(
                Finding(
                    status=FindingStatus.FAIL,
                    description=(
                        f"Invoice supplier '{invoice_vendor}' does not "
                        f"match contract supplier '{contract_supplier}'."
                    ),
                    citation=contract["contract_id"],
                    category="supplier_match",
                )
            )

        return findings

    ##############################################################

    def validate_contract_dates(self, invoice, contract):

        findings = []

        try:

            invoice_date = datetime.strptime(
                invoice["invoice_date"],
                "%Y-%m-%d",
            )

            start = datetime.strptime(
                contract["validity_start"],
                "%Y-%m-%d",
            )

            end = datetime.strptime(
                contract["validity_end"],
                "%Y-%m-%d",
            )

        except Exception:

            findings.append(
                Finding(
                    status=FindingStatus.WARNING,
                    description="Unable to verify contract validity dates.",
                    citation=contract.get("contract_id", "Contract"),
                    category="contract_period",
                )
            )

            return findings

        if start <= invoice_date <= end:

            findings.append(
                Finding(
                    status=FindingStatus.PASS,
                    description="Invoice date falls within contract validity.",
                    citation=contract["contract_id"],
                    category="contract_period",
                )
            )

        else:

            findings.append(
                Finding(
                    status=FindingStatus.FAIL,
                    description="Invoice date is outside contract validity.",
                    citation=contract["contract_id"],
                    category="contract_period",
                )
            )

        return findings

    ##############################################################

    def validate_amount(self, invoice, contract):

        findings = []

        invoice_amount = invoice.get("amount")
        contract_value = contract.get("contract_value")

        if invoice_amount is None or contract_value is None:

            findings.append(
                Finding(
                    status=FindingStatus.WARNING,
                    description="Unable to verify invoice amount.",
                    citation=contract.get("contract_id", "Contract"),
                    category="payment_amount",
                )
            )

            return findings

        #
        # NOTE:
        # Replace this rule later with:
        # Monthly Fee / Payment Terms validation
        #

        if invoice_amount <= contract_value:

            findings.append(
                Finding(
                    status=FindingStatus.PASS,
                    description="Invoice amount is within contract value.",
                    citation=contract["contract_id"],
                    category="payment_amount",
                )
            )

        else:

            findings.append(
                Finding(
                    status=FindingStatus.FAIL,
                    description="Invoice amount exceeds contract value.",
                    citation=contract["contract_id"],
                    category="payment_amount",
                )
            )

        return findings