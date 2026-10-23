"""C-16b review fixes: routing engine identity and the diversity-step pooling identity."""
from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance

TINY_CVRP = ProblemInstance(
    name="c16b-tiny-cvrp",
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
    name="c16b-tiny-cvrptw",
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
    name="c16b-tiny-tsp",
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
PSO_PARAMS = {
    "swarm_size": 6, "max_iterations": 4, "max_no_improvement": 3,
    "inertia_weight": 0.729, "cognitive_coeff": 1.49445, "social_coeff": 1.49445,
    "max_velocity_size": 3, "reinit_interval": 2,
}


@pytest.mark.parametrize("problem", [TINY_CVRP, TINY_CVRPTW], ids=["cvrp", "cvrptw"])
def test_core_pso_routing_call_is_refused_before_any_engine_is_built(monkeypatch, problem) -> None:
    # Gate C follow-up (owner 2026-10-21): Core-PSO-TSP is TSP/ATSP only. It used to build the
    # Matrix-PSO-TSP-legacy engine here and label the routing row "Core-PSO-TSP".
    built: list[str] = []
    monkeypatch.setattr(
        registry_setup, "create_matrix_engine", lambda name: built.append(name)
    )
    with pytest.raises(registry_setup.CoreRoutingRefusedError, match="Core-PSO-TSP is a TSP/ATSP"):
        AlgorithmRegistry.get_executor("Core-PSO-TSP")(problem, {}, 42, 0)
    assert built == []


@pytest.mark.parametrize("problem", [TINY_CVRP, TINY_CVRPTW], ids=["cvrp", "cvrptw"])
def test_cvrp_alias_builds_the_pso_engine_under_its_own_name(monkeypatch, problem) -> None:
    real_create = registry_setup.create_matrix_engine
    built: list[tuple[str, str]] = []

    def recording_create(name):
        engine = real_create(name)
        built.append((name, type(engine).__name__))
        return engine

    monkeypatch.setattr(registry_setup, "create_matrix_engine", recording_create)
    alias = ("CVRP-" if problem.problem_type == "cvrp" else "CVRPTW-") + "Core-PSO-TSP"
    result = AlgorithmRegistry.get_executor(alias)(problem, {}, 42, 0)

    assert built == [("Matrix-PSO-TSP-legacy", "TSPMetaMatrixEngine")]
    assert result.algorithm == alias
    assert result.routes


def _row_termination_policy(protocol_key: str, protocol: dict) -> str:
    from academic_benchmark.core.preflight import probe_runtime_backends

    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail
    row = AlgorithmRegistry.get_executor("Core-PSO-TSP")(
        TINY_TSP, {**PSO_PARAMS, protocol_key: protocol}, 1, 0
    )
    return row.termination_policy


FIXED = ("fair_comparison", {
    "evaluation_budget": 24, "base_seed": 5, "protocol_version": "uniride-fair-tsp-v2",
    "comparison_regime": "fixed_evaluation_budget",
})
NATIVE = ("native_comparison", {
    "base_seed": 5, "protocol_version": "uniride-native-tsp-v1",
    "comparison_regime": "algorithm_native_termination",
})


@pytest.mark.parametrize("protocol", [FIXED, NATIVE], ids=["fixed", "native"])
def test_rows_carry_the_fixed_diversity_constants_as_pooling_identity(
    monkeypatch, protocol
) -> None:
    from uniride_core.algorithms.tsp_matrix_metaheuristics import PSOOptimizer

    assert PSOOptimizer.REINIT_RANDOM_FRACTION == 0.1
    assert PSOOptimizer.REINIT_MAX_SWAPS == 3
    base = _row_termination_policy(*protocol)
    assert "reinit_random_fraction=0.1;reinit_max_swaps=3" in base
    # the constants are not part of the strict schema ...
    from academic_benchmark.fairness import PSO_REQUIRED_PARAMS

    assert not {"reinit_random_fraction", "reinit_max_swaps"} & PSO_REQUIRED_PARAMS
    # ... and changing one produces a different row identity
    monkeypatch.setattr(PSOOptimizer, "REINIT_MAX_SWAPS", 2)
    monkeypatch.setattr(PSOOptimizer, "REINIT_RANDOM_FRACTION", 0.2)
    changed = _row_termination_policy(*protocol)
    assert "reinit_random_fraction=0.2;reinit_max_swaps=2" in changed
    assert changed != base


def test_non_protocol_path_ignores_unknown_keys_and_runs_no_validation() -> None:
    # legacy behaviour (same as GA): documented in the executor docstring
    assert "ignored" in registry_setup._make_canonical_pso_executor.__doc__
    result = AlgorithmRegistry.get_executor("Core-PSO-TSP")(
        TINY_TSP,
        {"swarm_size": 6, "max_iterations": 2, "polish_iters": 99, "bogus": True},
        7, 0,
    )
    assert result.algorithm == "Core-PSO-TSP"
    assert sorted(result.tour) == list(range(1, 7))
