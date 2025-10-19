from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def chdir(target: str | os.PathLike[str] | None) -> Iterator[None]:
    """Temporarily change the current working directory.

    If target is None or empty, this is a no-op.
    Relative paths are resolved against the current working directory.
    Expands '~' to the user home.
    """
    if not target:
        yield
        return
    old_cwd = os.getcwd()
    try:
        new_cwd = Path(str(target)).expanduser()
        os.chdir(new_cwd)
        yield
    finally:
        try:
            os.chdir(old_cwd)
        except Exception:
            # Best-effort restore; in rare cases (deleted cwd), fall back to home
            try:
                os.chdir(str(Path.home()))
            except Exception:
                pass
