from models.schemas import OptimizationRequest, OptimizationResponse, VehicleRoute, RouteStep
from strategies.base_strategy import BaseRoutingStrategy
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from utils.data_loader import DataLoader
import math

class ORToolsCVRPStrategy(BaseRoutingStrategy):
    """
    MATLAB Exact Parity:
    - Independent Sw & So Capacity Limits
    - Reading Real Asymmetric Time Matrix from Veri.xlsx
    - Strict Maximum Tour Time Limit enforcement
    """
    def __init__(self):
        super().__init__()
        self.data_loader = DataLoader.get_instance()
        
    def _create_data_model(self, depot, students, sw_capacity, so_capacity):
        data = {}
        locations = [depot] + students
        
        # 1. Fetch Exact Time Matrix
        location_ids = [loc.id for loc in locations]
        raw_time_matrix = self.data_loader.get_submatrix(location_ids)
        
        # Scale to integer (x100 for 2 decimal places precision)
        SCALING_FACTOR = 100
        data["time_matrix"] = [[int(round(val * SCALING_FACTOR)) for val in row] for row in raw_time_matrix]
        data["locations"] = locations
        
        # 2. Extract specific demands properly
        data["sw_demands"] = [0] + [1 if loc.type == "Sw" else 0 for loc in students]
        data["so_demands"] = [0] + [1 if loc.type == "So" else 0 for loc in students]
        
        # Provide enough empty vehicles for OR-Tools to pick from
        total_veh = len(students)
        data["num_vehicles"] = total_veh
        
        data["sw_capacities"] = [sw_capacity] * total_veh
        data["so_capacities"] = [so_capacity] * total_veh
        data["depot"] = 0
        return data, SCALING_FACTOR

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        students = request.students
        if not students:
            return OptimizationResponse(algorithm_used="ortools_exact_cvrp", success=True, routes=[])
            
        data, SCALING_FACTOR = self._create_data_model(
            request.depot, students, request.sw_capacity, request.so_capacity
        )

        manager = pywrapcp.RoutingIndexManager(
            len(data["time_matrix"]), data["num_vehicles"], data["depot"]
        )
        routing = pywrapcp.RoutingModel(manager)

        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["time_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # DIMENSION 1: SW CAPACITY
        def sw_demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data["sw_demands"][from_node]

        sw_demand_callback_index = routing.RegisterUnaryTransitCallback(sw_demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            sw_demand_callback_index,
            0,
            data["sw_capacities"],
            True,
            "SwCapacity",
        )
        
        # DIMENSION 2: SO CAPACITY
        def so_demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data["so_demands"][from_node]

        so_demand_callback_index = routing.RegisterUnaryTransitCallback(so_demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            so_demand_callback_index,
            0,
            data["so_capacities"],
            True,
            "SoCapacity",
        )
        
        # DIMENSION 3: MAX TRAVEL TIME
        max_time_scaled = int(request.max_travel_time * SCALING_FACTOR)
        routing.AddDimension(
            transit_callback_index,
            0, 
            max_time_scaled, 
            True, 
            "Time"
        )
        
        # Penalize extra vehicles heavily so solver minimizes vehicle fleet count (like MATLAB does)
        penalty_cost = 1440 * SCALING_FACTOR
        for vehicle_id in range(data["num_vehicles"]):
            routing.SetFixedCostOfVehicle(penalty_cost, vehicle_id)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.FromSeconds(5)

        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            return OptimizationResponse(
                algorithm_used="ortools_exact_cvrp",
                success=False,
                routes=[],
                error_message="OR-Tools CVRP Failed. Strict constraints breached (Check max_travel_time or capacities)."
            )

        routes = []
        actual_vehicle_idx = 1
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue
                
            route_details = []
            route_time_scaled = 0
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                next_node_index = manager.IndexToNode(index)
                
                # Read pure travel time directly from the matrix to avoid
                # GetArcCostForVehicle including the fixed vehicle penalty cost
                arc_time = data["time_matrix"][node_index][next_node_index]
                route_time_scaled += arc_time
                
                duration_minutes = arc_time / SCALING_FACTOR
                
                loc1_id = data["locations"][node_index].id
                loc2_id = data["locations"][next_node_index].id
                
                if loc1_id != loc2_id:
                    route_details.append(RouteStep(
                        location1=loc1_id,
                        location2=loc2_id,
                        duration=round(duration_minutes, 2),
                        distance=0.0
                    ))
            
            if len(route_details) > 0:
                total_duration = route_time_scaled / SCALING_FACTOR
                routes.append(VehicleRoute(
                    vehicle_id=f"Araç {actual_vehicle_idx}",
                    route_details=route_details,
                    total_duration_minutes=round(total_duration, 2),
                    total_distance_km=0.0
                ))
                actual_vehicle_idx += 1

        return OptimizationResponse(
            algorithm_used="ortools_exact_cvrp",
            success=True,
            routes=routes
        )
