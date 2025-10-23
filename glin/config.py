"""Configuration management for Glin.

Phase 2 additions: read-only handling of DB/Markdown-related environment flags.
- GLIN_DB_PATH: optional filesystem path to the SQLite database file.
- GLIN_DB_AUTOWRITE: when truthy, certain integrations may persist data automatically.
- GLIN_MD_PATH: optional filesystem path to the Markdown worklog file.

Also supports a lightweight `glin.toml` file with keys:
- track_emails = ["..."]
- track_repositories = ["..."]
- db_path = "..."             # new: database path
- markdown_path = "..."       # new: markdown file path
"""

import os
import subprocess
import tomllib
from pathlib import Path


def get_tracked_emails() -> list[str]:
    """
    Get the list of email addresses to track commits from.

    Priority order:
    1. GLIN_TRACK_EMAILS environment variable (comma-separated)
    2. glin.toml configuration file
    3. Git user.email configuration
    4. Git user.name configuration (as fallback)

    Returns:
        List of email addresses/patterns to track. Empty list if none configured.
    """
    # 1. Check environment variable first
    env_emails = os.getenv("GLIN_TRACK_EMAILS")
    if env_emails:
        return [email.strip() for email in env_emails.split(",") if email.strip()]

    # 2. Check for configuration file
    config_emails = _get_config_file_emails()
    if config_emails:
        return config_emails

    # 3. Fallback to git configuration
    git_pattern = _get_git_author_pattern()
    if git_pattern:
        return [git_pattern]

    return []


def _get_config_file_emails() -> list[str]:
    """
    Read email configuration from glin.toml file.

    Returns:
        List of emails from config file, or empty list if file doesn't exist or has no emails.
    """
    config_paths = [
        Path.cwd() / "glin.toml",
        Path.home() / ".config" / "glin" / "glin.toml",
        Path.home() / ".glin.toml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
                emails = data.get("track_emails", [])
                if emails:
                    return emails
            except (tomllib.TOMLDecodeError, OSError):
                # If config file is malformed, continue to next location
                continue

    return []


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


def set_tracked_emails_env(emails: list[str]) -> None:
    """
    Set the GLIN_TRACK_EMAILS environment variable.

    Args:
        emails: List of email addresses to track
    """
    os.environ["GLIN_TRACK_EMAILS"] = ",".join(emails)


def create_config_file(emails: list[str], config_path: Path | None = None) -> Path:
    """
    Create a glin.toml configuration file with the specified emails.

    Args:
        emails: List of email addresses to track
        config_path: Optional path for config file. Defaults to ./glin.toml

    Returns:
        Path to the created configuration file
    """
    if config_path is None:
        config_path = Path.cwd() / "glin.toml"

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create TOML content
    emails_array = "[" + ", ".join(f'"{email}"' for email in emails) + "]"
    content = f"""# Glin Configuration
# List of email addresses to track commits from
track_emails = {emails_array}
"""

    config_path.write_text(content)
    return config_path


# --- Phase 2: Integration flags (read-only helpers) -------------------------


def _is_ci() -> bool:
    """Return True when running in a CI environment (e.g., GitHub Actions).

    We detect common CI signals to choose safer defaults that avoid relying
    on local developer configuration (like git user.email).
    """
    ci = os.getenv("CI")
    gha = os.getenv("GITHUB_ACTIONS")
    return (ci or "").lower() in {"1", "true", "yes", "on"} or (gha or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_db_path() -> str:
    """Return the DB path to use for SQLite storage.

    Precedence:
    1. GLIN_DB_PATH if set (respects exact value, including ":memory:")
    2. glin.toml key `db_path`
    3. Sensible default: ~/.glin/db.sqlite3

    This function is read-only; it does not create files or directories.
    """
    value = os.getenv("GLIN_DB_PATH")
    if value and value.strip():
        return value.strip()
    file_val = _get_config_file_value("db_path")
    if file_val and file_val.strip():
        return file_val.strip()
    # Default to a stable path in user home for CI and local runs.
    return "~/.glin/db.sqlite3"


def get_db_autowrite() -> bool:
    """Return True if GLIN_DB_AUTOWRITE is a truthy value.

    Accepted truthy values (case-insensitive): '1', 'true', 'yes', 'on'.
    """
    val = os.getenv("GLIN_DB_AUTOWRITE")
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "on"}


def get_markdown_path() -> str:
    """Return the Markdown worklog path.

    Precedence:
    1. GLIN_MD_PATH if set
    2. glin.toml key `markdown_path`
    3. Default: ./WORKLOG.md
    """
    value = os.getenv("GLIN_MD_PATH")
    if value and value.strip():
        return value.strip()
    file_val = _get_config_file_value("markdown_path")
    if file_val and file_val.strip():
        return file_val.strip()
    return "WORKLOG.md"


# --- Tracked repositories configuration -------------------------------------


def _get_common_config_paths() -> list[Path]:
    """Return the standard locations we search for glin.toml."""
    return [
        Path.cwd() / "glin.toml",
        Path.home() / ".config" / "glin" / "glin.toml",
        Path.home() / ".glin.toml",
    ]


def _get_config_file_value(key: str) -> str | None:
    """Read a simple string value from glin.toml for the given key.

    Searches standard locations and returns the first matching value.
    """
    for p in _get_common_config_paths():
        if p.exists():
            try:
                with open(p, "rb") as f:
                    data = tomllib.load(f)
                val = data.get(key)
                if val:
                    return val
            except (tomllib.TOMLDecodeError, OSError):
                continue
    return None


def _get_config_file_repositories() -> list[str]:
    """Read repository configuration from glin.toml (key: track_repositories)."""
    for p in _get_common_config_paths():
        if p.exists():
            try:
                with open(p, "rb") as f:
                    data = tomllib.load(f)
                repos = data.get("track_repositories", [])
                if repos:
                    return repos
            except (tomllib.TOMLDecodeError, OSError):
                continue
    return []


def get_tracked_repositories() -> list[str]:
    """
    Return the list of repositories to include when building worklogs.

    Accepted formats per entry:
    - Local filesystem path to a Git repo
    - GitHub shorthand "owner/repo"
    - Full Git remote URL (https or ssh)

    Precedence:
    1. GLIN_TRACK_REPOSITORIES (comma-separated)
    2. GLIN_TRACK_REPOS (alias; comma-separated)
    3. glin.toml key track_repositories = ["..."]
    """
    env_val = os.getenv("GLIN_TRACK_REPOSITORIES") or os.getenv("GLIN_TRACK_REPOS")
    if env_val:
        return [v.strip() for v in env_val.split(",") if v.strip()]
    file_repos = _get_config_file_repositories()
    if file_repos:
        return file_repos
    return []


def set_tracked_repositories_env(repositories: list[str]) -> None:
    """Set GLIN_TRACK_REPOSITORIES environment variable to a comma-separated list."""
    os.environ["GLIN_TRACK_REPOSITORIES"] = ",".join(repositories)
