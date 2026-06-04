from __future__ import annotations

import inspect

from optimizer_api.strategies.ga_strategy import GeneticAlgorithmStrategy
from optimizer_api.strategies.gwo_strategy import GreyWolfOptimizerStrategy
from optimizer_api.strategies.pso_strategy import PSOStrategy


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
