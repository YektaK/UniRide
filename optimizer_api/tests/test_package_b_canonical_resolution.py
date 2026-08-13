"""Package B canonical strategy resolution and fresh-factory contract."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from optimizer_api.strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY
from optimizer_api.strategies import canonical as canonical_module
from optimizer_api.strategies.canonical import (
    StrategyRegistryContractError,
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

@pytest.mark.parametrize("drift_side", ["registry", "factory"])
def test_resolver_rejects_registry_factory_key_drift(monkeypatch, drift_side) -> None:
    target = STRATEGY_REGISTRY if drift_side == "registry" else STRATEGY_FACTORIES
    source = STRATEGY_REGISTRY if drift_side == "registry" else STRATEGY_FACTORIES
    monkeypatch.setitem(target, "drift-only", source["ga"])

    with pytest.raises(StrategyRegistryContractError, match="registry and factory keys differ"):
        resolve_strategy("ga")



def test_factory_output_must_match_resolved_canonical_name(monkeypatch) -> None:
    greedy_factory = STRATEGY_FACTORIES["greedy"]
    assert greedy_factory is not None
    monkeypatch.setitem(STRATEGY_FACTORIES, "ga", greedy_factory)
    resolution = resolve_strategy("ga")

    with pytest.raises(StrategyRegistryContractError, match="expected 'genetic_algorithm'"):
        resolution.create()


def test_direct_module_resolver_binds_its_callers_registry(tmp_path) -> None:
    worktree_root = Path(__file__).resolve().parents[2]
    optimizer_root = worktree_root / "optimizer_api"
    shadow_root = tmp_path / "alternate-checkout"
    shadow_strategies = shadow_root / "optimizer_api" / "strategies"
    shadow_strategies.mkdir(parents=True)
    (shadow_root / "optimizer_api" / "__init__.py").write_text("", encoding="utf-8")
    (shadow_strategies / "__init__.py").write_text(
        "STRATEGY_REGISTRY = {}\nSTRATEGY_FACTORIES = {}\n",
        encoding="utf-8",
    )
    (shadow_strategies / "base_strategy.py").write_text(
        "class BaseRoutingStrategy: pass\n",
        encoding="utf-8",
    )

    script = "\n".join(
        (
            "import sys",
            f"sys.path.insert(0, {str(worktree_root)!r})",
            f"sys.path.insert(0, {str(shadow_root)!r})",
            f"sys.path.insert(0, {str(optimizer_root)!r})",
            "import strategies",
            "import strategies.canonical as canonical",
            "assert canonical.STRATEGY_REGISTRY is strategies.STRATEGY_REGISTRY",
            "assert canonical.STRATEGY_FACTORIES is strategies.STRATEGY_FACTORIES",
            "assert 'optimizer_api.strategies' not in sys.modules",
        )
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert canonical_module.STRATEGY_REGISTRY is STRATEGY_REGISTRY
    assert canonical_module.STRATEGY_FACTORIES is STRATEGY_FACTORIES
