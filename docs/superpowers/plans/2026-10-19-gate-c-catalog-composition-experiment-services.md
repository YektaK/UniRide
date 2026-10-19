# Gate C: Catalog, Composition and Experiment Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan item by item. Steps use checkbox (`- [ ]`) syntax. **This plan is not yet approved.** No item starts before the owner approves the plan and answers the owner questions in section 4 that block it.

**Goal:** Close unification Package C ("catalog, composition, and experiment services", `ACADEMIC_STUDY_UNIFICATION_DESIGN.md:441-449`) so that Gate C ("all capability, accounting, hybrid-boundary, TSP/ATSP, schema, and smoke-pilot tests pass", `:449`) can be declared on recorded evidence.

**Architecture:** Canonical algorithms, the shared objective-evaluation counter and the two-stage composition live in `uniride_core` (design `:47-56`). Academic adapters, study loading, plan expansion, smoke execution, result validation and protocol separation live in `academic_benchmark` (design `:64-75`). Study profiles stay thin JSON (`:77-87`). Production exposure does not change (`:89-93`, `:133`).

**Tech stack (observed in this run):** `.venv-jit` interpreter (Numba JIT available), pytest, Pydantic strict contracts, the immutable capability catalog in `uniride_core/algorithms/capabilities.py`.

**Base:** branch `WIP`, HEAD `559826b5` (2026-10-19). Plan written in worktree `.claude/worktrees/gate-c-plan` on branch `docs/gate-c-plan`.

## Global constraints (every brief that implements an item repeats these)

- **Python on Windows (top of every brief):** never open interactive Python (no bare `python`/`py`, no `python -i`, no `python -` or heredoc). Write scripts to a file under `C:\wt\<name>` and run them with `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`, with `PYTHONPATH` set to the worktree (the editable install points at the main checkout). Use `-c` only for one-liners. Time-limit every command and redirect output to a file. Stop on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only your own PIDs. Temp folders only under `C:\wt\<name>`.
- Never write, copy or delete `academic_benchmark/tsplib_data/tsplib.db*`. Never run AMPL.
- Each item runs in its own worktree and branch (`git worktree add <path> -b <branch> WIP`), red test first, frequent commits, no merge, no push. The lead merges with `--no-ff` after the reviewer's ONAY and passing tests.
- No benchmark runs beyond the tiny smoke cases named in an item. Smoke outputs go to `tmp_path` or `C:\wt\<name>`, never into the repository. Smoke results produce no superiority, causality or proof claims (AGENTS.md).
- Do not change production strategy exposure (`academic_benchmark/tests/test_production_registry_snapshot.py`) or `ExecutionProtocol` in core (DECISION_LOG E12).
- Do not reopen decided questions: A04 (fixed budget primary, native separate), A11 (algorithm IDs unchanged by label work), A13 (historical results labelled, never pooled), A14 (no pooling across result-changing fixes), A16 (benchmark router gate), E12 (academic-layer protocol registry; Package D calls `protocol_registry.assert_single_pooling_group`).
- Each merged item updates the audit tracker (Appendix J of `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md`) for the IDs it closes, and records owner decisions in `docs/DECISION_LOG.md`.

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
| D1e | GWO/HHO Memetic-2opt: fixed claims only | **PARTIAL** | `capabilities.py:266-267` pass `native_evidence=None`; the design table `:125-126` says Native = yes | C1 |
| D1f | GA, PSO: exact-fixed + native | **OPEN** (CANDIDATE) | `capabilities.py:262-263`; no budget plumbing outside GWO/HHO (`grep ObjectiveEvaluationBudget` finds only `gwo_solver.py`, `hho_solver.py`, `objective_budget.py` under `uniride_core/algorithms`) | none |
| D1g | `production_ready` field | **PARTIAL** | Academic field forced `False` (`capabilities.py:77, 110-111`); no production gate (audit M15) | C1 (academic half) |
| D2 | Truthful GWO-3opt / HHO-3opt compositions | **OPEN** | `capabilities.py:275-276` PLANNED; `CompositionKind` (`:44-48`) has no 3-opt or ALNS composition kind; no executor (`grep global_fraction|composite_complete` finds no implementation) | none |
| D2a | GWO-ALNS / HHO-ALNS compositions | **OPEN** | `capabilities.py:277-278` PLANNED | none |
| D3 | Shared budget across stages | **PARTIAL** | Counter exists (`uniride_core/algorithms/objective_budget.py:16-37`); budgeted 3-opt counts its start tour (`academic_benchmark/fairness.py:382-401`) but lives in the academic layer; GWO/HHO build a private counter and reset it on each solve (`gwo_solver.py:73, 153`; `hho_solver.py:83, 223`), so a counter cannot be shared across stages yet; ALNS has an accounted core path that always starts from nearest neighbour (`alns_tsp.py:86-93, 198-211`) | C1-C3 (single-stage) |
| D4 | Result contract and post-run validation | **PARTIAL** | Gateway: `academic_benchmark/core/execution_gateway.py:217-219` (resolve, preflight, execute, validate); fair manifest validation `fairness.py:256`; independent Hamiltonian validator `test_hamiltonian_cycle_validator.py` (WP-E8). Gap: governed CLI/Smart runs never get a manifest (audit H13, `execution_gateway.py:218`); no stage-level (composite) result contract | C1, WP-E8 |
| D5 | Study loading | **PARTIAL** | Schema and strict contract: `academic_benchmark/contracts/study.py:17-26, 58-101`, `academic_benchmark/schemas/study-v1.schema.json`. It rejects CANDIDATE/PLANNED IDs, but it does not check problem families, protocols or backends against claims, does not load dataset manifests, and no code loads or executes a study profile (only contracts and tests import `StudyManifestV1`) | Package A, C1 |
| D6 | Fixed/native separation | **PARTIAL** | Separate manifests and pilots (`fair_pilot.py:41-55`, `native_pilot.py:47-80`); protocol registry with pooling groups (`academic_benchmark/protocol_registry.py:33-60, 96-104`; `test_protocol_registry_pooling.py`). Budget levels are not a pooling key (left to Package D, E12) | WP-E8 (registry), earlier pilots |
| D7 | YAEM active study profile | **OPEN** | `academic_benchmark/studies/` contains only `bildiri2026/study.json`; only dataset manifest is `academic_benchmark/datasets/ft53.json` | none |

### 1.2 Gate C test categories (design `:449`)

| Category | Status | Existing tests (baseline: section 2, "Baseline measured") | Gap |
|---|---|---|---|
| Capability | **PARTIAL** | `test_algorithm_capability_catalog.py`, `test_algorithm_capability_evidence.py`, `test_algorithm_resolution.py`, `test_algorithm_preflight.py`, `test_algorithm_preflight_boundaries.py`, `test_canonical_registry_identity.py`, `test_production_registry_snapshot.py` | No conformance test against the normative table `:116-131`; four PLANNED, two CANDIDATE, two missing native claims |
| Accounting | **PARTIAL** | `test_objective_budget_ownership.py`, `test_fair_comparison_protocol.py`, `test_fair_comparison_scientific_integrity.py`, `test_fair_protocol_v2_metadata.py`, `test_cx04_fair_manifest_validation.py` | No shared-counter test across two stages |
| Hybrid boundary | **OPEN** | none | Design `:386-391`: one below, exactly at, one above an atomic phase; shared counter; fixed and native never aggregated |
| TSP/ATSP | **DONE** for single-stage algorithms | `test_canonical_three_opt_integration.py`, `test_core_tsp_registry.py`, `test_numba_three_opt.py`, `test_numba_registry_matrix.py`, `test_hamiltonian_cycle_validator.py`, `test_seed_atsp_collection.py`, `uniride_core/tests/test_canonical_three_opt.py` | Hybrids need the same TSP/ATSP evidence |
| Schema | **DONE** for v1 | `test_manifest_contracts.py`, `test_bildiri_study_profile.py`, `python -m academic_benchmark.contracts.export_schemas check` | Composite result fields and a YAEM profile are not covered |
| Smoke pilot | **PARTIAL** | `test_fair_pilot_cli.py`, `test_run_smoke_benchmark.py`, `test_sqlite_matrix_native_smoke.py`, `test_seed_smoke_datasets.py`, `test_mutation_proof_gateway.py` | No study-profile-driven smoke; no hybrid smoke |

### 1.3 Open audit findings in Package C scope (re-verified)

| ID | Live state | Package C? |
|---|---|---|
| H13 | Gateway calls `executor(problem, params, seed, run_idx)` without a manifest (`execution_gateway.py:217-218`); seeds `42 + run_idx` (`smart_benchmark.py:666`), `1000 + combo_idx*100 + run_idx` (`cli_engine.py:820, 962`) | **Yes** (governed entry points are part of the experiment services) |
| M19 | `polish_policy` is set from the `polish_enabled` boolean, not from executed polish (`registry_setup.py:778-782`); Bildiri profile sets `polish_iters: 0, final_polish_iters: 0` for both memetic IDs (`studies/bildiri2026/study.json:14, 16`) | **Yes** (truthful composition metadata) |
| L8 | Local-search executor derives termination from counters, not `search.termination_reason` (`registry_setup.py:222-227`) although the budgeted results carry one (`objective_budget.py:58, 85, 117`) | **Yes** (truthful result contract) |
| M17 | No `archive/__init__.py`; generic markers lack `archive.` (`uniride_core/tests/test_archive_boundaries.py:8-13`) | **Yes** (evidence integrity; WP-E8 residual) |
| H9 | `engine_factory.py:29-33` maps `Core-TwoOpt-TSP`, `Core-GWO-TSP`, `Core-HHO-TSP`, `Core-GA-TSP`, `Core-PSO-TSP` to matrix engines; `engine_core.py:181-185` overwrites duplicates silently; `registry_setup.py:793-833` keeps old executors silently when the Numba import fails | **Yes**, shape depends on owner Q10 |
| L9 (part) | `make_deterministic_seed` hashes the algorithm name (`benchmark_utils.py:672-678`); pilots use `pstdev` (`fair_pilot.py:486`, `native_pilot.py:428`). The global `random.seed` items are gone (H12 fix: `registry_setup.py:408`, `cli_engine.py:608` now use local generators) | seed helper: yes; `pstdev`: Package D (descriptive statistics) |
| H10 | SOTA layer 3 calls the forbidden kernel `_nb._three_opt_improve_atsp_numba` (`uniride_core/algorithms/sota_tsp/ls_engine.py:146-150`) | Contract violation of `CANONICAL_THREE_OPT_DESIGN.md:95-97`, but no catalog algorithm reaches it (ALNS does not import `ls_engine`); owner Q4 |
| H11 | Wall-clock stops: `ls_engine.py:203, 216`; `e2bso_tsp.py:240, 321, 325` | Same as H10 (SOTA-* only); owner Q4 |
| M14, M25 | Production hybrid 3-opt `_three_opt_cases` (`local_search.py:168, 234`); canonical 3-opt dedup by cycle keys (`three_opt.py:89-101, 150-171`) | MT6; M25 affects hybrid runtime, not correctness; owner Q4 |
| H19, M15, M16 | Quick runner rescoring (`optimizer_api/benchmark_runner.py:172, 473`; `routers/benchmark.py:331-334`); no production gate; core owns TSPLIB I/O | MT4/MT2, out of scope (section 5) |

---

## 2. Gate C acceptance definition

Gate C is met when **all** of the following hold on one commit of `WIP`, run in `.venv-jit` with `PYTHONPATH` set to the checkout under test, and the exact counts are recorded in DECISION_LOG and `docs/UNIRIDE_WORKSTATE.md`:

1. **Catalog conformance.** A new test `academic_benchmark/tests/test_gate_c_normative_catalog.py` checks every row of design `:116-131` against the catalog: ID, label, problems {TSP, ATSP}, a VERIFIED fixed claim with exact accounting, a VERIFIED native claim, `production_ready=False`. Rows the owner defers (Q2 GA/PSO, Q3 memetic-2opt native) are listed in the test with the DECISION_LOG entry ID that defers them; any other gap fails.
2. **Hybrid boundary tests pass** (item C-08/C-09): shared counter, one below / exactly at / one above an atomic phase, global cap `floor(B*0.80)`, polish gets `B - used_global`, polish failure fails the run, fixed and native composite rows refuse to pool.
3. **Governed entry points produce validated results** (item C-03): one governed CLI run and one governed Smart run on a 6-8 node in-memory matrix.
4. **Schema snapshots current:** `python -m academic_benchmark.contracts.export_schemas check` exits 0.
5. **Study profiles:** `bildiri2026` and `yaem2026` load through the study service and pass study-level capability preflight (item C-11, C-13).
6. **Smoke pilot:** each study runs a smoke plan (item C-12): one or two instances, `run_count` from the profile capped at 3 in smoke mode, the lowest budget level, outputs to `tmp_path`, every row validated by the independent Hamiltonian validator, fixed and native rows written to separate files, `assert_single_pooling_group` passes per file. "Pass" means the run completes with every row valid and the outputs well formed. It does not mean any algorithm is better, and the smoke report says so.
7. **Suites:**
   - `academic_benchmark/tests -m "not requires_ampl"`: all pass, no skip of an evidence test (the 3 streamlit skips seen at E12 are acceptable if they recur, and are listed).
   - `uniride_core/tests`: pass, with optional-solver environment failures (OR-Tools absent from `.venv-jit`) listed separately from source defects (design `:412`).
   - The 3-opt regression command of `CANONICAL_THREE_OPT_DESIGN.md:122-126` plus any new canonical 3-opt test file.
   - `academic_benchmark/tests/test_production_registry_snapshot.py` unchanged and passing.
   - `git diff --check` clean.
8. **No artifacts:** `git status --short` shows no generated result files after the suites.

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
| `academic_benchmark/tests -m "not requires_ampl"` | **1527 passed, 1 failed, 3 skipped**, 42 warnings, 464.8 s. The failure is an environment artifact, not a Package C defect: `test_exact_published_tours.py::test_the_real_database_published_tours_match_the_coordinates_of_the_verification_set` skips only when `tsplib.db` is absent (`test_exact_published_tours.py:107-108`), but earlier in the same run some test created an empty 4 KB `academic_benchmark/tsplib_data/tsplib.db` in the fresh worktree (`tsplib_manager.py:69` `sqlite3.connect` creates the file; audit M16 "created on first read"), so the test ran against an empty file (`no such table: problems`, `scripts/run_exact_tsp_reference.py:217`). In the main checkout, which has the real database, this test passes (merge `bad28413`). The skip guard should check for the `problems` table, not file existence (C-01 brief may include this one-line hardening; it is a test-order hazard for CI and fresh worktrees). |
| 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:122-126`) plus `uniride_core/tests/test_canonical_three_opt.py`, `academic_benchmark/tests/test_canonical_three_opt_integration.py` (7 files) | **58 passed**, 12 warnings, 4.9 s |
| `uniride_core/tests/test_archive_boundaries.py` | **2 passed**, 9.5 s |
| `python -m academic_benchmark.contracts.export_schemas check` | exit 0 (snapshots current) |

The `uniride_core/tests` full suite was not run for this plan (its OR-Tools split needs a separate environment note); item C-15 runs it. Gate C runs should be made in a checkout that has the real `tsplib.db`, or after the skip guard is hardened; the worktree's empty `tsplib.db` must not be copied anywhere.

---

## 3. Remaining work items

Dependency order and parallel lanes:

```text
Lane A (parallel, start immediately):  C-01 M17   C-02 L8   C-03 H13   C-04 M19 (needs Q3)
Lane B (core, serial):                  C-05 shared budget -> C-06 composition engine + 3-opt polish -> C-07 ALNS polish entry
Lane C (catalog, serial; one writer of capabilities.py at a time):
                                         C-08 3-opt hybrids (after C-05, C-06) -> C-09 ALNS hybrids (after C-07) -> C-10 memetic-2opt native (Q3)
Lane D (services):                      C-11 study service (parallel with Lane B) -> C-12 study smoke runner (after C-11; hybrids join when C-08/C-09 land)
                                         -> C-13 YAEM profile + dataset manifests (after C-08, C-09, C-11; Q1)
Lane E (owner-gated):                   C-14 H9 (Q10)   C-16 GA/PSO (Q2)   C-17 MT6 3-opt track (Q4)
Close:                                  C-15 Gate C close (after all required items)
```

Model and review guidance per CLAUDE.md: Lane A items are small (one developer, Sonnet reviewer). C-05 to C-09 change accounting or algorithm identity: developer Sonnet, reviewer **Opus**. C-11 to C-13: developer Sonnet, reviewer Sonnet. Suggested tool-call ceiling per item: about 12-25 (requested, not enforced).

### C-01: Archive namespace hardening (M17)

- [ ] **Goal:** `import archive` and `import archive.academic_benchmark...` fail with `ImportError`; generic boundary markers include `archive.`; scans include dynamic `importlib.import_module("archive...")` strings and root/`scripts` Python files.
- **Files:** create `archive/__init__.py` (raises `ImportError` with a pointer to `QUARANTINE.md`); modify `uniride_core/tests/test_archive_boundaries.py:7-13`; `academic_benchmark/tests/test_yaem_quarantine_boundary.py` (dynamic-import case). Same branch, separate commit: `academic_benchmark/tests/test_exact_published_tours.py:107-108` skips unless the `problems` table exists (see the baseline note in section 2).
- **Red test first:** `test_archive_package_is_not_importable` (subprocess `-c "import archive"` must fail) and a planted-string fixture for the dynamic scan; both fail before the change.
- **Acceptance:** new tests pass; `test_archive_manifest.py`, `test_archive_manifest_line_endings.py`, `test_archive_manifest_polish.py`, `test_historical_quarantine.py`, `test_quarantine_round2.py` still pass (the new file sits outside both legacy manifests; check that no manifest test counts files at `archive/` root).
- **Closes:** M17. **Risk:** low; a test or script that reads archive files by import (not by path) would break; grep first. **Changes academic results:** no.

### C-02: Truthful local-search termination (L8)

- [ ] **Goal:** the 2-opt/3-opt/Or-opt fixed-budget executor reports `search.termination_reason` instead of re-deriving it.
- **Files:** `academic_benchmark/core/registry_setup.py:222-227`; test in `academic_benchmark/tests/test_fair_protocol_v2_metadata.py` or a new `test_l8_termination_reason.py`.
- **Red test first:** a 6-node matrix where the search stops on `no_improving_move` at exactly `max_iterations` passes; the current code labels it `max_iterations`.
- **Acceptance:** red test green; golden tables (`test_fixed_budget_tables_unchanged.py`) unchanged or updated with a lead-reviewed note if a frozen row changes its label.
- **Closes:** L8. **Risk:** low. **Changes academic results:** costs and evaluation counts no; the `termination_reason` label can change. Termination-reason tallies from before and after the fix are not pooled (A14 rule, recorded in the tracker row).

### C-03: Governed CLI and Smart runs (H13)

- [ ] **Goal:** governed CLI and Smart runs produce validated canonical results with contract seeds.
- **Files:** `academic_benchmark/core/execution_gateway.py:190-225` (inject `fair_comparison` or `native_comparison` built from the decision and a caller base seed); `academic_benchmark/smart_benchmark.py:660-668`, `academic_benchmark/cli_engine.py:815-822, 955-970` (seed from `FairComparisonManifest.paired_seed`, `fairness.py:242-253`); `academic_benchmark/benchmark_utils.py:672-678` (delete or guard `make_deterministic_seed`, L9); tests in `test_smart_benchmark_preflight.py`.
- **Red test first:** governed Smart run of `Core-TwoOpt-TSP`, `ALNS-TSP` and `Core-GWO-TSP-Pure` on a 7-node matrix raises `ResultContractViolation` today (audit H13 evidence); expected: validated `FairRunResult`, identical seed and `seed_group` across algorithms for one (problem, replicate).
- **Acceptance:** red tests green; non-governed (`NON_C1_ROUTING`) tasks keep their six-field tuples and seeds (C1 final-review constraint, `2026-07-29-c1-final-review-fixes.md` Global Constraints).
- **Closes:** H13; L9 seed-helper bullet. **Risk:** medium (two entry points, persistence metadata). **Changes academic results:** only for governed runs, which today always fail closed (assumption to re-check in the brief: no governed CLI/Smart row exists in `benchmark_results`); legacy seeds of non-governed runs stay unchanged.

### C-04: Memetic-2opt truthfulness (M19)

- [ ] **Goal:** a memetic configuration with zero executed polish is rejected; `polish_policy` and the "polish ran" flags are derived from executed polish counts; the polish schedule is recorded in the result.
- **Files:** `academic_benchmark/core/registry_setup.py:740-782`; `uniride_core/algorithms/tsp_matrix_metaheuristics/gwo_solver.py:116-137` and `hho_solver.py` (expose executed polish counts in `extra_stats`, no equation change); `academic_benchmark/studies/bildiri2026/study.json:14, 16` per Q3; tests `test_fair_protocol_v2_metadata.py`, `test_bildiri_study_profile.py`.
- **Red test first:** `Core-GWO-TSP-Memetic-2opt` with `polish_iters=0, final_polish_iters=0` is accepted and labelled memetic today; expected: `ValueError` before execution. A second test: executed polish counts appear in `polish_policy`.
- **Acceptance:** red tests green; GWO/HHO parity tests (`test_numba_jit_parity.py`) unchanged.
- **Closes:** M19. **Risk:** low-medium; the Bildiri profile changes (owner Q3). **Changes academic results:** no cost change for valid configurations. Smoke rows produced from the zero-polish Bildiri profile are not pooled with rows from the corrected profile.

### C-05: Injectable shared objective counter for pure GWO/HHO (core, no behaviour change)

- [ ] **Goal:** `GWOOptimizer`/`HHOOptimizer` accept an injected `ObjectiveEvaluationBudget` plus a stage cap, and do not reset an injected counter. Default behaviour (own counter) stays identical.
- **Files:** `uniride_core/algorithms/objective_budget.py` (a stage-capped view over one shared counter: `can_spend` respects both the stage cap and the total limit); `gwo_solver.py:59-73, 150-170`; `hho_solver.py:83, 223`; tests `uniride_core/tests/test_objective_budget_stage_cap.py` (new) and the existing GWO/HHO parity fixtures.
- **Red test first:** a shared counter at `used=10`, limit 100, stage cap 60: pure GWO must stop with `used <= 60` and must not reset `used` to 0 (`gwo_solver.py:153` resets it today).
- **Acceptance:** red test green; every existing fixed and native GWO/HHO evidence test and `test_numba_jit_parity.py` pass unchanged (route, cost, evaluations, termination, backend), so relocation parity (design `:239`) holds.
- **Closes:** none directly (prerequisite of D2/D3). **Risk:** medium (JIT path; atomic population phase rule, fairness `:52-64`). **Changes academic results:** no (parity-gated).

### C-06: Two-stage composition engine with canonical 3-opt polish (core)

- [ ] **Goal:** one core function implements design `:181-203` for a pure global stage followed by one polish stage, fixed and native.
- **Files:** create `uniride_core/algorithms/composition.py`; move `improve_three_opt_budgeted` from `academic_benchmark/fairness.py:382-470` to `uniride_core/algorithms/objective_budget.py` next to the budgeted 2-opt/Or-opt (keep a re-export in `fairness.py`); tests `uniride_core/tests/test_composition_engine.py` (new), existing 3-opt tests.
- **Rules to implement (design `:183-191`):** global stage = pure GWO/HHO with no hidden polish; polish once on the best validated global tour; separate `global`/`polish` parameter namespaces with no implicit defaults in paper-scale manifests; `global_fraction` explicit (smoke default 0.80, global cap `floor(B*0.80)`, polish gets `B - used_global`); one shared counter; deterministic 3-opt records no secondary seed; global failure fails the composition; polish exception or invalid tour fails the run; result records stage IDs, parameters, seeds, allocated and consumed evaluations, termination reasons, `polish_changed_tour`. Native mode (`:195-201`): no cap, separate stage counts summed for description, aggregate termination `composite_complete` only when both stages complete.
- **Lead decision inside this item (recorded in DECISION_LOG):** whether the polish stage re-evaluates the incoming tour (1 unit, as `fairness.py:401` does today) or reuses the cost already counted by the global stage. Recommendation: reuse the known cost (fairness design `:46-50`: "reuse the solver's known objective where possible"), with the gateway's independent recomputation as the check. Precedent: the memetic 2-opt polish already passes `initial_cost` to `improve_two_opt_budgeted` (`gwo_solver.py:119-123`).
- **Red test first:** boundary triplet with a stub global stage whose atomic phase needs `k` units: remaining `k-1` (phase refused, termination `evaluation_budget_exhausted`), `k` (runs, total = B), `k+1`; polish with 0 remaining returns the global tour, `polish_changed_tour=False`; polish raising fails the run; the moved 3-opt function is byte-identical in behaviour (parity on the existing fixtures).
- **Acceptance:** red tests green; 3-opt regression command passes; `uniride_core` imports nothing from `academic_benchmark` (`test_core_import_boundary` or equivalent).
- **Closes:** design D2/D3 (engine half). **Risk:** high (accounting identity; design `:193`: a later change of timing, transfer or allocation needs a new variant). **Changes academic results:** no existing result (new identities only).

### C-07: ALNS polish entry from a given tour (core)

- [ ] **Goal:** an accounted ALNS entry that starts from a supplied complete tour and a supplied stage counter, with seed `SHA-256(protocol_version, run_seed, "polish")` (design `:189`), leaving the standalone `ALNS-TSP` path unchanged.
- **Files:** `uniride_core/algorithms/sota_tsp/alns_tsp.py:86-93, 198-211`; `uniride_core/algorithms/composition.py` (ALNS polish adapter); tests `uniride_core/tests/test_alns_polish_entry.py` (new); `academic_benchmark/tests/test_alns_c3_evidence.py` must stay green.
- **Red test first:** supplied tour is the start (first evaluated tour equals it), counter shared, derived seed independent of Python `hash()` and stable across processes (subprocess with two `PYTHONHASHSEED` values).
- **Acceptance:** red tests green; all four ALNS C3 evidence tests unchanged.
- **Closes:** prerequisite of D2a. **Risk:** medium. **Changes academic results:** no.

### C-08: Promote GWO-3opt and HHO-3opt

- [ ] **Goal:** `Core-GWO-TSP-Memetic-3opt` and `Core-HHO-TSP-Memetic-3opt` become VERIFIED with TSP/ATSP fixed and native claims backed by named evidence tests.
- **Files:** `uniride_core/algorithms/capabilities.py:44-48` (new `CompositionKind` value, name per Q5), `:275-276`; `academic_benchmark/core/registry_setup.py` (executors using C-06); `academic_benchmark/fairness.py` and `native_protocol.py` (composite result validation: stage fields, `evaluations == sum(stage evaluations)`, cap compliance); `academic_benchmark/core/execution_gateway.py` (`validate_preflighted_result` accepts the composite contract); `fair_pilot.py:44-50`, `native_pilot.py:60-80` allowlists; schema for composite run fields if the run contract changes (`academic_benchmark/contracts/run.py`, then `export_schemas write` and a lead-reviewed snapshot diff); tests `academic_benchmark/tests/test_hybrid_3opt_evidence.py` (new), `test_hybrid_budget_boundaries.py` (new).
- **Red test first:** `find_capability_claim("Core-GWO-TSP-Memetic-3opt", ...)` returns a claim (fails while PLANNED); boundary triplet through the real executor; ATSP directed-cost preservation (asymmetric 7-node fixture, independent closed-cycle cost); deterministic replay with the same seed; fixed and native composite rows fail `assert_single_pooling_group` together.
- **Acceptance:** red tests green; catalog drift tests (`test_algorithm_capability_catalog.py`) pass; production snapshot unchanged.
- **Closes:** D2 (3-opt half). **Risk:** high (new identities, scientific claims). **Changes academic results:** new algorithms only; no existing result changes.

### C-09: Promote GWO-ALNS and HHO-ALNS

- [ ] Same shape as C-08, with ALNS polish (C-07), required strict ALNS parameters under the `polish` namespace (`fairness.py:45`, C3 constraint list), and a recorded derived polish seed. New tests `test_hybrid_alns_evidence.py`. Depends on C-07 and on C-08 (same files; avoids catalog conflicts). **Closes:** D2a. **Risk:** high. **Changes academic results:** new algorithms only.

### C-10: Native claims for GWO/HHO Memetic-2opt (if Q3 says yes)

- [ ] **Goal:** add the native claims that the design table `:125-126` requires.
- **Files:** `capabilities.py:266-267` (`native_evidence=`), `test_algorithm_capability_evidence.py` (new native evidence functions), `native_pilot.py:60-80` allowlist.
- **Red test first:** `find_capability_claim(..., NATIVE_TERMINATION, ...)` for memetic-2opt returns a claim.
- **Acceptance:** native evidence tests green; memetic-2opt native evaluation counts include the polish. Confirmed gap: outside fair mode `_polish` runs the Numba kernel `_two_opt_improve_atsp_numba` and its candidate evaluations do not go through the counter (`gwo_solver.py:126-140`; same pattern in `hho_solver.py`), so a native claim with `exact_objective_accounting=True` needs counted polish first (either the budgeted Python 2-opt with an unlimited counter, as fair mode does at `:119-127`, or a counted kernel with JIT parity).
- **Closes:** D1e; L9 polish-count bullet. **Risk:** medium. **Changes academic results:** native memetic evaluation counts change (and costs if the polish implementation changes); earlier native memetic rows are not pooled with later ones.

### C-11: Study service (load, resolve, preflight, expand)

- [ ] **Goal:** `academic_benchmark/studies/service.py` loads a study JSON, validates it with `StudyManifestV1`, loads each dataset manifest (`DatasetManifestV1`, repository-relative path, checksum verified against the referenced file), checks that every (algorithm, problem family, protocol, backend policy) the study needs has a VERIFIED claim (`find_capability_claim`), and expands an immutable plan: (dataset, algorithm, protocol, budget level, replicate, paired seed, seed group).
- **Files:** new `academic_benchmark/studies/service.py`, `academic_benchmark/studies/__init__.py`; tests `academic_benchmark/tests/test_study_service.py`.
- **Red test first:** a profile that lists `Core-GWO-TSP-Memetic-2opt` in `secondary_protocol.algorithm_ids` passes `StudyManifestV1` today but has no native claim; the service must reject it. Also: unknown dataset ref, checksum mismatch, absolute path, alias ID, budget levels not pooled (each plan row carries its level).
- **Acceptance:** Bildiri profile loads and expands; plan seeds equal `FairComparisonManifest.paired_seed` for the same inputs.
- **Closes:** D5. **Risk:** medium. **Changes academic results:** no.

### C-12: Study smoke runner (fixed/native separated, validated)

- [ ] **Goal:** run an expanded plan in smoke mode through `execute_preflighted`, validate each result with the independent Hamiltonian validator, write fixed and native rows to separate files under a caller-provided directory outside the repository (reuse `fair_pilot._prepare_output_dir` rules, `fair_pilot.py:283-300`), and refuse to write a file whose rows fail `assert_single_pooling_group` or mix budget levels.
- **Files:** `academic_benchmark/studies/smoke.py` (new); reuse `fair_pilot.py`/`native_pilot.py` record builders rather than copying them; tests `academic_benchmark/tests/test_study_smoke.py`.
- **Red test first:** runner on the Bildiri profile, `ft53`, budget 100, 1 replicate, into `tmp_path`: two files, all rows valid; a forced invalid tour from a stub executor stops aggregation and records a failed-run row (design `:360`); smoke report text contains no ranking words (reuse the A15 wording check).
- **Acceptance:** red tests green; no file appears in `git status`.
- **Closes:** D4 (study path), D6 (study path), Gate C criterion 6. **Risk:** medium. **Changes academic results:** no (smoke only).
- **Note:** reproducibility manifests (`RunManifestV1` plus detached `.sha256`) are Package D (`:453`); the runner records only what the pilots already record.

### C-13: YAEM active study profile and dataset manifests

- [ ] **Goal:** `academic_benchmark/studies/yaem2026/study.json` (status `draft`, smoke-only output policy) selecting canonical IDs, problem families, primary fixed and secondary native protocols, run counts and budget levels per Q1; dataset manifests for the chosen instances.
- **Files:** `academic_benchmark/studies/yaem2026/study.json`; `academic_benchmark/datasets/<instance>.json` for each instance (sources: the committed `.tsp` files in `academic_benchmark/tsplib_data/tsp/` and the optimum provenance in their manifest from the E12 companion task; no download, no `tsplib.db` write); tests `academic_benchmark/tests/test_yaem_study_profile.py`.
- **Red test first:** the profile loads through C-11 and passes study-level preflight; `GWO-LKH`/`HHO-LKH` in any field fail with the truthful replacement (design `:149-150, 251`); no reference to `archive/` paths.
- **Acceptance:** C-12 smoke run of the YAEM profile on one instance at the lowest budget passes.
- **Closes:** D7. **Risk:** low-medium (scope is the owner's call). **Changes academic results:** no.

### C-14: One ID, one implementation (H9; shape per Q10)

- [ ] **Goal:** every canonical ID resolves to exactly one callable in every entry point; duplicate registration raises; a failed Numba import fails closed.
- **Files:** `uniride_core/algorithms/engine_factory.py:28-44, 94-133`; `academic_benchmark/engine_core.py:181-185`; `academic_benchmark/core/registry_setup.py:789-838`; web matrix mode names (`optimizer_api/routers/benchmark.py` matrix path) per Q10.
- **Red test first:** parametrized test across CLI, `AlgorithmRegistry`, `engine_factory` and the web matrix mode: `Core-GWO-TSP` maps to two different callables today; `AlgorithmRegistry.register` twice with one name succeeds today.
- **Acceptance:** red tests green; production snapshot unchanged unless Q10 says otherwise.
- **Closes:** H9. **Risk:** medium-high (web academic matrix mode, stored names). **Changes academic results:** stored `algorithm` strings of matrix-mode rows change; rows written under the old names are not pooled with rows under the new names (A14 rule; A13 labelling already covers pre-2026-10-13 rows).

### C-15: Close Gate C

- [ ] **Goal:** add `test_gate_c_normative_catalog.py` (section 2, criterion 1), run the full acceptance block, record counts, update Appendix J rows, add a DECISION_LOG entry ("Gate C met at `<sha>`", deferred rows and their decision IDs), update `docs/UNIRIDE_WORKSTATE.md` (ACAD-01 row).
- **Red test first:** the conformance test fails while any required row is PLANNED or CANDIDATE without a deferral entry.
- **Acceptance:** section 2 criteria 1-8 hold on one commit. **Risk:** low. **Changes academic results:** no.

### Owner-gated items (not required for Gate C unless the owner says so)

- **C-16 GA/PSO promotion (Q2).** GA and PSO have no budget plumbing; a separate evidence plan in the style of C2/C3 (exact accounting, deterministic replay, TSP/ATSP fixed and native) is needed. Large. Parallel with Lane C when approved; touches `capabilities.py:262-263` (serialize with C-08 to C-10).
- **C-17 MT6 3-opt track (Q4).** H10 (replace the kernel call at `ls_engine.py:146-150` with `improve_three_opt`), M25 (speed-up behind a candidate-set and order parity test, so evaluation counts do not change), H11 (iteration or evaluation termination, optional reported wall-clock deadline), M14 (production hybrid uses the canonical engine). H10, H11 and M14 change SOTA and production results: A14-style no pooling across the fix; M14 also changes production plans and needs the owner's approval like A14.

---

## 4. Owner questions

| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | Scope of the YAEM active profile | (a) mirror the legacy YAEM set: berlin52, eil51, st70, kroA100 (symmetric TSP) with 2-opt, 3-opt, Or-opt, GWO/HHO Pure, GWO/HHO-2opt, GWO/HHO-3opt, GWO/HHO-ALNS (legacy configs in `archive/academic_benchmark/yaem2026_legacy/configs/`, labels counted there; `GWO-LKH`/`HHO-LKH` become the 3-opt hybrids); (b) a minimal draft (one instance, the four hybrids plus their pure globals) now, full selection later; (c) defer the profile until a paper plan exists | (a) as a `draft`, smoke-only profile: it uses only instances already committed with provenance (E12 companion) and makes the profile meaningful without running anything large. Budget levels and run counts stay placeholders marked draft until the paper plan. |
| Q2 | GA/PSO in Gate C? The normative table (`:120-121`) lists them; no active or YAEM-legacy configuration uses them | (a) promote them before Gate C (C-16); (b) record a deferral in DECISION_LOG and let Gate C pass with GA/PSO CANDIDATE; (c) remove them from the target table (design change) | (b): they need new accounting code in two solvers, no study uses them, and the conformance test lists the deferral explicitly. |
| Q3 | Memetic-2opt: native claims and the Bildiri zero-polish profile | (a) add native claims (C-10) and give the Bildiri memetic entries a small non-zero polish; (b) add native claims and drop memetic IDs from the Bildiri profile; (c) defer native claims (deferral entry), fix only M19 | (a): the table requires native support, and the profile then tests what its labels say. |
| Q4 | H10/H11/M14/M25 (MT6) timing | (a) inside Gate C; (b) a separate MT6 plan right after Gate C, before any paper-scale run; (c) H10+M25 together now in a parallel lane, H11/M14 later | (b): no catalog algorithm reaches the forbidden kernel or the wall-clock stops, so Gate C does not need them; but H10 violates an approved contract, so it should not wait past Gate C. H10 and M25 land together (audit H10 fix sketch). |
| Q5 | Name of the composition kind for the four hybrids. IDs stay as in the normative table (`Core-*-Memetic-3opt`, `Core-*-Memetic-ALNS`), but these hybrids polish once at the end, unlike memetic-2opt, which polishes periodically | (a) keep IDs, add `CompositionKind` values `global_then_final_3opt` / `global_then_final_alns`, and show "final polish once" in labels; (b) rename the IDs (design change, new decision) | (a): IDs are normative and changing them is a design change; the kind and the label carry the truthful semantics. |
| Q10 | H9: should the matrix-surface TSP IDs stay production-only? (audit `:1788`) | (a) rename matrix engines to `Matrix-*-legacy`, canonical `Core-*` IDs only through catalog and gateway (audit fix sketch); (b) retire the web `academic_matrix` mode; (c) keep names and only make duplicate registration fail | (a): one ID, one implementation; the web matrix mode keeps working under truthful names. |
| Q6 | Global fraction for paper manifests | Smoke default 0.80 is fixed by design `:187`; paper levels must be explicit | No decision needed now; record "explicit in paper manifests" in the YAEM profile when it leaves draft. |

---

## 5. Out of scope / deferred

| Item | Reason |
|---|---|
| Package D: statistics, reproducibility manifests with `.sha256`, gap columns, descriptive smoke reports, `summarize_benchmark_rows` protocol check, `pstdev` vs `stdev` (L9) | Design `:451-460`; E12 (gap columns after Gate C; Package D calls `assert_single_pooling_group`) |
| CVRP exact (WP-E9), TSP/ATSP n > 100 | E09 |
| MT1 time-window work (H2-H4, H16, N1, L12) | Production routing, not the academic catalog |
| H17 production import of academic config, H8 storage half, H19 quick runner, M15 production-ready gate, M16 TSPLIB I/O in core | MT4/MT2 contract-change plan (audit `:1560`); A12/A16 already removed the silent and production-process effects |
| H14 polling races, M20 distinct-candidate telemetry | MT7 / LT1 |
| Linking the Bildiri profile to the exact reference | E12: not before Package D |
| Any paper-scale run | Design `:29, :416`; done later on the stronger computer |

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Hybrid budget leakage or double counting between stages | One shared counter with a stage-capped view (C-05); boundary triplet tests (C-06, C-08); gateway recomputes cost and checks `evaluations <= B` |
| Behaviour drift in GWO/HHO when adding injection | C-05 is parity-gated on existing fixed/native evidence and `test_numba_jit_parity.py`; no equation change |
| Accounting identity frozen too early (polish re-evaluation, allocation) | Decide once in C-06, record in DECISION_LOG; later changes need a new variant (design `:193`) |
| JIT variance on Windows | Use `.venv-jit` only; report any JIT skip as a gate failure, not a pass; full verification on the stronger computer before paper runs |
| Editable install runs main-checkout code | Every command sets `PYTHONPATH` to the worktree; briefs require printing `academic_benchmark.__file__` once |
| Catalog merge conflicts | Lane C is serial; only one open branch edits `capabilities.py` at a time |
| Golden tables change (`test_fixed_budget_tables_unchanged.py`) | Only C-02 may touch labels; any golden update needs a lead-reviewed note in the commit message |
| Smoke output leaking into the repo or into active reporting | Output directory rules of `fair_pilot.py:283-300`; `git status` check in C-12 and C-15 |
| Results that change across a fix being pooled | Each result-changing item names its affected rows and adds the A14-style note to its tracker row |
| A test run in a fresh worktree creates an empty `tsplib.db`, which turns a skip into a failure | Harden the skip guard (check the `problems` table); never copy or reuse the worktree's empty file; the lead removes it with the worktree |
| Python REPL runaway (13.9 GB incident) and process kills | Global constraints at the top of every brief; PID-only kills |

## 7. Confirmed facts vs assumptions

- **Confirmed (file:line above, or the baseline run):** catalog state (8 VERIFIED, 2 CANDIDATE, 4 PLANNED; `capabilities.py:244-332`), gateway call without manifest, counter reset in GWO/HHO, absence of composition code, absence of a study loader and a YAEM profile, the uncounted native memetic 2-opt polish (`gwo_solver.py:126-140`), M17 gaps, L8 override, M19 boolean labels, H9 duplicate mapping, H10/H11 code paths, and the 562-test focused baseline.
- **Assumptions to re-check in each brief:** no governed CLI/Smart row exists in `benchmark_results` (C-03); no archive file is imported as a module by an active script (C-01; a repository grep for `import archive`, `from archive` and `import_module("archive` outside `archive/` and tests found none in this run); the YAEM legacy set in Q1 is complete (only the four config files and their labels were inspected).
