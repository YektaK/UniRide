"""Factory helpers for core matrix-native algorithm engines."""

from __future__ import annotations

from typing import Dict

from uniride_core.algorithms.base_engine import UnifiedEngine
from uniride_core.algorithms.fcm_split_engine import FCMSplitMatrixEngine
from uniride_core.algorithms.greedy_engine import GreedyMatrixEngine
from uniride_core.algorithms.tsp_meta_engines import (
    solve_ga_tsp,
    solve_gwo_tsp,
    solve_hho_tsp,
    solve_pso_tsp,
    solve_two_opt_tsp,
)
from uniride_core.algorithms.tsp_meta_matrix_engine import TSPMetaMatrixEngine, TSPSolver


CORE_GREEDY_ALIASES = {
    "Core-Greedy-Routing": "Core-Greedy-Routing",
    "Greedy": "Core-Greedy-Routing",
    "greedy": "Core-Greedy-Routing",
    "core_greedy": "Core-Greedy-Routing",
}

CORE_TSP_SOLVERS: Dict[str, TSPSolver] = {
    "Core-TwoOpt-TSP": solve_two_opt_tsp,
    "Core-GA-TSP": solve_ga_tsp,
    "Core-PSO-TSP": solve_pso_tsp,
    "Core-GWO-TSP": solve_gwo_tsp,
    "Core-HHO-TSP": solve_hho_tsp,
}

CORE_TSP_ALIASES = {
    "Core-TwoOpt-TSP": "Core-TwoOpt-TSP",
    "Core-2OPT-TSP": "Core-TwoOpt-TSP",
    "Core-2-opt-TSP": "Core-TwoOpt-TSP",
    "Core-GA-TSP": "Core-GA-TSP",
    "Core-Genetic-TSP": "Core-GA-TSP",
    "Core-PSO-TSP": "Core-PSO-TSP",
    "Core-GWO-TSP": "Core-GWO-TSP",
    "Core-HHO-TSP": "Core-HHO-TSP",
    "FCM-GA-TSP": "FCM-GA-TSP",
    "FCM-PSO-TSP": "FCM-PSO-TSP",
    "FCM-GWO-TSP": "FCM-GWO-TSP",
    "FCM-HHO-TSP": "FCM-HHO-TSP",
}

FCM_TSP_SOLVERS: Dict[str, TSPSolver] = {
    "FCM-GA-TSP": solve_ga_tsp,
    "FCM-PSO-TSP": solve_pso_tsp,
    "FCM-GWO-TSP": solve_gwo_tsp,
    "FCM-HHO-TSP": solve_hho_tsp,
}


def canonical_matrix_engine_name(name: str) -> str:
    """Return the canonical core matrix-native engine name for an alias."""
    if name in CORE_GREEDY_ALIASES:
        return CORE_GREEDY_ALIASES[name]
    if name in CORE_TSP_ALIASES:
        return CORE_TSP_ALIASES[name]
    raise KeyError(name)


def create_matrix_engine(name: str) -> UnifiedEngine:
    """Create a core matrix-native engine by canonical name or compatibility alias."""
    canonical_name = canonical_matrix_engine_name(name)
    if canonical_name == "Core-Greedy-Routing":
        return GreedyMatrixEngine()
    if canonical_name in FCM_TSP_SOLVERS:
        return FCMSplitMatrixEngine(canonical_name, FCM_TSP_SOLVERS[canonical_name])
    if canonical_name in CORE_TSP_SOLVERS:
        return TSPMetaMatrixEngine(canonical_name, CORE_TSP_SOLVERS[canonical_name])
    raise KeyError(name)


def list_matrix_engine_names() -> list[str]:
    """List canonical core matrix-native engine names."""
    return ["Core-Greedy-Routing", *CORE_TSP_SOLVERS.keys(), *FCM_TSP_SOLVERS.keys()]


__all__ = [
    "CORE_GREEDY_ALIASES",
    "CORE_TSP_ALIASES",
    "CORE_TSP_SOLVERS",
    "FCM_TSP_SOLVERS",
    "canonical_matrix_engine_name",
    "create_matrix_engine",
    "list_matrix_engine_names",
]
