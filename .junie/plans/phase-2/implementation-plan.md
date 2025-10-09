# Phase 2: Data Storage & Persistence — Implementation Plan

Date: 2025-10-09
Source: `.junie/Roadmap.md` (Phase 2: v0.3.0)

## Objectives
Implement a local SQLite storage layer for conversations with efficient queries, backups, and migrations.

## Approach
- Use Python stdlib `sqlite3` with WAL mode and safe transactions.
- Keep a thin storage module under `glin/storage/` (package) with typed helpers.
- Make read/write APIs independent from MCP runtime so tests remain hermetic.
- Provide a Make/CLI task to run health/backup commands.

## Milestones & Schedule (2–3 weeks)

### Week 1 (2025-10-09 → 2025-10-15)
- M1.1 Design schema and migration strategy; draft ERD in docs (✓ when merged).
- M1.2 Implement `init_db`, `migrate_db`, `backup_db` scaffolding.
- M1.3 Create `insert_conversation`, `insert_message`, `link_message_ref`, tagging tables.
- M1.4 Add unit tests with tmp paths; seed sample data.

### Week 2 (2025-10-16 → 2025-10-22)
- M2.1 Implement query helpers and FTS5 integration.
- M2.2 Index tuning and basic performance tests (toy dataset ~100k msgs).
- M2.3 Health checks and error handling pass (PRAGMA checks, timeouts).

### Buffer (2025-10-23 → 2025-10-25)
- Stabilization, docs, examples, and polish.

## Deliverables
- Storage package: `glin/storage/` with typed API.
- Tests: `tests/storage/` covering init, CRUD, queries, backup, migrations.
- Docs: this plan + requirements + task breakdown committed under `.junie/plans/phase-2/`.
- Make targets: `make db-backup`, `make db-check` (optional if not overreaching).

## Dependencies
- Python 3.13 stdlib; no new heavy deps.
- Optional: enable SQLite FTS5 (available in default CPython builds on most platforms).

## Risks & Mitigations
- FTS availability differences → detect at runtime; feature-flag FTS search.
- File path defaults across OS → centralize path resolution; allow `GLIN_DATA_DIR` env override.

## Testing Strategy
- Use pytest with `tmp_path` to create isolated DBs per test.
- Property-style tests for insert/query round-trips.
- Deterministic seed data for performance sanity checks.

## Rollout & Backout
- Rollout: schema version starts at 1; migrations are forward-only scripts within code.
- Backout: drop and recreate DB for dev builds; preserve backups before running migrations.

## Acceptance Gates (match Requirements ACs)
- DB initializes on first use; queries return expected results; backup/migrate verified in CI.
