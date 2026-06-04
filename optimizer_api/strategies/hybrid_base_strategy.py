"""
Hybrid Split Base Strategy

Shared abstract base for all Route-First / Cluster-Second (Split-based)
strategies: GA-Split, PSO-Split, GWO-Split, HHO-Split.

Keeps shared request-mapping helpers while delegating critical logic to core:
  - _get_duration        (previously copy-pasted across all 4 strategies)
  - _build_distance_matrix

Inheriting strategies keep ONLY their algorithm-specific logic.
"""

from typing import List, Dict

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
