import subprocess
from typing import TypedDict

from ..mcp_app import mcp


class FileChange(TypedDict):
    path: str
    status: str
    additions: int
    deletions: int
    old_path: str | None


def get_commit_files(commit_hash: str):
    try:
        metadata_cmd = [
            "git",
            "show",
            "--no-patch",
            "--pretty=format:%H|%an|%ae|%ai|%s",
            commit_hash,
        ]
        metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, check=True)
        if not metadata_result.stdout.strip():
            return {"error": f"Commit {commit_hash} not found"}
        hash, author, email, date, message = metadata_result.stdout.strip().split("|", 4)

        status_cmd = ["git", "show", "--name-status", "--pretty=format:", commit_hash]
        status_result = subprocess.run(status_cmd, capture_output=True, text=True, check=True)

        numstat_cmd = ["git", "show", "--numstat", "--pretty=format:", commit_hash]
        numstat_result = subprocess.run(numstat_cmd, capture_output=True, text=True, check=True)

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
        return {"error": f"Git command failed: {e.stderr}"}
    except ValueError as e:  # noqa: BLE001
        return {"error": f"Failed to parse commit metadata: {str(e)}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to get commit files: {str(e)}"}


@mcp.tool(
    name="get_commit_files",
    description=(
        "Get the list of files changed in a specific commit with detailed statistics. Returns commit "
        "metadata along with a list of files showing their status and line counts."
    ),
)
def _tool_get_commit_files(commit_hash: str):  # pragma: no cover
    return get_commit_files(commit_hash=commit_hash)
