"""C-16a evidence: canonical pure GA with exact objective accounting.

Population initialization is one atomic phase (population_size evaluations); each
generation is one atomic phase of ``population_size - elite_count`` offspring
evaluations that starts only when it fits the remaining budget. No local search runs
inside the solver. Costs of asymmetric matrices are recomputed with directed arcs.
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

POP = 6
ELITE = 2
OFFSPRING = POP - ELITE  # evaluations of one generation phase
BASE_SEED = 311

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


SYMMETRIC_TSP = _Problem("c16a-ga-symmetric-tsp-7", "tsp", SYMMETRIC_7)
DIRECTED_ATSP = _Problem("c16a-ga-directed-atsp-7", "atsp", ASYMMETRIC_7)

GA_PARAMS = {
    "population_size": POP,
    "max_iterations": 4,
    "max_no_improvement": 3,
    "crossover_rate": 0.85,
    "mutation_rate": 0.15,
    "elite_count": ELITE,
    "tournament_size": 3,
}
NO_POLISH = {
    "enabled": False, "initial": False, "periodic": False, "final": False,
    "operator": None,
}


def _directed_cost(route: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[node][route[(i + 1) % len(route)]] for i, node in enumerate(route))


def _counting_solver(**overrides):
    """A GAOptimizer whose objective calls are counted independently of its budget."""
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    class Counting(GAOptimizer):
        calls = 0

        def _tour_length_fast(self, tour):
            type(self).calls += 1
            return super()._tour_length_fast(tour)

    values = dict(
        population_size=POP, max_iterations=50, max_no_improvement=1000,
        crossover_rate=0.85, mutation_rate=0.15, elite_count=ELITE,
        tournament_size=3, random_seed=17,
    )
    values.update(overrides)
    Counting.calls = 0
    return Counting(**values)


def _solve(matrix, **overrides):
    solver = _counting_solver(**overrides)
    result = solver.solve_with_matrix(matrix, recalculate=False, closed_tsp=True)
    return solver, result


@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_objective_evaluations_equal_independent_count_and_never_exceed_budget(kind) -> None:
    matrix = MATRICES[kind]
    for budget in (6, 9, 10, 14, 19, 40, 200):
        solver, result = _solve(matrix, evaluation_budget=budget)
        stats = result.extra_stats
        assert stats["objective_evaluations"] == type(solver).calls
        assert stats["objective_evaluations"] <= budget
        assert stats["evaluation_budget"] == budget
        # init phase + one phase per completed generation, nothing else
        assert stats["objective_evaluations"] == POP + result.iterations * OFFSPRING
    solver, result = _solve(matrix, evaluation_budget=None, max_iterations=3)
    assert result.extra_stats["objective_evaluations"] == type(solver).calls
    assert type(solver).calls == POP + 3 * OFFSPRING


@pytest.mark.parametrize("kind", sorted(MATRICES))
@pytest.mark.parametrize(
    ("budgets", "expected"),
    [
        # one below, exactly at, one above the first generation phase (6 + 4 = 10)
        ((9, 10, 11), (6, 10, 10)),
        # and around the second generation phase (6 + 4 + 4 = 14)
        ((13, 14, 15), (10, 14, 14)),
    ],
)
def test_generation_phase_boundary_triplet(kind, budgets, expected) -> None:
    matrix = MATRICES[kind]
    for budget, evaluations in zip(budgets, expected):
        _, result = _solve(matrix, evaluation_budget=budget)
        stats = result.extra_stats
        assert stats["objective_evaluations"] == evaluations
        assert stats["budget_terminated"] is True
        assert stats["termination_reason"] == "evaluation_budget_exhausted"
        assert result.iterations == (evaluations - POP) // OFFSPRING


def test_budget_smaller_than_initialization_phase_is_rejected_before_any_evaluation() -> None:
    solver = _counting_solver(evaluation_budget=POP - 1)
    with pytest.raises(ValueError, match="atomic population initialization"):
        solver.solve_with_matrix(SYMMETRIC_7, recalculate=False, closed_tsp=True)
    assert type(solver).calls == 0


@pytest.mark.parametrize("kind", sorted(MATRICES))
def test_same_seed_replays_route_cost_count_and_termination(kind) -> None:
    matrix = MATRICES[kind]
    for budget in (14, None):
        _, first = _solve(matrix, evaluation_budget=budget, max_iterations=5, max_no_improvement=3)
        _, second = _solve(matrix, evaluation_budget=budget, max_iterations=5, max_no_improvement=3)
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
        undirected_like = _directed_cost(reverse, ASYMMETRIC_7)
        # the matrix is genuinely asymmetric: the reverse orientation costs something else
        assert undirected_like != pytest.approx(result.tour_length)


def test_native_mode_is_uncapped_and_reports_max_iterations() -> None:
    solver, result = _solve(SYMMETRIC_7, evaluation_budget=None, max_iterations=3)
    stats = result.extra_stats
    assert stats["evaluation_budget"] is None
    assert stats["budget_terminated"] is False
    assert stats["termination_reason"] == "max_iterations"
    assert result.iterations == 3


def test_max_no_improvement_termination_is_reported() -> None:
    # every tour costs the same, so no generation can improve the best
    _, result = _solve(CONSTANT_7, evaluation_budget=None, max_iterations=50, max_no_improvement=2)
    assert result.extra_stats["termination_reason"] == "max_no_improvement"
    assert result.iterations == 2
    assert result.extra_stats["objective_evaluations"] == POP + 2 * OFFSPRING


def test_solver_has_no_hidden_local_search_and_exposes_reusable_hooks() -> None:
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

    breeds = {"count": 0}

    class Hooked(GAOptimizer):
        def breed_generation(self, population):
            breeds["count"] += 1
            return super().breed_generation(population)

    solver = Hooked(
        population_size=POP, max_iterations=3, max_no_improvement=1000, elite_count=ELITE,
        random_seed=5,
    )
    result = solver.solve_with_matrix(SYMMETRIC_7, recalculate=False, closed_tsp=True)
    assert breeds["count"] == result.iterations == 3
    for hook in ("initialize_population", "breed_generation", "best_of"):
        assert callable(getattr(solver, hook))
    assert result.extra_stats["variant"] == "pure"
    assert result.extra_stats["polish_executed"] == {"initial": 0, "periodic": 0, "final": 0}
    assert result.extra_stats["objective_evaluations"] == POP + 3 * OFFSPRING


# ----- registry executor: the four claim evidence tests (TSP/ATSP x fixed/native) -----

def _fixed_params(evaluation_budget: int) -> dict[str, object]:
    return {
        **GA_PARAMS,
        "fair_comparison": {
            "evaluation_budget": evaluation_budget,
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }


def _native_params() -> dict[str, object]:
    return {
        **GA_PARAMS,
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
    assert row.algorithm == row.algorithm_id == "Core-GA-TSP"
    assert row.algorithm_family == "GA"
    assert row.variant == "pure"
    assert row.seed == expected_seed
    assert row.initialization_policy == "paired_seed_random_population_all_nodes"
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
    executor = AlgorithmRegistry.get_executor("Core-GA-TSP")
    manifest = FairComparisonManifest.from_value(_fixed_params(1)["fair_comparison"])
    expected_seed = manifest.paired_seed(problem.name, 0)

    init_only = executor(problem, _fixed_params(POP), seed=987_654, run_idx=0)
    budget = POP + 2 * OFFSPRING
    first = executor(problem, _fixed_params(budget), seed=987_654, run_idx=0)
    replay = executor(problem, _fixed_params(budget), seed=123_456, run_idx=0)

    _assert_row_common(init_only, problem, expected_seed)
    assert init_only.evaluation_budget == POP
    assert init_only.evaluations == POP
    assert init_only.iterations == 0
    assert init_only.budget_terminated is True
    assert init_only.termination_reason == "evaluation_budget_exhausted"

    _assert_row_common(first, problem, expected_seed)
    assert first.evaluation_budget == budget
    assert first.evaluations == budget
    assert first.iterations == 2
    assert first.budget_terminated is True
    assert first.termination_reason == "evaluation_budget_exhausted"

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
    executor = AlgorithmRegistry.get_executor("Core-GA-TSP")
    params = _native_params()
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])
    expected_seed = manifest.paired_seed(problem.name, 0)

    first = executor(problem, params, seed=987_654, run_idx=0)
    replay = executor(problem, params, seed=123_456, run_idx=0)

    _assert_row_common(first, problem, expected_seed)
    assert first.evaluation_budget is None
    assert first.budget_terminated is False
    assert first.termination_reason in {"max_iterations", "stagnation_limit"}
    assert first.evaluations == POP + first.iterations * OFFSPRING
    assert replay.seed == expected_seed
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.iterations == first.iterations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend


def test_ga_fixed_tsp_evidence() -> None:
    _assert_fixed_evidence(SYMMETRIC_TSP, expected_problem_type="tsp")


def test_ga_fixed_atsp_evidence() -> None:
    _assert_fixed_evidence(DIRECTED_ATSP, expected_problem_type="atsp")


def test_ga_native_tsp_evidence() -> None:
    _assert_native_evidence(SYMMETRIC_TSP, expected_problem_type="tsp")


def test_ga_native_atsp_evidence() -> None:
    _assert_native_evidence(DIRECTED_ATSP, expected_problem_type="atsp")


# ----- strict scientific parameter schema -----

def test_validate_scientific_ga_params_accepts_exact_schema() -> None:
    from academic_benchmark.fairness import validate_scientific_ga_params

    assert validate_scientific_ga_params(dict(GA_PARAMS)) == GA_PARAMS


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("population_size"),
        lambda p: p.pop("elite_count"),
        lambda p: p.update(extra_knob=1),
        lambda p: p.update(hybrid_2opt=True),
        lambda p: p.update(population_size=1),
        lambda p: p.update(population_size=True),
        lambda p: p.update(elite_count=POP),
        lambda p: p.update(tournament_size=0),
        lambda p: p.update(max_iterations=0),
        lambda p: p.update(crossover_rate=1.5),
        lambda p: p.update(mutation_rate=float("nan")),
    ],
)
def test_validate_scientific_ga_params_rejects_invalid_schema(mutate) -> None:
    from academic_benchmark.fairness import validate_scientific_ga_params

    params = dict(GA_PARAMS)
    mutate(params)
    with pytest.raises(ValueError):
        validate_scientific_ga_params(params)


def test_protocol_executor_rejects_unknown_and_missing_ga_parameters() -> None:
    executor = AlgorithmRegistry.get_executor("Core-GA-TSP")
    unknown = {**_fixed_params(20), "polish_iters": 10}
    with pytest.raises(ValueError, match="GA parameter schema mismatch"):
        executor(SYMMETRIC_TSP, unknown, seed=1, run_idx=0)
    missing = _fixed_params(20)
    missing.pop("tournament_size")
    with pytest.raises(ValueError, match="GA parameter schema mismatch"):
        executor(SYMMETRIC_TSP, missing, seed=1, run_idx=0)


def test_ga_manifests_reject_foreign_variants_and_reasons() -> None:
    from academic_benchmark.fairness import FairRunResult

    executor = AlgorithmRegistry.get_executor("Core-GA-TSP")
    _require_live_numba_objective()
    row = executor(SYMMETRIC_TSP, _fixed_params(POP + OFFSPRING), seed=1, run_idx=0)
    manifest = FairComparisonManifest.from_value(_fixed_params(POP + OFFSPRING)["fair_comparison"])
    manifest.validate_result(row)
    assert isinstance(row, FairRunResult)
    row.variant = "memetic_2opt"
    with pytest.raises(FairnessValidationError):
        manifest.validate_result(row)
    row.variant = "pure"
    row.termination_reason = "no_improving_move"
    with pytest.raises(FairnessValidationError, match="GA fixed termination_reason"):
        manifest.validate_result(row)
