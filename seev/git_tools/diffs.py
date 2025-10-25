import subprocess
from typing import Annotated

from pydantic import Field

from ..mcp_app import mcp
from .utils import resolve_repo_root, run_git


def get_commit_diff(commit_hash: str, context_lines: int = 3, workdir: str | None = None) -> dict:
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return {"error": root_res["error"]}
            repo_root = root_res.get("path")

        metadata_args = ["show", "--no-patch", "--pretty=format:%H|%an|%ae|%ai|%s", commit_hash]
        metadata_result = run_git(metadata_args, repo_root=repo_root)
        if not metadata_result.stdout.strip():
            return {"error": f"Commit {commit_hash} not found"}
        hash, author, email, date, message = metadata_result.stdout.strip().split("|", 4)

        diff_args = ["show", f"-U{context_lines}", "--pretty=format:", commit_hash]
        diff_result = run_git(diff_args, repo_root=repo_root)

        stats_args = ["show", "--stat", "--pretty=format:", commit_hash]
        stats_result = run_git(stats_args, repo_root=repo_root)

        return {
            "hash": hash,
            "author": author,
            "email": email,
            "date": date,
            "message": message,
            "diff": diff_result.stdout.strip(),
            "stats": stats_result.stdout.strip(),
        }
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return {"error": f"Git command failed: {e.stderr}"}
    except ValueError as e:  # noqa: BLE001
        return {"error": f"Failed to parse commit metadata: {str(e)}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to get commit diff: {str(e)}"}


@mcp.tool(
    name="get_commit_diff",
    description=(
        "Get the diff (code changes) for a specific commit. Returns commit metadata along with the "
        "full diff and file statistics. Optionally specify the number of context lines around changes."
    ),
)
def _tool_get_commit_diff(
    commit_hash: str,
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
    context_lines: int = 3,
):  # pragma: no cover
    if not workdir:
        return {
            "error": (
                "Parameter 'workdir' is required. Provide a path inside the target Git repository "
                "so the server can execute git commands with '-C <root>'."
            )
        }
    return get_commit_diff(commit_hash=commit_hash, context_lines=context_lines, workdir=workdir)
