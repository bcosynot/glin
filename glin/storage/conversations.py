from .db import get_connection
from .types import Conversation, Message


def create_conversation(title: str | None = None, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title,),
        )
        return int(cur.lastrowid)


def add_message(
    conversation_id: int,
    role: str,
    content: str,
    *,
    db_path: str | None = None,
) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        return int(cur.lastrowid)


_message_cols = "id, conversation_id, role, content, created_at"


def list_messages(conversation_id: int, db_path: str | None = None) -> list[Message]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT {_message_cols} FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [Message(**dict(r)) for r in rows]


def get_conversation(conversation_id: int, db_path: str | None = None) -> Conversation | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        return Conversation(**dict(row)) if row else None
