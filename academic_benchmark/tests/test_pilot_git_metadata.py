"""Benchmark provenance (``fair_pilot._git_metadata``, shared by the fair and native pilots) asks
git with the shared timeout and the isolated git environment, and a failure is recorded as
"unknown" (null revision, null dirty) with the reason, never as a clean tree (2026-10-15)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import academic_benchmark.fair_pilot as fair_pilot
import academic_benchmark.native_pilot as native_pilot
from academic_benchmark.committed_bytes import GIT_QUERY_TIMEOUT_SECONDS

FAILURES = [
    (subprocess.TimeoutExpired(cmd="git", timeout=1), "timeout"),
    (subprocess.CalledProcessError(128, "git", stderr=b"fatal: not a git repository"), "exit"),
    (FileNotFoundError("git"), "unavailable"),
    (PermissionError("git"), "unavailable"),
]
FAILURE_IDS = ["timeout", "exit", "git-missing", "permission"]


def _git(cwd: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True,
    ).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "first")
    return repo


def _completed(stdout: bytes) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["git"], 0, stdout=stdout, stderr=b"")


@pytest.mark.parametrize(("failure", "kind"), FAILURES, ids=FAILURE_IDS)
def test_first_git_call_failure_is_unknown_with_reason(monkeypatch, tmp_path, failure, kind):
    def fake_run(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert fair_pilot._git_metadata(tmp_path) == {"revision": None, "dirty": None, "git_error": kind}


@pytest.mark.parametrize(("failure", "kind"), FAILURES, ids=FAILURE_IDS)
def test_status_failure_after_revision_is_not_recorded_as_clean(monkeypatch, tmp_path, failure, kind):
    calls = []

    def fake_run(command, *args, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return _completed(b"a" * 40 + b"\n")
        raise failure

    monkeypatch.setattr(subprocess, "run", fake_run)
    metadata = fair_pilot._git_metadata(tmp_path)
    assert len(calls) == 2
    assert metadata["dirty"] is None
    assert metadata["dirty"] is not False
    assert metadata == {"revision": None, "dirty": None, "git_error": kind}


def test_every_git_call_has_the_shared_timeout_and_isolated_environment(monkeypatch, tmp_path):
    for variable in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.setenv(variable, str(tmp_path / "elsewhere"))
    seen = []

    def fake_run(command, *args, **kwargs):
        seen.append((command, kwargs))
        return _completed(b"b" * 40 + b"\n" if "rev-parse" in command else b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert fair_pilot._git_metadata(tmp_path) == {"revision": "b" * 40, "dirty": False}
    assert len(seen) == 2
    for _command, kwargs in seen:
        assert kwargs.get("timeout") == GIT_QUERY_TIMEOUT_SECONDS
        environment = kwargs.get("env")
        assert environment is not None
        assert not {"GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"} & set(environment)


def test_real_repository_clean_then_dirty(tmp_path):
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD").decode().strip()
    assert fair_pilot._git_metadata(repo) == {"revision": head, "dirty": False}
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    assert fair_pilot._git_metadata(repo) == {"revision": head, "dirty": True}


def test_real_repository_ignores_inherited_git_dir(monkeypatch, tmp_path):
    repo = _repo(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q")
    head = _git(repo, "rev-parse", "HEAD").decode().strip()
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    assert fair_pilot._git_metadata(repo) == {"revision": head, "dirty": False}


def test_real_directory_outside_a_repository_is_unknown_not_clean(monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    metadata = fair_pilot._git_metadata(outside)
    assert metadata == {"revision": None, "dirty": None, "git_error": "exit"}


def test_native_pilot_shares_the_same_provenance_function():
    assert native_pilot._git_metadata is fair_pilot._git_metadata
