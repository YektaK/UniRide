"""H16: the routing diagnostics tab must warn that CVRPTW rows are validated
with school-pickup rules and must not be cited until MT1-11.

The tab body is extracted from dashboard.py by AST and run against a stub
``st`` (same technique as test_c5_dashboard_no_inference.py), so no real
streamlit is needed.
"""
import ast
from pathlib import Path

import pandas as pd

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"
NOTE_KEYS = ("cvrptw", "school-pickup", "h16", "mt1-11")


class _Recorder:
    """Stub of a module (st / px): records every string it is handed."""

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


def test_cvrptw_note_is_shown_when_cvrptw_rows_are_present():
    blob = _run_tab8(["cvrp", "cvrptw"])
    for key in NOTE_KEYS:
        assert key in blob, f"{key!r} missing from the diagnostics tab"
    assert "must not be cited" in blob


def test_cvrptw_note_is_hidden_without_cvrptw_rows():
    blob = _run_tab8(["cvrp", "uniride"])
    assert "school-pickup" not in blob
    assert "mt1-11" not in blob
