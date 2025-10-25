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


class CommitInput(TypedDict, total=False):
    """Input for upserting a commit (no DB id required).

    Includes optional aggregated stats; compatible with git_tools outputs
    when paired with per-file changes.
    """

    sha: str
    author_email: str
    author_name: str
    author_date: str  # ISO 8601
    message: str
    insertions: NotRequired[int]
    deletions: NotRequired[int]
    files_changed: NotRequired[int]


class CommitFileChange(TypedDict, total=False):
    file_path: str
    status: Literal["added", "modified", "deleted", "renamed"]
    additions: NotRequired[int]
    deletions: NotRequired[int]


class CommitSummary(TypedDict):
    """A reduced view for UI lists or summaries."""

    sha: str
    author: str
    date: str  # ISO 8601
    title: str  # first line of message
    stats: dict[str, int]  # keys: insertions, deletions, files


# Shapes compatible with glin.git_tools.commits
class GitCommitInfo(TypedDict):
    hash: str
    author: str
    date: str
    message: str


class ErrorResponse(TypedDict):
    error: str


class InfoResponse(TypedDict):
    info: str


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


class ConversationQuery(TypedDict, total=False):
    """Basic filters and options for querying conversations."""

    ids: list[int]
    title_contains: str
    created_from: str  # ISO 8601 or SQLite-compatible datetime string
    created_until: str
    updated_from: str
    updated_until: str
    order_by: Literal["created_at", "updated_at", "id"]
    order: Literal["asc", "desc"]
    limit: int
    offset: int
