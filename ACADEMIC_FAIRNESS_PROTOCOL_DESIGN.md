# Academic TSP Fair-Comparison Protocol Design

Date: 2026-07-17  
Status: Approved for implementation  
Scope: `academic_benchmark`, the Bildiri 2026 GWO/HHO/2-opt adapters, and the canonical 3-opt integration

## Objective

Provide a reproducible comparison protocol for GWO, HHO, 2-opt, and canonical 3-opt in which every result carries an unambiguous algorithm identity, paired seed provenance, exact objective-evaluation accounting, an explicit local-search policy, and a common evaluation-budget contract.

The protocol must prevent pure and memetic algorithms, different seeds, different execution backends, or unequal computational budgets from being silently reported as equivalent experiments.

## Compatibility Boundary

Existing `RunResult.algorithm` and `RunResult.evaluations` consumers remain supported. Fairness fields are additive and optional outside fair-comparison mode. Inside fair-comparison mode, all required fields become mandatory and are validated before a result may be accepted.

The former GWO/HHO registry names (`Numba-GWO`, `Numba-HHO`, `Core-GWO-TSP`, `Core-HHO-TSP`) are no longer registry entries. The resolver keeps them as deprecated CLI aliases, with a warning, that resolve to `Core-GWO-TSP-Memetic-2opt` / `Core-HHO-TSP-Memetic-2opt`. A manifest that names them is refused. Separately named pure and memetic variants are added for new experiments.

## Result Contract

Each fair result records:

- `algorithm_id`: exact public registry name used for the run;
- `algorithm_family`: `GWO`, `HHO`, `GA`, `PSO`, `ALNS`, `2-opt`, `3-opt` or `Or-opt`;
- `variant`: `pure`, `memetic_2opt`, `global_then_final_3opt` or `global_then_final_alns`; local searches, ALNS, PSO and pure GA carry `pure`;
- `seed_group`: stable identifier derived only from the problem, replicate, and experiment base seed;
- `objective_evaluations`: exact number of complete candidate-tour objective evaluations;
- `evaluation_budget`: configured upper bound;
- `initialization_policy`: explicit route/population initialization description;
- `termination_policy`: explicit budget and secondary stopping conditions;
- `execution_backend`: backend actually used, not merely implied by a historical alias;
- `polish_policy`: explicit initial, periodic, and final polish behavior.

`algorithm` must equal `algorithm_id`, and `evaluations` must equal `objective_evaluations`, whenever fairness metadata is present.

## Paired Seed Protocol

A stable deterministic seed is derived from:

```text
protocol version + experiment base seed + normalized problem identity + replicate index
```

The derivation uses a stable digest and never Python's randomized `hash()`. Algorithm identity, model index, parameter-combination index, and execution order are excluded. Consequently, all algorithms within a `(problem, replicate)` group receive the same experimental seed and `seed_group`.

## Objective-Evaluation Definition

One evaluation is one complete closed-tour objective calculation for one candidate route. Iterations, neighborhood scans, swaps, position updates, and random draws are not evaluations.

Initialization, metaheuristic search, and enabled local-search polishing consume the same budget. Reporting code reuses the solver's known objective where possible; any additional complete-tour recomputation performed by an algorithmic adapter must also be counted. Counts may not be inferred from iteration numbers.

## Atomic Upper-Bound Budget

The selected policy is `atomic_upper_bound_v1`:

1. The configured evaluation budget is a hard upper bound and may never be exceeded.
2. A complete population initialization and a complete GWO/HHO population iteration are atomic phases.
3. A population phase starts only when a deterministic safe upper bound for its search evaluations fits within the remaining budget.
4. A local-search candidate evaluation is atomic. It starts only when one budget unit remains.
5. Scheduled polishing consumes the same budget. If its next candidate evaluation cannot start, polishing terminates without overshoot.
6. An algorithm may finish below the common budget because its next atomic phase does not fit or because another declared termination condition fires.
7. The result records both the budget and actual usage. Fair mode rejects overshoot, fabricated counts, and solvers whose exact accounting cannot be established.
8. On fixed-budget paths the secondary stopping keys are written explicitly: `max_no_improvement` and `max_iterations` for GWO/HHO, `max_iterations` for 2-opt, 3-opt and Or-opt. A missing or non-positive key is refused before any evaluation.

This preserves population-update equations: fair mode never advances to a partially evaluated GWO/HHO generation.

## Algorithm Identity and Variants

New explicit registry identities:

- `Core-GWO-TSP-Pure`
- `Core-GWO-TSP-Memetic-2opt`
- `Core-HHO-TSP-Pure`
- `Core-HHO-TSP-Memetic-2opt`

The full set of canonical identities is the 15 VERIFIED IDs of the capability catalog (`uniride_core/algorithms/capabilities.py`), listed in the unification design's capability table and its design addition.

Deprecated GWO/HHO aliases resolve to the memetic 2-opt canonical IDs (CLI only, with a warning). Pure variants disable initial, periodic, and final 2-opt calls; no GWO/HHO position-update or selection equation is changed.

Legacy local-search executors receive their registered public identity through the executor factory and may no longer emit `algorithm="legacy"`.

## Backend Truthfulness

`execution_backend` reports what actually executed. A historical `Numba-*` registry alias must not claim Numba execution when the environment used a Python fallback. Fair mode may reject a requested backend when it cannot be verified.

## Manifest and Validation

A `FairComparisonManifest` activates fair mode and contains at least:

- protocol version;
- base seed;
- common evaluation budget;
- budget policy;
- required metadata fields.

Validation rejects missing fields, identity mismatches, evaluation-field mismatches, budget overshoot, invalid seed provenance, ambiguous polish policies, and unsupported exact accounting. Unit tests use in-memory matrices and must not write benchmark artifacts.

Rows of different protocol versions (`uniride-fair-tsp-v1`, `uniride-fair-tsp-v2`) are never one comparison cell, although the protocol registry puts them in one pooling group.

## Verification Strategy

Focused tests prove:

- no public registry result reports `legacy`;
- algorithms in the same problem/replicate group share the seed and seed group;
- pure and memetic GWO/HHO results are distinguishable;
- fixed tiny matrix/seed runs have positive deterministic evaluation counts;
- objective usage never exceeds the common budget;
- fair validation rejects incomplete or contradictory metadata;
- existing result consumers remain compatible;
- canonical symmetric TSP and directed ATSP 3-opt behavior remains intact.

The requested regression suite and all new focused tests will be run without generating large TSPLIB results.

## Non-Goals

This change does not alter TSPLIB data, frontend or production API code, GWO/HHO search equations, canonical 3-opt neighborhood semantics, dependencies, or historical benchmark artifacts. It does not claim Numba parity in the ordinary interpreter's NumPy 2.5.1 environment (recorded 2026-07-17). The JIT benchmark environment is separate and pins NumPy 2.4.6, llvmlite 0.48.0 and Numba 0.66.0 (`academic_benchmark/jit-benchmark-constraints.txt`).
