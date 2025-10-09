# Glin Development Guidelines (project-specific)

Last verified: 2025-10-09 (local time)

This document captures build, testing, and development conventions that are specific to this repository. It assumes an advanced Python developer.

---

## Build, setup, and configuration

- Runtime/tooling
  - Python: 3.13+ (project is configured for `py313`).
  - Package/deps: uv (recommended) — uses `pyproject.toml` and `uv.lock`.
  - Lint/format: Ruff (formatter + linter), configured in `pyproject.toml`.
  - Tests: pytest + pytest-cov.

- Dependency sync
  - Preferred: `uv sync --group dev` (installs main + dev dependencies).
  - Make target: `make sync` will assert `uv` is installed and run the above.
  - Devcontainer: `.devcontainer/devcontainer.json` uses Python 3.13 image and installs uv; `postCreateCommand` runs `uv sync --dev`.

- Executing the MCP server (for manual runs)
  - Entry point: `main.py` calls `glin.mcp_app.run()`.
  - Transports:
    - Default transport: `stdio`
    - HTTP transport: pass `--transport http` to `run()`; the server will bind to port 8000. The logic lives in `glin/mcp_app.py` lines 16–27.
  - Make targets (recommended):
    - `make run-stdio` → runs `uv run python main.py` (stdio transport, default)
    - `make run-http` → runs `uv run python main.py --transport http` (HTTP transport on port 8000)
  - Manual execution examples:
    - `python -m glin.mcp_app` (stdio) — if you add your own CLI.
    - `python main.py` (stdio), or `python -c "from glin.mcp_app import run; run(['script.py','--transport','http'])"` (HTTP).

- Email tracking configuration (central to Git tooling)
  - Precedence (implemented in `glin/config.py`):
    1. `GLIN_TRACK_EMAILS` env var (comma-separated). Example: `export GLIN_TRACK_EMAILS="user1@ex.com,user2@ex.com"`.
    2. `glin.toml` file at one of:
       - `./glin.toml`
       - `~/.config/glin/glin.toml`
       - `~/.glin.toml`
       Content format:
       ```toml
       # Glin Configuration
       track_emails = ["user1@example.com", "user2@example.com"]
       ```
    3. Git fallback: `git config --get user.email` (preferred), then `git config --get user.name`.
  - Programmatic helpers:
    - `get_tracked_emails()` → list[str]
    - `set_tracked_emails_env(emails: list[str])` → sets env var for current process
    - `create_config_file(emails, path?)` → writes TOML with `track_emails`
  - MCP tools (via `glin/git_tools.py`):
    - `get_tracked_email_config` — returns current config snapshot
    - `configure_tracked_emails` — set via env (`method='env'`) or file (`method='file'`)

---

## Testing: how it's wired here

- Invocation
  - Preferred: `uv run pytest` (or `make test` which chooses `uv` when available).
  - Quiet + coverage are configured by default via `pyproject.toml`:
    - `addopts = "-q --cov=glin --cov-report=term-missing --cov-report=xml:coverage.xml"`
    - Patterns: `testpaths = ["tests"]`, `python_files = ["test_*.py", "*_test.py"]`.

- What to expect
  - Tests are hermetic and rely on patching/mocking (no network, no real git needed for unit tests).
  - The MCP server object `mcp` is patched in tests; you do not need to run a server for tests.
  - On 2025-10-09, a full run (`uv run pytest -q`) produced 100% passing tests and wrote `coverage.xml`; summary at the time showed ~85% project coverage with module breakdown (see CI logs/terminal for exact numbers).

- Adding new tests (project conventions)
  - Place tests under `tests/` with filenames matching the patterns above.
  - Use `pytest.monkeypatch` for environment and filesystem isolation. Examples:
    - For config: monkeypatch `GLIN_TRACK_EMAILS`.
    - For git-dependent code in `glin/git_tools`, prefer patching `subprocess.run` or the high-level helpers. See `tests/test_git_tools.py` for patterns, including the `make_run` helper that matches command prefixes to mocked results.
  - For filesystem interactions (e.g., `markdown_tools.append_to_markdown`):
    - Use `tmp_path` and override CWD or pass explicit `file_path` to avoid writing into the repo.
    - The function normalizes newlines, creates parent dirs, and ensures a date-scoped `## YYYY-MM-DD` heading; tests assert structure and positions (line numbers returned in the result dict).
  - Keep tests deterministic across developer machines:
    - If behavior can vary with local git config, patch `glin.config._get_config_file_emails` and/or `glin.config._get_git_author_pattern` in tests to the desired value.

- Demonstration: create and run a simple test
  - We validated the following example end-to-end on 2025-10-09.
  - Example file (temporary): `tests/test_demo_example.py`
    ```python
    def test_demo_config_env(monkeypatch):
        monkeypatch.setenv("GLIN_TRACK_EMAILS", "a@b.com,b@c.com")
        from glin.config import get_tracked_emails
        assert get_tracked_emails() == ["a@b.com", "b@c.com"]

    def test_demo_unset_env(monkeypatch):
        # Make deterministic regardless of local git config
        monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)
        import glin.config as cfg
        monkeypatch.setattr(cfg, "_get_config_file_emails", lambda: [])
        monkeypatch.setattr(cfg, "_get_git_author_pattern", lambda: None)
        from glin.config import get_tracked_emails
        assert get_tracked_emails() == []
    ```
  - Run:
    - `uv sync --group dev`
    - `uv run pytest -q`
  - Result on 2025-10-09: all tests passed locally; coverage was generated per `pyproject.toml`.
  - Cleanup: remove the demo file when done (keep repo clean).

---

## Additional development notes (project-specific)

- Code style and quality
  - Ruff is both formatter and linter; configurations in `pyproject.toml`:
    - Target version: `py313`; line length: 100.
    - Lint rules: `select = ["E", "W", "F", "I", "UP", "B"]` with autofix enabled.
    - Format preferences: double quotes, space indent, docstring code formatting on.
  - Do NOT use `from __future__ import annotations` anywhere in the codebase. Python 3.13 already stringizes annotations by default; the future import is unnecessary and can mask type issues. Remove it if you see it in any file.
  - Make targets:
    - `make format` → `uv run ruff format`
    - `make lint` → `uv run ruff check --fix`
    - `make hooks` → enables repo-managed pre-commit that formats + fixes before commit.

- Git/MCP tool behaviors worth remembering
  - `glin/git_tools.py` uses `get_tracked_emails()` to build multiple `--author=...` filters for `git log`; when no emails are configured it returns an error entry instead of querying git.
  - `get_commits_by_date(since, until)` uses human-friendly ranges (`yesterday`, `1 week ago`, `YYYY-MM-DD`). Returns `[{"info": "No commits found in date range"}]` when empty.
  - The public MCP tools are registered via decorators attached to a single shared `FastMCP` instance (`glin/mcp_app.py`). Import order intentionally creates that instance first, then imports tool modules so their decorators register on the same instance.

- Filesystem and newline semantics in `markdown_tools.append_to_markdown`
  - Default target file is `./WORKLOG.md`, overridden by `file_path` argument or `GLIN_MD_PATH`.
  - Ensures Unix newlines, heading for today (`## YYYY-MM-DD`), and correct blank-line spacing around sections.
  - Returns a rich dict (path, bullets added, line numbers, whether heading was added, etc.) to aid calling clients and tests.

- Tips for writing robust tests here
  - Prefer patching at module boundaries (e.g., monkeypatch `subprocess.run` in git tools) rather than deep internals.
  - Avoid relying on the developer's global environment: always set/clear env vars and patch git/config fallbacks.
  - When asserting multi-line file edits, normalize newlines and compare structural markers (headings, bullet positions) rather than raw byte offsets.

- Common pitfalls
  - Importing `glin.mcp_app` creates the shared `FastMCP` instance; tests patch `mcp` where needed. Ensure `fastmcp` is available in your environment (`uv sync`) when executing runtime code outside tests.
  - Running git commands requires a repository and author filters; unit tests simulate these via mocks.

---

## Quick commands

- Install deps: `make sync`
- Run tests: `make test` (or `uv run pytest`)
- Format: `make format`
- Lint/fix: `make lint`
- Install git hook: `make hooks`
- Run MCP server (stdio): `make run-stdio`
- Run MCP server (HTTP): `make run-http`

---

Housekeeping for this session (2025-10-09)
- Verified `uv` availability and installed dev dependencies.
- Ran full test suite successfully.
- Created, executed, and then removed a temporary demo test for documentation purposes (see Testing section for the exact snippet).


---

## Modules and directory structure (updated 2025-10-09)

- Top-level package: `glin/`
  - `mcp_app.py` — creates and runs the shared FastMCP instance; imports tool modules so their decorators register on the same instance.
  - `config.py` — configuration helpers (e.g., tracked emails resolution with env/file/git fallbacks).
  - `markdown_tools.py` — filesystem-safe Markdown utilities (newline normalization, date headings, etc.).
  - `git_tools/` — NEW: refactored package replacing the previous single-file implementation. Submodules:
    - `branches.py` — branch-related utilities and MCP tools.
    - `commits.py` — commit queries and date-range helpers.
    - `config_tools.py` — tracked-email configuration tools used by MCP.
    - `diffs.py` — diff and patch helpers.
    - `files.py` — file-level Git helpers.
  - Compatibility shim: `git_tools.py` — maintained for backward compatibility; re-exports the public API to preserve existing imports (e.g., `from glin.git_tools import get_commits_by_date`). New code SHOULD prefer explicit imports from `glin.git_tools.<module>`.

Notes
- Tests were updated to patch module-level functions in the new package layout. When writing tests, patch `glin.git_tools.<module>.<name>` rather than deep internals.
- The public API is preserved; the shim is intended to ease migration for external users.

## Type annotations: arguments and returns

- Always annotate function/method arguments and return types in new or modified code.
- Prefer concrete, structured types over plain dict or list when the shape is known:
  - Use TypedDict (with total or total=False) or dataclasses for mapping-shaped results.
  - Use Literal and unions for well-defined variant responses (e.g., success vs error).
  - Example (simplified):
    ```python
    from typing import TypedDict

    class ErrorResponse(TypedDict):
        error: str

    class Item(TypedDict):
        id: str
        name: str

    def get_items(limit: int = 10) -> list[Item] | ErrorResponse:
        ...
    ```
- MCP tool wrappers should mirror the return type of the underlying helper.
- Keep types import-light and Python 3.13 native (builtins like list[str]) and align with Ruff.

## After every task: format and lint

Run Ruff formatter and linter before marking a task complete or opening/refreshing a PR. Use Makefile targets (preferred):

- Format: `make format`  (runs `uv run ruff format`)
- Lint/fix: `make lint`  (runs `uv run ruff check --fix`)

Alternative direct commands if you are not using Make:

- `uv run ruff format`
- `uv run ruff check --fix`

Tip: Install the repo-managed pre-commit hook once to auto-run formatting and fixes on commit:

- `make hooks`
