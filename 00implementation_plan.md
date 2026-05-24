# Priority 1 Critical Fixes Implementation Plan

This plan addresses the six Priority 1 (Critical) issues identified in the v2 architecture review. 

## User Review Required
> [!IMPORTANT]
> Please review the open questions below before approving this plan.

## Open Questions
1. **P1-4: API 3-opt Dimension Guard:** For `ThreeOptLocalSearch` in `optimizer_api/utils/local_search.py`, should I implement a sliding window (e.g., `window=12`) to keep it $O(n \cdot w^2)$ like in `uniride_core`, or should I simply add a hard fallback (e.g., if $n > 100$, automatically fall back to 2-opt)? *I recommend the sliding window for consistency, but a hard fallback is faster to implement.*
2. **Post-Implementation Testing:** Do you want me to run any specific test scripts (e.g., `test_patch.py`, `pytest`) after applying these fixes to verify them?

## Proposed Changes

### optimizer_api

#### [MODIFY] main.py
- **P1-1 (Path Traversal):** In `/api/v1/benchmark/cli/import`, validate the `filepath` argument. If provided, ensure it resolves to a path strictly inside `CLI_RESULTS_DIR` or `CLI_RESULTS_NUMBA_DIR`. Reject any requests trying to escape these directories using `..` or absolute paths.
- **P1-3 (Missing Import):** Add `BenchmarkImportRequest` to the Pydantic schema imports from `models.schemas` at the top of the file.

#### [MODIFY] utils/local_search.py
- **P1-4 (Unbounded 3-opt):** Modify `ThreeOptLocalSearch.improve()` to limit the inner loops for `j` and `k` to a maximum window size (e.g., `min(i + 2 + window, len(route) - 1)`), preventing the $O(n^3)$ explosion on large TSPLIB instances.

---

### academic_benchmark

#### [MODIFY] master_sota_engine.py
- **P1-2 (UnboundLocalError):** Initialize `selected_problems = None` before the interactive `while True:` loop in `_main_loop()`. Currently, if the script is run interactively without CLI args, it hits `if not selected_problems:` on the first iteration and crashes because the variable wasn't defined.

---

### uniride_core

#### [MODIFY] algorithms/sota_tsp/cgo_tsp.py
- **P1-5 (API Call Bug):** In `solve()` and `_expand_seeds()`, fix the `MultiLayerLS.improve()` calls to explicitly pass `dm_np=None` (or `self._dist_matrix_np`) to prevent argument misalignment.
- **P1-6 (Global Random):** Modify `_chaos_merge()` to accept an `rng: random.Random` parameter and replace the global `random.shuffle(missing)` with `rng.shuffle(missing)`. Update callers to pass `self._rng`.

#### [MODIFY] algorithms/sota_tsp/run_tsp.py
- **P1-5 (API Call Bug):** In `solve()`, fix the `MultiLayerLS.improve()` calls to explicitly pass `dm_np=None` to prevent argument misalignment with the Numba NumPy matrix parameter.
