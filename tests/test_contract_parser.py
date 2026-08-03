from backend.validation.contract_parser import ContractParser
from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.pdf_parser import parse_pdf

TEST_FILES = [
    ("data/knowledge_base/approved_contracts/supplier_agreement_acme_logistics.docx", "docx"),
    ("data/test_uploads/contracts_for_review/castellan_security_draft.docx", "docx"),
    ("data/test_uploads/contracts_for_review/hearthstone_payroll_draft.pdf", "pdf"),
    ("data/test_uploads/contracts_for_review/ridgeline_office_supply_draft.docx", "docx"),
]


def run():
    parser = ContractParser()

    for path, fmt in TEST_FILES:
        text = parse_docx(path) if fmt == "docx" else parse_pdf(path)
        result = parser.parse(text)

        print(f"\n{'='*70}")
        print(path)
        print('='*70)
        for key, value in result.items():
            flag = "  ⚠ MISSING" if value is None else ""
            print(f"  {key}: {value}{flag}")


if __name__ == "__main__":
    run()