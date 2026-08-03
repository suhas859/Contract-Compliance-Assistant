from backend.validation.invoice_validation import InvoiceValidationEngine

engine = InvoiceValidationEngine()

report = engine.validate_invoice(
    "data/test_uploads/invoices_to_validate/invoice_acme_logistics_march2026.pdf"
)

print(report.to_dict())