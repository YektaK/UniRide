"""
L5: CI regression gate — runs 5 TSP benchmarks across all SOTA solvers.

Fails if any solver exceeds the gap threshold on any problem.
Uses synthetic problems with known optimal (brute-force computed).
No network or TSPLIB data required.
"""

import math
import itertools
import pytest
from typing import List, Tuple

from uniride_core.algorithms.sota_tsp.e2bso_tsp import E2BSO_TSP, E2BSOTSPConfig
from uniride_core.algorithms.sota_tsp.r2dma_tsp import R2DMA_TSP, R2DMATSPConfig
from uniride_core.algorithms.sota_tsp.paoea_tsp import PAOEA_TSP, PAOEAConfig
from uniride_core.algorithms.sota_tsp.cgo_tsp import CGO_TSP, CGOConfig
from uniride_core.algorithms.sota_tsp.run_tsp import RUN_TSP, RUNConfig
from uniride_core.algorithms.sota_tsp.alns_tsp import ALNS_TSP, ALNSConfig

# ── 5 benchmark problems ────────────────────────────────────────────────

PROBLEMS = {
    "4-square": [(0, 0), (10, 0), (10, 10), (0, 10)],
    "5-cross": [(0, 0), (10, 0), (10, 10), (0, 10), (5, 5)],
    "6-random": [(0, 0), (3, 7), (8, 2), (1, 9), (6, 4), (9, 8)],
    "7-grid": [(0, 0), (0, 5), (0, 10), (5, 10), (10, 10), (10, 5), (10, 0)],
    "8-cluster": [(0, 0), (1, 1), (0, 10), (1, 9), (10, 0), (9, 1), (10, 10), (9, 9)],
}

# Solvers to test (configs tuned for fast CI — low iterations)
SOLVER_SPECS = [
    ("E2BSO", lambda: E2BSO_TSP(E2BSOTSPConfig(population_size=10, max_iterations=30, seed=42))),
    ("R2DMA", lambda: R2DMA_TSP(R2DMATSPConfig(population_size=10, max_iterations=30, seed=42, tournament_k=3))),
    ("P-AOEA", lambda: PAOEA_TSP(PAOEAConfig(population_size=10, max_iterations=30, genome_population_size=4, seed=42))),
    ("CGO",    lambda: CGO_TSP(CGOConfig(population_size=10, max_iterations=30, seed=42))),
    ("RUN",    lambda: RUN_TSP(RUNConfig(population_size=10, max_iterations=30, seed=42))),
    ("ALNS",   lambda: ALNS_TSP(ALNSConfig(iterations=500, seed=42))),
]

GAP_THRESHOLD_PCT = 15.0


def _euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _brute_force_optimal(coords: List[Tuple[float, float]]) -> float:
    best = float("inf")
    n = len(coords)
    for perm in itertools.permutations(range(n)):
        cost = sum(_euclidean(coords[perm[i]], coords[perm[(i + 1) % n]]) for i in range(n))
        if cost < best:
            best = cost
    return best


# Pre-compute optimal for each problem
_OPTIMALS = {name: _brute_force_optimal(coords) for name, coords in PROBLEMS.items()}


def _valid_tour(tour, n):
    assert len(tour) == n, f"Tour length {len(tour)} != {n}"
    assert set(tour) == set(range(n)), f"Tour missing or duplicate nodes"


@pytest.mark.parametrize("prob_name, coords", list(PROBLEMS.items()))
@pytest.mark.parametrize("solver_name, solver_factory", SOLVER_SPECS)
def test_solver_gap_on_problem(solver_name, solver_factory, prob_name, coords):
    solver = solver_factory()
    result = solver.solve(coords)
    _valid_tour(result.tour, len(coords))
    optimal = _OPTIMALS[prob_name]
    gap = (result.tour_length - optimal) / optimal * 100.0
    assert gap < GAP_THRESHOLD_PCT, (
        f"{solver_name} on {prob_name}: gap={gap:.1f}% "
        f"(tour={result.tour_length:.1f}, opt={optimal:.1f}), "
        f"threshold={GAP_THRESHOLD_PCT}%"
    )
