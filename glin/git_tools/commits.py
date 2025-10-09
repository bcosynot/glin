import subprocess
from typing import TypedDict

from ..mcp_app import mcp
from . import get_tracked_emails


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
    if isinstance(e, subprocess.CalledProcessError):
        return [{"error": f"Git command failed: {e.stderr}"}]
    return [{"error": f"Failed to get commits: {str(e)}"}]


def _get_author_filters() -> list[str]:
    # Local import so test monkeypatching glin.git_tools.get_tracked_emails takes effect

    return get_tracked_emails()


def get_recent_commits(count: int = 10) -> list[CommitInfo | ErrorResponse]:
    try:
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]
        cmd = _build_git_log_command([f"-{count}"], author_filters)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return _parse_commit_lines(result.stdout)
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
        return commits if commits else [{"info": "No commits found in date range"}]
    except Exception as e:  # noqa: BLE001
        return _handle_git_error(e)


def get_branch_commits(branch: str, count: int = 10) -> list[CommitInfo | ErrorResponse]:
    try:
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]
        base_args = [branch, f"-{count}"]
        cmd = _build_git_log_command(base_args, author_filters)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return _parse_commit_lines(result.stdout)
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
def _tool_get_recent_commits(count: int = 10):  # pragma: no cover
    return get_recent_commits(count=count)


@mcp.tool(
    name="get_commits_by_date",
    description=(
        "Get git commits within a specific date range. "
        "Supports flexible date formats like 'YYYY-MM-DD', 'yesterday', "
        "'2 days ago', '1 week ago'. Returns commits for the configured "
        "tracked email addresses."
    ),
)
def _tool_get_commits_by_date(since: str, until: str = "now"):  # pragma: no cover
    return get_commits_by_date(since=since, until=until)


@mcp.tool(
    name="get_branch_commits",
    description=(
        "Get recent commits for a specific branch filtered by configured tracked emails. "
        "Returns the same structure as get_recent_commits."
    ),
)
def _tool_get_branch_commits(branch: str, count: int = 10):  # pragma: no cover
    return get_branch_commits(branch=branch, count=count)
