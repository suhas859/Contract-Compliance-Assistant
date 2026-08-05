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


# Same ID-prefix convention used throughout the knowledge base
# (CTR-..., POL-..., SOP-..., KA-...) -- reused here since a session
# upload has no folder to infer type from the way ingest_knowledge_base.py
# does for the permanent collection.
DOC_TYPE_PREFIXES = {
    "CTR-": "contract",
    "POL-": "policy",
    "SOP-": "sop",
    "KA-": "knowledge_article",
}


def infer_doc_type(doc_id: str | None) -> str:
    if doc_id:
        for prefix, doc_type in DOC_TYPE_PREFIXES.items():
            if doc_id.startswith(prefix):
                return doc_type
    return "policy"


def ingest_session_file(
    session_id: str,
    file_path: str,
    original_filename: str,
    doc_type: str | None = None,
) -> dict:
    """
    Parses, chunks, embeds, and stores an uploaded file into this
    session's collection. doc_type is auto-detected from the document's
    own ID (e.g. "Contract ID: CTR-...") unless explicitly overridden --
    lets one upload path handle both policies and contracts.
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
        return {"chunk_count": 0, "doc_type": doc_type or "policy"}

    doc_id = extract_doc_id(text)
    resolved_doc_type = doc_type or infer_doc_type(doc_id)

    embeddings = embed_chunks(chunks)

    store = ChromaStore(collection_name=session_collection_name(session_id))
    store.add(
        embeddings=embeddings,
        chunks=chunks,
        source=original_filename,
        doc_type=resolved_doc_type,
        doc_id=doc_id,
    )
    store.persist()

    return {"chunk_count": len(chunks), "doc_type": resolved_doc_type}
