"""C-07: ALNS polish entry from a given tour.

Design rules under test (ACADEMIC_STUDY_UNIFICATION_DESIGN.md composition rules
2, 4, 6, 7, 8 and the native variant): the polish stage starts from the global
stage's complete tour and its known cost (not re-counted), shares the one
atomic counter, receives the stable derived seed
``SHA-256(protocol_version, run_seed, "polish")`` (never Python ``hash()``), and
may never return a tour worse than the one it received.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from uniride_core.algorithms.composition import (
    ALNS_POLISH_TERMINATION_MAP,
    CompositionError,
    GlobalStageResult,
    StageSpec,
    alns_polish_stage,
    derive_polish_seed,
    map_alns_termination,
    run_composition,
)
from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    StageCappedBudget,
)
from uniride_core.algorithms.sota_tsp import alns_tsp as alns_module
from uniride_core.algorithms.sota_tsp.alns_tsp import ALNS_TSP, ALNSConfig
from uniride_core.algorithms.three_opt import closed_tour_cost

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sym(n: int, seed: int):
    rng = random.Random(seed)
    pts = [(rng.uniform(0, 50), rng.uniform(0, 50)) for _ in range(n)]
    return [
        [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts
    ]


def _asym(n: int, seed: int):
    rng = random.Random(seed)
    return [[0 if i == j else rng.randint(1, 40) for j in range(n)] for i in range(n)]


def _circle(n: int):
    pts = [
        (math.cos(2 * math.pi * i / n) * 10, math.sin(2 * math.pi * i / n) * 10)
        for i in range(n)
    ]
    return [
        [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts
    ]


SYM12 = _sym(12, 5)
ASYM8 = _asym(8, 21)
CIRCLE12 = _circle(12)
IDENTITY12 = list(range(12))

PARAMS = {
    "max_iterations": 60,
    "max_no_improvement": 1000,
    "remove_ratio": 0.25,
    "min_remove": 2,
    "segment_length": 10,
    "weight_update_factor": 0.8,
    "use_sa": True,
    "sa_start_temp": 100.0,
    "sa_cooling_rate": 0.995,
}


def _config(**overrides) -> ALNSConfig:
    values = dict(
        iterations=40, max_no_improve=10_000, remove_ratio=0.25, min_remove=2,
        segment_length=10, weight_update_factor=0.8, use_sa=True,
        sa_start_temp=100.0, sa_cooling_rate=0.995, seed=3,
    )
    values.update(overrides)
    return ALNSConfig(**values)


class _SpyBudget(ObjectiveEvaluationBudget):
    """Records every tour handed to ``evaluate``."""

    def __init__(self, limit=None, used=0):
        super().__init__(limit, used)
        self.evaluated = []

    def evaluate(self, route, matrix):
        self.evaluated.append(list(route))
        return super().evaluate(route, matrix)


# ---- the entry: supplied tour, known cost, shared counter -------------------

def test_supplied_tour_is_the_start_and_is_not_recounted(monkeypatch):
    def boom(self):
        raise AssertionError("the polish entry must not build a nearest-neighbour start")

    monkeypatch.setattr(ALNS_TSP, "_nearest_neighbor_tour", boom)
    start = [3, 7, 0, 1, 5, 9, 2, 4, 6, 8, 10, 11]
    start_cost = closed_tour_cost(start, SYM12)
    spy = _SpyBudget(None)

    result = ALNS_TSP(_config(iterations=25)).solve_accounted_from_tour(
        SYM12, start, start_cost, spy
    )

    # not re-counted: every counted evaluation is a candidate, one per iteration
    assert result.iterations == 25
    assert result.evaluations == 25 == spy.used == len(spy.evaluated)
    assert start not in spy.evaluated
    assert result.cost <= start_cost + 1e-9
    assert result.cost == pytest.approx(closed_tour_cost(result.route, SYM12))


def test_first_destroy_receives_the_supplied_tour():
    start = [3, 7, 0, 1, 5, 9, 2, 4, 6, 8, 10, 11]
    solver = ALNS_TSP(_config(iterations=3))
    seen = []

    class Spy:
        def __init__(self, inner):
            self.inner = inner

        def destroy(self, tour, n_remove, rng, matrix):
            seen.append(list(tour))
            return self.inner.destroy(tour, n_remove, rng, matrix)

    solver._destroy_ops = tuple(Spy(op) for op in solver._destroy_ops)
    solver.solve_accounted_from_tour(
        SYM12, start, closed_tour_cost(start, SYM12), ObjectiveEvaluationBudget(None)
    )
    assert seen[0] == start


def test_counter_is_shared_and_grows_only_by_alns_evaluations():
    shared = ObjectiveEvaluationBudget(500, used=10)
    view = StageCappedBudget(shared, None)
    start = IDENTITY12
    result = ALNS_TSP(_config(iterations=17)).solve_accounted_from_tour(
        SYM12, start, closed_tour_cost(start, SYM12), view
    )
    assert shared.used == 10 + 17
    assert result.evaluations == 17


def test_entry_rejects_incomplete_or_malformed_start_tours():
    solver = ALNS_TSP(_config())
    counter = ObjectiveEvaluationBudget(None)
    for bad in ([0, 1, 2], [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], list(range(1, 13))):
        with pytest.raises(ValueError):
            solver.solve_accounted_from_tour(SYM12, bad, 1.0, counter)
    assert counter.used == 0


def test_standalone_entry_still_counts_its_own_nearest_neighbour_start():
    counter = ObjectiveEvaluationBudget(None)
    result = ALNS_TSP(_config(iterations=9)).solve_accounted_with_matrix(SYM12, counter)
    assert result.evaluations == 9 + 1  # the standalone path is unchanged


def test_fresh_entry_with_no_room_returns_the_input_untouched():
    start = [3, 7, 0, 1, 5, 9, 2, 4, 6, 8, 10, 11]
    cost = closed_tour_cost(start, SYM12)
    shared = ObjectiveEvaluationBudget(5, used=5)
    result = ALNS_TSP(_config()).solve_accounted_from_tour(SYM12, start, cost, shared)
    assert result.route == start
    assert result.cost == cost
    assert result.evaluations == 0
    assert result.termination_reason == "evaluation_budget_exhausted"
    assert shared.used == 5


# ---- never worse than the input ---------------------------------------------

@pytest.mark.parametrize("seed", range(5))
def test_polish_never_returns_a_tour_worse_than_its_input(seed):
    # Optimal circle tour + a scorching SA temperature: the walk accepts worse
    # tours almost always, so the LAST tour is worse; the best-found is the input.
    cost = closed_tour_cost(IDENTITY12, CIRCLE12)
    result = ALNS_TSP(
        _config(iterations=80, use_sa=True, sa_start_temp=1e6, sa_cooling_rate=1.0,
                seed=seed)
    ).solve_accounted_from_tour(CIRCLE12, IDENTITY12, cost, ObjectiveEvaluationBudget(None))
    assert result.cost <= cost + 1e-12
    assert result.cost == pytest.approx(closed_tour_cost(result.route, CIRCLE12))
    assert result.route == IDENTITY12


def test_polish_through_the_engine_never_worsens_the_global_tour():
    cost = closed_tour_cost(IDENTITY12, CIRCLE12)
    params = dict(PARAMS, sa_start_temp=1e6, sa_cooling_rate=1.0, max_iterations=80)
    for run_seed in range(4):
        out = run_composition(
            CIRCLE12,
            global_stage=_stub_global(CIRCLE12, 5, IDENTITY12),
            polish_stage=alns_polish_stage(
                CIRCLE12, params, protocol_version="p1", run_seed=run_seed
            ),
            evaluation_budget=200,
            global_fraction=0.5,
        )
        assert out.cost <= cost + 1e-12
        assert out.tour == IDENTITY12
        assert out.polish_changed_tour is False


# ---- derived seed -------------------------------------------------------------

def _reference_seed(protocol_version: str, run_seed: int) -> int:
    payload = json.dumps(
        [protocol_version, run_seed, "polish"], separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") >> 1


def test_derived_seed_follows_the_documented_encoding():
    for version, run_seed in (("p1", 7), ("fixed_budget_v2", 0), ("x", 12345678901)):
        assert derive_polish_seed(version, run_seed) == _reference_seed(version, run_seed)
    assert 0 <= derive_polish_seed("p1", 7) < 2 ** 63


def test_derived_seed_depends_on_each_input():
    base = derive_polish_seed("p1", 7)
    assert derive_polish_seed("p2", 7) != base
    assert derive_polish_seed("p1", 8) != base


@pytest.mark.parametrize("version,run_seed", [
    (1, 7), ("", 7), ("p1", True), ("p1", -1), ("p1", 1.5), ("p1", "7"),
])
def test_derived_seed_rejects_ambiguous_inputs(version, run_seed):
    with pytest.raises((TypeError, ValueError)):
        derive_polish_seed(version, run_seed)


def test_derived_seed_is_stable_across_processes_with_different_hash_seeds():
    code = (
        "from uniride_core.algorithms.composition import derive_polish_seed;"
        "print(derive_polish_seed('p1', 7))"
    )
    outputs = []
    for hash_seed in ("0", "123456"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONPATH=str(REPO_ROOT))
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env,
            cwd=str(REPO_ROOT), timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        outputs.append(int(proc.stdout.strip()))
    assert outputs[0] == outputs[1] == derive_polish_seed("p1", 7)


def test_stage_record_carries_the_derived_seed_and_its_inputs():
    out = run_composition(
        SYM12,
        global_stage=_stub_global(SYM12, 3, IDENTITY12),
        polish_stage=alns_polish_stage(SYM12, PARAMS, protocol_version="p1", run_seed=7),
        evaluation_budget=300,
        global_fraction=0.5,
    )
    stage = out.polish_stage
    assert stage.seed == derive_polish_seed("p1", 7)
    assert stage.stage_id == "ALNS-TSP"
    assert stage.parameters == PARAMS
    assert stage.details["protocol_version"] == "p1"
    assert stage.details["run_seed"] == 7
    assert stage.details["derived_seed"] == stage.seed
    assert "sha256" in stage.details["seed_derivation"]
    assert stage.details["incoming_cost_reused"] is True


def test_same_inputs_replay_identically_and_different_run_seed_walks_differently():
    def run(run_seed):
        return run_composition(
            SYM12,
            global_stage=_stub_global(SYM12, 3, IDENTITY12),
            polish_stage=alns_polish_stage(
                SYM12, PARAMS, protocol_version="p1", run_seed=run_seed
            ),
            evaluation_budget=300,
            global_fraction=0.5,
        ).to_dict()

    def untimed(record):  # wall times differ between two identical runs
        record = dict(record)
        record["stages"] = [
            {k: v for k, v in stage.items() if k != "elapsed_sec"} for stage in record["stages"]
        ]
        return record

    assert untimed(run(7)) == untimed(run(7))
    assert run(7)["stages"][1]["seed"] != run(8)["stages"][1]["seed"]


# ---- adapter: matrix, parameters ------------------------------------------------

def _stub_global(matrix, k, tour):
    cost = closed_tour_cost(tour, matrix)

    def run(shared, cap):
        if shared is None:
            return GlobalStageResult(list(tour), cost, 1, 0, "max_iterations")
        shared.consume(k)
        return GlobalStageResult(list(tour), cost, 1, shared.used, "max_iterations")

    return StageSpec("stub-global", run, {}, seed=1, matrix=matrix)


def test_adapter_fills_the_matrix():
    spec = alns_polish_stage(SYM12, PARAMS, protocol_version="p1", run_seed=7)
    assert spec.matrix is SYM12 or spec.matrix == SYM12
    assert spec.seed == derive_polish_seed("p1", 7)


def test_matrix_mismatch_is_refused_through_run_composition():
    other = _sym(12, 99)
    with pytest.raises(CompositionError, match="different matrix"):
        run_composition(
            SYM12,
            global_stage=_stub_global(SYM12, 3, IDENTITY12),
            polish_stage=alns_polish_stage(other, PARAMS, protocol_version="p1", run_seed=7),
            evaluation_budget=300,
            global_fraction=0.5,
        )


def test_strict_requires_every_alns_parameter_and_refuses_unknown_ones():
    for name in ("max_iterations", "max_no_improvement", "remove_ratio", "min_remove",
                 "segment_length", "weight_update_factor", "use_sa"):
        partial = {k: v for k, v in PARAMS.items() if k != name}
        with pytest.raises(CompositionError, match=name):
            alns_polish_stage(SYM12, partial, protocol_version="p1", run_seed=7)
    with pytest.raises(CompositionError, match="surprise"):
        alns_polish_stage(SYM12, dict(PARAMS, surprise=1), protocol_version="p1", run_seed=7)


@pytest.mark.parametrize("override", [
    {"max_iterations": 0}, {"max_iterations": True}, {"max_no_improvement": 1.5},
    {"remove_ratio": 0.0}, {"remove_ratio": 1.2}, {"remove_ratio": float("nan")},
    {"weight_update_factor": -0.1}, {"use_sa": 1}, {"sa_start_temp": -1.0},
    {"sa_cooling_rate": 0.0}, {"sa_cooling_rate": 1.5},
])
def test_invalid_alns_parameters_are_refused(override):
    with pytest.raises(CompositionError):
        alns_polish_stage(SYM12, dict(PARAMS, **override), protocol_version="p1", run_seed=7)


def test_non_strict_smoke_may_omit_parameters_but_not_misspell_them():
    spec = alns_polish_stage(
        SYM12, {"max_iterations": 20}, protocol_version="p1", run_seed=7, strict=False
    )
    assert spec.params == {"max_iterations": 20}
    with pytest.raises(CompositionError):
        alns_polish_stage(
            SYM12, {"max_iteration": 20}, protocol_version="p1", run_seed=7, strict=False
        )


# ---- termination vocabulary ---------------------------------------------------

def test_fixed_budget_reason_mapping_is_a_fixed_table():
    assert dict(ALNS_POLISH_TERMINATION_MAP) == {
        "evaluation_budget_exhausted": "evaluation_budget_exhausted",
        "max_iterations": "max_iterations",
        "stagnation_limit": "stagnation_limit",
        "max_no_improve": "stagnation_limit",
        "max_no_improvement": "stagnation_limit",
    }
    for source, expected in ALNS_POLISH_TERMINATION_MAP.items():
        native_ok = expected != "evaluation_budget_exhausted"
        assert map_alns_termination(source, native=False) == expected
        if native_ok:
            assert map_alns_termination(source, native=True) == expected
        else:
            with pytest.raises(CompositionError):
                map_alns_termination(source, native=True)
    with pytest.raises(CompositionError):
        map_alns_termination("time_limit", native=False)
    with pytest.raises(CompositionError):
        map_alns_termination("something_new", native=True)


def _polish_only(params, *, budget, global_cost_tour=IDENTITY12, matrix=SYM12, k=2):
    return run_composition(
        matrix,
        global_stage=_stub_global(matrix, k, global_cost_tour),
        polish_stage=alns_polish_stage(matrix, params, protocol_version="p1", run_seed=7),
        evaluation_budget=budget,
        global_fraction=0.5,
    )


def test_fixed_mode_reasons_max_iterations_stagnation_and_budget():
    out = _polish_only(dict(PARAMS, max_iterations=7), budget=100)
    assert out.polish_stage.termination_reason == "max_iterations"
    assert out.termination_reason == "max_iterations"
    assert out.polish_stage.consumed_evaluations == 7

    out = _polish_only(dict(PARAMS, max_no_improvement=1, max_iterations=500), budget=1000)
    assert out.polish_stage.termination_reason == "stagnation_limit"

    out = _polish_only(dict(PARAMS, max_iterations=500), budget=40)
    assert out.polish_stage.termination_reason == "evaluation_budget_exhausted"
    assert out.termination_reason == "evaluation_budget_exhausted"
    assert out.evaluations == 40 and out.polish_stage.consumed_evaluations == 38


def test_native_mode_reasons_and_composite_complete():
    def native(params):
        return run_composition(
            SYM12,
            global_stage=_stub_global(SYM12, 2, IDENTITY12),
            polish_stage=alns_polish_stage(SYM12, params, protocol_version="p1", run_seed=7),
        )

    out = native(dict(PARAMS, max_iterations=9))
    assert out.termination_reason == "composite_complete"
    assert out.polish_stage.termination_reason == "max_iterations"
    assert out.polish_stage.consumed_evaluations == 9  # no hidden re-count, no cap

    out = native(dict(PARAMS, max_no_improvement=1, max_iterations=500))
    assert out.polish_stage.termination_reason == "stagnation_limit"
    assert out.termination_reason == "composite_complete"


def test_native_adapter_refuses_a_budget_exhaustion_result(monkeypatch):
    spec = alns_polish_stage(SYM12, PARAMS, protocol_version="p1", run_seed=7)

    def exhausted(self, matrix, tour, cost, budget):
        return alns_module.AccountedALNSResult(
            route=list(tour), cost=cost, iterations=0, evaluations=0,
            budget_exhausted=True, termination_reason="evaluation_budget_exhausted",
        )

    monkeypatch.setattr(ALNS_TSP, "solve_accounted_from_tour", exhausted)
    with pytest.raises(CompositionError, match="polish stage"):
        run_composition(
            SYM12,
            global_stage=_stub_global(SYM12, 2, IDENTITY12),
            polish_stage=spec,
        )


# ---- atomic-phase boundary -----------------------------------------------------

@pytest.mark.parametrize("remaining", [1, 2, 3])
def test_boundary_one_iteration_is_the_atomic_phase(remaining):
    # The global stage spends k, the polish stage gets the rest. One ALNS
    # iteration is the atomic phase (one candidate evaluation), so the polish
    # stage spends exactly the remainder, never one unit more. (The engine always
    # leaves at least one unit: floor(B * f) < B for f < 1; zero room is tested on
    # the entry itself in test_fresh_entry_with_no_room_returns_the_input_untouched.)
    k = 5
    budget = k + remaining
    out = run_composition(
        SYM12,
        global_stage=_stub_global(SYM12, k, IDENTITY12),
        polish_stage=alns_polish_stage(
            SYM12, dict(PARAMS, max_iterations=500), protocol_version="p1", run_seed=7
        ),
        evaluation_budget=budget,
        global_fraction=0.9,
    )
    assert out.polish_stage.consumed_evaluations == remaining
    assert out.evaluations == budget
    assert out.termination_reason == "evaluation_budget_exhausted"
    assert out.polish_stage.allocated_evaluations == remaining


def test_asymmetric_matrix_keeps_directed_costs():
    tour = list(range(8))
    out = run_composition(
        ASYM8,
        global_stage=_stub_global(ASYM8, 2, tour),
        polish_stage=alns_polish_stage(
            ASYM8, dict(PARAMS, max_iterations=80), protocol_version="p1", run_seed=3
        ),
        evaluation_budget=400,
        global_fraction=0.5,
    )
    assert out.cost == pytest.approx(closed_tour_cost(out.tour, ASYM8))
    assert out.cost <= closed_tour_cost(tour, ASYM8) + 1e-9


# ---- C-09 polish: deterministic never-worse on every return path ----------------

WORSE_FIXED = [0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 11]  # interleaved: far longer than the circle


class _AlwaysWorse:
    """Repair operator that ignores the partial tour and returns one fixed worse tour."""

    def repair(self, partial, removed, matrix):
        return list(WORSE_FIXED)


def _worse_only_solver(**overrides) -> ALNS_TSP:
    solver = ALNS_TSP(_config(**overrides))
    solver._repair_ops = tuple(_AlwaysWorse() for _ in solver._repair_ops)
    solver._accept = lambda current, new, temp: True  # the walk always follows the worse tour
    return solver


@pytest.mark.parametrize(
    "overrides,limit,expected",
    [
        (dict(iterations=15, max_no_improve=10_000), 6, "evaluation_budget_exhausted"),
        (dict(iterations=500, max_no_improve=4), None, "stagnation_limit"),
        (dict(iterations=9, max_no_improve=10_000), None, "max_iterations"),
    ],
)
def test_never_worse_holds_on_every_return_path_when_every_candidate_is_worse(
    overrides, limit, expected
):
    cost = closed_tour_cost(IDENTITY12, CIRCLE12)
    assert closed_tour_cost(WORSE_FIXED, CIRCLE12) > cost  # the fixture really is worse
    result = _worse_only_solver(**overrides).solve_accounted_from_tour(
        CIRCLE12, list(IDENTITY12), cost, ObjectiveEvaluationBudget(limit)
    )
    assert result.termination_reason == expected
    assert result.iterations >= 1  # candidates were really generated and accepted
    assert result.route == IDENTITY12
    assert result.cost == cost


def test_derive_polish_seed_golden_literal_catches_a_silent_encoding_change():
    # computed once from the documented encoding; a change of separators, field order,
    # digest slice or the right shift changes this value (and is a new variant, rule 9)
    assert derive_polish_seed("uniride-fair-tsp-v2", 1000) == 5272418355014093478
