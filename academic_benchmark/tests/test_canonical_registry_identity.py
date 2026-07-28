from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401 - register executors
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance


CANONICAL_TSP_ALGORITHMS = (
    ("Core-TwoOpt-TSP", {"max_iterations": 12}),
    ("Core-ThreeOpt-TSP", {"max_iterations": 12}),
    ("Core-OrOpt-TSP", {"max_iterations": 12}),
    ("ALNS-TSP", {"iterations": 8, "max_no_improve": 4}),
)


def _tiny_directed_problem() -> ProblemInstance:
    return ProblemInstance(
        name="canonical_registry_atsp_4",
        dimension=4,
        coordinates=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        optimal=None,
        category="tiny",
        problem_type="atsp",
        dist_matrix=[
            [0.0, 1.0, 2.0, 1.0],
            [1.0, 0.0, 1.0, 2.0],
            [2.0, 1.0, 0.0, 1.0],
            [1.0, 2.0, 1.0, 0.0],
        ],
    )


def _closed_cost(one_indexed_tour: list[int], matrix: list[list[float]]) -> float:
    return sum(
        matrix[node - 1][one_indexed_tour[(index + 1) % len(one_indexed_tour)] - 1]
        for index, node in enumerate(one_indexed_tour)
    )


def test_canonical_tsp_registry_exposes_exact_executor_keys():
    algorithms = set(AlgorithmRegistry.list_algorithms())

    assert {algorithm for algorithm, _ in CANONICAL_TSP_ALGORITHMS}.issubset(algorithms)


@pytest.mark.parametrize(("canonical_id", "params"), CANONICAL_TSP_ALGORITHMS)
def test_canonical_tsp_executors_report_canonical_identity_and_closed_cycle_cost(
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
    problem = _tiny_directed_problem()

    result = AlgorithmRegistry.get_executor("SOTA-ALNS-TSP")(
        problem,
        {"iterations": 8, "max_no_improve": 4},
        seed=123,
        run_idx=0,
    )

    assert result.algorithm == "SOTA-ALNS-TSP"
