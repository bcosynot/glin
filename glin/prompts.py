"""
Server-side prompt templates for LLM use via FastMCP Prompts API.

These prompts do not call any LLMs. They return message sequences
that a client LLM can use to produce summaries and reports.

Clients can discover these with `list_prompts()` and render with
`get_prompt(name, args)` when using a FastMCP client.
"""

from typing import TypedDict

from .mcp_app import mcp


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
def commit_summary_prompt(commits: str, date_range: str | None = None):
    if not commits or not commits.strip():
        raise ValueError("commits argument is required and cannot be empty")
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
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# --- Diff summary ----------------------------------------------------------


@mcp.prompt(
    name="diff_summary",
    description="Summarize a unified diff or patch into human-readable changes and risk areas.",
    tags=["summary", "analysis", "git", "diff"],
)
def diff_summary_prompt(diff: str, context: str | None = None):
    if not diff or not diff.strip():
        raise ValueError("diff argument is required and cannot be empty")
    system = _system_header("Summarize a code diff and identify impacts")
    ctx = f"Context: {context}\n\n" if context else ""
    user = (
        ctx + "Summarize the diff below. Provide: (1) high-level overview, (2) key modules/files, "
        "(3) notable API/behavior changes, (4) risks and test ideas.\n\n"
        "<DIFF>\n" + diff + "\n</DIFF>"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# --- Worklog entry builder -------------------------------------------------


@mcp.prompt(
    name="worklog_entry",
    description=(
        "Generate a concise worklog entry for a given date from commits, diffs, or notes."
    ),
    tags=["worklog", "summary", "daily"],
)
def worklog_entry_prompt(date: str, inputs: str):
    if not date or not date.strip():
        raise ValueError("date argument is required and cannot be empty")
    if not inputs or not inputs.strip():
        raise ValueError("inputs argument is required and cannot be empty")
    system = _system_header("Create a daily engineering worklog entry")
    user = (
        f"Create a worklog entry for {date}. Include sections: Highlights, Details, Next. "
        "Keep it under 12 bullets total.\n\n"
        "<INPUTS>\n" + inputs + "\n</INPUTS>"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


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
    title: str,
    description: str | None = None,
    diffs: str | None = None,
    commits: str | None = None,
):
    if not title or not title.strip():
        raise ValueError("title argument is required and cannot be empty")
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
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
