# Quick Start

Get Seev running and generate your first worklog in ≤ 10 minutes.

> Tip: Commands first, then explanations. Copy buttons are enabled on this site.

## 1) Prerequisites

- Python 3.13+
- uv (recommended package runner)
- git

Verify:

```bash
python -V
uv --version
git --version
```

## 2) Initialize your workspace (1–2 minutes)

Recommended: use the install script. It prepares a workspace folder, a WORKLOG.md, a local DB, and your Seev config file.

```bash
# Create ~/seev-workspace with sensible defaults
curl -fsSL https://raw.githubusercontent.com/bcosynot/seev/main/seev-init.sh | bash -s
```

- Creates the target dir if missing
- Writes WORKLOG.md and a local SQLite DB
- Creates/updates ~/.config/seev/seev.toml with placeholders

!!! warning "Security"
    Always inspect scripts before piping to bash:
    
    ```bash
    curl -fsSL https://raw.githubusercontent.com/bcosynot/seev/main/seev-init.sh -o /tmp/seev-init.sh
    less /tmp/seev-init.sh
    bash /tmp/seev-init.sh -h
    ```

Optional flags:

```bash
# Set emails and repos at init time
bash /tmp/seev-init.sh -y \
  -e "me@ex.com,me@work.com" \
  -r "org/repo,~/code/another-repo" \
  -m WORKLOG.md -d seev.sqlite3 \
  ~/seev-workspace
```

## 3) Add Seev to your MCP client (2–4 minutes)

Use one of the tabs below and restart your client after editing its config.

=== "Claude Desktop"

    Config file paths:

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

=== "Cursor"

    Config file path:
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

    VS Code settings JSON (user or workspace):

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

## 4) Generate your first worklog entry (1–3 minutes)

Open your assistant and run one of these:

```text
/worklog_entry today
```

Or a specific date or range:

```text
/worklog_entry 2025-10-20
/worklog_entry last week
```

What happens:
- Seev gathers your commits, correlates with conversations/PRs, and writes to `WORKLOG.md` under `## YYYY-MM-DD`.

## 5) Verification checklist

- [ ] `WORKLOG.md` exists in your workspace and contains today’s date heading (YYYY-MM-DD).
- [ ] Entry includes commits and a metrics section.
- [ ] No client errors after restart; the Seev MCP server shows in logs.

If anything fails, see: [Troubleshooting](../troubleshooting.md) or [Workspace & Configuration](workspace-and-configuration.md).
