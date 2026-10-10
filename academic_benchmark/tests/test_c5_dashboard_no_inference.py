"""C5: the dashboard statistics tab must not emit any inferential claim.

Rows are not validated, protocol-homogeneous or seed_group-paired, so no
p-value, significance, superiority or proof wording may be produced
(AGENTS.md; ACADEMIC_STUDY_UNIFICATION_DESIGN.md, Statistical Protocol).
The tab body is extracted from dashboard.py by AST and run against a stub
``st`` so that no real streamlit is needed.
"""
import ast
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"
FORBIDDEN = ("significan", "outperform", "p-value", "p=", "p <", "p<",
             "academic proof", "wilcoxon", "winner")
SCIPY_TESTS = {"wilcoxon", "mannwhitneyu", "ttest_rel", "ttest_ind",
               "ttest_1samp", "kruskal", "friedmanchisquare"}


class _Recorder:
    """Stub of the streamlit module: records every string it is handed."""

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
                opts = list(args[1])
                return opts[kwargs.get("index", 0)]
            return None
        return call


def _tab4_node():
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.With)
                and isinstance(node.items[0].context_expr, ast.Name)
                and node.items[0].context_expr.id == "tab4"):
            return node
    raise AssertionError("tab4 block not found in dashboard.py")


def _run_tab4(monkeypatch):
    calls = []
    fake_stats = types.ModuleType("scipy.stats")
    for name in SCIPY_TESTS:
        def _t(*a, _n=name, **k):
            calls.append(_n)
            return 1.0, 0.001
        setattr(fake_stats, name, _t)
    fake_scipy = types.ModuleType("scipy")
    fake_scipy.stats = fake_stats
    monkeypatch.setitem(sys.modules, "scipy", fake_scipy)
    monkeypatch.setitem(sys.modules, "scipy.stats", fake_stats)

    rows = []
    for algo, base in (("A", 5.0), ("B", 1.0)):
        for prob in ("p1", "p2"):
            for i in range(6):
                rows.append({"problem": prob, "strategy": algo,
                             "avg_gap": base + 0.1 * i})
    frame = pd.DataFrame(rows)
    st = _Recorder()
    module = ast.Module(body=[_tab4_node()], type_ignores=[])
    ns = {
        "st": st, "pd": pd, "np": np, "tab4": _NullCtx(),
        "filtered_progress": frame,
        "selected_algos": ["A", "B"], "selected_probs": ["p1", "p2"],
    }
    exec(compile(module, str(DASHBOARD), "exec"), ns)
    return st.texts, calls


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_tab4_emits_no_inferential_wording(monkeypatch):
    texts, _ = _run_tab4(monkeypatch)
    blob = "\n".join(texts).lower()
    assert texts, "tab must still render an informational message"
    for word in FORBIDDEN:
        assert word not in blob, f"forbidden wording {word!r} in: {blob[:300]}"
    assert "disabled" in blob


def test_tab4_never_calls_scipy_tests(monkeypatch):
    _, calls = _run_tab4(monkeypatch)
    assert calls == []


def test_dashboard_never_references_scipy_stats_tests():
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("scipy"):
            raise AssertionError("dashboard.py imports scipy")
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("scipy") for a in node.names)
        if isinstance(node, ast.Name) and node.id in SCIPY_TESTS:
            raise AssertionError(f"dashboard.py references {node.id}")
        if isinstance(node, ast.Attribute) and node.attr in SCIPY_TESTS:
            raise AssertionError(f"dashboard.py references {node.attr}")


def test_tab_labels_make_no_inferential_claim():
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    labels = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "tabs"):
            labels += [c.value for c in ast.walk(node)
                       if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    assert labels
    blob = " ".join(labels).lower()
    for word in ("significan", "wilcoxon", "proof", "outperform"):
        assert word not in blob
