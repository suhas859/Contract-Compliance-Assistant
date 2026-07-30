import re
import sys
from pathlib import Path
from typing import Iterable

from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.pdf_parser import parse_pdf
from backend.ingestion.chunker import chunk_text
from backend.ingestion.embedder import embed_chunks
from backend.ingestion.vector_store import ChromaStore

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

DOC_ID_PATTERN = re.compile(r"(?:Document ID|Contract ID|Article ID):\s*([A-Za-z0-9\-]+)")


def get_doc_type(path: Path) -> str:
    """
    Derives the document type from which folder it lives in under
    knowledge_base/. Used to scope retrieval later (e.g. exclude
    contracts from a pure policy-question search).
    """
    parts = path.parts
    if "policies" in parts:
        return "policy"
    if "sops" in parts:
        return "sop"
    if "knowledge_articles" in parts:
        return "knowledge_article"
    if "approved_contracts" in parts:
        return "contract"
    return "unknown"


def extract_doc_id(text: str) -> str | None:
    """
    Pulls the document's own ID out of its content -- supports
    "Document ID:" (policies/SOPs), "Contract ID:" (contracts), and
    "Article ID:" (knowledge articles).
    """
    match = DOC_ID_PATTERN.search(text)
    return match.group(1) if match else None


def ingest_file(path: Path, store: ChromaStore) -> int:
    ext = path.suffix.lower()
    if ext == ".pdf":
        text = parse_pdf(str(path))
    elif ext == ".docx":
        text = parse_docx(str(path))
    else:
        print(f"[ERROR] Unsupported file type: {ext} (only .pdf and .docx allowed)")
        return 0

    chunks = chunk_text(text)
    if not chunks:
        print(f"[WARNING] no chunks extracted from {path}")
        return 0

    doc_type = get_doc_type(path)
    doc_id = extract_doc_id(text)
    if doc_id is None:
        print(f"[WARNING] no Document/Contract/Article ID found in {path.name} -- "
              f"exact lookup by ID won't work for this file")

    embeddings = embed_chunks(chunks)
    store.add(
        embeddings=embeddings,
        chunks=chunks,
        source=path.name,
        doc_type=doc_type,
        doc_id=doc_id,
    )
    return len(chunks)


def find_source_files(source_dir: Path) -> Iterable[Path]:
    yield from source_dir.rglob("*")


def ingest_directory(source_dir: Path) -> int:
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"source directory does not exist: {source_dir}")

    store = ChromaStore(collection_name="knowledge_base")
    total_chunks = 0

    for path in sorted(find_source_files(source_dir)):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        print(f"Ingesting {path}")
        try:
            chunk_count = ingest_file(path, store)
        except Exception as e:
            print(f"[ERROR] Failed to ingest {path}: {e}")
            continue

        if chunk_count > 0:
            total_chunks += chunk_count
            print(f"  -> {chunk_count} chunks (doc_type={get_doc_type(path)})")

    store.persist()
    return total_chunks


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python ingest_knowledge_base.py <folder_path>")
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    total = ingest_directory(source_dir)
    print(f"Finished ingesting. Total chunks added: {total}")


if __name__ == "__main__":
    main()