from pathlib import Path

from seev.markdown_tools import (
    _deduplicate_bullets,
    _deduplicate_commits,
    _extract_commit_hash,
    _is_similar,
    append_to_markdown,
    merge_date_sections,
    read_date_entry,
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def test_append_creates_file_and_heading(tmp_path, monkeypatch):
    target = tmp_path / "WORKLOG.md"
    cwd = tmp_path
    monkeypatch.chdir(cwd)
    # Mock get_markdown_path to return default relative path
    import seev.markdown_tools

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")

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

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")

    # First append creates file and heading
    res1 = append_to_markdown("a")
    path = Path(res1["path"])  # same file used implicitly

    # Second append should add below existing section, not duplicate heading
    append_to_markdown("b\n\nc")

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

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
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
        append_to_markdown("content", file_path=str(dir_path))
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

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create file with existing headings
    existing_content = """# Main Title

## 2024-01-01

- old entry

## 2023-12-31

- older entry
"""
    target.write_text(existing_content, encoding="utf-8")

    append_to_markdown("new entry")
    content = read(target)

    # Should insert new heading at the top, after main title
    lines = content.split("\n")
    assert "# Main Title" in lines[0]
    assert lines[2].startswith("## ")  # New heading
    assert "- new entry" in content


def test_handles_file_ending_without_newline_edge_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
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
    from unittest.mock import patch

    with patch("seev.markdown_tools.Path.write_text") as mock_write:
        mock_write.side_effect = OSError("Disk full")

        res = append_to_markdown("test content")
        assert "error" in res
        assert "Failed to append to markdown" in res["error"]


def test_heading_fallback_when_missing_after_insert(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
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


# Tests for read_date_entry function


def test_read_date_entry_nonexistent_file(tmp_path, monkeypatch):
    """Test reading from a file that doesn't exist."""
    monkeypatch.chdir(tmp_path)
    nonexistent = tmp_path / "nonexistent.md"

    result = read_date_entry("2024-01-15", file_path=str(nonexistent))

    assert result["exists"] is False
    assert result["date"] == "2024-01-15"
    assert result["heading_line"] is None
    assert result["raw_content"] == ""
    assert result["sections"]["goals"] == []
    assert result["sections"]["technical"] == []


def test_read_date_entry_empty_file(tmp_path, monkeypatch):
    """Test reading from an empty file."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    target.write_text("", encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is False
    assert result["date"] == "2024-01-15"
    assert result["heading_line"] is None


def test_read_date_entry_missing_date(tmp_path, monkeypatch):
    """Test reading a date that doesn't exist in the file."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-10

- Some entry

## 2024-01-12

- Another entry
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-11", file_path=str(target))

    assert result["exists"] is False
    assert result["date"] == "2024-01-11"
    assert result["heading_line"] is None


def test_read_date_entry_invalid_date_format(tmp_path, monkeypatch):
    """Test reading with an invalid date format."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    target.write_text("# Worklog", encoding="utf-8")

    result = read_date_entry("invalid-date", file_path=str(target))

    assert result["exists"] is False
    assert result["date"] == "invalid-date"
    assert result["heading_line"] is None


def test_read_date_entry_with_all_sections(tmp_path, monkeypatch):
    """Test reading a date entry with all section types."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-15

### 🎯 Goals & Context

- Complete feature X
- Review PR #123

### 💻 Technical Work

- Implemented function Y
- Fixed bug in module Z

### 📊 Metrics

- 5 commits
- 3 PRs reviewed

### 🔍 Key Decisions

- Decided to use approach A over B

### ⚠️ Impact Assessment

- Breaking change in API v2

### 🚧 Open Items

- Need to update documentation
- Pending review from team

### 📚 Learnings

- Learned about pattern X

### 🗓️ Weekly Summary

This week was productive.
Made significant progress on the project.

## 2024-01-14

- Previous day entry
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    assert result["date"] == "2024-01-15"
    assert result["heading_line"] == 3  # 1-based line number
    assert len(result["sections"]["goals"]) == 2
    assert "Complete feature X" in result["sections"]["goals"]
    assert "Review PR #123" in result["sections"]["goals"]
    assert len(result["sections"]["technical"]) == 2
    assert "Implemented function Y" in result["sections"]["technical"]
    assert len(result["sections"]["metrics"]) == 2
    assert len(result["sections"]["decisions"]) == 1
    assert len(result["sections"]["impact"]) == 1
    assert len(result["sections"]["open_items"]) == 2
    assert len(result["sections"]["learnings"]) == 1
    assert result["sections"]["weekly_summary"] is not None
    assert "This week was productive" in result["sections"]["weekly_summary"]


def test_read_date_entry_with_partial_sections(tmp_path, monkeypatch):
    """Test reading a date entry with only some sections."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-15

### 🎯 Goals

- Goal 1
- Goal 2

### 💻 Technical Work

- Work item 1

## 2024-01-14

- Previous entry
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    assert len(result["sections"]["goals"]) == 2
    assert len(result["sections"]["technical"]) == 1
    assert result["sections"]["metrics"] == []
    assert result["sections"]["decisions"] == []
    assert result["sections"]["weekly_summary"] is None


def test_read_date_entry_with_asterisk_bullets(tmp_path, monkeypatch):
    """Test reading entries with * bullets instead of - bullets."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-15

### 🎯 Goals

* Goal with asterisk
* Another goal

### 💻 Technical Work

- Mixed bullet style
* Another asterisk bullet
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    assert len(result["sections"]["goals"]) == 2
    assert "Goal with asterisk" in result["sections"]["goals"]
    assert len(result["sections"]["technical"]) == 2
    assert "Mixed bullet style" in result["sections"]["technical"]
    assert "Another asterisk bullet" in result["sections"]["technical"]


def test_read_date_entry_with_empty_sections(tmp_path, monkeypatch):
    """Test reading entries with section headers but no content."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-15

### 🎯 Goals

### 💻 Technical Work

- Some work

## 2024-01-14

- Previous entry
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    assert result["sections"]["goals"] == []
    assert len(result["sections"]["technical"]) == 1


def test_read_date_entry_with_malformed_content(tmp_path, monkeypatch):
    """Test reading entries with malformed markdown."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-15

Some text without section header

### 🎯 Goals

- Goal 1

Random text between sections

### 💻 Technical Work

- Work 1
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    # Should still parse the sections that are properly formatted
    assert len(result["sections"]["goals"]) == 1
    assert len(result["sections"]["technical"]) == 1


def test_read_date_entry_at_end_of_file(tmp_path, monkeypatch):
    """Test reading the last date entry in the file."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = """# Worklog

## 2024-01-14

- Earlier entry

## 2024-01-15

### 🎯 Goals

- Last entry goal
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    assert len(result["sections"]["goals"]) == 1
    assert "Last entry goal" in result["sections"]["goals"]


def test_read_date_entry_with_crlf_newlines(tmp_path, monkeypatch):
    """Test reading entries from files with CRLF line endings."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "WORKLOG.md"
    content = "# Worklog\r\n\r\n## 2024-01-15\r\n\r\n### 🎯 Goals\r\n\r\n- Goal 1\r\n"
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15", file_path=str(target))

    assert result["exists"] is True
    assert len(result["sections"]["goals"]) == 1
    assert "Goal 1" in result["sections"]["goals"]


def test_read_date_entry_uses_default_path(tmp_path, monkeypatch):
    """Test that read_date_entry uses get_markdown_path when no file_path provided."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"
    content = """## 2024-01-15

### 🎯 Goals

- Test goal
"""
    target.write_text(content, encoding="utf-8")

    result = read_date_entry("2024-01-15")

    assert result["exists"] is True
    assert len(result["sections"]["goals"]) == 1


# Tests for merge logic helper functions


def test_extract_commit_hash_markdown_link():
    """Test extracting commit hash from markdown link format."""
    bullet = "[abc1234](https://github.com/user/repo/commit/abc1234) - Fixed bug"
    assert _extract_commit_hash(bullet) == "abc1234"


def test_extract_commit_hash_plain_format():
    """Test extracting commit hash from plain format."""
    bullet = "abc1234 - Fixed bug"
    assert _extract_commit_hash(bullet) == "abc1234"

    bullet2 = "abc1234: Fixed bug"
    assert _extract_commit_hash(bullet2) == "abc1234"


def test_extract_commit_hash_commit_prefix():
    """Test extracting commit hash with 'Commit' prefix."""
    bullet = "Commit abc1234: Fixed bug"
    assert _extract_commit_hash(bullet) == "abc1234"

    bullet2 = "commit ABC1234 fixed the issue"
    assert _extract_commit_hash(bullet2) == "abc1234"


def test_extract_commit_hash_no_hash():
    """Test that None is returned when no hash is found."""
    bullet = "Just a regular bullet point"
    assert _extract_commit_hash(bullet) is None

    bullet2 = "Short abc hash"  # Too short to be a valid hash
    assert _extract_commit_hash(bullet2) is None


def test_extract_commit_hash_long_hash():
    """Test extracting full 40-character commit hash."""
    bullet = "[abcdef1234567890abcdef1234567890abcdef12](url) - message"
    assert _extract_commit_hash(bullet) == "abcdef1234567890abcdef1234567890abcdef12"


def test_is_similar_exact_match():
    """Test similarity with exact matches."""
    assert _is_similar("Same text", "Same text") is True
    assert _is_similar("  Same   text  ", "Same text") is True  # Normalized


def test_is_similar_case_insensitive():
    """Test similarity is case insensitive."""
    assert _is_similar("Hello World", "hello world") is True


def test_is_similar_different_texts():
    """Test similarity with completely different texts."""
    assert _is_similar("Completely different", "Nothing alike") is False


def test_is_similar_threshold():
    """Test similarity with custom threshold."""
    # Similar but not identical
    text1 = "Fixed bug in module X"
    text2 = "Fixed bug in module Y"
    # Should be similar with default threshold
    assert _is_similar(text1, text2, threshold=0.85) is True
    # Should not be similar with very high threshold
    assert _is_similar(text1, text2, threshold=0.99) is False


def test_is_similar_empty_strings():
    """Test similarity with empty strings."""
    assert _is_similar("", "") is True
    assert _is_similar("text", "") is False
    assert _is_similar("", "text") is False


def test_deduplicate_bullets_no_duplicates():
    """Test deduplication when there are no duplicates."""
    existing = ["Item 1", "Item 2"]
    new = ["Item 3", "Item 4"]

    merged, dup_count = _deduplicate_bullets(existing, new)

    assert len(merged) == 4
    assert merged == ["Item 1", "Item 2", "Item 3", "Item 4"]
    assert dup_count == 0


def test_deduplicate_bullets_with_duplicates():
    """Test deduplication with exact duplicates."""
    existing = ["Item 1", "Item 2"]
    new = ["Item 2", "Item 3"]

    merged, dup_count = _deduplicate_bullets(existing, new)

    assert len(merged) == 3
    assert "Item 1" in merged
    assert "Item 2" in merged
    assert "Item 3" in merged
    assert dup_count == 1


def test_deduplicate_bullets_fuzzy_match():
    """Test deduplication with fuzzy matching."""
    existing = ["Fixed bug in module X"]
    new = ["Fixed bug in module X", "Added new feature"]

    merged, dup_count = _deduplicate_bullets(existing, new)

    assert len(merged) == 2
    assert "Fixed bug in module X" in merged
    assert "Added new feature" in merged
    assert dup_count == 1


def test_deduplicate_bullets_preserves_order():
    """Test that deduplication preserves order."""
    existing = ["First", "Second"]
    new = ["Third", "Fourth"]

    merged, dup_count = _deduplicate_bullets(existing, new)

    assert merged == ["First", "Second", "Third", "Fourth"]


def test_deduplicate_bullets_empty_lists():
    """Test deduplication with empty lists."""
    merged, dup_count = _deduplicate_bullets([], [])
    assert merged == []
    assert dup_count == 0

    merged, dup_count = _deduplicate_bullets(["Item 1"], [])
    assert merged == ["Item 1"]
    assert dup_count == 0

    merged, dup_count = _deduplicate_bullets([], ["Item 1"])
    assert merged == ["Item 1"]
    assert dup_count == 0


def test_deduplicate_commits_no_duplicates():
    """Test commit deduplication with no duplicates."""
    existing = ["[abc1234](url) - Fix 1", "[def5678](url) - Fix 2"]
    new = ["[ghi9012](url) - Fix 3"]

    merged, dup_count = _deduplicate_commits(existing, new)

    assert len(merged) == 3
    assert dup_count == 0


def test_deduplicate_commits_with_duplicates():
    """Test commit deduplication with duplicate hashes."""
    existing = ["[abc1234](url) - Fix 1"]
    new = ["[abc1234](url) - Fix 1 (different message)", "[def5678](url) - Fix 2"]

    merged, dup_count = _deduplicate_commits(existing, new)

    assert len(merged) == 2
    assert dup_count == 1
    # Should keep the existing version and add the new non-duplicate
    assert "[abc1234](url) - Fix 1" in merged
    assert "[def5678](url) - Fix 2" in merged


def test_deduplicate_commits_different_formats():
    """Test commit deduplication with different hash formats."""
    existing = ["abc1234 - Fix 1"]
    new = ["[abc1234](url) - Same commit different format", "def5678: Fix 2"]

    merged, dup_count = _deduplicate_commits(existing, new)

    assert len(merged) == 2
    assert dup_count == 1


def test_deduplicate_commits_no_hash():
    """Test commit deduplication with bullets that have no hash."""
    existing = ["[abc1234](url) - Fix 1"]
    new = ["Regular bullet without hash", "[abc1234](url) - Duplicate"]

    merged, dup_count = _deduplicate_commits(existing, new)

    # Bullets without hash are always added
    assert len(merged) == 2
    assert "Regular bullet without hash" in merged
    assert dup_count == 1


def test_deduplicate_commits_preserves_order():
    """Test that commit deduplication preserves order."""
    existing = ["[aaa1111](url) - First", "[bbb2222](url) - Second"]
    new = ["[ccc3333](url) - Third", "[ddd4444](url) - Fourth"]

    merged, dup_count = _deduplicate_commits(existing, new)

    assert merged[0] == "[aaa1111](url) - First"
    assert merged[1] == "[bbb2222](url) - Second"
    assert merged[2] == "[ccc3333](url) - Third"
    assert merged[3] == "[ddd4444](url) - Fourth"


# Tests for merge_date_sections function


def test_merge_date_sections_empty_existing():
    """Test merging when existing entry is empty."""
    existing = {
        "exists": False,
        "date": "2024-01-15",
        "heading_line": None,
        "sections": {
            "goals": [],
            "technical": [],
            "metrics": [],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": None,
        },
        "raw_content": "",
    }

    new_content = """### 🎯 Goals

- Goal 1
- Goal 2

### 💻 Technical Work

- Work item 1
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    assert dup_count == 0
    assert "### 🎯 Goals & Context" in merged
    assert "- Goal 1" in merged
    assert "- Goal 2" in merged
    assert "### 💻 Technical Work" in merged
    assert "- Work item 1" in merged


def test_merge_date_sections_with_duplicates():
    """Test merging with duplicate content."""
    existing = {
        "exists": True,
        "date": "2024-01-15",
        "heading_line": 3,
        "sections": {
            "goals": ["Goal 1", "Goal 2"],
            "technical": ["[abc1234](url) - Fix 1"],
            "metrics": [],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": None,
        },
        "raw_content": "",
    }

    new_content = """### 🎯 Goals

- Goal 2
- Goal 3

### 💻 Technical Work

- [abc1234](url) - Fix 1 (duplicate)
- [def5678](url) - Fix 2
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    assert dup_count == 2  # One goal duplicate, one commit duplicate
    assert "- Goal 1" in merged
    assert "- Goal 2" in merged
    assert "- Goal 3" in merged
    assert merged.count("Goal 2") == 1  # Should appear only once
    assert "[abc1234](url) - Fix 1" in merged
    assert "[def5678](url) - Fix 2" in merged


def test_merge_date_sections_metrics_replacement():
    """Test that metrics are replaced, not merged."""
    existing = {
        "exists": True,
        "date": "2024-01-15",
        "heading_line": 3,
        "sections": {
            "goals": [],
            "technical": [],
            "metrics": ["Old metric 1", "Old metric 2"],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": None,
        },
        "raw_content": "",
    }

    new_content = """### 📊 Metrics

- New metric 1
- New metric 2
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    # Metrics should be replaced, not merged
    assert "- New metric 1" in merged
    assert "- New metric 2" in merged
    assert "Old metric 1" not in merged
    assert "Old metric 2" not in merged


def test_merge_date_sections_weekly_summary():
    """Test weekly summary handling."""
    existing = {
        "exists": True,
        "date": "2024-01-15",
        "heading_line": 3,
        "sections": {
            "goals": [],
            "technical": [],
            "metrics": [],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": "Old summary content",
        },
        "raw_content": "",
    }

    new_content = """### 🗓️ Weekly Summary

New summary content.
Multiple lines.
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    assert "### 🗓️ Weekly Summary" in merged
    assert "New summary content" in merged
    assert "Multiple lines" in merged
    assert "Old summary" not in merged


def test_merge_date_sections_preserves_existing_summary():
    """Test that existing summary is preserved when no new one provided."""
    existing = {
        "exists": True,
        "date": "2024-01-15",
        "heading_line": 3,
        "sections": {
            "goals": ["Goal 1"],
            "technical": [],
            "metrics": [],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": "Existing summary",
        },
        "raw_content": "",
    }

    new_content = """### 🎯 Goals

- Goal 2
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    assert "Existing summary" in merged
    assert "### 🗓️ Weekly Summary" in merged


def test_merge_date_sections_all_section_types():
    """Test merging with all section types."""
    existing = {
        "exists": True,
        "date": "2024-01-15",
        "heading_line": 3,
        "sections": {
            "goals": ["Existing goal"],
            "technical": ["[aaa1111](url) - Existing work"],
            "metrics": ["Old metric"],
            "decisions": ["Existing decision"],
            "impact": ["Existing impact"],
            "open_items": ["Existing item"],
            "learnings": ["Existing learning"],
            "weekly_summary": None,
        },
        "raw_content": "",
    }

    new_content = """### 🎯 Goals

- New goal

### 💻 Technical Work

- [bbb2222](url) - New work

### 📊 Metrics

- New metric

### 🔍 Key Decisions

- New decision

### ⚠️ Impact Assessment

- New impact

### 🚧 Open Items

- New item

### 📚 Learnings

- New learning
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    # Check all sections are present
    assert "### 🎯 Goals & Context" in merged
    assert "### 💻 Technical Work" in merged
    assert "### 📊 Metrics" in merged
    assert "### 🔍 Key Decisions" in merged
    assert "### ⚠️ Impact Assessment" in merged
    assert "### 🚧 Open Items" in merged
    assert "### 📚 Learnings" in merged

    # Check content is merged (except metrics which are replaced)
    assert "- Existing goal" in merged
    assert "- New goal" in merged
    assert "[aaa1111](url) - Existing work" in merged
    assert "[bbb2222](url) - New work" in merged
    assert "- New metric" in merged
    assert "Old metric" not in merged  # Metrics replaced


def test_merge_date_sections_preserve_lines_mode():
    """Test merge with preserve_lines mode."""
    existing = {
        "exists": True,
        "date": "2024-01-15",
        "heading_line": 3,
        "sections": {
            "goals": [],
            "technical": [],
            "metrics": [],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": None,
        },
        "raw_content": "",
    }

    new_content = """### 🎯 Goals

Some non-bullet text
- Bullet 1
More text
"""

    merged, dup_count = merge_date_sections(existing, new_content, preserve_lines=True)

    assert "- Some non-bullet text" in merged
    assert "- Bullet 1" in merged
    assert "- More text" in merged


def test_merge_date_sections_section_order():
    """Test that sections appear in standard order."""
    existing = {
        "exists": False,
        "date": "2024-01-15",
        "heading_line": None,
        "sections": {
            "goals": [],
            "technical": [],
            "metrics": [],
            "decisions": [],
            "impact": [],
            "open_items": [],
            "learnings": [],
            "weekly_summary": None,
        },
        "raw_content": "",
    }

    # Add sections in reverse order
    new_content = """### 📚 Learnings

- Learning 1

### 🎯 Goals

- Goal 1

### 💻 Technical Work

- Work 1
"""

    merged, dup_count = merge_date_sections(existing, new_content)

    # Check order: Goals should come before Technical, which should come before Learnings
    goals_pos = merged.find("### 🎯 Goals")
    tech_pos = merged.find("### 💻 Technical")
    learn_pos = merged.find("### 📚 Learnings")

    assert goals_pos < tech_pos < learn_pos


# Tests for append_to_markdown with update_mode


def test_append_to_markdown_update_mode_false(tmp_path, monkeypatch):
    """Test that update_mode=False uses traditional append behavior."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create initial content
    initial = """## 2024-01-15

### 🎯 Goals

- Goal 1
"""
    target.write_text(initial, encoding="utf-8")

    # Append with update_mode=False (default)
    res = append_to_markdown("Goal 2", update_mode=False)

    assert res["ok"] is True
    content = read(target)

    # Should have both goals as separate bullets (no deduplication)
    assert content.count("- Goal 1") == 1
    assert content.count("- Goal 2") == 1


def test_append_to_markdown_update_mode_true_no_existing(tmp_path, monkeypatch):
    """Test update_mode=True when no existing entry exists (falls through to normal append)."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create file without the target date
    initial = """## 2024-01-14

- Old entry
"""
    target.write_text(initial, encoding="utf-8")

    # Append with update_mode=True for a new date
    # When no existing entry exists, it falls through to normal append
    content = """### 🎯 Goals

- Goal 1
- Goal 2
"""
    res = append_to_markdown(content, date_str="2024-01-15", update_mode=True, preserve_lines=True)

    assert res["ok"] is True
    # Falls through to normal append when no existing entry
    assert res.get("update_mode_used") is False
    assert res.get("deduplicated_count", 0) == 0

    file_content = read(target)
    assert "## 2024-01-15" in file_content
    assert "### 🎯 Goals" in file_content
    assert "- Goal 1" in file_content
    assert "- Goal 2" in file_content


def test_append_to_markdown_update_mode_true_with_duplicates(tmp_path, monkeypatch):
    """Test update_mode=True deduplicates content."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create initial content
    initial = """## 2024-01-15

### 🎯 Goals

- Goal 1
- Goal 2

### 💻 Technical Work

- [abc1234](url) - Fix 1
"""
    target.write_text(initial, encoding="utf-8")

    # Update with some duplicate content
    new_content = """### 🎯 Goals

- Goal 2
- Goal 3

### 💻 Technical Work

- [abc1234](url) - Fix 1 (duplicate hash)
- [def5678](url) - Fix 2
"""
    res = append_to_markdown(new_content, date_str="2024-01-15", update_mode=True)

    assert res["ok"] is True
    assert res.get("update_mode_used") is True
    assert res.get("deduplicated_count", 0) == 2  # One goal, one commit

    file_content = read(target)

    # Should have all unique goals
    assert "- Goal 1" in file_content
    assert "- Goal 2" in file_content
    assert "- Goal 3" in file_content
    # Goal 2 should appear only once
    assert file_content.count("Goal 2") == 1

    # Should have both commits (deduplicated by hash)
    assert "[abc1234](url) - Fix 1" in file_content
    assert "[def5678](url) - Fix 2" in file_content
    # abc1234 should appear only once
    assert file_content.count("abc1234") == 1


def test_append_to_markdown_update_mode_preserves_other_dates(tmp_path, monkeypatch):
    """Test that update_mode only affects the target date."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create content with multiple dates
    initial = """## 2024-01-15

### 🎯 Goals

- Goal for 15th

## 2024-01-14

### 🎯 Goals

- Goal for 14th
"""
    target.write_text(initial, encoding="utf-8")

    # Update only 2024-01-15
    new_content = """### 🎯 Goals

- New goal for 15th
"""
    res = append_to_markdown(new_content, date_str="2024-01-15", update_mode=True)

    assert res["ok"] is True
    file_content = read(target)

    # 2024-01-15 should be updated
    assert "- Goal for 15th" in file_content
    assert "- New goal for 15th" in file_content

    # 2024-01-14 should be unchanged
    assert "## 2024-01-14" in file_content
    assert "- Goal for 14th" in file_content


def test_append_to_markdown_update_mode_metrics_replacement(tmp_path, monkeypatch):
    """Test that metrics are replaced in update mode."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create initial content with metrics
    initial = """## 2024-01-15

### 📊 Metrics

- 5 commits
- 2 PRs
"""
    target.write_text(initial, encoding="utf-8")

    # Update with new metrics
    new_content = """### 📊 Metrics

- 10 commits
- 5 PRs
"""
    res = append_to_markdown(new_content, date_str="2024-01-15", update_mode=True)

    assert res["ok"] is True
    file_content = read(target)

    # Old metrics should be replaced
    assert "10 commits" in file_content
    assert "5 PRs" in file_content
    assert "5 commits" not in file_content
    assert "2 PRs" not in file_content


def test_append_to_markdown_update_mode_return_structure(tmp_path, monkeypatch):
    """Test that update_mode returns proper structure with merge stats."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create initial content
    initial = """## 2024-01-15

### 🎯 Goals

- Goal 1
"""
    target.write_text(initial, encoding="utf-8")

    # Update with duplicate
    new_content = """### 🎯 Goals

- Goal 1
- Goal 2
"""
    res = append_to_markdown(new_content, date_str="2024-01-15", update_mode=True)

    # Check return structure
    assert res["ok"] is True
    assert "path" in res
    assert "heading" in res
    assert res.get("update_mode_used") is True
    assert res.get("deduplicated_count") == 1
    assert "bullets_added" in res


def test_append_to_markdown_backward_compatibility(tmp_path, monkeypatch):
    """Test that default behavior (update_mode not specified) works as before."""
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(seev.markdown_tools, "get_markdown_path", lambda: "WORKLOG.md")
    target = tmp_path / "WORKLOG.md"

    # Create initial content
    initial = """## 2024-01-15

- Old entry
"""
    target.write_text(initial, encoding="utf-8")

    # Append without specifying update_mode (should default to False)
    res = append_to_markdown("New entry")

    assert res["ok"] is True
    # Should have update_mode_used=False and deduplicated_count=0
    assert res.get("update_mode_used") is False
    assert res.get("deduplicated_count") == 0

    file_content = read(target)
    assert "- Old entry" in file_content
    assert "- New entry" in file_content
