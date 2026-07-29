import sys
from pathlib import Path
from typing import Iterable

from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.pdf_parser import parse_pdf
from backend.ingestion.chunker import chunk_text
from backend.ingestion.embedder import embed_chunks
from backend.ingestion.vector_store import ChromaStore

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


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

    embeddings = embed_chunks(chunks)
    store.add(embeddings=embeddings, chunks=chunks, source=path.name)
    return len(chunks)


def find_source_files(source_dir: Path) -> Iterable[Path]:
    yield from source_dir.rglob("*")   # always recursive


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
            print(f"  -> {chunk_count} chunks")

    store.persist()
    return total_chunks


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python ingest_knowledge_base.py <folder_path>")
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    total = ingest_directory(source_dir)
    print(f"Finished ingesting. Total chunks added: {total}")


if __name__ == "__main__":
    main()
