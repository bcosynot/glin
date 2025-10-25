from typing import Any

from .mcp_app import mcp
from .storage.conversations import (
    add_conversation,
    add_message,
    list_messages,
    query_conversations,
)


@mcp.tool(
    name="record_conversation_message",
    description=(
        "Record a message in a coding conversation. If conversation_id is None, a new "
        "conversation is created. Returns conversation_id and message_id."
    ),
)
async def record_conversation_message(
    role: str,
    content: str,
    conversation_id: int | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Record a conversation message into local storage.

    Args:
        role: Message role such as 'user', 'assistant', or 'system'.
        content: Text content of the message.
        conversation_id: Existing conversation id; if omitted, a new conversation is created.
        title: Optional title used when creating a new conversation.

    Returns:
        Dict containing ids and small echo metadata.
    """
    if conversation_id is None:
        conversation_id = add_conversation(title=title)

    message_id = add_message(conversation_id, role, content)

    return {
        "conversation_id": int(conversation_id),
        "message_id": int(message_id),
        "role": role,
        "content_length": len(content),
        "title": title,
        "created_new_conversation": title is not None,
    }


@mcp.tool(
    name="get_recent_conversations",
    description=(
        "Get recent conversations, optionally filtered by ISO date (YYYY-MM-DD). "
        "Returns conversation metadata with message counts and a preview of the first message."
    ),
)
async def get_recent_conversations(
    date: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """List recent conversations with lightweight message metadata.

    Args:
        date: Optional ISO date string to restrict conversations created on that date.
        limit: Max number of conversations to return.

    Returns:
        A list of conversation dictionaries enriched with message_count and first_message preview.
    """
    filters: dict[str, Any] = {"limit": limit, "order_by": "updated_at", "order": "desc"}
    if date:
        filters["created_from"] = f"{date} 00:00:00"
        filters["created_until"] = f"{date} 23:59:59"

    conversations = query_conversations(filters)

    results: list[dict[str, Any]] = []
    for conv in conversations:
        messages = list_messages(conv["id"])  # returns TypedDicts
        first_msg = None
        if messages:
            try:
                first_msg = messages[0]["content"][:100]
            except Exception:
                first_msg = None
        results.append(
            {
                **conv,
                "message_count": len(messages),
                "first_message": first_msg,
            }
        )

    return results
