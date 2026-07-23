from __future__ import annotations

import ast
from fnmatch import fnmatchcase
import json
import tomllib
from importlib.util import find_spec
from pathlib import Path


from academic_benchmark.archive_manifest import (
    EvidenceClass,
    load_manifest,
    scan_sensitive_file,
    verify_manifest,
)


REPO = Path(__file__).resolve().parents[2]
ACTIVE_YAEM = REPO / "academic_benchmark" / "yaem2026"
ARCHIVE = REPO / "archive" / "academic_benchmark" / "yaem2026_legacy"
PYTEST_DEFAULT_NORECURSEDIRS = {
    "*.egg",
    ".*",
    "_darcs",
    "build",
    "CVS",
    "dist",
    "node_modules",
    "venv",
    "{arch}",
}


def _active_python_files():
    for root in (
        REPO / "academic_benchmark",
        REPO / "uniride_core",
        REPO / ("optimizer" + "_api"),
    ):
        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
                yield path


def test_legacy_yaem_package_is_absent_and_not_importable():
    assert not ACTIVE_YAEM.exists()
    assert find_spec("academic_benchmark.yaem2026") is None


def test_active_python_has_no_yaem_imports():
    violations = []
    for path in _active_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(
                name == "yaem2026" or name.startswith("academic_benchmark.yaem2026")
                for name in names
            ):
                violations.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert violations == []


def test_distribution_discovery_excludes_archive_and_yaem():
    try:
        from setuptools.discovery import PEP420PackageFinder
    except ModuleNotFoundError:
        pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
        patterns = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
        archive_namespaces = {
            "archive",
            "archive.academic_benchmark",
            "archive.academic_benchmark.yaem2026_legacy",
        }
        assert not any(
            fnmatchcase(namespace, pattern)
            for namespace in archive_namespaces
            for pattern in patterns
        )
        assert not ACTIVE_YAEM.exists()
    else:
        packages = set(PEP420PackageFinder.find(str(REPO), include=["academic_benchmark*"]))
        assert not any("yaem2026" in package for package in packages)
        assert not any(package.startswith("archive") for package in packages)


def test_archive_manifest_covers_the_original_tracked_inventory_and_verifies():
    manifest = load_manifest(ARCHIVE / "manifest.json")
    assert manifest.schema_version == "uniride-archive/v1"
    assert len(manifest.entries) == 159
    assert len({entry.original_path for entry in manifest.entries}) == 159
    assert verify_manifest(manifest, ARCHIVE) == []
    assert {entry.classification for entry in manifest.entries} <= set(EvidenceClass)


def test_archive_contains_no_unmanifested_historical_files():
    manifest = load_manifest(ARCHIVE / "manifest.json")
    expected = {
        Path(entry.archive_path).relative_to(manifest.archive_root).as_posix()
        for entry in manifest.entries
        if entry.archive_path is not None
    }
    actual = {
        path.relative_to(ARCHIVE).as_posix()
        for path in ARCHIVE.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "QUARANTINE.md"}
    }
    assert actual == expected


def test_archive_rescan_has_no_sensitive_findings():
    findings = [
        finding
        for path in ARCHIVE.rglob("*")
        if path.is_file() and path.name != "manifest.json"
        for finding in scan_sensitive_file(path)
    ]
    assert findings == []


def test_manifest_has_no_sensitive_payload_fields():
    raw = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
    assert set(raw) == {
        "archive_id",
        "archive_root",
        "entries",
        "schema_version",
        "source_root",
    }
    assert all(
        set(entry)
        == {"archive_path", "byte_size", "classification", "original_path", "sha256"}
        for entry in raw["entries"]
    )


def test_pytest_norecursedirs_preserves_defaults_and_excludes_archive():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    norecursedirs = set(pyproject["tool"]["pytest"]["ini_options"]["norecursedirs"])
    assert PYTEST_DEFAULT_NORECURSEDIRS <= norecursedirs
    assert "archive" in norecursedirs

