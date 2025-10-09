from __future__ import annotations

import sys

# Optional FastMCP import with fallback stub for test environments without dependency
try:
    from fastmcp import FastMCP  # type: ignore
except Exception:  # pragma: no cover - used only when fastmcp is unavailable
    class FastMCP:  # minimal stub to satisfy tests
        def __init__(self, *_args, **_kwargs) -> None:
            self._tools = []

        def tool(self, name: str, description: str):  # noqa: D401 - signature matches usage
            def decorator(func):
                # store metadata for potential inspection; no-op in tests
                self._tools.append((name, description, func))
                return func

            return decorator

        def run(self, *args, **kwargs):  # noqa: D401 - compatibility no-op
            return None

# Single shared MCP instance used by all tool modules
mcp = FastMCP("Glin - Your worklog, without the work")

# Import tool modules to register their tools on the shared MCP instance
# These imports are intentionally placed after `mcp` is created
# so that decorators can attach to the same instance at import time.
from . import git_tools as _git_tools  # noqa: F401
from . import markdown_tools as _markdown_tools  # noqa: F401


def run(argv: list[str] | None = None) -> None:
    """
    Run the MCP server.

    If "--transport http" is present in argv, run with HTTP transport on port 8000
    to match the provided test_client. Otherwise, use the default transport.
    """
    args = argv if argv is not None else sys.argv
    if "--transport" in args and "http" in args:
        mcp.run(transport="http", port=8000)
    else:
        mcp.run()
