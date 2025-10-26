from seev.git_tools.commits import (
    _build_git_log_command,
    _get_author_filters,
    _handle_git_error,
    _parse_commit_lines,
    get_commits_by_date,
    get_recent_commits,
)
from seev.git_tools.config_tools import (
    _check_git_config,
    _get_config_source,
    configure_tracked_emails,
    get_tracked_email_config,
)
from seev.git_tools.diffs import get_commit_diff
from seev.git_tools.files import get_commit_files


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


def test_get_author_filters_from_config(monkeypatch):
    """Test that _get_author_filters uses the configuration system."""
    from unittest.mock import patch

    with patch(
        "seev.git_tools.get_tracked_emails", return_value=["user1@example.com", "user2@example.com"]
    ):
        filters = _get_author_filters()
        assert filters == ["user1@example.com", "user2@example.com"]


def test_get_author_filters_empty_when_no_config(monkeypatch):
    """Test that _get_author_filters returns empty list when no config."""
    from unittest.mock import patch

    with patch("seev.git_tools.get_tracked_emails", return_value=[]):
        filters = _get_author_filters()
        assert filters == []


def test_get_recent_commits_parses_output(monkeypatch):
    import subprocess
    from unittest.mock import patch

    log_ok = Completed(
        stdout=(
            "deadbeef|Alice|2024-01-01 12:00:00 +0000|msg1\n"
            "cafebabe|Bob|2024-01-02 13:00:00 +0000|feat: add stuff\n"
        )
    )

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "log"], log_ok),
                ]
            ),
        )

        commits = get_recent_commits(2)
        assert len(commits) == 2
        assert commits[0]["hash"] == "deadbeef"
        assert commits[1]["message"] == "feat: add stuff"


def test_get_recent_commits_no_author_config(monkeypatch):
    from unittest.mock import patch

    with patch("seev.git_tools.get_tracked_emails", return_value=[]):
        res = get_recent_commits(1)
        assert res and "error" in res[0]
        assert "No email addresses configured" in res[0]["error"]


def test_get_commits_by_date_parses_and_empty_info(monkeypatch):
    import subprocess
    from unittest.mock import patch

    # First run: no commits; Second run: two commits
    log_empty = Completed(stdout="\n")
    log_two = Completed(
        stdout=("a1|A|2024-01-01 00:00:00 +0000|one\nb2|B|2024-01-02 00:00:00 +0000|two\n")
    )

    # Empty result case
    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "log"], log_empty),
                ]
            ),
        )
        res_empty = get_commits_by_date("yesterday", "now")
        assert res_empty and res_empty[0].get("info") == "No commits found in date range"

        # Success case with two commits
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "log"], log_two),
                ]
            ),
        )
        res = get_commits_by_date("1 week ago", "now")
        assert len(res) == 2
        assert res[0]["hash"] == "a1"
        assert res[1]["message"] == "two"


def test_get_commits_handles_subprocess_error(monkeypatch):
    import subprocess
    from unittest.mock import patch

    cp_err = subprocess.CalledProcessError(
        128, ["git", "log"], output="", stderr="fatal: bad stuff"
    )

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "log"], cp_err),
                ]
            ),
        )

        res = get_recent_commits(3)
        assert res and "error" in res[0]


def test_get_recent_commits_handles_general_exception(monkeypatch):
    import subprocess
    from unittest.mock import patch

    def failing_run(*args, **kwargs):
        raise RuntimeError("Something went wrong")

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(subprocess, "run", failing_run)

        res = get_recent_commits(3)
        assert res and "error" in res[0]
        assert "Failed to get commits" in res[0]["error"]


def test_get_commits_by_date_handles_subprocess_error(monkeypatch):
    import subprocess
    from unittest.mock import patch

    cp_err = subprocess.CalledProcessError(
        128, ["git", "log"], output="", stderr="fatal: bad stuff"
    )

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (["git", "log"], cp_err),
                ]
            ),
        )

        res = get_commits_by_date("yesterday", "now")
        assert res and "error" in res[0]


def test_get_commits_by_date_handles_general_exception(monkeypatch):
    import subprocess
    from unittest.mock import patch

    def failing_run(*args, **kwargs):
        raise RuntimeError("Something went wrong")

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(subprocess, "run", failing_run)

        res = get_commits_by_date("yesterday", "now")
        assert res and "error" in res[0]
        assert "Failed to get commits" in res[0]["error"]


def test_get_commits_by_date_no_author_config(monkeypatch):
    from unittest.mock import patch

    with patch("seev.git_tools.get_tracked_emails", return_value=[]):
        res = get_commits_by_date("yesterday", "now")
        assert res and "error" in res[0]
        assert "No email addresses configured" in res[0]["error"]


def test_get_tracked_email_config():
    """Test getting current email configuration."""
    from unittest.mock import patch

    with patch(
        "seev.git_tools.get_tracked_emails", return_value=["user1@example.com", "user2@example.com"]
    ):
        with patch("seev.git_tools._get_config_source", return_value="environment_variable"):
            config = get_tracked_email_config()
            assert config["tracked_emails"] == ["user1@example.com", "user2@example.com"]
            assert config["count"] == 2
            assert config["source"] == "environment_variable"


def test_configure_tracked_emails_env():
    """Test configuring emails via environment variable."""
    emails = ["test1@example.com", "test2@example.com"]
    result = configure_tracked_emails(emails, method="env")

    assert result["success"] is True
    assert result["emails"] == emails
    assert result["method"] == "environment_variable"
    assert "GLIN_TRACK_EMAILS" in result["message"]


def test_configure_tracked_emails_file():
    """Test configuring emails via config file."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    emails = ["test1@example.com", "test2@example.com"]

    with tempfile.TemporaryDirectory() as tmpdir:
        expected_path = Path(tmpdir) / "glin.toml"
        with patch("seev.git_tools.create_config_file", return_value=expected_path) as mock_create:
            result = configure_tracked_emails(emails, method="file")

            assert result["success"] is True
            assert result["emails"] == emails
            assert result["method"] == "config_file"
            mock_create.assert_called_once_with(emails)


def test_configure_tracked_emails_invalid_method():
    """Test configuring emails with invalid method."""
    emails = ["test@example.com"]
    result = configure_tracked_emails(emails, method="invalid")

    assert result["success"] is False
    assert "Unknown configuration method" in result["error"]


def test_configure_tracked_emails_exception_handling(monkeypatch):
    """Test configuring emails handles exceptions."""
    from unittest.mock import patch

    emails = ["test@example.com"]

    # Mock set_tracked_emails_env to raise an exception
    with patch("seev.git_tools.set_tracked_emails_env", side_effect=RuntimeError("Test error")):
        result = configure_tracked_emails(emails, method="env")

        assert result["success"] is False
        assert "Failed to configure emails" in result["error"]
        assert "Test error" in result["error"]


def test_get_commit_diff_success(monkeypatch):
    """Test successful commit diff retrieval."""
    import subprocess

    metadata_output = Completed(
        stdout=(
            "abc123|Alice Author|alice@example.com|2024-01-01 12:00:00 +0000|feat: add new feature"
        )
    )

    diff_output = Completed(
        stdout="""diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
+    print("world")
     pass
"""
    )

    stats_output = Completed(stdout=" file.py | 1 +\n 1 file changed, 1 insertion(+)")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "-U3"], diff_output),
                (["git", "show", "--stat"], stats_output),
            ]
        ),
    )

    result = get_commit_diff("abc123")

    assert result["hash"] == "abc123"
    assert result["author"] == "Alice Author"
    assert result["email"] == "alice@example.com"
    assert result["date"] == "2024-01-01 12:00:00 +0000"
    assert result["message"] == "feat: add new feature"
    assert "diff --git" in result["diff"]
    assert "file.py" in result["stats"]


def test_get_commit_diff_custom_context(monkeypatch):
    """Test commit diff with custom context lines."""
    import subprocess

    metadata_output = Completed(
        stdout="def456|Bob Builder|bob@example.com|2024-01-02 14:00:00 +0000|fix: bug fix"
    )

    diff_output = Completed(stdout="diff content")
    stats_output = Completed(stdout="stats content")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "-U5"], diff_output),
                (["git", "show", "--stat"], stats_output),
            ]
        ),
    )

    result = get_commit_diff("def456", context_lines=5)

    assert result["hash"] == "def456"
    assert result["message"] == "fix: bug fix"


def test_get_commit_diff_with_workdir(monkeypatch):
    """Diff should execute with '-C <root>' when workdir provided."""
    import subprocess

    monkeypatch.setattr("seev.git_tools.diffs.resolve_repo_root", lambda p: {"path": "/repo"})

    metadata_output = Completed(
        stdout=(
            "abc123|Alice Author|alice@example.com|2024-01-01 12:00:00 +0000|feat: add new feature"
        )
    )
    diff_output = Completed(stdout="diff content")
    stats_output = Completed(stdout="stats content")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "-C", "/repo", "show", "--no-patch"], metadata_output),
                (["git", "-C", "/repo", "show", "-U3"], diff_output),
                (["git", "-C", "/repo", "show", "--stat"], stats_output),
            ]
        ),
    )

    from seev.git_tools.diffs import get_commit_diff as _gcd

    result = _gcd("abc123", workdir="/work/here")
    assert result["hash"] == "abc123"
    """Test commit diff with custom context lines."""
    import subprocess

    metadata_output = Completed(
        stdout="def456|Bob Builder|bob@example.com|2024-01-02 14:00:00 +0000|fix: bug fix"
    )

    diff_output = Completed(stdout="diff content")
    stats_output = Completed(stdout="stats content")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "-U5"], diff_output),
                (["git", "show", "--stat"], stats_output),
            ]
        ),
    )

    result = get_commit_diff("def456", context_lines=5)

    assert result["hash"] == "def456"
    assert result["message"] == "fix: bug fix"


def test_get_commit_diff_not_found(monkeypatch):
    """Test commit diff when commit doesn't exist."""
    import subprocess

    metadata_output = Completed(stdout="")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
            ]
        ),
    )

    result = get_commit_diff("nonexistent")

    assert "error" in result
    assert "not found" in result["error"]


def test_get_commit_diff_subprocess_error(monkeypatch):
    """Test commit diff handles subprocess errors."""
    import subprocess

    cp_err = subprocess.CalledProcessError(
        128, ["git", "show"], output="", stderr="fatal: bad object nonexistent"
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show"], cp_err),
            ]
        ),
    )

    result = get_commit_diff("badcommit")

    assert "error" in result
    assert "Git command failed" in result["error"]


def test_get_commit_diff_parse_error(monkeypatch):
    """Test commit diff handles metadata parsing errors."""
    import subprocess

    # Malformed metadata (missing fields)
    metadata_output = Completed(stdout="abc123|Alice")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
            ]
        ),
    )

    result = get_commit_diff("abc123")

    assert "error" in result
    assert "Failed to parse commit metadata" in result["error"]


def test_get_commit_diff_general_exception(monkeypatch):
    """Test commit diff handles general exceptions."""
    import subprocess

    def failing_run(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(subprocess, "run", failing_run)

    result = get_commit_diff("abc123")

    assert "error" in result
    assert "Failed to get commit diff" in result["error"]


def test_get_commit_files_success(monkeypatch):
    """Test successful commit files retrieval."""
    import subprocess

    metadata_output = Completed(
        stdout=(
            "abc123|Alice Author|alice@example.com|2024-01-01 12:00:00 +0000|feat: add new feature"
        )
    )

    status_output = Completed(
        stdout="""M\tsrc/main.py
A\tsrc/utils.py
D\told_file.py
"""
    )

    numstat_output = Completed(
        stdout="""10\t5\tsrc/main.py
20\t0\tsrc/utils.py
0\t15\told_file.py
"""
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "--name-status"], status_output),
                (["git", "show", "--numstat"], numstat_output),
            ]
        ),
    )

    result = get_commit_files("abc123")

    assert result["hash"] == "abc123"
    assert result["author"] == "Alice Author"
    assert result["email"] == "alice@example.com"
    assert result["date"] == "2024-01-01 12:00:00 +0000"
    assert result["message"] == "feat: add new feature"
    assert result["files_changed"] == 3
    assert result["total_additions"] == 30
    assert result["total_deletions"] == 20

    # Check individual files
    files = result["files"]
    assert len(files) == 3

    # Modified file
    main_py = next(f for f in files if f["path"] == "src/main.py")
    assert main_py["status"] == "M"
    assert main_py["additions"] == 10
    assert main_py["deletions"] == 5
    assert main_py["old_path"] is None

    # Added file
    utils_py = next(f for f in files if f["path"] == "src/utils.py")
    assert utils_py["status"] == "A"
    assert utils_py["additions"] == 20
    assert utils_py["deletions"] == 0

    # Deleted file
    old_file = next(f for f in files if f["path"] == "old_file.py")
    assert old_file["status"] == "D"
    assert old_file["additions"] == 0
    assert old_file["deletions"] == 15


def test_get_commit_files_with_rename(monkeypatch):
    """Test commit files with renamed file."""
    import subprocess

    metadata_output = Completed(
        stdout="def456|Bob Builder|bob@example.com|2024-01-02 14:00:00 +0000|refactor: rename file"
    )

    status_output = Completed(stdout="R100\told_name.py\tnew_name.py\n")

    numstat_output = Completed(stdout="5\t3\tnew_name.py\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "--name-status"], status_output),
                (["git", "show", "--numstat"], numstat_output),
            ]
        ),
    )

    result = get_commit_files("def456")

    assert result["hash"] == "def456"
    assert result["files_changed"] == 1
    assert result["total_additions"] == 5
    assert result["total_deletions"] == 3

    renamed_file = result["files"][0]
    assert renamed_file["path"] == "new_name.py"
    assert renamed_file["status"] == "R"
    assert renamed_file["old_path"] == "old_name.py"
    assert renamed_file["additions"] == 5
    assert renamed_file["deletions"] == 3


def test_get_commit_files_with_binary(monkeypatch):
    """Test handling of binary files in commit files output."""
    import subprocess

    metadata_output = Completed(
        stdout="abc123|Alice|alice@example.com|2024-01-01 12:00:00 +0000|msg"
    )
    status_output = Completed(stdout="M\tbinfile\n")
    numstat_output = Completed(stdout="-\t-\tbinfile\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "--name-status"], status_output),
                (["git", "show", "--numstat"], numstat_output),
            ]
        ),
    )

    result = get_commit_files("abc123")

    assert result["files"][0]["additions"] == 0
    assert result["files"][0]["deletions"] == 0


def test_get_commit_files_with_workdir(monkeypatch):
    """When workdir provided, ensure '-C <root>' is used for file queries."""
    import subprocess

    # Resolve workdir -> repo root
    monkeypatch.setattr("seev.git_tools.files.resolve_repo_root", lambda p: {"path": "/repo"})

    metadata_output = Completed(
        stdout="abc123|Alice|alice@example.com|2024-01-01 12:00:00 +0000|msg"
    )
    status_output = Completed(stdout="M\tfile.py\n")
    numstat_output = Completed(stdout="1\t0\tfile.py\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "-C", "/repo", "show", "--no-patch"], metadata_output),
                (["git", "-C", "/repo", "show", "--name-status"], status_output),
                (["git", "-C", "/repo", "show", "--numstat"], numstat_output),
            ]
        ),
    )

    from seev.git_tools.files import get_commit_files as _gcf

    result = _gcf("abc123", workdir="/work/here")
    assert result["hash"] == "abc123"
    """Test commit files with binary file (shown as '-' in numstat)."""
    import subprocess

    metadata_output = Completed(
        stdout="ghi789|Charlie|charlie@example.com|2024-01-03 15:00:00 +0000|chore: add image"
    )

    status_output = Completed(stdout="A\timage.png\n")

    numstat_output = Completed(stdout="-\t-\timage.png\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "--name-status"], status_output),
                (["git", "show", "--numstat"], numstat_output),
            ]
        ),
    )

    result = get_commit_files("ghi789")

    assert result["hash"] == "ghi789"
    assert result["files_changed"] == 1
    assert result["total_additions"] == 0
    assert result["total_deletions"] == 0

    binary_file = result["files"][0]
    assert binary_file["path"] == "image.png"
    assert binary_file["status"] == "A"
    assert binary_file["additions"] == 0
    assert binary_file["deletions"] == 0


def test_get_commit_files_not_found(monkeypatch):
    """Test commit files when commit doesn't exist."""
    import subprocess

    metadata_output = Completed(stdout="")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
            ]
        ),
    )

    result = get_commit_files("nonexistent")

    assert "error" in result
    assert "not found" in result["error"]


def test_get_commit_files_subprocess_error(monkeypatch):
    """Test commit files handles subprocess errors."""
    import subprocess

    cp_err = subprocess.CalledProcessError(
        128, ["git", "show"], output="", stderr="fatal: bad object nonexistent"
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show"], cp_err),
            ]
        ),
    )

    result = get_commit_files("badcommit")

    assert "error" in result
    assert "Git command failed" in result["error"]


def test_get_commit_files_parse_error(monkeypatch):
    """Test commit files handles metadata parsing errors."""
    import subprocess

    # Malformed metadata (missing fields)
    metadata_output = Completed(stdout="abc123|Alice")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
            ]
        ),
    )

    result = get_commit_files("abc123")

    assert "error" in result
    assert "Failed to parse commit metadata" in result["error"]


def test_get_commit_files_general_exception(monkeypatch):
    """Test commit files handles general exceptions."""
    import subprocess

    def failing_run(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(subprocess, "run", failing_run)

    result = get_commit_files("abc123")

    assert "error" in result
    assert "Failed to get commit files" in result["error"]


def test_build_git_log_command_basic():
    """Test building git log command with basic arguments."""
    base_args = ["-10"]
    author_filters = ["user@example.com"]

    cmd = _build_git_log_command(base_args, author_filters)

    assert cmd == [
        "git",
        "log",
        "-10",
        "--author=user@example.com",
        "--pretty=format:%H|%an|%ai|%s",
    ]


def test_build_git_log_command_multiple_authors():
    """Test building git log command with multiple author filters."""
    base_args = ["--since=yesterday", "--until=now"]
    author_filters = ["user1@example.com", "user2@example.com"]

    cmd = _build_git_log_command(base_args, author_filters)

    assert cmd == [
        "git",
        "log",
        "--since=yesterday",
        "--until=now",
        "--author=user1@example.com",
        "--author=user2@example.com",
        "--pretty=format:%H|%an|%ai|%s",
    ]


def test_build_git_log_command_no_authors():
    """Test building git log command with no author filters."""
    base_args = ["-5"]
    author_filters = []

    cmd = _build_git_log_command(base_args, author_filters)

    assert cmd == ["git", "log", "-5", "--pretty=format:%H|%an|%ai|%s"]


def test_parse_commit_lines_single():
    """Test parsing single commit line."""
    output = "abc123|Alice Author|2024-01-01 12:00:00 +0000|feat: add feature"

    commits = _parse_commit_lines(output)

    assert len(commits) == 1
    assert commits[0]["hash"] == "abc123"
    assert commits[0]["author"] == "Alice Author"
    assert commits[0]["date"] == "2024-01-01 12:00:00 +0000"
    assert commits[0]["message"] == "feat: add feature"


def test_parse_commit_lines_multiple():
    """Test parsing multiple commit lines."""
    output = (
        "abc123|Alice|2024-01-01 12:00:00 +0000|feat: add feature\n"
        "def456|Bob|2024-01-02 13:00:00 +0000|fix: bug fix\n"
        "ghi789|Charlie|2024-01-03 14:00:00 +0000|docs: update readme"
    )

    commits = _parse_commit_lines(output)

    assert len(commits) == 3
    assert commits[0]["hash"] == "abc123"
    assert commits[1]["author"] == "Bob"
    assert commits[2]["message"] == "docs: update readme"


def test_parse_commit_lines_with_pipe_in_message():
    """Test parsing commit with pipe character in message."""
    output = "abc123|Alice|2024-01-01 12:00:00 +0000|feat: add feature | with pipe"

    commits = _parse_commit_lines(output)

    assert len(commits) == 1
    assert commits[0]["message"] == "feat: add feature | with pipe"


def test_parse_commit_lines_empty():
    """Test parsing empty output."""
    output = ""

    commits = _parse_commit_lines(output)

    assert commits == []


def test_parse_commit_lines_whitespace_only():
    """Test parsing whitespace-only output."""
    output = "\n\n  \n"

    commits = _parse_commit_lines(output)

    assert commits == []


def test_handle_git_error_called_process_error():
    """Test handling CalledProcessError."""
    import subprocess

    error = subprocess.CalledProcessError(
        128, ["git", "log"], output="", stderr="fatal: not a git repository"
    )

    result = _handle_git_error(error)

    assert len(result) == 1
    assert "error" in result[0]
    assert "Git command failed" in result[0]["error"]
    assert "fatal: not a git repository" in result[0]["error"]


def test_handle_git_error_generic_exception():
    """Test handling generic exception."""
    error = RuntimeError("Something went wrong")

    result = _handle_git_error(error)

    assert len(result) == 1
    assert "error" in result[0]
    assert "Failed to get commits" in result[0]["error"]
    assert "Something went wrong" in result[0]["error"]


def test_check_git_config_exists(monkeypatch):
    """Test checking git config when key exists."""
    import subprocess

    def mock_run(cmd, **kwargs):
        if cmd == ["git", "config", "--get", "user.email"]:
            return Completed(stdout="user@example.com\n")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _check_git_config("user.email")

    assert result is True


def test_check_git_config_not_exists(monkeypatch):
    """Test checking git config when key doesn't exist."""
    import subprocess

    def mock_run(cmd, **kwargs):
        if cmd == ["git", "config", "--get", "user.email"]:
            raise subprocess.CalledProcessError(1, cmd)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _check_git_config("user.email")

    assert result is False


def test_get_config_source_environment(monkeypatch):
    """Test config source detection from environment variable."""
    monkeypatch.setenv("GLIN_TRACK_EMAILS", "user@example.com")

    source = _get_config_source()

    assert source == "environment_variable"


def test_get_config_source_config_file(monkeypatch, tmp_path):
    """Test config source detection from config file."""

    monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)

    # Create a config file in current directory
    config_file = tmp_path / "glin.toml"
    config_file.write_text('track_emails = ["user@example.com"]\n')

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    source = _get_config_source()

    assert source.startswith("config_file")
    assert "glin.toml" in source


def test_get_config_source_git_user_email(monkeypatch, tmp_path):
    """Test config source detection from git user.email."""
    import subprocess

    monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)
    monkeypatch.chdir(tmp_path)

    def mock_run(cmd, **kwargs):
        if cmd == ["git", "config", "--get", "user.email"]:
            return Completed(stdout="user@example.com\n")
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", mock_run)

    source = _get_config_source()

    assert source == "git_user_email"


def test_get_config_source_git_user_name(monkeypatch, tmp_path):
    """Test config source detection from git user.name."""
    import subprocess

    monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)
    monkeypatch.chdir(tmp_path)

    def mock_run(cmd, **kwargs):
        if cmd == ["git", "config", "--get", "user.email"]:
            raise subprocess.CalledProcessError(1, cmd)
        if cmd == ["git", "config", "--get", "user.name"]:
            return Completed(stdout="User Name\n")
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", mock_run)

    source = _get_config_source()

    assert source == "git_user_name"


def test_get_config_source_none(monkeypatch, tmp_path):
    """Test config source detection when no config exists."""
    import subprocess

    monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)
    monkeypatch.chdir(tmp_path)

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", mock_run)

    source = _get_config_source()

    assert source == "none"


def test_get_commit_files_empty_commit(monkeypatch):
    """Test commit files with no file changes (empty commit)."""
    import subprocess

    metadata_output = Completed(
        stdout="jkl012|Dave|dave@example.com|2024-01-04 16:00:00 +0000|chore: empty commit"
    )

    status_output = Completed(stdout="\n")
    numstat_output = Completed(stdout="\n")

    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "show", "--no-patch"], metadata_output),
                (["git", "show", "--name-status"], status_output),
                (["git", "show", "--numstat"], numstat_output),
            ]
        ),
    )

    result = get_commit_files("jkl012")

    assert result["hash"] == "jkl012"
    assert result["files_changed"] == 0
    assert result["total_additions"] == 0
    assert result["total_deletions"] == 0
    assert len(result["files"]) == 0


def test_get_commits_by_date_normalizes_single_iso_date(monkeypatch):
    """When since is an ISO date and until is default, normalize to previous day.."""
    import subprocess
    from unittest.mock import patch

    # Expectation: since=2025-10-10, until=2025-10-11 when input is since="2025-10-11"
    log_empty = Completed(stdout="\n")

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (
                        [
                            "git",
                            "log",
                            "--since=2025-10-10",
                            "--until=2025-10-11",
                        ],
                        log_empty,
                    ),
                ]
            ),
        )
        res = get_commits_by_date("2025-10-11")
        assert res and res[0].get("info") == "No commits found in date range"


def test_get_commits_by_date_no_normalize_with_explicit_until(monkeypatch):
    """If until is provided explicitly, do not shift dates."""
    import subprocess
    from unittest.mock import patch

    log_empty = Completed(stdout="\n")

    with patch("seev.git_tools.get_tracked_emails", return_value=["me@example.com"]):
        monkeypatch.setattr(
            subprocess,
            "run",
            make_run(
                [
                    (
                        [
                            "git",
                            "log",
                            "--since=2025-10-11",
                            "--until=2025-10-12",
                        ],
                        log_empty,
                    ),
                ]
            ),
        )
        res = get_commits_by_date("2025-10-11", "2025-10-12")
        assert res and res[0].get("info") == "No commits found in date range"
