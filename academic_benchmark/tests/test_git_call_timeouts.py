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


def test_working_copy_drift_fails_on_an_unexpected_git_exit_inside_a_repository(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    _raise_for(monkeypatch, "diff", subprocess.CalledProcessError(128, "git", stderr=b"fatal: bad object"))
    with pytest.raises(cb.GitQueryFailed, match="bad object"):
        cb.working_copy_drift(repo)


def test_working_copy_drift_keeps_its_documented_empty_result_without_git(tmp_path: Path, monkeypatch):
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


# ------------------------------------- real git: what git does when it cannot trust a directory
# GIT_TEST_ASSUME_DIFFERENT_OWNER=1 makes git refuse a repository as "dubious ownership". ``git diff``
# then exits 129 with "Not a git repository" (the SAME words as for a real non-repository) and
# ``git cat-file`` exits 128: the exit status and the message alone cannot tell the two apart, so the
# code asks ``git rev-parse --git-dir`` first (review round 1, 2026-10-15).

def _distrusted(monkeypatch, tmp_path: Path):
    """Make git refuse every repository as "dubious ownership", whatever the machine's git configuration says.

    The switch alone is not enough: a ``safe.directory = *`` in the system or global git configuration (GitHub's Ubuntu runners
    have one) trusts every directory again, and the three tests below then saw no refusal (nightly CI failure 2026-10-23..27).
    The global file is therefore replaced by an empty one, the system file is skipped and configuration passed through the
    environment is dropped, so the only source of ``safe.directory`` is the test's own (none)."""
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key in ("GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")


def test_the_dubious_ownership_switch_reaches_git_through_the_isolated_environment(monkeypatch, tmp_path: Path):
    _distrusted(monkeypatch, tmp_path)
    assert cb.git_environment()["GIT_TEST_ASSUME_DIFFERENT_OWNER"] == "1"


def test_a_global_safe_directory_wildcard_does_not_hide_the_distrust_setup(tmp_path: Path, monkeypatch):
    # what a CI runner has: every directory trusted by the global configuration
    trusting = tmp_path / "trusting.gitconfig"
    trusting.write_text("[safe]\n\tdirectory = *\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(trusting))
    repo = _committed_source_repo(tmp_path)
    assert cb.index_has_blob(repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py") is True
    _distrusted(monkeypatch, tmp_path)
    with pytest.raises(cb.GitQueryFailed, match="dubious ownership"):
        cb.index_has_blob(repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py")


def test_working_copy_drift_never_reports_no_drift_for_a_repository_git_distrusts(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    (repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py").write_bytes(b"VALUE = 999\n")  # a real hand edit
    assert cb.working_copy_drift(repo / Path(*SOURCE_ROOT.parts)) == ["core/solver.py"]  # git can see it
    _distrusted(monkeypatch, tmp_path)
    with pytest.raises(cb.GitQueryFailed, match="dubious ownership"):
        cb.working_copy_drift(repo / Path(*SOURCE_ROOT.parts))


def test_committed_bytes_and_index_has_blob_do_not_fall_back_for_a_repository_git_distrusts(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    target = repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py"
    assert cb.index_has_blob(target) is True
    _distrusted(monkeypatch, tmp_path)
    with pytest.raises(cb.GitQueryFailed, match="dubious ownership"):
        cb.committed_bytes(target)
    with pytest.raises(cb.GitQueryFailed, match="dubious ownership"):
        cb.index_has_blob(target)


def test_verify_manifest_is_never_clean_for_a_repository_git_distrusts(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    manifest = _quarantine(repo)
    archive = repo / Path(*ARCHIVE_ROOT.parts)
    _git(repo, "add", "-A")
    (archive / "core" / "solver.py").write_bytes(b"VALUE = 999\n")  # hand-edited archive file
    _distrusted(monkeypatch, tmp_path)
    errors = verify_manifest(manifest, archive, repo_root=repo)
    assert errors and all("cannot" in error for error in errors)


def test_a_real_non_repository_keeps_the_documented_results(tmp_path: Path, caplog):
    plain = tmp_path / "plain"
    plain.mkdir()
    target = plain / "x.txt"
    target.write_bytes(b"disk\r\n")
    assert cb.working_copy_drift(plain) == []
    assert cb.index_has_blob(target) is False
    assert cb.committed_bytes(target) == b"disk\r\n"
    assert "falling back to disk bytes" in caplog.text


def test_an_untracked_file_in_a_real_repository_keeps_the_disk_fallback(tmp_path: Path):
    repo = _committed_source_repo(tmp_path)
    loose = repo / "loose.txt"
    loose.write_bytes(b"disk\r\n")
    assert cb.index_has_blob(loose) is False
    assert cb.committed_bytes(loose) == b"disk\r\n"


def test_a_corrupt_index_inside_a_repository_is_not_read_as_not_in_the_index(tmp_path: Path):
    repo = _committed_source_repo(tmp_path)
    target = repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py"
    (repo / ".git" / "index").write_bytes(b"garbage")
    with pytest.raises(cb.GitQueryFailed, match="index"):
        cb.committed_bytes(target)
    with pytest.raises(cb.GitQueryFailed, match="index"):
        cb.index_has_blob(target)
    with pytest.raises(cb.GitQueryFailed, match="index"):
        cb.working_copy_drift(repo)


def test_a_corrupt_dot_git_is_not_read_as_not_a_repository(tmp_path: Path):
    repo = _committed_source_repo(tmp_path)
    target = repo / Path(*SOURCE_ROOT.parts) / "core" / "solver.py"
    (repo / ".git" / "HEAD").write_bytes(b"garbage\n")  # git now answers "not a git repository"
    with pytest.raises(cb.GitQueryFailed, match="not recognise"):
        cb.working_copy_drift(repo)
    with pytest.raises(cb.GitQueryFailed, match="not recognise"):
        cb.committed_bytes(target)


def test_the_repository_probe_is_cached_per_directory(tmp_path: Path, monkeypatch):
    repo = _committed_source_repo(tmp_path)
    folder = repo / "loose"
    folder.mkdir()
    files = []
    for name in ("a.txt", "b.txt", "c.txt"):
        (folder / name).write_bytes(b"disk\n")
        files.append(folder / name)
    real_run = subprocess.run
    probes: list[list[str]] = []

    def counting_run(command, **kwargs):
        if command[:3] == ["git", "rev-parse", "--git-dir"]:
            probes.append(list(command))
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", counting_run)
    cache: dict = {}
    for item in files:  # untracked everywhere: every lookup fails with exit 128 and needs the probe
        assert cb.committed_bytes(item, repository_cache=cache) == b"disk\n"
    assert len(probes) == 1
