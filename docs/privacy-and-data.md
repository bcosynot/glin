# Privacy & Data

Seev is designed with local-first principles:

- Local storage by default: Conversations and worklog files are stored on your machine. Git data is read from your local repositories unless you explicitly connect remote services via other MCP servers.
- Minimal logging: By default, only console logs are emitted. You can opt into file logging via environment variables (see below).
- No telemetry: The project does not send usage data.

## Logging controls

Seev can write server-side logs when running the MCP server. Configure via environment variables before start (seev.mcp_app.run reads these):

- SEEV_LOG_PATH: File path for log output. When set, a file handler is attached (parents are created as needed).
- SEEV_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR. Default: INFO.
- SEEV_LOG_STDERR: If truthy (default 1), keep a stderr stream handler.
- SEEV_LOG_ROTATE: If truthy (default 1), rotate logs instead of a single growing file.
- SEEV_LOG_MAX_BYTES: Max size per rotated file (default ~5MB).
- SEEV_LOG_BACKUPS: Number of rotated backups to keep (default 3).

Example:

```
export SEEV_LOG_PATH="$HOME/.local/state/seev/seev.log"
export SEEV_LOG_LEVEL=DEBUG
```

## Worklog location

The markdown worklog file path is resolved by `seev.config.get_markdown_path()`:
- Default: `./WORKLOG.md` in the current working directory.
- Override via env var `SEEV_MD_PATH`.
- Many tools accept an explicit `file_path` argument that, when provided, takes precedence over env/default.

## Tracked identity

Your commit identity for filtering is resolved by `seev.config.get_tracked_emails()` with precedence:
1) `SEEV_TRACK_EMAILS` environment variable (comma-separated)
2) `seev.toml` at `./seev.toml`, `~/.config/seev/seev.toml`, or `~/.seev.toml`
3) Git fallback: `git config --get user.email` then `git config --get user.name`

Use the `configure_tracked_emails` MCP tool to set these programmatically.

## Data you control

- Conversations: stored locally via `seev.storage` helpers. You can delete files to erase history.
- Worklogs: plain Markdown files; edit or remove as you wish.
- Logs: opt-in file path; delete the log file to clear history.

## External services

Seev itself does not call remote APIs. If you run your agent with additional MCP servers (e.g., GitHub), those servers have their own privacy characteristics. Review their docs and configure credentials carefully.
