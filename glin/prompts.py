"""
Server-side prompt templates for LLM use via FastMCP Prompts API.

These prompts do not call any LLMs. They return message sequences
that a client LLM can use to produce summaries and reports.

Clients can discover these with `list_prompts()` and render with
`get_prompt(name, args)` when using a FastMCP client.
"""

from typing import TypedDict

from fastmcp.utilities.logging import get_logger  # type: ignore

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


def _determine_commit_url_prefix(remote_url: str | None) -> str:
    """
    Given a Git remote URL, derive the HTTPS commit URL prefix for common hosts.

    Supported providers and their commit URL patterns:
    - GitHub:    https://<host>/<owner>/<repo>/commit/
    - GitLab:    https://<host>/<owner>/<repo>/-/commit/
    - Bitbucket: https://<host>/<owner>/<repo>/commits/

    Returns an empty string when the URL cannot be parsed or the host is unknown.
    """
    if not remote_url:
        return ""

    url = remote_url.strip()
    host: str | None = None
    path: str | None = None

    try:
        # SSH formats
        # - git@host:owner/repo.git
        # - ssh://git@host/owner/repo.git
        if url.startswith("ssh://"):
            rest = url.split("://", 1)[1]
            # Remove optional user@
            if "@" in rest:
                rest = rest.split("@", 1)[1]
            if "/" in rest:
                host, path = rest.split("/", 1)
        elif "@" in url and ":" in url and url.split("@", 1)[0].isidentifier():
            # Likely git@host:owner/repo.git (simple heuristic)
            user_host, path = url.split(":", 1)
            host = user_host.split("@", 1)[1]
        # HTTPS/HTTP format: https://host/owner/repo(.git)
        elif url.startswith("http://") or url.startswith("https://"):
            rest = url.split("://", 1)[1]
            if "/" in rest:
                host, path = rest.split("/", 1)
        else:
            return ""

        if not host or not path:
            return ""

        # Normalize path: drop leading slashes and trailing .git
        path = path.lstrip("/")
        if path.endswith(".git"):
            path = path[:-4]

        # In practice, we expect owner/repo; if more segments exist, keep them as-is.
        base = f"https://{host}/{path}"
        host_l = host.lower()
        if host_l == "github.com" or "github." in host_l:
            return base + "/commit/"
        if host_l == "gitlab.com" or "gitlab." in host_l:
            return base + "/-/commit/"
        if host_l == "bitbucket.org" or "bitbucket." in host_l:
            return base + "/commits/"
        return ""
    except Exception:  # pragma: no cover - be defensive in prompts layer
        return ""


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
def diff_summary_prompt(diff: str, context: str | None = None):
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
        "Generate a concise worklog entry for a given date or period. If tool-calling is available, "
        "fetch Git commits for that window using the 'get_commits_by_date' MCP tool and incorporate "
        "a brief commit summary, then combine with any provided notes. "
        "This prompt accepts an optional 'remote_url' parameter; you can retrieve it via the 'get_remote_origin' MCP tool."
    ),
    tags=["worklog", "summary", "daily", "git", "commits"],
)
def worklog_entry_prompt(date: str, inputs: str | None = None, remote_url: str | None = None):
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
    commit_url_prefix = _determine_commit_url_prefix(remote_url)
    user = (
        f"Create a worklog entry for the period: {date}. "
        "If you can call MCP tools, first fetch Git commits for this period using the 'get_commits_by_date' tool.\n"
        "Guidance for deriving since/until from the period string:\n"
        "- Single day 'YYYY-MM-DD' → since='YYYY-MM-DD', until='YYYY-MM-DD 23:59:59'.\n"
        "- Range 'YYYY-MM-DD..YYYY-MM-DD' → since=start, until=end '23:59:59'.\n"
        "- Relative periods (e.g., 'yesterday', 'last 2 days', '1 week ago') → since=expression, until='now'.\n"
        f"- Link to the commit hash to its respective commit page using this commit URL prefix: {commit_url_prefix}\n"
        "Then summarize the commits (group by theme, type/scope, note merges/PRs, issue keys, include counts if present) and combine with any notes below.\n"
        "Output sections: Highlights, Details, Next. Keep it under 12 bullets total. Use ISO dates. If there are no commits, say so.\n\n"
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
    title: str,
    description: str | None = None,
    diffs: str | None = None,
    commits: str | None = None,
):
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
