"""Seev package root.

This module avoids importing heavy submodules at import time to prevent side effects
when tools like mkdocstrings import the package for introspection.

Use `from seev.mcp_app import mcp, run` for direct access, or rely on the lazy
attributes provided here.
"""

__all__ = ["mcp", "run"]


def __getattr__(name: str):
    if name in {"mcp", "run"}:
        from .mcp_app import mcp as _mcp, run as _run  # local import to avoid side effects

        return {"mcp": _mcp, "run": _run}[name]
    raise AttributeError(f"module 'seev' has no attribute {name!r}")
