"""
L3: ATSP benchmark coverage — integration tests.

Tests ATSP problem parsing, distance matrix handling, and solver
compatibility with asymmetric distance matrices.
"""

import sys, os, math, random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from uniride_core.algorithms.tsplib_parser import (
    parse_atsp_text, TSPLIB_OPTIMALS, ATSP_PROBLEM_NAMES,
    download_atsp_problem, ensure_atsp_problems,
)
from uniride_core.models import ProblemInstance
from uniride_core.algorithms.sota_tsp import (
    E2BSO_TSP, E2BSOTSPConfig,
    R2DMA_TSP, R2DMATSPConfig,
    ALNS_TSP, ALNSConfig,
    BaseTSPSolver,
)

# ── Synthetic ATSP test data ──────────────────────────────────────────────

ATSP_4NODE_CONTENT = """NAME: test4.atsp
TYPE: ATSP
DIMENSION: 4
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
 0  10  20  30
40   0  50  60
70  80   0  90
10  20  30   0
EOF
"""

# Optimal tour: 0→1→2→3→0 = 10+50+90+10 = 160
ATSP_4NODE_OPTIMAL = 160


def test_atsp_parse_full_matrix():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    assert data is not None, "parse_atsp_text returned None"
    assert data['name'] == 'test4'
    assert data['dimension'] == 4
    assert data['edge_weight_type'] == 'EXPLICIT'
    assert 'explicit_matrix' in data
    matrix = data['explicit_matrix']
    assert len(matrix) == 4
    assert len(matrix[0]) == 4
    assert matrix[0] == [0, 10, 20, 30]
    assert matrix[1] == [40, 0, 50, 60]
    assert matrix[3] == [10, 20, 30, 0]


def test_atsp_matrix_asymmetric():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    matrix = data['explicit_matrix']
    assert matrix[0][1] != matrix[1][0], "ATSP matrix should be asymmetric"
    assert matrix[0][1] == 10 and matrix[1][0] == 40


def test_atsp_problem_instance_from_parsed():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    matrix = data['explicit_matrix']
    prob = ProblemInstance(
        name=data['name'],
        dimension=data['dimension'],
        problem_type=data['problem_type'],
        edge_weight_type=data['edge_weight_type'],
        dist_matrix=matrix,
        optimal=ATSP_4NODE_OPTIMAL,
    )
    assert prob.name == 'test4'
    assert prob.dimension == 4
    assert prob.dist_matrix is not None
    assert prob.dist_matrix[0][1] == 10


def test_sota_solver_on_atsp_matrix():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    matrix = data['explicit_matrix']
    solver = E2BSO_TSP(E2BSOTSPConfig(population_size=6, max_iterations=20, seed=42))
    result = solver.solve_with_matrix(matrix)
    tour = result.tour
    assert len(tour) == 4
    assert len(set(tour)) == 4
    assert min(tour) == 0 and max(tour) == 3
    assert result.tour_length > 0


def test_known_atsp_optimal_values_defined():
    for name in ATSP_PROBLEM_NAMES:
        assert name in TSPLIB_OPTIMALS, f"Missing ATSP optimal: {name}"
        assert TSPLIB_OPTIMALS[name] > 0, f"ATSP {name} optimal is zero"


def test_atsp_problem_names_list():
    assert "ftv33" in ATSP_PROBLEM_NAMES
    assert "ftv70" in ATSP_PROBLEM_NAMES
    assert "br17" in ATSP_PROBLEM_NAMES
    assert "rbg323" in ATSP_PROBLEM_NAMES


def test_alns_solver_on_atsp():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    matrix = data['explicit_matrix']
    solver = ALNS_TSP(ALNSConfig(iterations=100, seed=42))
    result = solver.solve_with_matrix(matrix)
    assert result.tour_length > 0
    assert len(result.tour) == 4
    assert len(set(result.tour)) == 4


def test_r2dma_solver_on_atsp():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    matrix = data['explicit_matrix']
    solver = R2DMA_TSP(R2DMATSPConfig(population_size=6, max_iterations=20, seed=42, tournament_k=3))
    result = solver.solve_with_matrix(matrix)
    assert result.tour_length > 0
    assert len(result.tour) == 4
    assert len(set(result.tour)) == 4


def test_atsp_problem_has_no_coordinates():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    assert 'coordinates' not in data or data['coordinates'] == []


def test_atsp_optimal_tour_cost_computation():
    data = parse_atsp_text(ATSP_4NODE_CONTENT, "test4.atsp")
    matrix = data['explicit_matrix']
    optimal_tour = [0, 1, 2, 3]
    cost = 0
    for i in range(4):
        cost += matrix[optimal_tour[i]][optimal_tour[(i + 1) % 4]]
    assert cost == ATSP_4NODE_OPTIMAL, f"Expected {ATSP_4NODE_OPTIMAL}, got {cost}"
