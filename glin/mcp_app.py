import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
    mcp._prompts = []

# Wrap the underlying prompt decorator (if present) to also record registrations
if hasattr(mcp, "prompt") and callable(mcp.prompt):
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
    conversation_tools as _conversation_tools,  # noqa: F401
    git_tools as _git_tools,  # noqa: F401
    markdown_tools as _markdown_tools,  # noqa: F401
    prompts as _prompts,  # noqa: F401
    worklog_generator as _worklog_generator,  # noqa: F401  # register rich worklog tool
)

# Import storage tools (commit-conversation links) to register their MCP tools
from .storage import links as _storage_links  # noqa: F401


def _truthy(val: str | None) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _configure_logging_from_env() -> None:
    """Configure server-side logging based on environment variables.

    Env vars:
      - GLIN_LOG_PATH: File path for log output. If set, a file handler is attached.
      - GLIN_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.
      - GLIN_LOG_STDERR: If truthy (default), keep a stderr StreamHandler; set to 0 to disable.
      - GLIN_LOG_ROTATE: If truthy (default), use RotatingFileHandler; else plain FileHandler.
      - GLIN_LOG_MAX_BYTES: Max size per log file in bytes when rotating. Default: 5_242_880 (~5MB).
      - GLIN_LOG_BACKUPS: Number of rotated backups to keep. Default: 3.
    """
    path = os.getenv("GLIN_LOG_PATH")
    if not path:
        return

    try:
        p = Path(os.path.expanduser(path))
        p.parent.mkdir(parents=True, exist_ok=True)

        level_name = os.getenv("GLIN_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

        root = logging.getLogger()
        root.setLevel(level)

        # Avoid duplicate handlers for the same file if run() is called multiple times in tests.
        if any(getattr(h, "baseFilename", None) == str(p) for h in root.handlers):
            return

        rotate = _truthy(os.getenv("GLIN_LOG_ROTATE", "1"))
        if rotate:
            max_bytes = int(os.getenv("GLIN_LOG_MAX_BYTES", str(5_242_880)))
            backups = int(os.getenv("GLIN_LOG_BACKUPS", "3"))
            fh: logging.Handler = RotatingFileHandler(
                filename=str(p), maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
            )
        else:
            fh = logging.FileHandler(filename=str(p), encoding="utf-8")

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        fh.setFormatter(fmt)
        root.addHandler(fh)

        if _truthy(os.getenv("GLIN_LOG_STDERR", "1")):
            # Only add if no existing StreamHandler to stderr is present
            if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
                sh = logging.StreamHandler()
                sh.setFormatter(fmt)
                root.addHandler(sh)

        # Align package loggers with chosen level
        logging.getLogger("glin").setLevel(level)
        logging.getLogger("fastmcp").setLevel(level)

    except Exception as e:  # pragma: no cover - best-effort, non-fatal
        try:
            logging.basicConfig(level=logging.INFO)
            logging.getLogger(__name__).warning("Failed to configure GLIN_LOG_PATH: %s", e)
        except Exception:
            pass


def run(argv: list[str] | None = None) -> None:
    """
    Run the MCP server.

    If "--transport http" is present in argv, run with HTTP transport on port 8000
    to match the provided test_client. Otherwise, use the default transport.
    """
    # Configure server-side logging if requested by environment
    _configure_logging_from_env()

    args = argv if argv is not None else sys.argv
    if "--transport" in args and "http" in args:
        mcp.run(transport="http", port=8000)
    else:
        mcp.run()
