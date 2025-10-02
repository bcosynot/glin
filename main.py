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
    Append lines as bullet points under a date heading in a markdown file.

    Behavior:
    - Each non-empty input line becomes a markdown bullet ("- ...").
    - Ensures a heading for the current local date ("## YYYY-MM-DD"). Creates it if missing.
    - Appends bullets under today's heading, before the next heading or at the end.
    - If file_path is provided, use that path; else GLIN_MD_PATH env var; else ./WORKLOG.md.

    Args:
        content: The text to append. Must be non-empty (after stripping). Newlines will be normalized.
        file_path: Optional target file path. Can be absolute or relative to the repo root.

    Returns:
        A dict with operation details or an error message.
    """
    try:
        if content is None or str(content).strip() == "":
            return {"error": "content is required and cannot be empty"}

        from datetime import datetime

        # Resolve target path: parameter > env var > default
        target = file_path or os.getenv("GLIN_MD_PATH") or "WORKLOG.md"
        path = Path(target)
        if not path.is_absolute():
            path = Path.cwd() / path

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize input newlines to Unix and split into lines
        text = str(content).replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.strip() for ln in text.split("\n")]
        bullets = [f"- {ln}" for ln in lines if ln != ""]
        if not bullets:
            return {"error": "content contained only blank lines"}

        # Prepare date heading
        today = datetime.now().date().isoformat()
        heading = f"## {today}"

        # Read existing file (normalize to Unix newlines)
        existing = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        # Ensure file ends with single newline for consistent processing
        if existing and not existing.endswith("\n"):
            existing += "\n"

        # Work with list of lines for insertion
        doc_lines = existing.split("\n") if existing else []
        # Remove a possible trailing empty string from split if file ended with newline
        if doc_lines and doc_lines[-1] == "":
            doc_lines.pop()

        # Find today's heading
        try:
            heading_idx = next(i for i, ln in enumerate(doc_lines) if ln.strip() == heading)
            heading_exists = True
        except StopIteration:
            heading_exists = False
            heading_idx = None

        # If heading is missing, append it at end with proper spacing
        if not heading_exists:
            # Ensure blank line before new heading if file not empty and last line not blank
            if doc_lines and doc_lines[-1].strip() != "":
                doc_lines.append("")
            doc_lines.append(heading)
            doc_lines.append("")  # blank line after heading
            heading_idx = len(doc_lines) - 1  # index of the blank line we just added
            # the actual section content starts at this position

        # Determine insertion index: after the heading and any existing content of that section,
        # which we define as lines until the next heading (line starting with '#').
        # First, find the line index of the heading itself
        # If we just created heading, it's at doc_lines[-1] - 1; otherwise found earlier.
        # Recompute heading index if needed
        if heading_exists:
            heading_idx = next(i for i, ln in enumerate(doc_lines) if ln.strip() == heading)
        else:
            # heading is at the line before the last blank line we added
            heading_idx = next(i for i, ln in enumerate(doc_lines) if ln.strip() == heading)

        # Find next heading after current section
        next_heading_idx = None
        for i in range(heading_idx + 1, len(doc_lines)):
            if doc_lines[i].lstrip().startswith("#") and doc_lines[i].strip() != "":
                next_heading_idx = i
                break

        # Build the new section content to insert
        insert_block = []
        # Ensure there is a blank line after heading if immediate next line isn't blank and we're inserting directly
        after_heading_idx = heading_idx + 1
        if after_heading_idx >= len(doc_lines) or doc_lines[after_heading_idx].strip() != "":
            # Only add a blank separator if we're inserting right after heading or existing content is not blank
            insert_block.append("")
        insert_block.extend(bullets)

        # If there will be another heading after, ensure there is a blank line before it
        trailing_blank = False
        if next_heading_idx is not None:
            # Check if the line before next heading will be blank; if not, add one
            trailing_blank = True
            insert_block.append("")

        # Compute insertion position
        insert_pos = next_heading_idx if next_heading_idx is not None else len(doc_lines)

        # Insert bullets block
        doc_lines[insert_pos:insert_pos] = insert_block

        # Reconstruct content with Unix newlines and ensure file ends with newline
        new_content = "\n".join(doc_lines)
        if not new_content.endswith("\n"):
            new_content += "\n"

        path.write_text(new_content, encoding="utf-8")
        bytes_written = len("\n".join(bullets))

        return {
            "ok": True,
            "path": str(path),
            "bullets_added": len(bullets),
            "heading": heading,
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
