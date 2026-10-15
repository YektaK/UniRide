"""Canonical bytes of a tracked file as git stores them in the INDEX (staged bytes), independent of
the platform's line-ending conversion.

Archive and quarantine manifests (A01 Bildiri/YAEM archives, A13 legacy results) describe what git
stores. The reference is the index (``git cat-file blob :<path>``), not HEAD and not the disk, on
purpose: a quarantine moves files before anything is staged or committed, the pre-move path is
still in the index, and repositories without a commit yet (and archives staged but not yet
committed) must keep working. The index equals the committed bytes only while nothing is staged
over them; ``quarantine_tracked_tree`` ties the two together by refusing a source that differs from
HEAD. A Windows working copy with ``core.autocrlf=true`` holds CRLF bytes for the same blob, so
hashing the disk would make a manifest that verifies on one platform only (2026-10-14 finding).
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Sequence

LOGGER = logging.getLogger(__name__)


_REPOSITORY_SELECTORS = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE")


def git_environment() -> dict[str, str]:
    """``os.environ`` without the variables that make git ignore ``cwd``. A git hook exports
    ``GIT_DIR``/``GIT_INDEX_FILE``/``GIT_WORK_TREE``; inherited, they would point the lookup at the
    hooked repository instead of the one the file lives in."""
    return {key: value for key, value in os.environ.items() if key not in _REPOSITORY_SELECTORS}


def working_copy_drift(git_cwd: Path | str) -> list[str]:
    """Paths below ``git_cwd`` (relative to it, POSIX) whose working copy differs from the index
    according to ``git diff``. Git applies its own end-of-line normalisation, so a CRLF checkout
    (``core.autocrlf=true``) or an LF checkout is clean and only a real content change is listed.
    Untracked files are not listed; without git or outside a repository the result is empty."""
    try:
        done = subprocess.run(
            ["git", "diff", "--name-only", "-z", "--relative", "--", "."],
            cwd=Path(git_cwd), capture_output=True, check=True, timeout=120, env=git_environment(),
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted(item.decode("utf-8", "replace") for item in done.stdout.split(b"\0") if item)


def _git_blob(cwd: Path, index_spec: str) -> tuple[bytes | None, str]:
    try:
        done = subprocess.run(
            ["git", "cat-file", "blob", f":{index_spec}"],
            cwd=cwd, capture_output=True, check=True, timeout=60, env=git_environment(),
        )
        return done.stdout, ""
    except subprocess.CalledProcessError as exc:
        return None, "not a tracked file in a git repository: " + exc.stderr.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"git unavailable ({type(exc).__name__})"


def committed_bytes(
    disk_path: Path | str,
    *,
    git_cwd: Path | str | None = None,
    index_spec: str | None = None,
    fallback_sources: Sequence[tuple[Path | str, str]] = (),
) -> bytes:
    """Return the index (staged) bytes, ``git cat-file blob :<index_spec>`` run in ``git_cwd``; fall
    back to the bytes on disk. The name says "committed" for history; the source is the index.

    Defaults address the file relative to its own directory (``:./name``), which is correct
    wherever the repository root is. ``index_spec`` is passed to git verbatim after the ``:`` (a
    ``./``-prefixed spec is relative to ``git_cwd``, any other spec is relative to the repo root).
    ``fallback_sources`` are further ``(git_cwd, index_spec)`` lookups tried in order before the
    disk is used. The disk fallback (git missing, not a repository, file untracked everywhere)
    logs a warning because the bytes are then whatever this platform's checkout wrote."""
    path = Path(disk_path)
    sources = [(Path(git_cwd) if git_cwd is not None else path.parent, index_spec if index_spec is not None else f"./{path.name}")]
    sources.extend((Path(cwd), spec) for cwd, spec in fallback_sources)
    reason = ""
    for cwd, spec in sources:
        blob, reason = _git_blob(cwd, spec)
        if blob is not None:
            return blob
    LOGGER.warning("index bytes unavailable for %s (%s); falling back to disk bytes", path, reason)
    return path.read_bytes()


def index_has_blob(
    disk_path: Path | str,
    *,
    git_cwd: Path | str | None = None,
    index_spec: str | None = None,
) -> bool:
    """True when git's index holds a blob at the same address ``committed_bytes`` would read first
    (default ``:./<name>`` relative to the file's own directory). Never falls back to the disk."""
    path = Path(disk_path)
    cwd = Path(git_cwd) if git_cwd is not None else path.parent
    blob, _ = _git_blob(cwd, index_spec if index_spec is not None else f"./{path.name}")
    return blob is not None
