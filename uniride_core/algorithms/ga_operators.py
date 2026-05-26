"""Reusable genetic operators for permutation-based routing algorithms."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple, TypeVar, cast

T = TypeVar("T")


def order_crossover(parent1: List[T], parent2: List[T], rng: random.Random) -> Tuple[List[T], List[T]]:
    """Order Crossover (OX1) for permutation chromosomes."""
    n = len(parent1)
    if n < 2:
        return parent1.copy(), parent2.copy()

    start = rng.randint(0, n - 1)
    end = rng.randint(start, n - 1)
    child1: List[T | None] = [None] * n
    child2: List[T | None] = [None] * n

    for idx in range(start, end + 1):
        child1[idx] = parent1[idx]
        child2[idx] = parent2[idx]

    def fill_child(child: List[T | None], other_parent: List[T]) -> None:
        segment = {item for item in child if item is not None}
        remaining = [item for item in other_parent if item not in segment]
        pos = 0
        for idx in range(n):
            if child[idx] is None:
                child[idx] = remaining[pos]
                pos += 1

    fill_child(child1, parent2)
    fill_child(child2, parent1)
    return cast(List[T], child1), cast(List[T], child2)


def mutate_permutation(chromosome: List[T], rng: random.Random, mutation_type: str | None = None) -> List[T]:
    """Apply swap, inversion, or scramble mutation to a permutation."""
    mutated = chromosome.copy()
    if len(mutated) < 2:
        return mutated

    selected = mutation_type or rng.choice(["swap", "inversion", "scramble"])
    if selected == "swap":
        i, j = rng.sample(range(len(mutated)), 2)
        mutated[i], mutated[j] = mutated[j], mutated[i]
    elif selected == "inversion":
        i, j = rng.sample(range(len(mutated)), 2)
        start, end = min(i, j), max(i, j)
        mutated[start:end + 1] = reversed(mutated[start:end + 1])
    elif selected == "scramble":
        i, j = rng.sample(range(len(mutated)), 2)
        start, end = min(i, j), max(i, j)
        segment = mutated[start:end + 1]
        rng.shuffle(segment)
        mutated[start:end + 1] = segment
    else:
        raise ValueError(f"Unknown mutation_type: {selected}")
    return mutated


def partially_mapped_crossover(parent1: List[T], parent2: List[T], rng: random.Random) -> List[T]:
    """Partially Mapped Crossover (PMX) for permutation chromosomes."""
    n = len(parent1)
    if n < 2:
        return parent1.copy()

    start = rng.randint(0, n - 2)
    end = rng.randint(start + 1, n - 1)
    child: List[Optional[T]] = [None] * n

    for idx in range(start, end + 1):
        child[idx] = parent1[idx]

    segment_values = set(parent1[start:end + 1])
    pos_in_parent1: Dict[T, int] = {value: idx for idx, value in enumerate(parent1)}

    for idx in range(n):
        if child[idx] is not None:
            continue

        value = parent2[idx]
        while value in segment_values:
            value = parent2[pos_in_parent1[value]]
        child[idx] = value

    return cast(List[T], child)


def cycle_crossover_2(parent1: List[T], parent2: List[T], rng: random.Random) -> List[T]:
    """Cycle Crossover 2 (CX2) for permutation chromosomes."""
    n = len(parent1)
    if n < 2:
        return parent1.copy()

    child: List[Optional[T]] = [None] * n
    visited: set[T] = set()

    for start in range(n):
        if parent1[start] in visited:
            continue

        cycle_indices: List[int] = []
        cycle_values: List[T] = []
        idx = start

        while True:
            cycle_indices.append(idx)
            cycle_values.append(parent1[idx])
            visited.add(parent1[idx])

            next_value = parent2[idx]
            if next_value in visited:
                break

            try:
                idx = parent1.index(next_value)
            except ValueError:
                break

            if idx == start:
                break

        if len(cycle_values) > 1 and rng.random() < 0.5:
            cycle_values = cycle_values[::-1]

        for cycle_idx, value in zip(cycle_indices, cycle_values):
            child[cycle_idx] = value

    if None in child:
        for idx in range(n):
            if child[idx] is None:
                child[idx] = parent2[idx]

    return cast(List[T], child)


__all__ = [
    "cycle_crossover_2",
    "mutate_permutation",
    "order_crossover",
    "partially_mapped_crossover",
]
