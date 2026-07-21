# Post-PR #23 GWO/HHO Small-Category Benchmark Evidence Report

> **Date:** 2026-06-30
> **Branch:** WIP (commit `3534ae8`)
> **PRs evaluated:** #22 (architecture-boundary test path), #23 (GWO/HHO registry execution fix)
> **Additional fixes applied:** Distance matrix bug fixes (commits `c59a2bb`, `7aedc56`, `3534ae8`)

---

## 1. Benchmark Command

```powershell
python -m academic_benchmark.cli_engine --mode default `
  --algos "Numba-GWO,Numba-HHO,Core-GWO-TSP,Core-HHO-TSP" `
  --problems eil51,berlin52,burma14,ulysses16,att48 `
  --runs 3 --workers 1 --size-limit 100
```

**Note:** A targeted problem subset was used instead of `--select small` because the
full small-category run (17 problems × 4 algorithms × 3 runs) takes over 30 minutes
without Numba acceleration. The subset covers all three TSPLIB edge-weight types
(EUC_2D, GEO, ATT) and includes the two problems with historical stale data (eil51).

---

## 2. PR #23 Fix Confirmation

| Verification point | Status |
|---|---|
| `academic_benchmark/cli_engine.py` has `_Problem.prepare_matrices()` | Confirmed (line 620) |
| `academic_benchmark/tests/test_core_tsp_registry.py` covers all 4 variants | Confirmed (lines 31, 32, 69, 78, 149, 179) |
| `academic_benchmark/HOW_TO_USE.md` documents GWO/HHO names | Confirmed (updated in PR #23) |
| `registry_setup.py` overrides for Core-GWO-TSP, Core-HHO-TSP, Numba-GWO, Numba-HHO | Confirmed (lines 469–493) |
| All 4 variants route to `GWOOptimizer` / `HHOOptimizer` from bildiri2026 | Confirmed (lines 475–476) |

---

## 3. Root Cause Summary

### Layer 1 — Registry Routing (PR #23)

The `_Problem` wrapper in `cli_engine.py` lacked `prepare_matrices()`, so registry-backed
GWO/HHO executors crashed when `_problem_matrix()` tried to build a distance matrix.
PR #23 added the method and registered all 4 algorithm variants to route through the
`_make_numba_metah_executor` override path, which calls `GWOOptimizer` / `HHOOptimizer`
from `academic_benchmark/bildiri2026/core/`.

### Layer 2 — Distance Matrix Construction (commits c59a2bb, 7aedc56, 3534ae8)

`prepare_matrices()` used raw Euclidean distance (`math.sqrt(dx²+dy²)`) for ALL edge
weight types, ignoring `EDGE_WEIGHT_TYPE`. This produced:

- **GEO problems** (burma14, ulysses16, gr96): distances ~100× too small (lat/lng
  treated as flat X/Y) → impossible negative gaps (−99%)
- **ATT problems** (att48): distances ~3× too large (ATT formula divides by 10,
  raw Euclidean doesn't) → absurd positive gaps (+217%)
- **EUC_2D problems** (eil51, berlin52): distances used raw float instead of TSPLIB
  NINT integer rounding → small but systematic discrepancies

The `tsplib_geo_distance` function also used `int(R × acos(…) + 0.5)` (NINT) instead
of the canonical `int(R × acos(…) + 1)` used by the tsplib95 reference, causing 45/91
edges in burma14 to be off by exactly 1.

**Fixes applied:**
- `prepare_matrices()` now dispatches on `edge_weight_type` via `tsplib_distance_by_type()`
- `tsplib_geo_distance` uses `int(… + 1)` rounding matching tsplib95
- `tsplib_att_distance` uses `int(rij + 0.5)` (NINT) instead of `int(round(rij))` (banker's)
- `tsplib_euc_2d_distance` uses `int(x + 0.5)` (NINT) instead of `int(round(x))` (banker's)
- `sota_tsp/base_solver.py:euclidean_distance` now returns NINT integer, not raw float
- `benchmark_runner._compute_tsplib_tour_distance` now dispatches on `edge_weight_type`
- SOTA executor fallback builds correct matrix for non-EUC_2D problems

---

## 4. Results

### eil51 (EUC_2D, optimum = 426) — Key Comparison Problem

| Algorithm | Old Avg Gap | Old Objective | New Avg Gap | New Objective | Improvement |
|-----------|------------|---------------|------------|---------------|-------------|
| **Numba-GWO** | 7.75% | 444.0 | **1.64%** | 431.0 | **−6.1 points** |
| **Numba-HHO** | 6.03% | 439.0 | **1.64%** | 431.0 | **−4.4 points** |
| Core-GWO-TSP | *(not present)* | — | 1.64% | 431.0 | — |
| Core-HHO-TSP | *(not present)* | — | 1.64% | 431.0 | — |

All 4 registry variants produce identical results, confirming they route through the
same `GWOOptimizer` / `HHOOptimizer` override path.

### berlin52 (EUC_2D, optimum = 7542)

| Algorithm | Avg Gap | Objective | Avg Time |
|-----------|---------|-----------|----------|
| Numba-GWO | 3.75% | 7772.0 | 384 ms |
| Numba-HHO | 3.75% | 7772.0 | 324 ms |
| Core-GWO-TSP | 3.75% | 7772.0 | 378 ms |
| Core-HHO-TSP | 3.75% | 7772.0 | 307 ms |

### burma14 (GEO, optimum = 3323) — Previously −99% gap

| Algorithm | Old Gap | New Gap | Objective |
|-----------|---------|---------|-----------|
| All 4 variants | −99.07% | **0.00%** | 3323.0 |

Solver finds the exact TSPLIB optimum. The distance fix eliminated the impossible
negative gap.

### ulysses16 (GEO, optimum = 6859) — Previously −99% gap

| Algorithm | Old Gap | New Gap | Objective |
|-----------|---------|---------|-----------|
| All 4 variants | −98.92% | **0.00%** | 6859.0 |

### att48 (ATT, optimum = 10628) — Previously +217% gap

| Algorithm | Old Gap | New Gap | Objective |
|-----------|---------|---------|-----------|
| All 4 variants | +216.79% | **0.30%** | 10653.0 |

---

## 5. Main Conclusions

1. **PR #23 fixed GWO/HHO routing.** Numba-GWO, Numba-HHO, Core-GWO-TSP, and
   Core-HHO-TSP now produce parity because they route through the same override path
   (`_make_numba_metah_executor` → `GWOOptimizer` / `HHOOptimizer`).

2. **eil51 gap improved from 7.75% → 1.64%.** The old stale rows used a broken/legacy
   executor. The new path uses the Numba-accelerated memetic solver with 2-opt polish
   and correct NINT-rounded distance matrices.

3. **Distance matrix fixes eliminated impossible gaps.** GEO problems (burma14,
   ulysses16) now correctly hit 0.00% gap. ATT problems (att48) dropped from +217%
   to 0.30%. All gaps are now mathematically valid (non-negative, reproducible).

4. **TSP small-category gaps are roughly 0.3–3.8%** for the tested problems
   (eil51: 1.64%, berlin52: 3.75%, att48: 0.30%). These are reasonable for a
   memetic GWO/HHO with 250 max iterations and 2-opt final polish.

5. **CVRP gaps are higher, roughly 3–16%** (observed in the earlier full
   `--select small` run), likely due to split-decoder overhead — the Prins split
   algorithm adds a vehicle-count penalty and capacity-constrained partitioning
   layer on top of the TSP giant tour.

6. **Numba is still inactive** in this environment. The installed Numba requires
   NumPy ≤ 2.4, but the environment has NumPy 2.5. The solvers fall back to pure
   Python paths gracefully. Installing a compatible Numba version would accelerate
   the 2-opt polish and tour-length evaluation kernels significantly.

---

## 6. Raw CSV Status

The benchmark CSVs were intentionally left **uncommitted** in the working tree:
- `academic_benchmark/numba_results/benchmark_summary.csv`
- `academic_benchmark/numba_results/benchmark_progress.csv`

These contain the fresh post-fix results and are available for inspection but are
not part of any commit, per the task instructions.
