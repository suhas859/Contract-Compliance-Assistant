import os

from fastapi import APIRouter, File, Form, UploadFile

from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import ingest_session_file, session_collection_name
from backend.llm.llm_provider import OllamaLLM
from backend.retrieval.retriever import Retriever

router = APIRouter()

llm = OllamaLLM()
qa_engine = PolicyQAEngine(llm)


@router.post("/chat")
async def chat(
    message: str = Form(""),
    session_id: str = Form("default"),
    file: UploadFile | None = File(None),
):
    upload_note = None

    if file is not None:
        safe_name = os.path.basename(file.filename)
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{session_id}_{safe_name}")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        chunk_count = ingest_session_file(session_id, file_path, safe_name)
        upload_note = f"Uploaded and indexed {safe_name} ({chunk_count} chunks)."

    if not message.strip():
        return {
            "reply": upload_note or "No message provided.",
            "citations": [],
        }

    retriever = Retriever(collection_name=session_collection_name(session_id))
    result = qa_engine.answer(retriever, message)

    if upload_note:
        result["reply"] = f"{upload_note}\n\n{result['reply']}"

    return result
