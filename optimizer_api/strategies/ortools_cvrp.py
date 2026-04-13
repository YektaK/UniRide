"""
OR-Tools CVRP Strategy
Uses Google OR-Tools for Capacitated Vehicle Routing Problem
Industry-standard solver for VRP
"""

import logging
import time
from typing import List, Dict, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, euclidean_distance, haversine_distance, estimate_travel_time
from utils.patterns import SingletonMeta
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)


class ORToolsCVRPStrategy(BaseRoutingStrategy):
    """
    OR-Tools based CVRP solver.
    Uses Google's optimization library for vehicle routing.
    """

    @property
    def name(self) -> str:
        return "ortools_cvrp"

    @property
    def display_name(self) -> str:
        return "OR-Tools CVRP"

    @property
    def description(self) -> str:
        return "Google OR-Tools kütüphanesi ile endüstri standardı VRP çözümü."

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between locations"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        logger.warning(f"Distance matrix miss for {from_loc} to {to_loc}. Using default fallback: {DEFAULT_TRAVEL_FALLBACK_MINUTES} mins")
        return DEFAULT_TRAVEL_FALLBACK_MINUTES

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute OR-Tools optimization"""
        start_time = time.time()

        students = request.students
        depot = request.depot

        if not students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time
            )

        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
        except ImportError:
            # Fall back to greedy if OR-Tools not installed
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message="OR-Tools not installed. Run: pip install ortools",
                execution_time_seconds=time.time() - start_time
            )

        # Build time matrix
        data_loader = DataLoader.get_instance()
        location_ids = [depot.id] + [s.location_code for s in students]

        # Build coordinates BEFORE get_submatrix for euclidean distance fallback
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        raw_matrix = data_loader.get_submatrix(location_ids, coordinates)

        # Convert to integer matrix (OR-Tools uses integers)
        # Multiply by 10 for precision
        time_matrix = [[int(raw_matrix[i][j] * 10) for j in range(len(raw_matrix))] for i in range(len(raw_matrix))]

        # Build euclidean distance matrix (same index order as location_ids)
        dist_matrix = DataLoader.build_euclidean_matrix(location_ids, coordinates)

        # Create routing model
        num_locations = len(location_ids)
        num_vehicles = min(len(students), 10)  # Reasonable upper bound
        depot_index = 0

        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, depot_index)
        routing = pywrapcp.RoutingModel(manager)

        # Distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Capacity constraints
        # Sw students (wheelchair)
        sw_demands = [0]  # Depot
        for s in students:
            sw_demands.append(10 if s.disability_type == "Sw" else 0)

        def sw_demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return sw_demands[from_node]

        sw_demand_callback_index = routing.RegisterUnaryTransitCallback(sw_demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            sw_demand_callback_index,
            0,  # null capacity slack
            [request.sw_capacity * 10] * num_vehicles,  # vehicle maximum capacities
            False,  # start cumul to zero
            'SwCapacity'
        )

        # So students (walking)
        so_demands = [0]  # Depot
        for s in students:
            so_demands.append(10 if s.disability_type == "So" else 0)

        def so_demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return so_demands[from_node]

        so_demand_callback_index = routing.RegisterUnaryTransitCallback(so_demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            so_demand_callback_index,
            0,
            [request.so_capacity * 10] * num_vehicles,
            False,
            'SoCapacity'
        )

        # Time constraint
        routing.AddDimension(
            transit_callback_index,
            0,  # allow waiting time
            int(request.max_travel_time * 10),  # maximum time per vehicle
            False,
            'Time'
        )

        # Setting first solution heuristic
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 30

        # Solve
        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message="OR-Tools could not find a solution",
                execution_time_seconds=time.time() - start_time
            )

        # Extract routes
        routes = []
        time_dimension = routing.GetDimensionOrDie('Time')

        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route_details = []
            route_students = []
            total_duration = 0
            sw_count = 0
            so_count = 0

            while not routing.IsEnd(index):
                from_index = index
                to_index = solution.Value(routing.NextVar(index))

                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)

                if to_node > 0:  # Not depot
                    student = students[to_node - 1]  # -1 because depot is 0
                    route_students.append(student)
                    if student.disability_type == "Sw":
                        sw_count += 1
                    else:
                        so_count += 1

                duration = time_matrix[from_node][to_node] / 10.0
                total_duration += duration

                route_details.append(RouteStep(
                    location1=location_ids[from_node],
                    location2=location_ids[to_node],
                    duration=round(duration, 2),
                    distance=round(dist_matrix[from_node][to_node], 2)
                ))

                index = to_index

            if route_details and len(route_students) > 0:
                routes.append(VehicleRoute(
                    vehicle_id=f"Araç {vehicle_id + 1} (OR-Tools)",
                    route_details=route_details,
                    total_duration_minutes=round(total_duration, 2),
                    total_distance_km=round(sum(s.distance for s in route_details), 2),
                    sw_count=sw_count,
                    so_count=so_count,
                    student_ids=[s.id for s in route_students]
                ))

        execution_time = time.time() - start_time

        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=round(execution_time, 4)
        )
