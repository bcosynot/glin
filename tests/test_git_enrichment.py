from typing import Any

from seev.git_tools.enrichment import (
    EnrichedCommit,
    get_enriched_commits,
)


def test_get_enriched_commits_forwards_info(monkeypatch):
    # When underlying commit query returns an info dict, forward it unchanged
    calls: dict[str, Any] = {}

    def fake_get_commits_by_date(since: str, until: str = "now", workdir: str | None = None):  # noqa: ARG001
        calls["workdir"] = workdir
        return [{"info": "No commits found in date range"}]

    monkeypatch.setattr("seev.git_tools.enrichment.get_commits_by_date", fake_get_commits_by_date)

    res = get_enriched_commits("2025-01-01")
    assert isinstance(res, list)
    assert res and res[0].get("info") == "No commits found in date range"
    # Ensure workdir was threaded
    assert calls["workdir"] is None


def test_get_enriched_commits_forwards_error(monkeypatch):
    def fake_get_commits_by_date(since: str, until: str = "now", workdir: str | None = None):  # noqa: ARG001
        return [{"error": "repo root not found"}]

    monkeypatch.setattr("seev.git_tools.enrichment.get_commits_by_date", fake_get_commits_by_date)

    res = get_enriched_commits("2025-01-01", workdir="/bad/path")
    assert isinstance(res, list)
    assert res and res[0].get("error") == "repo root not found"


def test_get_enriched_commits_success_with_workdir(monkeypatch):
    # Arrange: two commits returned by date query
    commits = [
        {"hash": "a1", "author": "A", "date": "2025-01-01 00:00:00 +0000", "message": "feat: one"},
        {"hash": "b2", "author": "B", "date": "2025-01-02 00:00:00 +0000", "message": "fix: two"},
    ]
    tracked_workdirs: list[str | None] = []

    def fake_get_commits_by_date(since: str, until: str = "now", workdir: str | None = None):  # noqa: ARG001
        tracked_workdirs.append(workdir)
        return commits

    def fake_stats(sha: str, workdir: str | None = None):  # noqa: ARG001
        # Return different stats per sha to validate aggregation
        return {
            "additions": 3 if sha == "a1" else 7,
            "deletions": 1 if sha == "a1" else 2,
            "files_changed": 2 if sha == "a1" else 5,
        }

    def fake_category(message_or_hash: str, is_hash: bool = True, workdir: str | None = None):  # noqa: ARG001
        # Minimal shape sufficient for UI/tests elsewhere
        return {"type": "feat" if message_or_hash == "a1" else "fix"}

    def fake_merge_info(commit_hash: str, workdir: str | None = None):  # noqa: ARG001
        return {"is_merge": False, "parents": [commit_hash]}

    monkeypatch.setattr("seev.git_tools.enrichment.get_commits_by_date", fake_get_commits_by_date)
    monkeypatch.setattr("seev.git_tools.enrichment.get_commit_statistics", fake_stats)
    monkeypatch.setattr("seev.git_tools.enrichment.categorize_commit", fake_category)
    monkeypatch.setattr("seev.git_tools.enrichment.detect_merge_info", fake_merge_info)

    res = get_enriched_commits("yesterday", "now", workdir="/work/repo")
    # Expect a structured EnrichedResult object
    assert isinstance(res, dict)
    assert set(res.keys()) == {"commits", "totals", "generated_at"}

    enriched = res["commits"]
    assert len(enriched) == 2

    # Validate enrichment content merged into base commit dict
    first: EnrichedCommit = enriched[0]
    assert first["hash"] == "a1"
    assert first["statistics"]["additions"] == 3
    assert first["category"]["type"] == "feat"
    assert first["merge_info"]["is_merge"] is False

    second: EnrichedCommit = enriched[1]
    assert second["hash"] == "b2"
    assert second["statistics"]["files_changed"] == 5

    # Totals aggregated across both commits
    totals = res["totals"]
    assert totals == {"additions": 10, "deletions": 3, "files_changed": 7}

    # Ensure the workdir was threaded into the underlying commit query
    assert tracked_workdirs == ["/work/repo"]
