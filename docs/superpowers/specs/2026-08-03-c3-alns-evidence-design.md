# C3 Standalone ALNS Evidence-Gated Promotion Design

**Date:** 2026-08-03  
**Status:** Approved for implementation planning  
**Package:** C3 — Standalone ALNS evidence-gated promotion  
**Depends on:** C1 capability/preflight contracts, Package B canonical extraction, and C2 Or-opt evidence promotion

## 1. Context

`ALNS-TSP` is a canonical `uniride_core` implementation and an academic-registry entry, but it remains a non-selectable `CANDIDATE`. Its current academic adapter returns a basic `RunResult`; it does not participate in the fixed-evaluation or native-termination contracts and does not report exact objective evaluations, termination reason, or stage-aware backend metadata.

The approved academic design requires standalone ALNS for symmetric TSP and directed ATSP. It also reserves later GWO/HHO–ALNS compositions. Those compositions must remain planned until standalone ALNS has independently proven objective correctness, deterministic behavior, budget accounting, and truthful result metadata.

## 2. Goals

1. Establish one canonical, deterministic ALNS execution path for TSP and directed ATSP.
2. Correct cyclic insertion scoring so boundary insertions use the same exact directed-cycle delta as interior insertions.
3. Add exact full-tour objective accounting with atomic upper-bound enforcement.
4. Support fixed evaluation budget as the primary comparison protocol and native termination as the secondary protocol.
5. Report complete normalized tours, independently reproducible costs, actual evaluation counts, truthful termination, and a Python-only backend profile.
6. Promote only `ALNS-TSP` from `CANDIDATE` to `VERIFIED` after executable evidence passes.
7. Preserve current production strategy exposure and keep all ALNS hybrid identities non-selectable.

## 3. Non-goals

- Implementing GWO/HHO–ALNS compositions.
- Changing GWO, HHO, GA, PSO, 2-opt, 3-opt, or Or-opt behavior.
- Promoting GA or PSO.
- Adding a Numba ALNS backend or claiming JIT execution.
- Changing the production strategy registry, FastAPI surface, frontend, dependencies, databases, or generated benchmark artifacts.
- Running full TSPLIB/CVRPLIB experiments.
- Refactoring unrelated SOTA solvers.

## 4. Architectural Decision

The canonical ALNS search remains owned by `uniride_core`. Academic code supplies protocol policy and converts the canonical search result into the strict scientific result contract.

```text
study/CLI request
  -> identifier resolution and evidence preflight
  -> academic ALNS protocol adapter
  -> canonical uniride_core ALNS search
  -> ObjectiveEvaluationBudget
  -> strict FairRunResult validation
  -> postflight validation and persistence
```

The core solver must not import `academic_benchmark`. The academic adapter may import the core solver and shared core accounting types. The ordinary non-scientific `ALNS-TSP` registry path remains compatible with its existing public identifier and parameter names.

## 5. Canonical Search Contract

### 5.1 Problem model

The search receives a complete matrix and a permutation containing every node exactly once. Node zero is an ordinary TSP/ATSP city, not a fixed or synthetic depot. The objective is the closed directed cycle:

```text
sum(matrix[route[i]][route[(i + 1) mod n]])
```

No symmetry inference is permitted. Every move and every independently reported cost must preserve matrix direction.

### 5.2 Initial solution

The current nearest-neighbor initialization remains the canonical ALNS initialization policy. It starts at node zero and uses outgoing directed costs. The initial complete tour consumes exactly one objective evaluation.

The random seed controls destroy/repair selection and simulated-annealing acceptance. Reconstructing or rerunning a solver with the same matrix, complete configuration, and nonzero seed must reproduce route, cost, objective-evaluation count, iteration count, and termination reason.

### 5.3 Destroy and repair behavior

Existing destroy and repair operator families remain unchanged except for correction of cyclic insertion scoring.

For inserting node `x` between predecessor `a` and successor `b`, every insertion position—including the duplicated start/end boundary representation—must use:

```text
matrix[a][x] + matrix[x][b] - matrix[a][b]
```

The implementation must not omit the removed closing edge at position zero or at the end of the linear representation. Tests must include a directed matrix where the old boundary formula selects a different position from the exact formula.

### 5.4 Objective accounting

`ObjectiveEvaluationBudget` remains the authoritative counter. One unit means one complete closed-tour objective evaluation.

- Initial complete tour: one unit.
- Each completed destroy/repair candidate: one unit.
- Operator delta calculations and roulette selection: zero units.
- No objective evaluation may start unless one unit remains.
- Fixed-budget execution must never overshoot, including a budget of one.
- Native execution uses an uncapped counter and reports the actual number consumed.

The canonical search result reports route, cost, iterations, evaluations, budget exhaustion, and termination reason. Compatibility wrappers may continue returning `TSPResult`, but scientific adapters must consume the exact accounting result rather than infer counts from iteration limits.

## 6. Termination Semantics

Only these reasons are valid for promoted ALNS claims:

- `evaluation_budget_exhausted`: the fixed protocol lacked capacity for the next complete candidate evaluation;
- `max_iterations`: the configured iteration ceiling was reached;
- `stagnation_limit`: the configured consecutive non-improvement ceiling was reached.

Fixed-budget results may terminate for any of the three reasons, but `budget_terminated` is true only for `evaluation_budget_exhausted`. Native results cannot report budget exhaustion and must have `evaluation_budget=None` and `budget_terminated=False`.

Iteration count means completed ALNS destroy/repair iterations. It must not be copied from configuration when fewer iterations actually ran.

## 7. Academic Adapter Contract

The academic registry retains:

- canonical identifier: `ALNS-TSP`;
- compatibility alias: `SOTA-ALNS-TSP`, resolved to canonical output by the existing resolver policy.

When a fixed or native manifest is present, the adapter must:

1. reject routing/CVRP inputs;
2. derive the paired seed from the manifest;
3. use the problem's canonical matrix without symmetrization;
4. run the canonical ALNS accounting path;
5. normalize the zero-indexed core route to the existing one-indexed academic result convention;
6. populate `FairRunResult` with exact values;
7. validate the result with the active manifest.

Required metadata:

- `algorithm` and `algorithm_id`: `ALNS-TSP`;
- `algorithm_family`: `ALNS`;
- `variant`: `pure`;
- `acceptance_policy`: `simulated_annealing` or `improving_only`, matching configuration;
- `initialization_policy`: `nearest_neighbor_from_node_zero_all_nodes`;
- `execution_backend`: a truthful Python-only observation;
- `polish_policy`: disabled at every stage;
- actual `iterations`, `evaluations`, `objective_evaluations`, and termination fields.

No result may imply Numba, hidden polishing, random-population initialization, or an ALNS hybrid composition.

## 8. Capability Promotion

`ALNS-TSP` becomes `VERIFIED` only with four independently evidenced claims:

| Problem | Protocol | Backend | Composition |
|---|---|---|---|
| TSP | fixed evaluation budget | Python objective, no polish | pure |
| ATSP | fixed evaluation budget | Python objective, no polish | pure |
| TSP | native termination | Python objective, no polish | pure |
| ATSP | native termination | Python objective, no polish | pure |

Every claim requires exact accounting, deterministic fixed-seed behavior, complete route validation, truthful reporting, and—where applicable—directed-cost preservation.

The following remain `PLANNED` with no claims:

- `Core-GWO-TSP-Memetic-ALNS`;
- `Core-HHO-TSP-Memetic-ALNS`.

Production readiness remains false. Production registry keys and exposure must remain byte-for-byte equivalent to their protected snapshot.

## 9. Validation Matrix

Focused evidence must use small in-memory matrices and fixed nonzero seeds.

### 9.1 Operator correctness

- symmetric cyclic insertion delta;
- directed cyclic insertion delta;
- start/end boundary scoring subtracts the replaced closing arc;
- repaired routes remain complete permutations.

### 9.2 Fixed-budget protocol

- TSP and genuinely asymmetric ATSP;
- budget one stops after the initial evaluation without overshoot;
- budget allowing candidates reports the exact consumed count;
- independent closed-cycle cost equals both reported cost fields;
- deterministic replay reproduces route, cost, evaluations, iterations, and reason.

### 9.3 Native protocol

- TSP and ATSP;
- uncapped exact counter;
- truthful `max_iterations` and `stagnation_limit` cases;
- no budget termination fields;
- deterministic replay.

### 9.4 Integration and regression

- strict manifest and capability evidence tests;
- resolver and preflight authorization for the exact four claims;
- fair and native pilot schema/record compatibility;
- alias canonicalization without duplicate capability identity;
- full academic suite;
- production registry exposure snapshot;
- no generated CSV, database, or report artifacts.

## 10. Expected File Boundary

Expected implementation owners, subject to live-source confirmation during planning:

- `uniride_core/algorithms/sota_tsp/repair_ops.py` — cyclic insertion correction;
- `uniride_core/algorithms/sota_tsp/alns_tsp.py` — exact accounting and canonical search result;
- `academic_benchmark/core/registry_setup.py` — fixed/native ALNS adapter;
- `academic_benchmark/fairness.py` and `academic_benchmark/native_protocol.py` — ALNS-specific result validation only;
- `uniride_core/algorithms/capabilities.py` — evidence-gated promotion;
- existing pilot/schema modules only where ALNS must be admitted to an already-governed list;
- focused ALNS tests and existing capability/manifest/registry regression tests.

No parallel result model, registry, budget counter, or ALNS implementation may be introduced when an existing canonical owner can be extended.

## 11. Acceptance Gate

C3 is complete only when:

1. cyclic insertion scoring is exact for TSP and directed ATSP;
2. fixed-budget execution never overshoots and reports exact complete-tour evaluations;
3. native execution reports its actual uncapped evaluations and truthful termination;
4. all four capability claims have stable executable evidence IDs;
5. deterministic replay passes for both problem types and protocols;
6. postflight independently validates complete routes and directed objectives;
7. `ALNS-TSP` is selectable only for the evidenced Python/no-polish profile;
8. ALNS hybrids remain planned and non-selectable;
9. production strategy exposure is unchanged;
10. focused and full academic verification pass without generated benchmark evidence.

## 12. Deferred Work

After C3, the project may implement GWO/HHO–ALNS compositions using a separately budgeted composition boundary. GA and PSO require their own design because their current implementations embed local search and do not expose exact population-level evaluation accounting.
