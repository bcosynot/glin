# Implementation Plan — MkDocs Site for Seev (Material theme)

Last updated: 2025-10-26 13:29 (local time)
Owner: Docs/Dev team
Target stack: MkDocs + Material + mkdocstrings[python] + mike + mkdocs-git-revision-date-localized-plugin
Hosting: GitHub Pages via Actions (gh-pages branch)

This plan translates the requirements in `.junie/plans/mk-docs/requirements.md` into small, execution-ready tasks with context, references to the relevant requirement sections, and clear verification steps. Junior-friendly: every task specifies files to touch, commands to run, and a concrete “done” check.

Notation for requirement references:
- [Req §X] → section number in requirements.md
- [Req §X lines A–B] when a specific line range is helpful (based on the copy you provided)

---

## Phase 0 — Repo hygiene and baseline

1. Add dev dependencies via uv (local only at first)
   - Why: Enable local `mkdocs serve` and plugins.
   - Steps: `uv add --dev mkdocs-material mkdocstrings[python] mike mkdocs-git-revision-date-localized-plugin`
   - Verify: `pyproject.toml` and `uv.lock` updated; `uv run mkdocs --version` works.
   - Requirements: [Req §7.1–§7.4].

---

## Phase 1 — MkDocs skeleton and configuration

1. Create `mkdocs.yml` baseline
   - Why: Site-level config matching theme/features.
   - Files: `mkdocs.yml` (repo root).
   - Content: set `site_name`, `site_description`, `site_url` (temporary), `repo_url`, `edit_uri`; enable theme Material; features `navigation.tabs`, `content.code.copy`, `content.action.edit`; plugins `search`, `mkdocstrings`, `git-revision-date-localized`; markdown extensions `admonition`, `toc(permalink)`, `pymdownx.highlight`, `pymdownx.superfences`.
   - Verify: `uv run mkdocs build --strict` passes with empty skeleton.
   - Requirements: [Req §7.2–§7.5, §12, §13].

2. Create docs directory structure
   - Why: Matches planned IA and acceptance criteria.
   - Files/dirs:
     - `docs/index.md` (Landing)
     - `docs/guides/index.md`
     - `docs/reference/index.md`
     - `docs/troubleshooting.md`
     - `docs/changelog.md`
   - Verify: All files exist; `mkdocs serve` renders pages.
   - Requirements: [Req §3, §6, §7.6–§7.10, §19B].

3. Configure navigation (top-level)
   - Why: Reflect IA in header/side nav.
   - Files: `mkdocs.yml` `nav:` with Home, Guides, Reference, Troubleshooting, Changelog.
   - Verify: Tabs or nav items appear; links work.
   - Requirements: [Req §3.1–§3.5, §7.5].

4. Enable “Last updated” metadata
   - Why: UX requirement for recency cues.
   - Files: `mkdocs.yml` plugin `git-revision-date-localized` with `fallback_to_build_date: true`.
   - Verify: Page footer shows a date when built.
   - Requirements: [Req §5.1, §5.4, §5.11].

---

## Phase 2 — Landing page (marketing-lite) inside MkDocs

1. Author above-the-fold hero in `docs/index.md`
   - Why: 30-second value recognition and clear CTAs.
   - Content: Title "Seev"; tagline "Your worklog, without the work."; buttons/links: "Get Started" → Guides/Quick Start; "GitHub" → repo.
   - Verify: Hero renders; links work.
   - Requirements: [Req §4.1–§4.3, §2.2.1].

2. Add trust badges and minimal social proof
   - Why: Reinforce confidence without clutter.
   - Content: Shields for Python 3.13, tests/coverage, license (can be placeholders first); optional quotes later.
   - Verify: Badges display; alt text present.
   - Requirements: [Req §4.4–§4.6, §10.4].

3. Add problem/solution + benefits section
   - Why: Explain outcomes succinctly.
   - Content: 4–6 bullets focusing on automatic capture, privacy/local-first, MCP-native, quick success.
   - Verify: Section visible; scannable bullets.
   - Requirements: [Req §4.7, §2 Key journeys].

4. Embed Quick Start excerpt on landing
   - Why: Reduce friction; fast path to value.
   - Content: 3–5 copyable commands pulled from README: curl `seev-init.sh`, configure MCP with `uvx`, run first worklog entry prompt.
   - Verify: Copy buttons show; commands run in a sandbox test.
   - Requirements: [Req §4.8, §1 Primary goal, §6.1].

5. Feature highlight cards
   - Why: Skimmable capabilities.
   - Content: Cards for Automatic capture, Privacy-first, MCP-native; each links to a deeper docs page.
   - Verify: Cards render; keyboard focus order OK.
   - Requirements: [Req §4.9, §10 A11y].

6. Footer with links
   - Why: Consistent navigation affordances.
   - Content: Docs, GitHub, Privacy & Data.
   - Verify: Links work; contrast passes.
   - Requirements: [Req §4.10, §10.2–§10.3].

---

## Phase 3 — Guides content (minimum viable set)

1. Guides index stub with summaries
   - Why: Orient users.
   - Files: `docs/guides/index.md` with 1–2 sentence synopsis per guide.
   - Verify: Links to child pages resolve (even if stubs initially).
   - Requirements: [Req §6 Guides].

2. Quick Start guide (end-to-end ≤ 10 min)
   - Why: Primary success path.
   - Files: `docs/guides/quick-start.md`
   - Content outline:
     - Prereqs (Python 3.13, uv, git).
     - Install via curl `seev-init.sh`.
     - Add Seev to MCP client (tabs: Claude, Cursor, Cline).
     - Generate first worklog entry with example.
     - Verification checklist.
   - Verify: A new user test completes in ≤ 10 minutes on macOS/Linux.
   - Requirements: [Req §1.1, §6.1, §5.6 Tabs, §5.3–§5.6].

3. Workspace & Configuration guide
   - Why: Clarify tracked emails, paths, env vars.
   - Files: `docs/guides/workspace-and-configuration.md`
   - Content: Map to `seev.toml`, env overrides, examples; admonitions for gotchas.
   - Verify: Examples match README; env examples copyable.
   - Requirements: [Req §6.2, §5 Content patterns].

4. Generating Worklogs guide
   - Why: Demonstrate date ranges, correlation, examples.
   - Files: `docs/guides/generating-worklogs.md`
   - Content: Examples-first, then details; link to MCP prompts reference.
   - Verify: Commands render with copy buttons; examples valid.
   - Requirements: [Req §6.3, §5.12–§5.15].

5. Using Different MCP Clients guide (tabs)
   - Why: Client-specific instructions without duplication.
   - Files: `docs/guides/mcp-clients.md`
   - Content: Tabs for Claude Desktop, Cursor, Cline with their config file paths; screenshots later.
   - Verify: Tabs render; keyboard accessible.
   - Requirements: [Req §6.4, §5.6 Tabs].

---

## Phase 4 — Reference, Troubleshooting, Changelog, Privacy

1. Python API Reference stub via mkdocstrings
   - Why: Auto-document code, types, and functions.
   - Files: `docs/reference/index.md`
   - Content: Top-level intro + mkdocstrings blocks for key modules (e.g., `seev.config`, `seev.git_tools.*`, `seev.markdown_tools`).
   - Verify: `uv run mkdocs build` shows rendered API; no import errors (use `handlers: python`).
   - Requirements: [Req §6.6–§6.7, §7.1, §7.3].

2. MCP Tools Reference page
   - Why: Map MCP tools to behaviors.
   - Files: `docs/reference/mcp-tools.md`
   - Content: Each tool with purpose, args, example, and returned shape.
   - Verify: Cross-links to API or code; examples match README.
   - Requirements: [Req §6.7].

3. Prompts Reference page
   - Why: Document `worklog_entry` prompt usage.
   - Files: `docs/reference/prompts.md`
   - Content: Required args, what it does, examples.
   - Verify: Mirrors README; examples copy/paste friendly.
   - Requirements: [Req §6.8].

4. Troubleshooting & FAQ page
   - Why: Reduce support burden; fast fixes.
   - Files: `docs/troubleshooting.md`
   - Content: Cover errors listed in requirements; add environment gotchas.
   - Verify: Each entry includes cause + fix; anchors linkable.
   - Requirements: [Req §6.9–§6.10].

5. Privacy & Data page
   - Why: Transparency and trust.
   - Files: `docs/privacy-and-data.md`
   - Content: Local-first storage, what’s logged, control knobs.
   - Verify: Matches README section.
   - Requirements: [Req §6.13].

6. Contributing page
   - Why: PR hygiene and contributor success.
   - Files: `docs/contributing.md`
   - Content: Tests (`make test`), format/lint (`make format`, `make lint`), PR checklist.
   - Verify: Commands work locally.
   - Requirements: [Req §6.12, §16].

7. Changelog page (seed)
   - Why: Release notes area; link from nav.
   - Files: `docs/changelog.md`
   - Content: Start with `Unreleased` section; later automate.
   - Verify: Page visible; linked from nav.
   - Requirements: [Req §3.4, §6.11, §19B].

---

## Phase 5 — UX features, accessibility, and quality gates

1. Ensure site-wide search (Phase 1)
   - Why: Immediate on-site discovery.
   - Steps: Confirm `search` plugin active; test queries for key terms.
   - Verify: Search returns relevant pages fast.
   - Requirements: [Req §8.1, §5.2].

2. Add tabs for OS and client variations
   - Why: Reduce duplication, improve clarity.
   - Steps: Use Material tab syntax (`===` or `tabs` extension) in relevant guides.
   - Verify: Tabs keyboard-accessible; focus rings visible.
   - Requirements: [Req §5.6, §10.2].

3. Admonitions for tips/warnings
   - Why: Scannability and risk communication.
   - Steps: Use `!!! tip`, `!!! warning` blocks near risky steps.
   - Verify: Rendered with icons; accessible contrast.
   - Requirements: [Req §5.3, §5.12–§5.15, §10].

4. Previous/Next navigation
   - Why: Guided reading path.
   - Steps: Rely on Material auto prev/next; ensure `nav` order logical.
   - Verify: Links appear at bottom; work across pages.
   - Requirements: [Req §5.7].

5. Accessibility sweep (WCAG 2.1 AA)
   - Why: Meet compliance targets.
   - Steps: Keyboard-only pass; check focus rings; headings order; alt text; descriptive links.
   - Verify: Lighthouse A11y ≥ 95; manual checks pass.
   - Requirements: [Req §10.1–§10.5, §11 Targets].

6. Performance budget checks
   - Why: Keep pages fast.
   - Steps: Lighthouse on landing and a deep page; ensure page weight < 300KB without images.
   - Verify: Perf ≥ 90; FCP < 1.8s; INP < 200ms (lab conditions).
   - Requirements: [Req §11.1–§11.4].

7. Broken link checking in CI
   - Why: Prevent regressions.
   - Steps: `mkdocs build --strict`; optionally add link checker action or plugin.
   - Verify: CI fails on broken links; green when fixed.
   - Requirements: [Req §11.3–§11.4, §19D].

---

## Phase 6 — Versioning (mike)

1. Initialize `mike` versioning
   - Why: Enable version switcher and `latest` alias.
   - Steps:
     - First run: `uv run mike deploy 0.1 latest`
     - Set default: `uv run mike set-default latest`
   - Verify: Local `site/` shows version selector; `gh-pages` will contain versioned folders after deploy.
   - Requirements: [Req §9.1–§9.4, §3.7].

2. Document release workflow for docs
   - Why: Make version bumps repeatable.
   - Files: `docs/guides/ci-cd-and-github-pages.md` (add a “Versioning with mike” section).
   - Verify: Steps are copyable; match our Actions.
   - Requirements: [Req §9, §15].

---

## Phase 7 — SEO & Sharing, Theming, Analytics (optional)

1. Add sitemap and robots (auto)
   - Why: Basic SEO hygiene.
   - Steps: Ensure Material/MkDocs generates sitemap.xml; set `site_url` in `mkdocs.yml`.
   - Verify: `site/sitemap.xml` exists; canonical URLs present.
   - Requirements: [Req §12.1–§12.2].

2. Populate meta tags and social cards
   - Why: Good previews and search snippets.
   - Steps: Configure `site_description`; add `extra` metadata; create social image for landing.
   - Verify: Meta tags present in built HTML; OG/Twitter validators pass.
   - Requirements: [Req §12.3–§12.4].

3. Optional Schema.org `SoftwareApplication`
   - Why: Rich results (optional).
   - Steps: Add JSON-LD via `extra_javascript` or theme overrides.
   - Verify: Structured Data Testing Tool passes.
   - Requirements: [Req §12.5] (optional).

4. Branding & theming pass
   - Why: Visual cohesion with Seev.
   - Steps: Provide logo/favicon; set primary/secondary palettes; ensure code block style consistent.
   - Verify: Contrast OK; dark/light variants.
   - Requirements: [Req §13.1–§13.4, §10.3].

5. Optional privacy-friendly analytics
   - Why: Understand usage without PII.
   - Steps: Document Plausible as optional; add code via `extra_javascript` with defer + SRI if enabled; ensure we can disable.
   - Verify: No third-party scripts by default; toggle works.
   - Requirements: [Req §14.1–§14.3, §17.1].

---

## Phase 8 — Deployment & Ops

1. Add GitHub Actions workflow for docs
   - Why: Automated deploy to GitHub Pages.
   - Files: `.github/workflows/docs.yml`
   - Steps: Checkout; setup Python 3.13; install via uv; `mkdocs build --strict`; deploy `site/` to `gh-pages` (peaceiris/actions-gh-pages) while retaining `CNAME` if present.
   - Verify: On push to `main`, workflow builds and publishes; `gh-pages` updated.
   - Requirements: [Req §15.1–§15.4, §19E].

2. Configure Pages in repo settings (manual)
   - Why: Enable hosting and custom domain.
   - Steps: Set source `gh-pages`; add custom domain if available; ensure `CNAME` file exists.
   - Verify: Site accessible over HTTPS; redirects correct.
   - Requirements: [Req §15.1–§15.3].

3. Optional PR previews
   - Why: Faster docs reviews.
   - Steps: Add job to upload `site/` as artifact or use a preview action.
   - Verify: PR shows preview link.
   - Requirements: [Req §15.4] (optional).

---

## File/Artifact Map

- Config: `mkdocs.yml`
- Content roots: `docs/`
  - Landing: `docs/index.md`
  - Guides: `docs/guides/*.md`
  - Reference: `docs/reference/*.md`
  - Troubleshooting: `docs/troubleshooting.md`
  - Changelog: `docs/changelog.md`
  - Privacy: `docs/privacy-and-data.md`
- CI/CD: `.github/workflows/docs.yml`

---

## Junior Developer Notes

- Always run commands with `uv run` when invoking Python-based tools in this repo.
- Keep PRs small: one phase per PR is OK.
- Use admonitions in docs for tips and warnings.
- When uncertain, cite the requirement section you’re implementing in the PR description.
- Before merging, run: `make format && make lint && uv run mkdocs build --strict`.
