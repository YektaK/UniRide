# Plan: Documentation + Dashboard Revival + Unknown Optimal Handling

> **Created:** 2026-05-15
> **Status:** ✅ COMPLETE (All phases implemented)
> **Scope:** Phase 1-5, comprehensive framework upgrade

---

## Phase 1: Documentation Consolidation

**Goal:** Replace `README_BENCHMARK.md` + `BENCHMARK_DOKUMANTASYON.md` with single comprehensive document.

### 1.1 Move Obsolete Docs to `old/`

| File | Reason |
|---|---|
| `README_BENCHMARK.md` | Replaced by new consolidated doc |
| `BENCHMARK_DOKUMANTASYON.md` | Documents pre-consolidation V1/V2 system (deleted files) |
| `000_HANDOFF.md` | Outdated handoff, superseded by AUDIT_FINDINGS |
| `ACADEMIC_INFRASTRUCTURE_REPORT.md` | Historical audit, findings in AUDIT_FINDINGS |
| `BILDIRI2026_VS_MASTER_NUMBA_ANALYSIS.md` | Historical analysis, root causes already fixed |
| `TSPLIB_DB_AGENT_GUIDE.md` | Implementation guide — work already completed |

### 1.2 Create New `BENCHMARK_DOKUMANTASYON.md`

Structure:
```
1. Sistem Genel Bakış
   ├── Dual-engine mimari (Numba + SOTA)
   ├── 15 algoritma listesi + kategorileri
   └── Library + CLI architecture diagram

2. Kurulum ve Çalıştırma
   ├── Dependencies (numpy, numba, scipy, streamlit)
   ├── İki motor karşılaştırma tablosu
   ├── DEFAULT vs TUNING modları
   └── CLI argümanları + örnekler

3. Algoritma Kataloğu
   ├── Her algoritma: açıklama, karmaşıklık, parametreler
   ├── E2BSO-TSP vs E2BSO-TSP-CPSO karşılaştırma
   ├── Sembol tablosu (★ ≤1%, ✓ ≤5%, ○ ≤10%, ✗ >10%)
   └── ATSP destekli algoritmalar

4. Sonuç Yönetimi
   ├── CSV şemaları (benchmark_progress, tuning_progress, summary)
   ├── metadata.json caching mekanizması
   ├── Parametre DB (param_db.py)
   └── TSPLIB SQLite DB (tsplib_manager.py)

5. Developer Guide
   ├── Yeni algoritma ekleme (5 adım)
   ├── Yeni problem ekleme
   ├── Test çalıştırma (pytest)
   └── Sorun giderme tablosu

6. Academic Methodology (English)
   ├── Classical Paper methodology (Mermaid diagrams)
   ├── SOTA Paper methodology (Mermaid diagrams)
   └── Statistical analysis protocol

7. Roadmap & Future Work
   ├── RL Parameter Control (prioritized — 3rd paper candidate)
   ├── LKH-3 Integration (noted for future — n>2000 only)
   └── GPU Acceleration (deprioritized — low ROI for TSP)
```

---

## Phase 2: Expand TSPLIB_OPTIMALS + BSF Fallback

**Goal:** No more `Gap: ERR` or `nan` for unknown-optimal problems.

### 2.1 Expand `TSPLIB_OPTIMALS` Dictionary

Source: Heidelberg TSPLIB95 (http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/)

Add missing values for:
- All STSP instances in `ALL_tsp.tar.gz` not currently in dict
- All ATSP instances (br17, ft53, ft70, ftv33-170, kro124p, p43, rbg323-443, etc.)
- Mark proven optimal vs best-known with comment

### 2.2 Best-So-Far (BSF) Fallback for Unknown Optimals

During benchmark run, when `optimal` is `None` or `0`:

```
Problem: d1655 (n=1655) | Optimal: UNKNOWN
┌─────────────┬──────────┬──────────┐
│ Algorithm   │  Length  │  BSF Gap │
├─────────────┼──────────┼──────────┤
│ E2BSO-TSP   │  62,145  │  0.00%*  │
│ R2DMA-TSP   │  62,201  │  +0.09%  │
│ Numba-GA    │  63,890  │  +2.81%  │
└─────────────┴──────────┴──────────┘
* = best found across all algorithms in this benchmark run
```

Implementation:
- `_compute_bsf_gap(tour_cost, bsf_cost)` → `(tour_cost - bsf_cost) / bsf_cost * 100`
- BSF tracked across all algorithms in current benchmark session
- Display: `BSF Gap` column instead of `Gap%` when optimal unknown
- CSV output: `gap_pct` = BSF gap, `gap_type` = `"bsf"` or `"optimal"`

### 2.3 Store Best Solutions in `tsplib.db`

After each benchmark run, save best-found tour to `best_solutions` table:
```sql
INSERT OR REPLACE INTO best_solutions
(problem_name, algorithm, tour, tour_length, gap, gap_type, timestamp)
VALUES (?, ?, ?, ?, ?, ?, ?)
```

This creates a growing database of best-known solutions that can be used as future baselines.

---

## Phase 3: Dashboard Revival + Enhancement

**Goal:** Move Streamlit dashboard from `old/` to active, fix paths, add enhancements.

### 3.1 Quick Fixes (30 min)

1. Move `dashboard.py` + `dashboard_utils.py` from `old/` to `academic_benchmark/`
2. Fix import: `from dashboard_utils import derive_filter_options`
3. Fix result dirs:
   ```python
   RESULT_DIRS = [
       str(_DASHBOARD_DIR / "sota_results"),
       str(_DASHBOARD_DIR / "numba_results"),
   ]
   ```
4. Fix convergence data source:
   ```python
   # Old: looked for smart_*.csv
   # New: read from benchmark_db/history/smart_*.csv
   history_dir = os.path.join(str(_DASHBOARD_DIR), "benchmark_db", "history")
   ```
5. Add `E2BSO-TSP-CPSO` support (automatic via CSV — no code change needed)

### 3.2 Enhancements (1.5 hours) ✅ COMPLETE

**A. Edge-Frequency Heatmap Tab** ✅ FIXED
- Parse tour data from results
- Build edge frequency matrix: how often each edge appears across top solutions
- Visualize with Plotly heatmap
- Highlight consensus edges (frequency > 70%)
- Added as 7th tab in dashboard

**B. Real-Time Convergence** ✅ FIXED
- Added "Last updated: HH:MM:SS" timestamp display
- Has `🔄 Refresh Data` button with `st.cache_data.clear()` + `st.rerun()`
- Detects new CSV files via cache TTL (60s)

**C. Algorithm Comparison Matrix** ✅ COMPLETE
- New tab: pairwise gap comparison (all vs all)
- Format: `Algorithm A vs Algorithm B` → `+X.XX%` or `-X.XX%` per problem
- Color-coded: green = A better, red = B better

**D. Improved LaTeX Export** ✅ FIXED
- Per-problem breakdown table with significance markers
- BSF gap notation for unknown-optimal problems (`\textsuperscript{\textdagger}`)
- Wilcoxon p-value formatting: `$p < 0.001$` vs `$p = 0.0234$`

### 3.3 Engine Menu Integration ✅ COMPLETE

Added `[D] Dashboard` option to both engine main menus:
```
--- MODLAR ---
  [1] DEFAULT (Standart/Best Parametrelerle Calistir)
  [2] TUNING  (DoE ile Parametre Optimizasyonu Yap)
  [D] DASHBOARD (Streamlit ile Sonuclari Gorsellestir)
  [Q] Cikis
```

**Files modified:**
- `master_numba_engine.py` — Added `[D]` option with subprocess launch
- `master_sota_engine.py` — Added `[D]` option with subprocess launch
- `smart_benchmark.py` — Added `[D]` option with subprocess launch

When selected:
```bash
streamlit run academic_benchmark/dashboard.py
```

---

## Phase 4: Cleanup (Low-Priority Fixes) ✅ COMPLETE

### 4.1 Or-opt Silent Cap ✅ FIXED
- File: `bildiri2026/core/or_opt.py:24`
- Added: `warnings.warn(f"max_segment_size capped from {user_val} to 3")`
- Users now see explicit warning when cap is applied

### 4.2 P-AOEA Diversity Injection ✅ FIXED
- File: `sota_tsp/paoea_tsp.py:217-228`
- Changed: `_inject_diversity()` now mutates from best tour instead of random
- Method: Random swaps (n/10) + 2-opt polish on best tour copy
- Impact: Preserves good solution structure while injecting diversity

### 4.3 R2DMA Edge Consistency ✅ FIXED
- File: `sota_tsp/r2dma_tsp.py:271-301`
- Changed: `_constructive_crossover()` now uses undirected edges `(min(a,b), max(a,b))`
- Impact: Theoretical consistency with resonance scoring component

### 4.4 Update AUDIT_FINDINGS ✅ DONE
- All 3 issues marked as resolved
- Session 6 notes added

---

## Phase 5: RL Parameter Control (Research Direction — Design Only)

**Goal:** Document the architecture for Q-Learning based dynamic parameter adaptation.

### 5.1 Architecture

```
┌─────────────────────────────────────────────┐
│  Q-Learning Agent (per algorithm instance)  │
│  State: [diversity, stagnation, gap, iter]  │
│  Actions: [↑mut, ↓mut, ↑pop, ↓pop,          │
│            ↑ls_int, ↓ls_int]                │
│  Reward: -Δgap (improvement = positive)     │
└──────────────────┬──────────────────────────┘
                   │ adjusted params
                   ▼
┌─────────────────────────────────────────────┐
│  Algorithm Engine (GA/PSO/E2BSO/R2DMA)      │
│  Reports: diversity, best_cost, iteration   │
│  Receives: adjusted params per epoch        │
└─────────────────────────────────────────────┘
```

### 5.2 State Space (4 dimensions)
| Dimension | Range | Discretization |
|---|---|---|
| Diversity (edge entropy) | 0.0 - 1.0 | Low/Med/High (3 bins) |
| Stagnation count | 0 - 100+ | 0/1-10/11-50/50+ (4 bins) |
| Gap percent | 0% - 100%+ | <1%/1-5%/5-20%/>20% (4 bins) |
| Progress ratio | 0.0 - 1.0 | Early/Mid/Late (3 bins) |

Total states: 3 × 4 × 4 × 3 = **144 states**

### 5.3 Action Space (6 discrete actions)
| Action | Effect |
|---|---|
| `↑mutation` | Increase mutation rate by 10% |
| `↓mutation` | Decrease mutation rate by 10% |
| `↑ls_intensity` | Increase local search budget |
| `↓ls_intensity` | Decrease local search budget |
| `↑exploration` | Increase diversity injection rate |
| `↓exploration` | Decrease diversity injection rate |

### 5.4 Reward Function
```
reward = -(gap_new - gap_old)  # Negative gap change = positive reward
if gap_new < gap_old * 0.99:   # Bonus for >1% improvement
    reward += 1.0
if stagnation_count > 20:      # Penalty for prolonged stagnation
    reward -= 0.5
```

### 5.5 Implementation Plan (Future Session)
1. Create `academic_benchmark/rl_controller.py` — Q-table agent
2. Create wrapper class that intercepts algorithm params per epoch
3. Integrate with existing engines (minimal changes — wrapper pattern)
4. Benchmark: RL vs DoE-tuned on 10 problems × 5 algorithms
5. Publish as 3rd paper: "Adaptive Meta-Heuristic Control via Q-Learning for TSP"

**Estimated effort:** 2-3 weeks
**Paper potential:** High — RL for meta-heuristic control is underexplored in TSP literature

---

## Execution Order

| Phase | Effort | Dependencies |
|---|---|---|
| 1. Documentation | 1 hour | None |
| 2. Expand Optimals + BSF | 2 hours | None |
| 3. Dashboard Revival | 2 hours | Phase 2 (BSF gap in CSV) |
| 4. Cleanup | 1 hour | None |
| 5. RL Design (doc only) | 1 hour | None |

**Total estimated effort:** ~7 hours

---

## Success Criteria ✅ ALL MET (12/12)

1. ✅ Single comprehensive `BENCHMARK_DOKUMANTASYON.md` replaces both old docs
2. ✅ All 111+ STSP + 19 ATSP instances have known optimal or BSF fallback
3. ✅ No `Gap: ERR` or `nan` during benchmark runs
4. ✅ Streamlit dashboard runs with `streamlit run academic_benchmark/dashboard.py`
5. ✅ Dashboard has 7 tabs: Leaderboard, Robustness, DoE, Wilcoxon, Convergence, Comparison Matrix, Edge Frequency Heatmap
6. ✅ Dashboard accessible from engine menu (`[D] Dashboard`)
7. ✅ 3 low-priority fixes applied (Or-opt warning, P-AOEA diversity, R2DMA edges)
8. ✅ RL parameter control design documented
9. ✅ All obsolete docs moved to `old/`
10. ✅ All tests pass (43/43)
11. ✅ `gap_type` persisted to all CSV outputs (benchmark_progress.csv + benchmark_summary.csv)
12. ✅ Dashboard enhancements: "Last updated" timestamp, Edge Frequency Heatmap, BSF LaTeX notation
