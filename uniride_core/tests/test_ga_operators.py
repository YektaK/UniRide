import random

import pytest

from uniride_core.algorithms.ga_operators import (
    cycle_crossover_2,
    mutate_permutation,
    order_crossover,
    partially_mapped_crossover,
)


def test_order_crossover_preserves_permutation_contents():
    parent1 = ["a", "b", "c", "d", "e", "f"]
    parent2 = ["f", "e", "d", "c", "b", "a"]

    child1, child2 = order_crossover(parent1, parent2, random.Random(42))

    assert len(child1) == len(parent1)
    assert len(child2) == len(parent2)
    assert set(child1) == set(parent1)
    assert set(child2) == set(parent2)


def test_order_crossover_short_permutations_return_copies():
    parent1 = ["a"]
    parent2 = ["b"]

    child1, child2 = order_crossover(parent1, parent2, random.Random(1))

    assert child1 == parent1
    assert child2 == parent2
    assert child1 is not parent1
    assert child2 is not parent2


@pytest.mark.parametrize(
    "crossover",
    [partially_mapped_crossover, cycle_crossover_2],
)
def test_enhanced_crossovers_preserve_permutation_contents(crossover):
    parent1 = ["a", "b", "c", "d", "e", "f"]
    parent2 = ["f", "e", "d", "c", "b", "a"]

    child = crossover(parent1, parent2, random.Random(11))

    assert len(child) == len(parent1)
    assert set(child) == set(parent1)


@pytest.mark.parametrize(
    "crossover",
    [partially_mapped_crossover, cycle_crossover_2],
)
def test_enhanced_crossovers_short_permutations_return_copies(crossover):
    parent1 = ["a"]
    parent2 = ["b"]

    child = crossover(parent1, parent2, random.Random(1))

    assert child == parent1
    assert child is not parent1


@pytest.mark.parametrize("mutation_type", ["swap", "inversion", "scramble"])
def test_mutate_permutation_preserves_permutation_contents(mutation_type):
    chromosome = ["a", "b", "c", "d", "e", "f"]

    mutated = mutate_permutation(chromosome, random.Random(7), mutation_type=mutation_type)

    assert len(mutated) == len(chromosome)
    assert set(mutated) == set(chromosome)
    assert chromosome == ["a", "b", "c", "d", "e", "f"]


def test_mutate_permutation_short_permutation_returns_copy():
    chromosome = ["a"]

    mutated = mutate_permutation(chromosome, random.Random(1), mutation_type="swap")

    assert mutated == chromosome
    assert mutated is not chromosome


def test_mutate_permutation_rejects_unknown_mutation_type():
    with pytest.raises(ValueError, match="Unknown mutation_type"):
        mutate_permutation(["a", "b", "c"], random.Random(1), mutation_type="bad")


def test_order_crossover_two_elements():
    parent1 = ["a", "b"]
    parent2 = ["b", "a"]
    child1, child2 = order_crossover(parent1, parent2, random.Random(0))
    assert set(child1) == {"a", "b"}
    assert set(child2) == {"a", "b"}
    assert len(child1) == 2
    assert len(child2) == 2


def test_mutate_permutation_two_elements_swap():
    chromosome = ["a", "b"]
    mutated = mutate_permutation(chromosome, random.Random(0), mutation_type="swap")
    assert set(mutated) == {"a", "b"}
    assert len(mutated) == 2


def test_order_crossover_preserves_permutation_for_five_nodes():
    parent1 = ["a", "b", "c", "d", "e"]
    parent2 = ["e", "d", "c", "b", "a"]
    child1, child2 = order_crossover(parent1, parent2, random.Random(42))
    assert set(child1) == set(parent1)
    assert set(child2) == set(parent2)


def test_partially_mapped_crossover_two_elements():
    parent1 = ["a", "b"]
    parent2 = ["b", "a"]
    child = partially_mapped_crossover(parent1, parent2, random.Random(0))
    assert set(child) == {"a", "b"}


def test_cycle_crossover_2_two_elements():
    parent1 = ["a", "b"]
    parent2 = ["b", "a"]
    child = cycle_crossover_2(parent1, parent2, random.Random(0))
    assert set(child) == {"a", "b"}
