from seev.git_tools.analysis import categorize_commit


def test_categorize_accepts_extended_types_case_insensitive():
    samples = [
        ("Added: new endpoint", "added"),
        ("Updated(scope): bump deps", "updated"),
        ("Fixed: crash on launch", "fixed"),
        ("Refactored(core): cleanup", "refactored"),
        ("Chore: tidy", "chore"),
        ("Task(ui): implement modal", "task"),
        ("WIP: experimenting", "wip"),
        ("Debugging: logs added", "debugging"),
        ("Bugfix: null ref", "bugfix"),
        ("Investigating: sporadic CI", "investigating"),
        ("Investigation: flaky tests", "investigation"),
        ("feat: keep supporting standard", "feat"),
        ("fix(core): bug also standard", "fix"),
    ]

    for msg, expected_type in samples:
        res = categorize_commit(msg)
        assert res["conventional"] is True, msg
        assert res["type"] == expected_type, msg
