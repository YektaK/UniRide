"""
Hybrid Split Base Strategy

Shared abstract base for all Route-First / Cluster-Second (Split-based)
strategies: GA-Split, PSO-Split, GWO-Split, HHO-Split.

Keeps shared request-mapping helpers while delegating critical logic to core:
  - _get_duration        (previously copy-pasted across all 4 strategies)
  - _build_distance_matrix

Inheriting strategies keep ONLY their algorithm-specific logic.
"""

import math
from typing import Any, List, Dict, Optional

from strategies.base_strategy import BaseRoutingStrategy
from uniride_core.adapters.string_matrix_builder import build_string_distance_matrix


class HybridSplitBaseStrategy(BaseRoutingStrategy):
    """
    Abstract base class for split-based (Route-First) optimization strategies.

    Subclasses must implement: name, display_name, description, optimize().
    They inherit the three shared helpers below for free.
    """

    # ── Shared helpers ────────────────────────────────────────────────────────

    # _get_duration is inherited from BaseRoutingStrategy

    NO_FEASIBLE_SPLIT_MESSAGE = (
        "no_feasible_split: the split decoder found no feasible partition of "
        "the giant tour; the routes returned are the one-route-per-student "
        "fallback and violate the capacity, tour-duration or time-window limits"
    )

    @classmethod
    def _split_failure_reason(cls, final_result: Dict[str, Any]) -> Optional[str]:
        """Rule R3 (MT1-07): reason text when the decoder fell back, else None.

        ``string_split_decoder`` signals the fallback with an ``error`` entry
        and ``total_cost = inf`` (one route per student, no feasible split).
        The strategy must then answer ``success=False`` instead of presenting
        the infeasible singleton routes as a plan.
        """
        total_cost = final_result.get("total_cost")
        if final_result.get("error") or (
            total_cost is not None and not math.isfinite(total_cost)
        ):
            return cls.NO_FEASIBLE_SPLIT_MESSAGE
        return None

    def _build_distance_matrix(
        self,
        location_ids: List[str],
        time_matrix: Dict,
        coordinates: Dict,
    ) -> Dict[str, Dict[str, float]]:
        """Build a complete O(n²) distance matrix for all locations."""
        return build_string_distance_matrix(
            location_ids,
            lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
        )
