# Prompts Reference

This page documents server-side prompts exposed via the MCP Prompts API. These prompts do not call LLMs; they return message sequences your client can feed to an LLM.

## worklog_entry

- Purpose: Generate an engineering worklog entry for a given day or period. If tool-calling is available, it orchestrates Git and GitHub data gathering before synthesis and then persists the result into your worklog file.
- Arguments:
  - date (string): Target day or period. Accepts YYYY-MM-DD, a range (YYYY-MM-DD..YYYY-MM-DD), or relative expressions like "yesterday", "last 2 days".
  - inputs (string, optional): Free-text notes to incorporate.
- Behavior highlights:
  - Gathers commits per repository using git MCP tools (get_commits_by_date, get_enriched_commits, get_remote_origin, determine_commit_url_prefix).
  - Correlates commits with conversations (get_recent_conversations) and with pull requests when PR numbers are found.
  - Produces structured sections: Goals & Context, Technical Work, Metrics, Key Decisions, Impact, Open Items, Learnings.
  - Persists one block per date by calling append_to_markdown with update_mode=true so entries merge idempotently.
  - Optionally writes a Weekly Summary for the Monday..Sunday window when a full week has completed and there are newer entries past the Sunday.
- Returns: list of messages like [{"role": "system"|"user", "content": "..."}] suitable for your LLM client.
- See code: seev.prompts.worklog_entry_prompt.

### Slash command usage

- Syntax: `/worklog_entry <date> [inputs]`
  - Positional arguments: `date` is required; `inputs` is optional.
  - Quoting: wrap strings that contain spaces in quotes. Double or single quotes are both allowed.
  - Spacing: use a single space between tokens.

Examples (today is 2025-10-26):
- `/worklog_entry 2025-10-25 "Wrapped up feature X; reviewed PR #123"`
- `/worklog_entry "last 2 days" "Pair-programmed on the parser; validated caching behavior"`
- `/worklog_entry 2025-10-20..2025-10-26`

Expected tool calls (handled by your assistant):
- get_tracked_repositories_config
- get_commits_by_date (per repo)
- get_enriched_commits (optional)
- get_recent_conversations
- get_remote_origin → determine_commit_url_prefix
- append_to_markdown (once per date)

---

## conversation_summary

- Purpose: Create a concise summary of the current task/conversation and persist it by calling the `record_conversation_summary` tool.
- Arguments:
  - date (string, optional): ISO calendar date (YYYY-MM-DD). If omitted/blank, the server resolves it to today's local date when rendering the prompt.
  - title (string, optional): Title used when creating a new conversation. If not provided and `conversation_id` is null, the LLM should derive a short title from the first sentence (<= 80 chars, no newlines).
  - conversation_id (integer, optional): Existing conversation id to append the summary to; when provided, `title` is ignored.
  - inputs (string, optional): Notes, highlights, or raw text to base the summary on.
- Behavior highlights:
  - The prompt instructs the LLM to write a brief summary (bullets or short sentences) emphasizing goals, key decisions, outcomes, blockers, and next steps.
  - Immediately after writing the summary, the LLM must call `record_conversation_summary` with the resolved parameters, using the server-injected date to avoid ambiguity.
- Returns: list of messages like [{"role": "system"|"user", "content": "..."}] suitable for your LLM client.
- See code: seev.prompts.conversation_summary_prompt.

### Slash command usage

- Syntax: `/conversation_summary <date|""> <title|""> <conversation_id|""> <inputs|"">`
  - Positional arguments, left-to-right. You may omit trailing optional arguments entirely.
  - Use an empty quoted string "" as a placeholder to skip an earlier argument (e.g., blank date means "use today").
  - Quoting: wrap strings with spaces in quotes. Double or single quotes are both allowed.
  - Spacing: use a single space between tokens.

Examples (today is 2025-10-26):
- `/conversation_summary "" "Cache rollout" "" "Finished caching layer; decided on Redis; add integration tests next"`
- `/conversation_summary 2025-10-26 "Cache rollout" "" "Finished caching layer; decided on Redis; add integration tests next"`
- `/conversation_summary 2025-10-26 "" 42 "Short update"`

Rules your assistant should follow (already encoded in the prompt):
- Make exactly one tool call to `record_conversation_summary`.
- If `conversation_id` is provided, ignore title derivation.
- If both `conversation_id` and `title` are omitted (i.e., both placeholders are empty), derive a short title from the first sentence (≤ 80 chars).
