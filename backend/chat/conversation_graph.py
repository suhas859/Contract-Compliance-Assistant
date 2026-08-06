import sqlite3
from pathlib import Path
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, MessagesState, StateGraph

from backend.chat.qa_engine import PolicyQAEngine
from backend.chat.session_documents import session_collection_name
from backend.retrieval.retriever import Retriever


class ConversationState(MessagesState):
    session_id: str
    upload_note: str | None
    citations: list[str]


class ConversationGraph:
    """Small LangGraph wrapper that persists each chat in SQLite."""

    def __init__(self, qa_engine: PolicyQAEngine, db_path: str = "data/chat_history.sqlite"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(connection)

        builder = StateGraph(ConversationState)
        builder.add_node("answer", self._answer)
        builder.add_edge(START, "answer")
        self.graph = builder.compile(checkpointer=checkpointer)
        self.qa_engine = qa_engine

    def _answer(self, state: ConversationState) -> dict:
        messages = state["messages"]
        question = str(messages[-1].content).strip()
        upload_note = state.get("upload_note")

        if question:
            retriever = Retriever(
                collection_name=session_collection_name(state["session_id"])
            )
            previous_messages = messages[:-1][-6:]
            conversation = "\n".join(
                f"{message.type}: {message.content}" for message in previous_messages
            )
            result = self.qa_engine.answer(retriever, question, conversation)
            reply = result["reply"]
            citations = result["citations"]
        else:
            reply = upload_note or "No message provided."
            citations = []

        if upload_note and question:
            reply = f"{upload_note}\n\n{reply}"

        return {
            "messages": [
                AIMessage(content=reply, additional_kwargs={"citations": citations})
            ],
            "citations": citations,
            "upload_note": None,
        }

    def answer(
        self,
        session_id: str,
        message: str,
        upload_note: str | None,
        file_names: list[str],
    ) -> dict:
        config = {"configurable": {"thread_id": session_id}}
        result = self.graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=message,
                        additional_kwargs={"file_names": file_names},
                    )
                ],
                "session_id": session_id,
                "upload_note": upload_note,
                "citations": [],
            },
            config,
        )
        assistant_message = result["messages"][-1]
        return {
            "reply": str(assistant_message.content),
            "citations": assistant_message.additional_kwargs.get("citations", []),
        }

    def history(self, session_id: str) -> list[dict]:
        config = {"configurable": {"thread_id": session_id}}
        snapshot = self.graph.get_state(config)
        messages = snapshot.values.get("messages", []) if snapshot.values else []

        history = []
        for message in messages:
            if isinstance(message, HumanMessage):
                history.append({
                    "role": "user",
                    "text": str(message.content),
                    "fileNames": message.additional_kwargs.get("file_names", []),
                })
            elif isinstance(message, AIMessage):
                history.append({
                    "role": "assistant",
                    "text": str(message.content),
                    "citations": message.additional_kwargs.get("citations", []),
                })
        return history
