import subprocess

from ..mcp_app import mcp


def get_commit_diff(commit_hash: str, context_lines: int = 3) -> dict:
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

        diff_cmd = [
            "git",
            "show",
            f"-U{context_lines}",
            "--pretty=format:",
            commit_hash,
        ]
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)

        stats_cmd = ["git", "show", "--stat", "--pretty=format:", commit_hash]
        stats_result = subprocess.run(stats_cmd, capture_output=True, text=True, check=True)

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
def _tool_get_commit_diff(commit_hash: str, context_lines: int = 3):  # pragma: no cover
    return get_commit_diff(commit_hash=commit_hash, context_lines=context_lines)
