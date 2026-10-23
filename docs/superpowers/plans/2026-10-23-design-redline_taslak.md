# Design-document redline proposal (Gate D, OQ-14 a)

Status: DRAFT proposal for the owner's approval. Nothing here is applied yet. [DECISION_LOG.md:486]

The owner chose OQ-14 a): the lead drafts a redline, the owner approves it, then D-11 and D-14 apply it. [DECISION_LOG.md:486; Gate D plan :330]

This file proposes changes to two documents: `ACADEMIC_STUDY_UNIFICATION_DESIGN.md` (section A) and `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md` (section B). Section C has one citation in a closed plan. Section D lists the choices the owner must make. Counts: A 23 changes, B 8, C 1; owner decisions OD-1 to OD-7.

Line numbers refer to the files on `WIP` at `0ddc56f3`. The main finding list is section 8 of `docs/superpowers/plans/2026-10-23-gate-d-analysis-documentation-publication.md` ("Gate D plan" below). [Gate D plan :369-380]

No proposed text changes a scientific value. Every value quoted below is copied from an existing decision or from live files.

Kind: **correction** = the text is behind a decision or live code. **choice** = see section D.

---

## A. `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`

### A1. Branch and publication model

**A1.1** Line :20 (Objective). Kind: correction, form per OD-1.
- Current: "publish the completed remediation on a branch and draft pull request without modifying `WIP` directly."
- Proposed: "publish the completed remediation by pushing `WIP` and opening a draft pull request `WIP -> main` that states that paper-scale verification on the stronger computer is pending."
- Source: DECISION_LOG.md:486 (OQ-13 a); Gate D plan :40, :371 (every package merged into `WIP` by the lead; `WIP` is `origin/HEAD`); `.git/packed-refs:71-72` (local refs list `origin/WIP` and `origin/main`).

**A1.2** Line :30 (Approved Decision 7). Kind: correction, form per OD-1.
- Current: "Preserve the current rescue checkout and perform work on `codex/reconcile-native-protocol`."
- Proposed: "Preserve the rescue checkout. Each work item runs in its own worktree and branch from `WIP`. The lead merges reviewed items into `WIP` with `--no-ff`."
- Source: Gate D plan :20, :40, :371; `docs/superpowers/specs/2026-08-01-wip-branch-consolidation-design.md:22` (`codex/reconcile-native-protocol` `002d461` is an ancestor of `WIP`, "Do not merge"), :62-68 (rescue head preserved as `archive/local-rescue-20260721`, `e0824b4`); `.git/packed-refs:78` (tag `refs/tags/archive/local-rescue-20260721`).
- Wording of "rescue checkout": per OD-7.
- [EKSİK: the path of the physical rescue checkout, if one still exists.]

**A1.3** Line :420 (Delivery Plan). Kind: correction.
- Current: "Work remains on `codex/reconcile-native-protocol` and is decomposed into four separately planned and gated work packages."
- Proposed: "Work is merged into `WIP` package by package and is decomposed into four separately planned and gated work packages."
- Source: Gate D plan :40, :371; `docs/superpowers/specs/2026-08-01-wip-branch-consolidation-design.md:22, :62-68`.

**A1.4** Lines :457-458 (Package D bullets). Kind: correction.
- Current: "fetch and inspect remote divergence;" / "push the branch and open a draft pull request."
- Proposed: "fetch and inspect divergence of `origin/WIP`;" / "with the owner's explicit permission, push `WIP` and open a draft pull request `WIP -> main`."
- Source: DECISION_LOG.md:486 (OQ-13 a); Gate D plan :277 (D-12: push and PR need the owner's explicit permission).

**A1.5** Line :460 (Gate D). Kind: correction.
- Current: "... documentation is consistent, the integration worktree is clean, and the draft PR explicitly awaits powerful-computer verification."
- Proposed: "... documentation is consistent, `git status --short` prints nothing after the suites and the integration worktree is clean, and the draft PR `WIP -> main` explicitly awaits powerful-computer verification."
- Source: Gate D plan :100 (criterion 11); DECISION_LOG.md:486.

**A1.6** Line :464. Kind: correction.
- Current: "Before publication, fetch the remote, inspect divergence, and reconcile only in the integration worktree. Never pull directly into the rescue checkout."
- Proposed: keep both sentences and add: "If the remote has new commits, the Gate D checks are rerun on the reconciled commit before anything is pushed."
- Source: Gate D plan :277.

**A1.7** Line :466. Kind: correction.
- Current: "After proportionate local checks pass, push the branch and open a draft pull request. The draft remains unmerged until the user returns the powerful-computer full-suite and pilot results."
- Proposed: "After proportionate local checks pass, push `WIP` at the commit the checks ran on and open a draft pull request `WIP -> main`. Its text states that paper-scale runs and full-suite verification on the stronger computer are pending. The draft remains unmerged until the user returns the powerful-computer full-suite and pilot results."
- Source: DECISION_LOG.md:486 (OQ-13 a); Gate D plan :100, :277.

**A1.8** Line :498 (Completion Criterion 10). Kind: correction.
- Current: "The branch is pushed and a draft pull request is opened for powerful-computer verification."
- Proposed: "`WIP` is pushed and a draft pull request `WIP -> main` is opened for powerful-computer verification."
- Source: DECISION_LOG.md:486 (OQ-13 a).

### A2. Catalog, composition kinds and the design addition

**A2.1** After the capability table (:116-131), as a paragraph below it, not a row. Kind: correction, placement per OD-3.
- Current: the table lists 14 IDs; `Core-GA-TSP-Memetic-2opt` is absent.
- Proposed (new paragraph after :131): "Design addition (DECISION_LOG A17, C-16c): `Core-GA-TSP-Memetic-2opt`, study label `GA-2opt`, a counted memetic GA with initial and final 2-opt. It is VERIFIED for TSP and ATSP, fixed and native. The live catalog holds the 14 IDs above plus this addition: 15 VERIFIED IDs, no candidate or planned ID."
- Source: DECISION_LOG.md:441, :464, :473; `uniride_core/algorithms/capabilities.py:395`.
- Note: `academic_benchmark/tests/test_gate_c_normative_catalog.py:31, :88-90` asserts exactly 14 table rows and reads the table up to the first line that does not start with `|` (:76-78). A paragraph below the table does not change what the test reads.

**A2.2** After the algorithm list (:156-171). Kind: correction.
- Current: the list ends with "HHO-ALNS."; it has no memetic GA and does not name composition kinds.
- Proposed: add the list item "GA-2opt (memetic GA, design addition A2.1);" and after :173 the sentence: "The catalog uses the kinds `pure`, `memetic_2opt`, `local_search`, `global_then_final_3opt` and `global_then_final_alns`; the enum also declares `population_based`, which no claim uses today. The four hybrid IDs keep their names; their kinds are `global_then_final_3opt` / `global_then_final_alns` and their labels say '(final polish once)'."
- Source: `uniride_core/algorithms/capabilities.py:44-50, :411-414`; DECISION_LOG.md:444, :460, :462, :463, :464.

### A3. Alias compatibility and migration table

**A3.1** ID migration table, lines :146-148 (policy column). Kind: correction.
- Current: `Numba-GWO`, `Core-GWO-TSP` and `Numba-HHO`, `Core-HHO-TSP`: "backward-compatible alias preserving current semantics"; `SOTA-ALNS-TSP`: "backward-compatible alias; manifests emit `ALNS-TSP`".
- Proposed: for all three rows "deprecated input alias with warning (CLI only); a manifest that names it is refused". The `SOTA-ALNS-TSP` row keeps "manifests emit `ALNS-TSP`".
- Source: `academic_benchmark/core/algorithm_resolution.py:52-56` (policy `DEPRECATED`); `academic_benchmark/tests/test_algorithm_resolution.py:78-90` (manifest source raises `DeprecatedManifestIdentifierError`).

**A3.2** ID migration table, rows :139-148. Kind: correction.
- Current: the table does not say whether a legacy name is still a registry entry.
- Proposed: add below the table: "These names have no registry entry of their own. Their raw registry entries are removed: `Numba-GA`/`Numba-PSO` in C-14, and `Core-GWO-TSP`, `Core-HHO-TSP`, `Numba-2-opt`, `Numba-3-opt-bounded`, `Numba-Or-opt`, `Numba-GWO`, `Numba-HHO`, `SOTA-ALNS-TSP` in the routing-refusal follow-up `58f77d66`. `B-GA` and `B-PSO` are refused like `GWO-LKH`/`HHO-LKH` and name `Core-GA-TSP` / `Core-PSO-TSP`."
- Source: DECISION_LOG.md:470, :471; `academic_benchmark/core/algorithm_resolution.py:65-71`.

**A3.3** ID migration table, new rows (or a pointer; per OD-5). Kind: choice (OD-5).
- Current: no rows for matrix engines or routing names.
- Proposed rows:
  - matrix engines: served only as `Matrix-TwoOpt/GA/PSO/GWO/HHO-TSP-legacy`; rows stored under the old `Core-*` matrix names are never pooled with `Matrix-*-legacy` rows. [DECISION_LOG.md:445, :470]
  - `CVRP-/CVRPTW-Numba-Swap` and `-Numba-Hybrid`: names kept for stored results; they run `Matrix-TwoOpt-TSP-legacy`. [DECISION_LOG.md:478-479; `academic_benchmark/core/registry_setup.py:1668-1693`]
  - routing refusals: see A4.1.

### A4. Routing refusals

**A4.1** Line :383 (Algorithm contracts). Kind: correction.
- Current: "unsupported CVRP/CVRPTW requests fail clearly;"
- Proposed: "unsupported CVRP/CVRPTW requests fail clearly: every `Core-*` catalog ID, `ALNS-TSP`, `Numba-Swap`, `Numba-Hybrid`, `SOTA-E2BSO-TSP`, `SOTA-R2DMA-TSP`, `SOTA-P-AOEA-TSP`, `SOTA-CGO-TSP`, `SOTA-RUN-TSP` and `FCM-GA/PSO/GWO/HHO-TSP` refuse CVRP/CVRPTW on every path; legacy routing engines run only under the `CVRP-*` / `CVRPTW-*` names;"
- Source: DECISION_LOG.md:469, :471, :476, :478, :479; `academic_benchmark/core/registry_setup.py:559, :1703` (`ALNS-TSP`).

### A5. Study profile schema and analysis plans

**A5.1** Line :215. Kind: correction.
- Current: "an analysis-plan ID;"
- Proposed: "an analysis-plan ID that resolves to `academic_benchmark/studies/<study>/analysis_plan.json` (schema `uniride-analysis-plan/v1`). Paper mode refuses a plan that does not resolve or is not `active`. The exact-reference link lives in the analysis plan; `study.json` stays unlinked;"
- Source: DECISION_LOG.md:489 (D-09), :491 (D-06); `academic_benchmark/studies/bildiri2026/study.json:67`; `academic_benchmark/studies/yaem2026/study.json:79`; `academic_benchmark/studies/bildiri2026/analysis_plan.json:2-5, :84-88`.

**A5.2** Line :220. Kind: correction.
- Current: "Run manifests use `uniride-run/v1` and contain the reproducibility fields defined below."
- Proposed: "Run manifests use `uniride-run/v1` (one per run) and contain the reproducibility fields defined below. A campaign index uses `uniride-run-index/v1`. Analysis plans use `uniride-analysis-plan/v1`."
- Source: DECISION_LOG.md:489, :493; `academic_benchmark/analysis/manifests.py:9-13`.

### A6. Experimental protocol

**A6.1** After line :285 (Primary protocol). Kind: correction.
- Current: no rule on secondary stopping keys in fixed-budget runs.
- Proposed (new sentences): "On fixed-budget paths every stopping key is written explicitly: `max_no_improvement` and `max_iterations` for GWO/HHO (flat IDs and the composite global stage; the ALNS polish stage also needs `max_no_improvement`), and `max_iterations` for 2-opt, 3-opt and Or-opt. A missing or non-positive key is refused before any evaluation, so no registry default can end a fixed-budget run early. Native Or-opt also requires `max_iterations`."
- Source: DECISION_LOG.md:475 (owner decision 3), :477, :478 (decision 3), :479, :480.

**A6.2** Line :287. Kind: correction.
- Current: "Because one budget level may favor some algorithm families, study manifests may predeclare multiple budget levels. Results at different levels remain separate and are not pooled."
- Proposed: keep both sentences and add: "Levels may scale with the instance (`scaled_fixed_budget_levels`; Bildiri 2026: 50x and 250x n(n-1)/2). Rows are grouped by the budget level index within the dataset's own level list, never by raw budget across instances."
- Source: DECISION_LOG.md:466, :468, :486 (OQ-2 a), :490; `academic_benchmark/analysis/identity.py:16`.

**A6.3** Proposes a new subsection "Comparison identity" after line :297 (no such heading exists today). Kind: correction.
- Current: the design names fixed/native separation (:203, :291) but no key below the protocol group.
- Proposed (new subsection text): "`assert_single_pooling_group` keeps fixed-budget, native and exact rows apart and nothing more; it maps fair v1 and fair v2 rows to one pooling group. Analysis also requires equal comparison-cell keys (`academic_benchmark/analysis/identity.py`): exact `protocol_version` (fair v1 and v2 never share a cell), study, dataset, budget level index, algorithm, configuration hash (including `termination_policy`, excluding timing fields), backend policy and profile, seed protocol and base seed, evidence class, commit and tree state. A family may vary only the algorithm and/or the dataset."
- Source: DECISION_LOG.md:490 (D-01); `academic_benchmark/protocol_registry.py:43-44, :89`; `academic_benchmark/analysis/identity.py:3, :13, :16`.

### A7. Statistics environment

**A7.1** Line :335. Kind: correction.
- Current: "The implementation uses a proven statistical library under a pinned scientific environment."
- Proposed: keep the sentence and add: "SciPy 1.18.1 and statsmodels 0.15.0, with their dependencies, are pinned in `requirements-analysis.txt` for academic analysis only, not as an operational dependency. NumPy 2.4.6, llvmlite 0.48.0 and Numba 0.66.0 stay pinned by `academic_benchmark/jit-benchmark-constraints.txt`. Effect sizes these libraries do not provide (epsilon-squared, matched-pairs rank-biserial, Kendall's W) will be local code (Gate D item D-05), tested against published examples. Each study's tests, alpha and effect sizes are predeclared in its analysis plan."
- Source: `requirements-analysis.txt:1-18` (:6-7 for the effect sizes); `academic_benchmark/jit-benchmark-constraints.txt:9-11`; DECISION_LOG.md:492, :494, :489.

### A8. Reproducibility manifest granularity

**A8.1** Line :339. Kind: correction.
- Current: "Each pilot or experiment records:"
- Proposed: "Each run (algorithm x dataset x budget level x replicate) writes one `RunManifestV1` that records:"
- Source: DECISION_LOG.md:493 (D-02); `academic_benchmark/analysis/manifests.py:9-13`; Gate D plan :171, :376.

**A8.2** After line :352. Kind: correction.
- Current: "A detached `<manifest>.sha256` file contains the run manifest's checksum. ..."
- Proposed: keep the paragraph and add: "A campaign index (`run_index.json`, `uniride-run-index/v1`) lists every run manifest with its checksum and holds the seed protocol version; it has its own detached `.sha256`. Files are written atomically, each sidecar after its file and the index last, so a crash never verifies. The `statistics_library` field holds the literal `none` until a caller in the pinned environment passes `statistics_library_identifier()` (`scipy==1.18.1+statsmodels==0.15.0`)."
- Today: no non-test caller passes `statistics_library_identifier()` yet.
- Source: DECISION_LOG.md:493, :494; `academic_benchmark/analysis/manifests.py:12-13, :48-50, :55, :122`; `academic_benchmark/analysis/environment.py:17, :68-72`; `academic_benchmark/studies/smoke.py:476, :534`; `academic_benchmark/tests/test_analysis_environment.py:95-100` (the only caller).

### A9. Packaging

**A9.1** Line :371. Kind: choice (OD-2). Text below is option a).
- Current: "packaging smoke tests prove archives are excluded and study profiles are included."
- Proposed (option a, ship): "packaging smoke tests prove that archives, `*_legacy` packages and `tsplib.db` files are excluded, and that both study profiles, their analysis plans and the dataset manifests they reference are included, with nothing else under `studies/` or `datasets/`."
- Proposed (option b, repository-only): "packaging smoke tests prove that archives, `*_legacy` packages, `tsplib.db` files, study profiles and analysis plans are excluded; study profiles are read from the repository."
- Source: DECISION_LOG.md:495 (D-14); `pyproject.toml:31-35`.

---

## B. `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`

**B1** Line :17. Kind: correction.
- Current: "Existing GWO/HHO public registry names remain registered. Because their implementations include initial, periodic, and final 2-opt polishing, those aliases report the truthful `memetic_2opt` variant."
- Proposed: "The former GWO/HHO registry names (`Numba-GWO`, `Numba-HHO`, `Core-GWO-TSP`, `Core-HHO-TSP`) are no longer registry entries. The resolver keeps them as deprecated CLI aliases, with a warning, that resolve to `Core-GWO-TSP-Memetic-2opt` / `Core-HHO-TSP-Memetic-2opt`. A manifest that names them is refused."
- Source: DECISION_LOG.md:470, :471; `academic_benchmark/core/algorithm_resolution.py:52-55`; `academic_benchmark/tests/test_algorithm_resolution.py:78-90`.

**B2** Line :24. Kind: correction.
- Current: "`algorithm_family`: `GWO`, `HHO`, `2-opt`, or `3-opt`;"
- Proposed: "`algorithm_family`: `GWO`, `HHO`, `GA`, `PSO`, `ALNS`, `2-opt`, `3-opt` or `Or-opt`;"
- Source: `academic_benchmark/fairness.py:451-472, :789`.

**B3** Line :25. Kind: correction.
- Current: "`variant`: at minimum `pure` or `memetic_2opt`;"
- Proposed: "`variant`: `pure`, `memetic_2opt`, `global_then_final_3opt` or `global_then_final_alns`;"
- Optional addition: "Local searches, ALNS, PSO and pure GA carry `pure`."
- Source: `academic_benchmark/fairness.py:645-677, :651, :721-747`; `academic_benchmark/composite_protocol.py:43-45`; `academic_benchmark/core/registry_setup.py:314, :397, :1780` (2-opt, 3-opt, Or-opt `pure`), `:1876` (ALNS), `:1236` (PSO), `:1075` (GA pure or `memetic_2opt`), `:1486-1503` (GWO/HHO pure or `memetic_2opt`), `:1423` (hybrids: the composite kind).

**B4** Lines :68-73 (new explicit identities). Kind: correction.
- Current: lists four IDs (`Core-GWO-TSP-Pure`, `Core-GWO-TSP-Memetic-2opt`, `Core-HHO-TSP-Pure`, `Core-HHO-TSP-Memetic-2opt`).
- Proposed: keep the four and add: "The full set of canonical identities is the 15 VERIFIED IDs of the capability catalog (`uniride_core/algorithms/capabilities.py`), listed in the unification design's capability table and its design addition."
- Source: DECISION_LOG.md:473; `uniride_core/algorithms/capabilities.py:378-414`.

**B5** Line :75. Kind: correction.
- Current: "Existing GWO/HHO aliases remain backward-compatible and report `variant=memetic_2opt`."
- Proposed: "Deprecated GWO/HHO aliases resolve to the memetic 2-opt canonical IDs (CLI only, with a warning)."
- The second sentence of :75 ("Pure variants disable ...") stays.
- Source: `academic_benchmark/core/algorithm_resolution.py:52-55`; DECISION_LOG.md:471.

**B6** After line :62 (Atomic Upper-Bound Budget). Kind: correction.
- Current: rule 6 allows "another declared termination condition"; no rule says the condition must be written.
- Proposed (new rule 8): "On fixed-budget paths the secondary stopping keys are written explicitly: `max_no_improvement` and `max_iterations` for GWO/HHO, `max_iterations` for 2-opt, 3-opt and Or-opt. A missing or non-positive key is refused before any evaluation."
- Source: DECISION_LOG.md:475, :477, :478, :479.

**B7** After line :91 (Manifest and Validation). Kind: correction.
- Current: no statement on protocol versions in analysis.
- Proposed: "Rows of different protocol versions (`uniride-fair-tsp-v1`, `uniride-fair-tsp-v2`) are never one comparison cell, although the protocol registry puts them in one pooling group."
- Source: DECISION_LOG.md:490; `academic_benchmark/protocol_registry.py:43-44, :89`; `academic_benchmark/analysis/identity.py:13`.

**B8** Line :112. Kind: choice (OD-4). This is a rewording; no source shows the current sentence is false.
- Current: "It does not claim Numba parity in the current NumPy 2.5.1 environment."
- Proposed: "It does not claim Numba parity in the ordinary interpreter's NumPy 2.5.1 environment (recorded 2026-07-17). The JIT benchmark environment is separate and pins NumPy 2.4.6, llvmlite 0.48.0 and Numba 0.66.0 (`academic_benchmark/jit-benchmark-constraints.txt`)."
- Source: `academic_benchmark/ACADEMIC_ALGORITHM_VALIDATION_AUDIT_2026-07-17.md:26`; `.superpowers/sdd/task-c1-6-report.md:26`; `academic_benchmark/jit-benchmark-constraints.txt:6-11`; Gate D plan :372.

---

## C. Other document (outside the two designs)

**C1** `docs/superpowers/plans/2026-10-19-gate-c-catalog-composition-experiment-services.md` lines :270 and :403. Kind: choice (OD-6).
- Current: "`fair_pilot.py:283-300`" for `fair_pilot._prepare_output_dir`.
- Proposed: at :270, delete only ", `fair_pilot.py:283-300`" (the line already names `fair_pilot._prepare_output_dir`); at :403, "rules of `fair_pilot._prepare_output_dir`".
- Source: `academic_benchmark/fair_pilot.py:341` (the function now starts here); Gate D plan :379 (it was at :327 when the Gate D plan was written).

---

## D. Decisions the owner must make

**OD-1. How to treat superseded approved text in the unification design (A1.1, A1.2).**
- a) Replace the text in place.
- b) Keep the original sentence and add a dated note: "Superseded 2026-10-23 by DECISION_LOG A18 (OQ-13 a)", followed by the new text.
- Recommendation: b) for :20 and :30 (they are the approval record); a) for the operational lines :420, :457-458, :460, :464, :466, :498.

**OD-2. Study profiles in the wheel (OQ-14 packaging choice; A9.1).**
- a) Ship: both `study.json`, both `analysis_plan.json` and the 7 referenced dataset manifests. This is the state after D-14 (`e75f4783`). [DECISION_LOG.md:495; `pyproject.toml:34-35`]
- b) Repository-only: remove the two package-data lines and flip the positive assertions in `test_gate_d_packaging.py` together, as D-14 recorded. [DECISION_LOG.md:495]
- Pros a: already built and tested; paper mode resolves the plan next to the profile [DECISION_LOG.md:495]. Cons a: academic configuration travels in the same wheel as `optimizer_api` [`pyproject.toml:29`]; the rule that production code does not import study profiles (unification design :91, :369) is unchanged by shipping.
- Pros b: the wheel carries no study configuration. Cons b: a code and test change, and :371 changes meaning.
- Recommendation: a).

**OD-3. Where the design addition `Core-GA-TSP-Memetic-2opt` goes (A2.1).**
- a) A paragraph below the capability table (no test change).
- b) A 15th table row; `test_gate_c_normative_catalog.py` (`NORMATIVE_ROW_COUNT = 14`, `DESIGN_ADDITIONS`) must then change with review. [`academic_benchmark/tests/test_gate_c_normative_catalog.py:31-35, :88-104`]
- Recommendation: a).

**OD-4. Fairness design: amend in place or mark as partly superseded (section B).**
- a) Apply B1-B8 in place.
- b) Leave the text and add a status line that points to the unification design and the live catalog for families, variants and IDs.
- Recommendation: a), because B1, B2 and B5 state facts that are false today, and B3 is incomplete against the live code. B8 is optional wording within a).

**OD-5. Where the new migration rows live (A3.3).**
- a) In the design's ID migration table and in the D-11 master-document table.
- b) Only in the D-11 master-document table; the design gets one sentence that points to it. A3.1 and A3.2 (corrections of existing rows) apply either way. [Gate D plan :269]
- Recommendation: b), so there is one table for the D-11 consistency test to check.

**OD-6. The stale citation in the closed Gate C plan (C1).**
- a) Replace the line number with the function name.
- b) Leave the closed plan unchanged; D-11 notes the drift.
- Recommendation: a).

**OD-7. The term "rescue checkout" at design :30 and :464 (A1.2, A1.6).**
- a) Keep "rescue checkout".
- b) Say "the preserved rescue head" (`archive/local-rescue-20260721`, `e0824b4`). [`docs/superpowers/specs/2026-08-01-wip-branch-consolidation-design.md:62-68`]
- Recommendation: [EKSİK: no source states whether a physical rescue checkout still exists; the owner chooses.]

---

## Considered, not proposed

- :354 (clean tree for paper mode) and the resumption half of :362: D-03 is not merged yet, so no text change is proposed. [Gate D plan :180-185; DECISION_LOG.md:485-495 lists no D-03 merge]
- The fixed-budget GWO/HHO schedule that follows the budget is a change of canonical behaviour. It is outside the topics of this brief. [DECISION_LOG.md:467-468]
