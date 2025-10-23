"""
Server-side prompt templates for LLM use via FastMCP Prompts API.

These prompts do not call any LLMs. They return message sequences
that a client LLM can use to produce summaries and reports.

Clients can discover these with `list_prompts()` and render with
`get_prompt(name, args)` when using a FastMCP client.
"""

from typing import Annotated, TypedDict

from fastmcp.utilities.logging import get_logger  # type: ignore
from pydantic import Field

from .mcp_app import mcp

log = get_logger("glin.prompts")


class PromptArg(TypedDict):
    name: str
    description: str
    required: bool


def _system_header(title: str) -> str:
    return (
        "You are a precise, transparent technical writing assistant. "
        f"Task: {title}.\n"
        "- Never invent facts.\n"
        "- Prefer bullet lists and short paragraphs.\n"
        "- Include concrete dates in ISO format when present.\n"
        "- If input appears to be JSON, preserve keys and values verbatim in quotes.\n"
        "- If there is nothing to summarize, say so succinctly."
    )


@mcp.prompt(
    name="worklog_entry",
    description=(
        "Generate a worklog entry for a given date or period. If tool-calling is "
        "available, first gather commits, conversations, PR details, enrichment, and optional heatmap for the period "
        "using appropriate MCP tools. Correlate commits with any recorded conversations for the same period and include those correlations in the entry "
        "(e.g., note which conversation a commit implements). When merge commits reference GitHub pull requests (e.g., "
        "'#123' or 'Merge pull request #123'), use the GitHub MCP 'pull_requests' toolset to fetch key PR details (title, author, state/merged, URL) and include them. "
        "Then produce a structured markdown yourself with sections: 🎯 Goals & Context, 💻 Technical Work, 📊 Metrics, 🔍 Key Decisions, ⚠️ Impact Assessment, 🚧 Open Items, 📚 Learnings. "
        "Do not call the 'generate_rich_worklog' tool; instead, synthesize these sections directly from the gathered data."
    ),
    tags=["worklog", "summary", "daily", "git", "commits"],
)
def worklog_entry_prompt(
    date: Annotated[
        str,
        Field(
            description=(
                "Target day or period. Accepts 'YYYY-MM-DD', a range 'YYYY-MM-DD..YYYY-MM-DD', or "
                "relative expressions like 'yesterday', 'last 2 days', '1 week ago'."
            )
        ),
    ],
    inputs: Annotated[
        str,
        Field(description="Free-text notes, bullets, or context to include in the worklog entry."),
    ],
) -> list[dict[str, str]]:
    if not date or not date.strip():
        log.warning("worklog_entry: empty date arg")
        raise ValueError("date argument is required and cannot be empty")
    if not inputs or not inputs.strip():
        log.warning("worklog_entry: empty inputs arg")
        raise ValueError("inputs argument is required and cannot be empty")
    log.info(
        "worklog_entry: rendering",
        extra={"date_len": len(date), "inputs_len": len(inputs)},
    )
    system = _system_header("Create an engineering worklog entry from commits and notes")
    user = (
        f"Create a worklog entry for the period: {date}. "
        "If you can call MCP tools, follow this workflow:\n\n"
        "STEP 1 — Get tracked repositories configuration:\n"
        "- First, call 'get_tracked_repositories_config' to retrieve the list of repositories to include in the worklog.\n"
        "- The tool returns: tracked_repositories (list), count, and source (environment variable or config file).\n"
        "- If the count is 0 (no tracked repositories configured), fall back to the current directory as the single repository to process.\n\n"
        "STEP 2 — Iteratively gather data for each repository:\n"
        "- For each repository R in the tracked_repositories list (or current directory if empty):\n"
        "  • If R is a local filesystem path that contains a Git repository:\n"
        "    - Call git MCP tools with 'workdir' parameter set to R (e.g., 'get_commits_by_date', 'get_recent_commits', 'get_branch_commits', 'get_commit_files', 'get_commit_diff', 'get_remote_origin').\n"
        "    - Gather: commits via 'get_commits_by_date'; enriched stats via 'get_enriched_commits' (additions/deletions, files changed) when available.\n"
        "    - To generate commit links: call 'get_remote_origin' with workdir=R, then 'determine_commit_url_prefix' with the returned URL.\n"
        "  • If R is a remote identifier (e.g., 'owner/repo' GitHub shorthand or a Git URL):\n"
        "    - Use the GitHub MCP or the GitHub CLI to fetch commits and related activity for that repository.\n"
        "    - Extract owner/repo from the identifier and query GitHub APIs accordingly.\n"
        "  • For each repository, use the Github MCP, falling back to the GitHub CLI, to fetch PR and Issues details (PRs or issues authored by the user, PRs reviewed by the user, or comments on PRs or issues left by the user) for the specified period.\n"
        "  • Collect data for the specified period across all repositories before proceeding to synthesis.\n\n"
        "STEP 3 — Gather additional context:\n"
        "- Recent conversations via 'get_recent_conversations'.\n"
        "When calling tools that accept a 'workdir' parameter, always include 'workdir' pointing to a path inside the target repository so commands execute in the correct repo.\n"
        "Correlate commits with conversations as follows: For each commit, try to identify related conversations by matching keywords, issue keys, or PR numbers present in the commit message to conversation titles/previews. When you have high confidence, include the related conversation title next to the commit summary (e.g., 'Implements: <Conversation Title>'). Optionally record the association by calling 'link_commit_to_conversation' with a relevance score between 0.5 and 1.0.\n"
        "Then, scan the commits for merge commits that reference pull requests (patterns like "
        "'Merge pull request #123' or '#123' in the message). When PR numbers are found and the GitHub MCP is available, "
        "use the GitHub Pull Requests toolset (falling back to the GitHub CLI) to retrieve details for those PRs (at minimum: title, number, HTML URL, author, "
        "state — open/closed/merged — and merge date/mergedBy). Include a one-line PR summary with the merge item. If the toolset "
        "is not available, include the PR numbers as-is.\n"
        "Additionally, for each merge commit, attempt to determine the merged branch name (e.g., from messages like 'Merge branch <name>' or 'Merge pull request ... from <owner>/<branch>'). If a branch name is identified, call the 'get_commits_by_date' MCP tool again with the same since/until window and with branch set to that merged branch. Use the returned commits to add a brief sub-summary under the merge item highlighting what was brought in by that branch. If the branch cannot be determined, skip this step.\n"
        "Next, use the GitHub MCP server to collect first-party activity for this period authored by the user: (1) issues opened, (2) PR comments, and (3) PR reviews. Determine the actor to filter by using the configured emails from 'get_tracked_emails' (map to GitHub login when possible) or fall back to the git author name/email. Apply the same since/until window when querying GitHub. Additionally, gather related context: issues referenced in PRs that the user created or reviewed, and reviews submitted by others on PRs created by the user.\n"
        "- Issues: fetch issues created by the user in the window; also fetch any issues referenced in PRs that the user created or reviewed (even if those issues were opened by someone else). For each issue, include a one-line summary with number/title/state/url and explicitly indicate the creator (e.g., 'by <login>' or 'by you'). Correlate each issue to any local branches and PRs that reference the issue key/number in branch names, commit messages, or PR titles. Add a 'Correlated PR/branch' sub-bullet when found.\n"
        "- PR comments: fetch comments authored by the user in the window. If a comment is on a PR created by the same user, include it inline with that PR's work item while summarizing the PR's evolution. If a comment was made in reference to a review the user submitted, include it under the context of that review (see Reviews below).\n"
        "- PR reviews: fetch submitted reviews by the user in the window (state, summary, decision). List these under Technical Work as discrete items with PR number/title/state/url. Also reflect their content in 'Key Decisions', 'Impact Assessment', and 'Learnings' where applicable.\n"
        "- Reviews on your PRs (by others): for PRs authored by the user, fetch reviews submitted by other participants within the window (state/decision, reviewer, highlights). Include their feedback inline with the corresponding PR item and factor it into summaries and context (Key Decisions, Impact Assessment, Learnings).\n"
        "To turn commit hashes into clickable links, determine the commit URL prefix by calling the "
        "'determine_commit_url_prefix' tool. First call 'get_remote_origin' to get the repository URL, "
        "then call 'determine_commit_url_prefix' with it. If the tool returns an error or an empty prefix, "
        "leave hashes as plain text without links.\n"
        "Finally, combine your structured sections with any notes below. Use ISO dates. If there are no commits, say so. Keep the writing concise and non-redundant.\n\n"
        "IMPORTANT — Persisting the worklog:\n"
        "- Group the final worklog content by each calendar date covered by the period.\n"
        "- Sort dates ascending (earliest first).\n"
        "- For each date D, produce a markdown block\n"
        "Now, produce the final structured markdown yourself (do not call 'generate_rich_worklog'). Group content by each calendar date covered. For each date, include the following sections with the specified details:\n\n"
        "### 🎯 Goals & Context\n"
        "- Summarize top goals/objectives for the day inferred from conversations (titles + first user message excerpts) and the provided inputs.\n"
        "- DO break down into multiple bullets if more than one goal/objective is present. Never comma-join multiple goals into a single bullet; always split them.\n"
        "- Note constraints, blockers, or external events shaping the work.\n"
        "- If no conversations exist, derive goals from commit themes and inputs.\n\n"
        "### 💻 Technical Work\n"
        "- deduplicated commit list with the same per-commit details and link to the commit.\n"
        "- PRs reviewed by the user (if any)"
        "- Never comma-join multiple work items into one bullet; one item per bullet.\n\n"
        "### 📊 Metrics\n"
        "- Total commits for the date.\n"
        "- Additions and deletions (from enrichment) when available.\n"
        "- Files touched and top languages by additions (top 3), plus the 'hot' file if provided by heatmap.\n"
        "- PRs opened/merged and notable branch merges (counts).\n\n"
        "- DO break down each metric into its own bullet. For example, 'Total commits' should be a bullet, not a header.\n\n"
        "### 🔍 Key Decisions\n"
        "- Bullet the important decisions made (from conversations and commit messages), with brief rationale and alternatives considered.\n"
        "- Reference the related conversation title or PR when applicable.\n"
        "- Split multiple decisions into separate bullets; never comma-join them into one bullet.\n\n"
        "### ⚠️ Impact Assessment\n"
        "- Describe the impact of changes on users, subsystems, APIs, and dependencies.\n"
        "- Call out risks/regressions and suggested tests or mitigations.\n"
        "- DO break down into multiple bullets if more than one impact category is present.\n"
        "- Note performance implications and backward-compatibility considerations.\n\n"
        "### 🚧 Open Items\n"
        "- List follow-ups, TODOs, and blockers with owners (if known) and next steps.\n"
        "- DO break down into multiple bullets if more than one open item category is present.\n"
        "- Include due dates or milestones if present.\n\n"
        "### 📚 Learnings\n"
        "- Capture lessons, debugging insights, patterns, tools, and gotchas worth remembering.\n"
        "- Split multiple learnings into separate bullets; never comma-join them into one bullet.\n\n"
        "Guidance for deriving since/until from the period string:\n"
        "- Single day 'YYYY-MM-DD' → since='YYYY-MM-DD', until='YYYY-MM-DD 23:59:59'.\n"
        "- Range 'YYYY-MM-DD..YYYY-MM-DD' → since=start, until=end '23:59:59'.\n"
        "- Relative periods (e.g., 'yesterday', 'last 2 days', '1 week ago') → since=expression, "
        "until='now'.\n\n\n"
        "After generating the above markdown content, then immediately call the 'append_to_markdown' MCP tool with:\n"
        "  • date_str = D (ISO format YYYY-MM-DD)\n"
        "  • content = the date-specific markdown block with h3 sub-headings and bullets\n"
        "  • preserve_lines = true (so lines are written as-is without auto-bullets)\n"
        "  • file_path can be omitted (defaults to GLIN_MD_PATH or ./WORKLOG.md).\n"
        "- Make exactly one tool call per date with just that date's content. Do not batch multiple dates in one call.\n\n"
        "Edge cases:\n"
        "- If a date has neither commits nor conversations, you may persist a single bullet line (e.g., '- No recorded commits or conversations (planning/research/offline work possible).') inside the '### Work' section.\n"
        "- If Git tools are unavailable or return errors for the period, add a one-line 'Data unavailable' note and proceed with the remaining sources.\n"
    )
    if inputs:
        user += f"\n\n<INPUTS>\n{inputs}\n</INPUTS>"
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    log.info("worklog_entry: rendered", extra={"messages": len(msgs)})
    return msgs
