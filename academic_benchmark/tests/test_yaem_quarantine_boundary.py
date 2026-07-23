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


def _package_parts(path: Path) -> tuple[str, ...]:
    return path.relative_to(REPO).with_suffix("").parts[:-1]


QUARANTINED_IMPORT_ROOTS = (
    "yaem2026",
    "academic_benchmark.yaem2026",
    "archive.academic_benchmark.yaem2026_legacy",
)


def _is_quarantined_import(name: str) -> bool:
    return name == "yaem2026" or any(
        name == root or name.startswith(f"{root}.")
        for root in QUARANTINED_IMPORT_ROOTS
    )


def _import_violations(path: Path, source: str) -> list[int]:
    violations = []
    package = _package_parts(path)
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: 1 - node.level] if node.level > 1 else package
                module = ".".join((*base, *(node.module or "").split("."))).strip(".")
            else:
                module = node.module or ""
            candidates = [module, *(f"{module}.{alias.name}" for alias in node.names)]
        else:
            continue
        if any(_is_quarantined_import(name) for name in candidates):
            violations.append(node.lineno)
    return sorted(violations)


def _configured_package_include_patterns() -> list[str]:
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["tool"]["setuptools"]["packages"]["find"]["include"]


PACKAGE_INCLUDE_PATTERNS = _configured_package_include_patterns()


def _quarantined_package_names() -> set[str]:
    namespaces = set()
    for directory in (ARCHIVE, *(path for path in ARCHIVE.rglob("*") if path.is_dir())):
        parts = directory.relative_to(REPO).parts
        namespaces.update(".".join(parts[:depth]) for depth in range(1, len(parts) + 1))
    return namespaces


def _patterns_expose_quarantined_packages(patterns: list[str]) -> bool:
    return any(
        fnmatchcase(namespace, pattern)
        for namespace in _quarantined_package_names()
        for pattern in patterns
    )


def _is_historical_archive_file(path: Path) -> bool:
    return path.relative_to(ARCHIVE) not in {
        Path("manifest.json"),
        Path("QUARANTINE.md"),
    }

def test_import_violation_helper_catches_aliases_and_relative_imports():
    source = "\n".join(
        (
            "import academic_benchmark.yaem2026 as legacy",
            "from academic_benchmark.yaem2026 import solver as legacy_solver",
            "from academic_benchmark import yaem2026 as legacy_package",
            "from . import yaem2026 as relative_legacy",
            "from archive.academic_benchmark.yaem2026_legacy import old_solver",
        )
    )

    assert _import_violations(
        REPO / "academic_benchmark" / "boundary_probe.py", source
    ) == [1, 2, 3, 4, 5]


def test_import_violation_helper_resolves_relative_imports_from_package_inits():
    assert _import_violations(
        REPO / "academic_benchmark" / "__init__.py", "from . import yaem2026"
    ) == [1]
    assert _import_violations(
        REPO / "academic_benchmark" / "core" / "__init__.py",
        "from .. import yaem2026",
    ) == [1]
    assert _import_violations(
        REPO / "academic_benchmark" / "core" / "regular_module.py",
        "from .. import yaem2026",
    ) == [1]


def test_import_violation_helper_respects_component_boundaries():
    source = "\n".join(
        (
            "import academic_benchmark.yaem2026_safe",
            "import archive.academic_benchmark.yaem2026_legacy_tools",
        )
    )

    assert _import_violations(
        REPO / "academic_benchmark" / "boundary_probe.py", source
    ) == []


def test_import_violation_helper_catches_bare_yaem2026_descendants_only():
    source = "\n".join(
        (
            "import yaem2026.solver",
            "import yaem2026_safe",
        )
    )

    assert _import_violations(
        REPO / "academic_benchmark" / "boundary_probe.py", source
    ) == [1]


def test_package_pattern_validation_rejects_archive_wildcard_and_descendant_only_pattern():
    assert _patterns_expose_quarantined_packages(["archive*"])
    assert _patterns_expose_quarantined_packages(
        ["archive.academic_benchmark.yaem2026_legacy.*"]
    )
    assert _patterns_expose_quarantined_packages(
        ["archive.academic_benchmark.yaem2026_legacy.archive_20260701_0120.results.*"]
    )


def test_historical_archive_file_classification_only_excludes_root_metadata():
    assert not _is_historical_archive_file(ARCHIVE / "manifest.json")
    assert not _is_historical_archive_file(ARCHIVE / "QUARANTINE.md")
    assert _is_historical_archive_file(ARCHIVE / "nested" / "manifest.json")
    assert _is_historical_archive_file(ARCHIVE / "nested" / "QUARANTINE.md")

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
    violations = [
        f"{path.relative_to(REPO)}:{lineno}"
        for path in _active_python_files()
        for lineno in _import_violations(path, path.read_text(encoding="utf-8"))
    ]
    assert violations == []
def test_distribution_discovery_excludes_archive_and_yaem():
    assert not _patterns_expose_quarantined_packages(PACKAGE_INCLUDE_PATTERNS)
    try:
        from setuptools.discovery import PEP420PackageFinder
    except ModuleNotFoundError:
        assert not ACTIVE_YAEM.exists()
    else:
        packages = set(
            PEP420PackageFinder.find(str(REPO), include=PACKAGE_INCLUDE_PATTERNS)
        )
        assert not any(_is_quarantined_import(package) for package in packages)
        assert not any(package == "archive" or package.startswith("archive.") for package in packages)
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
        if path.is_file() and _is_historical_archive_file(path)
    }
    assert actual == expected


def test_archive_rescan_has_no_sensitive_findings():
    findings = [
        finding
        for path in ARCHIVE.rglob("*")
        if path.is_file()
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
