from backend.chat.session_documents import ingest_session_file, session_collection_name
from backend.retrieval.retriever import Retriever
from backend.validation.invoice_parser import InvoiceParser
from backend.validation.invoice_validation import InvoiceValidationEngine

# Every invoice ever uploaded to a session, keyed by session_id -- lets a
# later "validate this invoice" text command, or an automatic retry once
# a missing contract/policy arrives, find it again. In-memory only, same
# lifetime as everything else session-scoped in this app (Express's
# sessions dict, the Chroma collections).
_SESSION_INVOICES: dict[str, list[dict]] = {}

_invoice_parser = InvoiceParser()


def register_session_invoice(session_id: str, invoice_path: str, filename: str) -> None:
    entries = _SESSION_INVOICES.setdefault(session_id, [])
    if not any(entry["path"] == invoice_path for entry in entries):
        entries.append({"path": invoice_path, "filename": filename, "resolved": False})


def ingest_and_register(session_id: str, file_path: str, filename: str) -> dict:
    """
    Ingests one file into a session, shared by every entry point that
    adds documents (manual chat upload, ServiceNow attachment pull).
    Detects invoices via InvoiceParser first -- the generic doc-id
    extractor only recognizes "Document ID"/"Contract ID"/"Article ID"
    labels, not "Invoice ID", so left alone it would mistag an invoice
    as a contract under the real contract's own ID (an invoice's text
    references that ID too). Registers detected invoices for later
    re-validation. Returns the ingest_session_file() result dict.
    """
    parsed_invoice = _invoice_parser.parse(file_path)
    invoice_id = parsed_invoice.get("invoice_id")

    result = ingest_session_file(
        session_id,
        file_path,
        filename,
        doc_type="invoice" if invoice_id else None,
        doc_id=invoice_id,
    )

    if invoice_id:
        register_session_invoice(session_id, file_path, filename)

    return result


def get_session_invoices(session_id: str) -> list[dict]:
    return _SESSION_INVOICES.get(session_id, [])


def _is_missing_contract(result: dict) -> bool:
    """
    True only when the sole problem is that this invoice's specific
    governing contract hasn't been uploaded yet -- uploading it later
    would resolve this. Different from "the invoice itself has no
    Contract ID at all", which no future upload could ever fix.
    """
    findings = result.get("findings", [])
    if len(findings) != 1:
        return False
    finding = findings[0]
    return (
        finding.get("category") == "contract_lookup"
        and finding.get("status") == "Fail"
        and finding.get("description", "").startswith("No contract found for")
    )


def needs_retry(result: dict) -> bool:
    """
    True if this result might change once more documents are uploaded --
    either the session-level guard (no contract/policy at all) or this
    invoice's specific contract not being present yet.
    """
    return "error" in result or _is_missing_contract(result)


def resolve_session_invoices(session_id: str, force: bool = False) -> list[dict]:
    """
    Re-validates this session's known invoices.

    force=False (default): only re-checks ones not yet resolved, and
    only returns ones that just became resolvable -- used on every
    request as a silent auto-retry, so it doesn't repeat an old result
    on unrelated messages.

    force=True: re-checks and returns every known invoice regardless of
    prior state -- used when the user explicitly asks to validate.
    """
    results = []
    for entry in _SESSION_INVOICES.get(session_id, []):
        if entry["resolved"] and not force:
            continue

        result = validate_session_invoice(session_id, entry["path"])
        entry["resolved"] = not needs_retry(result)

        if force or entry["resolved"]:
            results.append(result)

    return results


def validate_session_invoice(session_id: str, invoice_path: str) -> dict:
    """
    Validates an uploaded invoice against whatever contract (required)
    and policy (optional) have been uploaded to this same chat session
    -- NOT the permanent knowledge base.

    A contract is required -- every check (supplier, tax ID, dates,
    amount, payment terms) compares the invoice directly against it and
    has nothing to compare against without one. A policy is NOT
    required: the tolerance %/payment-term checks already fall back to
    documented defaults (5%, Net 30) when no policy is present. So
    contract-only validation is valid, just less precise than
    contract+policy.

    Returns the raw ComplianceReport dict (status + all findings) on
    success, or {"error": "..."} if no contract is present --
    presentation/formatting is left to the caller.
    """
    retriever = Retriever(collection_name=session_collection_name(session_id))

    if not retriever.get_by_doc_type("contract"):
        return {
            "error": (
                "Missing a contract in this session -- upload one before "
                "validating an invoice."
            )
        }

    engine = InvoiceValidationEngine(retriever=retriever)
    report = engine.validate_invoice(invoice_path)

    return report.to_dict()
