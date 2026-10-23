# Gate D: Analysis, Documentation and Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan item by item. Steps use checkbox (`- [ ]`) syntax. **Status: DRAFT for owner approval (DECISION_LOG A17, 2026-10-23 decision 1). No Package D work starts before the owner approves this plan and answers the owner questions in section 5.**

**Goal:** Close unification Package D ("analysis, documentation, and publication", `ACADEMIC_STUDY_UNIFICATION_DESIGN.md:451-460`) so that Gate D ("no invalid evidence is reachable from active reporting, local checks are recorded exactly, documentation is consistent, the integration worktree is clean, and the draft PR explicitly awaits powerful-computer verification", `:460`) can be declared on recorded evidence, together with every item that DECISION_LOG explicitly deferred to Package D.

**What Gate D is not:** Gate D does **not** run the paper-scale experiments. The design keeps them out of the remediation (`:29`, `:36`, `:416`, `:466`). Package D builds the tools that paper-scale runs need (a paper mode that refuses draft profiles and dirty trees, run manifests, a cost estimator, guarded statistics) and a procedure by which the owner approves one paper-scale run plan. The runs themselves happen afterwards, on the stronger computer, under that approved plan.

**Architecture:** analysis, manifests, statistics, reports and the run service live in `academic_benchmark` (design `:64-75`); `uniride_core` is not touched except where an item says so (none planned). Study profiles stay thin JSON (`:77-87`). Production exposure does not change (`:89-93`).

**Base:** branch `WIP`, HEAD `8d3cbab0` (2026-10-23). Plan written in worktree `.claude/worktrees/gated-plan` on branch `docs/gate-d-plan`. `origin/WIP` and `WIP` were at the same commit when this plan was written (`git rev-list --left-right --count origin/WIP...WIP` = `0 0`).

**Fact/assumption key used throughout:** **[F]** = verified in live code or a committed record at `8d3cbab0` (file:line given); **[A]** = assumption or inference that the item's developer re-checks first; **[O]** = owner value choice, listed in section 5 and never chosen by a developer.

## Global constraints (every brief that implements an item repeats these)

- **Python on Windows (top of every brief):** never open interactive Python (no bare `python`/`py`/`python3`, no `python -i`, no `python -`, no heredoc or stdin into Python, no `cat > file`). Write scripts to a file under `C:\wt\<name>` and run them with `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`, with `PYTHONPATH` set to the worktree (the editable install points at the main checkout; print `academic_benchmark.__file__` once). Use `-c` only for one-liners if the brief allows it at all. Time-limit every command and redirect output to a file. Stop on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only your own PIDs. Never `git stash`. No checkout/switch in the main checkout. Temp folders only under `C:\wt\<name>`.
- Never write, copy or delete `academic_benchmark/tsplib_data/tsplib.db*`. Never run AMPL. No download of instance files. Never write under `docs/paper/results`.
- Each item runs in its own worktree and branch (`git worktree add <path> -b <branch> WIP`), red test first, frequent commits, no merge, no push. The lead merges with `--no-ff` after the reviewer's ONAY and passing tests.
- No benchmark runs beyond the tiny smoke cases named in an item (in-memory matrices or the smoke slice of a profile, `run_count` capped at 3). Outputs go to `tmp_path` or `C:\wt\<name>`, never into the repository. Smoke results produce no superiority, causality or proof claims (AGENTS.md). The calibration slice of D-04b is the only timing measurement and is not evidence about algorithm quality.
- Do not change production strategy exposure (`academic_benchmark/tests/test_production_registry_snapshot.py`), core `ExecutionProtocol` (E12), any canonical algorithm, the capability catalog, or the study profiles' scientific values (budget levels, run counts, seeds, parameters): those change only by an owner decision (section 5) in a lead-merged commit.
- Do not reopen decided questions: A01, A04 (fixed budget primary, native separate, never pooled), A11, A13 (historical results labelled, never pooled), A14 (no pooling across result-changing fixes), A15, A16, A17 (all Gate C decisions, including the 2026-10-23 owner decisions), E09 (CVRP and n > 100 deferred), E10, E12 (exact rows never pooled; Package D calls `assert_single_pooling_group`).
- Archived code (`archive/academic_benchmark/*_legacy/`) is `REFERENCE_ONLY`: read as history, never imported or executed.
- Each merged item updates Appendix J of `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md` for the IDs it closes and records decisions in `docs/DECISION_LOG.md` (A-series, new entry A18 "Gate D (Package D) plan and owner decisions" created when this plan is merged).

---

## 1. Current state (verified against live code at `8d3cbab0`)

### 1.1 Package D deliverables (design `:453-458`)

| # | Deliverable | Status | Evidence |
|---|---|---|---|
| P1 | Statistically guarded analysis over validated results (`:453`; protocol `:318-335`; integrity tests `:400-404`) | **OPEN** | [F] No omnibus/post-hoc/correction code in `academic_benchmark`, `uniride_core` or `scripts` (grep for `kruskal`, `friedmanchisquare`, `mannwhitneyu`, `wilcoxon`, `holm`, `multipletests` outside tests finds nothing). [F] No statistical library is pinned or installed: `.venv-jit` site-packages hold `numpy`/`numba` but no `scipy`, `statsmodels`, `scikit_posthocs` or `pingouin`; no requirements file names one (`requirements-paper.txt` pins only matplotlib and pillow; `academic_benchmark/jit-benchmark-constraints.txt` pins numpy 2.4.6, llvmlite 0.48.0, numba 0.66.0). [F] The pilots summarize with the population standard deviation: `fair_pilot.py:532`, `native_pilot.py:517` (audit L9 bullet, left to Package D by the Gate C plan section 1.3). [F] The dashboard's statistical-tests tab is disabled (`dashboard.py:155, 300-302`; A09: re-enable only through the Package D analysis service). |
| P2 | Reproducibility manifests (`:454`, `:337-354`) | **PARTIAL (contract only)** | [F] `RunManifestV1` exists (`academic_benchmark/contracts/run.py:65-80`, schema `run-v1.schema.json`) but nothing builds or writes it: its only references are `contracts/__init__.py:3,8` and `export_schemas.py:10,18`. [F] No detached `.sha256` writer or verifier. [F] The smoke runner writes `report.json` with `"mode": "smoke"`, `git` and `environment` dictionaries (`studies/smoke.py:473-475`) from the pilot helpers `fair_pilot._git_metadata` / `_environment_metadata` (`fair_pilot.py:493, 507`), not a `RunManifestV1`. [F] `EnvironmentV1.statistics_library` is a required string (`run.py:29`) although no statistical library exists yet. |
| P3 | Descriptive smoke reports (`:454`) | **PARTIAL** | [F] `run_study_smoke` writes `report.txt`/`report.json` with a no-ranking wording check (`smoke.py:141-145, 366-398, 401-482`) but no descriptive table (by design it "aggregates nothing", `smoke.py:5`). |
| P4 | Synchronize master documentation and migration tables (`:455`) | **OPEN** | [F] `docs/UNIRIDE_WORKSTATE.md:104-107` records Gate C met and "Open before any paper-scale run: the separate MT6 plan ... and Package D". Master documents to synchronize: `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, `UniRide_Ultimate_Audit.md`, `README.md`, the two design documents (stale passages in section 8). |
| P5 | Proportionate automated suites and packaging checks (`:456`) | **Repeatable** | [F] Gate C acceptance run 2026-10-23 (DECISION_LOG A17, line 473): `academic_benchmark/tests -m "not requires_ampl"` 2579 passed, 3 skipped; `uniride_core/tests -m "not requires_ampl"` 2092 passed, 1 skipped, 42 AMPL deselected; 3-opt regression + production snapshot 60 passed. |
| P6 | Fetch and inspect remote divergence; push; draft PR (`:457-458`, `:466`) | **OPEN, meaning stale** | [F] The design assumes an integration branch `codex/reconcile-native-protocol` and "without modifying `WIP` directly" (`:18`, `:30`, `:420`); in practice every package has been merged into `WIP` by the lead and `WIP` is the default branch (`origin/HEAD -> origin/WIP`). See owner question OQ-13. |

### 1.2 Items DECISION_LOG explicitly deferred to Package D

| # | Deferred item | Source | Status at `8d3cbab0` |
|---|---|---|---|
| X1 | `RunManifestV1` plus detached `.sha256` | Gate C plan C-12 note; design `:352` | OPEN (P2) |
| X2 | Gap columns against the exact reference (`exact_reference_v1`) | E12 (DECISION_LOG `:653`) | OPEN. [F] Stage-1 reference rows exist for all 7 Bildiri instances and all 4 YAEM instances: `docs/paper/results/tsplib-exact-reference/stage1-verification/reference.csv` lists burma14, ulysses16, ulysses22, att48, eil51, berlin52, ft53, st70, eil76, pr76, gr96, kroa100, krob100-kroe100, rd100. [F] The pilots compute `gap_pct` from `problem.optimal` (`fair_pilot.py:398, 409, 430`), i.e. the database optimum, not the exact reference. |
| X3 | Link the Bildiri profile to the exact reference | E12 (DECISION_LOG `:656`); A17 C-05 note (`:456`) | OPEN; a Gate C test forbids the link today (A17 `:456`), so D-06 changes that test with review. |
| X4 | Analysis must call `protocol_registry.assert_single_pooling_group` before any summary; `matrix_run_summary.summarize_benchmark_rows` accepts dict rows without a protocol check | E12 lead acceptance (DECISION_LOG `:661`) | OPEN. [F] `matrix_run_summary.py:14` has no protocol check. |
| X5 | `termination_policy` is part of the identity (PSO re-initialization constants do not split a pooling group by themselves) | A17 C-16b note (`:455`) | OPEN |
| X6 | Pure `Core-GA-TSP` rows never pooled with pre-C-16a rows or production `ga`/`ga_split`; enforcement by Package D | A17 GA/PSO promotions note (`:463`) | OPEN |
| X7 | `elapsed_sec` (stage) and `elapsed_ms` (row) dropped from every export identity, identity hash and replay comparison | A17 C-09 note (`:462`); `smoke.comparable_row` already drops them (`smoke.py:104-118`) | PARTIAL (smoke only) |
| X8 | Group fixed rows by **level index** (or scan multiple), never by raw budget across instances | A17 C-19 note (`:468`) | OPEN. [F] `write_rows_file` checks one level per dataset (`smoke.py:177-200`); nothing groups across datasets. |
| X9 | The run service refuses `draft` profiles for paper-scale runs | A17 C-13 note (`:472`) | OPEN. [F] Status is `Literal["draft","active","archived"]` (`contracts/study.py:154`); both profiles are `draft` (`studies/bildiri2026/study.json:5`, `studies/yaem2026/study.json:5`). |
| X10 | A paper plan sets per-stage native limits for composites (design native rule 2) | A17 C-13 note (`:472`) | OPEN, value choice -> OQ-4 |
| X11 | The backend policy is a service argument (default `PREFER_NUMBA_OBJECTIVE`) and must enter the run manifest | A17 C-11 note (`:452`) | OPEN. [F] `AlgorithmRunV1.backend_policy` exists (`run.py:36`). |
| X12 | Persist composite stage records into `AlgorithmRunV1.composition_stages` / `BudgetRecordV1.stage_allocation` | A17 C-08 note (`:460`) | PARTIAL: smoke exports carry `composition` (A17 C-13 note); no manifest yet. |
| X13 | Re-enable dashboard inference only through the Package D service over validated, protocol-homogeneous, `seed_group`-paired rows | A09 (`:390`) | OPEN -> OQ-11 (recommend: stays disabled in Gate D) |
| X14 | Do not pool across result-changing fixes (A14 style): pre/post C-10 native memetic rows, pre/post 2026-10-22 GWO/HHO budget-following schedule, 10000/50000 vs scaled Bildiri profile, Smart vs CLI base seeds, `Core-*` matrix-mode vs `Matrix-*-legacy` rows | A17 notes (`:449`, `:461`, `:465`, `:467`, `:470`) | OPEN: needs an identity that carries code era (D-01) |

### 1.3 Gaps found while planning (facts)

- [F] **Pooling groups are coarser than a comparison cell.** `assert_single_pooling_group` maps fair v1 and fair v2 rows to the same group (`protocol_registry.py:57, 88-89`) and ignores study, dataset, budget level, algorithm configuration, `termination_policy` and code commit (`:99-107`). It is the right guard against fixed/native/exact mixing, not a sufficient analysis key.
- [F] **`analysis_plan_id` resolves nothing.** It is a required string (`contracts/study.py:168`), set to `bildiri2026-reproduction-v1` and `yaem2026-draft-v1` (`studies/bildiri2026/study.json:67`; `studies/yaem2026/study.json:79`); no code reads it (grep outside tests finds only the contract). The design wants statistics predeclared (`:205-216`, `:318-335`).
- [F] **The smoke runner stops at the first failure** (`smoke.py:455`) and has no resume, no paper mode and no clean-tree refusal; design `:354` requires a clean tree for paper-scale mode and `:362` requires atomic writes plus validated resumption.
- [F] **Bildiri secondary (native) protocol covers only `Core-GWO-TSP-Pure` and `Core-HHO-TSP-Pure` with `max_iterations: 2`** (`studies/bildiri2026/study.json:44-48`): a smoke placeholder, not a paper setting (-> OQ-4).
- [F] **YAEM profile still has `base_seed: 2026`** (`studies/yaem2026/study.json:76`) although the owner decided on 2026-10-23 that YAEM gets its own seed and "the lead set 2027" (DECISION_LOG A17 `:474`, decision 2). Either the change sits on an unmerged branch or it was not made (see section 1.4).
- [F] **Dataset identity spelling differs:** profile dataset id `tsplib-kroa100` and manifest file `kroA100.json` (`studies/bildiri2026/study.json:34, 57`) vs exact-reference instance `kroa100` (`reference.csv`). The C-11 identity rule (normalised TSPLIB `NAME` header) must be used for the gap join, not file names.

### 1.4 Prerequisites outside Package D (not Gate D items, but block paper-scale runs or Gate D)

| Item | Source | State | Blocks |
|---|---|---|---|
| MT6 plan: H10 + M25 (together), H11, M14 | A17 Q4 ("before any paper-scale run") | [F] H10, H11 OPEN in Appendix J; no MT6 plan file in `docs/superpowers/plans/` | paper-scale runs (not Gate D) |
| Owner 2026-10-23 decision 2: YAEM `base_seed` 2027 | A17 `:474` | [A] not on `WIP` (`yaem2026/study.json:76` = 2026); lead to confirm where it is | Gate D criterion 6 (profiles match DECISION_LOG) |
| Owner 2026-10-23 decision 3: explicit `max_no_improvement` on fixed-budget paths, missing key refused | A17 `:474` | [A] implementation status not verified (validators list the key, `fairness.py:80, 104, 144, 166, 259`, but whether a missing key is refused was not checked) | paper-scale runs |
| Owner 2026-10-23 decision 4: `Numba-Swap`, `Numba-Hybrid`, `SOTA-*` refuse CVRP/CVRPTW | A17 `:474` | [F] branch `fix/numba-sota-refuse-routing` exists and is checked out in a worktree (in progress) | nothing in Package D |
| Gate C follow-ups: `test_exact_tsp_runner.py` empty-db guard; conformance test A17 window stops at `## ` | A17 `:473` | [A] open | Gate D criterion 9 (suite counts) only if they flake |

---

## 2. Gate D acceptance definition

Gate D is met when **all** of the following hold on one commit of `WIP`, run in `.venv-jit` plus the pinned analysis requirements of D-04 (`PYTHONPATH` = the checkout under test, the main checkout with the real `tsplib.db`), and the exact counts are recorded in DECISION_LOG A18 and `docs/UNIRIDE_WORKSTATE.md` (ACAD-01 row):

1. **Comparison identity (D-01).** `academic_benchmark/tests/test_gate_d_comparison_identity.py` passes: rows that differ in protocol kind, protocol version (fair v1 vs v2), study, dataset (normalised identity), budget level index, algorithm ID, configuration hash (timing fields excluded, `termination_policy` included), evidence class or code commit are refused as one comparison cell; rows equal in all of them are accepted; identity hashes are unchanged when only `elapsed_ms`/`elapsed_sec` differ.
2. **Run manifests (D-02).** Every smoke run of both profiles writes `RunManifestV1` files that validate against `run-v1.schema.json` (or its successor version), each with a detached `<manifest>.sha256`; a verifier recomputes manifest and output checksums; a one-byte change to a manifest or an output file fails verification; output checksums exclude the manifest itself (design `:350-352`); `backend_policy`, composite stage records and stage allocation are present.
3. **Paper mode guards (D-03).** The run service refuses, before any execution or write: a `draft` or `archived` profile, a dirty tree, a profile whose `analysis_plan_id` does not resolve, an output directory inside the repository, and a resume against an incompatible manifest. Interrupted runs leave no file that verifies as complete.
4. **Statistics (D-05).** Synthetic fixtures with independently known results reproduce the omnibus statistic, post-hoc p-values, Holm adjustment and effect sizes within a stated tolerance; the service refuses smoke-mode rows, mixed comparison cells, falsely paired designs (unequal unit sets, missing replicates), samples below the plan's minimum, exact/union/joint rows (`assert_rankable`), `HISTORICAL_UNVERIFIED` and `INVALID` rows; every refusal names its reason.
5. **Gap columns (D-06).** For each of the 7 Bildiri and 4 YAEM instances the gap is computed against the `exact_reference_v1` value, which equals the published optimum in `reference.csv` and `problem.optimal`; exact rows are never ranked, averaged or tested.
6. **Profiles.** Both study profiles load, preflight and smoke-run through the D-03 service in smoke mode; their values match DECISION_LOG (including OQ answers and the YAEM base seed decision); `analysis_plan_id` resolves to a committed, schema-valid analysis plan (D-09).
7. **No invalid evidence reachable from active reporting (D-08).** A sweep test enumerates the active reporting entry points (analysis service, report generator, `matrix_run_summary`, `results_reader`, dashboard data utilities, the `/academic/*` API readers) and shows that `INVALID` rows are never returned and `HISTORICAL_UNVERIFIED` rows are returned only in the labelled historical view, never in an aggregate, statistic or report; archived paths are not discoverable as default input.
8. **Descriptive smoke reports (D-07).** One smoke report per profile contains descriptive tables (n, median, IQR, min, max of cost and gap per comparison cell, evaluations consumed), the mode/commit/dirty banner and manifest checksums, and passes the no-ranking wording check.
9. **Suites.** `export_schemas check` exit 0; `academic_benchmark/tests -m "not requires_ampl"` all pass (listed skips only); `uniride_core/tests -m "not requires_ampl"` pass with optional-solver environment skips listed separately (design `:412`); the 3-opt regression command plus production snapshot pass; `git diff --check` clean.
10. **Documentation consistent (D-11).** The master documents and the migration tables state the verified architecture; a consistency check (D-11 test) finds no active false label (`GWO-LKH`, `HHO-LKH`) outside migration tables and history, and every canonical ID in the catalog appears in the migration table.
11. **Clean and published (D-12).** `git status --short` shows no generated file after the suites; the integration worktree is clean; the publication step chosen in OQ-13 is done with the owner's explicit permission, and its text says the paper-scale runs and the full-suite verification on the stronger computer are still pending.

Command block (to be pasted into the closing item's brief):

```powershell
$env:PYTHONPATH = "<checkout>"; $env:PYTHON_BASIC_REPL = "1"
$PY = "C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe"
New-Item -ItemType Directory -Force C:\wt\gated | Out-Null
& $PY -m academic_benchmark.contracts.export_schemas check
& $PY -m pytest academic_benchmark/tests/test_gate_d_comparison_identity.py academic_benchmark/tests/test_run_manifest_writer.py academic_benchmark/tests/test_study_run_service.py academic_benchmark/tests/test_analysis_statistics.py academic_benchmark/tests/test_analysis_gap_columns.py academic_benchmark/tests/test_gate_d_reporting_sweep.py academic_benchmark/tests/test_analysis_plan_registry.py academic_benchmark/tests/test_gate_d_docs_consistency.py -q -p no:cacheprovider --tb=short > C:\wt\gated\gate_d_focused.txt 2>&1
& $PY -m pytest academic_benchmark/tests -m "not requires_ampl" -q -p no:cacheprovider --tb=short > C:\wt\gated\academic.txt 2>&1
& $PY -m pytest uniride_core/tests -m "not requires_ampl" -q -p no:cacheprovider --tb=short > C:\wt\gated\core.txt 2>&1
& $PY -m pytest academic_benchmark/tests/test_numba_registry_matrix.py academic_benchmark/tests/test_numba_three_opt.py academic_benchmark/tests/test_core_tsp_registry.py uniride_core/tests/test_local_search_core.py uniride_core/tests/test_tsp_meta_engines.py uniride_core/tests/test_canonical_three_opt.py academic_benchmark/tests/test_canonical_three_opt_integration.py academic_benchmark/tests/test_production_registry_snapshot.py -q -p no:cacheprovider --tb=short
# smoke of both profiles through the D-03 service (smoke mode), outputs outside the repository; module name fixed by D-03
& $PY -m academic_benchmark.studies.run --study academic_benchmark/studies/bildiri2026/study.json --mode smoke --out C:\wt\gated\smoke-bildiri
& $PY -m academic_benchmark.studies.run --study academic_benchmark/studies/yaem2026/study.json --mode smoke --out C:\wt\gated\smoke-yaem
& $PY -m academic_benchmark.studies.verify_manifests C:\wt\gated\smoke-bildiri C:\wt\gated\smoke-yaem
git diff --check
git status --short
```

Test file and module names above are the planned names; each item may rename them, and D-13 pastes the final names.

---

## 3. Work items

Dependency order and parallel lanes:

```text
Lane A (identity and manifests, serial):   D-01 comparison identity -> D-02 run manifests + .sha256 -> D-03 run service (smoke + paper mode)
                                            -> D-04b cost estimator (calibration slice)
Lane B (statistics):                        D-04a analysis environment pin (any time) ; D-09 analysis-plan registry (any time)
                                            -> D-05 statistics service (after D-01, D-04a, D-09)
Lane C (reference and reports):             D-06 gap columns (after D-01) -> D-07 descriptive reports (after D-02, D-05, D-06)
Lane D (reporting safety):                  D-08a summarize_benchmark_rows guard + pstdev (any time)
                                            -> D-08b reporting sweep (after D-05, D-07)
Lane E (process and docs):                  D-10 paper-scale run-plan procedure (after D-04b; owner answers in hand)
                                            -> D-11 documentation sync (after every code item) -> D-12 publication (owner permission)
Close:                                      D-13 Gate D close
Writing line (parallel, no developer):      W-1 .. W-5 (section 4)
```

Model and review guidance (CLAUDE.md): developer Sonnet for every item. Reviewer **Opus** for D-01, D-02, D-03, D-05, D-06 (identity, evidence integrity, statistics: high risk). Reviewer Sonnet for D-04a/b, D-07, D-08a/b, D-09, D-10, D-11. D-12 is done by the lead with owner permission. Suggested tool-call ceiling per item: about 15-25 (requested, not enforced).

### D-01: Comparison identity for analysis (pooling key below the protocol group)

- [ ] **Goal:** one function, `comparison_cell_key(row, manifest)`, that every analysis, summary and report calls after `assert_single_pooling_group`; rows may be aggregated or tested together only when their keys are equal (except the dimension being compared: algorithm ID inside one cell family; instance inside a cross-instance family).
- **Key fields:** pooling group and exact `protocol_version` (fair v1 and v2 separate; [F] `protocol_registry.py:88-89` lumps them); `study_id`; normalised dataset identity (C-11 rule); budget **level index** within the profile's level list (X8), never the raw budget across instances; algorithm ID; canonical configuration hash (sorted JSON of parameters, `termination_policy` included per X5, `elapsed_ms`/`elapsed_sec` excluded per X7, `polish_policy.final` flag excluded as a grouping key per A17 C-04 note `:450`); `seed_protocol_version` and `base_seed`; evidence class (current vs `HISTORICAL_UNVERIFIED`, A13); code commit of the run manifest (OQ-10).
- **Files:** `academic_benchmark/analysis/identity.py` (new package `academic_benchmark/analysis/`); tests `academic_benchmark/tests/test_gate_d_comparison_identity.py`.
- **Red test first:** two rows equal except fair v1 vs v2 are refused as one cell; equal except `elapsed_sec` give the same key; equal except a PSO `termination_policy` constant give different keys; Bildiri `eil51` level 63750 and `kroa100` level 247500 share level index 0 and form one cross-instance family; a pre-C-16a `Core-GA-TSP` row (no manifest/commit) is refused.
- **Acceptance:** red tests green; `assert_single_pooling_group` still called first (AST or call-order test).
- **Closes:** X5, X6, X7 (analysis side), X8, X14. **Depends on:** OQ-10 answer. **Risk:** high (decides what may be compared). **Changes academic results:** no (no run changes); changes which rows can be compared. **Reviewer:** Opus.

### D-02: `RunManifestV1` writer, detached `.sha256` and verifier

- [ ] **Goal:** every run (smoke and paper mode) produces schema-valid run manifests with the design fields (`:337-350`) and a detached `<manifest>.sha256` (`:352`); a verifier recomputes everything.
- **Content rules:** git commit + dirty flag (`run.py:17-19`); environment including the D-04a statistics-library version (or the literal `"none"` in smoke mode if OQ-7 is not yet answered; lead decision recorded in A18); dataset manifest (`DatasetManifestV1`); algorithm ID, capability evidence IDs, `backend_policy` (X11), backend profile, configuration, `composition_stages` (X12); complete seed schedule (`SeedScheduleV1.derived`); budget levels, policy, consumed evaluations, `stage_allocation`; termination reason and runtime; validation result; output checksums excluding the manifest itself.
- **Lead decision needed before the brief (not a scientific value):** manifest granularity. [F] `RunManifestV1` has one `algorithm`, one `dataset`, one `termination` (`run.py:65-80`), which fits one manifest per run (algorithm x dataset x level x replicate); the design wording "each pilot or experiment records ... complete derived seed schedule" (`:339`, `:346`) fits one per campaign. Recommendation: one `RunManifestV1` per run plus one campaign index (`uniride-run-index/v1`, new schema) listing run manifests with their `.sha256`; schema change only by a new version (design `:220`).
- **Files:** `academic_benchmark/analysis/manifests.py` (writer, verifier), `academic_benchmark/studies/verify_manifests.py` (CLI), possibly `academic_benchmark/schemas/run-index-v1.schema.json` + `export_schemas.py`; tests `test_run_manifest_writer.py`.
- **Red test first:** a smoke run on an in-memory 6-node matrix writes a manifest that validates and verifies; tampering with one output byte or one manifest byte fails the verifier; the manifest does not list itself in `outputs`; `elapsed_*` do not enter any identity hash written to the manifest; a composite row's stage records appear in `composition_stages`.
- **Acceptance:** red tests green; `export_schemas check` exit 0 with any new schema snapshot committed.
- **Closes:** X1, X11, X12, design `:337-354`. **Depends on:** D-01 (identity hash), D-04a only for the library version string. **Risk:** high. **Changes academic results:** no. **Reviewer:** Opus.

### D-03: Study run service with smoke and paper modes

- [ ] **Goal:** one entry point, `academic_benchmark/studies/run.py` (`--mode smoke|paper`), that wraps the C-11 plan and the C-12 row runner and adds the Package D guards. Smoke mode keeps today's behaviour (`smoke.py:401-482`) plus manifests. Paper mode is built and tested here but **not used for paper-scale runs in Gate D**.
- **Paper mode refuses before anything runs:** profile status not `active` (X9; `contracts/study.py:154`); dirty tree or unknown git state (design `:354`); unresolved `analysis_plan_id` (D-09); output inside the repository (`fair_pilot._prepare_output_dir`, `fair_pilot.py:327`; `output_policy.paper_scale_location: external`, `study.json:68`); MT6 not recorded as done in DECISION_LOG (lead decision whether this is a code check or a checklist item; recommendation: checklist item in D-10, not code).
- **Failure and resume:** atomic writes for every row file and manifest (design `:362`); resumption reads the existing campaign index, verifies every manifest and refuses a changed profile, commit or environment; failure policy per OQ-9 (smoke keeps "stop at first failure", `smoke.py:455`).
- **Files:** `academic_benchmark/studies/run.py` (new), small changes in `smoke.py` (reuse, no copy); tests `test_study_run_service.py`.
- **Red test first:** paper mode on the (draft) Bildiri profile is refused with a message naming the status; paper mode on a synthetic `active` profile in a dirty temporary git repository is refused; a run killed after N rows (simulated) resumes and produces the same comparable rows as an uninterrupted run; a resume after changing one parameter is refused.
- **Acceptance:** red tests green; the smoke runs of both profiles in the command block pass and verify.
- **Closes:** X9, design `:354`, `:362`. **Depends on:** D-02, D-09. **Risk:** high. **Changes academic results:** no. **Reviewer:** Opus.

### D-04a: Pinned analysis environment

- [ ] **Goal:** a pinned statistics library as an academic-only optional dependency (pattern of `requirements-paper.txt`), never an operational dependency.
- **Files:** `requirements-analysis.txt` (new; versions per OQ-7), an import guard in `academic_benchmark/analysis/__init__.py` with a clear error when missing, a CI/nightly note; tests `test_analysis_environment.py` (version recorded matches the pin).
- **Red test first:** the analysis service records the library name and version into `EnvironmentV1.statistics_library`; a missing library gives a named error, not an `ImportError` trace.
- **Closes:** design `:335` ("pinned scientific environment"). **Depends on:** OQ-7. **Risk:** low. **Changes academic results:** no. **Reviewer:** Sonnet.
- **Note:** installing a package into `.venv-jit` is an environment change; the lead installs it with the owner's OK and records the version in A18.

### D-04b: Cost estimator and calibration slice (input to the run-plan approval)

- [ ] **Goal:** `academic_benchmark/studies/estimate.py` prints, for a profile and a candidate run plan (run counts, levels, instances, algorithms), the number of runs, the evaluation upper bound per cell, and an estimated wall time from a measured calibration slice on the machine where it runs.
- **Calibration slice:** one replicate per algorithm on the smallest and the largest instance of the profile at the lowest level, timed per evaluation (Numba objective vs Python polish separately, because [F] memetic GWO/HHO spend about 98-99 % of the budget on Python 2-opt polish at smoke scale, A17 C-04 note `:450`), plus one native composite run with the OQ-4 limits. Output to `C:\wt\<name>`; the estimate is a planning number, not evidence.
- **Red test first:** evaluation upper bounds for the Bildiri profile equal the arithmetic from `study.json:53-61` (see section 6); the estimator refuses a plan that mixes levels across instances by raw value.
- **Closes:** the time estimate the owner needs before approving run counts. **Depends on:** D-03. **Risk:** low. **Changes academic results:** no. **Reviewer:** Sonnet.

### D-05: Statistics service (guarded)

- [ ] **Goal:** `academic_benchmark/analysis/statistics.py` implements the predeclared analysis of the study's analysis plan (D-09) over verified rows only. Per instance (independent samples, design `:322-327`): omnibus test, pairwise tests only when the omnibus is significant or the plan says so, Holm over the declared family, effect sizes, exact n. Across instances (matched units, design `:329-333`): omnibus over instances as blocks, paired post-hoc over the same units only, correction, effect sizes, exclusions listed. Tests, alpha, effect-size measures, the per-instance summary used as the matched unit and the minimum n are **[O]** (OQ-5, OQ-6) and come from the analysis plan, never from code defaults.
- **Guards:** inputs must verify (D-02) and share one comparison-cell family (D-01); `assert_rankable` (`protocol_registry.py:110-117`); smoke-mode manifests refused (design `:404`); equal numeric seeds are not taken as pairing evidence (design `:297`) — matched analysis pairs only by instance units with complete replicate sets; fixed and native never in one call; output text uses descriptive wording unless the plan's inferential conditions hold.
- **pstdev:** reports use the sample standard deviation (`statistics.stdev`) or report IQR; the pilots' `pstdev` (`fair_pilot.py:532`, `native_pilot.py:517`) is changed in D-08a (L9 bullet).
- **Files:** `academic_benchmark/analysis/statistics.py`; fixtures `academic_benchmark/tests/fixtures/statistics/` with expected values computed independently (published textbook examples or a second library run once by the developer, values committed with their source); tests `test_analysis_statistics.py`.
- **Red test first:** the fixtures reproduce; a falsely paired design (one instance missing an algorithm) is refused; smoke rows are refused; n below the plan minimum gives "insufficient sample", never a p-value.
- **Closes:** P1, design `:318-335`, `:400-404`, X13 prerequisite. **Depends on:** D-01, D-04a, D-09, OQ-5, OQ-6. **Risk:** high. **Changes academic results:** no runs change; this defines the claims. **Reviewer:** Opus.

### D-06: Gap columns against the exact reference; link the Bildiri profile

- [ ] **Goal:** an analysis column `gap_to_exact_reference = (cost - ref) / ref` (unit per OQ-6) where `ref` comes from the `exact_reference_v1` reader (WP-E8; the reader validates the stage-1 rows) and the join uses the normalised TSPLIB identity (section 1.3, `kroa100`). Exact rows are joined as a reference, never pooled, ranked or tested (`protocol_registry.py:59`, E12).
- **Profile link (X3):** the Bildiri (and YAEM) profile gets a reference to the exact-reference set only through the mechanism the lead chooses (dataset manifest `best_known.provenance` already discloses the source, A17 C-18 note; recommendation: an `exact_reference` field in the analysis plan, D-09, so `study.json` and its E12 LF pin stay unchanged). The studies boundary test that forbids exact-reference names in the Bildiri study check (A17 C-05 note `:456`) changes with review.
- **Cross-check:** for the 11 study instances, `ref` equals the published optimum in `reference.csv` and `problem.optimal` from the database; any difference blocks (no silent choice).
- **Files:** `academic_benchmark/analysis/gaps.py`; tests `test_analysis_gap_columns.py`; the boundary test touched by X3.
- **Red test first:** gap for a synthetic row on `eil51` with cost 426 is 0; a row whose instance has no exact reference gets no gap (null with reason), never the database value silently; an exact row passed as data to the statistics service is refused.
- **Closes:** X2, X3. **Depends on:** D-01, D-09 (if the link lives there). **Risk:** medium-high (touches E12 boundary). **Changes academic results:** reported gap values may change source (database optimum -> verified exact reference; equal on all 11 instances per `reference.csv`). **Reviewer:** Opus.

### D-07: Descriptive reports (smoke and paper)

- [ ] **Goal:** `academic_benchmark/analysis/report.py` writes descriptive tables per comparison cell (n, median, IQR, min, max, mean and sample SD of cost and gap, evaluations consumed and their share of the budget, termination reasons, failed-run counts), the banner (mode, commit, dirty, profile status, manifest index checksum) and, in paper mode only, the D-05 inferential section. Smoke reports keep the no-ranking wording check (`smoke.py:141-145`; A15 wording).
- **Files:** `academic_benchmark/analysis/report.py`; smoke integration in `studies/run.py`; tests `test_analysis_report.py`.
- **Red test first:** a smoke report on a synthetic plan contains every column and no ranking word; a report refuses rows from two comparison cells in one table.
- **Closes:** P3, design `:454`. **Depends on:** D-02, D-05, D-06. **Risk:** medium. **Changes academic results:** no. **Reviewer:** Sonnet.

### D-08a: Guard the existing summary path; sample SD in pilots

- [ ] **Goal:** `matrix_run_summary.summarize_benchmark_rows` (`matrix_run_summary.py:14`) calls `assert_single_pooling_group` (X4) and refuses unclassifiable rows; the pilots' summaries use the sample SD (L9 bullet; `fair_pilot.py:532`, `native_pilot.py:517`) or are labelled population SD explicitly (lead decision; recommendation: sample SD, label `stddev_cost_sample`).
- **Risk:** the golden `test_fixed_budget_tables_unchanged.py:298` includes `summarize_benchmark_rows`; any golden update needs a lead-reviewed commit note. **Changes academic results:** pilot summary SD values change (no run changes). **Closes:** X4, L9 `pstdev` bullet. **Reviewer:** Sonnet.

### D-08b: Reporting sweep: no invalid evidence reachable from active reporting

- [ ] **Goal:** one test that enumerates the active reporting entry points (D-05, D-07, `matrix_run_summary`, `results_reader.py`, `dashboard_utils.py`, `obsolete_results.py`, the `/academic/*` readers in `optimizer_api/routers/benchmark.py`) and feeds each a mixed fixture with `INVALID`, `HISTORICAL_UNVERIFIED`, current fixed, current native and exact rows. Expected: `INVALID` never returned; `HISTORICAL_UNVERIFIED` only in the labelled historical view (A13), never in an aggregate, statistic or report; archived paths never discovered as default input (existing quarantine tests `test_historical_quarantine.py`, `test_quarantine_round2.py`, `test_legacy_obsolete.py` are reused, not duplicated).
- **Closes:** Gate D first clause (`:460`). **Depends on:** D-05, D-07. **Risk:** medium. **Changes academic results:** no. **Reviewer:** Sonnet.

### D-09: Analysis-plan registry (`analysis_plan_id` resolves)

- [ ] **Goal:** versioned analysis-plan documents under `academic_benchmark/studies/<study>/analysis_plan.json` with schema `uniride-analysis-plan/v1`: response variable, per-instance summary for matched analysis, comparison families (which algorithm sets, which instance sets, TSP and ATSP separate or not), omnibus and post-hoc tests, correction, alpha, effect sizes, minimum n, exclusion and failure policy, exact-reference link (D-06). The study loader refuses an unknown or invalid plan ID (paper mode) and labels it (smoke mode). Values are **[O]**; until the owner answers, the plans carry `status: draft` and the D-03 paper mode refuses them.
- **Files:** `academic_benchmark/contracts/analysis_plan.py`, schema snapshot, two plan files, `service.load_study` check; tests `test_analysis_plan_registry.py`.
- **Closes:** section 1.3 gap; design `:205-216`. **Risk:** medium (schema). **Changes academic results:** no. **Reviewer:** Sonnet.

### D-10: Paper-scale run-plan approval procedure

- [ ] **Goal:** a short procedure (in `docs/designs/PAPER_SCALE_RUN_PLAN_TEMPLATE.md`, modelled on `docs/designs/WP_E10_RUN_README_TEMPLATE.md`) that every paper-scale campaign follows. A run plan states: study and profile commit; algorithms; instances; budget levels; run count; base seed and seed protocol; native limits (including per-stage composite limits); analysis plan ID; machine; the D-04b estimate (runs, evaluation bound, hours, measured on that machine); output location; failure policy; the checklist (MT6 merged, owner 2026-10-23 decisions 2-4 on `WIP`, profile status `active`, clean tree, analysis environment pinned, verification of the stronger computer's suite run). Approval: the owner approves the run plan in chat; the lead records it as a DECISION_LOG entry with the plan's sha256 and sets the profile `status: active` in the same lead-merged commit. A run whose manifest commit or profile hash differs from the approved plan is not paper evidence.
- **Closes:** the user's requirement "how a paper-scale run plan is defined and approved". **Depends on:** D-03, D-04b. **Risk:** low. **Changes academic results:** no. **Reviewer:** Sonnet.

### D-11: Documentation synchronization and migration tables

- [ ] **Goal:** bring `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, `UniRide_Ultimate_Audit.md`, `README.md`, `docs/UNIRIDE_WORKSTATE.md` in line with the verified state after Gates C and D; one migration table (old name -> canonical ID or refusal, with the DECISION_LOG entry): `GWO-LKH`/`HHO-LKH` -> `Core-GWO/HHO-TSP-Memetic-3opt`, B-GA/B-PSO -> guidance (A01), `Numba-GA`/`Numba-PSO` aliases (C-14), `Matrix-*-legacy` (C-14), `Core-*` routing refusal (`58f77d66`), `Numba-Swap`/`Numba-Hybrid`/`SOTA-*` routing refusal (owner decision 4, once merged). Design-document amendments (section 8) are proposed as a redline for the owner; the developer does not edit the approved designs without that approval.
- **Test:** `test_gate_d_docs_consistency.py`: every catalog ID appears in the migration table; no false label outside the table and history sections; the WORKSTATE row names the Gate D commit.
- **Who:** a developer (Sonnet) for the table and test; prose changes to master documents get an `olgu-denetcisi` (Sonnet) fact check against code and DECISION_LOG. **Closes:** P4. **Depends on:** every code item. **Risk:** low. **Changes academic results:** no.

### D-12: Publication step (owner permission)

- [ ] **Goal:** per OQ-13: fetch, inspect divergence of `origin/WIP` (and any branch named in OQ-13), push, and open the draft PR (or the chosen alternative) whose text says that paper-scale runs and full-suite verification on the stronger computer are pending. Done by the lead; pushing and opening a PR need the owner's explicit permission in chat.
- **Closes:** P6, design `:457-458`, `:466`. **Risk:** low (but irreversible publication). **Changes academic results:** no.

### D-13: Close Gate D

- [ ] Run the section 2 command block on one `WIP` commit; record counts in DECISION_LOG A18 and WORKSTATE ACAD-01; update Appendix J (X4/L9 bullet, C5 note "Package D present"); tick items here. **Reviewer:** Opus (gate evidence). **Depends on:** all items.

---

## 4. Writing-line items (paper text; not for developers)

Each goes through the writing line (arastirmaci -> yazar (Opus) -> olgu-denetcisi; CLAUDE.md "Yazı hattı"). None may be written from smoke evidence as a result.

| # | Text | Evidence it needs | When |
|---|---|---|---|
| W-1 | Methods: fixed-evaluation-budget protocol, the budget rule (50x and 250x of n(n-1)/2 for Bildiri, A17 C-19 notes), budget-following GWO/HHO schedules (A17 2026-10-22), composition semantics, native protocol as secondary and never pooled | Design `:277-297`; A17 C-04/C-06/C-07/C-19 notes; the approved run plan (D-10) | after OQ-1..OQ-4 |
| W-2 | Algorithms: which GA and PSO produced the original Bildiri numbers (memetic GA and memetic PSO with uncounted 2-opt) and which are rerun (pure GA/PSO and the counted memetic GA; no memetic PSO) | A17 Q2/P1 (`archive/.../Bildiri.md:9-11`, `ga_solver.py:62-69,150-156`, `pso_solver.py:12-18,110-151,212-217` as cited there; reference only) | any time |
| W-3 | Statistical analysis paragraph | The approved analysis plan (D-09) and the D-05 fixture evidence | after OQ-5/OQ-6 |
| W-4 | Exact reference and gap definition | E09/E10/E12; `reference.csv`; D-06 | after D-06 |
| W-5 | Results and discussion | Paper-scale results only (after D-10 approval and the stronger-computer runs); never smoke | after Gate D, out of Gate D scope |

---

## 5. Owner questions

No developer chooses these values. Each answer is recorded in DECISION_LOG A18 and lands in a profile or analysis plan by a lead-merged commit.

| # | Question | Options | Recommendation | Pros / cons |
|---|---|---|---|---|
| OQ-1 | Run count per cell (Bildiri, YAEM) | a) 30 (the original Bildiri design reported 30 independent runs, Gate C plan section 1.1 D8); b) 20; c) 50; d) per study different | a) 30 for both, **after** the D-04b estimate | a: comparable with the original paper, usual in the field; cost is the largest factor (section 6). b: cheaper, weaker power. c: more power, about 1.7x a. |
| OQ-2 | Fixed budget levels | a) keep 50x and 250x n(n-1)/2 (current, A17 2026-10-21); b) add a third level (e.g. 10x) to show budget dependence (design `:287`); c) one level only | a) | a: already decided and smoke-tested; b: shows ranking sensitivity but +~20 % cost per extra low level and more comparison families; c: cheapest, hides budget dependence |
| OQ-3 | YAEM paper values (currently placeholders, A17 C-13 note): instances, levels, run count, `global_fraction`, composite global extras, ALNS polish parameters | a) confirm the placeholders (berlin52, eil51, st70, kroA100; Bildiri rule levels; 0.80; solver defaults; `ALNSConfig` defaults); b) owner sets new values; c) defer YAEM paper runs | a) with the 2027 seed, after the estimate | a: no new design work; parameters are defaults, not tuned (state it in W-1). b: needs a justification per value. c: keeps Bildiri first |
| OQ-4 | Native (secondary) protocol for the paper: which algorithms, their stopping limits, and per-stage limits for composites (design native rule 2; A17 C-13 note) | a) every study algorithm, each with its own explicit `max_iterations`/stagnation limit, composite global stage = its pure counterpart's limits, 3-opt/ALNS polish stage capped (e.g. 3-opt `max_iterations` small enough to finish; [F] 1000 iterations "runs for hours at n = 52"); b) only GWO/HHO pure (current smoke scope, `study.json:44-48`); c) no native secondary in the paper | a) with limits set after a D-04b calibration of the composite polish | a: complete secondary picture; needs several values and their timing. b: cheap, thin. c: simplest; the design allows it (`secondary_protocol` optional, `:212`) |
| OQ-5 | Statistical tests, correction, alpha, effect sizes | a) per instance Kruskal-Wallis -> pairwise Mann-Whitney U with Holm; across instances Friedman -> Wilcoxon signed-rank with Holm; alpha 0.05; effect sizes Vargha-Delaney A12 (pairwise), epsilon-squared (KW), Kendall's W (Friedman); b) as a) but Nemenyi/Conover post-hoc after Friedman; c) descriptive plus confidence intervals only (no hypothesis tests) | a) | a: matches the design wording (`:322-333`), all tests in one proven library; with 6-7 instances the Friedman family has low power (state it). b: common in metaheuristics papers but needs an extra library and is not "paired post-hoc over the same units" in the design's sense. c: safest wording, weakest claims |
| OQ-6 | Response variable and the matched unit | a) relative gap to the exact reference (%), per-instance median as the Friedman unit; b) raw cost per instance, ranks per instance; c) mean gap | a) | a: scale-free across instances, exact reference available for all 11 instances; median robust. b: avoids reference dependence. c: sensitive to outliers |
| OQ-7 | Statistics library | a) SciPy only (pinned), Holm implemented locally and tested against a published example; b) SciPy + statsmodels (`multipletests`); c) SciPy + scikit-posthocs (if OQ-5 b) | b) | a: fewest dependencies, own Holm code to maintain. b: both "proven libraries" (design `:335`), small footprint for paper-only use. c: needed only for Nemenyi/Conover |
| OQ-8 | Instance families for cross-instance analysis | a) TSP instances only in the Friedman family, `ft53` (ATSP) analysed per instance only; b) one family with TSP and ATSP together; c) per-instance only, no cross-instance test | a) | a: keeps problem types separate (design TSP/ATSP contracts); b: one more block but mixes problem types; c: avoids low-power cross-instance tests |
| OQ-9 | Failure policy in paper mode | a) record the structured failed run, continue the campaign, exclude the cell from inference and report it; b) stop the campaign at the first failure (smoke behaviour); c) retry once with the same seed, then a) | a) | a: one failure does not waste days of runs; exclusions are visible. b: strictest, can waste a long run. c: hides nondeterminism unless the retry is reported |
| OQ-10 | Pooling across code commits | a) one campaign = one clean commit; rows from different commits are never pooled (E06 style); b) allow different commits when the comparison identity hash and algorithm code hashes are equal | a) | a: simple, already practised for exact campaigns; a bug fix mid-campaign forces a rerun. b: flexible, but needs code hashing and more review |
| OQ-11 | Dashboard statistical-tests tab (A09) | a) stays disabled in Gate D; b) re-enable through the D-05 service | a) | a: no new UI surface; analysis is file-based. b: convenience, more test surface |
| OQ-12 | Machine and timing for the estimate | a) D-04b on the current PC for plumbing, repeated on the stronger PC before approval; b) only on the stronger PC | a) | a: early cost signal; b: one measurement, later |
| OQ-13 | What "publication" means now (design `:457-458`, written for `codex/reconcile-native-protocol`) | a) push `WIP` and open a draft PR `WIP -> main` stating that paper-scale verification is pending; b) push `WIP` and tag `gate-d` (no PR); c) no push, local record only | a) | a: matches the design's intent (a reviewable draft that stays unmerged); b: lighter; c: keeps everything local but leaves Gate D's last clause unmet |
| OQ-14 | Design-document amendments (section 8) | a) the lead drafts a redline, the owner approves, then D-11 applies it; b) leave the designs, record deviations only in DECISION_LOG | a) | a: keeps "documentation is consistent" true; b: less work, designs stay stale |

---

## 6. Measured costs and the estimate that is still needed

Facts available now (no paper-scale timing exists):

- [F] One 2-opt scan = n(n-1)/2 counted evaluations (1275 at eil51, 4950 at n = 100), A17 C-19 measurement (`:465`).
- [F] Memetic GWO/HHO spend about 98-99 % of the budget on 2-opt polish at smoke scale (A17 C-04 note `:450`); polish runs in Python in native mode (A17 C-10 note `:461`), so those IDs will dominate wall time.
- [F] A native 3-opt polish limited only by its 1000 iterations "runs for hours at n = 52" (A17 C-13 note `:472`).
- [F] Suite timings: `academic_benchmark/tests -m "not requires_ampl"` 464.8 s at `559826b5` (Gate C plan, baseline table); the Gate C acceptance run did not record a time.
- [F] Evaluation upper bounds from the Bildiri level table (`studies/bildiri2026/study.json:53-61`): per algorithm and replicate, both levels on all 7 instances = 5,743,200 evaluations (berlin52 397,800; eil51 382,500; st70 724,500; kroA100 1,485,000; rd100 1,485,000; eil76 855,000; ft53 413,400). With 10 algorithms and 30 replicates: about 1.72 x 10^9 evaluations in the fixed protocol. Local searches may stop earlier at a local optimum (A17 C-19 note).
- [A] YAEM with the placeholder levels on its 4 instances: 2,989,800 per algorithm and replicate; 11 algorithms x 30 replicates: about 0.99 x 10^9 evaluations (assumes the YAEM levels equal the Bildiri rule, as the C-13 note says).
- **Missing:** seconds per evaluation by backend (Numba objective vs Python polish) and per instance size, and native-protocol run times. Without them no wall-time estimate is honest. D-04b measures them; the owner approves run counts (OQ-1) only after seeing the D-04b table from the machine that will run the campaign (OQ-12).

---

## 7. Out of scope / later

| Item | Reason |
|---|---|
| Paper-scale runs themselves (Bildiri, YAEM) | Design `:29, :36, :416, :466`; after Gate D, under an approved D-10 run plan, on the stronger computer |
| MT6 (H10 + M25, H11, M14) | A17 Q4: separate plan, required before paper-scale runs, not part of Package D |
| CVRP exact (WP-E9), TSP/ATSP n > 100 (gil262 and others) | E09 |
| Vehicle-routing (`vehicle_routes`) analysis and validation in reports | Design non-goals `:38-39`; no active study uses CVRP |
| WP-E11 method text and the daily-planning paper (E13/E14) | Separate writing-line work (A17 2026-10-23 decision 6); its exact protocols stay their own pooling groups |
| H8 storage half, H17 import half, H19, M15, M16 (MT4/MT2) | Production contract work |
| M20 repeated-evaluation telemetry (LT1) | Informational; changes no protocol |
| Re-enabling dashboard inference | OQ-11 recommendation a) |
| Genuine LKH | Design non-goal `:37` |
| Owner 2026-10-23 decisions 2-4 implementation | Separate items (section 1.4); Gate D only checks that 2 is on `WIP` |
| Git history rewrite | Design non-goal `:40` |

---

## 8. Contradictions and stale statements found

1. **Branch and publication model.** Design `:18`, `:30`, `:420`, `:466` (`codex/reconcile-native-protocol`, "without modifying `WIP` directly", draft PR stays unmerged until the stronger-computer results return) vs practice: every package merged into `WIP` by the lead, `WIP` is `origin/HEAD`, and `origin/WIP...WIP` = `0 0`. -> OQ-13, OQ-14.
2. **Fairness design is behind the code.** `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md:24` lists families `GWO`, `HHO`, `2-opt`, `3-opt` only and `:25` variants `pure`/`memetic_2opt` (GA, PSO, Or-opt, ALNS and the composite kinds now exist); `:70` says existing GWO/HHO aliases stay backward compatible (C-14 removed several aliases); `:112` refers to "the current NumPy 2.5.1 environment" while the JIT constraints pin numpy 2.4.6 (`jit-benchmark-constraints.txt`).
3. **Pooling group vs protocol version.** `protocol_registry.py:88-89` puts fair v1 and v2 rows in one pooling group although the composites are v2-only and v1 rows were produced under a different contract (D-01 separates them).
4. **YAEM seed.** DECISION_LOG A17 `:474` (decision 2: YAEM `base_seed` 2027, "the lead set 2027") vs `studies/yaem2026/study.json:76` (`2026`) on `WIP`.
5. **`EnvironmentV1.statistics_library` is required** (`run.py:29`) while no statistical library is installed or pinned; smoke manifests cannot fill it truthfully until D-04a (D-02 records the lead's interim rule).
6. **Manifest granularity is ambiguous:** one-run contract (`run.py:65-80`) vs "each pilot or experiment records ... complete derived seed schedule" (design `:339, :346`). D-02 lead decision.
7. **Design `:287` says manifests "may predeclare multiple budget levels" and results at different levels are not pooled**; with instance-scaled levels (A17 C-19) the same level index has different raw budgets per instance; the design does not say how a cross-instance analysis groups them (A17 `:468` says by level index). D-01 implements the A17 rule; the design text should be amended (OQ-14).
8. **Gate C plan citation drift:** it cites `fair_pilot._prepare_output_dir` at `fair_pilot.py:283-300`; it is now at `:327`. Harmless, but briefs must re-verify line numbers.
9. **Study `analysis_plan_id` is required but meaningless today** (section 1.3); the design requires it (`:205-216`) without defining its target.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Analysis pools rows that the protocol registry accepts but that are not comparable (v1/v2, levels, parameters, eras) | D-01 key checked in every analysis and report; Opus review; red tests per field |
| Self-referential or forgeable manifests | Detached `.sha256`, outputs exclude the manifest, verifier with tamper tests (D-02) |
| A draft profile or dirty tree produces "paper" evidence | Paper mode refusals (D-03); approval procedure with profile hash (D-10) |
| Inferential wording from smoke data | Smoke manifests refused by D-05; wording check in D-07; AGENTS.md rule repeated in briefs |
| Low statistical power with 6-7 instances | State it in the analysis plan and W-3; OQ-8 option a or c |
| Cost underestimated (Python polish, native 3-opt) | D-04b calibration on the target machine before OQ-1 is answered |
| Reference mismatch between database optimum and exact reference | D-06 cross-check blocks on any difference |
| Golden and boundary tests changed silently (`test_fixed_budget_tables_unchanged.py`, A17 C-15 Bildiri exact-reference ban, E12 LF pins) | Lead-reviewed commit notes; D-06 and D-08a name the exact tests they change |
| New dependency leaks into production | `requirements-analysis.txt` only; import guard; production snapshot test unchanged |
| Editable install runs main-checkout code | `PYTHONPATH` = worktree; print `academic_benchmark.__file__` |
| Python REPL runaway and process kills | Global constraints at the top of every brief; PID-only kills |
| Irreversible publication | D-12 only with the owner's explicit permission in chat |

## 10. Confirmed facts vs assumptions (summary)

- **Confirmed** (file:line in the sections above): no statistics code or library; `RunManifestV1` unused; smoke stops at first failure and writes no manifest; pooling registry lumps fair v1/v2 and ignores level/config/commit; `analysis_plan_id` unresolved; pilots use `pstdev`; `summarize_benchmark_rows` unguarded; both profiles `draft`; Bildiri native scope GWO/HHO pure with `max_iterations: 2`; YAEM `base_seed` 2026 on `WIP`; exact-reference rows exist for all 11 study instances; `origin/WIP` equals `WIP`; branch `fix/numba-sota-refuse-routing` exists.
- **Assumptions to re-check in each brief:** whether owner decisions 2 and 3 of 2026-10-23 are implemented on another branch; the YAEM levels follow the Bildiri rule exactly (C-13 note, not recomputed here); the active reporting entry-point list in D-08b is complete (built from file names that mention the historical labels: `cli_engine.py`, `dashboard_utils.py`, `obsolete_results.py`, `results_reader.py`, `routers/benchmark.py`, `tools/mark_obsolete_ga_split_variant_results.py`); evaluation bounds are upper bounds, not expected counts.
