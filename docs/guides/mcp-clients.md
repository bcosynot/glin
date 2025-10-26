# Using Different MCP Clients

Configure Seev with your preferred MCP‑compatible client. Use the tab for your client and restart it after saving the config.

=== "Claude Desktop"

    Config file (create if missing):

    - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
    - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

    ```json
    {
      "mcpServers": {
        "seev": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/bcosynot/seev.git", "seev"]
        }
      }
    }
    ```

    !!! tip "HTTP transport (optional)"
        Seev defaults to stdio. To run over HTTP (port 8000), start it manually:
        
        ```bash
        uv run python main.py --transport http
        ```

=== "Cursor"

    Config file:
    - macOS/Linux: `~/.cursor/mcp.json`
    - Windows: `%USERPROFILE%\.cursor\mcp.json`

    ```json
    {
      "mcpServers": {
        "seev": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/bcosynot/seev.git", "seev"]
        }
      }
    }
    ```

=== "Cline (VS Code)"

    VS Code settings (User or Workspace):

    ```json
    {
      "cline.mcpServers": {
        "seev": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/bcosynot/seev.git", "seev"]
        }
      }
    }
    ```

## Verifying your client can talk to Seev

- Restart the client after editing config
- Ask it to run a simple tool, e.g.:

```text
/get_tracked_email_config
```

Expected: a configuration snapshot including where tracked emails came from.
