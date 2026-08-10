import json
import sqlite3
import time
from pathlib import Path

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, message_to_dict, messages_from_dict

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chat_history.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            session_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            message TEXT NOT NULL,
            ts REAL NOT NULL,
            PRIMARY KEY (session_id, position)
        )
        """
    )
    return conn


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain BaseChatMessageHistory backed by a local SQLite file --
    keeps each chat session's turns across server restarts using
    langchain-core's message schema, without pulling in LangGraph or
    any agent runtime.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def messages(self) -> list[BaseMessage]:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT message FROM chat_messages WHERE session_id = ? ORDER BY position",
                (self.session_id,),
            ).fetchall()
        finally:
            conn.close()
        return messages_from_dict([json.loads(row[0]) for row in rows])

    def add_messages(self, messages) -> None:
        conn = _connect()
        try:
            next_pos = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM chat_messages WHERE session_id = ?",
                (self.session_id,),
            ).fetchone()[0]
            now = time.time()
            conn.executemany(
                "INSERT INTO chat_messages (session_id, position, message, ts) VALUES (?, ?, ?, ?)",
                [
                    (self.session_id, next_pos + offset, json.dumps(message_to_dict(message)), now)
                    for offset, message in enumerate(messages)
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def clear(self) -> None:
        conn = _connect()
        try:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (self.session_id,))
            conn.commit()
        finally:
            conn.close()


def _title_from_messages(messages: list[BaseMessage]) -> str:
    for message in messages:
        if not isinstance(message, HumanMessage):
            continue
        text = (message.content or "").strip()
        if text:
            return text[:42] + "…" if len(text) > 42 else text
        file_names = message.additional_kwargs.get("fileNames") or []
        if file_names:
            return f"📎 {file_names[0]}"
    return "New chat"


def _message_to_display(message: BaseMessage) -> dict:
    display = {
        "role": "user" if isinstance(message, HumanMessage) else "assistant",
        "text": message.content,
    }
    display.update(message.additional_kwargs)
    return display


def get_session_messages(session_id: str) -> list[dict]:
    return [_message_to_display(m) for m in SQLiteChatMessageHistory(session_id).messages]


def list_sessions() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT session_id, MAX(ts) FROM chat_messages GROUP BY session_id"
        ).fetchall()
    finally:
        conn.close()

    sessions = []
    for session_id, updated_at in rows:
        messages = SQLiteChatMessageHistory(session_id).messages
        sessions.append(
            {
                "id": session_id,
                "title": _title_from_messages(messages),
                "updated_at": updated_at,
            }
        )
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions
