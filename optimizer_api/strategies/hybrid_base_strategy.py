"""
Hybrid Split Base Strategy

Shared abstract base for all Route-First / Cluster-Second (Split-based)
strategies: GA-Split, PSO-Split, GWO-Split, HHO-Split.

Keeps backward-compatible helper methods while delegating critical logic to core:
  - _get_duration        (previously copy-pasted across all 4 strategies)
  - _build_distance_matrix
  - _nearest_neighbor_tour

Inheriting strategies keep ONLY their algorithm-specific logic.
"""

from typing import List, Dict, Optional

from strategies.base_strategy import BaseRoutingStrategy
from uniride_core.adapters.string_matrix_builder import build_string_distance_matrix
from uniride_core.algorithms.ga_split_engine import nearest_neighbor_tour


class HybridSplitBaseStrategy(BaseRoutingStrategy):
    """
    Abstract base class for split-based (Route-First) optimization strategies.

    Subclasses must implement: name, display_name, description, optimize().
    They inherit the three shared helpers below for free.
    """

    # ── Shared helpers ────────────────────────────────────────────────────────

    # _get_duration is inherited from BaseRoutingStrategy

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

    def _nearest_neighbor_tour(
        self,
        waypoints: List[str],
        distance_matrix: Optional[Dict] = None,
        depot: Optional[str] = None,
    ) -> List[str]:
        """
        Build an initial tour using the nearest-neighbour heuristic.

        Args:
            waypoints:       All customer location codes (depot excluded).
            distance_matrix: Pre-built matrix for accurate distance lookups.
                             Falls back to input order when None.
            depot:           Unused — retained for API compatibility with
                             callers that pass it explicitly.

        Returns:
            An ordered list of location codes representing the tour.
        """
        return nearest_neighbor_tour(waypoints, distance_matrix)
