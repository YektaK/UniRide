"""WP0 parity harness for docs/designs/HETEROGENEOUS_FLEET_DESIGN.md (P0/P1/P2).

Goldens in ``golden/split_parity.json`` were captured at base commit f3a41e2
(before any heterogeneous-fleet edit).  The test regenerates the same outputs and
requires a byte-identical JSON document.  To recapture deliberately, run
``python -m uniride_core.tests.test_split_parity_golden --write`` (only with a
documented reason: this file defines the default-path contract).
"""

from __future__ import annotations

import dataclasses
import json
import math
import random
import re
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Tuple

from uniride_core.algorithms import meta_split_common as msc
from uniride_core.algorithms.ga_split_engine import solve_ga_split
from uniride_core.algorithms.gwo_split_engine import solve_gwo_split
from uniride_core.algorithms.hho_split_engine import solve_hho_split
from uniride_core.algorithms.pso_split_engine import solve_pso_split
from uniride_core.algorithms.string_split_decoder import (
    Direction,
    decode_giant_tour,
    decode_with_time_windows,
)

GOLDEN = Path(__file__).parent / "golden" / "split_parity.json"
REPO = Path(__file__).resolve().parents[2]
DEPOT = "D"
SEEDS = (0, 42, 1234)
_LCG = 48271


def _instance(n: int, asymmetric: bool) -> Tuple[List[str], Dict[str, Dict[str, int]], Dict[str, Tuple[int, int]]]:
    """Deterministic EUC-style integer matrix (optionally skewed), Sw/So mix."""
    state = 7919 + n
    pts: Dict[str, Tuple[int, int]] = {}
    for name in [DEPOT] + [f"L{i}" for i in range(1, n + 1)]:
        state = state * _LCG % 2147483647
        x = state % 40
        state = state * _LCG % 2147483647
        pts[name] = (x, state % 40)
    names = list(pts)
    matrix: Dict[str, Dict[str, int]] = {}
    for a in names:
        matrix[a] = {}
        for b in names:
            if a == b:
                matrix[a][b] = 0
                continue
            d = math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])
            if asymmetric and a < b:
                d *= 1.25
            matrix[a][b] = max(1, round(d))
    demands = {f"L{i}": ((1, 0) if i % 3 else (0, 1 + i % 2)) for i in range(1, n + 1)}
    return names[1:], matrix, demands


def _windows(wps: List[str]) -> Dict[str, Tuple[int, int]]:
    return {w: (480 + 7 * i, 480 + 7 * i + 30) for i, w in enumerate(wps)}


def _jsonable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if hasattr(obj, "__dict__"):
        return {k: _jsonable(v) for k, v in vars(obj).items()}
    return repr(obj)


_GA_CFG = {"population_size": 10, "max_iterations": 6, "local_search_interval": 3, "max_no_improvement": 5}
_PSO_CFG = {
    "swarm_size": 8, "max_iterations": 5, "inertia_weight": 0.9, "inertia_min": 0.4,
    "cognitive_weight": 2.0, "social_weight": 2.0, "velocity_clamp": 0.7,
    "local_search_interval": 3, "local_search_type": "two_opt", "max_no_improvement": 4,
}
_GWO_CFG = {
    "population_size": 8, "max_iterations": 5, "initial_a": 2.5, "exploration_rate": 0.4,
    "local_search_interval": 3, "local_search_type": "two_opt", "max_no_improvement": 4,
}
_HHO_CFG = {
    "population_size": 8, "max_iterations": 5, "initial_energy": 2.0, "jump_probability": 0.4,
    "levy_flight_scale": 0.3, "local_search_interval": 3, "local_search_type": "two_opt",
    "max_no_improvement": 4,
}


def build_golden() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    # (name, waypoints, asymmetric, direction, sw cap, so cap, tour limit, ride limit)
    scenarios = [
        ("sym9_pickup_R50", 9, False, "pickup", 4, 5, 90.0, 50.0),
        ("asym8_dropoff_R90", 8, True, "dropoff", 4, 5, 120.0, 90.0),
        ("sym7_pickup_noR_small", 7, False, "pickup", 2, 3, 70.0, None),
    ]
    for name, n, asym, direction, swc, soc, tour, ride in scenarios:
        wps, matrix, demands = _instance(n, asym)
        windows = _windows(wps)
        d_enum = Direction(direction)
        for tw in (False, True):
            tag = f"{name}|tw={'on' if tw else 'off'}"
            common = dict(
                depot=DEPOT, distance_matrix=matrix, demands=demands,
                sw_capacity=swc, so_capacity=soc, max_tour_duration=tour,
            )
            tw_kw = (
                dict(use_time_windows=True, time_windows=windows, direction=direction,
                     target_time=540, offset_minutes=10)
                if tw else dict(direction=direction)
            )
            # Shared decoder, fixed tours (identity and reversed).
            for label, tour_order in (("id", wps), ("rev", wps[::-1])):
                if tw:
                    dec = decode_with_time_windows(
                        giant_tour=tour_order, time_windows=windows, direction=d_enum,
                        target_time=540, offset_minutes=10, is_asymmetric=asym,
                        max_ride_time=ride, **common,
                    )
                else:
                    dec = decode_giant_tour(
                        giant_tour=tour_order, is_asymmetric=asym, max_ride_time=ride,
                        direction=d_enum, **common,
                    )
                out[f"decoder|{tag}|{label}"] = _jsonable(dec)
                out[f"msc_final|{tag}|{label}"] = _jsonable(msc.decode_final_tour(
                    tour_order, is_asymmetric=asym, **common, **tw_kw,
                ))
                out[f"msc_cost|{tag}|{label}"] = {
                    "giant": msc.giant_tour_cost(tour_order, DEPOT, matrix),
                    "penalized": msc.split_penalized_cost(
                        tour_order, DEPOT, matrix, demands, swc, soc, tour, asym),
                }
            # Engines, fixed seeds.
            for seed in SEEDS:
                key = f"{tag}|seed={seed}"
                ga_kw = dict(common, waypoints=wps, use_time_windows=tw, is_asymmetric=asym,
                             time_windows=windows if tw else None, direction=direction,
                             target_time=540 if tw else None, offset_minutes=10)
                out[f"ga|{key}"] = _jsonable(solve_ga_split(
                    config=_GA_CFG, rng=random.Random(seed), max_ride_time=ride, **ga_kw))
                for label, solver, cfg in (
                    ("pso", solve_pso_split, _PSO_CFG),
                    ("gwo", solve_gwo_split, _GWO_CFG),
                    ("hho", solve_hho_split, _HHO_CFG),
                ):
                    out[f"{label}|{key}"] = _jsonable(solver(
                        config=cfg, rng=random.Random(seed), **ga_kw))
    return out


def _dump(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, indent=1) + "\n"


def test_split_outputs_are_byte_identical_to_base_commit_goldens():
    # Normalise CRLF so git autocrlf checkouts compare equal to the LF capture.
    expected = GOLDEN.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    actual = _dump(build_golden())
    if actual != expected:
        got, want = json.loads(actual), json.loads(expected)
        diff = sorted(k for k in set(got) | set(want) if got.get(k) != want.get(k))
        raise AssertionError(f"split parity drift in {len(diff)} entries, first: {diff[:5]}")
    assert actual.encode("utf-8") == expected.encode("utf-8")


def test_golden_covers_every_engine_and_mix():
    keys = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for prefix in ("ga", "pso", "gwo", "hho", "decoder", "msc_final", "msc_cost"):
        assert any(k.startswith(prefix + "|") for k in keys), prefix
    assert sum(k.startswith("ga|") for k in keys) == 3 * 2 * len(SEEDS)
    # Goldens must be informative: routes exist.
    assert all(v["final_result"]["routes"] for k, v in keys.items() if k.startswith("ga|"))


_NEW_MODULES = ("typed_split_decoder", "ga_split_typed_engine", "typed_day_selection")
_ALT = "|".join(_NEW_MODULES)
_IMPORT_RE = re.compile(
    rf"^\s*(?:from\s+[\w.]*\b(?:{_ALT})\b|import\s+[\w.]*\b(?:{_ALT})\b"
    rf"|from\s+[\w.]+\s+import\s+[^#\n]*\b(?:{_ALT})\b)",
    re.M,
)
_REGISTRY_FILES = (
    "uniride_core/algorithms/registry.py",
    "uniride_core/algorithms/engine_factory.py",
)


def _academic_sources() -> List[Path]:
    files = sorted((REPO / "academic_benchmark").rglob("*.py"))
    files += [REPO / p for p in _REGISTRY_FILES if (REPO / p).exists()]
    return files


def test_p2_academic_code_never_imports_heterogeneous_modules():
    files = _academic_sources()
    assert len(files) > 10  # the scan must actually see the academic tree
    offenders = [
        f"{p.relative_to(REPO)}: {m.group(0).strip()}"
        for p in files
        for m in _IMPORT_RE.finditer(p.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not offenders, offenders


def test_p2_guard_regex_detects_forbidden_imports():
    for line in (
        "from uniride_core.algorithms.typed_split_decoder import X",
        "from uniride_core.planning import typed_day_selection",
        "import uniride_core.algorithms.ga_split_typed_engine as g",
    ):
        assert _IMPORT_RE.search(line), line
    assert not _IMPORT_RE.search("from uniride_core.algorithms.string_split_decoder import SplitDecoder")


if __name__ == "__main__":
    if "--write" in sys.argv:
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_bytes(_dump(build_golden()).encode("utf-8"))
        print("written", GOLDEN)
