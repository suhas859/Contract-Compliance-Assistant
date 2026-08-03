from backend.validation.invoice_parser import InvoiceParser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

invoice_path = (
    BASE_DIR
    / "data"
    / "test_uploads"
    / "invoices_to_validate"
    / "invoice_pinegrove_nda_placeholder.pdf"
)

parser = InvoiceParser()
invoice = parser.parse(str(invoice_path))

print(invoice)
