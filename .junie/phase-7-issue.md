Title: Phase 7 — SEO & Sharing, Theming, Analytics (optional)

Summary
Improve discoverability and brand consistency by enabling sitemap/robots, metadata and social cards, light theming, and optional privacy-friendly analytics (documented and disabled by default).

Why
- Better search and link previews; cohesive look and feel; optional insights without PII.

Tasks
1) Sitemap and robots (auto): ensure `site_url` is set in mkdocs.yml so sitemap.xml and robots.txt are generated.
2) Meta tags and social cards: set `site_description`; add `extra` metadata; create a social image for landing; verify with OG/Twitter validators.
3) Optional Schema.org SoftwareApplication: add JSON-LD via extra_javascript or theme overrides; validate with Structured Data Testing Tool.
4) Branding & theming pass: logo/favicon; primary/secondary palettes; consistent code block style; verify contrast in light/dark.
5) Optional privacy-friendly analytics: document Plausible as opt-in; add code via extra_javascript with defer and SRI when enabled; default is off.

Files/Artifacts
- mkdocs.yml (site_url, extra metadata, extra_javascript)
- docs/index.md (ensure good title/description; social card reference if needed)
- assets/ (logo, favicon, social image) — create if needed

Commands
- uv run mkdocs build --strict

Verification (Done when all true)
- site/sitemap.xml exists with canonical URLs; robots.txt present.
- Built HTML contains title/description/OG/Twitter meta; validators pass.
- Optional JSON-LD validates cleanly (if implemented).
- Contrast OK; dark/light variants render.
- No third-party scripts by default; analytics toggle works if enabled.

Junior implementation notes
- Keep analytics opt-in and documented; never ship PII.
