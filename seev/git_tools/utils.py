import subprocess
from typing import TypedDict


class RepoRootResult(TypedDict, total=False):
    path: str
    error: str


def resolve_repo_root(path: str | None) -> RepoRootResult:
    """Resolve the git repository root for a given path.

    If ``path`` is None, this function returns an error-free result only if the
    current process working directory is inside a git repository. This helper is
    intended to be used when a caller explicitly supplies a path; for backward
    compatibility, most callers in this project will only invoke this when a
    ``workdir`` has been provided by the client.
    """
    if path is None:
        # Defer to callers to keep default behavior unchanged (no -C injection).
        # However, provide a best-effort resolution for potential direct uses.
        base = "."
    else:
        base = path
    try:
        res = subprocess.run(
            ["git", "-C", base, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        root = res.stdout.strip()
        return {"path": root}
    except subprocess.CalledProcessError as e:  # noqa: BLE001
        msg = (e.stderr or e.stdout or "Not a git repo").strip() or "Not a git repo"
        return {"error": msg}


def run_git(args: list[str], repo_root: str | None = None, **kwargs):
    """Run a git subcommand with optional repo root selection via ``-C``.

    - When ``repo_root`` is provided, the command becomes ``git -C <repo_root> <args...>``.
    - When ``repo_root`` is None, the command is executed as ``git <args...>`` to
      preserve existing behavior and test expectations.
    """
    if repo_root:
        cmd = ["git", "-C", repo_root, *args]
    else:
        cmd = ["git", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)
