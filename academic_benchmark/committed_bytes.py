"""Canonical (committed) bytes of a tracked file, independent of the platform's line-ending conversion.

Archive and quarantine manifests (A01 Bildiri/YAEM archives, A13 legacy results) describe what git
stores. A Windows working copy with ``core.autocrlf=true`` holds CRLF bytes for the same blob, so
hashing the disk would make a manifest that verifies on one platform only (2026-10-14 finding).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Sequence

LOGGER = logging.getLogger(__name__)


def _git_blob(cwd: Path, index_spec: str) -> tuple[bytes | None, str]:
    try:
        done = subprocess.run(
            ["git", "cat-file", "blob", f":{index_spec}"], cwd=cwd, capture_output=True, check=True, timeout=60
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
    """Return ``git cat-file blob :<index_spec>`` run in ``git_cwd``; fall back to the bytes on disk.

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
    LOGGER.warning("committed bytes unavailable for %s (%s); falling back to disk bytes", path, reason)
    return path.read_bytes()
