"""
GA-Split for a heterogeneous fleet (``ga_split_hf``).

Operational strategy only (design ``docs/designs/HETEROGENEOUS_FLEET_DESIGN.md``
section 3.1 / 6): a GA over giant tours whose split is the typed decoder. The
request declares ``vehicle_types``; ``minimize_type`` is the type whose route
count is minimised and at most one type may carry a per-call ``max_routes``
quota (the large minibus of a wave menu). Every returned route carries its
``vehicle_type`` and the response carries ``fleet_mix``.

It is not part of the academic catalog, has no evaluation-budget protocol
(native termination) and is never a ``/compare`` default. ``ga_split`` itself is
untouched.
"""

import random
import time
from typing import Dict, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.hybrid_base_strategy import HybridSplitBaseStrategy
from utils.data_loader import DataLoader
from uniride_core.adapters.demand_builder import (
    build_student_demands,
    build_student_map,
    student_occurrence_keys,
)
from uniride_core.algorithms.ga_split_typed_engine import solve_ga_split_typed
from uniride_core.algorithms.typed_split_decoder import VehicleType
from strategies.seed_utils import resolve_seed, make_rng


class GASplitHFStrategy(HybridSplitBaseStrategy):
    """Typed (heterogeneous fleet) GA-Split. Requires ``request.vehicle_types``."""

    DEFAULT_CONFIG = {
        "population_size": 50,
        "max_iterations": 100,
        "crossover_rate": 0.85,
        "mutation_rate": 0.20,
        "elite_count": 3,
        "tournament_size": 4,
        "max_no_improvement": 25,
        "seed": None,
        "local_search_type": "hybrid",
        "local_search_interval": 10,
        "diversify_threshold": 30,
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = resolve_seed(self.config)

    @property
    def name(self) -> str:
        return "ga_split_hf"

    @property
    def display_name(self) -> str:
        return "GA-Split (heterogeneous fleet)"

    @property
    def description(self) -> str:
        return (
            "Typed GA giant tour + typed split with a per-call quota on one "
            "vehicle type. Requires vehicle_types; operational use only."
        )

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        start_time = time.time()
        if request.use_time_windows:
            raise ValueError("ga_split_hf does not support use_time_windows")

        students = request.students
        depot = request.depot
        direction = request.direction
        if not request.vehicle_types:
            # fail closed: never invent a fleet (the API schema also returns 422)
            raise ValueError("ga_split_hf requires vehicle_types")
        specs = list(request.vehicle_types)
        minimize_type = request.minimize_type or specs[0].type_id
        type_ids = [spec.type_id for spec in specs]

        if not students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time,
                direction=direction,
                time_windows_used=False,
                fleet_mix={t: 0 for t in type_ids},
            )

        types = [
            VehicleType(
                id=spec.type_id,
                sw_capacity=spec.sw_capacity,
                so_capacity=spec.so_capacity,
                max_tour_duration=float(
                    spec.max_travel_time if spec.max_travel_time is not None else request.max_travel_time
                ),
                max_ride_time=(
                    float(spec.max_ride_time) if spec.max_ride_time is not None
                    else (float(request.max_ride_time) if request.max_ride_time is not None else None)
                ),
            )
            for spec in specs
        ]
        quota_specs = [spec for spec in specs if spec.max_routes is not None]
        quota_type = quota_specs[0].type_id if quota_specs else None
        quota = quota_specs[0].max_routes if quota_specs else None

        effective_config = dict(self.config)
        if request.ga_config:
            effective_config = {**self.config, **request.ga_config}
            rng = make_rng(effective_config, default=self.seed)
        else:
            rng = random.Random(self.seed)

        data_loader = DataLoader.get_instance()
        occurrence_keys = student_occurrence_keys(students)
        node_keys = [depot.id] + occurrence_keys
        physical_ids = [depot.id] + [s.location_code for s in students]
        physical_coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            physical_coordinates[s.location_code] = s.coordinates or {"lat": 0, "lng": 0}
        raw_matrix = data_loader.get_submatrix(physical_ids, coordinates=physical_coordinates)

        time_matrix = {}
        for i, from_loc in enumerate(node_keys):
            time_matrix[from_loc] = {}
            for j, to_loc in enumerate(node_keys):
                time_matrix[from_loc][to_loc] = raw_matrix[i][j]

        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s, key in zip(students, occurrence_keys):
            coordinates[key] = s.coordinates or {"lat": 0, "lng": 0}

        distance_matrix = self._build_distance_matrix(node_keys, time_matrix, coordinates)
        demands = build_student_demands(students)
        student_map = build_student_map(students)

        solution = solve_ga_split_typed(
            waypoints=occurrence_keys,
            depot=depot.id,
            distance_matrix=distance_matrix,
            demands=demands,
            types=types,
            config=effective_config,
            rng=rng,
            minimize_type=minimize_type,
            quota_type=quota_type,
            quota=quota,
            direction=direction,
            is_asymmetric=request.is_asymmetric,
        )
        final = solution.final_result
        if not final.feasible:
            # No singleton fallback: an infeasible typed split is reported as such.
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=round(time.time() - start_time, 4),
                direction=direction,
                time_windows_used=False,
                error_message="no feasible typed split for the declared vehicle types",
                fleet_mix={t: 0 for t in type_ids},
            )

        routes = []
        for route_idx, (route_locations, type_id) in enumerate(zip(final.routes, final.type_ids)):
            route_steps = []
            total_duration = 0
            sw_count = 0
            so_count = 0
            route_student_ids = []
            prev = depot.id
            for loc in route_locations:
                duration = self._get_duration(prev, loc, time_matrix, coordinates)
                total_duration += duration
                route_steps.append(RouteStep(
                    location1=prev, location2=loc, duration=round(duration, 2), distance=0.0
                ))
                if loc in student_map:
                    s = student_map[loc]
                    route_student_ids.append(s.id)
                    if s.disability_type == "Sw":
                        sw_count += 1
                    else:
                        so_count += 1
                prev = loc
            duration = self._get_duration(prev, depot.id, time_matrix, coordinates)
            total_duration += duration
            route_steps.append(RouteStep(
                location1=prev, location2=depot.id, duration=round(duration, 2), distance=0.0
            ))
            routes.append(VehicleRoute(
                vehicle_id=f"{type_id} {route_idx + 1} (GA-Split-HF)",
                route_details=route_steps,
                total_duration_minutes=round(total_duration, 2),
                total_distance_km=0.0,
                sw_count=sw_count,
                so_count=so_count,
                student_ids=route_student_ids,
                vehicle_type=type_id,
            ))

        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=round(time.time() - start_time, 4),
            direction=direction,
            time_windows_used=False,
            fleet_mix={t: final.routes_by_type.get(t, 0) for t in type_ids},
        )
