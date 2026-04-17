"""
Hybrid Split Base Strategy

Shared abstract base for all Route-First / Cluster-Second (Split-based)
strategies: GA-Split, PSO-Split, GWO-Split, HHO-Split.

Extracts duplicated helper methods into a single place (FIX-08 / P9 tech debt):
  - _get_duration        (previously copy-pasted across all 4 strategies)
  - _build_distance_matrix
  - _nearest_neighbor_tour

Inheriting strategies keep ONLY their algorithm-specific logic.
"""

import logging
from typing import List, Dict, Optional, cast

from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import haversine_distance, estimate_travel_time
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)


class HybridSplitBaseStrategy(BaseRoutingStrategy):
    """
    Abstract base class for split-based (Route-First) optimization strategies.

    Subclasses must implement: name, display_name, description, optimize().
    They inherit the three shared helpers below for free.
    """

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _get_duration(
        self,
        from_loc: str,
        to_loc: str,
        time_matrix: Dict,
        coordinates: Dict,
    ) -> float:
        """
        Return travel time between two locations in minutes.

        Resolution order:
        1. Supabase time_matrix lookup (exact)
        2. Haversine + speed estimate (coordinate fallback)
        3. DEFAULT_TRAVEL_FALLBACK_MINUTES with a warning log (last resort)
        """
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        # FIX-04 (shared): named constant + warning so missing matrix entries
        # are visible in logs instead of silently returning 15.0.
        logger.warning(
            "Distance matrix miss: %s \u2192 %s, using fallback %.1f min",
            from_loc,
            to_loc,
            DEFAULT_TRAVEL_FALLBACK_MINUTES,
        )
        return DEFAULT_TRAVEL_FALLBACK_MINUTES

    def _build_distance_matrix(
        self,
        location_ids: List[str],
        time_matrix: Dict,
        coordinates: Dict,
    ) -> Dict[str, Dict[str, float]]:
        """Build a complete O(n²) distance matrix for all locations."""
        matrix: Dict[str, Dict[str, float]] = {}
        for loc1 in location_ids:
            matrix[loc1] = {}
            for loc2 in location_ids:
                if loc1 == loc2:
                    matrix[loc1][loc2] = 0.0
                else:
                    matrix[loc1][loc2] = self._get_duration(
                        loc1, loc2, time_matrix, coordinates
                    )
        return matrix

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
                             Falls back to random selection when None.
            depot:           Unused — retained for API compatibility with
                             callers that pass it explicitly.

        Returns:
            An ordered list of location codes representing the tour.
        """
        if not waypoints:
            return []

        tour: List[str] = []
        remaining = waypoints.copy()
        current = remaining.pop(0)
        tour.append(current)

        while remaining:
            if distance_matrix and current in distance_matrix:
                # Use actual distances when available
                best_next = min(
                    remaining,
                    key=lambda x: distance_matrix[current].get(x, float("inf")),
                )
            else:
                # No matrix — random selection maintains population diversity
                import random
                best_next = remaining[random.randint(0, len(remaining) - 1)]

            best_next = cast(str, best_next)
            tour.append(best_next)
            remaining.remove(best_next)
            current = best_next

        return tour
