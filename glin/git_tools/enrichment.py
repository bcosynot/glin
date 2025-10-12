from datetime import datetime
from typing import Any, TypedDict

from ..mcp_app import mcp
from .analysis import (
    categorize_commit,
    detect_merge_info,
    get_commit_statistics,
)
from .commits import get_commits_by_date


class EnrichedCommit(TypedDict, total=False):
    # Base commit fields (from CommitInfo)
    hash: str
    author: str
    email: str
    date: str
    message: str
    # Enrichment
    statistics: dict[str, Any]
    category: dict[str, Any]
    merge_info: dict[str, Any]


class EnrichmentTotals(TypedDict):
    additions: int
    deletions: int
    files_changed: int


class EnrichedResult(TypedDict):
    commits: list[EnrichedCommit]
    totals: EnrichmentTotals
    generated_at: str


def get_enriched_commits(since: str, until: str = "now") -> EnrichedResult | list[dict]:
    """Return commits within a date range enriched with analysis metadata.

    Adds per-commit statistics, conventional commit categorization, and merge/PR detection.

    When the underlying commit query returns informational or error items (e.g.,
    no configured emails, or no commits in range), forward that response directly
    for the caller to handle. Otherwise, return a structured object with commits
    and aggregated totals.
    """
    commits = get_commits_by_date(since, until)

    # Forward-through behavior for non-standard responses
    if not isinstance(commits, list) or not commits:
        return commits  # type: ignore[return-value]

    if commits and isinstance(commits[0], dict) and ("error" in commits[0] or "info" in commits[0]):
        return commits  # type: ignore[return-value]

    enriched: list[EnrichedCommit] = []

    total_adds = 0
    total_dels = 0
    total_files = 0

    for c in commits:
        # Skip non-commit dicts defensively
        if "hash" not in c:
            continue

        sha = c["hash"]
        stats = get_commit_statistics(sha)
        category = categorize_commit(sha, is_hash=True)
        merge_info = detect_merge_info(sha)

        # Aggregate totals if stats have expected shape
        try:
            total_adds += int(stats.get("additions", 0))  # type: ignore[arg-type]
            total_dels += int(stats.get("deletions", 0))  # type: ignore[arg-type]
            total_files += int(stats.get("files_changed", 0))  # type: ignore[arg-type]
        except Exception:
            # Keep going even if stats are partially missing
            pass

        enriched.append(
            EnrichedCommit(
                **c,  # type: ignore[arg-type]
                statistics=stats,  # type: ignore[arg-type]
                category=category,  # type: ignore[arg-type]
                merge_info=merge_info,  # type: ignore[arg-type]
            )
        )

    return EnrichedResult(
        commits=enriched,
        totals=EnrichmentTotals(
            additions=total_adds,
            deletions=total_dels,
            files_changed=total_files,
        ),
        generated_at=datetime.now().isoformat(),
    )


@mcp.tool(
    name="get_enriched_commits",
    description=(
        "Get commits for a date range enriched with statistics, categorization, and merge info. "
        "Returns either a list with an error/info dict (when applicable) or a structured object "
        "with commits and aggregate totals."
    ),
)
async def _tool_get_enriched_commits(
    since: str,
    until: str = "now",
) -> EnrichedResult | list[dict]:
    return get_enriched_commits(since, until)
