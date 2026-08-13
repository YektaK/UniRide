"""Canonical production strategy resolution with request-scoped factories."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from . import STRATEGY_FACTORIES, STRATEGY_REGISTRY
from .base_strategy import BaseRoutingStrategy


_OPTIONAL_CANONICAL = {
    "pyvrp": "pyvrp",
    "hgs": "pyvrp",
    "pyvrp_alt": "pyvrp_alt",
    "vroom": "vroom",
    "vroom_fallback": "vroom_fallback",
}


class UnknownStrategyError(ValueError):
    """Raised when a submitted strategy key is not registered."""


class StrategyUnavailableError(ValueError):
    """Raised when a registered strategy cannot execute in this environment."""


class StrategyRegistryContractError(ValueError):
    """Raised when registry metadata and executable factories disagree."""


@dataclass(frozen=True)
class ResolvedStrategy:
    """Canonical strategy identity and its request-scoped factory."""

    requested: str
    canonical: str
    factory: Callable[[], BaseRoutingStrategy] | None
    requested_aliases: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.factory is not None

    def create(self) -> BaseRoutingStrategy:
        if self.factory is None:
            raise StrategyUnavailableError(
                f"Algorithm '{self.requested}' is unavailable"
            )
        strategy = self.factory()
        if strategy.name != self.canonical:
            raise StrategyRegistryContractError(
                f"Algorithm '{self.requested}' factory returned '{strategy.name}'; "
                f"expected '{self.canonical}'"
            )
        return strategy


def resolve_strategy(key: str, *, require_available: bool = True) -> ResolvedStrategy:
    """Resolve a submitted registry key to one canonical executable identity."""

    requested = key.strip().lower()
    if set(STRATEGY_REGISTRY) != set(STRATEGY_FACTORIES):
        raise StrategyRegistryContractError(
            "Strategy registry and factory keys differ"
        )

    if requested not in STRATEGY_FACTORIES:
        raise UnknownStrategyError(f"Unknown algorithm '{requested}'")
    singleton = STRATEGY_REGISTRY[requested]
    canonical = singleton.name if singleton is not None else _OPTIONAL_CANONICAL[requested]
    result = ResolvedStrategy(
        requested,
        canonical,
        STRATEGY_FACTORIES[requested],
        (requested,),
    )
    if require_available and not result.available:
        raise StrategyUnavailableError(f"Algorithm '{requested}' is unavailable")
    return result


def resolve_unique_strategies(
    keys: list[str] | tuple[str, ...],
) -> list[ResolvedStrategy]:
    """Resolve and deduplicate aliases while preserving first-requested order."""

    unique: dict[str, ResolvedStrategy] = {}
    for key in keys:
        item = resolve_strategy(key)
        previous = unique.get(item.canonical)
        if previous is None:
            unique[item.canonical] = item
        else:
            unique[item.canonical] = replace(
                previous,
                requested_aliases=previous.requested_aliases + (item.requested,),
            )
    return list(unique.values())
