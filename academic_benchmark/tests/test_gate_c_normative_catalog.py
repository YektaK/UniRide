"""Gate C criterion 1 (C-15): the live catalog conforms to the normative capability table.

The table is read from ``ACADEMIC_STUDY_UNIFICATION_DESIGN.md`` ("Initial academic capability
matrix"), so a change of the design table breaks this test until the catalog follows it. No row
is deferred: every normative ID is VERIFIED for TSP and ATSP with a fixed-budget claim (exact
accounting) and a native-termination claim, and none is production ready. IDs outside the table
are listed below with their DECISION_LOG reference; any other extra ID fails.

The design's "Study label" column (``GWO-3opt`` and so on) has no field in the catalog; the
catalog ``label`` is the longer display name. Labels are therefore pinned per row below, and the
hybrid and memetic labels are additionally checked for the wording Gate C requires.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from uniride_core.algorithms.capabilities import (
    CompositionKind,
    ExecutionProtocol,
    LifecycleStatus,
    ProblemContract,
    list_algorithm_capabilities,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN = REPO_ROOT / "ACADEMIC_STUDY_UNIFICATION_DESIGN.md"
DECISION_LOG = REPO_ROOT / "docs" / "DECISION_LOG.md"
NORMATIVE_ROW_COUNT = 14

# IDs outside the normative table, each with the DECISION_LOG entry that records it.
DESIGN_ADDITIONS = {
    "Core-GA-TSP-Memetic-2opt": "A17 - Gate C (Package C) plan and owner decisions",
}

# Live pins per normative row: (catalog label, composition kind of every claim).
K = CompositionKind
EXPECTED = {
    "Core-TwoOpt-TSP": ("2-opt", K.LOCAL_SEARCH),
    "Core-ThreeOpt-TSP": ("3-opt", K.LOCAL_SEARCH),
    "Core-OrOpt-TSP": ("Or-opt", K.LOCAL_SEARCH),
    "Core-GA-TSP": ("Genetic Algorithm", K.PURE),
    "Core-PSO-TSP": ("Particle Swarm Optimization", K.PURE),
    "Core-GWO-TSP-Pure": ("Grey Wolf Optimizer (pure)", K.PURE),
    "Core-HHO-TSP-Pure": ("Harris Hawks Optimizer (pure)", K.PURE),
    "Core-GWO-TSP-Memetic-2opt": ("Grey Wolf Optimizer (memetic 2-opt)", K.MEMETIC_2OPT),
    "Core-HHO-TSP-Memetic-2opt": ("Harris Hawks Optimizer (memetic 2-opt)", K.MEMETIC_2OPT),
    "ALNS-TSP": ("Adaptive Large Neighborhood Search", K.PURE),
    "Core-GWO-TSP-Memetic-3opt": (
        "Grey Wolf Optimizer + 3-opt (final polish once)", K.GLOBAL_THEN_FINAL_3OPT),
    "Core-HHO-TSP-Memetic-3opt": (
        "Harris Hawks Optimizer + 3-opt (final polish once)", K.GLOBAL_THEN_FINAL_3OPT),
    "Core-GWO-TSP-Memetic-ALNS": (
        "Grey Wolf Optimizer + ALNS (final polish once)", K.GLOBAL_THEN_FINAL_ALNS),
    "Core-HHO-TSP-Memetic-ALNS": (
        "Harris Hawks Optimizer + ALNS (final polish once)", K.GLOBAL_THEN_FINAL_ALNS),
}
HYBRIDS = {
    "Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-3opt",
    "Core-GWO-TSP-Memetic-ALNS", "Core-HHO-TSP-Memetic-ALNS",
}
ADDITION_EXPECTED = {
    "Core-GA-TSP-Memetic-2opt": (
        "Genetic Algorithm (memetic 2-opt: initial and final)", K.MEMETIC_2OPT),
}


def _design_rows() -> dict[str, list[str]]:
    """Normative rows by canonical ID, each as the list of the other table cells."""
    lines = DESIGN.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("### Initial academic capability matrix"))
    header = next(i for i in range(start, len(lines)) if lines[i].startswith("| Canonical ID |"))
    rows: dict[str, list[str]] = {}
    for line in lines[header + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[cells[0].strip("`")] = [cell.strip("`") for cell in cells[1:]]
    return rows


def _catalog() -> dict[str, object]:
    return {capability.canonical_id: capability for capability in list_algorithm_capabilities()}


def test_the_live_design_table_has_the_fourteen_normative_rows():
    rows = _design_rows()
    assert len(rows) == NORMATIVE_ROW_COUNT
    assert set(rows) == set(EXPECTED)
    for canonical_id, (study_label, problems, directed, fixed, native, production) in rows.items():
        assert study_label
        assert problems == "TSP, ATSP", canonical_id
        assert directed == "yes", canonical_id
        assert fixed == "exact-fixed", canonical_id
        assert native == "yes", canonical_id
        assert production == "false", canonical_id


def test_every_catalog_id_is_a_normative_row_or_a_listed_design_addition():
    extra = set(_catalog()) - set(_design_rows())
    assert extra == set(DESIGN_ADDITIONS), f"unlisted catalog IDs: {sorted(extra - set(DESIGN_ADDITIONS))}"
    assert set(_design_rows()) <= set(_catalog())


@pytest.mark.parametrize("canonical_id,heading", sorted(DESIGN_ADDITIONS.items()))
def test_each_design_addition_is_recorded_in_the_decision_log(canonical_id, heading):
    log = DECISION_LOG.read_text(encoding="utf-8")
    section = log[log.index("### " + heading):]
    next_heading = section.find("\n### ", 1)
    section = section if next_heading == -1 else section[:next_heading]
    assert canonical_id in section, f"{canonical_id} is not recorded under '{heading}'"


def _evidence_exists(evidence_id: str) -> bool:
    path_text, _, function = evidence_id.partition("::")
    path = REPO_ROOT / path_text
    return path.is_file() and f"def {function}(" in path.read_text(encoding="utf-8")


def _assert_conforms(canonical_id: str, label: str, kind: CompositionKind) -> None:
    capability = _catalog()[canonical_id]
    assert capability.lifecycle is LifecycleStatus.VERIFIED, canonical_id
    assert capability.production_ready is False, canonical_id
    assert capability.label == label, canonical_id
    claims = capability.claims
    assert {(c.problem, c.protocol) for c in claims} == {
        (problem, protocol)
        for problem in (ProblemContract.TSP, ProblemContract.ATSP)
        for protocol in (ExecutionProtocol.FIXED_BUDGET, ExecutionProtocol.NATIVE_TERMINATION)
    }, canonical_id
    assert len(claims) == 4, canonical_id
    for claim in claims:
        where = f"{canonical_id} {claim.problem.value} {claim.protocol.value}"
        assert claim.exact_objective_accounting is True, where
        assert claim.fixed_seed_deterministic is True, where
        assert claim.truthful_result_reporting is True, where
        assert claim.directed_cost_preserved is (claim.problem is ProblemContract.ATSP), where
        assert claim.composition is kind, where
        assert claim.evidence_ids and all(_evidence_exists(e) for e in claim.evidence_ids), where


@pytest.mark.parametrize("canonical_id", sorted(EXPECTED))
def test_normative_row_conforms(canonical_id):
    label, kind = EXPECTED[canonical_id]
    _assert_conforms(canonical_id, label, kind)


@pytest.mark.parametrize("canonical_id", sorted(HYBRIDS))
def test_hybrid_rows_carry_the_final_polish_once_wording_and_composition_kinds(canonical_id):
    capability = _catalog()[canonical_id]
    assert "final polish once" in capability.label
    polish = "3-opt" if canonical_id.endswith("3opt") else "ALNS"
    assert polish in capability.label
    expected_kind = (
        K.GLOBAL_THEN_FINAL_3OPT if polish == "3-opt" else K.GLOBAL_THEN_FINAL_ALNS
    )
    assert {c.composition for c in capability.claims} == {expected_kind}


@pytest.mark.parametrize("canonical_id", sorted(ADDITION_EXPECTED))
def test_design_addition_conforms(canonical_id):
    label, kind = ADDITION_EXPECTED[canonical_id]
    _assert_conforms(canonical_id, label, kind)
    label_text = _catalog()[canonical_id].label
    # the plan (C-15, C-16c) words it "initial and final 2-opt"; the live label is the C-16c wording
    assert "2-opt" in label_text and "initial and final" in label_text
    assert kind is K.MEMETIC_2OPT


def test_no_normative_or_added_id_is_deferred():
    lifecycle = {cid: cap.lifecycle for cid, cap in _catalog().items()}
    assert set(lifecycle.values()) == {LifecycleStatus.VERIFIED}
