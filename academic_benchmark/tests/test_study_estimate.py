"""Gate D, D-04b1: cost estimator (plan 2026-10-23, item D-04b; DECISION_LOG A18).

No real timing: the clock and the solver are injected. A fake solver advances a fake clock by 1 ms per evaluation, so
the estimate of every fixed cell must equal its evaluation upper bound times 1 ms. The two study profiles are the real
``study.json`` files (committed dataset artifacts only; ``tsplib.db`` is never opened).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from academic_benchmark.studies import build_study_plan
from academic_benchmark.studies.estimate import (
    PROVISIONAL_LABEL,
    EstimateError,
    NativeLimits,
    RunPlanSpec,
    SolverOutcome,
    build_cells,
    calibrate,
    estimate,
    main,
    render_report,
    report_payload,
    write_outputs,
)
from academic_benchmark.studies.smoke import assert_no_ranking_words
from uniride_core.algorithms.capabilities import ExecutionProtocol

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BILDIRI = "academic_benchmark/studies/bildiri2026/study.json"
YAEM = "academic_benchmark/studies/yaem2026/study.json"
MS = 0.001
MEMETIC_GWO_HHO = ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt")


@pytest.fixture(scope="module")
def bildiri():
    return build_study_plan(BILDIRI, repository_root=REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def yaem():
    return build_study_plan(YAEM, repository_root=REPOSITORY_ROOT)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def fake_solver(clock: FakeClock, calls: list, *, ms_per_eval: float = 1.0, polish_share: float = 0.5, iterations: int = 100):
    """Every evaluation costs ``ms_per_eval`` ms of fake time. Memetic 2-opt IDs report ``polish_share`` of them as polish."""

    def solve(row, params):
        calls.append((row, params))
        fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
        evaluations = row.budget_level if fixed else 10
        polish = int(evaluations * polish_share) if "Memetic-2opt" in row.algorithm_id else 0
        clock.now += evaluations * ms_per_eval / 1000.0
        return SolverOutcome(
            objective_evaluations=evaluations,
            iterations=iterations if fixed else 2,
            polish_evaluations=polish,
            termination_reason="evaluation_budget_exhausted" if fixed else "max_iterations",
        )

    return solve


def stub_provenance():
    return {"commit": "c" * 40, "dirty": False, "machine": {"cpu": "test-cpu", "python": "3.x"}}


# ----------------------------------------------------------------------------------------- evaluation upper bounds
def test_bildiri_evaluation_bounds_equal_the_plan_section_6_arithmetic(bildiri):
    study_json = json.loads((REPOSITORY_ROOT / BILDIRI).read_text(encoding="utf-8"))
    table = study_json["scaled_fixed_budget_levels"]["levels_by_dataset"]
    cells = [c for c in build_cells(bildiri, RunPlanSpec(run_count=1)) if c.protocol is ExecutionProtocol.FIXED_BUDGET]
    per_dataset = {}
    for cell in cells:
        if cell.algorithm_id == "Core-TwoOpt-TSP":
            per_dataset[cell.dataset_id] = per_dataset.get(cell.dataset_id, 0) + cell.evaluation_upper_bound
    assert per_dataset == {key: sum(levels) for key, levels in table.items()}
    # the figures written in plan section 6 (hand arithmetic, not read from the profile)
    assert per_dataset == {
        "tsplib-berlin52": 397_800, "tsplib-eil51": 382_500, "tsplib-st70": 724_500,
        "tsplib-kroa100": 1_485_000, "tsplib-rd100": 1_485_000, "tsplib-eil76": 855_000, "tsplib-ft53": 413_400,
    }
    assert sum(per_dataset.values()) == 5_743_200  # per algorithm and replicate, both levels, 7 instances
    # 10 algorithms x 30 replicates: about 1.72e9 in the fixed protocol
    thirty = [c for c in build_cells(bildiri, RunPlanSpec(run_count=30)) if c.protocol is ExecutionProtocol.FIXED_BUDGET]
    assert sum(c.evaluation_upper_bound for c in thirty) == 1_722_960_000
    assert all(c.evaluation_upper_bound == c.level * c.runs for c in thirty)
    assert {c.level_index for c in thirty} == {0, 1}


def test_native_cells_have_no_evaluation_bound(bildiri):
    native = [c for c in build_cells(bildiri, RunPlanSpec(run_count=3)) if c.protocol is ExecutionProtocol.NATIVE_TERMINATION]
    assert native and all(c.evaluation_upper_bound is None and c.level_index is None for c in native)
    only_fixed = build_cells(bildiri, RunPlanSpec(run_count=3, include_native=False))
    assert all(c.protocol is ExecutionProtocol.FIXED_BUDGET for c in only_fixed)


# --------------------------------------------------------------------------------------- levels across instances
def test_plan_that_mixes_levels_across_instances_by_raw_value_is_refused(bildiri):
    # 66300 is the first level of berlin52 only; as a raw value over all instances it would mix level indices
    with pytest.raises(EstimateError, match="raw"):
        build_cells(bildiri, RunPlanSpec(run_count=1, raw_levels=(66300,)))
    with pytest.raises(EstimateError, match="raw"):
        build_cells(bildiri, RunPlanSpec(run_count=1, raw_levels=(66300,), dataset_ids=("tsplib-berlin52", "tsplib-eil51")))
    # one instance, one of its own levels: unambiguous
    cells = build_cells(
        bildiri, RunPlanSpec(run_count=1, raw_levels=(66300,), dataset_ids=("tsplib-berlin52",), include_native=False)
    )
    assert {(c.dataset_id, c.level_index, c.level) for c in cells} == {("tsplib-berlin52", 0, 66300)}
    # by level index the same plan is fine for every instance
    by_index = build_cells(bildiri, RunPlanSpec(run_count=1, level_indices=(1,), include_native=False))
    assert {c.level_index for c in by_index} == {1}
    with pytest.raises(EstimateError, match="level index"):
        build_cells(bildiri, RunPlanSpec(run_count=1, level_indices=(2,)))


# ------------------------------------------------------------------------------------------------ the estimate
def test_with_one_millisecond_per_evaluation_the_estimate_equals_bound_times_one_millisecond(bildiri):
    clock, calls = FakeClock(), []
    spec = RunPlanSpec(run_count=30)
    cells = build_cells(bildiri, spec)
    calibration = calibrate(bildiri, fake_solver(clock, calls), clock, spec=spec)
    result = estimate(cells, calibration)
    fixed = [c for c in cells if c.protocol is ExecutionProtocol.FIXED_BUDGET]
    assert result.fixed_runs == len(fixed) * 30
    assert result.fixed_evaluation_upper_bound == sum(c.evaluation_upper_bound for c in fixed) == 1_722_960_000
    assert result.fixed_seconds == pytest.approx(result.fixed_evaluation_upper_bound * MS, rel=1e-9)
    for entry in result.cells:
        if entry.cell.protocol is ExecutionProtocol.FIXED_BUDGET:
            assert entry.seconds == pytest.approx(entry.cell.evaluation_upper_bound * MS, rel=1e-9)


def test_seconds_per_evaluation_is_interpolated_between_smallest_and_largest_instance(bildiri):
    clock, calls = FakeClock(), []

    def solve(row, params):
        calls.append(row)
        # 1 ms per evaluation on the smallest instance (eil51), 3 ms on the largest (n = 100)
        ms = 1.0 if row.dataset_id == "tsplib-eil51" else 3.0 if row.dataset_id in ("tsplib-kroa100", "tsplib-rd100") else None
        assert ms is not None, "only the smallest and the largest instance are calibrated"
        clock.now += row.budget_level * ms / 1000.0 if row.budget_level else 0.01
        return SolverOutcome(objective_evaluations=row.budget_level or 10, iterations=5, termination_reason="x")

    spec = RunPlanSpec(run_count=1, algorithm_ids=("Core-TwoOpt-TSP",), include_native=False)
    calibration = calibrate(bildiri, solve, clock, spec=spec)
    assert {r.dataset_id for r in calls} == {"tsplib-eil51", "tsplib-kroa100"}  # ties on n = 100 go to the first listed
    assert {r.budget_level for r in calls} == {63750, 247500}  # the lowest level of each
    rate = calibration.seconds_per_evaluation("Core-TwoOpt-TSP", 51), calibration.seconds_per_evaluation("Core-TwoOpt-TSP", 100)
    assert rate == pytest.approx((0.001, 0.003))
    assert calibration.seconds_per_evaluation("Core-TwoOpt-TSP", 76) == pytest.approx(0.001 + (76 - 51) / (100 - 51) * 0.002)


def test_default_slice_runs_one_replicate_per_algorithm_and_warms_up_the_smallest_instance(bildiri):
    clock, calls = FakeClock(), []
    spec = RunPlanSpec(run_count=3, include_native=False)
    calibrate(bildiri, fake_solver(clock, calls), clock, spec=spec)
    fixed_algorithms = len(bildiri.study.algorithm_ids)
    assert len(calls) == fixed_algorithms * 3  # warm-up + small + large, each a single replicate
    assert all(row.replicate == 0 for row, _ in calls)
    assert 1237500 not in {row.budget_level for row, _ in calls}  # the 250x probe is a separate, explicit flag
    calls.clear()
    calibrate(bildiri, fake_solver(clock, calls), clock, spec=spec, warmup=False)
    assert len(calls) == fixed_algorithms * 2


# ------------------------------------------------------------------------------- provisional native/composite limits
def test_provisional_composite_limit_is_always_labelled_provisional(yaem):
    clock, calls = FakeClock(), []
    limits = NativeLimits(global_iterations=3, polish_iterations=4)
    spec = RunPlanSpec(run_count=2)
    cells = build_cells(yaem, spec)
    calibration = calibrate(yaem, fake_solver(clock, calls), clock, spec=spec, native_limits=limits)
    # the limits really reach the stage parameters of the native composite rows
    native_composites = [(r, p) for r, p in calls if r.protocol is ExecutionProtocol.NATIVE_TERMINATION and "3opt" in r.algorithm_id.lower()]
    assert native_composites
    for _row, params in native_composites:
        assert params["global"]["max_iterations"] == 3 and params["polish"]["max_iterations"] == 4
    text = render_report(yaem, spec, cells, calibration, estimate(cells, calibration), stub_provenance())
    limit_lines = [line for line in text.splitlines() if "native limit" in line.lower()]
    assert any("Memetic-3opt" in line for line in limit_lines) and any("Memetic-ALNS" in line for line in limit_lines)
    assert limit_lines and all(PROVISIONAL_LABEL in line for line in limit_lines)
    native_time_lines = [line for line in text.splitlines() if "native" in line.lower() and "s/iteration" in line.lower()]
    assert native_time_lines and all(PROVISIONAL_LABEL in line for line in native_time_lines)
    payload = report_payload(yaem, spec, cells, calibration, estimate(cells, calibration), stub_provenance())
    assert PROVISIONAL_LABEL == "PROVISIONAL, NOT A SCIENTIFIC SETTING"
    assert payload["native_limits"]["label"] == PROVISIONAL_LABEL
    assert all(item["limits_label"] == PROVISIONAL_LABEL for item in payload["native_calibration"])
    assert payload["native_estimate"]["label"] == PROVISIONAL_LABEL


def test_report_carries_planning_banner_commit_machine_and_no_ranking_words(bildiri):
    clock, calls = FakeClock(), []
    spec = RunPlanSpec(run_count=3)
    cells = build_cells(bildiri, spec)
    calibration = calibrate(bildiri, fake_solver(clock, calls), clock, spec=spec)
    text = render_report(bildiri, spec, cells, calibration, estimate(cells, calibration), stub_provenance())
    assert "planning numbers, not evidence" in text.lower()
    assert "c" * 40 in text and "test-cpu" in text
    assert_no_ranking_words(text)


# ------------------------------------------------------------------------------------------ memetic GWO/HHO report
def test_memetic_report_gives_iterations_evaluations_per_iteration_and_projection_at_250x(bildiri):
    clock, calls = FakeClock(), []
    spec = RunPlanSpec(run_count=1, include_native=False)
    cells = build_cells(bildiri, spec)
    calibration = calibrate(bildiri, fake_solver(clock, calls, polish_share=0.75, iterations=100), clock, spec=spec)
    rows = [m for m in calibration.memetic if m.algorithm_id in MEMETIC_GWO_HHO]
    assert {m.algorithm_id for m in rows} == set(MEMETIC_GWO_HHO)
    assert {m.dataset_id for m in rows} == {"tsplib-eil51", "tsplib-kroa100"}
    small = next(m for m in rows if m.dataset_id == "tsplib-eil51" and m.algorithm_id == MEMETIC_GWO_HHO[0])
    assert small.iterations == 100
    assert small.objective_evaluations_per_iteration == pytest.approx((63750 - int(63750 * 0.75)) / 100)
    assert small.polish_evaluations_per_iteration == pytest.approx(int(63750 * 0.75) / 100)
    assert small.evaluations_per_iteration == pytest.approx(63750 / 100)
    assert small.top_level == 318750
    assert small.projected_iterations_at_top_level == pytest.approx(318750 / (63750 / 100))  # level / evaluations per iteration
    assert small.max_iterations == 60000 and small.max_no_improvement == 60000
    text = render_report(bildiri, spec, cells, calibration, estimate(cells, calibration), stub_provenance())
    assert "projected iterations" in text.lower()


def test_250x_probe_is_a_separate_flag_and_runs_each_memetic_gwo_hho_id_once_on_the_largest_instance(bildiri):
    clock, calls = FakeClock(), []
    spec = RunPlanSpec(run_count=1, include_native=False)
    calibration = calibrate(bildiri, fake_solver(clock, calls), clock, spec=spec, probe_250x=True)
    probes = [(r, p) for r, p in calls if r.budget_level == 1237500]
    assert sorted(r.algorithm_id for r, _ in probes) == sorted(MEMETIC_GWO_HHO)
    assert {r.dataset_id for r, _ in probes} == {"tsplib-kroa100"}
    assert {r.replicate for r, _ in probes} == {0}
    assert sorted(p.algorithm_id for p in calibration.probes) == sorted(MEMETIC_GWO_HHO)
    for probe in calibration.probes:
        assert probe.level == 1237500
        assert probe.consumed_evaluations == 1237500 and probe.limit_binds_before_budget is False


def test_250x_probe_reports_a_limit_that_binds_before_the_budget(bildiri):
    clock = FakeClock()

    def solve(row, params):
        clock.now += 0.001
        stops_early = row.budget_level == 1237500
        return SolverOutcome(
            objective_evaluations=500000 if stops_early else row.budget_level, iterations=60000 if stops_early else 10,
            polish_evaluations=100 if "Memetic-2opt" in row.algorithm_id else 0,
            termination_reason="max_iterations" if stops_early else "evaluation_budget_exhausted",
        )

    spec = RunPlanSpec(run_count=1, include_native=False, algorithm_ids=MEMETIC_GWO_HHO)
    cells = build_cells(bildiri, spec)
    calibration = calibrate(bildiri, solve, clock, spec=spec, probe_250x=True)
    assert all(p.limit_binds_before_budget and p.termination_reason == "max_iterations" for p in calibration.probes)
    text = render_report(bildiri, spec, cells, calibration, estimate(cells, calibration), stub_provenance())
    assert "binds before the budget" in text.lower()


# ------------------------------------------------------------------------------------------------ output location
def test_in_repository_output_is_refused_and_nothing_is_created(tmp_path):
    inside = REPOSITORY_ROOT / "estimate_out_must_not_exist"
    with pytest.raises(EstimateError, match="inside the repository"):
        write_outputs(inside, "text", {"a": 1}, repository_root=REPOSITORY_ROOT)
    assert not inside.exists()
    inside_sub = REPOSITORY_ROOT / "docs" / "estimate_out_must_not_exist"
    with pytest.raises(EstimateError, match="inside the repository"):
        write_outputs(inside_sub, "text", {"a": 1}, repository_root=REPOSITORY_ROOT)
    assert not inside_sub.exists()
    written = write_outputs(tmp_path / "out", "text\n", {"a": 1}, repository_root=REPOSITORY_ROOT)
    assert sorted(Path(p).name for p in written) == ["estimate.json", "estimate.txt"]
    with pytest.raises(EstimateError, match="not empty"):
        write_outputs(tmp_path / "out", "text\n", {"a": 1}, repository_root=REPOSITORY_ROOT)


def test_cli_refuses_in_repository_output_before_running_any_solver(capsys):
    inside = REPOSITORY_ROOT / "estimate_cli_out_must_not_exist"
    code = main(["--study", BILDIRI, "--out", str(inside)])
    assert code == 2 and not inside.exists()
    assert "inside the repository" in capsys.readouterr().err
