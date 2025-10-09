# Phase 3 Task Breakdown — Worklog Generation

This breakdown converts the roadmap goals into concrete, testable tasks. All tasks are Python 3.13, follow Ruff, and should be covered by pytest.

## Epics
- E1: Template and Rendering Engine
- E2: Summarization Pipeline (LLM abstraction)
- E3: Highlight Detection
- E4: Markdown Writing Integration
- E5: Public API and (optional) MCP wrappers
- E6: Testing and Docs

## Tasks by Epic

### E1: Template and Rendering Engine
- T1.1 Create template loader with default presets (daily, weekly, sprint)
- T1.2 Define token replacement rules and escaping
- T1.3 Add config overrides via glin.toml / env
- T1.4 Golden tests for rendering variations (brief/standard/detailed)

### E2: Summarization Pipeline (LLM abstraction)
- T2.1 Introduce Summarizer protocol with sync function: summarize(data, style, period) -> str
- T2.2 Implement PseudoLLM for tests (deterministic, seeded)
- T2.3 Add prompt templates and fixtures for unit tests
- T2.4 Wire data from git_tools into summarizer inputs

### E3: Highlight Detection
- T3.1 Rules: merged PRs, tags, issue keys, large diffs
- T3.2 Scoring and top-N selection
- T3.3 Tests: empty input, ties, and ranking stability

### E4: Markdown Writing Integration
- T4.1 Implement write_worklog using markdown_tools.append_to_markdown semantics
- T4.2 Ensure correct headings for daily/weekly/sprint
- T4.3 Idempotency tests and newline normalization

### E5: Public API and MCP wrappers
- T5.1 Implement render_worklog(period, since/until, template)
- T5.2 Implement generate_worklog(period, ...) -> WriteResult
- T5.3 Add MCP tools (optional in Phase 3) mirroring helpers
- T5.4 Structured types (TypedDict) for WriteResult and inputs

### E6: Testing and Docs
- T6.1 Unit tests for all modules; patch external deps
- T6.2 Example usage in README
- T6.3 Coverage thresholds unchanged; add coverage for new modules

## Estimates (rough)
- E1: 1.5–2.0 days
- E2: 2.0 days
- E3: 1.0 day
- E4: 0.5 day
- E5: 0.5–1.0 day
- E6: 0.5 day

Total: ~5.5–7.0 days of focused work within the 3–4 week phase including review and iterations.

## Acceptance Criteria per Task (samples)
- T2.2: PseudoLLM returns deterministic text for same seed + input; covered by tests.
- T4.2: Weekly and sprint headings conform to spec and pass tests asserting exact line placements.
- T5.2: generate_worklog returns a dict with path, lines_written, heading_added, template_name, and period.
