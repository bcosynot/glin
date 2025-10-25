from seev.mcp_app import mcp


def test_prompts_are_registered_in_stub():
    # In environments without fastmcp, our stub exposes `_prompts` for discovery
    prompts = getattr(mcp, "_prompts", [])
    # We expect at least one prompt to be registered
    assert any(p.get("name") == "worklog_entry" for p in prompts)
