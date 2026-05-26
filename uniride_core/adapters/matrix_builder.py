"""Matrix construction helpers for core-first optimization.

All engines consume explicit matrices. This module is the single place where
coordinates, TSPLIB edge types, academic instances, and UniRide travel-time
matrices are normalized into numpy arrays.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

from uniride_core.algorithms.distance import tsplib_distance_by_type
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem


Coordinate = Tuple[float, float]


class MatrixBuilder:
    """Build normalized numpy matrices for TSP/ATSP/CVRP/CVRPTW workflows."""

    @staticmethod
    def from_coordinates(
        coords: Sequence[Coordinate],
        edge_weight_type: str = "EUC_2D",
        dtype: np.dtype | str = np.int32,
    ) -> np.ndarray:
        n = len(coords)
        dm = np.zeros((n, n), dtype=dtype)
        for i in range(n):
            for j in range(n):
                if i != j:
                    dm[i, j] = tsplib_distance_by_type(edge_weight_type, coords[i], coords[j])
        return dm

    @staticmethod
    def from_explicit_matrix(matrix: Sequence[Sequence[float]]) -> np.ndarray:
        return MatrixBuilder._validate_square(np.asarray(matrix, dtype=np.float64))

    @staticmethod
    def from_travel_times(time_matrix: Sequence[Sequence[float]]) -> np.ndarray:
        return MatrixBuilder._validate_square(np.asarray(time_matrix, dtype=np.float64))

    @staticmethod
    def from_problem_instance(problem) -> np.ndarray:
        if getattr(problem, "time_matrix", None) is not None:
            return MatrixBuilder.from_travel_times(problem.time_matrix)
        if getattr(problem, "dist_matrix", None) is not None:
            return MatrixBuilder.from_explicit_matrix(problem.dist_matrix)
        coords = getattr(problem, "coordinates", None)
        if coords:
            return MatrixBuilder.from_coordinates(
                coords,
                getattr(problem, "edge_weight_type", "EUC_2D"),
            )
        raise ValueError(f"Problem {getattr(problem, 'name', '<unknown>')} has no matrix or coordinates")

    @staticmethod
    def from_tsplib_text(text: str, name: str = "tsplib") -> RoutingProblem:
        """Parse TSPLIB TSP text into the unified problem shape."""
        from uniride_core.algorithms.tsplib_parser import parse_tsplib_text

        data = parse_tsplib_text(text, name)
        if not data:
            raise ValueError("TSPLIB instance is not a supported coordinate TSP")

        coords = list(data["coordinates"])
        edge_weight_type = data.get("edge_weight_type", "EUC_2D")
        matrix = MatrixBuilder.from_coordinates(coords, edge_weight_type)
        labels = [str(i + 1) for i in range(len(coords))]
        return RoutingProblem(
            name=data.get("name", name),
            problem_type=str(data.get("problem_type", "TSP")).lower(),
            matrix=CostMatrix(matrix, kind="distance", labels=labels),
            constraints=ConstraintProfile(depot_index=0),
            coordinates=coords,
            source="tsplib",
            metadata={
                "edge_weight_type": edge_weight_type,
                "dimension": data.get("dimension", len(coords)),
            },
        )

    @staticmethod
    def from_atsp_text(text: str, name: str = "atsp") -> RoutingProblem:
        """Parse TSPLIB ATSP explicit-matrix text into the unified problem shape."""
        from uniride_core.algorithms.tsplib_parser import parse_atsp_text

        data = parse_atsp_text(text, name)
        if not data:
            raise ValueError("ATSP instance is not a supported explicit FULL_MATRIX problem")

        matrix = MatrixBuilder.from_explicit_matrix(data["explicit_matrix"])
        labels = [str(i + 1) for i in range(matrix.shape[0])]
        return RoutingProblem(
            name=data.get("name", name),
            problem_type=str(data.get("problem_type", "ATSP")).lower(),
            matrix=CostMatrix(matrix, kind="distance", is_asymmetric=True, labels=labels),
            constraints=ConstraintProfile(depot_index=0),
            source="tsplib",
            metadata={
                "edge_weight_type": data.get("edge_weight_type", "EXPLICIT"),
                "dimension": data.get("dimension", matrix.shape[0]),
            },
        )

    @staticmethod
    def to_problem_instance(problem: RoutingProblem):
        """Convert a unified routing problem into the legacy benchmark model.

        This keeps application and older academic runners thin while the core
        package owns parsing, matrices, constraints, and problem typing.
        """
        from uniride_core.models import ProblemInstance

        constraints = problem.constraints
        demands = constraints.demands
        scalar_demands = None
        if demands is not None:
            scalar_demands = [
                int(row[0]) if isinstance(row, (list, tuple)) and row else int(row)
                for row in demands
            ]

        capacities = list(constraints.capacities) if constraints.capacities is not None else None
        matrix_values = problem.matrix.values
        is_travel_time = problem.matrix.kind in {"travel_time", "synthetic_travel_time"}
        return ProblemInstance(
            name=problem.name,
            dimension=problem.dimension,
            coordinates=list(problem.coordinates or []),
            optimal=problem.optimal,
            category=problem.category,
            source=problem.source,
            problem_type=problem.problem_type,
            is_time_matrix=is_travel_time,
            time_matrix=matrix_values.tolist() if is_travel_time and hasattr(matrix_values, "tolist") else matrix_values if is_travel_time else None,
            dist_matrix=matrix_values.tolist() if not is_travel_time and hasattr(matrix_values, "tolist") else matrix_values if not is_travel_time else None,
            edge_weight_type=str(problem.metadata.get("edge_weight_type", "EUC_2D")),
            capacity=capacities[0] if capacities else None,
            capacities=capacities,
            demands=scalar_demands,
            service_times=list(constraints.service_times) if constraints.service_times is not None else None,
            num_vehicles=int(problem.metadata["vehicles"]) if "vehicles" in problem.metadata else None,
            max_route_duration=constraints.max_route_duration,
            matrix_kind=problem.matrix.kind,
            direction=constraints.direction,
            time_windows=list(constraints.time_windows) if constraints.time_windows is not None else None,
            depot_index=constraints.depot_index,
        )

    @staticmethod
    def to_routing_problem(problem) -> RoutingProblem:
        """Convert a legacy ProblemInstance-like object into RoutingProblem."""
        matrix = MatrixBuilder.from_problem_instance(problem)
        problem_type = str(getattr(problem, "problem_type", "tsp") or "tsp").lower()
        demands = getattr(problem, "demands", None)
        demand_vectors = None
        if demands is not None:
            demand_vectors = [
                list(item) if isinstance(item, (list, tuple)) else [int(item)]
                for item in demands
            ]
        capacities = getattr(problem, "capacities", None)
        capacity = getattr(problem, "capacity", None)
        if capacities is None and capacity is not None:
            capacities = [capacity]
        matrix_kind = getattr(problem, "matrix_kind", None)
        if matrix_kind is None:
            matrix_kind = "travel_time" if getattr(problem, "is_time_matrix", False) else "distance"
        return RoutingProblem(
            name=getattr(problem, "name", "problem"),
            problem_type=problem_type,
            matrix=CostMatrix(
                matrix,
                kind=matrix_kind,
                is_asymmetric=problem_type == "atsp",
            ),
            constraints=ConstraintProfile(
                demands=demand_vectors,
                capacities=list(capacities) if capacities is not None else None,
                time_windows=getattr(problem, "time_windows", None),
                service_times=getattr(problem, "service_times", None),
                depot_index=getattr(problem, "depot_index", 0),
                max_route_duration=getattr(problem, "max_route_duration", None),
                direction=getattr(problem, "direction", "pickup"),
            ),
            coordinates=list(getattr(problem, "coordinates", []) or []),
            optimal=getattr(problem, "optimal", None),
            category=getattr(problem, "category", "small"),
            source=getattr(problem, "source", "legacy"),
            metadata={"edge_weight_type": getattr(problem, "edge_weight_type", "EUC_2D")},
        )

    @staticmethod
    def tsplib_to_travel_time(
        coords: Sequence[Coordinate],
        speed_kmh: float = 40.0,
        noise_pct: float = 0.10,
        seed: int = 42,
        edge_weight_type: str = "EUC_2D",
    ) -> np.ndarray:
        """Create deterministic synthetic travel times from TSPLIB coordinates.

        TSPLIB coordinate units are treated as distance units. The conversion is
        intentionally synthetic and is only for controlled benchmark scenarios.
        """
        if speed_kmh <= 0:
            raise ValueError("speed_kmh must be positive")
        base = MatrixBuilder.from_coordinates(coords, edge_weight_type, dtype=np.float64)
        minutes = (base / speed_kmh) * 60.0
        if noise_pct > 0:
            rng = np.random.default_rng(seed)
            noise = rng.uniform(1.0 - noise_pct, 1.0 + noise_pct, size=minutes.shape)
            minutes = minutes * noise
        np.fill_diagonal(minutes, 0.0)
        return minutes.astype(np.float64, copy=False)

    @staticmethod
    def from_cvrplib_text(text: str, name: str = "cvrplib") -> RoutingProblem:
        """Parse a small CVRPLIB-style instance into the unified problem shape."""
        metadata: Dict[str, str] = {}
        coords: Dict[int, Coordinate] = {}
        demands: Dict[int, int] = {}
        depot_ids: List[int] = []
        section: str | None = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            upper = line.upper()
            if upper in {"NODE_COORD_SECTION", "DEMAND_SECTION", "DEPOT_SECTION"}:
                section = upper
                continue
            if upper == "EOF":
                break
            if ":" in line and section is None:
                key, value = line.split(":", 1)
                metadata[key.strip().upper()] = value.strip()
                continue
            if section == "NODE_COORD_SECTION":
                parts = line.split()
                if len(parts) >= 3:
                    node_id = int(parts[0])
                    coords[node_id] = (float(parts[1]), float(parts[2]))
            elif section == "DEMAND_SECTION":
                parts = line.split()
                if len(parts) >= 2:
                    demands[int(parts[0])] = int(float(parts[1]))
            elif section == "DEPOT_SECTION":
                depot_id = int(line.split()[0])
                if depot_id == -1:
                    section = None
                else:
                    depot_ids.append(depot_id)

        if not coords:
            raise ValueError("CVRPLIB instance has no NODE_COORD_SECTION")

        ordered_ids = sorted(coords)
        ordered_coords = [coords[node_id] for node_id in ordered_ids]
        id_to_index = {node_id: idx for idx, node_id in enumerate(ordered_ids)}
        depot_index = id_to_index.get(depot_ids[0], 0) if depot_ids else 0
        capacity = int(float(metadata.get("CAPACITY", "0")))
        demand_vectors = [[int(demands.get(node_id, 0))] for node_id in ordered_ids]
        matrix = MatrixBuilder.from_coordinates(ordered_coords, metadata.get("EDGE_WEIGHT_TYPE", "EUC_2D"))

        return RoutingProblem(
            name=metadata.get("NAME", name),
            problem_type="cvrp",
            matrix=CostMatrix(matrix, kind="distance", labels=[str(node_id) for node_id in ordered_ids]),
            constraints=ConstraintProfile(
                demands=demand_vectors,
                capacities=[capacity] if capacity else None,
                depot_index=depot_index,
            ),
            coordinates=ordered_coords,
            source="cvrplib",
            metadata=metadata,
        )

    @staticmethod
    def from_solomon_text(text: str, name: str = "solomon") -> RoutingProblem:
        """Parse a Solomon CVRPTW instance into the unified problem shape."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        vehicle_count: int | None = None
        capacity: int | None = None
        customers: List[Tuple[int, Coordinate, int, Tuple[int, int], int]] = []

        for idx, line in enumerate(lines):
            if line.upper().startswith("NUMBER") and idx + 1 < len(lines):
                parts = lines[idx + 1].split()
                if len(parts) >= 2:
                    vehicle_count = int(parts[0])
                    capacity = int(float(parts[1]))
            parts = line.split()
            if len(parts) >= 7 and parts[0].lstrip("-").isdigit():
                customer_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                demand = int(float(parts[3]))
                ready = int(float(parts[4]))
                due = int(float(parts[5]))
                service = int(float(parts[6]))
                customers.append((customer_id, (x, y), demand, (ready, due), service))

        if not customers:
            raise ValueError("Solomon instance has no customer rows")

        customers.sort(key=lambda row: row[0])
        coords = [row[1] for row in customers]
        matrix = MatrixBuilder.from_coordinates(coords, "EUC_2D")

        return RoutingProblem(
            name=lines[0] if lines else name,
            problem_type="cvrptw",
            matrix=CostMatrix(matrix, kind="distance", labels=[str(row[0]) for row in customers]),
            constraints=ConstraintProfile(
                demands=[[row[2]] for row in customers],
                capacities=[capacity] if capacity is not None else None,
                time_windows=[row[3] for row in customers],
                service_times=[row[4] for row in customers],
                depot_index=0,
            ),
            coordinates=coords,
            source="solomon",
            metadata={"vehicles": vehicle_count} if vehicle_count is not None else {},
        )

    @staticmethod
    def _validate_square(matrix: np.ndarray) -> np.ndarray:
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError(f"Matrix must be square, got shape={matrix.shape}")
        return matrix


__all__ = ["MatrixBuilder"]
