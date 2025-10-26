Title: Phase 6 — Versioning with mike

Summary
Enable versioned documentation using `mike` with a `latest` alias, and document the workflow so future releases can update docs predictably.

Why
- Allows users to browse docs for the version they’re using; keeps “latest” as default.

Tasks
1) Initialize mike locally:
   - uv run mike deploy 0.1 latest
   - uv run mike set-default latest
2) Confirm the version selector renders locally.
3) Document the release workflow for docs:
   - Add a section to docs/guides/ci-cd-and-github-pages.md titled “Versioning with mike” covering deploy and set-default commands.

Files/Artifacts
- No code changes required beyond docs and gh-pages content created by mike.
- docs/guides/ci-cd-and-github-pages.md (new/updated)

Commands
- uv run mike deploy 0.1 latest
- uv run mike set-default latest
- uv run mkdocs build --strict

Verification (Done when all true)
- Local site shows a version selector.
- After first deploy to gh-pages, versioned folders exist and `latest` is default.
- Docs guide has copyable commands that match our CI workflow.

Junior implementation notes
- Keep version numbers simple (start at 0.1 or current tag); we can revise later.
