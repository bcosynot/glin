# Compatibility shim: the git tools have been split into a package under glin/git_tools/.
# Import and re-export everything to preserve the original public API.
# TODO: Remove this shim after downstream code migrates to submodules.

from .git_tools import *  # noqa: F401,F403


@mcp.tool(
    name="get_branch_commits",
    description=(
        "Get recent commits for a specific branch filtered by configured tracked emails. "
        "Returns the same structure as get_recent_commits."
    ),
)
def _tool_get_branch_commits(branch: str, count: int = 10) -> list[dict]:  # pragma: no cover
    return get_branch_commits(branch=branch, count=count)  # type: ignore[return-value]
