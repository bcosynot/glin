# Phase 2 Implementation Plan — Data Storage & Persistence

Start date: 2025-10-09
Target version: v0.3.0

This plan sequences work to deliver local persistence, including commit metadata tracking in the database.

## Milestones and Timeline (proposed)
- M1 (2025-10-09 → 2025-10-11): Foundations
  - Decide DB path resolution and env/config precedence
  - Create schema.sql and basic migration runner
  - Add connection helper and PRAGMA tuning
- M2 (2025-10-12 → 2025-10-16): Git ingest
  - Implement commit ingest pipeline using existing git tools
  - Store commits, parents, stats, file-level changes, branches snapshot
  - Author filtering integrates with glin.config.get_tracked_emails()
- M3 (2025-10-17 → 2025-10-20): Conversations
  - Define session/message models; write ingest + simple retrieval queries
  - Add message_refs for file/commit linking
- M4 (2025-10-21 → 2025-10-24): Query layer and perf
  - Query helpers for commits/messages by date; indices; perf tests
- M5 (2025-10-25 → 2025-10-27): Tooling & backup
  - CLI scaffolding (if any) and backup helper; docs
- Buffer (2025-10-28 → 2025-10-31): Hardening and polish

## Workstreams

### A. Schema & Migrations
- Deliverables:
  - schema.sql (tables per requirements)
  - migration runner in Python (linear migrations, schema_version table)
- Risks:
  - Migration drift → keep SQL canonical in repo
- Mitigations:
  - Tests that run migrate() against tmp DB

### B. Git Ingest
- Deliverables:
  - ingest_commits(repo_path, authors, since, until)
  - Accurate mapping from glin.git_tools to DB rows
  - Idempotency via UNIQUE(sha)
- Dependencies:
  - A. Schema
- Risks:
  - Large repos performance
- Mitigations:
  - Batch inserts, indexes, stats table

### C. Conversations
- Deliverables:
  - sessions/messages tables and helpers
  - message_refs for file path + commit linkage
- Dependencies:
  - A. Schema

### D. Query Layer
- Deliverables:
  - get_commits_by_date and get_messages_by_date DB-backed versions
  - Keep current API surface for MCP tools
- Dependencies:
  - B, C

### E. Backup & Ops
- Deliverables:
  - Backup procedure and helper function/CLI
  - Minimal logging

## Testing Strategy
- Unit tests for migration runner and schema creation
- Unit/integration tests for ingest_commits with mocked git outputs
- Property tests for idempotency
- Performance smoke tests (timed inserts/queries)

## Rollout
- Feature-flag DB usage initially (env GLIN_DB_ENABLED=1)
- Fallback to in-memory/no-op when disabled

## Documentation
- Update README and .junie docs to reflect commit metadata tracked in DB
