import os
import subprocess
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("Glin - Your worklog, without the work")


def _get_git_author_pattern() -> str | None:
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


@mcp.tool
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


@mcp.tool
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


@mcp.tool
def append_to_markdown(content: str, file_path: str | None = None) -> dict:
    """
    Append text to a markdown file at a default or configured location.

    Behavior:
    - If file_path is provided, append to that path (relative or absolute). Parents will be created.
    - Otherwise, use the environment variable GLIN_MD_PATH if set.
    - If neither is provided, default to ./WORKLOG.md in the repository root.

    Args:
        content: The text to append. Must be non-empty (after stripping). Newlines will be normalized.
        file_path: Optional target file path. Can be absolute or relative to the repo root.

    Returns:
        A dict with operation details or an error message.
    """
    try:
        if content is None or str(content).strip() == "":
            return {"error": "content is required and cannot be empty"}

        # Resolve target path: parameter > env var > default
        target = file_path or os.getenv("GLIN_MD_PATH") or "WORKLOG.md"
        path = Path(target)
        if not path.is_absolute():
            path = Path.cwd() / path

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize line endings and ensure a trailing newline
        text = str(content)
        # Convert Windows newlines to Unix to keep file consistent
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if not text.endswith("\n"):
            text = text + "\n"

        # If file exists and does not end with a newline, add one separator
        needs_leading_newline = False
        if path.exists() and path.stat().st_size > 0:
            try:
                with path.open("rb") as f:
                    f.seek(-1, 2)  # Seek to last byte
                    last_byte = f.read(1)
                    if last_byte != b"\n":
                        needs_leading_newline = True
            except OSError:
                # If file is tiny or some OS error, fall back to a safe behavior
                needs_leading_newline = True

        to_write = ("\n" if needs_leading_newline else "") + text

        with path.open("a", encoding="utf-8", newline="\n") as f:
            written = f.write(to_write)

        return {
            "ok": True,
            "path": str(path),
            "bytes_written": written,
            "used_env": file_path is None and bool(os.getenv("GLIN_MD_PATH")),
            "defaulted": file_path is None and os.getenv("GLIN_MD_PATH") is None,
        }
    except Exception as e:
        return {"error": f"Failed to append to markdown: {e}"}


if __name__ == "__main__":
    import sys
    if "--transport" in sys.argv and "http" in sys.argv:
        mcp.run(transport="http", port=8000)
    else:
        mcp.run()
