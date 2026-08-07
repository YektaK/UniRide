"""Shared deterministic seed contract for routing strategies."""

import random
from typing import Dict, Optional


DEFAULT_SEED = 42


def resolve_seed(config: Dict, default: int = DEFAULT_SEED) -> int:
    """Resolve a deterministic seed from a config dict, preserving 0."""
    value = config.get("seed")
    if isinstance(value, int):
        return value
    if value is None:
        return default
    return int(value)


def make_rng(config: Dict, default: int = DEFAULT_SEED) -> random.Random:
    return random.Random(resolve_seed(config, default))