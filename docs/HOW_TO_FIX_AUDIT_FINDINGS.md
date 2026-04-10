# 🔧 How-To: Fixing Audit Findings — Developer Guide

**Companion to:** `CODEBASE_ANALYSIS_REPORT_04_10_2026.md`  
**Date:** 10 April 2026  
**Audience:** Developers working on `optimizer_api/`  
**Reading time:** ~25 minutes  

---

## Table of Contents

1. [Before You Start](#1-before-you-start)
2. [FIX-01 · Split Decoder: Negative departure masked to zero (PICKUP)](#2-fix-01--split-decoder-negative-departure-masked-to-zero-pickup)
3. [FIX-02 · Split Decoder: DROPOFF tw_violations reset bug + missing earliest wait](#3-fix-02--split-decoder-dropoff-tw_violations-reset-bug--missing-earliest-wait)
4. [FIX-03 · Split Decoder: PICKUP inner loop variable `j` collision](#4-fix-03--split-decoder-pickup-inner-loop-variable-j-collision)
5. [FIX-04 · Extract 15.0 fallback to constant + add logging](#5-fix-04--extract-150-fallback-to-constant--add-logging)
6. [FIX-05 · Remove duplicate `_minutes_to_time` method](#6-fix-05--remove-duplicate-_minutes_to_time-method)
7. [FIX-06 · Replace bare `except:` with typed exceptions](#7-fix-06--replace-bare-except-with-typed-exceptions)
8. [FIX-07 · Unify `haversine_distance` to a single canonical module](#8-fix-07--unify-haversine_distance-to-a-single-canonical-module)
9. [FIX-08 · Extract `_nearest_neighbor_tour` to shared base class](#9-fix-08--extract-_nearest_neighbor_tour-to-shared-base-class)
10. [FIX-09 · Remove unused `depot` parameter from time helpers](#10-fix-09--remove-unused-depot-parameter-from-time-helpers)
11. [FIX-10 · Update stale doc status in ALGORITHM_COMPARISON.md](#11-fix-10--update-stale-doc-status-in-algorithm_comparisonmd)
12. [Testing & Verification Checklist](#12-testing--verification-checklist)

---

## 1. Before You Start

### Dependency Map

Most fixes target `optimizer_api/utils/split_decoder.py`. Here is the call chain so you understand what depends on it:

```
main.py  ─→  ga_split_strategy.py  ─→  split_decoder.decode()
             pso_split_strategy.py ─→  split_decoder.decode()
             gwo_split_strategy.py ─→  split_decoder.decode()
             hho_split_strategy.py ─→  split_decoder.decode()
             cvrptw_wrapper.py     ─→  split_decoder.decode()
```

Any change to `split_decoder.py`'s return shape or Trip structure **will affect all 5 consumers above**. Changes that only fix internal logic (fixing a loop, adding a `continue`) are safe.

### Setup

```bash
cd UniRide/optimizer_api
python -m pytest tests/ -v          # Run existing tests first
python -m pytest tests/test_cvrptw_phase1.py -v  # Specifically the CVRPTW tests
```

Make sure all existing tests pass **before** you start making changes.

### Git Branch

```bash
git checkout -b fix/audit-findings-apr-2026
```

---

## 2. FIX-01 · Split Decoder: Negative departure masked to zero (PICKUP)

> **Severity:** 🔴 Critical · **Effort:** ~15 min · **File:** `optimizer_api/utils/split_decoder.py`

### What Is the Problem?

In **PICKUP mode** (backward scheduling), the decoder calculates when a vehicle must depart the depot to pick up all students and arrive at school by their target time. The formula is:

```
departure_time = target_arrival - total_trip_cost - offset_minutes
```

If the total trip cost exceeds the time available (e.g., a 3-hour route but target is 09:00 with 10 min offset → departure at -1:10), the result is a **negative number**. 

The current code masks this to zero:

```python
# Line 355 — CURRENT (BROKEN)
departure_time=max(0, departure_time)
```

This creates a trip that the DP solver considers "feasible" (is_feasible=True) but is **physically impossible**. The vehicle would need to leave before midnight to make it on time. The route ends up in the final solution with a wrong departure time of `00:00`.

### Why This Matters

- Routes that are mathematically infeasible get included in the solution
- The DP solver picks these routes because they look like they have acceptable cost
- In production, a driver would get assigned a route they physically cannot complete

### How to Fix It

**Locate:** Lines 347–356 in `split_decoder.py`, inside the `_build_trips_with_tw` method, PICKUP branch.

**Before (current code):**

```python
                trips[j + 1].append(Trip(
                    start_idx=i,
                    end_idx=j,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True,
                    time_window_violations=tw_violations,
                    departure_time=max(0, departure_time)
                ))
```

**After (fixed code):**

```python
                # FIX-01: If departure_time is negative, the trip is physically
                # infeasible — the driver would need to depart before midnight.
                # Skip this trip entirely instead of masking to 00:00.
                if departure_time < 0:
                    continue

                trips[j + 1].append(Trip(
                    start_idx=i,
                    end_idx=j,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True,
                    time_window_violations=tw_violations,
                    departure_time=departure_time
                ))
```

### Logic Explanation

1. `continue` skips adding this trip to the candidate list entirely
2. The DP solver never sees it, so it cannot select an infeasible route
3. If **all** trips for a given split point are infeasible, the DP solver will find an alternative split, or return "No feasible splitting found" — which is the correct behavior
4. We remove `max(0, ...)` because it's no longer needed — departure_time is guaranteed ≥ 0 if we reach the append

### How to Test

Write a test where `target_arrival` (say 540 = 09:00) minus `total_trip_cost` (say 600 = 10 hours) minus `offset_minutes` (10) equals -70. The decoder should **not** include this trip:

```python
def test_negative_departure_skipped():
    decoder = SplitDecoder(
        sw_capacity=4, so_capacity=5, max_tour_duration=700,  # high limit so duration doesn't block
        time_windows={"Sw1": (480, 540)},
        use_time_windows=True,
        direction=Direction.PICKUP,
        target_time=540,       # 09:00
        offset_minutes=10
    )
    # Build a distance matrix with very long travel times
    dm = {
        "D.Kampus": {"Sw1": 600},  # 10 hours — impossible for 09:00 target
        "Sw1": {"D.Kampus": 600}
    }
    demands = {"Sw1": (1, 0)}
    result = decoder.decode(["Sw1"], "D.Kampus", dm, demands)
    
    # The decoder must NOT produce a route
    assert result["num_vehicles"] == 0 or "error" in result
```

---

## 3. FIX-02 · Split Decoder: DROPOFF tw_violations reset bug + missing earliest wait

> **Severity:** 🔴 Critical · **Effort:** ~30 min · **File:** `optimizer_api/utils/split_decoder.py`

### What Is the Problem?

There are **two bugs** in the DROPOFF (forward scheduling) branch of `_build_trips_with_tw`.

#### Bug A: tw_violations resets every iteration

Look at lines 377:

```python
                    # Check time window
                    tw_violations = 0          # ← THIS IS INSIDE THE INNER LOOP
                    if loc in self.time_windows:
                        earliest, latest = self.time_windows[loc]
                        if current_time > latest:
                            tw_violations = 1  # ← Only ever counts last stop
```

The variable `tw_violations` is set to `0` at the **start of every iteration** of the inner loop (for every location `j`). This means:
- Stop 1 violates → tw_violations = 1
- Stop 2 is fine → tw_violations = 0 (reset!)
- Stop 3 violates → tw_violations = 1

The Trip is created with `tw_violations = 1`, but the actual count is **2**. The DP solver undercounts violations, which leads to selecting routes that are worse than they appear.

#### Bug B: Missing earliest-time wait

Compare the PICKUP branch (line 341–343) vs DROPOFF branch:

```python
# PICKUP (line 341-343) — CORRECT
elif current_time < earliest:
    current_time = earliest  # Wait until earliest

# DROPOFF (lines 378-381) — MISSING
if current_time > latest:
    tw_violations = 1
# No check for current_time < earliest!
```

In DROPOFF mode, if the vehicle arrives at a stop **before** the student's earliest drop-off time, it should wait. Currently, the early arrival is recorded as-is, which means the student would be dropped off before their time window starts (e.g., dropped at home at 12:30 when the window starts at 14:00).

### How to Fix It

**Locate:** Lines 358–401 in `split_decoder.py`, DROPOFF branch.

**Before (current code):**

```python
            else:  # DROPOFF - FORWARD SCHEDULING
                current_time = self._get_target_departure_time(giant_tour[i:min(i+1, n)], depot)
                
                for j in range(i, n):
                    loc = giant_tour[j]
                    sw_d, so_d = demands.get(loc, (0, 0))
                    sw_load += sw_d
                    so_load += so_d
                    
                    if sw_load > self.sw_capacity or so_load > self.so_capacity:
                        break
                    
                    # Add travel cost
                    travel_time = distance_matrix.get(prev, {}).get(loc, 15.0)
                    cost += travel_time
                    current_time += int(travel_time)
                    arrival_times[loc] = current_time
                    
                    # Check time window
                    tw_violations = 0
                    if loc in self.time_windows:
                        earliest, latest = self.time_windows[loc]
                        if current_time > latest:
                            tw_violations = 1
                    
                    prev = loc
                    
                    # Return to depot
                    return_cost = distance_matrix.get(loc, {}).get(depot, 15.0)
                    total_trip_cost = cost + return_cost
                    
                    if total_trip_cost > self.max_tour_duration:
                        continue
                    
                    trips[j + 1].append(Trip(
                        start_idx=i,
                        end_idx=j,
                        cost=total_trip_cost,
                        sw_count=sw_load,
                        so_count=so_load,
                        is_feasible=True,
                        time_window_violations=tw_violations,
                        departure_time=current_time - int(cost)
                    ))
```

**After (fixed code):**

```python
            else:  # DROPOFF - FORWARD SCHEDULING
                current_time = self._get_target_departure_time(giant_tour[i:min(i+1, n)], depot)
                
                # FIX-02A: Initialize violation counter BEFORE the loop, not inside it
                tw_violations = 0
                
                for j in range(i, n):
                    loc = giant_tour[j]
                    sw_d, so_d = demands.get(loc, (0, 0))
                    sw_load += sw_d
                    so_load += so_d
                    
                    if sw_load > self.sw_capacity or so_load > self.so_capacity:
                        break
                    
                    # Add travel cost
                    travel_time = distance_matrix.get(prev, {}).get(loc, 15.0)
                    cost += travel_time
                    current_time += int(travel_time)
                    
                    # FIX-02B: Check both bounds of the time window
                    if loc in self.time_windows:
                        earliest, latest = self.time_windows[loc]
                        if current_time > latest:
                            tw_violations += 1   # ACCUMULATE, don't reset
                        elif current_time < earliest:
                            current_time = earliest  # Wait until window opens
                    
                    arrival_times[loc] = current_time  # Record AFTER possible wait
                    
                    prev = loc
                    
                    # Return to depot
                    return_cost = distance_matrix.get(loc, {}).get(depot, 15.0)
                    total_trip_cost = cost + return_cost
                    
                    if total_trip_cost > self.max_tour_duration:
                        continue
                    
                    trips[j + 1].append(Trip(
                        start_idx=i,
                        end_idx=j,
                        cost=total_trip_cost,
                        sw_count=sw_load,
                        so_count=so_count,
                        is_feasible=True,
                        time_window_violations=tw_violations,
                        departure_time=current_time - int(cost)
                    ))
```

### Key Changes Explained

| Change | What | Why |
|---|---|---|
| Move `tw_violations = 0` before loop | Initialize once, not per-iteration | Allows violations to accumulate across all stops |
| `tw_violations = 1` → `tw_violations += 1` | Use `+=` instead of `=` | Multiple stops can violate, count them all |
| Add `elif current_time < earliest` | Wait until time window opens | Prevents dropping off students before their window |
| Move `arrival_times[loc]` after wait check | Record the actual arrival (including wait) | Ensures accurate ETA reporting |

### How to Test

```python
def test_dropoff_violations_accumulate():
    """2 stops, both late → tw_violations = 2, not 1"""
    decoder = SplitDecoder(
        sw_capacity=4, so_capacity=5, max_tour_duration=120,
        time_windows={
            "So1": (840, 870),  # 14:00-14:30
            "So2": (840, 870),  # 14:00-14:30
        },
        use_time_windows=True,
        direction=Direction.DROPOFF,
        target_time=840
    )
    dm = {
        "D.Kampus": {"So1": 40, "So2": 50},
        "So1": {"D.Kampus": 40, "So2": 15},
        "So2": {"D.Kampus": 50, "So1": 15}
    }
    demands = {"So1": (0, 1), "So2": (0, 1)}
    result = decoder.decode(["So1", "So2"], "D.Kampus", dm, demands)
    
    # Both stops are visited well after 14:30, so violations should be ≥ 2
    assert result["time_window_violations"] >= 2


def test_dropoff_early_arrival_waits():
    """If vehicle arrives before earliest, it should wait"""
    decoder = SplitDecoder(
        sw_capacity=4, so_capacity=5, max_tour_duration=120,
        time_windows={
            "So1": (900, 960),  # 15:00-16:00 (very late window)
        },
        use_time_windows=True,
        direction=Direction.DROPOFF,
        target_time=840  # Depart at 14:00
    )
    dm = {
        "D.Kampus": {"So1": 10},   # Arrives at 14:10
        "So1": {"D.Kampus": 10}
    }
    demands = {"So1": (0, 1)}
    result = decoder.decode(["So1"], "D.Kampus", dm, demands)
    
    # Vehicle arrives at 14:10 but window starts at 15:00
    # It should wait → no violation
    assert result["time_window_violations"] == 0
```

---

## 4. FIX-03 · Split Decoder: PICKUP inner loop variable `j` collision

> **Severity:** 🟡 Medium · **Effort:** ~10 min · **File:** `optimizer_api/utils/split_decoder.py`

### What Is the Problem?

In the PICKUP branch of `_build_trips_with_tw`, there are two sequential `for j in range(i, n)` loops:

```python
# LOOP 1 — Lines 291-303: Builds loads and costs
for j in range(i, n):          # ← variable 'j' defined here
    loc = giant_tour[j]
    sw_load += sw_d
    ...
    if sw_load > self.sw_capacity:
        break                  # ← 'j' freezes at the overflow point

# ... lines 304-328 ...

# LOOP 2 — Lines 329-345: Verifies time windows
for j in range(i, n):          # ← same 'j' reused, runs from i to n
    loc = giant_tour[j]
    ...
```

**Problem scenario:**
1. Loop 1 processes stops i, i+1, i+2 and breaks at i+3 (capacity overflow). `j` is now `i+3`.
2. Line 318 uses `giant_tour[i:j+1]` — this includes the overflowing node `i+3`.
3. Loop 2 iterates over `i` to `n-1`, going **past** the trip boundary that Loop 1 established.
4. The Trip is appended at `trips[j+1]` where `j` is now whatever Loop 2's last iteration was, not where Loop 1 stopped.

### How to Fix It

Track the actual end of the trip from Loop 1, and use that as the boundary for Loop 2.

**Before (lines 291–356):**

```python
                for j in range(i, n):
                    loc = giant_tour[j]
                    # ... capacity logic ...
                    if sw_load > self.sw_capacity or so_load > self.so_capacity:
                        break
                    # ... cost logic ...
                
                # ... total_trip_cost, target_arrival ...
                
                for j in range(i, n):
                    # ... time window verification ...
                
                trips[j + 1].append(Trip(...))
```

**After (fixed):**

```python
                # LOOP 1: Build loads and cost — track the actual trip end
                trip_end = i  # Will be updated as we successfully add stops
                for k in range(i, n):
                    loc = giant_tour[k]
                    sw_d, so_d = demands.get(loc, (0, 0))
                    sw_load += sw_d
                    so_load += so_d
                    
                    if sw_load > self.sw_capacity or so_load > self.so_capacity:
                        break
                    
                    travel_time = distance_matrix.get(prev, {}).get(loc, 15.0)
                    cost += travel_time
                    prev = loc
                    trip_end = k  # Update — this stop is feasible
                
                # Calculate return to depot
                if prev in distance_matrix and depot in distance_matrix[prev]:
                    return_cost = distance_matrix[prev][depot]
                else:
                    return_cost = 15.0
                
                total_trip_cost = cost + return_cost
                
                if total_trip_cost > self.max_tour_duration:
                    continue
                
                # Use trip_end (not j) for slicing
                target_arrival = self._get_target_arrival_time(
                    giant_tour[i:trip_end + 1], depot
                )
                
                departure_time = target_arrival - int(total_trip_cost) - self.offset_minutes
                
                # FIX-01: Skip trips with negative departure
                if departure_time < 0:
                    continue
                
                # LOOP 2: Verify TW — iterate only over the trip's stops
                tw_violations = 0
                current_time = departure_time
                prev = depot
                
                for k in range(i, trip_end + 1):  # Use trip_end as boundary
                    loc = giant_tour[k]
                    travel_time = distance_matrix.get(prev, {}).get(loc, 15.0)
                    current_time += int(travel_time)
                    arrival_times[loc] = current_time
                    
                    if loc in self.time_windows:
                        earliest, latest = self.time_windows[loc]
                        if current_time > latest:
                            tw_violations += 1
                        elif current_time < earliest:
                            current_time = earliest
                    
                    prev = loc
                
                trips[trip_end + 1].append(Trip(
                    start_idx=i,
                    end_idx=trip_end,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True,
                    time_window_violations=tw_violations,
                    departure_time=departure_time
                ))
```

### Key Changes Explained

| Change | Why |
|---|---|
| Rename loop variable to `k` | Avoids collision between loops — `j` was being reused |
| Introduce `trip_end` variable | Explicitly tracks the last feasible stop index |
| Use `trip_end + 1` in second loop's range | Second loop processes **only** the stops that passed Loop 1 |
| Use `trip_end + 1` as the Trip key | Trip is indexed by the correct position in the giant tour |

---

## 5. FIX-04 · Extract 15.0 fallback to constant + add logging

> **Severity:** 🟡 Medium · **Effort:** ~1 hour · **File:** Multiple (17 call sites)

### What Is the Problem?

When the distance matrix doesn't contain a pair of locations, every strategy independently returns a hardcoded `15.0` minutes with no warning log. This makes it **invisible** when the time_matrix is incomplete or when location codes are misspelled.

### How to Fix It

#### Step 1: Create a shared constant

Create a new file `optimizer_api/utils/constants.py`:

```python
"""
Shared constants for the optimizer API.
Centralizes magic numbers to improve traceability and debugging.
"""

# Default travel time (in minutes) used when the distance matrix
# does not contain an entry for a given origin-destination pair.
# WARNING: If you see this value appearing in route solutions,
# investigate the time_matrix completeness.
DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0
```

#### Step 2: Update each strategy file

For each of the 13 strategy files, replace the hardcoded `return 15.0` in `_get_duration` with:

**Before:**

```python
# Example from ga_split_strategy.py, line 106
    def _get_duration(self, from_loc, to_loc, time_matrix, coordinates):
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]
        
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)
        
        return 15.0
```

**After:**

```python
import logging
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)

    def _get_duration(self, from_loc, to_loc, time_matrix, coordinates):
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]
        
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)
        
        logger.warning(
            "Distance matrix miss: %s → %s, using fallback %.1f min",
            from_loc, to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES
        )
        return DEFAULT_TRAVEL_FALLBACK_MINUTES
```

#### Step 3: Update split_decoder.py

The split decoder uses `15.0` inline (not via `_get_duration`). Replace all 6 occurrences with the constant.

**Lines to change:** 236, 241, 301, 310, 371, 386

Example at line 301:

```python
# Before
travel_time = distance_matrix.get(prev, {}).get(loc, 15.0)

# After
travel_time = distance_matrix.get(prev, {}).get(loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
```

> **Note:** Adding `logger.warning` inside `split_decoder.py`'s inner loops could be very noisy (called thousands of times). Use it only at the strategy level's `_get_duration`. Inside `split_decoder.py`, just use the constant.

#### Full file list for this fix

| File | Lines to change |
|---|---|
| `utils/constants.py` | **NEW FILE** |
| `strategies/ga_strategy.py` | 86 |
| `strategies/pso_strategy.py` | 92 |
| `strategies/gwo_strategy.py` | 93 |
| `strategies/hho_strategy.py` | 98 |
| `strategies/ga_split_strategy.py` | 106 |
| `strategies/pso_split_strategy.py` | 127 |
| `strategies/gwo_split_strategy.py` | 127 |
| `strategies/hho_split_strategy.py` | 127 |
| `strategies/ortools_cvrp.py` | 47 |
| `strategies/pyvrp_strategy.py` | 63 |
| `strategies/vroom_strategy.py` | 62, 313 |
| `strategies/two_opt_strategy.py` | 82 |
| `strategies/greedy_heuristic.py` | 46 |
| `strategies/permutation_tsp.py` | 51 |
| `utils/split_decoder.py` | 236, 241, 301, 310, 371, 386 |
| `utils/time_window_extractor.py` | 250 |

---

## 6. FIX-05 · Remove duplicate `_minutes_to_time` method

> **Severity:** 🟢 Low · **Effort:** ~5 min · **File:** `optimizer_api/utils/split_decoder.py`

### What Is the Problem?

The method `_minutes_to_time` is defined twice in `SplitDecoder`:

- **First definition:** Line 439–443
- **Second definition:** Line 500–504 (shadows the first)

Both are byte-for-byte identical. In Python, the second definition silently replaces the first — no error, but confusing for readers.

### How to Fix It

**Delete lines 500–504** (the second copy). Keep only the first definition at line 439.

```python
# DELETE these lines (500-504):
    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes from midnight to HH:MM format"""
        hours = (minutes // 60) % 24
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
```

The `decode_with_details` method at line 483 calls `self._minutes_to_time(...)` — it will now resolve to the single remaining definition at line 439. No behavioral change.

### How to Verify

```bash
# Search for duplicates — should return exactly 1 hit after fix
grep -n "_minutes_to_time" optimizer_api/utils/split_decoder.py
```

---

## 7. FIX-06 · Replace bare `except:` with typed exceptions

> **Severity:** 🟡 Medium · **Effort:** ~30 min · **Files:** 6 files, 7 sites

### What Is the Problem?

Bare `except:` catches **everything**, including:
- `SystemExit` (prevents clean shutdown)
- `KeyboardInterrupt` (prevents Ctrl+C)
- `MemoryError` (masks critical OOM issues)

### File-by-File Fix Guide

#### 1. `local_search_numba.py` — Line 36

```python
# Before
    try:
        set_num_threads(min(4, numba.config.NUMBA_NUM_THREADS))
    except:
        pass

# After
    try:
        set_num_threads(min(4, numba.config.NUMBA_NUM_THREADS))
    except (AttributeError, RuntimeError):
        pass  # Numba config may not expose NUMBA_NUM_THREADS in all versions
```

**Why `AttributeError, RuntimeError`:** The only realistic failures here are (a) the config attribute doesn't exist, or (b) the runtime doesn't support thread-setting.

#### 2. `ga_split_strategy.py` — Line 348

```python
# Before
        except:
            return individual

# After
        except Exception as e:
            logger.debug("Local search failed for individual: %s", e)
            return individual
```

**Why `Exception`:** This wraps a local search call that could fail for many reasons (bad route, divide-by-zero, etc.). We want to catch all recoverable errors but not `SystemExit` / `KeyboardInterrupt`.

#### 3–5. Apply the same pattern to:

| File | Line | Same fix as #2 |
|---|---|---|
| `pso_split_strategy.py` | 319 | `except Exception as e:` |
| `gwo_split_strategy.py` | 321 | `except Exception as e:` |
| `hho_split_strategy.py` | 369 | `except Exception as e:` |

#### 6. `cvrptw_wrapper.py` — Lines 181, 223

```python
# Before (line 181)
        except:
            return 0

# After
        except (ValueError, IndexError):
            return 0

# Before (line 223)
        except:
            continue

# After
        except (ValueError, IndexError, KeyError):
            continue
```

**Why specific types:** These are time-parsing functions. The only realistic failures are bad string format (`ValueError`), missing split parts (`IndexError`), or missing dictionary keys (`KeyError`).

---

## 8. FIX-07 · Unify `haversine_distance` to a single canonical module

> **Severity:** 🟢 Low · **Effort:** ~20 min · **Files:** `data_loader.py`, `clustering.py`, clustering sub-strategies

### What Is the Problem?

`haversine_distance` is defined in two places with **different parameter names**:

```python
# data_loader.py line 145
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:

# clustering.py line 31
def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
```

This is confusing (`lon` vs `lng`) and violates DRY.

### How to Fix It

#### Step 1: Keep the canonical version in `data_loader.py`

Keep the `data_loader.py` version as-is.

#### Step 2: Replace `clustering.py`'s copy with a re-export

```python
# In clustering.py — REPLACE the function definition with an import
from utils.data_loader import haversine_distance  # Canonical source

# If callers use `lng` parameter name (keyword args), add a compat alias:
# Note: positional calls work fine since the parameters are in the same order.
```

#### Step 3: Verify callers

Callers already use **positional** arguments:
```python
haversine_distance(point.lat, point.lng, c[0], c[1])
```

Since positional args don't depend on parameter names, this change is safe. But search for any **keyword** calls:

```bash
grep -rn "lng1=" optimizer_api/
grep -rn "lon1=" optimizer_api/
```

If no keyword calls exist (likely), you're done. If they do, add a compatibility wrapper.

---

## 9. FIX-08 · Extract `_nearest_neighbor_tour` to shared base class

> **Severity:** 🟢 Low · **Effort:** ~1.5 hours · **Files:** 4 split strategy files + new base class

### What Is the Problem?

The method `_nearest_neighbor_tour` is copy-pasted identically across all 4 split strategies:
- `ga_split_strategy.py` (line 158–188)
- `pso_split_strategy.py` (line 178–208)
- `gwo_split_strategy.py` (line 174–204)
- `hho_split_strategy.py` (line 174–204)

This was flagged in `01_Implementation_Status.md` as **P9 technical debt** — "Hybrid Base Strategy Yok".

### How to Fix It

#### Step 1: Create `optimizer_api/strategies/hybrid_base_strategy.py`

```python
"""
Base class for split-based (Route-First, Cluster-Second) strategies.
Extracts shared logic to reduce duplication across GA/PSO/GWO/HHO split variants.
"""

from typing import List, Dict, Optional, cast
import random

from strategies.base_strategy import BaseRoutingStrategy
from utils.split_decoder import decode_giant_tour
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES


class HybridSplitBaseStrategy(BaseRoutingStrategy):
    """
    Abstract base for strategies that use:
      Giant Tour (meta-heuristic) → Optimal Split Decoder → Vehicle Routes
    """
    
    def _get_duration(self, from_loc: str, to_loc: str,
                      time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between two locations — shared implementation"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]
        
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)
        
        return DEFAULT_TRAVEL_FALLBACK_MINUTES

    def _build_distance_matrix(self, location_ids: List[str],
                                time_matrix: Dict, coordinates: Dict) -> Dict[str, Dict[str, float]]:
        """Build complete distance matrix for all locations"""
        matrix = {}
        for loc1 in location_ids:
            matrix[loc1] = {}
            for loc2 in location_ids:
                if loc1 == loc2:
                    matrix[loc1][loc2] = 0.0
                else:
                    matrix[loc1][loc2] = self._get_duration(
                        loc1, loc2, time_matrix, coordinates
                    )
        return matrix

    def _nearest_neighbor_tour(self, waypoints: List[str],
                                distance_matrix: Optional[Dict] = None,
                                depot: Optional[str] = None) -> List[str]:
        """Create a tour using nearest neighbor heuristic"""
        if not waypoints:
            return []
        
        tour = []
        remaining = waypoints.copy()
        current = remaining.pop(0)
        tour.append(current)
        
        while remaining:
            best_next = None
            best_dist = float('inf')
            
            for candidate in remaining:
                if distance_matrix and current in distance_matrix:
                    dist = distance_matrix[current].get(candidate, float('inf'))
                else:
                    dist = random.random() * 100
                if best_next is None or dist < best_dist:
                    best_dist = dist
                    best_next = candidate
            
            best_next = cast(str, best_next)
            tour.append(best_next)
            remaining.remove(best_next)
            current = best_next
        
        return tour
```

#### Step 2: Update each split strategy to inherit from the new base

In each file (`ga_split_strategy.py`, `pso_split_strategy.py`, etc.):

1. Change the import:
   ```python
   from strategies.hybrid_base_strategy import HybridSplitBaseStrategy
   ```

2. Change the class declaration:
   ```python
   class GASplitStrategy(HybridSplitBaseStrategy):
   ```

3. **Delete** the local `_get_duration`, `_build_distance_matrix`, and `_nearest_neighbor_tour` methods.

4. Test that all 4 strategies still work.

---

## 10. FIX-09 · Remove unused `depot` parameter from time helpers

> **Severity:** 🟢 Low · **Effort:** ~10 min · **File:** `optimizer_api/utils/split_decoder.py`

### What Is the Problem?

Both `_get_target_arrival_time(locations, depot)` and `_get_target_departure_time(locations, depot)` accept a `depot` parameter that is **never used** inside the method body. This misleads readers into thinking depot routing is being factored in.

### How to Fix It

#### Step 1: Remove the parameter from the method signatures

```python
# Before (line 405)
def _get_target_arrival_time(self, locations: List[str], depot: str) -> int:

# After
def _get_target_arrival_time(self, locations: List[str]) -> int:
```

```python
# Before (line 422)
def _get_target_departure_time(self, locations: List[str], depot: str) -> int:

# After
def _get_target_departure_time(self, locations: List[str]) -> int:
```

#### Step 2: Update the call sites

```python
# Line 318 — Before
target_arrival = self._get_target_arrival_time(giant_tour[i:j+1], depot)

# Line 318 — After
target_arrival = self._get_target_arrival_time(giant_tour[i:trip_end + 1])
```

```python
# Line 359 — Before
current_time = self._get_target_departure_time(giant_tour[i:min(i+1, n)], depot)

# Line 359 — After
current_time = self._get_target_departure_time(giant_tour[i:min(i+1, n)])
```

---

## 11. FIX-10 · Update stale doc status in ALGORITHM_COMPARISON.md

> **Severity:** ℹ️ Info · **Effort:** ~10 min · **File:** `docs/ALGORITHM_COMPARISON.md`

### What Is the Problem?

Table in §2 ("Yeni Algoritmalar") lists all four split strategies as `🔵 Planlanıyor` (Planning). They are **fully implemented and registered** in the strategy registry.

### How to Fix It

Update lines 48–53:

```markdown
<!-- Before -->
| GA-Split | `ga_split_strategy.py` | 🔵 Planlanıyor | ... |
| PSO-Split | `pso_split_strategy.py` | 🔵 Planlanıyor | ... |
| HHO-Split | `hho_split_strategy.py` | 🔵 Planlanıyor | ... |
| GWO-Split | `gwo_split_strategy.py` | 🔵 Planlanıyor | ... |

<!-- After -->
| GA-Split | `ga_split_strategy.py` | ✅ Tamamlandı | ... |
| PSO-Split | `pso_split_strategy.py` | ✅ Tamamlandı | ... |
| HHO-Split | `hho_split_strategy.py` | ✅ Tamamlandı | ... |
| GWO-Split | `gwo_split_strategy.py` | ✅ Tamamlandı | ... |
```

---

## 12. Testing & Verification Checklist

After applying all fixes, run this verification sequence:

### Unit Tests

```bash
cd optimizer_api
python -m pytest tests/test_cvrptw_phase1.py -v
python -m pytest tests/test_cvrptw_phase2.py -v
python -m pytest tests/test_cvrptw_phase3.py -v
python -m pytest tests/test_local_search.py -v
python -m pytest tests/test_resource_profiler.py -v
```

### Smoke Test — Full Pipeline

```bash
cd optimizer_api
python main.py &  # Start the server

# Test basic CVRP (no time windows)
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{"students": [...], "algorithm": "ga_split"}'

# Test CVRPTW (with time windows)
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{"students": [...], "algorithm": "ga_split", "direction": "pickup", "target_time": "09:00"}'
```

### Regression Checklist

| Test | Expected | Status |
|---|---|---|
| Existing tests pass | All green | ☐ |
| Negative departure → trip skipped (FIX-01) | No 00:00 departures in output | ☐ |
| DROPOFF violations accumulate (FIX-02A) | Count matches actual violations | ☐ |
| DROPOFF early arrival waits (FIX-02B) | No violations for early arrivals within window | ☐ |
| PICKUP loop uses separate variable (FIX-03) | `trip_end` tracks correct boundary | ☐ |
| `grep "return 15.0" optimizer_api/` returns 0 hits (FIX-04) | Constant used instead | ☐ |
| Single `_minutes_to_time` definition (FIX-05) | Only 1 definition in split_decoder.py | ☐ |
| No bare `except:` (FIX-06) | `grep "except:" optimizer_api/` returns 0 | ☐ |
| Single `haversine_distance` definition (FIX-07) | Only in data_loader.py | ☐ |
| Split strategies inherit from base (FIX-08) | No duplicate `_nearest_neighbor_tour` | ☐ |
| No unused `depot` param (FIX-09) | grep confirms removal | ☐ |

### Grep Validation Commands

```bash
# FIX-04: No more hardcoded 15.0 returns
grep -rn "return 15.0" optimizer_api/strategies/ optimizer_api/utils/split_decoder.py
# Expected: 0 results

# FIX-05: Single _minutes_to_time
grep -cn "_minutes_to_time" optimizer_api/utils/split_decoder.py
# Expected: 2 (1 definition + 1 call), NOT 4

# FIX-06: No bare excepts
grep -rn "except:" optimizer_api/ --include="*.py" | grep -v "except Exception" | grep -v "except ("
# Expected: 0 results

# FIX-07: Single haversine definition
grep -rn "def haversine_distance" optimizer_api/
# Expected: 1 result (data_loader.py only)
```

---

*End of developer guide.*
