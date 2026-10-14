"""Archive manifests describe the COMMITTED bytes, never a platform's line-ending conversion.

Finding 2026-10-14: the Bildiri/YAEM archive manifests were recorded from CRLF working copies
(Windows, core.autocrlf=true) while git stores LF, so a clean LF checkout (Linux CI) failed with
~286 'size mismatch' entries. Same class of defect as the A13 legacy-results quarantine.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path, PurePosixPath

import pytest

from academic_benchmark.archive_manifest import (
    ArchiveEntry,
    ArchiveManifest,
    build_manifest,
    quarantine_tracked_tree,
    verify_manifest,
)

REPO = Path(__file__).resolve().parents[2]
MANIFESTS = (
    REPO / "archive" / "academic_benchmark" / "bildiri2026_legacy" / "manifest.json",
    REPO / "archive" / "academic_benchmark" / "yaem2026_legacy" / "manifest.json",
)
LF_TEXT = b"VALUE = 1\nOTHER = 2\n"
CRLF_TEXT = LF_TEXT.replace(b"\n", b"\r\n")


def _git(cwd: Path, *args: str) -> bytes:
    # autocrlf pinned off so the blob is exactly the bytes we wrote, whatever the machine config is
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True,
    ).stdout


def _repo_with_crlf_working_copy(tmp_path: Path, tracked_relative: str) -> tuple[Path, Path]:
    """Repo whose committed blob is LF while the working copy of the same file is CRLF."""
    repo = tmp_path / "repo"
    target = repo / Path(tracked_relative)
    target.parent.mkdir(parents=True)
    target.write_bytes(LF_TEXT)
    _git(repo, "init")
    _git(repo, "add", tracked_relative)
    _git(repo, "commit", "-m", "lf blob")
    target.write_bytes(CRLF_TEXT)
    return repo, target


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_build_and_verify_use_the_blob_when_the_working_copy_is_crlf(tmp_path: Path):
    relative = "archive/academic_benchmark/yaem2026_legacy/core/solver.py"
    repo, target = _repo_with_crlf_working_copy(tmp_path, relative)
    archive = repo / "archive" / "academic_benchmark" / "yaem2026_legacy"
    assert target.read_bytes() == CRLF_TEXT  # the platform-dependent working copy
    manifest = build_manifest(
        archive_id="yaem2026_legacy",
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archived_root=archive,
        original_paths=[PurePosixPath("core/solver.py")],
        withheld=[],
    )
    (entry,) = manifest.entries
    assert entry.byte_size == len(LF_TEXT)
    assert entry.sha256 == _sha(LF_TEXT)
    assert verify_manifest(manifest, archive) == []


def test_verify_still_reports_a_manifest_that_disagrees_with_the_blob(tmp_path: Path):
    relative = "archive/academic_benchmark/yaem2026_legacy/core/solver.py"
    repo, _ = _repo_with_crlf_working_copy(tmp_path, relative)
    archive = repo / "archive" / "academic_benchmark" / "yaem2026_legacy"
    template = dict(
        original_path="academic_benchmark/yaem2026/core/solver.py",
        archive_path=relative,
        classification="REFERENCE_ONLY",
    )

    def manifest_for(size: int, digest: str) -> ArchiveManifest:
        return ArchiveManifest(
            schema_version="uniride-archive/v1", archive_id="yaem2026_legacy",
            source_root="academic_benchmark/yaem2026", archive_root="archive/academic_benchmark/yaem2026_legacy",
            entries=[ArchiveEntry(**template, byte_size=size, sha256=digest)],
        )

    # a manifest that still holds the CRLF working-copy values is wrong: git stores LF
    assert verify_manifest(manifest_for(len(CRLF_TEXT), _sha(CRLF_TEXT)), archive) == ["size mismatch: core/solver.py"]
    assert verify_manifest(manifest_for(len(LF_TEXT), "0" * 64), archive) == ["checksum mismatch: core/solver.py"]


def test_quarantine_records_the_committed_bytes_not_the_crlf_working_copy(tmp_path: Path):
    source = "academic_benchmark/yaem2026/core/solver.py"
    repo, _ = _repo_with_crlf_working_copy(tmp_path, source)
    manifest = quarantine_tracked_tree(
        repo_root=repo,
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archive_id="yaem2026_legacy",
    )
    (entry,) = manifest.entries
    assert (entry.byte_size, entry.sha256) == (len(LF_TEXT), _sha(LF_TEXT))
    on_disk = json.loads((repo / "archive/academic_benchmark/yaem2026_legacy/manifest.json").read_text(encoding="utf-8"))
    assert on_disk["entries"][0]["sha256"] == _sha(LF_TEXT)


def test_disk_fallback_warns_when_git_cannot_supply_the_blob(tmp_path: Path, caplog):
    from academic_benchmark.committed_bytes import committed_bytes

    loose = tmp_path / "loose.txt"
    loose.write_bytes(b"x\r\n")
    with caplog.at_level(logging.WARNING):
        assert committed_bytes(loose) == b"x\r\n"
    assert any("falling back to disk bytes" in record.getMessage() for record in caplog.records)


def test_legacy_results_helper_warns_on_disk_fallback(tmp_path: Path, caplog):
    from academic_benchmark.obsolete_results import _committed_bytes

    loose = tmp_path / "legacy" / "a.csv"
    loose.parent.mkdir()
    loose.write_bytes(b"a,b\r\n")
    with caplog.at_level(logging.WARNING):
        assert _committed_bytes(str(loose), str(tmp_path)) == b"a,b\r\n"
    assert any("falling back to disk bytes" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda p: p.parent.name)
def test_committed_manifest_values_equal_the_committed_blobs(manifest_path: Path):
    """Platform-independent: compares the manifest to git's blobs, not to whatever the checkout wrote."""
    try:
        inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=REPO, capture_output=True, text=True)
    except OSError:
        pytest.skip("git unavailable")
    if inside.returncode != 0:
        pytest.skip("not a git checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    wrong = []
    for entry in manifest["entries"]:
        if entry["archive_path"] is None:
            continue
        blob = subprocess.run(["git", "cat-file", "blob", f":{entry['archive_path']}"], cwd=REPO, capture_output=True, check=True).stdout
        if (len(blob), _sha(blob)) != (entry["byte_size"], entry["sha256"]):
            wrong.append(entry["archive_path"])
    assert not wrong, f"{len(wrong)} manifest entries differ from the committed blob, e.g. {wrong[:3]}"
