"""Strict-contract regressions for the split decoders under incomplete ATSP matrices.

Task A: a missing directed arc is data corruption — decoders must reject it
(inf / error / infeasible), never fabricate the old 15.0-minute default.
Task D: interior depot occurrences are stripped from the giant tour at decode
entry so the depot never appears as an interior route stop.
"""

import math

import pytest

from uniride_core.algorithms.cvrptw_decoder import CVRPTWDecoder
from uniride_core.algorithms.linear_split_decoder import LinearSplitDecoder
from uniride_core.algorithms.string_split_decoder import SplitDecoder

DEPOT = "DEPOT"


def _complete_atsp():
    """Full directed matrix for DEPOT/A/B/C with asymmetric travel times."""
    matrix = {node: {} for node in [DEPOT, "A", "B", "C"]}
    dists = {
        (DEPOT, "A"): 5.0, (DEPOT, "B"): 60.0, (DEPOT, "C"): 80.0,
        ("A", DEPOT): 50.0, ("A", "B"): 7.0, ("A", "C"): 40.0,
        ("B", DEPOT): 60.0, ("B", "A"): 70.0, ("B", "C"): 30.0,
        ("C", DEPOT): 3.0, ("C", "A"): 45.0, ("C", "B"): 40.0,
    }
    for (fr, to), d in dists.items():
        matrix[fr][to] = d
    return matrix


def _sparse_incomplete_atsp():
    """Only the arcs of one single-vehicle tour exist; B -> C is missing."""
    return {
        DEPOT: {"A": 5.0},
        "A": {"B": 7.0},
        "B": {},
        "C": {DEPOT: 3.0},
    }


def _demands():
    return {"A": (1, 0), "B": (1, 0), "C": (1, 0)}


def _route_arc_sum(matrix, route):
    total = 0.0
    prev = DEPOT
    for loc in route:
        total += matrix[prev][loc]
        prev = loc
    total += matrix[prev][DEPOT]
    return total


# ── Task A: reject missing directed arcs ────────────────────────────────────


def test_linear_rejects_missing_directed_arc_with_inf():
    decoder = LinearSplitDecoder(is_asymmetric=True)
    result = decoder.decode(["A", "B", "C"], DEPOT, _sparse_incomplete_atsp(), _demands())

    assert result.total_cost_ == float("inf")
    assert result.final_objective == float("inf")
    assert result.routes == []


def test_string_rejects_missing_directed_arc_with_error():
    decoder = SplitDecoder(is_asymmetric=True)
    result = decoder.decode(["A", "B", "C"], DEPOT, _sparse_incomplete_atsp(), _demands())

    assert "error" in result
    assert result["total_cost"] == float("inf")
    assert all(math.isinf(c) for c in result["costs"])


def test_single_missing_arc_is_not_fabricated_in_asymmetric_mode():
    matrix = _complete_atsp()
    del matrix["B"]["C"]

    linear = LinearSplitDecoder(is_asymmetric=True)
    res = linear.decode(["A", "B", "C"], DEPOT, matrix, _demands())
    assert res.routes == [["A", "B"], ["C"]]
    assert res.total_cost_ == pytest.approx(155.0)
    assert sum(_route_arc_sum(matrix, r) for r in res.routes) == pytest.approx(res.total_cost_)

    string = SplitDecoder(is_asymmetric=True)
    result = string.decode(["A", "B", "C"], DEPOT, matrix, _demands())
    assert result["routes"] == [["A", "B"], ["C"]]
    assert result["total_cost"] == pytest.approx(155.0)


def test_symmetric_reverse_lookup_still_allowed():
    matrix = _complete_atsp()
    del matrix["B"]["C"]

    linear = LinearSplitDecoder(is_asymmetric=False)
    res = linear.decode(["A", "B", "C"], DEPOT, matrix, _demands())
    assert res.routes == [["A", "B", "C"]]
    assert res.total_cost_ == pytest.approx(55.0)


def test_complete_atsp_decodes_normally_both_decoders():
    matrix = _complete_atsp()

    linear = LinearSplitDecoder(is_asymmetric=True)
    res = linear.decode(["A", "B", "C"], DEPOT, matrix, _demands())
    assert res.routes == [["A", "B", "C"]]
    assert res.total_cost_ == pytest.approx(45.0)

    string = SplitDecoder(is_asymmetric=True)
    result = string.decode(["A", "B", "C"], DEPOT, matrix, _demands())
    assert result["routes"] == [["A", "B", "C"]]
    assert result["total_cost"] == pytest.approx(45.0)


def test_is_feasible_rejects_missing_arc():
    decoder = CVRPTWDecoder(is_asymmetric=True)
    matrix = _complete_atsp()
    del matrix["B"]["C"]

    feasible, reason = decoder.is_feasible(["A", "B", "C"], DEPOT, matrix)
    assert feasible is False
    assert "missing arc" in reason


def test_is_feasible_rejects_missing_arc_in_symmetric_mode_too():
    decoder = CVRPTWDecoder()
    matrix = _complete_atsp()
    del matrix["B"]["C"]
    del matrix["C"]["B"]

    feasible, reason = decoder.is_feasible(["A", "B", "C"], DEPOT, matrix)
    assert feasible is False
    assert "missing arc" in reason


def test_is_feasible_accepts_complete_matrix():
    decoder = CVRPTWDecoder()
    matrix = _complete_atsp()

    feasible, reason = decoder.is_feasible(["A", "B", "C"], DEPOT, matrix)
    assert feasible is True
