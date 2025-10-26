from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, TypedDict

from ..mcp_app import mcp
from .commits import get_commits_by_date
from .enrichment import EnrichedCommit, EnrichedResult, get_enriched_commits


class TypeDistribution(TypedDict):
    # e.g., {"feat": 3, "fix": 1}
    # dynamic keys -> int counts
    # Using plain dict[str, int] where consumed
    pass


class WorkSession(TypedDict):
    start_time: str
    end_time: str
    duration_minutes: int
    commits: list[EnrichedCommit]  # may be plain CommitInfo if not enriched
    commit_count: int
    primary_type: str
    type_distribution: dict[str, int]
    focus_files: list[str]
    focus_dirs: list[str]
    theme: str


def detect_work_sessions(commits: list[dict], gap_threshold_minutes: int = 30) -> list[WorkSession]:
    """Group commits into logical work sessions.

    Heuristics:
    - Time gaps greater than ``gap_threshold_minutes`` start a new session
    - Primary type inferred from enriched ``category.type`` when present
    - Simple theme inferred from most common non-trivial words in messages

    The function is tolerant to mixed commit dict shapes. If commits are not
    enriched, it still works using basic fields (``date``, ``message``, etc.).
    """
    if not commits:
        return []

    # Sort by date (ISO-like string accepted). Tests ensure date is present.
    sorted_commits = sorted(commits, key=lambda c: c.get("date", ""))

    sessions: list[WorkSession] = []
    current: dict[str, Any] = {"commits": [], "start_time": None, "end_time": None}

    for c in sorted_commits:
        date_str = str(c.get("date", ""))
        if not date_str:
            # Skip items that don't look like commits
            continue
        # Normalize: allow "YYYY-MM-DD HH:MM:SS" or isoformat already
        ts = datetime.fromisoformat(date_str.replace(" ", "T"))

        if current["start_time"] is None:
            current["start_time"] = ts
            current["end_time"] = ts
            current["commits"].append(c)
            continue

        gap_min = (ts - current["end_time"]).total_seconds() / 60.0
        if gap_min > gap_threshold_minutes:
            sessions.append(_finalize_session(current))
            current = {"commits": [c], "start_time": ts, "end_time": ts}
        else:
            current["commits"].append(c)
            current["end_time"] = ts

    if current["commits"]:
        sessions.append(_finalize_session(current))

    return sessions


def _finalize_session(current: dict[str, Any]) -> WorkSession:
    commits: list[dict] = current["commits"]

    # Determine primary type
    type_counts: dict[str, int] = defaultdict(int)
    for c in commits:
        t = (
            (c.get("category") or {}).get("type")  # from enrichment
            if isinstance(c.get("category"), dict)
            else None
        )
        key = str(t) if t else "mixed"
        type_counts[key] += 1
    primary_type = max(type_counts.items(), key=lambda kv: kv[1])[0] if type_counts else "mixed"

    # Placeholder for focus files/dirs — requires per-commit file lists to be ideal.
    focus_files: list[str] = []
    focus_dirs: set[str] = set()

    # Simple theme from messages
    messages = [str(c.get("message", "")) for c in commits if c.get("message")]
    theme = _infer_theme_from_messages(messages)

    duration = int((current["end_time"] - current["start_time"]).total_seconds() / 60)

    return WorkSession(
        start_time=current["start_time"].isoformat(),
        end_time=current["end_time"].isoformat(),
        duration_minutes=duration,
        commits=commits,  # type: ignore[assignment]
        commit_count=len(commits),
        primary_type=primary_type,
        type_distribution=dict(type_counts),
        focus_files=focus_files,
        focus_dirs=list(focus_dirs),
        theme=theme,
    )


def _infer_theme_from_messages(messages: list[str]) -> str:
    if not messages:
        return "Miscellaneous work"

    # Remove conventional commit prefixes (e.g., "feat(auth): msg")
    words: list[str] = []
    for msg in messages:
        clean = msg.split(":", 1)[-1].strip()
        words.extend(clean.lower().split())

    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "over",
        "under",
        "about",
    }

    filtered = [w.strip(".,()[]{}!?") for w in words if len(w) > 3 and w not in stop_words]
    if not filtered:
        return "Development work"

    common = Counter(filtered).most_common(2)
    return f"{common[0][0].capitalize()} related work"


class WorkSessionsResult(TypedDict):
    sessions: list[WorkSession]
    commit_count: int
    generated_at: str


def get_work_sessions(
    since: str, until: str = "now", gap_threshold_minutes: int = 30
) -> WorkSessionsResult | list[dict]:
    """High-level API to compute sessions for a date range.

    Prefers enriched commits for better type detection; falls back to raw commits
    when enrichment returns an error/info payload.
    """
    data: EnrichedResult | list[dict] = get_enriched_commits(since, until)

    commits: list[dict]
    if isinstance(data, list):
        # error/info passthrough; also handle empty
        return data
    else:
        commits = data.get("commits", [])
        if not commits:
            # try fallback to raw commits for robustness
            raw = get_commits_by_date(since, until)
            if isinstance(raw, list) and raw and not ("error" in raw[0] or "info" in raw[0]):
                commits = raw  # type: ignore[assignment]
            else:
                return raw  # type: ignore[return-value]

    sessions = detect_work_sessions(commits, gap_threshold_minutes=gap_threshold_minutes)

    return WorkSessionsResult(
        sessions=sessions,
        commit_count=len([c for c in commits if isinstance(c, dict) and c.get("hash")]),
        generated_at=datetime.now().isoformat(),
    )


@mcp.tool(
    name="get_work_sessions",
    description=(
        "Group commits in a date range into logical work sessions based on time gaps and message patterns. "
        "Returns either an error/info list (when applicable) or a structured object with sessions."
    ),
)
async def _tool_get_work_sessions(
    since: str,
    until: str = "now",
    gap_threshold_minutes: int = 30,
) -> WorkSessionsResult | list[dict]:
    return get_work_sessions(since, until, gap_threshold_minutes)
