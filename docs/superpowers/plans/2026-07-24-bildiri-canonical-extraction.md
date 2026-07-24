# Bildiri 2026 Canonical Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Complete Package B by preserving deterministic Bildiri GWO/HHO behavior as canonical matrix solvers in uniride_core, redirecting every active caller, reporting JIT and fallback execution truthfully, physically archiving all remaining Bildiri material with reproducible checksums, and leaving production strategy exposure unchanged.

**Architecture:** The production string-keyed routing engines in uniride_core.algorithms.tsp_meta_engines remain untouched. A distinct uniride_core.algorithms.tsp_matrix_metaheuristics package owns the academically characterized permutation-matrix GWO/HHO solvers and consumes the already-canonical uniride_core.algorithms.numba_accel kernels. Neutral objective-budget primitives move into uniride_core and academic_benchmark.fairness re-exports them for compatibility. Academic registry adapters remain responsible for public IDs, paired seeds, 1-indexed output, protocol metadata, and TSP/ATSP dispatch. Archival is the final transaction, never the first.

**Tech Stack:** Python 3.11+, NumPy 2.4.6, Numba 0.66.0, llvmlite 0.48.0, pytest, Pydantic 2.13.4, Git, PowerShell, SHA-256.

## Global Constraints

- Work only in C:\tmp\UniRide-wip-next on codex/package-b-bildiri-extraction. Never edit, pull into, clean, reset, or stage the rescue checkout.
- Live source and executable tests outrank historical comments and reports.
- Package B only: deterministic characterization, GWO/HHO canonical extraction, neutral budget ownership, backend provenance, active-call redirection, legacy CLI removal, Bildiri archive, and a thin draft Bildiri study profile.
- Do not redesign GWO/HHO equations, random-number order, mutation or movement operators, 2-opt semantics, termination rules, seed rules, route normalization, or objective-accounting units during the mechanical extraction.
- Do not replace or refactor uniride_core.algorithms.tsp_meta_engines.solve_gwo_tsp or solve_hho_tsp. They serve production routing and are intentionally behaviorally distinct.
- Reuse uniride_core.algorithms.numba_accel. Do not promote the duplicate Bildiri numba_accel.py.
- Reuse canonical uniride_core 2-opt and 3-opt ownership. Do not promote Bildiri two_opt.py or three_opt.py.
- Reuse canonical GA and PSO. B-GA and B-PSO are removed as executable identities and receive explicit migration guidance; no false compatibility alias is registered.
- Preserve these public academic IDs and current default policies exactly:
  - Core-GWO-TSP: memetic_2opt, population 50.
  - Core-GWO-TSP-Pure: pure, population 50.
  - Core-GWO-TSP-Memetic-2opt: memetic_2opt, population 50.
  - Numba-GWO: memetic_2opt, population 80.
  - Core-HHO-TSP: memetic_2opt, population 50.
  - Core-HHO-TSP-Pure: pure, population 50.
  - Core-HHO-TSP-Memetic-2opt: memetic_2opt, population 50.
  - Numba-HHO: memetic_2opt, population 80.
- Preserve the exact 38-key production STRATEGY_REGISTRY surface. Package B may add tests around it but must not edit optimizer_api strategy registration.
- Symmetric TSP route comparison uses canonical rotation plus reversal. Directed ATSP comparison uses rotation only.
- Objective values, objective-evaluation counts, iteration counts, budget termination, seed, and mathematical route equivalence must match the characterized source at the relocation commit.
- Backend metadata is a known defect. First prove exact relocation parity, including the observed legacy label. Only in a later, separate commit replace availability-based labeling with runtime-observed labeling and update tests to document that intentional contract correction.
- The verified ft53 artifact is the only current tracked TSP-family raw artifact with complete provenance. The new Bildiri profile is therefore draft and ATSP-only. Do not invent TSP provenance or use SQLite as a dataset artifact.
- Do not run full TSPLIB, CVRPLIB, DOE, tuning, or paper-scale experiments. Only unit tests and tiny deterministic smoke cases are authorized.
- Do not modify dependencies, lockfiles, virtual environments, databases, generated CSVs, historical report bytes, frontend, FastAPI surface, Package A schemas, or the YAEM archive.
- Commit every task separately. Do not push, merge, or open a pull request in Package B.

---

## File Map

| Path | Responsibility |
|---|---|
| uniride_core/algorithms/objective_budget.py | Neutral complete-tour evaluation budget and budgeted 2-opt primitive required by canonical solvers. |
| uniride_core/algorithms/tsp_matrix_metaheuristics/__init__.py | Public GWOOptimizer and HHOOptimizer exports for academic matrix TSP/ATSP. |
| uniride_core/algorithms/tsp_matrix_metaheuristics/base_solver.py | Matrix/coordinate solver base, route normalization, objective dispatch, and runtime backend observation. |
| uniride_core/algorithms/tsp_matrix_metaheuristics/gwo_solver.py | Mechanically relocated permutation GWO, pure and memetic modes. |
| uniride_core/algorithms/tsp_matrix_metaheuristics/hho_solver.py | Mechanically relocated permutation HHO, pure and memetic modes. |
| academic_benchmark/fairness.py | Academic protocol contracts; imports and re-exports neutral core budget primitives. |
| academic_benchmark/core/registry_setup.py | Public academic IDs, defaults, paired seeds, matrix dispatch, and result conversion. |
| academic_benchmark/cli_engine.py | Canonical-only CLI discovery; no path injection or B-GA/B-PSO execution. |
| academic_benchmark/fair_pilot.py | Canonical Numba import. |
| academic_benchmark/param_spaces.py | Removes executable B-GA/B-PSO parameter spaces. |
| academic_benchmark/smart_benchmark.py | Removes B-GA/B-PSO discovery and text; emits migration guidance when legacy names are supplied. |
| academic_benchmark/archive_manifest.py | Generic classifier injection and repeatable include paths while preserving YAEM behavior. |
| academic_benchmark/datasets/ft53.json | Strict uniride-dataset/v1 manifest for the verified ft53 artifact. |
| academic_benchmark/studies/bildiri2026/study.json | Thin draft ATSP-only study profile using explicit canonical IDs. |
| academic_benchmark/tests/fixtures/bildiri_gwo_hho_v1.json | Deterministic pre-move behavior snapshot, excluding elapsed time. |
| academic_benchmark/tests/test_bildiri_solver_parity.py | Direct legacy-versus-canonical parity before archive, then canonical-versus-golden regression. |
| academic_benchmark/tests/test_solver_backend_reporting.py | Forced JIT, forced Python fallback, mixed objective, and polish backend truthfulness. |
| academic_benchmark/tests/test_production_registry_snapshot.py | Exact 38-key production registry guard. |
| academic_benchmark/tests/test_bildiri_quarantine_boundary.py | Gate B proof for zero active imports/references, manifest coverage, and archive integrity. |
| archive/academic_benchmark/bildiri2026_legacy/** | Byte-preserved tracked Bildiri tree and four adjacent legacy files, plus manifest and quarantine notice. |

---

### Task 1: Freeze Characterization and Production Exposure

**Files:**
- Create: academic_benchmark/tests/fixtures/bildiri_gwo_hho_v1.json
- Create: academic_benchmark/tests/test_bildiri_solver_parity.py
- Create: academic_benchmark/tests/test_production_registry_snapshot.py

**Interfaces:**
- Captures eight direct cases: GWO/HHO × pure/memetic_2opt × symmetric TSP/directed ATSP.
- Captures route, closed-cycle cost, iterations, objective_evaluations, evaluation_budget, budget_terminated, variant, observed execution_backend, and seed. elapsed_ms is forbidden.
- Protects the exact 38-key production registry.

- [ ] **Step 1: Add deterministic matrix and route-normalization helpers**

In test_bildiri_solver_parity.py define the existing six-node symmetric and directed matrices from test_numba_jit_parity.py and these helpers:

~~~python
def closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    return sum(
        float(matrix[node][tour[(index + 1) % len(tour)]])
        for index, node in enumerate(tour)
    )


def normalize_cycle(tour: list[int], *, directed: bool) -> tuple[int, ...]:
    route = tuple(tour)
    rotations = [route[index:] + route[:index] for index in range(len(route))]
    candidates = rotations
    if not directed:
        reversed_route = tuple(reversed(route))
        candidates += [
            reversed_route[index:] + reversed_route[:index]
            for index in range(len(route))
        ]
    return min(candidates)
~~~

- [ ] **Step 2: Capture the legacy golden fixture once**

Use fixed seed 1729, population 4, max_iterations 1, evaluation_budget 100, polish_interval 1, polish_iters 1, and final_polish_iters 1. HHO also sets dive_count 0. Serialize sorted JSON with indent 2 and a final newline. Validate every route before writing:

~~~python
assert len(result.tour) == len(matrix)
assert set(result.tour) == set(range(len(matrix)))
assert result.tour_length == pytest.approx(closed_cost(result.tour, matrix), abs=0.0)
~~~

The capture helper validates this complete record contract before serialization:

~~~python
class ParityRecord(TypedDict):
    directed: bool
    normalized_tour: list[int]
    tour_length: float
    iterations: int
    objective_evaluations: int
    evaluation_budget: int
    budget_terminated: bool
    variant: Literal["pure", "memetic_2opt"]
    observed_execution_backend: str
    seed: int
~~~

The top-level object contains schema_version uniride-bildiri-parity/v1 and exactly eight named records. The capture helper must reject non-finite costs, incomplete tours, non-positive evaluation counts, an evaluation budget other than 100, or a missing backend label. Do not hand-edit captured route or cost values.

Run the capture through the JIT interpreter:

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.tests.test_bildiri_solver_parity --capture academic_benchmark\tests\fixtures\bildiri_gwo_hho_v1.json
~~~

Expected: eight validated cases written; no benchmark CSV or report generated.

- [ ] **Step 3: Add the legacy-against-golden test**

Parametrize the eight cases, reconstruct each solver from the fixed configuration, and compare normalized route, exact cost, iterations, evaluation counts, budget fields, variant, observed backend label, and seed. Require Numba and at least one nopython signature for the objective kernel; skip only when NUMBA_AVAILABLE is false before execution.

- [ ] **Step 4: Add the production registry snapshot**

The expected key set is exactly:

~~~python
EXPECTED_PRODUCTION_STRATEGIES = frozenset({
    "genetic_algorithm", "ga", "pso", "gwo", "grey_wolf", "hho",
    "harris_hawks", "ga_split", "ga-split", "ga_split_enhanced",
    "ga-split-enhanced", "pso_split", "pso-split", "gwo_split",
    "gwo-split", "hho_split", "hho-split", "ortools_cvrp", "ortools",
    "pyvrp", "hgs", "pyvrp_alt", "vroom", "vroom_fallback", "e2bso",
    "entropy_bso", "e2b", "r2dma", "rdma", "paoea", "aoea", "two_opt",
    "2opt", "greedy", "nearest_neighbor", "permutation_tsp",
    "permutation", "exact",
})
~~~

Assert both STRATEGY_REGISTRY and STRATEGY_FACTORIES have this exact set. Import optimizer_api/strategies with the same path bootstrap used by existing optimizer_api tests; do not change production imports to satisfy the test.

- [ ] **Step 5: Run and commit characterization**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task1 --tb=short
git add academic_benchmark/tests/fixtures/bildiri_gwo_hho_v1.json academic_benchmark/tests/test_bildiri_solver_parity.py academic_benchmark/tests/test_production_registry_snapshot.py
git commit -m "test(academic): freeze Bildiri solver parity"
~~~

Expected: all characterization cases and the exact production snapshot pass.

---

### Task 2: Move Neutral Objective Accounting into uniride_core

**Files:**
- Create: uniride_core/algorithms/objective_budget.py
- Modify: academic_benchmark/fairness.py
- Create: academic_benchmark/tests/test_objective_budget_ownership.py

- [ ] **Step 1: Write the ownership and compatibility tests**

Assert the core module owns EvaluationBudgetExhausted, ObjectiveEvaluationBudget, BudgetedSearchResult, two_opt_evaluation_upper_bound, and improve_two_opt_budgeted. Assert academic_benchmark.fairness exports the identical objects by identity, not copies:

~~~python
from academic_benchmark import fairness
from uniride_core.algorithms import objective_budget


def test_academic_fairness_reexports_core_budget_primitives():
    for name in (
        "EvaluationBudgetExhausted",
        "ObjectiveEvaluationBudget",
        "BudgetedSearchResult",
        "two_opt_evaluation_upper_bound",
        "improve_two_opt_budgeted",
    ):
        assert getattr(fairness, name) is getattr(objective_budget, name)
~~~

Also copy the existing initial-evaluation, atomic-cap, directed-cost, first-improvement, and exhaustion cases into this test module.

- [ ] **Step 2: Confirm the new module is missing**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_objective_budget_ownership.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task2-red --tb=short
~~~

Expected: collection fails with ModuleNotFoundError for uniride_core.algorithms.objective_budget.

- [ ] **Step 3: Move the exact neutral implementation**

Move only lines that define the five named primitives. objective_budget.py imports closed_tour_cost from uniride_core.algorithms.three_opt and contains no academic_benchmark import. In fairness.py delete the duplicate definitions and add:

~~~python
from uniride_core.algorithms.objective_budget import (
    BudgetedSearchResult,
    EvaluationBudgetExhausted,
    ObjectiveEvaluationBudget,
    improve_two_opt_budgeted,
    two_opt_evaluation_upper_bound,
)
~~~

Do not move FairRunResult, FairComparisonManifest, seed derivation, protocol validation, or 3-opt protocol adapters into core.

- [ ] **Step 4: Run focused fairness checks and commit**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_objective_budget_ownership.py academic_benchmark\tests\test_fair_comparison_protocol.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task2 --tb=short
git add uniride_core/algorithms/objective_budget.py academic_benchmark/fairness.py academic_benchmark/tests/test_objective_budget_ownership.py
git commit -m "refactor(core): own objective budget accounting"
~~~

Expected: all focused tests pass and identity assertions prove one implementation.

---

### Task 3: Mechanically Relocate GWO and HHO

**Files:**
- Create: uniride_core/algorithms/tsp_matrix_metaheuristics/__init__.py
- Create: uniride_core/algorithms/tsp_matrix_metaheuristics/base_solver.py
- Create: uniride_core/algorithms/tsp_matrix_metaheuristics/gwo_solver.py
- Create: uniride_core/algorithms/tsp_matrix_metaheuristics/hho_solver.py
- Modify: academic_benchmark/tests/test_bildiri_solver_parity.py

- [ ] **Step 1: Extend parity tests to compare legacy and canonical classes**

Import the not-yet-existing canonical classes and compare each of the eight cases. Require normalized route, cost, iterations, objective evaluations, evaluation budget, budget termination, variant, execution backend, and seed to match exactly. Keep the independent closed-cost assertion.

- [ ] **Step 2: Confirm canonical imports fail**

Run Task 1 tests. Expected: ModuleNotFoundError for uniride_core.algorithms.tsp_matrix_metaheuristics.

- [ ] **Step 3: Copy authoritative files without equation edits**

~~~powershell
New-Item -ItemType Directory -Force uniride_core\algorithms\tsp_matrix_metaheuristics
Copy-Item academic_benchmark\bildiri2026\core\base_solver.py uniride_core\algorithms\tsp_matrix_metaheuristics\base_solver.py
Copy-Item academic_benchmark\bildiri2026\core\gwo_solver.py uniride_core\algorithms\tsp_matrix_metaheuristics\gwo_solver.py
Copy-Item academic_benchmark\bildiri2026\core\hho_solver.py uniride_core\algorithms\tsp_matrix_metaheuristics\hho_solver.py
~~~

Apply only these import ownership changes:

~~~python
# base_solver.py
from uniride_core.models import TSPResult
from uniride_core.algorithms import numba_accel as _nb

# gwo_solver.py and hho_solver.py
from .base_solver import BaseTSPSolver, TSPResult
from uniride_core.algorithms import numba_accel as _nb
from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    improve_two_opt_budgeted,
    two_opt_evaluation_upper_bound,
)
~~~

Replace the function-local from . import numba_accel in BaseTSPSolver._tour_length_fast with the module-level _nb import. No other source statement changes in this task.

Create __init__.py:

~~~python
from .base_solver import BaseTSPSolver
from .gwo_solver import GWOOptimizer
from .hho_solver import HHOOptimizer

__all__ = ["BaseTSPSolver", "GWOOptimizer", "HHOOptimizer"]
~~~

- [ ] **Step 4: Prove exact relocation parity**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_numba_jit_parity.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task3 --tb=short
~~~

Expected: all eight legacy/canonical pairs match and both canonical and legacy objective kernels show nopython compilation when JIT is available.

- [ ] **Step 5: Commit the parity checkpoint**

~~~powershell
git add uniride_core/algorithms/tsp_matrix_metaheuristics academic_benchmark/tests/test_bildiri_solver_parity.py
git commit -m "refactor(core): relocate Bildiri GWO and HHO"
~~~

This commit is the immutable evidence point for exact relocation parity before backend metadata correction.

---

### Task 4: Make Backend Reporting Runtime-Truthful

**Files:**
- Modify: uniride_core/algorithms/tsp_matrix_metaheuristics/base_solver.py
- Modify: uniride_core/algorithms/tsp_matrix_metaheuristics/gwo_solver.py
- Modify: uniride_core/algorithms/tsp_matrix_metaheuristics/hho_solver.py
- Create: academic_benchmark/tests/test_solver_backend_reporting.py
- Modify: academic_benchmark/tests/test_bildiri_solver_parity.py

- [ ] **Step 1: Add failing backend truthfulness cases**

Cover both algorithms, pure and memetic variants, symmetric TSP and directed ATSP. Force the objective kernel to raise for Python fallback. Assert:

- a successful compiled objective records objective=numba;
- a forced fallback records objective=python even when NUMBA_AVAILABLE is true;
- fair budgeted 2-opt records polish=python;
- direct compiled 2-opt records polish=numba;
- no polish records polish=none;
- mixed use is preserved rather than overwritten by the last call.

- [ ] **Step 2: Add an explicit observation object**

In base_solver.py add:

~~~python
from dataclasses import dataclass, field


@dataclass
class BackendObservation:
    objective: set[str] = field(default_factory=set)
    polish: set[str] = field(default_factory=set)

    def reset(self) -> None:
        self.objective.clear()
        self.polish.clear()

    def label(self) -> str:
        objective = "+".join(sorted(self.objective)) or "unused"
        polish = "+".join(sorted(self.polish)) or "none"
        return "objective={};polish={}".format(objective, polish)
~~~

Initialize one observation per solver. Reset it at the start of solve. Add numba only after a successful kernel return; add python in the exception fallback and pure-Python objective path. Each _polish branch records its actually executed backend after success.

Replace availability-based execution_backend expressions in GWO/HHO with:

~~~python
"execution_backend": self._backend_observation.label()
~~~

- [ ] **Step 3: Preserve mathematical parity while documenting metadata correction**

Update test_bildiri_solver_parity.py so route, cost, iterations, evaluations, budget fields, variant, and seed still compare to the golden fixture. Replace exact legacy-backend equality with an assertion that the legacy observed label remains recorded in the fixture and the canonical label equals the runtime-observed contract.

- [ ] **Step 4: Run and commit**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_numba_jit_parity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task4 --tb=short
git add uniride_core/algorithms/tsp_matrix_metaheuristics academic_benchmark/tests/test_solver_backend_reporting.py academic_benchmark/tests/test_bildiri_solver_parity.py
git commit -m "fix(core): report executed solver backends"
~~~

Expected: forced fallback never reports Numba, compiled cases prove nopython signatures, and all mathematical/accounting fields remain unchanged.

---

### Task 5: Redirect Active Registry, Pilots, and Canonical Tests

**Files:**
- Modify: academic_benchmark/core/registry_setup.py
- Modify: academic_benchmark/fair_pilot.py
- Modify: academic_benchmark/tests/test_numba_jit_parity.py
- Modify: academic_benchmark/tests/test_fair_comparison_scientific_integrity.py
- Modify: academic_benchmark/tests/test_canonical_three_opt_integration.py
- Modify: academic_benchmark/tests/test_numba_three_opt.py
- Modify: academic_benchmark/tests/test_bildiri_solver_parity.py

- [ ] **Step 1: Add import-ownership assertions**

Assert the eight public GWO/HHO executors instantiate classes whose modules begin with uniride_core.algorithms.tsp_matrix_metaheuristics. Assert Numba helpers come from uniride_core.algorithms.numba_accel. Assert 3-opt tests import uniride_core.algorithms.three_opt or uniride_core.algorithms.numba_accel, never Bildiri.

- [ ] **Step 2: Redirect imports only**

registry_setup.py imports:

~~~python
from uniride_core.algorithms.tsp_matrix_metaheuristics import GWOOptimizer, HHOOptimizer
~~~

fair_pilot.py and JIT/Numba tests import:

~~~python
from uniride_core.algorithms import numba_accel
~~~

Scientific-integrity and parity tests import the canonical matrix metaheuristic classes. Three-opt integration tests use the existing canonical core ThreeOptSolver/functions already identified by the characterization report.

- [ ] **Step 3: Verify public identities and ATSP behavior**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_numba_jit_parity.py academic_benchmark\tests\test_fair_comparison_protocol.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py academic_benchmark\tests\test_atsp_integration.py academic_benchmark\tests\test_canonical_three_opt_integration.py academic_benchmark\tests\test_numba_three_opt.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task5 --tb=short
~~~

Expected: all pass; GWO/HHO optimize all nodes, directed closed costs recompute exactly, public aliases retain memetic policy and population defaults, and production remains exactly 38 keys.

- [ ] **Step 4: Commit redirection**

~~~powershell
git add academic_benchmark/core/registry_setup.py academic_benchmark/fair_pilot.py academic_benchmark/tests/test_numba_jit_parity.py academic_benchmark/tests/test_fair_comparison_scientific_integrity.py academic_benchmark/tests/test_canonical_three_opt_integration.py academic_benchmark/tests/test_numba_three_opt.py academic_benchmark/tests/test_bildiri_solver_parity.py
git commit -m "refactor(academic): route solvers through canonical core"
~~~

---

### Task 6: Remove Environment-Dependent Bildiri CLI Execution

**Files:**
- Modify: academic_benchmark/cli_engine.py
- Modify: academic_benchmark/param_spaces.py
- Modify: academic_benchmark/smart_benchmark.py
- Create: academic_benchmark/tests/test_legacy_algorithm_migrations.py

- [ ] **Step 1: Add failing migration and import-boundary tests**

Use this truthful migration table:

~~~python
LEGACY_ALGORITHM_MIGRATIONS = {
    "B-GA": "Core-GA-TSP",
    "B-PSO": "Core-PSO-TSP",
}
~~~

Tests require old names to raise a deterministic ValueError containing the replacement ID. They must never execute or silently alias. Test _detect_numba against uniride_core.algorithms.numba_accel without sys.path mutation.

- [ ] **Step 2: Remove the legacy path**

Delete _AB_DIR, _run_bildiri_solver, _run_bildiri_pso, _run_bildiri_ga, _get_bildiri_strategies, BILDIRI_STRATEGIES, BILDIRI_GA/BILDIRI_PSO dispatch, Optuna branches, parameter spaces, smart-benchmark descriptions, and numba-algorithm special cases for B-GA/B-PSO.

Implement _detect_numba as:

~~~python
def _detect_numba() -> bool:
    try:
        from uniride_core.algorithms import numba_accel
    except Exception:
        return False
    return bool(numba_accel.NUMBA_AVAILABLE)
~~~

Add one shared validator that rejects the legacy names with migration guidance before algorithm selection. Change the old GWO/HHO deprecation message from Bildiri wording to canonical matrix-solver wording.

- [ ] **Step 3: Run CLI and migration tests**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_legacy_algorithm_migrations.py academic_benchmark\tests\test_run_smoke_benchmark.py academic_benchmark\tests\test_run_matrix_benchmark.py academic_benchmark\tests\test_core_tsp_registry.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task6 --tb=short
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.cli_engine --help
~~~

Expected: tests pass, help exits 0, and importing cli_engine never adds academic_benchmark/bildiri2026 to sys.path.

- [ ] **Step 4: Commit CLI cleanup**

~~~powershell
git add academic_benchmark/cli_engine.py academic_benchmark/param_spaces.py academic_benchmark/smart_benchmark.py academic_benchmark/tests/test_legacy_algorithm_migrations.py
git commit -m "refactor(academic): retire Bildiri CLI identities"
~~~

---

### Task 7: Generalize Safe Archive Classification and Includes

**Files:**
- Modify: academic_benchmark/archive_manifest.py
- Modify: academic_benchmark/tests/test_archive_manifest.py

- [ ] **Step 1: Add failing generic-classifier and include tests**

Preserve all existing YAEM tests unchanged. Add tests proving:

- build_manifest accepts an injected classifier;
- quarantine can include a tracked directory plus explicitly named tracked files beneath a broader source root;
- untracked, ignored, traversal, symlink, sensitive, rollback, and destination-collision protections still apply to every include;
- no include means the existing full-tree behavior;
- Bildiri student-matrix outputs are INVALID, other results and tuned-parameter evidence are HISTORICAL_UNVERIFIED, and source/config/paper material is REFERENCE_ONLY.

- [ ] **Step 2: Introduce classifier injection**

~~~python
from collections.abc import Callable, Iterable

EvidenceClassifier = Callable[[PurePosixPath], EvidenceClass]


def classify_bildiri_evidence(path: PurePosixPath) -> EvidenceClass:
    parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    if "results" in parts and "student_matrix" in name:
        return EvidenceClass.INVALID
    if "results" in parts or name == "tuned_parameters_db.json":
        return EvidenceClass.HISTORICAL_UNVERIFIED
    return EvidenceClass.REFERENCE_ONLY
~~~

Add classifier: EvidenceClassifier = classify_yaem_evidence to build_manifest and quarantine_tracked_tree. Add repeatable include_paths relative to source_root. Resolve, deduplicate, and validate all includes before scanning or moving any file.

CLI additions:

~~~text
--profile yaem|bildiri
--include RELATIVE_PATH
~~~

YAEM commands without --include remain byte-for-byte compatible in behavior.

- [ ] **Step 3: Run archive regression tests**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_archive_manifest.py academic_benchmark\tests\test_yaem_quarantine_boundary.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task7 --tb=short
~~~

Expected: all existing YAEM tests and new generic/Bildiri cases pass.

- [ ] **Step 4: Commit archive generalization**

~~~powershell
git add academic_benchmark/archive_manifest.py academic_benchmark/tests/test_archive_manifest.py
git commit -m "refactor(academic): generalize evidence quarantine"
~~~

---

### Task 8: Add the Verified Dataset Manifest and Thin Study Profile

**Files:**
- Create: academic_benchmark/datasets/ft53.json
- Create: academic_benchmark/studies/bildiri2026/study.json
- Create: academic_benchmark/tests/test_bildiri_study_profile.py

- [ ] **Step 1: Add strict contract and artifact checks**

Test DatasetManifestV1 and StudyManifestV1 validation, repository-relative references, exact SHA-256, dimension 53, directed FULL_MATRIX semantics, diagonal sentinel, optimum 6905, explicit canonical IDs, and ATSP-only problem_families. Verify every algorithm_parameters key exactly matches algorithm_ids.

- [ ] **Step 2: Create ft53.json**

Use:

~~~json
{
  "schema_version": "uniride-dataset/v1",
  "dataset_id": "tsplib-ft53",
  "artifact_path": "academic_benchmark/tsplib_data/ft53.atsp",
  "source": {
    "authority_url": "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz",
    "retrieved_on": "2026-07-20"
  },
  "checksum": {
    "algorithm": "sha256",
    "value": "692ae545e226d88aa095e3e726c8a1dadf4ecc9b97852d0cdbb2ca2a98dd2634"
  },
  "problem_type": "ATSP",
  "dimension": 53,
  "matrix_semantics": {
    "directed": true,
    "edge_weight_type": "EXPLICIT",
    "edge_weight_format": "FULL_MATRIX",
    "diagonal_semantics": "sentinel"
  },
  "best_known": {
    "status": "optimal",
    "value": 6905.0,
    "provenance": "TSPLIB95 canonical ATSP optimum"
  }
}
~~~

- [ ] **Step 3: Create the draft profile**

Use only explicit, non-alias GWO/HHO identities:

~~~json
{
  "schema_version": "uniride-study/v1",
  "study_id": "bildiri2026",
  "title": "Bildiri 2026 Canonical ATSP Reproduction Profile",
  "status": "draft",
  "algorithm_ids": [
    "Core-GWO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Pure",
    "Core-HHO-TSP-Memetic-2opt"
  ],
  "algorithm_parameters": {
    "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2},
    "Core-GWO-TSP-Memetic-2opt": {"pack_size": 4, "max_iterations": 2, "polish_iters": 0, "final_polish_iters": 0},
    "Core-HHO-TSP-Pure": {"hawks": 4, "dive_count": 0, "max_iterations": 2},
    "Core-HHO-TSP-Memetic-2opt": {"hawks": 4, "dive_count": 0, "max_iterations": 2, "polish_iters": 0, "final_polish_iters": 0}
  },
  "dataset_manifest_refs": ["academic_benchmark/datasets/ft53.json"],
  "primary_protocol": {
    "protocol_id": "fixed_evaluation_budget",
    "protocol_version": "uniride-fair-tsp-v2",
    "budget_policy": "atomic_upper_bound_v1"
  },
  "secondary_protocol": {
    "protocol_id": "algorithm_native_termination",
    "protocol_version": "uniride-native-tsp-v1",
    "termination": {"max_iterations": 2}
  },
  "fixed_budget_levels": [100, 500],
  "run_count": 3,
  "base_seed": 2026,
  "seed_protocol_version": "sha256-seed-v1",
  "problem_families": ["ATSP"],
  "analysis_plan_id": "bildiri2026-reproduction-v1",
  "output_policy": {"repository_outputs": "smoke_only", "paper_scale_location": "external"},
  "paper_metadata": {"paper_id": "bildiri2026", "year": 2026, "venue": "draft"}
}
~~~

This is a smoke/reproduction profile, not publishable evidence. Adding real TSP manifests and the wider algorithm catalog belongs to Package C.

- [ ] **Step 4: Validate and commit**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_study_profile.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_ft53_atsp_ingestion.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task8 --tb=short
git add academic_benchmark/datasets/ft53.json academic_benchmark/studies/bildiri2026/study.json academic_benchmark/tests/test_bildiri_study_profile.py
git commit -m "feat(academic): add Bildiri study profile"
~~~

Expected: strict contracts, source digest, matrix semantics, and profile references pass.

---

### Task 9: Prove Zero Active Bildiri Reachability Before Archival

**Files:**
- Create: academic_benchmark/tests/test_bildiri_quarantine_boundary.py
- Modify: any active file still identified by this test, within Package B scope only.

- [ ] **Step 1: Add AST and token boundary checks**

Scan active Python beneath academic_benchmark, uniride_core, and optimizer_api, excluding academic_benchmark/bildiri2026 because it is the pending source tree and excluding archive. Fail on:

- import or ImportFrom targeting academic_benchmark.bildiri2026, bildiri2026, or top-level core fallbacks;
- string/path injection of academic_benchmark/bildiri2026;
- executable B-GA, B-PSO, BILDIRI_GA, or BILDIRI_PSO tokens outside the migration table/tests;
- canonical matrix solver importing academic_benchmark;
- active tests that execute Bildiri data manager, orchestration, benchmark scripts, or tuned parameter DB.

Also assert registry_setup resolves GWOOptimizer/HHOOptimizer from uniride_core and production snapshot remains exact.

- [ ] **Step 2: Redirect or retire the final references**

The expected legacy-only files are exactly:

- academic_benchmark/run_numba_with_bildiri_params.py
- academic_benchmark/tests/test_bildiri_data_manager.py
- academic_benchmark/tests/test_bildiri2026_benchmark_script_smoke.py
- academic_benchmark/tests/test_orchestrate_batch.py

Do not delete them yet. Mark them as the four adjacent archive includes and ensure no active module imports them.

- [ ] **Step 3: Run the pre-archive gate**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_quarantine_boundary.py academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task9 --tb=short
~~~

Expected: zero active reachability outside the pending legacy tree and four declared archive includes.

- [ ] **Step 4: Commit the boundary gate**

~~~powershell
git add academic_benchmark/tests/test_bildiri_quarantine_boundary.py
git commit -m "test(academic): enforce Bildiri extraction boundary"
~~~

---

### Task 10: Physically Archive Bildiri Evidence

**Files:**
- Modify: .gitignore
- Modify: archive/README.md
- Create: archive/academic_benchmark/bildiri2026_legacy/QUARANTINE.md
- Create: archive/academic_benchmark/bildiri2026_legacy/manifest.json
- Move: 229 tracked files under academic_benchmark/bildiri2026.
- Move: the four adjacent legacy files listed in Task 9.
- Modify: academic_benchmark/tests/test_bildiri_solver_parity.py
- Modify: academic_benchmark/tests/test_bildiri_quarantine_boundary.py

**Hard precondition:** Do not start this task unless Tasks 1 through 9 are committed, their focused tests pass, exact mathematical/accounting relocation parity has been recorded, runtime backend tests pass, production registry snapshot passes, and the pre-archive zero-reachability test identifies only the declared pending legacy paths.

- [ ] **Step 1: Verify the exact 233-file inventory**

~~~powershell
python -c "import subprocess; paths=['academic_benchmark/bildiri2026','academic_benchmark/run_numba_with_bildiri_params.py','academic_benchmark/tests/test_bildiri_data_manager.py','academic_benchmark/tests/test_bildiri2026_benchmark_script_smoke.py','academic_benchmark/tests/test_orchestrate_batch.py']; p=subprocess.run(['git','ls-files','-z','--',*paths],check=True,capture_output=True); count=sum(bool(x) for x in p.stdout.split(bytes([0]))); assert count == 233, count; print('TRACKED', count)"
git status --short --branch
~~~

Expected: TRACKED 233 and no unrelated changes. Any count drift is a hard stop requiring plan reconciliation.

- [ ] **Step 2: Run non-mutating sensitive and include preflight**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.archive_manifest scan --repo-root . --source academic_benchmark --profile bildiri --include bildiri2026 --include run_numba_with_bildiri_params.py --include tests/test_bildiri_data_manager.py --include tests/test_bildiri2026_benchmark_script_smoke.py --include tests/test_orchestrate_batch.py
~~~

Expected: tracked=233, ambiguous=0, untracked=0, unsafe_ignored=0. Confirmed secrets, if any, are withheld by metadata only. Any ambiguity or inventory mismatch stops the task before mutation.

- [ ] **Step 3: Narrowly allow the Bildiri archive**

Extend the existing archive allowlist without changing the YAEM entries:

~~~gitignore
!archive/academic_benchmark/bildiri2026_legacy/
!archive/academic_benchmark/bildiri2026_legacy/**
~~~

- [ ] **Step 4: Run the transaction**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.archive_manifest quarantine --repo-root . --source academic_benchmark --profile bildiri --archive archive/academic_benchmark/bildiri2026_legacy --archive-id bildiri2026_legacy --include bildiri2026 --include run_numba_with_bildiri_params.py --include tests/test_bildiri_data_manager.py --include tests/test_bildiri2026_benchmark_script_smoke.py --include tests/test_orchestrate_batch.py
~~~

Expected: 233 manifest entries, less only any WITHHELD_SENSITIVE file content while retaining its metadata entry.

- [ ] **Step 5: Add the quarantine notice**

QUARANTINE.md must state:

- historical archive; non-importable and non-executable;
- pre-distance-fix and student-matrix results are not current scientific evidence;
- all remaining results are HISTORICAL_UNVERIFIED unless independently reproduced under current contracts;
- archived source/config/paper material is REFERENCE_ONLY;
- active GWO/HHO moved to uniride_core after exact parity;
- active 2-opt/3-opt/GA/PSO use canonical core implementations;
- B-GA and B-PSO are retired names with Core-GA-TSP and Core-PSO-TSP migration targets;
- manifest.json is authoritative for original path, archived path, size, digest, and evidence class.

- [ ] **Step 6: Convert parity to canonical-against-golden**

Remove all legacy imports from test_bildiri_solver_parity.py. Keep the same eight cases and compare canonical results against bildiri_gwo_hho_v1.json for every mathematical/accounting field. Backend assertions use the corrected runtime contract from Task 4.

Update the boundary test to require:

- academic_benchmark/bildiri2026 is absent and non-importable;
- all 233 original paths appear exactly once in manifest.json;
- every non-withheld archived byte verifies;
- no unmanifested historical file exists;
- active Python has zero Bildiri imports or path injections;
- package discovery excludes archive and Bildiri.

- [ ] **Step 7: Verify, stage, inspect, and commit**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/bildiri2026_legacy/manifest.json
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_quarantine_boundary.py academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-task10 --tb=short
git add -A -- .gitignore archive/README.md archive/academic_benchmark/bildiri2026_legacy academic_benchmark/bildiri2026 academic_benchmark/run_numba_with_bildiri_params.py academic_benchmark/tests/test_bildiri_data_manager.py academic_benchmark/tests/test_bildiri2026_benchmark_script_smoke.py academic_benchmark/tests/test_orchestrate_batch.py academic_benchmark/tests/test_bildiri_solver_parity.py academic_benchmark/tests/test_bildiri_quarantine_boundary.py
git diff --cached --stat
git diff --cached --summary
git diff --cached --check
git commit -m "chore(academic): quarantine legacy Bildiri evidence"
~~~

Expected: verifier reports 233 entries, tests pass, staged scope contains no production/frontend/dependency/generated-output change, and Git recognizes byte-identical moves where possible.

---

### Task 11: Execute Gate B and Record Exact Evidence

**Files:**
- Modify: WORKLOG.md

- [ ] **Step 1: Run the mandatory JIT/fallback and fair-protocol suites**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_numba_jit_parity.py academic_benchmark\tests\test_fair_comparison_protocol.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py academic_benchmark\tests\test_atsp_integration.py academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_bildiri_solver_parity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-gate-focused --tb=short
~~~

Expected: zero failures; no JIT parity skip in the pinned environment; objective kernel has nopython signatures; all four original pure JIT/fallback cases plus new pure/memetic cases pass.

- [ ] **Step 2: Run contract, archive, CLI, and production guards**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.contracts.export_schemas check
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/bildiri2026_legacy/manifest.json
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_archive_manifest.py academic_benchmark\tests\test_yaem_quarantine_boundary.py academic_benchmark\tests\test_bildiri_quarantine_boundary.py academic_benchmark\tests\test_bildiri_study_profile.py academic_benchmark\tests\test_production_registry_snapshot.py academic_benchmark\tests\test_legacy_algorithm_migrations.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-gate-contracts --tb=short
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.cli_engine --help
~~~

- [ ] **Step 3: Run the complete academic suite**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-b-full --tb=short
~~~

Expected: zero failures. Record the exact pass/skip count; do not copy the previous 409-pass baseline as the new outcome.

- [ ] **Step 4: Audit repository boundaries**

~~~powershell
git diff WIP...HEAD --name-only
git diff --check
git status --short --branch
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide status --short --branch
~~~

Expected: only Package B files changed; feature worktree clean after the final commit; rescue checkout retains its pre-existing dirty files and no Package B edits.

- [ ] **Step 5: Record the exact Gate B result**

Append a dated WORKLOG entry containing:

- relocation-parity commit and eight-case matrix;
- the deliberate backend metadata correction and exact truthful labels;
- exact focused/full test commands, pass/skip counts, and nopython evidence;
- archive manifest entry/classification counts and verification outcome;
- zero active Bildiri import result;
- exact production 38-key snapshot result;
- draft ATSP-only profile and why no TSP dataset was fabricated;
- explicit statement that no paper-scale benchmark ran;
- any environment blocker separated from code defects.

- [ ] **Step 6: Commit Gate B evidence**

~~~powershell
git add WORKLOG.md
git commit -m "docs: record Package B extraction verification"
git status --short --branch
~~~

---

## Gate B Acceptance Checklist

- [ ] Eight direct GWO/HHO parity cases cover pure/memetic and symmetric/directed matrices.
- [ ] All public GWO/HHO IDs and aliases retain their identity, variant policy, seed behavior, and 50/80 population defaults.
- [ ] Mathematical route equivalence, independent closed cost, iterations, objective-evaluation counts, budget termination, and seed match the characterization.
- [ ] Backend reporting reflects executed code, not NUMBA_AVAILABLE alone.
- [ ] Pinned JIT tests execute without skip and show nopython signatures.
- [ ] Canonical matrix GWO/HHO import no academic_benchmark module.
- [ ] Canonical Numba, 2-opt, 3-opt, GA, and PSO ownership is reused; duplicates are not promoted.
- [ ] cli_engine performs no Bildiri path injection or dynamic top-level core import.
- [ ] B-GA/B-PSO fail with truthful migration guidance and are not registered aliases.
- [ ] No active Python imports academic_benchmark.bildiri2026.
- [ ] The 233-file archive inventory is complete, checksum-verifiable, and free of unresolved sensitive findings.
- [ ] The active Bildiri package is absent and non-importable.
- [ ] ft53.json validates and matches the shipped artifact digest.
- [ ] The draft Bildiri profile is strict, explicit-ID-only, and ATSP-only.
- [ ] Production STRATEGY_REGISTRY and STRATEGY_FACTORIES remain exactly the approved 38-key set.
- [ ] Package A schemas and YAEM archive still verify.
- [ ] Full academic tests pass with exact counts recorded.
- [ ] No benchmark CSV/report, dependency, database, frontend, API, or rescue-checkout file was modified.

## Explicit Handoff Boundary

Stop after Gate B. Do not implement the Package C capability catalog, composition framework, ALNS or pseudo-LKH policy, broader dataset manifests, study runner, native-termination expansion, statistical analysis, paper-scale experiments, documentation synchronization, remote fetch/reconciliation, push, or pull request. Those actions require their own approved plans and the user's powerful-computer verification.
