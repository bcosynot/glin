# Phase 2 Implementation Plan — Data Storage & Persistence

Start date: 2025-10-09
Status: Draft
Owner: Junie (JetBrains)

## Overview
Implement a local SQLite persistence layer that stores conversations and Git metadata while remaining optional for current workflows. Add thin storage helpers (glin.storage) that mirror existing git_tools query shapes to avoid broad refactors in callers.

## Architecture
- Storage backend: SQLite via Python stdlib (sqlite3)
- Location: default .glin/glin.db (configurable by GLIN_DB_PATH and glin.toml, mirroring precedence in glin.config)
- Module layout:
  - glin/storage/__init__.py — re-exports public API
  - glin/storage/db.py — connection management, migrations, backups
  - glin/storage/commits.py — upsert_commit, bulk_upsert_commits, queries
  - glin/storage/conversations.py — add_conversation, add_message, queries
  - Optional: glin/storage/types.py — TypedDicts and type aliases

## Public API (draft)
- init_db(db_path: str | None = None) -> str
- migrate(db_path: str | None = None) -> int
- get_db_status(db_path: str | None = None) -> dict
- create_backup(db_path: str | None = None) -> str
- upsert_commit(commit: CommitRecord) -> None
- bulk_upsert_commits(commits: list[CommitRecord]) -> int
- query_commits_by_date(since: str, until: str, authors: list[str] | None = None) -> list[CommitSummary]
- add_conversation(meta: dict | None = None) -> str  # returns conversation id
- add_message(conversation_id: str, role: str, content: str, meta: dict | None = None) -> str
- query_conversations(date_from: str | None, date_to: str | None, topic: str | None) -> list[Conversation]

Types (TypedDicts) are defined under storage/types.py to keep shapes explicit and aligned with current git_tools returns.

## Migrations
- Version table: schema_version(version INT NOT NULL, migrated_at TEXT NOT NULL)
- V1: create tables conversations, messages, commits, commit_files with indices
- Migration strategy: forward-only, idempotent checks before CREATE
- CLI hook (optional later): uv run python -c "from glin.storage import migrate; migrate()"

## Integration points
- glin.git_tools.commits: optionally call bulk_upsert_commits when GLIN_DB_AUTOWRITE=true
- Future: when DB present, allow read path to prefer DB for faster queries (feature-flagged)
- Tests: monkeypatch DB path and stub sqlite3.connect as needed

## Observability & Ops
- get_db_status() returns {"path": str, "size_bytes": int, "tables": dict[str, int], "schema_version": int}
- create_backup() writes .glin/backups/YYYYMMDD/HHMMSS/glin.db

## Risks & mitigations
- Risk: Schema churn across phases — keep migrations small and additive
- Risk: Test fragility — isolate via monkeypatch and avoid implicit global connections
- Risk: Performance with large histories — use indices on authored_at, author_email, path

## Milestones
1. Scaffolding and types (1 day)
2. Migration V1 + init_db() (1–2 days)
3. Commit upsert + basic queries (1–2 days)
4. Conversation storage + queries (1–2 days)
5. Backups + status helpers (0.5 day)
6. Optional integration flag in git_tools (0.5 day)

## Definition of Done
- All helpers implemented behind a stable API with types
- Basic unit tests written (hermetic, no real DB file by default)
- Documentation in this folder references API and flags
