"""C-16b evidence: canonical pure PSO with exact objective accounting.

Swarm initialization is one atomic phase (swarm_size evaluations); each iteration is
one atomic phase of swarm_size evaluations (every particle moves and is evaluated once);
the optional diversity re-initialization is its OWN atomic phase of swarm_size
evaluations, run only when that bound fits the remaining budget, and carries no 2-opt.
No local search runs inside the solver. Costs of asymmetric matrices are recomputed
with directed arcs.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import (
    FairComparisonManifest,
    FairnessValidationError,
)
from academic_benchmark.native_protocol import NativeComparisonManifest

SWARM = 6  # evaluations of the init phase, of one iteration phase and of one re-init phase
BASE_SEED = 313

SYMMETRIC_7 = [
    [0.0, 4.0, 8.0, 7.0, 3.0, 6.0, 5.0],
    [4.0, 0.0, 5.0, 9.0, 6.0, 4.0, 7.0],
    [8.0, 5.0, 0.0, 2.0, 7.0, 3.0, 6.0],
    [7.0, 9.0, 2.0, 0.0, 4.0, 5.0, 8.0],
    [3.0, 6.0, 7.0, 4.0, 0.0, 8.0, 2.0],
    [6.0, 4.0, 3.0, 5.0, 8.0, 0.0, 9.0],
    [5.0, 7.0, 6.0, 8.0, 2.0, 9.0, 0.0],
]
ASYMMETRIC_7 = [
    [0.0, 2.0, 9.0, 7.0, 6.0, 5.0, 8.0],
    [8.0, 0.0, 3.0, 9.0, 2.0, 7.0, 4.0],
    [5.0, 6.0, 0.0, 2.0, 8.0, 4.0, 9.0],
    [4.0, 7.0, 6.0, 0.0, 2.0, 9.0, 3.0],
    [9.0, 3.0, 7.0, 8.0, 0.0, 2.0, 6.0],
    [3.0, 8.0, 5.0, 4.0, 6.0, 0.0, 7.0],
    [6.0, 5.0, 4.0, 3.0, 9.0, 8.0, 0.0],
]
CONSTANT_7 = [[0.0 if i == j else 1.0 for j in range(7)] for i in range(7)]
MATRICES = {"symmetric": SYMMETRIC_7, "asymmetric": ASYMMETRIC_7}


@dataclass
class _Problem:
    name: str
    problem_type: str
    dist_matrix: list[list[float]]
    optimal: float | None = None
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)


SYMMETRIC_TSP = _Problem("c16b-pso-symmetric-tsp-7", "tsp", SYMMETRIC_7)
DIRECTED_ATSP = _Problem("c16b-pso-directed-atsp-7", "atsp", ASYMMETRIC_7)

PSO_PARAMS = {
    "swarm_size": SWARM,
    "max_iterations": 4,
    "max_no_improvement": 3,
    "inertia_weight": 0.729,
    "cognitive_coeff": 1.49445,
    "social_coeff": 1.49445,
    "max_velocity_size": 3,
    "reinit_interval": 2,
}
NO_POLISH = {
    "enabled": False, "initial": False, "periodic": False, "final": False,
    "operator": None,
}


def _directed_cost(route: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[node][route[(i + 1) % len(route)]] for i, node in enumerate(route))


def _counting_solver(**overrides):
    """A PSOOptimizer whose objective calls are counted independently of its budget."""
    from uniride_core.algorithms.tsp_matrix_metaheuristics import PSOOptimizer

    class Counting(PSOOptimizer):
        calls = 0

        def _tour_length_fast(self, tour):
            type(self).calls += 1
            return super()._tour_length_fast(tour)

    values = dict(
        swarm_size=SWARM, max_iterations=50, max_no_improvement=1000,
        inertia_weight=0.729, cognitive_coeff=1.49445, social_coeff=1.49445,
        max_velocity_size=3, reinit_interval=0, random_seed=17,
    )
    values.update(overrides)
    Counting.calls = 0
    return Counting(**values)


def _solve(matrix, **overrides):
    solver = _counting_solver(**overrides)
    result = solver.solve_with_matrix(matrix, recalculate=False, closed_tsp=True)
    return solver, result


@pytest.mark.parametrize("kind", sorted(MATRICES))
@pytest.mark.parametrize("reinit_interval", [0, 2])
def test_objective_evaluations_equal_independent_count_and_never_exceed_budget(
    kind, reinit_interval
) -> None:
    matrix = MATRICES[kind]
    for budget in (6, 11, 12, 17, 18, 23, 24, 25, 40, 200):
        solver, result = _solve(
            matrix, evaluation_budget=budget, reinit_interval=reinit_interval
        )
        stats = result.extra_stats
        assert stats["objective_evaluations"] == type(solver).calls
        assert stats["objective_evaluations"] <= budget
        assert stats["evaluation_budget"] == budget
        # init phase + one phase per completed iteration + one per executed re-init
        assert stats["objective_evaluations"] == SWARM * (
            1 + result.iterations + stats["diversity_reinit_phases"]
        )
        assert stats["diversity_reinit_evaluations"] == SWARM * stats["diversity_reinit_phases"]
    solver, result = _solve(
        matrix, evaluation_budget=None, max_iterations=5, reinit_interval=reinit_interval
    )
    assert result.extra_stats["objective_evaluations"] == type(solver).calls
    assert type(solver).calls == SWARM * (
        1 + 5 + result.extra_stats["diversity_reinit_phases"]
    )


@pytest.mark.parametrize("kind", sorted(MATRICES))
@pytest.mark.parametrize(
    ("budgets", "expected"),
    [
        # one below, exactly at, one above the first iteration phase (6 + 6 = 12)
        ((11, 12, 13), (6, 12, 12)),
        # and around the second iteration phase (6 + 6 + 6 = 18)
        ((17, 18, 19), (12, 18, 18)),
    ],
)
def test_iteration_phase_boundary_triplet(kind, budgets, expected) -> None:
    matrix = MATRICES[kind]
    for budget, evaluations in zip(budgets, expected):
        _, result = _solve(matrix, evaluation_budget=budget)
        stats = result.extra_stats
        assert stats["objective_evaluations"] == evaluations
        assert stats["budget_terminated"] is True
        assert stats["termination_reason"] == "evaluation_budget_exhausted"
        assert result.iterations == (evaluations - SWARM) // SWARM
        assert stats["diversity_reinit_phases"] == 0


@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_reinit_phase_is_its_own_atomic_phase_with_a_boundary_triplet(kind) -> None:
    matrix = MATRICES[kind]
    # reinit_interval=2: init 6, iter 12, iter 18, re-init 24, iter 30
    for budget, evaluations, reinits in (
        ((23), 18, 0),  # one below the re-init phase: it must not start
        ((24), 24, 1),  # exactly at: it runs, the next iteration does not fit
        ((25), 24, 1),  # one above: same
        ((29), 24, 1),
        ((30), 30, 1),  # the iteration after the re-init fits exactly
    ):
        _, result = _solve(matrix, evaluation_budget=budget, reinit_interval=2)
        stats = result.extra_stats
        assert stats["objective_evaluations"] == evaluations
        assert stats["diversity_reinit_phases"] == reinits
        assert stats["termination_reason"] == "evaluation_budget_exhausted"
        assert stats["objective_evaluations"] <= budget


def test_reinit_runs_every_interval_and_not_after_the_last_iteration() -> None:
    solver, result = _solve(
        SYMMETRIC_7, evaluation_budget=None, max_iterations=6, reinit_interval=2
    )
    # after iterations 2 and 4; the one after iteration 6 would be the last phase
    assert result.iterations == 6
    assert result.extra_stats["diversity_reinit_phases"] == 2
    assert type(solver).calls == SWARM * (1 + 6 + 2)
    _, disabled = _solve(
        SYMMETRIC_7, evaluation_budget=None, max_iterations=6, reinit_interval=0
    )
    assert disabled.extra_stats["diversity_reinit_phases"] == 0


def test_budget_smaller_than_initialization_phase_is_rejected_before_any_evaluation() -> None:
    solver = _counting_solver(evaluation_budget=SWARM - 1)
    with pytest.raises(ValueError, match="atomic swarm initialization"):
        solver.solve_with_matrix(SYMMETRIC_7, recalculate=False, closed_tsp=True)
    assert type(solver).calls == 0


@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_same_seed_replays_route_cost_count_and_termination(kind) -> None:
    matrix = MATRICES[kind]
    for budget in (24, None):
        runs = [
            _solve(
                matrix, evaluation_budget=budget, max_iterations=5,
                max_no_improvement=3, reinit_interval=2,
            )[1]
            for _ in range(2)
        ]
        first, second = runs
        assert second.tour == first.tour
        assert second.tour_length == first.tour_length
        assert second.extra_stats["objective_evaluations"] == first.extra_stats["objective_evaluations"]
        assert second.extra_stats["termination_reason"] == first.extra_stats["termination_reason"]
        assert second.history == first.history


def test_asymmetric_cost_is_recomputed_with_directed_arcs() -> None:
    for seed in range(5):
        _, result = _solve(ASYMMETRIC_7, evaluation_budget=40, random_seed=seed)
        assert sorted(result.tour) == list(range(7))
        assert result.tour_length == pytest.approx(_directed_cost(result.tour, ASYMMETRIC_7))
        reverse = list(reversed(result.tour))
        # the matrix is genuinely asymmetric: the reverse orientation costs something else
        assert _directed_cost(reverse, ASYMMETRIC_7) != pytest.approx(result.tour_length)


def test_native_mode_is_uncapped_and_reports_max_iterations() -> None:
    _, result = _solve(SYMMETRIC_7, evaluation_budget=None, max_iterations=3)
    stats = result.extra_stats
    assert stats["evaluation_budget"] is None
    assert stats["budget_terminated"] is False
    assert stats["termination_reason"] == "max_iterations"
    assert result.iterations == 3


def test_max_no_improvement_termination_is_reported() -> None:
    # every tour costs the same, so no iteration can improve the best
    _, result = _solve(CONSTANT_7, evaluation_budget=None, max_iterations=50, max_no_improvement=2)
    assert result.extra_stats["termination_reason"] == "max_no_improvement"
    assert result.iterations == 2
    assert result.extra_stats["objective_evaluations"] == SWARM * 3


def test_solver_has_no_local_search_and_exposes_reusable_hooks() -> None:
    from uniride_core.algorithms.tsp_matrix_metaheuristics import PSOOptimizer

    _, result = _solve(SYMMETRIC_7, evaluation_budget=None, max_iterations=3)
    assert result.extra_stats["variant"] == "pure"
    assert result.extra_stats["polish_executed"] == {"initial": 0, "periodic": 0, "final": 0}
    assert result.params["memetic"] is False
    for hook in ("initialize_swarm", "move_swarm", "reinitialize_swarm"):
        assert callable(getattr(PSOOptimizer, hook))
    # a particle position is never replaced by a 2-opt result: the solver does not import it
    import inspect

    from uniride_core.algorithms.tsp_matrix_metaheuristics import pso_solver

    source = inspect.getsource(pso_solver)
    assert "two_opt" not in source


# ----- registry executor: the four claim evidence tests (TSP/ATSP x fixed/native) -----

def _fixed_params(evaluation_budget: int) -> dict[str, object]:
    return {
        **PSO_PARAMS,
        "fair_comparison": {
            "evaluation_budget": evaluation_budget,
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }


def _native_params() -> dict[str, object]:
    return {
        **PSO_PARAMS,
        "native_comparison": {
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        },
    }


def _require_live_numba_objective() -> None:
    from academic_benchmark.core.preflight import probe_runtime_backends

    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail


def _assert_row_common(row, problem: _Problem, expected_seed: int) -> None:
    matrix = problem.dist_matrix
    assert row.algorithm == row.algorithm_id == "Core-PSO-TSP"
    assert row.algorithm_family == "PSO"
    assert row.variant == "pure"
    assert row.seed == expected_seed
    assert row.initialization_policy == "paired_seed_random_swarm_all_nodes"
    assert row.acceptance_policy == "population_evolution"
    assert row.neighborhood_window is None
    assert row.polish_policy == NO_POLISH
    assert row.execution_backend == "objective=numba;polish=none"
    assert sorted(row.tour) == list(range(1, len(matrix) + 1))
    route = [node - 1 for node in row.tour]
    assert row.tour_cost == pytest.approx(_directed_cost(route, matrix))
    assert row.objective_cost == pytest.approx(_directed_cost(route, matrix))
    assert row.evaluations == row.objective_evaluations


def _assert_fixed_evidence(problem: _Problem, *, expected_problem_type: str) -> None:
    _require_live_numba_objective()
    assert problem.problem_type == expected_problem_type
    executor = AlgorithmRegistry.get_executor("Core-PSO-TSP")
    manifest = FairComparisonManifest.from_value(_fixed_params(1)["fair_comparison"])
    expected_seed = manifest.paired_seed(problem.name, 0)

    init_only = executor(problem, _fixed_params(SWARM), seed=987_654, run_idx=0)
    # init 6 + 2 iterations 12 + one re-init phase 6 (reinit_interval=2)
    budget = SWARM * 4
    first = executor(problem, _fixed_params(budget), seed=987_654, run_idx=0)
    replay = executor(problem, _fixed_params(budget), seed=123_456, run_idx=0)

    _assert_row_common(init_only, problem, expected_seed)
    assert init_only.evaluation_budget == SWARM
    assert init_only.evaluations == SWARM
    assert init_only.iterations == 0
    assert init_only.budget_terminated is True
    assert init_only.termination_reason == "evaluation_budget_exhausted"

    _assert_row_common(first, problem, expected_seed)
    assert first.evaluation_budget == budget
    assert first.evaluations == budget
    assert first.iterations == 2
    assert first.budget_terminated is True
    assert first.termination_reason == "evaluation_budget_exhausted"
    assert "reinit_interval=2" in first.termination_policy

    assert replay.seed == expected_seed
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.iterations == first.iterations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend


def _assert_native_evidence(problem: _Problem, *, expected_problem_type: str) -> None:
    _require_live_numba_objective()
    assert problem.problem_type == expected_problem_type
    executor = AlgorithmRegistry.get_executor("Core-PSO-TSP")
    params = _native_params()
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])
    expected_seed = manifest.paired_seed(problem.name, 0)

    first = executor(problem, params, seed=987_654, run_idx=0)
    replay = executor(problem, params, seed=123_456, run_idx=0)

    _assert_row_common(first, problem, expected_seed)
    assert first.evaluation_budget is None
    assert first.budget_terminated is False
    assert first.termination_reason in {"max_iterations", "stagnation_limit"}
    # re-init after iteration 2 only while the run continues (none after the last one)
    reinit_phases = (first.iterations - 1) // 2
    # init + iterations + re-init phases
    assert first.evaluations == SWARM * (1 + first.iterations + reinit_phases)
    assert replay.seed == expected_seed
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.iterations == first.iterations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend


def test_pso_fixed_tsp_evidence() -> None:
    _assert_fixed_evidence(SYMMETRIC_TSP, expected_problem_type="tsp")


def test_pso_fixed_atsp_evidence() -> None:
    _assert_fixed_evidence(DIRECTED_ATSP, expected_problem_type="atsp")


def test_pso_native_tsp_evidence() -> None:
    _assert_native_evidence(SYMMETRIC_TSP, expected_problem_type="tsp")


def test_pso_native_atsp_evidence() -> None:
    _assert_native_evidence(DIRECTED_ATSP, expected_problem_type="atsp")


# ----- strict scientific parameter schema -----

def test_validate_scientific_pso_params_accepts_exact_schema() -> None:
    from academic_benchmark.fairness import validate_scientific_pso_params

    assert validate_scientific_pso_params(dict(PSO_PARAMS)) == PSO_PARAMS


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("swarm_size"),
        lambda p: p.pop("reinit_interval"),
        lambda p: p.update(extra_knob=1),
        lambda p: p.update(final_polish_iters=300),
        lambda p: p.update(swarm_size=1),
        lambda p: p.update(swarm_size=True),
        lambda p: p.update(max_iterations=0),
        lambda p: p.update(max_no_improvement=0),
        lambda p: p.update(max_velocity_size=0),
        lambda p: p.update(reinit_interval=-1),
        lambda p: p.update(reinit_interval=1.5),
        lambda p: p.update(inertia_weight=-0.1),
        lambda p: p.update(inertia_weight=1.5),
        lambda p: p.update(cognitive_coeff=float("nan")),
        lambda p: p.update(social_coeff=-1.0),
    ],
)
def test_validate_scientific_pso_params_rejects_invalid_schema(mutate) -> None:
    from academic_benchmark.fairness import validate_scientific_pso_params

    params = dict(PSO_PARAMS)
    mutate(params)
    with pytest.raises(ValueError):
        validate_scientific_pso_params(params)


def test_protocol_executor_rejects_unknown_and_missing_pso_parameters() -> None:
    executor = AlgorithmRegistry.get_executor("Core-PSO-TSP")
    unknown = {**_fixed_params(20), "polish_iters": 10}
    with pytest.raises(ValueError, match="PSO parameter schema mismatch"):
        executor(SYMMETRIC_TSP, unknown, seed=1, run_idx=0)
    missing = _fixed_params(20)
    missing.pop("reinit_interval")
    with pytest.raises(ValueError, match="PSO parameter schema mismatch"):
        executor(SYMMETRIC_TSP, missing, seed=1, run_idx=0)
    native_unknown = {**_native_params(), "hybrid_2opt": True}
    with pytest.raises(ValueError, match="PSO parameter schema mismatch"):
        executor(SYMMETRIC_TSP, native_unknown, seed=1, run_idx=0)


def test_pso_manifests_reject_foreign_variants_and_reasons() -> None:
    from academic_benchmark.fairness import FairRunResult

    executor = AlgorithmRegistry.get_executor("Core-PSO-TSP")
    _require_live_numba_objective()
    row = executor(SYMMETRIC_TSP, _fixed_params(SWARM + SWARM), seed=1, run_idx=0)
    manifest = FairComparisonManifest.from_value(_fixed_params(SWARM + SWARM)["fair_comparison"])
    manifest.validate_result(row)
    assert isinstance(row, FairRunResult)
    row.variant = "memetic_2opt"
    with pytest.raises(FairnessValidationError):
        manifest.validate_result(row)
    row.variant = "pure"
    row.termination_reason = "no_improving_move"
    with pytest.raises(FairnessValidationError, match="PSO fixed termination_reason"):
        manifest.validate_result(row)


def test_native_manifest_rejects_foreign_pso_termination_reason() -> None:
    executor = AlgorithmRegistry.get_executor("Core-PSO-TSP")
    _require_live_numba_objective()
    params = _native_params()
    row = executor(SYMMETRIC_TSP, params, seed=1, run_idx=0)
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])
    manifest.validate_result(row)
    row.termination_reason = "evaluation_budget_exhausted"
    with pytest.raises(FairnessValidationError, match="PSO native termination_reason"):
        manifest.validate_result(row)


# ----- pilot allowlists: Core-PSO-TSP is an optional, strictly validated member -----

def _pilot_algorithm_blocks() -> dict[str, dict]:
    alns = {
        "max_iterations": 8, "max_no_improvement": 3, "remove_ratio": 0.34,
        "min_remove": 2, "segment_length": 2, "weight_update_factor": 0.8,
        "use_sa": True, "sa_start_temp": 5.0, "sa_cooling_rate": 0.9,
    }
    return {
        "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 10},
        "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "dive_count": 0, "max_no_improvement": 10},
        "Core-TwoOpt-TSP": {"max_iterations": 20, "first_improvement": False},
        "Core-ThreeOpt-TSP": {"max_iterations": 20, "first_improvement": False, "window": 4},
        "Core-OrOpt-TSP": {"max_iterations": 3, "first_improvement": False, "window": 3},
        "ALNS-TSP": alns,
    }


def _write(tmp_path, name, value):
    import json

    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _fair_pilot_config(blocks):
    blocks = {k: v for k, v in blocks.items() if k != "Core-OrOpt-TSP"}
    return {
        "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget",
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": blocks,
        "runs": 1,
        "evaluation_budget": 100,
        "base_seed": 17,
        "budget_policy": "atomic_upper_bound_v1",
        "workers": 1,
        "replay_replicates": [],
        "allow_repository_output": False,
        "overwrite": False,
    }


def _native_pilot_config(blocks):
    return {
        "protocol_version": "uniride-native-tsp-v1",
        "comparison_regime": "algorithm_native_termination",
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": blocks,
        "runs": 1,
        "base_seed": 71,
        "workers": 1,
        "replay_replicates": [0],
        "allow_repository_output": False,
        "overwrite": False,
    }


def test_fair_pilot_accepts_optional_pso_block_and_rejects_bad_ones(tmp_path) -> None:
    from academic_benchmark.fair_pilot import FairPilotError, load_fair_pilot_config

    blocks = _pilot_algorithm_blocks()
    without = load_fair_pilot_config(_write(tmp_path, "a.json", _fair_pilot_config(blocks)))
    assert "Core-PSO-TSP" not in without.algorithms
    with_pso = load_fair_pilot_config(
        _write(tmp_path, "b.json", _fair_pilot_config({**blocks, "Core-PSO-TSP": dict(PSO_PARAMS)}))
    )
    assert with_pso.algorithms["Core-PSO-TSP"] == PSO_PARAMS
    for bad in (
        {**PSO_PARAMS, "polish_iters": 10},
        {k: v for k, v in PSO_PARAMS.items() if k != "swarm_size"},
    ):
        with pytest.raises(FairPilotError, match="Core-PSO-TSP"):
            load_fair_pilot_config(
                _write(tmp_path, "c.json", _fair_pilot_config({**blocks, "Core-PSO-TSP": bad}))
            )


def test_native_pilot_accepts_optional_pso_block_and_rejects_bad_ones(tmp_path) -> None:
    from academic_benchmark.native_pilot import NativePilotError, load_native_pilot_config

    blocks = _pilot_algorithm_blocks()
    without = load_native_pilot_config(_write(tmp_path, "a.json", _native_pilot_config(blocks)))
    assert "Core-PSO-TSP" not in without.algorithms
    with_pso = load_native_pilot_config(
        _write(tmp_path, "b.json", _native_pilot_config({**blocks, "Core-PSO-TSP": dict(PSO_PARAMS)}))
    )
    assert with_pso.algorithms["Core-PSO-TSP"] == PSO_PARAMS
    for bad in (
        {**PSO_PARAMS, "final_polish_iters": 300},
        {k: v for k, v in PSO_PARAMS.items() if k != "reinit_interval"},
        {**PSO_PARAMS, "swarm_size": 1},
    ):
        with pytest.raises(NativePilotError, match="Core-PSO-TSP"):
            load_native_pilot_config(
                _write(tmp_path, "c.json", _native_pilot_config({**blocks, "Core-PSO-TSP": bad}))
            )


# ----- published capability claims (C-16b promotion) -----

def test_pso_claims_cite_all_four_focused_evidence_nodes() -> None:
    from pathlib import Path

    from uniride_core.algorithms.capabilities import (
        BackendKind,
        CompositionKind,
        ExecutionProtocol,
        LifecycleStatus,
        ProblemContract,
        get_algorithm_capability,
    )

    capability = get_algorithm_capability("Core-PSO-TSP")
    assert capability is not None
    assert capability.lifecycle is LifecycleStatus.VERIFIED
    prefix = "academic_benchmark/tests/test_pso_evidence.py::"
    assert {e for claim in capability.claims for e in claim.evidence_ids} == {
        prefix + "test_pso_fixed_tsp_evidence",
        prefix + "test_pso_fixed_atsp_evidence",
        prefix + "test_pso_native_tsp_evidence",
        prefix + "test_pso_native_atsp_evidence",
    }
    assert {(claim.problem, claim.protocol) for claim in capability.claims} == {
        (problem, protocol)
        for problem in (ProblemContract.TSP, ProblemContract.ATSP)
        for protocol in (ExecutionProtocol.FIXED_BUDGET, ExecutionProtocol.NATIVE_TERMINATION)
    }
    for claim in capability.claims:
        assert claim.composition is CompositionKind.PURE
        assert claim.backend_profile.objective is BackendKind.NUMBA_NOPYTHON
        assert claim.backend_profile.polish is BackendKind.NONE
        assert claim.directed_cost_preserved is (claim.problem is ProblemContract.ATSP)
        assert claim.exact_objective_accounting and claim.fixed_seed_deterministic
        assert claim.truthful_result_reporting
        for evidence_id in claim.evidence_ids:
            path, _, function = evidence_id.partition("::")
            source = (Path(__file__).resolve().parents[2] / path).read_text(encoding="utf-8")
            assert f"def {function}(" in source
