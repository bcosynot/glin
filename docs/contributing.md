# Contributing

Thanks for your interest in improving Seev! This guide summarizes how to set up your environment, run tests, and open a high‑quality pull request.

## Development setup

- Python 3.13+
- Package manager: `uv` (recommended)

Install dependencies (including dev):

```
make sync
```

Format and lint:

```
make format
make lint
```

Run tests (quiet + coverage configured via pyproject):

```
make test
```

## Docs

We use MkDocs with Material and mkdocstrings.

- Build locally with strict checks:
  
  ```
  uv run mkdocs build --strict
  ```

- Reference pages pull docstrings directly; keep public functions and return types well‑typed.

## PR checklist

- [ ] Tests added or updated; `make test` passes locally.
- [ ] Code formatted and linted (`make format`, `make lint`).
- [ ] Docs updated when behavior or public API changes.
- [ ] Keep changes scoped and well‑described in the PR body.

## Project conventions

- Type hints: prefer precise TypedDicts or dataclasses for structured results.
- Tests: pytest + pytest‑cov; use monkeypatch for env and filesystem isolation.
- Tools registration: MCP tools register at import via the shared `seev.mcp_app.mcp` instance.

## Getting help

Open an issue in the repository or draft a PR for discussion.
