"""Demand-vector normalization helpers for routing solver adapters."""

from __future__ import annotations

from typing import List, Sequence


def demand_vectors_from_legacy(
    disability_types: Sequence[str] | None,
    *,
    sw_capacity: int | None,
    so_capacity: int | None,
) -> tuple[List[List[int]], List[int]]:
    """Convert legacy UniRide SW/SO demand inputs to vector demands."""
    types = list(disability_types or [])
    vectors = [
        [1, 0] if disability_type == "Sw" else [0, 1]
        for disability_type in types
    ]
    return vectors, [int(sw_capacity or 0), int(so_capacity or 0)]


def normalize_demand_vectors(
    *,
    customer_count: int,
    demand_vectors: Sequence[Sequence[int] | int] | None = None,
    capacities: Sequence[int] | None = None,
    disability_types: Sequence[str] | None = None,
    sw_capacity: int | None = None,
    so_capacity: int | None = None,
) -> tuple[List[List[int]], List[int]]:
    """Return customer-only demand vectors and matching vehicle capacities.

    ``demand_vectors`` may include the depot row at index 0, as
    ``ConstraintProfile.demands`` does. Solver adapters consume customer-only
    demand vectors, so the depot row is stripped when present.
    """
    if demand_vectors is None:
        vectors, caps = demand_vectors_from_legacy(
            disability_types,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
        )
    else:
        raw_vectors = list(demand_vectors)
        if len(raw_vectors) == customer_count + 1:
            raw_vectors = raw_vectors[1:]
        vectors = [
            [int(value) for value in demand]
            if isinstance(demand, Sequence) and not isinstance(demand, (str, bytes))
            else [int(demand)]
            for demand in raw_vectors
        ]
        caps = [int(value) for value in capacities or []]

    if len(vectors) != customer_count:
        raise ValueError(
            f"Expected {customer_count} customer demand rows, got {len(vectors)}"
        )
    if not vectors:
        return [], caps or [0]

    dimension_count = max(len(row) for row in vectors)
    normalized = [row + [0] * (dimension_count - len(row)) for row in vectors]
    if not caps:
        caps = [sum(row[dim] for row in normalized) for dim in range(dimension_count)]
    if len(caps) < dimension_count:
        caps = caps + [0] * (dimension_count - len(caps))
    return normalized, caps[:dimension_count]


def load_for_route(route: Sequence[int], demand_vectors: Sequence[Sequence[int]]) -> List[int]:
    """Compute load for customer indices returned by adapter route plans."""
    if not demand_vectors:
        return []
    dimension_count = max(len(row) for row in demand_vectors)
    load = [0] * dimension_count
    for customer_idx in route:
        demand = demand_vectors[customer_idx]
        for dim, value in enumerate(demand):
            load[dim] += int(value)
    return load


__all__ = ["demand_vectors_from_legacy", "load_for_route", "normalize_demand_vectors"]
