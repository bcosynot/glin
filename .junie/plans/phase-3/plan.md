# Phase 3 Project Plan — Worklog Generation (v0.4.0)

Source: .junie/Roadmap.md (2025-10-09)

## Goals
- Turn raw git (and placeholder conversation) data into readable, configurable worklogs.
- Ship daily/weekly/sprint summaries with Markdown output and highlight extraction.

## Milestones and Deliverables
1. M1: Scaffolding and Test Harness (Week 1)
   - Deterministic pseudo-LLM component for tests.
   - Template engine interface and default templates (daily/weekly/sprint).
   - File writing harness reusing markdown_tools semantics.
2. M2: Data Shaping and Highlighting (Week 2)
   - Data model from git_tools (commits, diffs, stats, branches).
   - Highlight detection rules and ranking.
   - Edge cases: no commits, massive diffs.
3. M3: Summarization + Rendering (Week 3)
   - Summarizer pipeline combining data + templates.
   - Render to Markdown string; verify structure via tests.
4. M4: Write & Integrate (Week 4)
   - Append/create in WORKLOG.md with correct headings/spacing.
   - Expose Python helpers; optional MCP tool wrappers.
   - Docs and examples in README.

## Timeline
- Estimated: 3–4 weeks (per roadmap). Target v0.4.0.

## Work Breakdown Structure
- Engine
  - Template system (loading, token replacement, presets).
  - Summarizer (LLM interface abstraction with mockable backend).
  - Highlighter (rules: PR merges, big diffs, tags, issue keys).
- I/O
  - Data fetchers (thin wrappers around glin.git_tools).
  - Markdown writer (delegates to markdown_tools.append_to_markdown where possible).
- API
  - render_worklog, write_worklog, generate_worklog.
  - Type definitions for WriteResult and data records.
- Tests
  - Unit tests for each engine component and writer behavior.
  - Golden tests for template rendering.

## Definition of Done
- All M1–M4 deliverables complete with tests and README updates.
- Coverage does not regress; new modules have focused tests.
- Deterministic test mode; no network/real LLM required.

## Risks and Contingencies
- LLM prompt drift → Pin prompt templates; provide seedable mock.
- Performance on large repos → Summarize by groups; lazy-load diffs; cap outputs.
- File clobbering → Always use append_to_markdown and test with tmp paths.

## Acceptance
- Running generate_worklog("daily") on a repo with commits produces a well-formed Markdown section and returns a structured WriteResult.
