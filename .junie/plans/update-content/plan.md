# Plan: Update Existing Date Entries in Worklog

**Created:** 2025-10-23  
**Status:** Draft  
**Goal:** Modify the `worklog_entry` prompt and associated tools to detect and update existing date entries in the markdown file instead of always creating new date entries.

---

## 1. Problem Statement

### Current Behavior
- The `worklog_entry` prompt instructs the LLM to call `append_to_markdown` for each date in the period
- `append_to_markdown` always appends content under the date heading, even if content already exists for that date
- This results in duplicate or redundant entries when the same date is processed multiple times
- Users must manually merge or deduplicate entries

### Desired Behavior
- When generating a worklog entry for a date that already has content, the system should:
  1. Detect the existing entry for that date
  2. Read and parse the existing content
  3. Intelligently merge or update the existing sections with new information
  4. Preserve important existing content while adding new details
  5. Maintain idempotency (running the same command twice should not create duplicates)

---

## 2. Solution Architecture

### 2.1 High-Level Approach

**Option A: Read-Merge-Write Pattern (Recommended)**
- Before calling `append_to_markdown`, read the target markdown file
- Parse existing content for the target date
- Merge new content with existing content at the section level
- Write the merged result

**Option B: Replace-Mode Flag**
- Add a `replace_mode` parameter to `append_to_markdown`
- When enabled, replace existing date section entirely instead of appending
- Simpler but loses existing content

**Decision: Implement Option A** because it:
- Preserves valuable existing content
- Allows intelligent merging of sections
- Supports incremental updates throughout the day
- Maintains audit trail of all work

### 2.2 Merge Strategy by Section

Each section has different merge semantics:

| Section | Merge Strategy |
|---------|----------------|
| 🎯 Goals & Context | Deduplicate bullets; preserve unique goals from both old and new |
| 💻 Technical Work | Deduplicate commits by hash; append new commits; preserve PR reviews |
| 📊 Metrics | Recalculate from combined commit list; update totals |
| 🔍 Key Decisions | Deduplicate by content similarity; preserve all unique decisions |
| ⚠️ Impact Assessment | Merge and deduplicate impact statements |
| 🚧 Open Items | Merge; mark resolved items if new content shows completion |
| 📚 Learnings | Deduplicate by content similarity; preserve all unique learnings |
| 🗓️ Weekly Summary | Special handling: only create once; update if explicitly requested |

---

## 3. Implementation Plan

### 3.1 Phase 1: Add Read Capability to Markdown Tools

**File:** `glin/markdown_tools.py`

**New Function:** `read_date_entry`
```python
def read_date_entry(
    date_str: str,
    file_path: str | None = None,
) -> dict[str, Any]:
    """
    Read and parse an existing date entry from the markdown file.
    
    Returns:
        {
            "exists": bool,
            "date": str,  # YYYY-MM-DD
            "heading_line": int | None,
            "sections": {
                "goals": list[str],  # bullet content without "- " prefix
                "technical": list[str],
                "metrics": list[str],
                "decisions": list[str],
                "impact": list[str],
                "open_items": list[str],
                "learnings": list[str],
                "weekly_summary": str | None,  # full text if present
            },
            "raw_content": str,  # full section content for reference
        }
    """
```

**Implementation Details:**
- Use same path resolution as `append_to_markdown`
- Parse markdown structure to find `## YYYY-MM-DD` heading
- Extract content until next `##` heading
- Parse subsections by `###` headings with emoji markers
- Extract bullet points (lines starting with `- `)
- Handle edge cases: missing sections, malformed content, empty file

**New MCP Tool:** `read_date_entry`
- Wrapper around the function above
- Allows LLM to read existing entries before updating

### 3.2 Phase 2: Add Merge Logic

**File:** `glin/markdown_tools.py`

**New Function:** `merge_date_sections`
```python
def merge_date_sections(
    existing: dict[str, Any],
    new_content: str,
    *,
    preserve_lines: bool = False,
) -> str:
    """
    Merge new content with existing date entry sections.
    
    Args:
        existing: Result from read_date_entry
        new_content: New markdown content to merge (with ### sections)
        preserve_lines: Same semantics as append_to_markdown
    
    Returns:
        Merged markdown content ready to write (without date heading)
    """
```

**Merge Algorithm:**
1. Parse new_content into sections (same structure as read_date_entry)
2. For each section type:
   - Extract bullets from both existing and new
   - Apply section-specific merge strategy (see 2.2)
   - Deduplicate while preserving order
3. Reconstruct markdown with merged sections
4. Return formatted content

**Deduplication Strategies:**
- **Commits:** Extract hash from markdown links `[hash](url)` or plain text; dedupe by hash
- **Text bullets:** Normalize whitespace; compare; use fuzzy matching for high similarity (>85%)
- **Metrics:** Recalculate from merged commit list
- **Weekly Summary:** Preserve existing; only update if marker indicates same range

### 3.3 Phase 3: Add Update Mode to append_to_markdown

**File:** `glin/markdown_tools.py`

**Modify Function:** `append_to_markdown`

**New Parameter:** `update_mode: bool = False`

**Behavior Change:**
```python
def append_to_markdown(
    content: str,
    file_path: str | None = None,
    date_str: str | None = None,
    *,
    preserve_lines: bool = False,
    update_mode: bool = False,  # NEW
) -> MarkdownSuccessResponse | MarkdownErrorResponse:
    """
    ...existing docstring...
    
    Args:
        ...existing args...
        update_mode: When True, read existing entry for the date and merge 
                     new content with existing sections instead of appending.
                     When False (default), append as before (backward compatible).
    """
```

**Implementation:**
```python
if update_mode:
    # Read existing entry
    existing = read_date_entry(date_str or datetime.now().date().isoformat(), file_path)
    
    if existing["exists"]:
        # Merge new content with existing
        merged_content = merge_date_sections(existing, content, preserve_lines=preserve_lines)
        
        # Replace the entire date section
        # (delete lines from heading to next heading, then insert merged)
        # ... implementation ...
    else:
        # No existing entry, proceed with normal append
        # ... existing append logic ...
else:
    # Backward compatible: existing append behavior
    # ... existing code ...
```

**Return Type Enhancement:**
```python
class MarkdownSuccessResponse(TypedDict):
    # ... existing fields ...
    update_mode_used: bool  # NEW
    existing_bullets_preserved: int  # NEW
    new_bullets_added: int  # NEW
    deduplicated_count: int  # NEW
```

### 3.4 Phase 4: Update worklog_entry Prompt

**File:** `glin/prompts.py`

**Function:** `worklog_entry_prompt`

**Changes to User Prompt (lines 160-166):**

**Before:**
```python
"After generating the above markdown content, then immediately call the 'append_to_markdown' MCP tool with:\n"
"  • date_str = D (ISO format YYYY-MM-DD)\n"
"  • content = the date-specific markdown block with h3 sub-headings and bullets\n"
"  • preserve_lines = true (so lines are written as-is without auto-bullets)\n"
"  • file_path can be omitted (defaults to GLIN_MD_PATH or ./WORKLOG.md).\n"
f"  • Target worklog file path resolved now: {md_path}.\n"
"- Make exactly one tool call per date with just that date's content. Do not batch multiple dates in one call.\n\n"
```

**After:**
```python
"After generating the above markdown content, then immediately call the 'append_to_markdown' MCP tool with:\n"
"  • date_str = D (ISO format YYYY-MM-DD)\n"
"  • content = the date-specific markdown block with h3 sub-headings and bullets\n"
"  • preserve_lines = true (so lines are written as-is without auto-bullets)\n"
"  • update_mode = true (IMPORTANT: merge with existing entry if present; do not create duplicates)\n"
"  • file_path can be omitted (defaults to GLIN_MD_PATH or ./WORKLOG.md).\n"
f"  • Target worklog file path resolved now: {md_path}.\n"
"- Make exactly one tool call per date with just that date's content. Do not batch multiple dates in one call.\n"
"- The update_mode flag ensures that if an entry for date D already exists, the new content will be intelligently merged with the existing sections rather than appended, preventing duplicates.\n\n"
```

**Additional Guidance (new section before WEEKLY SUMMARY):**
```python
"MERGE BEHAVIOR (when update_mode=true):\n"
"- If the target date already has an entry, the tool will:\n"
"  1. Read and parse the existing sections\n"
"  2. Merge your new content with existing content at the section level\n"
"  3. Deduplicate commits (by hash), bullets (by content similarity), and metrics (recalculated)\n"
"  4. Preserve all unique information from both old and new entries\n"
"- This allows you to run the worklog generation multiple times for the same date without creating duplicates.\n"
"- Existing content is preserved; only new information is added.\n\n"
```

### 3.5 Phase 5: Testing

**File:** `tests/test_markdown_tools.py`

**New Test Cases:**

1. `test_read_date_entry_existing`
   - Create markdown with date entry and sections
   - Call `read_date_entry`
   - Assert correct parsing of all sections

2. `test_read_date_entry_missing`
   - Call `read_date_entry` for non-existent date
   - Assert `exists=False`

3. `test_merge_date_sections_commits`
   - Existing: 2 commits
   - New: 1 duplicate + 1 new commit
   - Assert: 3 unique commits in result

4. `test_merge_date_sections_bullets`
   - Existing: 3 goals
   - New: 1 duplicate + 2 new goals
   - Assert: 5 unique goals, no duplicates

5. `test_append_to_markdown_update_mode_merge`
   - Create file with existing date entry
   - Call `append_to_markdown` with `update_mode=True` and new content
   - Assert: merged content, no duplicates, correct counts in response

6. `test_append_to_markdown_update_mode_new_date`
   - Call `append_to_markdown` with `update_mode=True` for new date
   - Assert: behaves like normal append (no existing entry to merge)

7. `test_append_to_markdown_backward_compatible`
   - Call `append_to_markdown` with `update_mode=False` (default)
   - Assert: existing append behavior unchanged

8. `test_weekly_summary_idempotency`
   - Create weekly summary
   - Run again with same range
   - Assert: no duplicate weekly summary

**Test Coverage Target:** >90% for new functions

---

## 4. Rollout Plan

### 4.1 Implementation Order

1. **Step 1:** Implement `read_date_entry` function and MCP tool
   - Test thoroughly with various markdown structures
   - Handle edge cases (empty file, malformed content, missing sections)

2. **Step 2:** Implement `merge_date_sections` function
   - Start with simple deduplication (exact matches)
   - Add fuzzy matching for text bullets
   - Add commit hash extraction and deduplication

3. **Step 3:** Modify `append_to_markdown` to support `update_mode`
   - Ensure backward compatibility (default `update_mode=False`)
   - Test both modes extensively

4. **Step 4:** Update `worklog_entry` prompt
   - Add `update_mode=true` to instructions
   - Add merge behavior documentation

5. **Step 5:** Integration testing
   - Test full workflow: generate worklog → generate again → verify merge
   - Test with real git data and conversations

### 4.2 Backward Compatibility

- **Default behavior unchanged:** `update_mode=False` by default
- **Existing callers unaffected:** All existing code continues to work
- **Opt-in feature:** Only `worklog_entry` prompt uses new mode
- **Graceful degradation:** If merge fails, fall back to append with warning

### 4.3 Migration Path

**For existing worklogs:**
- No migration needed
- New behavior only affects future updates
- Users can manually clean up old duplicates if desired

**For new worklogs:**
- Benefit immediately from merge behavior
- No duplicate entries from repeated runs

---

## 5. Edge Cases and Error Handling

### 5.1 Edge Cases

| Case | Handling |
|------|----------|
| Empty existing entry | Treat as new entry; proceed with normal append |
| Malformed existing sections | Log warning; attempt best-effort parse; fall back to append |
| Very large existing entry (>10K lines) | Warn about performance; consider pagination or summary |
| Concurrent writes | File locking not implemented; last write wins (document limitation) |
| Weekly summary already exists | Check for marker comment; skip if present |
| Mixed date formats in file | Normalize to ISO format; warn about inconsistencies |

### 5.2 Error Handling

**Read Errors:**
- File not found → treat as new file
- Permission denied → return error response
- Encoding errors → try UTF-8, then fallback encodings, then error

**Parse Errors:**
- Invalid markdown structure → log warning, return partial parse
- Missing section markers → return empty lists for those sections
- Malformed bullets → include as-is in raw_content

**Merge Errors:**
- Deduplication failure → log warning, include both versions
- Section reconstruction failure → fall back to append mode with warning

**Write Errors:**
- Same as current `append_to_markdown` error handling
- Atomic write (write to temp file, then rename) to prevent corruption

---

## 6. Performance Considerations

### 6.1 Expected Performance

- **Read operation:** O(n) where n = file size; typically <100ms for files <1MB
- **Parse operation:** O(m) where m = number of lines in date section; typically <10ms
- **Merge operation:** O(k²) where k = number of bullets (for deduplication); typically <50ms for <100 bullets
- **Write operation:** Same as current append; typically <50ms

**Total overhead:** ~200ms for typical worklog update (acceptable)

### 6.2 Optimization Opportunities

- Cache parsed file structure if multiple dates updated in one session
- Use line-based indexing for faster section lookup
- Implement incremental parsing (only parse target date section)
- Add fuzzy matching threshold tuning parameter

---

## 7. Documentation Updates

### 7.1 User-Facing Documentation

**README.md additions:**
- Document `update_mode` parameter in `append_to_markdown` tool
- Explain merge behavior and deduplication strategies
- Provide examples of running worklog generation multiple times

**AGENTS.md additions:**
- Update worklog generation workflow to mention merge behavior
- Document idempotency guarantees
- Explain section-specific merge strategies

### 7.2 Code Documentation

**Docstrings:**
- Add detailed docstrings to all new functions
- Include examples in docstrings
- Document merge strategies and edge cases

**Inline Comments:**
- Comment complex merge logic
- Explain deduplication algorithms
- Note performance considerations

---

## 8. Testing Strategy

### 8.1 Unit Tests

- Test each new function in isolation
- Mock file I/O for deterministic tests
- Test edge cases and error conditions
- Achieve >90% code coverage

### 8.2 Integration Tests

- Test full workflow with real markdown files
- Test with various date ranges and content types
- Test backward compatibility with existing behavior
- Test concurrent scenarios (if applicable)

### 8.3 Manual Testing

- Generate worklog for today
- Generate again with new commits
- Verify merge behavior
- Check for duplicates
- Verify all sections updated correctly

---

## 9. Success Criteria

### 9.1 Functional Requirements

- ✅ Detect existing date entries in markdown file
- ✅ Parse existing sections correctly
- ✅ Merge new content with existing content
- ✅ Deduplicate commits by hash
- ✅ Deduplicate text bullets by content similarity
- ✅ Preserve all unique information
- ✅ Maintain backward compatibility
- ✅ Handle edge cases gracefully

### 9.2 Quality Requirements

- ✅ >90% test coverage for new code
- ✅ All existing tests pass
- ✅ No performance regression (merge overhead <500ms)
- ✅ Clear error messages for all failure modes
- ✅ Comprehensive documentation

### 9.3 User Experience Requirements

- ✅ Idempotent: running twice produces same result
- ✅ No manual deduplication needed
- ✅ Existing content preserved
- ✅ New information added correctly
- ✅ Clear feedback about merge operations

---

## 10. Future Enhancements

### 10.1 Potential Improvements

1. **Smart conflict resolution:**
   - Detect conflicting information (e.g., different metrics for same commits)
   - Prompt user or apply resolution strategy

2. **Merge history tracking:**
   - Add metadata comments showing when entries were merged
   - Track source of each bullet (original vs. merged)

3. **Section-level timestamps:**
   - Track when each section was last updated
   - Show staleness indicators

4. **Interactive merge mode:**
   - Allow user to review and approve merges
   - Provide diff view of changes

5. **Bulk operations:**
   - Merge multiple dates in one operation
   - Deduplicate entire worklog file

### 10.2 Related Features

- **Worklog search:** Find entries by keyword, date range, or commit hash
- **Worklog export:** Generate reports in different formats (PDF, HTML)
- **Worklog analytics:** Visualize productivity trends, commit patterns
- **Worklog templates:** Customizable section structure and merge strategies

---

## 11. Implementation Checklist

### Phase 1: Read Capability
- [x] Implement `read_date_entry` function
- [x] Add MCP tool wrapper for `read_date_entry`
- [x] Write unit tests for reading and parsing
- [x] Test with various markdown structures
- [x] Handle edge cases (empty file, malformed content)

### Phase 2: Merge Logic
- [x] Implement `merge_date_sections` function
- [x] Implement commit deduplication (hash extraction)
- [x] Implement text bullet deduplication (fuzzy matching)
- [x] Implement section-specific merge strategies
- [x] Write unit tests for merge logic
- [x] Test deduplication accuracy

### Phase 3: Update Mode
- [x] Add `update_mode` parameter to `append_to_markdown`
- [x] Implement update mode logic (read → merge → write)
- [x] Update return type with merge statistics
- [x] Ensure backward compatibility
- [x] Write unit tests for update mode
- [x] Test both modes (append and update)

### Phase 4: Prompt Updates
- [x] Update `worklog_entry` prompt with `update_mode=true`
- [x] Add merge behavior documentation to prompt
- [x] Add guidance for LLM on merge expectations
- [ ] Test prompt with real worklog generation

### Phase 5: Testing & Documentation
- [ ] Write integration tests for full workflow
- [ ] Test with real git data and conversations
- [ ] Update README.md with new feature documentation
- [ ] Update AGENTS.md with workflow changes
- [x] Add inline code comments
- [x] Run full test suite and verify coverage

### Phase 6: Validation
- [ ] Manual testing with real worklogs
- [ ] Performance testing (measure overhead)
- [ ] Edge case testing (large files, malformed content)
- [x] Backward compatibility verification
- [ ] User acceptance testing (if applicable)

### Phase 7: Deployment
- [ ] Code review
- [ ] Merge to main branch
- [ ] Update version number
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Gather user feedback

---

## 12. Risk Assessment

### 12.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Merge logic bugs causing data loss | Medium | High | Extensive testing; backup existing content before merge |
| Performance degradation on large files | Low | Medium | Performance testing; optimization if needed |
| Backward compatibility break | Low | High | Thorough testing; default to old behavior |
| Fuzzy matching false positives | Medium | Low | Tune threshold; allow manual override |

### 12.2 User Experience Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Unexpected merge behavior | Medium | Medium | Clear documentation; verbose logging |
| Loss of manual edits | Low | High | Preserve all content; only deduplicate obvious duplicates |
| Confusion about merge vs. append | Low | Low | Clear naming; good documentation |

### 12.3 Mitigation Strategies

1. **Backup strategy:** Always preserve original content in merge operations
2. **Verbose logging:** Log all merge decisions for debugging
3. **Dry-run mode:** Consider adding preview mode to show merge result before writing
4. **Rollback capability:** Keep old behavior as fallback option
5. **User feedback:** Collect feedback early and iterate

---

## 13. Timeline Estimate

### 13.1 Development Time

| Phase | Estimated Time | Dependencies |
|-------|----------------|--------------|
| Phase 1: Read Capability | 4-6 hours | None |
| Phase 2: Merge Logic | 6-8 hours | Phase 1 |
| Phase 3: Update Mode | 4-6 hours | Phase 1, 2 |
| Phase 4: Prompt Updates | 2-3 hours | Phase 3 |
| Phase 5: Testing & Docs | 6-8 hours | All phases |
| Phase 6: Validation | 3-4 hours | Phase 5 |
| Phase 7: Deployment | 2-3 hours | Phase 6 |

**Total Estimated Time:** 27-38 hours (3.5-5 days of focused work)

### 13.2 Milestones

- **Week 1:** Complete Phases 1-2 (read and merge logic)
- **Week 2:** Complete Phases 3-4 (update mode and prompt)
- **Week 3:** Complete Phases 5-7 (testing, validation, deployment)

---

## 14. Conclusion

This plan provides a comprehensive roadmap for implementing intelligent merge behavior in the worklog system. The solution:

- **Preserves existing content** while adding new information
- **Prevents duplicates** through smart deduplication
- **Maintains backward compatibility** with existing behavior
- **Handles edge cases** gracefully with clear error messages
- **Provides idempotency** for repeated worklog generation

The implementation is structured in phases to allow incremental development and testing, with clear success criteria and risk mitigation strategies.

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1 implementation (read capability)
3. Iterate based on testing and feedback
4. Deploy and monitor

---

**Plan Status:** Ready for implementation  
**Last Updated:** 2025-10-23  
**Author:** Junie (AI Assistant)
