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
