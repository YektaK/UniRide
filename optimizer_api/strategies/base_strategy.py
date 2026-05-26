"""
Base Strategy Abstract Class
All optimization algorithms must inherit from this class
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from models.schemas import OptimizationRequest, OptimizationResponse
from uniride_core.algorithms.route_metrics import calculate_route_duration, get_duration


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
        return get_duration(from_loc, to_loc, time_matrix, coordinates)

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
        return calculate_route_duration(route, depot, time_matrix, coordinates)
