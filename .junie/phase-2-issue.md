Title: Phase 2 — Landing page within MkDocs (marketing‑lite)

Summary
Author a clear landing page (`docs/index.md`) that communicates Seev’s value in ~30 seconds and routes users to the Quick Start. Include trust badges, benefits, a Quick Start excerpt, feature highlights, and a useful footer.

Why
- Converts evaluators quickly and reduces friction to first success.

Files/Artifacts
- docs/index.md (landing page content)
- Optional: images/ (social card later)

Tasks
1) Above‑the‑fold hero with:
   - Product name: Seev
   - Tagline: “Your worklog, without the work.”
   - Primary CTA button/link: Get Started → Guides/Quick Start
   - Secondary CTA: GitHub → repository URL
2) Trust badges (static for now): Python 3.13, tests/coverage, license; include alt text.
3) Problem → Solution → Benefits: 4–6 scannable bullets focused on outcomes (automatic capture; privacy/local‑first; MCP‑native; quick success).
4) Quick Start excerpt: 3–5 copyable commands pulled from README:
   - curl to run `seev-init.sh`
   - configure MCP client with `uvx`
   - generate first worklog entry
5) Feature highlight cards linking deeper docs.
6) Footer: Docs, GitHub, Privacy & Data links.

Commands
- uv run mkdocs serve  # live preview while editing
- uv run mkdocs build --strict

Verification (Done when all true)
- Hero renders with working CTAs; badges have alt text.
- Benefits are concise and scannable; copy buttons show on code blocks.
- Links to Quick Start and repo work.
- Strict build passes.

Junior implementation notes
- Use Material components (admonitions, grids/cards where applicable).
- Keep copy concise; avoid jargon; prefer imperative steps for Quick Start excerpt.

Relevant requirements (inlined)
- Landing must include hero + CTAs, badges, benefits, Quick Start excerpt, highlight cards, and footer links.
