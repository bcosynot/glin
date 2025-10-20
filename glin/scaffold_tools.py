import os
from pathlib import Path
from typing import TypedDict

from .mcp_app import mcp
from .storage.db import get_db_status, init_db


class InitGlinSuccess(TypedDict):
    ok: bool
    dir: str
    created: bool
    worklog_path: str
    db_path: str
    toml_path: str
    schema_version: int | None
    message: str


class InitGlinError(TypedDict):
    error: str
    dir: str
    missing: list[str] | None


def _write_toml(toml_path: Path, *, db_path: Path, markdown_path: Path) -> None:
    """Write a minimal glin.toml with db_path and markdown_path configured.

    We intentionally do not overwrite an existing file in the scaffold path; the caller
    should only invoke this when creating a fresh workspace.
    """
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# Glin Configuration\n"
        "# Managed by init_glin tool. You can edit values as needed.\n"
        f'db_path = "{str(db_path)}"\n'
        f'markdown_path = "{str(markdown_path)}"\n'
        "# Optionally, set tracked emails (highest priority remains GLIN_TRACK_EMAILS env var):\n"
        "# track_emails = [\n"
        '#   "user1@example.com",\n'
        '#   "user2@example.com",\n'
        "# ]\n"
    )
    toml_path.write_text(content, encoding="utf-8")


def _ensure_file(path: Path, *, initial_text: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(initial_text or "", encoding="utf-8")


@mcp.tool(
    name="init_glin",
    description=(
        "Initialize a directory to hold WORKLOG.md, SQLite DB, and glin.toml. "
        "If the directory exists and already contains those files, returns a helpful message. "
        "If the directory exists but is missing any of the files, returns an error. "
        "If the directory does not exist, creates it and scaffolds required files."
    ),
)
async def init_glin(path: str) -> InitGlinSuccess | InitGlinError:
    """Scaffold a Glin workspace directory.

    Args:
        path: Target directory path (absolute, or relative to current working directory). May include '~'.

    Returns:
        Success dict with created flag and file paths, or an error dict when pre-existing
        directory is missing required files.
    """
    try:
        if not path or not str(path).strip():
            return InitGlinError(
                error="path is required and cannot be empty",
                dir=str(Path.cwd()),
                missing=None,
            )

        base = Path(os.path.expanduser(path))
        if not base.is_absolute():
            base = Path.cwd() / base

        worklog_path = base / "WORKLOG.md"
        db_path = base / "db.sqlite3"
        # Compute XDG config path for glin.toml
        xdg_toml_path = Path.home() / ".config" / "glin" / "glin.toml"

        if base.exists():
            missing: list[str] = []
            if not worklog_path.exists():
                missing.append("WORKLOG.md")
            if not db_path.exists():
                missing.append("db.sqlite3")

            if missing:
                return InitGlinError(
                    error=(
                        "Directory exists but is not initialized. Missing: " + ", ".join(missing)
                    ),
                    dir=str(base),
                    missing=missing,
                )

            # Already initialized — return status without modifying files
            schema_version: int | None
            try:
                status = get_db_status(str(db_path))
                schema_version = int(status.get("schema_version", 0))
            except Exception:
                schema_version = None

            return InitGlinSuccess(
                ok=True,
                dir=str(base),
                created=False,
                worklog_path=str(worklog_path),
                db_path=str(db_path),
                toml_path=str(xdg_toml_path),
                schema_version=schema_version,
                message="Workspace already initialized.",
            )

        # Create directory and scaffold files
        base.mkdir(parents=True, exist_ok=True)

        # Create WORKLOG.md with a simple intro comment
        _ensure_file(
            worklog_path,
            initial_text=(
                "# Worklog\n\n"
                "# This file is managed by Glin tools. You can append entries using MCP.\n\n"
            ),
        )

        # Initialize the SQLite DB at the chosen path (creates file + schema)
        init_db(str(db_path))

        # Create glin.toml in XDG config path pointing to these files
        _write_toml(xdg_toml_path, db_path=db_path, markdown_path=worklog_path)

        # Gather DB schema version
        try:
            status = get_db_status(str(db_path))
            schema_version2 = int(status.get("schema_version", 0))
        except Exception:
            schema_version2 = None

        return InitGlinSuccess(
            ok=True,
            dir=str(base),
            created=True,
            worklog_path=str(worklog_path),
            db_path=str(db_path),
            toml_path=str(xdg_toml_path),
            schema_version=schema_version2,
            message="Workspace created and initialized.",
        )

    except Exception as e:
        return InitGlinError(
            error=f"Failed to scaffold workspace: {e}", dir=str(path), missing=None
        )
