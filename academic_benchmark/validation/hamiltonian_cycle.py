"""Independent Hamiltonian-cycle validator for TSP and ATSP tours (WP-E8, Package C; DECISION_LOG A04, E10, E12).

This module recomputes the length of a claimed tour from dataset artifacts (TSPLIB coordinate files, explicit full
matrices) under the TSPLIB95 convention and checks that the tour is one closed cycle through every node exactly once.

Independence: standard library only. It imports nothing from ``uniride_core`` (solver, parser, distance code),
``scripts``, ``numpy`` or ``academic_benchmark.core``, and it shares no function with the WP-E7 runner; a test checks the
imports statically and compares its distances with the repository's own TSPLIB code (parity, test-only import).

Convention (TSPLIB95 document, with the one documented deviation of E10):

* ``EUC_2D``: nint of the Euclidean distance, nint(x) = floor(x + 0.5).
* ``ATT``: r = sqrt((dx^2 + dy^2) / 10), t = nint(r), d = t + 1 when t < r, else t.
* ``GEO``: DD.MM coordinates (degrees truncated toward zero, minutes = fraction, converted with 5/3), radius 6378.388,
  d = trunc(6378.388 * acos(0.5 * ((1 + q1) * q2 - (1 - q1) * q3)) + 1.0). The constant PI is ``math.pi`` (E10: the
  TSPLIB95 document prints 3.141592; the effect is measured separately by the sensitivity re-solve of WP-E7). ``geo_pi``
  is a keyword only so that a test can show that the choice matters; the default is the contract.
* The tour is directed: arc ``tour[i] -> tour[i + 1]`` costs ``cost(a, b)``; the closing arc ``tour[-1] -> tour[0]`` is
  included; no symmetry of the cost is assumed, so an ATSP tour read backwards has its own length.

Scope: a TSP/ATSP Hamiltonian cycle only (one cycle, n nodes). Multi-route validation (CVRP/CVRPTW) is a separate
contract and lives elsewhere (A04); nothing here knows about vehicles, depots or routes.

Everything is pure and deterministic; nothing is read from disk or written.
"""
from __future__ import annotations

import math
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

SUPPORTED_EDGE_WEIGHT_TYPES = ("EUC_2D", "ATT", "GEO")
GEO_RADIUS = 6378.388

Cost = Callable[[int, int], int]


def _nint(value: float) -> int:
    return int(math.floor(value + 0.5))


def _geo_radians(x: float, geo_pi: float) -> float:
    degrees = int(x)  # truncation toward zero, as the TSPLIB95 reference code
    minutes = x - degrees
    return geo_pi * (degrees + 5.0 * minutes / 3.0) / 180.0


def tsplib_distance(edge_weight_type: str, a: Tuple[float, float], b: Tuple[float, float], *, geo_pi: float = math.pi) -> int:
    """TSPLIB95 integer distance between the coordinate pairs ``a`` and ``b``. Unsupported types raise ``ValueError``."""
    ewt = str(edge_weight_type).upper()
    if ewt == "EUC_2D":
        return _nint(math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))
    if ewt == "ATT":
        r = math.sqrt(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) / 10.0)
        t = _nint(r)
        return t + 1 if t < r else t
    if ewt == "GEO":
        lat1, lon1 = _geo_radians(a[0], geo_pi), _geo_radians(a[1], geo_pi)
        lat2, lon2 = _geo_radians(b[0], geo_pi), _geo_radians(b[1], geo_pi)
        q1 = math.cos(lon1 - lon2)
        q2 = math.cos(lat1 - lat2)
        q3 = math.cos(lat1 + lat2)
        arg = 0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)
        arg = max(-1.0, min(1.0, arg))  # rounding can leave [-1, 1] by one ulp for nearly identical points
        return int(GEO_RADIUS * math.acos(arg) + 1.0)
    raise ValueError(f"unsupported EDGE_WEIGHT_TYPE {edge_weight_type!r} (supported: {SUPPORTED_EDGE_WEIGHT_TYPES})")


# ---------------------------------------------------------------- TSPLIB text
_KEY_VALUE = re.compile(r"^\s*([A-Za-z_]+)\s*:?\s*(.*?)\s*$")


def parse_header(text: str) -> Dict[str, str]:
    """Upper-case keys and raw values of the ``KEY : value`` lines before the first data section."""
    header: Dict[str, str] = {}
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if line.upper().endswith("_SECTION") or line.upper() == "EOF":
            break
        match = _KEY_VALUE.match(line)
        if match and ":" in line:
            header[match.group(1).upper()] = match.group(2)
    return header


def _section_lines(text: str, section: str) -> List[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[str] = []
    inside = False
    for raw in lines:
        token = raw.strip()
        if not inside:
            if token.upper().startswith(section):
                inside = True
            continue
        if token.upper() == "EOF" or (token.upper().endswith("_SECTION") and token.upper() != section):
            break
        out.append(token)
    if not inside:
        raise ValueError(f"no {section} in the text")
    return out


def parse_coordinates(text: str) -> List[Tuple[float, float]]:
    """Coordinates of a ``NODE_COORD_SECTION`` ordered by node id; ids must be 1..n with no gap and no repeat."""
    nodes: Dict[int, Tuple[float, float]] = {}
    for line in _section_lines(text, "NODE_COORD_SECTION"):
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(f"coordinate line {line!r} has fewer than 3 fields")
        node = int(parts[0])
        if node in nodes:
            raise ValueError(f"node id {node} appears twice in the coordinate section")
        nodes[node] = (float(parts[1]), float(parts[2]))
    if sorted(nodes) != list(range(1, len(nodes) + 1)):
        raise ValueError("node ids of the coordinate section are not 1..n")
    return [nodes[i] for i in range(1, len(nodes) + 1)]


def parse_full_matrix(text: str) -> List[List[int]]:
    """The ``EDGE_WEIGHT_SECTION`` of an ``EXPLICIT`` / ``FULL_MATRIX`` file as an n x n list of ints (n from DIMENSION)."""
    header = parse_header(text)
    if header.get("EDGE_WEIGHT_TYPE", "EXPLICIT").upper() != "EXPLICIT":
        raise ValueError("not an EXPLICIT instance")
    if header.get("EDGE_WEIGHT_FORMAT", "FULL_MATRIX").upper() != "FULL_MATRIX":
        raise ValueError(f"unsupported EDGE_WEIGHT_FORMAT {header.get('EDGE_WEIGHT_FORMAT')!r} (only FULL_MATRIX)")
    n = int(header["DIMENSION"])
    values: List[int] = []
    for line in _section_lines(text, "EDGE_WEIGHT_SECTION"):
        values.extend(int(token) for token in line.split())
    if len(values) != n * n:
        raise ValueError(f"matrix has {len(values)} entries, expected {n * n}")
    return [values[i * n:(i + 1) * n] for i in range(n)]


# ---------------------------------------------------------------- cost callables
def matrix_cost(matrix: Sequence[Sequence[int]]) -> Cost:
    """``cost(i, j)`` over an explicit matrix (0-based, directed: row = from, column = to)."""
    return lambda i, j: matrix[i][j]


def coordinate_cost(edge_weight_type: str, coords: Sequence[Tuple[float, float]], *, geo_pi: float = math.pi) -> Cost:
    """``cost(i, j)`` over coordinates (0-based) under the TSPLIB convention of ``edge_weight_type``."""
    if str(edge_weight_type).upper() not in SUPPORTED_EDGE_WEIGHT_TYPES:
        raise ValueError(f"unsupported EDGE_WEIGHT_TYPE {edge_weight_type!r} (supported: {SUPPORTED_EDGE_WEIGHT_TYPES})")
    return lambda i, j: tsplib_distance(edge_weight_type, coords[i], coords[j], geo_pi=geo_pi)


# ---------------------------------------------------------------- cycle checks
def closed_length(tour0: Sequence[int], cost: Cost) -> int:
    """Length of the closed directed cycle ``tour0[0] -> ... -> tour0[-1] -> tour0[0]`` (0-based nodes)."""
    if len(tour0) < 2:
        return 0
    return sum(cost(tour0[i], tour0[(i + 1) % len(tour0)]) for i in range(len(tour0)))


def validate_hamiltonian_cycle(tour: Sequence[int], *, n: int, node_base: int, cost: Cost,
                               claimed_length: Optional[int] = None) -> List[str]:
    """Errors of a claimed Hamiltonian cycle (empty list: valid).

    ``tour`` holds node ids in the numbering of its file (``node_base`` 0 or 1) and lists every node once; the closing arc
    is implicit. A tour over a subset (a subtour), a repeated node, an id outside ``node_base .. node_base + n - 1``, a
    non-integer or boolean id, and a recomputed closed length different from ``claimed_length`` are each reported. The
    length is recomputed only when the node list is a valid permutation, so it never silently covers a structural error.
    """
    if node_base not in (0, 1):
        raise ValueError("node_base must be 0 or 1")
    errors: List[str] = []
    nodes = list(tour)
    if n < 1:
        return [f"n must be at least 1, got {n}"]
    if len(nodes) != n:
        errors.append(f"tour lists {len(nodes)} nodes, expected {n} (a tour over a subset is a subtour)")
    low, high = node_base, node_base + n - 1
    bad = [v for v in nodes if isinstance(v, bool) or not isinstance(v, int) or not low <= v <= high]
    if bad:
        errors.append(f"tour holds ids outside {low}..{high} or not integers: {bad[:5]}")
    elif len(set(nodes)) != len(nodes):
        repeated = sorted({v for v in nodes if nodes.count(v) > 1})
        errors.append(f"tour repeats a node: {repeated[:5]}")
    elif len(nodes) == n and claimed_length is not None:
        recomputed = closed_length([v - node_base for v in nodes], cost)
        if recomputed != claimed_length:
            errors.append(f"recomputed closed length {recomputed} differs from the claimed {claimed_length}")
    return errors
