from __future__ import annotations

import ast
import json
from importlib.metadata import PathDistribution
from importlib.machinery import PathFinder
from pathlib import Path

import pytest

from academic_benchmark.archive_manifest import load_manifest, verify_manifest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ACTIVE_ROOTS = (
    REPO_ROOT / "academic_benchmark",
    REPO_ROOT / "uniride_core",
    REPO_ROOT / "optimizer_api",
)
ARCHIVE_ROOT = REPO_ROOT / "archive"
BILDIRI_SOURCE_TREE = REPO_ROOT / "academic_benchmark" / "bildiri2026"
BILDIRI_ARCHIVE_ROOT = ARCHIVE_ROOT / "academic_benchmark" / "bildiri2026_legacy"
MANIFEST_PATH = BILDIRI_ARCHIVE_ROOT / "manifest.json"
BOUNDARY_TEST_FILE = Path(__file__).resolve()
CANONICAL_SOLVER_FILES = (
    REPO_ROOT / "uniride_core" / "algorithms" / "tsp_matrix_metaheuristics" / "gwo_solver.py",
    REPO_ROOT / "uniride_core" / "algorithms" / "tsp_matrix_metaheuristics" / "hho_solver.py",
)

# These legacy entry points must remain quarantined and unreachable from active code.
QUARANTINED_LEGACY_FILES = (
    REPO_ROOT / "academic_benchmark" / "run_numba_with_bildiri_params.py",
    REPO_ROOT / "academic_benchmark" / "tests" / "test_bildiri_data_manager.py",
    REPO_ROOT / "academic_benchmark" / "tests" / "test_bildiri2026_benchmark_script_smoke.py",
    REPO_ROOT / "academic_benchmark" / "tests" / "test_orchestrate_batch.py",
    BILDIRI_SOURCE_TREE / "data_manager.py",
    BILDIRI_SOURCE_TREE / "orchestrate_batch.py",
    BILDIRI_SOURCE_TREE / "benchmarks" / "tsplib_benchmark.py",
    BILDIRI_SOURCE_TREE / "benchmarks" / "timematrix_benchmark.py",
    BILDIRI_SOURCE_TREE / "data" / "tuned_parameters_db.json",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "academic_benchmark.bildiri2026",
    "bildiri2026",
)
FORBIDDEN_TOP_LEVEL_IMPORT_PREFIXES = (
    "core",
    "data_manager",
    "orchestrate_batch",
    "tsplib_benchmark",
    "timematrix_benchmark",
    "benchmarks.tsplib_benchmark",
    "benchmarks.timematrix_benchmark",
)
FORBIDDEN_EXECUTABLE_TOKENS = {"b_ga", "b_pso"}
EXECUTABLE_TOKEN_ALLOWLIST = {
    BOUNDARY_TEST_FILE,
    (REPO_ROOT / "academic_benchmark" / "cli_engine.py").resolve(),
    (REPO_ROOT / "academic_benchmark" / "tests" / "test_legacy_algorithm_migrations.py").resolve(),
}
LEGACY_PIPELINE_MARKERS = (
    "academic_benchmark.bildiri2026.data_manager",
    "academic_benchmark.bildiri2026.orchestrate_batch",
    "academic_benchmark.bildiri2026.benchmarks.tsplib_benchmark",
    "academic_benchmark.bildiri2026.benchmarks.timematrix_benchmark",
    "academic_benchmark/bildiri2026/data_manager.py",
    "academic_benchmark/bildiri2026/orchestrate_batch.py",
    "academic_benchmark/bildiri2026/benchmarks/tsplib_benchmark.py",
    "academic_benchmark/bildiri2026/benchmarks/timematrix_benchmark.py",
    "academic_benchmark/bildiri2026/data/tuned_parameters_db.json",
)


def _collect_active_python() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if path == BILDIRI_SOURCE_TREE or path.is_relative_to(BILDIRI_SOURCE_TREE):
                continue
            if path.is_relative_to(ARCHIVE_ROOT):
                continue
            files.append(path.resolve())
    return sorted(set(files))


def _archive_payload_paths(archive_root: Path) -> set[str]:
    control_paths = {"manifest.json", "QUARANTINE.md"}
    return {
        relative_path
        for path in archive_root.rglob("*")
        if path.is_file()
        for relative_path in [path.relative_to(archive_root).as_posix()]
        if relative_path not in control_paths
    }


def _normalize_token(token: str) -> str:
    return token.lower().replace("-", "_").replace(" ", "_")


def _module_matches(module: str, prefix: str) -> bool:
    lowered = module.lower()
    return lowered == prefix or lowered.startswith(prefix + ".")


def _check_ast_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        candidates: list[tuple[str, int]] = []
        if isinstance(node, ast.Import):
            candidates.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            candidates.append((node.module, node.level))
        for module, level in candidates:
            forbidden_bildiri = any(
                _module_matches(module, prefix) for prefix in FORBIDDEN_IMPORT_PREFIXES
            )
            forbidden_fallback = level == 0 and any(
                _module_matches(module, prefix)
                for prefix in FORBIDDEN_TOP_LEVEL_IMPORT_PREFIXES
            )
            if forbidden_bildiri or forbidden_fallback:
                violations.append(f"forbidden import {module} at line {node.lineno}")
    return violations


def _check_academic_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules = [node.module]
        else:
            modules = []
        for module in modules:
            if _module_matches(module, "academic_benchmark"):
                violations.append(f"academic_benchmark import {module} at line {node.lineno}")
    return violations


def _check_string_reachability(path: Path) -> list[str]:
    if path == BOUNDARY_TEST_FILE:
        return []
    source = path.read_text(encoding="utf-8").lower().replace("\\", "/")
    violations: list[str] = []
    for marker in LEGACY_PIPELINE_MARKERS:
        if marker in source:
            violations.append(f"legacy pipeline marker {marker}")
    if "academic_benchmark/bildiri2026" in source:
        violations.append("legacy Bildiri source-tree path")
    return violations


def _check_executable_tokens(path: Path) -> list[str]:
    if path in EXECUTABLE_TOKEN_ALLOWLIST:
        return []
    source = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        if line.strip().startswith("#"):
            continue
        normalized = _normalize_token(line)
        for token in FORBIDDEN_EXECUTABLE_TOKENS:
            if token in normalized:
                violations.append(f"executable token {token} at line {line_number}")
    return violations


def _assert_no_violations(label: str, checker) -> None:
    violations: dict[str, list[str]] = {}
    for path in _collect_active_python():
        issues = checker(path)
        if issues:
            violations[path.relative_to(REPO_ROOT).as_posix()] = issues
    assert not violations, label + ":\n" + "\n".join(
        f"  {path}: {'; '.join(issues)}" for path, issues in violations.items()
    )


class TestZeroActiveBildiriReachability:
    def test_no_legacy_or_top_level_fallback_imports(self):
        # No active file, including parity tests, is exempt from legacy import checks.
        _assert_no_violations("Active code has a forbidden import", _check_ast_imports)

    def test_no_legacy_pipeline_or_source_path_reachability(self):
        _assert_no_violations(
            "Active code reaches quarantined pipeline material", _check_string_reachability
        )

    def test_no_bildiri_ga_or_bildiri_pso_executable_aliases(self):
        _assert_no_violations(
            "Active code contains executable Bildiri aliases", _check_executable_tokens
        )

    def test_import_guard_detects_core_and_legacy_pipeline_fallbacks(self, tmp_path: Path):
        sample = tmp_path / "fallbacks.py"
        sample.write_text(
            "import core\n"
            "import core.gwo_solver\n"
            "from data_manager import DataManager\n"
            "from benchmarks.tsplib_benchmark import run\n",
            encoding="utf-8",
        )
        issues = _check_ast_imports(sample)
        assert len(issues) == 4

    def test_alias_guard_detects_exact_legacy_aliases(self, tmp_path: Path):
        sample = tmp_path / "aliases.py"
        sample.write_text(
            'first = "B-GA"\nsecond = "B-PSO"\n', encoding="utf-8"
        )
        issues = _check_executable_tokens(sample)
        assert {"b_ga", "b_pso"} == {
            token for issue in issues for token in FORBIDDEN_EXECUTABLE_TOKENS if token in issue
        }


class TestRegistryResolvesFromCanonicalCore:
    def test_registry_setup_imports_from_uniride_core(self):
        registry_path = REPO_ROOT / "academic_benchmark" / "core" / "registry_setup.py"
        source = registry_path.read_text(encoding="utf-8")
        assert "from uniride_core.algorithms.tsp_matrix_metaheuristics import" in source
        assert "from academic_benchmark.bildiri2026" not in source

    def test_gwo_hho_resolvers_are_canonical(self):
        registry_path = REPO_ROOT / "academic_benchmark" / "core" / "registry_setup.py"
        source = registry_path.read_text(encoding="utf-8")
        assert "GWOOptimizer" in source
        assert "HHOOptimizer" in source
        for line_number, line in enumerate(source.splitlines(), start=1):
            if ("GWOOptimizer" in line or "HHOOptimizer" in line) and "import" in line:
                assert "uniride_core" in line, (
                    f"Line {line_number}: solver import not from uniride_core: {line.strip()}"
                )

    @pytest.mark.parametrize("solver_path", CANONICAL_SOLVER_FILES)
    def test_canonical_solver_has_no_academic_benchmark_dependency(self, solver_path: Path):
        assert solver_path.is_file(), f"Canonical solver missing: {solver_path}"
        assert not _check_academic_imports(solver_path)

    def test_canonical_dependency_guard_detects_academic_import(self, tmp_path: Path):
        sample = tmp_path / "solver.py"
        sample.write_text(
            "from academic_benchmark.engine_core import RunResult\n", encoding="utf-8"
        )
        assert _check_academic_imports(sample)


class TestPostArchivalBoundary:
    def test_bildiri_source_tree_and_active_legacy_files_are_absent(self):
        assert not BILDIRI_SOURCE_TREE.exists(), (
            f"Bildiri source tree still exists: {BILDIRI_SOURCE_TREE}"
        )
        present = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in QUARANTINED_LEGACY_FILES
            if path.exists()
        ]
        assert not present, f"Quarantined legacy files remain active: {present}"

    def test_archive_manifest_covers_all_233_files(self):
        assert MANIFEST_PATH.is_file(), f"Archive manifest missing: {MANIFEST_PATH}"
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        entries = manifest.get("entries", [])
        original_paths = {entry["original_path"] for entry in entries}
        assert len(entries) == 233, f"Expected 233 entries, got {len(entries)}"
        assert len(original_paths) == 233, (
            f"Expected 233 unique original paths, got {len(original_paths)}"
        )

    def test_archive_verification_passes(self):
        assert MANIFEST_PATH.is_file(), f"Archive manifest missing: {MANIFEST_PATH}"
        manifest = load_manifest(MANIFEST_PATH)
        errors = verify_manifest(manifest, BILDIRI_ARCHIVE_ROOT)
        assert not errors, f"Archive verification failed: {errors}"

    def test_no_unmanifested_historical_files(self):
        assert MANIFEST_PATH.is_file(), f"Archive manifest missing: {MANIFEST_PATH}"
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        archive_prefix = "archive/academic_benchmark/bildiri2026_legacy/"
        manifest_paths = {
            entry["archive_path"][len(archive_prefix):]
            for entry in manifest.get("entries", [])
            if entry.get("archive_path", "").startswith(archive_prefix)
        }
        actual_files = _archive_payload_paths(BILDIRI_ARCHIVE_ROOT)
        assert actual_files == manifest_paths, (
            f"Archive/manifest mismatch: unmanifested={sorted(actual_files - manifest_paths)}, "
            f"missing={sorted(manifest_paths - actual_files)}"
        )

    @pytest.mark.parametrize("control_name", ["manifest.json", "QUARANTINE.md"])
    def test_nested_control_filename_is_archive_payload(
        self, tmp_path: Path, control_name: str
    ):
        nested = tmp_path / "historical" / control_name
        nested.parent.mkdir(parents=True)
        nested.write_text("historical evidence", encoding="utf-8")
        assert _archive_payload_paths(tmp_path) == {f"historical/{control_name}"}

    def test_distribution_package_discovery_excludes_archive_and_bildiri(self):
        distribution = PathDistribution(REPO_ROOT / "uniride.egg-info")
        top_levels = {
            line.strip()
            for line in (distribution.read_text("top_level.txt") or "").splitlines()
            if line.strip()
        }
        assert top_levels == {"academic_benchmark", "optimizer_api", "uniride_core"}
        assert "archive" not in top_levels
        assert all(
            PathFinder.find_spec(package, [str(REPO_ROOT)]) is not None
            for package in top_levels
        )
        academic_spec = PathFinder.find_spec("academic_benchmark", [str(REPO_ROOT)])
        assert academic_spec is not None
        academic_locations = list(academic_spec.submodule_search_locations or ())
        assert PathFinder.find_spec("bildiri2026", academic_locations) is None
