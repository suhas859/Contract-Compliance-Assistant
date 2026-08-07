import json
import os

from fastapi import APIRouter, File, Form, UploadFile

from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import ingest_session_file, session_collection_name
from backend.chat.session_invoice_validation import validate_session_invoice
from backend.llm.llm_provider import OllamaLLM, OpenAILLM
from backend.retrieval.retriever import Retriever
from backend.validation.invoice_parser import InvoiceParser

router = APIRouter()

# One PolicyQAEngine per provider, built once -- selecting a provider per
# request just picks which engine answers, no per-request construction.
QA_ENGINES = {
    "ollama": PolicyQAEngine(OllamaLLM()),
    "openai": PolicyQAEngine(OpenAILLM()),
}
DEFAULT_PROVIDER = "ollama"

invoice_parser = InvoiceParser()


STATUS_ICONS = {
    "Compliant": "✓",
    "Partially Compliant": "⚠",
    "Non-Compliant": "✗",
}

FINDING_ICONS = {
    "Pass": "✓",
    "Warning": "⚠",
    "Fail": "✗",
}

RECOMMENDATIONS = {
    "supplier_match": "Verify the supplier details and use the supplier named in the approved contract.",
    "contract_period": "Confirm the invoice date or obtain a valid contract extension or amendment.",
    "payment_amount": "Revise the invoice or obtain an approved contract amendment.",
    "payment_terms": "Correct the due date to match the applicable payment terms.",
    "contract_lookup": "Add the correct Contract ID and ensure the approved contract is available.",
}


def format_validation(validation: dict) -> str:
    """Render one validation report in the human-readable chat format."""
    if "error" in validation:
        return f"Compliance Status:\n⚠ Unable to Validate\n\nRecommendations\n- {validation['error']}"

    status = validation.get("status", "Partially Compliant")
    findings = validation.get("findings", [])
    lines = [
        "Compliance Status:",
        f"{STATUS_ICONS.get(status, '⚠')} {status}",
        "",
        "Findings",
    ]

    for finding in findings:
        icon = FINDING_ICONS.get(finding.get("status"), "⚠")
        description = finding.get("description", "No details available.")
        citation = finding.get("citation")
        suffix = f" ({citation})" if citation else ""
        lines.append(f"{icon} {description}{suffix}")

    lines.extend(["", "Related ServiceNow Incidents"])
    incidents = validation.get("related_incidents", [])
    if incidents:
        lines.extend(f"- {incident}" for incident in incidents)
    else:
        lines.append("- No related incidents available (ServiceNow integration is not configured).")

    lines.extend(["", "Recommendations"])
    categories = {
        finding.get("category")
        for finding in findings
        if finding.get("status") in {"Warning", "Fail"}
    }
    recommendations = [
        recommendation
        for category, recommendation in RECOMMENDATIONS.items()
        if category in categories
    ]
    if recommendations:
        lines.extend(f"- {recommendation}" for recommendation in recommendations)
    else:
        lines.append("- No corrective action is required.")

    return "\n".join(lines)


def summarize_validations(validations: list[dict]) -> str:
    return "\n\n".join(format_validation(validation) for validation in validations)


@router.post("/chat")
async def chat(
    message: str = Form(""),
    session_id: str = Form("default"),
    history: str = Form("[]"),
    provider: str = Form(DEFAULT_PROVIDER),
    files: list[UploadFile] = File([]),
):
    qa_engine = QA_ENGINES.get(provider, QA_ENGINES[DEFAULT_PROVIDER])

    upload_notes = []
    validations = []

    try:
        parsed_history = json.loads(history)
    except (json.JSONDecodeError, TypeError):
        parsed_history = []

    # Two passes: ingest every policy/contract first, THEN validate any
    # invoices. Files uploaded together in one request arrive in
    # whatever order the browser selected them -- if an invoice were
    # processed before its own contract/policy from the same batch,
    # the "do we have a contract and policy yet" guard would wrongly
    # fail even though everything needed was right there in the request.
    saved_files = []

    for file in files:
        safe_name = os.path.basename(file.filename)
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{session_id}_{safe_name}")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        saved_files.append((file_path, safe_name))

    invoice_files = []

    for file_path, safe_name in saved_files:
        # An invoice needs validation, not Q&A indexing -- detect it by
        # trying to parse an Invoice ID out of it first. Policies and
        # contracts won't match this and get ingested normally below.
        parsed_invoice = invoice_parser.parse(file_path)

        if parsed_invoice.get("invoice_id"):
            invoice_files.append(file_path)
        else:
            ingest_result = ingest_session_file(session_id, file_path, safe_name)
            upload_notes.append(
                f"Uploaded and indexed {safe_name} as a {ingest_result['doc_type']} "
                f"({ingest_result['chunk_count']} chunks)."
            )

    for file_path in invoice_files:
        validation = validate_session_invoice(session_id, file_path)
        if "error" not in validation:
            categories = {
                finding.get("category")
                for finding in validation.get("findings", [])
                if finding.get("status") in {"Warning", "Fail"}
            }
            validation["recommendations"] = [
                recommendation
                for category, recommendation in RECOMMENDATIONS.items()
                if category in categories
            ]
            validation["related_incidents"] = []
        validations.append(validation)

    upload_note = "\n".join(upload_notes) or None

    # An invoice that was just validated shouldn't have its result
    # overridden by a coincidental Q&A answer to whatever text came
    # along with the upload -- the validation IS the response here,
    # regardless of what (if anything) the user typed alongside it.
    if validations:
        reply_parts = [p for p in [upload_note, summarize_validations(validations)] if p]
        return {
            "reply": "\n\n".join(reply_parts),
            "upload_note": upload_note,
            "citations": [],
            "validations": validations,
        }

    if not message.strip():
        return {
            "reply": upload_note or "",
            "citations": [],
            "validations": [],
        }

    retriever = Retriever(collection_name=session_collection_name(session_id))
    result = qa_engine.answer(retriever, message, history=parsed_history)

    if upload_note:
        result["reply"] = f"{upload_note}\n\n{result['reply']}"
    result["validations"] = []

    return result
