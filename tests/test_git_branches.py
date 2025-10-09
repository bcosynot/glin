from glin.git_tools import (
    get_current_branch,
    list_branches,
    get_branch_commits,
)


class Completed:
    def __init__(self, stdout: str = "", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def make_run(outputs: list[tuple[list[str], Completed | Exception]]):
    """Return a fake subprocess.run that matches by command prefix."""

    def run(cmd: list[str], capture_output: bool = True, text: bool = True, check: bool = True):  # noqa: ARG001
        for prefix, result in outputs:
            if cmd[: len(prefix)] == prefix:
                if isinstance(result, Exception):
                    raise result
                return result
        raise AssertionError(f"Unexpected command: {cmd}")

    return run


def test_get_current_branch_basic(monkeypatch):
    import subprocess

    # Branch name and upstream
    name = Completed(stdout="main\n")
    upstream = Completed(stdout="origin/main\n")
    counts = Completed(stdout="2\t1\n".replace("\t", " "))

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "rev-parse", "--abbrev-ref", "HEAD"], name),
                (["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], upstream),
                (["git", "rev-list", "--left-right", "--count"], counts),
            ]
        ),
    )

    res = get_current_branch()
    assert res["name"] == "main"
    assert res["detached"] is False
    assert res["upstream"] == "origin/main"
    assert res["ahead"] == 2
    assert res["behind"] == 1


def test_list_branches_two(monkeypatch):
    import subprocess

    fmt_lines = "\n".join(
        [
            "main|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|origin/main|Alice|<alice@example.com>|2024-01-01 12:00:00 +0000|first",
            "feature|bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb|origin/feature|Bob|<bob@example.com>|2024-01-02 13:00:00 +0000|feat: work",
        ]
    )

    fer = Completed(stdout=fmt_lines + "\n")
    current = Completed(stdout="feature\n")
    c1 = Completed(stdout="1 0\n")
    c2 = Completed(stdout="0 3\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "for-each-ref"], fer),
                (["git", "rev-parse", "--abbrev-ref", "HEAD"], current),
                (["git", "rev-list", "--left-right", "--count", "main...origin/main"], c1),
                (["git", "rev-list", "--left-right", "--count", "feature...origin/feature"], c2),
            ]
        ),
    )

    branches = list_branches()
    assert isinstance(branches, list)
    assert len(branches) == 2

    main = next(b for b in branches if b["name"] == "main")
    feat = next(b for b in branches if b["name"] == "feature")

    assert main["is_current"] is False
    assert feat["is_current"] is True

    assert main["upstream"] == "origin/main"
    assert feat["ahead"] == 0 and feat["behind"] == 3

    assert main["last_commit"]["author"] == "Alice"
    assert feat["last_commit"]["email"] == "bob@example.com"


def test_get_branch_commits_filtered(monkeypatch):
    import subprocess
    from unittest.mock import patch

    log_ok = Completed(stdout=(
        "deadbeef|Alice|2024-01-01 12:00:00 +0000|on feature\n"
        "cafebabe|Alice|2024-01-02 12:00:00 +0000|second\n"
    ))

    with patch("glin.git_tools.get_tracked_emails", return_value=["alice@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "log"], log_ok),
                ]
            ),
        )
        commits = get_branch_commits("feature", count=2)
        assert len(commits) == 2
        assert commits[0]["hash"] == "deadbeef"
