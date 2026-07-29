from backend.retrieval.retriever import Retriever

retriever = Retriever(collection_name="knowledge_base")

test_questions = [
    "What is the approval threshold for a new contract?",
    "Is advance payment allowed?",
    "What clauses must every contract include?",
    "How long do confidentiality obligations last after termination?",
    "What happens if an invoice exceeds the contract value?",
]

for q in test_questions:
    print(f"\n{'='*70}")
    print(f"Q: {q}")
    print('='*70)
    results = retriever.retrieve(q, top_k=3)

    if not results:
        print("  ⚠ NO RESULTS — check score_threshold or whether KB was ingested")
        continue

    for r in results:
        print(f"\n  [score: {r.score:.3f}] source: {r.source}")
        print(f"  {r.text[:150]}...")