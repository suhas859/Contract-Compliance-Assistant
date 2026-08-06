from backend.chat.session_documents import session_collection_name
from backend.retrieval.retriever import Retriever
from backend.validation.invoice_validation import InvoiceValidationEngine


def validate_session_invoice(session_id: str, invoice_path: str) -> dict:
    """
    Validates an uploaded invoice against whatever contract and policy
    have been uploaded to this same chat session -- NOT the permanent
    knowledge base. Refuses to run if either is missing, rather than
    silently falling back to the org-wide knowledge base or producing a
    misleading partial result.

    Returns the raw ComplianceReport dict (status + all findings) on
    success, or {"error": "..."} if a contract/policy is missing --
    presentation/formatting is left to the caller.
    """
    retriever = Retriever(collection_name=session_collection_name(session_id))

    missing = []
    if not retriever.get_by_doc_type("contract"):
        missing.append("a contract")
    if not retriever.get_by_doc_type("policy"):
        missing.append("a policy")

    if missing:
        return {
            "error": (
                f"Missing {' and '.join(missing)} in this session -- upload "
                f"before validating an invoice."
            )
        }

    engine = InvoiceValidationEngine(retriever=retriever)
    report = engine.validate_invoice(invoice_path)

    return report.to_dict()
