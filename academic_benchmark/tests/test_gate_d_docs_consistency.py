"""Gate D item D-11: the master documents agree with the live algorithm catalog.

The migration table in ``CURRENT_ARCHITECTURE.md`` (between the
``migration-table`` markers) is checked against the code, not against a copy of
the code: the capability catalog, the resolver alias and forbidden-ID tables, the
matrix-legacy engine names and the routing-refusing non-catalog IDs.  The two
registry modules are read with ``ast`` so the test needs no solver imports.

History sections are fenced with ``<!-- history:start -->`` / ``<!-- history:end -->``;
a false historical label may appear only inside such a fence or inside the table.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from academic_benchmark.core.algorithm_resolution import (
    CLI_ALIAS_TARGETS,
    FORBIDDEN_ALGORITHM_REPLACEMENTS,
)
from uniride_core.algorithms.capabilities import CAPABILITY_CATALOG

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO_ROOT / "CURRENT_ARCHITECTURE.md"
WORKSTATE = REPO_ROOT / "docs" / "UNIRIDE_WORKSTATE.md"
DECISION_LOG = REPO_ROOT / "docs" / "DECISION_LOG.md"
SYNCHRONIZED_DOCUMENTS = (
    REPO_ROOT / "README.md",
    ARCHITECTURE,
    REPO_ROOT / "ACTIVE_ROADMAP.md",
    REPO_ROOT / "UniRide_Ultimate_Audit.md",
    WORKSTATE,
)

TABLE_START = "<!-- migration-table:start -->"
TABLE_END = "<!-- migration-table:end -->"
HISTORY_START = "<!-- history:start -->"
HISTORY_END = "<!-- history:end -->"

# Labels that were never true algorithm names. The two guidance-only IDs are built
# from pieces, as the resolver does, so no source scan of this repository flags them.
FALSE_LABELS = ("GWO-LKH", "HHO-LKH", "B" + "-GA", "B" + "-PSO")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    assert text.count(start) == 1 and text.count(end) == 1, (start, end)
    return text.split(start, 1)[1].split(end, 1)[0]


def _table_rows() -> dict[str, str]:
    """First-column backticked name -> whole row text, for every row in the table."""
    rows: dict[str, str] = {}
    for line in _between(_read(ARCHITECTURE), TABLE_START, TABLE_END).splitlines():
        if not line.startswith("|"):
            continue
        first_cell = line.split("|")[1]
        for name in re.findall(r"`([^`]+)`", first_cell):
            rows[name] = line
    return rows


def _assigned_node(path: Path, name: str) -> ast.AST:
    for node in ast.parse(_read(path)).body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return node.value
    raise AssertionError(f"{name} not found in {path}")


def _frozenset_literal(path: Path, name: str) -> set[str]:
    call = _assigned_node(path, name)
    assert isinstance(call, ast.Call) and call.func.id == "frozenset"  # type: ignore[attr-defined]
    return set(ast.literal_eval(call.args[0]))


def _dict_keys(path: Path, name: str) -> set[str]:
    value = _assigned_node(path, name)
    assert isinstance(value, ast.Dict)
    return {ast.literal_eval(key) for key in value.keys}


ROUTING_REFUSING_NONCATALOG = _frozenset_literal(
    REPO_ROOT / "academic_benchmark" / "core" / "registry_setup.py",
    "_ROUTING_REFUSING_NONCATALOG_IDS",
)
MATRIX_LEGACY = _dict_keys(
    REPO_ROOT / "uniride_core" / "algorithms" / "engine_factory.py",
    "MATRIX_LEGACY_TSP_SOLVERS",
)


def _dict_items(path: Path, name: str) -> dict[str, str]:
    value = _assigned_node(path, name)
    assert isinstance(value, ast.Dict)
    return {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(value.keys, value.values)}


REGISTRY_SETUP = REPO_ROOT / "academic_benchmark" / "core" / "registry_setup.py"
ROUTING_ALIAS_ENGINES = _dict_items(REGISTRY_SETUP, "_ROUTING_ALIAS_ENGINES")
ROUTING_ALTERNATIVE_BASES = _dict_items(REGISTRY_SETUP, "_ROUTING_ALTERNATIVE_BASES")
ROUTING_ALIAS_NAMES = {
    f"{prefix}-{base}" for prefix in ("CVRP", "CVRPTW") for base in ROUTING_ALIAS_ENGINES
}
GATE_D_STATUS_PHRASE = (
    "Gate D is closed except D-12 (publication, owner permission); D-04b2 (final estimate on the stronger computer) "
    "is a precondition of the paper-scale run, not a Gate D acceptance item"
)


def test_every_cvrp_alias_row_names_the_engine_it_runs() -> None:
    rows = _table_rows()
    for base, engine in ROUTING_ALIAS_ENGINES.items():
        for prefix in ("CVRP", "CVRPTW"):
            name = f"{prefix}-{base}"
            assert name in rows, f"{name} missing from the migration table"
            assert f"`{engine}`" in rows[name], f"row for {name} does not name its engine {engine}"


def test_the_routing_variant_column_matches_the_refusal_table() -> None:
    rows = _table_rows()
    for canonical_id in CAPABILITY_CATALOG:
        cell = rows[canonical_id].split("|")[3].strip()
        base = ROUTING_ALTERNATIVE_BASES.get(canonical_id)
        if base is None:
            assert cell == "none", f"{canonical_id}: expected 'none', found {cell!r}"
        else:
            assert f"`CVRP-{base}`" in cell and f"`CVRPTW-{base}`" in cell, (
                f"{canonical_id}: the variant column does not offer CVRP-{base} / CVRPTW-{base}: {cell!r}"
            )
            engine = ROUTING_ALIAS_ENGINES[base]
            assert f"`{engine}`" in cell, f"{canonical_id}: the variant column does not name {engine}"


@pytest.mark.parametrize("path", SYNCHRONIZED_DOCUMENTS, ids=lambda p: p.name)
def test_every_document_states_the_gate_d_status_in_the_same_words(path: Path) -> None:
    assert GATE_D_STATUS_PHRASE in " ".join(_read(path).split()), path.name


def test_the_migration_table_exists_and_cites_decision_log_entries() -> None:
    rows = _table_rows()
    assert rows, "no migration table between the markers in CURRENT_ARCHITECTURE.md"
    log = _read(DECISION_LOG)
    for name, row in rows.items():
        cited = set(re.findall(r"\b(A\d{2}|E\d{2})\b", row))
        assert cited, f"row for {name} cites no DECISION_LOG entry"
        for entry in cited:
            assert re.search(rf"^### {entry} ", log, re.MULTILINE), (
                f"row for {name} cites {entry}, which has no heading in DECISION_LOG.md"
            )


def test_every_catalog_id_is_in_the_migration_table() -> None:
    rows = _table_rows()
    missing = sorted(set(CAPABILITY_CATALOG) - set(rows))
    assert not missing, f"catalog IDs missing from the migration table: {missing}"


def test_every_alias_refusal_and_legacy_name_is_in_the_migration_table() -> None:
    rows = _table_rows()
    expected = (
        set(CLI_ALIAS_TARGETS)
        | set(FORBIDDEN_ALGORITHM_REPLACEMENTS)
        | set(MATRIX_LEGACY)
        | set(ROUTING_REFUSING_NONCATALOG)
    )
    missing = sorted(expected - set(rows))
    assert not missing, f"names missing from the migration table: {missing}"


def test_each_alias_and_forbidden_row_names_its_target_in_the_code() -> None:
    rows = _table_rows()
    for alias, target in {**CLI_ALIAS_TARGETS, **FORBIDDEN_ALGORITHM_REPLACEMENTS}.items():
        assert f"`{target}`" in rows[alias], f"row for {alias} does not name {target}"


def test_the_table_names_nothing_the_code_does_not_know() -> None:
    known = (
        set(CAPABILITY_CATALOG)
        | set(CLI_ALIAS_TARGETS)
        | set(FORBIDDEN_ALGORITHM_REPLACEMENTS)
        | set(MATRIX_LEGACY)
        | set(ROUTING_REFUSING_NONCATALOG)
        | ROUTING_ALIAS_NAMES
    )
    stray = sorted(set(_table_rows()) - known)
    assert not stray, f"migration table rows for IDs that no code path knows: {stray}"


def _strip(text: str) -> str:
    """Remove history fences and the migration table; what remains is active prose."""
    while HISTORY_START in text:
        head, rest = text.split(HISTORY_START, 1)
        assert HISTORY_END in rest, "unclosed history fence"
        text = head + rest.split(HISTORY_END, 1)[1]
    if TABLE_START in text:
        head, rest = text.split(TABLE_START, 1)
        text = head + rest.split(TABLE_END, 1)[1]
    return text


@pytest.mark.parametrize("path", SYNCHRONIZED_DOCUMENTS, ids=lambda p: p.name)
def test_no_false_label_outside_the_table_and_history_sections(path: Path) -> None:
    active = _strip(_read(path))
    for label in FALSE_LABELS:
        assert not re.search(rf"(?<![\w-]){re.escape(label)}(?![\w-])", active), (
            f"{path.name} uses the false label {label} outside the migration table and history sections"
        )


def test_the_history_fences_are_balanced_in_every_document() -> None:
    for path in SYNCHRONIZED_DOCUMENTS:
        text = _read(path)
        assert text.count(HISTORY_START) == text.count(HISTORY_END), path.name


def test_the_workstate_gate_d_row_states_the_status_and_names_a_commit() -> None:
    rows = [line for line in _read(WORKSTATE).splitlines() if line.startswith("| ACAD-01")]
    assert len(rows) == 1, "exactly one ACAD-01 row expected in the workstate"
    row = rows[0]
    assert GATE_D_STATUS_PHRASE in row
    commits = re.findall(r"WIP commit `([0-9a-f]{8,40})`", row)
    assert commits, "the Gate D row must name the WIP commit it is based on as WIP commit `<sha>`"
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not available to check the named commit")
    for sha in commits:
        result = subprocess.run(
            [git, "merge-base", "--is-ancestor", sha, "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=60,
        )
        assert result.returncode == 0, f"{sha} is not an ancestor of HEAD"


# ---------------------------------------------------------------- run-index completeness is merged, no longer a run precondition
RUN_INDEX_MERGED = "run-index completeness (`uniride-run-index/v2`)"
PRECONDITION_DOCUMENTS = (ARCHITECTURE, WORKSTATE, REPO_ROOT / "ACTIVE_ROADMAP.md")


@pytest.mark.parametrize("path", SYNCHRONIZED_DOCUMENTS, ids=lambda p: p.name)
def test_no_document_lists_the_run_index_follow_up_as_a_paper_run_precondition(path: Path) -> None:
    text = " ".join(_read(path).split())
    assert "run-index completeness follow-up" not in text, path.name
    assert "G1, G2, G3, G6, G7" not in text, path.name


@pytest.mark.parametrize("path", PRECONDITION_DOCUMENTS, ids=lambda p: p.name)
def test_the_paper_run_preconditions_are_mt6_d04b2_and_oq4(path: Path) -> None:
    text = " ".join(_read(path).split())
    start = text.index("reconditions of any paper-scale run")
    sentence = text[start:start + 700]
    assert "MT6" in sentence and "D-04b2" in sentence and "OQ-4" in sentence, path.name
    assert "run-index" not in sentence, path.name


@pytest.mark.parametrize("path", PRECONDITION_DOCUMENTS, ids=lambda p: p.name)
def test_the_documents_that_list_what_is_merged_name_the_run_index_v2(path: Path) -> None:
    assert RUN_INDEX_MERGED in " ".join(_read(path).split()), path.name
