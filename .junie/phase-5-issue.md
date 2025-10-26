Title: Phase 5 — UX features, accessibility, and quality gates

Summary
Enhance the docs UX with search, tabs, admonitions, prev/next navigation, and run accessibility and performance checks. Add strict/broken-link checks in CI.

Why
- Improves discoverability, inclusivity, and keeps docs fast and reliable.

Tasks
1) Site-wide search: confirm `search` plugin active; test key queries.
2) Tabs for OS/clients in relevant guides (Material tab syntax). Ensure keyboard accessibility and visible focus.
3) Admonitions: add `!!! tip` and `!!! warning` where users can make mistakes.
4) Previous/Next navigation: ensure logical `nav` order so Material shows prev/next links.
5) Accessibility sweep (WCAG 2.1 AA): keyboard-only nav, focus rings, heading order, alt text, descriptive links.
6) Performance checks: Lighthouse on landing and a deep page; keep page weight < 300KB (without images); target Perf ≥ 90, FCP < 1.8s, INP < 200ms.
7) Broken link checking in CI: ensure `uv run mkdocs build --strict` runs in CI. Optionally add link checker.

Files/Artifacts
- mkdocs.yml (ensure features/extensions on)
- docs/* (add tabs/admonitions as needed)
- CI workflow (if adding link checker): .github/workflows/docs.yml

Commands
- uv run mkdocs build --strict
- Optional: run Lighthouse in Chrome DevTools; record scores in PR description.

Verification (Done when all true)
- Search returns relevant pages quickly.
- Tabs are keyboard accessible; focus rings visible.
- Lighthouse A11y ≥ 95; Performance ≥ 90; no broken links; strict build green.

Junior implementation notes
- Prefer semantic headings; use alt text on any images; keep link text descriptive.
