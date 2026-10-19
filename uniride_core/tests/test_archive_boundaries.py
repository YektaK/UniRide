from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path


ACTIVE_ROOTS = ("academic_benchmark", "optimizer_api", "src", "uniride_core")
ARCHIVE_MARKERS = (
    ".proposed_changes",
    "docs/old",
    "docs\\old",
    "optimizer_api.strategies._archived",
)


def _python_files(project_root: Path):
    for root_name in ACTIVE_ROOTS:
        root = project_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            parts = set(path.parts)
            if "_archived" in parts or "old" in parts:
                continue
            yield path


def _constant_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


IMPORT_MARKERS = ("_archived", ".proposed_changes", "docs.old")


def _import_offences(source: str) -> list[int]:
    """Line numbers of imports that reach archived code."""
    offences: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        if any(
            marker in name.replace("/", ".").replace("\\", ".")
            for name in names
            for marker in IMPORT_MARKERS
        ):
            offences.append(node.lineno)
    return sorted(offences)


def test_import_offence_helper_rejects_the_archive_namespace_and_dynamic_imports():
    static = "\n".join(
        (
            "import archive",
            "import archive.academic_benchmark.bildiri2026_legacy.bildiri2026",
            "from archive.docs import x",
            "from archive import academic_benchmark",
        )
    )
    dynamic = "\n".join(
        (
            "import importlib",
            "importlib.import_module('archive.academic_benchmark.yaem2026_legacy')",
            "__import__('archive.docs')",
        )
    )
    assert _import_offences(static) == [1, 2, 3, 4]
    assert _import_offences(dynamic) == [2, 3]


def test_import_offence_helper_respects_component_boundaries():
    source = "\n".join(
        (
            "import archived_tools",
            "import my_archive.thing",
            "importlib.import_module('archive_old_docs')",
        )
    )
    assert _import_offences(source) == []


def test_archive_package_is_not_importable():
    project_root = Path(__file__).resolve().parents[1].parent
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PYTHONPATH"] = str(project_root)
    for statement in (
        "import archive",
        "import archive.academic_benchmark",
        "import archive.academic_benchmark.yaem2026_legacy",
    ):
        result = subprocess.run(
            [sys.executable, "-c", statement],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode != 0, statement
        assert "ImportError" in result.stderr, (statement, result.stderr)
        assert "QUARANTINE.md" in result.stderr, (statement, result.stderr)


def test_root_and_scripts_python_files_are_scanned():
    project_root = Path(__file__).resolve().parents[1].parent
    scanned = {path.relative_to(project_root).as_posix() for path in _python_files(project_root)}
    assert "scripts/run_exact_tsp_reference.py" in scanned
    assert any("/" not in name for name in scanned), "no repository-root *.py file is scanned"


def test_active_python_does_not_import_archived_modules_or_paths():
    project_root = Path(__file__).resolve().parents[1].parent
    offenders = [
        f"{path.relative_to(project_root)}:{line}"
        for path in _python_files(project_root)
        for line in _import_offences(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_active_python_does_not_add_archived_paths_to_sys_path():
    project_root = Path(__file__).resolve().parents[1].parent
    offenders: list[str] = []

    for path in _python_files(project_root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr in {"append", "insert"}
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "path"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "sys"
            ):
                continue

            constants = [_constant_text(arg) for arg in node.args]
            if any(
                value is not None and any(marker in value for marker in ARCHIVE_MARKERS)
                for value in constants
            ):
                offenders.append(str(path.relative_to(project_root)))

    assert offenders == []
