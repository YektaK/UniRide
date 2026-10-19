"""L8: the fixed-budget local-search executor reports the solver's own termination reason.

When the last permitted iteration is the one that finds no improving move, the search stopped because it
converged (``no_improving_move``), not because it was cut off (``max_iterations``). The executor used to
re-derive the label from ``iterations >= max_iterations`` and reported ``max_iterations`` in that case.
"""
from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance

ALGORITHMS = ("Core-TwoOpt-TSP", "Core-ThreeOpt-TSP")


def _problem() -> ProblemInstance:
    matrix = [[float(abs(i - j)) for j in range(6)] for i in range(6)]
    return ProblemInstance(
        name="l8-line-6", dimension=6, coordinates=[], problem_type="tsp", dist_matrix=matrix,
    )


def _run(algorithm: str, max_iterations: int, budget: int = 100_000):
    params = {
        "fair_comparison": {"evaluation_budget": budget, "base_seed": 77},
        "max_iterations": max_iterations,
    }
    return AlgorithmRegistry.get_executor(algorithm)(_problem(), params, seed=999, run_idx=0)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_convergence_on_the_last_permitted_iteration_is_no_improving_move(algorithm):
    probe = _run(algorithm, max_iterations=1000)
    assert probe.termination_reason == "no_improving_move"
    converged_at = probe.iterations
    assert converged_at >= 2, "the start route must need at least one improving move"

    result = _run(algorithm, max_iterations=converged_at)

    assert result.iterations == converged_at
    assert result.termination_reason == "no_improving_move"
    assert result.tour_cost == probe.tour_cost
    assert result.evaluations == probe.evaluations


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_cut_off_before_convergence_is_max_iterations(algorithm):
    probe = _run(algorithm, max_iterations=1000)
    cut = _run(algorithm, max_iterations=probe.iterations - 1)
    assert cut.termination_reason == "max_iterations"


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_exhausted_budget_is_evaluation_budget_exhausted(algorithm):
    result = _run(algorithm, max_iterations=1000, budget=10)
    assert result.termination_reason == "evaluation_budget_exhausted"
    assert result.budget_terminated is True
