from .db import get_connection
from .types import ConversationSummary, ConversationSummaryQuery


def add_summary(
    *,
    date: str,
    conversation_id: int,
    title: str | None,
    summary: str,
    db_path: str | None = None,
) -> int:
    """Insert a conversation summary row and return its id."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO conversation_summaries (date, conversation_id, title, summary)
            VALUES (?, ?, ?, ?)
            """,
            (date, conversation_id, title, summary),
        )
        return int(cur.lastrowid)


def list_summaries(
    filters: ConversationSummaryQuery | None = None,
    *,
    db_path: str | None = None,
) -> list[ConversationSummary]:
    """Query summaries by optional date and/or conversation_id with limit/offset."""
    f = filters or {}
    sql = (
        "SELECT id, date, conversation_id, title, summary, created_at "
        "FROM conversation_summaries WHERE 1=1"
    )
    params: list[object] = []

    if isinstance(f, dict):
        d = f.get("date")
        if d:
            sql += " AND date = ?"
            params.append(d)
        cid = f.get("conversation_id")
        if cid:
            sql += " AND conversation_id = ?"
            params.append(int(cid))
        limit = f.get("limit")
        if isinstance(limit, int) and limit > 0:
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            off = f.get("offset")
            if isinstance(off, int) and off > 0:
                sql += " OFFSET ?"
                params.append(off)
        else:
            sql += " ORDER BY id DESC"

    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [ConversationSummary(**dict(r)) for r in rows]
