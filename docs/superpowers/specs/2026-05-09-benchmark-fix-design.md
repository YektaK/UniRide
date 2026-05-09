# Benchmark Fix Design (nb_three_opt + dashboard filters)

Date: 2026-05-09

## Goal

Fix two correctness issues and add tests:

- Make Numba-backed `nb_three_opt` actually improve tours when improvements exist.
- Keep dashboard filters usable when only raw progress data exists (no summary CSV yet).

## Scope

In scope:

- `academic_benchmark/bildiri2026/core/numba_accel.py`
- `academic_benchmark/dashboard.py`
- Add or adjust tests under `academic_benchmark/tests/`

Out of scope:

- Broader dashboard UX changes beyond filter fallback.
- Performance refactors beyond the minimal fix to `nb_three_opt` selection logic.

## Design

### 1) Fix Numba `nb_three_opt` selection logic

Problem: `_three_opt_improve_atsp_numba` compares a full-tour `new_length` against a value derived from a subset of edges, which effectively prevents any improvement from being selected.

Change:

- Compare candidate `new_length` against the full-tour `best_length` to decide whether to accept a candidate improvement.
- Keep the existing bounded loops and 7-case reconnection logic unchanged.

Rationale:

- This is the smallest correct fix that makes the 3-opt kernel functional again.
- The test will verify that `nb_three_opt` can improve a small instance when Numba is available.

### 2) Dashboard filter fallback to raw progress

Problem: Filter options (`problem`, `strategy`) are derived from `summary_df` only, so if only `benchmark_progress.csv` exists, filters are empty and raw charts show no data.

Change:

- If `summary_df` is empty, derive `all_probs` and `all_algos` from `progress_df` instead.
- Keep the existing behavior when summaries exist.

Rationale:

- Ensures the dashboard is usable immediately after raw runs without implying aggregated metrics.

## Tests

### Numba 3-opt behavior

Add a Numba-gated test that:

- Creates a small instance where a 3-opt improvement is possible.
- Calls `nb_three_opt` and asserts the improved length is strictly lower than the baseline.
- Skips cleanly if Numba is unavailable.

### Dashboard filter fallback

Add a small helper (or inline logic) test that:

- Simulates `summary_df` empty and `progress_df` populated.
- Asserts derived filters match the values in raw progress.

## Data flow and compatibility

- No new files or data schema changes.
- Backward compatible: existing dashboards with summary files continue to behave the same.

## Risks

- The 3-opt test requires Numba; it will be skipped in environments without Numba.
- Dashboard fallback must not interfere with summary-based filtering when summaries exist.

## Acceptance criteria

- `nb_three_opt` can demonstrably improve a known case (Numba available).
- Dashboard filters show options when only raw progress exists.
- No regressions in existing test suite behavior.
