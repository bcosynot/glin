Title: Phase 1 — MkDocs skeleton and configuration

Summary
Create the initial MkDocs configuration and docs directory skeleton that matches our planned information architecture. Ensure the site builds in strict mode.

Why
- Establishes the base site structure and navigation.
- Enables strict builds to catch broken links early.

Files/Artifacts
- mkdocs.yml (repo root)
- docs/index.md
- docs/guides/index.md
- docs/reference/index.md
- docs/troubleshooting.md
- docs/changelog.md

Tasks
1) Create mkdocs.yml with:
   - site_name: Seev
   - site_description and temporary site_url
   - repo_url and edit_uri pointing to this GitHub repo
   - theme: material; features: navigation.tabs, content.code.copy, content.action.edit
   - plugins: search, mkdocstrings (python handler), git-revision-date-localized (fallback_to_build_date: true)
   - markdown_extensions: admonition, toc(permalink), pymdownx.highlight, pymdownx.superfences
   - nav: Home, Guides, Reference, Troubleshooting, Changelog
2) Create the docs/ files listed above (can be minimal stubs with headings).
3) Run a strict build to validate the skeleton.

Commands
- uv run mkdocs build --strict
- uv run mkdocs serve  # optional, to preview locally

Verification (Done when all true)
- mkdocs.yml exists and contains the settings listed.
- All docs/* files exist and render.
- `uv run mkdocs build --strict` completes without errors.
- Header nav shows Home, Guides, Reference, Troubleshooting, Changelog.
- Page footer shows a date from git revision plugin or build date.

Junior implementation notes
- Keep content minimal for now; detailed copy comes in later phases.
- Use short, descriptive titles at the top of each page for clarity.

Relevant requirements (inlined)
- Theme: Material; features: tabs, copy buttons, edit action.
- Plugins: search, mkdocstrings (python), git revision date localized.
- IA: Home, Guides, Reference, Changelog; Troubleshooting and Changelog present in nav.
