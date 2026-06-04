from __future__ import annotations

import inspect

from optimizer_api.strategies.ga_strategy import GeneticAlgorithmStrategy


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
