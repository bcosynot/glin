# Workspace & Configuration

This guide explains how Seev stores data, how to configure tracked emails, and which environment variables and paths control behavior.

## Defaults at a glance

- Workspace directory: you choose (e.g., `~/seev-workspace`)
- Worklog file: `WORKLOG.md` in your workspace
- Database: `db.sqlite3` (or `seev.sqlite3`) in your workspace
- Config file: `~/.config/seev/seev.toml`

## Tracked emails (who you are in git)

Seev needs your git author emails to filter commits. Resolution order:

1. `SEEV_TRACK_EMAILS` environment variable (comma-separated)
2. `seev.toml` at one of:
   - `./seev.toml`
   - `~/.config/seev/seev.toml`
   - `~/.seev.toml`
3. Git fallback: `git config --get user.email` then `git config --get user.name`

!!! warning "Precedence gotcha"
    The environment variable takes precedence over the config file for the current process. If values look wrong, check `SEEV_TRACK_EMAILS` first, then your `seev.toml`.

### Configure via environment

```bash
export SEEV_TRACK_EMAILS="you@work.com,you@personal.com,handle@users.noreply.github.com"
```

### Configure via file (recommended)

Create or edit `~/.config/seev/seev.toml`:

```toml
# Seev Configuration
track_emails = [
  "you@work.com",
  "you@personal.com",
  "handle@users.noreply.github.com",
]
```

!!! tip
    You can point your MCP session at specific emails by setting the env var in your shell before launching the client.

## Workspace paths and env vars

The installer creates sensible defaults, but you can override at runtime:

- `SEEV_MD_PATH` — path to your worklog Markdown (default: `<workspace>/WORKLOG.md`)
- `SEEV_DB_PATH` — path to the sqlite database (default: `<workspace>/db.sqlite3`)
- `SEEV_TRACK_EMAILS` — comma-separated emails (overrides file config for the process)

Example:

```bash
export SEEV_MD_PATH=~/seev-workspace/WORKLOG.md
export SEEV_DB_PATH=~/seev-workspace/db.sqlite3
export SEEV_TRACK_EMAILS="you@work.com,you@personal.com"
```

## Verifying configuration with MCP tools

From your assistant, ask it to call these tools:

```text
/get_tracked_email_config
```

Expected: a snapshot of where emails were resolved from and the current values.

```text
/configure_tracked_emails method="env" emails=["you@work.com","you@personal.com"]
```

Expected: the process env is updated for the MCP server.

## Notes for deterministic tests

When writing tests or debugging:

- Unset the env var to exercise file/git fallbacks
- Prefer patching config helpers over invoking `git` directly
- Use a temporary directory for any file outputs
