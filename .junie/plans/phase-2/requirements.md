# Phase 2: Data Storage & Persistence — Requirements

Source: `.junie/Roadmap.md` (Phase 2: Data Storage & Persistence, v0.3.0)

Date: 2025-10-09

## 1. Summary
Introduce a reliable, local-first storage layer for Glin to persist conversations and related metadata, enabling efficient queries and future worklog generation. Target release: v0.3.0.

## 2. Goals (from roadmap)
- SQLite database schema design
- Conversation log storage
- Efficient querying and indexing
- Backup and migration tools

## 3. In Scope
- Embedding a file-backed SQLite database in the project’s data directory.
- Schema to support: conversations, messages, participants, tags/topics, message-to-commit links, attachments/refs.
- Read/write APIs inside the package (no external service).
- Pragmatic indexing strategy for common queries.
- Lightweight backup and migration utilities bundled with the project.

## 4. Out of Scope (for v0.3.0)
- Cloud databases or remote replication.
- Full-text search beyond SQLite FTS5 baseline.
- Multi-user concurrency beyond local workstation usage.
- Analytics dashboards and summarization (deferred to later phases).

## 5. Functional Requirements
- FR1: Initialize database on first run; create schema if missing.
- FR2: Append conversation sessions with metadata: timestamps, transport/client, associated repo path.
- FR3: Store messages in order with role (user/assistant/system), text content, token counts (optional), and references (files/commits).
- FR4: Tagging: allow zero or more tags per session and/or message.
- FR5: Query APIs:
  - FR5.1: Get conversations by date range.
  - FR5.2: Search by tag/topic.
  - FR5.3: Filter messages linked to specific git commits or file paths.
  - FR5.4: Free-text search using FTS5 on message content.
- FR6: Import/export: dump and restore DB to a versioned file; include vacuum and integrity check.
- FR7: Migrations: version table and simple forward migrations; reject opening DB with higher version.
- FR8: Telemetry/observability: basic counters (rows written/read) and timings via debug logs.

## 6. Non‑Functional Requirements
- NFR1: Local-first, offline capable; no network calls.
- NFR2: Safety: atomic writes (use transactions), durable journaling (WAL), and graceful handling of corruption.
- NFR3: Performance: common queries under 100 ms on 100k messages on commodity laptops.
- NFR4: Storage footprint: < 500 MB for 1M short text messages (guideline; compression optional).
- NFR5: Privacy: data stays on disk; redact secrets via caller responsibility and provide advisory docs.
- NFR6: Compatibility: Python 3.13+; no heavy ORM required (stdlib `sqlite3` acceptable).

## 7. Proposed Data Model (initial)
- table conversations(
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  client TEXT,
  transport TEXT,
  repo_root TEXT,
  notes TEXT
)
- table messages(
  id INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  ts TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('system','user','assistant')),
  content TEXT NOT NULL,
  token_in INTEGER,
  token_out INTEGER
)
- table message_refs(
  message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  ref_type TEXT NOT NULL,  -- 'file','commit','url'
  ref_value TEXT NOT NULL,
  PRIMARY KEY(message_id, ref_type, ref_value)
)
- table tags(
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
)
- table conversation_tags(
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY(conversation_id, tag_id)
)
- FTS5 virtual table messages_fts(content, content='messages', content_rowid='id')
- table schema_version(version INTEGER NOT NULL)

Indexes:
- messages(conversation_id, ts)
- message_refs(ref_type, ref_value)
- conversation_tags(tag_id, conversation_id)

## 8. API Surface (internal, initial)
- init_db(path: str) -> None
- get_db(path?: str) -> sqlite3.Connection
- insert_conversation(...)
- insert_message(...)
- link_message_ref(...)
- tag_conversation(...)
- query_conversations(filters: TypedDict)
- query_messages(filters: TypedDict)
- backup_db(dst_path: str) -> BackupReport
- migrate_db(conn) -> MigrationReport

## 9. Security & Privacy
- Store files under user-controlled directory (default: ~/.local/share/glin or repo .glin/data).
- Respect `GLIN_DATA_DIR` env var override.
- Do not transmit data; follow least-privilege file permissions.

## 10. Observability
- Structured debug logs around DB ops (duration, rows affected).
- Health check: pragma quick_check, integrity_check exposed via helper.

## 11. Acceptance Criteria
- AC1: Fresh clone + run produces a database and schema without manual steps.
- AC2: Inserting and querying sample conversations works and returns expected rows.
- AC3: FTS search returns matches for inserted content.
- AC4: Backup file created; restore path validated; migrations bump version.
- AC5: All unit tests for storage module pass and integrate with existing test harness (pytest).

## 12. Risks & Mitigations
- Risk: Schema churn as phases 3–5 evolve → Mitigation: versioning + migrations.
- Risk: DB corruption on abrupt termination → Mitigation: WAL + frequent checkpoints and backups.
- Risk: Performance under large logs → Mitigation: targeted indexes and query profiling.

## 13. Timeline
- Duration target: 2–3 weeks from 2025-10-09.
