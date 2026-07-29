"""Freeze the public production strategy-key surface before solver relocation."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
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


def test_importing_production_strategies_does_not_load_academic_capabilities() -> None:
    root = Path(TEST_ROOT)
    script = "\n".join((
        "import sys",
        f"sys.path.insert(0, {str(root)!r})",
        f"sys.path.insert(0, {str(root / 'optimizer_api')!r})",
        "import optimizer_api.strategies",
        "assert 'uniride_core.algorithms.capabilities' not in sys.modules",
    ))
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
