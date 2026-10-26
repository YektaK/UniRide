# Gate C: Catalog, Composition and Experiment Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan item by item. Steps use checkbox (`- [ ]`) syntax. **Owner decisions recorded 2026-10-19; implementation starts after the lead merges this plan.** This includes the three points raised by the GA/PSO investigation (section 4.2).

**Goal:** Close unification Package C ("catalog, composition, and experiment services", `ACADEMIC_STUDY_UNIFICATION_DESIGN.md:441-449`) so that Gate C ("all capability, accounting, hybrid-boundary, TSP/ATSP, schema, and smoke-pilot tests pass", `:449`) can be declared on recorded evidence.

**Architecture:** Canonical algorithms, the shared objective-evaluation counter and the two-stage composition live in `uniride_core` (design `:47-56`). Academic adapters, study loading, plan expansion, smoke execution, result validation and protocol separation live in `academic_benchmark` (design `:64-75`). Study profiles stay thin JSON (`:77-87`). Production exposure does not change (`:89-93`, `:133`).

**Tech stack (observed in this run):** `.venv-jit` interpreter (Numba JIT available), pytest, Pydantic strict contracts, the immutable capability catalog in `uniride_core/algorithms/capabilities.py`.

**Base:** branch `WIP`, HEAD `559826b5` (2026-10-19). Plan written in worktree `.claude/worktrees/gate-c-plan` on branch `docs/gate-c-plan`.

## Global constraints (every brief that implements an item repeats these)

- **Python on Windows (top of every brief):** never open interactive Python (no bare `python`/`py`, no `python -i`, no `python -` or heredoc). Write scripts to a file under `C:\wt\<name>` and run them with `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`, with `PYTHONPATH` set to the worktree (the editable install points at the main checkout). Use `-c` only for one-liners. Time-limit every command and redirect output to a file. Stop on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only your own PIDs. Temp folders only under `C:\wt\<name>`.
- Never write, copy or delete `academic_benchmark/tsplib_data/tsplib.db*`. Never run AMPL. No download of instance files.
- Each item runs in its own worktree and branch (`git worktree add <path> -b <branch> WIP`), red test first, frequent commits, no merge, no push. The lead merges with `--no-ff` after the reviewer's ONAY and passing tests.
- No benchmark runs beyond the tiny smoke cases named in an item. Smoke outputs go to `tmp_path` or `C:\wt\<name>`, never into the repository. Smoke results produce no superiority, causality or proof claims (AGENTS.md).
- Do not change production strategy exposure (`academic_benchmark/tests/test_production_registry_snapshot.py`) or `ExecutionProtocol` in core (DECISION_LOG E12).
- Do not reopen decided questions: A01 (B-GA/B-PSO get migration guidance, not aliases), A04 (fixed budget primary, native separate), A11 (algorithm IDs unchanged by label work), A13 (historical results labelled, never pooled), A14 (no pooling across result-changing fixes), A16 (benchmark router gate), E12 (academic-layer protocol registry; Package D calls `protocol_registry.assert_single_pooling_group`), and the 2026-10-19 decisions in section 4.
- Archived code (`archive/academic_benchmark/*_legacy/`) is `REFERENCE_ONLY`: it may be read as design history, never imported or executed (QUARANTINE.md).
- Each merged item updates the audit tracker (Appendix J of `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md`) for the IDs it closes, and records decisions in `docs/DECISION_LOG.md`. The lead records the 2026-10-19 owner decisions of section 4 in DECISION_LOG when this plan is merged.

---

## 1. Current state (verified against live code at `559826b5`)

Status key: **DONE** = implemented and evidenced by a passing test in this run's baseline; **PARTIAL** = some of the deliverable exists; **OPEN** = absent.

### 1.1 Package C deliverables (design `:441-447`)

| # | Deliverable | Status | Evidence (file:line or test) | Delivered by |
|---|---|---|---|---|
| D1 | Canonical-ID/capability table (design `:116-131`) exists as an immutable, evidence-gated catalog | **DONE** (structure) | `uniride_core/algorithms/capabilities.py:99-126` (`build_capability_catalog`), `:244-279`; tests `test_algorithm_capability_catalog.py`, `test_canonical_registry_identity.py` | C1 (`2026-07-28` plan, closed 2026-07-29, `2026-07-29-c1-final-review-fixes.md`) |
| D1a | 2-opt, 3-opt: VERIFIED, TSP+ATSP, fixed+native, Python objective | **DONE** | `capabilities.py:245-260`; `test_algorithm_capability_evidence.py`, `test_native_termination_protocol.py` | C1 |
| D1b | Or-opt: VERIFIED, fixed+native | **DONE** | `capabilities.py:317-332` (replacement of the CANDIDATE row at `:261`); `test_or_opt_c2_evidence.py` | C2 (`29095fd`) |
| D1c | ALNS-TSP: VERIFIED, 4 claims, Python, no polish | **DONE** | `capabilities.py:200-241, 268-274`; `test_alns_c3_evidence.py` | C3 (`a3531ee` and Aug-3 commits) |
| D1d | GWO/HHO Pure: VERIFIED, fixed+native, Numba objective | **DONE** | `capabilities.py:264-265`; `test_algorithm_capability_evidence.py:414-417` | C1 |
| D1e | GWO/HHO Memetic-2opt: fixed claims only | **PARTIAL** | `capabilities.py:266-267` pass `native_evidence=None`; the design table `:125-126` says Native = yes; outside fair mode the 2-opt polish runs a Numba kernel whose candidate evaluations are not counted (`gwo_solver.py:126-140`) | C1 |
| D1f | GA, PSO: exact-fixed + native | **OPEN** (CANDIDATE), **required before Gate C** (owner 2026-10-19) | `capabilities.py:262-263`. Three GA/PSO implementations exist and none has budget plumbing (section 1.4) | none |
| D1h | Memetic GA `Core-GA-TSP-Memetic-2opt` (design addition, owner 2026-10-19; not in the table `:116-131`) | **OPEN** (no catalog entry) | Represents the paper's GA (section 1.4, G3) under the counted memetic contract | none |
| D1g | `production_ready` field | **PARTIAL** | Academic field forced `False` (`capabilities.py:77, 110-111`); no production gate (audit M15, out of scope) | C1 (academic half) |
| D2 | Truthful GWO-3opt / HHO-3opt compositions | **OPEN** | `capabilities.py:275-276` PLANNED; `CompositionKind` (`:44-48`) has no 3-opt or ALNS composition kind; no executor (`grep global_fraction|composite_complete` finds no implementation) | none |
| D2a | GWO-ALNS / HHO-ALNS compositions | **OPEN** | `capabilities.py:277-278` PLANNED | none |
| D3 | Shared budget across stages | **PARTIAL** | Counter exists (`uniride_core/algorithms/objective_budget.py:16-37`); budgeted 3-opt counts its start tour (`academic_benchmark/fairness.py:382-401`) but lives in the academic layer; GWO/HHO build a private counter and reset it on each solve (`gwo_solver.py:73, 153`; `hho_solver.py:83, 223`), so a counter cannot be shared across stages yet; ALNS has an accounted core path that always starts from nearest neighbour (`alns_tsp.py:86-93, 198-211`) | C1-C3 (single-stage) |
| D4 | Result contract and post-run validation | **PARTIAL** | Gateway: `academic_benchmark/core/execution_gateway.py:217-219` (resolve, preflight, execute, validate); fair manifest validation `fairness.py:256`; independent Hamiltonian validator `test_hamiltonian_cycle_validator.py` (WP-E8). Gap: governed CLI/Smart runs never get a manifest (audit H13, `execution_gateway.py:218`); no stage-level (composite) result contract | C1, WP-E8 |
| D5 | Study loading | **PARTIAL** | Schema and strict contract: `academic_benchmark/contracts/study.py:17-26, 58-101`, `academic_benchmark/schemas/study-v1.schema.json`. It rejects CANDIDATE/PLANNED IDs, but it does not check problem families, protocols or backends against claims, does not load dataset manifests, and no code loads or executes a study profile (only contracts and tests import `StudyManifestV1`) | Package A, C1 |
| D6 | Fixed/native separation | **PARTIAL** | Separate manifests and pilots (`fair_pilot.py:41-55`, `native_pilot.py:47-80`); protocol registry with pooling groups (`academic_benchmark/protocol_registry.py:33-60, 96-104`; `test_protocol_registry_pooling.py`). Budget levels are not a pooling key (left to Package D, E12) | WP-E8 (registry), earlier pilots |
| D7 | YAEM active study profile | **OPEN** | `academic_benchmark/studies/` contains only `bildiri2026/study.json`; the only dataset manifest is `academic_benchmark/datasets/ft53.json` | none |
| D8 | Active Bildiri profile matches the paper | **OPEN** | The paper (Göbeklitepe; `archive/academic_benchmark/bildiri2026_legacy/bildiri2026/Bildiri.md:9-11`) compares 2-opt, 3-opt, Or-opt, GA and PSO on TSPLIB with 30 independent runs each; the legacy configs list GA and PSO (for example `archive/academic_benchmark/bildiri2026_legacy/bildiri2026/configs/batch_berlin52.json`). The active `academic_benchmark/studies/bildiri2026/study.json:6-11` lists only GWO/HHO Pure and Memetic-2opt on ATSP `ft53` | none |

### 1.2 Gate C test categories (design `:449`)

| Category | Status | Existing tests (baseline: section 2, "Baseline measured") | Gap |
|---|---|---|---|
| Capability | **PARTIAL** | `test_algorithm_capability_catalog.py`, `test_algorithm_capability_evidence.py`, `test_algorithm_resolution.py`, `test_algorithm_preflight.py`, `test_algorithm_preflight_boundaries.py`, `test_canonical_registry_identity.py`, `test_production_registry_snapshot.py` | No conformance test against the normative table `:116-131`; four PLANNED, two CANDIDATE, two missing native claims |
| Accounting | **PARTIAL** | `test_objective_budget_ownership.py`, `test_fair_comparison_protocol.py`, `test_fair_comparison_scientific_integrity.py`, `test_fair_protocol_v2_metadata.py`, `test_cx04_fair_manifest_validation.py` | No shared-counter test across two stages; no GA/PSO accounting |
| Hybrid boundary | **OPEN** | none | Design `:386-391`: one below, exactly at, one above an atomic phase; shared counter; fixed and native never aggregated |
| TSP/ATSP | **DONE** for single-stage VERIFIED algorithms | `test_canonical_three_opt_integration.py`, `test_core_tsp_registry.py`, `test_numba_three_opt.py`, `test_numba_registry_matrix.py`, `test_hamiltonian_cycle_validator.py`, `test_seed_atsp_collection.py`, `uniride_core/tests/test_canonical_three_opt.py` | Hybrids, GA and PSO need the same TSP/ATSP evidence |
| Schema | **DONE** for v1 | `test_manifest_contracts.py`, `test_bildiri_study_profile.py`, `python -m academic_benchmark.contracts.export_schemas check` | Composite result fields, a YAEM profile, the revised Bildiri profile and new dataset manifests are not covered |
| Smoke pilot | **PARTIAL** | `test_fair_pilot_cli.py`, `test_run_smoke_benchmark.py`, `test_sqlite_matrix_native_smoke.py`, `test_seed_smoke_datasets.py`, `test_mutation_proof_gateway.py` | No study-profile-driven smoke; no hybrid, GA or PSO smoke |

### 1.3 Open audit findings in Package C scope (re-verified)

| ID | Live state | Package C? |
|---|---|---|
| H13 | Gateway calls `executor(problem, params, seed, run_idx)` without a manifest (`execution_gateway.py:217-218`); seeds `42 + run_idx` (`smart_benchmark.py:666`), `1000 + combo_idx*100 + run_idx` (`cli_engine.py:820, 962`) | **Yes** (C-03) |
| M19 | `polish_policy` is set from the `polish_enabled` boolean, not from executed polish (`registry_setup.py:778-782`); Bildiri profile sets `polish_iters: 0, final_polish_iters: 0` for both memetic IDs (`studies/bildiri2026/study.json:14, 16`) | **Yes** (C-04) |
| L8 | Local-search executor derives termination from counters, not `search.termination_reason` (`registry_setup.py:222-227`) although the budgeted results carry one (`objective_budget.py:58, 85, 117`) | **Yes** (C-02) |
| M17 | No `archive/__init__.py`; generic markers lack `archive.` (`uniride_core/tests/test_archive_boundaries.py:8-13`) | **Yes** (C-01; WP-E8 residual) |
| H9 | `engine_factory.py:29-33` maps `Core-TwoOpt-TSP`, `Core-GWO-TSP`, `Core-HHO-TSP`, `Core-GA-TSP`, `Core-PSO-TSP` to matrix engines; `engine_core.py:181-185` overwrites duplicates silently; `registry_setup.py:789-833` keeps old executors silently when the Numba import fails. GA/PSO add a third case: `Numba-GA`/`Numba-PSO` are registered to a different implementation (`registry_setup.py:452-455` → `numba_metaheuristics.py`) while the resolver treats `Numba-GA` as an alias of `Core-GA-TSP` (`algorithm_resolution.py:48`) | **Yes** (C-14, Q10 decided) |
| L9 (part) | `make_deterministic_seed` hashes the algorithm name (`benchmark_utils.py:672-678`); pilots use `pstdev` (`fair_pilot.py:486`, `native_pilot.py:428`); non-fair GWO/HHO counts exclude the Numba 2-opt polish (`gwo_solver.py:126-140`). The global `random.seed` items are gone (H12 fix: `registry_setup.py:408`, `cli_engine.py:608` use local generators) | seed helper: C-03; polish count: C-10; `pstdev`: Package D |
| H10, H11, M14, M25 | Forbidden kernel `_nb._three_opt_improve_atsp_numba` (`sota_tsp/ls_engine.py:146-150`); wall-clock stops (`ls_engine.py:203, 216`; `e2bso_tsp.py:240, 321, 325`); production hybrid 3-opt (`local_search.py:168, 234`); canonical 3-opt dedup cost (`three_opt.py:89-101, 150-171`) | **No:** separate MT6 plan right after Gate C (owner Q4). No catalog algorithm reaches the kernel or the wall-clock stops (ALNS does not import `ls_engine`) |
| H19, M15, M16 | Quick runner rescoring (`optimizer_api/benchmark_runner.py:172, 473`; `routers/benchmark.py:331-334`); no production gate; core owns TSPLIB I/O | MT4/MT2, out of scope (section 5) |

### 1.4 GA/PSO findings (investigation for C-16)

**Implementations found** (none counts objective evaluations; `grep ObjectiveEvaluationBudget` under `uniride_core/algorithms` finds only `gwo_solver.py`, `hho_solver.py`, `objective_budget.py`):

| # | Where | Reached by | Notes |
|---|---|---|---|
| G1 | `uniride_core/algorithms/tsp_meta_engines.py:138` `solve_ga_tsp`, `:414` `solve_pso_tsp` | `Core-GA-TSP`, `Core-PSO-TSP` through `engine_factory.CORE_TSP_SOLVERS` (`engine_factory.py:30-31`) and `_make_core_tsp_executor` (`registry_setup.py:88, 596-597`) | String waypoints and a `duration_func`. GA is memetic: every initial chromosome gets an uncounted 2-opt (`apply_local_search`, max 10 iterations), and any exception there is swallowed (`tsp_meta_engines.py:155-170`). Fitness evaluation at `:119-125`; generation loop from `:177`. PSO: swarm init `:435-448`, iteration loop `:456-470`. Two-node shortcut evaluates both directions (`:151-153`, `:427-429`) |
| G2 | `uniride_core/algorithms/numba_metaheuristics.py:95` `_run_ga`, `:163` `_run_pso` (`run_meta_heuristic`, `:294-310`) | `Numba-GA`, `Numba-PSO` registered by the `STRATEGIES` loop (`registry_setup.py:452-455`, `_make_legacy_executor`, `:342`, `:420-423`) | A second implementation behind a name the resolver calls an alias of `Core-GA-TSP` (H9 pattern) |
| G3 | `archive/academic_benchmark/bildiri2026_legacy/bildiri2026/core/ga_solver.py` (175 lines), `pso_solver.py` (237 lines) | nothing (archived; `B-GA`/`B-PSO` are hard errors, A01) | The implementations behind the paper's numbers, both on `BaseTSPSolver` with Numba objective, both memetic although labelled plain "GA"/"PSO" (details below). `REFERENCE_ONLY`; may not be executed, so no relocation parity fixture can be produced from them |

**What the paper's GA and PSO actually ran (archived source, read only):**

- **GA** (`ga_solver.py`): a Numba 2-opt of 10 iterations on every initial chromosome (`:62-69`), no periodic polish, and a final 2-opt of 300 iterations on the best chromosome (`:150-156`). The result says `algorithm="GA"` with `params["hybrid_2opt"]: True` (`:158-169`). None of the 2-opt evaluations is counted. C-16c gives this approach a truthful, counted canonical form.
- **PSO** (`pso_solver.py`): the module docstring calls it "Memetic PSO" with "Final 2-opt polishing (Memetic)" (`:12-18`). It runs a Numba 2-opt of 30 iterations on every initial particle (`:143-151`), again 30 iterations on every re-initialized particle at each re-initialization (every `reinit_interval` = 50 iterations by default; `_reinit_swarm` `:110-127`, called at `:196-197`), and a final 2-opt of 300 iterations on the global best (`:212-217`). The result says `algorithm="PSO"` (`:221`). No 2-opt evaluation is counted. So the paper's PSO was a memetic PSO with initial, periodic (at re-initialization) and final 2-opt. **The owner chose not to add a memetic PSO** (2026-10-19); canonical `Core-PSO-TSP` is pure (C-16b). The paper text must therefore say that its published PSO numbers came from this memetic PSO, and that a rerun uses the pure canonical PSO.

**Budget plumbing gap:** a fixed-budget claim needs (fairness design `:52-64`) a counted population initialization as one atomic phase, each generation (GA offspring evaluations) or iteration (PSO particle evaluations) as one atomic phase that starts only when its safe upper bound fits, counted (or removed) local search inside the solver, a reported termination reason, and native mode with `ObjectiveEvaluationBudget(None)`. None of G1-G3 has any of this. The GWO/HHO pattern to copy is `tsp_matrix_metaheuristics/gwo_solver.py:59-73` (counter), `:110-112` (`_evaluate` consumes), `:160-170` and `:205-206` (atomic phase checks), on `BaseTSPSolver` (`tsp_matrix_metaheuristics/base_solver.py:40, 138, 247`). Decided (P1, section 4.2): new pure solvers on the `BaseTSPSolver` matrix path (C-16a, C-16b) plus a counted memetic GA (C-16c).

**Instance and provenance comparison (Bildiri legacy vs committed):**

| Instance | In legacy Bildiri configs | Committed `.tsp` (`academic_benchmark/tsplib_data/tsp/MANIFEST.json`) | Committed optimal tour (`opt_tours/MANIFEST.json`) | `uniride-dataset/v1` manifest in `academic_benchmark/datasets/` | YAEM legacy |
|---|---|---|---|---|---|
| berlin52 | yes | yes | yes | **needed** | yes |
| eil51 | yes | yes | yes | **needed** | yes |
| st70 | yes | yes | yes | **needed** | yes |
| kroA100 | yes | yes | yes | **needed** | yes |
| eil76 | yes (`config_eil76_*`) | yes | yes | **needed** | no |
| rd100 | yes (`batch_rd100.json`, `batch_extra_*rd100.json`) | yes | yes | **needed** | no |
| gil262 | yes (`config_gil262_*`, tuning configs only) | **no** | **no** | needed **and** a source file | no |
| ft53 (ATSP, current active profile) | n/a | `academic_benchmark/tsplib_data/ft53.atsp` | none (no published tour) | exists (`datasets/ft53.json`) | no |

Source: config file names under `archive/academic_benchmark/bildiri2026_legacy/bildiri2026/configs/` (berlin52 5, eil51 5, kroA100 3, rd100 3, st70 3, eil76 2, gil262 2). The paper text in `Bildiri.md` does not name its instances, so the legacy configs are the only instance evidence. gil262 has n > 100 and no committed source; E09 defers n > 100 and no download is allowed; the owner excluded it (P3).

---

## 2. Gate C acceptance definition

Gate C is met when **all** of the following hold on one commit of `WIP`, run in `.venv-jit` with `PYTHONPATH` set to the checkout under test (a checkout that has the real `tsplib.db`, or after the skip guard of C-01 is hardened), and the exact counts are recorded in DECISION_LOG and `docs/UNIRIDE_WORKSTATE.md`:

1. **Catalog conformance.** A new test `academic_benchmark/tests/test_gate_c_normative_catalog.py` checks every row of design `:116-131` against the catalog: ID, label, problems {TSP, ATSP}, a VERIFIED fixed claim with exact accounting, a VERIFIED native claim, `production_ready=False`. **No row is deferred** (owner 2026-10-19: GA and PSO are promoted before Gate C; memetic-2opt gets native claims). The four hybrids carry composition kinds `global_then_final_3opt` / `global_then_final_alns` and labels saying "final polish once".
   The test also checks one **design addition** outside the table, `Core-GA-TSP-Memetic-2opt` (owner 2026-10-19; the lead records it in DECISION_LOG): VERIFIED, TSP and ATSP, fixed and native claims, composition kind `memetic_2opt`, label saying "initial and final 2-opt". The test lists every ID outside the table with its DECISION_LOG entry; any other extra ID fails.
2. **Hybrid boundary tests pass** (C-08, C-09): shared counter, one below / exactly at / one above an atomic phase, global cap `floor(B*0.80)`, polish gets `B - used_global`, the polish stage does not re-count the incoming tour, polish failure fails the run, fixed and native composite rows refuse to pool.
3. **GA/PSO accounting tests pass** (C-16a, C-16b, C-16c): atomic initialization and generation/iteration phases, no overshoot, deterministic replay, directed ATSP costs; for the memetic GA, every initial and final 2-opt evaluation goes through the shared counter and zero polish is rejected.
4. **Governed entry points produce validated results** (C-03): one governed CLI run and one governed Smart run on a 6-8 node in-memory matrix.
5. **Schema snapshots current:** `python -m academic_benchmark.contracts.export_schemas check` exits 0.
6. **Study profiles:** `bildiri2026` (revised by C-19 to the paper set plus the memetic GA and the GWO/HHO entries, on berlin52, eil51, st70, kroA100, rd100, eil76) and `yaem2026` (C-13) load through the study service and pass study-level capability preflight; every dataset reference resolves to a manifest whose checksum matches the committed file.
7. **Smoke pilot:** each study runs a smoke plan (C-12): one or two instances, `run_count` capped at 3 in smoke mode, the lowest budget level, outputs to `tmp_path`, every row validated by the independent Hamiltonian validator, fixed and native rows written to separate files, `assert_single_pooling_group` passes per file. "Pass" means the run completes with every row valid and the outputs well formed. It does not mean any algorithm is better, and the smoke report says so.
8. **Suites:**
   - `academic_benchmark/tests -m "not requires_ampl"`: all pass, no skip of an evidence test (the 3 skips seen in the baseline are listed in the record).
   - `uniride_core/tests`: pass, with optional-solver environment failures (OR-Tools absent from `.venv-jit`) listed separately from source defects (design `:412`).
   - The 3-opt regression command of `CANONICAL_THREE_OPT_DESIGN.md:122-126` plus any new canonical 3-opt test file.
   - `academic_benchmark/tests/test_production_registry_snapshot.py` unchanged and passing.
   - `git diff --check` clean.
9. **No artifacts:** `git status --short` shows no generated result files after the suites.

Command block (to be pasted into the closing item's brief):

```powershell
$env:PYTHONPATH = "<worktree>"; $env:PYTHON_BASIC_REPL = "1"
$PY = "C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe"
& $PY -m academic_benchmark.contracts.export_schemas check
& $PY -m pytest academic_benchmark/tests -m "not requires_ampl" -q -p no:cacheprovider --tb=short > C:\wt\gatec\academic.txt 2>&1
& $PY -m pytest uniride_core/tests -q -p no:cacheprovider --tb=short > C:\wt\gatec\core.txt 2>&1
& $PY -m pytest academic_benchmark/tests/test_numba_registry_matrix.py academic_benchmark/tests/test_numba_three_opt.py academic_benchmark/tests/test_core_tsp_registry.py uniride_core/tests/test_local_search_core.py uniride_core/tests/test_tsp_meta_engines.py uniride_core/tests/test_canonical_three_opt.py academic_benchmark/tests/test_canonical_three_opt_integration.py -q -p no:cacheprovider --tb=short
git diff --check
```

### Baseline measured for this plan (worktree at `559826b5`, `.venv-jit`, `PYTHONPATH` = worktree)

| Command | Result |
|---|---|
| Focused gate batch: 27 files (catalog, evidence, gateway, preflight x2, resolution, ALNS C3, Or-opt C2, registry identity, 3-opt integration, fair protocol x3, fair pilot CLI, native protocol, budget ownership, manifest contracts, Bildiri profile, mutation-proof gateway, pooling, Hamiltonian validator, production snapshot, Smart preflight, CX-04, JIT parity, smoke benchmark, smoke datasets) | **562 passed**, 0 skipped, 30 warnings, 112.5 s |
| `academic_benchmark/tests -m "not requires_ampl"` | **1527 passed, 1 failed, 3 skipped**, 42 warnings, 464.8 s. The failure is an environment artifact, not a Package C defect: `test_exact_published_tours.py::test_the_real_database_published_tours_match_the_coordinates_of_the_verification_set` skips only when `tsplib.db` is absent (`test_exact_published_tours.py:107-108`), but earlier in the same run some test created an empty 4 KB `academic_benchmark/tsplib_data/tsplib.db` in the fresh worktree (`tsplib_manager.py:69` `sqlite3.connect` creates the file; audit M16 "created on first read"), so the test ran against an empty file (`no such table: problems`, `scripts/run_exact_tsp_reference.py:217`). In the main checkout, which has the real database, this test passes (merge `bad28413`). C-01 hardens the skip guard. |
| 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:122-126`) plus `uniride_core/tests/test_canonical_three_opt.py`, `academic_benchmark/tests/test_canonical_three_opt_integration.py` (7 files) | **58 passed**, 12 warnings, 4.9 s |
| `uniride_core/tests/test_archive_boundaries.py` | **2 passed**, 9.5 s |
| `python -m academic_benchmark.contracts.export_schemas check` | exit 0 (snapshots current) |

The `uniride_core/tests` full suite was not run for this plan (its OR-Tools split needs a separate environment note); C-15 runs it. The worktree's empty `tsplib.db` must not be copied anywhere; the lead removes it with the worktree.

---

## 3. Remaining work items

Dependency order and parallel lanes:

```text
Lane A (parallel, start immediately):   C-01 M17 + skip guard   C-02 L8   C-03 H13   C-04 M19 (non-zero polish)
Lane B (core, serial):                   C-05 shared counter -> C-06 composition engine + 3-opt polish -> C-07 ALNS polish entry
Lane F (core GA/PSO, parallel with B):   C-16a pure GA + accounting   C-16b pure PSO + accounting
                                          C-16a -> C-16c memetic GA (also after C-04 and C-10's counted-polish step)
Lane C (catalog; the lead merges one capabilities.py change at a time, in this order):
                                          C-08 3-opt hybrids (after C-05, C-06) -> C-09 ALNS hybrids (after C-07)
                                          -> C-10 memetic-2opt native (after C-04) -> C-16a promotion -> C-16b promotion
                                          -> C-16c promotion (new ID, design addition)
Lane D (services and data):              C-11 study service (parallel with B) -> C-12 study smoke runner
                                          C-18 dataset manifests for the six instances (any time; data and tests only)
                                          -> C-13 YAEM profile (after C-08, C-09, C-11, C-18)
                                          -> C-19 Bildiri profile (after C-04, C-10, C-16a, C-16b, C-16c, C-11, C-18; confirmed by the owner)
Lane E:                                   C-14 H9 renames (after C-16a, C-16b, C-16c)
Close:                                    C-15 Gate C close (after every item above)
After Gate C, before any paper-scale run: separate MT6 plan (H10+M25 together, H11, M14)
```

Model and review guidance per CLAUDE.md: Lane A items are small (one developer, Sonnet reviewer). C-05 to C-10 and C-16a/b/c change accounting or algorithm identity: developer Sonnet, reviewer **Opus**. C-11 to C-14, C-18, C-19: developer Sonnet, reviewer Sonnet. Suggested tool-call ceiling per item: about 12-25 (requested, not enforced).

### C-01: Archive namespace hardening (M17) and the real-DB skip guard

- [x] **Goal:** `import archive` and `import archive.academic_benchmark...` fail with `ImportError`; generic boundary markers include `archive.`; scans include dynamic `importlib.import_module("archive...")` strings and root/`scripts` Python files.
- **Files:** create `archive/__init__.py` (raises `ImportError` with a pointer to `QUARANTINE.md`); modify `uniride_core/tests/test_archive_boundaries.py:7-13`; `academic_benchmark/tests/test_yaem_quarantine_boundary.py` (dynamic-import case). Same branch, separate commit: `academic_benchmark/tests/test_exact_published_tours.py:107-108` skips unless the `problems` table exists (see the baseline note in section 2).
- **Red test first:** `test_archive_package_is_not_importable` (subprocess `-c "import archive"` must fail) and a planted-string fixture for the dynamic scan; both fail before the change. For the guard: an empty SQLite file at a `tmp_path` DB path must lead to a skip, not a failure.
- **Acceptance:** new tests pass; `test_archive_manifest.py`, `test_archive_manifest_line_endings.py`, `test_archive_manifest_polish.py`, `test_historical_quarantine.py`, `test_quarantine_round2.py` still pass (the new file sits outside both legacy manifests; check that no manifest test counts files at `archive/` root).
- **Closes:** M17. **Risk:** low (a repository grep for `import archive`, `from archive` and `import_module("archive` outside `archive/` and tests found none in this run). **Changes academic results:** no.

### C-02: Truthful local-search termination (L8)

- [x] **Goal:** the 2-opt/3-opt/Or-opt fixed-budget executor reports `search.termination_reason` instead of re-deriving it.
- **Files:** `academic_benchmark/core/registry_setup.py:222-227`; a new `academic_benchmark/tests/test_l8_termination_reason.py`.
- **Red test first:** a 6-node matrix where the search stops on `no_improving_move` at exactly `max_iterations`; the current code labels it `max_iterations`.
- **Acceptance:** red test green; golden tables (`test_fixed_budget_tables_unchanged.py`) unchanged, or updated with a lead-reviewed note if a frozen row changes its label.
- **Closes:** L8. **Risk:** low. **Changes academic results:** costs and evaluation counts no; the `termination_reason` label can change. Termination-reason tallies from before and after the fix are not pooled (A14 rule, recorded in the tracker row).

### C-03: Governed CLI and Smart runs (H13)

- [x] **Goal:** governed CLI and Smart runs produce validated canonical results with contract seeds.
- **Files:** `academic_benchmark/core/execution_gateway.py:190-225` (inject `fair_comparison` or `native_comparison` built from the decision and a caller base seed); `academic_benchmark/smart_benchmark.py:660-668`, `academic_benchmark/cli_engine.py:815-822, 955-970` (seed from `FairComparisonManifest.paired_seed`, `fairness.py:242-253`); `academic_benchmark/benchmark_utils.py:672-678` (delete or guard `make_deterministic_seed`, L9); tests in `test_smart_benchmark_preflight.py`.
- **Red test first:** governed Smart run of `Core-TwoOpt-TSP`, `ALNS-TSP` and `Core-GWO-TSP-Pure` on a 7-node matrix raises `ResultContractViolation` today (audit H13 evidence); expected: validated `FairRunResult`, identical seed and `seed_group` across algorithms for one (problem, replicate).
- **Acceptance:** red tests green; non-governed (`NON_C1_ROUTING`) tasks keep their six-field tuples and seeds (C1 final-review constraint, `2026-07-29-c1-final-review-fixes.md` Global Constraints).
- **Closes:** H13; L9 seed-helper bullet. **Risk:** medium (two entry points, persistence metadata). **Changes academic results:** only for governed runs, which today always fail closed (assumption to re-check in the brief: no governed CLI/Smart row exists in `benchmark_results`); legacy seeds of non-governed runs stay unchanged.

### C-04: Memetic-2opt truthfulness (M19); Bildiri memetic entries get a small non-zero polish (owner Q3)

- [x] **Goal:** a memetic configuration with zero executed polish is rejected; `polish_policy` and the "polish ran" flags are derived from executed polish counts; the polish schedule is recorded in the result; the Bildiri profile's two memetic entries get a small non-zero `polish_iters`/`final_polish_iters` (smoke-sized; exact values set in the brief and kept as draft placeholders).
- **Files:** `academic_benchmark/core/registry_setup.py:740-782`; `uniride_core/algorithms/tsp_matrix_metaheuristics/gwo_solver.py:116-137` and `hho_solver.py` (expose executed polish counts in `extra_stats`, no equation change); `academic_benchmark/studies/bildiri2026/study.json:14, 16`; tests `test_fair_protocol_v2_metadata.py`, `test_bildiri_study_profile.py`.
- **Red test first:** `Core-GWO-TSP-Memetic-2opt` with `polish_iters=0, final_polish_iters=0` is accepted and labelled memetic today; expected: `ValueError` before execution. A second test: executed polish counts appear in `polish_policy`. A third: the Bildiri profile's memetic entries have non-zero polish.
- **Acceptance:** red tests green; GWO/HHO parity tests (`test_numba_jit_parity.py`) unchanged.
- **Closes:** M19. **Risk:** low-medium. **Changes academic results:** no cost change for valid configurations. Smoke rows produced from the zero-polish Bildiri profile are not pooled with rows from the corrected profile.

### C-05: Injectable shared objective counter for pure GWO/HHO (core, no behaviour change)

- [x] **Goal:** `GWOOptimizer`/`HHOOptimizer` accept an injected `ObjectiveEvaluationBudget` plus a stage cap, and do not reset an injected counter. Default behaviour (own counter) stays identical.
- **Files:** `uniride_core/algorithms/objective_budget.py` (a stage-capped view over one shared counter: `can_spend` respects both the stage cap and the total limit); `gwo_solver.py:59-73, 150-170`; `hho_solver.py:83, 223`; tests `uniride_core/tests/test_objective_budget_stage_cap.py` (new) and the existing GWO/HHO parity fixtures.
- **Red test first:** a shared counter at `used=10`, limit 100, stage cap 60: pure GWO must stop with `used <= 60` and must not reset `used` to 0 (`gwo_solver.py:153` resets it today).
- **Acceptance:** red test green; every existing fixed and native GWO/HHO evidence test and `test_numba_jit_parity.py` pass unchanged (route, cost, evaluations, termination, backend), so relocation parity (design `:239`) holds.
- **Closes:** none directly (prerequisite of D2/D3). **Risk:** medium (JIT path; atomic population phase rule, fairness `:52-64`). **Changes academic results:** no (parity-gated).

### C-06: Two-stage composition engine with canonical 3-opt polish (core)

- [x] **Goal:** one core function implements design `:181-203` for a pure global stage followed by one polish stage, fixed and native.
- **Files:** create `uniride_core/algorithms/composition.py`; move `improve_three_opt_budgeted` from `academic_benchmark/fairness.py:382-470` to `uniride_core/algorithms/objective_budget.py` next to the budgeted 2-opt/Or-opt (keep a re-export in `fairness.py`) and give it an `initial_cost` parameter like `improve_two_opt_budgeted`; tests `uniride_core/tests/test_composition_engine.py` (new), existing 3-opt tests.
- **Rules to implement (design `:183-191`):** global stage = pure GWO/HHO with no hidden polish; polish once on the best validated global tour; separate `global`/`polish` parameter namespaces with no implicit defaults in paper-scale manifests; `global_fraction` explicit (smoke default 0.80, global cap `floor(B*0.80)`, polish gets `B - used_global`); one shared counter; deterministic 3-opt records no secondary seed; global failure fails the composition; polish exception or invalid tour fails the run; result records stage IDs, parameters, seeds, allocated and consumed evaluations, termination reasons, `polish_changed_tour`. Native mode (`:195-201`): no cap, separate stage counts summed for description, aggregate termination `composite_complete` only when both stages complete.
- **Decided (2026-10-19, lead decision confirmed with the owner's answers):** the polish stage **reuses the cost already counted by the global stage** and does not re-count the incoming tour (fairness design `:46-50`: "reuse the solver's known objective where possible"); the gateway's independent cost recomputation is the check. Precedent: the memetic 2-opt polish passes `initial_cost` to `improve_two_opt_budgeted` (`gwo_solver.py:119-123`). The lead records this in DECISION_LOG with the plan merge.
- **Red test first:** boundary triplet with a stub global stage whose atomic phase needs `k` units: remaining `k-1` (phase refused, termination `evaluation_budget_exhausted`), `k` (runs, total = B), `k+1`; polish with 0 remaining returns the global tour, `polish_changed_tour=False`, and consumes 0 units; polish raising fails the run; the moved 3-opt function without `initial_cost` is behaviour-identical (parity on the existing fixtures).
- **Acceptance:** red tests green; 3-opt regression command passes; `uniride_core` imports nothing from `academic_benchmark`.
- **Closes:** design D2/D3 (engine half). **Risk:** high (accounting identity; design `:193`: a later change of timing, transfer or allocation needs a new variant). **Changes academic results:** no existing result (new identities only).

### C-07: ALNS polish entry from a given tour (core)

- [x] **Goal:** an accounted ALNS entry that starts from a supplied complete tour with its known cost and a supplied stage counter, with seed `SHA-256(protocol_version, run_seed, "polish")` (design `:189`), leaving the standalone `ALNS-TSP` path unchanged.
- **Files:** `uniride_core/algorithms/sota_tsp/alns_tsp.py:86-93, 198-211`; `uniride_core/algorithms/composition.py` (ALNS polish adapter); tests `uniride_core/tests/test_alns_polish_entry.py` (new); `academic_benchmark/tests/test_alns_c3_evidence.py` must stay green.
- **Red test first:** the supplied tour is the start and is not re-counted; counter shared; derived seed independent of Python `hash()` and stable across processes (subprocess with two `PYTHONHASHSEED` values).
- **Acceptance:** red tests green; all four ALNS C3 evidence tests unchanged.
- **Closes:** prerequisite of D2a. **Risk:** medium. **Changes academic results:** no.

### C-08: Promote GWO-3opt and HHO-3opt

- [x] **Goal:** `Core-GWO-TSP-Memetic-3opt` and `Core-HHO-TSP-Memetic-3opt` become VERIFIED with TSP/ATSP fixed and native claims backed by named evidence tests. IDs stay as in the normative table (owner Q5); the composition kind is `global_then_final_3opt` and the label says "final polish once" (for example "Grey Wolf Optimizer + 3-opt (final polish once)").
- **Files:** `uniride_core/algorithms/capabilities.py:44-48` (new `CompositionKind.GLOBAL_THEN_FINAL_3OPT = "global_then_final_3opt"`), `:275-276`; `academic_benchmark/core/registry_setup.py` (executors using C-06); `academic_benchmark/fairness.py` and `native_protocol.py` (composite result validation: stage fields, `evaluations == sum(stage evaluations)`, cap compliance); `academic_benchmark/core/execution_gateway.py` (`validate_preflighted_result` accepts the composite contract); `fair_pilot.py:44-50`, `native_pilot.py:60-80` allowlists; schema for composite run fields if the run contract changes (`academic_benchmark/contracts/run.py`, then `export_schemas write` and a lead-reviewed snapshot diff); tests `academic_benchmark/tests/test_hybrid_3opt_evidence.py` (new), `test_hybrid_budget_boundaries.py` (new).
- **Red test first:** `find_capability_claim("Core-GWO-TSP-Memetic-3opt", ...)` returns a claim (fails while PLANNED); boundary triplet through the real executor; ATSP directed-cost preservation (asymmetric 7-node fixture, independent closed-cycle cost); deterministic replay with the same seed; fixed and native composite rows fail `assert_single_pooling_group` together.
- **Acceptance:** red tests green; catalog drift tests (`test_algorithm_capability_catalog.py`) pass; production snapshot unchanged.
- **Closes:** D2 (3-opt half). **Risk:** high (new identities, scientific claims). **Changes academic results:** new algorithms only.

### C-09: Promote GWO-ALNS and HHO-ALNS

- [x] Same shape as C-08, with `CompositionKind.GLOBAL_THEN_FINAL_ALNS = "global_then_final_alns"`, labels saying "final polish once", ALNS polish (C-07), required strict ALNS parameters under the `polish` namespace (`fairness.py:45`, C3 constraint list), and a recorded derived polish seed. New tests `test_hybrid_alns_evidence.py`. Depends on C-07 and on C-08 (same files). **Closes:** D2a. **Risk:** high. **Changes academic results:** new algorithms only.

### C-10: Native claims for GWO/HHO Memetic-2opt (owner Q3: yes; counted polish first)

- [x] **Goal:** add the native claims that the design table `:125-126` requires, after the native polish is counted.
- **Step 1, counted polish:** outside fair mode `_polish` runs the Numba kernel `_two_opt_improve_atsp_numba` and its candidate evaluations do not go through the counter (`gwo_solver.py:126-140`; same pattern in `hho_solver.py`). Native mode must count them: either the budgeted Python 2-opt with an unlimited counter, as fair mode does (`:119-127`), or a counted kernel with JIT parity. The brief picks one and records it; the backend profile in the claim must say what actually ran (`polish=python` or `polish=numba_nopython`).
- **Step 2, claims:** `capabilities.py:266-267` (`native_evidence=`), new native evidence functions in `test_algorithm_capability_evidence.py`, `native_pilot.py:60-80` allowlist.
- **Red test first:** native memetic run reports `objective_evaluations` that equal an independent count of complete-tour evaluations including polish (fails today); `find_capability_claim(..., NATIVE_TERMINATION, ...)` for memetic-2opt returns a claim.
- **Acceptance:** native evidence tests green; fixed memetic evidence unchanged.
- **Closes:** D1e; L9 polish-count bullet. **Risk:** medium. **Changes academic results:** native memetic evaluation counts change (and costs if the polish implementation changes); earlier native memetic rows are not pooled with later ones.

### C-11: Study service (load, resolve, preflight, expand)

- [x] **Goal:** `academic_benchmark/studies/service.py` loads a study JSON, validates it with `StudyManifestV1`, loads each dataset manifest (`DatasetManifestV1`, repository-relative path, checksum verified against the referenced file), checks that every (algorithm, problem family, protocol, backend policy) the study needs has a VERIFIED claim (`find_capability_claim`), and expands an immutable plan: (dataset, algorithm, protocol, budget level, replicate, paired seed, seed group).
- **Files:** new `academic_benchmark/studies/service.py`, `academic_benchmark/studies/__init__.py`; tests `academic_benchmark/tests/test_study_service.py`.
- **Red test first:** a profile that lists `Core-GWO-TSP-Memetic-2opt` in `secondary_protocol.algorithm_ids` passes `StudyManifestV1` today but has no native claim yet; the service must reject it. Also: unknown dataset ref, checksum mismatch, absolute path, alias ID, budget levels not pooled (each plan row carries its level).
- **Acceptance:** the current Bildiri profile loads and expands; plan seeds equal `FairComparisonManifest.paired_seed` for the same inputs.
- **Closes:** D5. **Risk:** medium. **Changes academic results:** no.

### C-12: Study smoke runner (fixed/native separated, validated)

- [x] **Goal:** run an expanded plan in smoke mode through `execute_preflighted`, validate each result with the independent Hamiltonian validator, write fixed and native rows to separate files under a caller-provided directory outside the repository (reuse `fair_pilot._prepare_output_dir` rules), and refuse to write a file whose rows fail `assert_single_pooling_group` or mix budget levels.
- **Files:** `academic_benchmark/studies/smoke.py` (new); reuse `fair_pilot.py`/`native_pilot.py` record builders rather than copying them; tests `academic_benchmark/tests/test_study_smoke.py`.
- **Red test first:** runner on the Bildiri profile, `ft53`, budget 100, 1 replicate, into `tmp_path`: two files, all rows valid; a forced invalid tour from a stub executor stops aggregation and records a failed-run row (design `:360`); smoke report text contains no ranking words (reuse the A15 wording check).
- **Acceptance:** red tests green; no file appears in `git status`.
- **Closes:** D4 (study path), D6 (study path), Gate C criterion 7. **Risk:** medium. **Changes academic results:** no (smoke only).
- **Note:** reproducibility manifests (`RunManifestV1` plus detached `.sha256`) are Package D (`:453`); the runner records only what the pilots already record.

### C-18: Dataset manifests for the TSPLIB study instances

- [x] **Goal:** `uniride-dataset/v1` manifests for berlin52, eil51, st70, kroA100 (YAEM and Bildiri) and eil76, rd100 (Bildiri), built only from the committed files and their manifests (`academic_benchmark/tsplib_data/tsp/MANIFEST.json`, `opt_tours/MANIFEST.json`, E12 companion task): source, checksum, problem type, dimension, metric semantics (EUC_2D nearest-integer, as in E10/T06), optimum provenance. gil262 is excluded (owner P3).
- **Files:** `academic_benchmark/datasets/{berlin52,eil51,st70,kroA100,eil76,rd100}.json`; tests `academic_benchmark/tests/test_tsplib_dataset_manifests.py` (checksum of each referenced file, optimum equals the collection manifest's `published_optimum`, no `archive/` path, no `tsplib.db` path).
- **Red test first:** the study service (or, before C-11 lands, `DatasetManifestV1` plus a checksum helper) fails to resolve `academic_benchmark/datasets/berlin52.json`.
- **Acceptance:** red test green; schema check passes. **Closes:** data prerequisite of D7/D8. **Risk:** low. **Changes academic results:** no.

### C-13: YAEM active study profile (owner Q1: option a)

- [x] **Goal:** `academic_benchmark/studies/yaem2026/study.json`, status `draft`, output policy smoke-only, mirroring the legacy set: instances berlin52, eil51, st70, kroA100 (symmetric TSP); algorithms `Core-TwoOpt-TSP`, `Core-ThreeOpt-TSP`, `Core-OrOpt-TSP`, `Core-GWO-TSP-Pure`, `Core-HHO-TSP-Pure`, `Core-GWO-TSP-Memetic-2opt`, `Core-HHO-TSP-Memetic-2opt`, `Core-GWO-TSP-Memetic-3opt`, `Core-HHO-TSP-Memetic-3opt` (the truthful replacements of the legacy `GWO-LKH`/`HHO-LKH`), `Core-GWO-TSP-Memetic-ALNS`, `Core-HHO-TSP-Memetic-ALNS`; primary fixed protocol, secondary native protocol; budget levels, run counts and `global_fraction` are placeholders marked draft (explicit values come with a paper plan).
- **Files:** `academic_benchmark/studies/yaem2026/study.json`; tests `academic_benchmark/tests/test_yaem_study_profile.py`.
- **Red test first:** the profile loads through C-11 and passes study-level preflight; `GWO-LKH`/`HHO-LKH` in any field fail with the truthful replacement (design `:149-150, 251`); no reference to `archive/` paths.
- **Acceptance:** C-12 smoke run of the YAEM profile on one instance at the lowest budget passes.
- **Closes:** D7. **Risk:** low-medium. **Changes academic results:** no.

### C-16a: Canonical GA with exact accounting (required before Gate C; owner 2026-10-19)

- [x] **Decided (P1, 2026-10-19):** a canonical pure GA on the `BaseTSPSolver` matrix path next to GWO/HHO, its operators taken from the archived Bildiri `GAOptimizer` as reference only.
- **Goal:** `Core-GA-TSP` VERIFIED for TSP and ATSP, fixed and native, with exact objective accounting and deterministic replay, in the style of C2/C3.
- **Files:** create `uniride_core/algorithms/tsp_matrix_metaheuristics/ga_solver.py` (`GAOptimizer` on `base_solver.py:40`; counter as in `gwo_solver.py:59-73, 110-112`; atomic phase checks as in `gwo_solver.py:160-170, 205-206`); `uniride_core/algorithms/tsp_matrix_metaheuristics/__init__.py`; `academic_benchmark/core/registry_setup.py:596-597` (replace the `Core-GA-TSP` academic executor, which today runs `tsp_meta_engines.solve_ga_tsp`, with a manifest-aware executor like `_make_numba_metah_executor`, `:611`); strict GA parameter validation in `fairness.py` (required keys, reject unknown keys, as C3 did for ALNS); `fair_pilot.py:44-50`, `native_pilot.py:60-80` allowlists; `capabilities.py:262` (promotion commit, merged in Lane C order); tests `academic_benchmark/tests/test_ga_evidence.py` (new).
- **Accounting rules:** population initialization is one atomic phase (population size evaluations); each generation is one atomic phase whose safe upper bound is the number of offspring evaluated; no hidden local search (the archived GA's initial and final 2-opt is not part of `Core-GA-TSP`; it becomes the separate ID of C-16c); the solver exposes initialization, generation and best-tour hooks that C-16c reuses without copying; native mode uses `ObjectiveEvaluationBudget(None)` and reports actual counts; termination reasons `evaluation_budget_exhausted`, `max_iterations`, `max_no_improvement`.
- **Red test first:** fixed run on a 7-node symmetric and a 7-node asymmetric matrix: `objective_evaluations` equals an independent count, never exceeds B, boundary triplet at a generation phase (one below, exactly at, one above), same seed gives the same route, cost, count and termination twice; ATSP cost recomputed with directed arcs. All fail before the solver exists.
- **Acceptance:** four evidence tests (TSP/ATSP × fixed/native) named in the claims; catalog drift tests pass; production snapshot unchanged (the production `ga`/`ga_split` strategies are untouched).
- **Closes:** D1f (GA). **Risk:** high (new canonical algorithm, scientific claims). **Changes academic results:** yes for anything labelled `Core-GA-TSP` or `Numba-GA` (alias): rows produced before the change came from G1 or G2 and are not pooled with rows from the canonical GA (A14 rule; the archived Bildiri GA rows are already `HISTORICAL_UNVERIFIED`, A13).

### C-16b: Canonical PSO with exact accounting (required before Gate C; owner 2026-10-19)

- [x] Same shape as C-16a for `Core-PSO-TSP`, pure (owner P1: no memetic PSO; the archived PSO's initial, re-initialization and final 2-opt, section 1.4, are not part of it): create `uniride_core/algorithms/tsp_matrix_metaheuristics/pso_solver.py` (operators from the archived Bildiri `PSOOptimizer`, reference only; re-initialization kept only as a counted, explicitly parameterised diversity step without 2-opt); swarm initialization one atomic phase (swarm size evaluations), each iteration one atomic phase (particle evaluations); replace the `Core-PSO-TSP` executor at `registry_setup.py:596-597`; strict parameter validation; allowlists; `capabilities.py:263` promotion; tests `academic_benchmark/tests/test_pso_evidence.py`. Can be developed in parallel with C-16a; the promotion commits are merged one after the other. **Closes:** D1f (PSO). **Risk:** high. **Changes academic results:** yes for `Core-PSO-TSP`/`Numba-PSO` rows; no pooling across the change.

### C-16c: Counted memetic GA `Core-GA-TSP-Memetic-2opt` (design addition; owner 2026-10-19)

- [x] **Goal:** a new canonical ID that represents the paper's GA approach (section 1.4: 2-opt on every initial chromosome, a final 2-opt) under the same accounting contract as GWO/HHO memetic-2opt: every 2-opt evaluation goes through the shared counter, no hidden polish, explicit non-zero polish parameters. The archived `ga_solver.py` is reference only; no execution and no parity claim.
- **Design addition:** the ID is not in the normative table (design `:116-131`). The lead records it in DECISION_LOG (ID, reason "represents the Bildiri 2026 paper's GA truthfully", owner decision 2026-10-19) when C-16c merges; the Gate C conformance test (C-15) includes it as a listed addition. Naming follows `Core-GWO-TSP-Memetic-2opt`; label "Genetic Algorithm (memetic 2-opt: initial and final)". The study label is `GA-2opt`.
- **Composition kind and polish schedule:** reuse `CompositionKind.MEMETIC_2OPT`. The kind names the operator family (2-opt inside the search, counted), and the schedule is carried by the result's `polish_policy`, which the fairness design already requires to state initial, periodic and final polish explicitly (`ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md:32`). For this ID `polish_policy` is `{"initial": true, "periodic": false, "final": true, "operator": "2-opt"}`, derived from executed polish counts (the C-04 rule). A test pins that a GA memetic result never reports `periodic: true`, and that GWO/HHO memetic results keep their own schedule. A separate kind is not needed because claims never match on schedule; if a later study needs to select by schedule, that is a new kind by a new decision.
- **Parameters (strict, required, no defaults in paper-scale manifests):** the C-16a GA parameters plus `initial_polish_iters >= 1` and `final_polish_iters >= 1`; zero or missing polish is rejected before execution (C-04 rule); unknown keys rejected.
- **Accounting (fixed, `atomic_upper_bound_v1`):** population initialization (population size evaluations) is the atomic phase of C-16a; then the initial 2-opt runs per chromosome through `improve_two_opt_budgeted` with `initial_cost` (each candidate evaluation is atomic, fairness `:52-64` rules 4-5), handled exactly as the GWO/HHO memetic initial polish (`gwo_solver.py:116-127`, `initialization_policy="..._with_initial_2opt"`); generations as in C-16a; the final 2-opt runs once on the best chromosome with its known cost (not re-counted) and stops without overshoot when the budget ends. Budget exhaustion at any point is normal termination with `evaluation_budget_exhausted`, returning the best evaluated tour.
- **Native:** no cap; counter `ObjectiveEvaluationBudget(None)`; the 2-opt uses the counted Python path chosen in C-10 step 1, so `objective_evaluations` includes every polish evaluation.
- **Claims:** four, TSP and ATSP × fixed and native, backend profile objective = what the C-16a solver runs (Numba nopython expected), polish = Python (the budgeted 2-opt), `directed_cost_preserved` for ATSP, exact accounting, deterministic replay. Evidence tests in `academic_benchmark/tests/test_ga_memetic_evidence.py`: `test_core_ga_memetic_2opt_fixed_tsp_evidence`, `..._fixed_atsp_evidence`, `..._native_tsp_evidence`, `..._native_atsp_evidence`.
- **Files:** `uniride_core/algorithms/tsp_matrix_metaheuristics/ga_solver.py` (polish option on the C-16a solver, or a thin subclass; no copied GA loop); `academic_benchmark/core/registry_setup.py` (executor beside the pure GA, `variant="memetic_2opt"`); `academic_benchmark/core/algorithm_resolution.py` (canonical ID registered; no new alias; `Numba-GA` keeps pointing to the pure `Core-GA-TSP`, design `:142`); `fairness.py` parameter validation; `fair_pilot.py`/`native_pilot.py` allowlists; `capabilities.py` (new entry, merged last in Lane C).
- **Red test first:** fixed run on 7-node symmetric and asymmetric matrices: the independent count of complete-tour evaluations (population, initial 2-opt candidates, generations, final 2-opt candidates) equals `objective_evaluations` and never exceeds B; boundary triplet inside the initial polish and inside the final polish (one unit below, exactly at, one above what the next candidate needs); zero polish rejected; same seed twice gives the same route, cost, count, termination and `polish_policy`; ATSP 2-opt candidates are costed with directed arcs (fails until the solver exists).
- **Acceptance:** red tests green; C-16a pure GA evidence unchanged (the polish option is off for `Core-GA-TSP`); catalog drift tests pass; production snapshot unchanged.
- **Depends on:** C-16a (pure GA), C-04 (zero-polish rejection, polish flags from executed counts), C-10 step 1 (counted native 2-opt path). **Closes:** D1h. **Risk:** high (new identity outside the normative table; accounting across three phases). **Changes academic results:** new ID only. Its rows are never pooled with the archived Bildiri GA rows (`HISTORICAL_UNVERIFIED`, A13) nor with pure `Core-GA-TSP` rows (different algorithm).

### C-19: Bring the active Bildiri profile in line with the paper (confirmed by the owner 2026-10-19)

- [x] **Goal:** `academic_benchmark/studies/bildiri2026/study.json` covers the paper's algorithm set, `Core-TwoOpt-TSP`, `Core-ThreeOpt-TSP`, `Core-OrOpt-TSP`, `Core-GA-TSP`, `Core-PSO-TSP`, the new `Core-GA-TSP-Memetic-2opt` (C-16c), plus the current `Core-GWO-TSP-Pure`, `Core-HHO-TSP-Pure`, `Core-GWO-TSP-Memetic-2opt`, `Core-HHO-TSP-Memetic-2opt` (memetic entries with the non-zero polish of C-04); problem family TSP added with the six instances berlin52, eil51, st70, kroA100, rd100, eil76 (P2, via C-18; gil262 excluded, P3); `ft53`/ATSP kept (it is the E09/E12 exact-reference instance and the owner did not ask to remove it; the brief confirms with the lead); `run_count` stays a smoke placeholder (the paper used 30 runs; that value belongs to a paper-scale manifest, not to the smoke profile); status stays `draft`. That the published GA and PSO numbers came from the archived memetic GA and memetic PSO (section 1.4) is recorded in the C-19 DECISION_LOG note and the commit message; `PaperMetadataV1` is a strict contract, and the schema is not changed for a note.
- **Files:** `academic_benchmark/studies/bildiri2026/study.json`; `academic_benchmark/tests/test_bildiri_study_profile.py` (its pinned expectations, for example `test_profile_identity_and_scope` and `test_primary_protocol_retains_all_four_variants`, change with a lead-reviewed note); E12 LF pin of `study.json` updated.
- **Red test first:** the profile test expects the ten algorithm IDs, the TSP and ATSP families and the seven dataset references (six TSP plus `ft53`); it fails on the current profile.
- **Acceptance:** the profile loads through C-11 and passes study-level preflight; C-12 smoke on one TSP instance and `ft53` at the lowest budget passes.
- **Depends on:** C-04, C-10, C-16a, C-16b, C-16c, C-11, C-18. **Closes:** D8. **Risk:** low-medium (pinned tests, E12 note that the profile is not linked to the exact reference before Package D still holds). **Changes academic results:** rows from the new profile are not pooled with rows from the old profile (owner 2026-10-19).

### C-14: One ID, one implementation (H9; owner Q10: option a)

- [x] **Goal:** every canonical ID resolves to exactly one callable in every entry point; matrix engines get truthful `Matrix-*-legacy` names; `Core-*` IDs resolve only through the catalog and gateway; duplicate registration raises; a failed Numba import fails closed.
- **Files:** `uniride_core/algorithms/engine_factory.py:28-44, 94-133` (`Matrix-TwoOpt-TSP-legacy`, `Matrix-GA-TSP-legacy`, `Matrix-PSO-TSP-legacy`, `Matrix-GWO-TSP-legacy`, `Matrix-HHO-TSP-legacy`); `academic_benchmark/engine_core.py:181-185` (raise on duplicate names); `academic_benchmark/core/registry_setup.py:452-455` (the `Numba-GA`/`Numba-PSO` executors over `numba_metaheuristics.py` either get legacy names or are removed, so the resolver alias `Numba-GA` → `Core-GA-TSP` reaches only the canonical GA), `:789-838` (fail closed), `:996-1014` (routing alias table); web matrix mode names (`optimizer_api/routers/benchmark.py` matrix path, `src/lib/benchmark-backend-request.ts:59`).
- **Red test first:** parametrized test across CLI, `AlgorithmRegistry`, `engine_factory` and the web matrix mode: `Core-GWO-TSP` maps to two different callables today; `AlgorithmRegistry.register` twice with one name succeeds today.
- **Acceptance:** red tests green; production snapshot unchanged.
- **Depends on:** C-16a, C-16b, C-16c (so that `Core-GA-TSP`/`Core-PSO-TSP` keep a canonical executor when the matrix names move, and the GA alias table is final). **Closes:** H9. **Risk:** medium-high (web academic matrix mode, stored names). **Changes academic results:** stored `algorithm` strings of matrix-mode rows change; rows written under the old names are not pooled with rows under the new names (owner Q10; A14 rule; A13 labelling already covers pre-2026-10-13 rows).

### C-15: Close Gate C

- [x] **Goal:** add `test_gate_c_normative_catalog.py` (section 2, criterion 1: 14 normative rows, no deferred row, plus the listed design addition `Core-GA-TSP-Memetic-2opt`), run the full acceptance block, record counts, update Appendix J rows, add a DECISION_LOG entry ("Gate C met at `<sha>`"), update `docs/UNIRIDE_WORKSTATE.md` (ACAD-01 row).
- **Red test first:** the conformance test fails while any row is PLANNED or CANDIDATE or lacks a native claim.
- **Depends on:** C-01 to C-14, C-16a, C-16b, C-16c, C-18, C-19. **Acceptance:** section 2 criteria 1-9 hold on one commit. **Risk:** low. **Changes academic results:** no.

---

## 4. Owner decisions (2026-10-19)

### 4.1 Decisions on the plan questions

| # | Question | Decision | Rejected options (short) |
|---|---|---|---|
| Q1 | Scope of the YAEM active profile | **(a)** Mirror the legacy set: berlin52, eil51, st70, kroA100; 2-opt, 3-opt, Or-opt, GWO/HHO Pure, GWO/HHO-2opt, GWO/HHO-3opt, GWO/HHO-ALNS; `GWO-LKH`/`HHO-LKH` become the truthful 3-opt hybrids; draft, smoke-only; budget levels and run counts stay placeholders (C-13) | (b) minimal draft; (c) defer the profile |
| Q2 | GA/PSO in Gate C | **(a) Promote GA and PSO before Gate C** (C-16a, C-16b required; C-15 depends on them). The earlier plan text said no configuration uses GA/PSO; that was wrong for Bildiri: the paper compares 2-opt, 3-opt, Or-opt, GA and PSO (`Bildiri.md:9-11`) and the legacy configs list GA and PSO. The active Bildiri profile follows the paper after promotion (C-19) | (b) defer with a DECISION_LOG entry; (c) remove them from the target table |
| Q3 | Memetic-2opt native claims and the Bildiri zero-polish profile | **(a)** Add native claims, counted polish first (C-10); give the Bildiri memetic entries a small non-zero polish (C-04) | (b) drop memetic IDs from the profile; (c) defer native claims |
| Q4 | MT6 timing (H10, H11, M14, M25) | **(b)** A separate MT6 plan right after Gate C and before any paper-scale run; H10 and M25 land together | (a) inside Gate C; (c) H10+M25 now in a parallel lane |
| Q5 | Composition kind for the four hybrids | **(a)** Keep the normative IDs; add `global_then_final_3opt` and `global_then_final_alns`; labels say "final polish once" (C-08, C-09) | (b) rename the IDs |
| Q10 | H9: shape of the fix | **(a)** Rename the matrix engines to `Matrix-*-legacy`; `Core-*` IDs resolve only through the catalog and gateway; rows under old names are not pooled with rows under new names (C-14) | (b) retire the web matrix mode; (c) only make duplicate registration fail |
| C-06 | Does the polish stage re-count the incoming tour? | **Reuse the known cost.** No re-count; the gateway's independent recomputation is the check (C-06, C-07) | re-evaluate the incoming tour (1 unit) |
| Q6 | Global fraction for paper manifests | No decision needed now: smoke default 0.80 is fixed by design `:187`; paper manifests set it explicitly | |

### 4.2 Points raised by the GA/PSO investigation (owner decisions 2026-10-19)

| # | Point | Decision | Rejected options (short) |
|---|---|---|---|
| P1 | Which GA/PSO becomes canonical | **Pure plus memetic GA, both inside Gate C** (changed from the plan's recommendation of pure only). `Core-GA-TSP` and `Core-PSO-TSP` are pure, as in the design table: new solvers on the `BaseTSPSolver` matrix path, operators from the archived Bildiri solvers as reference only, no hidden 2-opt, every evaluation counted (C-16a, C-16b). A new canonical ID `Core-GA-TSP-Memetic-2opt` represents the paper's GA (initial and final 2-opt, all counted; C-16c), a design addition recorded in DECISION_LOG and included in the Gate C conformance test. **No memetic PSO**: the archived PSO's 2-opt use is only recorded (section 1.4) so that the paper text can say which PSO produced its numbers | pure only (memetic GA later); accounting on G1 `tsp_meta_engines` (string routes, uncounted 2-opt); accounting on G2 `numba_metaheuristics` |
| P2 | Bildiri TSP instance list | **The six instances with committed provenance:** berlin52, eil51, st70, kroA100, rd100, eil76 (C-18, C-19) | the YAEM four only |
| P3 | gil262 | **Excluded** (n > 100, E09; no committed source; no download) | add later with a separately approved source |
| C-19 | Align the active Bildiri profile with the paper | **Confirmed:** after GA/PSO are VERIFIED the profile holds 2-opt, 3-opt, Or-opt, GA, PSO, the memetic GA and the current GWO/HHO entries; new rows are not pooled with old ones | |

---

## 5. Out of scope / deferred

| Item | Reason |
|---|---|
| MT6: H10 + M25 (together), H11, M14 | Owner Q4: separate plan right after Gate C, before any paper-scale run. H10, H11 and M14 change SOTA and production results (A14-style no pooling; M14 needs the owner's approval like A14) |
| Package D: statistics, reproducibility manifests with `.sha256`, gap columns, descriptive smoke reports, `summarize_benchmark_rows` protocol check, `pstdev` vs `stdev` (L9) | Design `:451-460`; E12 (gap columns after Gate C; Package D calls `assert_single_pooling_group`) |
| CVRP exact (WP-E9), TSP/ATSP n > 100 (including gil262) | E09 |
| MT1 time-window work (H2-H4, H16, N1, L12) | Production routing, not the academic catalog |
| H17 production import of academic config, H8 storage half, H19 quick runner, M15 production-ready gate, M16 TSPLIB I/O in core | MT4/MT2 contract-change plan (audit `:1560`); A12/A16 already removed the silent and production-process effects |
| H14 polling races, M20 distinct-candidate telemetry | MT7 / LT1 |
| Linking the Bildiri profile to the exact reference | E12: not before Package D |
| A memetic PSO (the paper's PSO used initial, re-initialization and final 2-opt) | Owner P1 (2026-10-19): memetic GA only; the PSO fact is recorded in section 1.4 for the paper text |
| Any paper-scale run (including the paper's 30-run design) | Design `:29, :416`; done later on the stronger computer |

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Hybrid budget leakage or double counting between stages | One shared counter with a stage-capped view (C-05); boundary triplet tests (C-06, C-08); polish reuses the known cost; gateway recomputes cost and checks `evaluations <= B` |
| Behaviour drift in GWO/HHO when adding injection | C-05 is parity-gated on existing fixed/native evidence and `test_numba_jit_parity.py`; no equation change |
| Accounting identity frozen too early (allocation, transfer) | Fixed by the design rules and the 2026-10-19 decision; later changes need a new variant (design `:193`) |
| GA/PSO: the canonical solvers differ from the solvers behind the paper's numbers (the paper's GA and PSO were both memetic, section 1.4) | Pure `Core-GA-TSP`/`Core-PSO-TSP` plus the counted memetic GA (C-16c) as the truthful form of the paper's GA; the paper text states that its published PSO was memetic and that no memetic PSO is rerun; old rows stay `HISTORICAL_UNVERIFIED` (A13) and are never pooled with new ones; the paper must be rerun (design `:474`) |
| GA/PSO atomic phases mis-bounded (overshoot inside a generation or a polish) | Boundary triplets at the generation/iteration phase and inside the memetic GA's initial and final polish; fair validation rejects overshoot (`fairness.py:256`) |
| The memetic GA silently degrades to the pure GA (zero or skipped polish) or reports a wrong schedule | Zero polish rejected before execution (C-04 rule); `polish_policy` derived from executed counts and pinned to initial + final, never periodic (C-16c tests) |
| A design addition (`Core-GA-TSP-Memetic-2opt`) drifts from the normative table without record | DECISION_LOG entry at the C-16c merge; the conformance test lists every extra ID with its decision entry and fails on any unlisted one |
| `Numba-GA` alias users expect the paper's memetic GA | The alias stays mapped to pure `Core-GA-TSP` (design `:142`); the deprecation warning and the C-16c DECISION_LOG entry name the memetic ID |
| JIT variance on Windows | Use `.venv-jit` only; report any JIT skip as a gate failure, not a pass; full verification on the stronger computer before paper runs |
| Editable install runs main-checkout code | Every command sets `PYTHONPATH` to the worktree; briefs require printing `academic_benchmark.__file__` once |
| Catalog merge conflicts | The lead merges `capabilities.py` changes one at a time in Lane C order (C-08, C-09, C-10, C-16a, C-16b, C-16c) |
| Pinned profile tests and the E12 `study.json` LF pin | C-04 and C-19 update them with lead-reviewed notes |
| Golden tables change (`test_fixed_budget_tables_unchanged.py`) | Only C-02 may touch labels; any golden update needs a lead-reviewed note in the commit message |
| Smoke output leaking into the repo or into active reporting | Output directory rules of `fair_pilot._prepare_output_dir`; `git status` check in C-12 and C-15 |
| Results that change across a fix being pooled | Each result-changing item names its affected rows and adds the A14-style note to its tracker row |
| A test run in a fresh worktree creates an empty `tsplib.db`, which turns a skip into a failure | C-01 hardens the skip guard; never copy or reuse the worktree's empty file; the lead removes it with the worktree |
| Python REPL runaway (13.9 GB incident) and process kills | Global constraints at the top of every brief; PID-only kills |

## 7. Confirmed facts vs assumptions

- **Confirmed (file:line above, or the baseline run):** catalog state (8 VERIFIED, 2 CANDIDATE, 4 PLANNED; `capabilities.py:244-332`), gateway call without manifest, counter reset in GWO/HHO, absence of composition code, absence of a study loader and a YAEM profile, the uncounted native memetic 2-opt polish (`gwo_solver.py:126-140`), the three GA/PSO implementations and their missing accounting, the 2-opt use of the archived (paper) GA and PSO (section 1.4), the legacy Bildiri instance list and the committed provenance (section 1.4), M17 gaps, L8 override, M19 boolean labels, H9 duplicate mapping, H10/H11 code paths, and the baseline counts in section 2.
- **Assumptions to re-check in each brief:** no governed CLI/Smart row exists in `benchmark_results` (C-03); no active script imports archive modules (C-01; a grep in this run found none); the YAEM legacy set in Q1 is complete (only the four YAEM config files and their labels were inspected); the Bildiri instance list in P2 comes from config file names, not from the paper text, which names no instance.
