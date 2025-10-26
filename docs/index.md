---
title: "Seev — Your worklog, without the work"
description: "Seev turns your real work—commits, PRs, and AI conversations—into a clean daily worklog. No copy‑pasting. No end‑of‑day scramble."
social_image: assets/social.svg
---

# Seev

Your worklog, without the work.

[Get Started →](guides/index.md){ .md-button .md-button--primary }
[GitHub ↗](https://github.com/bcosynot/seev){ .md-button }

---

<!-- Trust badges -->
<p align="left">
  <a href="#" title="Python 3.13"><img alt="Python 3.13" src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white"></a>
  <a href="#" title="Tests & Coverage"><img alt="Tests & Coverage" src="https://img.shields.io/badge/tests-✓%20&%20coverage-4c1"></a>
  <a href="https://github.com/bcosynot/seev/blob/main/LICENSE" title="License"><img alt="License" src="https://img.shields.io/badge/license-TBD-informational"></a>
</p>

## Why Seev

Seev turns your real work—commits, PRs, and AI conversations—into a clean daily worklog. No copy‑pasting. No end‑of‑day scramble.

### Your challenges → How Seev helps → What you get
- Manual status updates steal time and are easy to forget.
- Signal gets buried across repos, PRs, and chats.
- Reviews and performance cycles demand accurate histories.

How Seev helps and what you get:
- Automatic capture from git and your AI assistant
- Privacy‑first and local‑first by default
- MCP‑native: works with Claude Desktop, Cursor, Cline, and more
- Fast first success: up and running in minutes

---

## Quick Start (excerpt)

Copy these into your terminal:

```bash
# 1) Initialize a workspace (creates WORKLOG.md and config)
curl -fsSL https://raw.githubusercontent.com/bcosynot/seev/main/seev-init.sh | bash -s -- -y ~/seev-workspace
```

```bash
# 2) Start the Seev MCP server (stdio)
uvx --from git+https://github.com/bcosynot/seev.git seev
```

```bash
# 3) (Optional) Run via HTTP on port 8000
uv run python main.py -- --transport http
```

```text
# 4) Ask your AI assistant
/worklog_entry today
```

> Tip: After adding Seev to your MCP client config, restart the client to load the server.

---

## Highlights

<div class="grid cards">

- :material-rocket-launch: **Quick Start** — Get going in minutes. → [Guides](guides/index.md)
- :material-git: **Git tools** — Commits, diffs, files, branches. → [Reference](reference/index.md)
- :material-file-document: **Worklog writer** — Append structured entries safely. → [Troubleshooting](troubleshooting.md)
- :material-shield-key: **Privacy & Data** — Local‑first by design. → [README section](https://github.com/bcosynot/seev#privacy--data)

</div>

---

## Stay in the loop

- Docs: [Guides](guides/index.md) · [Reference](reference/index.md)
- GitHub: [bcosynot/seev](https://github.com/bcosynot/seev)
- Privacy & Data: see [README → Privacy & Data](https://github.com/bcosynot/seev#privacy--data)
