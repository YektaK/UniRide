from models.schemas import OptimizationRequest, OptimizationResponse, VehicleRoute, RouteStep
from strategies.base_strategy import BaseRoutingStrategy
import math

class KMeansTSPStrategy(BaseRoutingStrategy):
    """
    Dummy implementation of K-Means + TSP Strategy.
    In a real-world scenario, you would copy the logic from MATLAB or existing TS code here.
    """
    def __init__(self):
        super().__init__()
        
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        # Extremely simplified distance calculation (Haversine formula approximation)
        # Just for skeleton demonstration purposes
        R = 6371 # km
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat/2) * math.sin(dLat/2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dLon/2) * math.sin(dLon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        return distance * 1000 # returns in meters
        
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """
        Implementation of the BaseRoutingStrategy.
        """
        # 1. Parse Data
        depot = request.depot
        students = request.students
        
        # In a real environment:
        # 1. Cluster students using KMeans (from scikit-learn)
        # 2. Iterate clusters and solve TSP (using custom logic or OR-Tools)
        
        # --- MOCK ROUTE GENERATION FOR SKELETON PROOF OF CONCEPT ---
        if not students:
            return OptimizationResponse(
                algorithm_used="kmeans_tsp",
                success=True,
                routes=[],
                error_message=None
            )
            
        mock_route_details = []
        current_loc = depot
        total_time = 0
        total_dist = 0
        
        # Visit all students sequentially (Dummy logic)
        for student in students:
            dist = self._calculate_distance(current_loc.lat, current_loc.lng, student.lat, student.lng)
            # assume 40km/h -> 40000m / 60min = ~666m per minute
            time_spent = dist / 666.0
            
            step = RouteStep(
                location1=current_loc.id,
                location2=student.id,
                duration=round(time_spent, 2),
                distance=round(dist, 2)
            )
            mock_route_details.append(step)
            total_time += time_spent
            total_dist += dist
            current_loc = student
            
        # Return to depot
        dist_home = self._calculate_distance(current_loc.lat, current_loc.lng, depot.lat, depot.lng)
        time_home = dist_home / 666.0
        mock_route_details.append(RouteStep(
            location1=current_loc.id,
            location2=depot.id,
            duration=round(time_home, 2),
            distance=round(dist_home, 2)
        ))
        
        total_time += time_home
        total_dist += dist_home
        
        mock_vehicle_route = VehicleRoute(
            vehicle_id="Vehicle_1_Mock",
            route_details=mock_route_details,
            total_duration_minutes=round(total_time, 2),
            total_distance_km=round(total_dist / 1000, 2)
        )
        
        return OptimizationResponse(
            algorithm_used="kmeans_tsp",
            success=True,
            routes=[mock_vehicle_route]
        )
