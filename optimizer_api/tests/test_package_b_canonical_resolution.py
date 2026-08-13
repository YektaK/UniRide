"""Package B canonical strategy resolution and fresh-factory contract."""

from __future__ import annotations

import pytest

from optimizer_api.strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY
from optimizer_api.strategies.canonical import (
    StrategyUnavailableError,
    UnknownStrategyError,
    resolve_strategy,
    resolve_unique_strategies,
)


OPTIONAL_CANONICAL = {
    "pyvrp": "pyvrp",
    "hgs": "pyvrp",
    "pyvrp_alt": "pyvrp_alt",
    "vroom": "vroom",
    "vroom_fallback": "vroom_fallback",
}


def test_every_registry_key_resolves_to_existing_canonical_identity() -> None:
    assert set(STRATEGY_REGISTRY) == set(STRATEGY_FACTORIES)

    for key, singleton in STRATEGY_REGISTRY.items():
        resolution = resolve_strategy(key, require_available=False)

        assert resolution.requested == key.lower()
        assert resolution.requested_aliases == (key.lower(),)
        if singleton is None:
            assert resolution.canonical == OPTIONAL_CANONICAL[key]
            assert resolution.available is False
        else:
            assert resolution.canonical == singleton.name
            first = resolution.create()
            second = resolution.create()
            assert first.name == second.name == singleton.name
            assert first is not second


def test_normalizes_requested_identity_without_changing_canonical_name() -> None:
    resolution = resolve_strategy("  GA  ")

    assert resolution.requested == "ga"
    assert resolution.canonical == "genetic_algorithm"
    assert resolution.requested_aliases == ("ga",)


def test_aliases_deduplicate_in_first_requested_order() -> None:
    resolved = resolve_unique_strategies(
        ["ga", "genetic_algorithm", "nearest_neighbor", "greedy"]
    )

    assert [item.canonical for item in resolved] == ["genetic_algorithm", "greedy"]
    assert resolved[0].requested == "ga"
    assert resolved[0].requested_aliases == ("ga", "genetic_algorithm")
    assert resolved[1].requested == "nearest_neighbor"
    assert resolved[1].requested_aliases == ("nearest_neighbor", "greedy")


def test_unknown_and_unavailable_strategies_are_distinct(monkeypatch) -> None:
    with pytest.raises(UnknownStrategyError, match="Unknown algorithm 'missing'"):
        resolve_strategy("missing")

    monkeypatch.setitem(STRATEGY_FACTORIES, "pyvrp", None)
    with pytest.raises(StrategyUnavailableError, match="Algorithm 'pyvrp' is unavailable"):
        resolve_strategy("pyvrp")


def test_known_unavailable_strategy_can_be_inspected_but_not_created(monkeypatch) -> None:
    monkeypatch.setitem(STRATEGY_REGISTRY, "hgs", None)
    monkeypatch.setitem(STRATEGY_FACTORIES, "hgs", None)

    resolution = resolve_strategy(" HGS ", require_available=False)

    assert resolution.requested == "hgs"
    assert resolution.canonical == "pyvrp"
    assert resolution.requested_aliases == ("hgs",)
    assert resolution.available is False
    with pytest.raises(StrategyUnavailableError, match="Algorithm 'hgs' is unavailable"):
        resolution.create()


def test_unique_resolution_rejects_an_unavailable_alias_before_execution(monkeypatch) -> None:
    monkeypatch.setitem(STRATEGY_REGISTRY, "vroom", None)
    monkeypatch.setitem(STRATEGY_FACTORIES, "vroom", None)

    with pytest.raises(StrategyUnavailableError, match="Algorithm 'vroom' is unavailable"):
        resolve_unique_strategies(["greedy", "vroom"])
