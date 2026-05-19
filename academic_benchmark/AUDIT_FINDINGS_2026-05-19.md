# Comprehensive Audit Report — UniRide Academic Benchmark

**Date:** 2026-05-19
**Scope:** `smart_benchmark.py`, `master_numba_engine.py`, `master_sota_engine.py`, `benchmark_utils.py`, `engine_core.py`
**Severity Levels:** CRITICAL (crash/data loss), HIGH (wrong results), MEDIUM (silent bug), LOW (code quality)

---

## 1. CRITICAL Bugs (Crash / Data Loss / Wrong Results)

### C-01: Param Source Mapping Broken in `smart_benchmark.py:724`
```python
run_unified_benchmark(problems, algos, ps_raw.lower() if ps_raw in ('B', 'M', 'D') else 'default', ...)
```
**Problem:** User selects 'B' → passes `'b'` to `run_unified_benchmark`. But line 416 checks `if param_source == 'db':`. `'b' != 'db'`, so DB lookup NEVER triggers. Benchmark always runs with empty params.
**Impact:** DB-based benchmarking silently degrades to default params.
**Fix:**
```python
param_map = {'B': 'db', 'M': 'manual', 'D': 'default'}
param_source = param_map.get(ps_raw, 'default')
```

### C-02: `_ProblemWithSafeOptimal` Cannot Be Pickled — `master_numba_engine.py:624-629`
```python
class _ProblemWithSafeOptimal(_Problem):
    def __init__(self, data):
        super().__init__(data)
        self.optimal = 1
```
**Problem:** Class defined inside `_evaluate_param_combo`. On Windows with `spawn` multiprocessing, child processes cannot pickle local classes. Also, fake `optimal=1` produces garbage gap values (e.g., 754200% for berlin52).
**Impact:** Crashes on Windows multiprocessing; silently wrong gaps when it does run.
**Fix:** Remove the class entirely. Use `float("nan")` for unknown optimals (already done at line 664-666).

### C-03: SOTA Gap Calculation Produces Meaningless Numbers — `master_sota_engine.py:1526`
```python
gap = ((result.tour_length - (problem.optimal or 0)) / max(problem.optimal or 1, 1)) * 100
```
**Problem:** When `problem.optimal is None`: numerator = `tour_length - 0`, denominator = `1`. Gap = `tour_length * 100`. A 7542-cost tour shows gap=754200%.
**Impact:** All unknown-optimal problems display absurd gap percentages.
**Fix:** Use `compute_gap()` utility:
```python
gap_pct, gap_type = compute_gap(problem.name, result.tour_length, problem.optimal)
```

### C-04: SOTA Executor Missing `elapsed_ms` Attribute — `master_sota_engine.py:1532`
```python
elapsed_sec=result.elapsed_ms / 1000.0,
```
**Problem:** SOTA solver results don't have `elapsed_ms`. Elapsed time is measured locally in `_run_solver_task` (line 629-634) but NOT in `_make_sota_executor`.
**Impact:** `AttributeError` crash when using SOTA algorithms via `AlgorithmRegistry`.
**Fix:** Measure elapsed time locally in the executor:
```python
t0 = time.perf_counter()
result = solver.solve(problem.coordinates)
elapsed = time.perf_counter() - t0
```

### C-05: `Path` Not Imported in `master_sota_engine.py:1697`
```python
subprocess.run(["streamlit", "run", str(Path(__file__).resolve().parent / "dashboard.py")])
```
**Problem:** `from pathlib import Path` is missing.
**Impact:** `NameError` when user selects Dashboard option.
**Fix:** Add `from pathlib import Path` at top of file.

### C-06: Graceful Shutdown is Windows-Only — `smart_benchmark.py:134-135, 470-478`
```python
def signal_handler(signum, frame):
    pass  # Intentional: Ctrl+C is no-op to allow safe copy-paste from terminal
signal.signal(signal.SIGINT, signal_handler)
```
**Problem:** Ctrl+C is intentionally swallowed to prevent accidental stops when users copy from terminal (good). However, the graceful shutdown mechanism (`Ctrl+Q` / `Ctrl+X`) uses `msvcrt.kbhit()` which is **Windows-only**. On Linux/macOS, the printed message `'Press Ctrl+Q to safely stop'` is misleading — it does nothing.
**Impact:** Linux/macOS users have no way to gracefully stop a running benchmark.
**Fix:** Add cross-platform keyboard polling using `select` + `termios`:
```python
def _check_interrupt_key():
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch()
            return key in (b'\x18', b'\x11', b'q', b'x')
    else:
        import select, sys, termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            if select.select([sys.stdin], [], [], 0.0)[0]:
                ch = sys.stdin.read(1)
                return ch in ('\x11', '\x18', 'q', 'x')
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return False
```
Replace `msvcrt.kbhit()` calls at lines 470-475 and 834-839 with `_check_interrupt_key()`.

---

## 2. HIGH Severity Bugs (Wrong Results / Data Corruption)

### H-01: Perfect Results Display Wrong Symbol — `master_numba_engine.py:1113, 1199`
```python
sym = "*" if (result.get("avg_gap") or 100) <= 1 else ...
```
**Problem:** When `avg_gap` is `0.0` (perfect match to optimal), `0.0 or 100` evaluates to `100`. Perfect results display "o" instead of "*".
**Impact:** Misleading visual indicators in tuning/benchmark output.
**Fix:**
```python
gap = result.get("avg_gap")
sym = "*" if gap is not None and not math.isnan(gap) and gap <= 1 else (
      "+" if gap is not None and not math.isnan(gap) and gap <= 5 else "o")
```

### H-02: Optuna Results Not Saved to Metadata — `master_numba_engine.py:1364-1393`
**Problem:** After Optuna tuning completes, `study.best_params` and `study.best_value` are printed but NEVER saved to `metadata["best_params"]`. Unlike grid search (line 1120), Optuna results are lost after the function returns.
**Impact:** All Optuna tuning work is discarded. No persistence.
**Fix:** Save results after each study:
```python
key = f"{problem.name}::{spec.name}"
metadata.setdefault("best_params", {})[key] = {
    "params": {**spec.default_params, **study.best_params},
    "avg_gap": study.best_value,
    "avg_length": ...,  # re-run or compute
}
save_metadata(METADATA_PATH, metadata)
```

### H-03: SOTA Optuna Conflates `avg_length` and `avg_gap` — `master_sota_engine.py:1162-1163`
```python
best_params[key] = {
    "avg_length": study.best_value,
    "avg_gap": study.best_value,
}
```
**Problem:** `study.best_value` is the gap% (when optimal known) or raw avg_cost (when unknown). Both fields get the same value, but `avg_length` should be the actual tour length.
**Impact:** Downstream code reading `avg_length` gets gap% instead of tour length.
**Fix:** Re-run with best params to get actual avg_length, or store objective value with clear label.

### H-04: DB Param Loading Overwrites Per-Problem Params — `master_sota_engine.py:1369-1375`
```python
for prob in problems:
    for algo in algos:
        best = _param_db_get_best(prob.name, algo)
        if best:
            result[algo] = best["params"]  # Last problem wins!
```
**Problem:** Dict keyed by `algo` only. When loading params for multiple problems, the last problem's params overwrite all previous ones.
**Impact:** Data loss — only the last problem's best params survive.
**Fix:** Key by `(problem_name, algo)` or return per-problem params.

### H-05: `int()` Truncates Float Tour Lengths — `master_numba_engine.py:570`
```python
tour_length = int(tour_length)
```
**Problem:** For time-matrix problems with float costs (e.g., 1234.56 seconds), `int()` truncates to 1234, losing precision.
**Impact:** Incorrect gap calculations for time-matrix problems.
**Fix:** `tour_length = round(tour_length)` or keep as float for time-matrix problems.

### H-06: `optimal or TSPLIB_OPTIMALS` Discards Explicit Zero — `benchmark_utils.py:120`
```python
opt = optimal or TSPLIB_OPTIMALS.get(problem.lower())
```
**Problem:** If `optimal=0` is passed explicitly, `0 or X` evaluates to `X`, discarding the explicit value.
**Impact:** Incorrect gap if a problem genuinely has optimal=0.
**Fix:** `opt = optimal if optimal is not None else TSPLIB_OPTIMALS.get(problem.lower())`

### H-07: `_evaluate_sota_combo` Gap Uses Truthiness — `master_sota_engine.py:710`
```python
avg_gap = ((avg_cost - optimal) / optimal * 100.0) if optimal else float("nan")
```
**Problem:** `if optimal` catches `optimal=0` (falsy), falling to NaN instead of computing gap. Also, if optimal is very small float, gap could be enormous but that's mathematically correct.
**Fix:** `if optimal is not None and optimal > 0:`

---

## 3. MEDIUM Severity Bugs (Silent Issues)

### M-01: CSV Race Condition — `benchmark_utils.py:774-782`
```python
exists = os.path.exists(path)
with open(path, "a", ...) as f:
    if not exists:
        writer.writeheader()
```
**Problem:** Two processes may both see `exists=False` and both write headers, resulting in duplicate header rows in CSV.
**Impact:** Corrupted CSV files when using ProcessPoolExecutor.
**Fix:** Use file locking or atomic writes.

### M-02: `_current_metadata` Could Be None — `smart_benchmark.py:504`
```python
_current_metadata["results"] = saved_results
```
**Problem:** If `_current_metadata` is None (its initial value), this raises `TypeError`.
**Fix:** Guard: `if _current_metadata is not None:`

### M-03: `selected_problems` May Be Undefined — `master_sota_engine.py:1708`
**Problem:** In the interactive while-loop, `selected_problems` is only defined inside the `if args.mode:` block. On first iteration without `--mode`, line 1708 references an undefined variable.
**Fix:** Initialize `selected_problems = None` before the while loop.

### M-04: Graceful Shutdown TOCTOU — `smart_benchmark.py:148-152`
**Problem:** `_current_results[0].keys()` accessed without lock. If another thread modifies the list between the `if` check and the access, `IndexError` possible.
**Fix:** Snapshot the list under a lock.

### M-05: `dist_matrix` Converted to Python List — `smart_benchmark.py:432`
```python
p.dist_matrix = dm.astype(np.float64).tolist()
```
**Problem:** Converting numpy array to Python list of lists is extremely memory-inefficient for large problems (1000×1000 = 1M Python floats vs compact numpy array).
**Fix:** Keep as numpy array: `p.dist_matrix = dm.astype(np.float64)`

### M-06: `assert` for Tour Validation — `master_numba_engine.py:1597-1603`, `master_sota_engine.py:645-648, 1522-1524`
**Problem:** `assert` statements are stripped in `python -O` mode. Invalid tours pass silently. Also, `AssertionError` crashes the entire benchmark run.
**Fix:** Replace with proper validation that logs warning and handles gracefully.

### M-07: Optuna Trial Count Too Low — `master_numba_engine.py:1388`
```python
study.optimize(..., n_trials=DOE_MAX_COMBINATIONS)  # 50
```
**Problem:** 50 trials may be too few for high-dimensional spaces (B-GA has 7 parameters).
**Fix:** Add separate constant: `OPTUNA_DEFAULT_TRIALS = 100`.

### M-08: Dead Code — `master_sota_engine.py:1631`
```python
selected_problems = all_problems
selected_problems = _select_problems_from_args(args, all_problems)
```
**Problem:** First assignment immediately overwritten.
**Fix:** Remove line 1631.

### M-09: Windows Encoding Fix Inconsistent — `master_numba_engine.py:50-55`
```python
if sys.platform == "win32":
```
**Problem:** `smart_benchmark.py:30` checks `sys.platform == 'win32' or 'pypy' in sys.implementation.name.lower()` but `master_numba_engine.py:50` only checks `sys.platform == "win32"`. On PyPy running on Linux, the encoding fix is skipped, potentially causing UnicodeEncodeError on non-ASCII output.
**Impact:** Inconsistent behavior across engines; crashes on PyPy with non-ASCII characters.
**Fix:** Match smart_benchmark.py pattern:
```python
_is_pypy = hasattr(sys, 'implementation') and 'pypy' in sys.implementation.name.lower()
if sys.platform == "win32" or _is_pypy:
```
Apply same fix to `master_sota_engine.py:52`.

### M-10: Missing Matrix Validation in SOTA Solver — `master_sota_engine.py:630-631`
```python
if matrix is not None and len(matrix) == len(coordinates):
    solver.set_dist_matrix(matrix)
```
**Problem:** Only checks `len(matrix) == n` but doesn't verify the matrix is square (`len(row) == n` for all rows) or that row lengths are consistent. A malformed matrix from the DB cache could cause silent wrong-distance calculations or downstream crashes.
**Impact:** Wrong tour costs if DB cache contains malformed matrix.
**Fix:**
```python
if matrix is not None and len(matrix) == n and all(len(r) == n for r in matrix):
    solver.set_dist_matrix(matrix)
```

### M-11: `engine_core.py` Performance — `ProblemInstance.prepare_matrices()` (lines 19-46)
**Problem:**
1. Distance matrix built as Python lists of lists — O(n²) memory with Python object overhead (each float is a full Python object, ~28 bytes vs 8 bytes in numpy).
2. KNN mask computation is O(n² log n) — sorts entire row for each node, no caching.
3. No NumPy acceleration despite numpy being available.
**Impact:** For n=1000, distance matrix uses ~28MB vs ~8MB with numpy. KNN mask takes ~10x longer than necessary.
**Fix:**
```python
import numpy as np
# Use numpy for distance matrix
np_matrix = np.zeros((n, n), dtype=np.float64)
# Use np.argpartition for KNN (O(n² k) instead of O(n² log n))
self.knn_mask[i] = np.argpartition(row, k)[:k].tolist()
```

---

## 4. LOW Severity (Code Quality / Compatibility)

### L-01: `set[Tuple[...]]` Syntax — `master_numba_engine.py:869`
**Problem:** Python 3.9+ only syntax. Breaks on Python 3.8 (common in academic/HPC environments).
**Fix:** `from __future__ import annotations` or use `Set[Tuple[str, str, str]]` from `typing`.

### L-02: Fallback File Encoding — `master_numba_engine.py:393`
**Problem:** `encoding="utf-8"` may fail for TSPLIB files with Latin-1 encoding (European city names).
**Fix:** `encoding="utf-8", errors="replace"` to match SOTA engine approach.

### L-03: `_count_combinations` Returns 0 for Bayesian — `smart_benchmark.py:227-228`
**Problem:** Returns 0 for Bayesian mode, but pre-run summary uses `self.max_combos` as trial count. Inconsistent.
**Fix:** Return `self.max_combos` for Bayesian, or add separate method.

### L-04: `sys.implementation` Access Without Guard — `smart_benchmark.py:30`
**Problem:** `sys.implementation.name` may not exist on exotic Python implementations.
**Fix:** `hasattr(sys, 'implementation') and 'pypy' in sys.implementation.name.lower()`

---

## 5. UI/UX Improvement Recommendations

### UX-01: Graceful Shutdown Windows-Only
**Current:** "Press Ctrl+Q to safely stop" printed on all platforms, but `msvcrt.kbhit()` only works on Windows. Ctrl+C intentionally no-op for safe copy-paste.
**Recommendation:** Implement cross-platform keyboard polling (see C-06 fix). Keep Ctrl+C as no-op. Show platform-appropriate key hints.

### UX-02: No Progress Bar, Only Text
**Current:** Progress shown as `\r[PROGRESS] 5/100 | ...` text line.
**Recommendation:** Add ASCII progress bar: `[####........] 5/100 (5%)`. Consider `tqdm` for rich progress bars.

### UX-03: Missing ETA in Smart Benchmark
**Current:** `smart_benchmark.py` has no ETA tracking. Numba engine has `ETATracker`.
**Recommendation:** Integrate `ETATracker` into `run_unified_benchmark` for consistent UX across all modes.

### UX-04: Confusing Param Source Labels
**Current:** "DB'den en iyi" / "Manuel" / "Varsayilan" — but DB option silently falls to default due to C-01.
**Recommendation:** After fixing C-01, add confirmation: "Found 3 param sets in DB for selected problems."

### UX-05: No Algorithm Comparison View
**Current:** Results printed as flat table. No side-by-side comparison.
**Recommendation:** Add summary comparison table at end:
```
Problem      | Best Algo    | Gap%  | 2nd Best   | Gap%  | Worst      | Gap%
berlin52     | Numba-GA     | 0.00% | B-GA       | 0.12% | HHO        | 15.3%
```

### UX-06: Dashboard Launch Blocks Terminal
**Current:** `subprocess.run()` blocks until Streamlit exits.
**Recommendation:** Use `subprocess.Popen()` to launch dashboard in background, print PID for later cleanup.

### UX-07: No Resume After Interrupt
**Current:** After Ctrl+X, results saved to CSV but benchmark cannot resume.
**Recommendation:** Add `--resume` flag that reads interrupted CSV and skips completed tasks.

---

## 6. General Improvement Recommendations

### G-01: Add Threading Locks for Shared State
**Files:** `smart_benchmark.py`, `master_sota_engine.py`
**Recommendation:** Use `threading.Lock()` around `_current_results`, `_active_results`, `metadata` modifications in parallel execution paths.

### G-02: Replace `assert` with Proper Validation
**Files:** `master_numba_engine.py:1597-1603`, `master_sota_engine.py:645-648, 1522-1524`
**Recommendation:** Use explicit `if` checks with logging. Return error results instead of crashing.

### G-03: Use `compute_gap()` Consistently
**Files:** `master_sota_engine.py:710, 1526`
**Recommendation:** Replace all inline gap calculations with `compute_gap()` utility that handles BSF fallback.

### G-04: Add Unit Tests for Gap Calculation
**Recommendation:** Test cases for: known optimal, unknown optimal (BSF), zero optimal, NaN gap, very large gap.

### G-05: Consider `tqdm` for Progress
**Recommendation:** Replace manual `\r` progress with `tqdm` for rich progress bars, ETA, and rate display. Already used in Optuna (`show_progress_bar=True`).

### G-06: Add Logging Framework
**Recommendation:** Replace `print()` with `logging` module. Allows file logging, log levels, and structured output.

### G-07: CSV Schema Versioning
**Recommendation:** Add schema version header to CSV files. Dashboard already handles 8 vs 9 column mismatch, but versioning prevents future breakage.

### G-08: Memory Optimization for Large Problems
**File:** `smart_benchmark.py:432`
**Recommendation:** Keep distance matrices as numpy arrays. Pass numpy arrays through multiprocessing using shared memory or memory-mapped files.

### G-09: Add `--resume` Flag
**Recommendation:** Check `benchmark_progress.csv` for completed (problem, algorithm) pairs and skip them.

### G-10: Type Annotations Consistency
**Recommendation:** Add `from __future__ import annotations` to all files for forward-compatible type hints (e.g., `list[str]` instead of `List[str]`).

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| CRITICAL | 6 | Fix immediately |
| HIGH | 7 | Fix before next release |
| MEDIUM | 11 | Fix in next sprint |
| LOW | 4 | Backlog |
| UI/UX | 7 | Backlog |
| General | 10 | Backlog |

**Total findings: 45**

---

## Appendix: Cross-Check with External Audit

The following findings were identified by another AI and verified against this report:

| External Finding | Status | Report Reference |
|-----------------|--------|-----------------|
| `sys.implementation` may not exist on exotic Pythons | ✅ Already covered | **L-04** |
| `_ProblemWithSafeOptimal` fake optimal=1 → misleading gaps | ✅ Already covered | **C-02** |
| Tour validation uses `assert` (disabled with `-O`) | ✅ Already covered | **M-06** / **G-02** |
| `selected_problems = all_problems` dead code | ✅ Already covered | **M-08** |
| Windows encoding fix missing PyPy check in numba engine | ✅ **Added** | **M-09** |
| `_dm_from_cache` doesn't verify matrix is square | ✅ **Added** | **M-10** |
| `engine_core.py` Python lists + O(n² log n) KNN | ✅ **Added** | **M-11** |
| Signal handler `fieldnames=list(_active_results[0].keys())` crashes if empty | ❌ **False positive** | Code already guards: `if _active_results:` before `[0]` access in both engines (numba:223, sota:251) |
| Ctrl+C no-op is wrong | ❌ **False positive** | Intentional design: prevents accidental stops when copying from terminal. Real issue is Ctrl+Q/Ctrl+X only works on Windows (C-06 updated) |

---

## Appendix B: Senior Developer Review (2026-05-19)

### Review Verdict: **Strong audit, good plan — needs adjustments**

**What's correct:**
- Well-structured with specific line numbers, concrete code snippets, sound severity prioritization
- Cross-check appendix with external audit adds credibility
- False positive identification (signal handler empty list, Ctrl+C intentional) shows rigor
- C-02 approach is right: delete `_ProblemWithSafeOptimal`, rely on existing NaN fallback
- Phase ordering (Critical → High → Medium → Backlog) is correct

**Required changes:**

| # | Change | Reason |
|---|--------|--------|
| 1 | **Move H-06 to Phase 1** | C-03 replaces inline gap calc with `compute_gap()`, but `compute_gap()` itself has the H-06 truthiness bug (`optimal or X`). Fixing C-03 without H-06 just moves the bug to a different location. These two are **coupled**. |
| 2 | **Combine C-03 + C-04** | Same function, same lines. Should be one atomic commit, not two separate tasks. |
| 3 | **Add regression tests** | Plan says "run existing tests" but doesn't add new tests for the bugs being fixed. Each critical fix should have at least one test. |
| 4 | **C-06 time estimate (30 min) is optimistic** | `termios`/`tty` on Unix has real risks: `sys.stdin.fileno()` fails if stdin is redirected (CI, piped input), `tty.setcbreak()` changes terminal state globally — crash leaves terminal broken. Needs `try/except` + graceful degradation to no-op. |
| 5 | **H-04 breaking change is under-scoped** | Changing DB param keys from `{algo: params}` to `{f"{prob}::{algo}": params}` breaks all callers. Need to grep for `_param_db_get_best` consumers and update them in the same commit. → **Postponed pending user decision on backward compatibility strategy.** |
| 6 | **H-03 avg_length re-run adds complexity** | Re-running solver to get actual avg_length doubles tuning time. Alternative: store objective value with clear label instead. → **Simplified: store `study.best_value` as `objective_value`, add `avg_length: null` placeholder.** |
| 7 | **Realistic timeline: ~12 hours** | 8.5h is optimistic for 45 findings with proper testing, cross-platform verification, and regression tests. |

### Updated Severity Classification

| Severity | Original | Revised | Change |
|----------|----------|---------|--------|
| CRITICAL | 6 | 7 | H-06 promoted (coupled with C-03) |
| HIGH | 7 | 6 | H-06 moved to CRITICAL |
| MEDIUM | 11 | 11 | No change |
| LOW | 4 | 4 | No change |
| UI/UX | 7 | 7 | No change |
| General | 10 | 10 | No change |

**Total findings: 45** (same, just reclassified)

---

## Appendix C: H-04 Resolution — DB Param Key Format Change (2026-05-19)

### Decision: Option B — Clean Break with Per-Problem Keys

**Chosen:** Change DB param keys from `{algo: params}` to `{f"{prob.name}::{algo}": params}`.

### Why Option B Was Chosen

| Criteria | Option A (Backward Compat) | Option B (Clean Break) ✅ | Option C (Hybrid Merge) |
|----------|---------------------------|--------------------------|------------------------|
| Correctness | Partial — dual-key logic | Full — single code path | Broken — semantically wrong |
| Code complexity | High — two paths to maintain | Low — one path | Medium — merge logic |
| Silent data corruption | Still possible with old metadata | Impossible | Different form of corruption |
| Migration cost | Hidden (maintain forever) | One-time re-tuning | None (but wrong results) |
| Future-proof | No | Yes | No |

**Key reasoning:**
1. The current behavior is **silently wrong** — users get last problem's params for all problems. Better to break loudly than silently produce wrong results.
2. The consumer functions needed updating regardless, so "backward compat" was illusory.
3. DB params are **regenerable** — users can re-run tuning to repopulate. Not irreplaceable data.
4. Simpler code = fewer future bugs.

### What Changed

| File | Function | Change |
|------|----------|--------|
| `master_sota_engine.py` | `_load_params_from_db_interactive` | Keys now `f"{prob.name}::{algo}"` |
| `master_sota_engine.py` | `_run_engine_with_params` | Lookup per-problem key, fallback to legacy |
| `master_numba_engine.py` | `_load_params_from_db_interactive` | Keys now `f"{prob.name}::{spec.name}"` |
| `master_numba_engine.py` | `_run_benchmark_with_params` | Lookup per-problem key, fallback to legacy |
| `smart_benchmark.py` | `run_unified_benchmark` | Per-problem DB lookup instead of `problems[0]` only |

### What Users Need to Do

1. **Existing metadata files** (`master_numba_metadata.json`, `master_sota_metadata.json`): Old `{algo: params}` entries will still work via the legacy fallback. No immediate action required.

2. **New tuning runs**: Will produce `{f"{prob.name}::{algo}": params}` entries. These take priority over legacy entries.

3. **To regenerate per-problem params**: Run tuning mode for each problem individually, or run multi-problem tuning — params will now be correctly stored per problem.

4. **Old multi-problem DB loads**: Were silently wrong (all problems got last problem's params). Re-run tuning to get correct per-problem params.

### Backward Compatibility

Both engines implement a **fallback chain**:
```python
per_problem_key = f"{problem.name}::{algo}"
if per_problem_key in custom_params:
    params = custom_params[per_problem_key]   # New format (preferred)
elif algo in custom_params:
    params = custom_params[algo]               # Legacy format (fallback)
else:
    params = defaults                           # Default params
```

This ensures old metadata files still work, but new runs use the correct per-problem format.
