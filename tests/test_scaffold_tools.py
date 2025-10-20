import asyncio
from pathlib import Path
from typing import Any

from glin.scaffold_tools import init_glin


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def test_rejects_empty_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for payload in ("", "   ", "\n\n"):
        res = asyncio.run(init_glin.fn(payload))
        assert "error" in res
        assert "path is required" in res["error"]
        assert Path(res["dir"]) == tmp_path
        assert res["missing"] is None


def test_creates_new_workspace(monkeypatch, tmp_path: Path) -> None:
    # Isolate XDG config to tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Target path that does not exist yet
    base = tmp_path / "ws"
    worklog = base / "WORKLOG.md"
    db = base / "db.sqlite3"
    xdg_toml = tmp_path / ".config" / "glin" / "glin.toml"

    # Mock DB init and status
    calls: dict[str, Any] = {"init_db": 0, "status": 0}

    def fake_init_db(path: str | None = None) -> int:
        calls["init_db"] += 1
        # create the file the way real init would ensure
        Path(path or db).touch()
        return 2

    def fake_get_db_status(path: str | None = None) -> dict[str, Any]:
        calls["status"] += 1
        return {"schema_version": 2, "ok": True}

    monkeypatch.setattr("glin.scaffold_tools.init_db", fake_init_db)
    monkeypatch.setattr("glin.scaffold_tools.get_db_status", fake_get_db_status)

    res = asyncio.run(init_glin.fn(str(base)))

    assert res["ok"] is True
    assert res["created"] is True
    assert Path(res["dir"]) == base
    assert Path(res["worklog_path"]) == worklog
    assert Path(res["db_path"]) == db
    assert Path(res["toml_path"]) == xdg_toml
    assert res["schema_version"] == 2
    assert "Workspace created and initialized" in res["message"]

    # Files should exist and contain expected basics
    assert worklog.exists()
    wl = read_text(worklog)
    assert wl.startswith("# Worklog\n\n")

    assert xdg_toml.exists()
    toml_text = read_text(xdg_toml)
    assert f'db_path = "{str(db)}"' in toml_text
    assert f'markdown_path = "{str(worklog)}"' in toml_text

    # DB helpers used
    assert calls["init_db"] == 1
    assert calls["status"] >= 1


def test_existing_dir_missing_files_returns_error(monkeypatch, tmp_path: Path) -> None:
    # Isolate XDG config to tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    base = tmp_path / "ws2"
    base.mkdir()
    # Create only WORKLOG.md so db is missing
    (base / "WORKLOG.md").write_text("# Worklog\n", encoding="utf-8")

    res = asyncio.run(init_glin.fn(str(base)))

    assert "error" in res
    assert res["dir"] == str(base)
    assert res["missing"] == ["db.sqlite3"]
    assert res["error"].startswith("Directory exists but is not initialized.")


def test_already_initialized_reports_status(monkeypatch, tmp_path: Path) -> None:
    # Isolate XDG config to tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    base = tmp_path / "ws3"
    worklog = base / "WORKLOG.md"
    db = base / "db.sqlite3"
    base.mkdir()
    worklog.write_text("# Worklog\n", encoding="utf-8")
    db.touch()

    # get_db_status returns string version; should be coerced to int
    def fake_get_db_status(path: str | None = None) -> dict[str, Any]:
        return {"schema_version": "3", "ok": True}

    init_called = {"count": 0}

    def fake_init_db(path: str | None = None) -> int:
        init_called["count"] += 1
        return 3

    monkeypatch.setattr("glin.scaffold_tools.get_db_status", fake_get_db_status)
    monkeypatch.setattr("glin.scaffold_tools.init_db", fake_init_db)

    res = asyncio.run(init_glin.fn(str(base)))

    assert res["ok"] is True
    assert res["created"] is False
    assert res["schema_version"] == 3
    assert "Workspace already initialized" in res["message"]
    # Should not call init_db when already initialized
    assert init_called["count"] == 0


def test_already_initialized_when_status_raises_sets_none(monkeypatch, tmp_path: Path) -> None:
    # Isolate XDG config to tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    base = tmp_path / "ws4"
    worklog = base / "WORKLOG.md"
    db = base / "db.sqlite3"
    base.mkdir()
    worklog.write_text("# Worklog\n", encoding="utf-8")
    db.touch()

    def boom(path: str | None = None) -> dict[str, Any]:  # type: ignore[override]
        raise RuntimeError("oops")

    monkeypatch.setattr("glin.scaffold_tools.get_db_status", boom)

    res = asyncio.run(init_glin.fn(str(base)))

    assert res["ok"] is True
    assert res["created"] is False
    assert res["schema_version"] is None


def test_relative_path_is_resolved_against_cwd(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    # Isolate XDG config to tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    rel = Path("rel_dir")

    # Mock DB functions to avoid real work
    monkeypatch.setattr("glin.scaffold_tools.init_db", lambda p=None: 1)
    monkeypatch.setattr(
        "glin.scaffold_tools.get_db_status", lambda p=None: {"schema_version": 1, "ok": True}
    )

    res = asyncio.run(init_glin.fn(str(rel)))

    assert Path(res["dir"]) == tmp_path / rel
    assert Path(res["worklog_path"]).exists()
    assert Path(res["toml_path"]).exists()
