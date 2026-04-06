"""
Base Strategy Abstract Class
All optimization algorithms must inherit from this class
"""

from abc import ABC, abstractmethod
from models.schemas import OptimizationRequest, OptimizationResponse


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
