"""Freeze the public production strategy-key surface before solver relocation."""
from __future__ import annotations

import os
import sys

TEST_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPTIMIZER_API_ROOT = os.path.join(TEST_ROOT, "optimizer_api")
sys.path.insert(0, TEST_ROOT)
sys.path.insert(0, OPTIMIZER_API_ROOT)

from optimizer_api.strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY


EXPECTED_PRODUCTION_STRATEGIES = frozenset({
    "genetic_algorithm", "ga", "pso", "gwo", "grey_wolf", "hho",
    "harris_hawks", "ga_split", "ga-split", "ga_split_enhanced",
    "ga-split-enhanced", "pso_split", "pso-split", "gwo_split",
    "gwo-split", "hho_split", "hho-split", "ortools_cvrp", "ortools",
    "pyvrp", "hgs", "pyvrp_alt", "vroom", "vroom_fallback", "e2bso",
    "entropy_bso", "e2b", "r2dma", "rdma", "paoea", "aoea", "two_opt",
    "2opt", "greedy", "nearest_neighbor", "permutation_tsp", "permutation",
    "exact",
})


def test_production_strategy_registry_has_exact_compatibility_surface() -> None:
    assert set(STRATEGY_REGISTRY) == EXPECTED_PRODUCTION_STRATEGIES
    assert set(STRATEGY_FACTORIES) == EXPECTED_PRODUCTION_STRATEGIES