import os
import re
from pathlib import Path
from typing import TypedDict

from .config import get_markdown_path
from .mcp_app import mcp


# Return type definitions for markdown tools
class MarkdownSuccessResponse(TypedDict):
    """Successful markdown append operation response."""

    ok: bool
    path: str
    bullets_added: int
    content_added: list[str]
    line_numbers_added: list[int]
    heading: str
    heading_added: bool
    heading_line_number: int | None
    used_env: bool
    defaulted: bool
    update_mode_used: bool
    existing_bullets_preserved: int
    new_bullets_added: int
    deduplicated_count: int


class MarkdownErrorResponse(TypedDict):
    """Error response from markdown operation."""

    error: str


class DateEntrySections(TypedDict):
    """Parsed sections from a date entry."""

    goals: list[str]
    technical: list[str]
    metrics: list[str]
    decisions: list[str]
    impact: list[str]
    open_items: list[str]
    learnings: list[str]
    weekly_summary: str | None


class DateEntryResponse(TypedDict):
    """Response from reading a date entry."""

    exists: bool
    date: str
    heading_line: int | None
    sections: DateEntrySections
    raw_content: str


def read_date_entry(
    date_str: str,
    file_path: str | None = None,
) -> DateEntryResponse:
    """
    Read and parse an existing date entry from the markdown file.

    Args:
        date_str: Date in ISO format (YYYY-MM-DD) to search for.
        file_path: Optional target file path. Uses same resolution as append_to_markdown.

    Returns:
        A dict with exists flag, date, heading line number, parsed sections, and raw content.
        If the date entry doesn't exist, returns exists=False with empty sections.
    """
    from datetime import date

    # Validate date format
    try:
        parsed_date = date.fromisoformat(date_str)
        date_iso = parsed_date.isoformat()
    except ValueError:
        # Return non-existent entry for invalid date
        return {
            "exists": False,
            "date": date_str,
            "heading_line": None,
            "sections": {
                "goals": [],
                "technical": [],
                "metrics": [],
                "decisions": [],
                "impact": [],
                "open_items": [],
                "learnings": [],
                "weekly_summary": None,
            },
            "raw_content": "",
        }

    # Resolve target path using same logic as append_to_markdown
    if file_path and str(file_path).strip():
        target = str(file_path).strip()
    else:
        target = get_markdown_path()
    path = Path(target)
    if not path.is_absolute():
        path = Path.cwd() / path

    # If file doesn't exist, return non-existent entry
    if not path.exists():
        return {
            "exists": False,
            "date": date_iso,
            "heading_line": None,
            "sections": {
                "goals": [],
                "technical": [],
                "metrics": [],
                "decisions": [],
                "impact": [],
                "open_items": [],
                "learnings": [],
                "weekly_summary": None,
            },
            "raw_content": "",
        }

    # Read and normalize file content
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")

    # Find the date heading
    heading = f"## {date_iso}"
    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            heading_idx = i
            break

    # If heading not found, return non-existent entry
    if heading_idx is None:
        return {
            "exists": False,
            "date": date_iso,
            "heading_line": None,
            "sections": {
                "goals": [],
                "technical": [],
                "metrics": [],
                "decisions": [],
                "impact": [],
                "open_items": [],
                "learnings": [],
                "weekly_summary": None,
            },
            "raw_content": "",
        }

    # Find the end of this date section (next ## heading or end of file)
    end_idx = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        # Match only level 2 headings (## ), not level 3 (###) or deeper
        if stripped.startswith("## ") and len(stripped) > 3:
            end_idx = i
            break

    # Extract raw content for this date section
    section_lines = lines[heading_idx + 1 : end_idx]
    raw_content = "\n".join(section_lines)

    # Parse sections by ### headings with emoji markers
    sections: DateEntrySections = {
        "goals": [],
        "technical": [],
        "metrics": [],
        "decisions": [],
        "impact": [],
        "open_items": [],
        "learnings": [],
        "weekly_summary": None,
    }

    # Section markers (emoji + text patterns)
    section_patterns = {
        "goals": r"###\s*🎯\s*Goals?\s*(&\s*Context)?",
        "technical": r"###\s*💻\s*Technical\s*Work",
        "metrics": r"###\s*📊\s*Metrics?",
        "decisions": r"###\s*🔍\s*Key\s*Decisions?",
        "impact": r"###\s*⚠️\s*Impact\s*Assessment",
        "open_items": r"###\s*🚧\s*Open\s*Items?",
        "learnings": r"###\s*📚\s*Learnings?",
        "weekly_summary": r"###\s*🗓️\s*Weekly\s*Summary",
    }

    current_section = None
    weekly_summary_lines = []

    for line in section_lines:
        # Check if this line starts a new section
        matched_section = None
        for section_key, pattern in section_patterns.items():
            if re.match(pattern, line.strip(), re.IGNORECASE):
                matched_section = section_key
                break

        if matched_section:
            current_section = matched_section
            if current_section == "weekly_summary":
                weekly_summary_lines = []
        elif current_section:
            # Extract content based on section type
            stripped = line.strip()
            if current_section == "weekly_summary":
                # Collect all lines for weekly summary
                weekly_summary_lines.append(line)
            elif stripped.startswith("- "):
                # Extract bullet content (remove "- " prefix)
                bullet_content = stripped[2:].strip()
                if bullet_content:
                    sections[current_section].append(bullet_content)
            elif stripped.startswith("* "):
                # Also handle * bullets
                bullet_content = stripped[2:].strip()
                if bullet_content:
                    sections[current_section].append(bullet_content)

    # Set weekly summary if any content was collected
    if weekly_summary_lines:
        sections["weekly_summary"] = "\n".join(weekly_summary_lines).strip()

    return {
        "exists": True,
        "date": date_iso,
        "heading_line": heading_idx + 1,  # 1-based line number
        "sections": sections,
        "raw_content": raw_content,
    }


def _extract_commit_hash(bullet: str) -> str | None:
    """
    Extract commit hash from a bullet point.

    Handles formats like:
    - [abc123](url) - message
    - abc123 - message
    - Commit abc123: message
    """
    # Try markdown link format [hash](url)
    match = re.search(r"\[([a-f0-9]{7,40})\]", bullet, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # Try plain hash at start
    match = re.match(r"^([a-f0-9]{7,40})\s*[-:]", bullet, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # Try "Commit hash:" format
    match = re.search(r"commit\s+([a-f0-9]{7,40})", bullet, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    return None


def _normalize_bullet(bullet: str) -> str:
    """Normalize a bullet for comparison by removing extra whitespace."""
    return " ".join(bullet.split()).strip()


def _is_similar(text1: str, text2: str, threshold: float = 0.85) -> bool:
    """
    Check if two text strings are similar using simple character-based similarity.

    Args:
        text1: First text string
        text2: Second text string
        threshold: Similarity threshold (0.0 to 1.0)

    Returns:
        True if similarity >= threshold
    """
    norm1 = _normalize_bullet(text1).lower()
    norm2 = _normalize_bullet(text2).lower()

    if norm1 == norm2:
        return True

    # Simple character overlap ratio
    if not norm1 or not norm2:
        return False

    # Use set intersection for simple fuzzy matching
    chars1 = set(norm1)
    chars2 = set(norm2)
    intersection = len(chars1 & chars2)
    union = len(chars1 | chars2)

    if union == 0:
        return False

    similarity = intersection / union
    return similarity >= threshold


def _deduplicate_bullets(existing: list[str], new: list[str]) -> tuple[list[str], int]:
    """
    Deduplicate bullets, preserving order and unique items from both lists.

    Args:
        existing: Existing bullets
        new: New bullets to merge

    Returns:
        Tuple of (merged list, count of duplicates removed)
    """
    merged = list(existing)  # Start with existing bullets
    duplicates = 0

    for new_bullet in new:
        is_duplicate = False

        # Check against all merged bullets
        for existing_bullet in merged:
            if _is_similar(new_bullet, existing_bullet):
                is_duplicate = True
                duplicates += 1
                break

        if not is_duplicate:
            merged.append(new_bullet)

    return merged, duplicates


def _deduplicate_commits(existing: list[str], new: list[str]) -> tuple[list[str], int]:
    """
    Deduplicate commit bullets by hash, preserving order.

    Args:
        existing: Existing commit bullets
        new: New commit bullets to merge

    Returns:
        Tuple of (merged list, count of duplicates removed)
    """
    merged = list(existing)
    seen_hashes = set()
    duplicates = 0

    # Extract hashes from existing commits
    for bullet in existing:
        commit_hash = _extract_commit_hash(bullet)
        if commit_hash:
            seen_hashes.add(commit_hash)

    # Add new commits if hash not seen
    for bullet in new:
        commit_hash = _extract_commit_hash(bullet)
        if commit_hash:
            if commit_hash in seen_hashes:
                duplicates += 1
                continue
            seen_hashes.add(commit_hash)
        merged.append(bullet)

    return merged, duplicates


def merge_date_sections(
    existing: DateEntryResponse,
    new_content: str,
    *,
    preserve_lines: bool = False,
) -> tuple[str, int]:
    """
    Merge new content with existing date entry sections.

    Args:
        existing: Result from read_date_entry
        new_content: New markdown content to merge (with ### sections)
        preserve_lines: Same semantics as append_to_markdown

    Returns:
        Tuple of (merged markdown content ready to write, deduplicated count)
    """
    # Parse new content into sections
    new_sections: DateEntrySections = {
        "goals": [],
        "technical": [],
        "metrics": [],
        "decisions": [],
        "impact": [],
        "open_items": [],
        "learnings": [],
        "weekly_summary": None,
    }

    # Normalize and split new content
    text = str(new_content).replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]

    # Section patterns (same as read_date_entry)
    section_patterns = {
        "goals": r"###\s*🎯\s*Goals?\s*(&\s*Context)?",
        "technical": r"###\s*💻\s*Technical\s*Work",
        "metrics": r"###\s*📊\s*Metrics?",
        "decisions": r"###\s*🔍\s*Key\s*Decisions?",
        "impact": r"###\s*⚠️\s*Impact\s*Assessment",
        "open_items": r"###\s*🚧\s*Open\s*Items?",
        "learnings": r"###\s*📚\s*Learnings?",
        "weekly_summary": r"###\s*🗓️\s*Weekly\s*Summary",
    }

    current_section = None
    weekly_summary_lines = []

    for line in lines:
        # Check if this line starts a new section
        matched_section = None
        for section_key, pattern in section_patterns.items():
            if re.match(pattern, line.strip(), re.IGNORECASE):
                matched_section = section_key
                break

        if matched_section:
            current_section = matched_section
            if current_section == "weekly_summary":
                weekly_summary_lines = []
        elif current_section:
            stripped = line.strip()
            if current_section == "weekly_summary":
                weekly_summary_lines.append(line)
            elif stripped.startswith("- "):
                bullet_content = stripped[2:].strip()
                if bullet_content:
                    new_sections[current_section].append(bullet_content)
            elif stripped.startswith("* "):
                bullet_content = stripped[2:].strip()
                if bullet_content:
                    new_sections[current_section].append(bullet_content)
            elif preserve_lines and stripped:
                # In preserve_lines mode, include non-bullet lines too
                new_sections[current_section].append(stripped)

    if weekly_summary_lines:
        new_sections["weekly_summary"] = "\n".join(weekly_summary_lines).strip()

    # Merge sections with deduplication
    merged_sections: DateEntrySections = {
        "goals": [],
        "technical": [],
        "metrics": [],
        "decisions": [],
        "impact": [],
        "open_items": [],
        "learnings": [],
        "weekly_summary": None,
    }

    total_duplicates = 0

    # Merge each section with appropriate strategy
    for section_key in ["goals", "decisions", "impact", "open_items", "learnings"]:
        merged_sections[section_key], dupes = _deduplicate_bullets(
            existing["sections"][section_key], new_sections[section_key]
        )
        total_duplicates += dupes

    # Technical section: deduplicate by commit hash
    merged_sections["technical"], dupes = _deduplicate_commits(
        existing["sections"]["technical"], new_sections["technical"]
    )
    total_duplicates += dupes

    # Metrics: prefer new (recalculated) over existing
    merged_sections["metrics"] = (
        new_sections["metrics"] if new_sections["metrics"] else existing["sections"]["metrics"]
    )

    # Weekly summary: preserve existing unless new one provided
    if new_sections["weekly_summary"]:
        merged_sections["weekly_summary"] = new_sections["weekly_summary"]
    else:
        merged_sections["weekly_summary"] = existing["sections"]["weekly_summary"]

    # Reconstruct markdown content
    output_lines = []

    # Add sections in standard order
    section_order = [
        ("goals", "### 🎯 Goals & Context"),
        ("technical", "### 💻 Technical Work"),
        ("metrics", "### 📊 Metrics"),
        ("decisions", "### 🔍 Key Decisions"),
        ("impact", "### ⚠️ Impact Assessment"),
        ("open_items", "### 🚧 Open Items"),
        ("learnings", "### 📚 Learnings"),
    ]

    for section_key, section_heading in section_order:
        bullets = merged_sections[section_key]
        if bullets:
            output_lines.append("")
            output_lines.append(section_heading)
            output_lines.append("")
            for bullet in bullets:
                output_lines.append(f"- {bullet}")

    # Add weekly summary if present
    if merged_sections["weekly_summary"]:
        output_lines.append("")
        output_lines.append("### 🗓️ Weekly Summary")
        output_lines.append("")
        # Weekly summary content already formatted
        for line in merged_sections["weekly_summary"].split("\n"):
            output_lines.append(line)

    # Join with newlines
    merged_content = "\n".join(output_lines)

    return merged_content, total_duplicates


def append_to_markdown(
    content: str,
    file_path: str | None = None,
    date_str: str | None = None,
    *,
    preserve_lines: bool = False,
    update_mode: bool = False,
) -> MarkdownSuccessResponse | MarkdownErrorResponse:
    """
    Append content under a date heading in a markdown file.

    Behavior:
    - Default (preserve_lines=False): Each non-empty input line becomes a markdown bullet ("- ...").
    - Raw mode (preserve_lines=True): Lines are written as-is (no automatic bullet prefix). Useful for writing headings like "### Goals".
    - Update mode (update_mode=True): Read existing entry for the date and merge new content with existing sections instead of appending.
    - Ensures a heading for the specified date ("## YYYY-MM-DD"). If no date is provided, uses the current local date. Creates it if missing.
    - Appends content under the chosen date's heading, before the next heading or at the end.
    - Path resolution: file_path argument > GLIN_MD_PATH env var > glin.toml `markdown_path` > ./WORKLOG.md.

    Args:
        content: The text to append. Must be non-empty (after stripping). Newlines will be normalized.
        file_path: Optional target file path. Can be absolute or relative to the repo root.
        date_str: Optional date string in ISO format (YYYY-MM-DD). When provided, content is added under this date's heading instead of today's.
        preserve_lines: When True, write lines as-is; when False, prefix each non-empty line with "- ".
        update_mode: When True, read existing entry for the date and merge new content with existing sections instead of appending.
                     When False (default), append as before (backward compatible).

    Returns:
        A dict with operation details or an error message, including the exact content and line numbers added.
    """
    try:
        if content is None or str(content).strip() == "":
            error_response: MarkdownErrorResponse = {
                "error": "content is required and cannot be empty"
            }
            return error_response

        from datetime import date, datetime

        # Resolve target path: parameter > env var > glin.toml > default
        if file_path and str(file_path).strip():
            target = str(file_path).strip()
            used_env_flag = False
            defaulted_flag = False
        else:
            # Delegate env/TOML/default resolution to config
            target = get_markdown_path()
            used_env_flag = bool(os.getenv("GLIN_MD_PATH"))
            # Consider defaulted when neither param nor env provided and config didn't override
            defaulted_flag = (not used_env_flag) and (target == "WORKLOG.md")
        path = Path(target)
        if not path.is_absolute():
            path = Path.cwd() / path

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare date heading (validate provided date_str if any)
        if date_str is not None:
            try:
                # Validate format using fromisoformat; it raises ValueError for invalid strings
                chosen_date: date = date.fromisoformat(date_str)
            except ValueError:
                return {"error": "date_str must be in YYYY-MM-DD format"}
            date_for_heading = chosen_date.isoformat()
        else:
            date_for_heading = datetime.now().date().isoformat()

        # UPDATE MODE: Read existing entry and merge
        if update_mode:
            existing = read_date_entry(date_for_heading, file_path)

            if existing["exists"]:
                # Merge new content with existing
                merged_content, deduplicated_count = merge_date_sections(
                    existing, content, preserve_lines=preserve_lines
                )

                # Read the file to replace the date section
                if path.exists():
                    file_content = (
                        path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
                    )
                    doc_lines = file_content.split("\n")
                    if doc_lines and doc_lines[-1] == "":
                        doc_lines.pop()
                else:
                    doc_lines = []

                # Find the date heading
                heading = f"## {date_for_heading}"
                heading_idx = None
                for i, line in enumerate(doc_lines):
                    if line.strip() == heading:
                        heading_idx = i
                        break

                # Find the end of this date section
                end_idx = len(doc_lines)
                if heading_idx is not None:
                    for i in range(heading_idx + 1, len(doc_lines)):
                        stripped = doc_lines[i].strip()
                        # Match only level 2 headings (## ), not level 3 (###) or deeper
                        if stripped.startswith("## ") and len(stripped) > 3:
                            end_idx = i
                            break

                    # Replace the section content (keep heading, replace everything until next heading)
                    merged_lines = merged_content.split("\n")
                    # Remove leading empty line if present (we'll add proper spacing)
                    while merged_lines and merged_lines[0].strip() == "":
                        merged_lines.pop(0)

                    # Ensure blank line after heading
                    replacement = [""]
                    replacement.extend(merged_lines)

                    # Ensure blank line before next heading if there is one
                    if end_idx < len(doc_lines):
                        replacement.append("")

                    # Replace content between heading and next section
                    doc_lines[heading_idx + 1 : end_idx] = replacement

                    # Count bullets in merged content
                    bullet_count = sum(1 for line in merged_lines if line.strip().startswith("- "))

                    # Reconstruct and write
                    new_content = "\n".join(doc_lines)
                    if not new_content.endswith("\n"):
                        new_content += "\n"
                    path.write_text(new_content, encoding="utf-8")

                    # Calculate statistics
                    existing_bullet_count = sum(
                        len(bullets)
                        for bullets in existing["sections"].values()
                        if isinstance(bullets, list)
                    )
                    new_bullets_added = bullet_count - existing_bullet_count + deduplicated_count

                    success_response: MarkdownSuccessResponse = {
                        "ok": True,
                        "path": str(path),
                        "bullets_added": bullet_count,
                        "content_added": merged_lines,
                        "line_numbers_added": list(
                            range(heading_idx + 2, heading_idx + 2 + len(merged_lines))
                        ),
                        "heading": heading,
                        "heading_added": False,
                        "heading_line_number": heading_idx + 1,
                        "used_env": used_env_flag,
                        "defaulted": defaulted_flag,
                        "update_mode_used": True,
                        "existing_bullets_preserved": existing_bullet_count,
                        "new_bullets_added": new_bullets_added,
                        "deduplicated_count": deduplicated_count,
                    }
                    return success_response
            # If no existing entry, fall through to normal append logic below

        # Normalize input newlines to Unix and split into lines
        text = str(content).replace("\r\n", "\n").replace("\r", "\n")
        lines = [
            ln.rstrip() for ln in text.split("\n")
        ]  # preserve leading '#' etc.; strip right only
        # Build the block lines according to mode
        if preserve_lines:
            block_lines = [ln for ln in lines if ln.strip() != ""]
        else:
            block_lines = [f"- {ln.strip()}" for ln in lines if ln.strip() != ""]
        if not block_lines:
            error_response: MarkdownErrorResponse = {"error": "content contained only blank lines"}
            return error_response

        heading = f"## {date_for_heading}"

        # Read existing file (normalize to Unix newlines)
        existing = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        # Ensure file ends with single newline for consistent processing
        if existing and not existing.endswith("\n"):
            existing += "\n"

        # Work with list of lines for insertion
        doc_lines = existing.split("\n") if existing else []
        # Remove a possible trailing empty string from split if file ended with newline
        if doc_lines and doc_lines[-1] == "":
            doc_lines.pop()

        # Find today's heading
        try:
            heading_idx = next(i for i, ln in enumerate(doc_lines) if ln.strip() == heading)
            heading_exists = True
        except StopIteration:
            heading_exists = False
            heading_idx = None

        # If heading is missing, append it at end with proper spacing
        if not heading_exists:
            # Ensure blank line before new heading if file not empty and last line not blank
            if doc_lines and doc_lines[-1].strip() != "":
                doc_lines.append("")
            doc_lines.append(heading)
            doc_lines.append("")  # blank line after heading
            # After appending, recalculate heading index

        # Determine insertion index: after the heading and any existing content of that section,
        # which we define as lines until the next heading (line starting with '#').
        # Recompute heading index to be robust
        heading_idx = next((i for i, ln in enumerate(doc_lines) if ln.strip() == heading), None)
        if heading_idx is None:
            # Fallback: append heading at end if somehow missing
            if doc_lines and doc_lines[-1].strip() != "":
                doc_lines.append("")
            doc_lines.append(heading)
            doc_lines.append("")
            heading_idx = len(doc_lines) - 2  # index of heading line
            heading_exists = False

        # Find next heading after current section
        next_heading_idx = None
        for i in range(heading_idx + 1, len(doc_lines)):
            if doc_lines[i].lstrip().startswith("#") and doc_lines[i].strip() != "":
                next_heading_idx = i
                break

        # Build the new section content to insert
        insert_block = []
        # Ensure there is a blank line after heading if immediate next line isn't blank and we're inserting directly
        after_heading_idx = heading_idx + 1
        if after_heading_idx >= len(doc_lines) or doc_lines[after_heading_idx].strip() != "":
            insert_block.append("")
        insert_block.extend(block_lines)

        # If there will be another heading after, ensure there is a blank line before it
        if next_heading_idx is not None:
            insert_block.append("")

        # Compute insertion position
        insert_pos = next_heading_idx if next_heading_idx is not None else len(doc_lines)

        # Determine the 1-based line numbers for the bullets we will insert
        # First, compute where within insert_block the bullets start
        bullets_offset_in_block = 1 if (len(insert_block) > 0 and insert_block[0] == "") else 0
        bullet_line_numbers = []
        # The final line number for a given inserted line at block index k is (insert_pos + k) + 1
        for idx in range(len(block_lines)):
            k = bullets_offset_in_block + idx
            bullet_line_numbers.append(insert_pos + k + 1)

        # If we created the heading in this call, compute its 1-based line number in the final document
        heading_added = not heading_exists
        heading_line_number = None
        if heading_added:
            # Heading line is at heading_idx (recomputed above) in doc_lines BEFORE inserting insert_block
            # Since we haven't yet inserted insert_block, its final 1-based line number is heading_idx + 1
            heading_line_number = heading_idx + 1

        # Insert bullets block
        doc_lines[insert_pos:insert_pos] = insert_block

        # Reconstruct content with Unix newlines and ensure file ends with newline
        new_content = "".join(line + "\n" for line in doc_lines)
        if not new_content.endswith("\n"):
            new_content += "\n"

        path.write_text(new_content, encoding="utf-8")

        success_response: MarkdownSuccessResponse = {
            "ok": True,
            "path": str(path),
            "bullets_added": len(block_lines),
            "content_added": block_lines,
            "line_numbers_added": bullet_line_numbers,
            "heading": heading,
            "heading_added": heading_added,
            "heading_line_number": heading_line_number,
            "used_env": used_env_flag,
            "defaulted": defaulted_flag,
            "update_mode_used": False,
            "existing_bullets_preserved": 0,
            "new_bullets_added": len(block_lines),
            "deduplicated_count": 0,
        }
        return success_response
    except Exception as e:
        error_response: MarkdownErrorResponse = {"error": f"Failed to append to markdown: {e}"}
        return error_response


# Register MCP tool wrappers
from fastmcp import Context  # type: ignore


@mcp.tool(
    name="read_date_entry",
    description=(
        "Read and parse an existing date entry from the markdown worklog file. "
        "Returns the parsed sections (goals, technical work, metrics, decisions, impact, "
        "open items, learnings, weekly summary) and raw content for the specified date. "
        "If the date entry doesn't exist, returns exists=False with empty sections."
    ),
)
async def _tool_read_date_entry(
    date_str: str,
    file_path: str | None = None,
    ctx: Context | None = None,
) -> DateEntryResponse:  # pragma: no cover
    """MCP tool wrapper for read_date_entry."""
    if ctx:
        await ctx.info(
            "Reading date entry",
            extra={
                "tool": "read_date_entry",
                "date_str": date_str,
                "file_path_arg": bool(file_path),
            },
        )

    result = read_date_entry(date_str=date_str, file_path=file_path)

    if ctx:
        await ctx.log(
            "Date entry read completed",
            level="info",
            logger_name="glin.markdown",
            extra={
                "exists": result["exists"],
                "date": result["date"],
                "heading_line": result["heading_line"],
                "sections_found": sum(
                    1
                    for k, v in result["sections"].items()
                    if (v if k != "weekly_summary" else v is not None)
                ),
            },
        )

    return result


@mcp.tool(
    name="append_to_markdown",
    description=(
        "Append content under a specified date heading (default: today) in a markdown file. "
        "Default behavior: each non-empty line becomes a bullet. Set preserve_lines=True to write "
        "lines as-is (useful for headings like '### Goals'). Set update_mode=True to merge with "
        "existing entry if present (deduplicates commits and bullets). Creates date heading (## YYYY-MM-DD) "
        "if missing. Target file can be specified, or resolves as: explicit file_path > GLIN_MD_PATH > glin.toml 'markdown_path' > ./WORKLOG.md."
    ),
)
async def _tool_append_to_markdown(
    content: str,
    file_path: str | None = None,
    date_str: str | None = None,
    preserve_lines: bool = False,
    update_mode: bool = False,
    ctx: Context | None = None,
) -> MarkdownSuccessResponse | MarkdownErrorResponse:  # pragma: no cover
    # Start logging
    if ctx:
        non_empty_lines = sum(1 for ln in str(content).splitlines() if ln.strip())
        await ctx.info(
            "Appending to markdown",
            extra={
                "tool": "append_to_markdown",
                "file_path_arg": bool(file_path),
                "non_empty_lines": non_empty_lines,
                "content_len": len(str(content)),
                "date_str": date_str or "<today>",
            },
        )

    result = append_to_markdown(
        content=content,
        file_path=file_path,
        date_str=date_str,
        preserve_lines=preserve_lines,
        update_mode=update_mode,
    )

    if ctx:
        if isinstance(result, dict) and result.get("ok"):
            await ctx.log(
                "Markdown append completed",
                level="info",
                logger_name="glin.markdown",
                extra={
                    "path": result["path"],
                    "bullets_added": result["bullets_added"],
                    "heading": result["heading"],
                    "heading_added": result["heading_added"],
                    "heading_line_number": result["heading_line_number"],
                    "used_env": result["used_env"],
                    "defaulted": result["defaulted"],
                    "line_numbers_added": result["line_numbers_added"],
                },
            )
        else:
            err = None
            try:
                err = None if not isinstance(result, dict) else result.get("error")
            except Exception:
                err = None
            await ctx.warning(
                "Markdown append returned an error",
                extra={"error": (err or "unknown")[:500]},
            )

    return result
