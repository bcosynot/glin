import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

DEFAULT_DB_PATH = "~/.glin/db.sqlite3"

# Types for status
from typing import TypedDict


class DBTableCount(TypedDict):
    table: str
    rows: int


class DBStatus(TypedDict):
    path: str
    schema_version: int
    tables: list[DBTableCount]
    ok: bool


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a sqlite3 connection with sensible defaults, ensuring migrations are applied.

    - Ensures parent directory exists when a filesystem path is used.
    - Expands user home (e.g., `~`) before connecting to avoid creating a literal `~` file.
    - Sets row factory to sqlite3.Row for dict-like access.
    - Enables foreign keys.
    - Ensures the database schema is initialized and up-to-date before use.
    """

    path = db_path or DEFAULT_DB_PATH
    if path == ":memory:":
        # In-memory database must be migrated on this very connection
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        migrate_conn(conn)
        return conn
    else:
        # Expand `~` and ensure parent directory exists before connecting
        full_path = Path(path).expanduser()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        # Open connection and migrate on it to avoid double opens
        conn = sqlite3.connect(str(full_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        migrate_conn(conn)
        return conn


# --- Migration machinery ----------------------------------------------------

MigrationFn = Callable[[sqlite3.Connection], None]


def _create_schema_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_version INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    # Ensure a single row exists; if table was empty, insert version 0
    row = conn.execute("SELECT current_version FROM schema_version WHERE id = 1").fetchone()
    if row is None:
        now = _now()
        conn.execute(
            "INSERT INTO schema_version (id, current_version, updated_at) VALUES (1, ?, ?)",
            (0, now),
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _mig_1(conn: sqlite3.Connection) -> None:
    """Migration V1: primary tables and indices for conversations and commits."""

    # Conversations and messages
    conn.executescript(
        """
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_messages_conversation ON messages(conversation_id);
        CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);

        -- Commits and files
        CREATE TABLE commits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sha TEXT NOT NULL UNIQUE,
            author_email TEXT,
            author_name TEXT,
            author_date TEXT NOT NULL,
            message TEXT NOT NULL,
            insertions INTEGER NOT NULL DEFAULT 0,
            deletions INTEGER NOT NULL DEFAULT 0,
            files_changed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX idx_commits_sha ON commits(sha);
        CREATE INDEX idx_commits_author_date ON commits(author_date);

        CREATE TABLE commit_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            status TEXT CHECK (status IN ('added','modified','deleted','renamed')),
            additions INTEGER NOT NULL DEFAULT 0,
            deletions INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE,
            UNIQUE(commit_id, file_path)
        );

        CREATE INDEX idx_commit_files_commit ON commit_files(commit_id);
        """
    )


def _mig_2(conn: sqlite3.Connection) -> None:
    """Migration V2: Add commit-conversation linking table and indices."""
    conn.executescript(
        """
        CREATE TABLE commit_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_sha TEXT NOT NULL,
            conversation_id INTEGER NOT NULL,
            relevance_score REAL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            UNIQUE(commit_sha, conversation_id)
        );

        CREATE INDEX idx_commit_conversations_sha ON commit_conversations(commit_sha);
        CREATE INDEX idx_commit_conversations_conv ON commit_conversations(conversation_id);
        """
    )


MIGRATIONS: dict[int, MigrationFn] = {
    1: _mig_1,
    2: _mig_2,
}


def _get_current_version(conn: sqlite3.Connection) -> int:
    _create_schema_version_table(conn)
    row = conn.execute("SELECT current_version FROM schema_version WHERE id = 1").fetchone()
    assert row is not None
    return int(row[0])


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "UPDATE schema_version SET current_version = ?, updated_at = ? WHERE id = 1",
        (version, _now()),
    )


def migrate_conn(conn: sqlite3.Connection, target: int | None = None) -> int:
    """Run pending migrations on an existing connection up to ``target`` (or latest).

    Returns the new/current schema version. Idempotent and safe to call multiple times.
    """

    cur = _get_current_version(conn)
    latest = max(MIGRATIONS) if MIGRATIONS else 0
    goal = target if target is not None else latest
    if goal < cur:
        # We don't support down-migrations in this simple system.
        return cur
    for v in range(cur + 1, goal + 1):
        fn = MIGRATIONS.get(v)
        if fn is None:
            raise RuntimeError(f"Missing migration {v}")
        fn(conn)
        _set_version(conn, v)
    conn.commit()
    return _get_current_version(conn)


def migrate(db_path: str | None = None, target: int | None = None) -> int:
    """Run pending migrations up to target version (or latest) and return new version.

    This function is idempotent and safe to call multiple times.
    """

    # Use a raw connection here to avoid recursion with get_connection().
    path = db_path or DEFAULT_DB_PATH
    if path == ":memory:":
        conn = sqlite3.connect(path)
    else:
        full_path = Path(path).expanduser()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(full_path))
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return migrate_conn(conn, target)
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> int:
    """Ensure the database exists and is migrated to the latest version.

    Returns the schema version after initialization.
    """

    return migrate(db_path)


# --- Backups & Status ------------------------------------------------------


def create_backup(db_path: str | None = None, *, backups_root: str = ".glin/backups") -> Path:
    """Create a timestamped backup of the database file.

    The backup path pattern is backups_root/YYYYMMDD/HHMMSS/<db_filename>.
    Returns the full path to the copied backup file.
    """
    import shutil

    path = db_path or DEFAULT_DB_PATH
    src = Path(path).expanduser()
    if src.name == ":memory:":
        raise ValueError("Cannot back up an in-memory database")
    if not src.exists():
        # Ensure directory exists but nothing to copy; raise to surface misconfiguration
        raise FileNotFoundError(f"DB file not found: {src}")
    ts = time.gmtime()
    day = time.strftime("%Y%m%d", ts)
    hms = time.strftime("%H%M%S", ts)
    root = Path(backups_root) / day / hms
    root.mkdir(parents=True, exist_ok=True)
    dest = root / src.name
    shutil.copy2(src, dest)
    return dest


def get_db_status(db_path: str | None = None) -> DBStatus:
    """Return a status snapshot: path, schema version, and row counts per table."""
    path = db_path or DEFAULT_DB_PATH
    tables = [
        "schema_version",
        "conversations",
        "messages",
        "commits",
        "commit_files",
        "commit_conversations",
    ]
    counts: list[DBTableCount] = []
    schema_version = 0
    ok = True
    try:
        with get_connection(path) as conn:
            # version
            row = conn.execute("SELECT current_version FROM schema_version WHERE id = 1").fetchone()
            schema_version = int(row[0]) if row else 0
            for t in tables:
                try:
                    c = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                    counts.append({"table": t, "rows": int(c[0]) if c else 0})
                except Exception:
                    counts.append({"table": t, "rows": 0})
                    ok = False
    except Exception:
        ok = False
    return DBStatus(
        path=str(Path(path).expanduser()), schema_version=schema_version, tables=counts, ok=ok
    )
