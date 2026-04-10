"""
PyVRP Strategy
State-of-the-art Hybrid Genetic Search (HGS) for CVRPTW
DIMACS 2021 Challenge Winner

Reference: Vidal, T. (2022). Hybrid genetic search for the CVRP
Installation: pip install pyvrp
"""

import time
from typing import List, Dict, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES
import logging

logger = logging.getLogger(__name__)


class PyVRPStrategy(BaseRoutingStrategy):
    """
    PyVRP based CVRPTW solver using Hybrid Genetic Search (HGS).
    
    Advantages:
    - DIMACS 2021 Challenge Winner
    - State-of-the-art solution quality
    - Native heterogeneous fleet support (HFVRP)
    - Time windows support (CVRPTW)
    - Multi-depot support
    - Well-documented academic implementation
    
    Best for:
    - High-quality offline route planning
    - Benchmark reference
    - Academic research
    - Quality-critical scenarios
    """

    @property
    def name(self) -> str:
        return "pyvrp"

    @property
    def display_name(self) -> str:
        return "PyVRP (HGS - DIMACS Winner)"

    @property
    def description(self) -> str:
        return "DIMACS 2021 birincisi Hybrid Genetic Search algoritması. En yüksek çözüm kalitesi."

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between locations in minutes"""
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
        """Execute PyVRP optimization"""
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
            from pyvrp import Model, ProblemData
            from pyvrp.stop import MaxRuntime
        except ImportError:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message="PyVRP not installed. Run: pip install pyvrp",
                execution_time_seconds=time.time() - start_time
            )

        # Load time matrix
        data_loader = DataLoader.get_instance()
        location_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(location_ids)

        # Build time matrix dict
        time_matrix = {}
        for i, from_loc in enumerate(location_ids):
            time_matrix[from_loc] = {}
            for j, to_loc in enumerate(location_ids):
                time_matrix[from_loc][to_loc] = raw_matrix[i][j]

        # Build coordinates dict
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        try:
            # Build duration matrix (in seconds for PyVRP)
            n = len(location_ids)
            duration_matrix = []
            for i, from_loc in enumerate(location_ids):
                row = []
                for j, to_loc in enumerate(location_ids):
                    duration_minutes = raw_matrix[i][j] if raw_matrix[i][j] > 0 else DEFAULT_TRAVEL_FALLBACK_MINUTES
                    row.append(int(duration_minutes * 60))  # Convert to seconds
                duration_matrix.append(row)

            # Create PyVRP model
            model = Model()

            # Add depot (index 0)
            depot_coords = coordinates[depot.id]
            model.add_depot(
                x=int(depot_coords["lng"] * 1000000),  # Scale for integer precision
                y=int(depot_coords["lat"] * 1000000)
            )

            # Add clients (students)
            for idx, student in enumerate(students):
                loc_code = student.location_code
                if loc_code in coordinates:
                    coords = coordinates[loc_code]
                    model.add_client(
                        x=int(coords["lng"] * 1000000),
                        y=int(coords["lat"] * 1000000),
                        # Demand: [Sw_demand, So_demand]
                        demand=[1 if student.disability_type == "Sw" else 0,
                                0 if student.disability_type == "Sw" else 1]
                    )
                else:
                    model.add_client(
                        x=0,
                        y=0,
                        demand=[1 if student.disability_type == "Sw" else 0,
                                0 if student.disability_type == "Sw" else 1]
                    )

            # Add vehicle type with heterogeneous capacity
            model.add_vehicle_type(
                num_available=min(len(students), 15),  # Max vehicles
                capacity=[request.sw_capacity, request.so_capacity],  # [Sw cap, So cap]
                # Depot assignment (default is 0)
            )

            # Add duration matrix edges
            for i in range(n):
                for j in range(n):
                    if i != j:
                        model.add_edge(i, j, duration=duration_matrix[i][j], distance=duration_matrix[i][j])

            # Solve
            result = model.solve(stop=MaxRuntime(30))  # 30 second time limit

            if result.best is None:
                return OptimizationResponse(
                    algorithm_used=self.name,
                    success=False,
                    routes=[],
                    total_vehicles=0,
                    error_message="PyVRP could not find a feasible solution",
                    execution_time_seconds=time.time() - start_time
                )

            # Extract routes from solution
            routes = []
            solution = result.best

            for route_idx, route in enumerate(solution.routes()):
                if not route:
                    continue

                route_details = []
                route_students = []
                total_duration = 0
                sw_count = 0
                so_count = 0
                prev_location = depot.id

                for client_idx in route:
                    # client_idx is 0-indexed for clients, we need to map back
                    # In PyVRP, depot is separate, clients are indexed from 0
                    student_idx = client_idx  # Already 0-indexed for clients
                    if 0 <= student_idx < len(students):
                        student = students[student_idx]
                        current_location = student.location_code

                        # Calculate duration
                        duration = self._get_duration(prev_location, current_location, time_matrix, coordinates)
                        total_duration += duration

                        route_details.append(RouteStep(
                            location1=prev_location,
                            location2=current_location,
                            duration=round(duration, 2),
                            distance=0.0
                        ))

                        route_students.append(student)
                        if student.disability_type == "Sw":
                            sw_count += 1
                        else:
                            so_count += 1

                        prev_location = current_location

                # Add return to depot
                if route_students:
                    duration = self._get_duration(prev_location, depot.id, time_matrix, coordinates)
                    total_duration += duration
                    route_details.append(RouteStep(
                        location1=prev_location,
                        location2=depot.id,
                        duration=round(duration, 2),
                        distance=0.0
                    ))

                    routes.append(VehicleRoute(
                        vehicle_id=f"Araç {len(routes) + 1} (PyVRP)",
                        route_details=route_details,
                        total_duration_minutes=round(total_duration, 2),
                        total_distance_km=0.0,
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

        except Exception as e:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message=f"PyVRP optimization failed: {str(e)}",
                execution_time_seconds=time.time() - start_time
            )


class PyVRPAlternativeStrategy(BaseRoutingStrategy):
    """
    Alternative PyVRP implementation using direct ProblemData construction.
    Use this if the Model-based approach has issues.
    """

    @property
    def name(self) -> str:
        return "pyvrp_alt"

    @property
    def display_name(self) -> str:
        return "PyVRP Alternative"

    @property
    def description(self) -> str:
        return "PyVRP alternatif implementasyon (ProblemData tabanlı)."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute using ProblemData directly"""
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
            import numpy as np
            from pyvrp import ProblemData, Client, Depot, VehicleType
            from pyvrp.stop import MaxRuntime, MaxIterations
        except ImportError:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message="PyVRP not installed. Run: pip install pyvrp",
                execution_time_seconds=time.time() - start_time
            )

        # Load time matrix
        data_loader = DataLoader.get_instance()
        location_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(location_ids)

        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        try:
            n_clients = len(students)
            
            # Build duration matrix (seconds, scaled for integer)
            scale = 100  # Scale factor for precision
            n = n_clients + 1  # +1 for depot

            # Duration matrix: depot + clients
            duration_matrix = np.zeros((n, n), dtype=int)
            for i in range(n):
                for j in range(n):
                    if i == j:
                        duration_matrix[i, j] = 0
                    elif i == 0 and j > 0:
                        # Depot to client
                        duration = raw_matrix[0][j] if raw_matrix[0][j] > 0 else DEFAULT_TRAVEL_FALLBACK_MINUTES
                        duration_matrix[i, j] = int(duration * 60 * scale)
                    elif i > 0 and j == 0:
                        # Client to depot
                        duration = raw_matrix[i][0] if raw_matrix[i][0] > 0 else DEFAULT_TRAVEL_FALLBACK_MINUTES
                        duration_matrix[i, j] = int(duration * 60 * scale)
                    else:
                        # Client to client
                        duration = raw_matrix[i][j] if raw_matrix[i][j] > 0 else DEFAULT_TRAVEL_FALLBACK_MINUTES
                        duration_matrix[i, j] = int(duration * 60 * scale)

            # Create depot
            depot_obj = Depot(
                x=int(depot.lng * 1000000),
                y=int(depot.lat * 1000000),
                tw_early=0,  # Earliest time window
                tw_late=int(request.max_travel_time * 60 * scale)  # Latest time window
            )

            # Create clients
            clients = []
            for idx, student in enumerate(students):
                loc_code = student.location_code
                if loc_code in coordinates:
                    coords = coordinates[loc_code]
                    x = int(coords["lng"] * 1000000)
                    y = int(coords["lat"] * 1000000)
                else:
                    x, y = 0, 0

                # Demand based on disability type
                if student.disability_type == "Sw":
                    demand = [1, 0]  # Sw demand
                else:
                    demand = [0, 1]  # So demand

                client = Client(
                    x=x,
                    y=y,
                    delivery=np.array(demand),
                    tw_early=0,
                    tw_late=int(request.max_travel_time * 60 * scale),
                    service_duration=int(5 * 60 * scale)  # 5 minutes service time
                )
                clients.append(client)

            # Create vehicle type
            vehicle_type = VehicleType(
                num_available=min(n_clients, 15),
                capacity=np.array([request.sw_capacity, request.so_capacity]),
                tw_late=int(request.max_travel_time * 60 * scale)
            )

            # Create problem data
            data = ProblemData(
                clients=clients,
                depots=[depot_obj],
                vehicle_types=[vehicle_type],
                distance_matrix=duration_matrix,  # Use same for distance
                duration_matrix=duration_matrix
            )

            # Solve
            from pyvrp import solve
            result = solve(data, stop=MaxRuntime(30))

            if result.best is None:
                return OptimizationResponse(
                    algorithm_used=self.name,
                    success=False,
                    routes=[],
                    total_vehicles=0,
                    error_message="PyVRP could not find a feasible solution",
                    execution_time_seconds=time.time() - start_time
                )

            # Extract routes
            routes = []
            solution = result.best

            for route in solution.routes():
                route_details = []
                route_students = []
                total_duration = 0
                sw_count = 0
                so_count = 0
                prev_location = depot.id

                for client in route:
                    student_idx = client
                    if 0 <= student_idx < len(students):
                        student = students[student_idx]
                        current_location = student.location_code

                        # Get duration
                        if prev_location in coordinates and current_location in coordinates:
                            c1 = coordinates[prev_location]
                            c2 = coordinates[current_location]
                            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
                            duration = estimate_travel_time(dist)
                        else:
                            duration = raw_matrix[location_ids.index(prev_location)][location_ids.index(current_location)] if prev_location in location_ids and current_location in location_ids else DEFAULT_TRAVEL_FALLBACK_MINUTES

                        total_duration += duration

                        route_details.append(RouteStep(
                            location1=prev_location,
                            location2=current_location,
                            duration=round(duration, 2),
                            distance=0.0
                        ))

                        route_students.append(student)
                        if student.disability_type == "Sw":
                            sw_count += 1
                        else:
                            so_count += 1

                        prev_location = current_location

                if route_students:
                    # Return to depot
                    if prev_location in coordinates and depot.id in coordinates:
                        c1 = coordinates[prev_location]
                        c2 = coordinates[depot.id]
                        dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
                        duration = estimate_travel_time(dist)
                    else:
                        duration = DEFAULT_TRAVEL_FALLBACK_MINUTES

                    total_duration += duration
                    route_details.append(RouteStep(
                        location1=prev_location,
                        location2=depot.id,
                        duration=round(duration, 2),
                        distance=0.0
                    ))

                    routes.append(VehicleRoute(
                        vehicle_id=f"Araç {len(routes) + 1} (PyVRP-Alt)",
                        route_details=route_details,
                        total_duration_minutes=round(total_duration, 2),
                        total_distance_km=0.0,
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

        except Exception as e:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message=f"PyVRP alternative failed: {str(e)}",
                execution_time_seconds=time.time() - start_time
            )
