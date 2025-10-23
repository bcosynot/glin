"""Tests for configuration management."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from glin.config import (
    _get_config_file_emails,
    _get_git_author_pattern,
    create_config_file,
    get_tracked_emails,
    set_tracked_emails_env,
)


class TestGetTrackedEmails:
    def test_env_variable_takes_priority(self, monkeypatch):
        """Environment variable should take priority over other sources."""
        monkeypatch.setenv("GLIN_TRACK_EMAILS", "env@example.com,env2@example.com")

        # Mock other sources to ensure they're not used
        with patch("glin.config._get_config_file_emails", return_value=["file@example.com"]):
            with patch("glin.config._get_git_author_pattern", return_value="git@example.com"):
                emails = get_tracked_emails()
                assert emails == ["env@example.com", "env2@example.com"]

    def test_config_file_fallback(self, monkeypatch):
        """Config file should be used when env variable is not set."""
        monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)

        with patch("glin.config._get_config_file_emails", return_value=["file@example.com"]):
            with patch("glin.config._get_git_author_pattern", return_value="git@example.com"):
                emails = get_tracked_emails()
                assert emails == ["file@example.com"]

    def test_git_config_fallback(self, monkeypatch):
        """Git config should be used when env and config file are not available."""
        monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)

        with patch("glin.config._get_config_file_emails", return_value=[]):
            with patch("glin.config._get_git_author_pattern", return_value="git@example.com"):
                emails = get_tracked_emails()
                assert emails == ["git@example.com"]

    def test_empty_when_no_config(self, monkeypatch):
        """Should return empty list when no configuration is found."""
        monkeypatch.delenv("GLIN_TRACK_EMAILS", raising=False)

        with patch("glin.config._get_config_file_emails", return_value=[]):
            with patch("glin.config._get_git_author_pattern", return_value=None):
                emails = get_tracked_emails()
                assert emails == []

    def test_env_variable_whitespace_handling(self, monkeypatch):
        """Environment variable should handle whitespace correctly."""
        monkeypatch.setenv("GLIN_TRACK_EMAILS", " email1@example.com , email2@example.com , ")
        emails = get_tracked_emails()
        assert emails == ["email1@example.com", "email2@example.com"]


class TestConfigFileEmails:
    def test_reads_from_current_directory(self):
        """Should read config from current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "glin.toml"
            config_path.write_text('track_emails = ["test@example.com"]')

            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                emails = _get_config_file_emails()
                assert emails == ["test@example.com"]

    def test_reads_from_home_config(self):
        """Should read config from ~/.config/glin/glin.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".config" / "glin"
            config_dir.mkdir(parents=True)
            config_path = config_dir / "glin.toml"
            config_path.write_text('track_emails = ["home@example.com"]')

            with patch("pathlib.Path.cwd", return_value=Path("/nonexistent")):
                with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                    emails = _get_config_file_emails()
                    assert emails == ["home@example.com"]

    def test_handles_malformed_config(self):
        """Should handle malformed config files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "glin.toml"
            config_path.write_text("invalid toml content [[[")

            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("pathlib.Path.home", return_value=Path(tmpdir) / "nonexistent"):
                    emails = _get_config_file_emails()
                    assert emails == []


class TestSetTrackedEmailsEnv:
    def test_sets_environment_variable(self, monkeypatch):
        """Should set GLIN_TRACK_EMAILS environment variable."""
        emails = ["test1@example.com", "test2@example.com"]
        set_tracked_emails_env(emails)

        assert os.environ["GLIN_TRACK_EMAILS"] == "test1@example.com,test2@example.com"

    def test_handles_empty_list(self):
        """Should handle empty email list."""
        set_tracked_emails_env([])
        assert os.environ["GLIN_TRACK_EMAILS"] == ""


class TestCreateConfigFile:
    def test_creates_config_file(self):
        """Should create config file with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_glin.toml"
            emails = ["user1@example.com", "user2@example.com"]

            result_path = create_config_file(emails, config_path)

            assert result_path == config_path
            assert config_path.exists()

            content = config_path.read_text()
            assert 'track_emails = ["user1@example.com", "user2@example.com"]' in content
            assert "# Glin Configuration" in content

    def test_creates_default_path(self):
        """Should create config file at default path when none specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                emails = ["test@example.com"]
                result_path = create_config_file(emails)

                expected_path = Path(tmpdir) / "glin.toml"
                assert result_path == expected_path
                assert expected_path.exists()

    def test_creates_parent_directories(self):
        """Should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "dir" / "glin.toml"
            emails = ["test@example.com"]

            result_path = create_config_file(emails, config_path)

            assert result_path == config_path
            assert config_path.exists()
            assert config_path.parent.exists()


class TestGitAuthorPattern:
    def test_prefers_email_over_name(self):
        """Should prefer git user.email over user.name."""
        with patch("subprocess.run") as mock_run:
            # First call (email) succeeds
            mock_run.return_value.stdout = "user@example.com\n"

            result = _get_git_author_pattern()
            assert result == "user@example.com"

            # Should only call git config for email, not name
            mock_run.assert_called_once_with(
                ["git", "config", "--get", "user.email"],
                capture_output=True,
                text=True,
                check=True,
            )

    def test_falls_back_to_name(self):
        """Should fall back to git user.name when email fails."""
        with patch("subprocess.run") as mock_run:

            def side_effect(cmd, **kwargs):
                if "user.email" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                else:  # user.name
                    mock_result = Mock()
                    mock_result.stdout = "John Doe\n"
                    return mock_result

            mock_run.side_effect = side_effect

            result = _get_git_author_pattern()
            assert result == "John Doe"

    def test_returns_none_when_both_fail(self):
        """Should return None when both email and name fail."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])

            result = _get_git_author_pattern()
            assert result is None
