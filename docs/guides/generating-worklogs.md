# Generating Worklogs

This guide shows practical, copy‑pasteable ways to create worklog entries using Seev via your MCP client.

## TL;DR examples

```text
/worklog_entry today
```

```text
/worklog_entry 2025-10-20
```

```text
/worklog_entry last week
```

```text
/worklog_entry 2025-10-15..2025-10-22
```

!!! tip
    Use natural language: `yesterday`, `last 2 days`, `1 week ago` are all supported.

## What the assistant does under the hood

1. Calls Seev's MCP tools to gather context (commits, conversations, PRs, metrics)
2. Correlates commits with conversations/PRs
3. Generates a structured markdown entry
4. Appends it under `## YYYY‑MM‑DD` in your WORKLOG.md

## Controlling scope with date ranges

- Single day: `2025-10-22` or `today`
- Relative: `last week`, `last 2 days`, `1 week ago`
- Explicit range: `2025-10-15..2025-10-22`

Examples:

```text
/worklog_entry yesterday
```

```text
/worklog_entry last 2 days
```

```text
/worklog_entry 2025-10-15..2025-10-22
```

## Adding your own context

Provide inputs to guide the summary:

```text
/worklog_entry today inputs="Refactored auth module; fixed checkout bug; reviewed dashboard PR"
```

The assistant will weave your inputs into Goals, Technical Work, and Decisions.

## Where entries are saved

Default path is the workspace worklog file, typically:

```bash
$ echo $SEEV_MD_PATH
/home/you/seev-workspace/WORKLOG.md
```

Change it by setting `SEEV_MD_PATH` before launching your client.

## Correlation details

Seev enriches entries by:

- Matching commits to conversations by time proximity and content hints
- Detecting PRs for commits when the GitHub MCP is available
- Computing metrics (additions, deletions, files changed)

See also: [MCP Prompts Reference](../reference/index.md#prompts) and [Workspace & Configuration](workspace-and-configuration.md).
