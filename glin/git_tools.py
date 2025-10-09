import subprocess
from typing import TypedDict

from .config import create_config_file, get_tracked_emails, set_tracked_emails_env
from .mcp_app import mcp


# Return type definitions for git tools
class CommitInfo(TypedDict):
    """Information about a single git commit."""

    hash: str
    author: str
    date: str
    message: str


class ErrorResponse(TypedDict):
    """Error response from a git operation."""

    error: str


class InfoResponse(TypedDict):
    """Informational response from a git operation."""

    info: str


class EmailConfig(TypedDict):
    """Current email tracking configuration."""

    tracked_emails: list[str]
    count: int
    source: str


class ConfigureSuccessResponse(TypedDict):
    """Successful email configuration response."""

    success: bool
    message: str
    emails: list[str]
    method: str
    config_path: str  # Optional, only present for file method


class ConfigureErrorResponse(TypedDict):
    """Failed email configuration response."""

    success: bool
    error: str


class CommitDiffSuccess(TypedDict):
    """Successful commit diff response."""

    hash: str
    author: str
    email: str
    date: str
    message: str
    diff: str
    stats: str


class CommitDiffError(TypedDict):
    """Error response from commit diff operation."""

    error: str


class FileChange(TypedDict):
    """Information about a single file change in a commit."""

    path: str
    status: str  # A (added), M (modified), D (deleted), R (renamed), C (copied)
    additions: int
    deletions: int
    old_path: str | None  # Only present for renamed/copied files


class CommitFilesSuccess(TypedDict):
    """Successful commit files response."""

    hash: str
    author: str
    email: str
    date: str
    message: str
    files: list[FileChange]
    total_additions: int
    total_deletions: int
    files_changed: int


class CommitFilesError(TypedDict):
    """Error response from commit files operation."""

    error: str


# Error message constants
NO_EMAIL_ERROR: ErrorResponse = {
    "error": (
        "No email addresses configured for tracking. "
        "Set GLIN_TRACK_EMAILS environment variable, create glin.toml, "
        "or configure git user.email"
    )
}


def _build_git_log_command(base_args: list[str], author_filters: list[str]) -> list[str]:
    """
    Build a git log command with author filters.

    Args:
        base_args: Base arguments for git log (e.g., ["-10"] or ["--since=yesterday"])
        author_filters: List of author patterns to filter by

    Returns:
        Complete git log command as a list of strings
    """
    cmd = ["git", "log"] + base_args
    for author in author_filters:
        cmd.append(f"--author={author}")
    cmd.append("--pretty=format:%H|%an|%ai|%s")
    return cmd


def _parse_commit_lines(output: str) -> list[CommitInfo]:
    """
    Parse git log output into a list of commit dictionaries.

    Args:
        output: Raw git log output with pipe-separated values

    Returns:
        List of commit information dictionaries
    """
    commits: list[CommitInfo] = []
    for line in output.strip().split("\n"):
        if line:
            hash, author, date, message = line.split("|", 3)
            commits.append({"hash": hash, "author": author, "date": date, "message": message})
    return commits


def _handle_git_error(e: Exception) -> list[ErrorResponse]:
    """
    Handle git command errors and return standardized error responses.

    Args:
        e: Exception from git command execution

    Returns:
        List containing a single error dictionary
    """
    if isinstance(e, subprocess.CalledProcessError):
        return [{"error": f"Git command failed: {e.stderr}"}]
    return [{"error": f"Failed to get commits: {str(e)}"}]


def _check_git_config(key: str) -> bool:
    """
    Check if a git config key exists.

    Args:
        key: Git config key to check (e.g., "user.email")

    Returns:
        True if the key exists, False otherwise
    """
    try:
        subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _get_author_filters() -> list[str]:
    """
    Get the list of author patterns to filter commits by.
    Uses the new configuration system that supports multiple emails.

    Returns:
        List of author patterns (emails/names) to filter commits by.
        Empty list if no configuration is found.
    """
    return get_tracked_emails()


def get_recent_commits(count: int = 10) -> list[CommitInfo | ErrorResponse]:
    """
    Get recent git commits from the current repository.

    Args:
        count: Number of recent commits to retrieve (default: 10)

    Returns:
        List of commit dictionaries with hash, author, date, and message
    """
    try:
        # Get configured author filters
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]

        # Build git log command with multiple author filters
        cmd = _build_git_log_command([f"-{count}"], author_filters)

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        return _parse_commit_lines(result.stdout)
    except Exception as e:
        return _handle_git_error(e)


def get_commits_by_date(
    since: str, until: str = "now"
) -> list[CommitInfo | ErrorResponse | InfoResponse]:
    """
    Get git commits within a specific date range.

    Args:
        since: Start date (formats: 'YYYY-MM-DD', 'yesterday', '2 days ago', '1 week ago')
        until: End date (default: 'now', same formats as since)

    Returns:
        List of commit dictionaries with hash, author, date, and message
    """
    try:
        # Get configured author filters
        author_filters = _get_author_filters()
        if not author_filters:
            return [NO_EMAIL_ERROR]

        # Build git log command with multiple author filters
        cmd = _build_git_log_command([f"--since={since}", f"--until={until}"], author_filters)

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        commits = _parse_commit_lines(result.stdout)
        return commits if commits else [{"info": "No commits found in date range"}]
    except Exception as e:
        return _handle_git_error(e)


def get_tracked_email_config() -> dict:
    """
    Get the current email tracking configuration.

    Returns:
        Dictionary with current configuration details
    """
    emails = get_tracked_emails()
    return {"tracked_emails": emails, "count": len(emails), "source": _get_config_source()}


def configure_tracked_emails(emails: list[str], method: str = "env") -> dict:
    """
    Configure email addresses to track commits from.

    Args:
        emails: List of email addresses to track
        method: Configuration method - "env" for environment variable, "file" for config file

    Returns:
        Dictionary with configuration result
    """
    try:
        if method == "env":
            set_tracked_emails_env(emails)
            return {
                "success": True,
                "message": f"Set GLIN_TRACK_EMAILS environment variable with {len(emails)} emails",
                "emails": emails,
                "method": "environment_variable",
            }
        elif method == "file":
            config_path = create_config_file(emails)
            return {
                "success": True,
                "message": f"Created configuration file at {config_path} with {len(emails)} emails",
                "emails": emails,
                "method": "config_file",
                "config_path": str(config_path),
            }
        else:
            return {
                "success": False,
                "error": f"Unknown configuration method: {method}. Use 'env' or 'file'",
            }
    except Exception as e:
        return {"success": False, "error": f"Failed to configure emails: {str(e)}"}


def get_commit_diff(commit_hash: str, context_lines: int = 3) -> dict:
    """
    Get the diff (code changes) for a specific commit.

    Args:
        commit_hash: The commit hash to retrieve the diff for
        context_lines: Number of context lines to show around changes (default: 3)

    Returns:
        Dictionary with commit metadata and diff content, or error information
    """
    try:
        # First verify the commit exists and get metadata
        metadata_cmd = [
            "git",
            "show",
            "--no-patch",
            "--pretty=format:%H|%an|%ae|%ai|%s",
            commit_hash,
        ]

        metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, check=True)

        if not metadata_result.stdout.strip():
            return {"error": f"Commit {commit_hash} not found"}

        # Parse metadata
        hash, author, email, date, message = metadata_result.stdout.strip().split("|", 4)

        # Get the diff with specified context lines
        diff_cmd = [
            "git",
            "show",
            f"-U{context_lines}",
            "--pretty=format:",  # Empty format to exclude commit message from diff output
            commit_hash,
        ]

        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)

        # Get file stats
        stats_cmd = ["git", "show", "--stat", "--pretty=format:", commit_hash]

        stats_result = subprocess.run(stats_cmd, capture_output=True, text=True, check=True)

        return {
            "hash": hash,
            "author": author,
            "email": email,
            "date": date,
            "message": message,
            "diff": diff_result.stdout.strip(),
            "stats": stats_result.stdout.strip(),
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"Git command failed: {e.stderr}"}
    except ValueError as e:
        return {"error": f"Failed to parse commit metadata: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to get commit diff: {str(e)}"}


def get_commit_files(commit_hash: str) -> CommitFilesSuccess | CommitFilesError:
    """
    Get the list of files changed in a specific commit with statistics.

    Args:
        commit_hash: The commit hash to retrieve file changes for

    Returns:
        Dictionary with commit metadata and list of file changes, or error information
    """
    try:
        # First verify the commit exists and get metadata
        metadata_cmd = [
            "git",
            "show",
            "--no-patch",
            "--pretty=format:%H|%an|%ae|%ai|%s",
            commit_hash,
        ]

        metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, check=True)

        if not metadata_result.stdout.strip():
            return {"error": f"Commit {commit_hash} not found"}

        # Parse metadata
        hash, author, email, date, message = metadata_result.stdout.strip().split("|", 4)

        # Get file status (A/M/D/R/C) and paths
        status_cmd = ["git", "show", "--name-status", "--pretty=format:", commit_hash]

        status_result = subprocess.run(status_cmd, capture_output=True, text=True, check=True)

        # Get numstat (additions/deletions per file)
        numstat_cmd = ["git", "show", "--numstat", "--pretty=format:", commit_hash]

        numstat_result = subprocess.run(numstat_cmd, capture_output=True, text=True, check=True)

        # Parse status output into a dict: {path: (status, old_path)}
        status_map: dict[str, tuple[str, str | None]] = {}
        for line in status_result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                status = parts[0]
                # Handle renames/copies which have format: R100\told_path\tnew_path
                if status.startswith(("R", "C")) and len(parts) == 3:
                    old_path = parts[1]
                    new_path = parts[2]
                    status_map[new_path] = (status[0], old_path)  # Store just R or C
                else:
                    path = parts[1]
                    status_map[path] = (status, None)

        # Parse numstat output and combine with status
        files: list[FileChange] = []
        total_additions = 0
        total_deletions = 0

        for line in numstat_result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                additions_str = parts[0]
                deletions_str = parts[1]
                path = parts[2]

                # Handle binary files (shown as '-' in numstat)
                additions = 0 if additions_str == "-" else int(additions_str)
                deletions = 0 if deletions_str == "-" else int(deletions_str)

                total_additions += additions
                total_deletions += deletions

                # Get status from status_map, default to 'M' if not found
                status, old_path = status_map.get(path, ("M", None))

                file_change: FileChange = {
                    "path": path,
                    "status": status,
                    "additions": additions,
                    "deletions": deletions,
                    "old_path": old_path,
                }
                files.append(file_change)

        return {
            "hash": hash,
            "author": author,
            "email": email,
            "date": date,
            "message": message,
            "files": files,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "files_changed": len(files),
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"Git command failed: {e.stderr}"}
    except ValueError as e:
        return {"error": f"Failed to parse commit metadata: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to get commit files: {str(e)}"}


def _get_config_source() -> str:
    """
    Determine the source of the current email configuration.

    Returns:
        String describing the configuration source
    """
    import os
    from pathlib import Path

    # Check environment variable
    if os.getenv("GLIN_TRACK_EMAILS"):
        return "environment_variable"

    # Check config files
    config_paths = [
        Path.cwd() / "glin.toml",
        Path.home() / ".config" / "glin" / "glin.toml",
        Path.home() / ".glin.toml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            return f"config_file ({config_path})"

    # Check git config
    if _check_git_config("user.email"):
        return "git_user_email"

    if _check_git_config("user.name"):
        return "git_user_name"

    return "none"


# Register MCP tool wrappers preserving public names
@mcp.tool(
    name="get_recent_commits",
    description=(
        "Get recent git commits from the current repository. "
        "Returns a list of commits with hash, author, date, and message "
        "for the configured tracked email addresses."
    ),
)
def _tool_get_recent_commits(
    count: int = 10,
) -> list[CommitInfo | ErrorResponse]:  # pragma: no cover
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
def _tool_get_commits_by_date(
    since: str, until: str = "now"
) -> list[CommitInfo | ErrorResponse | InfoResponse]:  # pragma: no cover
    return get_commits_by_date(since=since, until=until)


@mcp.tool(
    name="get_tracked_email_config",
    description=(
        "Get the current email tracking configuration. "
        "Returns the list of tracked email addresses, count, and "
        "configuration source (environment variable, config file, or git config)."
    ),
)
def _tool_get_tracked_email_config() -> dict:  # pragma: no cover
    return get_tracked_email_config()


@mcp.tool(
    name="configure_tracked_emails",
    description=(
        "Configure email addresses to track commits from. "
        "Supports two methods: 'env' to set the GLIN_TRACK_EMAILS "
        "environment variable, or 'file' to create a glin.toml configuration file."
    ),
)
def _tool_configure_tracked_emails(
    emails: list[str], method: str = "env"
) -> dict:  # pragma: no cover
    return configure_tracked_emails(emails=emails, method=method)


@mcp.tool(
    name="get_commit_diff",
    description=(
        "Get the diff (code changes) for a specific commit. "
        "Returns commit metadata (hash, author, email, date, message) "
        "along with the full diff and file statistics. "
        "Optionally specify the number of context lines around changes."
    ),
)
def _tool_get_commit_diff(
    commit_hash: str, context_lines: int = 3
) -> dict:  # pragma: no cover
    return get_commit_diff(commit_hash=commit_hash, context_lines=context_lines)


@mcp.tool(
    name="get_commit_files",
    description=(
        "Get the list of files changed in a specific commit with detailed statistics. "
        "Returns commit metadata along with a list of files showing their status "
        "(added/modified/deleted/renamed), lines added/deleted, and paths. "
        "Useful for understanding the scope of changes without viewing full diffs."
    ),
)
def _tool_get_commit_files(commit_hash: str) -> dict:  # pragma: no cover
    return get_commit_files(commit_hash=commit_hash)
