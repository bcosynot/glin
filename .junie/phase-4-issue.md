Title: Phase 4 — Reference, Troubleshooting, Changelog, Privacy

Summary
Build out the core reference and support pages so users can self-serve: API reference (mkdocstrings), MCP tools and prompts references, Troubleshooting/FAQ, Privacy & Data, Contributing, and seed the Changelog.

Why
- Users can find exact signatures/types and resolve issues without support.

Files/Artifacts
- docs/reference/index.md (mkdocstrings-driven)
- docs/reference/mcp-tools.md
- docs/reference/prompts.md
- docs/troubleshooting.md
- docs/privacy-and-data.md
- docs/contributing.md
- docs/changelog.md

Tasks
1) Python API reference (mkdocstrings): intro + blocks for key modules (seev.config, seev.git_tools.*, seev.markdown_tools). Use python handler.
2) MCP Tools Reference: one section per tool (purpose, args, example, return shape). Cross-link to API/code.
3) Prompts Reference: document `worklog_entry` prompt (args, behavior, examples).
4) Troubleshooting & FAQ: common errors with cause + fix; environment gotchas. Ensure anchors are linkable.
5) Privacy & Data: local-first storage, what’s logged, control knobs; align with README.
6) Contributing: tests (make test), format/lint (make format, make lint), PR checklist.
7) Changelog: create page with `Unreleased` section and link it in nav.

Commands
- uv run mkdocs build --strict

Verification (Done when all true)
- API reference renders without import errors.
- Cross-links work between reference and guides.
- Troubleshooting entries have clear anchor links.
- Strict build passes.

Junior implementation notes
- Prefer examples-first copy; keep headings semantic (h2/h3).
- Use admonitions for tips/warnings where appropriate.

Relevant requirements (inlined)
- Reference: Python API via mkdocstrings; MCP tools; Prompts.
- Support: Troubleshooting & FAQ; Privacy & Data; Contributing; Changelog linked from nav.
