# Glin Worklog Improvement Analysis

**Date:** 2025-10-11
**Analysis of:** Glin MCP Server - Making worklogs way more useful than just commit listings

---

## Executive Summary

**Key Finding:** Glin has excellent infrastructure already in place that's not being fully utilized. Most critically, you have a complete `storage` module with conversation tracking (`glin/storage/conversations.py:1-136`) but **no MCP tools expose it**. This is the biggest missed opportunity!

**The Core Problem:**
Worklogs are currently "just commit listings" because they lack:
1. **Context** - Why was work done? (conversations exist in DB but aren't queried!)
2. **Analysis** - What's the impact? (tools exist in `glin/git_tools/analysis.py:1-363` but aren't integrated)
3. **Structure** - Rich narrative vs bullets (`markdown_tools.py:1-258` only does bullets)

---

## Current State Assessment

### What You Have (Good Foundation)
- ✅ Git commit fetching with email tracking
- ✅ SQLite storage with `conversations` + `messages` tables (Phase 2)
- ✅ Analysis tools: merge detection, commit stats, conventional commits parsing, git blame
- ✅ MCP prompts for LLM-driven summaries
- ✅ Markdown appending with date sections

### The Gap
Your vision says Glin captures from *"prompts and conversations with your agentic coding assistant"* **AND** *"git history"*, but currently:
- ❌ **No conversation tracking is exposed** as MCP tools (despite having the DB schema!)
- ❌ Analysis tools exist but aren't integrated into worklog generation
- ❌ Worklog output is just bullet points - no rich context, impact, or narrative
- ❌ No automated session/theme detection
- ❌ No file/module focus analysis

---

## High-Impact Improvements

### 1. Conversation Context Integration 🎯 (HIGHEST IMPACT)

**Problem:** You have conversation storage but it's not used!

**Solution: Expose these MCP tools:**

```python
@mcp.tool(name="record_conversation_message")
async def record_conversation_message(
    role: str,  # user, assistant, system
    content: str,
    conversation_id: int | None = None,
    title: str | None = None
) -> dict:
    """Record a message in the current coding session.

    If conversation_id is None, creates a new conversation.
    Returns conversation_id and message_id.
    """
    # Implementation using existing glin/storage/conversations.py
    # - add_conversation() if new
    # - add_message() for each message
```

```python
@mcp.tool(name="get_recent_conversations")
async def get_recent_conversations(
    date: str | None = None,  # ISO date
    limit: int = 10
) -> list[dict]:
    """Get recent conversations, optionally filtered by date.

    Returns conversation metadata with message summaries.
    """
    # Implementation using query_conversations()
```

**Worklog Enhancement:**
Now your `worklog_entry` prompt can fetch BOTH:
- Commits for the day
- Conversations for the day

Example output:
```markdown
## 2025-10-11

### Context
🗣️ **Morning Discussion:** "How to implement OAuth2 token refresh?"
- User mentioned production 401 errors affecting users
- Discussed token expiry edge cases and rotation strategies

### Technical Work
**Authentication System:**
- feat(auth): implement OAuth2 token refresh (abc123)
  Related to conversation about token rotation
- fix(auth): handle expired tokens gracefully (def456)
```

**Implementation Location:**
- Add to: `glin/storage/conversations.py` or new `glin/conversation_tools.py`
- Import in: `glin/mcp_app.py`
- Update: `glin/prompts.py` - `worklog_entry_prompt()` line 175

---

### 2. Automated Analysis & Enrichment 🔍

**Problem:** Analysis tools (`get_commit_statistics`, `categorize_commit`, `detect_merge_info`) exist but aren't used in worklogs.

**Solution: Create an enrichment pipeline:**

```python
@mcp.tool(name="get_enriched_commits")
async def get_enriched_commits(
    since: str,
    until: str = "now"
) -> list[dict]:
    """Get commits with automatic enrichment:
    - Commit statistics (adds/dels, language breakdown)
    - Conventional commit categorization
    - Merge/PR detection
    - File change analysis

    Calls existing analysis tools for each commit.
    """
    from .git_tools.commits import get_commits_by_date
    from .git_tools.analysis import (
        get_commit_statistics,
        categorize_commit,
        detect_merge_info
    )

    commits = get_commits_by_date(since, until)
    enriched = []

    for commit in commits:
        if "hash" not in commit:
            continue

        sha = commit["hash"]
        stats = get_commit_statistics(sha)
        category = categorize_commit(sha, is_hash=True)
        merge_info = detect_merge_info(sha)

        enriched.append({
            **commit,
            "statistics": stats,
            "category": category,
            "merge_info": merge_info
        })

    return enriched
```

**Worklog Enhancement:**
```markdown
## 2025-10-11

### Impact Analysis
- **8 commits** across 3 features
- **Python** (450 +lines, 120 -lines) | **TypeScript** (200 +lines)
- **Hot files:** `auth.py` (5 changes), `api.ts` (3 changes)

### Work Breakdown
**Authentication (5 commits - feat type)**
- Implemented OAuth2 flow with token refresh (+450, -50)
- Fixed edge cases in session handling (+80, -20)
- PR #42 merged (detected via merge_info)

**Testing (3 commits - test type)**
- Added integration tests for auth endpoints (+200, -0)
- Fixed flaky test in user_service_test.py (+15, -10)
```

**Implementation Location:**
- Add to: new file `glin/git_tools/enrichment.py`
- Update: `glin/prompts.py` - `worklog_entry_prompt()` to suggest using this tool

---

### 3. Smart Session & Theme Detection 🧠

**Problem:** Commits are listed chronologically, not grouped by intent/theme.

**Solution: Add session detection logic:**

```python
from datetime import datetime, timedelta
from collections import defaultdict

def detect_work_sessions(
    commits: list[dict],
    gap_threshold_minutes: int = 30
) -> list[dict]:
    """Group commits into logical work sessions based on:
    - Time gaps (>30min = new session)
    - Conventional commit type patterns
    - File overlap analysis
    - Commit message similarity

    Returns:
        List of sessions with metadata:
        {
            "start_time": "2025-10-11T09:15:00",
            "end_time": "2025-10-11T11:45:00",
            "duration_minutes": 150,
            "commits": [...],
            "primary_type": "feat",
            "focus_files": ["auth.py", "tokens.py"],
            "focus_dirs": ["src/auth/"],
            "theme": "Authentication system overhaul"
        }
    """
    if not commits:
        return []

    # Sort by date
    sorted_commits = sorted(commits, key=lambda c: c.get("date", ""))

    sessions = []
    current_session = {
        "commits": [],
        "start_time": None,
        "end_time": None
    }

    for commit in sorted_commits:
        commit_time = datetime.fromisoformat(commit["date"].replace(" ", "T"))

        if current_session["start_time"] is None:
            # First commit
            current_session["start_time"] = commit_time
            current_session["commits"].append(commit)
        else:
            time_gap = (commit_time - current_session["end_time"]).total_seconds() / 60

            if time_gap > gap_threshold_minutes:
                # Finalize current session
                sessions.append(_finalize_session(current_session))
                # Start new session
                current_session = {
                    "commits": [commit],
                    "start_time": commit_time,
                    "end_time": commit_time
                }
            else:
                # Add to current session
                current_session["commits"].append(commit)

        current_session["end_time"] = commit_time

    # Finalize last session
    if current_session["commits"]:
        sessions.append(_finalize_session(current_session))

    return sessions


def _finalize_session(session: dict) -> dict:
    """Add metadata to a session."""
    commits = session["commits"]

    # Extract types from categorized commits
    types = [c.get("category", {}).get("type", "other") for c in commits]
    type_counts = defaultdict(int)
    for t in types:
        type_counts[t] += 1
    primary_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "mixed"

    # Extract files (would need enrichment data)
    focus_files = []
    focus_dirs = set()
    for c in commits:
        stats = c.get("statistics", {})
        # This would need file-level data from git show --name-only
        # For now, placeholder

    # Generate theme from commit messages
    messages = [c.get("message", "") for c in commits]
    theme = _infer_theme_from_messages(messages)

    duration = (session["end_time"] - session["start_time"]).total_seconds() / 60

    return {
        "start_time": session["start_time"].isoformat(),
        "end_time": session["end_time"].isoformat(),
        "duration_minutes": int(duration),
        "commits": commits,
        "commit_count": len(commits),
        "primary_type": primary_type,
        "type_distribution": dict(type_counts),
        "focus_files": focus_files,
        "focus_dirs": list(focus_dirs),
        "theme": theme
    }


def _infer_theme_from_messages(messages: list[str]) -> str:
    """Infer a theme from commit messages."""
    # Simple heuristic: find common words
    if not messages:
        return "Miscellaneous work"

    # Extract keywords from messages
    words = []
    for msg in messages:
        # Remove conventional commit prefix
        clean_msg = msg.split(":", 1)[-1].strip()
        words.extend(clean_msg.lower().split())

    # Find most common meaningful words
    from collections import Counter
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
    filtered = [w for w in words if len(w) > 3 and w not in stop_words]

    if not filtered:
        return "Development work"

    common = Counter(filtered).most_common(2)
    return f"{common[0][0].capitalize()} related work"
```

**Worklog Enhancement:**
```markdown
## 2025-10-11

### Morning Session (9:15 - 11:45) | 2h 30m
**Theme:** Authentication system overhaul
**Type:** feat (4 commits), fix (1 commit)
- Researched OAuth2 patterns (from conversation log)
- Implemented token refresh mechanism
- Added session middleware
- **Files:** auth.py, tokens.py, middleware.py

### Afternoon Session (14:00 - 16:30) | 2h 30m
**Theme:** Testing and bug fixes
**Type:** test (3 commits), fix (2 commits)
- Investigated production 401 errors
- Added integration test suite
- Fixed edge cases in token validation
- **PR:** #42 reviewed and merged
```

**Implementation Location:**
- Add to: new file `glin/git_tools/sessions.py`
- Update: `glin/prompts.py` - `worklog_entry_prompt()` to use session detection

---

### 4. File & Module Heatmaps 📊

**Problem:** No visibility into what parts of the codebase are being worked on.

**Solution:**

```python
from pathlib import Path
from collections import defaultdict

@mcp.tool(name="get_file_heatmap")
async def get_file_heatmap(
    since: str,
    until: str = "now",
    top_n: int = 10
) -> dict:
    """Generate heatmap of file/directory changes:
    - Changes per file
    - Directory-level aggregation
    - Top modified files
    - Language breakdown
    """
    import subprocess
    from .commits import get_commits_by_date, _get_author_filters

    authors = _get_author_filters()
    if not authors:
        return {"error": "No tracked emails configured"}

    # Get all commits in range
    commits = get_commits_by_date(since, until)

    if not commits or "error" in commits[0]:
        return {"files": [], "directories": [], "languages": {}}

    # Aggregate file changes
    file_changes = defaultdict(lambda: {"changes": 0, "additions": 0, "deletions": 0})
    dir_changes = defaultdict(int)
    lang_changes = defaultdict(lambda: {"files": 0, "additions": 0, "deletions": 0})

    for commit in commits:
        if "hash" not in commit:
            continue

        sha = commit["hash"]

        # Get file stats for this commit
        result = subprocess.run(
            ["git", "show", "--numstat", "--pretty=format:", sha],
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue

            add_s, del_s, path = parts[0], parts[1], parts[2]
            adds = 0 if add_s == "-" else int(add_s)
            dels = 0 if del_s == "-" else int(del_s)

            # File-level stats
            file_changes[path]["changes"] += 1
            file_changes[path]["additions"] += adds
            file_changes[path]["deletions"] += dels

            # Directory-level stats
            dir_path = str(Path(path).parent)
            dir_changes[dir_path] += 1

            # Language stats
            lang = _infer_language(path)
            lang_changes[lang]["files"] += 1
            lang_changes[lang]["additions"] += adds
            lang_changes[lang]["deletions"] += dels

    # Sort and get top files
    top_files = sorted(
        [{"path": k, **v} for k, v in file_changes.items()],
        key=lambda x: x["changes"],
        reverse=True
    )[:top_n]

    # Sort and get top directories
    top_dirs = sorted(
        [{"path": k, "changes": v} for k, v in dir_changes.items()],
        key=lambda x: x["changes"],
        reverse=True
    )[:top_n]

    return {
        "files": top_files,
        "directories": top_dirs,
        "languages": dict(lang_changes),
        "total_files_touched": len(file_changes),
        "total_commits_analyzed": len([c for c in commits if "hash" in c])
    }


def _infer_language(path: str) -> str:
    """Infer language from file extension."""
    _LANG_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        # ... (use existing map from analysis.py)
    }
    path_lower = path.lower()
    for ext, lang in _LANG_MAP.items():
        if path_lower.endswith(ext):
            return lang
    return "Other"
```

**Worklog Enhancement:**
```markdown
## 2025-10-11

### Focus Areas
📈 **Most Active Directories:**
- `src/auth/` (8 files, 15 changes)
- `tests/integration/` (5 files, 8 changes)
- `src/middleware/` (3 files, 5 changes)

🔥 **Hot Files:**
1. `src/auth/oauth.py` - 5 changes, 450 +lines, 50 -lines
2. `src/middleware/session.py` - 3 changes, 85 +lines, 20 -lines
3. `tests/integration/test_auth.py` - 2 changes, 200 +lines, 0 -lines

📊 **Language Breakdown:**
- Python: 12 files (650 +lines, 120 -lines)
- TypeScript: 5 files (200 +lines, 30 -lines)
- Markdown: 2 files (50 +lines, 10 -lines)
```

**Implementation Location:**
- Add to: `glin/git_tools/heatmap.py`
- Can be called from `worklog_entry` prompt

---

### 5. Impact & Risk Assessment ⚠️

**Problem:** No sense of the significance or risk of changes.

**Solution: Enhance prompts with impact analysis:**

Update `worklog_entry_prompt` in `glin/prompts.py:175-216`:

```python
@mcp.prompt(
    name="worklog_entry",
    description=(
        "Generate a comprehensive worklog entry for a given date or period. "
        "Fetches Git commits, enriches with statistics and categorization, "
        "fetches related conversations, and produces a structured narrative."
    ),
    tags=["worklog", "summary", "daily", "git", "commits"],
)
def worklog_entry_prompt(date: str, inputs: str | None = None, remote_url: str | None = None):
    # ... existing code ...

    user = (
        f"Create a comprehensive worklog entry for: {date}\n\n"
        "## Instructions\n"
        "1. Fetch data:\n"
        "   - Use 'get_commits_by_date' for commits\n"
        "   - Use 'get_recent_conversations' for conversations (if available)\n"
        "   - Use 'get_enriched_commits' for detailed commit analysis\n"
        "   - Use 'get_file_heatmap' for focus areas\n\n"
        "2. Analyze each work area:\n"
        "   - Assess impact: core/peripheral, breaking/non-breaking\n"
        "   - Note testing coverage: tests added/modified\n"
        "   - Flag risks: large refactors, deprecated APIs, TODO markers\n"
        "   - Link related conversations to commits\n\n"
        "3. Structure output with these sections:\n"
        "   - Context (from conversations)\n"
        "   - Technical Work (grouped by theme/session)\n"
        "   - Metrics (commits, lines, languages, files)\n"
        "   - Impact Assessment (high/medium/low impact changes)\n"
        "   - Key Decisions (from conversations + commit messages)\n"
        "   - Open Items (TODOs, next steps)\n\n"
        "4. Formatting:\n"
        "   - Use emojis sparingly for section markers\n"
        "   - Link commits to repo URLs using provided prefix\n"
        "   - Keep total output under 50 lines\n"
        "   - Use bullet points and sub-bullets for hierarchy\n\n"
    )

    if inputs:
        user += f"<ADDITIONAL_INPUTS>\n{inputs}\n</ADDITIONAL_INPUTS>\n\n"

    if remote_url:
        commit_url_prefix = _determine_commit_url_prefix(remote_url)
        user += f"Commit URL prefix: {commit_url_prefix}\n"

    # ... rest of implementation
```

**Worklog Enhancement:**
```markdown
## 2025-10-11

### Impact Assessment

⚠️ **High Impact Changes:**
- **Auth system refactor** (5 commits, 12 files touched)
  - BREAKING: Changed token format (requires migration)
  - Core module: affects all authenticated endpoints
  - ✅ Well-covered: 15 new integration tests added
  - Risk: Medium (isolated to auth module, good test coverage)

🟢 **Low Risk Changes:**
- Bug fixes in session handling (2 commits, 3 files)
  - Isolated changes, backward compatible
  - ✅ Covered: Existing tests pass + 5 new edge case tests

📝 **Documentation:**
- API docs updated (1 commit)
  - Low risk, informational only
```

**Implementation Location:**
- Update: `glin/prompts.py` - `worklog_entry_prompt()`
- The LLM will perform the analysis based on enriched data

---

### 6. Rich Markdown Structure 📝

**Problem:** Current worklog is just bullet points.

**Solution: Implement structured markdown generator:**

```python
def generate_rich_worklog(
    date: str,
    commits: list[dict],
    conversations: list[dict] | None = None,
    enriched_data: dict | None = None,
    heatmap: dict | None = None
) -> str:
    """Generate structured markdown with all sections.

    Template:
    ## {date}

    ### 🎯 Goals & Context
    ### 💻 Technical Work
    ### 📊 Metrics
    ### 🔍 Key Decisions
    ### ⚠️ Impact Assessment
    ### 🚧 Open Items
    ### 📚 Learnings
    """

    sections = []

    # Header
    sections.append(f"## {date}\n")

    # Context section (from conversations)
    if conversations:
        sections.append("### 🎯 Goals & Context\n")
        for conv in conversations[:3]:  # Top 3 conversations
            title = conv.get("title", "Coding session")
            messages = conv.get("messages", [])
            if messages:
                first_user_msg = next((m["content"][:100] for m in messages if m["role"] == "user"), None)
                if first_user_msg:
                    sections.append(f"- **{title}:** \"{first_user_msg}...\"\n")
        sections.append("\n")

    # Technical Work (grouped by session/theme)
    sections.append("### 💻 Technical Work\n")
    if enriched_data and "sessions" in enriched_data:
        for session in enriched_data["sessions"]:
            start = session["start_time"]
            end = session["end_time"]
            duration = session["duration_minutes"]
            theme = session["theme"]
            sections.append(f"\n**Session: {start[:10]} {start[11:16]}-{end[11:16]}** ({duration}m)\n")
            sections.append(f"*{theme}*\n")
            for commit in session["commits"]:
                msg = commit["message"]
                sha = commit["hash"][:7]
                sections.append(f"- {msg} ({sha})\n")
    else:
        # Fallback: simple commit listing
        for commit in commits:
            if "message" in commit:
                msg = commit["message"]
                sha = commit.get("hash", "")[:7]
                sections.append(f"- {msg} ({sha})\n")
    sections.append("\n")

    # Metrics section
    sections.append("### 📊 Metrics\n")
    total_commits = len([c for c in commits if "hash" in c])
    sections.append(f"- **{total_commits} commits**\n")

    if enriched_data and "totals" in enriched_data:
        totals = enriched_data["totals"]
        sections.append(f"- **{totals['additions']} additions, {totals['deletions']} deletions**\n")

    if heatmap and "languages" in heatmap:
        lang_summary = ", ".join(
            f"{lang} ({data['additions']}+)"
            for lang, data in sorted(
                heatmap["languages"].items(),
                key=lambda x: x[1]["additions"],
                reverse=True
            )[:3]
        )
        sections.append(f"- **Languages:** {lang_summary}\n")

    if heatmap and "files" in heatmap:
        top_file = heatmap["files"][0] if heatmap["files"] else None
        if top_file:
            sections.append(f"- **Hot file:** {top_file['path']} ({top_file['changes']} changes)\n")
    sections.append("\n")

    # Impact Assessment section
    sections.append("### ⚠️ Impact Assessment\n")
    sections.append("*Analysis based on changed files and commit messages*\n")
    # This would be populated by LLM analysis
    sections.append("\n")

    # Key Decisions section
    sections.append("### 🔍 Key Decisions\n")
    # Extract from conversations and commit messages
    sections.append("\n")

    # Open Items section
    sections.append("### 🚧 Open Items\n")
    # Could scan for TODO, FIXME in commit messages
    sections.append("\n")

    return "".join(sections)


@mcp.tool(name="generate_rich_worklog")
async def _tool_generate_rich_worklog(
    date: str,
    ctx: Context | None = None
) -> dict:
    """Generate a rich, structured worklog entry for the given date.

    This is a high-level tool that orchestrates:
    - Fetching commits
    - Enriching with analysis
    - Fetching conversations
    - Generating file heatmap
    - Producing structured markdown

    Returns:
        {
            "markdown": "...",
            "metadata": {
                "commit_count": 8,
                "conversation_count": 3,
                ...
            }
        }
    """
    from .git_tools.commits import get_commits_by_date
    from .git_tools.enrichment import get_enriched_commits
    from .git_tools.heatmap import get_file_heatmap
    from .storage.conversations import query_conversations

    # Fetch all data
    commits = await get_commits_by_date(date, date)
    enriched = await get_enriched_commits(date, date)
    heatmap = await get_file_heatmap(date, date)

    # Try to fetch conversations
    conversations = []
    try:
        conversations = query_conversations({
            "created_from": f"{date} 00:00:00",
            "created_until": f"{date} 23:59:59"
        })
    except Exception:
        pass  # Conversations may not be available

    # Generate markdown
    markdown = generate_rich_worklog(
        date=date,
        commits=commits,
        conversations=conversations,
        enriched_data=enriched,
        heatmap=heatmap
    )

    return {
        "markdown": markdown,
        "metadata": {
            "commit_count": len([c for c in commits if "hash" in c]),
            "conversation_count": len(conversations),
            "files_touched": heatmap.get("total_files_touched", 0),
            "generated_at": datetime.now().isoformat()
        }
    }
```

**Worklog Enhancement:**
See "Example: Before vs After" section below.

**Implementation Location:**
- Add to: new file `glin/worklog_generator.py`
- Update: `glin/mcp_app.py` to import this module

---

### 7. Conversation-Commit Linking 🔗

**Problem:** Can't connect "what you talked about" with "what you built."

**Solution: Add association table:**

```python
# Add to glin/storage/db.py MIGRATIONS

def _mig_2(conn: sqlite3.Connection) -> None:
    """Migration V2: Add commit-conversation linking."""
    conn.executescript(
        """
        CREATE TABLE commit_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_sha TEXT NOT NULL,
            conversation_id INTEGER NOT NULL,
            relevance_score REAL DEFAULT 1.0,  -- 0.0 to 1.0
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            UNIQUE(commit_sha, conversation_id)
        );

        CREATE INDEX idx_commit_conversations_sha ON commit_conversations(commit_sha);
        CREATE INDEX idx_commit_conversations_conv ON commit_conversations(conversation_id);
        """
    )

# Update MIGRATIONS dict
MIGRATIONS: dict[int, MigrationFn] = {
    1: _mig_1,
    2: _mig_2,
}
```

```python
# Add to glin/storage/conversations.py or new glin/storage/links.py

def link_commit_to_conversation(
    commit_sha: str,
    conversation_id: int,
    relevance_score: float = 1.0,
    db_path: str | None = None
) -> int:
    """Associate a commit with a conversation.

    Returns the link id.
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO commit_conversations (commit_sha, conversation_id, relevance_score)
            VALUES (?, ?, ?)
            ON CONFLICT(commit_sha, conversation_id) DO UPDATE SET
                relevance_score = excluded.relevance_score,
                created_at = datetime('now')
            """,
            (commit_sha, conversation_id, relevance_score)
        )
        return int(cur.lastrowid)


def get_conversations_for_commit(
    commit_sha: str,
    db_path: str | None = None
) -> list[dict]:
    """Get all conversations linked to a commit."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.id, c.title, c.created_at, c.updated_at,
                cc.relevance_score, cc.created_at as linked_at
            FROM conversations c
            JOIN commit_conversations cc ON c.id = cc.conversation_id
            WHERE cc.commit_sha = ?
            ORDER BY cc.relevance_score DESC
            """,
            (commit_sha,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_commits_for_conversation(
    conversation_id: int,
    db_path: str | None = None
) -> list[dict]:
    """Get all commits linked to a conversation."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                commit_sha, relevance_score, created_at as linked_at
            FROM commit_conversations
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            """,
            (conversation_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# MCP tool
@mcp.tool(name="link_commit_to_conversation")
async def _tool_link_commit_to_conversation(
    commit_sha: str,
    conversation_id: int,
    relevance_score: float = 1.0
) -> dict:
    """Associate a commit with a conversation.

    Use this when a commit implements work discussed in a conversation.
    Relevance score (0.0-1.0) indicates how strongly related they are.
    """
    link_id = link_commit_to_conversation(commit_sha, conversation_id, relevance_score)
    return {
        "ok": True,
        "link_id": link_id,
        "commit_sha": commit_sha,
        "conversation_id": conversation_id
    }
```

**Worklog Enhancement:**
```markdown
## 2025-10-11

### Morning Session (9:15-11:45)
🗣️ **Started with conversation #47:** "How do I implement OAuth2 token refresh?"

**Technical Implementation:**
- feat(auth): add OAuth2 refresh flow → [abc123](link)
  💬 Related to conversation #47: "Discussed token expiry edge cases"

- fix(auth): handle expired tokens → [def456](link)
  💬 Related to conversation #47: "User mentioned production errors"
```

**Implementation Location:**
- Update: `glin/storage/db.py` - add migration
- Add: `glin/storage/links.py` - linking functions
- Update: `glin/prompts.py` - `worklog_entry_prompt()` to fetch links

---

## Concrete Implementation Roadmap

### Phase 1: Conversation Integration (Week 1) - 8 hours
**Priority: HIGHEST - Quick win with massive impact**

1. ✅ Create conversation MCP tools (2 hours)
   - File: `glin/conversation_tools.py`
   - Tools: `record_conversation_message`, `get_recent_conversations`
   - Use existing `glin/storage/conversations.py` functions

2. ✅ Update worklog_entry prompt (1 hour)
   - File: `glin/prompts.py:175-216`
   - Add instructions to fetch conversations
   - Add conversation section to output template

3. ✅ Test conversation flow (1 hour)
   - Write tests in `tests/test_conversation_tools.py`
   - Manual test with MCP client

4. ✅ Documentation (1 hour)
   - Update README.md with new tools
   - Add examples to agents.md

### Phase 2: Enrichment Pipeline (Week 2) - 12 hours

1. ✅ Create enrichment module (3 hours)
   - File: `glin/git_tools/enrichment.py`
   - Function: `get_enriched_commits()`
   - Calls existing analysis tools

2. ✅ Create file heatmap module (3 hours)
   - File: `glin/git_tools/heatmap.py`
   - Function: `get_file_heatmap()`
   - MCP tool wrapper

3. ✅ Create session detection (4 hours)
   - File: `glin/git_tools/sessions.py`
   - Function: `detect_work_sessions()`
   - Time gap + file overlap logic

4. ✅ Update prompts to use enriched data (2 hours)
   - Update `worklog_entry_prompt`
   - Add examples showing enriched output

### Phase 3: Rich Worklog Format (Week 3) - 10 hours

1. ✅ Design markdown template (2 hours)
   - Document structure in comments
   - Get user feedback on sections

2. ✅ Implement worklog generator (4 hours)
   - File: `glin/worklog_generator.py`
   - Function: `generate_rich_worklog()`
   - MCP tool: `generate_rich_worklog`

3. ✅ Update prompts with rich template (2 hours)
   - File: `glin/prompts.py`
   - Add detailed instructions
   - Add examples

4. ✅ Testing & iteration (2 hours)
   - Test with real data
   - Refine template based on output

### Phase 4: Advanced Features (Week 4) - 12 hours

1. ✅ Commit-conversation linking (4 hours)
   - Migration in `glin/storage/db.py`
   - Functions in `glin/storage/links.py`
   - MCP tools

2. ✅ Impact & risk assessment (3 hours)
   - Enhance prompts with assessment logic
   - Add risk indicators

3. ✅ Work pattern analysis (3 hours)
   - Analyze commit patterns over time
   - Identify trends

4. ✅ Learning extraction (2 hours)
   - Extract learnings from conversations
   - Add to worklog template

**Total Estimated Time:** 42 hours (~1 month part-time)

---

## Quick Wins (Start Here)

If you want immediate improvement, prioritize these:

### 1. Expose Conversation MCP Tools (2 hours)
**Impact:** 10x improvement
**Effort:** Low

- Use existing storage code
- Add 2 MCP tool wrappers in new file `glin/conversation_tools.py`

```python
# glin/conversation_tools.py
from .mcp_app import mcp
from .storage.conversations import (
    add_conversation,
    add_message,
    query_conversations,
    list_messages
)

@mcp.tool(name="record_conversation_message")
async def record_conversation_message(
    role: str,
    content: str,
    conversation_id: int | None = None,
    title: str | None = None
) -> dict:
    if conversation_id is None:
        conversation_id = add_conversation(title=title)

    message_id = add_message(conversation_id, role, content)

    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "role": role,
        "content_length": len(content)
    }


@mcp.tool(name="get_recent_conversations")
async def get_recent_conversations(
    date: str | None = None,
    limit: int = 10
) -> list[dict]:
    filters = {"limit": limit, "order_by": "updated_at", "order": "desc"}

    if date:
        filters["created_from"] = f"{date} 00:00:00"
        filters["created_until"] = f"{date} 23:59:59"

    conversations = query_conversations(filters)

    # Enrich with message count
    result = []
    for conv in conversations:
        messages = list_messages(conv["id"])
        result.append({
            **conv,
            "message_count": len(messages),
            "first_message": messages[0]["content"][:100] if messages else None
        })

    return result
```

Then update `glin/mcp_app.py` to import:
```python
from . import (
    git_tools as _git_tools,
    markdown_tools as _markdown_tools,
    prompts as _prompts,
    conversation_tools as _conversation_tools,  # ADD THIS
)
```

### 2. Integrate Existing Analysis in Worklog Prompt (1 hour)
**Impact:** 5x improvement
**Effort:** Very Low

Update `glin/prompts.py` line 199:

```python
user = (
    f"Create a worklog entry for the period: {date}. "
    "1. Fetch Git commits using 'get_commits_by_date'.\n"
    "2. For each commit, call 'get_commit_statistics' to get line counts and language breakdown.\n"
    "3. Call 'categorize_commit' to identify conventional commit types.\n"
    "4. Group commits by type (feat/fix/test/etc) and summarize.\n"
    "5. Include aggregate metrics: total commits, lines added/deleted by language.\n"
    # ... rest
)
```

### 3. Add Structured Markdown Template (2 hours)
**Impact:** 3x improvement
**Effort:** Low

Update the `worklog_entry_prompt` instructions to produce:
```
## {date}

### Context & Goals
[From conversations or commit messages]

### Technical Work
**{Category} ({n} commits)**
- {message} [{sha}]({url}) - {stats}

### Metrics
- X commits | Y +lines, Z -lines
- Languages: Python (X%), TypeScript (Y%)

### Next Steps
[TODOs, open items]
```

---

## Example: Before vs After

### Before (Current State)
```markdown
## 2025-10-11

- feat(auth): implement OAuth2 token refresh
- fix(auth): handle expired tokens
- test: add integration tests
- docs: update API documentation
```

**Problems:**
- No context (why was this done?)
- No analysis (what's the impact?)
- No structure (just a flat list)
- No narrative (can't tell the story)

---

### After (With All Improvements)
```markdown
## 2025-10-11

### 🎯 Context & Goals
**Morning Discussion (Conversation #47):** "How do I implement OAuth2 token refresh?"
- User reported production 401 errors affecting 15% of users
- Identified root cause: tokens expiring without proper refresh handling
- Discussed token rotation strategies and edge cases

### 💻 Technical Work

**Morning Session: Authentication System Overhaul** (9:15-11:45 | 2h 30m)
*Primary focus: feat (4 commits)*

- **feat(auth): implement OAuth2 token refresh** [abc1234](link)
  - Added refresh token rotation mechanism
  - Implemented token expiry validation
  - **Impact:** 450 +lines, 50 -lines in `auth/oauth.py`
  - **Tests:** 8 new integration tests
  - 💬 Related to conversation #47

- **feat(auth): add token middleware** [def5678](link)
  - Automatic token refresh on 401 responses
  - **Impact:** 120 +lines in `middleware/session.py`
  - **Tests:** 3 new unit tests

- **fix(auth): handle expired token edge cases** [ghi9012](link)
  - Fixed race condition in concurrent requests
  - Added exponential backoff for retry logic
  - **Impact:** 80 +lines, 20 -lines
  - 💬 Addresses production errors mentioned in conversation #47

**Afternoon Session: Testing & Documentation** (14:00-16:30 | 2h 30m)
*Primary focus: test (3 commits), docs (1 commit)*

- **test: add comprehensive auth integration tests** [jkl3456](link)
  - 12 test cases covering edge cases
  - Mock production error scenarios
  - **Impact:** 200 +lines in `tests/integration/test_auth.py`

- **test: fix flaky session test** [mno7890](link)
  - Improved test isolation
  - **Impact:** 15 +lines, 10 -lines

- **docs: update authentication API docs** [pqr1234](link)
  - Added OAuth2 flow diagrams
  - Documented token refresh behavior
  - **Impact:** 50 +lines in `docs/api/auth.md`

### 📊 Metrics
- **8 commits** across 2 work sessions
- **650 additions, 120 deletions** (net: +530 lines)
- **Languages:**
  - Python: 12 files (85% of changes)
  - Markdown: 2 files (15% of changes)
- **Focus areas:**
  - `src/auth/` (8 files, 15 changes)
  - `tests/integration/` (5 files, 8 changes)
- **Hot files:**
  1. `src/auth/oauth.py` - 5 changes
  2. `src/middleware/session.py` - 3 changes
  3. `tests/integration/test_auth.py` - 2 changes

### ⚠️ Impact Assessment

**🔴 High Impact (Core System Changes):**
- OAuth2 token refresh system
  - **Scope:** Affects all authenticated API endpoints
  - **Breaking:** Token format changed (requires client update)
  - **Risk:** Medium - isolated to auth module
  - **Mitigation:** ✅ 15 new tests added, ✅ backward compatibility layer included

**🟡 Medium Impact (Enhancement):**
- Token middleware auto-refresh
  - **Scope:** Improves UX for expired sessions
  - **Breaking:** No
  - **Risk:** Low - graceful degradation on failure

**🟢 Low Impact (Testing & Docs):**
- Test additions and documentation updates
  - **Risk:** Minimal
  - **Coverage:** Auth module now at 92% test coverage (up from 75%)

### 🔍 Key Decisions
1. **Chose OAuth2 over JWT** for better security and revocation support
   - Source: Conversation #47, research into production patterns

2. **Implemented token rotation** instead of long-lived tokens
   - Reduces security risk if tokens are compromised

3. **Added server-side session tracking**
   - Enables immediate revocation
   - Trade-off: Additional DB queries (optimized with caching)

4. **Maintained backward compatibility**
   - Old token format supported for 30 days
   - Migration guide added to docs

### ✅ Completed Today
- ✅ OAuth2 refresh flow fully implemented and tested
- ✅ All tests passing (15 new, all existing passing)
- ✅ Production-ready: includes error handling, logging, metrics
- ✅ Documentation complete
- ✅ PR #42 reviewed and merged to main

### 🚧 Open Items & Next Steps
- [ ] Deploy to staging environment for QA testing
- [ ] Monitor error rates after production deployment
- [ ] Create metrics dashboard for token health
  - Track: refresh success rate, token age distribution, failure patterns
- [ ] Schedule follow-up: Add rate limiting for refresh endpoints (next sprint)
- [ ] TODO in code: Implement token cleanup job for expired tokens

### 📚 Learnings & Notes
- **OAuth2 best practices:** Refresh tokens should be single-use and rotated on each refresh
- **Testing insight:** Mock time in tests to verify token expiry logic reliably
- **Production debugging:** Added structured logging for token lifecycle events
- **Edge case discovered:** Concurrent refresh requests need idempotency handling

---

**Total time invested:** ~5 hours
**PR:** #42 merged
**Reviewers:** @alice (approved), @bob (approved)
```

**Improvements:**
- ✅ Context from conversations
- ✅ Work organized by sessions and themes
- ✅ Rich analysis (impact, stats, language breakdown)
- ✅ Structured sections (goals, work, metrics, decisions, next steps)
- ✅ Links between conversations and commits
- ✅ Impact assessment with risk levels
- ✅ Captured learnings and decisions
- ✅ Actionable next steps
- ✅ Metrics and focus areas

This transforms a simple commit listing into a **comprehensive engineering journal** that's actually useful for:
- Standups ("Here's what I did and why")
- Sprint reviews ("Here's the impact and metrics")
- Performance reviews ("Here's the scope and decisions I made")
- Knowledge transfer ("Here's what I learned")
- Debugging ("What changed in auth on Oct 11?")

---

## Technical Implementation Notes

### File Organization
```
glin/
├── mcp_app.py              # Register new modules
├── prompts.py              # Update worklog_entry_prompt
├── markdown_tools.py       # Keep existing
├── conversation_tools.py   # NEW - MCP wrappers for storage
├── worklog_generator.py    # NEW - Rich markdown generation
├── git_tools/
│   ├── commits.py          # Existing
│   ├── analysis.py         # Existing
│   ├── enrichment.py       # NEW - Orchestrate analysis tools
│   ├── heatmap.py          # NEW - File/directory focus
│   └── sessions.py         # NEW - Session detection
├── storage/
│   ├── db.py               # Add migration #2 for links
│   ├── conversations.py    # Existing
│   ├── commits.py          # Existing
│   └── links.py            # NEW - Commit-conversation links
```

### Testing Strategy
1. Unit tests for each new module
2. Integration tests for enrichment pipeline
3. End-to-end test: generate worklog from real data
4. Snapshot tests for markdown output format

### Migration Path
1. Phase 1 is backward compatible (adds tools, doesn't change existing)
2. Phase 2 adds new tools, existing tools unchanged
3. Phase 3 adds new `generate_rich_worklog` tool, `append_to_markdown` unchanged
4. Phase 4 requires DB migration (v1 → v2)

### Performance Considerations
- Enrichment can be slow (calls git for each commit)
  - Solution: Add caching layer, batch operations
  - Cache enrichment results in DB (optional)
- Conversation queries should be indexed
  - Already done in db.py (idx_messages_conversation)
- File heatmap needs optimization for large repos
  - Limit to date range only
  - Consider sampling for very large commit counts

---

## Success Metrics

Track these to measure improvement:

### Quantitative
- Worklog length: target 30-50 lines (vs current ~10)
- Sections included: target 6-7 sections (vs current 1)
- Conversation integration: % of worklogs with conversation context
- Enrichment coverage: % of commits with statistics
- Time to generate: < 5 seconds for typical day

### Qualitative (User Feedback)
- "Can I understand what I did and why?"
- "Is this useful for standups?"
- "Would I share this in a performance review?"
- "Does it capture key decisions?"
- "Are learnings documented?"

### Adoption
- % of days with worklog entries
- % using `generate_rich_worklog` vs basic `append_to_markdown`
- Conversation recording rate

---

## Conclusion

**Current State:** Glin is a commit logger with unused infrastructure.

**Opportunity:** By exposing existing capabilities (conversations, analysis) and adding structure, you transform it into a **comprehensive engineering journal** that captures:
- **What** you did (commits)
- **Why** you did it (conversations)
- **How** it matters (impact analysis)
- **What** you learned (extracted insights)

**Biggest Win:** Conversation integration (2 hours work, 10x improvement).

**Total Transformation:** 42 hours of work over 4 weeks gets you from "commit list" to "engineering journal that writes your standup notes."

The infrastructure is already there - you just need to connect the pieces and add the right structure! 🚀
