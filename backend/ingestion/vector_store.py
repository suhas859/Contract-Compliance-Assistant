import chromadb
from chromadb.config import Settings

class ChromaStore:
    def __init__(self, collection_name="documents"):
        self.client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory="chroma_db"
            )
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(self, embeddings, chunks, source):
        ids = [f"{source}_{i}" for i in range(len(chunks))]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"source": source} for _ in chunks]
        )

    def persist(self):
        self.client.persist()
