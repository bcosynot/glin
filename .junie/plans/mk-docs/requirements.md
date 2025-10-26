# MkDocs Site Requirements — Landing Page + Documentation (High Usability)

Last updated: 2025-10-26
Scope: Single MkDocs site using Material for MkDocs; includes a lightweight marketing landing page and full documentation for Seev. Focused on end‑user clarity, low ops, and excellent UX.

---

## 1) Goals and Success Criteria
- Primary goal: Help a new user install, run, and succeed with Seev in under 10 minutes, without outside help.
- Secondary goals:
  - Provide clear, searchable docs for power users (MCP tools, prompts, advanced config)
  - Reduce support burden by covering FAQ/troubleshooting well
  - Keep the site simple to maintain (content in Markdown; automated deploys)
- Success metrics (initial targets):
  - Time-to-first-successful-setup: ≤ 10 minutes (tested on macOS + Linux)
  - Search success (“user finds correct page within 1 query”): ≥ 80% in user tests
  - Lighthouse accessibility ≥ 95; Best Practices ≥ 95; SEO ≥ 95; Performance ≥ 90

## 2) Audience and Use Cases
- Primary persona: Senior software engineers using MCP-capable assistants (e.g., Claude Desktop, Cursor, Cline)
- Key journeys:
  1) Evaluate → Understand value in 30 seconds on landing page
  2) Install → Follow Quick Start to working setup via `uv`
  3) Use → Generate first worklog entry; view examples; iterate
  4) Troubleshoot → Resolve common errors quickly
  5) Contribute → Find development, testing, and PR guidelines

## 3) Information Architecture (IA) and Navigation
- Global navigation (top or left, depending on theme):
  - Home (Landing)
  - Guides (How-to, tutorials)
  - Reference (API via mkdocstrings; MCP tools & prompts)
  - Changelog (release notes)
  - FAQ / Troubleshooting
- Sidebar: Auto-generated section tree with clear grouping and short labels
- On-page: Breadcrumbs, on-page Table of Contents, “Edit this page” link to GitHub
- Version switcher (mike) visible in header

## 4) Landing Page (Marketing-Lite, Built in MkDocs Material)
- Above-the-fold hero:
  - Product name and 1-sentence value prop (“Your worklog, without the work.”)
  - Primary CTA: “Get Started” → Quick Start guide
  - Secondary CTA: “GitHub” → repo
- Social proof / trust:
  - Badges (Python 3.13, tests/coverage, license)
  - Minimal logos or quote snippets if available (optional)
- Problem/solution + key benefits: bullet list focused on outcomes
- Quick Start excerpt: 3–5 steps with copy-to-clipboard commands (command to run the `seev-init.sh` script using curl, MCP client setup using `uvx`, example prompt)
- Feature highlights (cards): automatic capture, privacy/local-first, MCP-native
- Footer: links to Docs, GitHub

## 5) Documentation UX Requirements
- Theme: Material for MkDocs; dark/light theme toggle; responsive mobile experience
- Core UX features:
  - Instant client-side search;
  - On-page TOC, anchor links with visible hover/focus states
  - Admonitions (note, tip, warning, danger) for scannability
  - Tabs for multi-OS or multi-client instructions (macOS, Windows, Linux; Claude/Cursor/Cline)
  - “Copy” buttons on code blocks; keyboard accessible
  - Previous/Next navigation at bottom of pages
  - “Last updated” via git revision date plugin
- Content patterns:
  - Each page starts with a succinct summary (what/why/when to use)
  - Examples first; full detail later
  - Troubleshooting sections near the point of use

## 6) Content Requirements (Initial Table of Contents)
- Guides
  - Quick Start (install with `seev-init` script invoked with curl, connect MCP client with `uvx`, first worklog)
  - Workspace & Configuration (tracked emails, paths, environment)
  - Generating Worklogs (date ranges, correlation, examples)
  - Using with Different MCP Clients (Claude Desktop, Cursor, Cline)
  - CI/CD and GitHub Pages (optional) for docs site
- Reference
  - Python API (auto-generated via mkdocstrings)
  - MCP Tools Reference (tool list mapped to Seev functions)
  - Prompts Reference (`worklog_entry` details; arguments; outputs)
- Troubleshooting & FAQ
  - Common errors (no commits found, workspace not initialized, git tools unavailable, server not loading)
  - Environment gotchas (git config, env vars)
- Changelog
- Contributing (tests, lint, formatting, PR checklist)
- Privacy & Data (local-first, what’s stored, opt-ins)

## 7) Technical Requirements (MkDocs + Material)
- Dependencies (dev):
  - `mkdocs-material`
  - `mkdocstrings[python]`
  - `mike` (versioning)
  - `mkdocs-git-revision-date-localized-plugin`
- Configuration (`mkdocs.yml` baseline):
  - `theme: material` with features: `navigation.tabs`, `content.code.copy`, `content.action.edit`
  - `plugins: search, mkdocstrings (python), git-revision-date-localized`
  - `markdown_extensions: admonition, toc(permalink), pymdownx.highlight, pymdownx.superfences`
  - `nav`: Home, Guides, Reference, Changelog
  - `repo_url`, `edit_uri` configured to GitHub
  - `site_name`, `site_description`, canonical `site_url`
- Structure:
  - `docs/index.md` (landing)
  - `docs/guides/index.md`
  - `docs/reference/index.md`
  - `docs/changelog.md`

## 8) Search Requirements
- Phase 1: Built-in Material search enabled and performant
- Phase 2 (optional): Algolia DocSearch configured after application approval
  - Must be privacy-friendly; no PII collection
  - Fallback gracefully to client-side search if Algolia unavailable

## 9) Versioning Requirements (mike)
- Support versioned docs with `latest` alias
- UI: clear version switcher; default to `latest`
- Workflow:
  - On release: `mike deploy <version> latest` + `mike set-default latest`
  - Keep unversioned “next” (optional) for main branch previews

## 10) Accessibility (A11y) Requirements
- Meet WCAG 2.1 AA
- Keyboard navigation for all interactive controls; visible focus rings
- Sufficient color contrast for both light and dark modes
- Semantic headings (h1–h3) and correct landmark roles
- Provide alt text for images; descriptive link text (no “click here”)

## 11) Performance & Quality
- Targets (desktop + mobile):
  - First Contentful Paint < 1.8s
  - Interaction to Next Paint (INP) < 200ms on average
  - Total size per page (initial): < 300KB without images
- Build checks:
  - Broken link checking in CI (mkdocs build `--strict` + link check plugin or external checker)
  - Optional spelling/style checks (CI) for docs

## 12) SEO & Sharing
- Auto sitemap and robots.txt; canonical URLs
- Metadata: title, description, OpenGraph/Twitter cards
- Social image for landing page
- Schema.org `SoftwareApplication` (optional) via meta tags

## 13) Branding & Theming
- Light/dark color palettes aligned with Seev
- Logo/favicon provided; fallback to text logo acceptable initially
- Consistent code block style and inline code formatting

## 14) Analytics & Privacy
- Optional privacy-friendly analytics (e.g., Plausible) with easy opt-out
- No user fingerprints or PII
- Document what is collected (if enabled)

## 15) Deployment & Ops
- Hosting: GitHub Pages via GitHub Actions
- Workflow: Build on push to `main`; publish `site/` to `gh-pages`
- Keep `CNAME` if using custom domain
- Preview environments (optional): PR build artifact or deploy previews via Actions

## 16) Authoring & Maintenance
- Markdown-first workflow; no local JS build required
- “Edit this page” links to GitHub; encourage drive-by fixes
- Content style guide:
  - Short sentences, imperative steps, 1 task per step
  - Show commands first; then explain
  - Provide copyable code blocks for every command
- Review process: PR labels `docs`, required reviewer for major guides
- Regular tasks: update Quick Start when install steps change; keep examples in sync with README

## 17) Security & Compliance
- No third-party scripts by default; if Algolia/analytics added, use SRI and load defer
- CSP header recommendations documented (for non-GitHub Pages hosts)
- Document license and third-party attributions

## 18) Out of Scope (for now)
- Complex marketing site or blog (consider later if needed)
- Auth-gated docs or multi-tenant docs
- Heavy custom React components

## 19) Acceptance Criteria (Definition of Done)
- A. Local dev: `uv run mkdocs serve` renders landing + docs skeleton without errors
- B. Core pages exist with usable content: Landing, Quick Start, Guides index, Reference index, Troubleshooting, Changelog
- C. Usability: New user can complete Quick Start successfully from this site alone
- D. Quality: Passes `mkdocs build --strict`; Lighthouse A11y ≥ 95; broken links = 0
- E. Ops: GitHub Actions workflow builds and deploys to `gh-pages` on push to `main`
