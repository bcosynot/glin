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


# --- Commit summary --------------------------------------------------------


@mcp.prompt(
    name="commit_summary",
    description=(
        "Create a clear, non-redundant summary of one or more Git commits, "
        "highlighting types (feat/fix/docs/etc), scopes, and notable changes by language."
    ),
    tags=["summary", "git", "commits"],
)
def commit_summary_prompt(
    commits: Annotated[
        str,
        Field(
            description=(
                "A text block with one or more commit entries (e.g., formatted git log output) "
                "or the 'get_commits_by_date' MCP tool. Provide raw text; do not JSON-encode."
            )
        ),
    ],
    date_range: Annotated[
        str | None,
        Field(
            description=(
                "Optional label describing the time window for the commits (e.g., '2025-10-01..' "
                "'2025-10-07', 'yesterday', or 'last 2 days'). Used only to improve the title."
            )
        ),
    ] = None,
) -> list[dict[str, str]]:
    if not commits or not commits.strip():
        log.warning("commit_summary: empty commits arg")
        raise ValueError("commits argument is required and cannot be empty")
    log.info(
        "commit_summary: rendering",
        extra={"date_range": bool(date_range), "commits_len": len(commits)},
    )
    title = "Summarize Git commits"
    if date_range:
        title += f" for {date_range}"
    system = _system_header(title)
    user = (
        "Summarize the following commits for a changelog/worklog entry.\n"
        "Guidelines:\n"
        "- Group by type and scope when available.\n"
        "- Include counts (commits, files, additions/deletions if provided).\n"
        "- Call out merges and PR numbers when present.\n"
        "- Provide a short highlights section and a detailed bullet list.\n\n"
        "<COMMITS>\n" + commits + "\n</COMMITS>"
    )
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    log.info("commit_summary: rendered", extra={"messages": len(msgs)})
    return msgs


# --- Diff summary ----------------------------------------------------------


@mcp.prompt(
    name="diff_summary",
    description="Summarize a unified diff or patch into human-readable changes and risk areas.",
    tags=["summary", "analysis", "git", "diff"],
)
def diff_summary_prompt(
    diff: Annotated[
        str,
        Field(
            description=(
                "Unified diff/patch text to analyze (e.g., output of 'git diff --unified' or a PR "
                "patch)."
            )
        ),
    ],
    context: Annotated[
        str | None,
        Field(
            description=(
                "Optional free-text context to tailor the summary (e.g., repository, ticket, goal, "
                "release)."
            )
        ),
    ] = None,
) -> list[dict[str, str]]:
    if not diff or not diff.strip():
        log.warning("diff_summary: empty diff arg")
        raise ValueError("diff argument is required and cannot be empty")
    log.info(
        "diff_summary: rendering",
        extra={"context": bool(context), "diff_len": len(diff)},
    )
    system = _system_header("Summarize a code diff and identify impacts")
    ctx = f"Context: {context}\n\n" if context else ""
    user = (
        ctx + "Summarize the diff below. Provide: (1) high-level overview, (2) key modules/files, "
        "(3) notable API/behavior changes, (4) risks and test ideas.\n\n"
        "<DIFF>\n" + diff + "\n</DIFF>"
    )
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    log.info("diff_summary: rendered", extra={"messages": len(msgs)})
    return msgs


# --- Worklog entry builder -------------------------------------------------


@mcp.prompt(
    name="worklog_entry",
    description=(
        "Generate a worklog entry for a given date or period. If tool-calling is "
        "available, first gather commits, conversations, PR details, enrichment, sessions, and optional heatmap for the period "
        "using appropriate MCP tools. Correlate commits with any recorded conversations for the same period and include those correlations in the entry "
        "(e.g., note which conversation a commit implements). When merge commits reference GitHub pull requests (e.g., "
        "'#123' or 'Merge pull request #123'), use the GitHub MCP 'pull_requests' toolset to fetch key PR details (title, author, state/merged, URL) and include them. "
        "Then produce a structured markdown yourself with sections: 🎯 Goals & Context, 💻 Technical Work (sessions when available; otherwise flat list), 📊 Metrics, 🔍 Key Decisions, ⚠️ Impact Assessment, 🚧 Open Items, 📚 Learnings. "
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
        "If you can call MCP tools, first gather context for this period: Git commits via 'get_commits_by_date'; recent conversations via "
        "'get_recent_conversations'; enriched Git stats via 'get_enriched_commits' (additions/deletions, files changed) when available; "
        "time-bounded work sessions via 'get_work_sessions' (to group commits into sessions) when available; and an optional file/language heatmap via "
        "'get_file_heatmap' if present.\n"
        "Correlate commits with conversations as follows: For each commit, try to identify related conversations by matching keywords, issue keys, or PR numbers present in the commit message to conversation titles/previews. When you have high confidence, include the related conversation title next to the commit summary (e.g., 'Implements: <Conversation Title>'). Optionally record the association by calling 'link_commit_to_conversation' with a relevance score between 0.5 and 1.0.\n"
        "Then, scan the commits for merge commits that reference pull requests (patterns like "
        "'Merge pull request #123' or '#123' in the message). When PR numbers are found and the GitHub MCP is available, "
        "use the GitHub Pull Requests toolset to retrieve details for those PRs (at minimum: title, number, HTML URL, author, "
        "state — open/closed/merged — and merge date/mergedBy). Include a one-line PR summary with the merge item. If the toolset "
        "is not available, include the PR numbers as-is.\n"
        "Additionally, for each merge commit, attempt to determine the merged branch name (e.g., from messages like 'Merge branch <name>' or 'Merge pull request ... from <owner>/<branch>'). If a branch name is identified, call the 'get_commits_by_date' MCP tool again with the same since/until window and with branch set to that merged branch. Use the returned commits to add a brief sub-summary under the merge item highlighting what was brought in by that branch. If the branch cannot be determined, skip this step.\n"
        "Next, use the GitHub MCP server to collect first-party activity for this period authored by the user: (1) issues opened, (2) PR comments, and (3) PR reviews. Determine the actor to filter by using the configured emails from 'get_tracked_emails' (map to GitHub login when possible) or fall back to the git author name/email. Apply the same since/until window when querying GitHub.\n"
        "- Issues: fetch issues created by the user in the window; correlate each issue to any local branches and PRs that reference the issue key/number in branch names, commit messages, or PR titles. Include a short one-line per issue with number/title/state/url and add a 'Correlated PR/branch' sub-bullet when found.\n"
        "- PR comments: fetch comments authored by the user in the window. If a comment is on a PR created by the same user, include it inline with that PR's work item while summarizing the PR's evolution. If a comment was made in reference to a review the user submitted, include it under the context of that review (see Reviews below).\n"
        "- PR reviews: fetch submitted reviews by the user in the window (state, summary, decision). List these under Technical Work as discrete items with PR number/title/state/url. Also reflect their content in 'Key Decisions', 'Impact Assessment', and 'Learnings' where applicable.\n"
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
        "### 💻 Technical Work (sessions when available; otherwise flat list)\n"
        "- If sessions are available: for each session, show time window (HH:MM-HH:MM), duration (m), optional theme, then list commits:\n"
        "  • For each commit/work item: concise message, type/scope if detectable, primary module/file, short hash (link if commit URL prefix known).\n"
        "  • If a commit/work item correlates with a PR, add a sub-bullet with PR number/title/status/link (format: 'PR: #<num> (<state>) — <title>; <url>').\n"
        "  • Add another sub-bullet 'Context:' synthesizing details from related conversations, commit messages, PR descriptions, and comments.\n"
        "  • For merge commits: include a sub-bullet summary of what the merged branch brought (from its commits), and PR title/number/status/link when available.\n"
        "  • DO break down into multiple bullets if summarizing more than one PR.\n"
        "- If sessions are not available: present a flat, deduplicated commit list with the same per-commit details and link to the commit.\n"
        "- Never comma-join multiple work items into one bullet; one item per bullet.\n\n"
        "### 📊 Metrics\n"
        "- Total commits for the date.\n"
        "- Additions and deletions (from enrichment) when available.\n"
        "- Files touched and top languages by additions (top 3), plus the 'hot' file if provided by heatmap.\n"
        "- Focused time and sessions when sessions are available. Report exactly as: 'Focused time: <minutes>m (sessions: <count>)'.\n"
        "- PRs opened/merged and notable branch merges (counts).\n\n"
        "- DO break down each metric into its own bullet. For example, 'Total commits' should be a bullet, not a header.\n\n"
        "If the period spans multiple days, also include a one-line period-level total focused time before the first date section, formatted exactly as: 'Focused time total (period): <HhMm or Mm> (sessions: <count>)'.\n\n"
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
        "- If heatmap data is unavailable, omit heatmap-related metrics entirely.\n"
    )
    if inputs:
        user += f"<INPUTS>\n{inputs}\n</INPUTS>"
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    log.info("worklog_entry: rendered", extra={"messages": len(msgs)})
    return msgs


# --- PR review summary -----------------------------------------------------


@mcp.prompt(
    name="pr_review_summary",
    description=(
        "Given PR title/description and optional diffs/commits, "
        "produce a reviewer-oriented summary."
    ),
    tags=["review", "summary", "analysis", "pr"],
)
def pr_review_summary_prompt(
    title: Annotated[
        str,
        Field(description="Pull request title (short, single-line title)."),
    ],
    description: Annotated[
        str | None,
        Field(description="Optional PR description/body text to provide additional context."),
    ] = None,
    diffs: Annotated[
        str | None,
        Field(description="Optional unified diff/patch text for the PR changes."),
    ] = None,
    commits: Annotated[
        str | None,
        Field(description="Optional text listing the commits associated with the PR."),
    ] = None,
) -> list[dict[str, str]]:
    if not title or not title.strip():
        log.warning("pr_review_summary: empty title arg")
        raise ValueError("title argument is required and cannot be empty")
    log.info(
        "pr_review_summary: rendering",
        extra={
            "title_len": len(title),
            "has_description": bool(description),
            "has_diffs": bool(diffs),
            "has_commits": bool(commits),
        },
    )
    system = _system_header("Produce a reviewer-oriented PR summary")
    parts: list[str] = [f"Title: {title}"]
    if description:
        parts.append(f"Description:\n{description}")
    if commits:
        parts.append(f"Commits:\n{commits}")
    if diffs:
        parts.append(f"Diffs:\n{diffs}")
    user = (
        "Create a review-ready summary with: Overview, Changes, Risks, Testing ideas, "
        "Breaking changes (if any).\n\n" + "\n\n".join(parts)
    )
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    log.info("pr_review_summary: rendered", extra={"messages": len(msgs)})
    return msgs
