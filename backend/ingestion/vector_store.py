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


    def query(self, query_embedding, n_results=3):
        """
        Search the vector database for the most similar chunks.

        Args:
            query_embedding (list[float]): Embedding of the user's query.
            n_results (int): Number of results to return.

        Returns:
            dict: ChromaDB query results.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return results


    
    def persist(self):
        # ChromaDB 1.x persists automatically.
        # Kept for compatibility with the rest of your code.
        pass