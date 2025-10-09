# Phase 3 Project Plan — Worklog Generation (Prompts-first, v0.4.0)

Source: .junie/Roadmap.md (2025-10-09)

## Goals
- Provide reusable, documented server-side prompt templates for commit/diff/worklog/PR summaries via FastMCP.
- Enable client LLMs to generate daily/weekly/sprint summaries using these prompts; the server does not call LLMs.

## Milestones and Deliverables
1. M1: Prompt Scaffolding (Week 1)
   - Implement core prompts in glin/prompts.py: commit_summary, diff_summary, worklog_entry, pr_review_summary.
   - Register prompts on the shared FastMCP instance (glin/mcp_app.py).
   - Basic tags/metadata for filtering (e.g., ["summary", "analysis"]).
2. M2: Arguments and Validation (Week 2)
   - Define argument schemas (names/descriptions/required) and input wrapping conventions (<COMMITS>, <DIFF>, etc.).
   - Tests for list_prompts/get_prompt, including automatic JSON serialization behavior in clients.
3. M3: Documentation and Examples (Week 3)
   - README updates: how to list and render prompts; example client snippets.
   - Usage guidance: size limits, chunking tips, and date formatting.
4. M4: Optional Local Integration (Week 4)
   - Example flow using markdown_tools locally to write worklogs with client-rendered text.
   - Keep file writing out of server responsibilities; provide guidance only.

## Timeline
- Estimated: 3–4 weeks (per roadmap). Target v0.4.0.

## Work Breakdown Structure
- Prompts
  - System/user message composition with safety and structure guidance.
  - Tags/metadata for filtering; argument docs.
- Testing
  - Unit tests for registration, discovery, and rendering outputs.
- Docs
  - README examples for FastMCP prompt APIs; notes on argument serialization.
- Optional Examples
  - Local markdown writing example leveraging markdown_tools.

## Definition of Done
- All M1–M4 deliverables complete with tests and README updates.
- Coverage does not regress; new prompt module has focused tests.
- No server-side LLM usage; prompts are discoverable and renderable.

## Risks and Contingencies
- Overly long inputs → Recommend chunking and selective inclusion in docs.
- Ambiguous client expectations → Provide minimal but clear output format expectations within prompts.
- File clobbering (when using local examples) → Use append_to_markdown and tmp paths in examples/tests.

## Acceptance
- Clients can call list_prompts() and get_prompt() to retrieve message sequences for the four core prompts.
