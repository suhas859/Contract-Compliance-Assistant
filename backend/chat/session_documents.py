from pathlib import Path

from backend.ingestion.chunker import chunk_text
from backend.ingestion.embedder import embed_chunks
from backend.ingestion.ingest_knowledge_base import extract_doc_id
from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.pdf_parser import parse_pdf
from backend.ingestion.vector_store import ChromaStore


def session_collection_name(session_id: str) -> str:
    """
    Documents uploaded mid-chat live in their own ChromaDB collection per
    session.
    """
    return f"session_{session_id}"


def ingest_session_file(
    session_id: str,
    file_path: str,
    original_filename: str,
    doc_type: str = "policy",
) -> int:
    """
    Parses, chunks, embeds, and stores an uploaded file into this
    session's collection.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        text = parse_pdf(file_path)
    elif suffix == ".docx":
        text = parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    chunks = chunk_text(text)
    if not chunks:
        return 0

    doc_id = extract_doc_id(text)

    embeddings = embed_chunks(chunks)

    store = ChromaStore(collection_name=session_collection_name(session_id))
    store.add(
        embeddings=embeddings,
        chunks=chunks,
        source=original_filename,
        doc_type=doc_type,
        doc_id=doc_id,
    )
    store.persist()

    return len(chunks)
