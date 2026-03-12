from abc import ABC, abstractmethod
from models.schemas import OptimizationRequest, OptimizationResponse

class BaseRoutingStrategy(ABC):
    """
    Abstract Base Class for all routing strategies.
    Any new routing algorithm (MATLAB, OR-Tools, Custom) must inherit from this class 
    and implement the 'optimize' method.
    """
    
    @abstractmethod
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """
        Execute the optimization algorithm.
        
        Args:
            request (OptimizationRequest): The validated JSON request containing nodes, depot, and constraints.
            
        Returns:
            OptimizationResponse: The calculated routes and execution metrics.
        """
        pass
