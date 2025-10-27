import re
import subprocess
from collections import defaultdict
from typing import Annotated, TypedDict

from pydantic import Field

from ..mcp_app import mcp
from .utils import resolve_repo_root, run_git


class ErrorResponse(TypedDict):
    error: str


def _err(msg: str) -> ErrorResponse:
    return {"error": msg}


class MergeInfo(TypedDict, total=False):
    hash: str
    parents: list[str]
    is_merge: bool
    is_pr_merge: bool
    pr_number: int | None
    message: str


class CommitStats(TypedDict):
    hash: str
    additions: int
    deletions: int
    files_changed: int
    by_language: dict[
        str, dict[str, int]
    ]  # {lang: {"additions": int, "deletions": int, "files": int}}


class Categorization(TypedDict, total=False):
    type: str
    scope: str | None
    description: str
    conventional: bool
    raw: str
    hash: str


_LANG_MAP = {
    # Common languages
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C/C++",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
}

_CONVENTIONAL_TYPES = {
    # Standard Conventional Commit types
    "feat",
    "fix",
    "chore",
    "refactor",
    "docs",
    "test",
    "perf",
    "build",
    "ci",
    "style",
    "revert",
    # Extended types requested by users/teams (accept case-insensitively)
    "added",
    "updated",
    "fixed",
    "refactored",
    "task",
    "wip",
    "debugging",
    "bugfix",
    "investigating",
    "investigation",
}


def _get_commit_message(commit_hash: str, workdir: str | None = None) -> str:
    repo_root: str | None = None
    if workdir is not None:
        root_res = resolve_repo_root(workdir)
        if "error" in root_res:
            raise subprocess.CalledProcessError(2, ["git", "show"], root_res["error"])  # type: ignore[arg-type]
        repo_root = root_res.get("path")
    res = run_git(["show", "--no-patch", "--pretty=%s", commit_hash], repo_root=repo_root)
    return res.stdout.strip()


def detect_merge_info(commit_hash: str, workdir: str | None = None) -> MergeInfo | ErrorResponse:
    """Detect whether a commit is a merge, and whether it's a PR merge.

    Heuristics for PR merges:
    - Subject contains "Merge pull request #<n>" (GitHub)
    - Subject starts with "Merge branch" (generic) → not necessarily a PR
    - Two or more parents in `git rev-list --parents -n 1`
    """
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return _err(root_res["error"])
            repo_root = root_res.get("path")

        parents_res = run_git(
            ["rev-list", "--parents", "-n", "1", commit_hash], repo_root=repo_root
        )
        parts = parents_res.stdout.strip().split()
        if not parts:
            return _err(f"Commit {commit_hash} not found")
        _hash, *parents = parts
        message = _get_commit_message(commit_hash, workdir=workdir)

        is_merge = len(parents) >= 2
        pr_number: int | None = None
        is_pr_merge = False

        m = re.search(r"Merge pull request #(\d+)", message, flags=re.IGNORECASE)
        if m:
            pr_number = int(m.group(1))
            is_pr_merge = True
        elif is_merge and message.lower().startswith("merge branch"):
            is_pr_merge = False

        return {
            "hash": commit_hash,
            "parents": parents,
            "is_merge": is_merge,
            "is_pr_merge": is_pr_merge,
            "pr_number": pr_number,
            "message": message,
        }
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return _err(f"Git command failed: {e.stderr}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Failed to detect merge info: {str(e)}")


def get_commit_statistics(
    commit_hash: str, workdir: str | None = None
) -> CommitStats | ErrorResponse:
    """Aggregate simple statistics for a commit, including language breakdown.

    Uses `git show --numstat` and infers language from file extensions.
    """
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return _err(root_res["error"])
            repo_root = root_res.get("path")

        numstat = run_git(
            ["show", "--numstat", "--pretty=format:", commit_hash], repo_root=repo_root
        )
        additions = 0
        deletions = 0
        files_changed = 0
        lang_data: dict[str, dict[str, int]] = defaultdict(
            lambda: {"additions": 0, "deletions": 0, "files": 0}
        )

        for line in numstat.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            add_s, del_s, path = parts[0], parts[1], parts[2]
            add = 0 if add_s == "-" else int(add_s)
            delete = 0 if del_s == "-" else int(del_s)
            additions += add
            deletions += delete
            files_changed += 1

            lang = _infer_language(path)
            d = lang_data[lang]
            d["additions"] += add
            d["deletions"] += delete
            d["files"] += 1

        return {
            "hash": commit_hash,
            "additions": additions,
            "deletions": deletions,
            "files_changed": files_changed,
            "by_language": dict(lang_data),
        }
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return _err(f"Git command failed: {e.stderr}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Failed to compute commit statistics: {str(e)}")


def _infer_language(path: str) -> str:
    path_lower = path.lower()
    for ext, lang in _LANG_MAP.items():
        if path_lower.endswith(ext):
            return lang
    return "Other"


_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?P<bang>!)?(?:\((?P<scope>[^)]+)\))?:\s*(?P<desc>.+)",
    re.IGNORECASE,
)


def categorize_commit(
    message_or_hash: str, is_hash: bool = False, workdir: str | None = None
) -> Categorization | ErrorResponse:
    """Categorize a commit message using Conventional Commits.

    If is_hash=True, the argument is treated as a commit hash and its subject is resolved first.
    """
    try:
        raw = _get_commit_message(message_or_hash, workdir=workdir) if is_hash else message_or_hash
        m = _CONVENTIONAL_RE.match(raw)
        if not m:
            return {
                "type": "other",
                "scope": None,
                "description": raw,
                "conventional": False,
                "raw": raw,
                **({"hash": message_or_hash} if is_hash else {}),
            }
        ctype_raw = m.group("type")
        ctype = ctype_raw.lower()
        scope = m.group("scope")
        desc = m.group("desc")
        conventional = ctype in _CONVENTIONAL_TYPES
        return {
            "type": ctype,
            "scope": scope,
            "description": desc,
            "conventional": conventional,
            "raw": raw,
            **({"hash": message_or_hash} if is_hash else {}),
        }
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return _err(f"Git command failed: {e.stderr}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Failed to categorize commit: {str(e)}")


def blame_file(
    path: str,
    start_line: int = 1,
    end_line: int | None = None,
    rev: str = "HEAD",
    workdir: str | None = None,
) -> dict:
    """Run git blame on a file or a line range.

    Returns a structured list with commit, author, date and code for each line.
    """
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return _err(root_res["error"])
            repo_root = root_res.get("path")

        args = ["blame", rev, "--line-porcelain"]
        if end_line is not None:
            args += [f"-L{start_line},{end_line}"]
        elif start_line != 1:
            args += [f"-L{start_line},+999999"]
        args.append(path)
        res = run_git(args, repo_root=repo_root)
        lines = res.stdout.splitlines()

        entries: list[dict] = []
        cur: dict | None = None
        for ln in lines:
            if re.match(r"^[0-9a-f]{7,40} ", ln):
                # start of a block
                if cur:
                    entries.append(cur)
                parts = ln.split()
                cur = {
                    "commit": parts[0],
                    "orig_line": int(parts[2]) if len(parts) > 2 else None,
                    "final_line": int(parts[1]) if len(parts) > 1 else None,
                    "author": None,
                    "author_mail": None,
                    "author_time": None,
                    "summary": None,
                    "code": None,
                }
            elif ln.startswith("author ") and cur is not None:
                cur["author"] = ln[len("author ") :]
            elif ln.startswith("author-mail ") and cur is not None:
                cur["author_mail"] = ln[len("author-mail ") :].strip("<>")
            elif ln.startswith("author-time ") and cur is not None:
                cur["author_time"] = int(ln[len("author-time ") :])
            elif ln.startswith("summary ") and cur is not None:
                cur["summary"] = ln[len("summary ") :]
            elif ln.startswith("\t") and cur is not None:
                cur["code"] = ln[1:]
        if cur:
            entries.append(cur)
        return {"path": path, "rev": rev, "start": start_line, "end": end_line, "entries": entries}
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return _err(f"Git command failed: {e.stderr}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Failed to run git blame: {str(e)}")


# MCP tool registrations
@mcp.tool(
    name="detect_merge_info",
    description=(
        "Detect whether a commit is a merge and whether it looks like a PR merge. "
        "Returns parents, flags and PR number if available."
    ),
)
def _tool_detect_merge_info(
    commit_hash: str,
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory path. Git runs in the repository containing this path "
                "using 'git -C <root>', ensuring commands "
                "execute in the client's project repository "
                "rather than the server process CWD. The path must reside inside a Git repository."
            )
        ),
    ],
) -> MergeInfo | ErrorResponse:  # pragma: no cover
    if not workdir:
        return _err(
            "Parameter 'workdir' is required. Provide a path inside the target Git repository "
            "so the server can execute git commands with '-C <root>'."
        )
    return detect_merge_info(commit_hash=commit_hash, workdir=workdir)


@mcp.tool(
    name="get_commit_statistics",
    description=(
        "Get aggregate statistics for a commit (additions, deletions, files changed) "
        "with a simple language breakdown."
    ),
)
def _tool_get_commit_statistics(
    commit_hash: str,
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory path. Git runs in the repository containing this path "
                "using 'git -C <root>', ensuring commands "
                "execute in the client's project repository "
                "rather than the server process CWD. The path must reside inside a Git repository."
            )
        ),
    ],
) -> CommitStats | ErrorResponse:  # pragma: no cover
    if not workdir:
        return _err(
            "Parameter 'workdir' is required. Provide a path inside the target Git repository "
            "so the server can execute git commands with '-C <root>'."
        )
    return get_commit_statistics(commit_hash=commit_hash, workdir=workdir)


@mcp.tool(
    name="categorize_commit",
    description=(
        "Categorize a commit message per Conventional Commits. "
        "Pass a commit hash with is_hash=True to resolve subject from git."
    ),
)
def _tool_categorize_commit(
    message_or_hash: str,
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory path. Git runs in the repository containing this path "
                "using 'git -C <root>', ensuring commands "
                "execute in the client's project repository "
                "rather than the server process CWD. The path must reside inside a Git repository."
            )
        ),
    ],
    is_hash: bool = False,
) -> Categorization | ErrorResponse:  # pragma: no cover
    if not workdir:
        return _err(
            "Parameter 'workdir' is required. Provide a path inside the target Git repository "
            "so the server can execute git commands with '-C <root>'."
        )
    return categorize_commit(message_or_hash=message_or_hash, is_hash=is_hash, workdir=workdir)


@mcp.tool(
    name="git_blame",
    description=(
        "Run git blame on a file or range. Returns per-line commit, author, timestamp and code."
    ),
)
def _tool_git_blame(
    path: str,
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory path. Git runs in the repository containing this path "
                "using 'git -C <root>', ensuring commands "
                "execute in the client's project repository "
                "rather than the server process CWD. The path must reside inside a Git repository."
            )
        ),
    ],
    start_line: int = 1,
    end_line: int | None = None,
    rev: str = "HEAD",
):  # pragma: no cover
    if not workdir:
        return _err(
            "Parameter 'workdir' is required. Provide a path inside the target Git repository "
            "so the server can execute git commands with '-C <root>'."
        )
    return blame_file(path=path, start_line=start_line, end_line=end_line, rev=rev, workdir=workdir)
