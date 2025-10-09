from typing import Iterable, Sequence

from .db import get_connection
from .types import (
    CommitFileChange,
    CommitInput,
    CommitRecord,
    CommitSummary,
    ErrorResponse,
    GitCommitInfo,
    InfoResponse,
)


def upsert_commit(
    commit: CommitInput,
    *,
    files: list[CommitFileChange] | None = None,
    db_path: str | None = None,
) -> int:
    """Upsert a commit by sha and optionally upsert per-file changes.

    Returns the commit row id.
    """

    # Fill defaults
    insertions = int(commit.get("insertions", 0) or 0)
    deletions = int(commit.get("deletions", 0) or 0)
    files_changed = int(commit.get("files_changed", 0) or 0)

    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO commits (
                sha, author_email, author_name, author_date, message,
                insertions, deletions, files_changed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sha) DO UPDATE SET
                author_email=excluded.author_email,
                author_name=excluded.author_name,
                author_date=excluded.author_date,
                message=excluded.message,
                insertions=excluded.insertions,
                deletions=excluded.deletions,
                files_changed=excluded.files_changed
            """,
            (
                commit["sha"],
                commit.get("author_email", ""),
                commit.get("author_name", ""),
                commit["author_date"],
                commit.get("message", ""),
                insertions,
                deletions,
                files_changed,
            ),
        )
        # Retrieve id
        row = conn.execute("SELECT id FROM commits WHERE sha = ?", (commit["sha"],)).fetchone()
        commit_id = int(row[0]) if row else int(cur.lastrowid)

        # Upsert file changes if provided
        if files:
            for f in files:
                _upsert_commit_file(conn, commit_id, f)
        return commit_id


def bulk_upsert_commits(
    commits: Sequence[CommitInput] | Iterable[CommitInput],
    *,
    db_path: str | None = None,
) -> int:
    """Bulk upsert a sequence of commits.

    Each commit may include a "files" key with a list[CommitFileChange].
    Returns the number of commits processed.
    """

    count = 0
    with get_connection(db_path) as conn:
        for c in commits:
            files = c.get("files") if isinstance(c, dict) else None  # type: ignore[assignment]
            insertions = int(c.get("insertions", 0) or 0)
            deletions = int(c.get("deletions", 0) or 0)
            files_changed = int(c.get("files_changed", 0) or 0)
            conn.execute(
                """
                INSERT INTO commits (
                    sha, author_email, author_name, author_date, message,
                    insertions, deletions, files_changed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sha) DO UPDATE SET
                    author_email=excluded.author_email,
                    author_name=excluded.author_name,
                    author_date=excluded.author_date,
                    message=excluded.message,
                    insertions=excluded.insertions,
                    deletions=excluded.deletions,
                    files_changed=excluded.files_changed
                """,
                (
                    c["sha"],
                    c.get("author_email", ""),
                    c.get("author_name", ""),
                    c["author_date"],
                    c.get("message", ""),
                    insertions,
                    deletions,
                    files_changed,
                ),
            )
            row = conn.execute("SELECT id FROM commits WHERE sha = ?", (c["sha"],)).fetchone()
            commit_id = int(row[0])
            if isinstance(files, list) and files:
                for f in files:
                    _upsert_commit_file(conn, commit_id, f)
            count += 1
        conn.commit()
    return count


def query_commits_by_date(
    since: str,
    until: str = "now",
    *,
    authors: list[str] | None = None,
    db_path: str | None = None,
) -> list[GitCommitInfo | ErrorResponse | InfoResponse]:
    """Query commits by date range returning git_tools-compatible shapes.

    - since/until should be ISO 8601 date-times or dates acceptable to SQLite datetime().
    - authors, if provided, filters by author_name OR author_email LIKE any value.
    """

    base_sql = (
        "SELECT sha AS hash, COALESCE(author_name, author_email) AS author, "
        "author_date AS date, message FROM commits WHERE 1=1"
    )
    params: list[object] = []
    if since:
        base_sql += " AND author_date >= ?"
        params.append(since)
    if until:
        base_sql += " AND author_date <= ?"
        params.append(until)
    if authors:
        clauses = []
        for a in authors:
            clauses.append("(author_email LIKE ? OR author_name LIKE ?)")
            like = f"%{a}%"
            params.extend([like, like])
        base_sql += " AND (" + " OR ".join(clauses) + ")"
    base_sql += " ORDER BY author_date DESC"

    with get_connection(db_path) as conn:
        rows = conn.execute(base_sql, params).fetchall()
        if not rows:
            return [InfoResponse(info="No commits found in date range")]
        return [GitCommitInfo(hash=r[0], author=r[1] or "", date=r[2], message=r[3] or "") for r in rows]


# --- Helpers ---------------------------------------------------------------

def _upsert_commit_file(conn, commit_id: int, f: CommitFileChange) -> None:
    additions = int(f.get("additions", 0) or 0)
    deletions = int(f.get("deletions", 0) or 0)
    status = f.get("status")
    file_path = f["file_path"]
    conn.execute(
        """
        INSERT INTO commit_files (commit_id, file_path, status, additions, deletions)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(commit_id, file_path) DO UPDATE SET
            status=excluded.status,
            additions=excluded.additions,
            deletions=excluded.deletions
        """,
        (commit_id, file_path, status, additions, deletions),
    )


# Back-compat helpers kept for existing call sites

def insert_commit(
    *,
    sha: str,
    author_email: str,
    author_name: str,
    author_date: str,
    message: str,
    insertions: int = 0,
    deletions: int = 0,
    files_changed: int = 0,
    db_path: str | None = None,
) -> int:
    """Insert or ignore a commit; returns commit id.

    If a commit with the same SHA exists, returns its id.
    """

    with get_connection(db_path) as conn:
        # Try existing
        row = conn.execute("SELECT id FROM commits WHERE sha = ?", (sha,)).fetchone()
        if row:
            return int(row[0])
        cur = conn.execute(
            """
            INSERT INTO commits (
                sha, author_email, author_name, author_date, message,
                insertions, deletions, files_changed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sha,
                author_email,
                author_name,
                author_date,
                message,
                insertions,
                deletions,
                files_changed,
            ),
        )
        return int(cur.lastrowid)


def get_commit_by_sha(sha: str, db_path: str | None = None) -> CommitRecord | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM commits WHERE sha = ?", (sha,)).fetchone()
        return CommitRecord(**dict(row)) if row else None


def list_commits(limit: int = 100, db_path: str | None = None) -> list[CommitSummary]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT sha,
                   COALESCE(author_name, author_email) AS author,
                   author_date AS date,
                   substr(message, 1, instr(message || '\n', '\n') - 1) AS title,
                   insertions, deletions, files_changed AS files
            FROM commits
            ORDER BY author_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        summaries: list[CommitSummary] = []
        for r in rows:
            stats = {"insertions": int(r[4]), "deletions": int(r[5]), "files": int(r[6])}
            summaries.append(
                CommitSummary(sha=r[0], author=r[1], date=r[2], title=r[3] or "", stats=stats)
            )
        return summaries
