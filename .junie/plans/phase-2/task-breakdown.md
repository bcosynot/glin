# Phase 2: Data Storage & Persistence — Task Breakdown

Date: 2025-10-09

This breakdown enumerates concrete tasks derived from the Phase 2 requirements and plan. IDs are stable for tracking.

## Legend
- [ ] TODO
- [x] Done
- (E) Estimate in ideal hours
- Owner: TBD unless assigned

## 0. Scaffolding & Docs
- [x] TB-0.1 Create planning directory and docs under `.junie/plans/phase-2/`. (E: 0.5h)

## 1. Schema & Initialization
- [ ] TB-1.1 Define schema DDL strings and versioning (schema_version=1). (E: 3h)
- [ ] TB-1.2 Implement `init_db(path)`, WAL mode, timeouts, pragmas. (E: 3h)
- [ ] TB-1.3 Implement `migrate_db(conn)` with forward-only steps. (E: 4h)
- [ ] TB-1.4 Add integrity/quick_check helpers and error mapping. (E: 2h)

## 2. Write APIs
- [ ] TB-2.1 `insert_conversation(...)` with start/end timestamps. (E: 3h)
- [ ] TB-2.2 `insert_message(...)` with ordering and token counts (optional). (E: 3h)
- [ ] TB-2.3 `link_message_ref(...)` for files/commits/urls. (E: 2h)
- [ ] TB-2.4 Tagging tables and `tag_conversation(...)`. (E: 2h)

## 3. Query APIs
- [ ] TB-3.1 `query_conversations(filters)` by date range and tags. (E: 3h)
- [ ] TB-3.2 `query_messages(filters)` by conversation, refs, and date. (E: 3h)
- [ ] TB-3.3 FTS5 setup and free-text search path with feature-detection. (E: 3h)
- [ ] TB-3.4 Index review and additions; simple benchmarks. (E: 3h)

## 4. Backup & Maintenance
- [ ] TB-4.1 `backup_db(dst)` with online `VACUUM INTO` fallback to copy. (E: 2h)
- [ ] TB-4.2 Restore procedure doc and validation helper. (E: 2h)
- [ ] TB-4.3 Health check CLI/Make target (optional). (E: 1h)

## 5. Testing
- [ ] TB-5.1 Unit tests for init/migrate/backup. (E: 4h)
- [ ] TB-5.2 CRUD tests for conversations/messages/refs/tags. (E: 4h)
- [ ] TB-5.3 Query/FTS tests and performance sanity. (E: 4h)

## 6. Documentation
- [ ] TB-6.1 Developer readme: storage usage examples. (E: 2h)
- [ ] TB-6.2 Update main README with one-paragraph storage overview. (E: 1h)

## 7. Acceptance & Sign‑off
- [ ] TB-7.1 Validate Acceptance Criteria from requirements. (E: 1h)
- [ ] TB-7.2 Tag milestone v0.3.0 (once code complete). (E: 0.5h)

## Notes
- Paths resolved via `GLIN_DATA_DIR` or default local dirs.
- Keep Python 3.13 types and follow Ruff rules.
