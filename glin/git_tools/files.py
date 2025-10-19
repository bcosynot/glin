import subprocess
from typing import Annotated, TypedDict

from pydantic import Field

from ..mcp_app import mcp
from .utils import resolve_repo_root, run_git


class ErrorResponse(TypedDict):
    error: str


def _err(msg: str) -> ErrorResponse:
    return {"error": msg}


class CommitFilesResult(TypedDict):
    hash: str
    author: str
    email: str
    date: str
    message: str
    files: list["FileChange"]
    total_additions: int
    total_deletions: int
    files_changed: int


class FileChange(TypedDict):
    path: str
    status: str
    additions: int
    deletions: int
    old_path: str | None


def get_commit_files(
    commit_hash: str, workdir: str | None = None
) -> CommitFilesResult | ErrorResponse:
    try:
        repo_root: str | None = None
        if workdir is not None:
            root_res = resolve_repo_root(workdir)
            if "error" in root_res:
                return _err(root_res["error"])
            repo_root = root_res.get("path")

        metadata_args = ["show", "--no-patch", "--pretty=format:%H|%an|%ae|%ai|%s", commit_hash]
        metadata_result = run_git(metadata_args, repo_root=repo_root)
        if not metadata_result.stdout.strip():
            return _err(f"Commit {commit_hash} not found")
        hash, author, email, date, message = metadata_result.stdout.strip().split("|", 4)

        status_args = ["show", "--name-status", "--pretty=format:", commit_hash]
        status_result = run_git(status_args, repo_root=repo_root)

        numstat_args = ["show", "--numstat", "--pretty=format:", commit_hash]
        numstat_result = run_git(numstat_args, repo_root=repo_root)

        status_map: dict[str, tuple[str, str | None]] = {}
        for line in status_result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                status = parts[0]
                if status.startswith(("R", "C")) and len(parts) == 3:
                    old_path = parts[1]
                    new_path = parts[2]
                    status_map[new_path] = (status[0], old_path)
                else:
                    path = parts[1]
                    status_map[path] = (status, None)

        files: list[FileChange] = []
        total_additions = 0
        total_deletions = 0

        for line in numstat_result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                additions_str, deletions_str, path = parts[0], parts[1], parts[2]
                additions = 0 if additions_str == "-" else int(additions_str)
                deletions = 0 if deletions_str == "-" else int(deletions_str)
                total_additions += additions
                total_deletions += deletions
                status, old_path = status_map.get(path, ("M", None))
                files.append(
                    {
                        "path": path,
                        "status": status,
                        "additions": additions,
                        "deletions": deletions,
                        "old_path": old_path,
                    }
                )

        return {
            "hash": hash,
            "author": author,
            "email": email,
            "date": date,
            "message": message,
            "files": files,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "files_changed": len(files),
        }
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        return _err(f"Git command failed: {e.stderr}")
    except ValueError as e:  # noqa: BLE001
        return _err(f"Failed to parse commit metadata: {str(e)}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Failed to get commit files: {str(e)}")


@mcp.tool(
    name="get_commit_files",
    description=(
        "Get the list of files changed in a specific commit with detailed statistics. Returns commit "
        "metadata along with a list of files showing their status and line counts."
    ),
)
def _tool_get_commit_files(
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
) -> CommitFilesResult | ErrorResponse:  # pragma: no cover
    if not workdir:
        return _err(
            "Parameter 'workdir' is required. Provide a path inside the target Git repository "
            "so the server can execute git commands with '-C <root>'."
        )
    return get_commit_files(commit_hash=commit_hash, workdir=workdir)
