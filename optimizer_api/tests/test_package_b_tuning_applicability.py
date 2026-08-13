"""Task 4: evidence-gated tuning applicability and request-local budgets."""

import random
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
from optimizer_api.strategies import get_available_strategy_names
from optimizer_api.strategies.canonical import resolve_strategy
from optimizer_api.strategies.ga_strategy import GeneticAlgorithmStrategy
from uniride_core.algorithms.local_search import LocalSearchType
from uniride_core.algorithms.sota_tsp import E2BSOTSPConfig, PAOEAConfig, R2DMATSPConfig
from uniride_core.algorithms.tsp_meta_engines import solve_pso_tsp


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

STANDARD_DECLARATION_ONLY = {
    "genetic_algorithm": frozenset({"local_search_type"}),
}

SOTA_DECLARATION_ONLY = {
    "paoea": frozenset({
        "tournament_size", "genome_injection_rate", "remove_ratio_range"
    }),
}

SOTA_CONFIGS = {
    "e2bso": E2BSOTSPConfig,
    "r2dma": R2DMATSPConfig,
    "paoea": PAOEAConfig,
}


def expected_applicable_keys(canonical: str) -> frozenset[str]:
    if canonical in SOTA_CONFIGS:
        config_type = SOTA_CONFIGS[canonical]
        declared = (
            frozenset(field.name for field in fields(config_type))
            & TUNING_ALLOWLISTS["sota_config"]
        )
        return declared - SOTA_DECLARATION_ONLY.get(canonical, frozenset())
    strategy = resolve_strategy(canonical).create()
    field_name = CONFIG_FIELD_BY_CANONICAL[canonical]
    live_defaults = frozenset(strategy.config) & TUNING_ALLOWLISTS[field_name]
    return live_defaults - STANDARD_DECLARATION_ONLY.get(canonical, frozenset())


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


UNTUNED_CANONICALS = tuple(
    sorted(set(get_available_strategy_names()) - set(CONFIG_FIELD_BY_CANONICAL))
)


@pytest.mark.parametrize("canonical", UNTUNED_CANONICALS)
@pytest.mark.parametrize("field_name", tuple(TUNING_ALLOWLISTS))
def test_unconfigured_strategies_reject_all_tuning_fields(canonical, field_name):
    key = next(iter(TUNING_ALLOWLISTS[field_name]))
    request = _request(canonical, **{field_name: {key: valid_sample(key)}})
    resolution = resolve_strategy(canonical)
    with pytest.raises(PolicyValidationError, match=field_name):
        apply_compute_policy(request, resolution, resolution.create(), HARD_CEILINGS)


def test_uninspectable_sota_config_fails_closed():
    resolution = resolve_strategy("e2bso")
    strategy = resolution.create()
    strategy._config = {"population_size": 24}
    request = _request("e2bso", sota_config={"population_size": 1})

    with pytest.raises(PolicyValidationError, match="not consumed"):
        apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)


def test_standard_pso_policy_forwards_live_consumed_local_search_type(monkeypatch):
    observed = []

    def fake_local_search(route, duration_func, local_search_type):
        observed.append(local_search_type)
        return route, duration_func(route)

    monkeypatch.setattr(
        "uniride_core.algorithms.tsp_meta_engines.apply_local_search",
        fake_local_search,
    )
    request = _request(
        "pso",
        pso_config={
            "swarm_size": 3,
            "max_iterations": 1,
            "max_no_improvement": 1,
            "local_search_type": "or_opt",
        },
    )
    resolution = resolve_strategy("pso")
    effective, _ = apply_compute_policy(
        request, resolution, resolution.create(), HARD_CEILINGS
    )

    solve_pso_tsp(
        ["A", "B", "C"],
        lambda route: float(len(route)),
        random.Random(7),
        effective.pso_config,
    )

    assert observed == [LocalSearchType.OR_OPT]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("tournament_size", 2),
        ("genome_injection_rate", 0.2),
        ("remove_ratio_range", [0.1, 0.2]),
    ],
)
def test_paoea_rejects_declaration_only_fields_without_enforcement_metadata(
    key, value
):
    request = _request("paoea", sota_config={key: value})
    resolution = resolve_strategy("paoea")

    with pytest.raises(PolicyValidationError, match="not consumed"):
        apply_compute_policy(request, resolution, resolution.create(), HARD_CEILINGS)
