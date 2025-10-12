import subprocess
from typing import TypedDict

from ..mcp_app import mcp


class RemoteInfo(TypedDict, total=False):
    name: str
    url: str
    error: str


def get_remote_origin() -> RemoteInfo:
    """
    Return information about the remote named 'origin' for the current repository.

    On success: {"name": "origin", "url": "..."}
    On failure: {"error": "..."}
    """
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
        )
        url = (res.stdout or "").strip()
        if not url:
            return {"error": "Remote 'origin' has no URL configured"}
        return {"name": "origin", "url": url}
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        # Git returns non-zero if origin does not exist or repo is not a git repo
        err = (e.stderr or "").strip() or (e.stdout or "").strip()
        if not err:
            err = "Git command failed"
        return {"error": err}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to get remote origin: {str(e)}"}


@mcp.tool(
    name="get_remote_origin",
    description=(
        "Get the current repository's remote named 'origin' (if configured). Returns its URL or an error."
    ),
)
def _tool_get_remote_origin() -> RemoteInfo:  # pragma: no cover
    return get_remote_origin()
