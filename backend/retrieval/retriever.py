from dataclasses import dataclass

from backend.ingestion.embedder import embed_query
from backend.ingestion.vector_store import ChromaStore


@dataclass
class RetrievedChunk:
    text: str
    source: str
    doc_type: str
    doc_id: str
    score: float


class Retriever:
    def __init__(self, collection_name: str = "knowledge_base", score_threshold: float = 0.3):
        self.store = ChromaStore(collection_name=collection_name)
        self.score_threshold = score_threshold

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_type_filter: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Semantic search. Optionally scope to specific doc types, e.g.
        doc_type_filter=["policy", "sop"] to exclude contracts from a
        policy-question search.
        """
        query_embedding = embed_query(query)

        where = None
        if doc_type_filter:
            where = {"doc_type": {"$in": doc_type_filter}}

        raw = self.store.query(query_embedding, n_results=top_k, where=where)

        documents = raw["documents"][0]
        metadatas = raw["metadatas"][0]
        distances = raw["distances"][0]

        chunks = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            similarity = 1 - distance
            if similarity >= self.score_threshold:
                chunks.append(RetrievedChunk(
                    text=doc,
                    source=meta.get("source", "unknown"),
                    doc_type=meta.get("doc_type", "unknown"),
                    doc_id=meta.get("doc_id", ""),
                    score=similarity,
                ))
        return chunks

    def get_by_id(self, doc_id: str) -> list[RetrievedChunk]:
        """
        Exact lookup by document ID, NOT semantic search. Works for any
        doc_type -- policy (POL-...), SOP (SOP-...), contract (CTR-...),
        or knowledge article (KA-...) -- since doc_id is unique across
        all of them regardless of type.
        """
        raw = self.store.get_by_metadata(where={"doc_id": doc_id})

        return [
            RetrievedChunk(
                text=doc,
                source=meta.get("source", "unknown"),
                doc_type=meta.get("doc_type", "unknown"),
                doc_id=meta.get("doc_id", ""),
                score=1.0,  # exact match, not a similarity score
            )
            for doc, meta in zip(raw["documents"], raw["metadatas"])
        ]

    def get_contract_by_id(self, contract_id: str) -> list[RetrievedChunk]:
        """
        Thin, explicitly-named wrapper around get_by_id() for the most
        common exact-lookup case: finding the governing contract
        referenced on an invoice. Kept separate from get_by_id() purely
        for readability at call sites -- functionally identical.
        """
        return self.get_by_id(contract_id)