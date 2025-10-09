# Phase 2 Task Breakdown — Data Storage & Persistence

Start date: 2025-10-09
Status: Draft
Owner: Junie (JetBrains)

Legend: [P1]=High, [P2]=Medium, [P3]=Low | (est)=rough estimate | ✅=done | 🚧=in progress | ⏳=blocked

## 0. Preparation
- [P2] Confirm roadmap alignment and capture stakeholder note to store commit metadata in DB (2025-10-09). ✅
- [P2] Create planning docs in .junie/plans/phase-2. ✅

## 1. Scaffolding & Types
- [P1] Create module glin/storage with __init__.py, db.py, commits.py, conversations.py, types.py. (0.5d)
- [P1] Define TypedDicts: CommitRecord, CommitSummary, Conversation, Message. (0.5d)

## 2. Migration V1
- [P1] Implement schema_version table and migration logic. (0.5d)
- [P1] Create tables conversations, messages, commits, commit_files + indices. (0.5d)
- [P2] Helper: init_db(db_path?) and migrate(db_path?). (0.5d)

## 3. Commit Storage
- [P1] upsert_commit() and bulk_upsert_commits(). (0.5–1d)
- [P1] query_commits_by_date() compatible with git_tools shapes. (0.5d)
- [P2] Store per‑file changes in commit_files when available. (0.5d)

## 4. Conversation Storage
- [P2] add_conversation() and add_message(). (0.5–1d)
- [P2] query_conversations() with basic filters. (0.5d)

## 5. Backups & Status
- [P2] create_backup() into .glin/backups/YYYYMMDD/HHMMSS/. (0.25d)
- [P2] get_db_status() with row counts and schema version. (0.25d)

## 6. Integration Flags
- [P3] Add GLIN_DB_PATH, GLIN_DB_AUTOWRITE env handling in glin.config (read only in Phase 2). (0.25d)
- [P2] Optional: wire git_tools.commits to bulk_upsert_commits when flag is on. (0.5d)

## 7. Testing
- [P1] Unit tests: migrations, upserts, queries (using tmp_path). (1–2d)
- [P2] Tests: integration flag behavior; ensure no DB usage by default. (0.5d)

## 8. Docs
- [P2] Update README and .junie docs with storage usage and flags. (0.5d)

## 9. Delivery
- [P1] PR: Phase 2 storage foundation. (0.25d)
- [P2] Follow‑ups: performance, FTS evaluation, analytics integration. (TBD)
