"""Neutral objective-evaluation accounting for matrix local search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from uniride_core.algorithms.three_opt import closed_tour_cost, is_symmetric_matrix


class EvaluationBudgetExhausted(RuntimeError):
    """Raised before an objective evaluation that would exceed its budget."""


@dataclass
class ObjectiveEvaluationBudget:
    """Count complete candidate-tour objective evaluations exactly."""

    limit: Optional[int] = None
    used: int = 0

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 1:
            raise ValueError("evaluation budget must be a positive integer")
        if self.used < 0 or (self.limit is not None and self.used > self.limit):
            raise ValueError("invalid initial evaluation count")

    @property
    def remaining(self) -> Optional[int]:
        return None if self.limit is None else self.limit - self.used

    def can_spend(self, count: int = 1) -> bool:
        if count < 0:
            raise ValueError("evaluation count cannot be negative")
        return self.limit is None or self.used + count <= self.limit

    def consume(self, count: int = 1) -> None:
        if not self.can_spend(count):
            raise EvaluationBudgetExhausted(
                f"objective evaluation budget exhausted: used={self.used}, "
                f"requested={count}, limit={self.limit}"
            )
        self.used += count

    def evaluate(self, route: Sequence[int], matrix: Sequence[Sequence[float]]) -> float:
        self.consume()
        return closed_tour_cost(route, matrix)


@dataclass(frozen=True)
class BudgetedSearchResult:
    route: List[int]
    cost: float
    iterations: int
    evaluations: int
    budget_exhausted: bool
    mode: str
    termination_reason: str = ""


def two_opt_evaluation_upper_bound(route_size: int, max_iterations: int) -> int:
    """Worst-case complete-tour evaluations, including the initial route."""
    pairs = route_size * max(0, route_size - 1) // 2
    return 1 + max(0, max_iterations) * pairs


def improve_two_opt_budgeted(
    route: Sequence[int],
    matrix: Sequence[Sequence[float]],
    budget: ObjectiveEvaluationBudget,
    *,
    max_iterations: int,
    first_improvement: bool = False,
    initial_cost: Optional[float] = None,
) -> BudgetedSearchResult:
    """Matrix-exact 2-opt with one budget unit per complete candidate tour."""
    current = list(route)
    start_evaluations = budget.used
    if initial_cost is None:
        current_cost = budget.evaluate(current, matrix)
    else:
        current_cost = float(initial_cost)
    iterations = 0
    exhausted = False
    termination_reason = "max_iterations"

    while iterations < max_iterations:
        iterations += 1
        selected_route: Optional[List[int]] = None
        selected_cost = current_cost
        stop_scan = False
        for i in range(len(current) - 1):
            for j in range(i + 1, len(current)):
                if not budget.can_spend():
                    exhausted = True
                    stop_scan = True
                    break
                candidate = current[:i] + list(reversed(current[i:j + 1])) + current[j + 1:]
                candidate_cost = budget.evaluate(candidate, matrix)
                if candidate_cost < selected_cost:
                    selected_route = candidate
                    selected_cost = candidate_cost
                    if first_improvement:
                        stop_scan = True
                        break
            if stop_scan:
                break

        if selected_route is None:
            termination_reason = (
                "evaluation_budget_exhausted" if exhausted else "no_improving_move"
            )
            break
        current = selected_route
        current_cost = selected_cost
        if exhausted:
            termination_reason = "evaluation_budget_exhausted"
            break

    return BudgetedSearchResult(
        route=current,
        cost=current_cost,
        iterations=iterations,
        evaluations=budget.used - start_evaluations,
        budget_exhausted=exhausted,
        mode="two_opt",
        termination_reason=termination_reason,
    )

def improve_or_opt_budgeted(
    route: Sequence[int],
    matrix: Sequence[Sequence[float]],
    budget: ObjectiveEvaluationBudget,
    *,
    max_iterations: int,
    first_improvement: bool = False,
    max_segment_length: int = 3,
    initial_cost: Optional[float] = None,
) -> BudgetedSearchResult:
    """Budgeted first/best-improvement Or-opt for TSP and directed ATSP."""
    if max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")
    if isinstance(max_segment_length, bool) or not isinstance(max_segment_length, int):
        raise ValueError("max_segment_length must be an integer from 1 through 3")
    if not 1 <= max_segment_length <= 3:
        raise ValueError("max_segment_length must be an integer from 1 through 3")

    current = list(route)
    start_evaluations = budget.used
    if initial_cost is None:
        current_cost = budget.evaluate(current, matrix)
    else:
        current_cost = float(initial_cost)
    iterations = 0
    exhausted = False
    termination_reason = "max_iterations"

    while iterations < max_iterations:
        iterations += 1
        selected_route: Optional[List[int]] = None
        selected_cost = current_cost
        stop_scan = False
        max_segment = min(max_segment_length, len(current))

        for segment_length in range(1, max_segment + 1):
            for start in range(len(current) - segment_length + 1):
                segment = current[start:start + segment_length]
                remaining = current[:start] + current[start + segment_length:]
                for insertion in range(len(remaining) + 1):
                    if insertion == start:
                        continue
                    if not budget.can_spend():
                        exhausted = True
                        stop_scan = True
                        break
                    candidate = (
                        remaining[:insertion]
                        + segment
                        + remaining[insertion:]
                    )
                    candidate_cost = budget.evaluate(candidate, matrix)
                    if candidate_cost < selected_cost:
                        selected_route = candidate
                        selected_cost = candidate_cost
                        if first_improvement:
                            stop_scan = True
                            break
                if stop_scan:
                    break
            if stop_scan:
                break

        if selected_route is None:
            termination_reason = (
                "evaluation_budget_exhausted"
                if exhausted
                else "no_improving_move"
            )
            break
        current = selected_route
        current_cost = selected_cost
        if exhausted:
            termination_reason = "evaluation_budget_exhausted"
            break

    return BudgetedSearchResult(
        route=current,
        cost=current_cost,
        iterations=iterations,
        evaluations=budget.used - start_evaluations,
        budget_exhausted=exhausted,
        mode="symmetric_tsp" if is_symmetric_matrix(matrix) else "directed_atsp",
        termination_reason=termination_reason,
    )
