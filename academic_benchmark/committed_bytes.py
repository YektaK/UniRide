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


# git messages are matched in English
_C_LOCALE = {"LC_ALL": "C"}

# ``git cat-file blob :<spec>`` for a path that is not in the index of a healthy repository exits 128
# with one of these messages. A corrupt index exits 128 too ("index file smaller than expected"), so
# the exit status alone is not enough.
_NOT_IN_INDEX_EXIT_STATUS = 128
_NOT_IN_INDEX_MESSAGES = ("does not exist", "but not in the index")


def _enclosing_dot_git(directory: Path) -> Path | None:
    """The nearest ``.git`` entry at or above ``directory``, if any."""
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate / ".git"
    return None


def is_git_repository(cwd: Path | str, cache: dict[Path, bool] | None = None) -> bool:
    """Whether ``cwd`` lies in a git repository, asked of git itself (``git rev-parse --git-dir``).

    ``git diff`` and ``git cat-file`` fail with exit 129 / 128 and the words "not a git repository"
    both outside a repository and inside one that git refuses to trust (dubious ownership,
    ``safe.directory``), so their failures cannot be classified by themselves. False only for git
    missing, or git saying "not a git repository" with no ``.git`` entry at or above ``cwd``;
    every other failure (dubious ownership, a ``.git`` git cannot read, a timeout) raises
    :class:`GitQueryFailed`. ``cache`` keeps one answer per directory for one verification run."""
    key = Path(cwd)
    if cache is not None and key in cache:
        return cache[key]
    try:
        run_git(["rev-parse", "--git-dir"], key, extra_environment=_C_LOCALE)
        answer = True
    except GitQueryFailed as exc:
        if exc.kind == "unavailable":
            answer = False
        elif exc.kind == "exit" and "not a git repository" in exc.stderr.lower():
            marker = _enclosing_dot_git(key.resolve())
            if marker is not None:
                raise GitQueryFailed(
                    f"git does not recognise {marker} as a repository ({exc.stderr})",
                    kind="exit", returncode=exc.returncode, stderr=exc.stderr,
                ) from exc
            answer = False
        else:
            raise
    if cache is not None:
        cache[key] = answer
    return answer


def working_copy_drift(git_cwd: Path | str, *, repository_cache: dict[Path, bool] | None = None) -> list[str]:
    """Paths below ``git_cwd`` (relative to it, POSIX) whose working copy differs from the index
    according to ``git diff``. Git applies its own end-of-line normalisation, so a CRLF checkout
    (``core.autocrlf=true``) or an LF checkout is clean and only a real content change is listed.
    Untracked files are not listed. Without git, or in a directory that is really not in a
    repository (:func:`is_git_repository`), the result is empty (the documented "nothing to
    compare"); a timeout or any other git failure, including a repository git refuses to trust,
    raises :class:`GitQueryFailed`, because "no drift" would then be a guess."""
    try:
        stdout = run_git(["diff", "--name-only", "-z", "--relative", "--", "."], git_cwd, extra_environment=_C_LOCALE)
    except GitQueryFailed as exc:
        if exc.kind == "unavailable":
            return []
        if exc.kind == "exit" and not is_git_repository(git_cwd, repository_cache):
            return []
        raise
    return sorted(item.decode("utf-8", "replace") for item in stdout.split(b"\0") if item)


def _git_blob(cwd: Path, index_spec: str, repository_cache: dict[Path, bool] | None = None) -> tuple[bytes | None, str]:
    """``(blob, "")``, or ``(None, reason)`` for the documented "no blob here" outcomes: git cannot
    be started, ``cwd`` is really not in a repository, or the path is not in the index of a healthy
    repository (exit 128 with git's "does not exist" / "not in the index" message). A timeout, an
    unexpected exit status, a repository git refuses to trust or a corrupt index raises
    :class:`GitQueryFailed`."""
    try:
        return run_git(["cat-file", "blob", f":{index_spec}"], cwd, extra_environment=_C_LOCALE), ""
    except GitQueryFailed as exc:
        if exc.kind == "unavailable":
            return None, str(exc)
        if exc.kind == "exit" and exc.returncode == _NOT_IN_INDEX_EXIT_STATUS:
            if not is_git_repository(cwd, repository_cache):
                return None, "not a git repository: " + exc.stderr
            if any(message in exc.stderr for message in _NOT_IN_INDEX_MESSAGES):
                return None, "not a tracked file in a git repository: " + exc.stderr
        raise


def committed_bytes(
    disk_path: Path | str,
    *,
    git_cwd: Path | str | None = None,
    index_spec: str | None = None,
    fallback_sources: Sequence[tuple[Path | str, str]] = (),
    repository_cache: dict[Path, bool] | None = None,
) -> bytes:
    """Return the index (staged) bytes, ``git cat-file blob :<index_spec>`` run in ``git_cwd``; fall
    back to the bytes on disk. The name says "committed" for history; the source is the index.

    Defaults address the file relative to its own directory (``:./name``), which is correct
    wherever the repository root is. ``index_spec`` is passed to git verbatim after the ``:`` (a
    ``./``-prefixed spec is relative to ``git_cwd``, any other spec is relative to the repo root).
    ``fallback_sources`` are further ``(git_cwd, index_spec)`` lookups tried in order before the
    disk is used. The disk fallback (git missing, not a repository, file untracked everywhere)
    logs a warning because the bytes are then whatever this platform's checkout wrote. A git
    timeout, an unexpected git exit status, a repository git refuses to trust (dubious ownership)
    or a corrupt index is NOT such a case: it raises :class:`GitQueryFailed`
    (and no further source is tried), because the disk bytes would then silently replace an
    answer git could not give."""
    path = Path(disk_path)
    sources = [(Path(git_cwd) if git_cwd is not None else path.parent, index_spec if index_spec is not None else f"./{path.name}")]
    sources.extend((Path(cwd), spec) for cwd, spec in fallback_sources)
    reason = ""
    cache = repository_cache if repository_cache is not None else {}
    for cwd, spec in sources:
        blob, reason = _git_blob(cwd, spec, cache)
        if blob is not None:
            return blob
    LOGGER.warning("index bytes unavailable for %s (%s); falling back to disk bytes", path, reason)
    return path.read_bytes()


def index_has_blob(
    disk_path: Path | str,
    *,
    git_cwd: Path | str | None = None,
    index_spec: str | None = None,
    repository_cache: dict[Path, bool] | None = None,
) -> bool:
    """True when git's index holds a blob at the same address ``committed_bytes`` would read first
    (default ``:./<name>`` relative to the file's own directory). Never falls back to the disk; a git timeout or
    unexpected exit status raises :class:`GitQueryFailed` instead of answering False."""
    path = Path(disk_path)
    cwd = Path(git_cwd) if git_cwd is not None else path.parent
    blob, _ = _git_blob(cwd, index_spec if index_spec is not None else f"./{path.name}", repository_cache)
    return blob is not None
