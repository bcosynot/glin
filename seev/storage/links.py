from __future__ import annotations

from typing import Any

from ..mcp_app import mcp
from .db import get_connection


def link_commit_to_conversation(
    commit_sha: str,
    conversation_id: int,
    relevance_score: float = 1.0,
    db_path: str | None = None,
) -> int:
    """Associate a commit with a conversation and return the link id.

    If a link already exists for the given commit and conversation, updates the
    relevance score and refreshed timestamp, then returns the existing row id.
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO commit_conversations (commit_sha, conversation_id, relevance_score)
            VALUES (?, ?, ?)
            ON CONFLICT(commit_sha, conversation_id) DO UPDATE SET
                relevance_score = excluded.relevance_score,
                created_at = datetime('now')
            """,
            (commit_sha, conversation_id, float(relevance_score)),
        )
        # sqlite3 lastrowid is defined for INSERT; on UPSERT with DO UPDATE it may
        # return the id of the existing row in modern SQLite. We keep it as int.
        return int(cur.lastrowid or 0)


def get_conversations_for_commit(
    commit_sha: str,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Return conversations linked to a commit, sorted by relevance desc."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.id AS id,
                c.title AS title,
                c.created_at AS created_at,
                c.updated_at AS updated_at,
                cc.relevance_score AS relevance_score,
                cc.created_at AS linked_at
            FROM conversations c
            JOIN commit_conversations cc ON c.id = cc.conversation_id
            WHERE cc.commit_sha = ?
            ORDER BY cc.relevance_score DESC, cc.created_at DESC
            """,
            (commit_sha,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_commits_for_conversation(
    conversation_id: int,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Return commits linked to a conversation, newest link first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                commit_sha AS commit_sha,
                relevance_score AS relevance_score,
                created_at AS linked_at
            FROM commit_conversations
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            """,
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@mcp.tool(
    name="link_commit_to_conversation",
    description=(
        "Associate a git commit (by SHA) with a recorded conversation id. "
        "Use this when a commit implements work discussed in a conversation. "
        "Relevance score (0.0-1.0) indicates how strongly they are related."
    ),
)
async def tool_link_commit_to_conversation(
    commit_sha: str,
    conversation_id: int,
    relevance_score: float = 1.0,
) -> dict[str, Any]:
    link_id = link_commit_to_conversation(commit_sha, conversation_id, relevance_score)
    return {
        "ok": True,
        "link_id": int(link_id),
        "commit_sha": commit_sha,
        "conversation_id": int(conversation_id),
        "relevance_score": float(relevance_score),
    }
