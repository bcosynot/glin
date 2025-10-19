from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Iterable


def resolve_caller_cwd() -> Path:
    """
    Determine the working directory where git commands should be executed.

    Precedence:
    1. Environment variable GLIN_CALLER_CWD, if set and points to an existing directory.
    2. Current process working directory (os.getcwd()).
    """
    env_cwd = os.environ.get("GLIN_CALLER_CWD")
    if env_cwd:
        p = Path(env_cwd).expanduser()
        if p.is_dir():
            return p
    return Path(os.getcwd())


def run_git(args: Iterable[str] | list[str], /, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """
    Wrapper around subprocess.run for git commands that ensures the command
    executes in the caller's working directory.

    - Sets cwd to `resolve_caller_cwd()` if not explicitly provided.
    - Forces text=True by default unless user overrides.
    - Returns subprocess.CompletedProcess with stdout/err as str.
    """
    if "cwd" not in kwargs or kwargs["cwd"] is None:
        kwargs["cwd"] = resolve_caller_cwd()
    kwargs.setdefault("text", True)
    # Type: we expect a list[str] or iterable of str; keep as-is
    return subprocess.run(list(args), **kwargs)  # type: ignore[arg-type]
