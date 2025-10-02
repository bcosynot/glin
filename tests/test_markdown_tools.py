import os
from pathlib import Path

import pytest

from glin.markdown_tools import append_to_markdown


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def test_append_creates_file_and_heading(tmp_path, monkeypatch):
    target = tmp_path / "WORKLOG.md"
    cwd = tmp_path
    monkeypatch.chdir(cwd)

    res = append_to_markdown("first line\nsecond line")

    assert res["ok"] is True
    assert Path(res["path"]) == target
    assert res["heading"].startswith("## ")
    assert res["heading_added"] is True
    assert res["bullets_added"] == 2
    # File content checks
    content = read(target)
    lines = content.strip().split("\n")
    # Expect heading, blank, two bullets
    assert lines[0] == res["heading"]
    assert lines[1] == ""
    assert lines[2] == "- first line"
    assert lines[3] == "- second line"


def test_append_to_existing_heading_appends_below(tmp_path, monkeypatch):
    cwd = tmp_path
    monkeypatch.chdir(cwd)

    # First append creates file and heading
    res1 = append_to_markdown("a")
    path = Path(res1["path"])  # same file used implicitly

    # Second append should add below existing section, not duplicate heading
    res2 = append_to_markdown("b\n\nc")

    content = read(path)
    # There should be a single heading, followed by bullets for a, b, c
    assert content.count(res1["heading"]) == 1
    # Ensure blank line after heading then bullets
    assert f"{res1['heading']}\n\n- a\n- b\n- c\n" in content


def test_respects_file_path_argument_over_env(tmp_path, monkeypatch):
    file_arg = tmp_path / "custom.md"
    env_file = tmp_path / "env.md"
    monkeypatch.setenv("GLIN_MD_PATH", str(env_file))

    res = append_to_markdown("x", file_path=str(file_arg))
    assert Path(res["path"]) == file_arg
    assert file_arg.exists()
    assert not env_file.exists()


def test_uses_env_when_no_file_path(tmp_path, monkeypatch):
    env_file = tmp_path / "env.md"
    monkeypatch.setenv("GLIN_MD_PATH", str(env_file))

    res = append_to_markdown("y")
    assert Path(res["path"]) == env_file
    assert res["used_env"] is True


def test_rejects_empty_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for payload in ("", "   ", "\n\n"):
        res = append_to_markdown(payload)
        assert "error" in res


def test_normalizes_windows_newlines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # CRLF and trailing carriage returns should be normalized
    res = append_to_markdown("line1\r\nline2\r")
    path = Path(res["path"])
    text = read(path)
    assert "\r" not in text
    assert "- line1\n- line2\n" in text
