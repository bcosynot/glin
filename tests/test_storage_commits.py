from glin.storage import commits as sc, db as sdb


def test_insert_and_get_commit_roundtrip(tmp_path):
    db_file = tmp_path / "commits.sqlite3"
    sdb.init_db(str(db_file))

    commit_id = sc.insert_commit(
        sha="abc123",
        author_email="dev@example.com",
        author_name="Dev",
        author_date="2025-10-09T12:00:00Z",
        message="Add feature X\n\nMore details...",
        insertions=10,
        deletions=2,
        files_changed=3,
        db_path=str(db_file),
    )
    assert commit_id > 0

    # Duplicate insert returns existing id
    commit_id2 = sc.insert_commit(
        sha="abc123",
        author_email="dev@example.com",
        author_name="Dev",
        author_date="2025-10-09T12:00:00Z",
        message="ignored",
        db_path=str(db_file),
    )
    assert commit_id2 == commit_id

    rec = sc.get_commit_by_sha("abc123", db_path=str(db_file))
    assert rec is not None
    assert rec["sha"] == "abc123"
    assert rec["insertions"] == 10
    assert rec["files_changed"] == 3

    summaries = sc.list_commits(limit=5, db_path=str(db_file))
    assert len(summaries) == 1
    s = summaries[0]
    assert s["sha"] == "abc123"
    assert s["author"] == "Dev"  # prefers author_name over email
    assert s["date"] == "2025-10-09T12:00:00Z"
    assert s["title"] == "Add feature X"
    assert s["stats"] == {"insertions": 10, "deletions": 2, "files": 3}
