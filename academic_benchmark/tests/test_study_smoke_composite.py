"""C-13 part A: composite IDs in the study smoke export and in the fair/native pilots.

Smoke scale on a synthetic 10-node instance (no claim about any algorithm). The synthetic study
is built in a temporary repository so the tests stay fast and do not depend on a TSPLIB instance.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from academic_benchmark.composite_protocol import (
    COMPOSITE_ALGORITHMS,
    validate_composite_result,
)
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.fair_pilot import (
    FairPilotError,
    OPTIONAL_ALGORITHMS,
    load_fair_pilot_config,
)
from academic_benchmark.native_pilot import (
    NativePilotError,
    load_native_pilot_config,
)
from academic_benchmark.native_protocol import OPTIONAL_NATIVE_ALGORITHMS
from academic_benchmark.studies import build_study_plan
from academic_benchmark.studies.smoke import (
    StudySmokeError,
    run_study_smoke,
)
from uniride_core.algorithms.distance import tsplib_distance_by_type

COMPOSITES = tuple(COMPOSITE_ALGORITHMS)
COORDS = [(0, 0), (3, 1), (6, 0), (9, 2), (10, 6), (8, 9), (5, 10), (2, 8), (0, 5), (4, 4)]
N = len(COORDS)
ARTIFACT = (
    "NAME: tiny10\nTYPE: TSP\nDIMENSION: 10\nEDGE_WEIGHT_TYPE: EUC_2D\nNODE_COORD_SECTION\n"
    + "".join(f"{i + 1} {x} {y}\n" for i, (x, y) in enumerate(COORDS))
    + "EOF\n"
).encode("utf-8")
SCAN = N * (N - 1) // 2  # 45
LEVELS = [20 * SCAN, 100 * SCAN]  # 900, 4500

GWO_GLOBAL = {"pack_size": 4, "max_iterations": 60, "initial_a": 2.0, "exploration_rate": 0.4,
              "max_no_improvement": 60}
HHO_GLOBAL = {"hawks": 4, "max_iterations": 60, "initial_energy": 1.0, "jump_probability": 0.5,
              "max_no_improvement": 60, "dive_count": 0, "levy_scale": 0.3}
THREE_OPT_POLISH = {"max_iterations": 50, "first_improvement": False, "window": 5}
ALNS_POLISH = {"max_iterations": 40, "max_no_improvement": 20, "remove_ratio": 0.2, "min_remove": 2,
               "segment_length": 10, "weight_update_factor": 0.8, "use_sa": True,
               "sa_start_temp": 100.0, "sa_cooling_rate": 0.995}


def _entry(algorithm_id: str) -> dict:
    family = COMPOSITE_ALGORITHMS[algorithm_id][0]
    return {
        "global": dict(GWO_GLOBAL if family == "GWO" else HHO_GLOBAL),
        "polish": dict(ALNS_POLISH if algorithm_id.endswith("ALNS") else THREE_OPT_POLISH),
        "global_fraction": 0.8,
    }


def _study_payload() -> dict:
    return {
        "schema_version": "uniride-study/v1",
        "study_id": "composite-smoke-fixture",
        "title": "Composite smoke fixture",
        "status": "draft",
        "algorithm_ids": list(COMPOSITES),
        "algorithm_parameters": {a: _entry(a) for a in COMPOSITES},
        "dataset_manifest_refs": ["datasets/tiny10.json"],
        "primary_protocol": {
            "protocol_id": "fixed_evaluation_budget",
            "protocol_version": "uniride-fair-tsp-v2",
            "budget_policy": "atomic_upper_bound_v1",
        },
        "secondary_protocol": {
            "protocol_id": "algorithm_native_termination",
            "protocol_version": "uniride-native-tsp-v1",
            "algorithm_ids": None,
            "termination": {"max_iterations": 2},
        },
        "scaled_fixed_budget_levels": {
            "rule": "two_opt_scan_multiples_v1",
            "scan_multipliers": [20, 100],
            "levels_by_dataset": {"tiny10": LEVELS},
        },
        "run_count": 3,
        "base_seed": 2026,
        "seed_protocol_version": "sha256-seed-v1",
        "problem_families": ["TSP"],
        "analysis_plan_id": "fixture",
        "output_policy": {"repository_outputs": "smoke_only", "paper_scale_location": "external"},
        "paper_metadata": {"paper_id": "fixture", "year": 2026, "venue": "draft"},
    }


def _dataset_payload() -> dict:
    return {
        "schema_version": "uniride-dataset/v1",
        "dataset_id": "tiny10",
        "artifact_path": "data/tiny10.tsp",
        "source": {"authority_url": "https://example.invalid/tiny10", "retrieved_on": "2026-10-22"},
        "checksum": {"algorithm": "sha256", "value": hashlib.sha256(ARTIFACT).hexdigest()},
        "problem_type": "TSP",
        "dimension": N,
        "matrix_semantics": {"directed": False, "edge_weight_type": "EUC_2D", "diagonal_semantics": "zero"},
        "best_known": {"status": "unknown", "value": None, "provenance": "none"},
    }


def _repository(root: Path, mutate=None) -> Path:
    for name in ("data", "datasets", "studies"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "data" / "tiny10.tsp").write_bytes(ARTIFACT)
    (root / "datasets" / "tiny10.json").write_text(json.dumps(_dataset_payload()), encoding="utf-8")
    payload = _study_payload()
    if mutate is not None:
        mutate(payload)
    (root / "studies" / "study.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


@dataclass
class _Problem:
    name: str
    dist_matrix: list
    problem_type: str = "tsp"
    optimal: float = 1.0
    edge_weight_type: str = "EUC_2D"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


def _loader(name: str = "tiny10"):
    matrix = [
        [0.0 if i == j else float(tsplib_distance_by_type("EUC_2D", COORDS[i], COORDS[j]))
         for j in range(N)] for i in range(N)
    ]
    problem = _Problem(name=name, dist_matrix=matrix)
    return lambda _name: problem


def _plan(root: Path):
    return build_study_plan("studies/study.json", repository_root=root)


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _as_result(row: dict) -> SimpleNamespace:
    """The exported row seen as a result object (``evaluations`` is the row's objective count)."""
    return SimpleNamespace(**row, evaluations=row["objective_evaluations"])


@pytest.fixture(scope="module")
def first_run(tmp_path_factory):
    root = _repository(tmp_path_factory.mktemp("repo"))
    out = tmp_path_factory.mktemp("first") / "out"
    report = run_study_smoke(
        _plan(root), out, problem_loader=_loader(), repository_root=root, replicates=1
    )
    return root, out, report


# ------------------------------------------------------------------------- smoke export of composites
def test_composite_ids_write_valid_fixed_and_native_rows_with_stage_records(first_run):
    _root, out, report = first_run
    assert report.status == "passed", report.text
    fixed, native = _read(out / "fixed_runs.jsonl"), _read(out / "native_runs.jsonl")
    assert sorted(r["algorithm_id"] for r in fixed) == sorted(COMPOSITES)
    assert sorted(r["algorithm_id"] for r in native) == sorted(COMPOSITES)
    assert {r["evaluation_budget"] for r in fixed} == {min(LEVELS)}
    for row in fixed:
        record = row["composition"]
        assert [s["name"] for s in record["stages"]] == ["global", "polish"]
        assert record["mode"] == "fixed_budget" and record["global_fraction"] == 0.8
        assert record["evaluation_budget"] == min(LEVELS)
        assert validate_composite_result(
            _as_result(row), fixed_budget=min(LEVELS), protocol_version=row["protocol_version"]
        ) == []
    for row in native:
        record = row["composition"]
        assert record["mode"] == "native" and record["global_fraction"] is None
        assert row["termination_reason"] == "composite_complete"
        assert validate_composite_result(
            _as_result(row), fixed_budget=None, protocol_version=row["protocol_version"]
        ) == []
    for row in fixed + native:
        assert row["hamiltonian_validation"] == "passed" and row["validation_status"] == "passed"


def test_exported_stage_records_keep_per_stage_wall_time(first_run):
    _root, out, _report = first_run
    for row in _read(out / "fixed_runs.jsonl") + _read(out / "native_runs.jsonl"):
        for stage in row["composition"]["stages"]:
            assert stage["elapsed_sec"] >= 0


def test_fixed_composite_without_global_fraction_is_refused_before_any_run(tmp_path):
    def drop_fraction(payload):
        del payload["algorithm_parameters"]["Core-GWO-TSP-Memetic-3opt"]["global_fraction"]

    root = _repository(tmp_path / "repo", drop_fraction)
    calls = []

    def gateway(**kwargs):
        calls.append(kwargs)
        return execute_preflighted(**kwargs)

    with pytest.raises(StudySmokeError, match="global_fraction"):
        run_study_smoke(
            _plan(root), tmp_path / "out", problem_loader=_loader(), repository_root=root,
            replicates=1, gateway_executor=gateway,
        )
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_fixed_runs_pass_global_fraction_explicitly_and_native_runs_never_do(tmp_path):
    root = _repository(tmp_path / "repo")
    seen = []

    def gateway(**kwargs):
        seen.append((kwargs["protocol"].value, copy.deepcopy(kwargs["params"])))
        return execute_preflighted(**kwargs)

    report = run_study_smoke(
        _plan(root), tmp_path / "out", problem_loader=_loader(), repository_root=root,
        replicates=1, gateway_executor=gateway,
    )
    assert report.status == "passed", report.text
    fixed = [p for proto, p in seen if proto == "fixed_budget"]
    native = [p for proto, p in seen if proto == "native_termination"]
    assert len(fixed) == len(native) == len(COMPOSITES)
    assert all(p["global_fraction"] == 0.8 for p in fixed)
    assert all("global_fraction" not in p for p in native)


def test_two_same_seed_runs_export_identical_rows_apart_from_timing(first_run, tmp_path):
    from academic_benchmark.studies.smoke import comparable_row

    root, out, _report = first_run
    again = tmp_path / "again"
    run_study_smoke(_plan(root), again, problem_loader=_loader(), repository_root=root, replicates=1)
    for name in ("fixed_runs.jsonl", "native_runs.jsonl"):
        a = [comparable_row(r) for r in _read(out / name)]
        b = [comparable_row(r) for r in _read(again / name)]
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), name


def test_comparable_row_drops_only_timing_and_does_not_mutate(first_run):
    from academic_benchmark.studies.smoke import comparable_row

    _root, out, _report = first_run
    row = _read(out / "fixed_runs.jsonl")[0]
    original = copy.deepcopy(row)
    view = comparable_row(row)
    assert row == original
    assert "elapsed_ms" not in view
    assert all("elapsed_sec" not in stage for stage in view["composition"]["stages"])
    stripped = copy.deepcopy(original)
    stripped.pop("elapsed_ms")
    for stage in stripped["composition"]["stages"]:
        stage.pop("elapsed_sec")
    assert view == stripped
    assert comparable_row(view) == view
    plain = {"algorithm_id": "Core-TwoOpt-TSP", "elapsed_ms": 1.0, "tour": [1, 2]}
    assert comparable_row(plain) == {"algorithm_id": "Core-TwoOpt-TSP", "tour": [1, 2]}


# ------------------------------------------------------------------------------ pilot allowlists
def _fair_config(tmp_path: Path, extra: dict) -> Path:
    value = {
        "protocol_version": "uniride-fair-tsp-v2", "comparison_regime": "fixed_evaluation_budget",
        "problems": ["tiny10"],
        "algorithms": {
            "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 10},
            "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "dive_count": 0, "max_no_improvement": 10},
            "Core-TwoOpt-TSP": {"max_iterations": 20, "first_improvement": False},
            "Core-ThreeOpt-TSP": {"max_iterations": 20, "first_improvement": False, "window": 4},
            "ALNS-TSP": dict(ALNS_POLISH),
            **extra,
        },
        "runs": 1, "evaluation_budget": 900, "base_seed": 17, "budget_policy": "atomic_upper_bound_v1",
        "workers": 1, "replay_replicates": [], "allow_repository_output": False, "overwrite": False,
    }
    path = tmp_path / "fair.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _native_config(tmp_path: Path, extra: dict) -> Path:
    value = {
        "protocol_version": "uniride-native-tsp-v1", "comparison_regime": "algorithm_native_termination",
        "problems": ["tiny10"],
        "algorithms": {
            "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 1},
            "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "max_no_improvement": 1, "dive_count": 1},
            "Core-TwoOpt-TSP": {"max_iterations": 2, "first_improvement": False},
            "Core-ThreeOpt-TSP": {"max_iterations": 2, "first_improvement": True, "window": 4},
            "Core-OrOpt-TSP": {"max_iterations": 3, "first_improvement": False, "window": 3},
            "ALNS-TSP": dict(ALNS_POLISH),
            **extra,
        },
        "runs": 1, "base_seed": 71, "workers": 1, "replay_replicates": [],
        "allow_repository_output": False, "overwrite": False,
    }
    path = tmp_path / "native.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_composite_ids_are_in_both_pilot_allowlists():
    assert set(COMPOSITES) <= OPTIONAL_ALGORITHMS
    assert set(COMPOSITES) <= OPTIONAL_NATIVE_ALGORITHMS


@pytest.mark.parametrize("algorithm_id", COMPOSITES)
def test_fair_pilot_accepts_a_composite_block_with_explicit_global_fraction(tmp_path, algorithm_id):
    config = load_fair_pilot_config(_fair_config(tmp_path, {algorithm_id: _entry(algorithm_id)}))
    assert config.algorithms[algorithm_id]["global_fraction"] == 0.8


@pytest.mark.parametrize("algorithm_id", COMPOSITES)
def test_fair_pilot_refuses_a_composite_block_without_global_fraction(tmp_path, algorithm_id):
    block = _entry(algorithm_id)
    del block["global_fraction"]
    with pytest.raises(FairPilotError, match="global_fraction"):
        load_fair_pilot_config(_fair_config(tmp_path, {algorithm_id: block}))


@pytest.mark.parametrize("algorithm_id", COMPOSITES)
def test_native_pilot_accepts_a_composite_block_and_refuses_global_fraction(tmp_path, algorithm_id):
    block = _entry(algorithm_id)
    del block["global_fraction"]
    config = load_native_pilot_config(_native_config(tmp_path, {algorithm_id: block}))
    assert "global_fraction" not in config.algorithms[algorithm_id]
    with pytest.raises(NativePilotError, match="global_fraction"):
        load_native_pilot_config(_native_config(tmp_path, {algorithm_id: _entry(algorithm_id)}))


def test_composite_row_is_validated_as_exported_not_only_as_computed(tmp_path, monkeypatch):
    """A record that lost its stage record on the way to the file fails the composite check."""
    from academic_benchmark.studies import smoke

    real = smoke._result_record

    def builder_that_drops_the_stage_record(*args, **kwargs):
        record = real(*args, **kwargs)
        record.pop("composition", None)
        return record

    monkeypatch.setattr(smoke, "_result_record", builder_that_drops_the_stage_record)
    root = _repository(tmp_path / "repo")
    report = run_study_smoke(
        _plan(root), tmp_path / "out", problem_loader=_loader(), repository_root=root, replicates=1
    )
    assert report.status == "failed"
    failed = _read(tmp_path / "out" / "failed_runs.jsonl")
    assert [row["stage"] for row in failed] == ["composite_validation"]
    assert "composition" in failed[0]["error"]
    assert not (tmp_path / "out" / "fixed_runs.jsonl").exists()


def test_native_termination_bounds_both_stages_of_a_composite_run(tmp_path):
    """The study's native termination (here max_iterations 2) caps the global and the polish stage,
    otherwise an unbounded native polish (1000 3-opt iterations) would make a smoke run last hours."""
    root = _repository(tmp_path / "repo")
    seen = []

    def gateway(**kwargs):
        if kwargs["protocol"].value == "native_termination":
            seen.append(copy.deepcopy(kwargs["params"]))
        return execute_preflighted(**kwargs)

    run_study_smoke(
        _plan(root), tmp_path / "out", problem_loader=_loader(), repository_root=root,
        replicates=1, gateway_executor=gateway,
    )
    assert len(seen) == len(COMPOSITES)
    for params in seen:
        assert params["global"]["max_iterations"] == 2
        assert params["polish"]["max_iterations"] == 2
