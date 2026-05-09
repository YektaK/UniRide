# Benchmark Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Numba 3-opt improvement selection and add a dashboard filter fallback with tests.

**Architecture:** Add a small pure helper for dashboard filter derivation and wire it into the Streamlit app. Fix the Numba 3-opt selection baseline so candidate tours are compared against the true best length. Add targeted tests with Numba gating and pandas-only validation.

**Tech Stack:** Python, pytest, pandas, numba (optional), Streamlit

---

## File Map

- Create: `academic_benchmark/dashboard_utils.py` — pure helper for filter options.
- Modify: `academic_benchmark/dashboard.py` — use helper to derive filter options.
- Modify: `academic_benchmark/bildiri2026/core/numba_accel.py` — fix 3-opt candidate selection baseline.
- Create: `academic_benchmark/tests/test_dashboard_filters.py` — tests for filter fallback behavior.
- Create: `academic_benchmark/tests/test_numba_three_opt.py` — Numba-gated improvement test.

---

### Task 1: Dashboard filter fallback helper + tests

**Files:**
- Create: `academic_benchmark/tests/test_dashboard_filters.py`
- Create: `academic_benchmark/dashboard_utils.py`
- Modify: `academic_benchmark/dashboard.py`

- [ ] **Step 1: Write the failing tests**

Create `academic_benchmark/tests/test_dashboard_filters.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

`pytest academic_benchmark/tests/test_dashboard_filters.py -v`

Expected: FAIL with `ModuleNotFoundError` for `academic_benchmark.dashboard_utils`.

- [ ] **Step 3: Implement the helper**

Create `academic_benchmark/dashboard_utils.py`:

```python
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
```

- [ ] **Step 4: Wire helper into the dashboard**

Modify `academic_benchmark/dashboard.py`:

1) Add import near the top:

```python
from academic_benchmark.dashboard_utils import derive_filter_options
```

2) Replace filter list creation:

```python
all_probs, all_algos = derive_filter_options(summary_df, progress_df)
```

- [ ] **Step 5: Re-run the tests**

Run:

`pytest academic_benchmark/tests/test_dashboard_filters.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add academic_benchmark/tests/test_dashboard_filters.py academic_benchmark/dashboard_utils.py academic_benchmark/dashboard.py
git commit -m "Add dashboard filter fallback helper"
```

---

### Task 2: Fix Numba 3-opt selection baseline + tests

**Files:**
- Create: `academic_benchmark/tests/test_numba_three_opt.py`
- Modify: `academic_benchmark/bildiri2026/core/numba_accel.py`

- [ ] **Step 1: Write the failing test**

Create `academic_benchmark/tests/test_numba_three_opt.py`:

```python
import pytest

from academic_benchmark.bildiri2026.core import numba_accel


@pytest.mark.skipif(not numba_accel.NUMBA_AVAILABLE, reason="Numba not available")
def test_nb_three_opt_improves_simple_instance():
    n = 6
    high = 10.0
    low = 1.0

    # Build a matrix where the route 0-1-2-3-4-5-0 is very cheap.
    dm = [[high for _ in range(n)] for _ in range(n)]
    for i in range(n):
        dm[i][i] = 0.0
    best_route = [0, 1, 2, 3, 4, 5]
    for i in range(n - 1):
        dm[best_route[i]][best_route[i + 1]] = low
    dm[best_route[-1]][best_route[0]] = low

    # Start from a suboptimal tour.
    start_tour = [0, 2, 1, 3, 4, 5]

    def tour_cost(tour):
        return sum(dm[tour[i]][tour[(i + 1) % n]] for i in range(n))

    start_len = tour_cost(start_tour)
    improved_tour, improved_len = numba_accel.nb_three_opt(start_tour, dm, 50, False)

    assert improved_len < start_len
    assert sorted(improved_tour) == sorted(start_tour)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

`pytest academic_benchmark/tests/test_numba_three_opt.py -v`

Expected: FAIL (no improvement) or PASS/skip if Numba is unavailable. If it passes without changes, keep the test and proceed; it will still guard the regression.

- [ ] **Step 3: Fix the 3-opt selection baseline**

Modify `_three_opt_improve_atsp_numba` in `academic_benchmark/bildiri2026/core/numba_accel.py`:

Replace:

```python
best_case_cost = current_cost
best_case_route = None
```

With:

```python
best_case_cost = best_length
best_case_route = None
```

Keep the rest of the loop and the `new_length < best_case_cost` check unchanged.

- [ ] **Step 4: Re-run the test**

Run:

`pytest academic_benchmark/tests/test_numba_three_opt.py -v`

Expected: PASS (or SKIP if Numba unavailable).

- [ ] **Step 5: Commit**

```bash
git add academic_benchmark/tests/test_numba_three_opt.py academic_benchmark/bildiri2026/core/numba_accel.py
git commit -m "Fix nb_three_opt selection baseline"
```

---

## Plan Self-Review

- Spec coverage: Task 1 covers dashboard fallback + tests. Task 2 covers nb_three_opt fix + tests.
- Placeholder scan: No TODO/TBD language; commands and code are concrete.
- Type consistency: Helper returns lists of strings; tests match those types.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-benchmark-fix-plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
