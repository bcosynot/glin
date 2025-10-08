from __future__ import annotations

import subprocess
from typing import Optional

from .config import get_tracked_emails, set_tracked_emails_env, create_config_file
from .mcp_app import mcp


def _get_author_filters() -> list[str]:
    """
    Get the list of author patterns to filter commits by.
    Uses the new configuration system that supports multiple emails.
    
    Returns:
        List of author patterns (emails/names) to filter commits by.
        Empty list if no configuration is found.
    """
    return get_tracked_emails()


def get_recent_commits(count: int = 10) -> list[dict]:
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
            return [{"error": "No email addresses configured for tracking. Set GLIN_TRACK_EMAILS environment variable, create glin.toml, or configure git user.email"}]
        
        # Build git log command with multiple author filters
        cmd = ["git", "log", f"-{count}"]
        
        # Add author filters - git log supports multiple --author flags (OR logic)
        for author in author_filters:
            cmd.extend([f"--author={author}"])
        
        cmd.append("--pretty=format:%H|%an|%ai|%s")
        
        result = subprocess.run(
            cmd,
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
        # Get configured author filters
        author_filters = _get_author_filters()
        if not author_filters:
            return [{"error": "No email addresses configured for tracking. Set GLIN_TRACK_EMAILS environment variable, create glin.toml, or configure git user.email"}]
        
        # Build git log command with multiple author filters
        cmd = ["git", "log", f"--since={since}", f"--until={until}"]
        
        # Add author filters - git log supports multiple --author flags (OR logic)
        for author in author_filters:
            cmd.extend([f"--author={author}"])
        
        cmd.append("--pretty=format:%H|%an|%ai|%s")
        
        result = subprocess.run(
            cmd,
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


def get_tracked_email_config() -> dict:
    """
    Get the current email tracking configuration.
    
    Returns:
        Dictionary with current configuration details
    """
    emails = get_tracked_emails()
    return {
        "tracked_emails": emails,
        "count": len(emails),
        "source": _get_config_source()
    }


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
                "method": "environment_variable"
            }
        elif method == "file":
            config_path = create_config_file(emails)
            return {
                "success": True,
                "message": f"Created configuration file at {config_path} with {len(emails)} emails",
                "emails": emails,
                "method": "config_file",
                "config_path": str(config_path)
            }
        else:
            return {
                "success": False,
                "error": f"Unknown configuration method: {method}. Use 'env' or 'file'"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to configure emails: {str(e)}"
        }


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
    try:
        import subprocess
        subprocess.run(
            ["git", "config", "--get", "user.email"],
            capture_output=True,
            text=True,
            check=True,
        )
        return "git_user_email"
    except subprocess.CalledProcessError:
        pass
    
    try:
        subprocess.run(
            ["git", "config", "--get", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return "git_user_name"
    except subprocess.CalledProcessError:
        pass
    
    return "none"



# Register MCP tool wrappers preserving public names
@mcp.tool(name="get_recent_commits")
def _tool_get_recent_commits(count: int = 10) -> list[dict]:  # pragma: no cover
    return get_recent_commits(count=count)


@mcp.tool(name="get_commits_by_date")
def _tool_get_commits_by_date(since: str, until: str = "now") -> list[dict]:  # pragma: no cover
    return get_commits_by_date(since=since, until=until)


@mcp.tool(name="get_tracked_email_config")
def _tool_get_tracked_email_config() -> dict:  # pragma: no cover
    return get_tracked_email_config()


@mcp.tool(name="configure_tracked_emails")
def _tool_configure_tracked_emails(emails: list[str], method: str = "env") -> dict:  # pragma: no cover
    return configure_tracked_emails(emails=emails, method=method)
