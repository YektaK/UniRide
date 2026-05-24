import math
import itertools
import pytest
from typing import List, Tuple
from uniride_core.algorithms.sota_tsp.e2bso_tsp import E2BSO_TSP, E2BSOTSPConfig
from uniride_core.algorithms.sota_tsp.r2dma_tsp import R2DMA_TSP, R2DMATSPConfig
from uniride_core.algorithms.sota_tsp.paoea_tsp import PAOEA_TSP, PAOEAConfig
from uniride_core.algorithms.sota_tsp.cgo_tsp import CGO_TSP, CGOConfig
from uniride_core.algorithms.sota_tsp.run_tsp import RUN_TSP, RUNConfig

# A trivial 5-node complete graph coordinate set
TRIVIAL_COORDS: List[Tuple[float, float]] = [
    (0.0, 0.0),
    (0.0, 10.0),
    (10.0, 10.0),
    (10.0, 0.0),
    (5.0, 5.0)
]

def euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def brute_force_optimal(coords: List[Tuple[float, float]]) -> float:
    best = float("inf")
    n = len(coords)
    for perm in itertools.permutations(range(n)):
        cost = sum(euclidean(coords[perm[i]], coords[perm[(i + 1) % n]]) for i in range(n))
        if cost < best:
            best = cost
    return best

def check_valid_tour(tour: List[int], n: int):
    assert len(tour) == n, f"Tour length {len(tour)} does not match n={n}"
    assert set(tour) == set(range(n)), "Tour does not contain all nodes exactly once"

@pytest.mark.parametrize("solver_cls, config_cls", [
    (E2BSO_TSP, E2BSOTSPConfig),
    (R2DMA_TSP, R2DMATSPConfig),
    (PAOEA_TSP, PAOEAConfig),
    (CGO_TSP, CGOConfig),
    (RUN_TSP, RUNConfig)
])
def test_sota_solvers_smoke(solver_cls, config_cls):
    """Smoke test to ensure the solver can instantiate and solve a small problem."""
    
    # We pass config overrides to make tests run extremely fast
    kwargs = {
        "max_iterations": 2,
        "ls_time_limit": 0.1,
        "time_limit": 10.0,
        "seed": 42
    }
    
    if solver_cls.__name__ == "PAOEA_TSP":
        kwargs["genome_population_size"] = 5
        kwargs["population_size"] = 10
    else:
        kwargs["population_size"] = 10
        
    try:
        config1 = config_cls(**kwargs)
        solver = solver_cls(config1)
        result = solver.solve(TRIVIAL_COORDS)
        
        check_valid_tour(result.tour, len(TRIVIAL_COORDS))
        
        # Verify cost correctness
        computed_cost = solver.tour_length(result.tour)
        assert abs(computed_cost - result.tour_length) < 1e-5, f"Mismatch in cost: {computed_cost} != {result.tour_length}"
        
        # Basic reproducibility (same seed = same cost)
        config2 = config_cls(**kwargs)
        solver2 = solver_cls(config2)
        result2 = solver2.solve(TRIVIAL_COORDS)
        assert result.tour_length == result2.tour_length, "Reproducibility failed"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        pytest.fail(f"{solver_cls.__name__} failed with {type(e).__name__}: {e}")


SQUARE_COORDS: List[Tuple[float, float]] = [
    (0.0, 0.0),
    (0.0, 10.0),
    (10.0, 10.0),
    (10.0, 0.0),
]

KNOWN_OPTIMAL_4 = brute_force_optimal(SQUARE_COORDS)


@pytest.mark.parametrize("solver_cls, config_cls", [
    (E2BSO_TSP, E2BSOTSPConfig),
    (R2DMA_TSP, R2DMATSPConfig),
    (PAOEA_TSP, PAOEAConfig),
    (CGO_TSP, CGOConfig),
    (RUN_TSP, RUNConfig)
])
def test_known_optimal_4node(solver_cls, config_cls):
    kwargs = {
        "max_iterations": 100,
        "population_size": 30,
        "ls_time_limit": 0.5,
        "time_limit": 30.0,
        "seed": 42
    }
    config = config_cls(**kwargs)
    solver = solver_cls(config)
    result = solver.solve(SQUARE_COORDS)
    check_valid_tour(result.tour, len(SQUARE_COORDS))
    gap = (result.tour_length - KNOWN_OPTIMAL_4) / KNOWN_OPTIMAL_4 * 100.0
    assert gap < 5.0, f"{solver_cls.__name__} gap={gap:.2f}% on 4-node square (opt={KNOWN_OPTIMAL_4}, got={result.tour_length})"
