"""WP-E8 Task 6: the academic-layer protocol registry and the no-pooling, no-ranking guarantees.

Fixed-budget and native rows come from the frozen golden fixture of Task 1 (real pilot output); exact rows come from the
committed stage-1 results through the reader. Rows are classified by the fields they carry today: ``comparison_regime`` and
``protocol_version`` for pilot rows, ``protocol`` for exact and union rows.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from academic_benchmark import fair_pilot, native_pilot, protocol_registry as registry
from academic_benchmark.core import preflight
from academic_benchmark.exact_reference import protocol as exact_protocol
from academic_benchmark.exact_reference.reader import load_exact_reference
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NATIVE_PROTOCOL, NATIVE_TERMINATION_REGIME
from uniride_core.algorithms.capabilities import ExecutionProtocol

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "academic_benchmark"
GOLDEN = PKG / "tests" / "fixtures" / "fixed_budget_tables_golden_v1.json"
STAGE1 = "docs/paper/results/tsplib-exact-reference/stage1-verification"


@pytest.fixture(scope="module")
def fixed_rows():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return [json.loads(line) for line in golden["fair_pilot"]["runs.jsonl"].splitlines()]


@pytest.fixture(scope="module")
def native_rows():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return [json.loads(line) for line in golden["native_pilot"]["runs.jsonl"].splitlines()]


@pytest.fixture(scope="module")
def exact_rows():
    return load_exact_reference(STAGE1, repo_root=REPO).rows


UNION_ROW = {"protocol": "union_day_v1", "day": "2026-10-05"}
JOINT_ROW = {"protocol": "exact_day_joint_v1", "date": "2026-10-05", "day_status": "optimal"}  # WP-E11 J7


# ---------------------------------------------------------------- the registry
def test_the_registry_has_exactly_the_five_kinds_with_their_pooling_rules():
    table = {k.kind: (k.version_label, k.pooling_group, k.rankable, k.statistics) for k in registry.PROTOCOL_KINDS}
    assert table == {
        "fixed_evaluation_budget": ("uniride-fair-tsp-v2", "fixed_budget", True, True),
        "algorithm_native_termination": ("uniride-native-tsp-v1", "native", True, True),
        "exact_reference_v1": ("exact_reference_v1", "exact_reference_v1", False, False),
        "union_day_v1": ("union_day_v1", "union_day_v1", False, False),
        "exact_day_joint_v1": ("exact_day_joint_v1", "exact_day_joint_v1", False, False),
    }
    assert len({k.pooling_group for k in registry.PROTOCOL_KINDS}) == 5, "every kind is its own pooling group"
    with pytest.raises(ValueError, match="unknown protocol kind"):
        registry.kind_of("exact_reference_v2")


def test_registry_labels_equal_the_labels_of_the_fixed_budget_native_and_exact_modules():
    assert registry.FIXED_BUDGET == FairComparisonManifest.FIXED_EVALUATION_REGIME
    assert registry.FAIR_V1_VERSION == FairComparisonManifest.V1_PROTOCOL
    assert registry.FAIR_V2_VERSION == FairComparisonManifest.V2_PROTOCOL
    assert registry.NATIVE_VERSION == NATIVE_PROTOCOL and registry.NATIVE_TERMINATION == NATIVE_TERMINATION_REGIME
    assert registry.EXACT_REFERENCE == exact_protocol.PROTOCOL_ID and registry.UNION_DAY == exact_protocol.UNION_DAY_PROTOCOL_ID
    assert registry.DAY_JOINT == exact_protocol.DAY_JOINT_PROTOCOL_ID


def test_core_execution_protocol_is_unchanged_and_preflight_rejects_a_foreign_protocol():
    assert {p.value for p in ExecutionProtocol} == {"fixed_budget", "native_termination"}
    for foreign in ("exact_reference_v1", "union_day_v1", "exact_day_joint_v1"):
        request = SimpleNamespace(protocol=foreign, evaluation_budget=None)
        with pytest.raises(preflight.UnsupportedProtocolError, match="Unsupported execution protocol"):
            preflight._validate_protocol_budget(request)


# ---------------------------------------------------------------- classification of real rows
def test_real_rows_are_classified_by_their_existing_fields(fixed_rows, native_rows, exact_rows):
    assert {registry.classify_row(r).kind for r in fixed_rows} == {"fixed_evaluation_budget"}
    assert {registry.classify_row(r).kind for r in native_rows} == {"algorithm_native_termination"}
    assert {registry.classify_row(r).kind for r in exact_rows} == {"exact_reference_v1"}
    assert registry.classify_row(UNION_ROW).kind == "union_day_v1"
    assert registry.classify_row(JOINT_ROW).kind == "exact_day_joint_v1"
    assert len(fixed_rows) == 40 and len(native_rows) == 24  # 40 = 5 algorithms x 2 problems x (3 runs + 1 replay), runs=3 since WP-E8 polish item 5
    # the golden pilot rows carry these fields today
    assert {r["protocol_version"] for r in fixed_rows} == {"uniride-fair-tsp-v1"}  # the stub executor leaves comparison_regime empty
    assert {r["comparison_regime"] for r in fixed_rows} == {""}
    assert {r["protocol_version"] for r in native_rows} == {"uniride-native-tsp-v1"}


def test_a_v1_fixed_row_without_a_regime_is_still_fixed_budget():
    assert registry.classify_row({"protocol_version": "uniride-fair-tsp-v1"}).kind == "fixed_evaluation_budget"


def test_contradictory_unclassifiable_and_foreign_objects_are_refused():
    with pytest.raises(ValueError, match="several protocol kinds"):
        registry.classify_row({"comparison_regime": "algorithm_native_termination", "protocol_version": "uniride-fair-tsp-v2"})
    with pytest.raises(ValueError, match="several protocol kinds"):
        registry.classify_row({"protocol": "exact_reference_v1", "comparison_regime": "fixed_evaluation_budget"})
    with pytest.raises(ValueError, match="identifies its kind"):
        registry.classify_row({"problem": "x"})
    with pytest.raises(TypeError):
        registry.classify_row(["not", "a", "row"])


# ---------------------------------------------------------------- no pooling
def test_exact_rows_cannot_be_pooled_with_fixed_budget_or_native_rows_and_fixed_not_with_native(fixed_rows, native_rows, exact_rows):
    for left, right in ((exact_rows, fixed_rows), (exact_rows, native_rows), (fixed_rows, native_rows), (exact_rows, [UNION_ROW]),
                        (native_rows, fixed_rows)):
        with pytest.raises(ValueError, match="different pooling groups"):
            registry.assert_single_pooling_group([*left[:2], *right[:2]])
    with pytest.raises(ValueError, match="different pooling groups"):
        registry.assert_single_pooling_group([fixed_rows[0], exact_rows[0], native_rows[0]])


def test_rows_of_one_group_may_meet(fixed_rows, native_rows, exact_rows):
    assert registry.assert_single_pooling_group(fixed_rows) == "fixed_budget"
    assert registry.assert_single_pooling_group(native_rows) == "native"
    assert registry.assert_single_pooling_group(exact_rows) == "exact_reference_v1"
    assert registry.assert_single_pooling_group([]) == ""


def test_a_joint_day_row_is_never_pooled_with_union_day_exact_reference_or_heuristic_rows(fixed_rows, native_rows, exact_rows):
    for other in (exact_rows[:2], [UNION_ROW], fixed_rows[:2], native_rows[:2], [{"protocol": "exact_reference_v1"}]):
        for rows in ([JOINT_ROW, *other], [*other, JOINT_ROW]):
            with pytest.raises(ValueError, match="different pooling groups"):
                registry.assert_single_pooling_group(rows)
    assert registry.assert_single_pooling_group([JOINT_ROW, dict(JOINT_ROW, date="2026-10-06")]) == "exact_day_joint_v1"


def test_a_joint_day_row_with_a_second_protocol_field_is_refused():
    with pytest.raises(ValueError, match="several protocol kinds"):
        registry.classify_row({"protocol": "exact_day_joint_v1", "comparison_regime": "fixed_evaluation_budget"})


# ---------------------------------------------------------------- no ranking
def test_exact_and_union_rows_are_never_rankable(exact_rows):
    for rows in (exact_rows, exact_rows[:1], [UNION_ROW], [JOINT_ROW]):
        with pytest.raises(ValueError, match="never ranked"):
            registry.assert_rankable(rows)


def test_heuristic_rows_are_rankable_within_one_group_only(fixed_rows, native_rows, exact_rows):
    registry.assert_rankable(fixed_rows)
    registry.assert_rankable(native_rows)
    registry.assert_rankable([])
    with pytest.raises(ValueError, match="different pooling groups"):
        registry.assert_rankable([*fixed_rows[:1], *native_rows[:1]])
    with pytest.raises(ValueError, match="never ranked"):
        registry.assert_rankable([*fixed_rows[:2], exact_rows[0]])


# ---------------------------------------------------------------- the existing guards stay as they are
def test_assert_not_pooled_behaves_as_before(fixed_rows):
    exact_protocol.assert_not_pooled([{"protocol": "exact_reference_v1"}, {"protocol": "exact_reference_v1"}])
    exact_protocol.assert_not_pooled([])
    with pytest.raises(ValueError, match="must not be pooled"):
        exact_protocol.assert_not_pooled([{"protocol": "exact_reference_v1"}, fixed_rows[0]])
    with pytest.raises(ValueError, match="must not be pooled"):
        exact_protocol.assert_not_pooled([{"protocol": "union_day_v1"}])
    with pytest.raises(ValueError, match="must not be pooled"):
        exact_protocol.assert_not_pooled([{"protocol": "exact_day_joint_v1"}])


def test_an_exact_row_is_not_a_mapping_and_cannot_enter_the_dict_based_aggregators(exact_rows, fixed_rows):
    from collections.abc import Mapping

    assert not isinstance(exact_rows[0], Mapping)
    with pytest.raises(TypeError):
        fair_pilot._aggregate([exact_rows[0]], True)
    with pytest.raises((TypeError, AttributeError)):
        native_pilot.aggregate_native_records([exact_rows[0]], True)
    with pytest.raises(native_pilot.NativePilotError, match="foreign"):
        native_pilot.aggregate_native_records(fixed_rows[:1], True)  # native aggregation already refuses fixed rows


# ---------------------------------------------------------------- import boundaries (AST)
FIXED_NATIVE_MODULES = ("fairness.py", "fair_pilot.py", "native_protocol.py", "native_pilot.py", "matrix_run_summary.py",
                        "results_reader.py", "data_export.py", "core/preflight.py", "core/execution_gateway.py",
                        "core/registry_setup.py")


def _imports(path: Path) -> set:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = ("." * node.level) + (node.module or "")
            names.add(base)
            names.update(f"{base}.{alias.name}".lstrip(".") for alias in node.names)
    return names


@pytest.mark.parametrize("module", FIXED_NATIVE_MODULES)
def test_fixed_budget_and_native_modules_import_neither_exact_reference_nor_the_registry(module):
    path = PKG / module
    assert path.is_file(), path
    for name in _imports(path):
        assert "exact_reference" not in name and "protocol_registry" not in name and "validation" not in name.split("."), (module, name)


def test_exact_reference_imports_none_of_the_fixed_budget_native_or_registry_modules():
    forbidden = {"fairness", "fair_pilot", "native_protocol", "native_pilot", "matrix_run_summary", "results_reader", "data_export",
                 "protocol_registry", "preflight", "execution_gateway", "registry_setup", "scripts"}
    files = sorted((PKG / "exact_reference").glob("*.py"))
    assert {f.name for f in files} >= {"inputs.py", "protocol.py", "reader.py", "rows.py"}
    for path in files:
        for name in _imports(path):
            assert not forbidden & set(name.replace("academic_benchmark.core.", "").split(".")), (path.name, name)
