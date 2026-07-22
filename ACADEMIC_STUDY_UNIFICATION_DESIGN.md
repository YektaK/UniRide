# Academic Study Unification and Evidence Quarantine Design

Date: 2026-07-22  
Status: Approved for implementation planning
Scope: `uniride_core`, `academic_benchmark`, the Bildiri 2026 and YAEM 2026 research subtrees, their historical evidence, and the Git delivery boundary

## Objective

Replace the independent Bildiri 2026 and YAEM 2026 research engines with reproducible study profiles over one canonical algorithm kernel and one academic experiment platform.

The remediation must:

- physically quarantine invalid or historically unverifiable research artifacts without deleting them;
- remove active solver ownership from paper-specific packages;
- preserve current validated GWO/HHO behavior while relocating it from `academic_benchmark.bildiri2026`;
- expose all approved algorithm families under truthful names;
- make fixed objective-evaluation budgets the primary comparison protocol and native termination a separately labelled secondary protocol;
- support future TSP, ATSP, CVRP, CVRPTW, and UniRide studies without coupling the production application to academic configuration;
- stop after code, tests, manifests, and small smoke/pilot validation;
- publish the completed remediation on a branch and draft pull request without modifying `WIP` directly.

## Approved Decisions

1. Use physical archival rather than in-place warnings.
2. Unify both YAEM 2026 and Bildiri 2026; neither remains an independent active engine.
3. Keep GWO, HHO, 2-opt, 3-opt, GA, PSO, Or-opt, standalone ALNS, GWO-ALNS, HHO-ALNS, GWO-3opt, and HHO-3opt available to active studies.
4. Rename pseudo-LKH variants to `GWO-3opt` and `HHO-3opt`. The active system must not expose an LKH identity unless it calls a genuine LKH implementation.
5. Use fixed evaluation budgets for the primary paper comparison and native termination for secondary analysis.
6. Generate only deterministic tests and small smoke/pilot evidence during remediation. Full paper experiments will run later on a more powerful computer.
7. Preserve the current rescue checkout and perform work on `codex/reconcile-native-protocol`.

## Non-Goals

This remediation does not:

- run full paper-scale experiments;
- implement genuine LKH;
- implement new CVRP or CVRPTW algorithms;
- force permutation TSP solvers into vehicle-routing contracts;
- rewrite Git history to remove historical binary size;
- repair old numerical results by relabelling them;
- change the Next.js user experience or FastAPI request surface except where an import boundary or production-readiness check requires it;
- claim algorithm superiority from smoke/pilot data.

## Target Architecture

### Canonical kernel

`uniride_core` owns:

- canonical problem and result contracts;
- objective, distance, feasibility, and route-completeness validation;
- canonical algorithm implementations;
- capability metadata;
- reusable fixed-budget accounting primitives;
- no paper names, report templates, TSPLIB database orchestration, FastAPI handlers, or frontend DTOs.

Algorithms remain grouped by problem contract rather than forced through one weak universal interface:

- `PermutationSolver` covers TSP and ATSP Hamiltonian cycles;
- `VehicleRoutingSolver` covers CVRP, CVRPTW, and UniRide multi-route problems;
- both return a common result envelope containing identity, objective, termination, accounting, backend, and audit metadata.

### Academic experiment platform

`academic_benchmark` owns:

- dataset adapters and problem manifests;
- algorithm selection through the canonical registry;
- fixed-budget and native-termination execution protocols;
- run scheduling and deterministic seed derivation;
- independent result validation;
- reproducibility manifests;
- statistically valid analysis and report generation;
- study-profile loading.

### Study profiles

Paper-specific active material moves under:

```text
academic_benchmark/studies/
|-- bildiri2026/
`-- yaem2026/
```

A study profile may contain configuration, dataset selection, protocol selection, paper metadata, and report templates. It may not contain algorithms, objective implementations, distance functions, budget counters, statistical tests, copied benchmark runners, or generated research conclusions.

### Production application

`optimizer_api` consumes canonical algorithms only through the production registry. A strategy must declare `production_ready=true` before it can be exposed to the API. The API, frontend, and map-provider code must not import study profiles or academic result artifacts.

The academic platform may evaluate production-capable algorithms; production must never depend on academic study configuration.

## Capability Model

Every canonical algorithm registration declares at least:

- canonical public name and family;
- problem contracts supported: TSP, ATSP, CVRP, CVRPTW, or UniRide;
- directed-cost support;
- capacity and time-window support;
- deterministic or stochastic behavior;
- supported termination protocols;
- exact objective-accounting support;
- execution backend truthfulness;
- production-readiness state;
- optional composition stages.

Preflight validation rejects unsupported algorithm/problem combinations before a run begins. A symmetric-only solver cannot accept an asymmetric matrix, and a permutation-only solver cannot claim CVRP support.

### Initial academic capability matrix

The following target IDs and values are normative for this remediation. `exact-fixed` means the adapter must pass objective-accounting tests before the capability is enabled.

| Canonical ID | Study label | Problems | Directed | Fixed | Native | Production ready |
|---|---|---|---|---|---|---|
| `Core-TwoOpt-TSP` | `2-opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-ThreeOpt-TSP` | `3-opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-OrOpt-TSP` | `Or-opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-GA-TSP` | `GA` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-PSO-TSP` | `PSO` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-GWO-TSP-Pure` | `GWO-Pure` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-HHO-TSP-Pure` | `HHO-Pure` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-GWO-TSP-Memetic-2opt` | `GWO-2opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-HHO-TSP-Memetic-2opt` | `HHO-2opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `ALNS-TSP` | `ALNS` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-GWO-TSP-Memetic-3opt` | `GWO-3opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-HHO-TSP-Memetic-3opt` | `HHO-3opt` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-GWO-TSP-Memetic-ALNS` | `GWO-ALNS` | TSP, ATSP | yes | exact-fixed | yes | false |
| `Core-HHO-TSP-Memetic-ALNS` | `HHO-ALNS` | TSP, ATSP | yes | exact-fixed | yes | false |

The active production strategy registry is a separate CVRP/CVRPTW/UniRide surface. This remediation snapshots every currently exposed production strategy key and preserves it. No existing API strategy is removed or made unavailable merely because academic TSP IDs default to `production_ready=false`. The production-readiness gate initially marks the existing API inventory as grandfathered `true`, subject to its current optional-dependency availability, and requires an explicit reviewed decision for any new strategy. Snapshot tests prevent accidental exposure changes.

### ID migration rules

| Legacy academic name | Canonical target | Policy |
|---|---|---|
| `Numba-2-opt` | `Core-TwoOpt-TSP` | deprecated input alias with warning |
| `Numba-3-opt-bounded` | `Core-ThreeOpt-TSP` | deprecated input alias with warning |
| `Numba-Or-opt` | `Core-OrOpt-TSP` | deprecated input alias with warning |
| `Numba-GA` | `Core-GA-TSP` | deprecated input alias with warning |
| `Numba-PSO` | `Core-PSO-TSP` | deprecated input alias with warning |
| `GWO` | `Core-GWO-TSP-Pure` | unqualified active study label means the pure variant |
| `HHO` | `Core-HHO-TSP-Pure` | unqualified active study label means the pure variant |
| `Numba-GWO`, `Core-GWO-TSP` | `Core-GWO-TSP-Memetic-2opt` | backward-compatible alias preserving current semantics |
| `Numba-HHO`, `Core-HHO-TSP` | `Core-HHO-TSP-Memetic-2opt` | backward-compatible alias preserving current semantics |
| `SOTA-ALNS-TSP` | `ALNS-TSP` | backward-compatible alias; manifests emit `ALNS-TSP` |
| `GWO-LKH` | `Core-GWO-TSP-Memetic-3opt` | hard error identifying the truthful replacement; no executable alias |
| `HHO-LKH` | `Core-HHO-TSP-Memetic-3opt` | hard error identifying the truthful replacement; no executable alias |

Stored manifests and new reports always emit canonical IDs, never compatibility aliases.

## Canonical Algorithm Set

The unified TSP/ATSP catalog exposes:

- GWO-Pure, with `GWO` as its unqualified study label;
- HHO-Pure, with `HHO` as its unqualified study label;
- GA;
- PSO;
- 2-opt;
- canonical 3-opt;
- Or-opt;
- standalone ALNS;
- GWO-2opt;
- HHO-2opt;
- GWO-3opt;
- HHO-3opt;
- GWO-ALNS;
- HHO-ALNS.

`GWO-3opt` and `HHO-3opt` are explicit bounded-3-opt compositions. They must not cite or imply Helsgaun LKH.

Hybrid algorithms are compositions of registered canonical stages rather than copied paper-specific classes. Global search and polishing share one injected budget counter and one result/audit contract.

### Hybrid composition semantics

`GWO-2opt` and `HHO-2opt` preserve the already validated initial/periodic/final 2-opt policy during mechanical relocation. Their exact polish schedule and evaluation accounting are emitted in the result metadata.

The new `GWO-3opt`, `HHO-3opt`, `GWO-ALNS`, and `HHO-ALNS` compositions use these rules:

1. The global stage is the corresponding pure canonical GWO or HHO implementation; it performs no hidden polish.
2. The polish stage runs once on the global stage's best complete validated tour. It receives the same matrix, problem identity, directionality, and objective evaluator.
3. Three-opt compositions call `Core-ThreeOpt-TSP`. ALNS compositions call `ALNS-TSP`. No YAEM class is promoted.
4. Parameters use separate `global` and `polish` namespaces. Paper-scale manifests may not rely on implicit hyperparameter defaults.
5. The default smoke allocation is `global_fraction=0.80`. The global stage has a maximum of `floor(B * 0.80)` evaluations; the polish stage may consume the remaining `B - used_global`. Other allocations must be explicit manifest values.
6. Both stages share the same atomic counter. Neither stage may start an atomic phase that would exceed its stage or total limit.
7. The global stage uses the run seed. Deterministic 3-opt records no secondary seed. Stochastic ALNS receives a stable derived seed from `SHA-256(protocol_version, run_seed, "polish")`, never Python `hash()`.
8. Budget exhaustion is normal termination. If the global stage cannot produce a valid tour, the composition fails. A polish exception or invalid result fails the run instead of silently returning an unpolished result.
9. The final result records stage identities, parameters, seeds, allocated and consumed evaluations, termination reasons, and whether the polish changed the tour.

These rules define algorithm identity. Changing invocation timing, stage algorithm, transfer semantics, seed derivation, or allocation policy requires a new variant or protocol version.

In native-termination mode, rules 1-4 and 7-9 remain in force, but no fixed budget `B`, `global_fraction`, or shared upper-bound allocation is imposed:

1. The pure global stage runs to its explicitly configured canonical native stopping conditions.
2. After a valid global result, the final polish stage runs once using its own explicitly configured native iteration, no-improvement, or time limits.
3. Native 3-opt uses its declared local-search termination. Native ALNS uses its declared ALNS termination and stable derived polish seed.
4. Objective-evaluation counts and runtimes remain measured separately for both stages and are summed for descriptive reporting, not capped.
5. The aggregate termination is `composite_complete` only when both stages complete validly, with both stage termination reasons retained. A failed or invalid stage fails the composite run.

Fixed-budget and native hybrid results therefore represent different declared protocols and cannot be pooled or ranked as one sample.

## Study Profile Schema

Study profiles use UTF-8 JSON validated against `academic_benchmark/schemas/study-v1.schema.json`. The schema ID is `uniride-study/v1`, uses `additionalProperties: false` at contract objects, and requires:

- `schema_version`, `study_id`, `title`, and `status`;
- canonical `algorithm_ids` and explicit parameter objects;
- dataset-manifest references by stable dataset ID;
- `primary_protocol` and optional `secondary_protocol`;
- fixed-budget levels, run count, base seed, and seed-protocol version;
- problem families permitted by the study;
- an analysis-plan ID;
- output policy and paper metadata.

References resolve only through the canonical registry and repository-relative dataset manifests; absolute paths and path traversal are rejected. Unknown IDs, compatibility aliases, capability mismatches, missing required values, and unsupported schema versions fail before execution.

Dataset manifests use `uniride-dataset/v1` and require ID, source, checksum, problem type, dimension, matrix/distance semantics, and optimum/BKS provenance. Run manifests use `uniride-run/v1` and contain the reproducibility fields defined below. Schema migrations create a new version; active files are never interpreted heuristically.

## Bildiri 2026 Migration

Bildiri 2026 cannot be archived in one step because active registry and fairness code import its GWO/HHO and Numba functionality.

Migration proceeds in this order:

1. Characterize existing seeded behavior with parity fixtures for route, cost, objective-evaluation count, termination reason, and backend.
2. Mechanically relocate still-authoritative GWO/HHO and required Numba kernels into canonical `uniride_core` modules without changing equations or results.
3. Replace Bildiri 2-opt and 3-opt ownership with the existing canonical core implementations.
4. Reuse canonical GA/PSO implementations where parity and contract requirements are satisfied; relocate only behavior that is both required and not already canonical.
5. Redirect registry, CLI, fair/native pilots, and tests to canonical imports.
6. Prove that no active code imports `academic_benchmark.bildiri2026`.
7. Archive the remaining runner, tuning, reporting, data-management, result, presentation, and paper material.
8. Create the thin `academic_benchmark/studies/bildiri2026` profile.

The mandatory rule is: relocate with exact parity first, redesign composition second, and rerun evidence last.

For parity, symmetric Hamiltonian cycles are compared after canonical rotation and reversal normalization. Directed cycles are compared after rotation only because reversal changes ATSP semantics. Objective, evaluation count, termination reason, and backend must match exactly; numeric objectives may use only the existing tested floating-point tolerance.

## YAEM 2026 Migration

The complete legacy `academic_benchmark/yaem2026` tree is moved to:

`archive/academic_benchmark/yaem2026_legacy/`

No legacy YAEM solver or statistical implementation is promoted into active code. Canonical algorithms and platform services replace those implementations.

The new `academic_benchmark/studies/yaem2026` profile selects algorithms, problem sets, primary and secondary protocols, run counts, budget levels, and report templates.

False legacy labels are not retained as active aliases. Historical files preserve their original text for provenance, but active configuration rejects `GWO-LKH` and `HHO-LKH` and points users to the truthful migration names.

## Evidence Quarantine

The remaining Bildiri tree is moved to:

`archive/academic_benchmark/bildiri2026_legacy/`

Each legacy archive contains:

- `QUARANTINE.md` describing confirmed defects and permitted uses;
- a machine-readable manifest with original relative path, archive path, byte size, SHA-256, and evidence classification;
- the preserved historical directory structure.

Evidence classifications are:

- `INVALID`: structurally or mathematically invalid outputs, including all YAEM `student_matrix` results derived from incomplete tours and reports derived from invalid statistical pairing;
- `HISTORICAL_UNVERIFIED`: coordinate-based or otherwise plausible results that lack a complete current provenance, fair-budget, environment, or validation chain;
- `REFERENCE_ONLY`: legacy source, configurations, presentation material, and evaluated design paths that may inform engineering history but cannot support numerical claims.

Before any archive file is staged, a credential and sensitive-data scan runs. A confirmed credential is never committed. Its archive manifest entry is recorded as `WITHHELD_SENSITIVE` with original relative path, byte size, and SHA-256 but no secret content; the original remains untouched in the rescue checkout pending user-directed revocation or secure storage. Personal absolute paths without credentials may remain in preserved raw evidence but are prohibited from active documentation and generated reports. Ambiguous high-risk matches block publication and require user review.

Moving files does not rehabilitate results. Archived evidence must not be used in current reports, imported by active Python packages, or discovered as default benchmark input.

Physical archival does not reduce Git history size. Any future history rewrite requires a separate decision and authorization.

## Experimental Protocol

### Primary protocol

The primary comparison uses the existing `atomic_upper_bound_v1` fixed objective-evaluation policy.

One evaluation is one complete closed-solution objective calculation for one candidate. Iterations, neighborhood loops, swaps, random draws, and delta checks are not silently substituted for this unit.

Initialization, global search, local search, and hybrid polishing consume the same declared cap. An atomic phase starts only when its proven upper bound fits in the remaining budget. Results record configured and consumed evaluations.

Because one budget level may favor some algorithm families, study manifests may predeclare multiple budget levels. Results at different levels remain separate and are not pooled.

### Secondary protocol

Native termination is reported separately with explicit stopping conditions, runtime, objective-evaluation count, and backend. Native results cannot be merged into fixed-budget rankings.

### Seed protocol

Seeds are derived deterministically from protocol version, base seed, normalized problem identity, and replicate index. Python's randomized `hash()` is prohibited.

The manifest records the complete schedule. Equal numeric seeds are not by themselves treated as proof of statistical pairing across unrelated algorithms.

## Result Validation

The common result envelope includes `solution_kind`, canonical algorithm identity, problem identity, objective, protocol/accounting fields, backend, termination, audit metadata, and exactly one problem-specific solution payload.

For `hamiltonian_cycle`, every accepted result is independently checked for:

- exact node membership and uniqueness;
- route completeness;
- closed-cycle objective recomputation;
- directed arc orientation for ATSP;
- algorithm identity and capability consistency;
- evaluation-budget compliance;
- backend truthfulness;
- termination-reason consistency.

For `vehicle_routes`, the payload is a list of routes. Depot repetition at route boundaries is valid; customers must appear exactly once across all routes unless the problem contract explicitly permits optional service. Validation independently checks depot placement, customer coverage, capacity, time windows, vehicle limits, route closure, and aggregate objective. Hamiltonian uniqueness rules are never applied to vehicle-routing solutions.

A failed validation invalidates the run and prevents aggregation. The platform records the failure boundary and does not fabricate or repair a tour for reporting.

## Statistical Protocol

The active platform does not retain fixed F thresholds, handwritten approximate p-values, or pairing by coincidental run index.

For independent repeated-run distributions on one problem:

- use a justified independent-sample omnibus test such as Kruskal-Wallis;
- perform pairwise Mann-Whitney comparisons only when justified;
- apply Holm correction over the declared comparison family;
- report effect sizes and exact sample counts.

For genuinely matched cross-instance comparisons:

- use a justified matched omnibus test such as Friedman;
- use paired post-hoc tests only over the same experimental units;
- report assumptions, corrections, effect sizes, and exclusions.

The implementation uses a proven statistical library under a pinned scientific environment. Smoke pilots produce descriptive summaries only and cannot emit superiority, causality, or proof language.

## Reproducibility Manifest

Each pilot or experiment records:

- schema and protocol versions;
- Git commit and dirty-tree state;
- Python, operating system, CPU, NumPy, Numba, llvmlite, and statistical-library versions;
- dataset source, checksum, type, dimension, optimum or BKS provenance, and matrix semantics;
- canonical algorithm identity, capability declaration, configuration, and composition stages;
- base seed and complete derived seed schedule;
- budget levels, budget policy, actual objective-evaluation count, and stage allocation;
- termination reason and runtime;
- independent validation result;
- output file checksums, excluding the run manifest itself.

A detached `<manifest>.sha256` file contains the run manifest's checksum. This prevents self-referential hashing while still making the manifest independently verifiable.

Paper-scale mode requires a clean tree. Smoke mode may run on a dirty tree only when the manifest and report label that state prominently.

## Error Handling

The platform fails before execution when a manifest, dataset, capability, budget, or backend requirement is unsatisfied.

Runtime failures produce a structured failed-run record containing algorithm, problem, seed, stage, exception category, and consumed budget. Failed runs are never converted into worst-case numeric observations without an explicit predeclared statistical policy.

Manifests and result files use atomic write/replace behavior so interrupted experiments cannot masquerade as complete runs. Resumption validates the existing manifest and rejects incompatible configuration changes.

## Verification Strategy

### Import boundaries

- `uniride_core` cannot import `academic_benchmark` or study profiles.
- production code cannot import study profiles or archives.
- active code cannot import legacy Bildiri or YAEM paths.
- packaging smoke tests prove archives are excluded and study profiles are included.

### Relocation parity

- fixed matrices and seeds compare pre-extraction and canonical GWO/HHO route, cost, evaluation count, termination, and backend;
- Python fallback and JIT paths retain deterministic parity where the supported environment permits it;
- canonical imports replace all active Bildiri imports before archival.

### Algorithm contracts

- every TSP and ATSP result is a complete permutation;
- directed costs are independently preserved;
- unsupported CVRP/CVRPTW requests fail clearly;
- truthful names are enforced and legacy LKH names are rejected.

### Fairness and composition

- objective use never exceeds the configured cap;
- global and polish stages share one atomic counter;
- boundary tests cover one unit below, exactly at, and one unit above an atomic phase requirement;
- fixed and native results cannot be accidentally aggregated together.

### Study and evidence integrity

- Bildiri and YAEM profiles validate against one versioned schema;
- archive manifests reproduce file checksums;
- invalid evidence cannot be loaded by active report generation;
- personal paths and secret-like material receive a quarantine scan without silently changing preserved raw evidence.

### Statistical integrity

- known synthetic fixtures verify omnibus, post-hoc, correction, and effect-size outputs;
- mismatched or falsely paired designs are rejected;
- undersized smoke pilots cannot produce inferential claims.

### Smoke pilots and regression suites

- run a small symmetric TSPLIB case;
- run a small directed ATSP fixture and minimal-budget `ft53` case;
- exercise fixed-budget primary and native secondary paths;
- run the full automated `academic_benchmark/tests` suite, not paper-scale benchmark execution;
- run `uniride_core` tests with optional-solver environment failures separated from source defects;
- run API tests in the proper FastAPI environment;
- run packaging/import smoke checks and `git diff --check`.

No full TSPLIB/CVRPLIB experiment is generated during remediation.

## Delivery Plan

Work remains on `codex/reconcile-native-protocol` and is decomposed into four separately planned and gated work packages. A later package cannot begin until the prior package's acceptance gate passes.

### Package A: YAEM quarantine and contract foundation

- scan and physically archive YAEM;
- create archive classification/checksum manifest;
- add study, dataset, and run schema contracts;
- add import/package boundary tests.

Gate A: YAEM is non-importable, archive checksums reproduce, no sensitive material is staged, and existing automated academic tests remain green.

### Package B: Bildiri canonical extraction

- add characterization/parity fixtures;
- mechanically relocate required GWO/HHO and Numba behavior;
- redirect registry, pilots, CLI, and tests;
- prove zero active Bildiri imports;
- only then archive the remaining Bildiri tree and create its study profile.

Gate B: parity passes, JIT/fallback checks are reported accurately, zero-import proof passes, archive checksums reproduce, and existing production registry exposure is unchanged.

### Package C: catalog, composition, and experiment services

- implement the normative canonical-ID/capability table;
- add truthful 3-opt and ALNS hybrid compositions;
- enforce shared budget and result contracts;
- implement study loading, result validation, and fixed/native separation;
- create the YAEM active study profile.

Gate C: all capability, accounting, hybrid-boundary, TSP/ATSP, schema, and smoke-pilot tests pass.

### Package D: analysis, documentation, and publication

- implement statistically guarded analysis over validated results;
- add reproducibility manifests and descriptive smoke reports;
- synchronize master documentation and migration tables;
- run proportionate automated suites and packaging checks;
- fetch and inspect remote divergence;
- push the branch and open a draft pull request.

Gate D: no invalid evidence is reachable from active reporting, local checks are recorded exactly, documentation is consistent, the integration worktree is clean, and the draft PR explicitly awaits powerful-computer verification.

Each package receives its own implementation plan and reviewable commits. Bildiri archival can never precede Gate B's relocation parity and zero-import checks.

Before publication, fetch the remote, inspect divergence, and reconcile only in the integration worktree. Never pull directly into the rescue checkout.

After proportionate local checks pass, push the branch and open a draft pull request. The draft remains unmerged until the user returns the powerful-computer full-suite and pilot results.

## Expected Risks and Required Mitigations

- **Behavior drift during Bildiri extraction:** mechanical relocation and parity gates precede refactoring.
- **Incommensurate evaluation accounting:** a single documented complete-objective unit and injected counter are mandatory.
- **Hybrid budget leakage:** all stages share one cap and boundary tests.
- **Over-generalized problem abstraction:** use separate permutation and vehicle-routing protocols.
- **Irrecoverable legacy evidence:** archive rather than relabel; rerun all publishable results.
- **Budget-dependent rankings:** predeclare multiple levels and separate native results.
- **Broken legacy names:** provide a migration table but no false active alias.
- **Large archival diff:** isolate `git mv` operations from code changes.
- **Repository size retention:** do not rewrite history in this scope.
- **Scientific-environment incompatibility:** pin and record versions; separate environment blockers from defects.
- **JIT platform variance:** maintain focused deterministic parity tests and require powerful-computer verification.
- **Production contamination:** import-boundary and `production_ready` gates.
- **Remote branch drift:** fetch and inspect before push; preserve the rescue checkout.
- **Premature CVRP expansion:** define contracts now and implement future adapters in separately scoped work.

## Completion Criteria

The remediation is complete when:

1. Both legacy research engines are physically archived with reproducible manifests and evidence classifications.
2. No active code imports a legacy research engine.
3. Required GWO/HHO behavior resides canonically in `uniride_core` and passes relocation parity tests.
4. Both paper projects exist as schema-valid study profiles.
5. All approved algorithm families are selectable under truthful names and valid capabilities.
6. Fixed-budget and native protocols remain distinct and validated.
7. Small TSP/ATSP smoke pilots produce complete, independently verified results and reproducibility manifests without scientific superiority claims.
8. Proportionate local suites pass, with external environment blockers identified precisely.
9. Master documentation describes the verified architecture and quarantined evidence truthfully.
10. The branch is pushed and a draft pull request is opened for powerful-computer verification.
