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

## Optional analytics (docs site)

The published documentation site can optionally use [Plausible Analytics](https://plausible.io/), a lightweight, privacy‑friendly analytics tool. This is disabled by default and ships as opt‑in.

What ships by default
- The site includes a tiny loader at `docs/js/analytics.plausible.js` that does nothing unless explicitly enabled.
- No third‑party requests are made without your action.

How to enable (docs maintainers)
1) Edit `mkdocs.yml` and add a Plausible domain meta tag under `extra.meta`:
   ```yaml
   extra:
     meta:
       - name: "plausible:domain"
         content: "docs.example.com"  # your docs domain
   ```
2) (Recommended) Add an SRI hash for Plausible’s script to enforce Subresource Integrity. Note that Plausible occasionally updates the script; you must refresh this hash when upgrading.
   ```yaml
   extra:
     meta:
       - name: "plausible:sri"
         content: "sha384-REPLACE_WITH_VALID_HASH"
   ```
3) Rebuild the site: `uv run mkdocs build --strict`.

How it works
- On page load, the loader looks for `meta[name="plausible:domain"]`. If found, it injects the official `https://plausible.io/js/script.js` with `defer` and `crossorigin="anonymous"`. If an SRI meta is present, it sets `integrity` accordingly.
- If the meta is absent (default in this repo), analytics remains OFF.

Data policy
- Plausible does not use cookies and does not collect PII. See their published policy for details.
