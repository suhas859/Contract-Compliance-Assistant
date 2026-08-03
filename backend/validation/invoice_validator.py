from datetime import datetime


class InvoiceValidator:

    def validate(self, invoice, contract, policies=None):

        findings = []

        findings.append(
            self.validate_contract_id(invoice, contract)
        )

        findings.append(
            self.validate_supplier(invoice, contract)
        )

        findings.append(
            self.validate_contract_period(invoice, contract)
        )

        findings.append(
            self.validate_amount(invoice, contract)
        )

        findings = [f for f in findings if f]

        overall = self.calculate_status(findings)

        return {
            "status": overall,
            "findings": findings
        }

    ####################################################

    def validate_contract_id(self, invoice, contract):

        if invoice["contract_id"] == contract["contract_id"]:

            return {
                "field": "Contract ID",
                "status": "PASS"
            }

        return {
            "field": "Contract ID",
            "status": "FAIL",
            "reason": "Invoice references a different contract."
        }

    ####################################################

    def validate_supplier(self, invoice, contract):

        if invoice["vendor"].lower() == contract["supplier"].lower():

            return {
                "field": "Supplier",
                "status": "PASS"
            }

        return {
            "field": "Supplier",
            "status": "FAIL",
            "reason": "Supplier does not match the governing contract."
        }

    ####################################################

    def validate_contract_period(self, invoice, contract):

        invoice_date = datetime.strptime(
            invoice["invoice_date"],
            "%Y-%m-%d"
        )

        start = datetime.strptime(
            contract["validity_start"],
            "%Y-%m-%d"
        )

        end = datetime.strptime(
            contract["validity_end"],
            "%Y-%m-%d"
        )

        if start <= invoice_date <= end:

            return {
                "field": "Contract Validity",
                "status": "PASS"
            }

        return {
            "field": "Contract Validity",
            "status": "FAIL",
            "reason": "Invoice date falls outside contract validity."
        }

    ####################################################

    def validate_amount(self, invoice, contract):

        if invoice["amount"] <= contract["contract_value"]:

            return {
                "field": "Amount",
                "status": "PASS"
            }

        return {
            "field": "Amount",
            "status": "FAIL",
            "reason": "Invoice exceeds contract value."
        }

    ####################################################

    def calculate_status(self, findings):

        if any(f["status"] == "FAIL" for f in findings):
            return "FAIL"

        if any(f["status"] == "WARNING" for f in findings):
            return "WARNING"

        return "PASS"