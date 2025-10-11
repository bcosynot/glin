from glin.mcp_app import mcp


def test_prompts_are_registered_in_stub():
    # In environments without fastmcp, our stub exposes `_prompts` for discovery
    prompts = getattr(mcp, "_prompts", [])
    # We expect at least one prompt to be registered
    assert any(p.get("name") == "commit_summary" for p in prompts)


def test_commit_summary_renders_messages():
    prompts = [p for p in getattr(mcp, "_prompts", []) if p.get("name") == "commit_summary"]
    assert prompts, "commit_summary prompt not found"
    render = prompts[0]["func"]
    messages = render(
        commits="feat(core): add X\nfix(ui): correct Y",
        date_range="2025-10-01 to 2025-10-09",
    )
    assert isinstance(messages, list) and len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "feat(core):" in messages[1]["content"]


def test_prompts_accept_complex_json_serializable_args():
    """Verify that prompts accept complex arguments that FastMCP will JSON-serialize."""
    # Multi-line strings with special characters
    complex_commits = """feat(api): add new endpoint

    - Added POST /api/users
    - Includes validation

    fix(ui): correct button alignment"""

    prompts = [p for p in getattr(mcp, "_prompts", []) if p.get("name") == "commit_summary"]
    assert prompts, "commit_summary prompt not found"
    render = prompts[0]["func"]
    messages = render(commits=complex_commits, date_range="2025-10-09")
    assert isinstance(messages, list)
    assert "POST /api/users" in messages[1]["content"]


def test_prompt_validation_errors():
    """Verify that prompts raise helpful errors for missing/empty required arguments."""
    import pytest

    prompts = [p for p in getattr(mcp, "_prompts", []) if p.get("name") == "commit_summary"]
    assert prompts, "commit_summary prompt not found"
    render = prompts[0]["func"]

    with pytest.raises(ValueError, match="commits argument is required"):
        render(commits="")

    with pytest.raises(ValueError, match="commits argument is required"):
        render(commits="   ")
