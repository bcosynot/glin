from __future__ import annotations

import subprocess
from typing import Optional

from .mcp_app import mcp


def _get_git_author_pattern() -> Optional[str]:
    """
    Return the git-configured author pattern to filter commits.
    Prefers user.email; falls back to user.name. Returns None if neither is set.
    """
    try:
        email = subprocess.run(
            ["git", "config", "--get", "user.email"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        email = ""

    if email:
        return email

    try:
        name = subprocess.run(
            ["git", "config", "--get", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        name = ""

    return name or None


def get_recent_commits(count: int = 10) -> list[dict]:
    """
    Get recent git commits from the current repository.

    Args:
        count: Number of recent commits to retrieve (default: 10)

    Returns:
        List of commit dictionaries with hash, author, date, and message
    """
    try:
        # Format: hash|author|date|message
        author = _get_git_author_pattern()
        if not author:
            return [{"error": "Git author not configured. Please set user.email or user.name"}]
        result = subprocess.run(
            [
                "git", "log",
                f"-{count}",
                f"--author={author}",
                "--pretty=format:%H|%an|%ai|%s"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                hash, author, date, message = line.split('|', 3)
                commits.append({
                    "hash": hash,
                    "author": author,
                    "date": date,
                    "message": message
                })

        return commits
    except subprocess.CalledProcessError as e:
        return [{"error": f"Git command failed: {e.stderr}"}]
    except Exception as e:
        return [{"error": f"Failed to get commits: {str(e)}"}]


def get_commits_by_date(since: str, until: str = "now") -> list[dict]:
    """
    Get git commits within a specific date range.

    Args:
        since: Start date (formats: 'YYYY-MM-DD', 'yesterday', '2 days ago', '1 week ago')
        until: End date (default: 'now', same formats as since)

    Returns:
        List of commit dictionaries with hash, author, date, and message
    """
    try:
        author = _get_git_author_pattern()
        if not author:
            return [{"error": "Git author not configured. Please set user.email or user.name"}]
        result = subprocess.run(
            [
                "git", "log",
                f"--since={since}",
                f"--until={until}",
                f"--author={author}",
                "--pretty=format:%H|%an|%ai|%s"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                hash, author, date, message = line.split('|', 3)
                commits.append({
                    "hash": hash,
                    "author": author,
                    "date": date,
                    "message": message
                })

        return commits if commits else [{"info": "No commits found in date range"}]
    except subprocess.CalledProcessError as e:
        return [{"error": f"Git command failed: {e.stderr}"}]
    except Exception as e:
        return [{"error": f"Failed to get commits: {str(e)}"}]



# Register MCP tool wrappers preserving public names
@mcp.tool(name="get_recent_commits")
def _tool_get_recent_commits(count: int = 10) -> list[dict]:  # pragma: no cover
    return get_recent_commits(count=count)


@mcp.tool(name="get_commits_by_date")
def _tool_get_commits_by_date(since: str, until: str = "now") -> list[dict]:  # pragma: no cover
    return get_commits_by_date(since=since, until=until)
