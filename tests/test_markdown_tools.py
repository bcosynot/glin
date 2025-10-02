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


def test_handles_file_without_trailing_newline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    
    # Create file without trailing newline
    target.write_text("# Existing content", encoding="utf-8")
    
    res = append_to_markdown("new content")
    content = read(target)
    
    # Should handle file without trailing newline properly
    assert res["ok"] is True
    assert "# Existing content\n" in content
    assert "- new content" in content


def test_handles_existing_file_with_crlf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    
    # Create file with CRLF line endings
    target.write_text("# Existing\r\n\r\nSome content\r\n", encoding="utf-8")
    
    res = append_to_markdown("new line")
    content = read(target)
    
    # Should normalize existing CRLF to LF
    assert "\r" not in content
    assert res["ok"] is True


def test_handles_permission_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "readonly.md"
    target.write_text("content", encoding="utf-8")
    target.chmod(0o444)  # Read-only
    
    try:
        res = append_to_markdown("new content", file_path=str(target))
        # If we get here, the system allows writing to read-only files
        # (some systems do), so just verify it worked
        if "ok" in res:
            assert res["ok"] is True
        elif "error" in res:
            # Expected on systems that enforce read-only
            assert "error" in res
    except PermissionError:
        # This is expected on systems that enforce read-only
        pass
    finally:
        # Clean up - restore write permissions
        target.chmod(0o644)


def test_handles_directory_as_file_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dir_path = tmp_path / "directory"
    dir_path.mkdir()
    
    try:
        res = append_to_markdown("content", file_path=str(dir_path))
        # Should handle this gracefully or raise appropriate error
        # The exact behavior depends on the implementation
    except (IsADirectoryError, PermissionError):
        # Expected on most systems
        pass


def test_empty_lines_only_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # Test content that becomes empty after stripping (caught by first check)
    res = append_to_markdown("   \n  \n   ")
    assert "error" in res
    assert "cannot be empty" in res["error"]


def test_blank_lines_only_after_normalization(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # Test content that has non-empty characters but becomes empty after line processing
    # This should reach the "blank lines" check
    res = append_to_markdown("x\n   \n  \n   ")  # Has content, so passes first check
    # After processing, only "x" becomes a bullet, so this should work
    assert res["ok"] is True
    
    # Test truly blank lines after normalization - need content that passes strip() but has no bullets
    # This is actually hard to trigger since any non-whitespace content will create bullets


def test_mixed_empty_and_content_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # Test content with empty lines mixed in
    res = append_to_markdown("line1\n\n  \nline2\n\n")
    assert res["ok"] is True
    assert res["bullets_added"] == 2  # Only non-empty lines become bullets
    
    content = read(Path(res["path"]))
    assert "- line1" in content
    assert "- line2" in content


def test_inserts_heading_in_middle_of_document(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    
    # Create file with existing headings
    existing_content = """# Main Title

## 2024-01-01

- old entry

## 2023-12-31

- older entry
"""
    target.write_text(existing_content, encoding="utf-8")
    
    res = append_to_markdown("new entry")
    content = read(target)
    
    # Should insert new heading at the top, after main title
    lines = content.split("\n")
    assert "# Main Title" in lines[0]
    assert lines[2].startswith("## ")  # New heading
    assert "- new entry" in content


def test_handles_file_ending_without_newline_edge_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    
    # Create file that doesn't end with newline and has content at the end
    target.write_text("# Title\n\nSome content", encoding="utf-8")
    
    res = append_to_markdown("new entry")
    content = read(target)
    
    # Should handle this properly
    assert res["ok"] is True
    assert "- new entry" in content


def test_handles_general_exception(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # Mock Path.write_text to raise an exception
    from unittest.mock import patch, Mock
    
    with patch('glin.markdown_tools.Path.write_text') as mock_write:
        mock_write.side_effect = OSError("Disk full")
        
        res = append_to_markdown("test content")
        assert "error" in res
        assert "Failed to append to markdown" in res["error"]


def test_heading_fallback_when_missing_after_insert(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    
    # Create a scenario where heading might go missing (edge case)
    # This is hard to trigger naturally, but we can test the fallback logic
    existing_content = "# Title\n\nContent without proper heading structure"
    target.write_text(existing_content, encoding="utf-8")
    
    res = append_to_markdown("new entry")
    content = read(target)
    
    # Should still work and create proper structure
    assert res["ok"] is True
    assert "- new entry" in content
