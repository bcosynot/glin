from __future__ import annotations

import sys
from fastmcp import FastMCP

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
