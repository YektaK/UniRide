"""C-12: study smoke runner (fixed and native kept apart, every row validated, no claims)."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.fair_pilot import _registry_executor
from academic_benchmark.protocol_registry import assert_single_pooling_group
from academic_benchmark.studies import build_study_plan
from academic_benchmark.studies.smoke import (
    SmokeReport,
    StudySmokeError,
    assert_no_ranking_words,
    run_study_smoke,
    select_smoke_rows,
    write_rows_file,
)
from uniride_core.algorithms.capabilities import ExecutionProtocol
from uniride_core.algorithms.tsplib_parser import parse_atsp_text

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BILDIRI_STUDY = "academic_benchmark/studies/bildiri2026/study.json"
FT53 = REPOSITORY_ROOT / "academic_benchmark" / "tsplib_data" / "ft53.atsp"


@dataclass
class _Problem:
    name: str
    dist_matrix: list
    problem_type: str = "atsp"
    optimal: float = 6905.0
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


def _ft53_problem(*, name: str = "ft53", tamper: bool = False) -> _Problem:
    parsed = parse_atsp_text(FT53.read_text(encoding="utf-8"), "ft53")
    matrix = [[float(v) for v in row] for row in parsed["explicit_matrix"]]
    if tamper:  # the solver sees a matrix that is not the committed artifact
        n = len(matrix)
        matrix = [[v + (1.0 if i != j else 0.0) for j, v in enumerate(row)] for i, row in enumerate(matrix)]
    return _Problem(name=name, dist_matrix=matrix)


def _loader(**kwargs):
    problem = _ft53_problem(**kwargs)
    return lambda name: problem


FT53_LEVELS = (50 * 1378, 250 * 1378)  # C-19: 50 and 250 full 2-opt scans of ft53


@pytest.fixture(scope="module")
def plan():
    """The Bildiri plan restricted to ft53 (the loader here serves ft53 only)."""
    full = build_study_plan(BILDIRI_STUDY, repository_root=REPOSITORY_ROOT)
    return dataclasses.replace(
        full,
        datasets=tuple(d for d in full.datasets if d.dataset_id == "tsplib-ft53"),
        rows=tuple(r for r in full.rows if r.dataset_id == "tsplib-ft53"),
    )


def _one_fixed_row(plan):
    row = next(
        r for r in select_smoke_rows(plan, replicates=1)
        if r.protocol is ExecutionProtocol.FIXED_BUDGET and r.algorithm_id == "Core-GWO-TSP-Pure"
    )
    return dataclasses.replace(plan, rows=(row,))


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="module")
def passed_run(plan, tmp_path_factory):
    out = tmp_path_factory.mktemp("smoke_ok") / "out"
    report = run_study_smoke(plan, out, problem_loader=_loader(), repository_root=REPOSITORY_ROOT, replicates=1)
    return report, out


def test_bildiri_ft53_lowest_budget_writes_two_valid_files(plan, passed_run):
    report, out = passed_run
    assert isinstance(report, SmokeReport) and report.status == "passed"
    fixed, native = _read(out / "fixed_runs.jsonl"), _read(out / "native_runs.jsonl")
    assert len(fixed) == len(plan.study.algorithm_ids) == 10 and len(native) == 10  # every study algorithm runs natively (A18 OQ-4 a)
    lowest = min(FT53_LEVELS)
    assert {row["evaluation_budget"] for row in fixed} == {lowest}
    assert {row["evaluation_budget"] for row in native} == {None}
    for row in fixed + native:
        assert row["validation_status"] == "passed"
        assert row["hamiltonian_validation"] == "passed"
        assert row["problem"] == "ft53" and row["smoke"] is True
    assert assert_single_pooling_group(fixed) == "fixed_budget"
    assert assert_single_pooling_group(native) == "native"
    assert not (out / "failed_runs.jsonl").exists()
    assert not any(out.glob("aggregate*"))  # smoke aggregates nothing


def test_smoke_report_text_has_no_ranking_words(passed_run):
    report, out = passed_run
    assert_no_ranking_words(report.text)
    assert (out / "smoke_report.txt").read_text(encoding="utf-8") == report.text
    assert "no claim" in report.text.lower()


@pytest.mark.parametrize("text", ["the best performing algorithm", "A is better than B", "winner: GWO", "Leaderboard"])
def test_ranking_words_are_refused(text):
    with pytest.raises(StudySmokeError, match="wording"):
        assert_no_ranking_words(text)


def test_smoke_caps_replicates_at_three_and_uses_lowest_level(plan):
    rows = select_smoke_rows(plan, replicates=10)
    assert max(r.replicate for r in rows) == 2
    assert {r.budget_level for r in rows if r.protocol is ExecutionProtocol.FIXED_BUDGET} == {
        min(FT53_LEVELS)
    }
    top = max(FT53_LEVELS)
    rows = select_smoke_rows(plan, replicates=1, budget_level=top)
    assert {r.budget_level for r in rows if r.protocol is ExecutionProtocol.FIXED_BUDGET} == {top}
    with pytest.raises(StudySmokeError, match="budget level"):
        select_smoke_rows(plan, replicates=1, budget_level=123)


def test_problem_name_mismatch_is_refused_before_any_run(plan, tmp_path):
    calls = []

    def gateway(**kwargs):
        calls.append(kwargs)
        return execute_preflighted(**kwargs)

    with pytest.raises(StudySmokeError, match="problem name"):
        run_study_smoke(
            _one_fixed_row(plan), tmp_path / "out", problem_loader=_loader(name="ft54"),
            repository_root=REPOSITORY_ROOT, replicates=1, gateway_executor=gateway,
        )
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_invalid_tour_from_executor_stops_and_records_failed_row(plan, tmp_path):
    seen = []

    def corrupt_registry(algorithm_id):
        executor = _registry_executor(algorithm_id)

        def run(problem, params, seed, replicate):
            result = executor(problem, params, seed, replicate)
            seen.append(algorithm_id)
            return dataclasses.replace(result, tour=[result.tour[0]] * len(result.tour))

        return run

    report = run_study_smoke(
        plan, tmp_path / "out", problem_loader=_loader(), repository_root=REPOSITORY_ROOT,
        replicates=1, registry_getter=corrupt_registry,
    )
    assert report.status == "failed" and len(seen) == 1  # stopped at the first failure
    failed = _read(tmp_path / "out" / "failed_runs.jsonl")
    assert len(failed) == 1
    row = failed[0]
    assert row["record_kind"] == "failed_run" and row["validation_status"] == "failed"
    assert row["stage"] == "execution"
    for key in ("algorithm_id", "problem", "seed", "replicate", "exception_category", "consumed_budget"):
        assert key in row
    assert not (tmp_path / "out" / "fixed_runs.jsonl").exists()
    assert not any((tmp_path / "out").glob("aggregate*"))
    assert "failed" in report.text


def test_result_that_passes_the_pilot_check_but_fails_independent_validator(plan, tmp_path):
    """The solver saw a shifted matrix: the pilot record check (same matrix) passes, the artifact-based
    Hamiltonian validator does not."""
    report = run_study_smoke(
        _one_fixed_row(plan), tmp_path / "out", problem_loader=_loader(tamper=True),
        repository_root=REPOSITORY_ROOT, replicates=1,
    )
    assert report.status == "failed"
    failed = _read(tmp_path / "out" / "failed_runs.jsonl")
    assert [row["stage"] for row in failed] == ["hamiltonian_validation"]
    assert failed[0]["consumed_budget"] is not None
    assert not (tmp_path / "out" / "fixed_runs.jsonl").exists()


def test_repository_output_is_refused(plan):
    with pytest.raises(Exception, match="repository"):
        run_study_smoke(
            _one_fixed_row(plan), REPOSITORY_ROOT / "smoke_must_not_exist", problem_loader=_loader(),
            repository_root=REPOSITORY_ROOT, replicates=1,
        )
    assert not (REPOSITORY_ROOT / "smoke_must_not_exist").exists()


def test_file_writer_refuses_mixed_levels_and_pooling_groups(tmp_path):
    fixed = {"comparison_regime": "fixed_evaluation_budget", "protocol_version": "uniride-fair-tsp-v2"}
    native = {"comparison_regime": "algorithm_native_termination", "protocol_version": "uniride-native-tsp-v1"}
    write_rows_file(tmp_path / "a.jsonl", [dict(fixed, evaluation_budget=100)], expected_group="fixed_budget")
    with pytest.raises(StudySmokeError, match="budget level"):
        write_rows_file(
            tmp_path / "b.jsonl",
            [dict(fixed, evaluation_budget=100), dict(fixed, evaluation_budget=500)],
            expected_group="fixed_budget",
        )
    with pytest.raises(ValueError, match="pooled"):
        write_rows_file(
            tmp_path / "c.jsonl", [dict(fixed, evaluation_budget=100), dict(native, evaluation_budget=None)],
            expected_group="fixed_budget",
        )
    with pytest.raises(StudySmokeError, match="group"):
        write_rows_file(tmp_path / "d.jsonl", [dict(native, evaluation_budget=None)], expected_group="fixed_budget")
    assert not (tmp_path / "b.jsonl").exists() and not (tmp_path / "c.jsonl").exists()
    assert not (tmp_path / "d.jsonl").exists()
