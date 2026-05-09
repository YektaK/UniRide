from typing import List, Tuple

import pandas as pd


def derive_filter_options(
    summary_df: pd.DataFrame,
    progress_df: pd.DataFrame,
) -> Tuple[List[str], List[str]]:
    source_df = summary_df if not summary_df.empty else progress_df
    if source_df.empty:
        return [], []

    probs = sorted([p for p in source_df["problem"].unique() if pd.notna(p)])
    algos = sorted([a for a in source_df["strategy"].unique() if pd.notna(a)])
    return probs, algos
