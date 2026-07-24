"""Ownership and compatibility tests for neutral objective-budget primitives."""

import pytest

from academic_benchmark import fairness
from uniride_core.algorithms import objective_budget


def _directed_matrix():
    return [
        [0.0, 10.0, 1.0, 50.0],
        [1.0, 0.0, 10.0, 50.0],
        [50.0, 50.0, 0.0, 1.0],
        [1.0, 1.0, 50.0, 0.0],
    ]


def test_academic_fairness_reexports_core_budget_primitives():
    for name in (
        "EvaluationBudgetExhausted",
        "ObjectiveEvaluationBudget",
        "BudgetedSearchResult",
        "two_opt_evaluation_upper_bound",
        "improve_two_opt_budgeted",
    ):
        assert getattr(fairness, name) is getattr(objective_budget, name)


def test_budgeted_two_opt_includes_initial_objective_evaluation():
    budget = objective_budget.ObjectiveEvaluationBudget(10)

    result = objective_budget.improve_two_opt_budgeted(
        [0, 1, 2, 3], _directed_matrix(), budget, max_iterations=0
    )

    assert result.evaluations == 1
    assert budget.used == 1


def test_budget_consumption_is_atomic_at_its_cap():
    budget = objective_budget.ObjectiveEvaluationBudget(2)
    budget.consume(2)

    with pytest.raises(objective_budget.EvaluationBudgetExhausted):
        budget.consume()

    assert budget.used == 2


def test_budgeted_two_opt_uses_directed_closed_tour_cost():
    budget = objective_budget.ObjectiveEvaluationBudget(10)

    result = objective_budget.improve_two_opt_budgeted(
        [0, 1, 2, 3], _directed_matrix(), budget, max_iterations=0
    )

    assert result.cost == pytest.approx(22.0)


def test_first_improvement_stops_after_first_improving_candidate():
    budget = objective_budget.ObjectiveEvaluationBudget(10)

    result = objective_budget.improve_two_opt_budgeted(
        [0, 1, 2, 3],
        _directed_matrix(),
        budget,
        max_iterations=1,
        first_improvement=True,
    )

    assert result.route == [1, 0, 2, 3]
    assert result.evaluations == 2


def test_budgeted_two_opt_reports_exhaustion_without_overspending():
    budget = objective_budget.ObjectiveEvaluationBudget(2)

    result = objective_budget.improve_two_opt_budgeted(
        [0, 1, 2, 3], _directed_matrix(), budget, max_iterations=2
    )

    assert result.budget_exhausted is True
    assert result.termination_reason == "evaluation_budget_exhausted"
    assert result.evaluations == budget.used == 2
