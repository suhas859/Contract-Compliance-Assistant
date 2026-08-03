from backend.validation.invoice_parser import InvoiceParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

invoice_path = (PROJECT_ROOT / "data" / "test_uploads" / "invoices_to_validate" / "invoice_pinegrove_nda_placeholder.pdf")



parser = InvoiceParser()

invoice = parser.parse(str(invoice_path ))


print(invoice)