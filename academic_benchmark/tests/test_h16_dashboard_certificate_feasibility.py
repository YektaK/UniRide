"""MT1-11 / audit H16: dashboards treat a CVRPTW row as feasible only when a feasible
certificate backs it. "Violation count 0" is not enough (the old split path reported 0
for the audit scenario). The H16 "do not cite" note of the MT1-13 first close record is gone.

The diagnostics tab body is extracted from dashboard.py by AST and run against a stub
``st`` (same technique as test_c5_dashboard_no_inference.py), so no real streamlit is needed.
"""
import ast
from pathlib import Path

import pandas as pd

from academic_benchmark.dashboard_utils import (
    add_routing_analysis_columns,
    benchmark_rows_to_progress_frame,
)
from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.algorithms.feasibility_certificate import certify_problem_instance
from uniride_core.models import RoutingResult

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"

AUDIT_SCENARIO = """
H16
VEHICLE
NUMBER     CAPACITY
2          10
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           45        0
1         10       0        1       0           50        10
2         10       10       1       0           50        10
"""


def _row(problem_type, tw=0, cap=0, **extra):
    return {"problem": "p", "problem_type": problem_type, "capacity_violations": cap,
            "tw_violations": tw, **extra}


def _feasible(rows):
    return list(add_routing_analysis_columns(pd.DataFrame(rows))["is_feasible"])


def test_cvrptw_row_without_certificate_is_not_feasible_even_with_zero_counts():
    assert _feasible([_row("cvrptw")]) == [False]


def test_cvrptw_row_with_infeasible_certificate_is_not_feasible():
    assert _feasible([_row("cvrptw", certificate_feasible=False)]) == [False]


def test_cvrptw_row_with_feasible_certificate_is_feasible():
    assert _feasible([_row("cvrptw", certificate_feasible=True)]) == [True]


def test_feasible_certificate_does_not_hide_violation_counts():
    assert _feasible([_row("cvrptw", tw=1, certificate_feasible=True)]) == [False]
    assert _feasible([_row("cvrptw", cap=1, certificate_feasible=True)]) == [False]


def test_upper_case_cvrptw_is_handled():
    assert _feasible([_row("CVRPTW")]) == [False]


def test_other_routing_types_keep_the_count_rule():
    assert _feasible([_row("cvrp"), _row("uniride"), _row("cvrp", tw=1)]) == [True, True, False]


def test_missing_certificate_has_a_readable_status():
    frame = add_routing_analysis_columns(pd.DataFrame([_row("cvrptw")]))
    assert "certificate" in frame["constraint_status"].iloc[0]


def test_audit_scenario_is_infeasible_in_the_dashboard_frame():
    problem = MatrixBuilder.from_solomon_text(AUDIT_SCENARIO)
    instance = MatrixBuilder.to_problem_instance(problem)
    result = RoutingResult(
        algorithm="t", problem_type="CVRPTW", objective_cost=34.14, routes=[[1, 2]],
        tw_violations=0,
    )
    cert = certify_problem_instance(result, instance)
    row = {
        "problem": "H16", "algorithm": "t", "objective_cost": 34.14,
        "problem_type": "cvrptw", "capacity_violations": 0, "tw_violations": 0,
        "metadata": {"feasibility_certificate": {"is_feasible": cert.is_feasible}},
    }
    frame = add_routing_analysis_columns(benchmark_rows_to_progress_frame([row]))
    assert list(frame["is_feasible"]) == [False]


def test_certificate_from_row_metadata_reaches_the_progress_frame():
    row = {"problem": "S", "algorithm": "t", "objective_cost": 1.0, "problem_type": "cvrptw",
           "metadata": {"feasibility_certificate": {"is_feasible": True}}}
    frame = add_routing_analysis_columns(benchmark_rows_to_progress_frame([row]))
    assert list(frame["is_feasible"]) == [True]


# --- the note of the MT1-13 first close record is gone ------------------------------

class _Recorder:
    def __init__(self):
        self.texts = []

    def _collect(self, value):
        if isinstance(value, str):
            self.texts.append(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                self._collect(item)

    def __getattr__(self, name):
        def call(*args, **kwargs):
            for value in list(args) + list(kwargs.values()):
                self._collect(value)
            return _Recorder()
        return call


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _tab8_node():
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.With)
                and isinstance(node.items[0].context_expr, ast.Name)
                and node.items[0].context_expr.id == "tab8"):
            return node
    raise AssertionError("tab8 block not found in dashboard.py")


def _run_tab8(problem_types):
    rows = [
        {"problem": f"p{i}", "strategy": "A", "problem_type": ptype,
         "dataset_family": "x", "is_routing_problem": True,
         "is_feasible": True, "num_vehicles": 2}
        for i, ptype in enumerate(problem_types)
    ]
    frame = pd.DataFrame(rows)
    st = _Recorder()
    ns = {
        "st": st, "pd": pd, "px": _Recorder(), "tab8": _NullCtx(),
        "filtered_progress": frame,
        "routing_dashboard_columns": lambda df: list(df.columns),
    }
    module = ast.Module(body=[_tab8_node()], type_ignores=[])
    exec(compile(module, str(DASHBOARD), "exec"), ns)
    return "\n".join(st.texts).lower()


def test_cvrptw_diagnostics_no_longer_carry_the_do_not_cite_note():
    for types in (["cvrp", "cvrptw"], ["cvrp", "CVRPTW"]):
        blob = _run_tab8(types)
        assert "school-pickup" not in blob
        assert "must not be cited" not in blob
        assert "mt1-11" not in blob


def test_diagnostics_tab_still_renders_cvrptw_rows():
    blob = _run_tab8(["cvrptw"])
    assert "constraint health" in blob
