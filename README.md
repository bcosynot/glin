# **Glin**
*Your worklog, without the work.*

---

### ✨ What is Glin?
**Glin** is an [MCP server](https://modelcontextprotocol.io/) that **automatically builds your worklog** from two places you already live in:

- The **prompts and conversations** you have with your **agentic coding assistant**
- Your **git history**

No more manual logging. No more "what did I even do today?" moments.  
Glin captures your flow of work as it happens — transparently, in the background — and turns it into a clean, searchable record.

---

### 🔮 Why Glin?
Developers spend hours *doing*, but often forget the **telling**:
- Daily standups
- Sprint updates
- Performance reviews
- Knowledge transfer

Glin flips the script: your tools already know what you did — it just makes that knowledge **visible**.

Think of it as a **black box recorder for your dev work**: light, ambient, and surprisingly insightful.

---

### ⚡ Key Features
- **Transparent logging**: Captures coding activity without interrupting your flow
- **Git + AI context**: Merges commit history with assistant interactions
- **Flexible email tracking**: Configure multiple email addresses to track commits from
- **Human-friendly summaries**: Turn messy traces into readable narratives
- **MCP-native**: Integrates with any client that speaks MCP
- **Privacy-first**: You control what gets logged, stored, or shared



---

### ⚙️ Configuration

Glin supports multiple ways to configure which email addresses to track commits from:

#### 1. Environment Variable (Highest Priority)
Set the `GLIN_TRACK_EMAILS` environment variable with a comma-separated list of emails:
```bash
export GLIN_TRACK_EMAILS="user1@example.com,user2@example.com,team@company.com"
```

#### 2. Configuration File
Create a `glin.toml` file in one of these locations:
- Current directory: `./glin.toml`
- User config: `~/.config/glin/glin.toml`
- User home: `~/.glin.toml`

Example `glin.toml`:
```toml
# Glin Configuration
# List of email addresses to track commits from
track_emails = ["user1@example.com", "user2@example.com", "team@company.com"]
```

#### 3. Git Configuration (Fallback)
If no explicit configuration is found, Glin falls back to your git configuration:
- `git config user.email` (preferred)
- `git config user.name` (if email not set)

#### MCP Tools for Configuration
Glin provides MCP tools to manage email configuration:
- `get_tracked_email_config`: View current configuration
- `configure_tracked_emails`: Set email addresses via environment variable or config file

---

### 📝 MCP Prompts for Worklog Generation

Glin provides server-side prompt templates that LLM clients can use to generate summaries and worklogs. These prompts are discoverable via the MCP protocol and return message sequences ready for client-side LLM processing.

#### Available Prompts

1. **`commit_summary`** - Summarize Git commits with types, scopes, and notable changes
   - Required: `commits` (string) - commit data to summarize
   - Optional: `date_range` (string) - time period for context
   - Tags: `["summary", "git", "commits"]`

2. **`diff_summary`** - Analyze code diffs and identify impacts
   - Required: `diff` (string) - unified diff or patch
   - Optional: `context` (string) - additional context
   - Tags: `["summary", "analysis", "git", "diff"]`

3. **`worklog_entry`** - Generate daily worklog entries
   - Required: `date` (string) - date in ISO format (YYYY-MM-DD)
   - Required: `inputs` (string) - commits, diffs, or notes
   - Tags: `["worklog", "summary", "daily"]`

4. **`pr_review_summary`** - Create reviewer-oriented PR summaries
   - Required: `title` (string) - PR title
   - Optional: `description`, `diffs`, `commits` (strings)
   - Tags: `["review", "summary", "analysis", "pr"]`

#### Using Prompts with MCP Clients

List available prompts:
```python
from fastmcp import Client

async with Client("http://localhost:8000/mcp") as client:
    prompts = await client.list_prompts()
    for prompt in prompts:
        print(f"{prompt.name}: {prompt.description}")
```

Render a prompt with arguments:
```python
# Get commit data from git tools
commits_result = await client.call_tool("get_commits_by_date", {
    "since": "2025-10-09",
    "until": "2025-10-09"
})

# Render the prompt
messages = await client.get_prompt("commit_summary", {
    "commits": commits_result,
    "date_range": "2025-10-09"
})

# Send to your LLM
summary = await your_llm.complete(messages)
```

#### Argument Serialization

FastMCP automatically handles JSON serialization for complex arguments:
- Multi-line strings work seamlessly
- Special characters are preserved
- Large diffs and commit logs are supported

For very large inputs (>100KB), consider:
- Chunking by date ranges or file paths
- Filtering to relevant commits only
- Using selective diff contexts

#### Date Formatting

Use ISO 8601 format (YYYY-MM-DD) for dates:
```python
await client.get_prompt("worklog_entry", {
    "date": "2025-10-09",
    "inputs": "..."
})
```

Human-friendly ranges work in `date_range` arguments:
- `"2025-10-01 to 2025-10-09"`
- `"yesterday"`
- `"last week"`

---

### 🗄️ Storage and integration flags

Phase 2 introduces an optional local SQLite storage used by some tools. By default, no database writes occur unless explicitly enabled.

- Database path: set with `GLIN_DB_PATH` (e.g., `~/.glin/db.sqlite3`). If unset, modules that use storage will fall back to the default `~/.glin/db.sqlite3` in your home directory.
- Auto-write: enable side-effectful persistence from certain tools by setting `GLIN_DB_AUTOWRITE` to a truthy value (`1`, `true`, `yes`, `on`). When enabled, git commit queries may upsert fetched commits into the database.
- Backups: you can create a timestamped backup of the database using the storage helper `create_backup()`. Backups are written to `.glin/backups/YYYYMMDD/HHMMSS/<db-file>` by default.
- Status: use `get_db_status()` to inspect the schema version and row counts per table.

Example (shell):
```bash
export GLIN_DB_PATH="$HOME/.glin/db.sqlite3"
export GLIN_DB_AUTOWRITE=1
```

---

### 🧾 Server-side logging outputs

By default, Glin’s server logs go to the same place as the process stdout/stderr (your terminal, `docker logs`, or `journalctl`, depending on how you run it). To persist logs to a file, set an environment variable before starting the server:

```bash
# Write server logs to a specific file (directories will be created if missing)
export GLIN_LOG_PATH="$HOME/.glin/logs/server.log"

# Optional tuning (shown with defaults)
export GLIN_LOG_LEVEL=INFO           # one of: DEBUG, INFO, WARNING, ERROR
export GLIN_LOG_STDERR=1             # keep stderr handler (set to 0 to disable)
export GLIN_LOG_ROTATE=1             # use rotation (RotatingFileHandler)
export GLIN_LOG_MAX_BYTES=5242880    # ~5 MB per file when rotating
export GLIN_LOG_BACKUPS=3            # keep 3 rotated backups
```

Notes
- This controls standard server-side logging (e.g., from `fastmcp.utilities.logging.get_logger("glin.*")`).
- MCP context logs (`ctx.debug/info/warning/error`) still go to the MCP client; use them for user-visible progress.
- If `GLIN_LOG_PATH` is not set, logging behaves as before (console-only).

---

### 🧪 Running tests
This project uses pytest with coverage configured in pyproject.toml. You can run the test suite either directly or via the provided Makefile target.

Prerequisites:
- Python 3.13+
- uv (recommended)

Install dependencies with uv:
1) Install uv if you don't have it yet: https://docs.astral.sh/uv/
2) Sync project and dev dependencies:
   uv sync --group dev

Run tests:
- Using Makefile:
   make test
- Or directly with uv:
   uv run pytest

Notes:
- Coverage is enabled by default via pyproject addopts and will print a summary to the terminal and write coverage.xml in the repo root.
- Tests live under the tests/ directory and follow the patterns test_*.py or *_test.py.

---

### 🧰 Developer tooling (Ruff + Git hook)
This repository includes a Git pre-commit hook that auto-formats code and applies Ruff autofixes using uv.

Set up the hook once per clone:
1) Ensure dependencies are installed:
   uv sync --group dev
2) Point Git to the repo-managed hooks and make the hook executable:
   make hooks
   # Equivalent to:
   # git config core.hooksPath .githooks
   # chmod +x .githooks/pre-commit

What the hook does:
- Runs: `uv run ruff format`
- Runs: `uv run ruff check --fix`
- Stages any changes so your commit includes the fixes

Run tooling manually if needed:
- Format: `make format` or `uv run ruff format`
- Lint (with fixes): `make lint` or `uv run ruff check --fix`
- Install deps: `make sync` or `uv sync --group dev`
