from .db import get_connection
from .types import Conversation, ConversationQuery, Message


def create_conversation(title: str | None = None, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title,),
        )
        return int(cur.lastrowid)


def add_conversation(title: str | None = None, db_path: str | None = None) -> int:
    """Back-compat alias matching the requested API name.

    Delegates to create_conversation(); returns new conversation id.
    """

    return create_conversation(title=title, db_path=db_path)


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


def query_conversations(
    filters: ConversationQuery | None = None,
    *,
    db_path: str | None = None,
) -> list[Conversation]:
    """Query conversations with basic filters.

    Supported filters in ConversationQuery:
    - ids: exact id matches
    - title_contains: case-insensitive substring match on title
    - created_from/created_until: filter by created_at range
    - updated_from/updated_until: filter by updated_at range
    - order_by: one of 'created_at', 'updated_at', 'id' (default: updated_at)
    - order: 'asc' or 'desc' (default: desc)
    - limit, offset
    """

    f = filters or {}
    sql = "SELECT id, title, created_at, updated_at FROM conversations WHERE 1=1"
    params: list[object] = []

    ids = f.get("ids") if isinstance(f, dict) else None  # type: ignore[assignment]
    if ids:
        placeholders = ",".join(["?"] * len(ids))
        sql += f" AND id IN ({placeholders})"
        params.extend([int(i) for i in ids])

    title_contains = f.get("title_contains") if isinstance(f, dict) else None
    if title_contains:
        sql += " AND title LIKE ?"
        params.append(f"%{title_contains}%")

    created_from = f.get("created_from") if isinstance(f, dict) else None
    if created_from:
        sql += " AND created_at >= ?"
        params.append(created_from)

    created_until = f.get("created_until") if isinstance(f, dict) else None
    if created_until:
        sql += " AND created_at <= ?"
        params.append(created_until)

    updated_from = f.get("updated_from") if isinstance(f, dict) else None
    if updated_from:
        sql += " AND updated_at >= ?"
        params.append(updated_from)

    updated_until = f.get("updated_until") if isinstance(f, dict) else None
    if updated_until:
        sql += " AND updated_at <= ?"
        params.append(updated_until)

    order_by = (f.get("order_by") if isinstance(f, dict) else None) or "updated_at"
    if order_by not in {"created_at", "updated_at", "id"}:
        order_by = "updated_at"
    order = (f.get("order") if isinstance(f, dict) else None) or "desc"
    order = order.lower()
    if order not in {"asc", "desc"}:
        order = "desc"
    sql += f" ORDER BY {order_by} {order.upper()}"

    limit = f.get("limit") if isinstance(f, dict) else None
    if isinstance(limit, int) and limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
        offset = f.get("offset") if isinstance(f, dict) else None
        if isinstance(offset, int) and offset > 0:
            sql += " OFFSET ?"
            params.append(offset)

    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [Conversation(**dict(r)) for r in rows]
