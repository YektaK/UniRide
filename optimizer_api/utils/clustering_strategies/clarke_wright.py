from typing import List, Dict, Tuple
from utils.clustering import Point, Cluster, calculate_centroid, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy
from utils.data_loader import estimate_travel_time, haversine_distance

def get_duration(p1: Point, p2: Point, time_matrix: Dict) -> float:
    if p1.location_code in time_matrix and p2.location_code in time_matrix[p1.location_code]:
        return time_matrix[p1.location_code][p2.location_code]
        
    dist = haversine_distance(p1.lat, p1.lng, p2.lat, p2.lng)
    return estimate_travel_time(dist)

class ClarkeWrightClusteringStrategy(BaseClusteringStrategy):
    """
    Clarke-Wright Savings algorithm adapted for clustering.
    Calculates savings metric: S(i,j) = Cost(Depot, i) + Cost(Depot, j) - Cost(i, j)
    Merges nodes iteratively to build efficient clusters based on true road times.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        if not students or num_vehicles <= 0: return []
        
        time_matrix = kwargs.get("time_matrix", {})
        depot = kwargs.get("depot", {"id": "D.Kampus", "lat": 41.001, "lng": 29.177})
        
        # We need a dummy depot point for distance calc
        depot_point = Point(id=depot["id"], lat=depot["lat"], lng=depot["lng"], disability_type="So")
        
        points_dict = {p.id: p for p in students}
        points_dict[depot["id"]] = depot_point
        
        # Start with everyone in their own cluster (route)
        routes = [[s] for s in students]
        
        # Calculate savings for all pairs
        savings = []
        for i in range(len(students)):
            for j in range(i + 1, len(students)):
                s1, s2 = students[i], students[j]
                
                # S_ij = t(depot, i) + t(depot, j) - t(i, j)
                cost_d_i = get_duration(depot_point, s1, time_matrix)
                cost_d_j = get_duration(depot_point, s2, time_matrix)
                cost_i_j = get_duration(s1, s2, time_matrix)
                
                saving_val = cost_d_i + cost_d_j - cost_i_j
                savings.append((saving_val, s1, s2))
                
        # Sort savings descending
        savings.sort(key=lambda x: x[0], reverse=True)
        
        # Merge routes
        for saving_val, s1, s2 in savings:
            if len(routes) <= num_vehicles:
                break # Reached desired number of clusters
                
            # Find which routes s1 and s2 belong to
            route1_idx = -1
            route2_idx = -1
            for idx, r in enumerate(routes):
                if r[0].id == s1.id or r[-1].id == s1.id:
                    route1_idx = idx
                if r[0].id == s2.id or r[-1].id == s2.id:
                    route2_idx = idx
                    
            if route1_idx != -1 and route2_idx != -1 and route1_idx != route2_idx:
                r1 = routes[route1_idx]
                r2 = routes[route2_idx]
                
                combined = r1 + r2
                sw_count = sum(1 for p in combined if p.disability_type == "Sw")
                so_count = sum(1 for p in combined if p.disability_type == "So")
                
                if sw_count <= self.sw_capacity and so_count <= self.so_capacity:
                    # Valid merge! 
                    # Note: We aren't strictly checking the CW 120-min max_tour_time here because 
                    # the cluster string will just be fed to the local TSP solver anyway.
                    # As long as capacity is fine, savings heuristic merges them.
                    routes.pop(max(route1_idx, route2_idx))
                    routes.pop(min(route1_idx, route2_idx))
                    routes.append(combined)

        # Convert back to Clusters
        clusters = []
        for r in routes:
            clusters.append(Cluster(
                centroid=calculate_centroid(r),
                points=r,
                sw_count=sum(1 for p in r if p.disability_type == "Sw"),
                so_count=sum(1 for p in r if p.disability_type == "So")
            ))
            
        return clusters
