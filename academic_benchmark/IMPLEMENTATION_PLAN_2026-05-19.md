# Implementation Plan — UniRide Academic Benchmark Bug Fixes & Improvements

**Date:** 2026-05-19
**Revised:** 2026-05-19 (Senior Developer Review)
**Source:** `AUDIT_FINDINGS_2026-05-19.md` (45 findings, 7 CRITICAL after reclassification)
**Strategy:** Fix critical bugs first, then high-severity, then medium. Each phase is independently testable.
**Review Notes:** See AUDIT_FINDINGS Appendix B for review verdict and required changes.

---

## Phase 1: Critical Bug Fixes (7 items) — Must Fix Immediately

### P1-1: Param Source Mapping Broken (C-01)
**File:** `smart_benchmark.py`
**Lines:** 724
**Time:** 5 min
**Risk:** Low — pure mapping fix

**Steps:**
1. Open `smart_benchmark.py` line 724
2. Replace the inline `ps_raw.lower()` expression with an explicit mapping dict
3. Verify the `run_unified_benchmark` function at line 416 checks for `'db'`, `'manual'`, `'default'`

**Code change:**
```python
# Line 724 — BEFORE:
run_unified_benchmark(problems, algos, ps_raw.lower() if ps_raw in ('B', 'M', 'D') else 'default',
                      runs, workers, metadata)

# AFTER:
param_map = {'B': 'db', 'M': 'manual', 'D': 'default'}
param_source = param_map.get(ps_raw, 'default')
run_unified_benchmark(problems, algos, param_source, runs, workers, metadata)
```

**Verification:**
- Run `smart_benchmark.py` → select option 3 → choose 'B' for DB params
- Confirm DB params are actually loaded (check console output)

---

### P1-2: `_ProblemWithSafeOptimal` Pickle Crash + Garbage Gaps (C-02)
**File:** `master_numba_engine.py`
**Lines:** 624-629, 664-666
**Time:** 15 min
**Risk:** Low — removing broken code, existing NaN fallback already works

**Steps:**
1. Delete the `_ProblemWithSafeOptimal` class definition (lines 624-629)
2. Remove `effective_problem` variable assignment (line 623)
3. Use `problem` directly in all calls (line 658, 661)
4. The existing NaN override at lines 664-666 already handles unknown optimals correctly

**Code change:**
```python
# Lines 621-629 — BEFORE:
    problem = _Problem(problem_dict)
    effective_problem = problem
    if not optimal:
        class _ProblemWithSafeOptimal(_Problem):
            def __init__(self, data: Dict[str, Any]):
                super().__init__(data)
                self.optimal = 1
        effective_problem = _ProblemWithSafeOptimal(problem_dict)

# AFTER (delete lines 623-629, keep line 622):
    problem = _Problem(problem_dict)
```

```python
# Lines 656-662 — BEFORE:
        elif is_time_matrix and time_matrix_data:
            result = run_single_test_with_matrix(
                effective_problem, strategy_payload, seed, strategy_params, time_matrix_data
            )
        else:
            result = run_single_test(effective_problem, strategy_payload, seed, strategy_params,
                                     dist_matrix=dist_matrix_np)

# AFTER:
        elif is_time_matrix and time_matrix_data:
            result = run_single_test_with_matrix(
                problem, strategy_payload, seed, strategy_params, time_matrix_data
            )
        else:
            result = run_single_test(problem, strategy_payload, seed, strategy_params,
                                     dist_matrix=dist_matrix_np)
```

**Verification:**
- Run `master_numba_engine.py` → tuning mode → select a problem with unknown optimal
- Confirm no pickle error on Windows
- Confirm gap shows "N/A" instead of huge number

---

### P1-3: SOTA Gap + Elapsed Time Fix (C-03 + C-04) — COMBINED
**File:** `master_sota_engine.py`
**Lines:** 1511-1535
**Time:** 15 min
**Risk:** Low — uses existing utility function + local timing
**Review Note:** C-03 and C-04 are in the same function, same lines. Combined into one atomic fix.

**Steps:**
1. In `_make_sota_executor`, add `time.perf_counter()` timing around `solver.solve()`
2. Replace inline gap calculation with `compute_gap()` call (also fixes H-06 dependency)
3. Add matrix square validation (M-10 bonus)

**Code change:**
```python
# Lines 1511-1535 — BEFORE:
    def executor(problem, params, seed, run_idx):
        run_params = params.copy()
        run_params["seed"] = seed
        solver = _make_solver(algo_name, run_params)
        matrix = _dm_from_cache(problem.name, TSPLIB_DB)
        if matrix is not None and len(matrix) == len(problem.coordinates):
            solver.set_dist_matrix(matrix)
        result = solver.solve(problem.coordinates)
        # Tour validation: ensure permutation is valid
        tour = getattr(result, "tour", [])
        n = problem.dimension
        if tour and len(tour) == n:
            assert len(set(tour)) == n, f"[{algo_name}] Invalid tour: duplicate nodes"
            assert min(tour) == 0, f"[{algo_name}] Invalid tour: min node {min(tour)} != 0"
            assert max(tour) == n - 1, f"[{algo_name}] Invalid tour: max node {max(tour)} != {n-1}"
        gap = ((result.tour_length - (problem.optimal or 0)) / max(problem.optimal or 1, 1)) * 100
        from academic_benchmark.engine_core import RunResult
        return RunResult(
            problem=problem.name, algorithm=algo_name,
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=problem.optimal, tour_cost=int(result.tour_length),
            gap_pct=round(gap, 4), elapsed_sec=result.elapsed_ms / 1000.0,
            iterations=result.iterations,
            tour=tour,
        )

# AFTER:
    def executor(problem, params, seed, run_idx):
        run_params = params.copy()
        run_params["seed"] = seed
        solver = _make_solver(algo_name, run_params)
        matrix = _dm_from_cache(problem.name, TSPLIB_DB)
        n = problem.dimension
        if matrix is not None and len(matrix) == n and all(len(r) == n for r in matrix):
            solver.set_dist_matrix(matrix)
        t0 = time.perf_counter()
        result = solver.solve(problem.coordinates)
        elapsed = time.perf_counter() - t0
        # Tour validation: ensure permutation is valid
        tour = getattr(result, "tour", [])
        if tour and len(tour) == n:
            assert len(set(tour)) == n, f"[{algo_name}] Invalid tour: duplicate nodes"
            assert min(tour) == 0, f"[{algo_name}] Invalid tour: min node {min(tour)} != 0"
            assert max(tour) == n - 1, f"[{algo_name}] Invalid tour: max node {max(tour)} != {n-1}"
        gap_pct, gap_type = compute_gap(problem.name, result.tour_length, problem.optimal)
        from academic_benchmark.engine_core import RunResult
        return RunResult(
            problem=problem.name, algorithm=algo_name,
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=problem.optimal, tour_cost=int(result.tour_length),
            gap_pct=round(gap_pct, 4) if not math.isnan(gap_pct) else None,
            elapsed_sec=round(elapsed, 3),
            iterations=result.iterations,
            tour=tour,
        )
```

**Verification:**
- Run SOTA algorithm via `smart_benchmark.py` (which uses AlgorithmRegistry)
- Confirm no `AttributeError` and elapsed time is non-zero
- Run on problem with unknown optimal → confirm gap shows "N/A" instead of 754200%

---

### P1-4: `optimal or TSPLIB_OPTIMALS` Discards Explicit Zero (H-06) — PROMOTED TO CRITICAL
**File:** `benchmark_utils.py`
**Lines:** 120
**Time:** 3 min
**Risk:** Low — pure logic fix
**Review Note:** Promoted from HIGH to CRITICAL because C-03 depends on `compute_gap()` working correctly. If H-06 is not fixed first, C-03 just moves the bug to a different location.

**Steps:**
1. Replace truthiness check with explicit None check

**Code change:**
```python
# Line 120 — BEFORE:
    opt = optimal or TSPLIB_OPTIMALS.get(problem.lower())

# AFTER:
    opt = optimal if optimal is not None else TSPLIB_OPTIMALS.get(problem.lower())
```

**Verification:** Call `compute_gap("test", 100, optimal=0)` → confirm it uses 0, not lookup

---

### P1-5: `Path` Not Imported in `master_sota_engine.py` (C-05)
**File:** `master_sota_engine.py`
**Lines:** 1697
**Time:** 2 min
**Risk:** Trivial

**Steps:**
1. Add `from pathlib import Path` to the imports section (after line 49)

**Code change:**
```python
# After line 49:
from pathlib import Path
```

**Verification:**
- Run `master_sota_engine.py` → press 'D' for Dashboard
- Confirm no `NameError`

---

### P1-6: Graceful Shutdown Windows-Only (C-06)
**File:** `smart_benchmark.py`
**Lines:** 134-135, 470-478, 834-839
**Time:** 45 min
**Risk:** Medium — involves terminal I/O, needs testing on both platforms
**Review Note:** Time estimate increased from 30→45 min. Added graceful degradation for systems without `termios`.

**Steps:**
1. Add cross-platform `_check_interrupt_key()` helper function after `graceful_shutdown()`
2. Replace `msvcrt.kbhit()` calls in `run_unified_benchmark` (line 470-475) and `run_benchmark` (line 834-839)
3. Keep Ctrl+C as no-op (intentional for safe copy-paste)
4. Add graceful degradation: if `termios` unavailable, return False with no-op

**Code change:**
```python
# Add after graceful_shutdown() (around line 156):

def _check_interrupt_key():
    """Check for Ctrl+Q / Ctrl+X / q / x without blocking.
    Cross-platform: msvcrt on Windows, select+termios on Unix.
    Ctrl+C is intentionally NOT checked here (safe for copy-paste).
    Graceful degradation: returns False if stdin unavailable (CI, piped input).
    """
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch()
            return key in (b'\x18', b'\x11', b'q', b'x', b'Q', b'X')
    else:
        try:
            import select, termios, tty
            if not sys.stdin.isatty():
                return False
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                if select.select([sys.stdin], [], [], 0.0)[0]:
                    ch = sys.stdin.read(1)
                    return ch in ('\x11', '\x18', 'q', 'x', 'Q', 'X')
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except (ImportError, OSError, AttributeError):
            pass  # Graceful degradation: no-op on systems without termios
    return False
```

Then replace in `run_unified_benchmark`:
```python
# Lines 470-475 — BEFORE:
            if sys.platform == 'win32':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b'\x18', b'\x11', b'q', b'x'):
                        _shutdown_requested = True

# AFTER:
            if _check_interrupt_key():
                _shutdown_requested = True
```

Same replacement in `run_benchmark` (lines 834-839).

**Verification:**
- On Windows: Run benchmark, press Ctrl+Q → confirm graceful shutdown
- On Linux/macOS: Run benchmark, press Ctrl+Q → confirm graceful shutdown
- On both: Ctrl+C should still be no-op (safe copy-paste)
- With piped input: confirm no crash, graceful degradation to no-op

---

### P1-7: Regression Tests for Critical Fixes
**Files:** `academic_benchmark/tests/`
**Time:** 30 min
**Risk:** Low — additive only

**Steps:**
1. Add test for C-01: param source mapping `'B'` → `'db'`
2. Add test for C-03: gap for unknown optimal returns NaN, not 754200%
3. Add test for C-04: SOTA executor returns valid `elapsed_sec`
4. Add test for H-06: `compute_gap` with explicit `optimal=0`

**Verification:**
- Run `python -m pytest academic_benchmark/tests/ -v` → all pass
- New tests cover critical bug scenarios

---

## Phase 2: High Severity Bug Fixes (6 items) — Fix Before Next Release

### P2-1: Perfect Results Display Wrong Symbol (H-01)
**Files:** `master_numba_engine.py:1113, 1199`
**Time:** 5 min

**Steps:**
1. Replace `result.get("avg_gap") or 100` with explicit None/NaN check at both locations

**Code change:**
```python
# Lines 1113 and 1199 — BEFORE:
        sym = "*" if (result.get("avg_gap") or 100) <= 1 else ("+" if (result.get("avg_gap") or 100) <= 5 else "o")

# AFTER:
        gap = result.get("avg_gap")
        sym = "*" if gap is not None and not math.isnan(gap) and gap <= 1 else (
              "+" if gap is not None and not math.isnan(gap) and gap <= 5 else "o")
```

**Verification:** Run tuning on a problem where algorithm finds optimal → confirm "*" symbol

---

### P2-2: Optuna Results Not Saved to Metadata (H-02)
**File:** `master_numba_engine.py:1364-1393`
**Time:** 20 min

**Steps:**
1. After each `study.optimize()` call, save best params to `metadata["best_params"]`
2. Save metadata to disk

**Code change:**
```python
# After line 1391 (inside the for loop, after print statements):
            key = f"{problem.name}::{spec.name}"
            defaults = spec.default_params.copy()
            metadata.setdefault("best_params", {})[key] = {
                "params": {**defaults, **study.best_params},
                "avg_gap": study.best_value,
                "n_runs": n_runs,
            }
            save_metadata(METADATA_PATH, metadata)
```

**Verification:**
- Run Optuna tuning → check `master_numba_metadata.json` for `best_params` entries

---

### P2-3: SOTA Optuna Conflates avg_length and avg_gap (H-03) — SIMPLIFIED
**File:** `master_sota_engine.py:1158-1165`
**Time:** 10 min
**Review Note:** Simplified — instead of re-running solver (which doubles tuning time), store `study.best_value` as `objective_value` with clear label. Add `avg_length: null` placeholder.

**Steps:**
1. Rename `avg_length` field to `objective_value` to avoid confusion
2. Add `avg_length: null` placeholder for downstream compatibility

**Code change:**
```python
# Lines 1158-1165 — BEFORE:
            key = f"{problem.name}::{algo}"
            defaults = _make_solver_config(algo, problem.dimension, _NUMBA_AVAILABLE)
            best_params[key] = {
                "params": {**defaults, **study.best_params},
                "avg_length": study.best_value,
                "avg_gap": study.best_value,
                "n_runs": n_runs,
            }

# AFTER:
            key = f"{problem.name}::{algo}"
            defaults = _make_solver_config(algo, problem.dimension, _NUMBA_AVAILABLE)
            best_params[key] = {
                "params": {**defaults, **study.best_params},
                "objective_value": study.best_value,
                "avg_gap": study.best_value,
                "avg_length": None,  # Placeholder — requires separate evaluation
                "n_runs": n_runs,
            }
```

**Verification:** Check `best_params` JSON — `objective_value` clearly labeled, `avg_length` is `null`

---

### P2-4: DB Param Loading Overwrites Per-Problem Params (H-04) — POSTPONED
**File:** `master_sota_engine.py:1369-1375`
**Time:** TBD
**Status:** ⏸️ **Postponed pending user decision on backward compatibility strategy**
**Review Note:** Changing DB param keys from `{algo: params}` to `{f"{prob}::{algo}": params}` breaks all callers. Need to audit all `_param_db_get_best` consumers first.

**Pending decisions:**
- Should we maintain backward compatibility with old key format?
- Or do a clean break with a migration note?
- Which callers need updating? (grep for `_param_db_get_best` consumers)

---

### P2-5: `int()` Truncates Float Tour Lengths (H-05)
**File:** `master_numba_engine.py:570`
**Time:** 5 min

**Steps:**
1. Replace `int(tour_length)` with `round(tour_length)` for time-matrix problems

**Code change:**
```python
# Line 570 — BEFORE:
    tour_length = int(tour_length)

# AFTER:
    tour_length = int(tour_length) if not is_time_matrix else round(tour_length, 2)
```

**Verification:** Run time-matrix problem → confirm tour_length preserves decimal precision

---

### P2-6: `_evaluate_sota_combo` Gap Uses Truthiness (H-07)
**File:** `master_sota_engine.py:710`
**Time:** 3 min

**Steps:**
1. Replace `if optimal` with explicit check

**Code change:**
```python
# Line 710 — BEFORE:
        avg_gap = ((avg_cost - optimal) / optimal * 100.0) if optimal else float("nan")

# AFTER:
        avg_gap = ((avg_cost - optimal) / optimal * 100.0) if (optimal is not None and optimal > 0) else float("nan")
```

**Verification:** Same as H-06

---

## Phase 3: Medium Severity Bug Fixes (11 items) — Fix in Next Sprint

### P3-1: CSV Race Condition (M-01)
**File:** `benchmark_utils.py:774-782`
**Time:** 15 min
**Approach:** Use `fcntl` (Unix) or `msvcrt.locking` (Windows) for file locking, or use atomic append with retry

### P3-2: `_current_metadata` Could Be None (M-02)
**File:** `smart_benchmark.py:504`
**Time:** 3 min
**Fix:** Add `if _current_metadata is not None:` guard

### P3-3: `selected_problems` May Be Undefined (M-03)
**File:** `master_sota_engine.py:1708`
**Time:** 3 min
**Fix:** Initialize `selected_problems = None` before while loop, update check to `if selected_problems is None:`

### P3-4: Graceful Shutdown TOCTOU (M-04)
**File:** `smart_benchmark.py:148-152`
**Time:** 10 min
**Fix:** Snapshot list under lock or use `results_copy = list(_current_results)` before access

### P3-5: `dist_matrix` Converted to Python List (M-05)
**File:** `smart_benchmark.py:432`
**Time:** 5 min
**Fix:** Keep as numpy array — verify downstream code handles numpy arrays

### P3-6: `assert` for Tour Validation (M-06)
**Files:** `master_numba_engine.py:1597-1603`, `master_sota_engine.py:645-648, 1522-1524`
**Time:** 15 min
**Fix:** Replace `assert` with `if` + logging + graceful error handling

### P3-7: Optuna Trial Count Too Low (M-07)
**File:** `master_numba_engine.py:1388`
**Time:** 3 min
**Fix:** Add `OPTUNA_DEFAULT_TRIALS = 100` constant, use instead of `DOE_MAX_COMBINATIONS`

### P3-8: Dead Code (M-08)
**File:** `master_sota_engine.py:1631`
**Time:** 1 min
**Fix:** Remove line

### P3-9: Windows Encoding Missing PyPy Check (M-09)
**Files:** `master_numba_engine.py:50-55`, `master_sota_engine.py:52-57`
**Time:** 5 min
**Fix:** Match `smart_benchmark.py` pattern with `hasattr(sys, 'implementation')` guard

### P3-10: Missing Matrix Validation (M-10)
**File:** `master_sota_engine.py:630-631`
**Time:** 5 min
**Fix:** Add `all(len(r) == n for r in matrix)` check

### P3-11: `engine_core.py` Performance (M-11)
**File:** `engine_core.py:19-46`
**Time:** 30 min
**Fix:** Use numpy for distance matrix, `np.argpartition` for KNN mask

---

## Phase 5: Optuna Parallelization & Optimization (4 items) — ✅ COMPLETED 2026-05-19

### P5-1: Dynamic Queue Architecture for Optuna (D-01 + D-04)
**Files:** `master_sota_engine.py`, `master_numba_engine.py`
**Status:** ✅ COMPLETED
**Time:** ~2 hours
**Description:** Replaced `study.optimize()` loop with `study.ask()` / `study.tell()` pattern. Main process holds all studies, workers pull trials from shared pool. All workers stay busy 100% of time regardless of algorithm speed differences.

**Key Functions:**
- `_run_sota_trial_task()` — worker function for SOTA trials
- `_run_numba_trial_task()` — worker function for Numba trials
- `_should_stop_early()` — early stopping check (gap ≤ 0.01% for 3 consecutive trials)

### P5-2: Early Stopping for Optuna Studies (D-02)
**Status:** ✅ COMPLETED
**Description:** Stops study when gap ≤ 0.01% for 3 consecutive trials. Prevents wasting hours on small problems where optimal is already found.

### P5-3: Time-Based Tie-Breaking (D-03)
**Status:** ✅ COMPLETED
**Description:** Among equal-gap trials, selects the fastest one. Stores `avg_time_sec` during trial execution.

### P5-4: Progress Reporting
**Status:** ✅ COMPLETED
**Description:** Real-time progress: `[OPTUNA] 47 trials done | 8 active | 2/6 studies stopped`

---

## Phase 4: Low Severity + UI/UX + General (21 items) — Backlog

All items from sections 4, 5, 6 of audit report. Prioritize based on user feedback.

---

## Testing Strategy

### After Each Phase:
1. Run existing test suite: `python -m pytest academic_benchmark/tests/ -v`
2. Run new regression tests (Phase 1): `python -m pytest academic_benchmark/tests/test_critical_fixes.py -v`
3. Manual smoke test:
   - `python academic_benchmark/smart_benchmark.py` → main menu loads
   - Select option 1 → tuning → confirm algorithms run
   - Select option 3 → benchmark → confirm results display
   - Select option D → dashboard → confirm Streamlit opens
4. Cross-platform test: Run on both Windows and Linux (if available)

### Specific Test Cases:
| Test | Phase | Description |
|------|-------|-------------|
| Param source mapping | P1 | `'B'` → `'db'` mapping works |
| Unknown optimal gap | P1 | Run on problem with no optimal → confirm "N/A" not huge number |
| SOTA via registry | P1 | Run SOTA algorithm via smart_benchmark → no AttributeError |
| compute_gap with optimal=0 | P1 | Explicit zero preserved, not discarded |
| Perfect result symbol | P2 | Algorithm finds optimal → confirm "*" not "o" |
| Optuna persistence | P2 | Run Optuna → restart → confirm best params saved |
| Time-matrix precision | P2 | Run time-matrix problem → confirm decimal tour length |
| Cross-platform interrupt | P1 | Press Ctrl+Q on Windows/Linux → confirm graceful shutdown |
| Ctrl+C safe | P1 | Press Ctrl+C → confirm no crash, benchmark continues |
| Piped input degradation | P1 | Run with piped input → confirm no crash, graceful no-op |

---

## Estimated Timeline

| Phase | Items | Est. Time | Cumulative | Status |
|-------|-------|-----------|------------|--------|
| Phase 1 (Critical) | 7 | ~2 hours | 2 hours | ✅ Done |
| Phase 2 (High) | 5 (+ 1 postponed) | ~45 min | 2.75 hours | ✅ Done |
| Phase 3 (Medium) | 11 | ~2 hours | 4.75 hours | ✅ Done |
| Phase 5 (Optuna) | 4 | ~2 hours | 6.75 hours | ✅ Done |
| Phase 4 (Backlog) | 21 | ~4 hours | 10.75 hours | Pending |
| Regression tests | 4 new tests | ~30 min | 11.25 hours | Pending |
| Cross-platform verification | C-06 | ~1 hour | 12.25 hours | Pending |
| Buffer (20%) | — | ~2 hours | **~14.25 hours** | — |

**Total estimated effort: ~14.25 hours** (revised from 12h — added Optuna parallelization phase)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cross-platform keyboard polling breaks on some terminals | Medium | Medium | Test on multiple terminal emulators; fallback to no-op |
| `termios` not available on all Unix systems | Low | Low | Wrap in try/except, fallback to no-op (added in P1-6) |
| `sys.stdin.isatty()` fails in CI/piped input | Medium | Low | Graceful degradation: return False (added in P1-6) |
| Numpy array changes break multiprocessing serialization | Low | High | Test with ProcessPoolExecutor after M-05 fix |
| DB param key format change breaks backward compatibility | Medium | Medium | **Postponed** — needs user decision on strategy |
| C-03 + H-06 coupling missed in original plan | Medium | High | **Fixed** — H-06 moved to Phase 1, applied before C-03 |
| SOTA executor test requires live solver run | Low | Medium | Mock solver for unit test, live test for integration |
