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
from dataclasses import dataclass, replace
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
            if item not in {"none", "two_opt", "three_opt", "or_opt", "hybrid"}:
                raise ValueError("local_search_type is unsupported")
        elif key in INTENSITY_KEYS:
            if item not in {"light", "moderate"}:
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
