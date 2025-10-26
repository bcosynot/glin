# Troubleshooting & FAQ

Use the links below to jump to specific issues.

- [fastmcp import error](#fastmcp-import-error)
- [Git repository not found](#git-repository-not-found)
- [Tracked emails not configured](#tracked-emails-not-configured)
- [Markdown path problems](#markdown-path-problems)
- [MkDocs strict build fails](#mkdocs-strict-build-fails)

## fastmcp import error

Symptoms: `ModuleNotFoundError: No module named 'fastmcp'` when running the server.

Cause: The runtime environment is missing the FastMCP dependency.

Fix:
- Run `make sync` (or `uv sync --group dev`).
- Verify `uv run python -c "import fastmcp; print(fastmcp.__version__)"` works.
- In tests, Seev stubs FastMCP automatically; you should not need the package to run unit tests.

## Git repository not found

Symptoms: Git tools return an error like `Not a git repository` or empty results.

Cause: The `workdir` argument points outside a git repo, or no repo exists in the current directory.

Fix:
- Ensure you pass `workdir` into git MCP tools pointing inside a repo.
- Initialize a repo: `git init` and commit at least once.
- Use the Troubleshooting tip in tool descriptions that accept `workdir`.

## Tracked emails not configured

Symptoms: Tools that need author filters cannot determine your identity.

Cause: No tracked emails were found via env, config file, or git fallback.

Fix:
- Quick start (env): `export SEEV_TRACK_EMAILS="user@ex.com,other@ex.com"`.
- File-based (recommended for persistence):
  - Create `seev.toml` at project root with:
    ```toml
    # Seev Configuration
    track_emails = ["user1@example.com", "user2@example.com"]
    ```
  - Or place it at `~/.config/seev/seev.toml` or `~/.seev.toml`.
- Programmatic: call the `configure_tracked_emails` MCP tool.

## Markdown path problems

Symptoms: `append_to_markdown` writes to an unexpected file, or headings are duplicated.

Cause: Mixing `SEEV_MD_PATH` and explicit `file_path`, or running on Windows with CRLF newlines in an existing file.

Fix:
- Prefer a single source of truth: set `SEEV_MD_PATH` or pass `file_path`, not both.
- The function normalizes to Unix newlines on write; open existing files with a UTF-8 aware editor.
- Use `read_date_entry` to inspect the current structure before writing.

## MkDocs strict build fails

Symptoms: `mkdocs build --strict` fails due to broken links or import errors.

Fix:
- Ensure `mkdocstrings` can import packages: run `make sync` first.
- Verify module names in reference pages are correct (e.g., `seev.git_tools.commits`).
- Check cross-page links (e.g., `[MCP Tools](reference/mcp-tools.md)`).
- Run `uv run mkdocs build --strict` locally to see detailed errors.

> Tip: All headings on this page use semantic h2/h3 so anchor links remain stable.