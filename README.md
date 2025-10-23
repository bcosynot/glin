# **Glin**
*Your worklog, without the work.*

---

## Why Glin?

As an experienced developer, you know the drill: daily standups, sprint updates, performance reviews, knowledge transfer. 
You spend hours *doing* the work, but documenting it? That's where the friction starts.

**Glin solves this.** It's an [MCP server](https://modelcontextprotocol.io/) that automatically builds your worklog from tools you're already using:

- **Your git commits** — the actual code changes you makey
- **Pull requests** — PRs you authored and reviewed
- **Your AI assistant conversations** — the context, decisions, and problem-solving

No manual logging. No "what did I even do today?" moments. Glin captures your flow of work transparently and turns it into clean, searchable records.

### What You Get

- **Automatic work capture**: Your commits and AI conversations become structured worklog entries
- **Rich context**: Correlates commits with conversations, PRs, and issues
- **Structured summaries**: Goals, technical work, metrics, decisions, impact, learnings
- **Privacy-first**: Everything stays local. You control what gets logged and shared
- **MCP-native**: Works with any AI assistant that supports MCP (Claude Desktop, Cursor, Junie, Cline, etc.)

---

## Quick Start

### 1. Add Glin to Your AI Coding Assistant

Glin works with any MCP-compatible client. Here's how to set it up:

#### Claude Desktop

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "glin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/glin.git", "glin"]
    }
  }
}
```

#### Cursor

Add to Cursor's MCP settings file:

**macOS/Linux**: `~/.cursor/mcp.json`  
**Windows**: `%USERPROFILE%\.cursor\mcp.json`

```json
{
  "mcpServers": {
    "glin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/glin.git", "glin"]
    }
  }
}
```

#### Cline (VS Code Extension)

Add to Cline's MCP settings in VS Code settings:

```json
{
  "cline.mcpServers": {
    "glin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/glin.git", "glin"]
    }
  }
}
```

#### Local Development Setup

If you're developing or want to run from a local clone:

```json
{
  "mcpServers": {
    "glin": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/glin", "python", "main.py"]
    }
  }
}
```

**Note**: After updating your config, restart your AI assistant to load the Glin MCP server.

---

### 2. Initialize Your Workspace

Once Glin is connected to your AI assistant, initialize a workspace to store your worklog:

**Ask your AI assistant:**

> "Use the init_glin tool to create a workspace at ~/glin-workspace"

**What happens:**
- Creates `WORKLOG.md` for your entries
- Sets up `db.sqlite3` for tracking commits and conversations
- Generates `~/.config/glin/glin.toml` with paths configured

If the workspace already exists, Glin will confirm it's ready without modifying files.

---

### 3. Generate Your First Worklog Entry

Now the magic happens. Ask your AI assistant to create a worklog entry:

**Simple daily entry:**

> "/worklog_entry today"

**Specific date:**

> "/worklog_entry 2025-10-20"

**Date range:**

> "/worklog_entry last week"

**What your AI assistant does:**

1. **Gathers context** using Glin's MCP tools:
   - Fetches your git commits for the period
   - Retrieves conversation history
   - Collects PR and issue activity (if GitHub MCP is available)
   - Calculates code metrics (additions, deletions, files changed)

2. **Correlates data**:
   - Matches commits to conversations
   - Links PRs to commits
   - Identifies merge commits and branch activity

3. **Generates structured markdown** with sections:
   - 🎯 **Goals & Context**: What you set out to do
   - 💻 **Technical Work**: Commits, PRs, reviews
   - 📊 **Metrics**: Commit counts, code changes, files touched
   - 🔍 **Key Decisions**: Important choices and rationale
   - ⚠️ **Impact Assessment**: Risks, dependencies, compatibility
   - 🚧 **Open Items**: TODOs, blockers, follow-ups
   - 📚 **Learnings**: Insights, patterns, gotchas

4. **Saves to WORKLOG.md** automatically under the date heading

**Example worklog entry:**

```markdown
## 2025-10-22

### 🎯 Goals & Context
- Refactor authentication module to support OAuth2 providers
- Fix critical bug in payment flow causing transaction failures
- Review team PRs for the dashboard redesign

### 💻 Technical Work
- [abc123f](https://github.com/org/repo/commit/abc123f) Refactor: Extract OAuth2 provider interface
- [def456a](https://github.com/org/repo/commit/def456a) Fix: Handle null payment tokens in checkout flow
- [ghi789b](https://github.com/org/repo/commit/ghi789b) Test: Add integration tests for OAuth2 flows
- Reviewed PR #234: Dashboard UI components (approved with suggestions)

### 📊 Metrics
- Total commits: 3
- Additions: +245, Deletions: -89
- Files changed: 8 (Python: 6, TypeScript: 2)
- PRs reviewed: 1

### 🔍 Key Decisions
- Chose interface-based design for OAuth2 to support multiple providers without tight coupling
- Decided to add null checks in payment flow rather than enforce non-null at API level (backward compatibility)

### ⚠️ Impact Assessment
- OAuth2 refactor affects all authentication flows; requires thorough testing before release
- Payment fix is backward-compatible; safe to deploy immediately
- Dashboard PR introduces new dependencies (chart.js); needs security review

### 🚧 Open Items
- Complete OAuth2 integration tests for Google and GitHub providers
- Schedule security review for dashboard dependencies
- Document OAuth2 configuration for deployment team

### 📚 Learnings
- Python's ABC module provides cleaner interface definitions than Protocol for this use case
- Payment gateway returns empty strings instead of null for missing tokens; need defensive checks
```

---

## Configuration

### Email Tracking

Glin needs to know which commits are yours. Configure email tracking in order of priority:

The `init_glin` tool creates `~/.config/glin/glin.toml`. Edit it to add your emails:

```toml
# Glin Configuration
track_emails = ["you@work.com", "you@personal.com", "yourgithubhandle@users.github.com"]
```

### Workspace Paths

By default, `init_glin` creates:
- Worklog: `<workspace>/WORKLOG.md`
- Database: `<workspace>/db.sqlite3`
- Config: `~/.config/glin/glin.toml`

---

## Advanced Usage

### Multiple Repositories

Track commits across multiple repos by configuring tracked repositories:

```toml
# ~/.config/glin/glin.toml
track_repositories = [
  "/path/to/local/repo",
  "github-org/repo-name",
  "https://github.com/org/another-repo.git"
]
```

When generating worklog entries, Glin will include commits and PRs from all tracked repositories.

### Custom Date Ranges

The `worklog_entry` prompt accepts flexible date formats:

- **Single day**: `2025-10-22` or `today` or `yesterday`
- **Relative**: `last 2 days`, `last week`, `1 week ago`
- **Range**: `2025-10-15..2025-10-22`

Examples:

> "Create a worklog entry for yesterday"

> "Generate worklog entries for the last 2 weeks"

> "Create a worklog for October 15-22, 2025"

### GitHub Integration

If you have the [GitHub MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/github) configured, Glin automatically enriches worklog entries with:

- Pull request details (title, state, reviews)
- Issue references and correlations
- PR comments and review activity
- Branch merge context

No additional configuration needed — Glin detects and uses the GitHub MCP when available.

---

## MCP Tools Reference

Glin provides these MCP tools for your AI assistant:

### Workspace Management
- **`init_glin`**: Initialize a workspace with WORKLOG.md, database, and config

### Git Tools
- **`get_commits_by_date`**: Fetch commits for a date range
- **`get_recent_commits`**: Get recent commits (default: last 10)
- **`get_commit_diff`**: View code changes for a specific commit
- **`get_commit_files`**: List files changed in a commit
- **`get_enriched_commits`**: Get commits with stats and categorization
- **`get_current_branch`**: Show current branch info
- **`list_branches`**: List all branches with metadata

### Conversation Tracking
- **`record_conversation_message`**: Log AI assistant conversations
- **`get_recent_conversations`**: Retrieve recent conversation history
- **`link_commit_to_conversation`**: Associate commits with conversations

### Worklog Generation
- **`append_to_markdown`**: Add content to WORKLOG.md under a date heading
- **`generate_rich_worklog`**: Create structured worklog with all sections

### Configuration
- **`get_tracked_email_config`**: View current email tracking config
- **`configure_tracked_emails`**: Set tracked emails via env or file

---

## MCP Prompts Reference

Glin provides server-side prompts that your AI assistant can use:

### `worklog_entry`

Generate a comprehensive worklog entry for a date or period.

**Required arguments:**
- `date`: Target day or period (e.g., `2025-10-22`, `yesterday`, `last week`)
- `inputs`: Your notes, context, or goals for the period

**What it does:**
1. Gathers commits, conversations, PRs, and metrics
2. Correlates commits with conversations and PRs
3. Generates structured markdown with all sections
4. Saves to WORKLOG.md automatically

**Usage:**

> "Use the worklog_entry prompt for today. My inputs: worked on authentication refactor and bug fixes."

---

## Troubleshooting

### "No commits found"

**Cause**: Email tracking not configured or no commits match your email.

**Fix**: Configure `glin.toml` with your email addresses.

### "Workspace not initialized"

**Cause**: `init_glin` hasn't been run yet.

**Fix**: Ask your AI assistant to run `init_glin` with a workspace path.

### "Git tools unavailable"

**Cause**: Not in a git repository or git not installed.

**Fix**: Ensure you're in a git repository and git is in your PATH.

### MCP server not loading

**Cause**: Config file syntax error or incorrect path.

**Fix**: 
1. Validate JSON syntax in your MCP config file
2. Restart your AI assistant after config changes
3. Check logs for error messages

---

## Development & Testing

### Running Tests

```bash
# Install dependencies
uv sync --group dev

# Run test suite
make test
# or
uv run pytest
```

### Code Quality

```bash
# Format code
make format

# Lint and fix
make lint

# Install pre-commit hook
make hooks
```

### Running the Server Manually

```bash
# Stdio transport (default)
make run-stdio

# HTTP transport (port 8000)
make run-http
```

### Server Logging

Enable detailed logging for debugging:

```bash
export GLIN_LOG_PATH="~/.glin/logs/server.log"
export GLIN_LOG_LEVEL=DEBUG
```

---

## Privacy & Data

**Everything stays local.** Glin:
- Stores data in your local filesystem
- Never sends data to external services
- Only accesses git repos you explicitly configure
- Logs conversations only when your AI assistant calls the recording tools

You control:
- What gets logged (via email tracking config)
- Where data is stored (via workspace paths)
- What gets shared (you decide what to commit or share from WORKLOG.md)

---

## Requirements

- **Python**: 3.13+
- **Git**: For commit tracking
- **uv**: Package manager (recommended)
- **MCP-compatible AI assistant**: Claude Desktop, Cursor, Cline, etc.

---

## License

[Add your license here]

---

## Contributing

Contributions welcome! Please:
1. Run tests: `make test`
2. Format code: `make format`
3. Lint: `make lint`
4. Submit PR with clear description

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/glin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/glin/discussions)
- **Documentation**: This README and inline code documentation
