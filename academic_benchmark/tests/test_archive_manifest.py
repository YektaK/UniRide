from __future__ import annotations

import json
import subprocess
from pathlib import Path, PurePosixPath

import pytest

from academic_benchmark.archive_manifest import (
    EvidenceClass,
    QuarantineBlocked,
    build_manifest,
    classify_bildiri_evidence,
    classify_yaem_evidence,
    main,
    quarantine_tracked_tree,
    scan_sensitive_file,
    verify_manifest,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("results/reports/FINAL_ANALYSIS.md", EvidenceClass.INVALID),
        ("results/benchmark_student_matrix.csv", EvidenceClass.INVALID),
        ("results/histories/convergence_eil51.json", EvidenceClass.HISTORICAL_UNVERIFIED),
        ("archive_20260701_0120/results/plots/eil51.png", EvidenceClass.HISTORICAL_UNVERIFIED),
        ("core/gwo_solver.py", EvidenceClass.REFERENCE_ONLY),
        ("data/student_matrix.json", EvidenceClass.REFERENCE_ONLY),
        ("yaem2026_sunum_slayt_sablonu.md", EvidenceClass.REFERENCE_ONLY),
    ],
)
def test_yaem_evidence_classification(path: str, expected: EvidenceClass):
    assert classify_yaem_evidence(PurePosixPath(path)) is expected


def test_sensitive_scan_never_returns_secret_value(tmp_path: Path):
    secret = "ghp_" + "A" * 36
    path = tmp_path / "settings.py"
    path.write_text(f'TOKEN = "{secret}"\n', encoding="utf-8")
    findings = scan_sensitive_file(path)
    assert [(finding.rule, finding.severity, finding.line) for finding in findings] == [
        ("github_token", "confirmed", 1)
    ]
    assert secret not in repr(findings)


def test_ambiguous_assignment_is_high_risk_without_secret_echo(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text('{"api_key": "long-non-placeholder-value-123456"}', encoding="utf-8")
    finding = scan_sensitive_file(path)[0]
    assert finding.rule == "credential_assignment"
    assert finding.severity == "ambiguous"
    assert "long-non-placeholder" not in repr(finding)


def test_manifest_hashes_archived_bytes_and_detects_tampering(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "core").mkdir(parents=True)
    (archive / "core" / "solver.py").write_text("print('legacy')\n", encoding="utf-8")
    manifest = build_manifest(
        archive_id="yaem2026_legacy",
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archived_root=archive,
        original_paths=[PurePosixPath("core/solver.py")],
        withheld=[],
    )
    assert verify_manifest(manifest, archive) == []
    (archive / "core" / "solver.py").write_text("tampered\n", encoding="utf-8")
    assert verify_manifest(manifest, archive) == ["size mismatch: core/solver.py"]

@pytest.mark.parametrize("name", [".env", ".env.local", "settings.js"])
def test_sensitive_scan_recognizes_dotenv_and_text_code_files(tmp_path: Path, name: str):
    path = tmp_path / name
    path.write_text('api_key = "long-literal-value-123456"\n', encoding="utf-8")
    assert [(finding.rule, finding.severity) for finding in scan_sensitive_file(path)] == [
        ("credential_assignment", "ambiguous")
    ]


def test_sensitive_scan_allows_value_expression_but_not_comment_masking(tmp_path: Path):
    path = tmp_path / "settings.py"
    path.write_text(
        'api_key = os.environ["API_KEY"]\n# os.environ\napi_key = "long-literal-value-123456"\n',
        encoding="utf-8",
    )
    findings = scan_sensitive_file(path)
    assert [(finding.rule, finding.line) for finding in findings] == [
        ("credential_assignment", 3)
    ]


@pytest.mark.parametrize("placeholder", ["placeholder" * 3, "YOUR_API_KEY_HERE_123456"])
def test_sensitive_scan_skips_complete_long_placeholder_values(tmp_path: Path, placeholder: str):
    path = tmp_path / ".env"
    path.write_text(f'api_key = "{placeholder}"\n', encoding="utf-8")
    assert scan_sensitive_file(path) == []


def test_verify_manifest_reports_size_mismatch_before_hashing(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "core").mkdir(parents=True)
    archived = archive / "core" / "solver.py"
    archived.write_text("legacy\n", encoding="utf-8")
    manifest = build_manifest(
        archive_id="yaem2026_legacy",
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archived_root=archive,
        original_paths=[PurePosixPath("core/solver.py")],
        withheld=[],
    )
    archived.write_text("changed length\n", encoding="utf-8")
    assert verify_manifest(manifest, archive) == ["size mismatch: core/solver.py"]


@pytest.mark.parametrize("relative", [PurePosixPath("/absolute.py"), PurePosixPath("../escape.py")])
def test_build_manifest_rejects_invalid_paths_before_file_access(tmp_path: Path, relative: PurePosixPath):
    with pytest.raises(ValueError, match="repository-relative"):
        build_manifest(
            archive_id="yaem2026_legacy",
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
            archived_root=tmp_path,
            original_paths=[relative],
            withheld=[],
        )


def test_verify_manifest_uses_archive_path_and_returns_mapping_errors(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "renamed").mkdir(parents=True)
    archived = archive / "renamed" / "solver.py"
    archived.write_text("legacy\n", encoding="utf-8")
    manifest = __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveManifest"]).ArchiveManifest(
        schema_version="uniride-archive/v1",
        archive_id="yaem2026_legacy",
        source_root="academic_benchmark/yaem2026",
        archive_root="archive/yaem2026_legacy",
        entries=[
            __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveEntry"]).ArchiveEntry(
                original_path="academic_benchmark/yaem2026/core/solver.py",
                archive_path="archive/yaem2026_legacy/renamed/solver.py",
                byte_size=archived.stat().st_size,
                sha256=__import__("hashlib").sha256(archived.read_bytes()).hexdigest(),
                classification=EvidenceClass.REFERENCE_ONLY,
            ),
            __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveEntry"]).ArchiveEntry(
                original_path="outside/source.py",
                archive_path="archive/yaem2026_legacy/outside.py",
                byte_size=0,
                sha256="0" * 64,
                classification=EvidenceClass.REFERENCE_ONLY,
            ),
            __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveEntry"]).ArchiveEntry(
                original_path="academic_benchmark/yaem2026/core/mapped.py",
                archive_path="other/mapped.py",
                byte_size=0,
                sha256="0" * 64,
                classification=EvidenceClass.REFERENCE_ONLY,
            ),
            __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveEntry"]).ArchiveEntry(
                original_path="academic_benchmark/yaem2026/private.env",
                archive_path=None,
                byte_size=0,
                sha256="0" * 64,
                classification=EvidenceClass.WITHHELD_SENSITIVE,
            ),
        ],
    )
    assert verify_manifest(manifest, archive) == [
        "original path outside source root: outside/source.py",
        "archive path outside archive root: other/mapped.py",
    ]

@pytest.mark.parametrize(
    "relative",
    [PurePosixPath(r"C:\\secret.txt"), PurePosixPath("C:/secret.txt"), PurePosixPath(r"..\\secret.txt")],
)
def test_build_manifest_rejects_windows_unsafe_paths_before_file_access(tmp_path: Path, relative: PurePosixPath):
    with pytest.raises(ValueError, match="repository-relative"):
        build_manifest(
            archive_id="yaem2026_legacy",
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
            archived_root=tmp_path,
            original_paths=[relative],
            withheld=[],
        )


def test_verify_manifest_rejects_unsafe_archive_path_without_file_access(tmp_path: Path):
    archive_entry = __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveEntry"]).ArchiveEntry.model_construct(
        original_path="academic_benchmark/yaem2026/core/solver.py",
        archive_path=r"..\\secret.txt",
        byte_size=0,
        sha256="0" * 64,
        classification=EvidenceClass.REFERENCE_ONLY,
    )
    manifest = __import__("academic_benchmark.archive_manifest", fromlist=["ArchiveManifest"]).ArchiveManifest.model_construct(
        schema_version="uniride-archive/v1",
        archive_id="yaem2026_legacy",
        source_root="academic_benchmark/yaem2026",
        archive_root="archive/yaem2026_legacy",
        entries=[archive_entry],
    )
    assert verify_manifest(manifest, tmp_path / "does-not-exist") == [
        r"unsafe archive path: ..\\secret.txt"
    ]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _legacy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    source = repo / "academic_benchmark" / "yaem2026"
    (source / "core").mkdir(parents=True)
    (source / "results" / "reports").mkdir(parents=True)
    (source / "core" / "solver.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "results" / "reports" / "analysis.md").write_text("legacy\n", encoding="utf-8")
    (source / "ignored.pyc").write_bytes(b"cache")
    (repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "add", ".gitignore", "academic_benchmark/yaem2026/core/solver.py", "academic_benchmark/yaem2026/results/reports/analysis.md")
    return repo


def test_quarantine_moves_only_tracked_files_and_writes_reproducible_manifest(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    manifest = quarantine_tracked_tree(
        repo_root=repo,
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archive_id="yaem2026_legacy",
    )
    archive = repo / "archive" / "academic_benchmark" / "yaem2026_legacy"
    assert (archive / "core" / "solver.py").is_file()
    assert (archive / "results" / "reports" / "analysis.md").is_file()
    assert not (archive / "ignored.pyc").exists()
    assert not (repo / "academic_benchmark" / "yaem2026" / "ignored.pyc").exists()
    assert verify_manifest(manifest, archive) == []
    assert json.loads((archive / "manifest.json").read_text(encoding="utf-8"))["entries"]


def test_ambiguous_sensitive_match_aborts_before_any_move(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    risky = repo / "academic_benchmark" / "yaem2026" / "config.json"
    risky.write_text('{"api_key": "ambiguous-real-looking-value-123"}', encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/config.json")
    with pytest.raises(QuarantineBlocked, match="ambiguous high-risk match"):
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"), archive_id="yaem2026_legacy")
    assert risky.is_file()
    assert not (repo / "archive").exists()


def test_confirmed_secret_is_withheld_without_secret_content(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    secret = "ghp_" + "A" * 36
    risky = repo / "academic_benchmark" / "yaem2026" / "credential.txt"
    risky.write_text(secret, encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/credential.txt")
    manifest = quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"), archive_id="yaem2026_legacy")
    entry = next(item for item in manifest.entries if item.original_path.endswith("credential.txt"))
    assert entry.classification is EvidenceClass.WITHHELD_SENSITIVE
    assert entry.archive_path is None
    assert not risky.exists()
    assert secret not in (repo / "archive" / "academic_benchmark" / "yaem2026_legacy" / "manifest.json").read_text(encoding="utf-8")


def test_untracked_user_file_blocks_without_mutation(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    note = repo / "academic_benchmark" / "yaem2026" / "local-note.bin"
    note.write_bytes(b"user data")
    with pytest.raises(QuarantineBlocked, match="untracked non-ignored"):
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"), archive_id="yaem2026_legacy")
    assert note.is_file()
    assert not (repo / "archive").exists()


def test_manifest_failure_restores_moved_and_withheld_files(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as archive_module

    repo = _legacy_repo(tmp_path)
    secret = "ghp_" + "A" * 36
    credential = repo / "academic_benchmark" / "yaem2026" / "credential.txt"
    credential.write_text(secret, encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/credential.txt")

    def fail_write(*args, **kwargs):
        raise OSError("simulated manifest failure")

    monkeypatch.setattr(archive_module, "write_manifest", fail_write)
    with pytest.raises(OSError, match="simulated manifest failure"):
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"), archive_id="yaem2026_legacy")
    assert credential.read_text(encoding="utf-8") == secret
    assert (repo / "academic_benchmark" / "yaem2026" / "core" / "solver.py").is_file()
    assert not (repo / "archive").exists()


def test_cli_help_lists_transaction_subcommands(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--help"])
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert all(command in output for command in ("scan", "quarantine", "verify"))

def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("source_root", "archive_root", "message"),
    [
        (".git", "archive/legacy", ".git"),
        ("academic_benchmark/yaem2026", ".git/legacy", ".git"),
        ("academic_benchmark/yaem2026", "academic_benchmark/yaem2026/archive", "overlap"),
    ],
)
def test_quarantine_rejects_git_and_overlapping_roots_before_mutation(
    tmp_path: Path, source_root: str, archive_root: str, message: str
):
    repo = _legacy_repo(tmp_path)
    before = _snapshot_tree(repo)
    with pytest.raises(QuarantineBlocked, match=message):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath(source_root),
            archive_root=PurePosixPath(archive_root),
            archive_id="legacy",
        )
    assert _snapshot_tree(repo) == before


def test_quarantine_rejects_repo_root_that_is_not_git_toplevel(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    with pytest.raises(QuarantineBlocked, match="git toplevel"):
        quarantine_tracked_tree(
            repo_root=repo / "academic_benchmark",
            source_root=PurePosixPath("yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
        )


def test_ignored_non_cache_data_inside_cache_named_directory_blocks(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    cache_data = repo / "academic_benchmark" / "yaem2026" / ".numba_cache" / "note.txt"
    cache_data.parent.mkdir()
    cache_data.write_text("must not be deleted", encoding="utf-8")
    (repo / ".gitignore").write_text("*.pyc\n.numba_cache/\n", encoding="utf-8")
    with pytest.raises(QuarantineBlocked, match="ignored non-cache"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
        )
    assert cache_data.read_text(encoding="utf-8") == "must not be deleted"


def test_ignored_database_evidence_blocks_without_mutating_bytes(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    database = source / "research-evidence.db"
    database.write_bytes(b"SQLite format 3\x00user evidence\xff")
    (repo / ".gitignore").write_text("*.pyc\n*.db\n", encoding="utf-8")
    before = _snapshot_tree(source)

    with pytest.raises(QuarantineBlocked, match="ignored non-cache"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
        )

    assert _snapshot_tree(source) == before
    assert database.read_bytes() == b"SQLite format 3\x00user evidence\xff"
    assert not (repo / "archive").exists()


def test_keyboard_interrupt_restores_files_and_staged_caches(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as archive_module

    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    before = _snapshot_tree(source)

    def interrupt_after_cache_stage(_source_root: Path) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(archive_module, "_prune_empty_directories", interrupt_after_cache_stage)
    with pytest.raises(KeyboardInterrupt):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
        )
    assert _snapshot_tree(source) == before
    assert not (repo / "archive").exists()


def test_cli_validation_error_is_redacted(tmp_path: Path, capsys):
    repo = _legacy_repo(tmp_path)
    manifest = repo / "manifest.json"
    sentinel = "CLI_SECRET_SENTINEL"
    manifest.write_text('{"archive_id": "' + sentinel + '"}', encoding="utf-8")
    assert main(["verify", "--repo-root", str(repo), "--manifest", "manifest.json"]) == 2
    output = capsys.readouterr()
    assert sentinel not in output.out
    assert sentinel not in output.err
    assert output.err.startswith("manifest validation failed:")


def test_quarantine_rejects_symlinked_tracked_entry_when_supported(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    target = tmp_path / "outside.py"
    target.write_text("outside\n", encoding="utf-8")
    linked = source / "core" / "solver.py"
    linked.unlink()
    try:
        linked.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(QuarantineBlocked, match="reparse"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
        )

def test_failed_move_back_retains_destination_and_backup(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    original_replace = Path.replace
    calls = 0

    def fail_move_back(self: Path, target: Path):
        nonlocal calls
        if self.is_relative_to(repo / "archive") and target.is_relative_to(source):
            calls += 1
            raise OSError("injected move-back failure")
        return original_replace(self, target)

    monkeypatch.setattr(module, "write_manifest", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("trigger rollback")))
    monkeypatch.setattr(Path, "replace", fail_move_back)
    with pytest.raises(QuarantineBlocked, match="recovery incomplete; backup retained") as raised:
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")
    assert calls
    assert (repo / "archive" / "legacy" / "core" / "solver.py").is_file()
    assert "VALUE = 1" not in str(raised.value)


def test_cli_verify_uses_safe_verify_and_reports_success(tmp_path: Path, monkeypatch, capsys):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    called = False

    def safe_verify(repo_root: Path, manifest_path: Path):
        nonlocal called
        called = True
        return module.ArchiveManifest.model_construct(entries=[]), repo, []

    monkeypatch.setattr(module, "_safe_verify_manifest", safe_verify)
    assert main(["verify", "--repo-root", str(repo), "--manifest", "manifest.json"]) == 0
    assert called
    assert capsys.readouterr().out == "verified 0 entries\n"

def _directory_snapshot(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()}


def test_partial_prune_failure_restores_original_empty_directories(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    (source / "empty" / "nested").mkdir(parents=True)
    before_files = _snapshot_tree(source)
    before_directories = _directory_snapshot(source)
    original = module._prune_empty_directories

    def prune_then_fail(root: Path) -> None:
        original(root)
        raise OSError("injected post-prune failure")

    monkeypatch.setattr(module, "_prune_empty_directories", prune_then_fail)
    with pytest.raises(OSError, match="injected post-prune failure"):
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")
    assert _snapshot_tree(source) == before_files
    assert _directory_snapshot(source) == before_directories


def test_backup_cleanup_failure_after_rollback_warns_without_masking_original(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    monkeypatch.setattr(module, "write_manifest", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("original failure")))
    original_rmtree = module.shutil.rmtree

    def fail_backup_cleanup(path: Path, *args, **kwargs):
        if Path(path).name.startswith("uniride-quarantine-"):
            raise OSError("cleanup failure")
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(module.shutil, "rmtree", fail_backup_cleanup)
    with pytest.warns(RuntimeWarning, match="backup retained"):
        with pytest.raises(OSError, match="original failure"):
            quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")


def test_backup_cleanup_failure_after_commit_warns_but_returns_manifest(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    original_rmtree = module.shutil.rmtree

    def fail_backup_cleanup(path: Path, *args, **kwargs):
        if Path(path).name.startswith("uniride-quarantine-"):
            raise OSError("cleanup failure")
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(module.shutil, "rmtree", fail_backup_cleanup)
    with pytest.warns(RuntimeWarning, match="backup retained"):
        manifest = quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")
    assert manifest.entries
    assert (repo / "archive" / "legacy" / "manifest.json").is_file()

def test_directory_restore_failure_is_collected_and_retains_recovery(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    (source / "empty" / "nested").mkdir(parents=True)
    monkeypatch.setattr(module, "_prune_empty_directories", lambda root: (_ for _ in ()).throw(OSError("trigger rollback")))
    original_mkdir = Path.mkdir

    def fail_empty_restore(self: Path, *args, **kwargs):
        if self.name == "empty":
            raise OSError("directory restore failure")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_empty_restore)
    with pytest.raises(QuarantineBlocked, match="recovery incomplete; backup retained"):
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")


def test_empty_symlink_directory_blocks_before_mutation_when_supported(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    target = tmp_path / "outside-dir"
    target.mkdir()
    linked = source / "empty-link"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")
    with pytest.raises(QuarantineBlocked, match="reparse"):
        quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")


@pytest.mark.parametrize("after_commit", [False, True])
def test_backup_retention_warning_never_raises_when_warnings_are_errors(tmp_path: Path, monkeypatch, after_commit: bool):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    if not after_commit:
        monkeypatch.setattr(module, "write_manifest", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("original failure")))
    original_rmtree = module.shutil.rmtree
    monkeypatch.setattr(module.shutil, "rmtree", lambda path, *args, **kwargs: (_ for _ in ()).throw(OSError("cleanup")) if Path(path).name.startswith("uniride-quarantine-") else original_rmtree(path, *args, **kwargs))
    with pytest.MonkeyPatch.context() as context:
        context.setattr(module.warnings, "warn", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeWarning("warnings error")))
        if after_commit:
            assert quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy").entries
        else:
            with pytest.raises(OSError, match="original failure"):
                quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")


def test_non_ascii_repository_path_quarantine(tmp_path: Path):
    repo = _legacy_repo(tmp_path / "café")
    manifest = quarantine_tracked_tree(repo_root=repo, source_root=PurePosixPath("academic_benchmark/yaem2026"), archive_root=PurePosixPath("archive/legacy"), archive_id="legacy")
    assert manifest.entries

def test_cli_verify_redacts_archive_path_outside_mapping_without_file_access(tmp_path: Path, monkeypatch, capsys):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    sentinel = "CLI_MAPPING_SECRET_SENTINEL"
    entry = module.ArchiveEntry(
        original_path="academic_benchmark/yaem2026/core/solver.py",
        archive_path=f"outside/{sentinel}",
        byte_size=0,
        sha256="0" * 64,
        classification=EvidenceClass.REFERENCE_ONLY,
    )
    manifest = module.ArchiveManifest(schema_version="uniride-archive/v1", archive_id="legacy", source_root="academic_benchmark/yaem2026", archive_root="archive/legacy", entries=[entry])
    (repo / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(module, "sha256_file", lambda path: (_ for _ in ()).throw(AssertionError("unexpected filesystem access")))
    assert main(["verify", "--repo-root", str(repo), "--manifest", "manifest.json"]) == 1
    output = capsys.readouterr()
    assert output.err == "manifest mapping error\n"
    assert sentinel not in output.err


# --- Task 7: Generalize Safe Archive Classification and Includes ---


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("results/student_matrix_output.csv", EvidenceClass.INVALID),
        ("results/student_matrix_v2.csv", EvidenceClass.INVALID),
        ("results/benchmark_results.json", EvidenceClass.HISTORICAL_UNVERIFIED),
        ("tuned_parameters_db.json", EvidenceClass.HISTORICAL_UNVERIFIED),
        ("src/gwo_solver.py", EvidenceClass.REFERENCE_ONLY),
        ("paper/bildiri_2026.pdf", EvidenceClass.REFERENCE_ONLY),
        ("README.md", EvidenceClass.REFERENCE_ONLY),
    ],
)
def test_bildiri_evidence_classification(path: str, expected: EvidenceClass):
    assert classify_bildiri_evidence(PurePosixPath(path)) is expected


def test_build_manifest_accepts_injected_classifier(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "core").mkdir(parents=True)
    (archive / "core" / "solver.py").write_text("print('legacy')\n", encoding="utf-8")

    def custom_classifier(path: PurePosixPath) -> EvidenceClass:
        return EvidenceClass.REFERENCE_ONLY

    manifest = build_manifest(
        archive_id="test_profile",
        source_root=PurePosixPath("academic_benchmark/test"),
        archive_root=PurePosixPath("archive/test"),
        archived_root=archive,
        original_paths=[PurePosixPath("core/solver.py")],
        withheld=[],
        classifier=custom_classifier,
    )
    assert manifest.entries[0].classification is EvidenceClass.REFERENCE_ONLY


def test_build_manifest_defaults_to_yaem_classifier(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "results" / "reports").mkdir(parents=True)
    (archive / "results" / "reports" / "analysis.md").write_text("report\n", encoding="utf-8")

    manifest = build_manifest(
        archive_id="yaem2026_legacy",
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/yaem2026_legacy"),
        archived_root=archive,
        original_paths=[PurePosixPath("results/reports/analysis.md")],
        withheld=[],
    )
    assert manifest.entries[0].classification is EvidenceClass.INVALID


def test_quarantine_tracked_tree_with_include_paths(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    extra = repo / "academic_benchmark" / "yaem2026" / "extra"
    extra.mkdir()
    (extra / "data.json").write_text('{"key": "value"}', encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/extra/data.json")

    manifest = quarantine_tracked_tree(
        repo_root=repo,
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archive_id="yaem2026_legacy",
        include_paths=[PurePosixPath("core/solver.py")],
    )
    archived_files = {entry.original_path for entry in manifest.entries}
    assert any("core/solver.py" in path for path in archived_files)
    assert not any("extra/data.json" in path for path in archived_files)


def test_quarantine_include_paths_rejects_nonexistent_file(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    with pytest.raises(QuarantineBlocked, match="include path not found"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
            include_paths=[PurePosixPath("nonexistent/file.py")],
        )


def test_quarantine_include_paths_rejects_unsafe_path(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    with pytest.raises(QuarantineBlocked, match="include path must be repository-relative"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
            include_paths=[PurePosixPath("../../../etc/passwd")],
        )


def _include_repo(tmp_path: Path) -> Path:
    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026" / "core"
    (source / "nested").mkdir()
    (source / "nested" / "helper.py").write_text("HELPER = 1\n", encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/core/nested/helper.py")
    return repo


@pytest.mark.parametrize(
    ("include_paths", "expected_relative_paths"),
    [
        ([PurePosixPath("core")], ["core/nested/helper.py", "core/solver.py"]),
        ([PurePosixPath("core/solver.py"), PurePosixPath("core/solver.py")], ["core/solver.py"]),
        ([PurePosixPath("core"), PurePosixPath("core")], ["core/nested/helper.py", "core/solver.py"]),
        ([PurePosixPath("core"), PurePosixPath("core/solver.py")], ["core/nested/helper.py", "core/solver.py"]),
    ],
    ids=["tracked-directory", "duplicate-file", "repeated-directory", "overlapping-directory-and-file"],
)
def test_quarantine_include_paths_expand_and_deduplicate_files_once(
    tmp_path: Path,
    include_paths: list[PurePosixPath],
    expected_relative_paths: list[str],
):
    repo = _include_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    archive = repo / "archive" / "legacy"

    manifest = quarantine_tracked_tree(
        repo_root=repo,
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/legacy"),
        archive_id="legacy",
        include_paths=include_paths,
    )

    manifest_paths = [entry.original_path.removeprefix("academic_benchmark/yaem2026/") for entry in manifest.entries]
    assert manifest_paths == expected_relative_paths
    assert len(manifest_paths) == len(set(manifest_paths))
    for relative_path in expected_relative_paths:
        assert (archive / relative_path).is_file()
        assert not (source / relative_path).exists()


def test_quarantine_validates_all_includes_before_scanning_or_mutating(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    target = tmp_path / "outside.py"
    target.write_text("outside\n", encoding="utf-8")
    linked = source / "results" / "reports" / "analysis.md"
    linked.unlink()
    try:
        linked.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    before = _snapshot_tree(source)

    with pytest.raises(QuarantineBlocked, match="include path not found"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
            include_paths=[PurePosixPath("core/solver.py"), PurePosixPath("missing/later.py")],
        )

    assert _snapshot_tree(source) == before
    assert not (repo / "archive").exists()


def test_quarantine_invalid_later_include_fails_before_git_enumeration(
    tmp_path: Path, monkeypatch
):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    source = repo / "academic_benchmark" / "yaem2026"
    before = _snapshot_tree(source)

    def fail_git_enumeration(*_args, **_kwargs):
        raise AssertionError("Git enumeration occurred before include validation")

    monkeypatch.setattr(module, "git_tracked_files", fail_git_enumeration)
    with pytest.raises(QuarantineBlocked, match="include path not found"):
        module.quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/legacy"),
            archive_id="legacy",
            include_paths=[PurePosixPath("core/solver.py"), PurePosixPath("missing/later.py")],
        )

    assert _snapshot_tree(source) == before
    assert not (repo / "archive").exists()


def test_cli_quarantine_profile_bildiri(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    called_with = {}

    def fake_quarantine(**kwargs):
        called_with.update(kwargs)
        return module.ArchiveManifest(
            schema_version="uniride-archive/v1",
            archive_id="test",
            source_root="academic_benchmark/yaem2026",
            archive_root="archive/legacy",
            entries=[],
        )

    monkeypatch.setattr(module, "quarantine_tracked_tree", fake_quarantine)
    assert main(["quarantine", "--repo-root", str(repo), "--source", "academic_benchmark/yaem2026", "--archive", "archive/legacy", "--archive-id", "test", "--profile", "bildiri"]) == 0
    assert called_with.get("classifier") is module.classify_bildiri_evidence


def test_cli_quarantine_include_flag(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    called_with = {}

    def fake_quarantine(**kwargs):
        called_with.update(kwargs)
        return module.ArchiveManifest(
            schema_version="uniride-archive/v1",
            archive_id="test",
            source_root="academic_benchmark/yaem2026",
            archive_root="archive/legacy",
            entries=[],
        )

    monkeypatch.setattr(module, "quarantine_tracked_tree", fake_quarantine)
    assert main(["quarantine", "--repo-root", str(repo), "--source", "academic_benchmark/yaem2026", "--archive", "archive/legacy", "--archive-id", "test", "--include", "core/solver.py", "--include", "results/reports/analysis.md"]) == 0
    assert called_with.get("include_paths") == [PurePosixPath("core/solver.py"), PurePosixPath("results/reports/analysis.md")]


def test_cli_quarantine_default_profile_is_yaem(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as module

    repo = _legacy_repo(tmp_path)
    called_with = {}

    def fake_quarantine(**kwargs):
        called_with.update(kwargs)
        return module.ArchiveManifest(
            schema_version="uniride-archive/v1",
            archive_id="test",
            source_root="academic_benchmark/yaem2026",
            archive_root="archive/legacy",
            entries=[],
        )

    monkeypatch.setattr(module, "quarantine_tracked_tree", fake_quarantine)
    assert main(["quarantine", "--repo-root", str(repo), "--source", "academic_benchmark/yaem2026", "--archive", "archive/legacy", "--archive-id", "test"]) == 0
    assert called_with.get("classifier") is module.classify_yaem_evidence