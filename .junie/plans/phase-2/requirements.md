# Phase 2 Requirements — Data Storage & Persistence

Start date: 2025-10-09
Status: Draft
Owner: Junie (JetBrains)

## Goal
Provide reliable local persistence for Glin so we can store and query structured data used by the MCP tools and future worklog generation. Phase 2 targets a self‑contained SQLite backend that works offline and is easy to ship.

## Scope (from Roadmap + stakeholder comments)
- Core (Roadmap: Phase 2)
  - SQLite database schema design
  - Conversation log storage (inputs/outputs, metadata, timestamps)
  - Efficient querying and indexing
  - Backup and migration tools
- Added per discussion on 2025-10-09
  - Persist Git commit information in the DB to enable richer queries and cross‑linking with conversations

## Functional requirements
1. Local database
   - SQLite file lives under project root by default: .glin/glin.db
   - Configurable via GLIN_DB_PATH env var and glin.toml (same precedence model as tracked emails)
2. Schema v1
   - conversations(id, started_at, ended_at, transport, client, topic, meta JSON)
   - messages(id, conversation_id FK, role, content, created_at, meta JSON)
   - commits(id TEXT PK = git SHA, author_email, author_name, authored_at, subject, body, repo_root, meta JSON)
   - commit_files(id INTEGER PK, commit_id FK, path, change_type, lines_added, lines_deleted)
   - indices on authored_at, author_email, path
3. Write paths
   - Public helpers in glin.storage for: init_db(), upsert_commit(...), add_conversation(...), add_message(...)
   - Git MCP tools can optionally write query results into DB when GLIN_DB_AUTOWRITE=true
4. Read/query paths
   - Helper functions to fetch commits by date range/author from DB with the same shape as current git_tools outputs
   - Conversation/message queries by date range and topic
5. Migrations
   - Simple migration table schema_version with forward‑only migrations scripted in Python
   - Safe no‑op if DB already at latest
6. Backups
   - create_backup(db_path) writes timestamped copy under .glin/backups/YYYYMMDD/HHMMSS/
7. Observability
   - Basic row counts and last_migrated_at via get_db_status()

## Non‑functional requirements
- Zero external services; SQLite only
- Deterministic behavior in tests; allow monkeypatch of DB path
- Schema and helpers fully type‑annotated
- No blocking of existing workflows: if DB is missing and autowrite is false, tools continue to work

## Out of scope (Phase 2)
- Cloud sync, user accounts, RBAC
- Full‑text search (can be evaluated with FTS5 later)
- Complex analytics dashboards

## Acceptance criteria
- Repo contains .junie/plans/phase-2 with this document and companion plan/tasks files
- glin.storage API is drafted (function names, signatures) and referenced in plan
- Tests can run without a real DB (monkeypatch path and/or stub helpers)
- Draft migration script plan exists in implementation plan
