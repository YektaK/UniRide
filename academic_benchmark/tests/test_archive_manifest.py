from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from academic_benchmark.archive_manifest import (
    EvidenceClass,
    build_manifest,
    classify_yaem_evidence,
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
