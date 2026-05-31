from uniride_core.algorithms.registry import (
    alias_map,
    list_algorithm_names,
    list_algorithm_specs,
    normalize_algorithm_name,
)


def test_core_registry_exposes_required_algorithm_families():
    names = set(list_algorithm_names())
    assert {"GA", "PSO", "GWO", "HHO"}.issubset(names)
    assert {"Core-GA-TSP", "Core-PSO-TSP", "Core-GWO-TSP", "Core-HHO-TSP", "Core-TwoOpt-TSP"}.issubset(names)
    assert {"FCM-GA-TSP", "FCM-PSO-TSP", "FCM-GWO-TSP", "FCM-HHO-TSP"}.issubset(names)
    assert {"GA-Split", "PSO-Split", "GWO-Split", "HHO-Split"}.issubset(names)
    assert {"OR-Tools", "PyVRP", "VROOM", "Greedy"}.issubset(names)
    assert {"2-OPT", "3-OPT", "OR-OPT", "SWAP", "HYBRID"}.issubset(names)
    assert {"E2BSO-TSP", "R2DMA-TSP", "P-AOEA-TSP", "CGO-TSP", "RUN-TSP", "ALNS-TSP"}.issubset(names)


def test_core_registry_tracks_problem_type_coverage():
    split_specs = list_algorithm_specs("pipeline_b")
    assert split_specs
    for spec in split_specs:
        assert {"cvrp", "cvrptw", "uniride"}.issubset(set(spec.problem_types))


def test_core_registry_normalizes_compatibility_aliases():
    aliases = alias_map()
    assert aliases["ga_split"] == "GA-Split"
    assert aliases["genetic_algorithm"] == "GA"
    assert aliases["Numba-GA"] == "GA"
    assert aliases["Core-2OPT-TSP"] == "Core-TwoOpt-TSP"
    assert aliases["Numba-Or-opt"] == "OR-OPT"
    assert aliases["Numba-Hybrid"] == "HYBRID"
    assert aliases["ortools_cvrp"] == "OR-Tools"
    assert normalize_algorithm_name("Numba-3-opt-bounded") == "3-OPT"
    assert normalize_algorithm_name("pso-split") == "PSO-Split"
