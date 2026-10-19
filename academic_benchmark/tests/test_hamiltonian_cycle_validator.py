"""WP-E8 Task 2: the independent Hamiltonian-cycle validator (``academic_benchmark.validation.hamiltonian_cycle``).

Hand-computed expectations, convention tests, an AST independence test and (test-only imports) parity with the repository's
own TSPLIB code. Nothing here opens a database; the committed instance files are required (a missing file is a failure).
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import pytest

from academic_benchmark.validation import hamiltonian_cycle as hc

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "academic_benchmark" / "validation" / "hamiltonian_cycle.py"
TSP_DIR = REPO / "academic_benchmark" / "tsplib_data" / "tsp"
FT53 = REPO / "academic_benchmark" / "tsplib_data" / "ft53.atsp"

# an asymmetric 4-node matrix: the cycle 0>1>2>3>0 costs 1+2+3+10 = 16, the same nodes read backwards cost 6+7+8+4 = 25
ASYM = [
    [0, 1, 9, 4],
    [8, 0, 2, 9],
    [9, 7, 0, 3],
    [10, 9, 6, 0],
]
SYM = [[0, 2, 7, 4], [2, 0, 5, 6], [7, 5, 0, 7], [4, 6, 7, 0]]


# ---------------------------------------------------------------- closed length and permutation checks
def test_closed_length_includes_the_closing_arc():
    cost = hc.matrix_cost(ASYM)
    assert hc.closed_length([0, 1, 2, 3], cost) == 1 + 2 + 3 + 10  # 0>1, 1>2, 2>3, 3>0
    assert hc.closed_length([0, 1, 2, 3], hc.matrix_cost(SYM)) == 2 + 5 + 7 + 4


def test_atsp_reversed_tour_has_a_different_length():
    cost = hc.matrix_cost(ASYM)
    forward = hc.closed_length([0, 1, 2, 3], cost)
    backward = hc.closed_length([3, 2, 1, 0], cost)
    assert (forward, backward) == (16, 25)  # 3>2, 2>1, 1>0, 0>3
    assert forward != backward
    # no symmetry is assumed: the validator accepts each direction only with its own length
    ok = hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=1, cost=cost, claimed_length=16)
    bad = hc.validate_hamiltonian_cycle([4, 3, 2, 1], n=4, node_base=1, cost=cost, claimed_length=16)
    assert ok == [] and bad and "differs" in bad[0]


def test_a_valid_tour_with_the_right_length_has_no_errors():
    cost = hc.matrix_cost(SYM)
    assert hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=1, cost=cost, claimed_length=18) == []
    assert hc.validate_hamiltonian_cycle([0, 1, 2, 3], n=4, node_base=0, cost=cost, claimed_length=18) == []
    assert hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=1, cost=cost) == []  # no length claimed


def test_subtour_is_rejected():
    errors = hc.validate_hamiltonian_cycle([1, 2, 3], n=4, node_base=1, cost=hc.matrix_cost(SYM))
    assert errors and "subtour" in errors[0]


def test_repeated_node_is_rejected_and_the_length_is_not_computed():
    errors = hc.validate_hamiltonian_cycle([1, 2, 2, 4], n=4, node_base=1, cost=hc.matrix_cost(SYM), claimed_length=18)
    assert errors == ["tour repeats a node: [2]"]


def test_node_outside_the_range_is_rejected():
    for tour in ([1, 2, 3, 5], [1, 2, 3, -1], [1, 2, 3, 0]):
        errors = hc.validate_hamiltonian_cycle(tour, n=4, node_base=1, cost=hc.matrix_cost(SYM))
        assert errors and "outside 1..4" in errors[0], tour


def test_zero_one_base_mismatch_is_rejected():
    cost = hc.matrix_cost(SYM)
    assert hc.validate_hamiltonian_cycle([0, 1, 2, 3], n=4, node_base=1, cost=cost), "a 0-based tour is not 1-based"
    assert hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=0, cost=cost), "a 1-based tour is not 0-based"
    with pytest.raises(ValueError, match="node_base"):
        hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=2, cost=cost)


@pytest.mark.parametrize("bad", [True, 2.0, "2", None])
def test_non_integer_and_boolean_nodes_are_rejected(bad):
    errors = hc.validate_hamiltonian_cycle([1, bad, 3, 4], n=4, node_base=1, cost=hc.matrix_cost(SYM))
    assert errors and "not integers" in errors[0]


def test_wrong_claimed_length_is_rejected():
    errors = hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=1, cost=hc.matrix_cost(SYM), claimed_length=17)
    assert errors == ["recomputed closed length 18 differs from the claimed 17"]


def test_a_tour_longer_than_n_is_rejected():
    errors = hc.validate_hamiltonian_cycle([1, 2, 3, 4, 1], n=4, node_base=1, cost=hc.matrix_cost(SYM))
    assert errors and "expected 4" in errors[0]


# ---------------------------------------------------------------- TSPLIB distances (hand computed)
def test_euc_2d_rounds_half_up_not_to_even():
    assert hc.tsplib_distance("EUC_2D", (0, 0), (2.5, 0)) == 3  # python's round(2.5) is 2
    assert hc.tsplib_distance("EUC_2D", (0, 0), (1.5, 0)) == 2
    assert hc.tsplib_distance("EUC_2D", (0, 0), (0.4, 0)) == 0
    assert hc.tsplib_distance("EUC_2D", (0, 0), (3, 4)) == 5


def test_att_rule():
    assert hc.tsplib_distance("ATT", (0, 0), (10, 0)) == 4   # r = 3.1623, t = 3 < r  -> 4
    assert hc.tsplib_distance("ATT", (0, 0), (3, 9)) == 3    # r = 3 exactly, t = 3, not < r -> 3
    assert hc.tsplib_distance("ATT", (0, 0), (12, 0)) == 4   # r = 3.7947, t = 4 >= r -> 4
    assert hc.tsplib_distance("ATT", (0, 0), (0, 0)) == 0


def test_geo_uses_math_pi_on_two_hand_computed_burma14_pairs():
    """burma14, nodes 1..3: 16.47 96.10 / 16.47 94.44 / 20.09 92.54. Distances 153 and 510 are the published weights of
    the instance (computed by hand from the TSPLIB formula: d(1,2) = int(6378.388 * 0.023952 + 1) = 153)."""
    n1, n2, n3 = (16.47, 96.10), (16.47, 94.44), (20.09, 92.54)
    assert hc.tsplib_distance("GEO", n1, n2) == 153
    assert hc.tsplib_distance("GEO", n1, n3) == 510
    assert hc.tsplib_distance("GEO", n2, n1) == 153  # symmetric for coordinates


def test_geo_default_pi_is_math_pi_and_a_3_141592_variant_differs_where_the_data_say_so():
    coords = hc.parse_coordinates((TSP_DIR / "gr96.tsp").read_text(encoding="utf-8"))
    differing = [(i, j) for i in range(len(coords)) for j in range(len(coords))
                 if i != j and hc.tsplib_distance("GEO", coords[i], coords[j])
                 != hc.tsplib_distance("GEO", coords[i], coords[j], geo_pi=3.141592)]
    assert len(differing) == 8, "WP-E7 geo_pi_sensitivity: gr96 has 8 differing arcs of 9120 under PI = 3.141592"
    burma = hc.parse_coordinates((TSP_DIR / "burma14.tsp").read_text(encoding="utf-8"))
    assert all(hc.tsplib_distance("GEO", burma[i], burma[j]) == hc.tsplib_distance("GEO", burma[i], burma[j], geo_pi=3.141592)
               for i in range(14) for j in range(14) if i != j), "burma14: 0 differing arcs"


def test_unsupported_edge_weight_type_is_refused():
    for ewt in ("CEIL_2D", "EUC_3D", "EXPLICIT", ""):
        with pytest.raises(ValueError, match="unsupported EDGE_WEIGHT_TYPE"):
            hc.tsplib_distance(ewt, (0, 0), (1, 1))
        with pytest.raises(ValueError, match="unsupported EDGE_WEIGHT_TYPE"):
            hc.coordinate_cost(ewt, [(0, 0), (1, 1)])


# ---------------------------------------------------------------- parsing
def test_parse_coordinates_orders_by_id_and_checks_the_ids():
    text = "NAME : t\nTYPE : TSP\nDIMENSION : 3\nEDGE_WEIGHT_TYPE : EUC_2D\nNODE_COORD_SECTION\n2 1.5 2.5\n1 0 0\n3 -1 7e0\nEOF\n"
    assert hc.parse_coordinates(text) == [(0.0, 0.0), (1.5, 2.5), (-1.0, 7.0)]
    assert hc.parse_header(text)["DIMENSION"] == "3" and hc.parse_header(text)["EDGE_WEIGHT_TYPE"] == "EUC_2D"
    with pytest.raises(ValueError, match="1..n"):
        hc.parse_coordinates("NODE_COORD_SECTION\n1 0 0\n3 1 1\nEOF\n")
    with pytest.raises(ValueError, match="twice"):
        hc.parse_coordinates("NODE_COORD_SECTION\n1 0 0\n1 1 1\nEOF\n")
    with pytest.raises(ValueError, match="NODE_COORD_SECTION"):
        hc.parse_coordinates("NAME : x\n")


def test_parse_full_matrix_reads_wrapped_rows_and_checks_the_size():
    text = ("NAME: m\nTYPE: ATSP\nDIMENSION: 3\nEDGE_WEIGHT_TYPE: EXPLICIT\nEDGE_WEIGHT_FORMAT: FULL_MATRIX\n"
            "EDGE_WEIGHT_SECTION\n 0 1\n 2 3 0\n 4 5 6 0\nEOF\n")  # rows wrapped at arbitrary places
    assert hc.parse_full_matrix(text) == [[0, 1, 2], [3, 0, 4], [5, 6, 0]]
    with pytest.raises(ValueError, match="expected 9"):
        hc.parse_full_matrix(text.replace(" 4 5 6 0\n", " 4 5 6\n"))
    with pytest.raises(ValueError, match="FULL_MATRIX"):
        hc.parse_full_matrix(text.replace("FULL_MATRIX", "LOWER_DIAG_ROW"))


# ---------------------------------------------------------------- independence (AST)
def test_the_module_imports_only_the_standard_library():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative import"
            imported.add((node.module or "").split(".")[0])
    assert imported, "the module imports something"
    assert imported <= set(sys.stdlib_module_names), sorted(imported - set(sys.stdlib_module_names))
    forbidden = {"uniride_core", "scripts", "numpy", "academic_benchmark", "numba", "scipy", "amplpy"}
    assert not imported & forbidden
    source = MODULE.read_text(encoding="utf-8")
    for token in ("uniride_core", "academic_benchmark.core", "run_exact", "numpy"):
        assert f"import {token}" not in source and f"from {token}" not in source


def test_the_module_has_no_route_or_vrp_logic():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    identifiers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr.lower())
        elif isinstance(node, ast.arg):
            identifiers.add(node.arg.lower())
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            identifiers.add(node.name.lower())
    for word in ("vehicle", "depot", "capacity", "window", "cvrp", "route"):
        assert not [i for i in identifiers if word in i], word  # the docstring may name the separate contract


# ---------------------------------------------------------------- parity with the repository (test-only import)
def test_distances_equal_the_repository_tsplib_code_on_every_committed_tsp_instance():
    from uniride_core.algorithms import tsplib_parser as repo

    checked = 0
    for path in sorted(TSP_DIR.glob("*.tsp")):
        text = path.read_text(encoding="utf-8")
        header = hc.parse_header(text)
        ewt = header["EDGE_WEIGHT_TYPE"]
        coords = hc.parse_coordinates(text)
        assert len(coords) == int(header["DIMENSION"]), path.name
        step = 1  # every ordered pair
        for i in range(0, len(coords), step):
            for j in range(len(coords)):
                if i != j:
                    assert hc.tsplib_distance(ewt, coords[i], coords[j]) == repo.tsplib_distance_by_type(ewt, coords[i], coords[j]), \
                        (path.name, i, j)
                    checked += 1
    assert len(sorted(TSP_DIR.glob("*.tsp"))) == 16 and checked > 50000


def test_matrix_parser_equals_the_repository_parser_on_the_tracked_ft53():
    from uniride_core.algorithms import tsplib_parser as repo

    assert FT53.is_file(), "ft53.atsp is tracked: a missing file is a failure, not a skip"
    text = FT53.read_text(encoding="utf-8")
    ours = hc.parse_full_matrix(text)
    theirs = repo.parse_atsp_text(text, "ft53")["explicit_matrix"]
    assert ours == theirs and len(ours) == 53
    assert any(ours[i][j] != ours[j][i] for i in range(53) for j in range(53)), "ft53 is asymmetric"


def test_geo_parity_with_math_pi_and_the_variant_pi_differs_from_the_repository_on_the_same_arcs():
    from uniride_core.algorithms import tsplib_parser as repo

    coords = hc.parse_coordinates((TSP_DIR / "gr96.tsp").read_text(encoding="utf-8"))
    ours = [(i, j) for i in range(96) for j in range(96) if i != j and hc.tsplib_distance("GEO", coords[i], coords[j])
            != repo.tsplib_distance_by_type("GEO", coords[i], coords[j])]
    assert ours == [], "math.pi in both (E10)"
    variant = [(i, j) for i in range(96) for j in range(96) if i != j
               and hc.tsplib_distance("GEO", coords[i], coords[j], geo_pi=3.141592) != repo.tsplib_distance_by_type("GEO", coords[i], coords[j])]
    assert len(variant) == 8


def test_validator_is_pure_and_deterministic():
    cost = hc.matrix_cost(SYM)
    first = hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=1, cost=cost, claimed_length=18)
    second = hc.validate_hamiltonian_cycle([1, 2, 3, 4], n=4, node_base=1, cost=cost, claimed_length=18)
    assert first == second == []
    tour = [1, 2, 3, 4]
    hc.validate_hamiltonian_cycle(tour, n=4, node_base=1, cost=cost)
    assert tour == [1, 2, 3, 4], "the input is not modified"
    assert math.isfinite(hc.closed_length([0, 1, 2, 3], cost))
