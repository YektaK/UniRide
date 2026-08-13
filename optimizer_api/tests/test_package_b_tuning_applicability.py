"""Task 4: evidence-gated tuning applicability and request-local budgets."""

from dataclasses import fields

import pytest

from optimizer_api.compute_policy import (
    HARD_CEILINGS,
    TUNING_ALLOWLISTS,
    PolicyValidationError,
    applicable_keys,
    apply_compute_policy,
    load_compute_policy,
)
from optimizer_api.models.schemas import OptimizationRequest, PolicyValueSource
from optimizer_api.strategies.canonical import resolve_strategy
from optimizer_api.strategies.ga_strategy import GeneticAlgorithmStrategy
from uniride_core.algorithms.sota_tsp import E2BSOTSPConfig, PAOEAConfig, R2DMATSPConfig


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
    "pso": frozenset({"swarm_size", "max_iterations", "max_no_improvement", "max_velocity_size", "reinit_interval", "inertia_weight", "cognitive_weight", "social_weight", "seed"}),
    "pso_split": frozenset({"swarm_size", "max_iterations", "max_no_improvement", "local_search_interval", "local_search_type", "inertia_weight", "inertia_min", "cognitive_weight", "social_weight", "velocity_clamp", "seed"}),
    "gwo": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_a", "exploration_rate", "local_search_type", "seed"}),
    "gwo_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_a", "exploration_rate", "local_search_interval", "local_search_type", "seed"}),
    "hho": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_energy", "jump_probability", "local_search_type", "seed"}),
    "hho_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_energy", "jump_probability", "levy_flight_scale", "local_search_interval", "local_search_type", "seed"}),
    "two_opt": TUNING_ALLOWLISTS["two_opt_config"],
}

SOTA_CONFIGS = {
    "e2bso": E2BSOTSPConfig,
    "r2dma": R2DMATSPConfig,
    "paoea": PAOEAConfig,
}


def expected_applicable_keys(canonical: str) -> frozenset[str]:
    if canonical in STANDARD_APPLICABLE_KEYS:
        return STANDARD_APPLICABLE_KEYS[canonical]
    config_type = SOTA_CONFIGS[canonical]
    return frozenset(field.name for field in fields(config_type)) & TUNING_ALLOWLISTS["sota_config"]


def valid_sample(key: str):
    if key in {"first_improvement", "multi_start"}:
        return True
    if key == "local_search_type":
        return "two_opt"
    if key.startswith("ls_intensity_"):
        return "light"
    if key == "destroy_ops_pool":
        return ["random"]
    if key == "repair_ops_pool":
        return ["greedy"]
    if key == "acceptance_types":
        return ["sa"]
    if key == "remove_ratio_range":
        return [0.1, 0.2]
    if key == "seed":
        return 7
    if key in {
        "max_iterations", "max_no_improvement", "diversify_threshold",
        "local_search_interval", "reinit_interval", "entropy_check_interval",
        "diversity_check_interval", "learn_period", "meta_evolution_interval",
        "population_size", "swarm_size", "genome_population_size", "elite_count",
        "tournament_size", "tournament_k", "num_starts", "lahc_history",
        "max_velocity_size", "three_opt_window", "segment_size", "n_edges_normal",
        "n_edges_aggressive",
    }:
        return 1
    return 0.5


def _request(algorithm: str, **overrides) -> OptimizationRequest:
    payload = {
        "algorithm": algorithm,
        "students": [],
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
    }
    payload.update(overrides)
    return OptimizationRequest(**payload)


def _make_unrelated_defaults_compatible(strategy, key: str, sample) -> None:
    """Keep the exhaustive applicability row focused on one submitted key."""

    config = getattr(strategy, "config", getattr(strategy, "_config", None))
    if key in {"population_size", "swarm_size"}:
        for dependent in (
            "elite_count", "tournament_size", "tournament_k", "genome_population_size"
        ):
            if isinstance(config, dict) and dependent in config:
                config[dependent] = sample
            elif hasattr(config, dependent):
                setattr(config, dependent, sample)
    if key == "n_edges_aggressive" and hasattr(config, "n_edges_normal"):
        config.n_edges_normal = sample


CANONICALS = tuple(CONFIG_FIELD_BY_CANONICAL)
PUBLIC_KEY_CASES = tuple(
    (canonical, field_name, key)
    for canonical in CANONICALS
    for field_name, keys in TUNING_ALLOWLISTS.items()
    for key in sorted(keys)
)


@pytest.mark.parametrize(
    ("canonical", "field_name", "key"),
    PUBLIC_KEY_CASES,
    ids=lambda value: str(value),
)
def test_every_public_tuning_key_is_accepted_only_when_live_strategy_consumes_it(
    canonical, field_name, key
):
    resolution = resolve_strategy(canonical)
    strategy = resolution.create()
    sample = valid_sample(key)
    _make_unrelated_defaults_compatible(strategy, key, sample)
    request = _request(canonical, **{field_name: {key: sample}})
    expected = (
        field_name == CONFIG_FIELD_BY_CANONICAL[canonical]
        and key in expected_applicable_keys(canonical)
    )

    if not expected:
        with pytest.raises(PolicyValidationError):
            apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)
        return

    effective, _ = apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)
    expected_value = tuple(sample) if isinstance(sample, list) else sample
    assert getattr(effective, field_name)[key] == expected_value


@pytest.mark.parametrize("canonical", CANONICALS)
def test_applicability_contract_matches_characterized_live_surface(canonical):
    strategy = resolve_strategy(canonical).create()
    assert applicable_keys(canonical, strategy) == expected_applicable_keys(canonical)


def test_policy_application_deep_copies_request_and_preserves_identity():
    request = _request("ga", ga_config={"max_iterations": 5})
    original_config = request.ga_config
    resolution = resolve_strategy("ga")

    effective, metadata = apply_compute_policy(
        request, resolution, resolution.create(), HARD_CEILINGS
    )

    assert effective is not request
    assert effective.ga_config is not original_config
    assert request.ga_config == {"max_iterations": 5}
    assert metadata.algorithm_requested == "ga"
    assert metadata.algorithm_canonical == "genetic_algorithm"


def test_caller_values_win_without_mutating_registered_defaults():
    request = _request("ga", ga_config={"population_size": 7, "max_iterations": 9})
    resolution = resolve_strategy("ga")
    strategy = resolution.create()
    registered = dict(strategy.config)

    effective, metadata = apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)

    assert effective.ga_config["population_size"] == 7
    assert effective.ga_config["max_iterations"] == 9
    assert metadata.limits["population_size"].source is PolicyValueSource.CALLER
    assert metadata.limits["max_iterations"].source is PolicyValueSource.CALLER
    assert strategy.config == registered


def test_profile_caps_registered_defaults_on_request_copy():
    request = _request("ga")
    resolution = resolve_strategy("ga")
    strategy = GeneticAlgorithmStrategy({"population_size": 500, "max_iterations": 5000})

    effective, metadata = apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)

    assert effective.ga_config["population_size"] == HARD_CEILINGS.max_population
    assert effective.ga_config["max_iterations"] == HARD_CEILINGS.max_iterations
    assert metadata.limits["population_size"].source is PolicyValueSource.PROFILE_DEFAULT
    assert metadata.limits["max_iterations"].source is PolicyValueSource.PROFILE_DEFAULT
    assert strategy.config["population_size"] == 500
    assert strategy.config["max_iterations"] == 5000


def test_lower_server_policy_caps_defaults_and_reports_source():
    request = _request("ga")
    resolution = resolve_strategy("ga")
    policy = load_compute_policy({
        "UNIRIDE_COMPUTE_MAX_POPULATION": "10",
        "UNIRIDE_COMPUTE_MAX_ITERATIONS": "20",
    })

    effective, metadata = apply_compute_policy(request, resolution, resolution.create(), policy)

    assert effective.ga_config["population_size"] == 10
    assert effective.ga_config["max_iterations"] == 20
    assert metadata.limits["population_size"].source is PolicyValueSource.SERVER_OVERRIDE
    assert metadata.limits["max_iterations"].source is PolicyValueSource.SERVER_OVERRIDE


def test_caller_value_above_passed_lower_policy_fails_closed(monkeypatch):
    request = _request("ga", ga_config={"population_size": 11})
    resolution = resolve_strategy("ga")
    policy = load_compute_policy({"UNIRIDE_COMPUTE_MAX_POPULATION": "10"})

    with pytest.raises(PolicyValidationError, match="population_size"):
        apply_compute_policy(request, resolution, resolution.create(), policy)


@pytest.mark.parametrize(
    ("canonical", "field_name", "caller", "match"),
    [
        ("genetic_algorithm", "ga_config", {"elite_count": 4}, "elite_count"),
        ("pso_split", "pso_config", {"inertia_min": 0.95}, "inertia_min"),
        ("e2bso", "sota_config", {"h_end": 0.9}, "h_end"),
        ("e2bso", "sota_config", {"n_edges_normal": 6}, "n_edges_normal"),
        ("paoea", "sota_config", {"genome_population_size": 25}, "genome_population_size"),
    ],
)
def test_cross_field_relations_are_rechecked_against_registered_defaults(
    canonical, field_name, caller, match
):
    request = _request(canonical, **{field_name: caller})
    resolution = resolve_strategy(canonical)
    strategy = resolution.create()
    if canonical == "genetic_algorithm":
        strategy.config["population_size"] = 3

    with pytest.raises(PolicyValidationError, match=match):
        apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)


@pytest.mark.parametrize("canonical", ["greedy", "ortools_cvrp"])
def test_unconfigured_strategies_reject_all_tuning_fields(canonical):
    request = _request(canonical, ga_config={"max_iterations": 1})
    resolution = resolve_strategy(canonical)
    with pytest.raises(PolicyValidationError, match="ga_config"):
        apply_compute_policy(request, resolution, resolution.create(), HARD_CEILINGS)


def test_uninspectable_sota_config_fails_closed():
    resolution = resolve_strategy("e2bso")
    strategy = resolution.create()
    strategy._config = {"population_size": 24}
    request = _request("e2bso", sota_config={"population_size": 1})

    with pytest.raises(PolicyValidationError, match="not consumed"):
        apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)
