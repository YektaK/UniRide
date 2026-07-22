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
    assert verify_manifest(manifest, archive) == ["checksum mismatch: core/solver.py"]
