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
