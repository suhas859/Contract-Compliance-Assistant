import re
import pdfplumber


class InvoiceParser:

    INVOICE_ID_PATTERN = re.compile(r"Invoice\s*ID\s*:\s*(INV-[A-Za-z0-9\-]+)")
    CONTRACT_ID_PATTERN = re.compile(r"Contract\s*ID\s*:\s*(CTR-[A-Za-z0-9\-]+)")
    # FIX: was r"Supplier\s*:\s*(.*?)\s+Tax\s*ID" -- required "Tax ID" to
    # appear immediately after the supplier name to know where to stop
    # capturing. Invoices with no Tax ID field (e.g. minimal/placeholder
    # invoices) had no valid stopping point, so the match failed
    # entirely and returned None, even though the supplier name was
    # present in the text. Now stops at "Tax ID" OR a double-space OR
    # a newline OR end of string -- whichever comes first.
    VENDOR_PATTERN = re.compile(
       r"Supplier\s*:\s*(.+?)(?=\s*(?:[-]{3,}|[A-Z][A-Za-z ]+:\s|$))"
    )
    TAX_ID_PATTERN = re.compile(r"Tax\s*ID\s*:\s*([0-9\-]+)")
    INVOICE_DATE_PATTERN = re.compile(r"Invoice\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})")
    DUE_DATE_PATTERN = re.compile(r"Due\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})")
    TOTAL_AMOUNT_PATTERN = re.compile(r"Total\s+Invoiced\s+Amount\s*:\s*\$?([\d,]+\.\d{2})")
    BASE_FEE_PATTERN = re.compile(r"Base\s+Monthly\s+Service\s+Fee.*?\$([\d,]+\.\d{2})")
    ADDITIONAL_CHARGES_PATTERN = re.compile(r"Additional\s+Charges\s*:\s*\$([\d,]+\.\d{2})")

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
        text = re.sub(r"(\d{2}-)\s*\n\s*(\d+)", r"\1\2", text)

        # Join words broken with hyphen
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

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
            "invoice_id": self.search(self.INVOICE_ID_PATTERN, text),
            "contract_id": self.search(self.CONTRACT_ID_PATTERN, text),
            "vendor": self.search(self.VENDOR_PATTERN, text),
            "tax_id": self.search(self.TAX_ID_PATTERN, text),
        }

    #######################################################
    # Dates
    #######################################################

    def extract_dates(self, text: str):
        return {
            "invoice_date": self.search(self.INVOICE_DATE_PATTERN, text),
            "due_date": self.search(self.DUE_DATE_PATTERN, text),
        }

    #######################################################
    # Billing
    #######################################################

    def extract_billing_details(self, text: str):
        total_amount = self.search(self.TOTAL_AMOUNT_PATTERN, text)
        base_fee = self.search(self.BASE_FEE_PATTERN, text)
        additional_charges = self.search(self.ADDITIONAL_CHARGES_PATTERN, text)

        return {
            "amount": self.to_float(total_amount),
            "base_fee": self.to_float(base_fee),
            "additional_charges": self.to_float(additional_charges),
        }

    #######################################################
    # Helper Functions
    #######################################################

    @staticmethod
    def search(pattern: re.Pattern, text: str):
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    @staticmethod
    def to_float(value):
        if value is None:
            return None
        return float(value.replace(",", ""))