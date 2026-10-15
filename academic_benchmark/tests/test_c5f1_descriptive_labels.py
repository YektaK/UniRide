"""C5-F1: dashboard labels must be descriptive, not superiority claims.

Rows shown by the dashboard are pooled and not validated (AGENTS.md: smoke or
pilot runs cannot produce superiority claims; DECISION_LOG A13/A15).  Owner
decision 2026-10-15: "Lower mean gap (descriptive)" replaces best/better
marking, and "Descriptive LaTeX table (not validated for publication)"
replaces the paper-ready LaTeX wording.  Tabs are executed from dashboard.py
by AST against a stub ``st`` so no real streamlit is needed.
"""
import ast
import types
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"

LOWER_GAP = "Lower mean gap (descriptive)"
LATEX_LABEL = "Descriptive LaTeX table (not validated for publication)"
# Superiority-sounding fragments that must no longer be rendered.
OLD_PHRASES = (
    "best performing",
    "paper-ready",
    "best values in bold",
    "row algorithm better",
    "column algorithm better",
    "top solutions",
    "export as latex table",
    "generate academic latex",
    "leaderboard",
)


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Recorder:
    def __init__(self):
        self.texts = []

    def _collect(self, value):
        if isinstance(value, str):
            self.texts.append(value)
        elif isinstance(value, pd.DataFrame):
            self.texts.append(" ".join(map(str, value.columns)))
            self.texts.append(value.to_string())
        elif isinstance(value, (list, tuple)):
            for item in value:
                self._collect(item)

    def __getattr__(self, name):
        def call(*args, **kwargs):
            for value in list(args) + list(kwargs.values()):
                self._collect(value)
            if name == "selectbox":
                return list(args[1])[kwargs.get("index", 0)]
            if name == "button":
                return True
            if name == "columns":
                return [_NullCtx() for _ in range(len(args[0]))]
            return None
        return call


def _tab_node(name):
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.With)
                and isinstance(node.items[0].context_expr, ast.Name)
                and node.items[0].context_expr.id == name):
            return node
    raise AssertionError(f"{name} block not found in dashboard.py")


class _Frame(pd.DataFrame):
    """DataFrame without the optional jinja2 dependency (.style, to_latex)."""

    @property
    def _constructor(self):
        return _Frame

    @property
    def style(self):
        return mock.MagicMock()

    def to_latex(self, **kwargs):
        caption = kwargs.get("caption")
        cap = f"\\caption{{{caption}}}\n" if caption else ""
        return "\\begin{tabular}\n" + cap + "\\end{tabular}"


def _summary():
    rows = []
    for algo, base in (("A", 5.0), ("B", 1.0)):
        for prob in ("p1", "p2"):
            rows.append({"problem": prob, "strategy": algo,
                         "avg_gap": base, "avg_time_ms": 10.0 + base,
                         "gap_type": "bsf"})
    return _Frame(rows)


def _run_tab(name):
    st = _Recorder()
    summary = _summary()
    ns = {
        "st": st, "pd": pd, "np": np, "go": mock.MagicMock(),
        name: _NullCtx(),
        "filtered_summary": summary,
        "filtered_progress": pd.DataFrame(),
        "selected_algos": ["A", "B"], "selected_probs": ["p1", "p2"],
    }
    module = ast.Module(body=[_tab_node(name)], type_ignores=[])
    exec(compile(module, str(DASHBOARD), "exec"), ns)
    return st.texts


def _blob(texts):
    return "\n".join(texts)


def test_tab1_uses_descriptive_lower_gap_and_latex_labels():
    blob = _blob(_run_tab("tab1"))
    assert LOWER_GAP in blob
    assert LATEX_LABEL in blob
    low = blob.lower()
    for phrase in OLD_PHRASES:
        assert phrase not in low, f"old label {phrase!r} still rendered"


def test_tab1_latex_export_carries_descriptive_caption():
    texts = _run_tab("tab1")
    latex = [t for t in texts if "\\begin{" in t]
    assert latex, "LaTeX export was not generated"
    assert all(LATEX_LABEL in t for t in latex)


def test_tab6_comparison_column_is_descriptive():
    texts = _run_tab("tab6")
    blob = _blob(texts)
    assert LOWER_GAP in blob
    assert "Better" not in blob
    low = blob.lower()
    for phrase in OLD_PHRASES:
        assert phrase not in low, f"old label {phrase!r} still rendered"


def test_tab7_edge_analysis_does_not_call_algorithms_top_or_best():
    blob = _blob(_run_tab("tab7"))
    assert LOWER_GAP in blob
    low = blob.lower()
    assert "top 2 algorithms" not in low and "top solutions" not in low


def test_tab_titles_do_not_say_leaderboard():
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    labels = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "tabs"):
            labels += [c.value for c in ast.walk(node)
                       if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    assert labels
    assert not [l for l in labels if "leaderboard" in l.lower() or "🏆" in l]


def test_no_old_superiority_string_constants_anywhere():
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    parts = [n.value.lower() for n in ast.walk(tree)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for phrase in OLD_PHRASES + ("better",):
        hits = [p[:80] for p in parts if phrase in p]
        assert not hits, f"{phrase!r} in dashboard.py string(s): {hits}"
