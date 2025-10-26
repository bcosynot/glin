from datetime import datetime
from typing import Any, TypedDict

from fastmcp import Context  # type: ignore

from .mcp_app import mcp

# Optional imports guarded for environments where modules may be missing
try:  # pragma: no cover - optional helper
    from .git_tools.enrichment import EnrichedResult, get_enriched_commits
except Exception:  # pragma: no cover - tests monkeypatch when needed
    EnrichedResult = dict  # type: ignore[assignment]

    def get_enriched_commits(since: str, until: str = "now") -> Any:  # type: ignore[no-redef]
        return []


try:  # pragma: no cover - optional helper
    from .git_tools.sessions import WorkSessionsResult, get_work_sessions
except Exception:  # pragma: no cover - tests monkeypatch when needed
    WorkSessionsResult = dict  # type: ignore[assignment]

    def get_work_sessions(since: str, until: str = "now", gap_threshold_minutes: int = 30) -> Any:  # type: ignore[no-redef]
        return {"sessions": [], "commit_count": 0, "generated_at": datetime.now().isoformat()}


try:  # pragma: no cover - optional helper (may not exist yet in repo)
    from .git_tools.heatmap import get_file_heatmap
except Exception:  # pragma: no cover - optional

    def get_file_heatmap(since: str, until: str = "now", top_n: int = 10) -> Any:  # type: ignore
        return {}


try:
    from .git_tools.commits import get_commits_by_date
except Exception:  # pragma: no cover

    def get_commits_by_date(since: str, until: str = "now") -> list[dict]:  # type: ignore
        return []


try:
    from .storage.conversations import query_conversations
except Exception:  # pragma: no cover

    def query_conversations(filters: dict[str, Any]) -> list[dict]:  # type: ignore
        return []


class GenerateWorklogMetadata(TypedDict, total=False):
    commit_count: int
    conversation_count: int
    files_touched: int
    generated_at: str


def _first_user_message_excerpt(messages: list[dict], limit: int = 100) -> str | None:
    try:
        for m in messages:
            if str(m.get("role")) == "user" and m.get("content"):
                text = str(m["content"]).strip()
                if not text:
                    continue
                return (text[: limit - 3] + "...") if len(text) > limit else text
    except Exception:
        pass
    return None


def generate_rich_worklog(
    date: str,
    commits: list[dict],
    conversations: list[dict] | None = None,
    enriched_data: dict | EnrichedResult | None = None,
    heatmap: dict | None = None,
    sessions: WorkSessionsResult | dict | None = None,
) -> str:
    """Generate structured markdown worklog content for a given date.

    Sections:
    - Goals & Context
    - Technical Work (by sessions when available; otherwise flat list)
    - Metrics
    - Key Decisions
    - Impact Assessment
    - Open Items
    - Learnings
    """

    sections: list[str] = []

    # Header
    sections.append(f"## {date}\n\n")

    # Context from conversations (up to 3 snippets)
    if conversations:
        sections.append("### 🎯 Goals & Context\n")
        shown = 0
        for conv in conversations:
            if shown >= 3:
                break
            title = str(conv.get("title") or "Coding session")
            msgs = conv.get("messages") or []
            excerpt = _first_user_message_excerpt(msgs) if isinstance(msgs, list) else None
            if excerpt:
                sections.append(f'- **{title}:** "{excerpt}"\n')
                shown += 1
        sections.append("\n")

    # Technical Work
    sections.append("### 💻 Technical Work\n")

    # Prefer sessions view if provided
    if (
        sessions
        and isinstance(sessions, dict)
        and isinstance(sessions.get("sessions"), list)
        and sessions["sessions"]
    ):
        for sess in sessions["sessions"]:
            try:
                start = str(sess.get("start_time", ""))
                end = str(sess.get("end_time", ""))
                dur = int(sess.get("duration_minutes", 0))
                theme = str(sess.get("theme", "Work session"))
                sections.append(
                    f"\n**Session: {start[11:16] if len(start) >= 16 else start}"
                    f"-{end[11:16] if len(end) >= 16 else end}** ({dur}m)\n"
                )
                if theme:
                    sections.append(f"*{theme}*\n")
                for c in sess.get("commits") or []:
                    msg = str(c.get("message", "")).strip()
                    sha = str(c.get("hash", ""))[:7]
                    if msg:
                        sections.append(f"- {msg} ({sha})\n")
            except Exception:
                # Be resilient; continue rendering remaining sessions
                continue
    else:
        # Fallback to flat list of commits
        for c in commits:
            if not isinstance(c, dict):
                continue
            msg = str(c.get("message", "")).strip()
            if not msg:
                continue
            sha = str(c.get("hash", ""))[:7]
            sections.append(f"- {msg} ({sha})\n")
    sections.append("\n")

    # Metrics
    sections.append("### 📊 Metrics\n")
    total_commits = len([c for c in commits if isinstance(c, dict) and c.get("hash")])
    sections.append(f"- **{total_commits} commits**\n")

    if enriched_data and isinstance(enriched_data, dict):
        totals = enriched_data.get("totals")
        if isinstance(totals, dict):
            adds = int(totals.get("additions", 0))
            dels = int(totals.get("deletions", 0))
            sections.append(f"- **{adds} additions, {dels} deletions**\n")

    if heatmap and isinstance(heatmap, dict):
        langs = heatmap.get("languages")
        if isinstance(langs, dict) and langs:
            # Show top 3 by additions when present
            try:
                top = sorted(
                    langs.items(),
                    key=lambda kv: int((kv[1] or {}).get("additions", 0)),
                    reverse=True,
                )[:3]
                lang_summary = ", ".join(f"{k} ({(v or {}).get('additions', 0)}+)" for k, v in top)
                if lang_summary:
                    sections.append(f"- **Languages:** {lang_summary}\n")
            except Exception:
                pass
        files = heatmap.get("files") if isinstance(heatmap, dict) else None
        if isinstance(files, list) and files:
            top_file = files[0]
            try:
                path = top_file.get("path")
                chg = top_file.get("changes")
                if path is not None and chg is not None:
                    sections.append(f"- **Hot file:** {path} ({chg} changes)\n")
            except Exception:
                pass
    sections.append("\n")

    # Impact Assessment (placeholder text; intended for LLM augmentation)
    sections.append("### ⚠️ Impact Assessment\n")
    sections.append("*Analysis based on changed files and commit messages*\n\n")

    # Key Decisions
    sections.append("### 🔍 Key Decisions\n\n")

    # Open Items
    sections.append("### 🚧 Open Items\n\n")

    # Learnings
    sections.append("### 📚 Learnings\n\n")

    return "".join(sections)


class GenerateWorklogResponse(TypedDict):
    markdown: str
    metadata: GenerateWorklogMetadata


@mcp.tool(
    name="generate_rich_worklog",
    description=(
        "Generate a rich, structured worklog entry for the given date. "
        "Fetches commits, tries enrichment and sessions, optionally heatmap, "
        "queries conversations when available, and renders markdown sections."
    ),
)
async def _tool_generate_rich_worklog(
    date: str, ctx: Context | None = None
) -> GenerateWorklogResponse:  # type: ignore[name-defined]
    # Gather inputs
    since = date
    until = date

    commits = get_commits_by_date(since, until)

    enriched: Any = get_enriched_commits(since, until)

    sessions: Any
    try:
        sessions = get_work_sessions(since, until)
    except Exception:
        sessions = {"sessions": [], "commit_count": 0, "generated_at": datetime.now().isoformat()}

    # Heatmap is optional; may not be available in this codebase
    try:
        heatmap = get_file_heatmap(since, until)
    except Exception:
        heatmap = {}

    # Conversations (best-effort)
    conversations: list[dict] = []
    try:
        conversations = query_conversations(
            {
                "created_from": f"{date} 00:00:00",
                "created_until": f"{date} 23:59:59",
                "order_by": "updated_at",
                "order": "desc",
            }
        )
    except Exception:
        conversations = []

    markdown = generate_rich_worklog(
        date=date,
        commits=commits if isinstance(commits, list) else [],
        conversations=conversations,
        enriched_data=enriched if isinstance(enriched, dict) else None,
        heatmap=heatmap if isinstance(heatmap, dict) else None,
        sessions=sessions if isinstance(sessions, dict) else None,
    )

    meta: GenerateWorklogMetadata = {
        "commit_count": len([c for c in (commits or []) if isinstance(c, dict) and c.get("hash")]),
        "conversation_count": len(conversations or []),
        "files_touched": int((heatmap or {}).get("total_files_touched", 0))
        if isinstance(heatmap, dict)
        else 0,
        "generated_at": datetime.now().isoformat(),
    }

    return GenerateWorklogResponse(markdown=markdown, metadata=meta)
