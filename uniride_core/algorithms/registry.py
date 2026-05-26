"""Core-owned algorithm family metadata.

This module intentionally contains discovery metadata, not web/API routing.
Application layers can map these stable core names to their own compatibility
keys while keeping solver ownership in ``uniride_core``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple


@dataclass(frozen=True)
class AlgorithmFamilySpec:
    name: str
    category: str
    problem_types: Tuple[str, ...]
    aliases: Tuple[str, ...] = ()
    param_space: Optional[str] = None


_ALGORITHM_SPECS: Tuple[AlgorithmFamilySpec, ...] = (
    AlgorithmFamilySpec("2-OPT", "local_search", ("tsp", "atsp"), ("two_opt", "2opt", "Numba-2-opt"), "3-OPT-BOUNDED"),
    AlgorithmFamilySpec("3-OPT", "local_search", ("tsp", "atsp"), ("three_opt", "3opt", "Numba-3-opt-bounded"), "3-OPT-BOUNDED"),
    AlgorithmFamilySpec("OR-OPT", "local_search", ("tsp", "atsp"), ("or_opt", "Numba-Or-opt"), "3-OPT-BOUNDED"),
    AlgorithmFamilySpec("SWAP", "local_search", ("tsp", "atsp"), ("swap", "Numba-Swap"), "3-OPT-BOUNDED"),
    AlgorithmFamilySpec("HYBRID", "local_search", ("tsp", "atsp"), ("hybrid", "Numba-Hybrid"), "3-OPT-BOUNDED"),
    AlgorithmFamilySpec("GA", "metaheuristic", ("tsp", "atsp"), ("genetic_algorithm", "ga", "Numba-GA"), "GA"),
    AlgorithmFamilySpec("PSO", "metaheuristic", ("tsp", "atsp"), ("pso", "Numba-PSO"), "PSO"),
    AlgorithmFamilySpec("GWO", "metaheuristic", ("tsp", "atsp"), ("gwo", "grey_wolf", "Numba-GWO"), "GWO"),
    AlgorithmFamilySpec("HHO", "metaheuristic", ("tsp", "atsp"), ("hho", "harris_hawks", "Numba-HHO"), "HHO"),
    AlgorithmFamilySpec("GA-Split", "pipeline_b", ("cvrp", "cvrptw", "uniride"), ("ga_split", "ga-split"), "GA-Split"),
    AlgorithmFamilySpec("PSO-Split", "pipeline_b", ("cvrp", "cvrptw", "uniride"), ("pso_split", "pso-split"), "PSO-Split"),
    AlgorithmFamilySpec("GWO-Split", "pipeline_b", ("cvrp", "cvrptw", "uniride"), ("gwo_split", "gwo-split"), "GWO-Split"),
    AlgorithmFamilySpec("HHO-Split", "pipeline_b", ("cvrp", "cvrptw", "uniride"), ("hho_split", "hho-split"), "HHO-Split"),
    AlgorithmFamilySpec("OR-Tools", "holistic", ("cvrp", "cvrptw", "uniride"), ("ortools", "ortools_cvrp")),
    AlgorithmFamilySpec("PyVRP", "holistic", ("cvrp", "cvrptw", "uniride"), ("pyvrp", "hgs")),
    AlgorithmFamilySpec("VROOM", "holistic", ("cvrp", "cvrptw", "uniride"), ("vroom", "vroom_fallback")),
    AlgorithmFamilySpec("Greedy", "heuristic", ("tsp", "atsp", "cvrp", "cvrptw", "uniride"), ("greedy", "nearest_neighbor")),
    AlgorithmFamilySpec("E2BSO-TSP", "sota_tsp", ("tsp", "atsp"), ("SOTA-E2BSO-TSP",), "E2BSO-TSP"),
    AlgorithmFamilySpec("E2BSO-TSP-CPSO", "sota_tsp", ("tsp", "atsp"), ("SOTA-E2BSO-TSP-CPSO",), "E2BSO-TSP-CPSO"),
    AlgorithmFamilySpec("R2DMA-TSP", "sota_tsp", ("tsp", "atsp"), ("SOTA-R2DMA-TSP",), "R2DMA-TSP"),
    AlgorithmFamilySpec("P-AOEA-TSP", "sota_tsp", ("tsp", "atsp"), ("SOTA-P-AOEA-TSP",), "P-AOEA-TSP"),
    AlgorithmFamilySpec("CGO-TSP", "sota_tsp", ("tsp", "atsp"), ("SOTA-CGO-TSP",), "CGO-TSP"),
    AlgorithmFamilySpec("RUN-TSP", "sota_tsp", ("tsp", "atsp"), ("SOTA-RUN-TSP",), "RUN-TSP"),
    AlgorithmFamilySpec("ALNS-TSP", "sota_tsp", ("tsp", "atsp"), ("SOTA-ALNS-TSP",), "ALNS-TSP"),
)


def list_algorithm_specs(category: Optional[str] = None) -> Tuple[AlgorithmFamilySpec, ...]:
    if category is None:
        return _ALGORITHM_SPECS
    return tuple(spec for spec in _ALGORITHM_SPECS if spec.category == category)


def list_algorithm_names(category: Optional[str] = None) -> Tuple[str, ...]:
    return tuple(spec.name for spec in list_algorithm_specs(category))


def alias_map(specs: Iterable[AlgorithmFamilySpec] = _ALGORITHM_SPECS) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for spec in specs:
        mapping[spec.name] = spec.name
        for alias in spec.aliases:
            mapping[alias] = spec.name
    return mapping


def normalize_algorithm_name(name: str) -> str:
    return alias_map().get(name, name)
