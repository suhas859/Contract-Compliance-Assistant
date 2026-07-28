import chromadb


class ChromaStore:
    def __init__(self, collection_name="documents"):
        # Creates a persistent database in ./chroma_db
        self.client = chromadb.PersistentClient(path="chroma_db")

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
        # ChromaDB 1.x persists automatically.
        # Kept for compatibility with the rest of your code.
        pass