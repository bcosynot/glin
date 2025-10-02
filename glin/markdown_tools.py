from __future__ import annotations

import os
from pathlib import Path

from .mcp_app import mcp


@mcp.tool
def append_to_markdown(content: str, file_path: str | None = None) -> dict:
    """
    Append lines as bullet points under a date heading in a markdown file.

    Behavior:
    - Each non-empty input line becomes a markdown bullet ("- ...").
    - Ensures a heading for the current local date ("## YYYY-MM-DD"). Creates it if missing.
    - Appends bullets under today's heading, before the next heading or at the end.
    - If file_path is provided, use that path; else GLIN_MD_PATH env var; else ./WORKLOG.md.

    Args:
        content: The text to append. Must be non-empty (after stripping). Newlines will be normalized.
        file_path: Optional target file path. Can be absolute or relative to the repo root.

    Returns:
        A dict with operation details or an error message, including the exact content and line numbers added.
    """
    try:
        if content is None or str(content).strip() == "":
            return {"error": "content is required and cannot be empty"}

        from datetime import datetime

        # Resolve target path: parameter > env var > default
        target = file_path or os.getenv("GLIN_MD_PATH") or "WORKLOG.md"
        path = Path(target)
        if not path.is_absolute():
            path = Path.cwd() / path

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize input newlines to Unix and split into lines
        text = str(content).replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.strip() for ln in text.split("\n")]
        bullets = [f"- {ln}" for ln in lines if ln != ""]
        if not bullets:
            return {"error": "content contained only blank lines"}

        # Prepare date heading
        today = datetime.now().date().isoformat()
        heading = f"## {today}"

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
        insert_block.extend(bullets)

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
        for idx in range(len(bullets)):
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

        return {
            "ok": True,
            "path": str(path),
            "bullets_added": len(bullets),
            "content_added": bullets,
            "line_numbers_added": bullet_line_numbers,
            "heading": heading,
            "heading_added": heading_added,
            "heading_line_number": heading_line_number,
            "used_env": file_path is None and bool(os.getenv("GLIN_MD_PATH")),
            "defaulted": file_path is None and os.getenv("GLIN_MD_PATH") is None,
        }
    except Exception as e:
        return {"error": f"Failed to append to markdown: {e}"}
