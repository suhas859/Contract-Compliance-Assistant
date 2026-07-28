from fastapi import APIRouter, UploadFile, File, HTTPException
import os

from backend.ingestion.parsers.pdf_parser import parse_pdf
from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.md_parser import parse_md

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
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format"
    )

    # Chunk
    chunks = chunk_text(text)

    # Embed
    embeddings = embed_chunks(chunks)

    # Store
    vector_store.add(
        embeddings=embeddings,
        chunks=chunks,
        source=file.filename
    )

    vector_store.persist()

    return {
        "status": "success",
        "chunks": len(chunks),
        "file": file.filename
    }
