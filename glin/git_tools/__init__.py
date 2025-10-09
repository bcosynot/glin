# New git_tools package that breaks down the monolithic implementation.
# This module re-exports public functions to preserve import stability
# and registers MCP tools by importing submodules (which decorate on shared mcp).

from ..config import (
    get_tracked_emails,  # re-export for backward-compatibility in tests/patching
    create_config_file,
    set_tracked_emails_env,
)
from .commits import (
    CommitInfo,
    ErrorResponse,
    InfoResponse,
    get_recent_commits,
    get_commits_by_date,
    get_branch_commits,
    _build_git_log_command,
    _parse_commit_lines,
    _handle_git_error,
    _get_author_filters,
)
from .config_tools import (
    get_tracked_email_config,
    configure_tracked_emails,
    _check_git_config,
    _get_config_source,
)
from .diffs import get_commit_diff
from .files import get_commit_files
from .branches import get_current_branch, list_branches

__all__ = [
    # compatibility re-exports for patching
    "get_tracked_emails",
    "create_config_file",
    "set_tracked_emails_env",
    # commits
    "CommitInfo",
    "ErrorResponse",
    "InfoResponse",
    "get_recent_commits",
    "get_commits_by_date",
    "get_branch_commits",
    "_build_git_log_command",
    "_parse_commit_lines",
    "_handle_git_error",
    "_get_author_filters",
    # config
    "get_tracked_email_config",
    "configure_tracked_emails",
    "_check_git_config",
    "_get_config_source",
    # diffs/files
    "get_commit_diff",
    "get_commit_files",
    # branches
    "get_current_branch",
    "list_branches",
]
