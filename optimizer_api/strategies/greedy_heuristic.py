from models.schemas import OptimizationRequest, OptimizationResponse, VehicleRoute, RouteStep
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader
import itertools

class GreedyHeuristicStrategy(BaseRoutingStrategy):
    """
    Greedy (Nearest Neighbor) Heuristic.
    Constructs routes by always visiting the geographically/temporally closest unvisited student,
    respecting capacity limits (Sw and So) and the maximum tour time.
    """
    def __init__(self):
        super().__init__()
        self.data_loader = DataLoader.get_instance()

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        students = request.students
        if not students:
            return OptimizationResponse(algorithm_used="greedy_heuristic", success=True, routes=[])

        depot = request.depot
        sw_capacity = request.sw_capacity
        so_capacity = request.so_capacity
        max_time = request.max_travel_time

        locations = [depot] + students
        loc_ids = [loc.id for loc in locations]
        
        # Load time matrix
        raw_matrix = self.data_loader.get_submatrix(loc_ids)
        time_matrix = {loc_ids[i]: {loc_ids[j]: raw_matrix[i][j] for j in range(len(loc_ids))} for i in range(len(loc_ids))}

        unassigned = students.copy()
        routes = []
        vehicle_idx = 1

        while unassigned:
            current_loc = depot
            current_sw = 0
            current_so = 0
            current_time = 0.0
            route_details = []

            # While there's capacity and unassigned students
            while unassigned and current_sw <= sw_capacity and current_so <= so_capacity:
                best_student = None
                best_time = float('inf')

                # Find nearest valid student
                for student in unassigned:
                    # Check capacity
                    sw_needed = 1 if student.type == "Sw" else 0
                    so_needed = 1 if student.type == "So" else 0
                    
                    if current_sw + sw_needed > sw_capacity or current_so + so_needed > so_capacity:
                        continue
                        
                    # Check if adding this student and returning to depot exceeds max time
                    travel_time = time_matrix[current_loc.id][student.id]
                    return_time = time_matrix[student.id][depot.id]
                    
                    if current_time + travel_time + return_time > max_time:
                        continue
                        
                    if travel_time < best_time:
                        best_time = travel_time
                        best_student = student

                if best_student is None:
                    break # Vehicle is full or adding more violates time constraints

                # Assign student
                route_details.append(RouteStep(
                    location1=current_loc.id,
                    location2=best_student.id,
                    duration=round(best_time, 2),
                    distance=0.0
                ))
                current_time += best_time
                current_sw += 1 if best_student.type == "Sw" else 0
                current_so += 1 if best_student.type == "So" else 0
                current_loc = best_student
                unassigned.remove(best_student)

            # Return to depot
            return_time = time_matrix[current_loc.id][depot.id]
            route_details.append(RouteStep(
                location1=current_loc.id,
                location2=depot.id,
                duration=round(return_time, 2),
                distance=0.0
            ))
            current_time += return_time

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {vehicle_idx} (Greedy)",
                route_details=route_details,
                total_duration_minutes=round(current_time, 2),
                total_distance_km=0.0
            ))
            vehicle_idx += 1

        return OptimizationResponse(
            algorithm_used="greedy_heuristic",
            success=True,
            routes=routes
        )
