"""Synthetic lifecycle entries for refusal tests that must not depend on the live catalog.

Refusal tests (candidate / planned) need an algorithm whose lifecycle is CANDIDATE or PLANNED.
Which live IDs hold those states changes with every promotion, so tests must not rely on it.
``force_lifecycle`` replaces one catalog entry for the duration of a test: the ID is still a
real, resolvable canonical ID, but its capability is a synthetic CANDIDATE or PLANNED entry
without claims.  Every module that holds a reference to the live catalog mapping is patched,
so the change is seen by ``get_algorithm_capability`` (preflight, manifest contracts, study
service) and by ``cli_engine.CAPABILITY_CATALOG``.
"""

from __future__ import annotations

import dataclasses
import sys

import pytest

from uniride_core.algorithms import capabilities
from uniride_core.algorithms.capabilities import (
    AlgorithmCapability,
    LifecycleStatus,
    build_capability_catalog,
)


def synthetic_capability(
    canonical_id: str, lifecycle: LifecycleStatus
) -> AlgorithmCapability:
    """Return a claim-free CANDIDATE/PLANNED entry derived from the live entry's identity."""
    if lifecycle not in (LifecycleStatus.CANDIDATE, LifecycleStatus.PLANNED):
        raise ValueError("synthetic entries are only for CANDIDATE or PLANNED refusals")
    live = capabilities.CAPABILITY_CATALOG[canonical_id]
    return dataclasses.replace(
        live,
        lifecycle=lifecycle,
        claims=(),
        planning_note=(
            "synthetic PLANNED entry for a refusal test"
            if lifecycle is LifecycleStatus.PLANNED
            else None
        ),
    )


def _holds_catalog(module: object, live_catalog: object) -> bool:
    try:
        return getattr(module, "CAPABILITY_CATALOG", None) is live_catalog
    except Exception:  # lazy or exotic modules in sys.modules
        return False


def force_lifecycle(
    monkeypatch: pytest.MonkeyPatch, canonical_id: str, lifecycle: LifecycleStatus
) -> None:
    """Make ``canonical_id`` a synthetic CANDIDATE/PLANNED entry for this test only."""
    live_catalog = capabilities.CAPABILITY_CATALOG
    replacement = synthetic_capability(canonical_id, lifecycle)
    patched = build_capability_catalog(
        replacement if cap.canonical_id == canonical_id else cap
        for cap in live_catalog.values()
    )
    for module in tuple(sys.modules.values()):
        if _holds_catalog(module, live_catalog):
            monkeypatch.setattr(module, "CAPABILITY_CATALOG", patched)
