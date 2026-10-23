"""Gate D, D-06: gap columns against the exact reference (plan 2026-10-23 section 3, D-06; DECISION_LOG E09, E10, E12, A18).

The response of both analysis plans is the relative gap to the exact reference in percent (A18 OQ-6 a). The reference comes from the
``exact_reference_v1`` reader and is joined to heuristic rows by the normalised TSPLIB problem name (A17 C-11), never by file or
dataset id. Exact rows stay references: they are never pooled, ranked, averaged or tested. A row whose instance has no proven
exact optimum gets no gap (null with a reason), never the database value or the published value silently.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path

import pytest

from academic_benchmark.analysis import gaps
from academic_benchmark.analysis.gaps import (
    GAP_COLUMN,
    GAP_UNIT,
    GapColumnError,
    ReferenceCrossCheckError,
    add_gap_columns,
    build_reference_table,
    cross_check_problem_optimal,
    cross_check_study_datasets,
    load_reference_table,
    relative_gap_percent,
)
from academic_benchmark.exact_reference.reader import ExactReferenceSet
from academic_benchmark.exact_reference.rows import ExactReferenceRowV1
from academic_benchmark.studies.service import load_study_with_plan, resolve_datasets

REPO = Path(__file__).resolve().parents[2]
FAIR_V2 = "uniride-fair-tsp-v2"
NATIVE = "uniride-native-tsp-v1"
SHA = "a" * 64
STUDY_PATHS = {
    "bildiri2026": "academic_benchmark/studies/bildiri2026/study.json",
    "yaem2026": "academic_benchmark/studies/yaem2026/study.json",
}
BILDIRI_INSTANCES = {"berlin52", "eil51", "st70", "kroa100", "rd100", "eil76", "ft53"}


# ---------------------------------------------------------------- fixtures
def exact_row(instance="eil51", *, value=426, role="primary", status="optimal", contract="TSP", published=None,
              validated=True, solver="Gurobi", lb=None):
    published = value if published is None else published
    optimal = status == "optimal"
    return ExactReferenceRowV1(
        row_schema_version="uniride-exact-reference-row/v1", protocol="exact_reference_v1",
        solution_kind="hamiltonian_cycle", problem_contract=contract, instance_id=instance, stage=None, solver_role=role,
        solver_name=solver, solver_version="12.0", option_string="Threads=1",
        status=status, stop_reason="optimal" if optimal else "wall_limit",
        lb=value if lb is None and optimal else lb, ub=value, reference_optimum=published, reference_optimum_source="tsplib",
        timing_dependent=not optimal, wall_seconds=1.0, ub_validated=validated and role == "primary",
        ub_validation_basis="independent_hamiltonian_validator" if validated and role == "primary" else "not_validated",
        source={"results_dir": "docs/paper/results/tsplib-exact-reference/stage1-verification", "manifest_kind": "tsp_reference",
                "manifest_sha256": SHA, "work_package": "WP-E7", "git_commit": "abcdef1"},
    )


def exact_set(*rows, kind="tsp_reference", results_dir="docs/paper/results/tsplib-exact-reference/stage1-verification"):
    return ExactReferenceSet(results_dir=results_dir, manifest_kind=kind, manifest_sha256=SHA, manifest={}, rows=list(rows))


def table_of(*rows):
    return build_reference_table([exact_set(*rows)])


def heuristic_row(problem="eil51", cost=426.0, **extra):
    row = {
        "record_kind": "primary", "protocol_version": FAIR_V2, "comparison_regime": "fixed_evaluation_budget",
        "problem": problem, "problem_type": "TSP", "algorithm_id": "Core-GA-TSP", "replicate": 0, "seed": 7,
        "evaluation_budget": 63750, "objective_cost": float(cost), "validation_status": "passed",
        "optimum": 426.0, "optimum_source": "problem.optimal", "gap_pct": 0.0,
    }
    row.update(extra)
    return row


@pytest.fixture(scope="module")
def plan():
    loaded = load_study_with_plan(STUDY_PATHS["bildiri2026"], repository_root=REPO, mode="smoke")
    assert loaded.analysis_plan.plan is not None
    return loaded.analysis_plan.plan


@pytest.fixture(scope="module")
def real_table():
    return load_reference_table(REPO)


# ---------------------------------------------------------------- the gap value
def test_gap_of_a_row_that_reaches_the_reference_is_zero(plan):
    table = table_of(exact_row("eil51", value=426))
    (out,) = add_gap_columns([heuristic_row("eil51", 426)], table, plan=plan)
    assert out[GAP_COLUMN] == 0.0
    assert out["gap_unit"] == GAP_UNIT == "percent"
    assert out["exact_reference_value"] == 426
    assert out["gap_missing_reason"] is None


def test_gap_is_the_relative_difference_in_percent(plan):
    table = table_of(exact_row("eil51", value=426))
    (out,) = add_gap_columns([heuristic_row("eil51", 447)], table, plan=plan)
    assert out[GAP_COLUMN] == pytest.approx((447 - 426) / 426 * 100.0, rel=0, abs=1e-12)
    assert relative_gap_percent(447, 426) == out[GAP_COLUMN]


def test_the_unit_comes_from_the_analysis_plan(plan):
    assert plan.response.unit == "percent" and plan.response.variable == "relative_gap_to_exact_reference"
    assert plan.exact_reference.reader == "exact_reference_v1"
    assert plan.exact_reference.join_identity == "normalised_tsplib_problem_name"
    assert plan.exact_reference.pooling == "reference_only"


@pytest.mark.parametrize("cost, ref", [(float("nan"), 426), (float("inf"), 426), (-1.0, 426), (True, 426), (100.0, 0), (100.0, -5)])
def test_gap_arithmetic_refuses_non_finite_negative_and_non_positive_inputs(cost, ref):
    with pytest.raises(GapColumnError):
        relative_gap_percent(cost, ref)


def test_a_cost_below_the_proven_optimum_is_reported_not_hidden(plan):
    table = table_of(exact_row("eil51", value=426))
    (out,) = add_gap_columns([heuristic_row("eil51", 400)], table, plan=plan)
    assert out[GAP_COLUMN] < 0  # impossible for a valid tour: the reference check of D-07 reports it, nothing clamps it


# ---------------------------------------------------------------- the join identity
@pytest.mark.parametrize("name", ["kroA100", "KROA100", " kroa100 ", "KroA100"])
def test_the_join_uses_the_normalised_tsplib_name(plan, name):
    table = table_of(exact_row("kroa100", value=21282))
    (out,) = add_gap_columns([heuristic_row(name, 21282, optimum=21282.0)], table, plan=plan)
    assert out[GAP_COLUMN] == 0.0


def test_the_dataset_id_is_not_the_join_key(plan):
    table = table_of(exact_row("kroa100", value=21282))
    row = heuristic_row("eil51", 426, dataset_id="tsplib-kroa100")  # contradictory dataset id: the problem name decides
    (out,) = add_gap_columns([row], table, plan=plan)
    assert out[GAP_COLUMN] is None and "eil51" in out["gap_missing_reason"]


# ---------------------------------------------------------------- no reference, no gap
def test_an_instance_without_an_exact_reference_gets_a_null_gap_with_a_reason_never_the_database_value(plan):
    table = table_of(exact_row("eil51", value=426))
    row = heuristic_row("berlin52", 8000, optimum=7542.0, gap_pct=6.07)  # the pilot's database value stays out of the column
    (out,) = add_gap_columns([row], table, plan=plan)
    assert out[GAP_COLUMN] is None
    assert out["exact_reference_value"] is None
    assert "berlin52" in out["gap_missing_reason"] and "no exact reference" in out["gap_missing_reason"]
    assert out["gap_pct"] == 6.07  # the pilot column is untouched, only not reused


def test_a_reference_that_is_not_a_proven_optimum_gives_no_gap_not_the_published_value(plan):
    table = table_of(exact_row("eil51", value=430, status="feasible_with_gap", published=426, lb=420))
    assert "eil51" not in table.values
    (out,) = add_gap_columns([heuristic_row("eil51", 430)], table, plan=plan)
    assert out[GAP_COLUMN] is None
    assert "not a proven optimum" in out["gap_missing_reason"] and "feasible_with_gap" in out["gap_missing_reason"]


def test_a_failed_run_has_no_cost_and_no_gap(plan):
    table = table_of(exact_row("eil51", value=426))
    failed = {"record_kind": "failed_run", "validation_status": "failed", "protocol_version": FAIR_V2,
              "comparison_regime": "fixed_evaluation_budget", "problem": "eil51", "algorithm_id": "Core-GA-TSP", "replicate": 1}
    (out,) = add_gap_columns([failed], table, plan=plan)
    assert out[GAP_COLUMN] is None and "failed run" in out["gap_missing_reason"]


def test_a_valid_row_without_a_finite_cost_is_refused(plan):
    table = table_of(exact_row("eil51", value=426))
    for bad in ({"objective_cost": None}, {"objective_cost": float("nan")}, {"objective_cost": "426"}):
        with pytest.raises(GapColumnError, match="objective_cost"):
            add_gap_columns([heuristic_row("eil51", 426, **bad)], table, plan=plan)
    row = heuristic_row("eil51", 426)
    del row["objective_cost"]
    with pytest.raises(GapColumnError, match="objective_cost"):
        add_gap_columns([row], table, plan=plan)


# ---------------------------------------------------------------- disagreement blocks
def test_a_row_optimum_that_differs_from_the_exact_reference_blocks(plan):
    table = table_of(exact_row("eil51", value=426))
    with pytest.raises(GapColumnError, match="differs from the exact reference"):
        add_gap_columns([heuristic_row("eil51", 430, optimum=428.0)], table, plan=plan)


def test_a_problem_type_that_differs_from_the_reference_contract_blocks(plan):
    table = table_of(exact_row("ft53", value=6905, contract="ATSP"))
    with pytest.raises(GapColumnError, match="problem type"):
        add_gap_columns([heuristic_row("ft53", 7000, problem_type="TSP", optimum=6905.0)], table, plan=plan)


def test_an_atsp_row_gets_the_same_gap_definition(plan):
    table = table_of(exact_row("ft53", value=6905, contract="ATSP"))
    row = heuristic_row("ft53", 7500, problem_type="ATSP", optimum=6905.0)
    (out,) = add_gap_columns([row], table, plan=plan)
    assert out[GAP_COLUMN] == pytest.approx((7500 - 6905) / 6905 * 100.0, abs=1e-12)


def test_an_existing_gap_column_is_never_overwritten(plan):
    table = table_of(exact_row("eil51", value=426))
    with pytest.raises(GapColumnError, match=GAP_COLUMN):
        add_gap_columns([heuristic_row("eil51", 426, **{GAP_COLUMN: 1.0})], table, plan=plan)


def test_the_input_rows_are_not_modified(plan):
    table = table_of(exact_row("eil51", value=426))
    rows = [heuristic_row("eil51", 430)]
    snapshot = copy.deepcopy(rows)
    add_gap_columns(rows, table, plan=plan)
    assert rows == snapshot


# ---------------------------------------------------------------- exact rows are references only
def test_a_typed_exact_row_as_data_is_refused(plan):
    table = table_of(exact_row("eil51", value=426))
    with pytest.raises(ValueError, match="never ranked, averaged or tested"):
        add_gap_columns([exact_row("eil51", value=426)], table, plan=plan)


def test_an_exact_row_dict_as_data_is_refused(plan):
    table = table_of(exact_row("eil51", value=426))
    row = {"protocol": "exact_reference_v1", "problem": "eil51", "objective_cost": 426.0}
    with pytest.raises(ValueError, match="never ranked, averaged or tested"):
        add_gap_columns([row], table, plan=plan)


def test_exact_rows_mixed_into_heuristic_rows_are_refused_before_any_gap(plan):
    table = table_of(exact_row("eil51", value=426))
    mixed = [heuristic_row("eil51", 430), {"protocol": "exact_reference_v1", "problem": "eil51", "objective_cost": 426.0}]
    with pytest.raises(ValueError, match="different pooling groups"):
        add_gap_columns(mixed, table, plan=plan)


def test_fixed_and_native_rows_are_not_gapped_together(plan):
    table = table_of(exact_row("eil51", value=426))
    native = heuristic_row("eil51", 430, protocol_version=NATIVE, comparison_regime="native_termination", evaluation_budget=None)
    with pytest.raises(ValueError, match="different pooling groups"):
        add_gap_columns([heuristic_row("eil51", 430), native], table, plan=plan)


def test_a_row_that_names_no_protocol_is_refused(plan):
    table = table_of(exact_row("eil51", value=426))
    row = heuristic_row("eil51", 430)
    for key in ("protocol_version", "comparison_regime"):
        del row[key]
    with pytest.raises(ValueError):
        add_gap_columns([row], table, plan=plan)


def test_the_table_values_are_not_rows_a_statistics_caller_could_receive(plan):
    value = table_of(exact_row("eil51", value=426)).values["eil51"]
    assert not isinstance(value, dict) and not hasattr(value, "algorithm_id")


# ---------------------------------------------------------------- building the reference table
def test_the_table_reads_the_primary_proven_optimum_and_ignores_verification_rows():
    table = table_of(exact_row("eil51", value=426), exact_row("eil51", value=426, role="verification", solver="HiGHS"))
    entry = table.values["eil51"]
    assert entry.value == 426 and entry.problem_contract == "TSP" and entry.solver_name == "Gurobi"
    assert entry.results_dir.endswith("stage1-verification") and entry.manifest_sha256 == SHA


def test_a_proven_optimum_that_differs_from_the_published_optimum_blocks():
    with pytest.raises(ReferenceCrossCheckError, match="published optimum"):
        table_of(exact_row("eil51", value=427, published=426))


def test_a_reference_row_whose_tour_was_not_independently_validated_is_refused():
    with pytest.raises(ReferenceCrossCheckError, match="validated"):
        table_of(exact_row("eil51", value=426, validated=False))


def test_two_sets_that_disagree_on_an_instance_block():
    first = exact_set(exact_row("eil51", value=426))
    second = exact_set(exact_row("eil51", value=427, published=427), results_dir="docs/paper/results/tsplib-exact-reference/other")
    with pytest.raises(ReferenceCrossCheckError, match="eil51"):
        build_reference_table([first, second])


def test_two_sets_that_agree_are_accepted_once():
    first = exact_set(exact_row("eil51", value=426))
    second = exact_set(exact_row("eil51", value=426), results_dir="docs/paper/results/tsplib-exact-reference/other")
    assert build_reference_table([first, second]).values["eil51"].value == 426


def test_wave_campaign_sets_carry_no_gap_reference():
    wave_row = exact_row("eil51", value=426).model_copy(update={"instance_id": "2026-10-05-R50"})
    assert build_reference_table([exact_set(wave_row, kind="wave_campaign")]).values == {}



# ---------------------------------------------------------------- the committed stage-1 reference
def test_the_committed_reference_covers_every_study_instance_and_is_proven(real_table):
    for name in BILDIRI_INSTANCES:
        assert name in real_table.values, name
    assert len(real_table.values) == 17 and not real_table.unproven
    assert real_table.values["eil51"].value == 426
    assert real_table.values["kroa100"].value == 21282
    assert real_table.values["ft53"].problem_contract == "ATSP"


def test_the_reference_table_loader_validates_the_tours_independently(real_table):
    assert all(entry.ub_validated for entry in real_table.values.values())


def test_the_loader_reads_only_the_tsp_reference_directories_of_the_index(real_table):
    assert {entry.results_dir for entry in real_table.values.values()} == {
        "docs/paper/results/tsplib-exact-reference/stage1-verification"}


@pytest.mark.parametrize("study, count", [("bildiri2026", 7), ("yaem2026", 4)])
def test_cross_check_the_study_instances_against_reference_manifest_and_published_optimum(real_table, study, count):
    loaded = load_study_with_plan(STUDY_PATHS[study], repository_root=REPO, mode="smoke")
    datasets = resolve_datasets(loaded.study, repository_root=REPO)
    checked = cross_check_study_datasets(real_table, datasets)
    assert len(checked) == count
    assert set(checked) <= BILDIRI_INSTANCES
    for identity in checked:
        entry = real_table.values[identity]
        assert entry.value == entry.published_optimum


def test_the_two_studies_use_seven_distinct_instances(real_table):
    names = set()
    for study in STUDY_PATHS:
        loaded = load_study_with_plan(STUDY_PATHS[study], repository_root=REPO, mode="smoke")
        names |= set(cross_check_study_datasets(real_table, resolve_datasets(loaded.study, repository_root=REPO)))
    assert names == BILDIRI_INSTANCES


def test_a_study_dataset_manifest_value_that_differs_from_the_reference_blocks(real_table):
    loaded = load_study_with_plan(STUDY_PATHS["bildiri2026"], repository_root=REPO, mode="smoke")
    datasets = list(resolve_datasets(loaded.study, repository_root=REPO))
    first = datasets[0]
    bad_best = first.manifest.best_known.model_copy(update={"value": first.manifest.best_known.value + 1})
    datasets[0] = first.__class__(first.manifest_path, first.manifest.model_copy(update={"best_known": bad_best}),
                                  first.artifact_sha256, first.problem_name, first.artifact_dimension)
    with pytest.raises(ReferenceCrossCheckError, match="best_known"):
        cross_check_study_datasets(real_table, datasets)


def test_a_study_dataset_without_an_exact_reference_blocks():
    loaded = load_study_with_plan(STUDY_PATHS["bildiri2026"], repository_root=REPO, mode="smoke")
    datasets = resolve_datasets(loaded.study, repository_root=REPO)
    with pytest.raises(ReferenceCrossCheckError, match="no exact reference"):
        cross_check_study_datasets(build_reference_table([]), datasets)


def test_a_study_dataset_whose_best_known_is_not_an_optimum_cannot_confirm_the_reference(real_table):
    loaded = load_study_with_plan(STUDY_PATHS["bildiri2026"], repository_root=REPO, mode="smoke")
    datasets = list(resolve_datasets(loaded.study, repository_root=REPO))
    first = datasets[0]
    weak = first.manifest.best_known.model_copy(update={"status": "best_known"})
    datasets[0] = first.__class__(first.manifest_path, first.manifest.model_copy(update={"best_known": weak}),
                                  first.artifact_sha256, first.problem_name, first.artifact_dimension)
    with pytest.raises(ReferenceCrossCheckError, match="best_known"):
        cross_check_study_datasets(real_table, datasets)


# ---------------------------------------------------------------- problem.optimal (database value) cross-check helper
def test_the_problem_optimal_cross_check_passes_on_equal_values_and_blocks_on_any_difference(real_table):
    values = {"eil51": 426.0, "ft53": 6905, "kroA100": 21282.0}
    assert cross_check_problem_optimal(real_table, values) == ["eil51", "ft53", "kroa100"]
    values["eil51"] = 428.0
    with pytest.raises(ReferenceCrossCheckError, match="eil51"):
        cross_check_problem_optimal(real_table, values)
    with pytest.raises(ReferenceCrossCheckError, match="no exact reference"):
        cross_check_problem_optimal(real_table, {"pcb442": 50778.0})


def test_the_gap_module_never_opens_the_database_or_writes():
    source = Path(gaps.__file__).read_text(encoding="utf-8")
    for token in ("sqlite3", "tsplib.db", "open(", ".write", "unlink", "shutil"):
        assert token not in source, token


def test_every_gap_value_is_finite_for_real_instances(real_table, plan):
    rows = [heuristic_row("kroA100", 22000, optimum=21282.0, problem_type="TSP"),
            heuristic_row("berlin52", 7600, optimum=7542.0, problem_type="TSP")]
    out = add_gap_columns(rows, real_table, plan=plan)
    assert all(math.isfinite(r[GAP_COLUMN]) for r in out)
