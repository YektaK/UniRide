# Academic Capability Catalog and Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Package C1 as an evidence-gated canonical TSP/ATSP capability catalog, resolver, problem/backend/protocol preflight service, and decision-bound execution gateway across every public academic runner without changing solver mathematics or production strategy exposure.

**Architecture:** A frozen `uniride_core.algorithms.capabilities` module owns capability facts but is not imported by production registration. Academic resolver, validation, preflight, and gateway modules authorize an exact claim before registry access and validate the result afterward. Registry membership remains an implementation fact, never scientific evidence.

**Tech Stack:** Python 3.11+, dataclasses, Enum, MappingProxyType, Pydantic 2.13.4, NumPy 2.4.6, Numba 0.66.0, llvmlite 0.48.0, pytest, JSON Schema, Git, PowerShell.

## Global Constraints

- Work only in `C:\tmp\UniRide-wip-next` on `codex/package-c1-capability-preflight-design`.
- Follow `docs/superpowers/specs/2026-07-28-academic-capability-catalog-preflight-design.md`.
- C1 covers canonical academic TSP/ATSP only. CVRP/CVRPTW/UniRide, frontend, FastAPI, archives, dependencies, databases, and generated benchmark reports are excluded.
- Do not change solver equations, random order, moves, evaluation units, seeds, or termination mathematics.
- `CANDIDATE` is implemented but non-selectable; `PLANNED` is reserved and unimplemented.
- TSP, ATSP, fixed, native, pure, memetic, Python, and Numba claims require independent executable evidence.
- `REQUIRE_NUMBA_OBJECTIVE` applies to the objective stage; evidenced Python polish is allowed.
- Unexpected mixed/Python execution after a Numba decision invalidates the attempt; a retry requires a new decision.
- Manifests accept canonical IDs only. CLI uses the exact normative table, with no fuzzy/case normalization.
- `B-GA`, `B-PSO`, `GWO-LKH`, and `HHO-LKH` remain hard errors.
- Catalog-governed TSP/ATSP requests require fixed/native protocol plus caller backend policy. CVRP/CVRPTW remain outside C1.
- Leave `uniride_core.algorithms.registry`, `engine_factory.py`, and the production 38-key registry unchanged.
- Do not re-export capabilities from `uniride_core/algorithms/__init__.py`.
- Run deterministic unit, focused JIT, and small smoke tests only. Commit each task separately.

## File Map

| Path | Responsibility |
|---|---|
| `uniride_core/algorithms/capabilities.py` | Frozen types, catalog, invariants, lookup, exact claim matching. |
| `academic_benchmark/core/algorithm_errors.py` | Typed identifier, preflight, and result failures. |
| `academic_benchmark/core/algorithm_resolution.py` | Source-aware canonical/alias/forbidden resolution. |
| `academic_benchmark/core/problem_validation.py` | Real-problem matrix validation and fingerprint report. |
| `academic_benchmark/core/preflight.py` | Runtime probe and exact protocol/backend claim selection. |
| `academic_benchmark/core/execution_gateway.py` | Resolve, preflight, registry lookup, execute, postflight. |
| `academic_benchmark/core/registry_setup.py` | Identity-preserving canonical executor wiring. |
| `academic_benchmark/contracts/study.py` | Canonical-only active algorithms. |
| `academic_benchmark/contracts/run.py` | Canonical/requested identity and decision provenance. |
| `academic_benchmark/fairness.py` | Canonical backend labels and requested-ID field. |
| `academic_benchmark/fair_pilot.py` | Fixed caller policy and gateway integration. |
| `academic_benchmark/native_pilot.py` | Native caller policy and gateway integration. |
| `academic_benchmark/cli_engine.py` | CLI resolution, execution context, no governed fallback. |
| `academic_benchmark/engine_core.py` | Picklable smart-benchmark request fields. |
| `academic_benchmark/smart_benchmark.py` | Catalog-filtered gateway execution. |

---

### Task 1: Frozen Core Capability Model

**Files:** Create `uniride_core/algorithms/capabilities.py` and `academic_benchmark/tests/test_algorithm_capability_catalog.py`.

**Produces:** all enums and frozen types from the spec plus `build_capability_catalog`, `list_algorithm_capabilities`, `get_algorithm_capability`, and `find_capability_claim`.

- [ ] **Write failing invariant tests.** Cover duplicate IDs, VERIFIED without claims, CANDIDATE/PLANNED with claims, empty evidence, objective NONE, pure with polish, ATSP without directed preservation, fixed without exact accounting, `production_ready=True`, planned without a note, and mutation attempts.

~~~python
def test_candidate_cannot_publish_claims():
    with pytest.raises(ValueError, match="cannot publish claims"):
        build_capability_catalog([
            AlgorithmCapability(
                canonical_id="Core-X-TSP",
                family="X",
                label="X",
                lifecycle=LifecycleStatus.CANDIDATE,
                claims=(valid_claim(),),
            )
        ])
~~~

- [ ] **Run red.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task1-red --tb=short
~~~

Expected: missing module.

- [ ] **Implement exact frozen interfaces.**

~~~python
@dataclass(frozen=True)
class ExecutionBackendProfile:
    objective: BackendKind
    polish: BackendKind = BackendKind.NONE

@dataclass(frozen=True)
class CapabilityClaim:
    problem: ProblemContract
    protocol: ExecutionProtocol
    backend_profile: ExecutionBackendProfile
    composition: CompositionKind
    directed_cost_preserved: bool
    exact_objective_accounting: bool
    fixed_seed_deterministic: bool
    truthful_result_reporting: bool
    evidence_ids: tuple[str, ...]

@dataclass(frozen=True)
class AlgorithmCapability:
    canonical_id: str
    family: str
    label: str
    lifecycle: LifecycleStatus
    claims: tuple[CapabilityClaim, ...] = ()
    production_ready: bool = False
    planning_note: str | None = None
~~~

Return `MappingProxyType` and tuples at every collection boundary.

- [ ] **Populate safe initial IDs.** CANDIDATE: Core TwoOpt, ThreeOpt, OrOpt, GA, PSO, GWO/HHO pure and memetic-2opt, and ALNS. PLANNED: four approved GWO/HHO 3-opt/ALNS hybrids. Add no claims yet.

- [ ] **Run green and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task1 --tb=short
git add uniride_core\algorithms\capabilities.py academic_benchmark\tests\test_algorithm_capability_catalog.py
git commit -m "feat(core): add immutable algorithm capability catalog"
~~~

### Task 2: Exact Identifier Resolution

**Files:** Create `academic_benchmark/core/algorithm_errors.py`, `algorithm_resolution.py`, and `tests/test_algorithm_resolution.py`; modify `cli_engine.py` and `test_legacy_algorithm_migrations.py`.

- [ ] **Write mapping and failure tests.** Exact CLI mappings are:

~~~python
EXPECTED = {
    "Numba-2-opt": "Core-TwoOpt-TSP",
    "Numba-3-opt-bounded": "Core-ThreeOpt-TSP",
    "Numba-Or-opt": "Core-OrOpt-TSP",
    "Numba-GA": "Core-GA-TSP",
    "Numba-PSO": "Core-PSO-TSP",
    "GWO": "Core-GWO-TSP-Pure",
    "HHO": "Core-HHO-TSP-Pure",
    "Numba-GWO": "Core-GWO-TSP-Memetic-2opt",
    "Core-GWO-TSP": "Core-GWO-TSP-Memetic-2opt",
    "Numba-HHO": "Core-HHO-TSP-Memetic-2opt",
    "Core-HHO-TSP": "Core-HHO-TSP-Memetic-2opt",
    "SOTA-ALNS-TSP": "ALNS-TSP",
}
~~~

Manifest aliases fail; deprecated aliases warn; GWO/HHO active labels do not; case variants fail; four forbidden IDs fail before registry enumeration.

- [ ] **Implement stable errors and result.**

~~~python
@dataclass(frozen=True)
class ResolutionResult:
    requested_id: str
    canonical_id: str
    source: IdentifierSource
    alias_used: bool
    alias_policy: AliasPolicy | None
    warning_code: str | None
    warning_message: str | None
~~~

`AlgorithmSelectionError` carries `code`, `message`, and optional `replacement_id`. Implement every named spec subclass.

- [ ] **Implement immutable tables and `resolve_algorithm_id`.** Validate alias/canonical collisions against the catalog. Never import `AlgorithmRegistry`.

- [ ] **Keep `_validate_algorithm_migration` as a resolver-backed compatibility wrapper.**

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_resolution.py academic_benchmark\tests\test_legacy_algorithm_migrations.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task2 --tb=short
git add academic_benchmark\core\algorithm_errors.py academic_benchmark\core\algorithm_resolution.py academic_benchmark\cli_engine.py academic_benchmark\tests\test_algorithm_resolution.py academic_benchmark\tests\test_legacy_algorithm_migrations.py
git commit -m "feat(academic): add canonical algorithm resolver"
~~~

### Task 3: Identity-Preserving Canonical Registry Wiring

**Files:** Modify `academic_benchmark/core/registry_setup.py`, `test_core_tsp_registry.py`, and `test_canonical_three_opt_integration.py`; create `test_canonical_registry_identity.py`.

- [ ] **Write failing tests** for Core TwoOpt/ThreeOpt/OrOpt and ALNS exact registry keys, complete 1-indexed tours, independent closed cost, and `result.algorithm == canonical_id`. Preserve `SOTA-ALNS-TSP` with its own reported ID.

- [ ] **Register canonical local-search wrappers** through `_make_legacy_executor(payload, "local_search", canonical_id)` after broad core registration. Do not change operators.

- [ ] **Make SOTA reporting explicit.**

~~~python
def _make_sota_executor(algo: str, reported_algorithm_id: str | None = None):
    public_id = reported_algorithm_id or f"SOTA-{algo}"
~~~

Use `public_id` in results; add `ALNS-TSP` while preserving `SOTA-ALNS-TSP`.

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_core_tsp_registry.py academic_benchmark\tests\test_canonical_three_opt_integration.py academic_benchmark\tests\test_canonical_registry_identity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task3 --tb=short
git add academic_benchmark\core\registry_setup.py academic_benchmark\tests\test_core_tsp_registry.py academic_benchmark\tests\test_canonical_three_opt_integration.py academic_benchmark\tests\test_canonical_registry_identity.py
git commit -m "feat(academic): wire canonical TSP executor identities"
~~~

### Task 4: Canonical Problem Validation

**Files:** Create `academic_benchmark/core/problem_validation.py` and `test_algorithm_problem_validation.py`; modify `fair_pilot.py`.

- [ ] **Write tests** for square shape, dimension, numeric finite/non-negative off-diagonal costs, time/distance selection, stable fingerprint, immutable matrix, and TSP/ATSP metadata. A symmetric declared ATSP remains ATSP with `observed_asymmetric=False`; fair-pilot suite rules may separately require an asymmetric ATSP fixture.

- [ ] **Implement the report.**

~~~python
@dataclass(frozen=True)
class ProblemValidationReport:
    problem_name: str
    contract: ProblemContract
    dimension: int
    matrix_kind: str
    matrix: tuple[tuple[float, ...], ...]
    matrix_sha256: str
    observed_asymmetric: bool
~~~

`validate_problem_for_preflight(problem)` receives the actual object, extracts/prepares its matrix once, validates it, and fingerprints compact JSON with `allow_nan=False`. Reject non-TSP/ATSP contracts.

- [ ] **Delegate fair-pilot matrix extraction** to this validator; keep mixed-suite and asymmetric-ATSP study rules in `resolve_problems`.

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_problem_validation.py academic_benchmark\tests\test_fair_pilot_cli.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task4 --tb=short
git add academic_benchmark\core\problem_validation.py academic_benchmark\fair_pilot.py academic_benchmark\tests\test_algorithm_problem_validation.py
git commit -m "feat(academic): validate TSP problem contracts"
~~~

### Task 5: Evidence-Gated Preflight

**Files:** Create `academic_benchmark/core/preflight.py` and `test_algorithm_preflight.py`; modify `fair_pilot.py` and `test_numba_jit_parity.py`.

- [ ] **Write the full matrix tests:** candidate/planned errors; fixed positive budget; native no budget; exact TSP/ATSP claim; PYTHON_ONLY; prefer Numba then evidenced Python; require Numba; Numba objective plus Python polish; missing executor; immutable decision provenance.

- [ ] **Refactor the existing tiny JIT probe** into:

~~~python
@dataclass(frozen=True)
class RuntimeBackendAvailability:
    python: bool
    numba_nopython: bool
    detail: str
~~~

`probe_runtime_backends` executes the canonical tiny ATSP kernel and requires `nopython_signatures`. Keep `preflight_numba_objective` as a compatibility wrapper.

- [ ] **Implement request and decision.**

~~~python
@dataclass(frozen=True)
class PreflightRequest:
    resolution: ResolutionResult
    problem: object
    protocol: ExecutionProtocol
    backend_policy: BackendPolicy
    evaluation_budget: int | None
    registered_algorithm_ids: frozenset[str]
    runtime_backends: RuntimeBackendAvailability

@dataclass(frozen=True)
class PreflightDecision:
    resolution: ResolutionResult
    problem: ProblemValidationReport
    protocol: ExecutionProtocol
    backend_policy: BackendPolicy
    selected_claim: CapabilityClaim
    selected_backend: ExecutionBackendProfile
    fallback_reason: str | None
    executor_registry_id: str
    evidence_ids: tuple[str, ...]
~~~

`preflight_run(request, *, capability_lookup=get_algorithm_capability)` validates lifecycle, problem, protocol/budget, registration, and exact backend claim in that order. It never calls `get_executor`.
Tests inject a lookup backed by a synthetic immutable catalog; production uses the core lookup.

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_preflight.py academic_benchmark\tests\test_numba_jit_parity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task5 --tb=short
git add academic_benchmark\core\preflight.py academic_benchmark\fair_pilot.py academic_benchmark\tests\test_algorithm_preflight.py academic_benchmark\tests\test_numba_jit_parity.py
git commit -m "feat(academic): add evidence-gated execution preflight"
~~~

### Task 6: Prove and Promote Exact Claims

**Files:** Create `test_algorithm_capability_evidence.py`; modify `registry_setup.py`, `fairness.py`, `native_protocol.py`, `capabilities.py`, and fair/native protocol tests.

- [ ] **Canonicalize local metadata:** use `execution_backend="objective=python;polish=none"` and replace native/fair approved Numba 2/3 IDs with Core TwoOpt/ThreeOpt. Keep historical registry keys.

- [ ] **Add executable evidence** on symmetric TSP and directed ATSP with independent cost, complete route, fixed seed, exact counts, termination, and backend:

| Algorithms | Protocol | Profile |
|---|---|---|
| GWO/HHO pure | fixed and native | objective Numba, polish none |
| GWO/HHO memetic-2opt | fixed | objective Numba, polish Python |
| Core TwoOpt/ThreeOpt | fixed and native | objective Python, polish none |

Do not publish Python-objective GWO/HHO claims because caller-controlled Python selection does not exist.

- [ ] **Add native ATSP GWO/HHO evidence** and require no skip for a published Numba claim.

- [ ] **Promote catalog entries** using evidence IDs that name real test functions. Leave OrOpt, GA, PSO, ALNS CANDIDATE.

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_fair_comparison_protocol.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py academic_benchmark\tests\test_native_termination_protocol.py academic_benchmark\tests\test_solver_backend_reporting.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task6 --tb=short
git add uniride_core\algorithms\capabilities.py academic_benchmark\core\registry_setup.py academic_benchmark\fairness.py academic_benchmark\native_protocol.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_native_termination_protocol.py academic_benchmark\tests\test_fair_comparison_protocol.py
git commit -m "test(academic): promote evidenced TSP capabilities"
~~~

### Task 7: Decision-Bound Postflight and Contracts

**Files:** Create `execution_gateway.py` and `test_algorithm_execution_gateway.py`; modify `fairness.py`, study/run contracts, schemas, and contract/profile tests.

- [ ] **Write ordering/postflight tests.** Exploding getters prove all resolution/preflight failures precede lookup. Fake results prove incomplete/duplicate tours, wrong directed cost, wrong counts, empty termination, mixed backend, and profile mismatch fail.

- [ ] **Extend provenance:** add `requested_algorithm_id: str | None` to `FairRunResult`. Add to `AlgorithmRunV1`:

~~~python
requested_algorithm_id: str | None = None
backend_policy: Literal["python_only", "prefer_numba", "require_numba"]
backend_profile: dict[str, str]
capability_evidence_ids: list[str]
~~~

- [ ] **Enforce canonical StudyManifestV1 IDs** in primary and secondary lists via `IdentifierSource.MANIFEST`; reject candidate/planned entries. Bildiri profile remains valid.

- [ ] **Implement backend parsing and postflight.** Accept only objective `python`/`numba` and polish `none`/`python`/`numba`. Reject unknown, unused, mixed, and `numba+python`. Recompute the 1-indexed directed cycle, validate protocol accounting/termination, require canonical `algorithm` and `algorithm_id`, then attach requested provenance.

- [ ] **Implement the exact gateway boundary:**

~~~python
def execute_preflighted(
    *,
    requested_algorithm_id: str,
    identifier_source: IdentifierSource,
    problem: object,
    params: Mapping[str, Any],
    seed: int,
    run_idx: int,
    protocol: ExecutionProtocol,
    backend_policy: BackendPolicy,
    evaluation_budget: int | None,
    registered_algorithm_ids: frozenset[str],
    runtime_backends: RuntimeBackendAvailability,
    registry_getter: Callable[[str], Callable[..., RunResult]],
) -> tuple[RunResult, PreflightDecision]:
    # Body follows the required resolve -> preflight -> lookup -> execute -> postflight order.

- [ ] **Regenerate schemas, test, commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m academic_benchmark.contracts.export_schemas
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_execution_gateway.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_bildiri_study_profile.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task7 --tb=short
git add academic_benchmark\core\execution_gateway.py academic_benchmark\fairness.py academic_benchmark\contracts academic_benchmark\schemas academic_benchmark\tests\test_algorithm_execution_gateway.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_bildiri_study_profile.py
git commit -m "feat(academic): validate preflighted results and provenance"
~~~

### Task 8: Fair and Native Pilot Integration

**Files:** Modify `fair_pilot.py`, `native_pilot.py`, pilot tests; create `test_algorithm_preflight_boundaries.py`.

- [ ] **Write no-bypass tests** with exploding getters for candidate, planned, wrong problem/protocol, and unavailable backend.

- [ ] **Migrate stored/config IDs** from Numba 2/3 to canonical Core TwoOpt/ThreeOpt.

- [ ] **Remove eager executor dictionaries.** Probe once per pilot; call the gateway per problem/algorithm/replicate. Declare REQUIRE_NUMBA_OBJECTIVE for GWO/HHO and PYTHON_ONLY for local search.

- [ ] **Persist decision metadata** and delete duplicate ad hoc backend checks.

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_fair_pilot_cli.py academic_benchmark\tests\test_native_termination_protocol.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8 --tb=short
git add academic_benchmark\fair_pilot.py academic_benchmark\native_pilot.py academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_fair_pilot_cli.py academic_benchmark\tests\test_native_termination_protocol.py
git commit -m "feat(academic): preflight fair and native pilots"
~~~

### Task 9: CLI and Smart-Benchmark Enforcement

**Files:** Modify `cli_engine.py`, `engine_core.py`, `smart_benchmark.py`, boundary/migration tests; create `test_smart_benchmark_preflight.py`.

- [ ] **Add exact CLI choices:**

~~~python
parser.add_argument("--execution-protocol", choices=("fixed_evaluation_budget", "algorithm_native_termination"))
parser.add_argument("--evaluation-budget", type=int)
parser.add_argument("--backend-policy", choices=("python_only", "prefer_numba", "require_numba"))
~~~

Resolve `--algos` before setup. Fixed requires positive budget; native forbids one. Cataloged TSP/ATSP requires protocol and policy; error exit is 2.

- [ ] **Carry picklable request data** in CLI task payload and `BenchmarkTask`: requested/canonical ID, protocol, optional budget, backend policy. Update CLI tuple producers at current lines 1016, 1100, 1119, 1401, and 1865. Six-field legacy tuples are allowed only for non-TSP/ATSP routing.

- [ ] **Replace `_evaluate_param_combo` registry access** with the gateway. Governed TSP/ATSP cannot reach direct `run_single_test` fallback. CVRP/CVRPTW remain unchanged.

- [ ] **Replace smart `_run_single_task` access** with the gateway. Menus select verified canonical IDs only; candidates/planned may be displayed as unavailable. Do not convert `ResultContractViolation` to a persistable success/error result.

- [ ] **Run and commit.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_legacy_algorithm_migrations.py academic_benchmark\tests\test_smart_benchmark_preflight.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task9 --tb=short
git add academic_benchmark\cli_engine.py academic_benchmark\engine_core.py academic_benchmark\smart_benchmark.py academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_legacy_algorithm_migrations.py academic_benchmark\tests\test_smart_benchmark_preflight.py
git commit -m "feat(academic): enforce preflight across benchmark entrypoints"
~~~

### Task 10: Close Gate C1

**Files:** Modify catalog/evidence/production/profile tests and check this plan’s boxes.

- [ ] **Add drift tests:** every VERIFIED ID is registered; every claim has a real named evidence function; implemented candidates have canonical executors; planned IDs do not.

- [ ] **Strengthen production isolation:** assert 38 exact keys for both production mappings and use a subprocess to prove importing `optimizer_api.strategies` does not import capabilities.

- [ ] **Run focused gate.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_resolution.py academic_benchmark\tests\test_algorithm_problem_validation.py academic_benchmark\tests\test_algorithm_preflight.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_algorithm_execution_gateway.py academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_smart_benchmark_preflight.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_bildiri_study_profile.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-focused --tb=short
~~~

No promoted evidence case may skip.

- [ ] **Run Package A/B/JIT regression.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_numba_jit_parity.py academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_fair_comparison_protocol.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py academic_benchmark\tests\test_native_termination_protocol.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_archive_manifest.py academic_benchmark\tests\test_yaem_quarantine_boundary.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-regression --tb=short
~~~

- [ ] **Run full local suite and hygiene.**

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests uniride_core\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-full --tb=short
git diff --check
git status --short --branch
~~~

If the full JIT suite exceeds local capacity, report the exact completed focused results and blocker; never claim a pass.

- [ ] **Commit final gate.**

~~~powershell
git add academic_benchmark\tests docs\superpowers\plans\2026-07-28-academic-capability-catalog-preflight.md
git commit -m "test(academic): close Package C1 capability gate"
~~~

Do not push, merge, or mark the Package B draft PR ready until the user reviews the completed C1 verification package.

