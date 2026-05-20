# UniRide Academic Benchmark — Parallelization & Optimization Strategy

**Date:** 2026-05-19
**Status:** Design Decisions & Architecture Plan
**Hardware Target:** AMD Ryzen 2700X (8 cores / 16 threads, 16GB+ RAM)

---

## 1. Problem Statement

### 1.1 Original Bottleneck: Sequential Optuna Studies

The SOTA engine's `_run_sota_optuna_tuning()` and Numba engine's `_run_optuna_tuning_flow()` ran **completely sequentially**. The `workers` parameter was accepted but never used. Each `(problem, algorithm)` study ran one trial at a time on a single worker.

**Example from berlin52 / R2DMA-TSP:**
```
[I 2026-05-19 15:04:15] Trial 0 finished with value: 0.0 (3 min)
[I 2026-05-19 15:04:50] Trial 1 finished with value: 0.0 (40 sec)
...
[I 2026-05-19 16:04:30] Trial 28 finished with value: 0.0 (4+ min)
```
Trial 0 hit 0% gap at 15:04. Optuna then blindly ran 28+ more trials — **all returning 0.0%** — burning ~4 hours for zero information gain. With 8 workers selected, only 1 was active (12.5% CPU utilization).

### 1.2 Secondary Bottleneck: Study-Level Parallelism Imbalance

After fixing the sequential issue by parallelizing at the **study level** (each study on its own worker), a new problem emerged with heterogeneous workloads:

```
Scenario: 1 problem × 2 algorithms, 8 workers available

Worker 1: Numba-GA study     → 5 min   ✅ done
Worker 2: SOTA-R2DMA study   → 180 min ⏳ still running...
Workers 3-8: IDLE            → 175 min 💀 wasted (73% CPU idle)
```

The more heterogeneous the algorithm speeds, the worse the imbalance. For statistical benchmarking (30 runs × multiple algorithms × multiple problems), this translates to **days of wasted compute time**.

---

## 2. Options Evaluated

### 2.1 Option A: Study-Level Parallelism (Implemented)
**Approach:** Each `(problem, algorithm)` Optuna study runs on its own worker via `ProcessPoolExecutor`.

| Pros | Cons |
|------|------|
| Simple implementation | Workers sit idle when few studies exist |
| No database needed | No cross-study coordination |
| Each study has independent TPE | Severe imbalance with heterogeneous algorithms |
| Works well for many algorithms × many problems | 50-70% CPU waste in mixed workloads |

**Verdict:** Good baseline, insufficient for our use case.

### 2.2 Option B: RDB Shared Storage (Optuna Documented)
**Approach:** All workers connect to a shared PostgreSQL/MySQL database. Optuna's TPE sampler reads all completed trials across workers.

| Pros | Cons |
|------|------|
| Official Optuna pattern | Requires external database server |
| Shared TPE learning across workers | Optuna explicitly says: "never recommend SQLite3 for parallel" |
| Works across multiple machines | `SELECT ... FOR UPDATE` unsupported in SQLite |
| `MaxTrialsCallback` for global trial limits | ~10-20ms overhead per trial |

**Verdict:** Overkill for single-machine use. SQLite file locking on Windows is unreliable. PostgreSQL adds operational complexity.

### 2.3 Option C: `study.ask()` / `study.tell()` with Dynamic Queue (Selected)
**Approach:** Main process holds all studies. Workers pull trial tasks from a shared queue. Results are reported back via `study.tell()`.

| Pros | Cons |
|------|------|
| All workers busy 100% of time | More complex than `study.optimize()` |
| Fast trials cycle through quickly | Manual early stopping logic required |
| Slow trials don't block others | Must handle worker crashes manually |
| No database needed | Must manage trial state lifecycle |
| Each study keeps independent TPE | Callbacks don't work (must check manually) |

**Verdict:** Best fit for our requirements. Maximizes CPU utilization across mixed workloads.

### 2.4 Option D: Chunked Study Submission
**Approach:** Instead of "run 50 trials on 1 worker", do "run 5 trials → submit next 5 → repeat".

| Pros | Cons |
|------|------|
| Better utilization than static assignment | TPE only learns within each chunk |
| No database needed | Cross-chunk learning requires RDB |
| Simpler than ask/tell | Still suboptimal for heterogeneous workloads |

**Verdict:** Middle ground, but ask/tell is superior.

---

## 3. Decisions Made

### 3.1 Early Stopping for Optuna Studies
**Decision:** Stop a study when `gap ≤ 0.01%` for **3 consecutive trials**.

**Rationale:**
- SOTA algorithms find 0% gap on small problems with almost any parameters
- Continuing to 50 trials wastes hours with zero information gain
- Patience=3 prevents stopping on a lucky fluke
- Threshold=0.01% means "close enough to known optimal"

**Implementation:** `_make_optuna_early_stop_callback(patience=3, gap_threshold=0.01)`

**Expected Impact:** ~95% time saved on small problems (3 trials instead of 50).

### 3.2 Time-Based Tie-Breaking
**Decision:** When multiple trials achieve the same gap, select the **fastest** one.

**Rationale:**
- If Trial A (pop=20, 2 min) and Trial B (pop=60, 8 min) both hit 0% gap, Trial A is better
- Faster parameters are more efficient for large-scale benchmarking
- Stored via `trial.set_user_attr("avg_time_sec", ...)` during objective evaluation

**Implementation:** `_select_best_sota_trial(study)` and `_select_best_numba_trial(study)`

### 3.3 Dynamic Queue Architecture (Future Implementation)
**Decision:** Migrate from `study.optimize()` to `study.ask()` / `study.tell()` pattern with a shared task queue.

**Architecture:**
```
Main Process (Scheduler)
  ├── Study A (Numba-GA)     → study.ask() generates trial params
  ├── Study B (Numba-PSO)    → study.ask() generates trial params
  ├── Study C (SOTA-R2DMA)   → study.ask() generates trial params
  └── Task Queue: [A-Trial1, A-Trial2, C-Trial1, B-Trial1, ...]

Workers (8-10 processes)
  ├── Worker 1: A-Trial1 (3 min) → tell() → A-Trial3
  ├── Worker 2: A-Trial2 (3 min) → tell() → B-Trial1
  ├── Worker 3: C-Trial1 (15 min) → still running...
  └── Workers 4-8: Cycle through fast Numba trials
```

**Why this works:**
- Fast trials (Numba: seconds) cycle through quickly
- Slow trials (SOTA: minutes) occupy 1-2 workers but don't block the rest
- All 8 cores stay busy 100% of the time
- Each study maintains its own independent TPE sampler

### 3.4 CPU Utilization Strategy for Ryzen 2700X
**Decision:** Use **8 workers** for pure CPU-bound tasks, **10-12 workers** for mixed workloads.

**Rationale:**
- 8 physical cores → 8 workers saturate compute
- Hyperthreading (16 threads) helps with I/O and memory latency but won't double compute
- Mixed workloads benefit from extra workers to fill idle cycles
- Memory: 16GB+ recommended. 1000-city distance matrix = ~8MB. 8 workers × 8MB = 64MB (negligible)

### 3.5 Statistical Benchmarking Strategy (30 Runs)
**Decision:** Treat each of the 30 runs as an independent task in the queue.

**Rationale:**
- 30 runs per algorithm/problem is standard for academic papers
- Each run uses deterministic seed: `seed = base_seed + run_idx`
- Runs are independent → perfect for parallel execution
- With 8 workers, 30 runs × 6 algorithms = 180 tasks → ~22 batches → fast completion

### 3.6 Small Problems First Scheduling
**Decision:** Schedule problems by size (smallest → largest).

**Rationale:**
- User sees results immediately (burma14, berlin52 complete in minutes)
- Big problems (pr1002, fl1577) run in background
- Psychological benefit: progress is visible from the start
- Early results can guide parameter tuning for larger problems

---

## 4. Numba in SOTA Algorithms: Current Status

### 4.1 What's Already Accelerated
The SOTA algorithms **already use Numba** for the heaviest computational path:

| Component | File | Numba Status |
|-----------|------|--------------|
| Local Search Engine (2-opt, Or-opt, Swap) | `sota_tsp/ls_engine.py` | ✅ Uses `core.numba_accel` |
| Position Matching (R2DMA) | `sota_tsp/r2dma_tsp.py` | ✅ Uses `@numba.njit` |
| Distance Matrix Operations | `sota_tsp/ls_engine.py` | ✅ Uses numpy arrays |

**Critical Insight:** In SOTA algorithms, **80-90% of execution time is spent in local search**. Since local search is already Numba-accelerated, the main evolutionary loop (population update, crossover, mutation) is not the bottleneck.

### 4.2 Recommendation: Don't Numba-ize the Main Loop
**Rationale:**
- The main loop is complex (population management, crossover operators, SA acceptance)
- Numba support for complex Python objects is limited
- ROI is poor: even if 10x faster, the main loop is only 10-20% of total time
- **Better ROI:** Parallelize trials across workers (10x speedup for free)

### 4.3 What to Monitor
- Ensure `NUMBA_AVAILABLE` is `True` in SOTA engine output
- Check that `ls_engine.py` successfully imports `core.numba_accel`
- If Numba is unavailable, SOTA algorithms fall back to pure Python (5-10x slower)

---

## 5. Implementation Roadmap

### Phase 1: Completed ✅
- [x] Parallelize Optuna studies across workers (study-level parallelism)
- [x] Early stopping callback for Optuna (patience=3, threshold=0.01%)
- [x] Time-based tie-breaking for equal-gap trials
- [x] Progress output showing trial count and early stop status

### Phase 2: Dynamic Queue Architecture (Future)
- [ ] Refactor `_run_sota_optuna_tuning` to use `study.ask()` / `study.tell()`
- [ ] Refactor `_run_optuna_tuning_flow` to use `study.ask()` / `study.tell()`
- [ ] Implement shared task queue with `multiprocessing.Queue`
- [ ] Implement worker pool that pulls tasks and reports results
- [ ] Implement manual early stopping (check after each `tell()`)
- [ ] Implement worker crash handling (mark trial as FAIL)

### Phase 3: Benchmark Mode Optimization (Future)
- [ ] For 30-run statistical benchmarking, use same queue without Optuna
- [ ] Schedule problems by size (smallest first)
- [ ] Show live progress dashboard
- [ ] Implement time-per-trial budget for big problems

---

## 6. Key Technical Notes

### 6.1 Why Not a Single Shared Study?
Optuna's TPE sampler learns from past trials to suggest promising regions. However, **different algorithms have completely different parameter spaces**:

```
Numba-GA:   pop_size, generations, mutation_rate, elite_size, crossover_rate
SOTA-R2DMA: population_size, max_iterations, theta_base, remove_ratio, pulse_injection_rate
```

Merging these into one study would be nonsensical — TPE would try to correlate GA's `mutation_rate` with R2DMA's `theta_base`, which have no relationship. Each algorithm needs its own study.

### 6.2 Optuna's Official Stance on Parallelization
From [Optuna docs](https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/004_distributed.html):

| Pattern | How | Good for |
|---------|-----|----------|
| `n_jobs` | `study.optimize(obj, n_jobs=4)` | I/O-bound only (GIL blocks CPU work) |
| RDB shared storage | Multiple processes connect to PostgreSQL/MySQL | Multi-node, same objective function |
| JournalStorage | File-based lock, single machine | Multi-process, same objective function |

**Optuna explicitly says:** *"We would never recommend SQLite3 for parallel optimization"* — `SELECT ... FOR UPDATE` isn't supported by SQLite.

### 6.3 `study.optimize()` vs `ask()`/`tell()`
| Feature | `study.optimize()` | `ask()`/`tell()` |
|---------|-------------------|------------------|
| Ease of use | Automatic loop | Manual scheduling |
| Parallelism | Limited (threads, GIL-bound) | Full (processes, no GIL) |
| Callbacks | Supported | Manual check required |
| Crash safety | Auto-marks FAIL | Must handle manually |
| Optimization quality | Identical | Identical |
| Speed | Sequential per study | Parallel across studies |

### 6.4 Memory Considerations
- Distance matrices are passed to workers via multiprocessing serialization
- For large problems (n > 500), consider `multiprocessing.shared_memory` to avoid duplication
- Current approach: numpy arrays are serialized efficiently (contiguous memory)
- Python lists of lists are ~3x larger than numpy arrays (already fixed in audit)

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **Study** | An Optuna optimization session for one (problem, algorithm) pair |
| **Trial** | A single parameter evaluation within a study |
| **TPE** | Tree-structured Parzen Estimator — Optuna's default sampler |
| **Gap** | Percentage difference from known optimal: `(cost - optimal) / optimal × 100` |
| **BSF** | Best So Far — fallback when optimal is unknown |
| **SOTA** | State-of-the-Art algorithms (E2BSO, R2DMA, P-AOEA, CGO, RUN) |
| **Numba** | JIT compiler that accelerates Python to C-like speeds |
| **ask/tell** | Optuna API for manual trial lifecycle management |

---

## 8. References

- Optuna Distributed Optimization: https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/004_distributed.html
- Optuna FAQ: https://optuna.readthedocs.io/en/stable/faq.html
- Optuna `ask`/`tell` API: https://optuna.readthedocs.io/en/stable/reference/generated/optuna.study.Study.html#optuna.study.Study.ask
- Audit Findings: `AUDIT_FINDINGS_2026-05-19.md`
- Implementation Plan: `IMPLEMENTATION_PLAN_2026-05-19.md`

---

*This document was created on 2026-05-19 to capture design decisions, evaluated options, and the rationale behind the parallelization strategy for the UniRide Academic Benchmark Framework.*
