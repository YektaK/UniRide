"""Production compute profile for the optimizer API.

The ``production-conservative-v1`` profile freezes exhaustive public tuning-key
allowlists and hard safety ceilings. Server configuration (the nine approved
``UNIRIDE_COMPUTE_*`` variables) may lower an operational default but may never
raise a hard ceiling; invalid or out-of-range configuration fails at startup
instead of silently falling back.
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from numbers import Real
from typing import Any

PROFILE_ID = "production-conservative-v1"
DEFAULT_COMPARE_ALGORITHMS = (
    "greedy", "two_opt", "genetic_algorithm", "ga_split", "pso_split", "ortools_cvrp",
)


@dataclass(frozen=True)
class ComputePolicy:
    profile_id: str = PROFILE_ID
    max_students: int = 250
    max_vehicles: int = 50
    max_algorithms: int = 6
    max_workers: int = 2
    deadline_seconds: int = 120
    solver_seconds: int = 60
    max_iterations: int = 2_000
    max_population: int = 250
    local_search_seconds: int = 2
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60


HARD_CEILINGS = ComputePolicy()
ENV_FIELDS = {
    "UNIRIDE_COMPUTE_MAX_STUDENTS": "max_students",
    "UNIRIDE_COMPUTE_MAX_VEHICLES": "max_vehicles",
    "UNIRIDE_COMPUTE_MAX_ALGORITHMS": "max_algorithms",
    "UNIRIDE_COMPUTE_MAX_WORKERS": "max_workers",
    "UNIRIDE_COMPUTE_DEADLINE_SECONDS": "deadline_seconds",
    "UNIRIDE_COMPUTE_SOLVER_SECONDS": "solver_seconds",
    "UNIRIDE_COMPUTE_MAX_ITERATIONS": "max_iterations",
    "UNIRIDE_COMPUTE_MAX_POPULATION": "max_population",
    "UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS": "local_search_seconds",
    "UNIRIDE_RATE_LIMIT_REQUESTS": "rate_limit_requests",
    "UNIRIDE_RATE_LIMIT_WINDOW_SECONDS": "rate_limit_window_seconds",
}


def load_compute_policy(environ: Mapping[str, str] | None = None) -> ComputePolicy:
    source = os.environ if environ is None else environ
    changes: dict[str, int] = {}
    for env_name, field_name in ENV_FIELDS.items():
        raw = source.get(env_name)
        if raw is None:
            continue
        if not raw.isdecimal() or int(raw) < 1:
            raise ValueError(f"{env_name} must be a positive integer")
        value = int(raw)
        ceiling = getattr(HARD_CEILINGS, field_name)
        if value > ceiling:
            raise ValueError(f"{env_name} cannot exceed hard ceiling {ceiling}")
        changes[field_name] = value
    if changes.get("max_algorithms", HARD_CEILINGS.max_algorithms) < len(DEFAULT_COMPARE_ALGORITHMS):
        raise ValueError(
            "UNIRIDE_COMPUTE_MAX_ALGORITHMS cannot be lower than the six-algorithm default set"
        )
    return replace(HARD_CEILINGS, **changes)


TUNING_ALLOWLISTS = {
    "ga_config": frozenset({"crossover_rate", "diversify_threshold", "elite_count", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "mutation_rate", "population_size", "seed", "tournament_size"}),
    "pso_config": frozenset({"cognitive_weight", "inertia_min", "inertia_weight", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "max_velocity_size", "reinit_interval", "seed", "social_weight", "swarm_size", "velocity_clamp"}),
    "gwo_config": frozenset({"exploration_rate", "initial_a", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "population_size", "seed"}),
    "hho_config": frozenset({"initial_energy", "jump_probability", "levy_flight_scale", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "population_size", "seed"}),
    "two_opt_config": frozenset({"first_improvement", "max_iterations", "multi_start", "num_starts", "seed"}),
    "sota_config": frozenset({"acceptance_types", "crossover_rate", "delta_threshold", "destroy_ops_pool", "diversity_check_interval", "diversity_injection_rate", "diversity_threshold", "entropy_check_interval", "entropy_threshold", "gamma", "genome_injection_rate", "genome_population_size", "h_end", "h_start", "injection_rate", "lahc_history", "learn_period", "ls_intensity_compress", "ls_intensity_constructive", "ls_intensity_destructive", "ls_intensity_moderate", "ls_intensity_normal", "ls_time_limit", "max_iterations", "meta_evolution_interval", "mutation_rate", "n_edges_aggressive", "n_edges_normal", "p_best", "p_gbest", "population_size", "pulse_injection_rate", "remove_ratio", "remove_ratio_range", "repair_ops_pool", "sa_cooling_rate", "sa_end_temp", "sa_start_temp_factor", "seed", "segment_size", "theta_base", "three_opt_window", "time_limit", "tournament_k", "tournament_size"}),
}

BOOL_KEYS = frozenset({"first_improvement", "multi_start"})
ITERATION_KEYS = frozenset({"max_iterations", "max_no_improvement", "diversify_threshold", "local_search_interval", "reinit_interval", "entropy_check_interval", "diversity_check_interval", "learn_period", "meta_evolution_interval"})
ALLOCATION_KEYS = frozenset({"population_size", "swarm_size", "genome_population_size", "elite_count", "tournament_size", "tournament_k", "num_starts", "lahc_history"})
STRUCTURAL_KEYS = frozenset({"max_velocity_size", "three_opt_window", "segment_size", "n_edges_normal", "n_edges_aggressive"})
UNIT_INTERVAL_KEYS = frozenset({"crossover_rate", "mutation_rate", "exploration_rate", "jump_probability", "velocity_clamp", "diversity_injection_rate", "diversity_threshold", "entropy_threshold", "genome_injection_rate", "injection_rate", "p_best", "p_gbest", "pulse_injection_rate", "remove_ratio", "inertia_min", "inertia_weight", "h_start", "h_end", "gamma", "delta_threshold", "theta_base"})
POSITIVE_REAL_KEYS = frozenset({"cognitive_weight", "social_weight", "initial_a", "initial_energy", "levy_flight_scale", "sa_start_temp_factor", "sa_end_temp"})
INTENSITY_KEYS = frozenset({"ls_intensity_compress", "ls_intensity_constructive", "ls_intensity_destructive", "ls_intensity_moderate", "ls_intensity_normal"})

CONFIG_FIELD_BY_CANONICAL = {
    "genetic_algorithm": "ga_config",
    "ga_split": "ga_config",
    "ga_split_enhanced": "ga_config",
    "pso": "pso_config",
    "pso_split": "pso_config",
    "gwo": "gwo_config",
    "gwo_split": "gwo_config",
    "hho": "hho_config",
    "hho_split": "hho_config",
    "two_opt": "two_opt_config",
    "e2bso": "sota_config",
    "r2dma": "sota_config",
    "paoea": "sota_config",
}

STANDARD_APPLICABLE_KEYS = {
    "genetic_algorithm": frozenset({"population_size", "max_iterations", "max_no_improvement", "elite_count", "tournament_size", "crossover_rate", "mutation_rate", "seed"}),
    "ga_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "elite_count", "tournament_size", "crossover_rate", "mutation_rate", "local_search_interval", "local_search_type", "diversify_threshold", "seed"}),
    "ga_split_enhanced": frozenset({"population_size", "max_iterations", "max_no_improvement", "elite_count", "tournament_size", "crossover_rate", "mutation_rate", "local_search_interval", "local_search_type", "diversify_threshold", "seed"}),
    "pso": frozenset({"swarm_size", "max_iterations", "max_no_improvement", "max_velocity_size", "reinit_interval", "inertia_weight", "cognitive_weight", "social_weight", "local_search_type", "seed"}),
    "pso_split": frozenset({"swarm_size", "max_iterations", "max_no_improvement", "local_search_interval", "local_search_type", "inertia_weight", "inertia_min", "cognitive_weight", "social_weight", "velocity_clamp", "seed"}),
    "gwo": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_a", "exploration_rate", "local_search_type", "seed"}),
    "gwo_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_a", "exploration_rate", "local_search_interval", "local_search_type", "seed"}),
    "hho": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_energy", "jump_probability", "local_search_type", "seed"}),
    "hho_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_energy", "jump_probability", "levy_flight_scale", "local_search_interval", "local_search_type", "seed"}),
    "two_opt": TUNING_ALLOWLISTS["two_opt_config"],
}

SOTA_DECLARATION_ONLY_KEYS = {
    "paoea": frozenset({
        "tournament_size", "genome_injection_rate", "remove_ratio_range"
    }),
}

BUDGET_KEYS = ITERATION_KEYS | ALLOCATION_KEYS | STRUCTURAL_KEYS | {
    "time_limit", "ls_time_limit"
}


class PolicyValidationError(ValueError):
    """Raised when policy cannot be applied truthfully before solver work."""


def _finite_real(key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{key} must be a finite number")
    return float(value)


def _positive_int(key: str, value: Any, ceiling: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > ceiling:
        raise ValueError(f"{key} must be an integer in [1, {ceiling}]")
    return value


def _operator_list(key: str, value: Any, allowed: frozenset[str]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a non-empty string list")
    normalized = tuple(value)
    if not set(normalized) <= allowed:
        raise ValueError(f"{key} contains an unsupported value")
    return normalized


def validate_tuning_dict(
    field_name: str,
    value: Mapping[str, Any],
    policy: ComputePolicy,
    student_count: int,
) -> dict[str, Any]:
    if student_count < 0 or student_count > policy.max_students:
        raise ValueError("student_count is outside the effective policy")
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    unknown = set(value) - TUNING_ALLOWLISTS[field_name]
    if unknown:
        raise ValueError(f"{field_name} contains unsupported keys: {sorted(unknown)}")
    result = dict(value)
    for key, item in result.items():
        if key in BOOL_KEYS:
            if not isinstance(item, bool):
                raise ValueError(f"{key} must be a boolean")
        elif key == "seed":
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError("seed must be an integer")
        elif key in ITERATION_KEYS:
            result[key] = _positive_int(key, item, policy.max_iterations)
        elif key in ALLOCATION_KEYS:
            result[key] = _positive_int(key, item, policy.max_population)
        elif key in STRUCTURAL_KEYS:
            result[key] = _positive_int(key, item, min(policy.max_students, policy.max_population))
        elif key == "time_limit":
            number = _finite_real(key, item)
            if not 0 < number <= policy.solver_seconds:
                raise ValueError(f"time_limit must be in (0, {policy.solver_seconds}]")
            result[key] = number
        elif key == "ls_time_limit":
            number = _finite_real(key, item)
            if not 0 < number <= policy.local_search_seconds:
                raise ValueError(f"ls_time_limit must be in (0, {policy.local_search_seconds}]")
            result[key] = number
        elif key in UNIT_INTERVAL_KEYS:
            number = _finite_real(key, item)
            if not 0 <= number <= 1:
                raise ValueError(f"{key} must be in [0, 1]")
            result[key] = number
        elif key in POSITIVE_REAL_KEYS:
            number = _finite_real(key, item)
            if number <= 0:
                raise ValueError(f"{key} must be positive")
            result[key] = number
        elif key == "sa_cooling_rate":
            number = _finite_real(key, item)
            if not 0 < number < 1:
                raise ValueError("sa_cooling_rate must be in (0, 1)")
            result[key] = number
        elif key == "local_search_type":
            if not isinstance(item, str) or item not in {"none", "two_opt", "three_opt", "or_opt", "hybrid"}:
                raise ValueError("local_search_type is unsupported")
        elif key in INTENSITY_KEYS:
            if not isinstance(item, str) or item not in {"light", "moderate"}:
                raise ValueError(f"{key} is unsupported")
        elif key == "destroy_ops_pool":
            result[key] = _operator_list(key, item, frozenset({"random", "worst", "shaw", "related"}))
        elif key == "repair_ops_pool":
            result[key] = _operator_list(key, item, frozenset({"greedy", "regret2", "regret3"}))
        elif key == "acceptance_types":
            result[key] = _operator_list(key, item, frozenset({"sa", "lahc"}))
        elif key == "remove_ratio_range":
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("remove_ratio_range must contain two numbers")
            low, high = (_finite_real(key, part) for part in item)
            if not 0 <= low <= high <= 1:
                raise ValueError("remove_ratio_range must satisfy 0 <= low <= high <= 1")
            result[key] = (low, high)
        else:
            raise ValueError(f"{key} has no production validation rule")
    if "h_start" in result and "h_end" in result and result["h_end"] > result["h_start"]:
        raise ValueError("h_end cannot exceed h_start")
    if "inertia_min" in result and "inertia_weight" in result and result["inertia_min"] > result["inertia_weight"]:
        raise ValueError("inertia_min cannot exceed inertia_weight")
    if "n_edges_normal" in result and "n_edges_aggressive" in result and result["n_edges_normal"] > result["n_edges_aggressive"]:
        raise ValueError("n_edges_normal cannot exceed n_edges_aggressive")
    population = result.get("population_size", result.get("swarm_size", policy.max_population))
    for dependent in ("elite_count", "tournament_size", "tournament_k", "genome_population_size"):
        if dependent in result and result[dependent] > population:
            raise ValueError(f"{dependent} cannot exceed effective population")
    return result


def applicable_keys(canonical: str, strategy: object) -> frozenset[str]:
    """Return only tuning keys proven by the live strategy configuration."""

    if canonical in STANDARD_APPLICABLE_KEYS:
        return STANDARD_APPLICABLE_KEYS[canonical]
    config = getattr(strategy, "_config", None)
    if canonical in {"e2bso", "r2dma", "paoea"} and is_dataclass(config):
        declared = (
            frozenset(field.name for field in fields(config))
            & TUNING_ALLOWLISTS["sota_config"]
        )
        return declared - SOTA_DECLARATION_ONLY_KEYS.get(canonical, frozenset())
    return frozenset()


def _ceiling_for(key: str, policy: ComputePolicy) -> float:
    if key in ITERATION_KEYS:
        return policy.max_iterations
    if key in ALLOCATION_KEYS:
        return policy.max_population
    if key in STRUCTURAL_KEYS:
        return min(policy.max_students, policy.max_population)
    if key == "time_limit":
        return policy.solver_seconds
    if key == "ls_time_limit":
        return policy.local_search_seconds
    raise KeyError(key)


def _registered_config(strategy: object) -> dict[str, Any]:
    raw = getattr(strategy, "config", None)
    if raw is None:
        raw = getattr(strategy, "_config", None)
    if raw is None:
        return {}
    if is_dataclass(raw):
        return {field.name: getattr(raw, field.name) for field in fields(raw)}
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    if isinstance(raw, Mapping):
        return dict(raw)
    raise PolicyValidationError("strategy configuration is not inspectable")


def _source_for_default(
    key: str,
    registered: float,
    effective: float,
    policy: ComputePolicy,
):
    try:
        from optimizer_api.models.schemas import PolicyValueSource
    except ModuleNotFoundError:  # direct-module compatibility
        from models.schemas import PolicyValueSource

    ceiling = _ceiling_for(key, policy)
    hard_ceiling = _ceiling_for(key, HARD_CEILINGS)
    if effective == registered:
        return PolicyValueSource.STRATEGY_DEFAULT
    if ceiling < hard_ceiling:
        return PolicyValueSource.SERVER_OVERRIDE
    return PolicyValueSource.PROFILE_DEFAULT


def _capped_registered_budget(key: str, value: Any, ceiling: float) -> int | float:
    if key in ITERATION_KEYS | ALLOCATION_KEYS | STRUCTURAL_KEYS:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise PolicyValidationError(f"registered {key} must be a positive integer")
        return min(value, int(ceiling))
    try:
        number = _finite_real(key, value)
    except ValueError as exc:
        raise PolicyValidationError(f"registered {exc}") from None
    if number <= 0:
        raise PolicyValidationError(f"registered {key} must be positive")
    return min(number, ceiling)


def _reject_if_greater(
    config: Mapping[str, Any],
    left: str,
    right: str,
    message: str,
) -> None:
    if left not in config or right not in config:
        return
    try:
        invalid = config[left] > config[right]
    except TypeError:
        raise PolicyValidationError(f"{left} and {right} must be comparable numbers") from None
    if invalid:
        raise PolicyValidationError(message)


def validate_effective_relations(
    config: Mapping[str, Any], policy: ComputePolicy
) -> None:
    """Recheck cross-field rules after defaults and caller values are combined."""

    _reject_if_greater(config, "h_end", "h_start", "h_end cannot exceed h_start")
    _reject_if_greater(
        config,
        "inertia_min",
        "inertia_weight",
        "inertia_min cannot exceed inertia_weight",
    )
    _reject_if_greater(
        config,
        "n_edges_normal",
        "n_edges_aggressive",
        "n_edges_normal cannot exceed n_edges_aggressive",
    )
    population = config.get(
        "population_size", config.get("swarm_size", policy.max_population)
    )
    for dependent in (
        "elite_count", "tournament_size", "tournament_k", "genome_population_size"
    ):
        if dependent not in config:
            continue
        try:
            invalid = config[dependent] > population
        except TypeError:
            raise PolicyValidationError(
                f"{dependent} and effective population must be comparable numbers"
            ) from None
        if invalid:
            raise PolicyValidationError(
                f"{dependent} cannot exceed effective population"
            )


def apply_compute_policy(request, resolution, strategy, policy: ComputePolicy):
    """Return an isolated request plus truthful metadata for one fresh strategy."""

    try:
        from optimizer_api.models.schemas import (
            AppliedComputePolicyInfo,
            AppliedPolicyLimitInfo,
            PolicyValueSource,
        )
    except ModuleNotFoundError:  # direct-module compatibility
        from models.schemas import (
            AppliedComputePolicyInfo,
            AppliedPolicyLimitInfo,
            PolicyValueSource,
        )

    effective = request.model_copy(deep=True)
    canonical = resolution.canonical
    selected_field = CONFIG_FIELD_BY_CANONICAL.get(canonical)

    for field_name in TUNING_ALLOWLISTS:
        supplied = getattr(effective, field_name)
        if supplied and field_name != selected_field:
            raise PolicyValidationError(f"{field_name} does not apply to {canonical}")

    limits: dict[str, AppliedPolicyLimitInfo] = {}
    if selected_field is not None:
        raw_caller = dict(getattr(effective, selected_field) or {})
        allowed = applicable_keys(canonical, strategy)
        rejected = set(raw_caller) - allowed
        if rejected:
            raise PolicyValidationError(
                f"{selected_field} keys not consumed by {canonical}: {sorted(rejected)}"
            )
        try:
            caller = validate_tuning_dict(
                selected_field, raw_caller, policy, len(effective.students)
            )
        except ValueError as exc:
            raise PolicyValidationError(str(exc)) from None

        registered = _registered_config(strategy)
        merged = dict(caller)
        for key in sorted(allowed & BUDGET_KEYS):
            ceiling = _ceiling_for(key, policy)
            if key in caller:
                value = caller[key]
                source = PolicyValueSource.CALLER
            elif key in registered:
                value = _capped_registered_budget(key, registered[key], ceiling)
                source = _source_for_default(key, registered[key], value, policy)
            else:
                continue
            merged[key] = value
            limits[key] = AppliedPolicyLimitInfo(
                value=value,
                source=source,
                enforcement=f"request-local {selected_field}.{key}",
            )

        relation_view = {
            key: value for key, value in registered.items() if key in allowed
        }
        relation_view.update(merged)
        validate_effective_relations(relation_view, policy)
        setattr(effective, selected_field, merged)

    if canonical in {"ortools_cvrp", "pyvrp", "pyvrp_alt"}:
        registered_seconds = strategy.time_limit_seconds
        strategy.time_limit_seconds = min(registered_seconds, policy.solver_seconds)
        limits["solver_seconds"] = AppliedPolicyLimitInfo(
            value=strategy.time_limit_seconds,
            source=_source_for_default(
                "time_limit", registered_seconds, strategy.time_limit_seconds, policy
            ),
            enforcement="request-local native solver limit",
        )

    metadata = AppliedComputePolicyInfo(
        profile_id=policy.profile_id,
        algorithm_requested=resolution.requested,
        algorithm_canonical=canonical,
        student_count=len(effective.students),
        vehicle_count=len(effective.vehicles or []),
        cancellation_mode="none",
        limits=limits,
    )
    return effective, metadata
