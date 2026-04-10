# UniRide — Improvement Analysis & Remaining Work

> **Date:** 10 April 2026  
> **Scope:** Full codebase + documentation audit  
> **Status:** Post-forensic-audit, all P0/P1 fixes applied

---

## 📋 Remaining Tasks (Priority Ordered)

### 🔴 High Priority — Do Before Production

| # | Task | Files | Effort | Why |
|---|------|-------|--------|-----|
| 1 | **FIX-04 extend to Pipeline A** — Replace `return 15.0` in 11 non-split strategies with `DEFAULT_TRAVEL_FALLBACK_MINUTES` + `logger.warning` | `ga_strategy.py`, `pso_strategy.py`, `gwo_strategy.py`, `hho_strategy.py`, `ortools_cvrp.py`, `pyvrp_strategy.py`, `vroom_strategy.py` (×2), `greedy_heuristic.py`, `permutation_tsp.py`, `two_opt_strategy.py` | 1 hr | Silent data misses produce wrong routes |
| 2 | **Split Decoder regression tests** — Write pytest cases for FIX-01 (negative departure), FIX-02 (tw_violations accumulation + earliest wait), FIX-03 (trip_end boundary) | New file: `tests/test_split_decoder_audit.py` | 2 hr | Critical logic fixes have zero test coverage |
| 3 | **Strategy smoke tests** — Run each of 18 strategies with a 10-student sample, assert no crash + valid output format | New file: `tests/test_all_strategies_smoke.py` | 2 hr | Any import or method signature break is currently invisible |
| 4 | **FIX-07 complete** — Remove `haversine_distance` from `clustering.py:31`, replace imports in `kmeans.py`, `fuzzy_cmeans.py`, `fuzzy_cmeans_enhanced.py` to use `data_loader.haversine_distance` | `utils/clustering.py`, `utils/clustering_strategies/*.py` | 30 min | Two definitions with different param names (`lon` vs `lng`) — accident waiting to happen |

### 🟡 Medium Priority — Do Before Academic Paper

| # | Task | Files | Effort | Why |
|---|------|-------|--------|-----|
| 5 | **Run benchmark suite** — Execute TSPLib + Solomon instances with all strategies, record wall-time and solution quality | `academic_benchmark/run_smart_benchmark.py` | 3 hr (compute) | Paper needs real numbers, not `[TAHMİNİ]` estimates |
| 6 | **PyVRP/VROOM activation** — `pip install pyvrp pyvroom` and run head-to-head comparison | `requirements-benchmark.txt` | 30 min | Reviewers will ask "Where is your comparison with HGS?" |
| 7 | **GAP calculation fix** — Investigate negative GAP values in benchmark results | `academic_benchmark/utils_benchmark.py` | 1 hr | Theoretically impossible — indicates formula or data error |
| 8 | **Algorithm parameter config UI** — Frontend controls for pop_size, iterations, crossover_rate | New component | 4 hr | Users can't tune solvers without code changes |

### 🟢 Low Priority — Nice to Have

| # | Task | Files | Effort | Why |
|---|------|-------|--------|-----|
| 9 | **DataLoader TTL** — Add `_loaded_at` timestamp + `max_age_seconds` to `DataLoader` singleton | `utils/data_loader.py` | 1 hr | Stale distance data if `time_matrix` is updated during server runtime |
| 10 | **ResourceProfiler config** — Extract `14*60`, `17*60`, `{sw:4, so:5}` to config/env | `utils/resource_profiler.py` | 30 min | Breaks for different campus schedules |
| 11 | **`main.old.py` cleanup** — 24KB dead file sitting in root | `optimizer_api/main.old.py` | 5 min | Confusing for new developers |
| 12 | **Rate limiter middleware** — Redis-backed request throttling for all API endpoints | `main.py` + Redis | 3 hr | Only `/api/auth/hint` has rate limiting currently |

---

## 🧠 Improvement Recommendations

### 1. Performance & Scalability

#### 1.1 Async Optimization Endpoint
**Current:** `/api/v1/optimize` is synchronous — Flask/FastAPI worker blocks until solver finishes (up to 30s for large instances).  
**Recommendation:** Convert to `async def` + `asyncio.run_in_executor(None, solver.optimize, ...)`. Add a job-queue pattern for N>100 students:
```
POST /api/v1/optimize → returns job_id immediately
GET  /api/v1/optimize/{job_id} → poll for result
```
**Impact:** Unblocks the API server for concurrent requests. Essential for production with multiple admin users.

#### 1.2 time_matrix Caching Layer
**Current:** Every optimization request queries Supabase for the full 812-row `time_matrix` table.  
**Recommendation:** Add in-memory cache with 10-minute TTL in `DataLoader`. For multi-server deployment, move to Redis.  
**Impact:** Eliminates redundant DB round-trips (~200ms savings per request).

#### 1.3 Warm-Start for Meta-Heuristics
**Current:** GA/PSO/GWO/HHO always start from random or nearest-neighbor initial populations.  
**Recommendation:** Store the best solution found per (student_set, direction, time) tuple. Seed the initial population with the cached solution + mutations.  
**Impact:** 30-50% reduction in convergence time for repeated planning of similar routes.

---

### 2. Code Quality & Architecture

#### 2.1 Complete the DRY Consolidation
The forensic audit fixed split strategies, but **Pipeline A** (cluster-first) strategies still have:
- 11× hardcoded `return 15.0` (→ use `DEFAULT_TRAVEL_FALLBACK_MINUTES`)
- 4× independent `_get_duration` implementations (→ consider a lightweight mixin or utility function)
- `haversine_distance` in `clustering.py` still duplicates `data_loader.py`

**Concrete action:** One `_get_duration()` function in `utils/distance_helpers.py` imported by all strategies.

#### 2.2 Test Pyramid
**Current state:**
| Layer | Count | Coverage |
|-------|-------|----------|
| Unit tests (resource_profiler) | 20 | ~100% of IE engine |
| CVRPTW phase tests | 3 files | Partial |
| Strategy tests | 2 files | Partial |
| Integration / API tests | 1 file | Minimal |
| E2E (browser) | 0 | None |

**Recommended additions (priority):**
1. `test_split_decoder_audit.py` — Regression tests for FIX-01/02/03
2. `test_all_strategies_smoke.py` — Every strategy runs without crash
3. `test_api_endpoints.py` — FastAPI TestClient for all 7 endpoints
4. `test_clustering_strategies.py` — Each of 7 clustering algorithms
5. Frontend E2E — Playwright test for the optimization flow

#### 2.3 Error Observability
**Current:** `logger.warning` added for distance matrix misses (FIX-04). But there's no centralized error tracking or performance monitoring.  
**Recommendation:**
- Add Sentry or similar APM for Python backend
- Structured JSON logging with correlation IDs per request
- Track p50/p95/p99 optimization latency per algorithm

---

### 3. Feature Enhancements

#### 3.1 Heterogeneous Fleet Activation
**Status:** `VehicleConfig` schema exists in `schemas.py`, `resource_profiler.py` calculates needs, but **no strategy actually uses per-vehicle capacities**.  
**Recommendation:** Modify `HybridSplitBaseStrategy._build_distance_matrix` and `SplitDecoder.__init__` to accept a `List[VehicleConfig]` instead of flat `sw_capacity/so_capacity`. The split decoder already has `sw_capacity` and `so_capacity` — extend it to try different vehicle types in the DP table.  
**Impact:** Enables mixed fleets (minibus + van + bus), which is the real-world scenario.

#### 3.2 Driver Assignment System
**Status:** `route_plans` table has a `driver_assignments` JSONB column. No UI to assign drivers.  
**Recommendation:**
- Drag-and-drop UI: list of drivers → drag onto route cards
- Constraint check: driver availability, vehicle type match
- Auto-assign heuristic: minimize total driver-route distance
**Impact:** Completes the admin workflow — currently optimization output has no actionable driver mapping.

#### 3.3 Evening Confirmation Flow
**Recommendation:**
1. Cron job at 22:00 → query next-day ride requests
2. Push notification to each student: "Confirm or cancel your ride"
3. Student taps confirm → ride confirmed; no response by 23:00 → auto-confirmed
4. At 23:00 → trigger automatic route optimization with confirmed riders only
5. Send route + ETA to assigned drivers

**Impact:** Eliminates manual admin work for daily planning.

#### 3.4 Dynamic Re-Routing
**Scenario:** Student cancels at 07:30, bus departs at 08:00.  
**Recommendation:**
- API endpoint: `POST /api/v1/reoptimize` with `exclude_students: [id1, id2]`
- Run lightweight solver (greedy or two-opt only) on existing routes — don't recompute from scratch
- Push updated route to driver's phone via Supabase Realtime
**Impact:** Handles real-world last-minute changes without full recomputation.

---

### 4. Academic Paper Support

#### 4.1 Benchmark Gaps
The `academic_benchmark/` infrastructure exists but results are **not generated**:
- TSPLib instances: loaded but not benchmarked
- Solomon instances: not integrated yet
- GAP calculation: returns negative values (bug)

**Recommended workflow:**
1. Fix GAP formula in `utils_benchmark.py`
2. Run full benchmark: all 18 strategies × 5 TSPLib instances × 3 runs
3. Generate LaTeX table with mean/std/best/worst
4. Compare against PyVRP (DIMACS 2021 winner) as SOTA baseline

#### 4.2 Statistical Validation
- Use Wilcoxon signed-rank test for pairwise algorithm comparison
- Report p-values for "our method vs. SOTA" claims
- Include convergence curves (fitness vs. iteration) for at least 3 instances

---

### 5. Deployment Readiness

| Area | Current | Recommended |
|------|---------|-------------|
| **Containerization** | None | Dockerfile (frontend) + Dockerfile (backend) + docker-compose.yml |
| **CI/CD** | None | GitHub Actions: lint → test → build → deploy |
| **Rate Limiting** | Only `/api/auth/hint` | Redis-backed middleware for all endpoints |
| **Secrets** | `.env` files | Vercel/Railway env vars + Supabase secrets |
| **Monitoring** | None | Sentry (errors) + Axiom/Datadog (logs + metrics) |
| **SSL** | Via Vercel | Ensure Python API also behind HTTPS (reverse proxy or Railway) |

---

## 📊 Summary Scorecard

| Area | Score | Notes |
|------|-------|-------|
| **Algorithm Correctness** | 9/10 | All P0/P1 bugs fixed; FIX-04 Pipeline A incomplete |
| **Code Quality** | 7/10 | DRY violations reduced but not eliminated; bare excepts clean |
| **Test Coverage** | 3/10 | ~25% estimated; no regression tests for audit fixes |
| **Documentation** | 9/10 | All docs synced with codebase; roadmap current |
| **Security** | 8/10 | Auth guard, CORS fixed; rate limiting still partial |
| **Deployment Readiness** | 2/10 | No Docker, no CI/CD, no monitoring |
| **Feature Completeness** | 6/10 | Core optimization works; driver assignment, notifications, async missing |

**Overall:** The optimization engine is solid post-audit. The biggest gaps are **test coverage**, **deployment infrastructure**, and **driver assignment workflow**.
