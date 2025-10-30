# Using Different MCP Clients

Configure Seev with your preferred MCP‑compatible client. Use the tab for your client and restart it after saving the config.

=== "Claude Code"

    Use the Claude CLI to add Seev at user scope (recommended):

    ```bash
    claude mcp add --transport stdio --scope user --name seev -- uvx --from git+https://github.com/bcosynot/seev.git seev
    ```

    After running the command, restart Claude Code so it picks up the new MCP server.


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

=== "Cline"

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
use seev to get the last 10 commits
```

Expected: a configuration snapshot including where tracked emails came from.
