import subprocess
from typing import Annotated, TypedDict

from pydantic import Field

from ..mcp_app import mcp
from .utils import resolve_repo_root, run_git


def get_current_branch(workdir: str | None = None) -> dict:
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return {"error": root_res["error"]}
            repo_root = root_res.get("path")

        name_res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root=repo_root)
        name = name_res.stdout.strip()
        detached = name == "HEAD"

        upstream = None
        try:
            up_res = run_git(
                ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
                repo_root=repo_root,
            )
            upstream = up_res.stdout.strip() or None
        except subprocess.CalledProcessError:
            upstream = None

        ahead = 0
        behind = 0
        if upstream:
            try:
                cnt = run_git(
                    ["rev-list", "--left-right", "--count", f"{name}...{upstream}"],
                    repo_root=repo_root,
                )
                left, right = cnt.stdout.strip().split()
                ahead = int(left)
                behind = int(right)
            except Exception:
                ahead, behind = 0, 0

        return {
            "name": name,
            "detached": detached,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
        }
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return {"error": f"Git command failed: {e.stderr}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to get current branch: {str(e)}"}


class BranchLastCommit(TypedDict, total=False):
    hash: str
    author: str
    email: str | None
    date: str
    message: str


class BranchEntry(TypedDict, total=False):
    name: str
    is_current: bool
    upstream: str | None
    ahead: int
    behind: int
    last_commit: BranchLastCommit | None
    error: str


def list_branches(workdir: str | None = None) -> list[BranchEntry]:
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return [{"error": root_res["error"]}]
            repo_root = root_res.get("path")

        fmt = "%(refname:short)|%(objectname)|%(upstream:short)|%(authorname)|%(authoremail)|%(authordate:iso8601)|%(subject)"
        res = run_git(["for-each-ref", f"--format={fmt}", "refs/heads"], repo_root=repo_root)
        branches: list[dict] = []

        cur_res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root=repo_root)
        current = cur_res.stdout.strip()

        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            name, commit_hash, upstream, author, email, date, subject = line.split("|", 6)
            upstream = upstream or None

            ahead = 0
            behind = 0
            if upstream:
                try:
                    cnt = run_git(
                        ["rev-list", "--left-right", "--count", f"{name}...{upstream}"],
                        repo_root=repo_root,
                    )
                    left, right = cnt.stdout.strip().split()
                    ahead = int(left)
                    behind = int(right)
                except Exception:
                    ahead, behind = 0, 0

            last_commit: dict | None = {
                "hash": commit_hash,
                "author": author,
                "email": email.strip("<>") if isinstance(email, str) else email,
                "date": date,
                "message": subject,
            }

            branches.append(
                {
                    "name": name,
                    "is_current": name == current,
                    "upstream": upstream,
                    "ahead": ahead,
                    "behind": behind,
                    "last_commit": last_commit,
                }
            )

        return branches
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return [{"error": f"Git command failed: {e.stderr}"}]
    except Exception as e:  # noqa: BLE001
        return [{"error": f"Failed to list branches: {str(e)}"}]


@mcp.tool(
    name="get_current_branch",
    description=(
        "Get the current git branch information, including whether HEAD is detached, the upstream (if any), and ahead/behind counts versus upstream."
    ),
)
def _tool_get_current_branch(
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory path. Git runs in the repository containing this path "
                "using 'git -C <root>', ensuring commands execute in the client's project repository "
                "rather than the server process CWD. The path must reside inside a Git repository."
            )
        ),
    ],
) -> dict:  # pragma: no cover
    if not workdir:
        return {
            "error": (
                "Parameter 'workdir' is required. Provide a path inside the target Git repository "
                "so the server can execute git commands with '-C <root>'."
            )
        }
    return get_current_branch(workdir=workdir)


@mcp.tool(
    name="list_branches",
    description=(
        "List local branches with upstream, ahead/behind counts, and last commit metadata. The current branch is marked in the response."
    ),
)
def _tool_list_branches(
    workdir: Annotated[
        str,
        Field(
            description=(
                "Required working directory path. Git runs in the repository containing this path "
                "using 'git -C <root>', ensuring commands execute in the client's project repository "
                "rather than the server process CWD. The path must reside inside a Git repository."
            )
        ),
    ],
) -> list[BranchEntry]:  # pragma: no cover
    if not workdir:
        return [
            {
                "error": (
                    "Parameter 'workdir' is required. Provide a path inside the target Git repository "
                    "so the server can execute git commands with '-C <root>'."
                )
            }
        ]
    return list_branches(workdir=workdir)  # type: ignore[return-value]
