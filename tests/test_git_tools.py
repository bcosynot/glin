import types
from typing import Any
from unittest.mock import Mock

import pytest

from glin.git_tools import _get_git_author_pattern, get_recent_commits, get_commits_by_date


class FakeCPError(Exception):
    pass


class Completed:
    def __init__(self, stdout: str = "", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def make_run(outputs: list[tuple[list[str], Completed | Exception]]):
    """Return a fake subprocess.run that matches by command prefix.

    outputs: list of (prefix, result) where prefix is the list[str] we expect at start of command
    and result is either Completed (with stdout/stderr) or CalledProcessError-like Exception.
    """
    def run(cmd: list[str], capture_output: bool = True, text: bool = True, check: bool = True):  # noqa: ARG001
        for prefix, result in outputs:
            if cmd[: len(prefix)] == prefix:
                if isinstance(result, Exception):
                    # emulate subprocess.CalledProcessError behavior expected by code paths
                    raise result
                return result
        raise AssertionError(f"Unexpected command: {cmd}")

    return run


def test_get_git_author_prefers_email(monkeypatch):
    import subprocess

    # Mock: email present
    email_ok = Completed(stdout="user@example.com\n")
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], email_ok),
        ]),
    )

    assert _get_git_author_pattern() == "user@example.com"


def test_get_git_author_falls_back_to_name(monkeypatch):
    import subprocess

    # email lookup fails, name returns
    cp_err = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.email"], output="", stderr="")
    name_ok = Completed(stdout="Jane Doe\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], cp_err),
            (["git", "config", "--get", "user.name"], name_ok),
        ]),
    )

    assert _get_git_author_pattern() == "Jane Doe"


def test_get_git_author_none_when_unset(monkeypatch):
    import subprocess

    cp_err_email = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.email"], output="", stderr="")
    cp_err_name = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.name"], output="", stderr="")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], cp_err_email),
            (["git", "config", "--get", "user.name"], cp_err_name),
        ]),
    )

    assert _get_git_author_pattern() is None


def test_get_recent_commits_parses_output(monkeypatch):
    import subprocess

    email_ok = Completed(stdout="me@example.com\n")
    log_ok = Completed(
        stdout=(
            "deadbeef|Alice|2024-01-01 12:00:00 +0000|msg1\n"
            "cafebabe|Bob|2024-01-02 13:00:00 +0000|feat: add stuff\n"
        )
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], email_ok),
            (["git", "log"], log_ok),
        ]),
    )

    commits = get_recent_commits(2)
    assert len(commits) == 2
    assert commits[0]["hash"] == "deadbeef"
    assert commits[1]["message"] == "feat: add stuff"


def test_get_recent_commits_no_author_config(monkeypatch):
    import subprocess

    cp_err_email = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.email"], output="", stderr="")
    cp_err_name = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.name"], output="", stderr="")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], cp_err_email),
            (["git", "config", "--get", "user.name"], cp_err_name),
        ]),
    )

    res = get_recent_commits(1)
    assert res and "error" in res[0]


def test_get_commits_by_date_parses_and_empty_info(monkeypatch):
    import subprocess

    email_ok = Completed(stdout="me@example.com\n")
    # First run: no commits; Second run: two commits
    log_empty = Completed(stdout="\n")
    log_two = Completed(stdout=("a1|A|2024-01-01 00:00:00 +0000|one\n" "b2|B|2024-01-02 00:00:00 +0000|two\n"))

    # Empty result case
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], email_ok),
            (["git", "log"], log_empty),
        ]),
    )
    res_empty = get_commits_by_date("yesterday", "now")
    assert res_empty and res_empty[0].get("info") == "No commits found in date range"

    # Success case with two commits
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], email_ok),
            (["git", "log"], log_two),
        ]),
    )
    res = get_commits_by_date("1 week ago", "now")
    assert len(res) == 2
    assert res[0]["hash"] == "a1"
    assert res[1]["message"] == "two"


def test_get_commits_handles_subprocess_error(monkeypatch):
    import subprocess

    email_ok = Completed(stdout="me@example.com\n")
    cp_err = subprocess.CalledProcessError(128, ["git", "log"], output="", stderr="fatal: bad stuff")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], email_ok),
            (["git", "log"], cp_err),
        ]),
    )

    res = get_recent_commits(3)
    assert res and "error" in res[0]


def test_get_recent_commits_handles_general_exception(monkeypatch):
    import subprocess

    email_ok = Completed(stdout="me@example.com\n")
    
    def failing_run(*args, **kwargs):
        if args[0][:3] == ["git", "config", "--get"]:
            return email_ok
        raise RuntimeError("Something went wrong")

    monkeypatch.setattr(subprocess, "run", failing_run)

    res = get_recent_commits(3)
    assert res and "error" in res[0]
    assert "Failed to get commits" in res[0]["error"]


def test_get_commits_by_date_handles_subprocess_error(monkeypatch):
    import subprocess

    email_ok = Completed(stdout="me@example.com\n")
    cp_err = subprocess.CalledProcessError(128, ["git", "log"], output="", stderr="fatal: bad stuff")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], email_ok),
            (["git", "log"], cp_err),
        ]),
    )

    res = get_commits_by_date("yesterday", "now")
    assert res and "error" in res[0]


def test_get_commits_by_date_handles_general_exception(monkeypatch):
    import subprocess

    email_ok = Completed(stdout="me@example.com\n")
    
    def failing_run(*args, **kwargs):
        if args[0][:3] == ["git", "config", "--get"]:
            return email_ok
        raise RuntimeError("Something went wrong")

    monkeypatch.setattr(subprocess, "run", failing_run)

    res = get_commits_by_date("yesterday", "now")
    assert res and "error" in res[0]
    assert "Failed to get commits" in res[0]["error"]


def test_get_commits_by_date_no_author_config(monkeypatch):
    import subprocess

    cp_err_email = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.email"], output="", stderr="")
    cp_err_name = subprocess.CalledProcessError(1, ["git", "config", "--get", "user.name"], output="", stderr="")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run([
            (["git", "config", "--get", "user.email"], cp_err_email),
            (["git", "config", "--get", "user.name"], cp_err_name),
        ]),
    )

    res = get_commits_by_date("yesterday", "now")
    assert res and "error" in res[0]
    assert "Git author not configured" in res[0]["error"]
