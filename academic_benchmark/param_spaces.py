#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
param_spaces.py — Unified parameter space definitions for all algorithms.

Single source of truth for DoE grid search and Optuna Bayesian optimization.
Each parameter defines its type, range (for Optuna), and discrete values (for DoE).

Usage:
    from academic_benchmark.param_spaces import (
        SOTA_PARAM_SPACES, NUMBA_PARAM_SPACES,
        build_doe_space, build_optuna_space,
    )
"""

from typing import Any, Dict, List, Optional

# ── SOTA Algorithm Parameter Spaces ──────────────────────────────────────────

SOTA_PARAM_SPACES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "E2BSO-TSP": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "gamma":               {"type": "float", "doe": [0.15, 0.20, 0.30],  "optuna": (0.10, 0.35)},
        "injection_rate":      {"type": "float", "doe": [0.08, 0.12, 0.18],  "optuna": (0.05, 0.25)},
        "remove_ratio":        {"type": "float", "doe": [0.10, 0.15, 0.20],  "optuna": (0.05, 0.25)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
    "E2BSO-TSP-CPSO": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "gamma":               {"type": "float", "doe": [0.15, 0.20, 0.30],  "optuna": (0.10, 0.35)},
        "injection_rate":      {"type": "float", "doe": [0.08, 0.12, 0.18],  "optuna": (0.05, 0.25)},
        "remove_ratio":        {"type": "float", "doe": [0.10, 0.15, 0.20],  "optuna": (0.05, 0.25)},
        "c1":                  {"type": "float", "doe": [1.0, 1.5, 2.0],     "optuna": (0.5, 2.5)},
        "c2":                  {"type": "float", "doe": [1.0, 1.5, 2.0],     "optuna": (0.5, 2.5)},
        "inertia":             {"type": "float", "doe": [0.5, 0.7, 0.9],     "optuna": (0.3, 0.95)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
    "R2DMA-TSP": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "theta_base":          {"type": "float", "doe": [0.15, 0.25, 0.35],  "optuna": (0.10, 0.40)},
        "remove_ratio":        {"type": "float", "doe": [0.10, 0.15, 0.20],  "optuna": (0.05, 0.25)},
        "pulse_injection_rate":{"type": "float", "doe": [0.05, 0.10, 0.15],  "optuna": (0.02, 0.20)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
    "P-AOEA-TSP": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "genome_population_size": {"type": "int","doe": [8, 12, 16],         "optuna": (6, 20)},
        "crossover_rate":      {"type": "float", "doe": [0.75, 0.85, 0.95],  "optuna": (0.60, 0.99)},
        "mutation_rate":       {"type": "float", "doe": [0.10, 0.18, 0.26],  "optuna": (0.05, 0.30)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
    "CGO-TSP": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "chaos_rate":          {"type": "float", "doe": [3.80, 3.90, 3.99],  "optuna": (3.57, 4.0)},
        "seed_length_ratio":   {"type": "float", "doe": [0.15, 0.25, 0.35],  "optuna": (0.10, 0.40)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
    "RUN-TSP": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "beta":                {"type": "float", "doe": [0.3, 0.5, 0.7],     "optuna": (0.1, 0.9)},
        "esq_probability":     {"type": "float", "doe": [0.1, 0.2, 0.3],     "optuna": (0.05, 0.40)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
    "ALNS-TSP": {
        "population_size":     {"type": "int",   "doe": [24, 36, 48],        "optuna": (20, 60)},
        "max_iterations":      {"type": "int",   "doe": [200, 320, 450],     "optuna": (150, 500)},
        "remove_ratio":        {"type": "float", "doe": [0.10, 0.15, 0.20],  "optuna": (0.05, 0.25)},
        "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
    },
}

# ── Numba Engine Parameter Spaces ────────────────────────────────────────────

NUMBA_PARAM_SPACES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "GA": {
        "pop_size":        {"type": "int", "doe": [80, 120, 150]},
        "generations":     {"type": "int", "doe": [250, 350, 500]},
        "mutation_rate":   {"type": "float", "doe": [0.08, 0.12, 0.16]},
        "elite_size":      {"type": "int", "doe": [2, 4, 6, 8]},
        "crossover_rate":  {"type": "float", "doe": [0.80, 0.85, 0.90]},
    },
    "PSO": {
        "swarm_size":      {"type": "int", "doe": [50, 80, 120]},
        "iterations":      {"type": "int", "doe": [200, 300, 450, 500]},
        "w":               {"type": "float", "doe": [0.65, 0.72, 0.80]},
        "c1":              {"type": "float", "doe": [1.4, 1.6, 1.9]},
        "c2":              {"type": "float", "doe": [1.4, 1.6, 1.9]},
        "reinit_interval": {"type": "int", "doe": [30, 50, 70]},
    },
    "GWO": {
        "pack_size":       {"type": "int", "doe": [50, 80, 120]},
        "iterations":      {"type": "int", "doe": [200, 300, 450]},
    },
    "HHO": {
        "hawks":           {"type": "int", "doe": [50, 80, 120]},
        "iterations":      {"type": "int", "doe": [200, 300, 450]},
    },
    "B-PSO": {
        "swarm_size":      {"type": "int", "doe": [30, 50, 80]},
        "max_iterations":  {"type": "int", "doe": [300, 500]},
        "inertia_weight":  {"type": "float", "doe": [0.729]},
        "cognitive_coeff": {"type": "float", "doe": [1.49445]},
        "social_coeff":    {"type": "float", "doe": [1.49445]},
        "max_velocity_size": {"type": "int", "doe": [5, 8]},
        "reinit_interval": {"type": "int", "doe": [30, 50]},
        "max_no_improvement": {"type": "int", "doe": [100]},
    },
    "GA-Split": {
        "pop_size":        {"type": "int", "doe": [80, 120, 150]},
        "generations":     {"type": "int", "doe": [250, 350, 500]},
        "mutation_rate":   {"type": "float", "doe": [0.08, 0.12, 0.16]},
        "elite_size":      {"type": "int", "doe": [2, 4, 6, 8]},
        "crossover_rate":  {"type": "float", "doe": [0.80, 0.85, 0.90]},
        "max_stops_bounded": {"type": "int", "doe": [10, 15, 20]},
    },
    "PSO-Split": {
        "swarm_size":      {"type": "int", "doe": [50, 80, 120]},
        "iterations":      {"type": "int", "doe": [200, 300, 450, 500]},
        "w":               {"type": "float", "doe": [0.65, 0.72, 0.80]},
        "c1":              {"type": "float", "doe": [1.4, 1.6, 1.9]},
        "c2":              {"type": "float", "doe": [1.4, 1.6, 1.9]},
        "reinit_interval": {"type": "int", "doe": [30, 50, 70]},
        "max_stops_bounded": {"type": "int", "doe": [10, 15, 20]},
    },
    "GWO-Split": {
        "pack_size":       {"type": "int", "doe": [50, 80, 120]},
        "iterations":      {"type": "int", "doe": [200, 300, 450]},
        "max_stops_bounded": {"type": "int", "doe": [10, 15, 20]},
    },
    "HHO-Split": {
        "hawks":           {"type": "int", "doe": [50, 80, 120]},
        "iterations":      {"type": "int", "doe": [200, 300, 450]},
        "max_stops_bounded": {"type": "int", "doe": [10, 15, 20]},
    },
    "B-GA": {
        "population_size": {"type": "int", "doe": [80, 100, 150]},
        "generations":     {"type": "int", "doe": [300, 500]},
        "crossover_rate":  {"type": "float", "doe": [0.80, 0.85, 0.90]},
        "mutation_rate":   {"type": "float", "doe": [0.12, 0.15, 0.18]},
        "elite_count":     {"type": "int", "doe": [2, 4]},
        "tournament_size": {"type": "int", "doe": [3, 5]},
        "max_no_improvement": {"type": "int", "doe": [100]},
    },
    "3-OPT-BOUNDED": {
        "max_iterations":  {"type": "int", "doe": [300, 500, 1000]},
        "first_improvement": {"type": "bool", "doe": [True, False]},
        "window":          {"type": "int", "doe": [8, 12, 20, 50]},
    },
}


# ── Routing Problem Parameter Spaces ─────────────────────────────────────────

ROUTING_SPLIT_PARAM_SPACE: Dict[str, Dict[str, Any]] = {
    "split_method": {
        "type": "categorical",
        "doe": ["optimal_split"],
        "optuna": ["optimal_split"],
    },
    "vehicle_penalty": {
        "type": "float",
        "doe": [25.0, 50.0, 100.0],
        "optuna": (10.0, 150.0),
    },
    "capacity_penalty": {
        "type": "float",
        "doe": [100.0, 500.0, 1000.0],
        "optuna": (50.0, 2000.0),
    },
    "tw_penalty_rate": {
        "type": "float",
        "doe": [5.0, 10.0, 25.0],
        "optuna": (1.0, 50.0),
    },
    "max_route_duration_penalty": {
        "type": "float",
        "doe": [5.0, 10.0, 25.0],
        "optuna": (1.0, 50.0),
    },
    "max_stops_bounded": {
        "type": "int",
        "doe": [10, 15, 20],
        "optuna": (5, 30),
    },
}


def _with_routing_params(base: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
    params: Dict[str, Dict[str, Any]] = {}
    if base:
        params.update({key: value.copy() for key, value in base.items()})
    params.update({key: value.copy() for key, value in ROUTING_SPLIT_PARAM_SPACE.items()})
    return params


_SOTA_ROUTING_BASES = {
    name: SOTA_PARAM_SPACES[name]
    for name in [
        "E2BSO-TSP",
        "R2DMA-TSP",
        "P-AOEA-TSP",
        "CGO-TSP",
        "RUN-TSP",
        "ALNS-TSP",
    ]
}

_NUMBA_ROUTING_BASES = {
    "Numba-2-opt": NUMBA_PARAM_SPACES.get("3-OPT-BOUNDED", {}),
    "Numba-3-opt-bounded": NUMBA_PARAM_SPACES.get("3-OPT-BOUNDED", {}),
    "Numba-Or-opt": NUMBA_PARAM_SPACES.get("3-OPT-BOUNDED", {}),
    "Numba-Swap": NUMBA_PARAM_SPACES.get("3-OPT-BOUNDED", {}),
    "Numba-Hybrid": NUMBA_PARAM_SPACES.get("3-OPT-BOUNDED", {}),
    "Numba-GA": NUMBA_PARAM_SPACES["GA"],
    "Numba-PSO": NUMBA_PARAM_SPACES["PSO"],
    "Numba-GWO": NUMBA_PARAM_SPACES["GWO"],
    "Numba-HHO": NUMBA_PARAM_SPACES["HHO"],
    "Core-Greedy-Routing": {},
    "Core-TwoOpt-TSP": NUMBA_PARAM_SPACES.get("3-OPT-BOUNDED", {}),
    "Core-GA-TSP": NUMBA_PARAM_SPACES["GA"],
    "Core-PSO-TSP": NUMBA_PARAM_SPACES["PSO"],
    "Core-GWO-TSP": NUMBA_PARAM_SPACES["GWO"],
    "Core-HHO-TSP": NUMBA_PARAM_SPACES["HHO"],
}

FCM_PARAM_SPACE = {
    "fcm_clusters": {"type": "int", "doe": [2, 3, 4], "optuna": (2, 6)},
    "fcm_m": {"type": "float", "doe": [1.5, 2.0, 2.5], "optuna": (1.1, 3.0)},
    "fcm_iterations": {"type": "int", "doe": [50, 100], "optuna": (25, 150)},
    "fcm_min_cluster_size": {"type": "int", "doe": [4, 8], "optuna": (2, 20)},
    "fcm_polish_iterations": {"type": "int", "doe": [100, 200], "optuna": (50, 400)},
}


def _with_fcm_params(base: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    params = {key: value.copy() for key, value in base.items()}
    params.update({key: value.copy() for key, value in FCM_PARAM_SPACE.items()})
    return params


for _name, _base_key in {
    "FCM-GA-TSP": "GA",
    "FCM-PSO-TSP": "PSO",
    "FCM-GWO-TSP": "GWO",
    "FCM-HHO-TSP": "HHO",
}.items():
    NUMBA_PARAM_SPACES[_name] = _with_fcm_params(NUMBA_PARAM_SPACES[_base_key])

CVRP_PARAM_SPACES: Dict[str, Dict[str, Dict[str, Any]]] = {}
CVRPTW_PARAM_SPACES: Dict[str, Dict[str, Dict[str, Any]]] = {}

for base_name, base_space in _SOTA_ROUTING_BASES.items():
    for prefix in ("SOTA-", ""):
        name = f"{prefix}{base_name}"
        CVRP_PARAM_SPACES[f"CVRP-{name}"] = _with_routing_params(base_space)
        CVRPTW_PARAM_SPACES[f"CVRPTW-{name}"] = _with_routing_params(base_space)

for base_name, base_space in _NUMBA_ROUTING_BASES.items():
    CVRP_PARAM_SPACES[f"CVRP-{base_name}"] = _with_routing_params(base_space)
    CVRPTW_PARAM_SPACES[f"CVRPTW-{base_name}"] = _with_routing_params(base_space)

SOTA_PARAM_SPACES.update(
    {
        key: value
        for key, value in {**CVRP_PARAM_SPACES, **CVRPTW_PARAM_SPACES}.items()
        if "SOTA-" in key or any(algo in key for algo in _SOTA_ROUTING_BASES)
    }
)
NUMBA_PARAM_SPACES.update(
    {
        key: value
        for key, value in {**CVRP_PARAM_SPACES, **CVRPTW_PARAM_SPACES}.items()
        if key not in SOTA_PARAM_SPACES
    }
)


# ── Builder Functions ────────────────────────────────────────────────────────

def build_doe_space(algo_name: str, source: str = "sota") -> Dict[str, List[Any]]:
    """Build DoE grid search parameter space from unified definitions."""
    spaces = SOTA_PARAM_SPACES if source == "sota" else NUMBA_PARAM_SPACES
    space = spaces.get(algo_name, {})
    return {key: val["doe"] for key, val in space.items()}


def build_optuna_space(algo_name: str, trial) -> Dict[str, Any]:
    """Build Optuna trial parameter space from unified definitions."""
    space = SOTA_PARAM_SPACES.get(algo_name) or NUMBA_PARAM_SPACES.get(algo_name, {})
    params = {}
    for key, val in space.items():
        optuna_range = val.get("optuna")
        if optuna_range is None:
            continue
        if val["type"] == "int":
            lo, hi = optuna_range
            params[key] = trial.suggest_int(key, lo, hi)
        elif val["type"] == "float":
            lo, hi = optuna_range
            params[key] = trial.suggest_float(key, lo, hi)
        elif val["type"] in {"categorical", "bool"}:
            params[key] = trial.suggest_categorical(key, optuna_range)
    return params
