# MT6: One Canonical 3-opt (Speed-up with Parity, SOTA Polish, Production Hybrid) and Deterministic SOTA Termination

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan item by item. Steps use checkbox (`- [ ]`) syntax. **Status: DRAFT for owner approval (Gate C plan Q4, DECISION_LOG A17 `:443`; A18 `:500`, `:508`: MT6 is a precondition of any paper-scale run). No MT6 code work starts before the owner approves this plan and answers the owner questions in section 6.**

**Goal:** close audit findings **M25** (canonical 3-opt is dominated by duplicate-detection bookkeeping), **H10** (the forbidden Numba 3-opt kernel runs in every SOTA final polish), **H11** (SOTA TSP solvers stop on wall-clock time) and **M14** (the production "hybrid" local search uses a second, non-canonical 3-opt), so that one 3-opt neighbourhood family is reachable from public entry points and every SOTA result is a function of its seed and configuration only.

**What MT6 is not:** MT6 does not make the SOTA solvers governed (they stay refused in fixed-budget and native protocol mode, `academic_benchmark/core/registry_setup.py:571-575`), does not add SOTA IDs to a study profile, does not tune parameters, and does not run paper-scale experiments. Audit roadmap row MT6 (`docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md:1562`) also lists `sota_common` archiving, shim removal, L3 and L10; the owner's Q4 scoped this plan to H10, H11, M14 and M25, so those stay out (section 8, OQ-MT6-7). M26 is already FIXED (tracker `:2339`).

**Architecture:** every neighbourhood change is core-owned in `uniride_core/algorithms/three_opt.py` (AGENTS.md: canonical algorithms belong in `uniride_core`). SOTA solvers (`uniride_core/algorithms/sota_tsp/`) and the production local search (`uniride_core/algorithms/local_search.py`) become callers. `academic_benchmark` changes only in tests. Production strategy exposure does not change (`academic_benchmark/tests/test_production_registry_snapshot.py`).

**Base:** branch `WIP`, HEAD `02554692` (2026-10-26). Plan written in worktree `.claude/worktrees/mt6-plan` on branch `docs/mt6-plan`. The planner ran no tests and no timings (a D-04b timing calibration was running on this machine); every developer records a fresh baseline first.

**Fact/assumption key used throughout:** **[F]** = verified in live code or a committed record at `02554692` (file:line given); **[A]** = assumption or inference that the item's developer re-checks first; **[O]** = owner choice, listed in section 6 and never chosen by a developer or the lead.

## Global constraints (every brief that implements an item repeats these)

- **Python on Windows (top of every brief):** never open interactive Python (no bare `python`/`py`/`python3`, no `python -i`, no `python -`, no heredoc or stdin into Python, no `cat > file`). Write scripts to a file under `C:\wt\<name>` and run them with `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`, with `PYTHONPATH` set to the worktree (the editable install points at the main checkout; print `uniride_core.__file__` once). Use `-c` only for one-liners if the brief allows it at all. Time-limit every command and redirect output to a file. Stop on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only your own PIDs. Never `git stash`. No checkout/switch in the main checkout. Temp folders only under `C:\wt\<name>`.
- Never write, copy or delete `academic_benchmark/tsplib_data/tsplib.db*`. Never run AMPL. No download of instance files. Never write under `docs/paper/results`.
- Each item runs in its own worktree and branch (`git worktree add <path> -b <branch> WIP`, except MT6-02, which branches from the MT6-01 branch head, section 4), red test first, frequent commits, no merge, no push. The lead merges with `--no-ff` after the reviewer's ONAY and passing tests.
- No benchmark runs. Tests use in-memory matrices (n <= 60) and at most the smoke slice of a profile. The only timings are the ones an item names explicitly (MT6-01 one-pass timing, MT6-03 latency check, MT6-04 replay, MT6-06 re-measure); they are planning numbers, never evidence of algorithm quality, and they never run while another timing run is active on the same machine. Smoke or pilot results produce no superiority, causality or proof claims (AGENTS.md).
- Do not change: production strategy exposure, core `ExecutionProtocol` (E12), the capability catalog, the study profiles' scientific values, the objective-evaluation definition ("one complete closed-tour objective calculation", `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md:49`), or the canonical neighbourhood semantics (`CANONICAL_THREE_OPT_DESIGN.md:37-75`) except where an owner answer in section 6 says so.
- Do not reopen decided questions: A01, A04 (fixed budget primary, native separate, never pooled), A11, A13, A14 (no pooling across result-changing fixes), A15, A16, A17 (all Gate C decisions, including owner decision 4: SOTA-* refuse CVRP/CVRPTW), A18 (Gate D decisions, OQ-10: one campaign = one clean commit), E09, E10, E12.
- Archived code (`archive/academic_benchmark/*_legacy/`) is `REFERENCE_ONLY`: read as history, never imported or executed.
- The canonical 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:124-128`) passes before and after every item; any new focused 3-opt test module is added to that command in the design document by the same item (`:130`).
- Each merged item updates Appendix J of `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md` for the IDs it closes (H10 `:2328`, H11 `:2329`; M14 and M25 are inside the collective row "M1-M25 (others)" `:2350`: the first MT6 merge splits them into their own rows) and records decisions in `docs/DECISION_LOG.md` (new entry **A19 "MT6 plan and owner decisions"**, created when this plan is merged).

---

## 1. Verified current state (live code at `02554692`)

### 1.1 M25: canonical 3-opt cost per evaluation

| # | Claim | Status | Evidence |
|---|---|---|---|
| M25-a | Cut enumeration scans every `C(n,3)` triple even with a window, then filters | **[F] CONFIRMED** | `three_opt.py:78-83` (`combinations(range(n), 3)`, then `j - i > window` / `k - j > window` skip). At n = 100, window 12 the loop visits 161,700 triples to admit roughly n*w^2 [A: about 13,000; the developer counts it]. |
| M25-b | Every candidate pays an O(n^2) duplicate key | **[F] CONFIRMED** | Symmetric mode builds 48 arrangements per triple (`:154-162`, 6 orders x 8 reversal flags) and calls `_symmetric_cycle_key` on each (`:96-101`: 2n rotations of length n, then `min`). Directed mode builds 6 orders and calls `_directed_cycle_key` (`:91-93`, n rotations). The original route's key is also recomputed per triple (`:142`, `:151`). |
| M25-c | The symmetric output order is a sort by (edges changed, tuple) | **[F]** | `:164-170`; `_undirected_edges` (`:104-108`) builds two frozensets per candidate. Any speed-up must reproduce this order exactly, because best-improvement ties and first-improvement both depend on it (`:219-236`). |
| M25-d | Duplicates never remove a candidate for admitted cuts | **[A] (audit measured n = 6..12)** | Audit `:1374` says the 7 symmetric reconnections are always distinct because admitted cuts give every segment at least 2 nodes, and directed mode always yields exactly one candidate (`S1+S3+S2`). MT6-01 proves it with an exhaustive parity test before relying on it. |
| M25-e | `local_search_numba.ThreeOptLocalSearch` passes a NumPy array into the Python engine | **[F] CONFIRMED** | `local_search_numba.py:782-788` passes `dist_matrix` from `_prepare_numba_inputs` (`:765-769`, `np.ndarray`); `closed_tour_cost` then indexes NumPy scalars in Python loops (`three_opt.py:33-40`). Same in `improve_route_numba` (`local_search_numba.py:1184-1200`, `route.tolist()` but the matrix stays an ndarray). |
| M25-f | Cost on the paper path | **[F] measured** | DECISION_LOG A18 D-04b1 (`:503`): `Core-ThreeOpt-TSP` **965 us per evaluation on kroA100** (other algorithms 14-80 us); Bildiri fixed budget 45.1 h serial, of which ThreeOpt 36.1 h; YAEM 31.0 h (ThreeOpt 17.3 h, GWO/HHO memetic-3opt 4.6 h and 3.7 h); native ThreeOpt 63 s per iteration and memetic-3opt polish 66-68 s per iteration on kroA100. The fixed-budget path uses `improve_three_opt_budgeted` (`objective_budget.py:317-391`, called from `registry_setup.py:290-300` and `composition.py:581`), which uses the same generator (`objective_budget.py:355-356`). |

**Consequence:** M25 is a pure speed-up if the candidate list (content, rotation and order) stays identical. Evaluation counts, routes, costs, iterations and termination reasons are then unchanged on every path, so **M25 changes no academic result** and needs no pooling rule; it changes only wall time (section 5).

### 1.2 H10: the forbidden kernel in the SOTA final polish

| # | Claim | Status | Evidence |
|---|---|---|---|
| H10-a | `ls_engine.improve_3opt` calls the old Numba kernel | **[F] CONFIRMED** | `sota_tsp/ls_engine.py:146-148` (`_nb._three_opt_improve_atsp_numba` when `dm_np` is given) and `:149-150` (`_nb.nb_three_opt` when only the list matrix is given; same kernel, `numba_accel.py:301-305`). |
| H10-b | The kernel is non-canonical | **[F] CONFIRMED** | `numba_accel.py:199-276`: 7 fixed cases from flag arrays `:216-218` (`rev_b`, `rev_c`, `tail_rev`), i.e. `A + B(+-rev) + C(+-rev) + D(+-rev)` only, never a segment exchange; it reverses segments on asymmetric matrices; it admits adjacent cuts (`for k in range(j + 1, ...)`, `:233`). Candidates are fully costed, so tours stay valid; the neighbourhood is not the contract (`CANONICAL_THREE_OPT_DESIGN.md:35`, `:97`). |
| H10-c | There is a third non-canonical branch | **[F] new detail** | Without Numba, `improve_3opt` runs a Python "reverse-middle" neighbourhood (`ls_engine.py:144`, `:151-184`): a different neighbourhood again, so the SOTA 3-opt layer is backend-dependent. |
| H10-d | Only the final polish reaches it | **[F]** | The 3-opt layer exists only for intensity `"full"` (`ls_engine.py:207-210`). In-loop calls use `light`/`moderate` (E2BSO `e2bso_tsp.py:39-40, 284-297`; R2DMA `r2dma_tsp.py:106-108, 379-389`; P-AOEA genomes `paoea_tsp.py:157, 185-186, 202`). `"full"` is used in the final polish of E2BSO (`e2bso_tsp.py:328-331`), E2BSO-CPSO (`:546-549`), R2DMA (`r2dma_tsp.py:438-441`) and P-AOEA (`paoea_tsp.py:298-300`). CGO and RUN use `light` only (`cgo_tsp.py:350, 372`; `run_tsp.py:462-465, 488-491`). |
| H10-e | Reach | **[F]** | Production: `ebso`/`rdma`/`aoea` strategies (`optimizer_api/strategies/__init__.py:210-214, 272-274`) -> `solve_student_order_with_sota_tsp` (`uniride_core/adapters/sota_tsp_strategy_adapter.py:109-132`, `solver.solve_with_matrix`). Academic: `SOTA-E2BSO-TSP`, `SOTA-R2DMA-TSP`, `SOTA-P-AOEA-TSP` executors (`registry_setup.py:556-681`), ungoverned only: protocol mode is refused for every SOTA ID except ALNS (`:571-575`). No study profile lists a SOTA ID (`studies/bildiri2026/study.json:6-17`, `studies/yaem2026/study.json:6-18`). |
| H10-f | Existing tests pin the old behaviour | **[F]** | `academic_benchmark/tests/test_sota_parity.py:6-25` monkeypatches `ls_engine.improve_3opt` with the old signature; `academic_benchmark/tests/test_numba_three_opt.py:16-35` calls `numba_accel.nb_three_opt` directly and is part of the canonical regression command (`CANONICAL_THREE_OPT_DESIGN.md:127`). No test asserts the kernel is unreachable. |

### 1.3 H11: wall-clock stops in SOTA solvers

| # | Claim | Status | Evidence |
|---|---|---|---|
| H11-a | Per-call local-search wall clock | **[F] CONFIRMED** | `MultiLayerLS.improve(..., time_limit=5.0)` (`ls_engine.py:196`), `t0 = time.monotonic()` (`:203`), checked before each layer (`:216`); callers pass `ls_time_limit = 0.5` (E2BSO `e2bso_tsp.py:41, 70`; R2DMA `r2dma_tsp.py:109`; P-AOEA `paoea_tsp.py:91`; CGO `cgo_tsp.py:41`; RUN `run_tsp.py:44`). Whether a layer runs depends on how long the previous layers took. |
| H11-b | Global wall clock and a time-derived final polish budget | **[F] CONFIRMED** | E2BSO `e2bso_tsp.py:240, 321, 325-327` (and CPSO `:451, 540, 543-545`); R2DMA `r2dma_tsp.py:324, 432, 435-437`; P-AOEA `paoea_tsp.py:239, 292, 295-297`; CGO `cgo_tsp.py:272, 295, 299` (`perf_counter`); RUN `run_tsp.py:400, 423, 427`. `time_limit` default 300 s (`e2bso_tsp.py:53`, `r2dma_tsp.py:119`, `paoea_tsp.py:100`, `cgo_tsp.py:43`, `run_tsp.py:46`). |
| H11-c | Production can override the limits per request | **[F]** | `merge_sota_config` copies any config field from `request.sota_config` (`optimizer_api/strategies/sota_config_utils.py:11-26`; `optimizer_api/models/schemas.py:288`). |
| H11-d | ALNS is not affected | **[F]** | `alns_tsp.py:221, 227` only measures elapsed time; ALNS does not import `ls_engine` (Gate C plan `:74`). |
| H11-e | Audit evidence (3 runs: cost 288, 280, 280) | **[A] not re-run** | Audit `:960`; the planner ran no solver. MT6-03's red test reproduces the mechanism deterministically with a fake clock instead. |
| H11-f | Contention is the normal case in production | **[F]** | `/compare` runs solvers in a thread pool (`optimizer_api/routers/optimization.py:4, 604`; the audit cited `:516`, the line moved). |

### 1.4 M14: the production hybrid 3-opt

| # | Claim | Status | Evidence |
|---|---|---|---|
| M14-a | The hybrid default includes a second 3-opt | **[F] CONFIRMED** | `local_search.py:721-731` (default method list ends with `THREE_OPT`), `:799-801` (`ThreeOptLocalSearch(max_iterations=15)`). |
| M14-b | Its cases | **[F] CONFIRMED** | `_three_opt_cases` (`:168-208`): `B'C'`, `B'C`, `BC'`, `BC` (identity), `CB`, `C'B`, `CB'`; `C'B'` is missing; `A = route[:i + 1]` (`:190`) so position 0 never moves. |
| M14-c | More drift than the audit lists | **[F] new detail** | Window bounds differ from the canonical rule (`:231-232`: `j - i` and `k - j` up to `window + 1`, canonical `<= window`, `three_opt.py:82`); routes shorter than 4 fall back to 2-opt under the 3-opt name (`local_search.py:216-219`), which the design forbids (`CANONICAL_THREE_OPT_DESIGN.md:104`); with `first_improvement=False` it replaces `best_route` mid-scan and keeps scanning on the new route (`:236-241`), a running-best rather than a best-improvement pass. |
| M14-d | The audit fix sketch does not fit the production objective | **[F] new, important** | The sketch ("run `improve_three_opt` on `[depot] + route`, rotate back", audit `:1230`) assumes a closed-cycle matrix objective. Production calls the hybrid through `apply_local_search(route, duration_func, ...)` (`local_search.py:863-898`) where `duration_func` is a black box: in `ga_split` it is the Split-decoded chromosome cost (`ga_split_engine.py:205-209`), and the route is an open sequence whose positions matter. Canonical cycle candidates are rotated to the route's first node (`three_opt.py:139, 148, 162`), which is neutral for a cycle but not for a Split chromosome. A path form of the neighbourhood is needed (OQ-MT6-3). |
| M14-e | Reach | **[F]** | `local_search_type: "hybrid"` defaults in `ga_split_strategy.py:66` (API default algorithm), `ga_split_hf_strategy.py:48`, `gwo_split_strategy.py:75`, `hho_split_strategy.py:76`, `pso_split_strategy.py:76`, `pso_strategy.py:48`, `hho_strategy.py:60`; engines `ga_split_engine.py:11`, `meta_split_common.py:9, 71`, `gwo_split_engine.py:186`, `hho_split_engine.py:245`, `pso_split_engine.py:218` import `local_search.py`. `tsp_meta_engines.py:405-408` defaults to `two_opt` [A: whether any academic `Matrix-*-legacy` config selects `hybrid` or `three_opt`; developer checks]. The academic `Numba-Hybrid` path uses `local_search_numba.py`, whose 3-opt is already canonical (`:1192-1200`). |

### 1.5 Observation found while planning (not an audit ID)

| # | Observation | Status | Evidence |
|---|---|---|---|
| N-1 | Budgeted controllers accept with a strict `<`; the design asks for a scale-aware tolerance | **[F] discrepancy** | `CANONICAL_THREE_OPT_DESIGN.md:75` ("Objective comparisons use a scale-aware tolerance"); `improve_three_opt` follows it (`three_opt.py:228`), the budgeted 2-opt/Or-opt/3-opt controllers do not (`objective_budget.py:200, 282, 363`). On integer-valued matrices (every Bildiri/YAEM instance [A: all study instances use integer TSPLIB distances]) the two rules accept the same moves, because any real improvement is >= 1 and the tolerance is < 1 for costs below 10^10. Not relabelled as compliant; OQ-MT6-6. |

---

## 2. MT6 acceptance definition

MT6 is closed when all of the following hold on one recorded commit (MT6-07):

1. No `numba_accel` 3-opt symbol (`_three_opt_improve_atsp_numba`, `nb_three_opt`, `_build_3opt_candidate`) is reachable from any public entry point: production strategies, registry executors, CLI, SOTA solvers (spy test, H10).
2. Canonical candidate parity: the new generator returns exactly the old candidate list (content, rotation, order) for every admitted triple on exhaustive small cases and seeded larger ones; full-run parity of `improve_three_opt` and `improve_three_opt_budgeted` (route, cost, iterations, evaluations, termination reason) on fixed seeds (M25).
3. Same seed, same configuration -> identical route and cost for every SOTA solver under a fake clock that advances arbitrarily, and across 5 real runs under induced CPU load (H11).
4. The production hybrid's 3-opt step is the core-owned neighbourhood chosen in OQ-MT6-3, with an independent reference enumerator test; `_three_opt_cases` is deleted (M14).
5. The canonical regression command plus every new MT6 test module pass; `uniride_core/tests`, `academic_benchmark/tests` and `optimizer_api/tests` (`-m "not requires_ampl"`) pass with counts recorded in A19; `test_production_registry_snapshot.py` unchanged.
6. Appendix J rows for H10, H11, M14, M25 are FIXED with branch, red/green commits and test names; DECISION_LOG A19 records the owner approvals, the no-pooling statements and the re-measured D-04b1 rows (MT6-06).

---

## 3. Work items

Model and review guidance (CLAUDE.md): developer Sonnet for every code item. Reviewer **Opus** for MT6-01, MT6-02, MT6-03 and MT6-04 (core neighbourhood, result-changing, production behaviour: high risk); Sonnet for MT6-05 and MT6-07 (fact-check of the close record). MT6-06 is a lead run. Suggested tool-call ceiling per item: about 15-25 (requested, not enforced).

### MT6-01: Canonical 3-opt speed-up with candidate parity (M25)

- [ ] **Goal:** the same candidates in the same order, produced without per-candidate cycle keys or full `C(n,3)` scans.
- **Change (core, `uniride_core/algorithms/three_opt.py`):** (1) `iter_three_opt_cuts` generates `i`, then `j` in `[i+2, i+w]`, then `k` in `[j+2, j+w]`, keeping `n - k + i >= 2` and the current lexicographic order; `window=None` keeps the full enumeration. (2) Symmetric mode emits the 7 non-identity reconnections from a fixed (order, reversal) table, rotated to the anchor exactly as now, and keeps the existing sort key (`:164-170`) unless the parity test proves a precomputed order equal. (3) Directed mode emits `S1+S3+S2` directly, rotated to the anchor. (4) Keep full closed-cycle costing (`closed_tour_cost`) and the evaluation definition; no delta evaluation. (5) `local_search_numba.py:782-788` and `:1184-1200` pass `dist_matrix.tolist()` (values identical, float64 -> Python float). Keep the old generator as a private test fixture copy in the test module, not in production code.
- **Files:** `uniride_core/algorithms/three_opt.py`, `uniride_core/algorithms/local_search_numba.py`; tests `uniride_core/tests/test_three_opt_candidate_parity.py` (new), added to the regression command in `CANONICAL_THREE_OPT_DESIGN.md:124-128`.
- **Red test first (deterministic, no timing):** (a) `generate_three_opt_candidates` must not call `_symmetric_cycle_key`/`_directed_cycle_key` per candidate (monkeypatch them to count calls; red: 48 resp. 6 calls per triple); (b) `iter_three_opt_cuts(n, window)` must not call `itertools.combinations` when `window` is set (monkeypatch the module name; red today); (c) parity against the frozen old generator for every admitted triple, n = 6..14, windows `None, 2, 3, 12`, symmetric and asymmetric random integer and float matrices, and seeded routes at n = 30 and 60 (green today and after: guards the refactor); (d) full-run parity of `improve_three_opt` and `improve_three_opt_budgeted` (best and first improvement; budget binding and not binding) on seeded n = 30 symmetric, n = 30 asymmetric and an in-memory ft53-like asymmetric matrix.
- **Timing (planning number only, after the running calibration finished):** one 3-opt pass on kroA100, window 12, before and after, one replicate each, recorded in the report; not a test.
- **Acceptance:** red (a), (b) green; (c), (d) green; regression command and `uniride_core/tests` + `academic_benchmark/tests` green; revert check: undoing the source change makes (a) and (b) red again.
- **Closes:** M25. **Depends on:** nothing. **Risk:** high (dominant algorithm of the paper; an order slip silently changes results). **Changes academic results:** **no** by construction (parity); only wall time changes (section 5). **Reviewer:** Opus (runs the parity tests itself and mutates the order table in a throwaway worktree to see (c) fail).

### MT6-02: SOTA final polish uses the canonical 3-opt (H10; lands with MT6-01)

- [ ] **Goal:** every branch of `ls_engine.improve_3opt` calls `improve_three_opt` (directed mode auto-detected from the matrix); the Numba kernel and the Python reverse-middle fallback are no longer reachable from public entry points.
- **Change:** `sota_tsp/ls_engine.py:142-184` becomes a thin call `improve_three_opt(tour, dm, max_iterations=..., window=...)` on the list matrix (`dm`), ignoring `dm_np`; returns `(res.route, float(res.cost))`. SOTA tours are full permutations of `0..n-1` (`e2bso_tsp.py:134-137`) [A: the developer checks R2DMA and P-AOEA tour builders and `solve_with_matrix` too, since `improve_three_opt` validates the permutation, `three_opt.py:174-181`]. Kernel fate per OQ-MT6-1 (recommended: keep the kernel file, mark `nb_three_opt` non-canonical in its docstring, add the reachability spy).
- **Files:** `uniride_core/algorithms/sota_tsp/ls_engine.py`; tests `uniride_core/tests/test_mt6_no_forbidden_three_opt.py` (new, added to the regression command), `academic_benchmark/tests/test_sota_parity.py` (fake signature unchanged; it already matches), `academic_benchmark/tests/test_numba_three_opt.py` per OQ-MT6-1.
- **Red test first:** (a) spy: monkeypatch `numba_accel._three_opt_improve_atsp_numba`, `numba_accel.nb_three_opt` and `numba_accel._build_3opt_candidate` to raise, then run `E2BSO_TSP`, `E2BSO_TSP_CPSO`, `R2DMA_TSP`, `PAOEA_TSP` (`solve_with_matrix`, tiny configs, n = 12 asymmetric), the three production strategies through `solve_student_order_with_sota_tsp`, and the `SOTA-*` registry executors; red today; (b) the 3-opt layer result equals `improve_three_opt` on the same input for a symmetric and an asymmetric matrix (red today on the asymmetric one); (c) same with Numba unavailable (monkeypatch `_NUMBA_OK = False`): no reverse-middle fallback.
- **Acceptance:** red tests green; regression command, `uniride_core/tests/test_sota_tsp_strategy_adapter.py`, `optimizer_api/tests/test_sota_adapter_truth.py` and the routing-refusal tests green; revert check makes (a) red.
- **Closes:** H10. **Depends on:** MT6-01 (branch from its head; merged in the same lead session right after MT6-01, owner Q4 "land together"); OQ-MT6-1, OQ-MT6-5. **Risk:** high (changes production `ebso`/`rdma`/`aoea` routes and runtime). **Changes results:** **yes**, SOTA-E2BSO/R2DMA/P-AOEA (academic, ungoverned) and production `ebso`/`rdma`/`aoea`. No pooling of pre- and post-MT6-02 SOTA rows (A14 rule); stored route plans keep their solver provenance (S08) [A: whether S08 provenance carries the code commit; the developer checks and says so in the report]. **Reviewer:** Opus.

### MT6-03: Deterministic SOTA termination (H11)

- [ ] **Goal:** a SOTA result depends only on seed and configuration; wall clock is at most an optional, reported safety deadline.
- **Change (per OQ-MT6-2, recommended option a):** (1) `MultiLayerLS.improve` drops the per-layer clock check (`ls_engine.py:203, 216`); its work is bounded by the existing `max_ls_pass_iterations = 5` (`:212`) and each layer's `max_iterations`; it keeps measuring elapsed time for `stats`. (2) Each solver's main loop stops on `max_iterations` (and existing stagnation rules) only; `time_limit`/`ls_time_limit` become `deadline_seconds: Optional[float] = None`; when set and reached, the solver stops, sets `termination_reason = "wall_clock_deadline"` and `reproducible = False` in the result metadata [A: the developer picks the field on `TSPResult`/`params` without breaking `RunResult`]. (3) The final polish always runs with its iteration limit (no `final_ls_budget = min(ls_time_limit, remaining)`). (4) Files: E2BSO and CPSO, R2DMA, P-AOEA, CGO, RUN (section 1.3 lines). (5) `merge_sota_config` keeps accepting the old keys `time_limit`/`ls_time_limit` for one release and maps them per OQ-MT6-2 [O], or refuses them with a clear 422 [O].
- **Files:** `uniride_core/algorithms/sota_tsp/{ls_engine,e2bso_tsp,r2dma_tsp,paoea_tsp,cgo_tsp,run_tsp}.py`, `optimizer_api/strategies/sota_config_utils.py` (only if OQ-MT6-2 maps keys); tests `uniride_core/tests/test_mt6_sota_deterministic_stop.py` (new).
- **Red test first:** for each of the six solvers, a fake clock (monkeypatch the module's `time.monotonic`/`time.perf_counter` to advance 10 s per call) and the real clock give identical tour and cost for the same seed and config (red today: layers and iterations are skipped); a set deadline that is hit yields `termination_reason == "wall_clock_deadline"` and `reproducible is False`; no deadline -> no clock-dependent branch (AST/grep test: no `time.monotonic() - t` comparison outside the optional deadline helper).
- **Latency check (planning number, after calibration finished):** the three production SOTA strategies on the Dudullu demo request sizes (in-memory, one replicate each, old vs new), recorded for OQ-MT6-2; not a test.
- **Acceptance:** red tests green; audit acceptance (5 runs under induced CPU load, identical) recorded in the report; production adapter tests green.
- **Closes:** H11. **Depends on:** MT6-02 (same files; serial), OQ-MT6-2, OQ-MT6-5. **Risk:** high (production latency; every SOTA result changes). **Changes results:** **yes**, all SOTA-* (academic, ungoverned) and production `ebso`/`rdma`/`aoea`; no pooling with pre-MT6-03 rows. **Reviewer:** Opus.

### MT6-04: Production hybrid 3-opt through a core-owned neighbourhood (M14)

- [ ] **Goal:** the hybrid's 3-opt step uses a core-owned, independently tested neighbourhood with a truthful name; `_three_opt_cases` is deleted.
- **Change (per OQ-MT6-3, recommended option b):** add to `three_opt.py` a path neighbourhood for open sequences costed by a caller's black-box objective: cuts `-1 <= i < j < k <= n-1` with `B = route[i+1:j+1]`, `C = route[j+1:k+1]` non-empty, `A`/`D` fixed (an empty `A` lets the first position move, closing the "depot arc never cut" gap); candidates = the 7 non-identity arrangements of `(B, C)` order x reversal (`C'B'` included), deduplicated by sequence equality (a 1-node segment makes `B' = B`), fixed deterministic order; windows by the canonical rule (`j - i <= w`, `k - j <= w`). `ThreeOptLocalSearch.improve` (`local_search.py:210-252`) delegates to it with the existing acceptance semantics made explicit (true best-improvement per pass, OQ-MT6-3 note), drops the `< 4` 2-opt fallback (returns the route unchanged, as the design asks), and the hybrid keeps `max_iterations = 15` and `window = 12`. Option a would instead use `reversals=False` (only `A C B D`) on asymmetric travel times.
- **Files:** `uniride_core/algorithms/three_opt.py`, `uniride_core/algorithms/local_search.py`; `CANONICAL_THREE_OPT_DESIGN.md` new subsection "Path neighbourhood for production local search" (design addition -> A19); tests `uniride_core/tests/test_mt6_path_three_opt.py` (new: independent brute-force enumerator that does not import the generator, per design `:109`), additions to `uniride_core/tests/test_local_search_core.py`.
- **Red test first:** `C'B'` is generated; the first position can move; no duplicate candidates for 1-node segments; `ThreeOptLocalSearch` on a 5-node route does not run 2-opt; window bound equals the canonical rule; best-improvement pass returns the reference best move on small cases (all red today).
- **Replay check (planning number, before the owner approves the merge):** the API default `ga_split` and `hho_strategy` on N archived Dudullu daily requests (in-memory, fixed seed, old vs new: vehicles, total duration, runtime), N chosen by the lead [O: OQ-MT6-3]; not evidence, shown to the owner.
- **Acceptance:** red tests green; `uniride_core/tests`, `optimizer_api/tests` green, including certifier tests; revert check.
- **Closes:** M14. **Depends on:** OQ-MT6-3, OQ-MT6-5; MT6-01 merged first (both edit `three_opt.py`). Can be developed in parallel with MT6-02/03 (different files). **Risk:** high (production default algorithm). **Changes results:** **yes**, production `ga_split` (API default), `ga_split_hf`, `gwo/hho/pso_split`, `pso_strategy`, `hho_strategy`; academic only if a `Matrix-*-legacy` configuration selects `hybrid`/`three_opt` [A]. No pooling of production benchmark rows across the change. **Reviewer:** Opus.

### MT6-05: Acceptance tolerance in the budgeted controllers (N-1; only if OQ-MT6-6 = b)

- [ ] **Goal:** budgeted 2-opt/Or-opt/3-opt accept with the design's scale-aware tolerance, like `improve_three_opt`.
- **Files:** `uniride_core/algorithms/objective_budget.py:200, 282, 363`; test `uniride_core/tests/test_mt6_budgeted_tolerance.py`.
- **Red test first:** a float matrix where a candidate improves by less than the tolerance is not accepted (red today); every Bildiri/YAEM study instance (in-memory from the committed `.tsp` files, smoke slice) gives identical fixed-budget results before and after (green both).
- **Closes:** N-1. **Depends on:** MT6-01. **Risk:** medium. **Changes results:** none on integer instances (proved by the test); possible on float matrices (pilot rows on float matrices not pooled). **Reviewer:** Sonnet.

### MT6-06: Re-measure the 3-opt rows of the D-04b1 table (lead run)

- [ ] After MT6-01 is merged and no other timing run is active: re-run the D-04b1 calibration slice (`academic_benchmark/studies/estimate.py`, A18 `:501`) for `Core-ThreeOpt-TSP` and `Core-GWO/HHO-TSP-Memetic-3opt` on the same machine; record per-evaluation and per-iteration times and the new study totals in A19 as planning numbers. Evaluation upper bounds must be unchanged (parity). This replaces the 3-opt rows of D-04b1 as input to OQ-4 and D-04b2 (OQ-MT6-4).

### MT6-07: Close MT6

- [ ] Run the acceptance checks of section 2 on one clean `WIP` commit; update Appendix J (split M14 and M25 out of `:2350`); A19 note with test counts; update the MT6 status where documents name it as a paper-run precondition (`docs/UNIRIDE_WORKSTATE.md`, `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, `README.md`, `UniRide_Ultimate_Audit.md`, without changing the Gate D status phrase checked by `academic_benchmark/tests/test_gate_d_docs_consistency.py:118-121`); DURUM.md. **Reviewer:** Sonnet fact-check of the close record.

---

## 4. Lanes and order

```text
Owner answers first:   OQ-MT6-1 .. OQ-MT6-7 (section 6)
Lane A (core + SOTA, serial; H10 and M25 land together):
    MT6-01 M25 speed-up (branch fix/mt6-01-three-opt-speedup from WIP)
      -> MT6-02 H10 (branch fix/mt6-02-sota-canonical-3opt from the MT6-01 head)
         lead merges MT6-01 then MT6-02 in one session, no other merge in between
      -> MT6-03 H11 (branch from WIP after that merge)
Lane B (production):   MT6-04 M14 (develop in parallel with MT6-02/03; rebase on WIP after MT6-01 is merged;
                        merge only after the replay numbers were shown to the owner)
Lane C (optional):     MT6-05 tolerance (after MT6-01; only if OQ-MT6-6 = b)
Lead:                  MT6-06 re-measure (after MT6-01 merged, calibration idle)
                        -> OQ-4 second measurement and D-04b2 (Gate D) use the post-MT6 code
Close:                 MT6-07 after every item merged
```

Why this order: M25 alone changes no result and removes the runtime growth H10 would otherwise cause (audit `:945`), so it goes first; H10 then swaps the kernel for the now-fast canonical engine; H11 touches the same SOTA files and goes after H10 to avoid conflicts; M14 is independent except for `three_opt.py`.

---

## 5. Impact on the study profiles and on the D-04b1 cost table

| Item | Bildiri profile | YAEM profile | D-04b1 table |
|---|---|---|---|
| MT6-01 (M25) | `Core-ThreeOpt-TSP`: identical results, faster | `Core-ThreeOpt-TSP`, `Core-GWO/HHO-TSP-Memetic-3opt` (3-opt polish via `composition.py:581`): identical results, faster | **Yes.** Per-evaluation time of the 3-opt rows drops; evaluation upper bounds unchanged. The 965 us/evaluation (36.1 h of 45.1 h Bildiri; 17.3 h + 4.6 h + 3.7 h of 31.0 h YAEM) is dominated by key building, not costing (audit cProfile at n = 50: 16.9 s of 25.5 s in `_symmetric_cycle_key`, `:1366`). Expected order of magnitude: costing one candidate is O(n), so [A] tens of microseconds per evaluation at n = 100; the real figure comes from MT6-01's one-pass timing and MT6-06. The native ThreeOpt 63 s/iteration falls by the same factor, which matters for the OQ-4 second measurement (3-opt runs capped at about 1 h, A18 `:504`). |
| MT6-02 (H10) | none (no SOTA ID) | none | none |
| MT6-03 (H11) | none | none | none |
| MT6-04 (M14) | none (`local_search.py` is not on the profile paths [F] section 1.4) | none | none |
| MT6-05 (N-1) | none on integer instances | none on integer instances | none |

Paper consequence: no paper-scale run exists yet (A18 `:508`), so no stored paper evidence is invalidated; OQ-10 (one campaign = one clean commit) already forbids pooling across commits. The D-04b2 final estimate on the stronger PC must run on a commit that contains MT6-01.

---

## 6. Owner questions

No developer or lead chooses these. Each answer is recorded in DECISION_LOG A19.

| # | Question | Options | Recommendation | Pros / cons |
|---|---|---|---|---|
| OQ-MT6-1 | H10: what replaces the SOTA final-polish 3-opt, and what happens to the old kernel | a) canonical `improve_three_opt` (directed mode on asymmetric matrices), kernel kept but unreachable and marked non-canonical (design `:35`, `:97`); b) as a) but delete the kernel, `nb_three_opt` and their test; c) drop the 3-opt layer from SOTA `"full"` (2-opt, Or-opt, swap only) | a) | a: matches the design wording and the audit sketch; old kernel stays available for a future JIT parity task. b: less dead code; loses that option, edits a regression-command test. c: cheapest, but changes the SOTA algorithms' published structure (3-opt layer) more than needed |
| OQ-MT6-2 | H11: stop rule and production deadline | a) iteration/pass limits only; optional `deadline_seconds` (default `None` in academic runs; production default set by the owner from the MT6-03 latency check), a hit deadline is reported (`wall_clock_deadline`, `reproducible: false`); old request keys `time_limit`/`ls_time_limit` mapped to the deadline for one release; b) as a) but no production deadline at all; c) keep wall clock, label every SOTA result non-reproducible | a) | a: reproducible by default, latency still bounded in production and visibly labelled when it binds. b: fully reproducible; a large request could run long (H7, no global solver cap, is still open). c: no code risk, but keeps the defect H11 names |
| OQ-MT6-3 | M14: neighbourhood of the production hybrid 3-opt step (objective is a black box over an open sequence, section 1.4 M14-d) | a) strict canonical directed semantics on asymmetric travel times: only `A C B D`, no reversals; b) core-owned **path 3-opt**: all 7 `(B, C)` arrangements with reversals, fully costed by the caller's objective, `C'B'` and the first position included, canonical window, truthful name in docs ("path 3-opt, reversals fully costed"); c) remove 3-opt from the hybrid default; d) keep the code, rename and document it as non-canonical (no result change) | b), merged only after the MT6-04 replay numbers are shown | a: closest to the academic contract; production 2-opt already reverses on asymmetric matrices, so a reversal-free 3-opt adds little beyond Or-opt and may lower quality. b: complete, tested neighbourhood; every candidate is exactly costed so reversals are valid tours; it is a declared production operator, never used for paper claims. c: simplest, removes the drift; weaker search. d: zero risk, but the audit's "missing case, depot arc never cut" stays |
| OQ-MT6-4 | Order relative to Gate D measurements | a) MT6-01 merged and MT6-06 done before the OQ-4 second measurement and before D-04b2; b) run the OQ-4 measurement now and MT6 later | a) | a: OQ-4 limits and the final estimate are measured on the code that will run; the 1 h cap truncates fewer native 3-opt runs. b: no wait, but the numbers are stale after MT6-01 |
| OQ-MT6-5 | Approval of result changes (A14 style) | a) approve H10, H11 and M14 knowing they change SOTA (academic, ungoverned) and production results; no pooling of pre- and post-change rows; production responses keep solver provenance; b) approve H10/H11 only, M14 later; c) approve none (M25 only) | a) | a: closes all four findings before any paper-scale run (Q4). b: production default unchanged for now. c: paper path unaffected either way (no SOTA or `local_search.py` in profiles), but H10/H11 stay open |
| OQ-MT6-6 | N-1: strict `<` in budgeted controllers vs the design's tolerance | a) record the discrepancy, change nothing (identical on integer instances); b) MT6-05: align the code to the design; c) amend the design to strict comparison for budgeted controllers | b) | a: no work; contract and code keep disagreeing. b: contract honoured, proven no-op on study instances; small risk on float pilots. c: no code change, but the design then has two rules |
| OQ-MT6-7 | The rest of audit roadmap row MT6 (`:1562`): archive `sota_common`, remove shims, L3, L10; and `run_tsp._apply_3opt_bounded` (perturbation with two identical cases, audit `:1601`) | a) out of MT6, one follow-up plan after MT6; b) add to MT6 now | a) | a: keeps MT6 to the four findings Q4 named and the paper precondition short. b: one pass over the area; longer before paper runs |

---

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The speed-up changes candidate order and silently changes Core-ThreeOpt results | Frozen-copy parity test (exhaustive small n, seeded larger n), full-run parity of both controllers, Opus reviewer mutates the table to prove the test bites |
| H10 makes SOTA polish much slower | H10 branches from the MT6-01 head and merges right after it (Q4) |
| Removing wall-clock stops raises production latency | Pass limits stay; optional reported deadline (OQ-MT6-2); latency check before merge |
| Path 3-opt changes the production default algorithm's plans | Replay numbers shown to the owner before merge; certifier tests; A14-style no pooling |
| Old tests pin removed behaviour (`test_numba_three_opt.py`, `test_sota_parity.py`) | Handled explicitly in MT6-02 per OQ-MT6-1; regression command updated in the design by the same item |
| Timing numbers taken while another timing run is active | Global constraint: no timing while another runs; numbers are planning only |
| Agents slip into interactive Python | Python rule at the top of every brief |

---

## 8. Out of scope / later

| Item | Reason |
|---|---|
| Making SOTA solvers governed (exact evaluation accounting, fixed-budget/native protocol) | Not an MT6 finding; they stay refused (`registry_setup.py:571-575`) |
| Backend-dependent 2-opt/Or-opt/swap layers in `ls_engine` (Numba kernel vs Python fallback semantics differ, `ls_engine.py:47-139`) | Observation only; follow-up with OQ-MT6-7 |
| `sota_common` archive, shims, L3, L10, `run_tsp._apply_3opt_bounded` | OQ-MT6-7 recommendation a) |
| JIT acceleration of canonical 3-opt | Design non-goal until a JIT parity task (`CANONICAL_THREE_OPT_DESIGN.md:138`) |
| Delta evaluation for 3-opt | Would change the evaluation definition (`ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md:49`) and float summation; needs its own design decision |
| H7 (global solver cap) | Separate finding (MT3) |

---

## 9. Confirmed facts vs assumptions (summary)

- **Confirmed [F]:** M25-a/b/c/e/f, H10-a/b/c/d/e/f, H11-a/b/c/d/f (mechanism), M14-a/b/c/d/e, N-1 (discrepancy); no study profile contains a SOTA ID or uses `local_search.py`; SOTA IDs are refused in protocol mode.
- **Assumptions [A]:** M25-d (no duplicates for admitted cuts; MT6-01 proves it), the size of the speed-up, the audit's 288/280/280 demo (not re-run), whether S08 provenance carries the code commit, whether any `Matrix-*-legacy` configuration selects `hybrid`, that every study instance is integer-valued (MT6-05 test checks it).
