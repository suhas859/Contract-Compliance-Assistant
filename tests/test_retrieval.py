from backend.retrieval.retriever import Retriever

retriever = Retriever(collection_name="knowledge_base")


def section(title: str):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


# --- 1. Basic semantic search still works (regression check) ---
section("1. Basic semantic search (no filter) — regression check")
results = retriever.retrieve("What is the approval threshold for a new contract?", top_k=3)
for r in results:
    print(f"  [{r.score:.3f}] {r.source} | doc_type={r.doc_type} | doc_id={r.doc_id}")
    print(f"    {r.text[:100]}...")


# --- 2. doc_type_filter actually excludes what it should ---
section("2. Filtered search: policy/sop only, should return NO contracts")
results = retriever.retrieve(
    "What is the approval threshold for a new contract?",
    top_k=5,
    doc_type_filter=["policy", "sop"],
)
all_correct_type = all(r.doc_type in ["policy", "sop"] for r in results)
print(f"  Results: {len(results)} | All doc_type in [policy, sop]: {all_correct_type}")
for r in results:
    print(f"  [{r.score:.3f}] {r.source} | doc_type={r.doc_type}")

section("3. Filtered search: contract only")
results = retriever.retrieve(
    "data privacy and confidentiality requirements",
    top_k=5,
    doc_type_filter=["contract"],
)
all_correct_type = all(r.doc_type == "contract" for r in results)
print(f"  Results: {len(results)} | All doc_type == contract: {all_correct_type}")
for r in results:
    print(f"  [{r.score:.3f}] {r.source} | doc_type={r.doc_type}")


# --- 4. Exact contract lookup by ID ---
section("4. get_contract_by_id — exact lookup, not semantic search")
# Use a real Contract ID from your knowledge_base/approved_contracts/ files
contract_id = "CTR-2026-0088"  # Acme Logistics
chunks = retriever.get_contract_by_id(contract_id)
print(f"  Looked up: {contract_id}")
print(f"  Chunks found: {len(chunks)}")
if chunks:
    sources = {c.source for c in chunks}
    print(f"  Source file(s): {sources}")
    print(f"  All scores == 1.0 (exact match, not similarity): {all(c.score == 1.0 for c in chunks)}")
else:
    print("  ⚠ NO CHUNKS FOUND — check the ID is correct and the KB was re-ingested "
          "with the updated ingest_knowledge_base.py (doc_id metadata)")


# --- 5. Lookup with a WRONG id should return empty, not crash ---
section("5. get_contract_by_id with a nonexistent ID — should return []")
chunks = retriever.get_by_id("CTR-9999-9999")
print(f"  Chunks found: {len(chunks)} (expected: 0)")


# --- 6. get_by_id works for non-contract types too ---
section("6. get_by_id — a policy and a knowledge article")
for doc_id in ["POL-PROC-001", "KA-0142"]:
    chunks = retriever.get_by_id(doc_id)
    print(f"  {doc_id}: {len(chunks)} chunks found")