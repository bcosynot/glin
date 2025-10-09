from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

# Typed structures for storage layer.


class CommitRecord(TypedDict):
    """A single commit with basic metadata and stats.

    Mirrors the commits table schema.
    """

    id: int
    sha: str
    author_email: str
    author_name: str
    author_date: str  # ISO 8601
    message: str
    insertions: int
    deletions: int
    files_changed: int


class CommitSummary(TypedDict):
    """A reduced view for UI lists or summaries."""

    sha: str
    author: str
    date: str  # ISO 8601
    title: str  # first line of message
    stats: dict[str, int]  # keys: insertions, deletions, files


class Message(TypedDict, total=False):
    """A message inside a conversation."""

    id: NotRequired[int]
    conversation_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: NotRequired[str]  # ISO 8601


class Conversation(TypedDict, total=False):
    """A conversation container with optional title and timestamps."""

    id: NotRequired[int]
    title: NotRequired[str]
    created_at: NotRequired[str]
    updated_at: NotRequired[str]
