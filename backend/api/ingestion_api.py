from fastapi import APIRouter, UploadFile, File
import os

from backend.ingestion.parsers.pdf_parser import parse_pdf
from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.md_parser import parse_md
from backend.ingestion.parsers.json_parser import parse_json

from backend.ingestion.chunker import chunk_text
from backend.ingestion.embedder import embed_chunks
from backend.ingestion.vector_store import ChromaStore

router = APIRouter()
vector_store = ChromaStore()

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    file_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Parse based on extension
    ext = file.filename.lower()

    if ext.endswith(".pdf"):
        text = parse_pdf(file_path)
    elif ext.endswith(".docx"):
        text = parse_docx(file_path)
    elif ext.endswith(".md"):
        text = parse_md(file_path)
    elif ext.endswith(".json"):
        text = parse_json(file_path)
    else:
        return {"error": "Unsupported file format"}

    # Chunk
    chunks = chunk_text(text)

    # Embed
    embeddings = embed_chunks(chunks)

    # Store
    metadata = [{"chunk": c, "source": file.filename} for c in chunks]
    vector_store.add(embeddings, metadata)
    vector_store.save()

    return {
        "status": "success",
        "chunks": len(chunks),
        "file": file.filename
    }
