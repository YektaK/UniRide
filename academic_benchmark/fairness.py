"""Reproducible fairness contract and budgeted TSP local-search adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List, Optional, Sequence

from academic_benchmark.engine_core import RunResult
from uniride_core.algorithms.objective_budget import (
    BudgetedSearchResult,
    EvaluationBudgetExhausted,
    ObjectiveEvaluationBudget,
    improve_two_opt_budgeted,
    two_opt_evaluation_upper_bound,
)
from uniride_core.algorithms.three_opt import (
    generate_three_opt_candidates,
    is_symmetric_matrix,
    iter_three_opt_cuts,
)


class FairnessValidationError(ValueError):
    """Raised when a result violates the fair-comparison contract."""


@dataclass
class FairRunResult(RunResult):
    """Backward-compatible RunResult carrying the academic fairness contract."""

    algorithm_id: str = ""
    algorithm_family: str = ""
    variant: str = ""
    seed_group: str = ""
    objective_evaluations: int = 0
    evaluation_budget: Optional[int] = None
    budget_terminated: bool = False
    initialization_policy: str = ""
    termination_policy: str = ""
    execution_backend: str = ""
    polish_policy: Dict[str, Any] = field(default_factory=dict)
    comparison_regime: str = ""
    acceptance_policy: str = ""
    neighborhood_window: Optional[int] = None
    termination_reason: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.algorithm_id:
            self.algorithm_id = self.algorithm
        if self.evaluations == 0 and self.objective_evaluations:
            self.evaluations = self.objective_evaluations
        elif self.objective_evaluations == 0 and self.evaluations:
            self.objective_evaluations = self.evaluations


@dataclass(frozen=True)
class FairComparisonManifest:
    """Common experiment budget, paired-seed protocol, and result validator."""

    evaluation_budget: int
    base_seed: int = 1000
    protocol_version: str = "uniride-fair-tsp-v1"
    budget_policy: str = "atomic_upper_bound_v1"
    comparison_regime: Optional[str] = None

    REQUIRED_RESULT_FIELDS = (
        "algorithm_id",
        "algorithm_family",
        "variant",
        "seed_group",
        "objective_evaluations",
        "evaluation_budget",
        "budget_terminated",
        "initialization_policy",
        "termination_policy",
        "execution_backend",
        "polish_policy",
    )
    ALGORITHM_FAMILIES = {
        "Core-GWO-TSP-Pure": "GWO",
        "Core-GWO-TSP-Memetic-2opt": "GWO",
        "Core-HHO-TSP-Pure": "HHO",
        "Core-HHO-TSP-Memetic-2opt": "HHO",
        "Core-TwoOpt-TSP": "2-opt",
        "Core-ThreeOpt-TSP": "3-opt",
        "Numba-2-opt": "2-opt",
        "Numba-3-opt-bounded": "3-opt",
        "Core-GWO-TSP": "GWO",
        "Core-HHO-TSP": "HHO",
        "Numba-GWO": "GWO",
        "Numba-HHO": "HHO",
    }
    POLISH_POLICY_FIELDS = ("enabled", "initial", "periodic", "final", "operator")
    V1_PROTOCOL = "uniride-fair-tsp-v1"
    V2_PROTOCOL = "uniride-fair-tsp-v2"
    FIXED_EVALUATION_REGIME = "fixed_evaluation_budget"
    NATIVE_TERMINATION_REGIME = "algorithm_native_termination"
    V2_RESULT_FIELDS = (
        "comparison_regime",
        "acceptance_policy",
        "neighborhood_window",
        "termination_reason",
    )
    TERMINATION_REASONS = frozenset({
        "evaluation_budget_exhausted",
        "max_iterations",
        "no_improving_move",
        "stagnation_limit",
    })

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_budget, int) or self.evaluation_budget < 1:
            raise ValueError("fair comparison evaluation_budget must be a positive integer")
        if self.budget_policy != "atomic_upper_bound_v1":
            raise ValueError(f"unsupported budget policy: {self.budget_policy}")
        if self.protocol_version not in {self.V1_PROTOCOL, self.V2_PROTOCOL}:
            raise ValueError(f"unsupported fair protocol_version: {self.protocol_version}")
        if self.protocol_version == self.V2_PROTOCOL:
            if self.comparison_regime == self.NATIVE_TERMINATION_REGIME:
                raise ValueError("algorithm_native_termination is not implemented")
            if self.comparison_regime != self.FIXED_EVALUATION_REGIME:
                raise ValueError(
                    "protocol v2 comparison_regime must be 'fixed_evaluation_budget'"
                )

    @classmethod
    def from_value(cls, value: Any) -> Optional["FairComparisonManifest"]:
        if value is None or value is False:
            return None
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise ValueError("fair_comparison must be a mapping or FairComparisonManifest")
        if "evaluation_budget" not in value:
            raise ValueError("fair_comparison requires evaluation_budget")
        return cls(
            evaluation_budget=int(value["evaluation_budget"]),
            base_seed=int(value.get("base_seed", 1000)),
            protocol_version=str(value.get("protocol_version", "uniride-fair-tsp-v1")),
            budget_policy=str(value.get("budget_policy", "atomic_upper_bound_v1")),
            comparison_regime=value.get("comparison_regime"),
        )

    def _seed_payload(self, problem: str, replicate: int) -> str:
        return (
            f"{self.protocol_version}|{self.base_seed}|"
            f"{normalize_problem(problem)}|{replicate}"
        )

    def paired_seed(self, problem: str, replicate: int) -> int:
        digest = hashlib.sha256(self._seed_payload(problem, replicate).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % 2_147_483_647

    def seed_group(self, problem: str, replicate: int) -> str:
        digest = hashlib.sha256(self._seed_payload(problem, replicate).encode("utf-8")).hexdigest()
        return f"{normalize_problem(problem)}:r{replicate}:{digest[:16]}"

    def validate_result(self, result: RunResult) -> None:
        errors: List[str] = []
        required_fields = self.REQUIRED_RESULT_FIELDS
        if self.protocol_version == self.V2_PROTOCOL:
            required_fields = required_fields + self.V2_RESULT_FIELDS
        for name in required_fields:
            value = getattr(result, name, None)
            if name == "neighborhood_window" and value is None:
                continue
            if value is None or value == "" or value == {}:
                errors.append(f"missing fairness field: {name}")

        if getattr(result, "algorithm_id", None) != result.algorithm:
            errors.append("algorithm_id must equal algorithm")
        if getattr(result, "objective_evaluations", None) != result.evaluations:
            errors.append("objective_evaluations must equal evaluations")
        if getattr(result, "evaluation_budget", None) != self.evaluation_budget:
            errors.append("result evaluation_budget does not match manifest")
        if result.evaluations <= 0:
            errors.append("objective evaluation count must be positive")
        if result.evaluations > self.evaluation_budget:
            errors.append("objective evaluation budget was exceeded")
        if getattr(result, "algorithm_id", None) == "legacy":
            errors.append("legacy is not a valid public algorithm identity")
        algorithm_id = getattr(result, "algorithm_id", None)
        expected_family = self.ALGORITHM_FAMILIES.get(algorithm_id)
        if expected_family is None:
            errors.append("unsupported fair algorithm_id")
        elif getattr(result, "algorithm_family", None) != expected_family:
            errors.append(
                "algorithm_family does not match the expected family for algorithm_id"
            )
        if not isinstance(getattr(result, "budget_terminated", None), bool):
            errors.append("budget_terminated must be a boolean")

        polish_policy = getattr(result, "polish_policy", None)
        if not isinstance(polish_policy, dict):
            errors.append("polish_policy must be a mapping")
        else:
            missing_policy_fields = [
                field for field in self.POLISH_POLICY_FIELDS if field not in polish_policy
            ]
            if missing_policy_fields:
                errors.append(
                    "polish_policy missing fields: " + ", ".join(missing_policy_fields)
                )
            else:
                bool_fields = ("enabled", "initial", "periodic", "final")
                if any(not isinstance(polish_policy[field], bool) for field in bool_fields):
                    errors.append("polish_policy phase fields must be booleans")
                if polish_policy["operator"] not in (None, "2-opt"):
                    errors.append("polish_policy operator must be None or '2-opt'")

                variant = getattr(result, "variant", None)
                if variant == "pure":
                    if any(polish_policy[field] for field in bool_fields):
                        errors.append("pure variant cannot enable polishing")
                    if polish_policy["operator"] is not None:
                        errors.append("pure variant cannot declare a polish operator")
                elif variant == "memetic_2opt":
                    if not all(polish_policy[field] for field in bool_fields):
                        errors.append(
                            "memetic_2opt variant must enable every polish phase"
                        )
                    if polish_policy["operator"] != "2-opt":
                        errors.append(
                            "memetic_2opt variant must declare operator '2-opt'"
                        )
                else:
                    errors.append("unsupported fair variant")
        if getattr(result, "execution_backend", None) == "unknown":
            errors.append("execution backend must be known")
        if result.seed != self.paired_seed(result.problem, result.run):
            errors.append("result seed is not the paired problem/replicate seed")
        if getattr(result, "seed_group", None) != self.seed_group(result.problem, result.run):
            errors.append("result seed_group is not the paired problem/replicate group")

        if self.protocol_version == self.V2_PROTOCOL:
            if getattr(result, "comparison_regime", None) != self.comparison_regime:
                errors.append("result comparison_regime does not match manifest")
            family = getattr(result, "algorithm_family", None)
            acceptance_policy = getattr(result, "acceptance_policy", None)
            neighborhood_window = getattr(result, "neighborhood_window", None)
            termination_reason = getattr(result, "termination_reason", None)
            if family in {"GWO", "HHO"}:
                if acceptance_policy != "population_evolution":
                    errors.append("GWO/HHO acceptance_policy must be population_evolution")
                if neighborhood_window is not None:
                    errors.append("GWO/HHO neighborhood_window must be null")
            elif family == "2-opt":
                if acceptance_policy not in {"best_improvement", "first_improvement"}:
                    errors.append("2-opt acceptance_policy is invalid")
                if neighborhood_window is not None:
                    errors.append("2-opt neighborhood_window must be null")
            elif family == "3-opt":
                if acceptance_policy not in {"best_improvement", "first_improvement"}:
                    errors.append("3-opt acceptance_policy is invalid")
                if isinstance(neighborhood_window, bool) or not isinstance(neighborhood_window, int) or neighborhood_window < 2:
                    errors.append("3-opt neighborhood_window must be an integer >= 2")
            if termination_reason not in self.TERMINATION_REASONS:
                errors.append("unsupported termination_reason")

        if errors:
            raise FairnessValidationError("; ".join(errors))


def normalize_problem(problem: str) -> str:
    normalized = "-".join(str(problem).strip().lower().split())
    return normalized or "unnamed"


def fair_manifest_from_params(params: Dict[str, Any]) -> Optional[FairComparisonManifest]:
    return FairComparisonManifest.from_value(params.get("fair_comparison"))


def improve_three_opt_budgeted(
    route: Sequence[int],
    matrix: Sequence[Sequence[float]],
    budget: ObjectiveEvaluationBudget,
    *,
    max_iterations: int,
    first_improvement: bool = False,
    window: Optional[int] = 12,
    directed: Optional[bool] = None,
) -> BudgetedSearchResult:
    """Budgeted controller over the canonical TSP/ATSP 3-opt neighborhood."""
    current = list(route)
    symmetric = is_symmetric_matrix(matrix)
    if directed is None:
        directed = not symmetric
    elif not directed and not symmetric:
        raise ValueError("symmetric 3-opt cannot be used with an asymmetric matrix")

    start_evaluations = budget.used
    current_cost = budget.evaluate(current, matrix)
    iterations = 0
    exhausted = False
    termination_reason = "max_iterations"

    while iterations < max_iterations:
        iterations += 1
        selected_route: Optional[List[int]] = None
        selected_cost = current_cost
        stop_scan = False
        for i, j, k in iter_three_opt_cuts(len(current), window):
            candidates = generate_three_opt_candidates(current, i, j, k, directed=bool(directed))
            for candidate in candidates:
                if not budget.can_spend():
                    exhausted = True
                    stop_scan = True
                    break
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
        mode="directed_atsp" if directed else "symmetric_tsp",
        termination_reason=termination_reason,
    )


__all__ = [
    "BudgetedSearchResult",
    "EvaluationBudgetExhausted",
    "FairComparisonManifest",
    "FairRunResult",
    "FairnessValidationError",
    "ObjectiveEvaluationBudget",
    "fair_manifest_from_params",
    "improve_three_opt_budgeted",
    "improve_two_opt_budgeted",
    "two_opt_evaluation_upper_bound",
]
