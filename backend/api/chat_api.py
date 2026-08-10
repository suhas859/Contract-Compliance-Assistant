import json
import os

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from backend.chat.chat_store import SQLiteChatMessageHistory, get_session_messages, list_sessions
from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import ingest_session_file, session_collection_name
from backend.chat.session_invoice_validation import (
    get_session_invoices,
    register_session_invoice,
    resolve_session_invoices,
)
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
    "tax_id_match": "Verify the tax ID and use the tax ID recorded in the approved contract.",
    "contract_period": "Confirm the invoice date or obtain a valid contract extension or amendment.",
    "payment_amount": "Revise the invoice or obtain an approved contract amendment.",
    "payment_terms": "Correct the due date to match the applicable payment terms.",
    "contract_lookup": "Add the correct Contract ID and ensure the approved contract is available.",
}


def categories_needing_recommendation(findings: list[dict]) -> set[str]:
    return {
        finding.get("category")
        for finding in findings
        if finding.get("status") in {"Warning", "Fail"}
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
    categories = categories_needing_recommendation(findings)
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


def attach_recommendations(validation: dict) -> dict:
    if "error" in validation:
        return validation

    categories = categories_needing_recommendation(validation.get("findings", []))
    validation["recommendations"] = [
        recommendation
        for category, recommendation in RECOMMENDATIONS.items()
        if category in categories
    ]
    validation["related_incidents"] = []
    return validation


def is_validate_intent(message: str) -> bool:
    """
    Lightweight, deterministic check for "please validate this" style
    requests -- e.g. "validate the invoice", "is this valid?". Simple on
    purpose: catches the common phrasing without an extra LLM call just
    to classify intent.
    """
    return "valid" in message.lower()


@router.get("/chat/sessions")
async def sessions():
    return {"sessions": list_sessions()}


@router.get("/chat/sessions/{session_id}")
async def session_history(session_id: str):
    return {"messages": get_session_messages(session_id)}


@router.post("/chat")
async def chat(
    message: str = Form(""),
    session_id: str = Form("default"),
    provider: str = Form(DEFAULT_PROVIDER),
    stream: bool = Form(False),
    files: list[UploadFile] = File([]),
):
    qa_engine = QA_ENGINES.get(provider, QA_ENGINES[DEFAULT_PROVIDER])
    history_store = SQLiteChatMessageHistory(session_id)

    upload_notes = []
    validations = []

    # Save every uploaded file, then ingest ALL of them (policies,
    # contracts, and invoices alike) into the session's collection --
    # invoices need this too now, so a later question can retrieve their
    # content, not just a one-time validation attempt at upload time.
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
        # Detect invoices via InvoiceParser first -- an invoice's text
        # contains both its own Invoice ID and a *reference* to a
        # different document's Contract ID, and the generic doc-ID
        # detection used for policies/contracts doesn't know about
        # "Invoice ID" at all. Left to auto-detect, an invoice would get
        # mistagged as a contract, under the real contract's own ID.
        parsed_invoice = invoice_parser.parse(file_path)
        invoice_id = parsed_invoice.get("invoice_id")

        ingest_result = ingest_session_file(
            session_id,
            file_path,
            safe_name,
            doc_type="invoice" if invoice_id else None,
            doc_id=invoice_id,
        )
        upload_notes.append(
            f"Uploaded and indexed {safe_name} as a{'n' if ingest_result['doc_type'] == 'invoice' else ''} "
            f"{ingest_result['doc_type']} ({ingest_result['chunk_count']} chunks)."
        )

        if invoice_id:
            invoice_files.append((file_path, safe_name))
            register_session_invoice(session_id, file_path, safe_name)

    if invoice_files:
        # Freshly uploaded invoice(s) this request -- validate immediately
        # so there's always feedback right away.
        validations = [
            attach_recommendations(v) for v in resolve_session_invoices(session_id, force=True)
        ]
    elif message.strip() and is_validate_intent(message) and get_session_invoices(session_id):
        # No new invoice this request, but the user is explicitly asking
        # to validate one uploaded earlier in this chat.
        validations = [
            attach_recommendations(v) for v in resolve_session_invoices(session_id, force=True)
        ]
    else:
        # Routine message/upload -- silently pick up anything that
        # couldn't be resolved before (e.g. its policy just arrived),
        # without repeating an old result on an unrelated message.
        validations = [
            attach_recommendations(v) for v in resolve_session_invoices(session_id)
        ]

    upload_note = "\n".join(upload_notes) or None

    # An invoice result shouldn't be overridden by a coincidental Q&A
    # answer to whatever text came along with it -- the validation IS
    # the response here, regardless of what (if anything) was typed.
    if validations:
        reply_parts = [p for p in [upload_note, summarize_validations(validations)] if p]
        result = {
            "reply": "\n\n".join(reply_parts),
            "upload_note": upload_note,
            "citations": [],
            "validations": validations,
        }
    elif not message.strip():
        result = {
            "reply": upload_note or "",
            "upload_note": upload_note,
            "citations": [],
            "validations": [],
        }
    else:
        retriever = Retriever(collection_name=session_collection_name(session_id))
        # Load prior turns from this session's own persisted history --
        # the backend is the single source of truth for it now, rather
        # than trusting whatever the client happens to submit.
        parsed_history = [
            {"role": "user" if isinstance(m, HumanMessage) else "assistant", "text": m.content}
            for m in history_store.messages
        ]
        if stream:
            token_stream, citations = qa_engine.answer_stream(
                retriever, message, history=parsed_history
            )

            def generate_events():
                reply_parts = []
                sequence = 0
                try:
                    if upload_note:
                        reply_parts.append(upload_note + "\n\n")
                        yield json.dumps(
                            {"type": "token", "sequence": sequence, "text": reply_parts[-1]}
                        ) + "\n"
                        sequence += 1
                    for token in token_stream:
                        reply_parts.append(token)
                        yield json.dumps(
                            {"type": "token", "sequence": sequence, "text": token}
                        ) + "\n"
                        sequence += 1
                    reply = "".join(reply_parts)
                    history_store.add_messages([
                        HumanMessage(
                            content=message,
                            additional_kwargs={"fileNames": [name for _, name in saved_files]},
                        ),
                        AIMessage(
                            content=reply,
                            additional_kwargs={
                                "uploadNote": upload_note or "",
                                "citations": citations,
                                "validations": [],
                            },
                        ),
                    ])
                    yield json.dumps(
                        {"type": "done", "sequence": sequence, "citations": citations}
                    ) + "\n"
                except Exception as exc:
                    yield json.dumps({"type": "error", "message": str(exc)}) + "\n"

            return StreamingResponse(
                generate_events(),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "X-Accel-Buffering": "no",
                },
            )

        result = qa_engine.answer(retriever, message, history=parsed_history)

        if upload_note:
            result["reply"] = f"{upload_note}\n\n{result['reply']}"
        result["upload_note"] = upload_note
        result["validations"] = []

    history_store.add_messages(
        [
            HumanMessage(
                content=message,
                additional_kwargs={"fileNames": [safe_name for _, safe_name in saved_files]},
            ),
            AIMessage(
                content=result["reply"],
                additional_kwargs={
                    "uploadNote": result.get("upload_note") or "",
                    "citations": result.get("citations", []),
                    "validations": result.get("validations", []),
                },
            ),
        ]
    )

    return result
