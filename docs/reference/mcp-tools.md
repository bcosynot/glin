# MCP Tools Reference

This page documents the MCP tools exposed by Seev. Each tool includes a brief purpose, arguments, an example call, and return shape. For full Python signatures and types, see the API reference pages linked inline.

Tip: Tools names match the decorators in the code (mcp.tool). You can discover them at runtime from the FastMCP client.

## Conversations

### record_conversation_message
- Purpose: Record a message in a coding conversation. Creates the conversation if conversation_id is omitted.
- Args:
  - role: string, e.g. "user", "assistant", "system".
  - content: string message body.
  - conversation_id: integer or null.
  - title: optional string, used when creating a new conversation.
- Returns: object with conversation_id, message_id, role, content_length, title, created_new_conversation.
- See code: seev.conversation_tools.record_conversation_message.

### get_recent_conversations
- Purpose: List recent conversations with message counts and a preview.
- Args:
  - date: optional ISO date (YYYY-MM-DD). Filters to that day.
  - limit: max items to return (default 10).
- Returns: list of conversations with message_count and first_message fields.
- See code: seev.conversation_tools.get_recent_conversations.

## Git — Commits and Branches

### get_recent_commits
- Purpose: Recent commits for the current repo (or workdir), most recent first.
- Key args: workdir (path), max_count (int).
- Returns: list of commit dicts (hash, author, date, message ...).
- See code: seev.git_tools.commits.get_recent_commits.

### get_commits_by_date
- Purpose: Commits within a date/time window or human-friendly range.
- Key args: since, until, branch (optional), workdir.
- Returns: list of commits or an info entry if none found.
- See code: seev.git_tools.commits.get_commits_by_date.

### get_branch_commits
- Purpose: Commits on a specific branch.
- Key args: branch (name), since/until (optional), workdir.
- See code: seev.git_tools.commits.get_branch_commits.

### list_branches
- Purpose: List local branches with ahead/behind counts vs default.
- Key args: workdir.
- Returns: list of branches with status.
- See code: seev.git_tools.branches.list_branches.

### get_current_branch
- Purpose: Return the current branch name.
- Key args: workdir.
- Returns: { name } or an error object.
- See code: seev.git_tools.branches.get_current_branch.

## Git — Files, Diffs, Remotes

### get_commit_files
- Purpose: Files changed in a commit.
- Args: commit (hash), workdir.
- Returns: list of file paths + stats.
- See code: seev.git_tools.files.get_commit_files.

### get_commit_diff
- Purpose: Unified diff for a commit (or commit range).
- Args: commit (hash or range), workdir.
- Returns: text diff or structured summary.
- See code: seev.git_tools.diffs.get_commit_diff.

### get_remote_origin
- Purpose: Read the repository origin URL.
- Args: workdir.
- Returns: url string or error.
- See code: seev.git_tools.remotes.get_remote_origin.

### determine_commit_url_prefix
- Purpose: Normalize a remote URL to a web commit URL prefix for linking (e.g., https://host/owner/repo/commit/).
- Args: remote_url string.
- Returns: url_prefix or empty when unknown.
- See code: seev.git_tools.remotes.determine_commit_url_prefix.

## Git — Analysis & Enrichment

### get_enriched_commits
- Purpose: Add stats like additions/deletions and files changed to commits.
- Args: commits (list) or an implicit range via since/until; workdir.
- Returns: list of enriched commit dicts.
- See code: seev.git_tools.enrichment.get_enriched_commits.

### detect_merge_info
- Purpose: Parse merge commit messages to extract PR number and branch info.
- Args: message (string).
- Returns: object with pr_number, source_branch, target_branch when found.
- See code: seev.git_tools.analysis.detect_merge_info.

### get_commit_statistics
- Purpose: Aggregate totals (additions/deletions, file counts) for a commit list.
- Args: commits (list).
- Returns: object with totals.
- See code: seev.git_tools.analysis.get_commit_statistics.

### categorize_commit
- Purpose: Lightweight heuristic categorization (feature, fix, docs, chore...).
- Args: message (string).
- Returns: category string.
- See code: seev.git_tools.analysis.categorize_commit.

### git_blame
- Purpose: Annotate a file with blame metadata.
- Args: path (file), rev (optional), workdir.
- Returns: list of line annotations.
- See code: seev.git_tools.analysis.git_blame.

## Git — Sessions

### get_work_sessions
- Purpose: Rough session clusters from commit timestamps.
- Args: commits (list) or since/until, threshold_minutes (gap size), workdir.
- Returns: list of sessions with start/end/commit_count.
- See code: seev.git_tools.sessions.get_work_sessions.

## Configuration Tools

### get_tracked_email_config
- Purpose: Show the current tracked email configuration and its source.
- Returns: snapshot object.
- See code: seev.git_tools.config_tools.get_tracked_email_config.

### get_tracked_repositories_config
- Purpose: List repositories to include in worklogs.
- Returns: object with tracked_repositories, count, and source.
- See code: seev.git_tools.config_tools.get_tracked_repositories_config.

### configure_tracked_emails
- Purpose: Set tracked emails via env or file.
- Args: method ("env"|"file"), emails (list), optional path for file.
- Returns: confirmation object.
- See code: seev.git_tools.config_tools.configure_tracked_emails.

## Markdown Tools

### read_date_entry
- Purpose: Read one date section from the worklog file.
- Args: date_str, file_path (optional), env var SEEV_MD_PATH respected.
- Returns: structured object including lines and positions.
- See code: seev.markdown_tools.read_date_entry.

### append_to_markdown
- Purpose: Append or update a date section in the worklog (idempotent merge when update_mode=true).
- Args: date_str, content, preserve_lines (bool), update_mode (bool), file_path optional.
- Returns: rich result dict (path, bullets added, line numbers, heading_added, etc.).
- See code: seev.markdown_tools.append_to_markdown.

## Worklog & Scaffolding

### generate_rich_worklog
- Purpose: Server-side synthesis of rich worklog content from inputs and tools (not used by worklog_entry prompt; see prompt docs).
- Args: since/until or date, inputs text.
- Returns: generated markdown.
- See code: seev.worklog_generator.generate_rich_worklog.

### init_glin
- Purpose: Initialize a workspace with Seev scaffolding.
- Returns: paths created and next steps.
- See code: seev.scaffold_tools.init_glin.
