from seev.git_tools import (
    get_branch_commits,
    get_current_branch,
    list_branches,
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
                (
                    ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
                    upstream,
                ),
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

    log_ok = Completed(
        stdout=(
            "deadbeef|Alice|2024-01-01 12:00:00 +0000|on feature\n"
            "cafebabe|Alice|2024-01-02 12:00:00 +0000|second\n"
        )
    )

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
                (
                    ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
                    upstream,
                ),
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


def test_get_current_branch_with_workdir(monkeypatch):
    import subprocess

    # Force repo root resolution to a fixed path
    monkeypatch.setattr("glin.git_tools.branches.resolve_repo_root", lambda p: {"path": "/repo"})

    name = Completed(stdout="main\n")
    upstream = Completed(stdout="origin/main\n")
    counts = Completed(stdout="2 1\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "-C", "/repo", "rev-parse", "--abbrev-ref", "HEAD"], name),
                (
                    [
                        "git",
                        "-C",
                        "/repo",
                        "rev-parse",
                        "--abbrev-ref",
                        "--symbolic-full-name",
                        "@{upstream}",
                    ],
                    upstream,
                ),
                (
                    [
                        "git",
                        "-C",
                        "/repo",
                        "rev-list",
                        "--left-right",
                        "--count",
                        "main...origin/main",
                    ],
                    counts,
                ),
            ]
        ),
    )

    from seev.git_tools.branches import get_current_branch as _get

    res = _get(workdir="/work/here")
    assert res["name"] == "main"
    assert res["upstream"] == "origin/main"


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


def test_list_branches_with_workdir(monkeypatch):
    import subprocess

    monkeypatch.setattr("glin.git_tools.branches.resolve_repo_root", lambda p: {"path": "/repo"})

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
                (["git", "-C", "/repo", "for-each-ref"], fer),
                (["git", "-C", "/repo", "rev-parse", "--abbrev-ref", "HEAD"], current),
                (
                    [
                        "git",
                        "-C",
                        "/repo",
                        "rev-list",
                        "--left-right",
                        "--count",
                        "main...origin/main",
                    ],
                    c1,
                ),
                (
                    [
                        "git",
                        "-C",
                        "/repo",
                        "rev-list",
                        "--left-right",
                        "--count",
                        "feature...origin/feature",
                    ],
                    c2,
                ),
            ]
        ),
    )

    from seev.git_tools.branches import list_branches as _list

    branches = _list(workdir="/work/here")
    assert any(b.get("is_current") for b in branches)


def test_get_branch_commits_filtered(monkeypatch):
    import subprocess
    from unittest.mock import patch

    log_ok = Completed(
        stdout=(
            "deadbeef|Alice|2024-01-01 12:00:00 +0000|on feature\n"
            "cafebabe|Alice|2024-01-02 12:00:00 +0000|second\n"
        )
    )

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


def test_get_branch_commits_with_workdir(monkeypatch):
    import subprocess
    from unittest.mock import patch

    monkeypatch.setattr("glin.git_tools.commits.resolve_repo_root", lambda p: {"path": "/repo"})

    log_ok = Completed(
        stdout=(
            "deadbeef|Alice|2024-01-01 12:00:00 +0000|on feature\n"
            "cafebabe|Alice|2024-01-02 12:00:00 +0000|second\n"
        )
    )

    with patch("glin.git_tools.get_tracked_emails", return_value=["alice@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "-C", "/repo", "log"], log_ok),
                ]
            ),
        )
        from seev.git_tools.commits import get_branch_commits as _gbc

        commits = _gbc("feature", count=2, workdir="/work/here")
        assert len(commits) == 2
        assert commits[0]["hash"] == "deadbeef"
