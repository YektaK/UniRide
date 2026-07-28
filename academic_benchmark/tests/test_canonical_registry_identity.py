from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401 - register executors
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance


CANONICAL_LOCAL_SEARCH_ALGORITHMS = (
    ("Core-TwoOpt-TSP", {"max_iterations": 12}),
    ("Core-ThreeOpt-TSP", {"max_iterations": 12}),
    ("Core-OrOpt-TSP", {"max_iterations": 12}),
)


def _tiny_directed_problem() -> ProblemInstance:
    return ProblemInstance(
        name="canonical_registry_atsp_4",
        dimension=4,
        coordinates=[],
        optimal=None,
        category="tiny",
        problem_type="atsp",
        dist_matrix=[
            [0.0, 1.0, 9.0, 5.0],
            [3.0, 0.0, 1.0, 8.0],
            [7.0, 4.0, 0.0, 1.0],
            [1.0, 6.0, 2.0, 0.0],
        ],
    )


def _fractional_directed_problem() -> ProblemInstance:
    return ProblemInstance(
        name="canonical_alns_atsp_4",
        dimension=4,
        coordinates=[],
        optimal=None,
        category="tiny",
        problem_type="atsp",
        dist_matrix=[
            [0.0, 1.25, 9.75, 3.5],
            [4.4, 0.0, 2.25, 8.75],
            [7.5, 5.6, 0.0, 1.1],
            [2.2, 6.4, 3.3, 0.0],
        ],
    )


def _closed_cost(one_indexed_tour: list[int], matrix: list[list[float]]) -> float:
    return sum(
        matrix[node - 1][one_indexed_tour[(index + 1) % len(one_indexed_tour)] - 1]
        for index, node in enumerate(one_indexed_tour)
    )


def test_canonical_tsp_registry_exposes_exact_executor_keys():
    algorithms = set(AlgorithmRegistry.list_algorithms())

    assert {*(algorithm for algorithm, _ in CANONICAL_LOCAL_SEARCH_ALGORITHMS), "ALNS-TSP"}.issubset(algorithms)


@pytest.mark.parametrize(("canonical_id", "params"), CANONICAL_LOCAL_SEARCH_ALGORITHMS)
def test_canonical_local_search_executors_report_canonical_identity_and_closed_cycle_cost(
    canonical_id: str, params: dict[str, int]
):
    problem = _tiny_directed_problem()

    result = AlgorithmRegistry.get_executor(canonical_id)(
        problem,
        params,
        seed=123,
        run_idx=0,
    )

    assert result.algorithm == canonical_id
    assert result.tour is not None
    assert sorted(result.tour) == list(range(1, problem.dimension + 1))
    assert result.tour_cost == pytest.approx(_closed_cost(result.tour, problem.dist_matrix))


def test_sota_alns_registry_key_preserves_historical_reported_identity():
    problem = _fractional_directed_problem()

    result = AlgorithmRegistry.get_executor("SOTA-ALNS-TSP")(
        problem,
        {"iterations": 8, "max_no_improve": 4},
        seed=123,
        run_idx=0,
    )

    assert result.algorithm == "SOTA-ALNS-TSP"


def test_canonical_alns_uses_explicit_fractional_directed_matrix_without_truncating_cost():
    problem = _fractional_directed_problem()

    result = AlgorithmRegistry.get_executor("ALNS-TSP")(
        problem,
        {"iterations": 8, "max_no_improve": 4},
        seed=123,
        run_idx=0,
    )

    assert result.algorithm == "ALNS-TSP"
    assert result.tour is not None
    assert sorted(result.tour) == list(range(1, problem.dimension + 1))
    expected_cost = _closed_cost(result.tour, problem.dist_matrix)
    assert expected_cost % 1 != 0
    assert result.tour_cost == pytest.approx(expected_cost)
    assert result.objective_cost == pytest.approx(expected_cost)
