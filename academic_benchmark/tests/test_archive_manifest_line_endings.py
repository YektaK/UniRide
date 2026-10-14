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
    # this repo behaves like a Windows checkout: git normalises CRLF, so a CRLF working copy is NOT drift
    subprocess.run(["git", "config", "--local", "core.autocrlf", "true"], cwd=repo, check=True)
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


SOURCE_ROOT = PurePosixPath("academic_benchmark/yaem2026")
ARCHIVE_ROOT = PurePosixPath("archive/academic_benchmark/yaem2026_legacy")


def _committed_source_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    source = repo / "academic_benchmark" / "yaem2026" / "core" / "solver.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(LF_TEXT)
    _git(repo, "init")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source")
    return repo, source


def _quarantine(repo: Path):
    return quarantine_tracked_tree(
        repo_root=repo, source_root=SOURCE_ROOT, archive_root=ARCHIVE_ROOT, archive_id="yaem2026_legacy"
    )


@pytest.mark.parametrize("stage", [False, True], ids=["unstaged", "staged-not-committed"])
def test_quarantine_refuses_a_source_that_differs_from_head_and_moves_nothing(tmp_path: Path, stage: bool):
    """P2: the manifest records committed bytes, so an uncommitted edit would be silently archived
    as something the manifest does not describe. The function must raise before any move."""
    from academic_benchmark.archive_manifest import QuarantineBlocked

    repo, source = _committed_source_repo(tmp_path)
    edited = b"VALUE = 99  # uncommitted edit\n"
    source.write_bytes(edited)
    if stage:
        _git(repo, "add", "-A")
    with pytest.raises(QuarantineBlocked, match="uncommitted"):
        _quarantine(repo)
    assert source.read_bytes() == edited  # still in place, untouched
    assert not (repo / "archive").exists()  # nothing moved, no archive directory created


def test_clean_quarantine_moves_exactly_the_bytes_the_manifest_describes(tmp_path: Path):
    repo, source = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)
    moved = repo / Path(*ARCHIVE_ROOT.parts) / "core" / "solver.py"
    (entry,) = manifest.entries
    assert (len(moved.read_bytes()), _sha(moved.read_bytes())) == (entry.byte_size, entry.sha256)
    assert not source.exists()


def test_verify_reports_working_copy_drift_in_a_tracked_archive(tmp_path: Path):
    """P1: with a repo present, a tracked archived file edited after commit is reported (the
    manifest equals the blob, so only git's own comparison can see it)."""
    relative = "archive/academic_benchmark/yaem2026_legacy/core/solver.py"
    repo, target = _repo_with_crlf_working_copy(tmp_path, relative)
    archive = repo / Path(*ARCHIVE_ROOT.parts)
    manifest = build_manifest(
        archive_id="yaem2026_legacy", source_root=SOURCE_ROOT, archive_root=ARCHIVE_ROOT, archived_root=archive,
        original_paths=[PurePosixPath("core/solver.py")], withheld=[],
    )
    assert verify_manifest(manifest, archive) == []  # CRLF alone is normalised away by git
    target.write_bytes(b"VALUE = 99\r\n")
    assert verify_manifest(manifest, archive) == ["working copy differs from committed: core/solver.py"]


def test_committed_bytes_ignores_inherited_git_environment(tmp_path: Path, monkeypatch):
    """A git hook exports GIT_DIR/GIT_INDEX_FILE/GIT_WORK_TREE; they must not redirect the lookup."""
    from academic_benchmark.committed_bytes import committed_bytes

    relative = "archive/x/core/solver.py"
    repo, target = _repo_with_crlf_working_copy(tmp_path / "a", relative)
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git" / "index"))
    assert committed_bytes(target) == LF_TEXT
