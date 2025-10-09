# Phase 2 Requirements — Data Storage & Persistence

Start date: 2025-10-09
Target version: v0.3.0

This document captures the requirements for Phase 2 as outlined in the project roadmap (Data Storage & Persistence) and incorporates stakeholder feedback to track commit metadata in the database.

## Goals
- Provide reliable local persistence for core artifacts:
  - Git entities: repositories, commits, branches, files, diffs, stats.
  - AI interaction entities: conversations, messages, sessions, message metadata.
- Enable efficient queries for worklog generation and insights in later phases.
- Remain privacy-first and local-first.

## Non-goals
- Cloud sync, multi-user tenancy, or remote DB.
- Full analytics or summarization (Phase 3+).

## Storage Engine
- SQLite 3 (bundled, file-backed, WAL mode by default).
- Single DB file under project/user scope (see configuration section).

## Data Model (initial)

### Git domain
- repositories(id, root_path, remote_url, created_at)
- commits(id, repo_id, sha, author_name, author_email, authored_at, committer_name, committer_email, committed_at, summary, body, is_merge, pr_number NULLABLE)
- commit_stats(commit_id, files_changed, insertions, deletions)
- commit_parents(commit_id, parent_sha)
- commit_files(commit_id, path, status, additions, deletions, changes)
- branches(id, repo_id, name, is_current, ahead, behind, updated_at)

Notes:
- Author filters should align with glin.config.get_tracked_emails().
- Support indexes: commits(repo_id, authored_at), commits(sha UNIQUE), commit_files(commit_id), branches(repo_id, name UNIQUE).

### Conversation domain
- sessions(id, started_at, ended_at NULLABLE, client, transport, notes)
- messages(id, session_id, role CHECK IN ('user','assistant','system'), created_at, model, tokens_input, tokens_output, text, metadata JSON)
- message_refs(message_id, file_path, line_start, line_end, commit_sha NULLABLE)

Indexes: messages(session_id, created_at), message_refs(message_id), sessions(started_at).

## Migrations
- Use simple, linear migration files stored under .junie/db/migrations, applied at startup by a tiny migration runner.
- Version table: schema_version(version INTEGER PRIMARY KEY, applied_at TEXT).

## Configuration
- DB file path precedence:
  1. GLIN_DB_PATH env var
  2. ./glin.toml key: db_path
  3. Default: ~/.local/share/glin/glin.db (or %AppData% on Windows)

## API Requirements (internal helpers)
- open_db(path?) -> sqlite3.Connection
- migrate(conn) -> None
- upsert_repo(root_path, remote_url?) -> repo_id
- ingest_commits(repo_path, authors:list[str], since?, until?) -> counts
- ingest_conversation(session_proto) -> ids
- query helpers used by Phase 3 (summaries):
  - get_commits_by_date(since, until, authors?) -> rows
  - get_messages_by_date(since, until) -> rows

## Performance & Integrity
- WAL mode; PRAGMA synchronous=NORMAL; cache_size tuned.
- Foreign keys ON.
- Batch inserts with executemany.
- Idempotent ingest (commits UNIQUE by sha; messages UNIQUE by (session_id, created_at, role, text hash)).

## Observability
- Minimal timing logs for ingest and queries (DEBUG level).

## Backups
- Simple file copy while DB in WAL mode; CLI helper planned: glin db backup --dest <dir>.

## Security & Privacy
- Local-only by default. No network writes.
- Optional redaction of secrets in stored texts (simple regex list in config).

## Acceptance Criteria
- Schema SQL file and migration runner exist.
- Calling ingest_commits against a test repo stores at least sha, author_email, authored_at, summary, stats, and changed files.
- Conversation sessions/messages can be inserted and retrieved by date.
- Queries perform within <200ms for 5k commits, <100ms for 1k messages on a typical laptop.
- Documentation reflects commit metadata tracking in DB.
