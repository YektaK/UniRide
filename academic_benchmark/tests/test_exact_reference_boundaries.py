"""WP-E8 Task 7: import, archive-path, schema and study-profile boundaries of the exact reference protocol.

* production code (``optimizer_api``, ``uniride_core``) imports none of the new academic modules, and the frontend ``src``
  references none of the new exact artifacts (unification design: production never depends on academic artifacts);
* the new modules hold no archive path string and no legacy Bildiri path, and the reader refuses archive paths at run time;
* the Bildiri study profile and the three pre-existing schemas are byte-identical to the WP-E8 base commit (pinned sha256 over
  LF-normalised bytes: a Windows checkout with core.autocrlf holds CRLF);
* the two archive manifests still verify (YAEM 159 entries, Bildiri 233), with the existing ``archive_manifest verify`` command.

Archive-like path pieces are built from components; the legacy paths are never spelled out as one literal.
"""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

from academic_benchmark import archive_manifest
from academic_benchmark.exact_reference.reader import ExactReferenceRefused, load_exact_reference

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "academic_benchmark"
ARCHIVE = "arch" + "ive"
NEW_ACADEMIC_MODULES = ("academic_benchmark.exact_reference", "academic_benchmark.validation", "academic_benchmark.protocol_registry")
NEW_MODULE_FILES = (
    [PKG / "protocol_registry.py", PKG / "validation" / "__init__.py", PKG / "validation" / "hamiltonian_cycle.py",
       PKG / "validation" / "day_plan.py"]
    + sorted((PKG / "exact_reference").glob("*.py")))
LEGACY_LITERAL = "academic_benchmark" + "/" + "bildiri2026"
EXACT_ARTIFACT_MARKERS = ("exact_reference", "tsplib-exact-reference", "week-2026-10-05-exact")
# No src file may name an academic result folder (no exceptions: the WP-E10 fleet re-run guards and the tests that read the
# historical archives live under scripts/). Literal paths, path.join/path.resolve segment lists and folder names all count.
RESULT_FOLDER_PATTERNS = (
    re.compile(r"docs[\\/]+paper", re.IGNORECASE),
    re.compile(r"""["'`]docs["'`]\s*,\s*["'`]paper["'`]""", re.IGNORECASE),
    re.compile(r"""["'`]paper["'`]\s*,\s*["'`]results["'`]""", re.IGNORECASE),
    re.compile(r"""["'`]paper[\\/]+results""", re.IGNORECASE),
    re.compile(r"week-2026-10-05", re.IGNORECASE),
    re.compile(r"tsplib-exact-reference", re.IGNORECASE),
)

PINNED_LF_SHA256 = {  # at the WP-E8 base commit
    "academic_benchmark/studies/bildiri2026/study.json": "4bfeb48d8d4be1ac8ab3c35f0fec8eb604b9aea73097da360852bb68427920a5",
    "academic_benchmark/schemas/study-v1.schema.json": "193a2e38e033fd8d7b54c791e69b412aa8803b557bc0deaca39d0c8e01a650a8",
    "academic_benchmark/schemas/dataset-v1.schema.json": "6584167fee1ed3d18008fa3a6aea17ce6a31f2970bcab990ec8c0ff800178da1",
    "academic_benchmark/schemas/run-v1.schema.json": "a17b7d8639c06be3b421a2e0cb2664276cb326f9d245e3213f363e18fd466846",
}


def _production_python(root: str):
    base = REPO / root
    for path in sorted(base.rglob("*.py")):
        parts = set(path.parts)
        if "tests" in parts or "__pycache__" in parts or "node_modules" in parts:
            continue
        yield path


def _imported_names(path: Path) -> list:
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.append(module)
            names.extend(f"{module}.{alias.name}" for alias in node.names)
    return names


@pytest.mark.parametrize("root", ["optimizer_api", "uniride_core"])
def test_production_python_imports_none_of_the_new_academic_modules(root):
    files = list(_production_python(root))
    assert len(files) > 20, f"{root}: the scan found {len(files)} files"
    offenders = [f"{p.relative_to(REPO).as_posix()} imports {name}" for p in files for name in _imported_names(p)
                 if any(name == m or name.startswith(m + ".") for m in NEW_ACADEMIC_MODULES)]
    assert offenders == []


def test_production_python_names_no_result_folder_in_a_string():
    """No string constant of production code (comments are not strings) names a ``docs/paper/results`` path."""
    offenders = []
    for root in ("optimizer_api", "uniride_core"):
        for path in _production_python(root):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and "docs/paper/results" in node.value.replace("\\", "/"):
                    offenders.append(f"{path.relative_to(REPO).as_posix()}:{node.lineno}")
    assert offenders == [], "production code reads no academic result artifact"


def test_frontend_src_references_none_of_the_new_exact_artifacts_and_no_new_result_folder():
    referencing_results, offenders = set(), []
    scanned = 0
    for path in sorted((REPO / "src").rglob("*")):
        if not path.is_file() or path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".json", ".mjs"):
            continue
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(REPO).as_posix()
        scanned += 1
        if any(pattern.search(text) for pattern in RESULT_FOLDER_PATTERNS):
            referencing_results.add(rel)
        offenders.extend(f"{rel}: {m}" for m in EXACT_ARTIFACT_MARKERS if m in text)
    assert scanned > 200, f"the scan found {scanned} src files"
    assert offenders == []
    assert sorted(referencing_results) == [], "src names an academic result folder"


@pytest.mark.parametrize("text", [
    'const a = "docs/paper/results/x";', 'const a = "docs\\\\paper\\\\results";',
    'join(process.cwd(), "docs", "paper", "results", "w")', 'path.resolve(root, "paper", "results")',
    'const n = "week-2026-10-05-fleet";', 'const n = "tsplib-exact-reference";',
])
def test_result_folder_patterns_catch_literal_and_path_join_spellings(text):
    assert any(pattern.search(text) for pattern in RESULT_FOLDER_PATTERNS)


def test_result_folder_patterns_ignore_the_benchmark_api_route():
    assert not any(p.search('fetch("/api/benchmark/results/1")') for p in RESULT_FOLDER_PATTERNS)


# ---------------------------------------------------------------- archive paths
_ARCHIVE_PATH = re.compile(r"archive[/\\]|/\s*[\"']archive[\"']|[\"']archive[\"']\s*/|[\"']archive[\"']\s*,\s*[\"']")


@pytest.mark.parametrize("path", NEW_MODULE_FILES, ids=lambda p: p.relative_to(PKG).as_posix())
def test_new_modules_hold_no_archive_path_segment_and_no_legacy_bildiri_path(path):
    assert path.is_file(), path
    text = path.read_text(encoding="utf-8")
    hits = [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1) if _ARCHIVE_PATH.search(line)]
    assert hits == []
    assert LEGACY_LITERAL not in text and "bildiri2026_legacy" not in text and "yaem2026_legacy" not in text


def test_the_runner_and_the_inputs_module_hold_no_legacy_bildiri_path_either():
    for path in (REPO / "scripts" / "run_exact_tsp_reference.py", PKG / "exact_reference" / "inputs.py"):
        text = path.read_text(encoding="utf-8")
        assert LEGACY_LITERAL not in text and "bildiri2026_legacy" not in text, path.name


def test_the_new_file_list_covers_the_modules_of_this_work_package():
    names = {p.name for p in NEW_MODULE_FILES}
    assert {"rows.py", "reader.py", "inputs.py", "protocol.py", "protocol_registry.py", "hamiltonian_cycle.py",
            "day_plan.py"} <= names


# WP-E11 J6: the day-plan checker stays independent of the solver and planning code it verifies (design section 5.1).
FORBIDDEN_CHECKER_IMPORTS = ("uniride_core", "optimizer_api", "scripts", "academic_benchmark")


def test_the_day_plan_checker_imports_only_the_standard_library():
    import sys

    path = PKG / "validation" / "day_plan.py"
    assert path.is_file()
    tops = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import in the day-plan checker"
            tops.add((node.module or "").split(".")[0])
    assert tops, "the scan found no import at all"
    assert not [t for t in tops if t in FORBIDDEN_CHECKER_IMPORTS], sorted(tops)
    assert not [t for t in tops if t not in sys.stdlib_module_names], sorted(tops)


@pytest.mark.parametrize("bad", [f"{ARCHIVE}/x", f"docs/{ARCHIVE}/x", f"docs/{ARCHIVE.upper()}/x"])
def test_the_reader_refuses_archive_paths_at_run_time(bad):
    with pytest.raises(ExactReferenceRefused):
        load_exact_reference(bad, repo_root=REPO)


# ---------------------------------------------------------------- unchanged study profile and schemas
@pytest.mark.parametrize("relative", sorted(PINNED_LF_SHA256))
def test_study_profile_and_existing_schemas_are_byte_identical_to_the_base(relative):
    data = (REPO / relative).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == PINNED_LF_SHA256[relative]


def test_the_bildiri_study_profile_stays_unlinked_from_the_exact_reference():
    text = (PKG / "studies" / "bildiri2026" / "study.json").read_text(encoding="utf-8")
    assert "exact_reference" not in text and "exact-reference" not in text
    for path in sorted((PKG / "studies").rglob("*.py")):
        assert not [n for n in _imported_names(path) if "exact_reference" in n or "protocol_registry" in n], path.name


# ---------------------------------------------------------------- the archive manifests still verify
@pytest.mark.parametrize("legacy_dir, count", [("yaem2026_legacy", 159), ("bildiri2026_legacy", 233)])
def test_archive_manifests_verify(capsys, legacy_dir, count):
    manifest = "/".join((ARCHIVE, "academic_benchmark", legacy_dir, "manifest.json"))
    assert archive_manifest.main(["verify", "--repo-root", str(REPO), "--manifest", manifest]) == 0
    assert f"verified {count} entries" in capsys.readouterr().out
