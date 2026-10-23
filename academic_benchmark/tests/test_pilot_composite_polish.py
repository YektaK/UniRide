"""C-13 review polish: composite IDs under the protocol-v1 fair pilot and end to end in both pilots.

Smoke scale on synthetic 10-node stand-ins (one TSP, one ATSP); nothing here is a claim about
any algorithm.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from academic_benchmark.composite_protocol import COMPOSITE_ALGORITHMS, validate_composite_result
from academic_benchmark.fair_pilot import (
    APPROVED_ALGORITHMS,
    FairPilotError,
    load_fair_pilot_config,
    run_fair_pilot,
)
from academic_benchmark.native_pilot import run_native_pilot

COMPOSITES = tuple(COMPOSITE_ALGORITHMS)
COORDS = [(0, 0), (3, 1), (6, 0), (9, 2), (10, 6), (8, 9), (5, 10), (2, 8), (0, 5), (4, 4)]
N = len(COORDS)
BUDGET = 900

GWO_GLOBAL = {"pack_size": 4, "max_iterations": 60, "initial_a": 2.0, "exploration_rate": 0.4,
              "max_no_improvement": 60}
HHO_GLOBAL = {"hawks": 4, "max_iterations": 60, "initial_energy": 1.0, "jump_probability": 0.5,
              "max_no_improvement": 60, "dive_count": 0, "levy_scale": 0.3}
THREE_OPT_POLISH = {"max_iterations": 50, "first_improvement": False, "window": 5}
ALNS_POLISH = {"max_iterations": 40, "max_no_improvement": 20, "remove_ratio": 0.2, "min_remove": 2,
               "segment_length": 10, "weight_update_factor": 0.8, "use_sa": True,
               "sa_start_temp": 100.0, "sa_cooling_rate": 0.995}


def _entry(algorithm_id: str, *, global_fraction: bool) -> dict:
    family = COMPOSITE_ALGORITHMS[algorithm_id][0]
    block = {
        "global": dict(GWO_GLOBAL if family == "GWO" else HHO_GLOBAL),
        "polish": dict(ALNS_POLISH if algorithm_id.endswith("ALNS") else THREE_OPT_POLISH),
    }
    if global_fraction:
        block["global_fraction"] = 0.8
    return block


@dataclass
class _Problem:
    name: str
    problem_type: str
    dist_matrix: list
    optimal: float = 1.0
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


def _problems() -> list[_Problem]:
    def euclid(i: int, j: int) -> float:
        return float(round(math.dist(COORDS[i], COORDS[j])))

    tsp = [[0.0 if i == j else euclid(i, j) for j in range(N)] for i in range(N)]
    atsp = [[0.0 if i == j else euclid(i, j) + float((j - i) % N) for j in range(N)] for i in range(N)]
    return [_Problem("tiny-tsp", "tsp", tsp), _Problem("tiny-atsp", "atsp", atsp)]


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


# ------------------------------------------------------------------ 1a: composite under protocol v1
def test_protocol_v1_fair_config_refuses_a_composite_block(tmp_path):
    """The block itself is valid; only the protocol version makes the load fail."""
    algorithm_id = COMPOSITES[0]
    config = {
        "protocol_version": "uniride-fair-tsp-v1",
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": {**{a: {} for a in APPROVED_ALGORITHMS}, algorithm_id: _entry(algorithm_id, global_fraction=True)},
        "runs": 1, "evaluation_budget": BUDGET, "base_seed": 5, "budget_policy": "atomic_upper_bound_v1",
        "workers": 1, "replay_replicates": [], "allow_repository_output": False, "overwrite": False,
    }
    with pytest.raises(FairPilotError, match="runs only under protocol"):
        load_fair_pilot_config(_write(tmp_path / "fair_v1.json", config))


# ----------------------------------------------------------------- 1b: end to end on both pilots
def _fair_config(tmp_path: Path) -> Path:
    return _write(tmp_path / "fair.json", {
        "protocol_version": "uniride-fair-tsp-v2", "comparison_regime": "fixed_evaluation_budget",
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": {
            "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 10},
            "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "dive_count": 0, "max_no_improvement": 10},
            "Core-TwoOpt-TSP": {"max_iterations": 20, "first_improvement": False},
            "Core-ThreeOpt-TSP": {"max_iterations": 20, "first_improvement": False, "window": 4},
            "ALNS-TSP": dict(ALNS_POLISH),
            **{a: _entry(a, global_fraction=True) for a in COMPOSITES},
        },
        "runs": 1, "evaluation_budget": BUDGET, "base_seed": 17, "budget_policy": "atomic_upper_bound_v1",
        "workers": 1, "replay_replicates": [], "allow_repository_output": False, "overwrite": False,
    })


def _native_config(tmp_path: Path) -> Path:
    return _write(tmp_path / "native.json", {
        "protocol_version": "uniride-native-tsp-v1", "comparison_regime": "algorithm_native_termination",
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": {
            "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 1},
            "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "max_no_improvement": 1, "dive_count": 1},
            "Core-TwoOpt-TSP": {"max_iterations": 2, "first_improvement": False},
            "Core-ThreeOpt-TSP": {"max_iterations": 2, "first_improvement": True, "window": 4},
            "Core-OrOpt-TSP": {"max_iterations": 3, "first_improvement": False, "window": 3},
            "ALNS-TSP": dict(ALNS_POLISH),
            **{a: {**_entry(a, global_fraction=False),
                   "global": {**_entry(a, global_fraction=False)["global"], "max_iterations": 2},
                   "polish": {**_entry(a, global_fraction=False)["polish"], "max_iterations": 2}}
               for a in COMPOSITES},
        },
        "runs": 1, "base_seed": 71, "workers": 1, "replay_replicates": [],
        "allow_repository_output": False, "overwrite": False,
    })


def _rows(out: Path) -> list[dict]:
    lines = (out / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def _check_composition(rows: list[dict], *, fixed_budget: int | None) -> None:
    by_problem = {(r["problem"], r["algorithm_id"]) for r in rows}
    assert {(p, a) for p in ("tiny-tsp", "tiny-atsp") for a in COMPOSITES} <= by_problem
    for row in rows:
        if row["algorithm_id"] in COMPOSITES:
            assert "composition" in row, row["algorithm_id"]
            stages = [s["name"] for s in row["composition"]["stages"]]
            assert stages == ["global", "polish"]
            result = SimpleNamespace(**row, evaluations=row["objective_evaluations"])
            assert validate_composite_result(
                result, fixed_budget=fixed_budget, protocol_version=row["protocol_version"]
            ) == [], row["algorithm_id"]
        else:
            assert "composition" not in row, row["algorithm_id"]


def test_fair_pilot_runs_composites_end_to_end_on_tsp_and_atsp(tmp_path):
    out = tmp_path / "fair_out"
    report = run_fair_pilot(_fair_config(tmp_path), out, problem_loader=_problems, repo_root=tmp_path / "repo")
    assert report["validation"]["status"] == "passed"
    rows = _rows(out)
    _check_composition(rows, fixed_budget=BUDGET)
    assert {r["objective_evaluations"] <= BUDGET for r in rows} == {True}


def test_native_pilot_runs_composites_end_to_end_on_tsp_and_atsp(tmp_path):
    out = tmp_path / "native_out"
    report = run_native_pilot(_native_config(tmp_path), out, problem_loader=_problems, repo_root=tmp_path / "repo")
    assert report["validation"]["status"] == "passed"
    rows = _rows(out)
    _check_composition(rows, fixed_budget=None)
    assert {r["termination_reason"] for r in rows if r["algorithm_id"] in COMPOSITES} == {"composite_complete"}
