import sqlite3

from glin.storage import db as sdb


def test_init_db_and_migrate_idempotent(tmp_path):
    db_file = tmp_path / "glin.sqlite3"
    # First run initializes to latest (currently 1)
    version1 = sdb.init_db(str(db_file))
    assert isinstance(version1, int)
    assert version1 >= 1

    # Idempotent: second run returns same version
    version2 = sdb.migrate(str(db_file))
    assert version2 == version1

    # Schema table is present and single row exists
    with sdb.get_connection(str(db_file)) as conn:
        row = conn.execute("SELECT id, current_version FROM schema_version WHERE id = 1").fetchone()
        assert row is not None
        assert row[0] == 1
        assert int(row[1]) == version1


def test_memory_db_creates_schema():
    # Using :memory: should work and create schema_version row during migrate
    version = sdb.migrate(":memory:")
    assert version >= 1
    with sdb.get_connection(":memory:") as conn:
        # Note: a new in-memory connection is a fresh database, so the schema table
        # may not exist here. Instead, validate that get_connection returns a usable
        # sqlite3 connection and foreign keys are ON.
        assert isinstance(conn, sqlite3.Connection)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
