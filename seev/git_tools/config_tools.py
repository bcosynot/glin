import subprocess
from typing import TypedDict

import seev.git_tools as git_tools

from ..mcp_app import mcp


class ConfigureSuccessResponse(TypedDict):
    success: bool
    message: str
    emails: list[str]
    method: str
    config_path: str | None


class ConfigureErrorResponse(TypedDict):
    success: bool
    error: str


class EmailConfig(TypedDict):
    tracked_emails: list[str]
    count: int
    source: str


class RepositoriesConfig(TypedDict):
    tracked_repositories: list[str]
    count: int
    source: str


def _check_git_config(key: str) -> bool:
    try:
        subprocess.run(["git", "config", "--get", key], capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _get_config_source() -> str:
    import os
    from pathlib import Path

    if os.getenv("SEEV_TRACK_EMAILS"):
        return "environment_variable"

    config_paths = [
        Path.cwd() / "seev.toml",
        Path.home() / ".config" / "seev" / "seev.toml",
        Path.home() / ".seev.toml",
        Path.cwd() / "glin.toml",
        Path.home() / ".config" / "glin" / "glin.toml",
        Path.home() / ".glin.toml",
    ]
    for p in config_paths:
        if p.exists():
            return f"config_file ({p})"

    if _check_git_config("user.email"):
        return "git_user_email"
    if _check_git_config("user.name"):
        return "git_user_name"
    return "none"


def _get_repositories_config_source() -> str:
    import os
    from pathlib import Path

    if os.getenv("SEEV_TRACK_REPOSITORIES") or os.getenv("SEEV_TRACK_REPOS"):
        return "environment_variable"

    config_paths = [
        Path.cwd() / "seev.toml",
        Path.home() / ".config" / "seev" / "seev.toml",
        Path.home() / ".seev.toml",
        Path.cwd() / "glin.toml",
        Path.home() / ".config" / "glin" / "glin.toml",
        Path.home() / ".glin.toml",
    ]
    for p in config_paths:
        if p.exists():
            return f"config_file ({p})"

    return "none"


def get_tracked_email_config() -> EmailConfig:
    emails = git_tools.get_tracked_emails()
    return {
        "tracked_emails": emails,
        "count": len(emails),
        "source": git_tools._get_config_source(),
    }


def get_tracked_repositories_config() -> RepositoriesConfig:
    repositories = git_tools.get_tracked_repositories()
    return {
        "tracked_repositories": repositories,
        "count": len(repositories),
        "source": _get_repositories_config_source(),
    }


def configure_tracked_emails(
    emails: list[str], method: str = "env"
) -> ConfigureSuccessResponse | ConfigureErrorResponse:
    try:
        if method == "env":
            git_tools.set_tracked_emails_env(emails)
            return {
                "success": True,
                "message": f"Set SEEV_TRACK_EMAILS environment variable with {len(emails)} emails",
                "emails": emails,
                "method": "environment_variable",
                "config_path": None,
            }
        if method == "file":
            cfg_path = git_tools.create_config_file(emails)
            return {
                "success": True,
                "message": f"Created configuration file at {cfg_path} with {len(emails)} emails",
                "emails": emails,
                "method": "config_file",
                "config_path": str(cfg_path),
            }
        return {
            "success": False,
            "error": f"Unknown configuration method: {method}. Use 'env' or 'file'",
        }
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"Failed to configure emails: {str(e)}"}


# MCP tools
@mcp.tool(
    name="get_tracked_email_config",
    description=(
        "Get the current email tracking configuration. Returns the list of tracked email "
        "addresses, count, and configuration source (environment variable, config file, or "
        "git config)."
    ),
)
def _tool_get_tracked_email_config() -> EmailConfig:  # pragma: no cover
    return get_tracked_email_config()


@mcp.tool(
    name="get_tracked_repositories_config",
    description=(
        "Get the current tracked repositories configuration. Returns the list of tracked "
        "repositories, count, and configuration source (environment variable or config file). "
        "Repositories can be local filesystem paths, GitHub shorthand (owner/repo), or full "
        "Git URLs."
    ),
)
def _tool_get_tracked_repositories_config() -> RepositoriesConfig:  # pragma: no cover
    return get_tracked_repositories_config()


@mcp.tool(
    name="configure_tracked_emails",
    description=(
        "Configure email addresses to track commits from. Supports two methods: 'env' to set the "
        "SEEV_TRACK_EMAILS environment variable, or 'file' to create a seev.toml configuration "
        "file (with glin.toml fallback support)."
    ),
)
def _tool_configure_tracked_emails(
    emails: list[str], method: str = "env"
) -> ConfigureSuccessResponse | ConfigureErrorResponse:  # pragma: no cover
    return configure_tracked_emails(emails=emails, method=method)
