import sys

# Optional FastMCP import with fallback stub for test environments without dependency
try:
    from fastmcp import FastMCP  # type: ignore
except Exception:  # pragma: no cover - used only when fastmcp is unavailable

    class FastMCP:  # minimal stub to satisfy tests
        def __init__(self, *_args, **_kwargs) -> None:
            self._tools = []
            self._prompts = []

        def tool(self, name: str, description: str):  # noqa: D401 - signature matches usage
            def decorator(func):
                # store metadata for potential inspection; no-op in tests
                self._tools.append({"name": name, "description": description, "func": func})
                return func

            return decorator

        def prompt(self, name: str, description: str, **_kwargs):
            """Register a prompt in test environments without fastmcp installed.

            The real FastMCP exposes a similar decorator; this stub captures enough
            to let tests discover prompts and call their render function.
            """
            def decorator(func):
                # Store minimal metadata for tests
                self._prompts.append(
                    {
                        "name": name,
                        "description": description,
                        "func": func,
                    }
                )
                return func

            return decorator

        def run(self, *args, **kwargs):  # noqa: D401 - compatibility no-op
            return None


# Single shared MCP instance used by all tool modules
mcp = FastMCP("Glin - Your worklog, without the work")

# Ensure we can introspect prompts during tests even if fastmcp is installed
if not hasattr(mcp, "_prompts"):
    setattr(mcp, "_prompts", [])

# Wrap the underlying prompt decorator (if present) to also record registrations
if hasattr(mcp, "prompt") and callable(getattr(mcp, "prompt")):
    _orig_prompt = mcp.prompt  # type: ignore[attr-defined]

    def _prompt_wrapper(*args, **kwargs):  # type: ignore[no-redef]
        # Extract metadata if passed by name
        name = None
        description = None
        if args and isinstance(args[0], str):
            name = args[0]
        name = kwargs.get("name", name)
        description = kwargs.get("description", description)

        dec = _orig_prompt(*args, **kwargs)

        def decorator(func):
            try:
                mcp._prompts.append({"name": name, "description": description, "func": func})
            except Exception:
                pass
            return dec(func)

        return decorator

    mcp.prompt = _prompt_wrapper  # type: ignore[assignment]

# Import tool modules to register their tools on the shared MCP instance
# These imports are intentionally placed after `mcp` is created
# so that decorators can attach to the same instance at import time.
from . import (
    git_tools as _git_tools,  # noqa: F401
    markdown_tools as _markdown_tools,  # noqa: F401
    prompts as _prompts,  # noqa: F401
)


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
