"""Polish items P8 and P9 of the archive-manifest review (2026-10-15).

P8: an archive path that git does not track, while its pre-move original path is still in the index,
    must not verify as clean outside a quarantine run (the bytes at the archive path cannot be checked).
P9: ``_uncommitted_changes`` must time out and fail closed with the module's own error type.
"""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

import pytest

import academic_benchmark.archive_manifest as module
from academic_benchmark.archive_manifest import QuarantineBlocked, quarantine_tracked_tree, verify_manifest

SOURCE_ROOT = PurePosixPath("academic_benchmark/yaem2026")
ARCHIVE_ROOT = PurePosixPath("archive/academic_benchmark/yaem2026_legacy")
LF_TEXT = b"VALUE = 1\nOTHER = 2\n"


def _git(cwd: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True,
    ).stdout


def _committed_source_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    source = repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(LF_TEXT)
    _git(repo, "init")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source")
    return repo


def _quarantine(repo: Path):
    return quarantine_tracked_tree(
        repo_root=repo, source_root=SOURCE_ROOT, archive_root=ARCHIVE_ROOT, archive_id="yaem2026_legacy"
    )


# ---------------------------------------------------------------- P8

def test_verify_reports_an_untracked_archive_file_whose_original_path_is_tracked(tmp_path: Path):
    repo = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)  # moved, nothing staged: archive untracked, original still in the index
    archive = repo / Path(*ARCHIVE_ROOT.parts)

    errors = verify_manifest(manifest, archive, repo_root=repo)

    assert errors == ["archive file not tracked in git (stage it): core/solver.py"]


def test_verify_is_clean_once_the_archive_is_staged_or_committed(tmp_path: Path):
    repo = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)
    archive = repo / Path(*ARCHIVE_ROOT.parts)
    _git(repo, "add", "-A")
    assert verify_manifest(manifest, archive, repo_root=repo) == []
    _git(repo, "commit", "-m", "archive")
    assert verify_manifest(manifest, archive, repo_root=repo) == []


def test_quarantine_run_itself_still_succeeds_before_anything_is_staged(tmp_path: Path):
    """The end-of-run verification inside quarantine_tracked_tree sees the unstaged state by design."""
    repo = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)  # would raise QuarantineBlocked if the strict check ran in the quarantine
    assert len(manifest.entries) == 1
    assert (repo / Path(*ARCHIVE_ROOT.parts) / "core" / "solver.py").read_bytes() == LF_TEXT


def test_the_explicit_quarantine_state_flag_keeps_the_lenient_behaviour(tmp_path: Path):
    repo = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)
    archive = repo / Path(*ARCHIVE_ROOT.parts)
    assert verify_manifest(manifest, archive, repo_root=repo, allow_unstaged_archive=True) == []


# ---------------------------------------------------------------- P9

def _completed(returncode: int = 0, stdout: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=b"")


def test_uncommitted_changes_passes_a_timeout_and_the_isolated_git_environment(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "elsewhere"))
    calls: list[dict] = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return _completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module._uncommitted_changes(tmp_path, SOURCE_ROOT) == []
    assert len(calls) == 2  # rev-parse HEAD, then diff
    for kwargs in calls:
        assert kwargs.get("timeout") and kwargs["timeout"] > 0
        assert "GIT_DIR" not in kwargs["env"]


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired(cmd="git", timeout=1),
        FileNotFoundError("git"),
        PermissionError("git"),
    ],
    ids=["timeout", "git-missing", "permission"],
)
@pytest.mark.parametrize("failing_step", ["rev-parse", "diff"])
def test_uncommitted_changes_converts_git_failures_into_quarantine_blocked(tmp_path: Path, monkeypatch, failure, failing_step):
    def fake_run(command, **kwargs):
        if command[1] == failing_step:
            raise failure
        return _completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    with pytest.raises(QuarantineBlocked, match="uncommitted state"):
        module._uncommitted_changes(tmp_path, SOURCE_ROOT)


def test_uncommitted_changes_converts_a_failing_diff_exit_status(tmp_path: Path, monkeypatch):
    def fake_run(command, **kwargs):
        if command[1] == "diff":
            raise subprocess.CalledProcessError(128, command, stderr=b"fatal: bad object")
        return _completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    with pytest.raises(QuarantineBlocked, match="uncommitted state"):
        module._uncommitted_changes(tmp_path, SOURCE_ROOT)


def test_quarantine_refuses_and_moves_nothing_when_git_diff_times_out(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    real_run = subprocess.run

    def flaky_run(command, **kwargs):
        if command[:2] == ["git", "diff"]:
            raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 0))
        return real_run(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", flaky_run)
    with pytest.raises(QuarantineBlocked, match="uncommitted state"):
        _quarantine(repo)
    assert (repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py").read_bytes() == LF_TEXT
    assert not (repo / "archive").exists()
