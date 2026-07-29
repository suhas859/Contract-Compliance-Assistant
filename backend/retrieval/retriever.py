from dataclasses import dataclass

from backend.ingestion.embedder import embed_query
from backend.ingestion.vector_store import ChromaStore


@dataclass
class RetrievedChunk:
    text: str
    source: str
    score: float
    doc_type: str | None
    doc_id: str | None


class Retriever:
    def __init__(self, collection_name: str = "knowledge_base", score_threshold: float = 0.3):
        self.store = ChromaStore(collection_name=collection_name)
        self.score_threshold = score_threshold

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """
        Embeds the query (using embed_query, with the correct
        "search_query:" prefix) and retrieves the top_k most relevant
        chunks from the knowledge base, filtered by a minimum
        similarity threshold so weak/irrelevant matches don't get fed
        to the LLM as if they were real evidence.
        """
        query_embedding = embed_query(query)
        raw = self.store.query(query_embedding, n_results=top_k)
        documents = raw["documents"][0]
        metadatas = raw["metadatas"][0]
        distances = raw["distances"][0]

        chunks = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            similarity = 1 - distance  # cosine distance -> similarity
            if similarity >= self.score_threshold:
                chunks.append(RetrievedChunk(text=doc,
                    source=meta.get("source", "unknown"),
                    score=similarity,
                    doc_type=meta.get("doc_type"),
                    doc_id=meta.get("doc_id"),
                ))

        return chunks