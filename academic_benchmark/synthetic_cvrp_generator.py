"""Synthetic CVRP/CVRPTW generators backed by the unified academic DB.

These helpers turn existing TSPLIB-style coordinate problems into routing
instances with demands, capacities, travel-time matrices, and time windows.
They are intended for controlled academic experiments where plain TSP data is
useful geometrically but does not carry UniRide-style constraints.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

from academic_benchmark.tsplib_manager import (
    DB_PATH,
    get_all_problems,
    load_routing_problem,
    store_routing_problem,
)
from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem

Coordinate = Tuple[float, float]


def generate_cvrp_from_coordinates(
    name: str,
    coordinates: Sequence[Coordinate],
    *,
    capacity: Optional[int] = None,
    demand_range: Tuple[int, int] = (1, 10),
    seed: int = 42,
    edge_weight_type: str = "EUC_2D",
) -> RoutingProblem:
    """Create a deterministic scalar-capacity CVRP instance from coordinates."""
    coords = _validate_coordinates(coordinates)
    demands = _generate_scalar_demands(len(coords), demand_range, seed)
    cap = int(capacity) if capacity is not None else _default_capacity(demands)
    matrix = MatrixBuilder.from_coordinates(coords, edge_weight_type)
    return RoutingProblem(
        name=name,
        problem_type="cvrp",
        matrix=CostMatrix(matrix, kind="distance", labels=[str(i) for i in range(len(coords))]),
        constraints=ConstraintProfile(
            demands=[[demand] for demand in demands],
            capacities=[cap],
            depot_index=0,
        ),
        coordinates=coords,
        category=_category(len(coords)),
        source="synthetic_cvrp",
        metadata={
            "edge_weight_type": edge_weight_type,
            "synthetic_seed": seed,
            "demand_range": list(demand_range),
        },
    )


def generate_cvrp_from_tsplib(
    problem_name: str,
    *,
    db_path: str = DB_PATH,
    capacity: Optional[int] = None,
    demand_range: Tuple[int, int] = (1, 10),
    seed: int = 42,
    store: bool = False,
) -> RoutingProblem:
    """Create CVRP from a stored TSPLIB coordinate problem."""
    base = _load_coordinate_problem(problem_name, db_path)
    problem = generate_cvrp_from_coordinates(
        f"{base.name}-synthetic-cvrp-s{seed}",
        base.coordinates or [],
        capacity=capacity,
        demand_range=demand_range,
        seed=seed,
        edge_weight_type=str(base.metadata.get("edge_weight_type", "EUC_2D")),
    )
    problem.metadata["base_problem"] = base.name
    if store:
        store_routing_problem(problem, db_path=db_path)
    return problem


def generate_cvrptw_from_tsplib(
    problem_name: str,
    *,
    db_path: str = DB_PATH,
    capacity: Optional[int] = None,
    demand_range: Tuple[int, int] = (1, 10),
    speed_kmh: float = 40.0,
    time_window_width: int = 60,
    service_time: int = 5,
    horizon: Tuple[int, int] = (0, 480),
    max_route_duration: Optional[float] = None,
    seed: int = 42,
    store: bool = False,
) -> RoutingProblem:
    """Create CVRPTW from a stored TSPLIB problem with synthetic travel times."""
    base = _load_coordinate_problem(problem_name, db_path)
    coords = _validate_coordinates(base.coordinates or [])
    edge_weight_type = str(base.metadata.get("edge_weight_type", "EUC_2D"))
    demands = _generate_scalar_demands(len(coords), demand_range, seed)
    cap = int(capacity) if capacity is not None else _default_capacity(demands)
    matrix = MatrixBuilder.tsplib_to_travel_time(
        coords,
        speed_kmh=speed_kmh,
        noise_pct=0.10,
        seed=seed,
        edge_weight_type=edge_weight_type,
    )
    time_windows = _generate_time_windows(
        len(coords),
        time_window_width=time_window_width,
        horizon=horizon,
        seed=seed,
    )
    service_times = [0] + [int(service_time)] * (len(coords) - 1)
    problem = RoutingProblem(
        name=f"{base.name}-synthetic-cvrptw-s{seed}",
        problem_type="cvrptw",
        matrix=CostMatrix(matrix, kind="synthetic_travel_time", labels=[str(i) for i in range(len(coords))]),
        constraints=ConstraintProfile(
            demands=[[demand] for demand in demands],
            capacities=[cap],
            time_windows=time_windows,
            service_times=service_times,
            depot_index=0,
            max_route_duration=max_route_duration,
            direction="dropoff",
        ),
        coordinates=coords,
        category=_category(len(coords)),
        source="synthetic_cvrptw",
        metadata={
            "base_problem": base.name,
            "edge_weight_type": edge_weight_type,
            "synthetic_seed": seed,
            "demand_range": list(demand_range),
            "speed_kmh": speed_kmh,
            "time_window_width": time_window_width,
        },
    )
    if store:
        store_routing_problem(problem, db_path=db_path)
    return problem


def batch_generate_cvrp(
    problem_names: Optional[Iterable[str]] = None,
    *,
    db_path: str = DB_PATH,
    max_dim: int = 500,
    seed: int = 42,
    include_cvrptw: bool = False,
    store: bool = True,
) -> List[RoutingProblem]:
    """Generate synthetic routing instances for eligible TSPLIB problems."""
    names = list(problem_names) if problem_names is not None else [
        row["name"]
        for row in get_all_problems(db_path=db_path, max_dim=max_dim, exclude_explicit=True)
        if str(row.get("problem_type", "TSP")).upper() == "TSP"
    ]
    generated: List[RoutingProblem] = []
    for name in names:
        cvrp = generate_cvrp_from_tsplib(name, db_path=db_path, seed=seed, store=store)
        generated.append(cvrp)
        if include_cvrptw:
            cvrptw = generate_cvrptw_from_tsplib(name, db_path=db_path, seed=seed, store=store)
            generated.append(cvrptw)
    return generated


def _load_coordinate_problem(problem_name: str, db_path: str) -> RoutingProblem:
    problem = load_routing_problem(problem_name, db_path=db_path)
    if problem is None:
        raise KeyError(f"Academic problem not found: {problem_name}")
    if not problem.coordinates:
        raise ValueError(f"Problem {problem_name} has no coordinates for synthetic generation")
    return problem


def _validate_coordinates(coordinates: Sequence[Coordinate]) -> List[Coordinate]:
    coords = [(float(x), float(y)) for x, y in coordinates]
    if len(coords) < 2:
        raise ValueError("At least depot plus one customer coordinate is required")
    return coords


def _generate_scalar_demands(
    dimension: int,
    demand_range: Tuple[int, int],
    seed: int,
) -> List[int]:
    low, high = demand_range
    if low < 0 or high < low:
        raise ValueError("demand_range must be non-negative and ordered")
    rng = np.random.default_rng(seed)
    demands = [0]
    if dimension > 1:
        demands.extend(int(value) for value in rng.integers(low, high + 1, size=dimension - 1))
    return demands


def _default_capacity(demands: Sequence[int]) -> int:
    total = sum(demands)
    customers = max(1, len(demands) - 1)
    estimated_vehicles = max(2, int(round(math.sqrt(customers))))
    return max(max(demands, default=1), int(math.ceil(total / estimated_vehicles)))


def _generate_time_windows(
    dimension: int,
    *,
    time_window_width: int,
    horizon: Tuple[int, int],
    seed: int,
) -> List[Tuple[int, int]]:
    if time_window_width <= 0:
        raise ValueError("time_window_width must be positive")
    start, end = horizon
    if end <= start:
        raise ValueError("horizon end must be greater than start")
    latest_ready = max(start, end - time_window_width)
    rng = np.random.default_rng(seed + 17)
    windows = [(start, end + time_window_width)]
    for _ in range(1, dimension):
        ready = int(rng.integers(start, latest_ready + 1))
        windows.append((ready, ready + time_window_width))
    return windows


def _category(n: int) -> str:
    return "small" if n <= 100 else ("medium" if n <= 500 else "large")


__all__ = [
    "batch_generate_cvrp",
    "generate_cvrp_from_coordinates",
    "generate_cvrp_from_tsplib",
    "generate_cvrptw_from_tsplib",
]
