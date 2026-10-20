"""C-16a follow-up fixes: routing engine identity, native GA purity, DOE key mapping."""
from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from academic_benchmark.fairness import FairnessValidationError
from academic_benchmark.native_protocol import NativeComparisonManifest

TINY_CVRP = ProblemInstance(
    name="c16a-tiny-cvrp",
    dimension=4,
    coordinates=[],
    problem_type="cvrp",
    dist_matrix=[
        [0, 10, 10, 10],
        [10, 0, 1, 1],
        [10, 1, 0, 1],
        [10, 1, 1, 0],
    ],
    demands=[0, 1, 1, 1],
    capacities=[2],
    capacity=2,
)
TINY_CVRPTW = ProblemInstance(
    name="c16a-tiny-cvrptw",
    dimension=3,
    coordinates=[],
    problem_type="cvrptw",
    dist_matrix=[[0, 10, 10], [10, 0, 10], [10, 10, 0]],
    demands=[0, 1, 1],
    capacities=[2],
    capacity=2,
    time_windows=[(0, 999), (0, 5), (0, 999)],
    service_times=[0, 0, 0],
    direction="dropoff",
)
TINY_TSP = ProblemInstance(
    name="c16a-tiny-tsp",
    dimension=6,
    coordinates=[],
    problem_type="tsp",
    dist_matrix=[
        [0, 4, 8, 7, 3, 6],
        [4, 0, 5, 9, 6, 4],
        [8, 5, 0, 2, 7, 3],
        [7, 9, 2, 0, 4, 5],
        [3, 6, 7, 4, 0, 8],
        [6, 4, 3, 5, 8, 0],
    ],
)


@pytest.mark.parametrize("problem", [TINY_CVRP, TINY_CVRPTW], ids=["cvrp", "cvrptw"])
def test_core_ga_routing_call_builds_the_ga_engine_not_the_greedy_default(monkeypatch, problem) -> None:
    real_create = registry_setup.create_matrix_engine
    built: list[tuple[str, str]] = []

    def recording_create(name):
        engine = real_create(name)
        built.append((name, type(engine).__name__))
        return engine

    monkeypatch.setattr(registry_setup, "create_matrix_engine", recording_create)
    result = AlgorithmRegistry.get_executor("Core-GA-TSP")(problem, {}, 42, 0)

    assert built == [("Core-GA-TSP", "TSPMetaMatrixEngine")]
    assert result.algorithm == "Core-GA-TSP"
    assert result.routes


def test_native_ga_branch_rejects_non_pure_variant_with_a_ga_message() -> None:
    from academic_benchmark.fairness import FairRunResult  # noqa: F401

    params = {
        "population_size": 6, "max_iterations": 2, "max_no_improvement": 3,
        "crossover_rate": 0.85, "mutation_rate": 0.15, "elite_count": 2,
        "tournament_size": 3,
        "native_comparison": {
            "base_seed": 5, "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        },
    }
    row = AlgorithmRegistry.get_executor("Core-GA-TSP")(TINY_TSP, params, 1, 0)
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])
    manifest.validate_result(row)
    row.variant = "memetic_2opt"
    with pytest.raises(FairnessValidationError, match="GA comparison accepts only pure variants"):
        manifest.validate_result(row)


def test_doe_ga_keys_pop_size_and_elite_size_reach_the_canonical_ga() -> None:
    # NUMBA_PARAM_SPACES["GA"] (shared with Numba-GA) names these keys pop_size/elite_size.
    params = {"pop_size": 8, "elite_size": 3, "generations": 2, "mutation_rate": 0.1,
              "crossover_rate": 0.9}
    row = AlgorithmRegistry.get_executor("Core-GA-TSP")(TINY_TSP, params, 7, 0)
    # init 8 + 2 generations of (8 - 3) offspring; defaults (100/2) would give far more
    assert row.evaluations == 8 + 2 * (8 - 3)
    assert row.iterations == 2


# ----- review round 1: strict protocol schema takes no aliases; alias conflicts raise -----

GA_SCHEMA = {
    "population_size": 6, "max_iterations": 2, "max_no_improvement": 3,
    "crossover_rate": 0.85, "mutation_rate": 0.15, "elite_count": 2,
    "tournament_size": 3,
}
_PROTOCOLS = {
    "fair": {
        "fair_comparison": {
            "evaluation_budget": 40, "base_seed": 5,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        }
    },
    "native": {
        "native_comparison": {
            "base_seed": 5, "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        }
    },
}


@pytest.mark.parametrize("protocol", sorted(_PROTOCOLS))
@pytest.mark.parametrize(("alias", "value"), [("pop_size", 8), ("elite_size", 3)])
def test_protocol_path_rejects_doe_alias_next_to_the_full_schema(protocol, alias, value) -> None:
    params = {**GA_SCHEMA, alias: value, **_PROTOCOLS[protocol]}
    with pytest.raises(ValueError, match="unknown"):
        AlgorithmRegistry.get_executor("Core-GA-TSP")(TINY_TSP, params, 1, 0)


@pytest.mark.parametrize("protocol", sorted(_PROTOCOLS))
def test_protocol_path_rejects_alias_only_parameter_set(protocol) -> None:
    params = {k: v for k, v in GA_SCHEMA.items() if k not in {"population_size", "elite_count"}}
    params.update(pop_size=6, elite_size=2, **_PROTOCOLS[protocol])
    with pytest.raises(ValueError, match="unknown"):
        AlgorithmRegistry.get_executor("Core-GA-TSP")(TINY_TSP, params, 1, 0)


@pytest.mark.parametrize(
    "params",
    [
        {"pop_size": 8, "population_size": 6},
        {"population_size": 6, "pop_size": 8},
        {"elite_size": 3, "elite_count": 2},
        {"elite_count": 2, "elite_size": 3},
    ],
    ids=["pop-alias-first", "pop-canonical-first", "elite-alias-first", "elite-canonical-first"],
)
def test_non_protocol_alias_and_canonical_key_together_raise(params) -> None:
    with pytest.raises(ValueError, match="alias"):
        AlgorithmRegistry.get_executor("Core-GA-TSP")(TINY_TSP, params, 1, 0)
