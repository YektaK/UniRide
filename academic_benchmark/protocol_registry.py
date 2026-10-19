"""Academic-layer registry of the comparison protocols and their pooling groups (WP-E8 Task 6; DECISION_LOG A04, E12 OQ4).

Four protocol kinds exist. Rows of different kinds are never pooled, ranked, averaged or tested together:

=============================  ==========================  ===================  ========  ==========
kind                           version label               pooling group        rankable  statistics
=============================  ==========================  ===================  ========  ==========
``fixed_evaluation_budget``    ``uniride-fair-tsp-v2``     ``fixed_budget``     yes       yes
``algorithm_native_termination``  ``uniride-native-tsp-v1``  ``native``         yes       yes
``exact_reference_v1``         ``exact_reference_v1``      ``exact_reference_v1``  no     no
``union_day_v1``               ``union_day_v1``            ``union_day_v1``     no        no
=============================  ==========================  ===================  ========  ==========

"Rankable" and "statistics" hold within one pooling group of heuristic rows only. Exact and union-day rows are references and
selections, never competitors (design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 4; A04).

This registry lives in the academic layer on purpose (owner decision OQ4, 2026-10-18): ``uniride_core``'s
``ExecutionProtocol`` stays ``fixed_budget``/``native_termination`` and no preflight path accepts ``exact_reference_v1``.
The fixed-budget and native modules do not import this module (an AST test checks it); the existing
``protocol.assert_not_pooled`` is unchanged and stays the exact-side guard.

Rows are classified by the fields they carry today: ``protocol`` (exact and union rows), ``comparison_regime`` and
``protocol_version`` (fixed-budget and native pilot rows). A row whose fields point at two kinds, or at none, raises.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from academic_benchmark.exact_reference import protocol as exact_protocol
from academic_benchmark.exact_reference.rows import ExactReferenceRowV1

FIXED_BUDGET = "fixed_evaluation_budget"
NATIVE_TERMINATION = "algorithm_native_termination"
EXACT_REFERENCE = exact_protocol.PROTOCOL_ID  # "exact_reference_v1"
UNION_DAY = exact_protocol.UNION_DAY_PROTOCOL_ID  # "union_day_v1"

# labels of the existing fixed-budget and native modules, repeated here so that this registry imports neither of them;
# a test compares them with ``fairness.FairComparisonManifest`` and ``native_protocol`` constants
FAIR_V1_VERSION = "uniride-fair-tsp-v1"
FAIR_V2_VERSION = "uniride-fair-tsp-v2"
NATIVE_VERSION = "uniride-native-tsp-v1"


@dataclass(frozen=True)
class ProtocolKind:
    kind: str
    version_label: str
    pooling_group: str
    rankable: bool
    statistics: bool


PROTOCOL_KINDS = (
    ProtocolKind(FIXED_BUDGET, FAIR_V2_VERSION, "fixed_budget", True, True),
    ProtocolKind(NATIVE_TERMINATION, NATIVE_VERSION, "native", True, True),
    ProtocolKind(EXACT_REFERENCE, EXACT_REFERENCE, EXACT_REFERENCE, False, False),
    ProtocolKind(UNION_DAY, UNION_DAY, UNION_DAY, False, False),
)
_BY_KIND = {k.kind: k for k in PROTOCOL_KINDS}


def kind_of(name: str) -> ProtocolKind:
    try:
        return _BY_KIND[name]
    except KeyError:
        raise ValueError(f"unknown protocol kind {name!r}; known: {sorted(_BY_KIND)}") from None


def classify_row(row) -> ProtocolKind:
    """The protocol kind of one row: a typed exact row, or a mapping classified by ``protocol``, ``comparison_regime`` and
    ``protocol_version``. Contradictory or missing evidence raises ``ValueError``; other objects raise ``TypeError``."""
    if isinstance(row, ExactReferenceRowV1):
        return _BY_KIND[EXACT_REFERENCE]
    if not isinstance(row, Mapping):
        raise TypeError(f"cannot classify a {type(row).__name__}: rows are ExactReferenceRowV1 or mappings")
    found = set()
    protocol_id = row.get("protocol")
    if protocol_id in (EXACT_REFERENCE, UNION_DAY):
        found.add(protocol_id)
    regime = row.get("comparison_regime")
    if regime in (FIXED_BUDGET, NATIVE_TERMINATION):
        found.add(regime)
    version = row.get("protocol_version")
    if version in (FAIR_V1_VERSION, FAIR_V2_VERSION):
        found.add(FIXED_BUDGET)
    elif version == NATIVE_VERSION:
        found.add(NATIVE_TERMINATION)
    if len(found) > 1:
        raise ValueError(f"row fields point at several protocol kinds {sorted(found)}; refusing to guess")
    if not found:
        raise ValueError("row carries no protocol, comparison_regime or protocol_version that identifies its kind")
    return _BY_KIND[found.pop()]


def assert_single_pooling_group(rows: Iterable) -> str:
    """The pooling group shared by every row (``''`` for no rows); raises ``ValueError`` when rows of two groups meet."""
    groups = {}
    for row in rows:
        kind = classify_row(row)
        groups.setdefault(kind.pooling_group, kind.kind)
    if len(groups) > 1:
        raise ValueError(f"rows of different pooling groups must not be pooled: {sorted(groups)} (protocol kinds {sorted(groups.values())})")
    return next(iter(groups), "")


def assert_rankable(rows: Iterable) -> None:
    """Raise ``ValueError`` when any row belongs to a kind that is never ranked (exact and union-day rows), and when the rows
    span more than one pooling group (a ranking is only meaningful inside one)."""
    rows = list(rows)
    unrankable = sorted({classify_row(r).kind for r in rows if not classify_row(r).rankable})
    if unrankable:
        raise ValueError(f"{unrankable} rows are references or selections and are never ranked, averaged or tested")
    assert_single_pooling_group(rows)
