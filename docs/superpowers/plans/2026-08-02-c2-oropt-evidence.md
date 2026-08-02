# C2 Or-opt Evidence-Gated Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Make \`Core-OrOpt-TSP\` selectable only after deterministic, exactly-accounted TSP/ATSP evidence proves its canonical budgeted and native behavior, while preserving all other candidate/planned algorithms and production registry exposure.

**Architecture:** Add one canonical matrix Or-opt controller beside the existing objective-budgeted 2-opt primitive. Route the academic fair and native protocols through that controller, expose truthful Python-only backend/accounting fields, and publish two-problem claims only after focused fixtures pass. Keep the existing \`uniride_core.algorithms.local_search_numba.OrOptLocalSearch\` and academic registry ID/alias intact; no Numba claim, solver relocation, archival, or production strategy change is part of C2.

**Tech Stack:** Python 3.14, pytest, dataclasses, typed matrix algorithms, \`ObjectiveEvaluationBudget\`, \`FairComparisonManifest\`, \`NativeComparisonManifest\`, immutable capability catalog, existing \`.venv-jit\` test interpreter.

## Global Constraints

- Work only in \`C:\\tmp\\UniRide-package-c2\` on branch \`codex/package-c2-oropt-evidence-20260802\`.
- Do not modify the original checkout, \`C:\\tmp\\UniRide-wip-promote-20260801\`, Package A, Bildiri archival state, frontend, FastAPI API, dependencies, databases, generated reports, or unrelated worktrees.
- Do not change production strategy registry exposure or fairness-budget policy; preserve \`Core-OrOpt-TSP\` and \`Numba-Or-opt\` identifiers.
- Do not run large TSPLIB/CVRPLIB experiments and do not claim Numba execution; the promoted Or-opt capability is Python objective/backend evidence only.
- Use fixed nonzero paired seeds, in-memory symmetric and directed matrices, complete 1-indexed returned tours, independent closed-cycle cost checks, exact evaluation counts, termination reasons, and truthful backend labels.
- Keep the working tree reviewable; no commit or push is performed unless separately authorized by the user.

---

### Task 1: Freeze the intended Or-opt contract with failing fixtures

**Files:**
- Create: \`academic_benchmark/tests/test_or_opt_c2_evidence.py\`
- Inspect only: \`academic_benchmark/tests/test_algorithm_capability_evidence.py\`, \`academic_benchmark/fairness.py\`, \`academic_benchmark/core/registry_setup.py\`

**Interfaces:**
- Consumes the existing \`AlgorithmRegistry.get_executor\`, \`FairComparisonManifest\`, \`NativeComparisonManifest\`, and \`ProblemInstance\`-compatible in-memory problems.
- Produces a small deterministic test contract for \`Core-OrOpt-TSP\` that later tasks must satisfy without changing public IDs.

- [ ] **Step 1: Write the failing test.** Add a test module with two 5-node fixtures: one symmetric \`problem_type="tsp"\` matrix and one genuinely asymmetric \`problem_type="atsp"\` matrix. Add helpers that convert the returned 1-indexed tour to zero-based, recompute \`sum(matrix[u][v])\` over the closed cycle, and assert sorted tour nodes equal \`1..dimension\`. Add these tests before implementation:

~~~python
def test_or_opt_fixed_protocol_is_currently_not_silently_accepted():
    params = {
        "max_iterations": 3,
        "first_improvement": False,
        "window": 3,
        "fair_comparison": {
            "evaluation_budget": 12,
            "base_seed": 239,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }
    with pytest.raises(ValueError, match="exact objective accounting"):
        AlgorithmRegistry.get_executor("Core-OrOpt-TSP")(
            SYMMETRIC_TSP, params, seed=987654, run_idx=0
        )
~~~

  Also add the target tests (initially expected to fail at the same guard) for fixed TSP/ATSP and native TSP/ATSP. Each target test must assert: fixed nonzero paired seed, \`algorithm == algorithm_id == "Core-OrOpt-TSP"\`, \`algorithm_family == "Or-opt"\`, \`variant == "pure"\`, complete route, independent cost equality, \`objective_evaluations == evaluations\`, \`0 < evaluations <= budget\`, \`budget_terminated is True\` only when the atomic budget is exhausted, \`execution_backend == "objective=python;polish=none"\`, \`termination_reason\` in the manifest vocabulary, and replay equality for route/cost/evaluations/termination/backend when the caller seed changes but \`(problem, run)\` is unchanged. Native tests must require \`evaluation_budget is None\`, \`budget_terminated is False\`, and no budget-exhaustion termination.

- [ ] **Step 2: Run the focused fixture to verify the red state.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py -q -p no:cacheprovider --tb=short
~~~

Expected: the fixed/native target tests fail because registry fair/native dispatch currently accepts only \`LocalSearchType.TWO_OPT\` and \`LocalSearchType.THREE_OPT\`; the temporary guard test passes. Do not weaken the target assertions to make the suite green.

---

### Task 2: Add the canonical atomic-budget Or-opt controller

**Files:**
- Modify: \`uniride_core/algorithms/objective_budget.py:1-128\`
- Modify: \`academic_benchmark/tests/test_or_opt_c2_evidence.py\`

**Interfaces:**
- Consumes \`Sequence[int]\`, a square numeric matrix, \`ObjectiveEvaluationBudget\`, \`max_iterations\`, \`first_improvement\`, and a segment bound of \`1..3\`.
- Produces \`BudgetedSearchResult(route, cost, iterations, evaluations, budget_exhausted, mode, termination_reason)\` with one budget unit per complete candidate-tour objective evaluation.

- [ ] **Step 1: Add direct primitive tests before implementation.** In the new test module, call \`improve_or_opt_budgeted\` directly on both matrices with a fixed initial permutation and budgets \`1\`, \`7\`, and an unbounded \`ObjectiveEvaluationBudget(None)\`. Assert the route remains a permutation, the independent directed/symmetric closed cost equals \`result.cost\`, \`result.evaluations == budget.used - initial_used\`, \`result.evaluations <= limit\` when bounded, no candidate is evaluated after exhaustion, and repeated calls with identical inputs produce identical records. Assert \`result.mode\` is \`symmetric_tsp\` for the symmetric matrix and \`directed_atsp\` for the asymmetric matrix.

- [ ] **Step 2: Run direct tests to verify they fail.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py -k budgeted -q -p no:cacheprovider --tb=short
~~~

Expected: import or attribute failure because \`improve_or_opt_budgeted\` does not yet exist.

- [ ] **Step 3: Implement the minimal canonical controller.** Add \`improve_or_opt_budgeted\` after \`improve_two_opt_budgeted\` and export it in \`__all__\`. The implementation must:

~~~python
def improve_or_opt_budgeted(
    route: Sequence[int],
    matrix: Sequence[Sequence[float]],
    budget: ObjectiveEvaluationBudget,
    *,
    max_iterations: int,
    first_improvement: bool = False,
    max_segment_length: int = 3,
    initial_cost: Optional[float] = None,
) -> BudgetedSearchResult:
    """Budgeted first/best-improvement Or-opt for symmetric TSP and directed ATSP."""
~~~

  Validate \`max_iterations >= 0\` and \`1 <= max_segment_length <= 3\`. Evaluate the initial route through \`budget.evaluate\` unless \`initial_cost\` is supplied. For each iteration enumerate every contiguous segment length \`1..max_segment_length\`, every valid segment start, and every insertion position that is not inside the removed segment; construct a new route without mutating the input, evaluate it only after \`budget.can_spend()\`, and accept a strict improvement. Stop the scan immediately for first-improvement. On exhaustion, set \`budget_exhausted=True\` and \`termination_reason="evaluation_budget_exhausted"\`; otherwise use \`no_improving_move\` when no move improves and \`max_iterations\` when the cap is reached after an improvement. Set \`mode="directed_atsp"\` when \`is_symmetric_matrix(matrix)\` is false, otherwise \`mode="symmetric_tsp"\`. Return the exact \`budget.used - start_evaluations\` count. Reuse \`closed_tour_cost\` only through \`ObjectiveEvaluationBudget.evaluate\`; do not add a second objective or a Numba label.

- [ ] **Step 4: Run direct tests to verify green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py -k budgeted -q -p no:cacheprovider --tb=short
~~~

Expected: all direct budget, route, cost, symmetric/directed, and deterministic tests pass with no skips.

---

### Task 3: Wire Or-opt into fair and native academic execution

**Files:**
- Modify: \`academic_benchmark/fairness.py:82-355\`
- Modify: \`academic_benchmark/core/registry_setup.py:179-340\`
- Modify: \`academic_benchmark/tests/test_or_opt_c2_evidence.py\`

**Interfaces:**
- Consumes \`improve_or_opt_budgeted\` and the existing paired-seed manifests.
- Produces \`FairRunResult\`/\`NativeRunResult\` records with \`algorithm_family="Or-opt"\`, \`neighborhood_window=3\`, \`acceptance_policy\` derived from \`first_improvement\`, \`variant="pure"\`, \`execution_backend="objective=python;polish=none"\`, and exact termination/accounting fields.

- [ ] **Step 1: Write validator and dispatch assertions.** Extend the new tests to call \`FairComparisonManifest.validate_result\` with a valid Or-opt record and invalid records (\`algorithm_family="2-opt"\`, boolean \`neighborhood_window\`, window \`0\`, unsupported termination reason). Add a native test that proves no finite measurement budget is passed to the controller and that a native run rejects unexpected budget exhaustion.

- [ ] **Step 2: Run the protocol tests to verify the expected red state.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py -k "fixed or native or validator" -q -p no:cacheprovider --tb=short
~~~

Expected: failures at the current local-search type guards and the missing \`"Or-opt"\` manifest family.

- [ ] **Step 3: Implement the minimal protocol wiring.** Import and expose \`improve_or_opt_budgeted\` from \`academic_benchmark.fairness\`; add \`"Core-OrOpt-TSP": "Or-opt"\` to \`FairComparisonManifest.ALGORITHM_FAMILIES\`; add an \`elif family == "Or-opt"\` validator branch requiring \`acceptance_policy\` to be \`best_improvement\` or \`first_improvement\` and an integer \`neighborhood_window\` in \`1..3\`. In \`_run_fair_local_search\` and \`_run_native_local_search\`, allow \`LocalSearchType.OR_OPT\`, read \`window\` or \`max_segment_length\` with default \`3\`, call the new controller with the existing manifest budget or an unbounded \`ObjectiveEvaluationBudget(None)\`, set \`family="Or-opt"\`, and retain Python-only backend and no polish. Preserve the existing 2-opt/3-opt branches byte-for-byte in behavior. Native mode must continue to reject any \`evaluation_budget\` exhaustion.

- [ ] **Step 4: Run protocol tests to verify green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py -k "fixed or native or validator" -q -p no:cacheprovider --tb=short
~~~

Expected: all Or-opt fixed/native protocol tests pass, including independent costs, exact evaluation counts, termination, and replay determinism.

---

### Task 4: Publish evidence-gated Or-opt capability and preserve candidate boundaries

**Files:**
- Modify: \`uniride_core/algorithms/capabilities.py:201-224\`
- Modify: \`academic_benchmark/tests/test_algorithm_capability_evidence.py:100-390\`
- Modify: \`academic_benchmark/tests/test_algorithm_capability_catalog.py\`
- Modify: \`academic_benchmark/tests/test_algorithm_preflight.py\`
- Modify: \`academic_benchmark/tests/test_algorithm_preflight_boundaries.py\`
- Modify: \`academic_benchmark/tests/test_algorithm_execution_gateway.py\`
- Modify: \`academic_benchmark/tests/test_or_opt_c2_evidence.py\`

**Interfaces:**
- Consumes the passing Or-opt evidence node(s) from \`academic_benchmark/tests/test_algorithm_capability_evidence.py\` or the dedicated fixture module.
- Produces two verified \`Core-OrOpt-TSP\` claims (TSP and ATSP) for fixed-budget and native protocols, with Python/no-polish backend, local-search composition, directed-cost preservation, exact accounting, deterministic seeds, and truthful result reporting.

- [ ] **Step 1: Add evidence functions and run the capability tests red.** Add \`_fixed_params\` and \`_native_params\` branches for \`Core-OrOpt-TSP\` with \`window=3\`; add fixed and native evidence functions that invoke the executor on both existing in-memory matrices and assert the complete contract; add catalog assertions that initially fail because the capability is still \`CANDIDATE\`.

- [ ] **Step 2: Promote only after evidence exists.** Change the immutable catalog row to \`LifecycleStatus.VERIFIED\` and attach \`_fixed_local_search_claims\` plus \`_native_local_search_claims\` using exact pytest node IDs. Do not add a Numba claim. The fixed claim backend must be \`ExecutionBackendProfile(objective=BackendKind.PYTHON, polish=BackendKind.NONE)\`; native must use the same Python/no-polish profile. Update lifecycle tests so Or-opt is in the verified set, while \`Core-GA-TSP\`, \`Core-PSO-TSP\`, and \`ALNS-TSP\` remain candidate and all 3-opt/ALNS planned compositions remain non-selectable.

- [ ] **Step 3: Update preflight/gateway boundary tests.** Replace only the old expectation that Or-opt raises \`CandidateAlgorithmError\` with a successful Python-only preflight/execution path using a valid Or-opt result. Retain candidate rejection coverage for GA/PSO/ALNS, planned rejection for memetic 3-opt/ALNS, wrong-problem rejection, missing backend, missing executor, alias/deprecation behavior, and postflight backend/accounting validation.

- [ ] **Step 4: Run the catalog/evidence boundary suite to verify green.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py academic_benchmark/tests/test_algorithm_capability_evidence.py academic_benchmark/tests/test_algorithm_capability_catalog.py academic_benchmark/tests/test_algorithm_resolution.py academic_benchmark/tests/test_algorithm_preflight.py academic_benchmark/tests/test_algorithm_preflight_boundaries.py academic_benchmark/tests/test_algorithm_execution_gateway.py -q -p no:cacheprovider --tb=short
~~~

Expected: zero failures; any Numba-dependent GWO/HHO evidence remains governed by its existing environment probe and is not reclassified by C2.

---

### Task 5: Protect registry exposure and execute the C2 regression gate

**Files:**
- Modify: \`academic_benchmark/tests/test_core_tsp_registry.py\`
- Modify: \`academic_benchmark/tests/test_or_opt_c2_evidence.py\`
- No production registry file is changed except the already-scoped fair/native dispatch in Task 3.

**Interfaces:**
- Consumes the existing \`AlgorithmRegistry\` registration for \`Core-OrOpt-TSP\` and its deprecated alias \`Numba-Or-opt\`.
- Produces a registry smoke test proving matrix-native TSP execution returns a complete 1-indexed tour and exact objective cost without changing the set of production strategy IDs.

- [ ] **Step 1: Add a small registry smoke test.** Parameterize the existing tiny matrix test with \`Core-OrOpt-TSP\` and parameters \`max_iterations=3\`, \`first_improvement=False\`, \`max_segment_length=3\` (or the existing legacy executor parameter name), then assert algorithm identity, TSP problem type, matrix kind, objective/tour-cost equality, complete tour, and independent closed cost. Do not add Or-opt to production \`STRATEGY_REGISTRY\` or to any CVRP list.

- [ ] **Step 2: Run the focused C2 gate.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_or_opt_c2_evidence.py academic_benchmark/tests/test_algorithm_capability_catalog.py academic_benchmark/tests/test_algorithm_capability_evidence.py academic_benchmark/tests/test_algorithm_resolution.py academic_benchmark/tests/test_algorithm_preflight.py academic_benchmark/tests/test_algorithm_preflight_boundaries.py academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_core_tsp_registry.py -q -p no:cacheprovider --tb=short
~~~

Expected: all focused C2 tests pass; no benchmark artifacts are generated.

- [ ] **Step 3: Run the required regression suites.**

Run:

~~~powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_numba_jit_parity.py academic_benchmark/tests/test_fair_comparison_protocol.py academic_benchmark/tests/test_fair_comparison_scientific_integrity.py academic_benchmark/tests/test_atsp_integration.py -q -p no:cacheprovider --tb=short
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short
git diff --check
git status --short --branch
~~~

Expected: the existing Package A/Package B suites remain green; no test should report an Or-opt Numba backend. Record exact pass/skip counts, warnings, and any environment blockers rather than estimating them.

- [ ] **Step 4: Self-review the C2 gate before handoff.** Confirm by source inspection that: \`Core-OrOpt-TSP\` is verified only because exact evidence IDs point to passing tests; TSP and ATSP both recompute directed closed costs independently; every bounded run obeys the atomic budget; native runs have \`evaluation_budget=None\`; backend labels are Python-only; GA/PSO/ALNS and planned compositions remain non-selectable; production registry IDs are unchanged; no Bildiri files were moved; and the original checkout/WIP worktree were not modified.

---

## Self-Review Checklist

- [ ] Every required C2 behavior has a deterministic test: symmetric TSP, directed ATSP, fixed nonzero seed, route normalization, independent cost, evaluation count, termination reason, backend truthfulness, and replay determinism.
- [ ] The plan does not infer Numba execution and does not publish a Numba claim for Or-opt.
- [ ] No task changes fairness-budget policy, production strategy exposure, solver relocation, archival, dependencies, frontend, API, databases, or generated evidence.
- [ ] Type/signature consistency is maintained: \`improve_or_opt_budgeted\` returns \`BudgetedSearchResult\`; fairness imports and registry dispatch use the same name; \`window\` is an integer \`1..3\`; \`Or-opt\` is the family string; \`objective=python;polish=none\` is the backend string.
- [ ] Candidate and planned boundaries remain explicitly tested after Or-opt promotion.

