"""
TSP Problem definition, TSPLIB file parsing, and distance computation.

Provides:
    - TSPProblem: Core dataclass holding problem instance data
    - load_tsplib(): Parse individual .tsp files
    - load_tsplib_directory(): Batch-load a folder of .tsp files with auto optimal detection
    - compute_distance_matrix(): Build an n x n Euclidean distance matrix via numpy broadcasting
"""

import math
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

@dataclass
class TSPProblem:
    """Represents a single TSP problem instance.

    Attributes:
        name: Problem identifier (e.g. ``"berlin52"``).
        dimension: Number of cities / nodes.
        optimal_value: Known optimal tour length (0 if unknown).
        coordinates: List of ``(x, y)`` tuples, 0-indexed by position.
        edge_weight_type: Distance metric (``"EUC_2D"``, ``"CEIL_2D"``, ``"GEO"``).
        category: Auto-detected size bucket (``"small"`` / ``"medium"`` / ``"large"``).
    """

    name: str = ""
    dimension: int = 0
    optimal_value: int = 0
    coordinates: List[Tuple[float, float]] = field(default_factory=list)
    edge_weight_type: str = "EUC_2D"
    category: str = ""

    def __post_init__(self):
        if not self.category:
            if self.dimension <= 100:
                self.category = "small"
            elif self.dimension <= 500:
                self.category = "medium"
            else:
                self.category = "large"


# ---------------------------------------------------------------------------
# Distance functions
# ---------------------------------------------------------------------------

def euc_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Standard Euclidean L2 distance."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def ceil_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """Ceiling of Euclidean distance (TSPLIB CEIL_2D)."""
    return int(math.ceil(euc_2d_distance(p1, p2)))


def _geo_to_radians(coord: float) -> float:
    """Convert TSPLIB GEO coordinate (degrees/minutes) to radians."""
    deg = int(coord)
    minutes = coord - deg
    return math.pi * (deg + 5.0 * minutes / 3.0) / 180.0


def geo_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """TSPLIB GEO pseudo-Earth-sphere distance."""
    R = 6378.388
    lat1 = _geo_to_radians(p1[1])
    lon1 = _geo_to_radians(p1[0])
    lat2 = _geo_to_radians(p2[1])
    lon2 = _geo_to_radians(p2[0])

    q1 = math.cos(lon1 - lon2)
    q2 = math.cos(lat1 - lat2)
    q3 = math.cos(lat1 + lat2)
    return int(R * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)


def _distance_fn(edge_weight_type: str):
    """Return the appropriate distance function for the given weight type."""
    if edge_weight_type == "CEIL_2D":
        return ceil_2d_distance
    if edge_weight_type == "GEO":
        return geo_distance
    # Default: EUC_2D
    return euc_2d_distance


# ---------------------------------------------------------------------------
# Distance matrix
# ---------------------------------------------------------------------------

def compute_distance_matrix(problem: TSPProblem) -> np.ndarray:
    """Build an ``n x n`` distance matrix using numpy broadcasting.

    For ``EUC_2D`` a fully vectorised numpy computation is used.
    For other weight types a Python loop falls back to the correct
    distance function.

    Returns:
        ``np.ndarray`` of shape ``(n, n)`` with dtype ``float64``.
    """
    coords = np.asarray(problem.coordinates, dtype=np.float64)
    n = len(coords)

    if problem.edge_weight_type == "EUC_2D":
        # Fast vectorised Euclidean distance via broadcasting
        diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
        return np.sqrt((diff ** 2).sum(axis=2)).astype(np.float64)

    # Fallback for CEIL_2D / GEO
    dist_fn = _distance_fn(problem.edge_weight_type)
    mat = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        xi, yi = problem.coordinates[i]
        for j in range(i + 1, n):
            d = float(dist_fn((xi, yi), problem.coordinates[j]))
            mat[i, j] = d
            mat[j, i] = d
    return mat


# ---------------------------------------------------------------------------
# Tour length
# ---------------------------------------------------------------------------

def compute_tour_length(tour: List[int], dist_matrix: np.ndarray) -> float:
    """Calculate total tour length (including return to start).

    Args:
        tour: 0-based node indices.
        dist_matrix: Precomputed ``n x n`` distance matrix.

    Returns:
        Total tour length as ``float``.
    """
    n = len(tour)
    if n < 2:
        return 0.0
    total = 0.0
    for i in range(n - 1):
        total += dist_matrix[tour[i], tour[i + 1]]
    total += dist_matrix[tour[n - 1], tour[0]]
    return float(total)


# ---------------------------------------------------------------------------
# .opt.tour parsing
# ---------------------------------------------------------------------------

def parse_opt_tour(filepath: str) -> List[int]:
    """Parse a TSPLIB ``.opt.tour`` file and return the node list (1-based).

    Returns a list of integer node indices (1-based as stored in the file).
    The list is terminated by ``-1`` which is *not* included in the output.
    """
    tour: List[int] = []
    in_section = False
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line == "EOF":
                continue
            if line.startswith("TOUR_SECTION"):
                in_section = True
                continue
            if in_section:
                try:
                    val = int(line)
                    if val == -1:
                        break
                    tour.append(val)
                except ValueError:
                    pass
    return tour


# ---------------------------------------------------------------------------
# TSPLIB .tsp parser
# ---------------------------------------------------------------------------

def load_tsplib(filepath: str, optimal_value: int = 0) -> TSPProblem:
    """Parse a TSPLIB ``.tsp`` file and return a :class:`TSPProblem`.

    Handles ``NAME``, ``DIMENSION``, ``EDGE_WEIGHT_TYPE``, and
    ``NODE_COORD_SECTION`` fields.  Supports ``EUC_2D``, ``CEIL_2D``,
    and ``GEO`` weight types.

    Args:
        filepath: Path to the ``.tsp`` file.
        optimal_value: Known optimal tour length (default 0 = unknown).

    Returns:
        A populated :class:`TSPProblem` instance.
    """
    name = os.path.basename(filepath).replace(".tsp", "")
    dimension = 0
    edge_weight_type = "EUC_2D"
    coordinates: List[Tuple[float, float]] = []

    in_node_section = False

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line == "EOF":
                continue

            if line.startswith("NAME"):
                name = line.split(":")[-1].strip()
            elif line.startswith("DIMENSION"):
                dimension = int(line.split(":")[-1].strip())
            elif line.startswith("EDGE_WEIGHT_TYPE"):
                edge_weight_type = line.split(":")[-1].strip()
            elif line.startswith("NODE_COORD_SECTION"):
                in_node_section = True
                continue

            if in_node_section:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        coordinates.append((x, y))
                    except ValueError:
                        pass

    return TSPProblem(
        name=name,
        dimension=dimension,
        optimal_value=optimal_value,
        coordinates=coordinates,
        edge_weight_type=edge_weight_type,
    )


# ---------------------------------------------------------------------------
# Directory loader
# ---------------------------------------------------------------------------

def load_tsplib_directory(directory: str) -> List[TSPProblem]:
    """Load every ``.tsp`` file found in *directory*.

    For each problem, if a companion ``<name>.opt.tour`` file exists it is
    parsed and the optimal tour length is computed automatically via
    :func:`compute_tour_length`.

    Args:
        directory: Path to a folder containing ``.tsp`` (and optionally
            ``.opt.tour``) files.

    Returns:
        List of :class:`TSPProblem` instances.
    """
    problems: List[TSPProblem] = []

    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".tsp"):
            continue

        filepath = os.path.join(directory, filename)
        problem = load_tsplib(filepath)

        # Try to auto-detect optimal from .opt.tour
        base = filepath.replace(".tsp", "")
        opt_tour_path = base + ".opt.tour"
        if os.path.exists(opt_tour_path):
            tour_nodes = parse_opt_tour(opt_tour_path)  # 1-based
            if tour_nodes:
                # Convert 1-based tour to 0-based for our distance matrix
                tour_0based = [n - 1 for n in tour_nodes]
                dist_mat = compute_distance_matrix(problem)
                opt_length = compute_tour_length(tour_0based, dist_mat)
                problem.optimal_value = int(opt_length)

        problems.append(problem)

    return problems
