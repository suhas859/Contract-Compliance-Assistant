from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1.5",
    trust_remote_code=True
)


def embed_chunks(chunks: list[str]):
    formatted_chunks = [
        f"search_document: {chunk}"
        for chunk in chunks
    ]

    embeddings = model.encode(
        formatted_chunks,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    return embeddings.tolist()


def embed_query(question: str):
    
    formatted_query = f"search_query: {question}"

    embedding = model.encode(
        formatted_query,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    return embedding.tolist()

