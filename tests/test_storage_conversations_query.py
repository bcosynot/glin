from seev.storage import conversations as conv, db as sdb


def test_query_conversations_basic_filters(tmp_path):
    db_file = tmp_path / "conv.sqlite3"
    sdb.init_db(str(db_file))

    # Create conversations
    a = conv.add_conversation("Alpha", db_path=str(db_file))
    b = conv.add_conversation("Beta story", db_path=str(db_file))
    c = conv.add_conversation("Gamma Beta", db_path=str(db_file))

    # Pin timestamps to deterministic values
    with sdb.get_connection(str(db_file)) as conn:
        conn.execute(
            "UPDATE conversations SET created_at=?, updated_at=? WHERE id=?",
            ("2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", a),
        )
        conn.execute(
            "UPDATE conversations SET created_at=?, updated_at=? WHERE id=?",
            ("2025-01-02T00:00:00Z", "2025-01-02T00:00:00Z", b),
        )
        conn.execute(
            "UPDATE conversations SET created_at=?, updated_at=? WHERE id=?",
            ("2025-01-03T00:00:00Z", "2025-01-03T00:00:00Z", c),
        )

    # Title substring filter (case-insensitive LIKE via SQLite default)
    betas = conv.query_conversations({"title_contains": "Beta"}, db_path=str(db_file))
    titles = [x.get("title", "") for x in betas]
    assert titles == ["Gamma Beta", "Beta story"]  # default order: updated_at DESC

    # ID filter and ordering ASC
    some = conv.query_conversations(
        {"ids": [a, c], "order": "asc", "order_by": "id"}, db_path=str(db_file)
    )
    assert [x["id"] for x in some] == [a, c]

    # Date range filter on updated_from
    recent = conv.query_conversations(
        {"updated_from": "2025-01-02T00:00:00Z"}, db_path=str(db_file)
    )
    assert [x["id"] for x in recent] == [c, b]

    # Limit/offset
    page1 = conv.query_conversations({"limit": 1}, db_path=str(db_file))
    page2 = conv.query_conversations({"limit": 1, "offset": 1}, db_path=str(db_file))
    assert page1[0]["id"] != page2[0]["id"]
