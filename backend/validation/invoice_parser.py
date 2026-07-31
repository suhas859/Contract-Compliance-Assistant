import re
import pdfplumber


class InvoiceParser:

    def parse(self, file_path: str) -> dict:
        """
        Main entry point.
        """

        text = self.extract_text(file_path)
        text = self.clean_text(text)

        header = self.extract_header_fields(text)
        dates = self.extract_dates(text)
        billing = self.extract_billing_details(text)

        return {
            **header,
            **dates,
            **billing,
            "raw_text": text
        }

    #######################################################
    # PDF Extraction
    #######################################################

    def extract_text(self, file_path: str) -> str:

        text = ""

        with pdfplumber.open(file_path) as pdf:

            for page in pdf.pages:

                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

        return text

    #######################################################
    # Cleaning
    #######################################################

    def clean_text(self, text: str) -> str:

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Join Tax IDs split across lines
        text = re.sub(
            r"(\d{2}-)\s*\n\s*(\d+)",
            r"\1\2",
            text
        )

        # Join words broken with hyphen
        text = re.sub(
            r"(\w)-\n(\w)",
            r"\1\2",
            text
        )

        # Replace newlines with spaces
        text = text.replace("\n", " ")

        # Remove tabs
        text = text.replace("\t", " ")

        # Collapse spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    #######################################################
    # Header Fields
    #######################################################

    def extract_header_fields(self, text: str):

        return {

            "invoice_id": self.search(
                r"Invoice\s*ID\s*:\s*(INV-[A-Za-z0-9\-]+)",
                text
            ),

            "contract_id": self.search(
                r"Contract\s*ID\s*:\s*(CTR-[A-Za-z0-9\-]+)",
                text
            ),

            "vendor": self.search(
                r"Supplier\s*:\s*(.*?)\s+Tax\s*ID",
                text
            ),

            "tax_id": self.search(
                r"Tax\s*ID\s*:\s*([0-9\-]+)",
                text
            )
        }

    #######################################################
    # Dates
    #######################################################

    def extract_dates(self, text: str):

        invoice_date = self.search(
            r"Invoice\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})",
            text
        )

        due_date = self.search(
            r"Due\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})",
            text
        )

        return {

            "invoice_date": invoice_date,
            "due_date": due_date

        }

    #######################################################
    # Billing
    #######################################################

    def extract_billing_details(self, text: str):

        total_amount = self.search(
            r"Total\s+Invoiced\s+Amount\s*:\s*\$?([\d,]+\.\d{2})",
            text
        )

        base_fee = self.search(
            r"Base\s+Monthly\s+Service\s+Fee.*?\$([\d,]+\.\d{2})",
            text
        )

        additional_charges = self.search(
            r"Additional\s+Charges\s*:\s*\$([\d,]+\.\d{2})",
            text
        )

        return {

            "amount": self.to_float(total_amount),

            "base_fee": self.to_float(base_fee),

            "additional_charges": self.to_float(additional_charges)

        }

    #######################################################
    # Helper Functions
    #######################################################

    def search(self, pattern, text):

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return None

    def to_float(self, value):

        if value is None:
            return None

        return float(value.replace(",", ""))