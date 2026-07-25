from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ACTIVE_ROOTS = [
    REPO_ROOT / "academic_benchmark",
    REPO_ROOT / "uniride_core",
    REPO_ROOT / "optimizer_api",
]

ARCHIVE_ROOT = REPO_ROOT / "archive"
BILDIRI_SOURCE_TREE = REPO_ROOT / "academic_benchmark" / "bildiri2026"

PENDING_LEGACY_FILES = [
    REPO_ROOT / "academic_benchmark" / "run_numba_with_bildiri_params.py",
    REPO_ROOT / "academic_benchmark" / "tests" / "test_bildiri_data_manager.py",
    REPO_ROOT / "academic_benchmark" / "tests" / "test_bildiri2026_benchmark_script_smoke.py",
    REPO_ROOT / "academic_benchmark" / "tests" / "test_orchestrate_batch.py",
]

MIGRATION_TABLE_MODULES = {
    REPO_ROOT / "academic_benchmark" / "core" / "registry_setup.py",
    REPO_ROOT / "academic_benchmark" / "cli_engine.py",
}

PARITY_TEST_FILES = {
    REPO_ROOT / "academic_benchmark" / "tests" / "test_bildiri_solver_parity.py",
}

BOUNDARY_TEST_FILE = REPO_ROOT / "academic_benchmark" / "tests" / "test_bildiri_quarantine_boundary.py"

MIGRATION_TEST_FILES = {
    REPO_ROOT / "academic_benchmark" / "tests" / "test_legacy_algorithm_migrations.py",
}

ALLOWED_EXECUTABLE_TOKEN_FILES = MIGRATION_TABLE_MODULES | set(PENDING_LEGACY_FILES) | PARITY_TEST_FILES | {BOUNDARY_TEST_FILE} | MIGRATION_TEST_FILES


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
            if path.is_relative_to(REPO_ROOT / "archive"):
                continue
            files.append(path)
    return sorted(set(files))


def _normalize_token(token: str) -> str:
    return token.lower().replace("-", "_").replace(" ", "_")


FORBIDDEN_IMPORTS = {
    "academic_benchmark.bildiri2026",
    "academic_benchmark.bildiri2026.core",
    "academic_benchmark.bildiri2026.core.gwo_solver",
    "academic_benchmark.bildiri2026.core.hho_solver",
    "academic_benchmark.bildiri2026.core.numba_accel",
    "bildiri2026",
    "bildiri2026.core",
    "bildiri2026.core.gwo_solver",
    "bildiri2026.core.hho_solver",
    "bildiri2026.core.numba_accel",
}

FORBIDDEN_EXECUTABLE_TOKENS = {"b_ga", "b_pso", "biliri_ga", "biliri_pso"}


def _check_ast_imports(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                normalized = _normalize_token(alias.name)
                if any(normalized.startswith(forbidden) for forbidden in FORBIDDEN_IMPORTS):
                    violations.append(f"import {alias.name} at line {node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                normalized = _normalize_token(node.module)
                if any(normalized.startswith(forbidden) for forbidden in FORBIDDEN_IMPORTS):
                    violations.append(f"from {node.module} import ... at line {node.lineno}")
    return violations


def _check_string_injection(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    violations: list[str] = []
    for i, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "academic_benchmark/bildiri2026" in line or "academic_benchmark\\bildiri2026" in line:
            if path in MIGRATION_TABLE_MODULES or path in PENDING_LEGACY_FILES or path == BOUNDARY_TEST_FILE:
                continue
            violations.append(f"string path injection at line {i}")
    return violations


def _check_executable_tokens(path: Path) -> list[str]:
    if path in ALLOWED_EXECUTABLE_TOKEN_FILES:
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    violations: list[str] = []
    for i, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for token in FORBIDDEN_EXECUTABLE_TOKENS:
            if token in _normalize_token(stripped):
                violations.append(f"executable token '{token}' at line {i}")
    return violations


def _check_solver_imports_bildiri(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "tsp_matrix_metaheuristics" in (node.module or ""):
                for alias in node.names:
                    if alias.name in ("GWOOptimizer", "HHOOptimizer"):
                        violations.append(f"canonical solver imports academic_benchmark at line {node.lineno}")
    return violations


class TestZeroActiveBildiriReachability:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.active_files = _collect_active_python()

    def test_no_import_of_bildiri2026_in_active_code(self):
        allowed_import_files = set(PENDING_LEGACY_FILES) | PARITY_TEST_FILES
        violations: dict[str, list[str]] = {}
        for path in self.active_files:
            if path in allowed_import_files:
                continue
            issues = _check_ast_imports(path)
            if issues:
                violations[str(path.relative_to(REPO_ROOT))] = issues
        assert not violations, "Active code imports bildiri2026:\n" + "\n".join(
            f"  {f}: {'; '.join(v)}" for f, v in violations.items()
        )

    def test_no_string_injection_of_bildiri2026_path(self):
        violations: dict[str, list[str]] = {}
        for path in self.active_files:
            issues = _check_string_injection(path)
            if issues:
                violations[str(path.relative_to(REPO_ROOT))] = issues
        assert not violations, "Active code contains string path injection:\n" + "\n".join(
            f"  {f}: {'; '.join(v)}" for f, v in violations.items()
        )

    def test_no_executable_bildiri_tokens(self):
        violations: dict[str, list[str]] = {}
        for path in self.active_files:
            issues = _check_executable_tokens(path)
            if issues:
                violations[str(path.relative_to(REPO_ROOT))] = issues
        assert not violations, "Active code contains executable Bildiri tokens:\n" + "\n".join(
            f"  {f}: {'; '.join(v)}" for f, v in violations.items()
        )

    def test_pending_legacy_files_are_declared(self):
        for path in PENDING_LEGACY_FILES:
            assert path.exists(), f"Declared pending legacy file missing: {path.relative_to(REPO_ROOT)}"

    def test_pending_legacy_files_are_not_imported_by_active_code(self):
        for path in self.active_files:
            if any(path == f for f in PENDING_LEGACY_FILES):
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = node.module if isinstance(node, ast.ImportFrom) else None
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for legacy in PENDING_LEGACY_FILES:
                                if legacy.stem in alias.name:
                                    pytest.fail(f"{path.relative_to(REPO_ROOT)} imports {alias.name} at line {node.lineno}")
                    elif module:
                        for legacy in PENDING_LEGACY_FILES:
                            if legacy.stem in module:
                                pytest.fail(f"{path.relative_to(REPO_ROOT)} imports from {module} at line {node.lineno}")


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
        lines = source.splitlines()
        for i, line in enumerate(lines, start=1):
            if "GWOOptimizer" in line or "HHOOptimizer" in line:
                if "import" in line:
                    assert "uniride_core" in line, f"Line {i}: solver import not from uniride_core: {line.strip()}"
