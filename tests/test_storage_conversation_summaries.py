from seev.storage import conversations as conv, db as sdb, summaries as summ


def test_add_and_list_summaries(tmp_path):
    db_file = tmp_path / "conv.sqlite3"
    # Initialize DB and ensure migration V3 is applied
    ver = sdb.init_db(str(db_file))
    assert ver >= 3

    # Create a conversation and add a couple of summaries
    cid = conv.add_conversation("Sprint Discussion", db_path=str(db_file))
    sid1 = summ.add_summary(
        date="2025-10-26",
        conversation_id=cid,
        title="Sprint Planning",
        summary="Planned tasks and assigned owners.",
        db_path=str(db_file),
    )
    assert sid1 > 0

    sid2 = summ.add_summary(
        date="2025-10-26",
        conversation_id=cid,
        title="Sprint Planning",
        summary="Follow-up: clarified scope and risks.",
        db_path=str(db_file),
    )
    assert sid2 > sid1

    # Query by date
    rows = summ.list_summaries({"date": "2025-10-26"}, db_path=str(db_file))
    assert len(rows) == 2
    assert rows[0]["id"] == sid2  # ordered DESC by id
    assert rows[1]["id"] == sid1

    # Query by date and conversation_id with limit
    rows2 = summ.list_summaries(
        {"date": "2025-10-26", "conversation_id": cid, "limit": 1}, db_path=str(db_file)
    )
    assert len(rows2) == 1
    assert rows2[0]["id"] == sid2
