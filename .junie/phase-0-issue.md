Title: Phase 0 — Repo hygiene and baseline (MkDocs dev deps)

Summary
Set up local development prerequisites for the MkDocs site so any contributor can run and build docs locally using Python 3.13 and uv.

Why
- Enables `mkdocs serve` and required plugins locally.
- Establishes the baseline to build later phases.

Scope and Deliverables
- Add dev dependencies to the project for docs work.
- Verify the toolchain works end-to-end locally.

Files to touch
- pyproject.toml (dev dependencies)
- uv.lock (will update automatically)

Commands (run from repo root)
- uv add --dev mkdocs-material mkdocstrings[python] mike mkdocs-git-revision-date-localized-plugin
- uv run mkdocs --version

Acceptance/Verification
- pyproject.toml lists the new dev dependencies under the dev group.
- uv.lock updated.
- `uv run mkdocs --version` prints a version without error.

Junior implementation notes
- Use Python 3.13+ and uv as the package manager (project standard).
- Prefer the Makefile targets when available (`make sync`, `make format`, `make lint`).
- After installing, you can sanity-check with: `uv run mkdocs build --strict` (builds an empty skeleton for now).

Relevant requirements (inlined)
- Dev dependencies: mkdocs-material, mkdocstrings[python], mike, mkdocs-git-revision-date-localized-plugin.
- Target runtime: Python 3.13; docs are Markdown-first with automated deploys.
