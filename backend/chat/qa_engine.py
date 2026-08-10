from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from backend.llm.llm_provider import LLMProvider
from backend.retrieval.retriever import Retriever

PROMPT_TEMPLATE = """You are a compliance assistant. Answer the question using ONLY \
the document text provided below (policy, contract, and/or invoice text \
uploaded this session). If the answer isn't in the text, say so clearly instead \
of guessing. Use the conversation so far only to understand what the user is \
referring to (e.g. "that section") -- the document text is still the only \
source of truth for facts.

DOCUMENT TEXT:
{context}
{history_block}
QUESTION: {question}

ANSWER:"""

# How many prior turns (user+assistant pairs) to carry into the prompt.
# Keeps prompt size bounded rather than growing unboundedly with the session.
MAX_HISTORY_MESSAGES = 6


class PolicyQAEngine:
    """
    Answers a question against whatever policy, contract, or invoice
    documents have been uploaded in this chat session: retrieve relevant
    chunks from the session's collection, then have the LLM answer
    grounded in them.

    Conversation history is passed in per-call (not stored here) --
    the chat session's messages already live server-side in the Express
    layer, so this stays a single source of truth instead of tracking
    the same history twice.
    """

    def __init__(self, llm: LLMProvider, top_k: int = 5):
        self.llm = llm
        self.top_k = top_k

    def answer(self, retriever: Retriever, question: str, history: list[dict] | None = None) -> dict:

        chunks = retriever.retrieve(
            question,
            top_k=self.top_k,
            doc_type_filter=["policy", "contract", "invoice"],
        )

        if not chunks:
            return {
                "reply": (
                    "I don't have any uploaded policy, contract, or invoice "
                    "document to answer that from yet -- upload one first."
                ),
                "citations": [],
            }

        context = "\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.text}" for chunk in chunks
        )

        history_block = self._format_history(history)

        prompt = PROMPT_TEMPLATE.format(
            context=context,
            history_block=history_block,
            question=question,
        )

        reply = self.llm.generate(prompt)

        citations = sorted({chunk.source for chunk in chunks})

        return {"reply": reply, "citations": citations}

    @staticmethod
    def _to_messages(history: list[dict] | None) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for turn in history or []:
            text = turn.get("text")
            if not text:
                continue
            if turn.get("role") == "user":
                messages.append(HumanMessage(content=text))
            elif turn.get("role") == "assistant":
                messages.append(AIMessage(content=text))
        return messages[-MAX_HISTORY_MESSAGES:]

    def _format_history(self, history: list[dict] | None) -> str:
        messages = self._to_messages(history)
        if not messages:
            return ""

        lines = [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in messages
        ]
        return "\nCONVERSATION SO FAR:\n" + "\n".join(lines) + "\n"
