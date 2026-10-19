r"""A NAME header line must not borrow its value from the next line (DECISION_LOG A17).

The old pattern ``^NAME\s*[:\s]\s*(\S+)`` let ``\s`` match a line break, so ``NAME:`` with
no value took the first word of the following header line (``TYPE:``).
"""
from uniride_core.algorithms.tsplib_parser import parse_atsp_text, parse_tsplib_text

_COORDS = "NODE_COORD_SECTION\n1 0 0\n2 3 4\n3 6 8\nEOF\n"


def _tsp(name_line: str) -> str:
    return (
        f"{name_line}\nTYPE: TSP\nDIMENSION: 3\nEDGE_WEIGHT_TYPE: EUC_2D\n{_COORDS}"
    )


def _atsp(name_line: str) -> str:
    return (
        f"{name_line}\nTYPE: ATSP\nDIMENSION: 2\nEDGE_WEIGHT_TYPE: EXPLICIT\n"
        "EDGE_WEIGHT_FORMAT: FULL_MATRIX\nEDGE_WEIGHT_SECTION\n0 1\n2 0\nEOF\n"
    )


def test_tsp_empty_name_value_does_not_take_next_line():
    parsed = parse_tsplib_text(_tsp("NAME:"), "eil51.tsp")
    assert parsed is not None
    assert parsed["name"] != "TYPE:"
    assert parsed["name"] == "eil51"  # same fallback as an absent NAME header


def test_tsp_bare_name_keyword_does_not_take_next_line():
    parsed = parse_tsplib_text(_tsp("NAME"), "eil51.tsp")
    assert parsed is not None
    assert parsed["name"] == "eil51"


def test_tsp_name_with_value_unchanged():
    assert parse_tsplib_text(_tsp("NAME : eil51"), "x.tsp")["name"] == "eil51"
    assert parse_tsplib_text(_tsp("NAME: eil51"), "x.tsp")["name"] == "eil51"
    assert parse_tsplib_text(_tsp("NAME eil51"), "x.tsp")["name"] == "eil51"


def test_atsp_empty_name_value_does_not_take_next_line():
    parsed = parse_atsp_text(_atsp("NAME:"), "ftv33.atsp")
    assert parsed is not None
    assert parsed["name"] != "TYPE:"
    assert parsed["name"] == "ftv33"


def test_atsp_name_with_value_unchanged():
    assert parse_atsp_text(_atsp("NAME : ftv33"), "x.atsp")["name"] == "ftv33"
