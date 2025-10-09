# Phase 3 Task Breakdown — Worklog Generation (Prompts-first)

This breakdown converts the roadmap goals into concrete, testable tasks. All tasks are Python 3.13, follow Ruff, and should be covered by pytest.

## Epics
- E1: MCP Prompts (definition and registration)
- E2: Arguments, Metadata, and Validation
- E3: Documentation and Examples
- E4: Optional Local Markdown Integration
- E5: Testing and Quality

## Tasks by Epic

### E1: MCP Prompts (definition and registration)
- T1.1 Implement core prompts in glin/prompts.py: commit_summary, diff_summary, worklog_entry, pr_review_summary
- T1.2 Ensure prompts register on the shared FastMCP instance (import order via glin/mcp_app.py)
- T1.3 Add descriptive prompt docstrings and concise descriptions for discovery
- T1.4 Add tags/metadata for filtering (e.g., ["summary", "analysis"]) where supported

### E2: Arguments, Metadata, and Validation
- T2.1 Define argument schemas (name, description, required) for each prompt
- T2.2 Confirm automatic JSON serialization compatibility for complex args in clients
- T2.3 Validate arguments at runtime and provide helpful error messages
- T2.4 Wrap inputs in clear markers (<COMMITS>, <DIFF>, <INPUTS>) for robustness

### E3: Documentation and Examples
- T3.1 README: how to list and render prompts (list_prompts/get_prompt)
- T3.2 README: argument serialization notes and small code snippets
- T3.3 Guidance on chunking long inputs and using ISO dates

### E4: Optional Local Markdown Integration
- T4.1 Example: take client-produced text and write to WORKLOG.md using markdown_tools.append_to_markdown
- T4.2 Ensure correct daily heading (## YYYY-MM-DD) in example and tests
- T4.3 Idempotency and newline normalization in example tests

### E5: Testing and Quality
- T5.1 Unit tests: prompt registration and discovery
- T5.2 Unit tests: get_prompt() returns expected message shapes and content markers
- T5.3 Maintain coverage thresholds; add focused tests for prompts.py
- T5.4 Ruff format/lint as part of CI

## Estimates (rough)
- E1: 1.0–1.5 days
- E2: 0.5–1.0 days
- E3: 0.5 day
- E4: 0.5 day (optional)
- E5: 0.5 day

Total: ~3.0–4.0 days of focused work within the 3–4 week phase including review and iterations.

## Acceptance Criteria per Task (samples)
- T5.2: get_prompt("worklog_entry", {"date":"2025-10-09","inputs":"..."}) yields a two-message sequence (system+user) with <INPUTS> block.
- T4.2: Example ensures headings conform to markdown_tools conventions with exact line placements in tests.
