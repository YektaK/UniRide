import pandas as pd

from academic_benchmark.dashboard_utils import derive_filter_options


def test_filters_fallback_to_progress_when_summary_empty():
    summary_df = pd.DataFrame()
    progress_df = pd.DataFrame({
        "problem": ["p1", "p2", None],
        "strategy": ["A", "B", "A"],
    })

    probs, algos = derive_filter_options(summary_df, progress_df)

    assert probs == ["p1", "p2"]
    assert algos == ["A", "B"]


def test_filters_use_summary_when_present():
    summary_df = pd.DataFrame({
        "problem": ["s1", "s2"],
        "strategy": ["X", "Y"],
    })
    progress_df = pd.DataFrame({
        "problem": ["p1"],
        "strategy": ["A"],
    })

    probs, algos = derive_filter_options(summary_df, progress_df)

    assert probs == ["s1", "s2"]
    assert algos == ["X", "Y"]
