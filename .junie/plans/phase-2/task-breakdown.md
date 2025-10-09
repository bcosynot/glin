# Phase 2 Task Breakdown — Data Storage & Persistence

Start date: 2025-10-09
Target version: v0.3.0

The following tasks break down Phase 2 into actionable units. Each task includes acceptance criteria. Owner placeholders can be updated per sprint.

## 0. Project scaffolding
- [ ] Create .junie/db/migrations directory
- [ ] Add schema.sql with tables for git and conversations
- [ ] Add migration runner and schema_version table management

## 1. DB access layer
- [ ] open_db(path?) with PRAGMAs and FK enforcement
- [ ] Path resolution honoring GLIN_DB_PATH and glin.toml
- [ ] Unit tests for connection and migration

## 2. Git ingest
- [ ] Map glin.git_tools.commits APIs to DB rows
- [ ] Implement ingest_commits(repo_path, authors, since, until)
- [ ] Store commits, parents, stats, file-level changes, branches
- [ ] Idempotency on sha; batch inserts
- [ ] Indexes for common queries
- [ ] Tests: mocked git outputs → rows persisted

## 3. Conversation ingest
- [ ] Define sessions/messages/message_refs models
- [ ] Implement insert helpers and retrieval by date
- [ ] Tests for inserts and lookups

## 4. Query helpers
- [ ] get_commits_by_date DB version matching current API
- [ ] get_messages_by_date for later summarization
- [ ] Performance checks on 5k commit synthetic dataset

## 5. Backup & ops
- [ ] Backup helper and docs (WAL-safe copy)
- [ ] Minimal logging for ingest timings

## 6. Documentation
- [ ] Update README with DB feature flag and usage
- [ ] Confirm docs emphasize commit metadata tracking in DB
- [ ] Ensure acceptance criteria from requirements are testable

## Dependencies & Notes
- Depends on .junie/Roadmap.md Phase 2 scope
- Incorporates feedback to "keep track of commits and related information in the db"

## Acceptance Definition (done for Phase 2)
- Schema and migration runner in repo
- Commits + file changes ingested from a sample repo
- Conversations stored and retrievable by date
- Query helpers return expected results fast enough
- Backup procedure documented
