"""
Acceptance Criteria Library (DNA #7)

Provides metaheuristic acceptance decision logic for local search
and ALNS frameworks.  Three concrete strategies are included:

  1. **SimulatedAnnealing (SA)**  — exponential cooling schedule
  2. **LateAcceptanceHC (LAHC)**  — acceptance vs. historical deque
  3. **RecordToRecordTravel (RTR)** — threshold-based acceptance

All implement a common :class:`AcceptanceCriterion` abstract interface
so callers can swap strategies transparently.

Usage::

    criterion = SimulatedAnnealing()
    result = criterion.decide(current_cost=100, new_cost=105,
                              best_cost=95, iteration=50, rng=rng)
    if result.accepted:
        ...
"""

import logging
import math
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AcceptResult:
    """Result of an acceptance decision.

    Attributes:
        accepted:    Whether the new solution was accepted.
        improved:    Whether the new solution is better than the current.
        is_new_best: Whether the new solution is the overall best found.
    """

    accepted: bool
    improved: bool
    is_new_best: bool


class AcceptanceCriterion(ABC):
    """Abstract base for acceptance criteria.

    Subclasses must implement :meth:`decide`.
    """

    @abstractmethod
    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: "random.Random",  # noqa: F821
    ) -> AcceptResult:
        """Decide whether to accept a new solution.

        Args:
            current_cost: Cost of the incumbent solution.
            new_cost:     Cost of the candidate solution.
            best_cost:    Best cost observed so far.
            iteration:    Current iteration number.
            rng:          Seeded random generator.

        Returns:
            :class:`AcceptResult` with acceptance details.
        """
        ...


class SimulatedAnnealing(AcceptanceCriterion):
    """Simulated Annealing with geometric cooling.

    Acceptance probability:

        P(accept) = exp( -ΔE / T )

    where ``ΔE = new_cost - current_cost`` and ``T`` decays
    geometrically from ``T₀`` to ``T_end`` at rate ``cooling_rate``.

    Args:
        start_temp:    Initial temperature (T₀).
        end_temp:      Minimum temperature (T_end).
        cooling_rate:  Multiplicative cooling factor per iteration.
        max_iteration: Normalisation denominator for temperature decay.
    """

    def __init__(
        self,
        start_temp: float = 0.4,
        end_temp: float = 0.0001,
        cooling_rate: float = 0.9995,
        max_iteration: int = 100_000,
    ) -> None:
        self._start_temp = start_temp
        self._end_temp = end_temp
        self._cooling_rate = cooling_rate
        self._max_iteration = max_iteration

    def _temperature(self, iteration: int) -> float:
        """Compute temperature at a given iteration via geometric cooling.

        ``T(iter) = max(T_end, T₀ · cooling_rate^iter)``

        Args:
            iteration: Current iteration.

        Returns:
            Temperature value.
        """
        t = self._start_temp * (self._cooling_rate ** iteration)
        return max(t, self._end_temp)

    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: "random.Random",  # noqa: F821
    ) -> AcceptResult:
        """SA acceptance decision.

        Improving moves are always accepted.  Worsening moves are
        accepted with probability ``exp(-ΔE/T)``.
        """
        delta = new_cost - current_cost
        improved = delta < -1e-10
        is_new_best = new_cost < best_cost - 1e-10

        if improved:
            return AcceptResult(accepted=True, improved=True, is_new_best=is_new_best)

        # Worsening move — probabilistic acceptance
        t = self._temperature(iteration)
        if delta < 0:
            delta = 0.0  # Guard against floating point noise

        try:
            prob = math.exp(-delta / t)
        except (OverflowError, ZeroDivisionError):
            prob = 0.0

        accepted = rng.random() < prob
        return AcceptResult(accepted=accepted, improved=False, is_new_best=False)


class LateAcceptanceHC(AcceptanceCriterion):
    """Late Acceptance Hill Climbing (LAHC).

    Maintains a circular buffer (deque) of the last *L* solution costs.
    A worsening candidate is accepted if it is no worse than the worst
    cost in the buffer.

    During a warmup period (first ``warmup`` iterations) the history
    is not yet full; all improving moves are accepted but worsening
    moves are rejected.

    Args:
        history_length: Size of the LAHC memory (L).
        warmup:         Number of initial iterations before LAHC kicks in.
    """

    def __init__(
        self,
        history_length: int = 500,
        warmup: int = 50,
    ) -> None:
        self._L = history_length
        self._warmup = warmup
        self._history: deque = deque(maxlen=history_length)

    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: "random.Random",  # noqa: F821
    ) -> AcceptResult:
        """LAHC acceptance decision.

        Improving moves are always accepted and recorded.  Worsening
        moves are accepted if ``new_cost <= worst(history)``.
        """
        delta = new_cost - current_cost
        improved = delta < -1e-10
        is_new_best = new_cost < best_cost - 1e-10

        # Always accept improving moves
        if improved:
            self._history.append(new_cost)
            return AcceptResult(accepted=True, improved=True, is_new_best=is_new_best)

        # Warmup: reject worsening moves
        if iteration < self._warmup or len(self._history) < self._L:
            self._history.append(current_cost)
            return AcceptResult(accepted=False, improved=False, is_new_best=False)

        # LAHC: accept if no worse than the worst in history
        worst_in_history = max(self._history)
        if new_cost <= worst_in_history + 1e-10:
            self._history.append(new_cost)
            return AcceptResult(accepted=True, improved=False, is_new_best=False)

        self._history.append(current_cost)
        return AcceptResult(accepted=False, improved=False, is_new_best=False)

    def reset(self) -> None:
        """Clear the history buffer (e.g., for a new run)."""
        self._history.clear()


class RecordToRecordTravel(AcceptanceCriterion):
    """Record-to-Record Travel (RTR).

    Maintains a dynamic threshold ``θ = best + deviation``.  A candidate
    is accepted if ``new_cost <= θ``.  The deviation decays
    exponentially from *initial_deviation* toward *min_deviation*.

    ``deviation(iter) = max(min_dev, initial_dev · decay^iter)``

    Args:
        initial_deviation: Starting threshold deviation.
        min_deviation:     Minimum threshold deviation.
        decay_rate:        Exponential decay factor per iteration.
    """

    def __init__(
        self,
        initial_deviation: float = 0.4,
        min_deviation: float = 0.001,
        decay_rate: float = 0.9999,
    ) -> None:
        self._initial_dev = initial_deviation
        self._min_dev = min_deviation
        self._decay_rate = decay_rate

    def _deviation(self, iteration: int) -> float:
        """Compute current deviation value.

        Args:
            iteration: Current iteration.

        Returns:
            Deviation (float).
        """
        d = self._initial_dev * (self._decay_rate ** iteration)
        return max(d, self._min_dev)

    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: "random.Random",  # noqa: F821
    ) -> AcceptResult:
        """RTR acceptance decision.

        A candidate is accepted if ``new_cost <= best + deviation(iter)``.
        """
        delta = new_cost - current_cost
        improved = delta < -1e-10
        is_new_best = new_cost < best_cost - 1e-10

        threshold = best_cost + self._deviation(iteration)
        accepted = new_cost <= threshold + 1e-10

        return AcceptResult(accepted=accepted, improved=improved, is_new_best=is_new_best)
