from __future__ import annotations

import inspect

from optimizer_api.strategies.ga_strategy import GeneticAlgorithmStrategy
from optimizer_api.strategies.ga_split_strategy import GAEnhancedSplitStrategy, GASplitStrategy
from optimizer_api.strategies.gwo_strategy import GreyWolfOptimizerStrategy
from optimizer_api.strategies.hho_strategy import HarrisHawksOptimizerStrategy
from optimizer_api.strategies.gwo_split_strategy import GWOSplitStrategy
from optimizer_api.strategies.hho_split_strategy import HHOSplitStrategy
from optimizer_api.strategies.hybrid_base_strategy import HybridSplitBaseStrategy
from optimizer_api.strategies.pso_strategy import PSOStrategy
from optimizer_api.strategies.pso_split_strategy import PSOSplitStrategy
from optimizer_api.strategies.two_opt_strategy import TwoOptStrategy


def test_ga_strategy_does_not_own_legacy_ga_operator_helpers():
    wrapper_methods = {
        name
        for name, member in inspect.getmembers(GeneticAlgorithmStrategy, predicate=inspect.isfunction)
        if member.__qualname__.startswith("GeneticAlgorithmStrategy.")
    }

    assert not {
        "_initialize_population",
        "_evaluate_population",
        "_tournament_selection",
        "_order_crossover",
        "_mutate",
        "_evolve",
    } & wrapper_methods


def test_pso_strategy_does_not_own_legacy_pso_operator_helpers():
    wrapper_methods = {
        name
        for name, member in inspect.getmembers(PSOStrategy, predicate=inspect.isfunction)
        if member.__qualname__.startswith("PSOStrategy.")
    }

    assert not {
        "_shuffle",
        "_generate_random_velocity",
        "_initialize_swarm",
        "_diff_swaps",
        "_apply_swaps",
        "_combine_velocities",
        "_get_difference_swaps",
        "_apply_velocity",
        "_update_velocity",
    } & wrapper_methods


def test_gwo_strategy_does_not_own_legacy_gwo_operator_helpers():
    wrapper_methods = {
        name
        for name, member in inspect.getmembers(GreyWolfOptimizerStrategy, predicate=inspect.isfunction)
        if member.__qualname__.startswith("GreyWolfOptimizerStrategy.")
    }

    assert not {
        "_shuffle",
        "_initialize_pack",
        "_get_difference_vector",
        "_apply_swaps",
        "_update_position",
    } & wrapper_methods


def test_hho_strategy_does_not_own_legacy_hho_operator_helpers():
    wrapper_methods = {
        name
        for name, member in inspect.getmembers(HarrisHawksOptimizerStrategy, predicate=inspect.isfunction)
        if member.__qualname__.startswith("HarrisHawksOptimizerStrategy.")
    }

    assert not {
        "_shuffle",
        "_initialize_population",
        "_levy_flight",
        "_get_difference_swaps",
        "_apply_swaps",
        "_soft_besiege",
        "_hard_besiege",
        "_soft_besiege_with_dives",
        "_hard_besiege_with_dives",
        "_calculate_fitness",
        "_evaluate_hawk",
    } & wrapper_methods


def test_two_opt_strategy_does_not_own_unused_shuffle_helper():
    wrapper_methods = {
        name
        for name, member in inspect.getmembers(TwoOptStrategy, predicate=inspect.isfunction)
        if member.__qualname__.startswith("TwoOptStrategy.")
    }

    assert "_shuffle" not in wrapper_methods


def _wrapper_methods(cls):
    return {
        name
        for name, member in inspect.getmembers(cls, predicate=inspect.isfunction)
        if member.__qualname__.startswith(f"{cls.__name__}.")
    }


def test_ga_split_strategies_do_not_own_legacy_operator_helpers():
    disallowed = {
        "_initialize_population",
        "_evaluate_individual",
        "_evaluate_population",
        "_tournament_selection",
        "_order_crossover",
        "_mutate",
        "_educate",
        "_diversify",
        "_evolve",
    }
    assert not disallowed & _wrapper_methods(GASplitStrategy)
    assert not {"_crossover_pmx", "_crossover_cx2"} & _wrapper_methods(GAEnhancedSplitStrategy)


def test_pso_split_strategy_does_not_own_legacy_operator_helpers():
    assert not {
        "_shuffle",
        "_initialize_swarm",
        "_calculate_giant_tour_cost",
        "_get_difference_swaps",
        "_apply_velocity",
        "_update_velocity",
        "_evaluate_particle",
        "_local_search_improve",
    } & _wrapper_methods(PSOSplitStrategy)


def test_gwo_split_strategy_does_not_own_legacy_operator_helpers():
    assert not {
        "_shuffle",
        "_initialize_pack",
        "_get_difference_swaps",
        "_apply_swaps",
        "_update_position",
        "_calculate_giant_tour_cost",
        "_evaluate_wolf",
        "_local_search_improve",
    } & _wrapper_methods(GWOSplitStrategy)


def test_hho_split_strategy_does_not_own_legacy_operator_helpers():
    assert not {
        "_shuffle",
        "_initialize_population",
        "_levy_flight",
        "_get_difference_swaps",
        "_apply_swaps",
        "_soft_besiege",
        "_hard_besiege",
        "_soft_besiege_with_dives",
        "_hard_besiege_with_dives",
        "_calculate_giant_tour_cost",
        "_evaluate_hawk",
        "_local_search_improve",
    } & _wrapper_methods(HHOSplitStrategy)


def test_hybrid_split_base_does_not_own_unused_nearest_neighbor_helper():
    assert "_nearest_neighbor_tour" not in _wrapper_methods(HybridSplitBaseStrategy)
