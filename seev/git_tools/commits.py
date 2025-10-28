import logging
import subprocess
from datetime import date, timedelta
from os import getcwd as _getcwd  # added for logging
from typing import Annotated, TypedDict

from fastmcp import Context  # type: ignore
from pydantic import Field

from ..mcp_app import mcp
from .utils import resolve_repo_root, run_git

logger = logging.getLogger("seev.git.commits")


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
        "Set SEEV_TRACK_EMAILS environment variable, create seev.toml (with glin.toml fallback), "
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
    # Log to standard logging so errors appear in SEEV_LOG_PATH output when configured
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
    """Optionally persist commits to storage if SEEV_DB_AUTOWRITE is truthy.

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


def _run_git_log_query(
    base_args: list[str],
    branch: str | None,
    empty_msg_default: str,
    empty_msg_branch_fmt: str | None = None,
    *,
    auto_write: bool = True,
    workdir: str | None = None,
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    """Run a git log query with optional branch and standardized handling.

    Parameters
    - base_args: arguments to pass to `git log` (excluding authors and pretty format).
    - branch: optional branch name; when provided it is prepended to `base_args`.
    - empty_msg_default: info message when no results and no branch-specific message applies.
    - empty_msg_branch_fmt: optional format string used when no results and a branch was
      specified. Should contain `{branch}` placeholder.
    - auto_write: when True, call `_maybe_autowrite` on non-empty results.

    Returns a list of `CommitInfo` or a single `ErrorResponse`/`InfoResponse` dict.
    """
    try:
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]

        effective_args = [*base_args]
        if branch:
            effective_args = [branch, *effective_args]

        cmd = _build_git_log_command(effective_args, author_filters)
        # Respect optional workdir by resolving repo root and using `git -C <root>` when provided.
        repo_root: str | None = None
        if workdir:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return [{"error": root_res["error"]}]
            repo_root = root_res.get("path")
        if repo_root:
            # `run_git` expects subcommand args (without leading 'git')
            result = run_git(cmd[1:], repo_root=repo_root)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = _parse_commit_lines(result.stdout)
        if commits:
            if auto_write:
                _maybe_autowrite(commits)
            return commits
        if branch and empty_msg_branch_fmt:
            return [{"info": empty_msg_branch_fmt.format(branch=branch)}]
        return [{"info": empty_msg_default}]
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


def get_recent_commits(
    count: int = 10,
    branch: str | None = None,
    workdir: str | None = None,
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    try:
        base_args: list[str] = [f"-{count}"]
        return _run_git_log_query(
            base_args,
            branch,
            empty_msg_default="No recent commits found",
            empty_msg_branch_fmt="No recent commits found on branch {branch}",
            auto_write=True,
            workdir=workdir,
        )
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


def _normalize_date_range(since: str, until: str | None) -> tuple[str, str]:
    """Normalize date range for day-specific queries.

    If ``since`` is an ISO date (YYYY-MM-DD) and ``until`` is missing or "now",
    treat the request as "commits for that specific day" by setting:
      - since = previous day's date (YYYY-MM-DD)
      - until = the provided date (YYYY-MM-DD)

    This aligns with the requested behavior where a specific day implies a bounded
    range, and ``until`` must be a concrete date, not "now".
    """
    until_norm = (until or "now").strip() or "now"
    try:
        d = date.fromisoformat(since.strip())
        # Only adjust if until is not explicitly provided (or set to "now")
        if until_norm == "now":
            prev = d - timedelta(days=1)
            return prev.isoformat(), d.isoformat()
        return since, until_norm
    except Exception:
        # Non-ISO inputs (e.g., "yesterday", "1 week ago") are passed through
        return since, until_norm


def get_commits_by_date(
    workdir: str,
    since: str,
    until: str = "now",
    branch: str | None = None,
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    try:
        norm_since, norm_until = _normalize_date_range(since, until)
        base_args: list[str] = [f"--since={norm_since}", f"--until={norm_until}"]
        return _run_git_log_query(
            base_args,
            branch,
            empty_msg_default="No commits found in date range",
            empty_msg_branch_fmt="No commits found in date range on branch {branch}",
            auto_write=True,
            workdir=workdir,
        )
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


def get_branch_commits(
    branch: str, count: int = 10, workdir: str | None = None
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    try:
        base_args: list[str] = [f"-{count}"]
        # Use branch parameter to prepend in helper and to produce branch-aware empty message.
        return _run_git_log_query(
            base_args,
            branch,
            empty_msg_default=f"No commits found on branch {branch}",
            empty_msg_branch_fmt="No commits found on branch {branch}",
            auto_write=False,
            workdir=workdir,
        )
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


# MCP tool registrations
@mcp.tool(
    name="get_recent_commits",
    description=(
        "Get recent git commits from the current repository. "
        "Returns a list of commits with hash, author, date, and message "
        "for the configured tracked email addresses."
    ),
)
async def _tool_get_recent_commits(
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory for Git operations. Git runs in the repository "
                "containing this path using 'git -C <root>', ensuring commands execute in the "
                "client's project repository rather than the server process CWD."
            )
        ),
    ],
    count: int = 10,
    branch: str | None = None,
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
                "branch": branch or "",
                "authors_count": authors_count,
            },
        )
        # Debug: redacted command + cwd
        base_args = [f"-{count}"]
        if branch:
            base_args = [branch, *base_args]
        redacted_cmd = ["git", "log", *base_args]
        if authors_count:
            redacted_cmd.append(f"--author=<{authors_count} authors>")
        await ctx.log(
            "Planned git command",
            level="debug",
            logger_name="glin.git.commits",
            extra={
                "cmd": redacted_cmd,
                "cwd": _getcwd(),
                "authors_count": authors_count,
                "branch": branch or "",
            },
        )

    # Call pure helper
    result = get_recent_commits(count=count, branch=branch, workdir=workdir)

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
                "Recent commits fetch completed",
                level="info",
                logger_name="glin.git.commits",
                extra={
                    "tool": "get_recent_commits",
                    "count": count,
                    "branch": branch or "",
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
                        "branch": branch or "",
                    },
                )
            elif authors_count == 0:
                await ctx.warning(
                    "No tracked emails configured; cannot query commits",
                    extra={"tool": "get_recent_commits", "branch": branch or ""},
                )
            else:
                await ctx.warning(
                    "No recent commits found",
                    extra={"tool": "get_recent_commits", "count": count, "branch": branch or ""},
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
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory for Git operations. Git runs in the repository "
                "containing this path using 'git -C <root>', ensuring commands execute in the "
                "client's project repository rather than the server process CWD."
            )
        ),
    ],
    since: str,
    until: str = "now",
    branch: str | None = None,
    ctx: Context | None = None,
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
                "branch": branch or "",
                "authors_count": authors_count,
            },
        )
        base_args = [f"--since={since}", f"--until={until}"]
        if branch:
            base_args = [branch, *base_args]
        redacted_cmd = ["git", "log", *base_args]
        if authors_count:
            redacted_cmd.append(f"--author=<{authors_count} authors>")
        await ctx.log(
            "Planned git command",
            level="debug",
            logger_name="glin.git.commits",
            extra={
                "cmd": redacted_cmd,
                "cwd": _getcwd(),
                "authors_count": authors_count,
                "branch": branch or "",
            },
        )

    result = get_commits_by_date(workdir, since=since, until=until, branch=branch)

    commits_only: list[CommitInfo] = [r for r in result if isinstance(r, dict) and "hash" in r]
    commit_count = len(commits_only)

    if ctx:
        if commit_count:
            await ctx.log(
                "Date-range fetch completed",
                level="info",
                logger_name="glin.git.commits",
                extra={
                    "tool": "get_commits_by_date",
                    "since": since,
                    "until": until,
                    "branch": branch or "",
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
                        "get_commits_by_date failed (since=%s, until=%s, branch=%s): %s",
                        since,
                        until,
                        branch or "",
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
                        "branch": branch or "",
                        "return": msg[:500],
                    },
                )
            elif authors_count == 0:
                await ctx.warning(
                    "No tracked emails configured; cannot query commits",
                    extra={"tool": "get_commits_by_date", "branch": branch or ""},
                )
            else:
                await ctx.warning(
                    "No commits found in date range",
                    extra={
                        "tool": "get_commits_by_date",
                        "since": since,
                        "until": until,
                        "branch": branch or "",
                    },
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
    branch: str,
    count: int = 10,
    workdir: Annotated[
        str | None,
        Field(
            description=(
                "Optional working directory for Git operations. "
                "When set, Git runs in the repository "
                "containing this path using 'git -C <root>', ensuring commands "
                "execute in the client's project repository rather than the server process CWD."
            )
        ),
    ] = None,
    ctx: Context | None = None,
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
            "Planned git command",
            level="debug",
            logger_name="glin.git.commits",
            extra={"cmd": redacted_cmd, "cwd": _getcwd(), "authors_count": authors_count},
        )

    result = get_branch_commits(branch=branch, count=count, workdir=workdir)

    commits_only: list[CommitInfo] = [r for r in result if isinstance(r, dict) and "hash" in r]
    commit_count = len(commits_only)

    if ctx:
        if commit_count:
            await ctx.log(
                "Branch commits fetch completed",
                level="info",
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
