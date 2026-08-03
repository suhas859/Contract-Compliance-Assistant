import re
import pdfplumber


class InvoiceParser:

    INVOICE_ID_PATTERN = re.compile(r"Invoice\s*ID\s*:\s*(INV-[A-Za-z0-9\-]+)")
    CONTRACT_ID_PATTERN = re.compile(r"Contract\s*ID\s*:\s*(CTR-[A-Za-z0-9\-]+)")
    # Stops at a known label on the same line, OR a real newline, OR
    # end of string. Needs line-preserving text (not flattened) --
    # flattening destroys the newline signal this depends on.
    VENDOR_PATTERN = re.compile(
        r"Supplier\s*:\s*(.+?)"
        r"(?=\s+(?:Tax\s*ID|Invoice\s*Date|Due\s*Date|Amount\s*Due|Contract\s*ID|"
        r"Total\s+Invoiced|Billing\s+Details|Note)\s*:|\n|$)"
    )
    TAX_ID_PATTERN = re.compile(r"Tax\s*ID\s*:\s*([0-9\-]+)")
    INVOICE_DATE_PATTERN = re.compile(r"Invoice\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})")
    DUE_DATE_PATTERN = re.compile(r"Due\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})")
    TOTAL_AMOUNT_PATTERN = re.compile(r"(?:Total\s+Invoiced\s+Amount|Amount\s+Due)\s*:\s*\$?([\d,]+\.\d{2})")
    BASE_FEE_PATTERN = re.compile(r"Base\s+Monthly\s+Service\s+Fee.*?\$([\d,]+\.\d{2})")
    ADDITIONAL_CHARGES_PATTERN = re.compile(r"Additional\s+Charges\s*:\s*\$([\d,]+\.\d{2})")

    def parse(self, file_path: str) -> dict:
        raw = self.extract_text(file_path)
        lines_text = self.repair_line_breaks(raw)
        flat_text = self.flatten(lines_text)

        header = self.extract_header_fields(lines_text)
        dates = self.extract_dates(flat_text)
        billing = self.extract_billing_details(flat_text)

        return {**header, **dates, **billing, "raw_text": flat_text}

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

    def repair_line_breaks(self, text: str) -> str:
        """Fixes PDF line-wrap corruption WITHOUT removing real newlines."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"(\d{2}-)\s*\n\s*(\d+)", r"\1\2", text)
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        return text

    def flatten(self, text: str) -> str:
        text = text.replace("\n", " ").replace("\t", " ")
        return re.sub(r"\s+", " ", text).strip()

    def clean_text(self, text: str) -> str:
        """Kept for backward compatibility with any external caller."""
        return self.flatten(self.repair_line_breaks(text))

    #######################################################
    # Header Fields (operate on line-preserving text)
    #######################################################

    def extract_header_fields(self, text: str):
        return {
            "invoice_id": self.search(self.INVOICE_ID_PATTERN, text),
            "contract_id": self.search(self.CONTRACT_ID_PATTERN, text),
            "vendor": self.search(self.VENDOR_PATTERN, text),
            "tax_id": self.search(self.TAX_ID_PATTERN, text),
        }

    #######################################################
    # Dates (operate on flattened text)
    #######################################################

    def extract_dates(self, text: str):
        return {
            "invoice_date": self.search(self.INVOICE_DATE_PATTERN, text),
            "due_date": self.search(self.DUE_DATE_PATTERN, text),
        }

    #######################################################
    # Billing (operate on flattened text -- values may span a PDF line wrap)
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