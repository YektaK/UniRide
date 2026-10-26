"""MT6-05 (N-1): the budgeted 2-opt, Or-opt and 3-opt controllers accept a move only
when it improves by more than the scale-aware tolerance of ``improve_three_opt``
(``CANONICAL_THREE_OPT_DESIGN.md``, "Objective comparisons use a scale-aware tolerance").

Two groups of tests:

* float matrices: an improvement below the tolerance is not accepted, an improvement
  above it is; evaluation counting is unchanged by the rule;
* study instances: every Bildiri 2026 and YAEM 2026 dataset (loaded from the committed
  artifacts, never from ``tsplib.db``) is integer valued, and the three controllers give
  the results recorded in ``GOLDEN`` below.  ``GOLDEN`` was captured on the code before
  the tolerance change (commit a08920e1) and stored in
  ``golden/mt6_budgeted_tolerance_golden.json``, so the tests prove that the change is a
  no-op on the study instances.  Regenerate by running this file as a script (its output
  is the JSON) only after a deliberate change of the neighbourhood or the start route.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest

from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    improve_or_opt_budgeted,
    improve_three_opt_budgeted,
    improve_two_opt_budgeted,
)
from uniride_core.algorithms.tsplib_parser import parse_atsp_text, parse_tsplib_text
from uniride_core.models import ProblemInstance

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_FILES = (
    "academic_benchmark/studies/bildiri2026/study.json",
    "academic_benchmark/studies/yaem2026/study.json",
)

CONTROLLERS = {
    "two_opt": improve_two_opt_budgeted,
    "or_opt": improve_or_opt_budgeted,
    "three_opt": improve_three_opt_budgeted,
}

# ---------------------------------------------------------------------------
# Float matrices
# ---------------------------------------------------------------------------

N = 8


def _uniform_matrix(scale: float, special_edge=None, delta: float = 0.0):
    """Every off-diagonal entry is ``scale``; ``special_edge`` is cheaper by ``delta``."""
    matrix = [[0.0 if i == j else scale for j in range(N)] for i in range(N)]
    if special_edge is not None:
        a, b = special_edge
        matrix[a][b] = matrix[b][a] = scale - delta
    return matrix


def _run(name, matrix, first_improvement, limit=None):
    budget = ObjectiveEvaluationBudget(limit)
    result = CONTROLLERS[name](
        list(range(N)), matrix, budget, max_iterations=50, first_improvement=first_improvement
    )
    return result, budget


# (scale, improvement below the tolerance, improvement above it).  The tolerance of a
# cost C is 1e-10 * max(1, |C|); the identity tour on the uniform matrix costs 8 * scale.
SCALES = (
    (1.0, 1e-12, 1e-6),
    (1e6, 1e-4, 1.0),
)


@pytest.mark.parametrize("first_improvement", (False, True))
@pytest.mark.parametrize("scale,tiny,big", SCALES)
@pytest.mark.parametrize("name", sorted(CONTROLLERS))
def test_improvement_below_tolerance_is_not_accepted(name, scale, tiny, big, first_improvement):
    base, base_budget = _run(name, _uniform_matrix(scale), first_improvement)
    assert base.route == list(range(N))
    assert base.termination_reason == "no_improving_move"

    # Edge (0, 2) is not in the identity tour; every move that adds it changes the
    # tour cost by exactly -tiny (all other edges cost ``scale``).
    result, budget = _run(name, _uniform_matrix(scale, (0, 2), tiny), first_improvement)
    assert result.route == list(range(N))
    assert result.cost == pytest.approx(N * scale, abs=0.0, rel=0.0)
    assert result.termination_reason == "no_improving_move"
    # The tolerance changes acceptance, never the accounting: one complete pass.
    assert result.evaluations == base.evaluations
    assert budget.used == base_budget.used


@pytest.mark.parametrize("first_improvement", (False, True))
@pytest.mark.parametrize("scale,tiny,big", SCALES)
@pytest.mark.parametrize("name", sorted(CONTROLLERS))
def test_improvement_above_tolerance_is_accepted(name, scale, tiny, big, first_improvement):
    result, _ = _run(name, _uniform_matrix(scale, (0, 2), big), first_improvement)
    assert result.route != list(range(N))
    assert result.cost == pytest.approx(N * scale - big, abs=0.0, rel=1e-12)


# ---------------------------------------------------------------------------
# Study instances
# ---------------------------------------------------------------------------


def _study_dataset_refs():
    refs = []
    for study_file in STUDY_FILES:
        study = json.loads((REPO_ROOT / study_file).read_text(encoding="utf-8"))
        for ref in study["dataset_manifest_refs"]:
            if ref not in refs:
                refs.append(ref)
    return refs


def _load_study_matrix(ref):
    """Distance matrix of one study dataset from its committed artifact (as the study runner)."""
    manifest = json.loads((REPO_ROOT / ref).read_text(encoding="utf-8"))
    text = (REPO_ROOT / manifest["artifact_path"]).read_text(encoding="utf-8")
    name = Path(manifest["artifact_path"]).stem
    if manifest["problem_type"] == "ATSP":
        parsed = parse_atsp_text(text, f"{name}.atsp")
        assert parsed
        return manifest["dataset_id"], [[float(v) for v in row] for row in parsed["explicit_matrix"]]
    parsed = parse_tsplib_text(text, f"{name}.tsp")
    assert parsed
    problem = ProblemInstance(
        name=parsed["name"], dimension=parsed["dimension"],
        coordinates=list(parsed["coordinates"]), optimal=0.0,
        problem_type="tsp", edge_weight_type=parsed["edge_weight_type"],
    )
    problem.prepare_matrices()
    return manifest["dataset_id"], problem.dist_matrix


# Smoke slice: first-improvement with a small budget, best-improvement with a larger one.
MODES = {"first": (True, 4000), "best": (False, 12000)}


def _fingerprint(result, budget):
    route_hash = hashlib.sha256(json.dumps(list(result.route)).encode()).hexdigest()[:16]
    return [
        route_hash, float(result.cost), int(result.evaluations), int(result.iterations),
        bool(result.budget_exhausted), result.termination_reason, int(budget.used),
    ]


def _study_run(matrix, controller, mode):
    first_improvement, limit = MODES[mode]
    start = list(range(len(matrix)))
    random.Random(2026).shuffle(start)
    budget = ObjectiveEvaluationBudget(limit)
    result = CONTROLLERS[controller](
        start, matrix, budget, max_iterations=1000, first_improvement=first_improvement
    )
    return _fingerprint(result, budget)


def _all_study_cases():
    return [
        (dataset_id, matrix)
        for dataset_id, matrix in (_load_study_matrix(ref) for ref in _study_dataset_refs())
    ]


GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "mt6_budgeted_tolerance_golden.json").read_text(encoding="utf-8")
)


def test_study_datasets_are_the_expected_set_and_integer_valued():
    cases = _all_study_cases()
    assert sorted(dataset_id for dataset_id, _ in cases) == sorted(
        {key.split("|")[0] for key in GOLDEN}
    )
    for dataset_id, matrix in cases:
        for row in matrix:
            for value in row:
                assert float(value).is_integer(), (dataset_id, value)


@pytest.mark.parametrize("mode", sorted(MODES))
@pytest.mark.parametrize("controller", sorted(CONTROLLERS))
@pytest.mark.parametrize("dataset_id", sorted({key.split("|")[0] for key in GOLDEN}))
def test_study_instances_unchanged_by_tolerance(dataset_id, controller, mode):
    matrices = dict(_all_study_cases())
    assert _study_run(matrices[dataset_id], controller, mode) == GOLDEN[f"{dataset_id}|{controller}|{mode}"]


if __name__ == "__main__":  # capture script: prints the GOLDEN literal
    captured = {}
    for dataset_id, matrix in _all_study_cases():
        for controller in sorted(CONTROLLERS):
            for mode in sorted(MODES):
                captured[f"{dataset_id}|{controller}|{mode}"] = _study_run(matrix, controller, mode)
    print(json.dumps(captured, indent=4, sort_keys=True))
