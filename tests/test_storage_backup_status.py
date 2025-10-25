from seev.storage import db as sdb


def test_create_backup_and_status(tmp_path):
    db_file = tmp_path / "data.sqlite3"
    # Init and insert a row to ensure file exists and schema_version populated
    version = sdb.init_db(str(db_file))
    assert version >= 1

    # Status before data
    status = sdb.get_db_status(str(db_file))
    assert status["ok"] is True
    assert status["schema_version"] >= 1
    # Expect counts keys present
    table_names = {t["table"] for t in status["tables"]}
    assert {"schema_version", "conversations", "messages", "commits", "commit_files"} <= table_names

    # Create backup under provided root
    backups_root = tmp_path / ".glin" / "backups"
    backup_path = sdb.create_backup(str(db_file), backups_root=str(backups_root))
    assert backup_path.exists()
    # Path should be .../YYYYMMDD/HHMMSS/<filename>
    parts = backup_path.relative_to(backups_root).parts
    assert len(parts) == 3
    day, hms, fname = parts
    assert len(day) == 8 and day.isdigit()
    assert len(hms) == 6 and hms.isdigit()
    assert fname == db_file.name
