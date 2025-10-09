import subprocess


def make_git_output(commits):
    # Helper to create git log-like lines
    return "\n".join(f"{c['hash']}|{c['author']}|{c['date']}|{c['message']}" for c in commits)


def test_default_no_db_autowrite(monkeypatch, tmp_path):
    # Ensure env flags are unset
    monkeypatch.delenv("GLIN_DB_AUTOWRITE", raising=False)
    monkeypatch.delenv("GLIN_DB_PATH", raising=False)
    # Configure tracked emails so git_tools runs
    monkeypatch.setenv("GLIN_TRACK_EMAILS", "dev@example.com")

    # Stub subprocess.run for git log
    commits = [
        {
            "hash": "abc",
            "author": "Dev",
            "date": "2025-10-09 12:00:00 +0000",
            "message": "Message",
        }
    ]

    def fake_run(cmd, capture_output, text, check):  # noqa: ARG001
        class R:
            stdout = make_git_output(commits)

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)

    calls = {"count": 0}

    def fake_bulk_upsert(payload, db_path=None):  # noqa: ARG001
        calls["count"] += 1
        return len(payload)

    # Monkeypatch bulk_upsert_commits; since import is local inside function we patch the module
    import glin.storage.commits as storage_commits

    monkeypatch.setattr(storage_commits, "bulk_upsert_commits", fake_bulk_upsert)

    from glin.git_tools.commits import get_recent_commits

    out = get_recent_commits(count=1)
    assert isinstance(out, list) and len(out) == 1
    # No autowrite since flag is off
    assert calls["count"] == 0


def test_db_autowrite_enabled(monkeypatch, tmp_path):
    db_file = tmp_path / "auto.sqlite3"
    # Turn on flag and path
    monkeypatch.setenv("GLIN_DB_AUTOWRITE", "1")
    monkeypatch.setenv("GLIN_DB_PATH", str(db_file))
    # Configure tracked emails so git_tools runs
    monkeypatch.setenv("GLIN_TRACK_EMAILS", "dev@example.com")

    commits = [
        {
            "hash": "def",
            "author": "Dev",
            "date": "2025-10-09 13:00:00 +0000",
            "message": "Other",
        }
    ]

    def fake_run(cmd, capture_output, text, check):  # noqa: ARG001
        class R:
            stdout = make_git_output(commits)

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)

    from glin.git_tools.commits import get_recent_commits
    from glin.storage import commits as sc, db as sdb

    # Ensure DB exists
    sdb.init_db(str(db_file))

    out = get_recent_commits(count=1)
    assert isinstance(out, list) and len(out) == 1

    # The commit should be persisted
    rec = sc.get_commit_by_sha("def", db_path=str(db_file))
    assert rec is not None
    assert rec["sha"] == "def"
