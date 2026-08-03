# C3 Standalone ALNS Evidence-Gated Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote only `ALNS-TSP` from `CANDIDATE` to four evidence-gated Python/no-polish TSP/ATSP fixed-budget/native claims, with exact directed objectives, deterministic replay, truthful termination, and unchanged production exposure.

**Architecture:** Keep ALNS search and its one shared `ObjectiveEvaluationBudget` in `uniride_core`; expose an accounted core result while preserving the ordinary `TSPResult` SOTA entry point. The academic registry owns protocol adaptation, the fair/native manifests own ALNS result validation, and the decision-bound gateway remains the independent route/cost/budget/backend verifier. Pilot loaders accept only the new strict scientific ALNS parameter schema and persist the existing canonical result records.

**Tech Stack:** Python 3.14, pytest, dataclasses, `ObjectiveEvaluationBudget`, `FairComparisonManifest`, `NativeComparisonManifest`, immutable capability catalog, `ExecutionBackendProfile`, existing `.venv-jit` interpreter.

## Global Constraints

- Work only in `C:\tmp\UniRide-package-c3` on `codex/package-c3-alns-evidence-20260803`; do not touch another checkout or worktree.
- Do not change production strategy registration, FastAPI, frontend, dependencies, databases, generated reports, benchmark CSVs, or the GWO/HHO/GA/PSO/2-opt/3-opt/Or-opt algorithms.
- Do not implement GWO/HHO-ALNS compositions, Numba ALNS, hidden polish, or any ALNS hybrid claim. The two ALNS hybrid catalog entries stay `PLANNED` with zero claims.
- Fixed comparison uses only `atomic_upper_bound_v1`: one unit is one full directed closed-tour objective; initialization and every completed ALNS candidate consume the same injected counter; delta scoring, selection, and random draws consume zero units.
- Native comparison uses `ObjectiveEvaluationBudget(None)`, reports actual objective evaluations, sets `evaluation_budget=None` and `budget_terminated=False`, and never emits `evaluation_budget_exhausted`.
- All academic ALNS records use canonical identity `ALNS-TSP`, `algorithm_family="ALNS"`, `variant="pure"`, `initialization_policy="nearest_neighbor_from_node_zero_all_nodes"`, disabled polish, and exactly `execution_backend="objective=python;polish=none"`.
- Use small in-memory symmetric TSP and genuinely asymmetric ATSP fixtures, fixed nonzero evidence seeds, complete 1-indexed academic tours, independent directed closed-cycle cost checks, and deterministic paired-seed replay.
- Strict scientific ALNS parameters are required: `max_iterations`, `max_no_improvement`, `remove_ratio`, `min_remove`, `segment_length`, `weight_update_factor`, and `use_sa`; optional: `sa_start_temp`, `sa_cooling_rate`. Reject `seed`, `iterations`, `max_no_improve`, `noise_scale`, and every other key.
- Preserve the exact protected production registry key set and the zero academic-capabilities production import boundary. Do not generate artifacts during tests.
- Do not commit or push unless separately authorized after the implementation and verification work is complete.

---

### Task 1: Freeze operator, accounting, and protocol behavior with failing focused fixtures

**Files:**
- Create: `academic_benchmark/tests/test_alns_c3_evidence.py`
- Inspect only: `uniride_core/algorithms/sota_tsp/alns_tsp.py`, `uniride_core/algorithms/sota_tsp/repair_ops.py`, `uniride_core/algorithms/objective_budget.py`, `academic_benchmark/core/registry_setup.py`

**Interfaces:**
- Consumes `GreedyInsertion`, `Regret2Insertion`, `Regret3Insertion`, `ALNS_TSP`, `ALNSConfig`, `ObjectiveEvaluationBudget`, `AlgorithmRegistry`, and the fair/native manifests.
- Produces the four concrete capability-evidence pytest nodes: `test_alns_fixed_tsp_evidence`, `test_alns_fixed_atsp_evidence`, `test_alns_native_tsp_evidence`, and `test_alns_native_atsp_evidence`.

- [ ] **Step 1: Write the focused fixture module before production changes.** Define two six-node in-memory problem objects compatible with preflight (`name`, `dimension`, `problem_type`, `dist_matrix`, `optimal=None`, `is_time_matrix=False`): one symmetric TSP matrix and one genuinely asymmetric ATSP matrix. Add these reusable helpers:

~~~python
def _closed_cost(one_indexed_tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in one_indexed_tour]
    return sum(matrix[node][route[(index + 1) % len(route)]] for index, node in enumerate(route))

def _assert_complete_and_exact(result, matrix: list[list[float]]) -> None:
    assert result.tour is not None
    assert sorted(result.tour) == list(range(1, len(matrix) + 1))
    assert result.tour_cost == pytest.approx(_closed_cost(result.tour, matrix))
    assert result.objective_cost == pytest.approx(_closed_cost(result.tour, matrix))
    assert result.evaluations == result.objective_evaluations
~~~

  Use a directed repair fixture whose boundary insertion is cheaper only after subtracting the replaced closing arc. Assert all three repair operators choose the mathematically exact insertion position at both duplicated boundary positions. Add direct target tests for an accounted fixed-budget run at budget `1`, a larger fixed budget, and an unbounded native counter. The budget-one test must require `evaluations == 1`, `iterations == 0`, `budget_exhausted is True`, and `termination_reason == "evaluation_budget_exhausted"`.

- [ ] **Step 2: Add the four currently-red registry evidence tests.** Each test invokes `AlgorithmRegistry.get_executor("ALNS-TSP")` with a manifest-derived paired seed and ignores the caller seed. Fixed tests use `fair_comparison` protocol v2 with budget `1` and a larger budget; native tests use `native_comparison` with no evaluation budget. Require identity, family, pure/no-polish metadata, exact backend string, independent directed cost, evaluation equality, exact permitted termination set, and replay equality for tour/cost/evaluations/iterations/reason/backend. Use these exact parameter blocks:

~~~python
ALNS_PARAMS = {
    "max_iterations": 8,
    "max_no_improvement": 3,
    "remove_ratio": 0.34,
    "min_remove": 2,
    "segment_length": 2,
    "weight_update_factor": 0.8,
    "use_sa": True,
    "sa_start_temp": 5.0,
    "sa_cooling_rate": 0.9,
}
~~~

  Add negative tests rejecting caller `seed`, legacy `iterations`, `max_no_improve`, `noise_scale`, unknown keys, `remove_ratio=0`, `weight_update_factor=1.1`, and `use_sa=True, sa_start_temp=0`.

- [ ] **Step 3: Run the red focused suite.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_alns_c3_evidence.py -q -p no:cacheprovider --tb=short
~~~

Expected: failures proving the current repair boundary delta is wrong and that the present basic SOTA ALNS executor does not accept fair/native accounting contracts or return their required metadata. Keep all target assertions; do not weaken them to make the baseline pass.

---

### Task 2: Correct cyclic insertion and add the canonical accounted ALNS core path

**Files:**
- Modify: `uniride_core/algorithms/sota_tsp/repair_ops.py:12-109`
- Modify: `uniride_core/algorithms/sota_tsp/alns_tsp.py:14-220`
- Modify: `academic_benchmark/tests/test_alns_c3_evidence.py`

**Interfaces:**
- Consumes a complete matrix, `ALNSConfig`, and one caller-owned `ObjectiveEvaluationBudget`.
- Produces `AccountedALNSResult(route, cost, iterations, evaluations, budget_exhausted, termination_reason)` from `ALNS_TSP.solve_accounted_with_matrix(matrix, budget)`.
- Preserves `ALNS_TSP.solve_with_matrix(matrix) -> TSPResult` for the non-protocol registry path.

- [ ] **Step 1: Keep the direct core assertions red.** Add tests importing `AccountedALNSResult` and calling:

~~~python
solver = ALNS_TSP(ALNSConfig(iterations=8, max_no_improve=3, seed=41))
result = solver.solve_accounted_with_matrix(ATSP_MATRIX, ObjectiveEvaluationBudget(1))
assert isinstance(result, AccountedALNSResult)
assert result.evaluations == 1
assert result.iterations == 0
assert result.termination_reason == "evaluation_budget_exhausted"
~~~

  Add a no-global-best-improvement fixture with `use_sa=True` and a small `max_no_improve`; assert accepted non-improving candidates still advance the stagnation counter and yield `stagnation_limit`, rather than `max_iterations`.

- [ ] **Step 2: Implement exact repair scoring.** In every insertion-score loop in `GreedyInsertion.repair` and both the regret-selection and final-placement loops in `RegretKInsertion.repair`, calculate the one directed-cycle delta without the interior-only guard:

~~~python
cost = dm[prev_node][node] + dm[node][next_node] - dm[prev_node][next_node]
~~~

  Retain the existing empty-result branch. Do not deduplicate the two boundary positions: they represent the same cycle edge and must receive the same exact score.

- [ ] **Step 3: Implement the minimal accounted ALNS result and path.** Add the frozen result type and public method in `alns_tsp.py`:

~~~python
@dataclass(frozen=True)
class AccountedALNSResult:
    route: list[int]
    cost: float
    iterations: int
    evaluations: int
    budget_exhausted: bool
    termination_reason: str

def solve_accounted_with_matrix(
    self,
    matrix: list[list[float]],
    budget: ObjectiveEvaluationBudget,
) -> AccountedALNSResult:
    self.set_dist_matrix(matrix)
    return self._solve_accounted(budget)
~~~

  Import `ObjectiveEvaluationBudget` from `uniride_core.algorithms.objective_budget`; never import `academic_benchmark`. In `_solve_accounted`, reset the RNG and adaptive weights exactly as the normal search does, evaluate the initial nearest-neighbor route only with `budget.evaluate`, and check `budget.can_spend()` before generating/evaluating each complete repaired candidate. Increment `iterations` only after a candidate full-tour objective is completed. Emit `evaluation_budget_exhausted` before a next candidate when one cannot start, `stagnation_limit` after the just-completed iteration reaches the counter ceiling, and `max_iterations` only after the configured ceiling is actually completed. Set `evaluations=budget.used-start_evaluations`.

  Define global-best improvement precisely: reset `no_improve` only when the candidate is a strict new `best_cost`; otherwise increment it whether the candidate is accepted by simulated annealing or rejected. Continue to use SA only for choosing `current`; update operator scores and temperature once per completed candidate. Make `_solve()` call the same `_solve_accounted(ObjectiveEvaluationBudget(None))` path and convert the result to the existing `TSPResult`, preserving its historical name, tour, tour length, time, iterations, and configured seed.

- [ ] **Step 4: Run direct repair and core tests green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_alns_c3_evidence.py -k "repair or accounted or budget or stagnation" -q -p no:cacheprovider --tb=short
~~~

Expected: directed and symmetric boundary deltas, budget-one atomic behavior, exact consumed counts, strict-global-best stagnation, and deterministic direct-core replay pass. The ordinary non-protocol ALNS tests still remain green.

---

### Task 3: Define strict ALNS parameters, wire validators, and add the canonical registry adapter

**Files:**
- Modify: `academic_benchmark/fairness.py:59-264`
- Modify: `academic_benchmark/native_protocol.py:14-184`
- Modify: `academic_benchmark/core/registry_setup.py:459-561`
- Modify: `academic_benchmark/tests/test_alns_c3_evidence.py`

**Interfaces:**
- Consumes `AccountedALNSResult`, the paired-seed fair/native manifests, and the preflight-selected canonical `ALNS-TSP` executor.
- Produces `ALNS_REQUIRED_PARAMS`, `ALNS_OPTIONAL_PARAMS`, `validate_scientific_alns_params(params: Mapping[str, Any]) -> dict[str, Any]`, and `FairRunResult` records from `_run_canonical_alns(problem, params, run_idx, manifest, *, native)`.

- [ ] **Step 1: Add strict-parameter, validator, and dispatch tests before wiring.** Add direct `validate_scientific_alns_params(ALNS_PARAMS)` success coverage, plus failures for missing required keys, caller `seed`, legacy `iterations`, legacy `max_no_improve`, `noise_scale`, unknown keys, boolean integer fields, `remove_ratio=0`, `weight_update_factor=1.1`, and `use_sa=True, sa_start_temp=0`. Test that both manifests reject wrong family, non-pure variant, non-null `neighborhood_window`, an acceptance policy outside `simulated_annealing`/`improving_only`, a native budget field, a fixed `no_improving_move` reason, and a native `evaluation_budget_exhausted` reason. Add a routing-shaped problem test requiring fair/native ALNS to raise before solver construction and a fractional ATSP test requiring precise unrounded directed costs.

- [ ] **Step 2: Run the protocol tests red.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_alns_c3_evidence.py -k "fixed or native or validator or routing" -q -p no:cacheprovider --tb=short
~~~

Expected: failures because neither manifest recognizes `ALNS-TSP`, and the current SOTA executor returns only a basic `RunResult`.

- [ ] **Step 3: Implement the shared strict scientific parameter validator before adapter use.** In `fairness.py`, define:

~~~python
ALNS_REQUIRED_PARAMS = frozenset({
    "max_iterations", "max_no_improvement", "remove_ratio", "min_remove",
    "segment_length", "weight_update_factor", "use_sa",
})
ALNS_OPTIONAL_PARAMS = frozenset({"sa_start_temp", "sa_cooling_rate"})

def validate_scientific_alns_params(params: Mapping[str, Any]) -> dict[str, Any]:
    missing = ALNS_REQUIRED_PARAMS - params.keys()
    unknown = params.keys() - ALNS_REQUIRED_PARAMS - ALNS_OPTIONAL_PARAMS
    if missing or unknown:
        raise ValueError(f"ALNS parameter schema mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    return dict(params)
~~~

  Complete the function with §7.1 validation: non-boolean integers >= 1 for `max_iterations`, `max_no_improvement`, `min_remove`, and `segment_length`; finite `0 < remove_ratio <= 1`; finite `0 <= weight_update_factor <= 1`; boolean `use_sa`; finite non-negative optional `sa_start_temp`; finite `0 < sa_cooling_rate <= 1`; and a strictly positive start temperature when SA is enabled. Raise `ValueError` naming the invalid field. Task 3 tests call this function directly before `_run_canonical_alns` is implemented.
- [ ] **Step 4: Implement validator admission without relaxing other families.** Add `"ALNS-TSP": "ALNS"` to each manifest family map. Add the ALNS-specific validation branch in both validators: `variant == "pure"`; null `neighborhood_window`; accepted policies are `simulated_annealing` and `improving_only`; fixed reasons are exactly `evaluation_budget_exhausted`, `max_iterations`, or `stagnation_limit`; native reasons are exactly `max_iterations` or `stagnation_limit`. Keep existing GWO/HHO/2-opt/3-opt/Or-opt validations unchanged.

- [ ] **Step 5: Implement the registry adapter and dispatch.** In `registry_setup.py`, add `_run_canonical_alns` beside `_run_canonical_or_opt`. It must:

~~~python
scientific = validate_scientific_alns_params(alns_params)
seed = manifest.paired_seed(problem.name, run_idx)
config = ALNSConfig(
    iterations=scientific["max_iterations"],
    max_no_improve=scientific["max_no_improvement"],
    remove_ratio=scientific["remove_ratio"],
    min_remove=scientific["min_remove"],
    segment_length=scientific["segment_length"],
    weight_update_factor=scientific["weight_update_factor"],
    use_sa=scientific["use_sa"],
    sa_start_temp=scientific.get("sa_start_temp", ALNSConfig.sa_start_temp),
    sa_cooling_rate=scientific.get("sa_cooling_rate", ALNSConfig.sa_cooling_rate),
    seed=seed,
)
accounting = ObjectiveEvaluationBudget(None if native else manifest.evaluation_budget)
search = ALNS_TSP(config).solve_accounted_with_matrix(matrix, accounting)
~~~

  Derive `matrix, matrix_kind` with `_problem_matrix`, reject `_is_routing_problem(problem)`, convert `search.route` to one-indexed, preserve unrounded `float(search.cost)` in both cost fields, and set `evaluations == objective_evaluations == accounting.used`. For fixed mode set the manifest budget and `budget_terminated=(search.termination_reason == "evaluation_budget_exhausted")`; native mode sets `evaluation_budget=None`, `budget_terminated=False`, and raises if the unbounded counter reports budget exhaustion. Populate all global metadata exactly as required, validate using the active manifest, and return the result.

  In `_make_sota_executor`, parse `fair_comparison` and `native_comparison` before its legacy SOTA execution. Reject both manifests together; dispatch only `algo == "ALNS-TSP"` plus one active manifest to `_run_canonical_alns`; leave all no-manifest SOTA behavior, including `SOTA-ALNS-TSP`, unchanged.

- [ ] **Step 6: Run the adapter tests green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_alns_c3_evidence.py academic_benchmark/tests/test_canonical_registry_identity.py -q -p no:cacheprovider --tb=short
~~~

Expected: fixed and native TSP/ATSP records validate with exact metadata, routing is rejected only in protocol mode, and the historical non-protocol SOTA registry identity remains compatible.

---

### Task 4: Reuse strict validation in fair/native pilot admission and prove record/replay integration

**Files:**
- Modify: `academic_benchmark/fair_pilot.py:39-218`
- Modify: `academic_benchmark/native_protocol.py:12-42`
- Modify: `academic_benchmark/native_pilot.py:54-237`
- Modify: `academic_benchmark/tests/test_fair_pilot_cli.py`
- Modify: `academic_benchmark/tests/test_native_termination_protocol.py`
- Modify: `academic_benchmark/tests/test_alns_c3_evidence.py`

**Interfaces:**
- Consumes the Task 3 `ALNS_REQUIRED_PARAMS`, `ALNS_OPTIONAL_PARAMS`, and `validate_scientific_alns_params` in both pilot loaders; it does not redefine or relax that contract.
- Produces pilot configs whose exact algorithm set includes `ALNS-TSP` and whose persisted/replay records include canonical ALNS provenance already emitted by `_result_record`/`_native_result_record`.

- [ ] **Step 1: Write exact-set admission and record/replay red tests.** Add tests that a complete fair pilot config and native pilot config containing their respective current exact approved set augmented with `ALNS-TSP` load successfully. Update existing fixture factories so every expected exact algorithm set includes an ALNS block with `ALNS_PARAMS`. Add loader-delegation tests confirming forbidden/invalid ALNS blocks receive the shared Task 3 validator error without duplicating validation. Add record/replay tests requiring `ALNS-TSP` rows to retain canonical identity, selected backend profile/evidence IDs, complete tours, exact evaluations, and equal replay route/cost/evaluations/iterations/reason/backend.

- [ ] **Step 2: Run the pilot schema tests red.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_fair_pilot_cli.py academic_benchmark/tests/test_native_termination_protocol.py -k "config or schema or replay or record" -q -p no:cacheprovider --tb=short
~~~

Expected: strict validation already passes from Task 3, but pilot config tests fail because their exact admission sets and native allowed/required maps still exclude `ALNS-TSP`.

- [ ] **Step 3: Admit ALNS to both exact pilot schemas by reusing Task 3 validation.** Add `ALNS-TSP` to `fair_pilot.APPROVED_ALGORITHMS` and `native_protocol.APPROVED_NATIVE_ALGORITHMS`; include its family in the native map. In fair pilot v2 validation, call `validate_scientific_alns_params` for ALNS and forbid local-search window fields. In native pilot, derive ALNS required/allowed key entries from Task 3's constant sets, call the same validator after exact-key admission, and retain strict checks for every existing algorithm. Do not allow CLI aliases in either stored pilot config and do not duplicate §7.1 validation logic.
- [ ] **Step 4: Run pilot tests green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_fair_pilot_cli.py academic_benchmark/tests/test_native_termination_protocol.py academic_benchmark/tests/test_alns_c3_evidence.py -q -p no:cacheprovider --tb=short
~~~

Expected: exact-set pilot admission and shared invalid-parameter delegation pass, fair/native pilot records carry canonical ALNS fields, replay is deterministic, and no output is created in the repository.

---

### Task 5: Publish four claims and update preflight, gateway, and manifest boundaries

**Files:**
- Modify: `uniride_core/algorithms/capabilities.py:199-281`
- Modify: `academic_benchmark/tests/test_algorithm_capability_catalog.py:185-323`
- Modify: `academic_benchmark/tests/test_algorithm_capability_evidence.py:117-315`
- Modify: `academic_benchmark/tests/test_algorithm_preflight.py:395-410`
- Modify: `academic_benchmark/tests/test_algorithm_execution_gateway.py:203-267`
- Modify: `academic_benchmark/tests/test_manifest_contracts.py:178-201`
- Modify: `academic_benchmark/tests/test_algorithm_resolution.py`
- Modify: `academic_benchmark/tests/test_alns_c3_evidence.py`

**Interfaces:**
- Produces exactly four `CapabilityClaim` entries for `ALNS-TSP`: TSP/ATSP × fixed/native, `CompositionKind.PURE`, `ExecutionBackendProfile(BackendKind.PYTHON, BackendKind.NONE)`, false production readiness, and the four focused pytest node IDs from Task 1.
- Consumes the immutable resolver/preflight/gateway contracts without adding a production registry dependency or relaxing backend parsing.

- [ ] **Step 1: Add evidence and boundary tests red.** In the focused ALNS module, ensure each of the four named tests independently exercises its exact problem/protocol pair. In capability-catalog tests assert `ALNS-TSP` is initially expected to become `VERIFIED` with exactly four claims and that both hybrid ALNS identities remain planned/no-claim. Update capability-evidence test helpers to verify every cited ALNS node exists and passes. Replace the old candidate-only ALNS expectation in manifest/preflight tests with a successful canonical `python_only` ALNS decision; retain GA/PSO candidate and ALNS-hybrid planned rejection coverage. Add gateway tests that reject malformed backend strings or result/backend-profile mismatches for an otherwise valid ALNS record.

- [ ] **Step 2: Run capability and boundary tests red.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_algorithm_capability_catalog.py academic_benchmark/tests/test_algorithm_capability_evidence.py academic_benchmark/tests/test_algorithm_preflight.py academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_algorithm_resolution.py -q -p no:cacheprovider --tb=short
~~~

Expected: catalog/preflight failures because the live ALNS capability remains `CANDIDATE`; no production registry code is loaded or changed.

- [ ] **Step 3: Replace only the ALNS capability row.** Add a dedicated `_alns_claims()` builder, then replace the `ALNS-TSP` row in the immutable catalog with `LifecycleStatus.VERIFIED` and exactly these claims:

~~~python
CapabilityClaim(
    problem=ProblemContract.ATSP,
    protocol=ExecutionProtocol.FIXED_BUDGET,
    backend_profile=ExecutionBackendProfile(BackendKind.PYTHON),
    composition=CompositionKind.PURE,
    directed_cost_preserved=True,
    exact_objective_accounting=True,
    fixed_seed_deterministic=True,
    truthful_result_reporting=True,
    evidence_ids=(
        "academic_benchmark/tests/test_alns_c3_evidence.py::test_alns_fixed_atsp_evidence",
    ),
)
~~~

  Create analogous TSP/ATSP native claims and the fixed TSP claim, with the appropriate four exact node IDs. For TSP, `directed_cost_preserved=False`; native `exact_objective_accounting` remains true because actual complete-tour evaluations are reported. Do not change `_INITIAL_CAPABILITIES` identities other than ALNS and do not attach any claim to either planned hybrid.

- [ ] **Step 4: Confirm resolver, preflight, and gateway behavior.** Keep `SOTA-ALNS-TSP -> ALNS-TSP` as a deprecated CLI-only alias; assert manifests reject the alias and stored result identity stays canonical. Confirm preflight selects only the exact Python/no-polish claim for each matrix-declared contract, and the gateway independently verifies the 1-indexed complete tour, directed closed cost, exact budget/no-budget fields, and stage-aware backend string. Do not modify `execution_gateway._parse_backend_profile`.

- [ ] **Step 5: Run publication and boundary tests green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_alns_c3_evidence.py academic_benchmark/tests/test_algorithm_capability_catalog.py academic_benchmark/tests/test_algorithm_capability_evidence.py academic_benchmark/tests/test_algorithm_preflight.py academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_algorithm_resolution.py -q -p no:cacheprovider --tb=short
~~~

Expected: exactly four selectable ALNS claims pass their referenced evidence nodes; aliases remain CLI-only; malformed/mismatched postflight records are rejected; candidate/planned boundaries and production isolation remain intact.

---

### Task 6: Run regressions, verify production isolation, and close the artifact/status gate

**Files:**
- Modify only when a test exposes a C3 contract gap: `academic_benchmark/tests/test_alns_c3_evidence.py` or the exact existing test owner named in Tasks 1-5.
- Inspect only: `academic_benchmark/tests/test_production_registry_snapshot.py`, `academic_benchmark/tests/test_smart_benchmark_preflight.py`, `academic_benchmark/tests/test_atsp_integration.py`, `academic_benchmark/tests/test_solver_backend_reporting.py`.

**Interfaces:**
- Consumes the passing C3 focused suite and existing production snapshot/import-boundary tests.
- Produces a reviewable working tree with no benchmark outputs and evidence only from passing deterministic tests.

- [ ] **Step 1: Run the focused C3 and surrounding protocol gate.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_alns_c3_evidence.py academic_benchmark/tests/test_canonical_registry_identity.py academic_benchmark/tests/test_atsp_integration.py academic_benchmark/tests/test_fair_comparison_protocol.py academic_benchmark/tests/test_fair_comparison_scientific_integrity.py academic_benchmark/tests/test_native_termination_protocol.py academic_benchmark/tests/test_fair_pilot_cli.py academic_benchmark/tests/test_solver_backend_reporting.py -q -p no:cacheprovider --tb=short
~~~

Expected: all focused C3 and contract tests pass with no ALNS Numba claim, no silent polish, no generated benchmark artifact, and exact fixed/native regime separation.

- [ ] **Step 2: Run capability, public-path, and production-isolation regressions.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_algorithm_capability_catalog.py academic_benchmark/tests/test_algorithm_capability_evidence.py academic_benchmark/tests/test_algorithm_resolution.py academic_benchmark/tests/test_algorithm_preflight.py academic_benchmark/tests/test_algorithm_preflight_boundaries.py academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_smart_benchmark_preflight.py academic_benchmark/tests/test_production_registry_snapshot.py -q -p no:cacheprovider --tb=short
~~~

Expected: all four ALNS tuples are authorized only through their exact evidence; `SOTA-ALNS-TSP` remains a deprecated CLI-only alias; both production strategy maps retain the protected exact key set; importing production strategies does not load `uniride_core.algorithms.capabilities`.

- [ ] **Step 3: Run the full academic suite and workspace hygiene checks.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short
git diff --check
git status --short --branch
git diff --name-only
~~~

Expected: full academic suite passes or reports only pre-existing, explicitly recorded environment blockers; `git diff --check` is silent; changed files are limited to the C3 source/test owners in this plan; no CSV, database, report, cache, or benchmark evidence artifact appears. Do not run TSPLIB/CVRPLIB experiments.

- [ ] **Step 4: Self-review before requesting integration.** Verify by source and test output that: every objective evaluation uses the injected shared budget; the initial tour is the only budget-one evaluation; `no_improve` measures strict global-best stagnation; ATSP costs and repair deltas preserve direction; all public scientific records are canonical/one-indexed and postflight-valid; paired seeds override caller seeds; fixed and native rows cannot be pooled; ALNS hybrids remain planned; and production keys/import boundaries are unchanged. Record exact command results, warnings, skips, and environment blockers; do not claim a benchmark result or algorithm superiority.

---

## Self-Review Checklist

- [ ] Each requirement of `docs/superpowers/specs/2026-08-03-c3-alns-evidence-design.md` maps to Tasks 1-6: boundary delta, accounting, atomic budget one, termination, seed replay, strict backend syntax, aliases, pilot admission, four claims, postflight, production isolation, and artifact exclusion.
- [ ] Interface names are consistent: `AccountedALNSResult`, `solve_accounted_with_matrix`, `_run_canonical_alns`, and `validate_scientific_alns_params` are defined before their consumers use them.
- [ ] The ordinary non-protocol `ALNS-TSP` and historical `SOTA-ALNS-TSP` execution paths retain existing public parameters/identity behavior; strict scientific manifests use only §7.1 keys.
- [ ] Every capability claim cites one concrete passing node in `academic_benchmark/tests/test_alns_c3_evidence.py`; TSP/ATSP and fixed/native claims are independently represented.
- [ ] No task silently changes `execution_gateway` parsing, adds a Numba label, adds polish, changes production strategy exposure, promotes GA/PSO/hybrids, or writes benchmark artifacts.
- [ ] All PowerShell commands use `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe` and disable pytest cache creation.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-03-c3-alns-evidence.md`.

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, and use `superpowers:subagent-driven-development`.
2. **Inline Execution** — execute the tasks in this session using `superpowers:executing-plans`, with checkpoints after each task.
