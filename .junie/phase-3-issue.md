Title: Phase 3 — Guides content (minimum viable set)

Summary
Create core “Guides” pages that let a new user succeed in ≤ 10 minutes and enable deeper usage. Provide stubs where needed but aim for usable content, examples-first.

Why
- Guides are the primary success path and reduce support burden.

Files/Artifacts
- docs/guides/index.md (summaries + links)
- docs/guides/quick-start.md
- docs/guides/workspace-and-configuration.md
- docs/guides/generating-worklogs.md
- docs/guides/mcp-clients.md

Tasks
1) Guides index: 1–2 sentence synopsis per guide; ensure links resolve.
2) Quick Start (≤ 10 minutes):
   - Prereqs: Python 3.13, uv, git
   - Install via curl `seev-init.sh`
   - Add Seev to MCP client (tabs: Claude Desktop, Cursor, Cline)
   - Generate first worklog entry with example
   - End with a verification checklist
3) Workspace & Configuration: tracked emails, paths, env vars; examples mirror README.
4) Generating Worklogs: examples-first; date ranges; correlation; link to MCP prompts reference.
5) Using Different MCP Clients: tabs for each client; include config file paths; screenshots later.

Commands
- uv run mkdocs serve
- uv run mkdocs build --strict

Verification (Done when all true)
- A new user test completes Quick Start on macOS/Linux in ≤ 10 minutes.
- Tabs render and are keyboard accessible.
- Code blocks have copy buttons and run as written.
- Strict build passes.

Junior implementation notes
- Put commands first, then explain.
- Use admonitions for tips/warnings at risky steps.

Relevant requirements (inlined)
- Goals: new user can install, run, and succeed in under 10 minutes.
- UX: tabs, copy buttons, on-page TOC, last updated metadata.
