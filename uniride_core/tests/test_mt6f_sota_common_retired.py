"""MT6F-01: the unused ``sota_common`` package is archived and its shims are gone.

Plan: docs/superpowers/plans/2026-10-27-mt6-followup-sota-common-shims-l3-l10.md (MT6F-01);
decision DECISION_LOG A21 OQ-F1 a (physical archive with the manifest tool).

Nothing live imported the package (S-2); it held a non-canonical "3-opt" (a 2-opt) and wall-clock
stops. It now lives only under ``archive/`` as ``REFERENCE_ONLY`` bytes.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

from academic_benchmark.archive_manifest import EvidenceClass, load_manifest, main as archive_main

REPO = Path(__file__).resolve().parents[2]
MANIFEST = "archive/uniride_core/sota_common_legacy/manifest.json"
SCAN_DIRS = ("uniride_core", "optimizer_api", "academic_benchmark", "scripts")
SKIP_PARTS = {"__pycache__", "node_modules", ".venv", ".venv-jit", ".git"}


def _find_spec_or_none(name: str):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        # a missing parent package also means the module cannot be imported
        return None


@pytest.mark.parametrize(
    "name",
    ["uniride_core.algorithms.sota_common", "optimizer_api.strategies.sota_common"],
)
def test_sota_common_cannot_be_imported(name: str):
    assert _find_spec_or_none(name) is None


def test_shim_directory_is_gone():
    # the API's modules import as ``strategies.*`` (optimizer_api is on sys.path), so find_spec on the
    # ``optimizer_api.strategies`` dotted name is None even while the shims exist; check the folder too
    assert not (REPO / "optimizer_api" / "strategies" / "sota_common").exists()
    assert not (REPO / "uniride_core" / "algorithms" / "sota_common").exists()


def _python_files() -> list[Path]:
    files = sorted(REPO.glob("*.py"))
    for directory in SCAN_DIRS:
        root = REPO / directory
        if root.is_dir():
            files.extend(
                path for path in sorted(root.rglob("*.py")) if not SKIP_PARTS.intersection(path.parts)
            )
    return files


def _sota_common_imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        else:
            continue
        found.extend(f"{path.relative_to(REPO).as_posix()}:{node.lineno} {n}" for n in names if "sota_common" in n)
    return found


def test_no_active_python_file_imports_sota_common():
    files = _python_files()
    assert files, "the scan found no Python files; the guard would be vacuous"
    offenders = [hit for path in files for hit in _sota_common_imports(path)]
    assert not offenders, offenders


def test_archive_manifest_verifies_and_is_reference_only():
    assert (REPO / MANIFEST).is_file()
    assert archive_main(["verify", "--repo-root", str(REPO), "--manifest", MANIFEST]) == 0
    manifest = load_manifest(REPO / MANIFEST)
    assert manifest.archive_id == "sota_common_legacy"
    assert manifest.source_root == "uniride_core/algorithms/sota_common"
    assert manifest.entries
    assert {entry.classification for entry in manifest.entries} == {EvidenceClass.REFERENCE_ONLY}
