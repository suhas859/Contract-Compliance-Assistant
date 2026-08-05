import json
import os

from fastapi import APIRouter, File, Form, UploadFile

from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import ingest_session_file, session_collection_name
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

    try:
        parsed_history = json.loads(history)
    except (json.JSONDecodeError, TypeError):
        parsed_history = []

    for file in files:
        safe_name = os.path.basename(file.filename)
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{session_id}_{safe_name}")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        ingest_result = ingest_session_file(session_id, file_path, safe_name)
        upload_notes.append(
            f"Uploaded and indexed {safe_name} as a {ingest_result['doc_type']} "
            f"({ingest_result['chunk_count']} chunks)."
        )

    upload_note = "\n".join(upload_notes) or None

    if not message.strip():
        return {
            "reply": upload_note or "No message provided.",
            "citations": [],
        }

    retriever = Retriever(collection_name=session_collection_name(session_id))
    result = qa_engine.answer(retriever, message, history=parsed_history)

    if upload_note:
        result["reply"] = f"{upload_note}\n\n{result['reply']}"

    return result
