# SOTA Benchmark — Deep Analysis & Implementation Plan

> **Goal:** Make `run_sota_benchmark.py` the gold-standard TSPLIB benchmark for E²BSO, R²DMA, and P-AOEA — correct, fast, and visually excellent.

---

## 1. CODEBASE OVERVIEW

### File Map

| File | Role | Status |
|------|------|--------|
| `run_sota_benchmark.py` | Main benchmark runner (460 lines) | Multiple issues |
| `sota_tsp/e2bso_tsp.py` | E²BSO-TSP solver | Critical perf issue |
| `sota_tsp/r2dma_tsp.py` | R²DMA-TSP solver | O(n²) resonance bug |
| `sota_tsp/paoea_tsp.py` | P-AOEA-TSP solver | Mostly correct |
| `sota_tsp/ls_engine.py` | Multi-layer local search | Missing 3-opt, wrong docstring |
| `sota_tsp/base_solver.py` | NINT Euclidean distance | Correct |
| `sota_tsp/destroy_ops.py` | ALNS operators | Correct |
| `sota_tsp/repair_ops.py` | ALNS repair | Correct |
| `bildiri2026/3_run_benchmark.py` | Reference benchmark (2-opt/3-opt/GA/PSO) | Correct reference |

---

## 2. CRITICAL BUG ANALYSIS

### BUG 1 (CRITICAL): E²BSO Taking 85 Seconds on berlin52

**Location:** `e2bso_tsp.py:295` and `ls_engine.py`

The config uses `ls_time_limit=0.5s` per individual per iteration. For berlin52 (n=52) with pop_size=26 and max_iter=156:
- 156 iterations × 26 individuals × 0.5s = **up to 2028s** theoretical
- In practice (no Numba, Python fallback 2-opt): ~85s total

**Root cause:** The 0.5s per-call LS time limit is not scaled by Numba availability. When Numba is absent, the Python fallback 2-opt on n=52 takes 0.05-0.5s per call.

**Fix:** Detect Numba at import time and scale `ls_time_limit` accordingly:
- No Numba: `ls_time_limit = min(0.05, 0.002 * n_nodes)`
- With Numba: keep 0.5s limits

---

### BUG 2 (CRITICAL): R²DMA O(n²) Resonance Per Iteration

**Location:** `r2dma_tsp.py:86-93` — `_compute_resonance` function

```python
# BUGGY: O(n²) adjacency match
for i in range(len(t1)):
    a, b = t1[i], t1[(i + 1) % len(t1)]
    for j in range(len(t2)):   # <-- O(n²) !
        c, d = t2[j], t2[(j + 1) % len(t2)]
        if (a == c and b == d) or (a == d and b == c):
            adj_match += 1
            break
```

Combined with the outer `O(pop²)` partner selection loop:
- **Total per iteration:** `O(pop² × n²)` = 60² × 52² ≈ 9.7M ops × 500 iters = 4.8B ops

**Fix:** Replace `adj_sim` with O(n) set-based computation:
```python
edges1 = {(min(a,b), max(a,b)) for i in range(n) for a,b in [(t1[i], t1[(i+1)%n])]}
edges2 = {(min(a,b), max(a,b)) for i in range(n) for a,b in [(t2[i], t2[(i+1)%n])]}
adj_sim = len(edges1 & edges2) / n  # O(n)
```
(Edge_sim already does this correctly — adj_sim was redundant and bugged.)

New resonance formula: `0.6 * edge_sim + 0.4 * pos_match` (remove adj_sim entirely).

---

### BUG 3 (MEDIUM): Non-Deterministic Seeding Across Processes

**Location:** `run_sota_benchmark.py:392`

```python
seed = SEED_BASE + run_idx + hash(algo) % 1000
```

Python's `hash()` is randomized by PYTHONHASHSEED (per-process on Windows). In multiprocessing (spawn mode), child processes may compute different hash values.

**Fix:** Use algo index: `seed = SEED_BASE + run_idx * 37 + algo_idx * 100`

---

### BUG 4 (MEDIUM): ProcessPoolExecutor Crashes on Windows

Windows multiprocessing (spawn) pickles the distance matrix (`List[List[float]]`) for every subprocess. For large problems this causes memory pressure and crashes (confirmed in conversation `3e3d0d9c`).

**Fix:** Sequential execution by default on Windows, `--parallel` flag for opt-in.

---

### BUG 5 (LOW): `ls_engine.py` Docstring/Chain Mismatch

The docstring says "Chains: 2-opt → Or-opt → 3-opt → Swap" but actual code uses `improve_swap` (not 3-opt) for `"full"` intensity.

**Fix:** Update docstring to say "2-opt → Or-opt → Swap" (accurate), or add proper 3-opt from `bildiri2026/core/three_opt.py`.

---

### BUG 6 (LOW): TSPLIB Parser CRLF Handling

**Location:** `run_sota_benchmark.py:115-126`

The regex `r"NODE_COORD_SECTION\s*\n(.*?)"` fails on Windows CRLF files.

**Fix:** Normalize line endings before parsing: `content = content.replace('\r\n', '\n')`

---

### BUG 7 (LOW): Missing Optimals for Existing TSPLIB Files

Files in `tsplib_data/` without entries in `TSPLIB_OPTIMALS`:
- `lin105.tsp` → optimal = 14379
- `rd100.tsp` → optimal = 7910  
- `pr136.tsp` → optimal = 96772
- `pr144.tsp` → optimal = 58537

---

## 3. ALGORITHM CORRECTNESS REVIEW

### E²BSO-TSP: CORRECT (performance issue only)
- Shannon edge entropy: correct normalized formula
- LAHC acceptance: correctly implemented
- Adaptive entropy thresholds: learning period logic correct
- Swarm update (edge forcing): sound implementation
- ALNS inject diversity: correct
- Final LS polish: applied correctly after loop
- **Only issue:** LS time budget scaling (Bug 1)

### R²DMA-TSP: MOSTLY CORRECT (one critical bug)
- OX crossover: correct order crossover implementation
- Constructive crossover: edge-based, sound logic
- SA acceptance with dissonance filter: correct
- Theta adaptation via success rate: correct
- **Critical issue:** `adj_sim` is O(n²) (Bug 2)
- After fix: algorithm logic is sound

### P-AOEA-TSP: CORRECT (best implementation)
- Operator genomes with selection weights: correct
- Meta-evolution (crossover/mutation of genomes): correct
- Destroy intensity linear decay: good exploration-exploitation
- LAHC/SA dual acceptance: correctly implemented
- No bugs found

---

## 4. COMPARISON WITH bildiri2026

| Feature | bildiri2026/3_run_benchmark.py | run_sota_benchmark.py |
|---------|-------------------------------|----------------------|
| Problem loading | JSON config + TSPLIB parser | Direct TSPLIB parser |
| Execution | Parallel ProcessPool | Parallel (crashes on Win) |
| Per-result CSV | Immediate append | Immediate append |
| Gap vs optimal | Yes | Yes |
| Summary table | Detailed | Detailed but basic |
| Convergence JSON | Yes | Yes |
| Interactive UI | Rich (categories, alias) | Basic |
| ETA estimation | DynamicTimeEstimator class | None |
| Algorithm info | No | No |
| System info | Yes (OS, CPU, Numba) | No |
| Performance | Fast (LS only) | Slow (SOTA overhead) |
| Windows stability | High | Low (crashes) |

---

## 5. PERFORMANCE ANALYSIS

### Measured Results (berlin52, n=52, 1 run each)

| Algorithm | Time | Gap | Assessment |
|-----------|------|-----|------------|
| E²BSO-TSP | 85.6s | 0.00% | Too slow — fix LS budget |
| R²DMA-TSP | 6.2s | 4.55% | After O(n²) fix: ~1-2s, better quality |
| P-AOEA-TSP | 24.2s | 0.00% | Acceptable but can be faster |

### Speed Targets After Fixes

| Algorithm | Target Time | Target Gap |
|-----------|------------|------------|
| E²BSO-TSP | < 10s (berlin52) | <= 2% |
| R²DMA-TSP | < 2s (berlin52) | <= 5% |
| P-AOEA-TSP | < 15s (berlin52) | <= 2% |

---

## 6. UI IMPROVEMENTS

### Current Deficiencies
1. No system capability banner (Numba/workers status)
2. No ETA estimation during benchmark
3. Progress is only `[x/y]` counter, no bar
4. Summary table has inconsistent separators
5. No per-problem best-algorithm highlight
6. No overall ranking table
7. No color/emphasis for critical values

### Planned Enhancements

**A) Rich startup banner:**
```
╔═══════════════════════════════════════════════════════╗
║    SOTA BENCHMARK v5.0 — TSP-native TSPLIB Suite     ║
║    E²BSO · R²DMA · P-AOEA  |  2026-04-29 23:10      ║
╠═══════════════════════════════════════════════════════╣
║  Python 3.11 | Numba: ACTIVE | Workers: 1 (seq)      ║
║  Problems: 8 | Algorithms: 3 | Runs/algo: 3          ║
╚═══════════════════════════════════════════════════════╝
```

**B) Live progress per problem:**
```
══ berlin52 (n=52, optimal=7542) ══════════════ ETA: 28s
  [1/3] E2BSO-TSP   ████████░░  7542  gap=0.00%   8.2s DONE
  [2/3] R2DMA-TSP   ██████████  7885  gap=4.55%   1.8s DONE
  [3/3] P-AOEA-TSP  ████░░░░░░  running...
```

**C) Box-drawing summary table:**
```
┌─ berlin52 (n=52, optimal=7542) ─────────────────────────────┐
│  Algorithm   │   Best │   Mean │ StdDev │ Gap(B) │ Gap(A) │
│──────────────┼────────┼────────┼────────┼────────┼────────│
│ *E2BSO-TSP   │   7542 │ 7542.0 │    0.0 │  0.00% │  0.00% │
│  R2DMA-TSP   │   7885 │ 7885.0 │    0.0 │  4.55% │  4.55% │
│ *P-AOEA-TSP  │   7542 │ 7542.0 │    0.0 │  0.00% │  0.00% │
└─────────────────────────────────────────────────────────────┘
```

**D) Final ranking:**
```
OVERALL RANKING (avg gap across N problems):
  1. E2BSO-TSP   avg=1.23%  best=0.00%
  2. P-AOEA-TSP  avg=1.87%  best=0.00%  
  3. R2DMA-TSP   avg=4.21%  best=2.10%
```

---

## 7. IMPLEMENTATION PLAN

### Phase 1: Critical Bug Fixes

**Task 1.1** — Fix `_compute_resonance` in `r2dma_tsp.py`
- Remove O(n²) `adj_sim` loop
- New: `adj_sim = len(edges1 & edges2) / n` using precomputed edge sets
- Formula: `0.6 * edge_sim + 0.4 * pos_match`
- **File:** `sota_tsp/r2dma_tsp.py` — function `_compute_resonance`

**Task 1.2** — Fix LS time budget scaling in `run_sota_benchmark.py`
- Import `_NUMBA_AVAILABLE` from ls_engine at module level
- Add helper `_make_solver_config(algo, n, numba_ok)` that sets tight time limits when no Numba
- **File:** `run_sota_benchmark.py` — `_run_solver_task` function

**Task 1.3** — Fix deterministic seeding
- Replace `hash(algo) % 1000` with `ALL_ALGOS.index(algo) * 100`
- **File:** `run_sota_benchmark.py` — line 392

**Task 1.4** — Add CRLF normalization to parser
- `content = content.replace('\r\n', '\n').replace('\r', '\n')`
- **File:** `run_sota_benchmark.py` — `parse_tsplib` function

**Task 1.5** — Add missing TSPLIB optimals
- Add lin105, rd100, pr136, pr144 to `TSPLIB_OPTIMALS` dict
- **File:** `run_sota_benchmark.py` — lines 49-68

**Task 1.6** — Fix ls_engine.py docstring
- Update to "2-opt → Or-opt → Swap"
- **File:** `sota_tsp/ls_engine.py` — line 4

### Phase 2: Execution Mode Fix

**Task 2.1** — Switch default to sequential execution on Windows
- Detect `sys.platform == 'win32'` at startup
- Default `workers=1` on Windows unless `--parallel` flag
- Implement sequential fallback: simple for-loop over tasks
- **File:** `run_sota_benchmark.py` — `main()` function

**Task 2.2** — Adaptive config helper
```python
def _make_solver_config(algo_name, n_nodes, numba_ok):
    if numba_ok:
        ls_limit = 0.5
        pop = max(20, min(60, n_nodes // 2))
        max_iter = max(200, min(500, n_nodes * 5))
    else:
        ls_limit = min(0.08, 0.002 * n_nodes)
        pop = max(15, min(40, n_nodes // 3))
        max_iter = max(100, min(300, n_nodes * 3))
    ...
```

### Phase 3: UI Rewrite

**Task 3.1** — Startup banner with system detection
- Detect Python version, Numba, CPU count, Windows/Linux
- Display in box-drawing frame

**Task 3.2** — ETA system (adapted from bildiri2026's DynamicTimeEstimator)
- Track actual elapsed times per (algo, n_nodes)
- Estimate remaining time dynamically

**Task 3.3** — Live progress display
- Per-problem header with optimal
- Per-run result line with gap and time

**Task 3.4** — Enhanced summary table
- Box-drawing characters (┌┐└┘│─┼)
- `*` prefix for algorithms matching best cost
- Warn if gap > 10%

**Task 3.5** — Final ranking table across all problems

### Phase 4: Feature Polish

**Task 4.1** — `--parallel` CLI flag (opt-in ProcessPool)
**Task 4.2** — `--time-limit N` per-algorithm time limit
**Task 4.3** — Convergence JSON matching bildiri2026 format
**Task 4.4** — `--size-limit` default change: 300 (was 500)

---

## 8. FILES TO CHANGE

| File | Change | Risk |
|------|--------|------|
| `run_sota_benchmark.py` | Full rewrite (UI + execution + configs) | Low — standalone script |
| `sota_tsp/r2dma_tsp.py` | Fix `_compute_resonance` function only | Low — isolated function |
| `sota_tsp/ls_engine.py` | Update docstring only | None |

**NOT changing:** `e2bso_tsp.py`, `paoea_tsp.py`, `base_solver.py`, `destroy_ops.py`, `repair_ops.py`

---

## 9. ACCEPTANCE CRITERIA

- [ ] `berlin52`: E²BSO-TSP completes in < 15s (was 85s)
- [ ] `berlin52`: R²DMA-TSP completes in < 3s with gap < 5%
- [ ] No Windows crash with sequential mode
- [ ] `--non-interactive` works end-to-end
- [ ] Summary table uses box-drawing characters
- [ ] ETA shows during benchmark run
- [ ] Convergence JSON saved per problem
- [ ] All 37 TSPLIB files in `tsplib_data/` load correctly
