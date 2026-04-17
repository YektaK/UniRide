"""
Adaptive Penalty Manager (DNA #9)

Implements an Iterated Penalty Method (IPM) with three phases for
controlled exploration of infeasible regions in CVRPTW:

  1. **Relax**    — low penalties, wide exploration
  2. **Moderate** — smooth penalty increase (×1.001 per iteration)
  3. **Strict**   — aggressive penalty increase (×1.5 per iteration)

The manager computes a *penalised cost* that blends the base routing
cost with time-window and capacity violation penalties.  Phase
transitions are governed by iteration thresholds.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PenaltyState:
    """Immutable snapshot of the penalty manager's internal state.

    Attributes:
        iteration:    Current iteration count.
        alpha_tw:     Current time-window penalty weight.
        alpha_cap:    Current capacity penalty weight.
        phase:        Active phase name (``"relax"``, ``"moderate"``, ``"strict"``).
        feasible_best: Best cost among feasible solutions found so far.
        current_best: Best penalised cost overall (may be infeasible).
    """

    iteration: int = 0
    alpha_tw: float = 10.0
    alpha_cap: float = 5.0
    phase: str = "relax"
    feasible_best: float = float("inf")
    current_best: float = float("inf")


class PenaltyManager:
    """Adaptive penalty controller for CVRPTW infeasible-region search.

    Usage::

        pm = PenaltyManager()
        penalised = pm.compute_penalized_cost(base_cost, tw_viol, cap_viol)
        pm.update(iteration, current_cost, is_feasible)
        state = pm.get_state()

    The manager is stateful; keep a single instance per optimisation run.
    """

    def __init__(
        self,
        initial_alpha_tw: float = 10.0,
        initial_alpha_cap: float = 5.0,
        max_alpha_tw: float = 10_000.0,
        max_alpha_cap: float = 5_000.0,
        relax_end: int = 500,
        moderate_end: int = 5_000,
    ) -> None:
        """Initialise the penalty manager.

        Args:
            initial_alpha_tw: Starting TW penalty weight.
            initial_alpha_cap: Starting capacity penalty weight.
            max_alpha_tw: Upper bound for TW penalty.
            max_alpha_cap: Upper bound for capacity penalty.
            relax_end:      Iteration at which relax phase ends.
            moderate_end:   Iteration at which moderate phase ends
                            (strict phase starts after this).
        """
        self._alpha_tw = initial_alpha_tw
        self._alpha_cap = initial_alpha_cap
        self._max_alpha_tw = max_alpha_tw
        self._max_alpha_cap = max_alpha_cap
        self._relax_end = relax_end
        self._moderate_end = moderate_end

        self._iteration = 0
        self._phase = "relax"
        self._feasible_best = float("inf")
        self._current_best = float("inf")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def compute_penalized_cost(
        self,
        base_cost: float,
        tw_violation: float,
        cap_violation: float,
    ) -> float:
        """Compute the penalised objective value.

        ``penalised = base_cost + α_tw · tw_violation + α_cap · cap_violation``

        Args:
            base_cost:    Pure routing cost (distance / time).
            tw_violation: Total time-window violation magnitude.
            cap_violation: Total capacity violation magnitude.

        Returns:
            Penalised cost (float).
        """
        return (
            base_cost
            + self._alpha_tw * tw_violation
            + self._alpha_cap * cap_violation
        )

    def update(
        self,
        iteration: int,
        current_cost: float,
        is_feasible: bool,
    ) -> None:
        """Update internal state based on the latest iteration result.

        Manages phase transitions and penalty weight increases.

        Args:
            iteration:    Current iteration number.
            current_cost: Penalised cost of the current solution.
            is_feasible:  Whether the current solution is feasible.
        """
        self._iteration = iteration

        # Track bests
        if is_feasible and current_cost < self._feasible_best:
            self._feasible_best = current_cost
            logger.debug(
                "New feasible best: %.4f at iteration %d",
                current_cost,
                iteration,
            )

        if current_cost < self._current_best:
            self._current_best = current_cost

        # Phase transition logic
        old_phase = self._phase
        if iteration < self._relax_end:
            self._phase = "relax"
        elif iteration < self._moderate_end:
            self._phase = "moderate"
        else:
            self._phase = "strict"

        if self._phase != old_phase:
            logger.info(
                "Penalty phase transition: %s → %s at iteration %d "
                "(α_tw=%.2f, α_cap=%.2f)",
                old_phase,
                self._phase,
                iteration,
                self._alpha_tw,
                self._alpha_cap,
            )

        # Penalty weight updates
        if self._phase == "relax":
            # No penalty increase during relax — allow exploration
            pass
        elif self._phase == "moderate":
            # Smooth increase (×1.001)
            self._alpha_tw = min(
                self._alpha_tw * 1.001, self._max_alpha_tw
            )
            self._alpha_cap = min(
                self._alpha_cap * 1.001, self._max_alpha_cap
            )
        elif self._phase == "strict":
            # Aggressive increase (×1.5)
            self._alpha_tw = min(
                self._alpha_tw * 1.5, self._max_alpha_tw
            )
            self._alpha_cap = min(
                self._alpha_cap * 1.5, self._max_alpha_cap
            )

    def get_state(self) -> PenaltyState:
        """Return an immutable snapshot of the current penalty state.

        Returns:
            :class:`PenaltyState` dataclass instance.
        """
        return PenaltyState(
            iteration=self._iteration,
            alpha_tw=self._alpha_tw,
            alpha_cap=self._alpha_cap,
            phase=self._phase,
            feasible_best=self._feasible_best,
            current_best=self._current_best,
        )

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #

    @property
    def alpha_tw(self) -> float:
        """Current time-window penalty weight."""
        return self._alpha_tw

    @property
    def alpha_cap(self) -> float:
        """Current capacity penalty weight."""
        return self._alpha_cap

    @property
    def phase(self) -> str:
        """Current phase name."""
        return self._phase

    @property
    def iteration(self) -> int:
        """Current iteration counter."""
        return self._iteration
