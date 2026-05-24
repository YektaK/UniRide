# UniRide Worklog

## Phase 1–6: Refactoring & Bugfixing (Completed)

### NameError Fixes
- `paoea_tsp.py`, `e2bso_tsp.py`: Fixed undefined `rng`, `pd`, `np`, `random` references
- `cgo_tsp.py`: Fixed undefined `_rank_selection`, `_merge_solutions`, `_chaos_merge`
- `run_tsp.py`: Fixed undefined `np`, `_merge_solutions`
- `r2dma_tsp.py`: Fixed undefined `adjacency_mutate`, `_merge_solutions`, `np`
- All `sota_common/` strategies: Fixed import-based NameErrors

### Integration & Pinning
- `base_solver.py`: Hardcoded `num_vehicles=3` removed → uses solver default
- `e2bso_tsp.py`: `_improve_population` bound to `e2bso_improve` (was pointing to local_search)
- `run_tsp.py`: `_improve_population` bound to `run_improve` (was pointing to local_search)
- `paoea_tsp.py`: `_improve_population` bound to `paoea_improve`
- `cgo_tsp.py`: `_solve` no longer re-wraps `dm_np`

### Test Infrastructure
- `test_all_solvers.py`: Created with 5-solver test + `brute_force_optimal()` reference solver
- `test_known_optimal_4node`: All 5 solvers pass at <5% gap on optimal 4-node tour
- `00walkthrough.v2.md`: Status document kept current

### Dead Code Removal
- `e2bso_tsp.py` (2x), `r2dma_tsp.py` (1x): `prev_best = gbest_cost` removed (never read)

### CGO O(n³) Fix
- `_seed_to_full_tour` in `cgo_tsp.py`: Replaced full-tour recompute with delta insertion cost (O(n²))

### Repair Operations
- `repair_ops.py`: Added `_regret_k_insertion(k)` factory; `RegretKInsertion(k)` base class already existed

### Documentation
- `uniride_core/README.md`: Structure, usage, solver table, test command

---

## Phase 3.4: TSPLIB Parser Consolidation
- `tsplib_parser.py` moved to `uniride_core/algorithms/` as canonical location
- `optimizer_api/utils/tsplib_parser.py` → re-export shim for backward compatibility
- Duplicate parsing functions removed from `tsplib_manager.py`, `cli_engine.py`

## Phase 3.5: API Error Response Sanitization
- `routers/optimization.py`: `traceback.print_exc()` → `logger.exception()`
- `routers/benchmark.py`: Raw `str(e)` leaks → generic error messages
- `main.py`: Global exception handler added

## Phase 3.6: TTL/Eviction for BenchmarkStateManager
- `BenchmarkStateManager._evict_expired()`: Configurable TTL (default 2h) + `max_runs` cap (100)
- Lazy eviction on `create_run`, `get_run`, `list_runs`

---

## Phase 4: Cleanup & Polish (Completed)

### P4-1: Remove stale docs from root
- `00walkthrough.md`, `code_review.md`, `turkish_code_review.md` removed

### P4-2: 3-opt deduplication in numba_accel.py
- `_build_3opt_candidate()` helper — 7 reconnection cases → 1 parametrized call

### P4-3: py.typed marker
- Added `py.typed` to `uniride_core`

### P4-4: i18n (next-intl)
- `messages/en.json`, `messages/tr.json` — ~300 keys each
- Locale routing via middleware (`as-needed`, Turkish default)
- `NextIntlClientProvider` in layout
- All ~45 frontend files migrated to `useTranslations()`
- Build + type-check pass clean

---

## Code Review Quick Wins (All Applied)

| # | Issue | Fix |
|---|-------|-----|
| Q1 | Duplicate `euclidean_distance` in `data_loader.py` | Second definition (lines 241–247) deleted |
| Q2 | 3 `Direction` enums across codebase | Unified import: both `split_decoder.py` + `linear_split_decoder.py` import from `models.schemas` |
| Q3 | `_get_duration` duplicate in `HybridSplitBaseStrategy` | Deleted (inherited from `BaseRoutingStrategy`) |
| Q4 | `LocationNode.lat/lng` no validation | Added `ge=-90/90`, `le=-180/180` validators |
| Q5 | `TSPResult.__post_init__` falsy-value bug | Explicit `is not None` + `!= 0.0` instead of truthiness |
| Q6 | `print()` in `registry_setup.py` | → `logger.info()` |
| Q7 | `GAEnhancedSplitStrategy` not in registry | Registered as `"ga_split_enhanced"` / `"ga-split-enhanced"` in `STRATEGY_REGISTRY` |

---

## S2: 3-opt Reconnection Pattern Fix
- `local_search.py`: Replaced 4 duplicate patterns with 3 missing relocation variants (swap B/C, swap+reverse B, swap+reverse C)
- All 7 patterns are now unique and correct

---

## S1: Thread-Safe Optimize (Completed)

Per-request `self.rng` override added to all 6 strategies that had a local `rng` variable but never assigned it back:

| Strategy | File | Change |
|----------|------|--------|
| GASplitStrategy | `ga_split_strategy.py:407` | `self.rng = rng` |
| PSOSplitStrategy | `pso_split_strategy.py:315` | `self.rng = rng` |
| GWOSplitStrategy | `gwo_split_strategy.py:319` | `self.rng = rng` |
| HHOSplitStrategy | `hho_split_strategy.py:369` | `self.rng = rng` |
| GAStrategy | `ga_strategy.py:369` | `self.rng = rng` |
| GWOStrategy | `gwo_strategy.py:318` | `self.rng = rng` |

**Skipped (negligible race window):** PSO Pipeline A, HHO Pipeline A (no per-request RNG variable); TwoOptStrategy (2 RNG uses in `_initialize_population`, called once per `optimize()`)

---

## S3: Asymmetric Haversine Fallback (Completed)

- `build_haversine_matrix()`: Added `asymmetric` + `asymmetry_range` params
- When `asymmetric=True`, applies deterministic per-edge perturbation via `hash()` of location ID pair — same request always produces same asymmetry
- Plumbed through `get_submatrix()` as `asymmetric_haversine` parameter
- Matrix remains symmetric by default (`asymmetric=False`)

---

## L3: ATSP Benchmark Coverage in DOE (Completed)

### ATSP download infrastructure (`uniride_core/algorithms/tsplib_parser.py`)
- Added `ATSP_DOWNLOAD_URL` (Heidelberg ATSP archive)
- Added `ATSP_PROBLEM_NAMES` list (18 ATSP instances: br17, ft53, ft70, ftv33–ftv170, kro124p, p43, rbg323–rbg443)
- Added `download_atsp_problem()` — downloads `.atsp` files (via tgz or direct) to `tsplib_data/`
- Added `ensure_atsp_problems()` — batch download/verify all ATSP instances
- Added ATSP optimal values (19 entries) to `TSPLIB_OPTIMALS`
- Updated `get_available_problems()` to scan both `.tsp` and `.atsp` files
- Updated `__all__` exports with new symbols

### ATSP integration tests (`academic_benchmark/tests/test_atsp_integration.py`)
- 10 tests covering: ATSP parsing, asymmetric matrix verification, ProblemInstance creation, SOTA solver compatibility (E2BSO, R2DMA, ALNS) on asymmetric matrices, optimal value presence, deterministic tour cost computation
- All tests run offline (no network) using synthetic ATSP matrix

---

## L5: CI Pipeline with Strategy Regression Tests (Completed)

### Regression gate test (`academic_benchmark/tests/test_regression_gate.py`)
- 6 SOTA solvers (E2BSO, R2DMA, P-AOEA, CGO, RUN, ALNS) × 5 synthetic problems (4 to 8 nodes) = 30 parametrized test cases
- Each problem's optimal computed via brute-force permutation
- Gap threshold: 15% (conservative for low-iteration CI config)
- No network or TSPLIB data required — runs entirely on synthetic data
- Execution time: ~3.5s for all 30 tests

### GitHub Actions workflow (`.github/workflows/benchmark.yml`)
- Triggers on PR + push to main/master
- Matrix build: Python 3.12 + 3.13 on ubuntu-latest
- Four test stages: SOTA smoke tests → ATSP integration → Regression gate (5×6) → SOTA E2E
- Fails CI if any solver exceeds gap threshold on any problem

---

## L2: Vectorize ProblemInstance.prepare_matrices (Completed)

- `uniride_core/models.py`: Distance matrix uses NumPy broadcasting for n > 100:
  - `coords[:, np.newaxis, :] - coords[np.newaxis, :, :]` → fully vectorized O(n²)
  - KNN mask uses `np.argsort(arr, axis=1)` → `indices[i, 1:k+1]`
- Falls back to pure-Python loops for n ≤ 100 (avoids NumPy import overhead)
- Backward compatible — method signature unchanged

---

## L6: ALNS Destroy/Repair Operators (Completed)

### New file: `uniride_core/algorithms/sota_tsp/alns_tsp.py`
- `ALNSConfig` dataclass: iterations (5000), max_no_improve (500), remove_ratio (0.2), segment_length (100), weight_update_factor (0.8), noise_scale (0.05), SA params (start_temp=100, cooling_rate=0.995)
- `ALNS_TSP(BaseTSPSolver)`: Standalone ALNS solver with:
  - **Initial solution**: Nearest-neighbor heuristic
  - **Operator pool**: 4 destroy (Random, Worst, Shaw, Related) + 3 repair (Greedy, Regret-2, Regret-3)
  - **Adaptive selection**: Roulette-wheel based on cumulative segment scores
  - **Weight updates**: Every `segment_length` iterations, weights decay via `w * (1-ρ) + ρ * (score/count)`
  - **SA acceptance**: `exp(-Δ/T)` probability for worsening moves, temperature cools geometrically
  - **Sigma scoring**: 5 (new best), 2 (better than current), 0 (rejected)
  - **Early stopping**: `max_no_improve` iterations without improvement
- Exported from `sota_tsp/__init__.py` as `ALNS_TSP`, `ALNSConfig`
- Registered in `academic_benchmark/core/registry_setup.py` as `SOTA-ALNS-TSP` (in `SOTA_ALGOS` + `mod_map`)

### Remaining backlog items
- (none — all backlog items complete)
