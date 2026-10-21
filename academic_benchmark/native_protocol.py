"""Scientific contract for the algorithm-native TSP/ATSP regime."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from academic_benchmark.composite_protocol import (
    COMPOSITE_ALGORITHMS,
    COMPOSITE_COMPLETE_REASON,
    COMPOSITE_VARIANT,
    validate_composite_policy,
    validate_composite_result,
)
from academic_benchmark.engine_core import RunResult
from academic_benchmark.fairness import (
    FairComparisonManifest,
    FairRunResult,
    FairnessValidationError,
    normalize_problem,
)


NATIVE_PROTOCOL = "uniride-native-tsp-v1"
NATIVE_TERMINATION_REGIME = "algorithm_native_termination"
APPROVED_NATIVE_ALGORITHMS = frozenset({
    "Core-GWO-TSP-Pure",
    "Core-HHO-TSP-Pure",
    "Core-TwoOpt-TSP",
    "Core-ThreeOpt-TSP",
    "ALNS-TSP",
})
# Optional member of a native pilot configuration (not required of existing configs).
# Memetic 2-opt members (C-10): their polish is counted, so the native contract accepts
# the memetic variant for exactly these IDs and checks the polish counts.
NATIVE_MEMETIC_2OPT_ALGORITHMS = frozenset({
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Memetic-2opt",
})
OPTIONAL_NATIVE_ALGORITHMS = frozenset({"Core-GA-TSP", "Core-PSO-TSP"}) | NATIVE_MEMETIC_2OPT_ALGORITHMS


@dataclass(frozen=True)
class NativeComparisonManifest:
    """Paired-seed and result validator without a shared evaluation cap."""

    base_seed: int = 1000
    protocol_version: str = NATIVE_PROTOCOL
    comparison_regime: str = NATIVE_TERMINATION_REGIME

    ALGORITHM_FAMILIES = {
        "Core-GWO-TSP-Pure": "GWO",
        "Core-HHO-TSP-Pure": "HHO",
        "Core-GWO-TSP-Memetic-3opt": "GWO",
        "Core-HHO-TSP-Memetic-3opt": "HHO",
        "Core-TwoOpt-TSP": "2-opt",
        "Core-ThreeOpt-TSP": "3-opt",
        "Numba-2-opt": "2-opt",
        "Numba-3-opt-bounded": "3-opt",
        "ALNS-TSP": "ALNS",
        "Core-GA-TSP": "GA",
        "Core-PSO-TSP": "PSO",
        "Core-GWO-TSP-Memetic-2opt": "GWO",
        "Core-HHO-TSP-Memetic-2opt": "HHO",
    }
    TERMINATION_REASONS = frozenset({
        "max_iterations",
        "no_improving_move",
        "stagnation_limit",
        # only composite rows (global_then_final_3opt) may carry it; validate_result
        # refuses it on every other row
        COMPOSITE_COMPLETE_REASON,
    })
    REQUIRED_RESULT_FIELDS = (
        "algorithm_id",
        "algorithm_family",
        "variant",
        "seed_group",
        "objective_evaluations",
        "initialization_policy",
        "termination_policy",
        "execution_backend",
        "polish_policy",
        "comparison_regime",
        "acceptance_policy",
        "termination_reason",
    )
    POLISH_POLICY_FIELDS = ("enabled", "initial", "periodic", "final", "operator")

    def __post_init__(self) -> None:
        if isinstance(self.base_seed, bool) or not isinstance(self.base_seed, int) or self.base_seed < 0:
            raise ValueError("native comparison base_seed must be a non-negative integer")
        if self.protocol_version != NATIVE_PROTOCOL:
            raise ValueError(f"unsupported native protocol_version: {self.protocol_version}")
        if self.comparison_regime != NATIVE_TERMINATION_REGIME:
            raise ValueError(
                "native comparison_regime must be 'algorithm_native_termination'"
            )

    @classmethod
    def from_value(cls, value: Any) -> Optional["NativeComparisonManifest"]:
        if value is None or value is False:
            return None
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise ValueError(
                "native_comparison must be a mapping or NativeComparisonManifest"
            )
        if "evaluation_budget" in value:
            raise ValueError("native_comparison must not declare evaluation_budget")
        allowed = {"base_seed", "protocol_version", "comparison_regime"}
        extra = set(value) - allowed
        if extra:
            raise ValueError(f"unknown native_comparison fields: {sorted(extra)}")
        return cls(
            base_seed=value.get("base_seed", 1000),
            protocol_version=str(value.get("protocol_version", NATIVE_PROTOCOL)),
            comparison_regime=str(
                value.get("comparison_regime", NATIVE_TERMINATION_REGIME)
            ),
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
        for name in self.REQUIRED_RESULT_FIELDS:
            value = getattr(result, name, None)
            if value is None or value == "" or value == {}:
                errors.append(f"missing native-comparison field: {name}")

        algorithm_id = getattr(result, "algorithm_id", None)
        expected_family = self.ALGORITHM_FAMILIES.get(algorithm_id)
        family = getattr(result, "algorithm_family", None)
        if algorithm_id != result.algorithm:
            errors.append("algorithm_id must equal algorithm")
        if expected_family is None:
            errors.append("unsupported native algorithm_id")
        elif family != expected_family:
            errors.append("algorithm_family does not match algorithm_id")
        variant = getattr(result, "variant", None)
        # Memetic-2opt IDs (C-10) accept only memetic_2opt; the composite variant (C-08)
        # belongs to the 3-opt hybrid IDs; every other ID is pure-only.
        memetic = algorithm_id in NATIVE_MEMETIC_2OPT_ALGORITHMS
        composite_row = variant == COMPOSITE_VARIANT and not memetic
        if memetic:
            if variant != "memetic_2opt":
                errors.append(
                    "native comparison accepts only the memetic_2opt variant for memetic IDs"
                )
        elif variant != "pure" and not composite_row:
            errors.append("native comparison accepts only pure variants")
        if getattr(result, "objective_evaluations", None) != result.evaluations:
            errors.append("objective_evaluations must equal evaluations")
        if result.evaluations <= 0:
            errors.append("objective evaluation count must be positive")
        if getattr(result, "evaluation_budget", None) is not None:
            errors.append("native result evaluation_budget must be null")
        if getattr(result, "budget_terminated", None) is not False:
            errors.append("native result budget_terminated must be false")
        if getattr(result, "comparison_regime", None) != self.comparison_regime:
            errors.append("result comparison_regime does not match native manifest")
        if result.seed != self.paired_seed(result.problem, result.run):
            errors.append("result seed is not the paired problem/replicate seed")
        if getattr(result, "seed_group", None) != self.seed_group(result.problem, result.run):
            errors.append("result seed_group is not the paired problem/replicate group")

        polish_policy = getattr(result, "polish_policy", None)
        if not isinstance(polish_policy, dict):
            errors.append("polish_policy must be a mapping")
        else:
            missing = [name for name in self.POLISH_POLICY_FIELDS if name not in polish_policy]
            if missing:
                errors.append("polish_policy missing fields: " + ", ".join(missing))
            else:
                phases = ("enabled", "initial", "periodic", "final")
                if memetic:
                    flags = [polish_policy[name] for name in phases[1:]]
                    if any(not isinstance(polish_policy[name], bool) for name in phases):
                        errors.append("polish_policy phase fields must be booleans")
                    if not any(flags):
                        errors.append("native memetic_2opt must execute at least one polish phase")
                    if polish_policy["enabled"] is not any(flags):
                        errors.append("polish_policy enabled flag must match the executed phases")
                    if polish_policy["operator"] != "2-opt":
                        errors.append("native memetic_2opt must declare operator '2-opt'")
                    errors.extend(
                        FairComparisonManifest._memetic_polish_count_errors(polish_policy, result)
                    )
                elif composite_row:
                    errors.extend(validate_composite_policy(polish_policy, result))
                else:
                    if any(polish_policy[name] is not False for name in phases):
                        errors.append("native pure variants cannot enable polishing")
                    if polish_policy["operator"] is not None:
                        errors.append("native pure variants cannot declare a polish operator")

        acceptance = getattr(result, "acceptance_policy", None)
        window = getattr(result, "neighborhood_window", None)
        reason = getattr(result, "termination_reason", None)
        if family in {"GWO", "HHO"}:
            if acceptance != "population_evolution":
                errors.append("GWO/HHO acceptance_policy must be population_evolution")
            if window is not None:
                errors.append("GWO/HHO neighborhood_window must be null")
            expected_reasons = (
                {COMPOSITE_COMPLETE_REASON}
                if composite_row else {"max_iterations", "stagnation_limit"}
            )
            if reason not in expected_reasons:
                errors.append("GWO/HHO native termination_reason is invalid")
        elif family == "2-opt":
            if acceptance not in {"best_improvement", "first_improvement"}:
                errors.append("2-opt acceptance_policy is invalid")
            if window is not None:
                errors.append("2-opt neighborhood_window must be null")
            if reason not in {"max_iterations", "no_improving_move"}:
                errors.append("2-opt native termination_reason is invalid")
        elif family == "3-opt":
            if acceptance not in {"best_improvement", "first_improvement"}:
                errors.append("3-opt acceptance_policy is invalid")
            if isinstance(window, bool) or not isinstance(window, int) or window < 2:
                errors.append("3-opt neighborhood_window must be an integer >= 2")
            if reason not in {"max_iterations", "no_improving_move"}:
                errors.append("3-opt native termination_reason is invalid")
        elif family == "ALNS":
            if acceptance not in {"simulated_annealing", "improving_only"}:
                errors.append("ALNS acceptance_policy is invalid")
            if window is not None:
                errors.append("ALNS neighborhood_window must be null")
            if reason not in {"max_iterations", "stagnation_limit"}:
                errors.append("ALNS native termination_reason is invalid")
        elif family == "GA":
            if getattr(result, "variant", None) != "pure":
                errors.append("GA comparison accepts only pure variants")
            if acceptance != "population_evolution":
                errors.append("GA acceptance_policy must be population_evolution")
            if window is not None:
                errors.append("GA neighborhood_window must be null")
            if reason not in {"max_iterations", "stagnation_limit"}:
                errors.append("GA native termination_reason is invalid")
        elif family == "PSO":
            if acceptance != "population_evolution":
                errors.append("PSO acceptance_policy must be population_evolution")
            if window is not None:
                errors.append("PSO neighborhood_window must be null")
            if reason not in {"max_iterations", "stagnation_limit"}:
                errors.append("PSO native termination_reason is invalid")
        if reason not in self.TERMINATION_REASONS:
            errors.append("unsupported native termination_reason")
        if composite_row or algorithm_id in COMPOSITE_ALGORITHMS:
            errors.extend(validate_composite_result(result, fixed_budget=None))
        elif reason == COMPOSITE_COMPLETE_REASON:
            errors.append("composite_complete is reserved for composite rows")
        if getattr(result, "execution_backend", None) in {None, "", "unknown"}:
            errors.append("execution backend must be known")

        if errors:
            raise FairnessValidationError("; ".join(errors))


def native_manifest_from_params(
    params: Dict[str, Any],
) -> Optional[NativeComparisonManifest]:
    return NativeComparisonManifest.from_value(params.get("native_comparison"))


NativeRunResult = FairRunResult


__all__ = [
    "APPROVED_NATIVE_ALGORITHMS",
    "NATIVE_MEMETIC_2OPT_ALGORITHMS",
    "OPTIONAL_NATIVE_ALGORITHMS",
    "NATIVE_PROTOCOL",
    "NATIVE_TERMINATION_REGIME",
    "NativeComparisonManifest",
    "NativeRunResult",
    "native_manifest_from_params",
]
APPROVED_NATIVE_ALGORITHMS = frozenset(
    set(APPROVED_NATIVE_ALGORITHMS) | {"Core-OrOpt-TSP"}
)
NativeComparisonManifest.ALGORITHM_FAMILIES["Core-OrOpt-TSP"] = "Or-opt"
_native_validate_result_without_or_opt = NativeComparisonManifest.validate_result


def _native_validate_result_with_or_opt(self, result: NativeRunResult) -> None:
    _native_validate_result_without_or_opt(self, result)
    if getattr(result, "algorithm_id", None) != "Core-OrOpt-TSP":
        return
    errors: list[str] = []
    family = getattr(result, "algorithm_family", None)
    acceptance = getattr(result, "acceptance_policy", None)
    window = getattr(result, "neighborhood_window", None)
    reason = getattr(result, "termination_reason", None)
    if family != "Or-opt":
        errors.append("Or-opt algorithm_family must be Or-opt")
    if acceptance not in {"best_improvement", "first_improvement"}:
        errors.append("Or-opt acceptance_policy is invalid")
    if isinstance(window, bool) or not isinstance(window, int) or not 1 <= window <= 3:
        errors.append("Or-opt neighborhood_window must be an integer from 1 through 3")
    if reason not in {"max_iterations", "no_improving_move"}:
        errors.append("Or-opt native termination_reason is invalid")
    if errors:
        raise FairnessValidationError("; ".join(errors))


NativeComparisonManifest.validate_result = _native_validate_result_with_or_opt
