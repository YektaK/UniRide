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
NEW_ACADEMIC_MODULES = ("academic_benchmark.exact_reference", "academic_benchmark.validation", "academic_benchmark.protocol_registry",
                       "academic_benchmark.analysis")
NEW_MODULE_FILES = (
    [PKG / "protocol_registry.py", PKG / "validation" / "__init__.py", PKG / "validation" / "hamiltonian_cycle.py",
       PKG / "validation" / "day_plan.py"]
    + sorted((PKG / "exact_reference").glob("*.py")) + [PKG / "analysis" / "gaps.py"])
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

PINNED_LF_SHA256 = {  # at the WP-E8 base commit; the bildiri2026 profile hash is re-pinned by the pre-approval values commits (run_count 30, native protocol; paper venue named)
    "academic_benchmark/studies/bildiri2026/study.json": "d8f5577b18a758a625cfa6767138038b294e6ce427eb05644ead21b9f58ac639",
    "academic_benchmark/schemas/study-v1.schema.json": "ac641217e7365d1d49405b4cd6380f3e9a3d2aa3ea14be096f3ef9275c8de5ce",
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
            "day_plan.py", "day_compare.py"} <= names


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


# Study code may use the pooling API of the shared protocol registry (Gate C C-12 refuses mixed-pooling files, Package D
# pools through it) and nothing else of it; the registry itself imports the exact-reference modules, so the allowlist is
# explicit and the exact-reference protocol ids stay banned from study source text (DECISION_LOG E12, A17).
STUDY_REGISTRY_MODULE = "academic_benchmark.protocol_registry"
STUDY_REGISTRY_ALLOWLIST = ("assert_single_pooling_group",)


def _study_import_violations(path: Path) -> list:
    """Imports of a study file that link it to the exact reference: any import naming ``exact_reference``, and any import of
    ``protocol_registry`` other than ``from academic_benchmark.protocol_registry import <allowlisted names>``."""
    bad = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "exact_reference" in alias.name or "protocol_registry" in alias.name:
                    bad.append(f"line {node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            shown = f"line {node.lineno}: from {'.' * node.level}{module} import {', '.join(names)}"
            if "exact_reference" in module or any("exact_reference" in n for n in names):
                bad.append(shown)
            elif "protocol_registry" in module:
                if node.level != 0 or module != STUDY_REGISTRY_MODULE or not set(names) <= set(STUDY_REGISTRY_ALLOWLIST):
                    bad.append(shown)
            elif any("protocol_registry" in n for n in names):
                bad.append(shown)
    return bad


def _exact_reference_protocol_ids() -> set:
    from academic_benchmark.exact_reference import protocol

    ids = {value for name, value in vars(protocol).items()
           if isinstance(value, str) and value and (name.endswith("PROTOCOL_ID") or name == "TSP_REFERENCE_KIND")}  # not the generic solution kind
    assert {"exact_reference_v1", "union_day_v1", "exact_day_joint_v1"} <= ids, ids  # the scan must not go quiet on a rename
    return ids


def _study_text_violations(path: Path, ids: set) -> list:
    text = path.read_text(encoding="utf-8")
    return sorted({token for token in ids | {"exact_reference", "exact-reference"} if token in text})


def test_the_bildiri_study_profile_stays_unlinked_from_the_exact_reference():
    text = (PKG / "studies" / "bildiri2026" / "study.json").read_text(encoding="utf-8")
    assert "exact_reference" not in text and "exact-reference" not in text
    ids = _exact_reference_protocol_ids()
    files = sorted((PKG / "studies").rglob("*.py"))
    assert files, "the scan found no study module"
    for path in files:
        assert _study_import_violations(path) == [], path.name
        assert _study_text_violations(path, ids) == [], path.name


# Gate D, D-06 (X3): the study profiles are linked to the exact reference only through the analysis plan's
# ``exact_reference`` block (reader, join identity, pooling = reference only). The study profile files, the study modules and the
# study row files stay free of exact-reference names and rows; gap columns are computed by the analysis layer, not by a study.
EXPECTED_PLAN_LINK = {"reader": "exact_reference_v1", "join_identity": "normalised_tsplib_problem_name", "pooling": "reference_only"}
PLAN_KEYS_THAT_MAY_NAME_THE_GAP = ("decisions", "response", "exact_reference", "unresolved")  # prose and the response variable
STUDY_FOLDERS = ("bildiri2026", "yaem2026")


@pytest.mark.parametrize("folder", STUDY_FOLDERS)
def test_the_study_profile_files_name_no_exact_reference(folder):
    text = (PKG / "studies" / folder / "study.json").read_text(encoding="utf-8")
    assert "exact_reference" not in text and "exact-reference" not in text


@pytest.mark.parametrize("folder", STUDY_FOLDERS)
def test_the_analysis_plan_is_the_only_study_artifact_linked_to_the_exact_reference(folder):
    import json

    base = PKG / "studies" / folder
    plan = json.loads((base / "analysis_plan.json").read_text(encoding="utf-8"))
    assert plan["exact_reference"] == EXPECTED_PLAN_LINK
    for key, value in plan.items():
        if key not in PLAN_KEYS_THAT_MAY_NAME_THE_GAP:
            assert "exact_reference" not in json.dumps(value) and "exact-reference" not in json.dumps(value), key
    others = [p for p in base.rglob("*") if p.is_file() and p.name not in ("analysis_plan.json", "study.json") and "__pycache__" not in p.parts]
    for path in others:
        assert "exact_reference" not in path.read_text(encoding="utf-8", errors="replace"), path.name


def test_the_study_modules_do_not_import_the_gap_columns():
    files = sorted((PKG / "studies").rglob("*.py"))
    assert files, "the scan found no study module"
    for path in files:
        names = _imported_names(path)
        assert [n for n in names if n == "academic_benchmark.analysis.gaps" or n.startswith("academic_benchmark.analysis.gaps.")] == [], path.name


def test_the_study_row_files_refuse_exact_reference_rows(tmp_path):
    from academic_benchmark.studies.smoke import FIXED_GROUP, NATIVE_GROUP, write_rows_file

    exact = {"protocol": "exact_reference_v1", "problem": "eil51", "instance_id": "eil51", "solver_role": "primary"}
    fixed = {"protocol_version": "uniride-fair-tsp-v2", "comparison_regime": "fixed_evaluation_budget", "problem": "eil51",
             "dataset_id": "tsplib-eil51", "evaluation_budget": 63750}
    for expected in (FIXED_GROUP, NATIVE_GROUP):
        for rows in ([exact], [fixed, exact]):
            target = tmp_path / f"{expected}-{len(rows)}.jsonl"
            with pytest.raises(ValueError):
                write_rows_file(target, rows, expected_group=expected)
            assert not target.exists()


# ---------------------------------------------------------------- the archive manifests still verify
@pytest.mark.parametrize("legacy_dir, count", [("yaem2026_legacy", 159), ("bildiri2026_legacy", 233)])
def test_archive_manifests_verify(capsys, legacy_dir, count):
    manifest = "/".join((ARCHIVE, "academic_benchmark", legacy_dir, "manifest.json"))
    assert archive_manifest.main(["verify", "--repo-root", str(REPO), "--manifest", manifest]) == 0
    assert f"verified {count} entries" in capsys.readouterr().out
