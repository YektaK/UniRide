# Academic Capability Catalog and Preflight Design

**Date:** 2026-07-28  
**Status:** Approved for implementation planning  
**Package:** C1 — Capability catalog and preflight validation  
**Depends on:** Package A study contracts and Package B Bildiri canonical extraction

## 1. Context

UniRide now has canonical academic GWO/HHO implementations in `uniride_core`, strict study and dataset contracts, and an academic executor registry. The remaining selection path still allows algorithm identity, problem compatibility, execution protocol, and backend availability to be inferred from registry membership or historical names. That is not sufficient evidence for scientific execution.

Package C1 introduces one authoritative, immutable description of evidenced TSP/ATSP capabilities and a separate academic resolver/preflight service. The catalog describes facts; the resolver translates identifiers; preflight decides whether a requested run is permitted. Solver construction remains the responsibility of the academic executor registry.

This design covers canonical TSP and directed ATSP algorithms only. CVRP, CVRPTW, production aliases, and hybrid composition implementation remain outside C1.

## 2. Goals

1. Give every canonical academic TSP/ATSP algorithm a stable identity.
2. Make capability claims granular and evidence-gated.
3. Reject unsupported algorithm, problem, protocol, composition, or backend combinations before solver execution.
4. Require canonical identifiers in persisted study manifests while retaining explicitly approved CLI compatibility.
5. Prevent silent Numba-to-Python fallback.
6. Preserve the production strategy registry's public 38-key exposure exactly.
7. Detect drift between catalog claims, executor availability, and executable evidence.

## 3. Non-goals

- Implementing or changing a solver.
- Changing GWO/HHO search behavior, budgets, termination, objective accounting, or random seeding.
- Implementing GWO/HHO with 3-opt or ALNS composition.
- Cataloging CVRP or CVRPTW algorithms.
- Changing the FastAPI or frontend surface.
- Changing the production strategy registry.
- Moving or archiving Bildiri or YAEM material.
- Running full TSPLIB/CVRPLIB experiments or generating benchmark reports.

## 4. Architectural Decision

C1 uses two layers with one-way dependencies:

```text
uniride_core immutable capability catalog
                  ↑
academic identifier resolver and preflight service
                  ↑
study manifest / CLI / academic runner
                  ↓
academic executor registry
                  ↓
result-contract validation
```

The core catalog must not import `academic_benchmark`, CLI code, study schemas, or executor factories. Academic services may import the core catalog. Identifier resolution must not construct or inspect a solver at runtime. Preflight may verify that a canonical executor is registered, but it must not execute that solver.

## 5. Core Capability Model

The catalog belongs in `uniride_core/algorithms/capabilities.py`. Its public structures are frozen typed values, exposed through read-only mappings and tuples.

### 5.1 Enumerations

- `ProblemContract`: `TSP`, `ATSP`
- `ExecutionProtocol`: `FIXED_BUDGET`, `NATIVE_TERMINATION`
- `BackendKind`: `NONE`, `PYTHON`, `NUMBA_NOPYTHON`
- `BackendPolicy`: `PYTHON_ONLY`, `PREFER_NUMBA_OBJECTIVE`, `REQUIRE_NUMBA_OBJECTIVE`
- `LifecycleStatus`: `VERIFIED`, `CANDIDATE`, `PLANNED`
- `CompositionKind`: `PURE`, `MEMETIC_2OPT`, `LOCAL_SEARCH`, `POPULATION_BASED`

`BackendPolicy` represents a caller request, not an algorithm capability. It may be colocated with the shared types, but the academic caller owns the chosen value. The external spellings `prefer_numba` and `require_numba` map to the explicitly objective-scoped enum values; they do not assert that every composition stage is compiled.

`CANDIDATE` means an implementation exists but no capability tuple is selectable until evidence is attached. `PLANNED` means the canonical identity is reserved for work that is not yet implemented. `VERIFIED` means at least one granular claim is selectable; it does not imply that every possible problem, protocol, or backend is supported.

### 5.2 `ExecutionBackendProfile`

Backend identity is stage-aware. A frozen profile contains:

- `objective`: `PYTHON` or `NUMBA_NOPYTHON`;
- `polish`: `NONE`, `PYTHON`, or `NUMBA_NOPYTHON`.

The profile models existing truthful values such as `objective=numba;polish=python`. A single backend enum value must never flatten a mixed-stage execution into an inaccurate `numba` label.

### 5.3 `CapabilityClaim`

One claim represents one evidenced executable combination. It contains:

- problem contract;
- execution protocol;
- execution backend profile;
- composition kind;
- directed-cost support;
- exact objective-evaluation accounting support;
- fixed-seed determinism support;
- truthful termination and backend reporting support;
- one or more executable evidence identifiers.

Evidence identifiers are stable pytest node IDs or named contract fixtures, not prose citations. A claim cannot be selectable when its evidence set is empty.

### 5.4 `AlgorithmCapability`

Each frozen algorithm entry contains:

- canonical algorithm ID;
- algorithm family;
- human-readable label;
- lifecycle status;
- immutable tuple of `CapabilityClaim` objects;
- `production_ready`, which is `False` for every C1 academic entry;
- optional planning note for non-selectable entries.

Selectability is derived, not manually asserted: an algorithm is selectable only for an exact request matched by a verified claim. `CANDIDATE` and `PLANNED` entries are discoverable but always non-selectable.

### 5.5 Catalog invariants

- Canonical IDs are unique and case-sensitive.
- Canonical, alias, and planned-ID namespaces cannot collide.
- No claim may imply another problem, protocol, composition, or backend.
- TSP evidence never implies ATSP support.
- Python evidence never implies Numba nopython support.
- Fixed-budget evidence never implies native-termination support.
- Pure evidence never implies memetic support, or vice versa.
- ATSP claims must explicitly assert directed-cost preservation.
- Fixed-budget claims must assert exact, no-overshoot objective accounting.
- Candidate and planned entries have no selectable claims.
- Candidate entries correspond to an implemented executor awaiting evidence; planned entries reserve an unimplemented identity.
- Catalog construction fails immediately if an invariant is violated.

## 6. Initial Catalog Policy

The Package B parity surface provides the initial selectable baseline:

| Canonical ID | Composition | Initially eligible protocols | Problem scope |
|---|---|---|---|
| `Core-GWO-TSP-Pure` | pure | fixed and native, independently evidenced | TSP and ATSP, independently evidenced |
| `Core-HHO-TSP-Pure` | pure | fixed and native, independently evidenced | TSP and ATSP, independently evidenced |
| `Core-GWO-TSP-Memetic-2opt` | memetic 2-opt | fixed only | TSP and ATSP, independently evidenced |
| `Core-HHO-TSP-Memetic-2opt` | memetic 2-opt | fixed only | TSP and ATSP, independently evidenced |

The table defines candidates, not blanket activation. Each exact problem/protocol/backend tuple becomes selectable only when its executable evidence passes in C1.

The following current families begin C1 with lifecycle `CANDIDATE` and remain non-selectable until granular contract tests prove their claims:

- `Core-TwoOpt-TSP`
- `Core-ThreeOpt-TSP`
- `Core-OrOpt-TSP`
- `Core-GA-TSP`
- `Core-PSO-TSP`
- canonical ALNS-TSP ID, after its identity and executor ownership are established

C1 may add a canonical academic registry ID pointing to an already-valid implementation when required to align identity. Such wiring must not alter algorithm behavior.

The following are reserved `PLANNED` entries for Package C2 and cannot be selected:

- `Core-GWO-TSP-Memetic-3opt`
- `Core-HHO-TSP-Memetic-3opt`
- `Core-GWO-TSP-Memetic-ALNS`
- `Core-HHO-TSP-Memetic-ALNS`

## 7. Identifier Resolution

Identifier resolution belongs in `academic_benchmark/core/algorithm_resolution.py` and is independent of executor lookup.

### 7.1 Identifier sources

- `MANIFEST`: persisted scientific configuration;
- `CLI`: interactive or scripted compatibility boundary;
- `INTERNAL`: already-canonical application calls.

### 7.2 Manifest rules

- Only an exact canonical ID is accepted.
- Deprecated aliases, case variants, and fuzzy matches are rejected.
- Unknown, candidate, and planned IDs produce distinct errors.
- The manifest schema stores only the canonical ID.

### 7.3 CLI rules

- Exact canonical IDs are preferred.
- A historical alias is accepted only when an explicit alias table maps it to a behaviorally equivalent canonical ID.
- Alias use emits a deprecation warning to stderr.
- Execution and results record the canonical ID, plus the originally requested identifier when provenance requires it.
- Alias approval requires executable equivalence; similarity of names is insufficient.
- False LKH, pseudo-LKH, ambiguous, or behavior-changing aliases are rejected with a replacement hint when one exists.
- Resolution is exact and case-sensitive; no fuzzy matching is permitted.

The following migration table is normative for CLI input. Every noncanonical identifier in this table remains invalid in stored manifests.

| Requested CLI ID | Canonical target | Policy |
|---|---|---|
| `Numba-2-opt` | `Core-TwoOpt-TSP` | deprecated alias with warning |
| `Numba-3-opt-bounded` | `Core-ThreeOpt-TSP` | deprecated alias with warning |
| `Numba-Or-opt` | `Core-OrOpt-TSP` | deprecated alias with warning |
| `Numba-GA` | `Core-GA-TSP` | deprecated alias with warning |
| `Numba-PSO` | `Core-PSO-TSP` | deprecated alias with warning |
| `GWO` | `Core-GWO-TSP-Pure` | active unqualified CLI label for the pure variant |
| `HHO` | `Core-HHO-TSP-Pure` | active unqualified CLI label for the pure variant |
| `Numba-GWO`, `Core-GWO-TSP` | `Core-GWO-TSP-Memetic-2opt` | compatibility alias preserving current semantics |
| `Numba-HHO`, `Core-HHO-TSP` | `Core-HHO-TSP-Memetic-2opt` | compatibility alias preserving current semantics |
| `SOTA-ALNS-TSP` | `ALNS-TSP` | compatibility alias with canonical output |
| `B-GA` | `Core-GA-TSP` | hard error with replacement hint |
| `B-PSO` | `Core-PSO-TSP` | hard error with replacement hint |
| `GWO-LKH` | `Core-GWO-TSP-Memetic-3opt` | hard error; truthful replacement only, never executable alias |
| `HHO-LKH` | `Core-HHO-TSP-Memetic-3opt` | hard error; truthful replacement only, never executable alias |

`B-GA` and `B-PSO` retain Package A's current rejection behavior. LKH identifiers never resolve to executable algorithms. Alias acceptance is still conditional on the target's exact capability passing preflight; resolution alone never makes a candidate or unsupported tuple selectable.


### 7.4 Resolution result

The typed result contains:

- requested identifier;
- canonical identifier;
- identifier source;
- whether an alias was used;
- warning code/message, if applicable.

## 8. Preflight Service

Preflight belongs in `academic_benchmark/core/preflight.py`.

### 8.1 Input

`PreflightRequest` contains:

- complete immutable `ResolutionResult`, including requested and canonical identity;
- canonical problem object supplied by the active loader;
- execution protocol;
- caller-declared backend policy;
- requested evaluation budget when fixed-budget mode is used;
- executor-registry availability snapshot;
- runtime backend-availability snapshot.

The backend policy is mandatory at the call boundary. Global environment state must not silently choose policy.

The public `preflight_run` boundary accepts the actual problem, not a caller-supplied validation Boolean. It invokes the named canonical `validate_problem_for_preflight` validator, which returns a frozen `ProblemValidationReport` containing problem identity, declared contract, dimension, matrix fingerprint, directedness, and structural checks. The report is embedded in the decision. If an existing Package A validator already owns these checks, planning must extend or adapt that owner rather than create a competing validator.

No governed caller may construct a trusted `ProblemValidationReport` directly.

### 8.2 Backend policy

- `PYTHON_ONLY`: select an evidenced profile whose objective stage is Python; polish is `NONE` or Python as required by the composition.
- `PREFER_NUMBA_OBJECTIVE`: prefer an evidenced profile whose objective stage is Numba nopython; when unavailable before execution, select an independently evidenced Python-objective profile and record the fallback decision.
- `REQUIRE_NUMBA_OBJECTIVE`: require an evidenced and runtime-available Numba nopython objective stage. An explicitly evidenced Python polish stage remains valid for a memetic composition.

`PREFER_NUMBA_OBJECTIVE` permits an explicit pre-execution fallback decision, not a silent fallback. The decision must be included in the preflight result and final run metadata.

An unexpected mid-run objective fallback invalidates that execution attempt because its observed profile differs from the preflight decision. A Python retry is permitted only as a new attempt with a new attempt identifier and a fresh preflight decision selecting the Python-objective profile. No policy permits a result to relabel an already-executed attempt.

Numba availability requires a truthful runtime probe that establishes importability and the required nopython execution path. Package presence alone is not availability evidence.

### 8.3 Problem checks

- TSP and ATSP are distinct contracts.
- ATSP execution requires an exact ATSP claim with directed-cost support.
- Matrix dimension must agree with the problem definition.
- Off-diagonal costs must satisfy the active dataset contract.
- A symmetric matrix presented as ATSP is not automatically reclassified; caller and dataset metadata remain authoritative.
- Route completeness and independent closed-cycle cost are validated after execution.

### 8.4 Protocol checks

- Fixed-budget execution requires a positive budget and an exact-accounting claim.
- Atomic upper-bound enforcement must prevent objective-evaluation overshoot.
- Native execution requires a separately evidenced native-termination claim.
- A fixed-budget claim cannot authorize native execution.
- Memetic and pure identifiers are separate compositions and cannot substitute for each other.

### 8.5 Output

`PreflightDecision` contains:

- complete immutable `ResolutionResult`; the canonical algorithm ID is derived from it;
- selected exact capability claim;
- frozen `ProblemValidationReport`;
- execution protocol;
- requested backend policy;
- selected `ExecutionBackendProfile`;
- explicit fallback status and reason;
- executor registry ID;
- evidence identifiers used to authorize the run.

The decision is immutable and is passed to executor construction and post-execution validation.

## 9. Failure Model

Expected validation failures use typed exceptions with stable machine-readable codes:

- `UnknownAlgorithmError`
- `PlannedAlgorithmError`
- `CandidateAlgorithmError`
- `DeprecatedManifestIdentifierError`
- `ForbiddenAliasError`
- `UnsupportedProblemContractError`
- `UnsupportedProtocolError`
- `BackendUnavailableError`
- `CapabilityEvidenceError`
- `ExecutorUnavailableError`
- `ResultContractViolation`

CLI adapters convert these failures to concise user-facing messages and non-zero exit codes. Library callers retain the typed exception. Generic `ValueError` strings are not the public failure contract.

## 10. Execution and Result Validation

The academic execution flow is:

```text
request
  -> resolve identifier
  -> look up immutable capability
  -> preflight exact claim and backend
  -> construct registered executor
  -> execute
  -> validate result against preflight decision
  -> persist canonical identity and actual backend
```

Post-execution validation must:

1. verify a complete, duplicate-free permutation of the expected dimension;
2. independently recompute the directed or symmetric closed-cycle objective;
3. compare the independent cost to the reported cost;
4. verify evaluation count and no-overshoot behavior for fixed-budget runs;
5. verify truthful termination reason for native runs;
6. parse the truthful stage-aware observation and verify that its full `ExecutionBackendProfile` equals the preflight-selected profile;
7. keep existing `algorithm` and `algorithm_id` fields canonical and equal, and store the original CLI input separately as optional `requested_algorithm_id` when an alias was used.

Failure after solver execution is a `ResultContractViolation`; invalid output must not be persisted as a successful scientific run.

## 11. Production Isolation

C1 must not import the capability catalog into production strategy registration and must not add, remove, or rename a production strategy. A regression fixture records the exact public production registry key set before C1 and asserts the same 38-key set afterward.

Academic capability metadata does not certify production readiness. Every C1 catalog entry therefore has `production_ready=False`. Actual production exposure is not a catalog field; it is derived and protected separately through the production registry's exact public-key snapshot.

## 12. File-Level Boundary

Expected implementation files:

- `uniride_core/algorithms/capabilities.py` — types, immutable catalog, invariants;
- `academic_benchmark/core/algorithm_resolution.py` — source-aware identity resolution;
- `academic_benchmark/core/preflight.py` — compatibility and backend decision;
- the canonical Package A validation owner, or `academic_benchmark/core/problem_validation.py` only if no such owner exists — construction of `ProblemValidationReport`;
- existing academic study schema modules — canonical manifest validation only;
- existing academic CLI and runner modules — resolver/preflight integration;
- existing result validator/accounting modules — decision-bound postflight checks;
- existing academic registry setup — canonical wiring only where evidence justifies it.

Expected focused test files:

- `academic_benchmark/tests/test_algorithm_capability_catalog.py`
- `academic_benchmark/tests/test_algorithm_resolution.py`
- `academic_benchmark/tests/test_algorithm_preflight.py`
- `academic_benchmark/tests/test_algorithm_capability_evidence.py`
- an existing or new production-registry snapshot regression test

Exact integration files must be confirmed from live source during implementation planning. No filename assumption authorizes creating a parallel schema, runner, or result model when a canonical owner already exists.

### 12.1 Governed execution boundaries

C1 integration is mandatory at every current public academic path that reaches the TSP/ATSP executor registry:

- `academic_benchmark.cli_engine._evaluate_param_combo`;
- `academic_benchmark.fair_pilot.run_fair_pilot`;
- `academic_benchmark.native_pilot.run_native_pilot`, including its delegated `_registry_executor` path;
- `academic_benchmark.smart_benchmark._run_single_task`.

Boundary tests must prove that each path resolves and preflights before calling `AlgorithmRegistry.get_executor`, and that a rejected request cannot enumerate or construct an executor. New public academic runners must use the same service.

Direct `AlgorithmRegistry.get_executor` remains a low-level internal/testing escape hatch for executor contract tests. Registry membership alone neither authorizes a scientific run nor creates a capability claim.


## 13. Verification Matrix

### 13.1 Catalog invariants

- unique canonical IDs;
- namespace collision rejection;
- empty evidence rejection for selectable claims;
- candidate- and planned-entry non-selectability;
- independent TSP/ATSP, fixed/native, pure/memetic, and stage-aware Python/Numba claims.

### 13.2 Resolver

- canonical manifest success;
- manifest alias rejection;
- approved CLI alias resolution and warning;
- unknown, candidate, planned, `B-GA`/`B-PSO`, false-LKH, ambiguous, and case-variant rejection;
- canonical result identity with optional separate requested-ID provenance.

### 13.3 Preflight

- symmetric TSP and directed ATSP;
- fixed and native protocols;
- pure and memetic-2opt compositions;
- all three backend policies;
- Numba available, unavailable, and unverified states;
- pure Python, pure Numba objective, and mixed Numba-objective/Python-polish profiles;
- registered and missing executor states;
- supported, unsupported, unverified, and planned combinations.
- all governed entry points rejecting before executor lookup;

### 13.4 Evidence promotion

TwoOpt, ThreeOpt, OrOpt, GA, PSO, and ALNS candidates require tests proving, for every promoted tuple:

- canonical executor ownership;
- complete permutation;
- independent symmetric or directed objective;
- exact fixed-budget accounting without overshoot, when claimed;
- native termination semantics, when claimed;
- truthful backend reporting;
- deterministic fixed-seed behavior, when claimed;
- absence of undocumented local-search polishing or composition mismatch.

### 13.5 Regression

- Package B GWO/HHO parity remains green;
- JIT/fallback reporting remains truthful;
- Package A strict study contracts remain green;
- production registry public keys remain exactly unchanged;
- focused C1 tests and the full academic suite pass;
- no benchmark CSV, database, or report artifact is generated.

## 14. C1 Acceptance Gate

C1 is complete only when all of the following are true:

1. Every catalog entry is `VERIFIED` with executable evidence, `CANDIDATE` with an existing implementation awaiting evidence, or `PLANNED` with a reserved unimplemented identity.
2. Every selectable tuple has granular problem, protocol, composition, and backend evidence.
3. Strict manifests accept canonical IDs only.
4. Approved CLI compatibility is explicit, warning-bearing, and canonicalized in output.
5. Unsupported requests fail before solver construction.
6. No backend fallback is silent; an unexpected mid-run fallback invalidates the attempt.
7. Catalog-to-executor drift is detected by tests.
8. Invalid solver output fails post-execution validation and is not persisted as success.
9. Production registry exposure remains the same exact 38-key set.
10. Every governed academic entry point invokes resolver and preflight before executor lookup.
11. Focused verification and the full academic test suite pass without generated benchmark artifacts.

## 15. Deferred Work

Package C2 may implement the reserved 3-opt and ALNS hybrid compositions. A later catalog extension may introduce CVRP/CVRPTW capability types, but it must preserve the same evidence-gated principles and must not overload TSP/ATSP claims.
