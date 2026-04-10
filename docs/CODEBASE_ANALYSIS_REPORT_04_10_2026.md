# UniRide — Forensic Codebase Analysis & Review

**Date:** 10 April 2026  
**Auditor:** AI Code Review Agent  
**Scope:** Full `optimizer_api/`, `academic_benchmark/`, and `docs/` against live codebase  
**Severity Scale:** 🔴 Critical · 🟡 Medium · 🟢 Low · ℹ️ Info

---

## Executive Summary

The UniRide CVRPTW optimizer is a substantial system (29 registered strategies, dual-pipeline architecture, 6+ local search operators). Documentation broadly reflects reality, but the audit found **5 logic errors**, **3 systemic code smells**, **7 bare `except:` clauses**, and **2 cross-file DRY violations** that undermine constraint-handling correctness and observability.

| Category              | Critical | Medium | Low | Info |
| --------------------- | -------- | ------ | --- | ---- |
| Logic Errors          | 2        | 2      | 1   | —    |
| Code Smells           | —        | 2      | 1   | —    |
| Documentation Gaps    | —        | 1      | 2   | 2    |
| Security / Robustness | —        | 1      | —   | 1    |

---

## 1. Documentation vs. Codebase Sync

### ✅ Aligned Areas

| Claim (docs)                                          | Evidence (code)                                       | Verdict |
| ----------------------------------------------------- | ----------------------------------------------------- | ------- |
| 29 strategies in registry                             | `strategies/__init__.py` — 29 keys confirmed          | ✅ Match |
| Pipeline A (Cluster-First) + Pipeline B (Route-First) | GA/PSO/GWO/HHO + `*_split` variants all present       | ✅ Match |
| PyVRP / VROOM graceful fallback                       | `try/except ImportError` with `_PYVRP_AVAILABLE` flag | ✅ Match |
| ResourceProfiler IE engine                            | `resource_profiler.py` 659 lines, 20 tests passing    | ✅ Match |
| Supabase time_matrix (812 rows, 29 nodes)             | `DataLoader._load_from_supabase()` confirmed          | ✅ Match |
| CORS env-based config (A-2 fix)                       | `ALLOWED_ORIGINS` in `main.py`                        | ✅ Match |
| Auth guard on `/api/calculate-vehicles` (A-1 fix)     | `requireAdmin` middleware in route handler            | ✅ Match |

### ⚠️ Sync Gaps

| Gap                                        | Severity | Details                                                                                                                                                                                  |
| ------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Caveman Heuristic missing**              | 🟡       | Conv. `95989c49` shows intent to implement. Neither `strategies/` nor `clustering_strategies/` contain it. Docs silent → dropped context or unmerged branch. |
| **`ALGORITHM_COMPARISON.md` stale status** | 🟡       | Table in §2 lists GA-Split, PSO-Split, etc. as `🔵 Planlanıyor` — they are **fully implemented and registered**. Status should be `✅`.                                                   |
| **Time Matrix caching undone**             | 🟢       | `01_Implementation_Status.md` P7 correctly marks it as pending. `DataLoader` is a singleton but does **no TTL or invalidation** — acceptable for now, but worth noting.                  |
| **Test coverage claim at 40%**             | ℹ️       | `03_Roadmap.md` shows `~40%`. Only `test_resource_profiler.py` + 3 CVRPTW phase tests exist. Actual coverage is likely **< 25%** for `optimizer_api/`.                                   |
| **Driver Assignments**                     | ℹ️       | Accurately documented as awaiting UI. No discrepancy.                                                                                                                                    |

---

## 2. Logic Errors

### F-01 · 🔴 SplitDecoder: Negative departure masked to zero (PICKUP)

**File:** [split_decoder.py](file:///c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/optimizer_api/utils/split_decoder.py#L321-L355)

```python
# Line 321 — backward scheduling
departure_time = target_arrival - int(total_trip_cost) - self.offset_minutes

# Line 355
departure_time=max(0, departure_time)  # ← masks infeasibility
```

**Problem:** If `target_arrival - total_trip_cost - offset < 0`, the trip is physically impossible (the driver would need to depart before midnight). Clamping to `0` silently produces an **infeasible route** that the DP solver treats as valid.

**Fix:** Set `is_feasible=False` and skip the trip instead of clamping:

```python
if departure_time < 0:
    continue  # infeasible — skip this trip
```

---

### F-02 · 🔴 SplitDecoder: DROPOFF ignores `earliest` constraint

**File:** [split_decoder.py](file:///c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/optimizer_api/utils/split_decoder.py#L376-L382)

```python
# Lines 377-381 — DROPOFF time window check
tw_violations = 0  # ← RESET every iteration — overwrites accumulated count
if loc in self.time_windows:
    earliest, latest = self.time_windows[loc]
    if current_time > latest:
        tw_violations = 1
    # MISSING: elif current_time < earliest → wait
```

**Two bugs in one:**

1. `tw_violations = 0` is **inside the inner loop**, which resets the counter for every location — only the *last* location's violation is ever counted.
2. No `elif current_time < earliest` check — if the vehicle arrives early at a dropoff stop, it should wait until `earliest`, adding idle time. Currently the arrival is recorded raw, potentially violating constraints.

**Fix:**

```python
# Move reset before inner loop
tw_violations = 0

for j in range(i, n):
    loc = giant_tour[j]
    ...
    if loc in self.time_windows:
        earliest, latest = self.time_windows[loc]
        if current_time > latest:
            tw_violations += 1  # accumulate, don't reset
        elif current_time < earliest:
            current_time = earliest  # wait
    ...
```

---

### F-03 · 🟡 SplitDecoder: PICKUP inner loop reuses outer `j` variable

**File:** [split_decoder.py](file:///c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/optimizer_api/utils/split_decoder.py#L279-L356)

The PICKUP branch has **two `for j in range(i, n)` loops** (lines ~291 and ~329). The first loop computes loads, the second verifies time windows. But both use the same variable name `j`. When the first loop breaks early due to capacity overflow, the variable `j` retains the break-point value. The second loop then starts from `i` and runs up to `n`, potentially going **past** the actual trip boundary established by the first loop.

After the first loop, `j` may point to a node that exceeded capacity. Line 318 then uses `giant_tour[i:j+1]` which could include an infeasible node.

**Fix:** Rename the second loop variable or explicitly track `trip_end` from the first loop.

---

### F-04 · 🟡 15.0-minute silent fallback across entire codebase

**Files (15 occurrences):**

| Strategy File              | Line                         |
| -------------------------- | ---------------------------- |
| `ga_strategy.py`           | 86                           |
| `pso_strategy.py`          | 92                           |
| `gwo_strategy.py`          | 93                           |
| `hho_strategy.py`          | 98                           |
| `ga_split_strategy.py`     | 106                          |
| `pso_split_strategy.py`    | 127                          |
| `gwo_split_strategy.py`    | 127                          |
| `hho_split_strategy.py`    | 127                          |
| `ortools_cvrp.py`          | 47                           |
| `pyvrp_strategy.py`        | 63                           |
| `vroom_strategy.py`        | 62, 313                      |
| `two_opt_strategy.py`      | 82                           |
| `greedy_heuristic.py`      | 46                           |
| `permutation_tsp.py`       | 51                           |
| `split_decoder.py`         | 236, 241, 301, 310, 371, 386 |
| `time_window_extractor.py` | 250                          |

Every strategy independently returns a magic `15.0` when a distance-matrix key is missing, with **zero logging or telemetry**. This masks broken data silently.

**Fix:** Extract to a shared constant with a `logger.warning`:

```python
# In a shared module (e.g., utils/constants.py)
DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0

# At each call site:
logger.warning("Distance matrix miss: %s → %s, using fallback %.1f", from_loc, to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
return DEFAULT_TRAVEL_FALLBACK_MINUTES
```

---

### F-05 · 🟢 Duplicate `_minutes_to_time` method

**File:** [split_decoder.py](file:///c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/optimizer_api/utils/split_decoder.py#L439-L504)

The method `_minutes_to_time` appears on lines 439 and 500. Both are identical. The second silently shadows the first. No runtime error, but a clear DRY violation.

---

## 3. Code Smells & Systemic Issues

### S-01 · 🟡 Seven bare `except:` clauses

| File                    | Line     |
| ----------------------- | -------- |
| `local_search_numba.py` | 36       |
| `ga_split_strategy.py`  | 348      |
| `pso_split_strategy.py` | 319      |
| `gwo_split_strategy.py` | 321      |
| `hho_split_strategy.py` | 369      |
| `cvrptw_wrapper.py`     | 181, 223 |

Bare `except:` catches `SystemExit`, `KeyboardInterrupt`, and memory errors. All should be `except Exception:` at minimum, or typed to the expected failure mode.

---

### S-02 · 🟡 `haversine_distance` defined in 2 separate modules

| Module                 | Line | Param names              |
| ---------------------- | ---- | ------------------------ |
| `utils/data_loader.py` | 145  | `lat1, lon1, lat2, lon2` |
| `utils/clustering.py`  | 31   | `lat1, lng1, lat2, lng2` |

Both are functionally identical but use **different parameter names** (`lon` vs `lng`). Clustering sub-strategies import from one or the other inconsistently:

- `k_medoids.py`, `clarke_wright.py` → import from `data_loader`
- `kmeans.py`, `fuzzy_cmeans.py`, `fuzzy_cmeans_enhanced.py` → import from `clustering`

**Fix:** Keep one canonical copy in `data_loader.py`, alias in `clustering.py`.

---

### S-03 · 🟢 `_nearest_neighbor_tour` duplicated across 4 Split strategies

Each of `ga_split_strategy.py`, `pso_split_strategy.py`, `gwo_split_strategy.py`, `hho_split_strategy.py` contains an identical `_nearest_neighbor_tour` method (~20 lines each). This is prime refactoring material into a shared `HybridSplitBaseStrategy` — which is already flagged in `01_Implementation_Status.md` as P9 technical debt.

---

## 4. Architecture & Design Observations

### 4.1 Singleton DataLoader — No Invalidation

`DataLoader` uses a class-level `_instance` singleton pattern. The matrix is loaded once from Supabase on first access and never refreshed. If the `time_matrix` table is updated during server runtime, stale data is served until restart.

**Impact:** Low for current deployment (single-campus, infrequent updates). Medium if multi-campus or real-time schedule changes are added.

---

### 4.2 Unused `depot` Parameters

Both `_get_target_arrival_time(locations, depot)` and `_get_target_departure_time(locations, depot)` accept a `depot` arg that is never used. They default to `09:00` or `14:00` via `self.target_time`. This is misleading — callers may believe depot routing is factored in.

---

### 4.3 ResourceProfiler Magic Numbers

`resource_profiler.py` uses hardcoded scheduling constants:

- `14 * 60` (14:00) for dropoff start
- `17 * 60` (17:00) for dropoff end
- Standard capacity `{sw: 4, so: 5}`

These are correct for the current Doğuş University deployment but would break for multi-campus or varying fleet configurations.

---

### 4.4 Benchmark Exception Suppression

**File:** [utils_benchmark.py](file:///c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/academic_benchmark/utils_benchmark.py)

The benchmark cache loader uses a broad `except Exception` that silently returns `None` on any I/O or JSON parsing failure. This hides critical data formatting issues during academic validation.

---

## 5. Cross-File DRY Violations Summary

| Duplicated Code                  | Files                             | LOC  |
| -------------------------------- | --------------------------------- | ---- |
| `_minutes_to_time`               | `split_decoder.py` (×2)           | 6    |
| `haversine_distance`             | `data_loader.py`, `clustering.py` | 26   |
| `_nearest_neighbor_tour`         | 4× `*_split_strategy.py`          | ~80  |
| `_build_distance_matrix` pattern | 13× strategy files                | ~130 |
| `return 15.0` fallback           | 15 files, 17 sites                | 17   |

**Total duplicated LOC: ~260 lines** — consolidation would improve maintainability significantly.

---

## 6. Prioritized Remediation Plan

| Priority | ID   | Action                                                                     | Impact             | Effort |
| -------- | ---- | -------------------------------------------------------------------------- | ------------------ | ------ |
| 🔴 P0    | F-01 | SplitDecoder: fail infeasible trips instead of clamping departure to 0     | Correctness        | 15 min |
| 🔴 P0    | F-02 | SplitDecoder DROPOFF: fix `tw_violations` reset + add `earliest` wait      | Correctness        | 30 min |
| 🟡 P1    | F-03 | SplitDecoder PICKUP: rename inner loop variable to avoid `j` collision     | Correctness        | 10 min |
| 🟡 P1    | F-04 | Extract `15.0` fallback to constant + add `logger.warning` at all 17 sites | Observability      | 1 hr   |
| 🟡 P1    | S-01 | Replace 7 bare `except:` with typed exceptions                             | Robustness         | 30 min |
| 🟢 P2    | F-05 | Remove duplicate `_minutes_to_time`                                        | Cleanliness        | 5 min  |
| 🟢 P2    | S-02 | Unify `haversine_distance` to single canonical module                      | DRY                | 20 min |
| 🟢 P2    | S-03 | Extract `_nearest_neighbor_tour` to `HybridSplitBaseStrategy`              | DRY / P9 tech debt | 1.5 hr |
| 🟢 P3    | §4.2 | Remove unused `depot` params from time helper methods                      | API clarity        | 10 min |
| 🟢 P3    | §4.3 | Extract ResourceProfiler magic numbers to config                           | Flexibility        | 30 min |
| ℹ️ P4    | §4.1 | Add TTL/invalidation to `DataLoader` singleton                             | Freshness          | 2 hr   |
| ℹ️ P4    | §1   | Update `ALGORITHM_COMPARISON.md` status for Split strategies               | Accuracy           | 10 min |

---

## 7. Positive Observations

- **Strategy registry pattern** is clean and extensible — adding new algorithms is trivial.
- **Local search module** (`local_search.py` + `local_search_numba.py`) is well-designed with consistent API, factory pattern, and Numba acceleration.
- **2-OPT periodic recalculation fix** (line 181 of numba module) correctly addresses floating-point drift.
- **SWAP adjacent-pair fix** properly removes the old skip condition that discarded 50% of moves.
- **TimeWindowExtractor** is correctly designed with clean separation of concerns for pickup vs. dropoff scheduling.
- **K-Means++** initialization in `clustering.py` is correctly implemented.
- **Pydantic schemas** provide strong runtime validation for API contracts.

---

*End of report.*
