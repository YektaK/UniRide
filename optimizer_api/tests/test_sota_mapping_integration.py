"""
Integration test: SOTA strategy location-code ↔ integer-index mapping.

Validates that the bridge between string-location-coded distance lookups
and integer-indexed numpy distance matrices (used by SOTA solvers) is
consistent and produces correct results.

Key test scenarios:
1. Location-code to integer-index round-trip consistency
2. Distance matrix consistency between dict and numpy representations
3. Full strategy execution: string-location tour in → SOTA solver → string-location tour out
"""
import math
import numpy as np
from typing import Dict, List

from models.schemas import OptimizationRequest, OptimizationResponse, StudentNode, LocationNode
from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig


TRIVIAL_STUDENTS = [
    StudentNode(id="s1", name="A", location_code="loc_a",
                coordinates={"lat": 0.0, "lng": 0.0}, disability_type="So"),
    StudentNode(id="s2", name="B", location_code="loc_b",
                coordinates={"lat": 0.0, "lng": 10.0}, disability_type="So"),
    StudentNode(id="s3", name="C", location_code="loc_c",
                coordinates={"lat": 10.0, "lng": 10.0}, disability_type="So"),
    StudentNode(id="s4", name="D", location_code="loc_d",
                coordinates={"lat": 10.0, "lng": 0.0}, disability_type="So"),
]

TRIVIAL_DEPOT = LocationNode(id="depot", lat=5.0, lng=5.0, type="So")


def euclidean_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def test_mapping_round_trip_consistency():
    """Verify that location_code → integer index → location_code is a bijection."""
    student_ids = [s.location_code for s in TRIVIAL_STUDENTS]
    n = len(student_ids)

    # Forward: index → location_code
    assert len(student_ids) == n
    assert len(set(student_ids)) == n, "Location codes must be unique"

    # Reverse: location_code → index
    code_to_idx = {code: i for i, code in enumerate(student_ids)}
    for s in TRIVIAL_STUDENTS:
        assert s.location_code in code_to_idx

    # Round-trip: index → code → index
    for i in range(n):
        code = student_ids[i]
        assert code_to_idx[code] == i

    # Indices cover all locations exactly once
    assert set(code_to_idx.values()) == set(range(n))


def test_distance_matrix_equivalence():
    """Verify dict-based and int-indexed distance matrices produce identical values."""
    student_ids = [s.location_code for s in TRIVIAL_STUDENTS]
    n = len(student_ids)

    coordinates: Dict[str, Dict[str, float]] = {
        depot_id: {"lat": TRIVIAL_DEPOT.lat, "lng": TRIVIAL_DEPOT.lng}
        for depot_id in [TRIVIAL_DEPOT.id]
    }
    for s in TRIVIAL_STUDENTS:
        coordinates[s.location_code] = s.coordinates or {"lat": 0, "lng": 0}

    # Dict-based distance (as in ebso_strategy._dist helper)
    def _dict_dist(loc1: str, loc2: str) -> float:
        c1 = coordinates.get(loc1, {})
        c2 = coordinates.get(loc2, {})
        return round(
            euclidean_2d(
                c1.get("lat", 0), c1.get("lng", 0),
                c2.get("lat", 0), c2.get("lng", 0),
            ), 2
        )

    idx_to_code = {i: student_ids[i] for i in range(n)}

    # Integer-indexed distance (as in SOTA solver path)
    int_dm: Dict[int, Dict[int, int]] = {}
    for i in range(n):
        int_dm[i] = {}
        for j in range(n):
            if i != j:
                d = _dict_dist(idx_to_code[i], idx_to_code[j])
                int_dm[i][j] = max(1, int(d * 1000))
            else:
                int_dm[i][j] = 0

    # Verify symmetry and consistency
    for i in range(n):
        for j in range(n):
            dict_dist = _dict_dist(idx_to_code[i], idx_to_code[j])
            int_dist = int_dm[i][j] / 1000.0 if i != j else 0.0
            assert abs(dict_dist - int_dist) < 0.1 or i == j, (
                f"Distance mismatch for ({i},{j}): dict={dict_dist}, int={int_dist}"
            )


class MockSolverStrategy:
    """
    Simulates the location-code↔integer-index mapping that SOTA strategies use.
    Mirrors the exact pattern from ebso_strategy.py, rdma_strategy.py, aoea_strategy.py.
    """

    def __init__(self):
        self.students = TRIVIAL_STUDENTS
        self.depot = TRIVIAL_DEPOT

    def _build_mapping(self):
        student_ids = [s.location_code for s in self.students]
        coordinates: Dict[str, Dict[str, float]] = {
            self.depot.id: {"lat": self.depot.lat, "lng": self.depot.lng},
        }
        for s in self.students:
            coordinates[s.location_code] = s.coordinates or {"lat": 0, "lng": 0}
        return student_ids, coordinates

    def _dist(self, loc1: str, loc2: str, coordinates: Dict) -> float:
        c1 = coordinates.get(loc1, {})
        c2 = coordinates.get(loc2, {})
        return round(euclidean_2d(
            c1.get("lat", 0), c1.get("lng", 0),
            c2.get("lat", 0), c2.get("lng", 0),
        ), 2)

    def run_mapping_pipeline(self) -> List[str]:
        """Execute the full mapping pipeline as done by actual SOTA strategies."""
        student_ids, coordinates = self._build_mapping()
        n = len(student_ids)

        idx_to_code = {i: student_ids[i] for i in range(n)}
        code_to_idx = {v: k for k, v in idx_to_code.items()}

        # Verify mapping is bijective (no duplicate codes, no missing indices)
        assert len(idx_to_code) == n, "Index→code map must have exactly n entries"
        assert len(code_to_idx) == n, "Code→index map must have exactly n entries"

        int_dm: Dict[int, Dict[int, int]] = {}
        for i in range(n):
            int_dm[i] = {}
            for j in range(n):
                if i != j:
                    d = self._dist(idx_to_code[i], idx_to_code[j], coordinates)
                    int_dm[i][j] = max(1, int(d * 1000))
                else:
                    int_dm[i][j] = 0

        # Build numpy matrix (as SOTA solvers do)
        matrix = np.array([[float(int_dm[i][j]) for j in range(n)] for i in range(n)])
        assert matrix.shape == (n, n), f"Matrix shape {matrix.shape} != ({n},{n})"

        # Run solver
        config = E2BSOTSPConfig(population_size=10, max_iterations=5, seed=42, ls_time_limit=0.1)
        solver = E2BSO_TSP(config)
        result = solver.solve_with_matrix(matrix.tolist())

        # Verify result.tour is a valid permutation of [0..n-1]
        tour = result.tour
        assert len(tour) == n, f"Tour length {len(tour)} != {n}"
        assert set(tour) == set(range(n)), f"Tour {tour} does not cover all indices"

        # Convert back to location codes (mirroring strategy code)
        best_order = [idx_to_code[idx] for idx in tour]
        assert len(best_order) == n
        assert set(best_order) == set(student_ids), "Round-trip location codes differ"

        return best_order


def test_sota_mapping_full_pipeline():
    """Run the full location-code ↔ integer-index mapping pipeline end-to-end."""
    strategy = MockSolverStrategy()
    result_order = strategy.run_mapping_pipeline()
    assert len(result_order) == 4
    # Verify each student location appears exactly once
    expected = {s.location_code for s in TRIVIAL_STUDENTS}
    assert set(result_order) == expected


def test_sota_mapping_disambiguates_duplicate_location_codes():
    """Duplicate location codes become unique occurrence keys, not a mapping error."""
    from uniride_core.adapters.demand_builder import student_occurrence_keys

    students = [
        StudentNode(id="s1", name="A", location_code="dup",
                    coordinates={"lat": 0.0, "lng": 0.0}, disability_type="So"),
        StudentNode(id="s2", name="B", location_code="dup",
                    coordinates={"lat": 0.0, "lng": 10.0}, disability_type="So"),
    ]
    node_ids = [TRIVIAL_DEPOT.id] + list(student_occurrence_keys(students))
    assert node_ids == ["depot", "dup#s1", "dup#s2"]
    assert len(set(node_ids)) == len(node_ids), "Occurrence keys must be unique"

    # The integer-index mapping is a bijection over the disambiguated node ids.
    idx_to_code = {i: nid for i, nid in enumerate(node_ids)}
    code_to_idx = {v: k for k, v in idx_to_code.items()}
    assert len(idx_to_code) == len(node_ids)
    assert len(code_to_idx) == len(node_ids)
    for i in range(len(node_ids)):
        assert code_to_idx[idx_to_code[i]] == i


def test_sota_mapping_with_depot_included():
    """Verify mapping works when depot is included in the distance matrix."""
    student_ids = [s.location_code for s in TRIVIAL_STUDENTS]
    location_ids = [TRIVIAL_DEPOT.id] + student_ids
    n_all = len(location_ids)

    idx_to_code = {i: location_ids[i] for i in range(n_all)}
    code_to_idx = {v: k for k, v in idx_to_code.items()}

    # Verify depot is index 0
    assert idx_to_code[0] == TRIVIAL_DEPOT.id
    assert code_to_idx[TRIVIAL_DEPOT.id] == 0

    # Verify students follow
    for i, s in enumerate(TRIVIAL_STUDENTS, start=1):
        assert code_to_idx[s.location_code] == i
