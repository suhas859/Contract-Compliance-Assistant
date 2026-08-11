import json
import os

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from backend.chat.chat_store import SQLiteChatMessageHistory, get_session_messages, list_sessions
from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import session_collection_name
from backend.chat.session_invoice_validation import (
    get_session_invoices,
    ingest_and_register,
    resolve_session_invoices,
)
from backend.chat.validation_presentation import (
    attach_recommendations,
    is_validate_intent,
    related_incidents_for_session,
    summarize_validations,
)
from backend.llm.llm_provider import OllamaLLM, OpenAILLM
from backend.retrieval.retriever import Retriever

router = APIRouter()

# One PolicyQAEngine per provider, built once -- selecting a provider per
# request just picks which engine answers, no per-request construction.
QA_ENGINES = {
    "ollama": PolicyQAEngine(OllamaLLM()),
    "openai": PolicyQAEngine(OpenAILLM()),
}
DEFAULT_PROVIDER = "ollama"


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
        ingest_result = ingest_and_register(session_id, file_path, safe_name)
        upload_notes.append(
            f"Uploaded and indexed {safe_name} as a{'n' if ingest_result['doc_type'] == 'invoice' else ''} "
            f"{ingest_result['doc_type']} ({ingest_result['chunk_count']} chunks)."
        )

        if ingest_result["doc_type"] == "invoice":
            invoice_files.append((file_path, safe_name))

    related_incidents = related_incidents_for_session(session_id)

    if invoice_files:
        # Freshly uploaded invoice(s) this request -- validate immediately
        # so there's always feedback right away.
        validations = [
            attach_recommendations(v, related_incidents)
            for v in resolve_session_invoices(session_id, force=True)
        ]
    elif message.strip() and is_validate_intent(message) and get_session_invoices(session_id):
        # No new invoice this request, but the user is explicitly asking
        # to validate one uploaded earlier in this chat.
        validations = [
            attach_recommendations(v, related_incidents)
            for v in resolve_session_invoices(session_id, force=True)
        ]
    else:
        # Routine message/upload -- silently pick up anything that
        # couldn't be resolved before (e.g. its policy just arrived),
        # without repeating an old result on an unrelated message.
        validations = [
            attach_recommendations(v, related_incidents)
            for v in resolve_session_invoices(session_id)
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
