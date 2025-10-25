from seev.git_tools import get_remote_origin


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


def test_get_remote_origin_https(monkeypatch):
    import subprocess

    origin = Completed(stdout="https://github.com/org/repo.git\n")
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "remote", "get-url", "origin"], origin),
            ]
        ),
    )

    res = get_remote_origin()
    assert res["name"] == "origin"
    assert res["url"] == "https://github.com/org/repo.git"


def test_get_remote_origin_ssh(monkeypatch):
    import subprocess

    origin = Completed(stdout="git@github.com:org/repo.git\n")
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "remote", "get-url", "origin"], origin),
            ]
        ),
    )

    res = get_remote_origin()
    assert res["url"].startswith("git@github.com:")


def test_get_remote_origin_missing(monkeypatch):
    import subprocess

    err = subprocess.CalledProcessError(
        2, ["git", "remote", "get-url", "origin"], stderr="fatal: No such remote: 'origin'\n"
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "remote", "get-url", "origin"], err),
            ]
        ),
    )

    res = get_remote_origin()
    assert "error" in res
    assert "No such remote" in res["error"]


def test_get_remote_origin_with_workdir(monkeypatch):
    """When workdir is provided, commands should include '-C <root>'."""
    import subprocess

    # Mock repo root resolution
    monkeypatch.setattr("glin.git_tools.remotes.resolve_repo_root", lambda p: {"path": "/repo"})

    origin = Completed(stdout="https://github.com/org/repo.git\n")
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "-C", "/repo", "remote", "get-url", "origin"], origin),
            ]
        ),
    )

    from seev.git_tools.remotes import get_remote_origin as _get

    res = _get(workdir="/some/project")
    assert res["name"] == "origin"
    assert res["url"] == "https://github.com/org/repo.git"
    import subprocess

    err = subprocess.CalledProcessError(
        2, ["git", "remote", "get-url", "origin"], stderr="fatal: No such remote: 'origin'\n"
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        make_run(
            [
                (["git", "remote", "get-url", "origin"], err),
            ]
        ),
    )

    res = get_remote_origin()
    assert "error" in res
    assert "No such remote" in res["error"]
