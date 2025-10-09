from __future__ import annotations

from .db import get_connection
from .types import CommitRecord, CommitSummary


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
