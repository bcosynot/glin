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

### Example

Request (client-side pseudocode):

```
prompt = client.get_prompt("worklog_entry")
messages = prompt.render(date="2025-10-25", inputs="Wrapped up feature X; reviewed PR #123")
# Feed messages to your LLM and then let it call MCP tools per instructions.
```

Expected tool calls during execution (by your LLM agent):
- get_tracked_repositories_config
- get_commits_by_date (per repo)
- get_enriched_commits (optional)
- get_recent_conversations
- get_remote_origin → determine_commit_url_prefix
- append_to_markdown (once per date)
