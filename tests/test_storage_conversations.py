from seev.storage import conversations as conv, db as sdb


def test_create_conversation_and_messages(tmp_path):
    db_file = tmp_path / "conv.sqlite3"
    sdb.init_db(str(db_file))

    cid = conv.create_conversation("Test Chat", db_path=str(db_file))
    assert cid > 0

    m1 = conv.add_message(cid, role="user", content="Hello", db_path=str(db_file))
    m2 = conv.add_message(cid, role="assistant", content="Hi there", db_path=str(db_file))
    assert m1 != m2

    msgs = conv.list_messages(cid, db_path=str(db_file))
    assert [m["content"] for m in msgs] == ["Hello", "Hi there"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]

    convo = conv.get_conversation(cid, db_path=str(db_file))
    assert convo is not None
    assert convo.get("title") == "Test Chat"
    assert "created_at" in convo and "updated_at" in convo
