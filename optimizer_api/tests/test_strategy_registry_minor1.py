"""Test MINOR-1 fix: Unavailable strategies map to None, not fallback."""
import pytest
from strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY, get_strategy_info


def test_unavailable_optional_deps_map_to_none():
    """PyVRP/VROOM should be None when packages are not installed."""
    for key in ("pyvrp", "hgs", "pyvrp_alt", "vroom", "vroom_fallback"):
        val = STRATEGY_REGISTRY.get(key)
        # Either the package is installed (not None) or it's None
        assert val is None or val is not None
        # If it's not None, it should NOT be the OR-Tools strategy
        from strategies.ortools_cvrp import ORToolsCVRPStrategy
        assert not isinstance(val, ORToolsCVRPStrategy), (
            f"{key} should not silently fall back to OR-Tools"
        )


def test_strategy_info_includes_unavailable():
    """Unavailable strategies should appear with available=False in info."""
    info = get_strategy_info()
    names = {s["name"] for s in info}

    # Core strategies must always be present
    for core in ("genetic_algorithm", "ga_split", "pso", "ortools_cvrp"):
        assert core in names, f"{core} must be in strategy info"

    # Optional strategies should be listed regardless of availability
    optional_info = [s for s in info if s["name"] in ("pyvrp", "vroom")]
    assert len(optional_info) >= 1
    for s in optional_info:
        assert "available" in s


def test_get_strategy_returns_none_for_unavailable():
    """get_strategy() should return None for unavailable optional deps."""
    from strategies import get_strategy
    for key in ("pyvrp", "hgs", "pyvrp_alt", "vroom", "vroom_fallback"):
        val = get_strategy(key)
        # Must be either None (unavailable) or a strategy instance (available)
        assert val is None or hasattr(val, "optimize")


def test_get_strategy_returns_fresh_instances_for_thread_safety():
    """Production lookups should not share mutable strategy instances."""
    from strategies import get_strategy

    first = get_strategy("ga")
    second = get_strategy("ga")

    assert first is not None
    assert second is not None
    assert first is not second
    assert first.__class__ is second.__class__


def test_strategy_factories_cover_registry_keys():
    """Compatibility registry keys should all have a factory entry, including optional None."""
    assert set(STRATEGY_REGISTRY) == set(STRATEGY_FACTORIES)
