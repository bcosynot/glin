from typing import Annotated, Any

from pydantic import Field

from .mcp_app import mcp
from .storage.conversations import (
    add_conversation,
    add_message,
)
from .storage.summaries import add_summary, list_summaries


@mcp.tool(
    name="record_conversation_summary",
    description=(
        "Record a summary row for a conversation on a given date. If conversation_id is None, "
        "a new conversation is created (optionally with title). Returns the summary id and "
        "the conversation id."
    ),
)
async def record_conversation_summary(
    date: Annotated[
        str,
        Field(description="ISO date the summary applies to. Use YYYY-MM-DD (e.g., 2025-10-26)."),
    ],
    summary: Annotated[
        str,
        Field(description="Concise summary for the conversation on that date. Markdown allowed."),
    ],
    conversation_id: Annotated[
        int | None,
        Field(
            description=(
                "Existing conversation id. If omitted or null, a new conversation is created."
            )
        ),
    ] = None,
    title: Annotated[
        str | None,
        Field(
            description=(
                "Optional title when creating a new conversation; also stored with the summary."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """Store a conversation summary and return identifiers.

    Parameters
    ----------
    date: str
        ISO-8601 calendar date (YYYY-MM-DD) that this summary belongs to.
    summary: str
        Free-text summary for that date; short markdown is acceptable.
    conversation_id: int | None
        Pass an existing conversation id to append; when omitted, a new conversation
        is created first and its id is returned.
    title: str | None
        Optional title used when creating a new conversation; if provided it is also
        saved alongside the summary row.
    """
    if conversation_id is None:
        conversation_id = add_conversation(title=title)
    # If title is provided, keep it in the summary record; otherwise reuse existing conv title
    sid = add_summary(date=date, conversation_id=conversation_id, title=title, summary=summary)
    return {
        "summary_id": int(sid),
        "conversation_id": int(conversation_id),
        "date": date,
        "title": title,
        "summary_length": len(summary),
    }


@mcp.tool(
    name="get_recent_conversations",
    description=(
        "Get recent conversation summaries from storage, optionally filtered by ISO date "
        "(YYYY-MM-DD). Returns rows containing date, conversation_id, title, and summary."
    ),
)
async def get_recent_conversations(
    date: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """List recent conversation summaries.

    Args:
        date: Optional ISO date string (YYYY-MM-DD) to restrict results to that date.
        limit: Max number of summaries to return.

    Returns:
        A list of dictionaries with keys: id, date, conversation_id, title, summary, created_at.
    """
    f: dict[str, Any] = {"limit": limit}
    if date:
        f["date"] = date

    summaries = list_summaries(f)
    # Ensure plain dicts are returned
    return [dict(s) for s in summaries]
