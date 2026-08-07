import unittest

from backend.api.chat_api import format_validation


class ValidationFormatterTests(unittest.TestCase):
    def test_formats_status_findings_incidents_and_recommendations(self):
        report = {
            "status": "Partially Compliant",
            "findings": [
                {
                    "status": "Pass",
                    "description": "Supplier details match approved contract.",
                    "citation": "CTR-001",
                    "category": "supplier_match",
                },
                {
                    "status": "Warning",
                    "description": "Invoice exceeds the approved contract value.",
                    "citation": "POL-PAY-001",
                    "category": "payment_amount",
                },
            ],
        }

        output = format_validation(report)

        self.assertIn("⚠ Partially Compliant", output)
        self.assertIn("✓ Supplier details match approved contract. (CTR-001)", output)
        self.assertIn("Related ServiceNow Incidents", output)
        self.assertIn("Revise the invoice or obtain an approved contract amendment.", output)


if __name__ == "__main__":
    unittest.main()
