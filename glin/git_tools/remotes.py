import subprocess
from typing import TypedDict, TypedDict as _TypedDict  # noqa: F401

from ..mcp_app import mcp
from .utils import chdir


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
from .utils import chdir

def _tool_get_remote_origin(path: str | None = None) -> RemoteInfo:  # pragma: no cover
    with chdir(path):
        return get_remote_origin()


class CommitUrlPrefixResult(TypedDict, total=False):
    prefix: str
    error: str


def determine_commit_url_prefix(remote_url: str | None) -> CommitUrlPrefixResult:
    """
    Given a Git remote URL, derive the HTTPS commit URL prefix for common hosts.

    Supported providers and their commit URL patterns:
    - GitHub:    https://<host>/<owner>/<repo>/commit/
    - GitLab:    https://<host>/<owner>/<repo>/-/commit/
    - Bitbucket: https://<host>/<owner>/<repo>/commits/

    Returns {"prefix": "..."} or {"error": "..."} when unknown or unparseable.
    """
    if not remote_url:
        return {"error": "remote_url is required"}

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
            return {"error": "Unrecognized remote URL format"}

        if not host or not path:
            return {"error": "Remote URL missing host or path"}

        # Normalize path: drop leading slashes and trailing .git
        path = path.lstrip("/")
        if path.endswith(".git"):
            path = path[:-4]

        # In practice, we expect owner/repo; if more segments exist, keep them as-is.
        base = f"https://{host}/{path}"
        host_l = host.lower()
        if host_l == "github.com" or "github." in host_l:
            return {"prefix": base + "/commit/"}
        if host_l == "gitlab.com" or "gitlab." in host_l:
            return {"prefix": base + "/-/commit/"}
        if host_l == "bitbucket.org" or "bitbucket." in host_l:
            return {"prefix": base + "/commits/"}
        return {"error": "Unknown host for commit URL prefix"}
    except Exception as e:  # pragma: no cover - be defensive in tool
        return {"error": f"Failed to parse remote URL: {str(e)}"}


@mcp.tool(
    name="determine_commit_url_prefix",
    description=(
        "Given a Git remote URL (HTTPS or SSH), return the web commit URL prefix to link a "
        "commit hash. For example, returns 'https://host/owner/repo/commit/' for GitHub."
    ),
)
def _tool_determine_commit_url_prefix(
    remote_url: str | None,
) -> CommitUrlPrefixResult:  # pragma: no cover
    return determine_commit_url_prefix(remote_url)
