from __future__ import annotations

import ast
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


def test_active_python_does_not_import_archived_modules_or_paths():
    project_root = Path(__file__).resolve().parents[1].parent
    offenders: list[str] = []

    for path in _python_files(project_root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue

            if any(
                marker in name.replace("/", ".").replace("\\", ".")
                for name in names
                for marker in ("_archived", ".proposed_changes", "docs.old")
            ):
                offenders.append(str(path.relative_to(project_root)))

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
