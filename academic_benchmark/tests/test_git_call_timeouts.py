"""Every git call of the archive / quarantine code carries the shared timeout and the isolated git
environment, and a git failure is never read as "nothing tracked" / "no changes" (2026-10-15 review
follow-up of P9).

``archive_manifest`` converts git failures into ``QuarantineBlocked`` (or, in ``verify_manifest``, a
reported error); the helpers in ``committed_bytes`` raise ``GitQueryFailed``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

import pytest

import academic_benchmark.archive_manifest as module
import academic_benchmark.committed_bytes as cb
from academic_benchmark.archive_manifest import QuarantineBlocked, quarantine_tracked_tree, verify_manifest

SOURCE_ROOT = PurePosixPath("academic_benchmark/yaem2026")
ARCHIVE_ROOT = PurePosixPath("archive/academic_benchmark/yaem2026_legacy")
LF_TEXT = b"VALUE = 1\nOTHER = 2\n"

FAILURES = [
    subprocess.TimeoutExpired(cmd="git", timeout=1),
    subprocess.CalledProcessError(128, "git", stderr=b"fatal: bad object"),
    FileNotFoundError("git"),
    PermissionError("git"),
]
FAILURE_IDS = ["timeout", "exit-128", "git-missing", "permission"]


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


def _raise_for(monkeypatch, subcommand: str, failure: BaseException) -> list[list[str]]:
    """Make every ``git <subcommand>`` fail with ``failure``; other git calls run for real."""
    real_run = subprocess.run
    seen: list[list[str]] = []

    def fake_run(command, **kwargs):
        if command[0] == "git" and subcommand in command[1:3]:
            seen.append(list(command))
            raise failure
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def _ok(stdout: bytes) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=b"")


QUERIES = [
    lambda root: module._git_paths(root, "ls-files", "-z"),
    lambda root: module._git_directory(root),
    lambda root: module._canonical_repo_root(root),
]
QUERY_IDS = ["_git_paths", "_git_directory", "_canonical_repo_root"]


# --------------------------------------------------------- one shared constant

def test_one_shared_timeout_constant():
    assert cb.GIT_QUERY_TIMEOUT_SECONDS == 120
    assert module._GIT_QUERY_TIMEOUT_SECONDS is cb.GIT_QUERY_TIMEOUT_SECONDS


# --------------------------------------- archive_manifest: timeout + isolation per call

@pytest.mark.parametrize("call", QUERIES, ids=QUERY_IDS)
def test_archive_git_queries_pass_the_shared_timeout_and_the_isolated_environment(tmp_path: Path, monkeypatch, call):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "elsewhere"))
    calls: list[dict] = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return _ok(str(tmp_path.resolve()).encode() + b"\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    call(tmp_path)
    assert calls, "git was not called"
    for kwargs in calls:
        assert kwargs.get("timeout") == cb.GIT_QUERY_TIMEOUT_SECONDS
        assert "GIT_DIR" not in kwargs["env"]


@pytest.mark.parametrize("failure", FAILURES, ids=FAILURE_IDS)
@pytest.mark.parametrize("call", QUERIES, ids=QUERY_IDS)
def test_archive_git_queries_convert_failures_into_quarantine_blocked(tmp_path: Path, monkeypatch, call, failure):
    def fake_run(command, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(QuarantineBlocked, match="cannot"):
        call(tmp_path)


def test_a_failing_ls_files_is_never_an_empty_listing(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    _raise_for(monkeypatch, "ls-files", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(QuarantineBlocked, match="timed out"):
        module.git_tracked_files(repo, SOURCE_ROOT)
    with pytest.raises(QuarantineBlocked, match="timed out"):
        module._git_untracked_files(repo, SOURCE_ROOT)
    with pytest.raises(QuarantineBlocked, match="timed out"):
        module._git_ignored_files(repo, SOURCE_ROOT)


def test_a_timed_out_toplevel_lookup_blocks_the_public_entry_points(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    _raise_for(monkeypatch, "rev-parse", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(QuarantineBlocked, match="timed out"):
        _quarantine(repo)
    assert (repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py").read_bytes() == LF_TEXT
    assert not (repo / "archive").exists()


def test_non_utf8_git_output_is_a_quarantine_block_not_a_raw_decode_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: _ok(b"academic_benchmark/\xff.py\0"))
    with pytest.raises(QuarantineBlocked, match="UTF-8"):
        module._git_paths(tmp_path, "ls-files", "-z")


# ------------------------------------------------- committed_bytes: working_copy_drift

def test_working_copy_drift_times_out_loudly_instead_of_reporting_no_drift(tmp_path: Path, monkeypatch):
    _raise_for(monkeypatch, "diff", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(cb.GitQueryFailed, match="timed out"):
        cb.working_copy_drift(tmp_path)


def test_working_copy_drift_fails_on_an_unexpected_git_exit(tmp_path: Path, monkeypatch):
    _raise_for(monkeypatch, "diff", subprocess.CalledProcessError(128, "git", stderr=b"fatal: detected dubious ownership"))
    with pytest.raises(cb.GitQueryFailed, match="dubious ownership"):
        cb.working_copy_drift(tmp_path)


def test_working_copy_drift_keeps_its_documented_empty_result_outside_a_repository_or_without_git(tmp_path: Path, monkeypatch):
    _raise_for(
        monkeypatch, "diff",
        subprocess.CalledProcessError(128, "git", stderr=b"fatal: not a git repository (or any of the parent directories): .git"),
    )
    assert cb.working_copy_drift(tmp_path) == []
    _raise_for(monkeypatch, "diff", FileNotFoundError("git"))
    assert cb.working_copy_drift(tmp_path) == []


# ------------------------------------------------- committed_bytes: committed_bytes / index_has_blob

def test_committed_bytes_does_not_fall_back_to_disk_when_git_times_out(tmp_path: Path, monkeypatch):
    target = tmp_path / "x.txt"
    target.write_bytes(b"disk bytes\r\n")
    _raise_for(monkeypatch, "cat-file", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(cb.GitQueryFailed, match="timed out"):
        cb.committed_bytes(target)


def test_committed_bytes_does_not_try_further_sources_after_a_timeout(tmp_path: Path, monkeypatch):
    target = tmp_path / "x.txt"
    target.write_bytes(b"disk\n")
    seen = _raise_for(monkeypatch, "cat-file", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(cb.GitQueryFailed):
        cb.committed_bytes(target, fallback_sources=[(tmp_path, "other")])
    assert len(seen) == 1


def test_committed_bytes_does_not_fall_back_on_an_unexpected_exit_status(tmp_path: Path, monkeypatch):
    target = tmp_path / "x.txt"
    target.write_bytes(b"disk\n")
    _raise_for(monkeypatch, "cat-file", subprocess.CalledProcessError(129, "git", stderr=b"usage: git cat-file"))
    with pytest.raises(cb.GitQueryFailed, match="129"):
        cb.committed_bytes(target)


def test_committed_bytes_keeps_the_documented_disk_fallback(tmp_path: Path, monkeypatch, caplog):
    target = tmp_path / "x.txt"
    target.write_bytes(b"disk\r\n")
    # not in the index (git exits 128) and git missing: both stay a warned fallback
    _raise_for(
        monkeypatch, "cat-file",
        subprocess.CalledProcessError(128, "git", stderr=b"fatal: path 'x.txt' exists on disk, but not in the index"),
    )
    assert cb.committed_bytes(target) == b"disk\r\n"
    _raise_for(monkeypatch, "cat-file", FileNotFoundError("git"))
    assert cb.committed_bytes(target) == b"disk\r\n"
    assert "falling back to disk bytes" in caplog.text


def test_index_has_blob_raises_on_timeout_instead_of_answering_false(tmp_path: Path, monkeypatch):
    target = tmp_path / "x.txt"
    target.write_bytes(b"x")
    _raise_for(monkeypatch, "cat-file", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(cb.GitQueryFailed):
        cb.index_has_blob(target)


def test_obsolete_results_manifest_bytes_do_not_fall_back_on_timeout(tmp_path: Path, monkeypatch):
    from academic_benchmark.obsolete_results import _committed_bytes

    target = tmp_path / "x.csv"
    target.write_bytes(b"a,b\r\n")
    _raise_for(monkeypatch, "cat-file", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(cb.GitQueryFailed):
        _committed_bytes(str(target), str(tmp_path))


# ------------------------------------------- verify / quarantine see the failure

@pytest.mark.parametrize("subcommand", ["cat-file", "diff"])
def test_verify_reports_a_git_timeout_instead_of_a_clean_result(tmp_path: Path, monkeypatch, subcommand):
    repo = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)
    archive = repo / Path(*ARCHIVE_ROOT.parts)
    _git(repo, "add", "-A")
    assert verify_manifest(manifest, archive, repo_root=repo) == []
    _raise_for(monkeypatch, subcommand, subprocess.TimeoutExpired(cmd="git", timeout=1))
    errors = verify_manifest(manifest, archive, repo_root=repo)
    assert errors and any("timed out" in error for error in errors)


def test_quarantine_rolls_back_when_reading_the_index_bytes_times_out(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    _raise_for(monkeypatch, "cat-file", subprocess.TimeoutExpired(cmd="git", timeout=1))
    with pytest.raises(QuarantineBlocked, match="timed out"):
        _quarantine(repo)
    assert (repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py").read_bytes() == LF_TEXT
    assert not (repo / "archive").exists()
