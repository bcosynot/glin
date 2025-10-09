# Phase 3: Worklog Generation — Requirements

Source: .junie/Roadmap.md (Last updated: 2025-10-09)

## Objective
Provide server-side prompt templates (via FastMCP Prompts API) that LLM clients can use to generate accurate, human-readable worklogs and summaries without the server invoking any LLMs.

## In-Scope Functional Requirements
1. Server-side prompt templates (no server-side LLM calls)
   - Expose reusable prompts for commits, diffs, daily worklogs, and PR reviews.
   - Each prompt returns a sequence of MCP messages (system/user) suitable for client-side LLMs.
   - Include clear, safety-focused system guidance and deterministic structure.
2. Prompt arguments and metadata
   - Define arguments with name, description, and required flags.
   - Support optional context/date ranges.
   - Provide tags via `_meta._fastmcp.tags` to enable client-side filtering.
3. Prompt discovery and rendering
   - Prompts are discoverable through `list_prompts()` and renderable with `get_prompt(name, args)`.
   - Arguments accept complex values; clients auto-serialize to JSON per FastMCP.
4. Time-slice orientation and headings (client responsibility)
   - Prompts include guidance for daily/weekly/sprint framing; final formatting and file writes remain on the client (or existing markdown tools if used locally).
5. Documentation and examples
   - README includes examples for listing and getting prompts with FastMCP clients and argument serialization.

## Non-Functional Requirements
- Deterministic and hermetic: unit tests pass without network; no server-side LLM usage.
- Performance: listing and rendering prompts is near-instant; no heavy processing.
- Privacy-first: server does not transmit repo data externally; clients decide what to include in prompt args.
- Extensibility: easy to add new prompts without touching unrelated code.
- Error handling: return informative errors for missing/invalid arguments.

## Inputs
- Client-provided strings for commits, diffs, titles/descriptions, date ranges, etc.
- Config from glin.toml and env variables (for paths if integrating with markdown_tools locally).

## Outputs
- MCP-compatible message sequences for LLM clients.
- Optional: when used locally with markdown_tools, a structured result dict for file writes (out of primary scope for Phase 3 prompts).

## API Surface (initial)
- MCP Prompts (primary):
  - commit_summary(commits: str, date_range?: str)
  - diff_summary(diff: str, context?: str)
  - worklog_entry(date: str, inputs: str)
  - pr_review_summary(title: str, description?: str, diffs?: str, commits?: str)
- Python access occurs by importing prompts to register with the shared MCP instance (see glin/mcp_app.py).

## Prompt Content Guidelines (draft)
- System messages emphasize precision, non-invention, bullet lists, and ISO dates.
- User messages wrap inputs in XML-ish tags (<COMMITS>, <DIFF>, <INPUTS>) for clarity.

## Risks & Mitigations
- Misuse of prompts (too-long inputs) → Provide guidance in docs; clients may chunk inputs.
- Missing data → Prompts instruct the model to state when there is nothing to summarize.

## Dependencies
- FastMCP server infrastructure (already in project via mcp_app and prompts.py).

## Out of Scope (Phase 3)
- Server-side LLM invocation or streaming.
- Team aggregation dashboards and analytics.

## Definition of Done
- Unit tests cover: prompt registration, listing, argument schemas, and rendering message sequences.
- README includes examples for `list_prompts()` and `get_prompt()` with argument serialization notes.
- Prompts discoverable at runtime via the shared FastMCP instance.
