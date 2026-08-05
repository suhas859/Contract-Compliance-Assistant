from backend.llm.llm_provider import LLMProvider
from backend.retrieval.retriever import Retriever

PROMPT_TEMPLATE = """You are a compliance assistant. Answer the question using ONLY \
the policy text provided below. If the answer isn't in the text, say so clearly \
instead of guessing.

POLICY TEXT:
{context}

QUESTION: {question}

ANSWER:"""


class PolicyQAEngine:
    """
    Answers a question against whatever policy documents have been
    uploaded in this chat session: retrieve relevant chunks from the
    session's collection, then have the LLM answer grounded in them.
    """

    def __init__(self, llm: LLMProvider, top_k: int = 5):
        self.llm = llm
        self.top_k = top_k

    def answer(self, retriever: Retriever, question: str) -> dict:

        chunks = retriever.retrieve(
            question,
            top_k=self.top_k,
            doc_type_filter=["policy"],
        )

        if not chunks:
            return {
                "reply": (
                    "I don't have any uploaded policy document to answer that "
                    "from yet -- upload one first."
                ),
                "citations": [],
            }

        context = "\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.text}" for chunk in chunks
        )

        prompt = PROMPT_TEMPLATE.format(context=context, question=question)

        reply = self.llm.generate(prompt)

        citations = sorted({chunk.source for chunk in chunks})

        return {"reply": reply, "citations": citations}
