import re


class ContractParser:
    """
    Extracts structured fields from a contract's raw text. Shared by
    both Contract Review (checking a new draft) and Invoice Validation
    (checking an invoice against its governing contract's supplier,
    tax ID, and validity period).
    """

    CONTRACT_ID_PATTERN = re.compile(r"Contract\s*ID\s*:\s*(CTR-[A-Za-z0-9\-]+)")
    SUPPLIER_PATTERN = re.compile(
        r"Supplier\s*:\s*(.+?)"
        r"(?=\s+(?:Tax\s*ID|Contract\s*Owner|Total\s+Contract\s+Value|"
        r"Contract\s+Validity\s+Period|Supplier\s+Relationship|Vendor\s+Risk\s+Tier)\s*:|\n|$)"
    )
    TAX_ID_PATTERN = re.compile(r"Tax\s*ID\s*:\s*([0-9\-]+)")
    CONTRACT_VALUE_PATTERN = re.compile(r"Total\s+Contract\s+Value\s*:\s*\$?([\d,]+(?:\.\d+)?)")
    VALIDITY_PERIOD_PATTERN = re.compile(
        r"Contract\s+Validity\s+Period\s*:\s*(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})"
    )
    # Matches "Approved by:" (executed contracts) or "Submitted by:"
    # (drafts pending review) -- stops at the next "Date:" label or
    # newline, since PDF/DOCX-extracted text doesn't reliably preserve
    # line breaks between adjacent fields.
    SUBMITTER_PATTERN = re.compile(
        r"(?:Approved\s+by|Submitted\s+by)\s*:\s*[^,]+,\s*(.+?)(?:\s+Date:|\n|$)"
    )

    def parse(self, text: str) -> dict:
        """
        Parses already-extracted contract text (from parse_pdf() or
        parse_docx() -- this class does NOT do file I/O itself, unlike
        InvoiceParser, so it can be reused regardless of which parser
        produced the text).
        """
        text = self._clean_text(text)

        return {
            "contract_id": self._search(self.CONTRACT_ID_PATTERN, text),
            "supplier": self._search(self.SUPPLIER_PATTERN, text),
            "tax_id": self._search(self.TAX_ID_PATTERN, text),
            "contract_value": self._to_float(self._search(self.CONTRACT_VALUE_PATTERN, text)),
            "validity_start": self._search_group(self.VALIDITY_PERIOD_PATTERN, text, group=1),
            "validity_end": self._search_group(self.VALIDITY_PERIOD_PATTERN, text, group=2),
            "submitter_role": self._search(self.SUBMITTER_PATTERN, text),
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Repairs text corruption that can happen when pdfplumber extracts
        a PDF where a field value happened to wrap across a page-width
        line break -- e.g. a tax ID or hyphenated word split by a
        literal '\\n' in the middle. Without this, such a value would
        be silently wrong (extra newline inside an ID) rather than
        cleanly missing, which is harder to notice.
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Join tax IDs split across a line break, e.g. "94-\n3021177" -> "94-3021177"
        text = re.sub(r"(\d{2}-)\s*\n\s*(\d+)", r"\1\2", text)

        # Join words broken with a hyphen at a line wrap, e.g. "last-\nmile" -> "lastmile"
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        return text

    @staticmethod
    def _search(pattern: re.Pattern, text: str) -> str | None:
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _search_group(pattern: re.Pattern, text: str, group: int) -> str | None:
        match = pattern.search(text)
        return match.group(group).strip() if match else None

    @staticmethod
    def _to_float(value: str | None) -> float | None:
        if value is None:
            return None
        return float(value.replace(",", ""))