import logging
import subprocess
from typing import TypedDict

from ..mcp_app import mcp

logger = logging.getLogger("glin.git.commits")


class CommitInfo(TypedDict):
    hash: str
    author: str
    date: str
    message: str


class ErrorResponse(TypedDict):
    error: str


class InfoResponse(TypedDict):
    info: str


NO_EMAIL_ERROR: ErrorResponse = {
    "error": (
        "No email addresses configured for tracking. "
        "Set GLIN_TRACK_EMAILS environment variable, create glin.toml, "
        "or configure git user.email"
    )
}


def _build_git_log_command(base_args: list[str], author_filters: list[str]) -> list[str]:
    cmd = ["git", "log"] + base_args
    for author in author_filters:
        cmd.append(f"--author={author}")
    cmd.append("--pretty=format:%H|%an|%ai|%s")
    return cmd


def _parse_commit_lines(output: str) -> list[CommitInfo]:
    commits: list[CommitInfo] = []
    for line in output.strip().split("\n"):
        if line:
            hash, author, date, message = line.split("|", 3)
            commits.append({"hash": hash, "author": author, "date": date, "message": message})
    return commits


def _handle_git_error(e: Exception) -> list[ErrorResponse]:
    # Log to standard logging so errors appear in GLIN_LOG_PATH output when configured
    try:
        if isinstance(e, subprocess.CalledProcessError):
            stderr = e.stderr if isinstance(e.stderr, str) else str(e.stderr)
            logger.error("Git command failed: %s", stderr)
            return [{"error": f"Git command failed: {stderr}"}]
        else:
            logger.error("Failed to get commits: %s", e)
            return [{"error": f"Failed to get commits: {str(e)}"}]
    except Exception:
        # Fallback without logging if logger itself fails
        if isinstance(e, subprocess.CalledProcessError):
            return [{"error": f"Git command failed: {e.stderr}"}]
        return [{"error": f"Failed to get commits: {str(e)}"}]


def _get_author_filters() -> list[str]:
    # Local import so test monkeypatching glin.git_tools.get_tracked_emails takes effect
    from . import get_tracked_emails as _get  # type: ignore

    return _get()


def _maybe_autowrite(commits: list[CommitInfo]) -> None:
    """Optionally persist commits to storage if GLIN_DB_AUTOWRITE is truthy.

    This is a best-effort side effect and failures are swallowed to avoid
    impacting the primary git query behavior.
    """
    try:
        # Local imports to avoid heavy deps and to make monkeypatching easy in tests
        from ..config import get_db_autowrite, get_db_path  # type: ignore

        if not get_db_autowrite():
            return
        from ..storage.commits import bulk_upsert_commits  # type: ignore

        db_path = get_db_path()
        # Map CommitInfo -> minimal CommitInput
        payload = [
            {
                "sha": c["hash"],
                "author_name": c.get("author", ""),
                "author_email": "",  # unknown from git log format here
                "author_date": c.get("date", ""),
                "message": c.get("message", ""),
            }
            for c in commits
        ]
        bulk_upsert_commits(payload, db_path=db_path)
    except Exception:
        # Silently ignore; logging could be added later
        return


def get_recent_commits(count: int = 10) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    try:
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]
        cmd = _build_git_log_command([f"-{count}"], author_filters)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = _parse_commit_lines(result.stdout)
        if commits:
            _maybe_autowrite(commits)
            return commits
        return [{"info": "No recent commits found"}]
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


def get_commits_by_date(
    since: str, until: str = "now"
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    try:
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]
        cmd = _build_git_log_command([f"--since={since}", f"--until={until}"], author_filters)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = _parse_commit_lines(result.stdout)
        if commits:
            _maybe_autowrite(commits)
            return commits
        return [{"info": "No commits found in date range"}]
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


def get_branch_commits(
    branch: str, count: int = 10
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    try:
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]
        base_args = [branch, f"-{count}"]
        cmd = _build_git_log_command(base_args, author_filters)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = _parse_commit_lines(result.stdout)
        if commits:
            return commits
        return [{"info": f"No commits found on branch {branch}"}]
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


# MCP tool registrations
from os import getcwd as _getcwd  # added for logging

from fastmcp import Context  # type: ignore


@mcp.tool(
    name="get_recent_commits",
    description=(
        "Get recent git commits from the current repository. "
        "Returns a list of commits with hash, author, date, and message "
        "for the configured tracked email addresses."
    ),
)
async def _tool_get_recent_commits(
    count: int = 10,
    ctx: Context | None = None,
) -> list[CommitInfo | ErrorResponse | InfoResponse]:  # pragma: no cover
    # Start/context info
    authors = []
    try:
        authors = _get_author_filters()
    except Exception:
        authors = []
    authors_count = len(authors)

    if ctx:
        await ctx.info(
            "Fetching recent commits",
            extra={
                "tool": "get_recent_commits",
                "count": count,
                "authors_count": authors_count,
            },
        )
        # Debug: redacted command + cwd
        base_args = [f"-{count}"]
        redacted_cmd = ["git", "log", *base_args]
        if authors_count:
            redacted_cmd.append(f"--author=<{authors_count} authors>")
        await ctx.log(
            "DEBUG",
            "Planned git command",
            logger_name="glin.git.commits",
            extra={"cmd": redacted_cmd, "cwd": _getcwd(), "authors_count": authors_count},
        )

    # Call pure helper
    result = get_recent_commits(count=count)

    # Summarize outcome
    try:
        commits_only: list[CommitInfo] = [r for r in result if isinstance(r, dict) and "hash" in r]
    except Exception:
        commits_only = []
    commit_count = len(commits_only)

    if ctx:
        if commit_count:
            first_sha = commits_only[0]["hash"]
            last_sha = commits_only[-1]["hash"]
            first_date = commits_only[0]["date"]
            last_date = commits_only[-1]["date"]
            await ctx.log(
                "INFO",
                "Recent commits fetch completed",
                logger_name="glin.git.commits",
                extra={
                    "tool": "get_recent_commits",
                    "count": count,
                    "commit_count": commit_count,
                    "first_sha": first_sha,
                    "last_sha": last_sha,
                    "first_date": first_date,
                    "last_date": last_date,
                },
            )
        else:
            # Detect config gap or empty results/errors
            error_entries = [r for r in result if isinstance(r, dict) and "error" in r]
            info_entries = [r for r in result if isinstance(r, dict) and "info" in r]
            if error_entries:
                # Truncate error detail to avoid large payloads
                msg = str(error_entries[0].get("error", ""))
                try:
                    logger.error("get_recent_commits failed: %s", msg)
                except Exception:
                    pass
                await ctx.error(
                    "Git fetch failed",
                    extra={
                        "tool": "get_recent_commits",
                        "return": msg[:500],
                    },
                )
            elif authors_count == 0:
                await ctx.warning(
                    "No tracked emails configured; cannot query commits",
                    extra={"tool": "get_recent_commits"},
                )
            else:
                await ctx.warning(
                    "No recent commits found",
                    extra={"tool": "get_recent_commits", "count": count},
                )

    return result


@mcp.tool(
    name="get_commits_by_date",
    description=(
        "Get git commits within a specific date range. "
        "Supports flexible date formats like 'YYYY-MM-DD', 'yesterday', "
        "'2 days ago', '1 week ago'. Returns commits for the configured "
        "tracked email addresses."
    ),
)
async def _tool_get_commits_by_date(
    since: str, until: str = "now", ctx: Context | None = None
) -> list[CommitInfo | ErrorResponse | InfoResponse]:  # pragma: no cover
    authors = []
    try:
        authors = _get_author_filters()
    except Exception:
        authors = []
    authors_count = len(authors)

    if ctx:
        await ctx.info(
            "Fetching commits in date range",
            extra={
                "tool": "get_commits_by_date",
                "since": since,
                "until": until,
                "authors_count": authors_count,
            },
        )
        base_args = [f"--since={since}", f"--until={until}"]
        redacted_cmd = ["git", "log", *base_args]
        if authors_count:
            redacted_cmd.append(f"--author=<{authors_count} authors>")
        await ctx.log(
            "DEBUG",
            "Planned git command",
            logger_name="glin.git.commits",
            extra={"cmd": redacted_cmd, "cwd": _getcwd(), "authors_count": authors_count},
        )

    result = get_commits_by_date(since=since, until=until)

    commits_only: list[CommitInfo] = [r for r in result if isinstance(r, dict) and "hash" in r]
    commit_count = len(commits_only)

    if ctx:
        if commit_count:
            await ctx.log(
                "INFO",
                "Date-range fetch completed",
                logger_name="glin.git.commits",
                extra={
                    "tool": "get_commits_by_date",
                    "since": since,
                    "until": until,
                    "commit_count": commit_count,
                    "first_sha": commits_only[0]["hash"],
                    "last_sha": commits_only[-1]["hash"],
                    "first_date": commits_only[0]["date"],
                    "last_date": commits_only[-1]["date"],
                },
            )
        else:
            error_entries = [r for r in result if isinstance(r, dict) and "error" in r]
            if error_entries:
                msg = str(error_entries[0].get("error", ""))
                try:
                    logger.error(
                        "get_commits_by_date failed (since=%s, until=%s): %s",
                        since,
                        until,
                        msg,
                    )
                except Exception:
                    pass
                await ctx.error(
                    "Git fetch failed",
                    extra={
                        "tool": "get_commits_by_date",
                        "since": since,
                        "until": until,
                        "return": msg[:500],
                    },
                )
            elif authors_count == 0:
                await ctx.warning(
                    "No tracked emails configured; cannot query commits",
                    extra={"tool": "get_commits_by_date"},
                )
            else:
                await ctx.warning(
                    "No commits found in date range",
                    extra={"tool": "get_commits_by_date", "since": since, "until": until},
                )

    return result


@mcp.tool(
    name="get_branch_commits",
    description=(
        "Get recent commits for a specific branch filtered by configured tracked emails. "
        "Returns the same structure as get_recent_commits."
    ),
)
async def _tool_get_branch_commits(
    branch: str, count: int = 10, ctx: Context | None = None
):  # pragma: no cover
    authors = []
    try:
        authors = _get_author_filters()
    except Exception:
        authors = []
    authors_count = len(authors)

    if ctx:
        await ctx.info(
            "Fetching commits for branch",
            extra={
                "tool": "get_branch_commits",
                "branch": branch,
                "count": count,
                "authors_count": authors_count,
            },
        )
        base_args = [branch, f"-{count}"]
        redacted_cmd = ["git", "log", *base_args]
        if authors_count:
            redacted_cmd.append(f"--author=<{authors_count} authors>")
        await ctx.log(
            "DEBUG",
            "Planned git command",
            logger_name="glin.git.commits",
            extra={"cmd": redacted_cmd, "cwd": _getcwd(), "authors_count": authors_count},
        )

    result = get_branch_commits(branch=branch, count=count)

    commits_only: list[CommitInfo] = [r for r in result if isinstance(r, dict) and "hash" in r]
    commit_count = len(commits_only)

    if ctx:
        if commit_count:
            await ctx.log(
                "INFO",
                "Branch commits fetch completed",
                logger_name="glin.git.commits",
                extra={
                    "tool": "get_branch_commits",
                    "branch": branch,
                    "count": count,
                    "commit_count": commit_count,
                    "first_sha": commits_only[0]["hash"],
                    "last_sha": commits_only[-1]["hash"],
                    "first_date": commits_only[0]["date"],
                    "last_date": commits_only[-1]["date"],
                },
            )
        else:
            error_entries = [r for r in result if isinstance(r, dict) and "error" in r]
            if error_entries:
                msg = str(error_entries[0].get("error", ""))
                await ctx.error(
                    "Git fetch failed",
                    extra={
                        "tool": "get_branch_commits",
                        "branch": branch,
                        "count": count,
                        "return": msg[:500],
                    },
                )
            elif authors_count == 0:
                await ctx.warning(
                    "No tracked emails configured; cannot query commits",
                    extra={"tool": "get_branch_commits", "branch": branch},
                )
            else:
                await ctx.warning(
                    "No commits found on branch",
                    extra={"tool": "get_branch_commits", "branch": branch, "count": count},
                )

    return result
