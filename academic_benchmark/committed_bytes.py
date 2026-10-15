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


# one bound for every git query of the archive / quarantine code (a diff over a whole tree is the
# slowest; ``archive_manifest`` imports this constant instead of keeping its own)
GIT_QUERY_TIMEOUT_SECONDS = 120


class GitQueryFailed(RuntimeError):
    """A git query did not produce an answer: it timed out (``kind="timeout"``), exited non-zero
    (``"exit"``, with ``returncode`` and ``stderr``) or could not be started (``"unavailable"``).
    Callers must treat it as "unknown", never as "empty" or "not tracked"."""

    def __init__(self, message: str, *, kind: str, returncode: int | None = None, stderr: str = "") -> None:
        super().__init__(message)
        self.kind = kind
        self.returncode = returncode
        self.stderr = stderr


def run_git(arguments: Sequence[str], cwd: Path | str, *, extra_environment: dict[str, str] | None = None) -> bytes:
    """stdout of ``git <arguments>`` run in ``cwd`` with the shared timeout and the isolated
    environment; every failure becomes a :class:`GitQueryFailed`."""
    environment = git_environment()
    if extra_environment:
        environment.update(extra_environment)
    try:
        done = subprocess.run(
            ["git", *arguments], cwd=Path(cwd), capture_output=True, check=True,
            timeout=GIT_QUERY_TIMEOUT_SECONDS, env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitQueryFailed(f"git timed out after {GIT_QUERY_TIMEOUT_SECONDS} s", kind="timeout") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
        raise GitQueryFailed(
            f"git failed with exit status {exc.returncode}" + (f" ({detail})" if detail else ""),
            kind="exit", returncode=exc.returncode, stderr=detail,
        ) from exc
    except OSError as exc:
        raise GitQueryFailed(f"git unavailable ({type(exc).__name__})", kind="unavailable") from exc
    return done.stdout


def working_copy_drift(git_cwd: Path | str) -> list[str]:
    """Paths below ``git_cwd`` (relative to it, POSIX) whose working copy differs from the index
    according to ``git diff``. Git applies its own end-of-line normalisation, so a CRLF checkout
    (``core.autocrlf=true``) or an LF checkout is clean and only a real content change is listed.
    Untracked files are not listed. Without git, or outside a repository, the result is empty (the
    documented "nothing to compare"); a timeout or any other git failure raises
    :class:`GitQueryFailed`, because "no drift" would then be a guess."""
    try:
        # LC_ALL=C: the "not a git repository" test below reads git's English message
        stdout = run_git(["diff", "--name-only", "-z", "--relative", "--", "."], git_cwd, extra_environment={"LC_ALL": "C"})
    except GitQueryFailed as exc:
        if exc.kind == "unavailable" or (exc.kind == "exit" and "not a git repository" in exc.stderr.lower()):
            return []
        raise
    return sorted(item.decode("utf-8", "replace") for item in stdout.split(b"\0") if item)


# ``git cat-file blob :<spec>`` exits 128 ("fatal: ...") for a path that is not in the index and
# for a directory that is not a repository: the documented disk fallback. Any other exit status,
# and a timeout, is not that case.
_NOT_IN_INDEX_EXIT_STATUS = 128


def _git_blob(cwd: Path, index_spec: str) -> tuple[bytes | None, str]:
    """``(blob, "")``, or ``(None, reason)`` for the documented "no blob here" outcomes (not in the
    index / not a repository: exit 128; git cannot be started). A timeout or an unexpected exit
    status raises :class:`GitQueryFailed`."""
    try:
        return run_git(["cat-file", "blob", f":{index_spec}"], cwd), ""
    except GitQueryFailed as exc:
        if exc.kind == "exit" and exc.returncode == _NOT_IN_INDEX_EXIT_STATUS:
            return None, "not a tracked file in a git repository: " + exc.stderr
        if exc.kind == "unavailable":
            return None, str(exc)
        raise


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
    logs a warning because the bytes are then whatever this platform's checkout wrote. A git
    timeout or an unexpected git exit status is NOT such a case: it raises :class:`GitQueryFailed`
    (and no further source is tried), because the disk bytes would then silently replace an
    answer git could not give."""
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
    (default ``:./<name>`` relative to the file's own directory). Never falls back to the disk; a git timeout or
    unexpected exit status raises :class:`GitQueryFailed` instead of answering False."""
    path = Path(disk_path)
    cwd = Path(git_cwd) if git_cwd is not None else path.parent
    blob, _ = _git_blob(cwd, index_spec if index_spec is not None else f"./{path.name}")
    return blob is not None
