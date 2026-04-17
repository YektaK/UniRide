from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from utils.clustering import Point, Cluster, validate_cluster_capacity

class BaseClusteringStrategy(ABC):
    """
    Abstract base class for all clustering strategies used in the 'Cluster-First, Route-Second' architecture.
    """
    
    def __init__(self, sw_capacity: int = 4, so_capacity: int = 5):
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
        
    @abstractmethod
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        """
        Cluster a list of students into 'num_vehicles' clusters.
        
        Args:
            students: List of Point objects representing students
            num_vehicles: The target number of clusters to create
            kwargs: Additional algorithm-specific parameters (like time_matrix)
            
        Returns:
            List of Cluster objects.
        """
        pass
