"""C-19 (owner 2026-10-21, revised): in the Bildiri profile the budget is the stopping rule.

Every algorithm of the profile must end a fixed-budget run with ``evaluation_budget_exhausted``
(spending the budget up to the atomic remainder of its next phase) or with the documented
local-optimum reason ``no_improving_move`` of a deterministic local search, never with an
iteration or stagnation limit.

Fast check (a full run of every algorithm at 250 x n(n-1)/2 on kroA100 takes many minutes, the
3-opt alone most of it): the full matrix eil51/kroA100 x both levels was run once by script for the
C-19 report. Here:

1. every algorithm runs on eil51 (the smallest instance) at its lowest level and is checked;
2. the limits are checked against the largest level of the profile without running it:
   - pure GA, PSO, memetic GA, pure GWO and pure HHO: ``max_iterations`` and
     ``max_no_improvement`` >= the largest level; every generation/iteration of these
     algorithms spends at least one objective evaluation, so such a limit cannot fire first;
   - memetic GWO/HHO keep the C-04 limit 60000: the iterations per evaluation measured on eil51
     (smallest n, so the cheapest polish and the most iterations per evaluation of all profile
     instances) times the largest level stay below 60000;
   - 2-opt, 3-opt, Or-opt: one iteration is at least one full scan of n(n-1)/2 candidates, so an
     iteration limit of at least 250 (the largest scan multiplier) cannot fire first.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from academic_benchmark.validation.hamiltonian_cycle import (
    parse_coordinates,
    parse_header,
    tsplib_distance,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STUDY = json.loads(
    (REPOSITORY_ROOT / "academic_benchmark/studies/bildiri2026/study.json").read_text(encoding="utf-8")
)
TABLE = STUDY["scaled_fixed_budget_levels"]["levels_by_dataset"]
LARGEST_LEVEL = max(level for levels in TABLE.values() for level in levels)
LARGEST_MULTIPLIER = max(STUDY["scaled_fixed_budget_levels"]["scan_multipliers"])
LOCAL_SEARCH = ("Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-OrOpt-TSP")
LIMITS_AT_LARGEST_LEVEL = (
    "Core-GA-TSP", "Core-PSO-TSP", "Core-GA-TSP-Memetic-2opt", "Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure",
)
MEMETIC_SWARM = ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt")
C04_LIMIT = 60000


def _atomic_remainder_bound(algorithm_id: str) -> int:
    """Largest unspent budget allowed after ``evaluation_budget_exhausted`` (next atomic phase)."""
    params = STUDY["algorithm_parameters"][algorithm_id]
    if algorithm_id in ("Core-GA-TSP", "Core-PSO-TSP"):
        return params.get("population_size", params.get("swarm_size"))
    if algorithm_id == "Core-GWO-TSP-Pure":
        return params["pack_size"]
    if algorithm_id == "Core-HHO-TSP-Pure":
        return 3 * params["hawks"]
    return 1  # local-search candidates and polish candidates are atomic single evaluations


@lru_cache(maxsize=None)
def _eil51() -> ProblemInstance:
    text = (REPOSITORY_ROOT / "academic_benchmark/tsplib_data/tsp/eil51.tsp").read_text(encoding="utf-8")
    ewt = parse_header(text)["EDGE_WEIGHT_TYPE"].upper()
    c = parse_coordinates(text)
    matrix = [[0.0 if i == j else float(tsplib_distance(ewt, c[i], c[j])) for j in range(len(c))]
              for i in range(len(c))]
    return ProblemInstance(name="eil51", dimension=len(matrix), coordinates=[], problem_type="tsp",
                           dist_matrix=matrix, optimal=426.0)


@lru_cache(maxsize=None)
def _run_eil51_lowest(algorithm_id: str):
    budget = TABLE["tsplib-eil51"][0]
    params = dict(STUDY["algorithm_parameters"][algorithm_id])
    params["fair_comparison"] = {"evaluation_budget": budget, "base_seed": STUDY["base_seed"]}
    return budget, AlgorithmRegistry.get_executor(algorithm_id)(_eil51(), params, seed=1, run_idx=0)


def test_largest_level_is_kroa100_rd100_at_250_scans():
    assert LARGEST_LEVEL == 250 * 4950 == 1237500 and LARGEST_MULTIPLIER == 250


@pytest.mark.parametrize("algorithm_id", STUDY["algorithm_ids"])
def test_eil51_lowest_level_ends_on_the_budget_or_a_local_optimum(algorithm_id):
    budget, result = _run_eil51_lowest(algorithm_id)
    reason = result.termination_reason
    assert result.objective_evaluations <= budget
    if reason == "no_improving_move":  # documented local-optimum stop of a deterministic local search
        assert algorithm_id in LOCAL_SEARCH
        return
    assert reason == "evaluation_budget_exhausted", (algorithm_id, reason)
    assert budget - result.objective_evaluations < _atomic_remainder_bound(algorithm_id), (
        algorithm_id, result.objective_evaluations,
    )


@pytest.mark.parametrize("algorithm_id", LIMITS_AT_LARGEST_LEVEL)
def test_iteration_and_stagnation_limits_reach_the_largest_level(algorithm_id):
    params = STUDY["algorithm_parameters"][algorithm_id]
    assert params["max_iterations"] >= LARGEST_LEVEL
    assert params["max_no_improvement"] >= LARGEST_LEVEL


@pytest.mark.parametrize("algorithm_id", MEMETIC_SWARM)
def test_memetic_swarm_c04_limit_cannot_bind_before_the_largest_level(algorithm_id):
    params = STUDY["algorithm_parameters"][algorithm_id]
    assert params["max_iterations"] == params["max_no_improvement"] == C04_LIMIT
    budget, result = _run_eil51_lowest(algorithm_id)
    assert result.termination_reason == "evaluation_budget_exhausted"
    iterations_per_evaluation = result.iterations / result.objective_evaluations
    assert iterations_per_evaluation * LARGEST_LEVEL < C04_LIMIT, iterations_per_evaluation


@pytest.mark.parametrize("algorithm_id", LOCAL_SEARCH)
def test_local_search_iteration_limit_exceeds_the_largest_scan_multiplier(algorithm_id):
    budget, result = _run_eil51_lowest(algorithm_id)
    found = re.search(r"max_iterations=(\d+)", str(result.termination_policy))
    assert found, result.termination_policy
    assert int(found.group(1)) >= LARGEST_MULTIPLIER
    # one iteration spends at least one full scan of n(n-1)/2 candidates (the last may stop early)
    if result.iterations > 1:
        assert result.objective_evaluations / (result.iterations - 1) >= 51 * 50 // 2
