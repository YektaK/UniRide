"""
Diversity Controller (DNA #8)

Manages population diversity for metaheuristic frameworks that
maintain a pool of solutions.  Provides:

  * **Edge-based entropy**   — structural diversity of tours
  * **Average Hamming distance** — edit-based diversity
  * **Diversity injection**   — when diversity drops below threshold

The controller maintains a history buffer so callers can monitor
diversity trends over the course of an optimisation run.
"""

import logging
import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DiversityState:
    """Snapshot of diversity metrics.

    Attributes:
        entropy:          Edge-based entropy of the population.
        avg_distance:     Average pairwise Hamming distance.
        injection_count:  Total number of diversity injections performed.
        population_size:  Number of solutions in the population.
    """

    entropy: float = 0.0
    avg_distance: float = 0.0
    injection_count: int = 0
    population_size: int = 0


class DiversityController:
    """Tracks and manages population diversity.

    Usage::

        dc = DiversityController()
        should_inject = dc.should_inject_diversity(population, threshold=0.3)
        if should_inject:
            population = dc.inject_diverse_solutions(population, count=2,
                                                      generator_func=gen, rng=rng)
        state = dc.get_state()
    """

    def __init__(self, history_size: int = 100) -> None:
        """Initialise the diversity controller.

        Args:
            history_size: Number of past diversity snapshots to retain
                          for trend analysis.
        """
        self._injection_count = 0
        self._history: Deque[DiversityState] = deque(maxlen=history_size)

    # ------------------------------------------------------------------ #
    # Core metrics
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_population_entropy(population: List[List[str]]) -> float:
        """Compute edge-based Shannon entropy of a population.

        For each tour, every consecutive pair ``(tour[i], tour[i+1])``
        forms a directed *edge*.  The entropy measures how uniformly
        these edges are distributed across the population.

        ``H = - Σ  p(e) · log2(p(e))``

        where ``p(e)`` is the fraction of tours containing edge *e*.

        High entropy → high structural diversity (many different edges).
        Low entropy → many tours share the same edges (convergence).

        Args:
            population: List of tours (each a list of node ids).

        Returns:
            Shannon entropy in bits.  Returns 0.0 for empty or
            single-tour populations.
        """
        if len(population) < 2:
            return 0.0

        edge_counts: Counter = Counter()
        total_edges = 0

        for tour in population:
            if len(tour) < 2:
                continue
            for i in range(len(tour) - 1):
                edge = (tour[i], tour[i + 1])
                edge_counts[edge] += 1
                total_edges += 1

        if total_edges == 0:
            return 0.0

        entropy = 0.0
        for count in edge_counts.values():
            p = count / total_edges
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    @staticmethod
    def compute_average_distance(population: List[List[str]]) -> float:
        """Compute average pairwise Hamming distance.

        Hamming distance between two tours of equal length is the number
        of positions at which they differ.  For tours of unequal length,
        the shorter one is conceptually padded.

        Args:
            population: List of tours.

        Returns:
            Average Hamming distance across all pairs.  Returns 0.0
            for populations with fewer than 2 tours.
        """
        n = len(population)
        if n < 2:
            return 0.0

        total_dist = 0.0
        pairs = 0

        for i in range(n):
            for j in range(i + 1, n):
                d = DiversityController._hamming_distance(
                    population[i], population[j]
                )
                total_dist += d
                pairs += 1

        return total_dist / pairs if pairs > 0 else 0.0

    @staticmethod
    def _hamming_distance(a: List[str], b: List[str]) -> int:
        """Compute Hamming distance between two tours.

        Args:
            a: First tour.
            b: Second tour.

        Returns:
            Number of positions with different nodes.  Tours are
            compared position-wise up to ``min(len(a), len(b))``;
            extra elements in the longer tour each count as a difference.
        """
        min_len = min(len(a), len(b))
        diff = sum(1 for k in range(min_len) if a[k] != b[k])
        diff += abs(len(a) - len(b))
        return diff

    # ------------------------------------------------------------------ #
    # Diversity management
    # ------------------------------------------------------------------ #

    def should_inject_diversity(
        self,
        population: List[List[str]],
        threshold: float = 0.3,
    ) -> bool:
        """Decide whether the population needs diversity injection.

        Returns ``True`` if the normalised average distance is below
        *threshold*.  The distance is normalised by the maximum possible
        Hamming distance (tour length).

        Args:
            population: Current population.
            threshold:  Normalised distance threshold (0.0–1.0).

        Returns:
            Whether to inject diverse solutions.
        """
        if len(population) < 2:
            return False

        avg_dist = self.compute_average_distance(population)

        # Normalise by maximum possible Hamming distance
        max_len = max(len(t) for t in population)
        if max_len == 0:
            return False

        normalised = avg_dist / max_len
        return normalised < threshold

    def inject_diverse_solutions(
        self,
        population: List[List[str]],
        count: int,
        generator_func: Callable[..., List[str]],
        rng: "random.Random",  # noqa: F821
    ) -> List[List[str]]:
        """Replace the least-diverse solutions with new random ones.

        The *count* tours with the lowest contribution to entropy are
        removed and replaced by solutions from *generator_func*.

        Args:
            population:      Current population.
            count:           Number of solutions to inject.
            generator_func:  Callable ``rng -> tour`` that produces a
                             new tour.
            rng:             Seeded random generator.

        Returns:
            Modified population with diverse solutions injected.
        """
        if count <= 0 or not population:
            return population

        # Identify least-diverse members: those sharing the most edges
        # with the rest of the population
        edge_freq: Counter = Counter()
        for tour in population:
            for i in range(len(tour) - 1):
                edge_freq[(tour[i], tour[i + 1])] += 1

        # Score each tour by how "common" its edges are
        scores: List[Tuple[int, float]] = []
        for idx, tour in enumerate(population):
            common_edges = 0
            for i in range(len(tour) - 1):
                if edge_freq[(tour[i], tour[i + 1])] > 1:
                    common_edges += 1
            scores.append((idx, common_edges))

        # Remove tours with highest common-edge count
        scores.sort(key=lambda x: -x[1])
        to_remove = set(s[0] for s in scores[:count])

        new_pop = [t for idx, t in enumerate(population) if idx not in to_remove]

        # Generate new diverse solutions
        for _ in range(count):
            new_tour = generator_func(rng)
            new_pop.append(new_tour)

        self._injection_count += count
        logger.debug(
            "Injected %d diverse solutions (total injections: %d)",
            count,
            self._injection_count,
        )

        return new_pop

    # ------------------------------------------------------------------ #
    # State / history
    # ------------------------------------------------------------------ #

    def get_state(self, population: List[List[str]]) -> DiversityState:
        """Compute and return current diversity state.

        Also appends the state to the internal history buffer.

        Args:
            population: Current population.

        Returns:
            :class:`DiversityState` snapshot.
        """
        state = DiversityState(
            entropy=self.compute_population_entropy(population),
            avg_distance=self.compute_average_distance(population),
            injection_count=self._injection_count,
            population_size=len(population),
        )
        self._history.append(state)
        return state

    def get_history(self) -> List[DiversityState]:
        """Return the history buffer as a list (oldest first).

        Returns:
            List of past :class:`DiversityState` snapshots.
        """
        return list(self._history)

    @property
    def injection_count(self) -> int:
        """Total number of diversity injections performed."""
        return self._injection_count

    def reset(self) -> None:
        """Reset the controller state (history + injection counter)."""
        self._injection_count = 0
        self._history.clear()
