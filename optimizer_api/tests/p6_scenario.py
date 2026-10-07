"""Scenario behind the P6 golden (heterogeneous fleet design section 7, P6).

``golden/p6_ga_split_optimize_response.json`` was captured at base commit
e1366ee, BEFORE any heterogeneous-fleet API field existed, by running exactly
this module (``python p6_scenario.py <out.json>`` with the base tree on
PYTHONPATH). It uses only the pre-existing API, so it runs unchanged on the
base. The test replays it on the current tree and requires an identical JSON
document (wall-clock ``execution_time_seconds`` neutralised).
"""

from __future__ import annotations

import json
import sys

DEPOT_ID = "DEPOT"


class ArcLoader:
    """DataLoader stand-in serving an explicit directed arc table."""

    def __init__(self, arcs):
        self._arcs = arcs

    def get_submatrix(self, locations, **_kwargs):
        return [
            [0.0 if a == b else float(self._arcs[(a, b)]) for b in locations]
            for a in locations
        ]


def star_arcs(count, out_arc=6.0, in_arc=5.0, between=3.0):
    nodes = [f"L{i}" for i in range(1, count + 1)]
    arcs = {}
    for x in nodes:
        arcs[(DEPOT_ID, x)] = out_arc
        arcs[(x, DEPOT_ID)] = in_arc
        for y in nodes:
            if x != y:
                arcs[(x, y)] = between
    return arcs


def install_loader(monkeypatch, strategy_name, arcs):
    """Patch the loader the strategy solves on and the certificate re-costs on."""
    from routers import optimization
    from certifier_matrix_support import certify_on_loader_matrix

    strategy = optimization.resolve_strategy(strategy_name).create()
    module = sys.modules[type(strategy).__module__]
    loader = ArcLoader(arcs)
    monkeypatch.setattr(module.DataLoader, "get_instance", staticmethod(lambda: loader))
    certify_on_loader_matrix(monkeypatch, loader)


def students(n_sw, n_so):
    from models.schemas import StudentNode

    out = []
    for i in range(1, n_sw + n_so + 1):
        out.append(StudentNode(
            id=f"s{i}",
            location_code=f"L{i}",
            disability_type="Sw" if i <= n_sw else "So",
            coordinates={"lat": 0.0, "lng": 0.0},
            pickup_time="08:30",
            dropoff_time="17:00",
        ))
    return out


def run_default_scenario(monkeypatch) -> str:
    """Run a plain ``ga_split`` /optimize call and return its normalised JSON."""
    from models.schemas import LocationNode, OptimizationRequest
    from routers import optimization

    install_loader(monkeypatch, "ga_split", star_arcs(5))
    request = OptimizationRequest(
        algorithm="ga_split",
        students=students(2, 3),
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        sw_capacity=4,
        so_capacity=2,
        max_travel_time=120,
        max_ride_time=40,
        direction="pickup",
        is_asymmetric=True,
        ga_config={"population_size": 20, "max_iterations": 15, "seed": 7},
    )
    response = optimization.optimize_route(request)
    document = json.loads(response.model_dump_json())
    document["execution_time_seconds"] = 0.0
    return json.dumps(document, sort_keys=True, indent=1)


if __name__ == "__main__":
    from _pytest.monkeypatch import MonkeyPatch

    patch = MonkeyPatch()
    try:
        text = run_default_scenario(patch)
    finally:
        patch.undo()
    with open(sys.argv[1], "w", encoding="utf-8", newline=chr(10)) as handle:
        handle.write(text + chr(10))
