from models.schemas import OptimizationRequest, OptimizationResponse, VehicleRoute, RouteStep
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader
from sklearn.cluster import KMeans
import numpy as np
import math
import itertools

class PermutationTSPStrategy(BaseRoutingStrategy):
    """
    K-Means Clustering + Exact Permutation Search (TSP)
    Matches MATLAB's exact clustering loop but uses brute-force permutations 
    to find the absolute shortest path for each cluster instead of intlinprog.
    """
    def __init__(self):
        super().__init__()
        self.data_loader = DataLoader.get_instance()

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        students = request.students
        if not students:
            return OptimizationResponse(algorithm_used="permutation_tsp", success=True, routes=[])

        depot = request.depot
        sw_cap = request.sw_capacity
        so_cap = request.so_capacity
        max_time = request.max_travel_time

        locations = [depot] + students
        loc_ids = [loc.id for loc in locations]
        raw_matrix = self.data_loader.get_submatrix(loc_ids)
        time_map = {loc_ids[i]: {loc_ids[j]: raw_matrix[i][j] for j in range(len(loc_ids))} for i in range(len(loc_ids))}

        # Calculate initial K-Means vehicle count
        sw_count = sum(1 for s in students if s.type == "Sw")
        so_count = sum(1 for s in students if s.type == "So")
        num_vehicles = max(1, math.ceil(sw_count / max(1, sw_cap)), math.ceil(so_count / max(1, so_cap)))

        coords = np.array([[s.lat, s.lng] for s in students])

        while True:
            # 1. Cluster students using K-Means (Cityblock distance approximation via standard KMeans)
            kmeans = KMeans(n_clusters=num_vehicles, n_init=10, max_iter=100, random_state=42)
            cluster_labels = kmeans.fit_predict(coords)

            clusters = [[] for _ in range(num_vehicles)]
            for idx, label in enumerate(cluster_labels):
                clusters[label].append(students[idx])

            valid_clustering = True
            final_routes = []
            
            # 2. Check clusters and apply Permutation TSP
            for v_idx, cluster_students in enumerate(clusters):
                if not cluster_students:
                    continue
                    
                # Capacity Check
                c_sw = sum(1 for s in cluster_students if s.type == "Sw")
                c_so = sum(1 for s in cluster_students if s.type == "So")
                
                if c_sw > sw_cap or c_so > so_cap:
                    valid_clustering = False
                    break
                    
                # Permutation TSP Search
                best_tour_time = float('inf')
                best_route = None
                
                # If cluster > 9 students, permutation (n!) takes too long, fallback to greedy for this cluster
                if len(cluster_students) > 9:
                    valid_clustering = False # Force split into more vehicles
                    break
                
                for perm in itertools.permutations(cluster_students):
                    current_time = 0.0
                    current_loc = depot
                    valid_tour = True
                    
                    for student in perm:
                        travel_t = time_map[current_loc.id][student.id]
                        current_time += travel_t
                        current_loc = student
                        
                        if current_time > max_time:
                            valid_tour = False
                            break
                            
                    if not valid_tour:
                        continue
                        
                    # Return to depot
                    current_time += time_map[current_loc.id][depot.id]
                    
                    if current_time <= max_time and current_time < best_tour_time:
                        best_tour_time = current_time
                        best_route = perm
                        
                if best_route is None:
                    # No permutation satisfies the max_time constraint
                    valid_clustering = False
                    break
                    
                # Build Vehicle Route object
                route_details = []
                last_node = depot
                run_time = 0.0
                for s in best_route:
                    leg_time = time_map[last_node.id][s.id]
                    route_details.append(RouteStep(
                        location1=last_node.id,
                        location2=s.id,
                        duration=round(leg_time, 2),
                        distance=0.0
                    ))
                    run_time += leg_time
                    last_node = s
                    
                ret_time = time_map[last_node.id][depot.id]
                route_details.append(RouteStep(
                    location1=last_node.id,
                    location2=depot.id,
                    duration=round(ret_time, 2),
                    distance=0.0
                ))
                run_time += ret_time
                
                final_routes.append(VehicleRoute(
                    vehicle_id=f"Araç {v_idx+1} (Permutation)",
                    route_details=route_details,
                    total_duration_minutes=round(run_time, 2),
                    total_distance_km=0.0
                ))

            if valid_clustering:
                break
                
            num_vehicles += 1
            # Failsafe: if we reach more vehicles than students, return error
            if num_vehicles > len(students):
                return OptimizationResponse(
                    algorithm_used="permutation_tsp",
                    success=False,
                    routes=[],
                    error_message="Could not find a valid permutation tour for the given constraints. Increase max_travel_time."
                )

        return OptimizationResponse(
            algorithm_used="permutation_tsp",
            success=True,
            routes=final_routes
        )
