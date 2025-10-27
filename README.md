# Seev — Your worklog, without the work

Seev turns your real work—commits, PRs, and AI conversations—into a clean daily worklog. No copy‑pasting. No end‑of‑day scramble. Privacy‑first and local by default.

[Docs →](docs/index.md) · [Guides →](docs/guides/index.md) · [Troubleshooting →](docs/troubleshooting.md)

---

## Why Seev

- Automatically captures commits, PRs, and AI assistant conversations
- Generates structured, readable worklog entries (goals, work, metrics, decisions, impact, todo, learnings)
- MCP‑native: works with Claude Desktop, Cursor, Junie, Cline, and other MCP clients
- Local‑first: you control what’s logged and where it’s stored

---

## Quick Start

Copy this into your terminal to set up Seev and a local workspace:

```bash
curl -fsSL https://raw.githubusercontent.com/bcosynot/seev/main/seev-init.sh | bash -s
```

Then restart your MCP client so it can load the Seev server.

Add your first entry from your AI assistant by sending:

```text
/worklog_entry today
```

More examples and details are in Guides → Quick Start: docs/guides/quick-start.md

---

## Works with your MCP client

Seev is an MCP server and runs alongside your editor/assistant. For client‑specific setup (Cursor, Claude Desktop/Cline, Junie, VS Code, etc.), see:

- Guides → MCP clients: docs/guides/mcp-clients.md

---

## Configuration (essentials)

The init script creates a workspace and a config file you can edit later:

- Worklog file: WORKLOG.md
- Database: db.sqlite3
- Config file: ~/.config/seev/seev.toml

Track which commits are yours by listing your emails in the config:

```toml
# ~/.config/seev/seev.toml
track_emails = ["you@work.com", "you@personal.com", "yourgithubhandle@users.noreply.github.com"]
```

Environment variables can override paths and email tracking at runtime. See Guides → Workspace & Configuration: docs/guides/workspace-and-configuration.md

---

## What a worklog entry looks like

```markdown
## 2025-10-22

### 🎯 Goals & Context
- Refactor authentication module to support OAuth2 providers

### 💻 Technical Work
- abc1234: Extract OAuth2 provider interface

### 📊 Metrics
- Total commits: 3; Files changed: 8

### 🔍 Key Decisions
- Interface‑based design for new providers

### 🚧 Open Items
- Add integration tests for Google & GitHub

### 📚 Learnings
- ABCs fit this use case better than Protocols
```

Your assistant generates and saves this under the date heading in WORKLOG.md using Seev’s MCP tools.

---

## Privacy & Data

- Everything stays local: files and database on your machine
- Only repositories you configure are read
- Conversations are logged only when your assistant calls the recording tools

See docs/privacy-and-data.md for details.

---

## Requirements

- Python 3.13+
- Git
- An MCP‑compatible client (Claude Desktop, Cursor, Junie, Cline, …)

---

## Links

- Documentation: docs/index.md
- Guides: docs/guides/index.md
- Reference: docs/reference/index.md
- Troubleshooting: docs/troubleshooting.md
- GitHub: https://github.com/bcosynot/seev
- Contributing: docs/contributing.md
- License: LICENSE (see repository)

---

## Development (for contributors)

- Install deps: make sync
- Run tests: make test (or: uv run pytest)
- Format: make format; Lint: make lint
- Run MCP server: make run-stdio (stdio) · make run-http (port 8000)

For deeper development notes, see AGENTS.md and the docs/ folder.