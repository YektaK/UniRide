"""WP-E8 Task 3: the ``exact_reference_v1`` row contract (``academic_benchmark.exact_reference.rows``)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_benchmark.contracts.export_schemas import check_schemas, render_schemas
from academic_benchmark.exact_reference import protocol
from academic_benchmark.exact_reference.rows import ExactReferenceRowV1

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "academic_benchmark" / "schemas"
SHA = "a" * 64
OPTIONS = "mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 lim:time=600"


def tsp_row(**changes) -> dict:
    row = {
        "row_schema_version": "uniride-exact-reference-row/v1", "protocol": "exact_reference_v1",
        "solution_kind": "hamiltonian_cycle", "problem_contract": "TSP", "instance_id": "eil51", "stage": None,
        "solver_role": "primary", "solver_name": "gurobi", "solver_version": "Gurobi 13.0.3", "option_string": OPTIONS,
        "status": "optimal", "stop_reason": "optimal", "lb": 426, "ub": 426, "reference_optimum": 426,
        "reference_optimum_source": "tsplib", "timing_dependent": False, "wall_seconds": 1.3, "ub_validated": False,
        "ub_validation_basis": "not_validated",
        "source": {"results_dir": "docs/paper/results/tsplib-exact-reference/stage1-verification", "manifest_kind": "tsp_reference",
                   "manifest_sha256": SHA, "work_package": "WP-E7", "git_commit": "0123456789abcdef0123456789abcdef01234567"},
    }
    row.update(changes)
    return row


def wave_row(**changes) -> dict:
    row = tsp_row(solution_kind="vehicle_routes", problem_contract="uniride_wave", instance_id="2026-10-05_R50/2026-10-05:pickup:765",
                  stage="stage1", reference_optimum=None, reference_optimum_source=None, lb=2, ub=2,
                  ub_validation_basis="certified_by_producing_run")
    row["source"] = dict(row["source"], manifest_kind="wave_campaign", work_package="WP-E3",
                         results_dir="docs/paper/results/week-2026-10-05-exact/wp-e3-goal1-single")
    row.update(changes)
    return row


def test_a_valid_hamiltonian_row_and_a_valid_wave_row_are_accepted():
    assert ExactReferenceRowV1.model_validate(tsp_row()).solution_kind == "hamiltonian_cycle"
    assert ExactReferenceRowV1.model_validate(wave_row()).stage == "stage1"


@pytest.mark.parametrize("key, value", [
    ("gap_to_LB", 0.0), ("gap_to_reference_optimum", 0), ("gap_to_reference", 0), ("gap_pct", 1.0),
    ("algorithm_id", "Core-GWO-TSP-Pure"), ("evaluation_budget", 1000),
])
def test_forbidden_keys_are_rejected(key, value):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExactReferenceRowV1.model_validate(tsp_row(**{key: value}))


def test_the_model_has_no_gap_algorithm_or_budget_field():
    names = set(ExactReferenceRowV1.model_fields)
    assert not [n for n in names if n.startswith("gap") or "gap_" in n]
    assert "algorithm_id" not in names and "evaluation_budget" not in names


def test_best_solutions_cannot_be_a_reference_source():
    with pytest.raises(ValidationError):
        ExactReferenceRowV1.model_validate(tsp_row(reference_optimum_source="best_solutions"))


def test_reference_optimum_and_source_are_both_set_or_both_null():
    with pytest.raises(ValidationError, match="both set or both null"):
        ExactReferenceRowV1.model_validate(tsp_row(reference_optimum_source=None))
    with pytest.raises(ValidationError, match="both set or both null"):
        ExactReferenceRowV1.model_validate(tsp_row(reference_optimum=None))
    ExactReferenceRowV1.model_validate(tsp_row(reference_optimum=None, reference_optimum_source=None))


@pytest.mark.parametrize("lb, ub", [(425, 426), (400, 426), (427, 426)])
def test_optimal_needs_a_closed_gap(lb, ub):
    with pytest.raises(ValidationError, match="ub - lb < 1|both lb and ub"):
        ExactReferenceRowV1.model_validate(tsp_row(lb=lb, ub=ub))


def test_optimal_needs_both_bounds():
    for changes in ({"lb": None}, {"ub": None}):
        with pytest.raises(ValidationError, match="both lb and ub"):
            ExactReferenceRowV1.model_validate(tsp_row(**changes))


def test_wall_limit_without_timing_dependent_is_rejected():
    changes = dict(status="feasible_with_gap", stop_reason="wall_limit", lb=400, ub=430, timing_dependent=False)
    with pytest.raises(ValidationError, match="timing_dependent"):
        ExactReferenceRowV1.model_validate(tsp_row(**changes))
    ExactReferenceRowV1.model_validate(tsp_row(**dict(changes, timing_dependent=True)))
    with pytest.raises(ValidationError, match="timing_dependent"):
        ExactReferenceRowV1.model_validate(tsp_row(**dict(changes, stop_reason="other_limit")))


def test_vehicle_routes_with_a_tsp_contract_is_rejected_and_the_reverse():
    with pytest.raises(ValidationError, match="uniride_wave"):
        ExactReferenceRowV1.model_validate(wave_row(problem_contract="TSP"))
    with pytest.raises(ValidationError, match="TSP or ATSP"):
        ExactReferenceRowV1.model_validate(tsp_row(problem_contract="uniride_wave"))
    with pytest.raises(ValidationError, match="TSP or ATSP"):
        ExactReferenceRowV1.model_validate(tsp_row(problem_contract="uniride_wave", stage="stage1"))


def test_a_hamiltonian_row_has_no_stage_and_a_wave_row_needs_one():
    with pytest.raises(ValidationError, match="no stage"):
        ExactReferenceRowV1.model_validate(tsp_row(stage="stage1"))
    with pytest.raises(ValidationError, match="needs a stage"):
        ExactReferenceRowV1.model_validate(wave_row(stage=None))


def test_status_stop_reason_and_stage_vocabularies_are_the_protocol_ones():
    schema = json.loads(render_schemas()["exact-reference-row-v1.schema.json"])
    props = schema["properties"]
    assert set(props["status"]["enum"]) == set(protocol.STATUS_LABELS)
    stop = [p for p in props["stop_reason"]["anyOf"] if "enum" in p][0]["enum"]
    assert set(stop) == set(protocol.STOP_REASONS)
    stage = [p for p in props["stage"]["anyOf"] if "enum" in p][0]["enum"]
    assert tuple(stage) == protocol.STAGES
    assert schema["properties"]["protocol"]["const"] == protocol.PROTOCOL_ID


def test_optimal_is_never_inferred_from_ub_equal_to_the_reference():
    row = ExactReferenceRowV1.model_validate(tsp_row(status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True,
                                                      lb=400, ub=426, reference_optimum=426))
    assert row.status == "feasible_with_gap" and row.ub == row.reference_optimum
    with pytest.raises(ValidationError):  # nor does the equality rescue an optimal row without a closed gap
        ExactReferenceRowV1.model_validate(tsp_row(lb=400, ub=426, reference_optimum=426))


def test_feasible_with_gap_and_bound_only_rules():
    ExactReferenceRowV1.model_validate(tsp_row(status="feasible_with_gap", stop_reason="work_limit", lb=400, ub=430))
    with pytest.raises(ValidationError, match="exceeds"):
        ExactReferenceRowV1.model_validate(tsp_row(status="feasible_with_gap", stop_reason="work_limit", lb=431, ub=430))
    with pytest.raises(ValidationError, match="incumbent"):
        ExactReferenceRowV1.model_validate(tsp_row(status="feasible_with_gap", stop_reason="work_limit", lb=400, ub=None))
    with pytest.raises(ValidationError, match="ub must be null"):
        ExactReferenceRowV1.model_validate(tsp_row(status="bound_only", stop_reason="work_limit", lb=400, ub=430))
    ExactReferenceRowV1.model_validate(tsp_row(status="bound_only", stop_reason="work_limit", lb=400, ub=None))
    ExactReferenceRowV1.model_validate(wave_row(status="infeasible_proven", stop_reason="infeasible", lb=None, ub=None))


def test_ub_validated_requires_the_independent_validator_and_wave_rows_never_are():
    ok = ExactReferenceRowV1.model_validate(tsp_row(ub_validated=True, ub_validation_basis="independent_hamiltonian_validator"))
    assert ok.ub_validated
    with pytest.raises(ValidationError, match="exactly when"):
        ExactReferenceRowV1.model_validate(tsp_row(ub_validated=True, ub_validation_basis="not_validated"))
    with pytest.raises(ValidationError, match="exactly when"):
        ExactReferenceRowV1.model_validate(tsp_row(ub_validated=False, ub_validation_basis="independent_hamiltonian_validator"))
    with pytest.raises(ValidationError, match="never validated|only a hamiltonian_cycle"):
        ExactReferenceRowV1.model_validate(wave_row(ub_validated=True, ub_validation_basis="independent_hamiltonian_validator"))
    with pytest.raises(ValidationError, match="certified_by_producing_run"):
        ExactReferenceRowV1.model_validate(wave_row(ub_validation_basis="not_validated"))
    with pytest.raises(ValidationError, match="independent validator or not validated"):
        ExactReferenceRowV1.model_validate(tsp_row(ub_validation_basis="certified_by_producing_run"))


def test_wave_rows_carry_no_reference_optimum():
    with pytest.raises(ValidationError, match="published reference"):
        ExactReferenceRowV1.model_validate(wave_row(reference_optimum=3, reference_optimum_source="tsplib"))


@pytest.mark.parametrize("field, bad", [
    ("protocol", "exact_reference_v2"), ("protocol", "fixed_evaluation_budget"), ("row_schema_version", "uniride-exact-reference-row/v2"),
    ("solver_role", "tertiary"), ("status", "not_run"), ("status", "OPTIMAL"), ("stop_reason", "timeout"),
    ("lb", 426.0), ("ub", True), ("ub", "426"), ("timing_dependent", 0), ("wall_seconds", -1.0), ("wall_seconds", float("nan")),
    ("solver_name", ""), ("instance_id", ""),
])
def test_invalid_field_values_are_rejected(field, bad):
    with pytest.raises(ValidationError):
        ExactReferenceRowV1.model_validate(tsp_row(**{field: bad}))


def test_source_must_be_a_repository_relative_path_with_a_sha256():
    for bad in ("C:/results/x", "/abs/results", "../outside", ""):
        with pytest.raises(ValidationError):
            ExactReferenceRowV1.model_validate(tsp_row(source=dict(tsp_row()["source"], results_dir=bad)))
    with pytest.raises(ValidationError):
        ExactReferenceRowV1.model_validate(tsp_row(source=dict(tsp_row()["source"], manifest_sha256="xyz")))
    with pytest.raises(ValidationError):
        ExactReferenceRowV1.model_validate(tsp_row(source=dict(tsp_row()["source"], manifest_kind="union_day_v1")))


def test_private_data_cannot_enter_a_row():
    with pytest.raises(ValidationError, match="absolute path"):
        ExactReferenceRowV1.model_validate(tsp_row(option_string="--cache C:\\Users\\someone\\file"))
    with pytest.raises(ValidationError, match="e-mail"):
        ExactReferenceRowV1.model_validate(tsp_row(solver_version="x@y.org"))


def test_protocol_literal_equals_the_protocol_module_constant():
    assert ExactReferenceRowV1.model_validate(tsp_row()).protocol == protocol.PROTOCOL_ID


def test_rows_are_frozen_and_serialise_deterministically():
    row = ExactReferenceRowV1.model_validate(tsp_row())
    with pytest.raises(ValidationError):
        row.status = "bound_only"
    assert row.model_dump_json() == ExactReferenceRowV1.model_validate(tsp_row()).model_dump_json()


def test_schema_snapshot_is_current_and_the_three_existing_snapshots_are_in_the_check():
    assert check_schemas() == []
    rendered = render_schemas()
    assert list(rendered) == ["study-v1.schema.json", "dataset-v1.schema.json", "run-v1.schema.json",
                              "exact-reference-row-v1.schema.json", "analysis-plan-v1.schema.json",
                              "run-index-v2.schema.json"]
    schema = json.loads(rendered["exact-reference-row-v1.schema.json"])
    assert schema["$id"] == "uniride-exact-reference-row/v1" and schema["additionalProperties"] is False
    assert not [k for k in schema["properties"] if k.startswith("gap")]
    assert json.loads((SCHEMAS / "exact-reference-row-v1.schema.json").read_text(encoding="utf-8")) == schema
