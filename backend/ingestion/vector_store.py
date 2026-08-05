import chromadb
from uuid import uuid4


class ChromaStore:
    def __init__(self, collection_name="documents"):
        self.client = chromadb.PersistentClient(path="chroma_db")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(self, embeddings, chunks, source, doc_type=None, doc_id=None):
        upload_id = uuid4().hex
        ids = [f"{upload_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source": source,
                "doc_type": doc_type or "unknown",
                "doc_id": doc_id or "",
            }
            for _ in chunks
        ]
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

    def query(self, query_embedding, n_results=3, where=None):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def get_by_metadata(self, where: dict) -> dict:
        return self.collection.get(where=where)

    def persist(self):
        pass
