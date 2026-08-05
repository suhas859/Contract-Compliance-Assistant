import json
import os

from fastapi import APIRouter, File, Form, UploadFile

from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import ingest_session_file, session_collection_name
# from backend.llm.llm_provider import OllamaLLM
from backend.llm.llm_provider import OpenAILLM
from backend.retrieval.retriever import Retriever

router = APIRouter()

# llm = OllamaLLM()
llm = OpenAILLM()
qa_engine = PolicyQAEngine(llm)  # Use OpenAI LLM for QA engine


@router.post("/chat")
async def chat(
    message: str = Form(""),
    session_id: str = Form("default"),
    history: str = Form("[]"),
    files: list[UploadFile] = File([]),
):
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

        chunk_count = ingest_session_file(session_id, file_path, safe_name)
        upload_notes.append(
            f"Uploaded and indexed {safe_name} ({chunk_count} chunks)."
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
