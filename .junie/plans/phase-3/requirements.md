# Phase 3: Worklog Generation — Requirements

Source: .junie/Roadmap.md (Last updated: 2025-10-09)

## Objective
Transform stored git/conversation data into accurate, human-readable worklogs suitable for daily standups, weekly/sprint updates, and performance reviews.

## In-Scope Functional Requirements
1. Natural language summarization
   - Use an LLM to turn structured activity data (commits, diffs, file stats, conversations) into prose.
   - Controllable verbosity: brief, standard, detailed.
   - Supports perspectives: individual developer (default); future: team roll-up (out of scope now).
2. Configurable summary templates
   - Token-based or Jinja-like templates to shape structure (e.g., headings, sections).
   - Built-in presets: daily.md, weekly.md, sprint.md.
   - Per-user overrides via glin.toml or env var.
3. Time-slice summaries
   - Daily, weekly, and sprint windows.
   - Date bounds may be explicit (YYYY-MM-DD) or relative ("yesterday", "last week").
4. Achievement highlighting
   - Detect notable events: merged PRs, first release tags, big diffs, closed issues (if referenced in commits).
   - Deduplicate and rank highlights; include links/ids when available.
5. Markdown output
   - Write summaries to a Markdown file with normalized Unix newlines.
   - Default path: ./WORKLOG.md (align with markdown_tools), overridable via GLIN_MD_PATH or function arg.
   - Ensure a date-scoped heading: "## YYYY-MM-DD" for daily; "## YYYY-Www" for weekly; "## Sprint <name or dates>".

## Non-Functional Requirements
- Deterministic and hermetic: unit tests must pass without network; all LLM calls are mockable.
- Performance: generate a daily worklog for 200 commits in < 1s with cached inputs; < 3s cold (excluding real LLM).
- Privacy-first: no data leaves machine in tests; clearly marked flags if/when remote LLMs are used.
- Extensibility: summarizer and template engines modular; new templates can be added without touching core.
- Error handling: return structured errors; never corrupt existing WORKLOG.md.

## Inputs
- Git data via glin.git_tools.* (commits, diffs, files, branches, stats).
- Optional conversation data (will be empty/stub in Phase 3).
- Config from glin.toml and env variables (GLIN_TRACK_EMAILS, GLIN_MD_PATH, template overrides).

## Outputs
- Markdown text appended to or created at target path.
- Structured result dict for tools and tests: path, range of lines written, bullets/sections added, template used, time window, did_add_heading, etc.

## API Surface (initial)
- Python helpers (not MCP yet):
  - render_worklog(period: Literal["daily","weekly","sprint"], *, since: str|None, until: str|None, template: str|None) -> str
  - write_worklog(markdown: str, *, file_path: str|None) -> WriteResult (TypedDict)
  - generate_worklog(period: Literal["daily","weekly","sprint"], **kwargs) -> WriteResult
- MCP wrappers (Phase 3 late or Phase 4): mirror helpers and return the WriteResult structure.

## Template Tokens (draft)
- {{date}}, {{period}}, {{since}}, {{until}}
- {{highlights}} (bulleted), {{commits}} (grouped), {{stats}} (files, lines added/removed), {{branches}}, {{languages}}

## Risks & Mitigations
- LLM variability → Provide deterministic test-mode with canned responses and seedable pseudo-LLM.
- Large diffs → Cap per-commit details; summarize by file/language.
- Missing data (no commits) → Emit informative stub section, not an error.

## Dependencies
- Phase 1 git utilities (commits, diffs, stats) — DONE per roadmap.
- Phase 2 storage — DONE per roadmap and used as optional cache.

## Out of Scope (Phase 3)
- Real conversation capture and indexing (Phase 4).
- Team aggregation, dashboards, and analytics (Phase 5+).

## Definition of Done
- Unit tests covering: template rendering, heading insertion, empty-data behavior, highlight detection, and file writing semantics.
- CLI/MCP: optional; at least Python helpers callable from code/tests.
- Documentation in README: short usage snippet and config options.