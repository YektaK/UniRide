"""
Base Strategy Abstract Class
All optimization algorithms must inherit from this class
"""

from abc import ABC, abstractmethod
from typing import List, Dict
import logging
from models.schemas import OptimizationRequest, OptimizationResponse
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES
from utils.haversine import haversine_distance, estimate_travel_time

logger = logging.getLogger(__name__)


class BaseRoutingStrategy(ABC):
    """
    Abstract Base Class for all routing strategies.
    Any new routing algorithm must inherit from this class
    and implement the 'optimize' method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Algorithm name identifier"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable algorithm name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Algorithm description"""
        pass

    @abstractmethod
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """
        Execute the optimization algorithm.

        Args:
            request: The validated request containing students, depot, and constraints.

        Returns:
            OptimizationResponse: The calculated routes and execution metrics.
        """
        pass

    def get_time_matrix(self, location_ids: list, data_loader) -> dict:
        """
        Extract time matrix for given locations.

        Args:
            location_ids: List of location IDs
            data_loader: DataLoader instance

        Returns:
            Dict of dicts: matrix[from][to] = duration
        """
        raw_matrix = data_loader.get_submatrix(location_ids)
        return {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }

    # === SHARED HELPER METHODS (extracted from meta-heuristics) ===

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """
        Calculate duration between two locations using time matrix or coordinates.
        
        This is a shared helper method used by GA, PSO, GWO, HHO strategies.
        Attempts to get time from matrix first, then falls back to haversine calculation,
        then uses DEFAULT_TRAVEL_FALLBACK_MINUTES constant (15.0 minutes).
        
        Args:
            from_loc: Origin location ID
            to_loc: Destination location ID
            time_matrix: Dict[from_id][to_id] = travel_time_minutes
            coordinates: Dict[location_id] = {"lat": float, "lng": float}
            
        Returns:
            Travel time in minutes (float)
        """
        # Priority 1: Time matrix
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        # Priority 2: Haversine calculation from coordinates
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        # Priority 3: Fallback constant (no data available)
        logger.warning(
            f"Distance matrix miss for {from_loc} to {to_loc}. "
            f"Using default fallback: {DEFAULT_TRAVEL_FALLBACK_MINUTES} mins"
        )
        return DEFAULT_TRAVEL_FALLBACK_MINUTES

    def _calculate_route_duration(
        self,
        route: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> float:
        """
        Calculate total route duration given a sequence of stops.
        
        This is a shared helper method used by GA, PSO, GWO, HHO strategies.
        Computes: depot → stop[0] → stop[1] → ... → stop[n] → depot
        
        Args:
            route: List of location IDs in order (waypoints, not including depot)
            depot: Depot location ID
            time_matrix: Duration matrix (Dict[from_id][to_id] = minutes)
            coordinates: Coordinate mapping for haversine fallback
            
        Returns:
            Total route duration in minutes (float)
        """
        if not route:
            return 0.0

        total = 0.0
        
        # Depot to first location
        total += self._get_duration(depot, route[0], time_matrix, coordinates)

        # Between consecutive locations
        for i in range(len(route) - 1):
            total += self._get_duration(route[i], route[i + 1], time_matrix, coordinates)

        # Last location back to depot
        total += self._get_duration(route[-1], depot, time_matrix, coordinates)

        return total
