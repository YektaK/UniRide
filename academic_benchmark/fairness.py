"""Reproducible fairness contract and budgeted TSP local-search adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from academic_benchmark.composite_protocol import (
    COMPOSITE_ALGORITHMS,
    POLISH_OPERATORS,
    is_composite_variant,
    validate_composite_policy,
    validate_composite_result,
)
from academic_benchmark.engine_core import RunResult
from uniride_core.algorithms.composition import (
    ALNS_OPTIONAL_PARAMS,
    ALNS_REQUIRED_PARAMS,
    SWARM_REQUIRED_PARAMS,
    CompositionError,
    validate_alns_polish_params,
)
from uniride_core.algorithms.objective_budget import (
    BudgetedSearchResult,
    EvaluationBudgetExhausted,
    ObjectiveEvaluationBudget,
    # C-06: the budgeted 3-opt controller now lives next to the budgeted 2-opt and
    # Or-opt in uniride_core; this import keeps every ``academic_benchmark.fairness``
    # import working.
    improve_three_opt_budgeted,
    improve_two_opt_budgeted,
    two_opt_evaluation_upper_bound,
)


class FairnessValidationError(ValueError):
    """Raised when a result violates the fair-comparison contract."""


# ALNS_REQUIRED_PARAMS / ALNS_OPTIONAL_PARAMS are the composition engine's: the ALNS rules
# live in one place (``uniride_core.algorithms.composition``), standalone ALNS included.


def _is_finite_alns_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _delegate_alns_values(params: Mapping[str, Any], label: str) -> None:
    """Value rules of the ALNS parameters: the composition engine's validator, as ValueError."""
    try:
        validate_alns_polish_params(params, strict=True)
    except CompositionError as exc:
        raise ValueError(str(exc).replace("ALNS polish parameter", label)) from exc


def validate_scientific_alns_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact scientific ALNS configuration schema."""
    missing = ALNS_REQUIRED_PARAMS - params.keys()
    unknown = params.keys() - ALNS_REQUIRED_PARAMS - ALNS_OPTIONAL_PARAMS
    if missing or unknown:
        raise ValueError(
            "ALNS parameter schema mismatch; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )

    _delegate_alns_values(params, "ALNS parameter")

    return dict(params)


GA_REQUIRED_PARAMS = frozenset({
    "population_size", "max_iterations", "max_no_improvement", "crossover_rate",
    "mutation_rate", "elite_count", "tournament_size",
})
GA_OPTIONAL_PARAMS = frozenset()
GA_MEMETIC_ID = "Core-GA-TSP-Memetic-2opt"  # C-16c
GA_MEMETIC_POLISH_PARAMS = frozenset({"initial_polish_iters", "final_polish_iters"})
GA_MEMETIC_REQUIRED_PARAMS = GA_REQUIRED_PARAMS | GA_MEMETIC_POLISH_PARAMS


def validate_scientific_ga_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact scientific GA configuration schema (C-16a).

    Every key is required and unknown keys (for example a polish or 2-opt knob that the
    pure GA does not have) are rejected, so a result row can never be produced from a
    configuration the solver silently ignored.
    """
    missing = GA_REQUIRED_PARAMS - params.keys()
    unknown = params.keys() - GA_REQUIRED_PARAMS - GA_OPTIONAL_PARAMS
    if missing or unknown:
        raise ValueError(
            "GA parameter schema mismatch; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    for field, minimum in (
        ("population_size", 2), ("max_iterations", 1), ("max_no_improvement", 1),
        ("tournament_size", 1), ("elite_count", 0),
    ):
        value = params[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"invalid GA parameter: {field}")
    if params["elite_count"] >= params["population_size"]:
        raise ValueError("invalid GA parameter: elite_count")
    for field in ("crossover_rate", "mutation_rate"):
        value = params[field]
        if not _is_finite_alns_number(value) or not 0 <= value <= 1:
            raise ValueError(f"invalid GA parameter: {field}")
    return dict(params)


def validate_scientific_ga_memetic_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact scientific memetic GA schema (C-16c).

    The C-16a GA keys plus ``initial_polish_iters`` and ``final_polish_iters``, all required
    and at least 1 (C-04: a memetic configuration that executes no polish is a pure GA under
    a false name). Unknown keys, including a periodic ``polish_interval``, are rejected.
    """
    missing = GA_MEMETIC_REQUIRED_PARAMS - params.keys()
    unknown = params.keys() - GA_MEMETIC_REQUIRED_PARAMS
    if missing or unknown:
        raise ValueError(
            "GA memetic parameter schema mismatch; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    for field in sorted(GA_MEMETIC_POLISH_PARAMS):
        value = params[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"invalid GA memetic parameter: {field} must be an integer >= 1")
    validate_scientific_ga_params(
        {key: value for key, value in params.items() if key not in GA_MEMETIC_POLISH_PARAMS}
    )
    return dict(params)


PSO_REQUIRED_PARAMS = frozenset({
    "swarm_size", "max_iterations", "max_no_improvement", "inertia_weight",
    "cognitive_coeff", "social_coeff", "max_velocity_size", "reinit_interval",
})
PSO_OPTIONAL_PARAMS = frozenset()


def validate_scientific_pso_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact scientific PSO configuration schema (C-16b).

    Every key is required and unknown keys (for example a polish or 2-opt knob that the
    pure PSO does not have) are rejected, so a result row can never be produced from a
    configuration the solver silently ignored. ``reinit_interval`` 0 disables the
    counted diversity re-initialization.
    """
    missing = PSO_REQUIRED_PARAMS - params.keys()
    unknown = params.keys() - PSO_REQUIRED_PARAMS - PSO_OPTIONAL_PARAMS
    if missing or unknown:
        raise ValueError(
            "PSO parameter schema mismatch; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    for field, minimum in (
        ("swarm_size", 2), ("max_iterations", 1), ("max_no_improvement", 1),
        ("max_velocity_size", 1), ("reinit_interval", 0),
    ):
        value = params[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"invalid PSO parameter: {field}")
    value = params["inertia_weight"]
    if not _is_finite_alns_number(value) or not 0 <= value <= 1:
        raise ValueError("invalid PSO parameter: inertia_weight")
    for field in ("cognitive_coeff", "social_coeff"):
        value = params[field]
        if not _is_finite_alns_number(value) or value < 0:
            raise ValueError(f"invalid PSO parameter: {field}")
    return dict(params)


HYBRID_3OPT_POLISH_REQUIRED = frozenset({"max_iterations", "first_improvement", "window"})


def validate_scientific_hybrid_alns_params(
    family: str, params: Mapping[str, Any], *, fixed_budget: bool
) -> dict[str, Any]:
    """Strict parameter schema of a ``global_then_final_alns`` run (C-09).

    Same ``global`` namespace and ``global_fraction`` rules as the 3-opt hybrid; the
    ``polish`` namespace is the strict ALNS schema, whose value rules are the composition
    engine's ``validate_alns_polish_params`` (the one rule set also behind standalone ALNS).
    """
    return _validate_hybrid(family, params, fixed_budget=fixed_budget, polish_kind="ALNS")


def validate_scientific_hybrid_3opt_params(
    family: str, params: Mapping[str, Any], *, fixed_budget: bool
) -> dict[str, Any]:
    """Validate the strict parameter schema of a ``global_then_final_3opt`` run (C-08).

    The run takes two separate namespaces, ``global`` (the pure GWO/HHO stage) and
    ``polish`` (the one 3-opt stage), both with every key explicit and no unknown key; a
    polish knob in the global namespace is refused, so a result row can never be produced
    from a configuration the solver silently ignored. A fixed-budget run also needs an
    explicit ``global_fraction`` in (0, 1); a native run has none.
    """
    return _validate_hybrid(family, params, fixed_budget=fixed_budget, polish_kind="3-opt")


def _validate_hybrid(
    family: str, params: Mapping[str, Any], *, fixed_budget: bool, polish_kind: str
) -> dict[str, Any]:
    top_required = {"global", "polish"} | ({"global_fraction"} if fixed_budget else set())
    missing = top_required - params.keys()
    unknown = params.keys() - top_required
    if missing or unknown:
        raise ValueError(
            "hybrid parameter schema mismatch (global and polish namespaces"
            + (", explicit global_fraction" if fixed_budget else "; native runs take no global_fraction")
            + f"); missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    global_params, polish_params = params["global"], params["polish"]
    if not isinstance(global_params, Mapping) or not isinstance(polish_params, Mapping):
        raise ValueError("hybrid global and polish parameters must be mappings")
    required = set(SWARM_REQUIRED_PARAMS[family])
    missing = required - global_params.keys()
    unknown = global_params.keys() - required
    if missing or unknown:
        raise ValueError(
            f"hybrid global ({family}) parameter schema mismatch; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if polish_kind == "ALNS":
        missing = ALNS_REQUIRED_PARAMS - polish_params.keys()
        unknown = polish_params.keys() - ALNS_REQUIRED_PARAMS - ALNS_OPTIONAL_PARAMS
    else:
        missing = HYBRID_3OPT_POLISH_REQUIRED - polish_params.keys()
        unknown = polish_params.keys() - HYBRID_3OPT_POLISH_REQUIRED
    if missing or unknown:
        raise ValueError(
            f"hybrid polish ({polish_kind}) parameter schema mismatch; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    counts = ("pack_size", "hawks", "max_iterations", "max_no_improvement")
    for field in counts:
        if field in global_params:
            value = global_params[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"invalid hybrid global parameter: {field}")
    for field in ("dive_count",):
        if field in global_params:
            value = global_params[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"invalid hybrid global parameter: {field}")
    for field in required - set(counts) - {"dive_count"}:
        if not _is_finite_alns_number(global_params[field]):
            raise ValueError(f"invalid hybrid global parameter: {field}")
    if polish_kind == "ALNS":
        _delegate_alns_values(polish_params, "hybrid polish (ALNS) parameter")
    else:
        value = polish_params["max_iterations"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("invalid hybrid polish parameter: max_iterations")
        if not isinstance(polish_params["first_improvement"], bool):
            raise ValueError("invalid hybrid polish parameter: first_improvement")
        value = polish_params["window"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError("invalid hybrid polish parameter: window")
    if fixed_budget:
        fraction = params["global_fraction"]
        if not _is_finite_alns_number(fraction) or not 0 < fraction < 1:
            raise ValueError("invalid hybrid parameter: global_fraction must be strictly between 0 and 1")
    return {key: params[key] for key in top_required}


@dataclass
class FairRunResult(RunResult):
    """Backward-compatible RunResult carrying the academic fairness contract."""

    algorithm_id: str = ""
    requested_algorithm_id: Optional[str] = None
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
    # Stage record of a composite (global_then_final_3opt) run; None for every other row.
    composition: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.algorithm_id:
            self.algorithm_id = self.algorithm
        if self.evaluations == 0 and self.objective_evaluations:
            self.evaluations = self.objective_evaluations
        elif self.objective_evaluations == 0 and self.evaluations:
            self.objective_evaluations = self.evaluations


def validate_evaluation_budget(value: Any) -> int:
    """Return ``value`` if it is a positive int (bool excluded); never coerces."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("fair comparison evaluation_budget must be a positive integer")
    return value


def validate_base_seed(value: Any) -> int:
    """Return ``value`` if it is an int (bool excluded); negatives are hashed into valid seeds."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("fair comparison base_seed must be an integer")
    return value


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
        "Core-GWO-TSP-Memetic-3opt": "GWO",
        "Core-HHO-TSP-Memetic-3opt": "HHO",
        "Core-GWO-TSP-Memetic-ALNS": "GWO",
        "Core-HHO-TSP-Memetic-ALNS": "HHO",
        "Core-TwoOpt-TSP": "2-opt",
        "Core-ThreeOpt-TSP": "3-opt",
        "Numba-2-opt": "2-opt",
        "Numba-3-opt-bounded": "3-opt",
        "Core-GWO-TSP": "GWO",
        "Core-HHO-TSP": "HHO",
        "Numba-GWO": "GWO",
        "Numba-HHO": "HHO",
        "ALNS-TSP": "ALNS",
        "Core-GA-TSP": "GA",
        "Core-GA-TSP-Memetic-2opt": "GA",
        "Core-PSO-TSP": "PSO",
    }
    POLISH_POLICY_FIELDS = ("enabled", "initial", "periodic", "final", "operator")
    MANIFEST_FIELDS = (
        "evaluation_budget", "base_seed", "protocol_version", "budget_policy", "comparison_regime",
    )
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
        validate_evaluation_budget(self.evaluation_budget)
        validate_base_seed(self.base_seed)
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
        unknown = sorted(str(key) for key in value if key not in cls.MANIFEST_FIELDS)
        if unknown:
            raise ValueError(
                f"fair_comparison has unknown field(s): {', '.join(unknown)}; "
                f"allowed: {', '.join(cls.MANIFEST_FIELDS)}"
            )
        return cls(
            evaluation_budget=validate_evaluation_budget(value["evaluation_budget"]),
            base_seed=validate_base_seed(value.get("base_seed", 1000)),
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

    @staticmethod
    def _memetic_polish_count_errors(polish_policy, result) -> list:
        """Phase flags of a memetic result must equal the polish evaluations it spent."""
        phases = ("initial", "periodic", "final")
        errors = []
        counts = {}
        for key in ("executed", "evaluations"):
            value = polish_policy.get(key)
            if not isinstance(value, dict) or set(value) != set(phases) or any(
                not isinstance(value[phase], int)
                or isinstance(value[phase], bool)
                or value[phase] < 0
                for phase in phases
            ):
                errors.append(
                    f"memetic_2opt polish_policy must carry '{key}' as non-negative "
                    "integer counts for initial, periodic and final"
                )
            else:
                counts[key] = value
        if len(counts) == 2:
            for phase in phases:
                if polish_policy[phase] is not (counts["evaluations"][phase] > 0):
                    errors.append(
                        f"polish_policy {phase} flag must equal "
                        f"(polish evaluations spent in that phase > 0)"
                    )
                if counts["evaluations"][phase] > 0 and counts["executed"][phase] < 1:
                    errors.append(
                        f"polish_policy {phase} spent evaluations without an executed polish call"
                    )
            objective_evaluations = getattr(result, "objective_evaluations", None)
            if isinstance(objective_evaluations, int) and (
                sum(counts["evaluations"].values()) > objective_evaluations
            ):
                errors.append("polish evaluations exceed the objective evaluations")
        return errors

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
                composite_row = is_composite_variant(getattr(result, "variant", None))
                allowed_operators = (
                    (None, POLISH_OPERATORS[result.variant]) if composite_row else (None, "2-opt")
                )
                if polish_policy["operator"] not in allowed_operators:
                    errors.append(
                        "polish_policy operator must be None or "
                        + (f"'{POLISH_OPERATORS[result.variant]}'" if composite_row else "'2-opt'")
                    )

                variant = getattr(result, "variant", None)
                if variant == "pure":
                    if any(polish_policy[field] for field in bool_fields):
                        errors.append("pure variant cannot enable polishing")
                    if polish_policy["operator"] is not None:
                        errors.append("pure variant cannot declare a polish operator")
                elif variant == "memetic_2opt":
                    # Phase flags are derived from executed polish (audit M19): a
                    # memetic result must show that some phase ran, and ``enabled``
                    # must agree with the phases. A phase that never ran (for
                    # example periodic polish when the interval was not reached)
                    # is reported False, not forced True.
                    phase_flags = [
                        polish_policy[field]
                        for field in ("initial", "periodic", "final")
                    ]
                    if not any(phase_flags):
                        errors.append(
                            "memetic_2opt variant must execute at least one polish phase"
                        )
                    if polish_policy["enabled"] is not any(phase_flags):
                        errors.append(
                            "polish_policy enabled flag must match the executed phases"
                        )
                    if polish_policy["operator"] != "2-opt":
                        errors.append(
                            "memetic_2opt variant must declare operator '2-opt'"
                        )
                    errors.extend(self._memetic_polish_count_errors(polish_policy, result))
                elif is_composite_variant(variant):
                    errors.extend(validate_composite_policy(polish_policy, result))
                else:
                    errors.append("unsupported fair variant")
        if is_composite_variant(getattr(result, "variant", None)) or (
            algorithm_id in COMPOSITE_ALGORITHMS
        ):
            if self.protocol_version != self.V2_PROTOCOL:
                errors.append("composite rows need protocol v2 (explicit termination_reason)")
            errors.extend(
                validate_composite_result(
                    result, fixed_budget=self.evaluation_budget,
                    protocol_version=self.protocol_version,
                )
            )
        elif getattr(result, "termination_reason", None) == "composite_complete":
            errors.append("composite_complete is reserved for composite rows")
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
            elif family == "ALNS":
                if getattr(result, "variant", None) != "pure":
                    errors.append("ALNS comparison accepts only pure variants")
                if acceptance_policy not in {"simulated_annealing", "improving_only"}:
                    errors.append("ALNS acceptance_policy is invalid")
                if neighborhood_window is not None:
                    errors.append("ALNS neighborhood_window must be null")
                if termination_reason not in {
                    "evaluation_budget_exhausted", "max_iterations", "stagnation_limit",
                }:
                    errors.append("ALNS fixed termination_reason is invalid")
            elif family == "GA":
                expected_variant = (
                    "memetic_2opt" if algorithm_id == GA_MEMETIC_ID else "pure"
                )
                if getattr(result, "variant", None) != expected_variant:
                    errors.append(f"GA comparison accepts only {expected_variant} variants")
                if acceptance_policy != "population_evolution":
                    errors.append("GA acceptance_policy must be population_evolution")
                if neighborhood_window is not None:
                    errors.append("GA neighborhood_window must be null")
                if termination_reason not in {
                    "evaluation_budget_exhausted", "max_iterations", "stagnation_limit",
                }:
                    errors.append("GA fixed termination_reason is invalid")
            elif family == "PSO":
                if getattr(result, "variant", None) != "pure":
                    errors.append("PSO comparison accepts only pure variants")
                if acceptance_policy != "population_evolution":
                    errors.append("PSO acceptance_policy must be population_evolution")
                if neighborhood_window is not None:
                    errors.append("PSO neighborhood_window must be null")
                if termination_reason not in {
                    "evaluation_budget_exhausted", "max_iterations", "stagnation_limit",
                }:
                    errors.append("PSO fixed termination_reason is invalid")
            if termination_reason not in self.TERMINATION_REASONS:
                errors.append("unsupported termination_reason")

        if errors:
            raise FairnessValidationError("; ".join(errors))


def normalize_problem(problem: str) -> str:
    normalized = "-".join(str(problem).strip().lower().split())
    return normalized or "unnamed"


def fair_manifest_from_params(params: Dict[str, Any]) -> Optional[FairComparisonManifest]:
    return FairComparisonManifest.from_value(params.get("fair_comparison"))


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

from uniride_core.algorithms.objective_budget import improve_or_opt_budgeted

__all__.append("improve_or_opt_budgeted")

FairComparisonManifest.ALGORITHM_FAMILIES["Core-OrOpt-TSP"] = "Or-opt"
_fair_validate_result_without_or_opt = FairComparisonManifest.validate_result


def _fair_validate_result_with_or_opt(self, result: FairRunResult) -> None:
    _fair_validate_result_without_or_opt(self, result)
    if getattr(result, "algorithm_id", None) != "Core-OrOpt-TSP":
        return
    errors: list[str] = []
    family = getattr(result, "algorithm_family", None)
    acceptance = getattr(result, "acceptance_policy", None)
    window = getattr(result, "neighborhood_window", None)
    if family != "Or-opt":
        errors.append("Or-opt algorithm_family must be Or-opt")
    if acceptance not in {"best_improvement", "first_improvement"}:
        errors.append("Or-opt acceptance_policy is invalid")
    if isinstance(window, bool) or not isinstance(window, int) or not 1 <= window <= 3:
        errors.append("Or-opt neighborhood_window must be an integer from 1 through 3")
    if errors:
        raise FairnessValidationError("; ".join(errors))


FairComparisonManifest.validate_result = _fair_validate_result_with_or_opt
