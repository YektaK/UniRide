# Package B Compute Admission, Budget, and Alias Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect production optimization work, canonicalize algorithm execution, enforce the versioned conservative compute profile, and return truthful policy metadata without changing solver mathematics or academic protocols.

**Architecture:** FastAPI admits heavy requests through the existing internal-key boundary, resolves every submitted name through a canonical factory, and applies an immutable request-local policy before solver execution. `/compare` deduplicates canonical runs and uses a two-worker executor with one monotonic soft response deadline. Next.js remains the authenticated user boundary and injects the internal key only from server code.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, `concurrent.futures`, pytest, Next.js 16, TypeScript, Vitest.

## Global Constraints

- Start from a clean isolated worktree whose merge base is the then-current `origin/WIP`; never work in the rescue checkout.
- Approved profile identifier: `production-conservative-v1`.
- Hard ceilings: 250 students, 50 vehicles, 6 canonical compare algorithms, 2 workers, 120-second response deadline, 60-second supported solver runtime, 2,000 iterations, 250 population/swarm members, and 2-second local-search sublimit.
- Server overrides may lower but never raise hard ceilings. Invalid overrides fail at startup.
- Protect `POST /api/v1/optimize`, `POST /api/v1/compare`, and `POST /api/v1/vehicle-calculator` with `X-Internal-API-Key`.
- Keep `/health`, `/api/v1/strategies`, `/api/v1/extract-time-windows`, and `/api/v1/schedule-to-students` public.
- `UNIRIDE_DISABLE_AUTH=1` is local/test-only and is a startup error when `APP_ENV=production`.
- Next.js reads `OPTIMIZER_INTERNAL_API_KEY`; FastAPI continues to validate the matching `INTERNAL_API_KEY`. Neither value may be logged, returned, or exposed through a `NEXT_PUBLIC_*` variable.
- Alias keys remain accepted, but responses and rankings use canonical names and each canonical run receives a fresh strategy instance.
- The v1 omitted/default comparison remains exactly six algorithms; configuring `UNIRIDE_COMPUTE_MAX_ALGORITHMS` below six is a startup error, while callers may explicitly request fewer.
- Request values above policy fail; they are never silently clamped. Registered or promoted defaults may be reduced on a request-local copy to meet the profile.
- Package B provides `soft_response_deadline`, not hard solver cancellation. Do not add processes, durable jobs, rate limiting, or cooperative cancellation.
- Package A feasibility certification remains the final success and ranking gate.
- Do not alter academic DTO bounds, fairness accounting, solver formulas, registry exposure, dependencies, databases, generated evidence, or frontend UX.
- Use RED-GREEN TDD, one reviewable commit per task, `git diff --check` before every commit, and explicit user authorization before merge or push.
- Preserve both package and legacy direct-module startup modes; every new intra-`optimizer_api` import must follow the repository's `try: optimizer_api... except ModuleNotFoundError: local...` compatibility pattern until direct mode is retired separately.

## File Structure

- Create `optimizer_api/compute_policy.py`: frozen profile, environment parsing, exhaustive tuning validation, per-strategy applicability, request-local budget application, and metadata construction.
- Create `optimizer_api/strategies/canonical.py`: normalized alias resolution, availability, canonical deduplication, and fresh factory access.
- Modify `optimizer_api/runtime_config.py`: one startup validator for production auth and compute-profile configuration.
- Modify `optimizer_api/auth.py`: shared local opt-out and constant-time key comparison.
- Modify `optimizer_api/main.py`: invoke startup validation once.
- Modify `optimizer_api/models/schemas.py`: additive typed policy DTOs and admission validators.
- Modify `optimizer_api/routers/optimization.py`: protected endpoints, canonical execution, bounded comparison, ranking, and metadata attachment.
- Modify `optimizer_api/strategies/ortools_cvrp.py`: expose its existing native runtime as a request-local constructor value.
- Modify `optimizer_api/strategies/pyvrp_strategy.py`: expose the existing native runtime on fresh strategy instances.
- Modify `uniride_core/algorithms/string_exact_tsp.py`: reject oversize exact searches instead of truncating.
- Create `src/lib/optimizer-server.ts`: server-only authenticated FastAPI transport.
- Create `src/services/optimizer-types.ts`: browser-safe shared response/request types.
- Modify `src/services/optimizer-service.ts`: use server transport and preserve new metadata.
- Modify the three principal BFF routes, sandbox route, and legacy DouBus caller to preserve the server-only boundary.
- Add focused Python and TypeScript tests named in each task.
- Update `README.md`, `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, and `WORKLOG.md` only after all code gates pass.

## Suggested Agent Routing

| Task | Preferred order | Required independent gate |
|---|---|---|
| 1. Runtime/auth | GPT-5.6 Terra, GPT-5.6 Luna, Big Pickle | Terra or current orchestrator verifies security behavior |
| 2. Profile/DTO | Big Pickle, GPT-5.6 Terra, GPT-5.6 Luna | Terra verifies typed validation and startup semantics |
| 3. Canonical resolver | GPT-5.6 Terra, GPT-5.6 Luna, Big Pickle | Luna can run exhaustive mechanical alias checks |
| 4. Policy application | Big Pickle, GPT-5.6 Terra, DeepSeek V4Pro | Terra verifies every applicability row |
| 5. Compare orchestration | GPT-5.6 Terra, DeepSeek V4Pro, Big Pickle | current orchestrator performs concurrency/ranking review |
| 6. Exact TSP repair | DeepSeek V4Pro, GPT-5.6 Terra, Big Pickle | solver-specific tests plus current orchestrator review |
| 7. Next.js boundary | GPT-5.6 Luna, GPT-5.6 Terra, Big Pickle | Terra verifies server/client import boundary |
| 8. Docs/final gates | GPT-5.6 Luna, GPT-5.6 Terra | Terra verifies claims against final test output |

Do not give one agent the whole package. Each task is a separate context and review boundary.

---

### Task 1: Fail-Closed Production Compute Authentication

**Files:**
- Modify: `optimizer_api/runtime_config.py:1-43`
- Modify: `optimizer_api/auth.py:1-22`
- Modify: `optimizer_api/main.py:20-43`
- Modify: `optimizer_api/routers/optimization.py:7-20`
- Modify: `optimizer_api/tests/test_phase0_auth_guard.py:79-105`
- Create: `optimizer_api/tests/test_package_b_compute_auth.py`

**Interfaces:**
- Produces: `validate_runtime_configuration() -> None` and the existing `require_internal_api_key(...) -> None` with production-safe opt-out behavior.
- Consumes: existing `INTERNAL_API_KEY`, `APP_ENV`, and `UNIRIDE_DISABLE_AUTH` environment variables.

- [ ] **Step 1: Write the failing endpoint-boundary tests**

Create `optimizer_api/tests/test_package_b_compute_auth.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from optimizer_api.routers import optimization, strategies, utils


OPTIMIZE = {
    "algorithm": "does-not-exist",
    "students": [],
    "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
}
COMPARE = {
    "algorithms": ["does-not-exist"],
    "students": [],
    "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
}


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(optimization.router)
    app.include_router(strategies.router)
    app.include_router(utils.router)
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/optimize", OPTIMIZE),
        ("/api/v1/compare", COMPARE),
        ("/api/v1/vehicle-calculator", OPTIMIZE),
    ],
)
def test_heavy_routes_require_internal_key(monkeypatch, path, payload):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("INTERNAL_API_KEY", "expected")

    missing = _client().post(path, json=payload)
    wrong = _client().post(path, json=payload, headers={"X-Internal-API-Key": "wrong"})
    allowed = _client().post(path, json=payload, headers={"X-Internal-API-Key": "expected"})

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert missing.json() == wrong.json() == {"detail": "Forbidden"}
    assert allowed.status_code == 400
    assert "expected" not in allowed.text


def test_lightweight_routes_remain_public(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("INTERNAL_API_KEY", "expected")
    client = _client()

    assert client.get("/api/v1/strategies").status_code == 200
    response = client.post(
        "/api/v1/extract-time-windows",
        params={"direction": "pickup", "target_day": "monday"},
        json=[],
    )
    assert response.status_code == 200
```

In `test_phase0_auth_guard.py`, replace the old production-opt-out expectation with:

```python
def test_g3_production_rejects_explicit_disable(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(SystemExit, match="UNIRIDE_DISABLE_AUTH"):
        runtime_config.validate_runtime_configuration()
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -m pytest optimizer_api/tests/test_package_b_compute_auth.py optimizer_api/tests/test_phase0_auth_guard.py -q -p no:cacheprovider --tb=short
```

Expected: heavy routes are not protected and `validate_runtime_configuration` does not exist.

- [ ] **Step 3: Implement the smallest shared runtime/auth boundary**

Add to `runtime_config.py`:

```python
def app_env() -> str:
    return os.getenv("APP_ENV", "development").strip().lower()


def internal_api_key() -> str | None:
    value = os.getenv("INTERNAL_API_KEY")
    return value if value else None


def validate_runtime_configuration() -> None:
    disabled = internal_auth_disabled()
    if disabled and app_env() == "production":
        raise SystemExit("UNIRIDE_DISABLE_AUTH=1 is forbidden when APP_ENV=production")
    if not disabled and internal_api_key() is None:
        raise SystemExit(
            "INTERNAL_API_KEY is not set; configure it or use "
            "UNIRIDE_DISABLE_AUTH=1 outside production"
        )
```

Replace the body of `require_internal_api_key` in `auth.py`:

```python
try:
    from optimizer_api.runtime_config import internal_api_key, internal_auth_disabled
except ModuleNotFoundError:  # direct-module compatibility
    from runtime_config import internal_api_key, internal_auth_disabled


async def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if internal_auth_disabled():
        return
    expected = internal_api_key()
    if expected is None or x_internal_api_key is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
```

In `optimization.py`, add `Depends` and protect the router rather than repeating dependencies per endpoint:

```python
from fastapi import APIRouter, Depends, HTTPException
try:
    from optimizer_api.auth import require_internal_api_key
except ModuleNotFoundError:  # direct-module compatibility
    from auth import require_internal_api_key

router = APIRouter(
    prefix="/api/v1",
    tags=["Optimization"],
    dependencies=[Depends(require_internal_api_key)],
)
```

In `main.py`, import and invoke the shared validator after `load_dotenv`:

```python
try:
    from optimizer_api.runtime_config import (
        optimizer_host,
        validate_bind_host,
        validate_runtime_configuration,
    )
except ModuleNotFoundError:  # direct `python optimizer_api/main.py` compatibility
    from runtime_config import optimizer_host, validate_bind_host, validate_runtime_configuration

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
validate_runtime_configuration()
```

Delete the old inline key guard from `main.py`; there must be one startup authority.

- [ ] **Step 4: Run focused and existing containment tests**

Run:

```powershell
python -m pytest optimizer_api/tests/test_package_b_compute_auth.py optimizer_api/tests/test_phase0_auth_guard.py optimizer_api/tests/test_phase0_containment.py -q -p no:cacheprovider --tb=short
```

Expected: all pass; auth failures contain only `Forbidden`.

- [ ] **Step 5: Commit**

```powershell
git add optimizer_api/runtime_config.py optimizer_api/auth.py optimizer_api/main.py optimizer_api/routers/optimization.py optimizer_api/tests/test_phase0_auth_guard.py optimizer_api/tests/test_package_b_compute_auth.py
git diff --cached --check
git commit -m "feat(api): protect production compute routes"
```

### Task 2: Immutable Profile, Admission Validation, and Typed Metadata

**Files:**
- Create: `optimizer_api/compute_policy.py`
- Modify: `optimizer_api/runtime_config.py`
- Modify: `optimizer_api/models/schemas.py:201-223,349-411`
- Create: `optimizer_api/tests/test_package_b_compute_policy.py`

**Interfaces:**
- Produces: frozen `ComputePolicy`, `load_compute_policy()`, `validate_tuning_dict()`, `AppliedComputePolicyInfo`, and optional `applied_policy` response fields.
- Consumes: the nine approved `UNIRIDE_COMPUTE_*` variables.

- [ ] **Step 1: Write RED profile and DTO tests**

Create tests covering exact defaults, lower overrides for each reducible limit, rejection of `UNIRIDE_COMPUTE_MAX_ALGORITHMS=5`, rejection of zero/non-integer/above-ceiling values, 251 students, 51 vehicles, seven algorithms, unknown tuning keys, booleans passed as integers, NaN/Infinity, and additive response compatibility. Core examples:

```python
import pytest
from pydantic import ValidationError

from optimizer_api.compute_policy import HARD_CEILINGS, load_compute_policy
from optimizer_api.models.schemas import (
    AppliedComputePolicyInfo,
    CompareRequest,
    LocationNode,
    OptimizationRequest,
    OptimizationResponse,
)


def test_profile_defaults_and_lower_override():
    assert HARD_CEILINGS.max_students == 250
    policy = load_compute_policy({"UNIRIDE_COMPUTE_MAX_STUDENTS": "125"})
    assert policy.max_students == 125
    assert policy.profile_id == "production-conservative-v1"


@pytest.mark.parametrize("value", ["0", "251", "1.5", "yes"])
def test_student_override_must_be_positive_integer_at_or_below_ceiling(value):
    with pytest.raises(ValueError, match="UNIRIDE_COMPUTE_MAX_STUDENTS"):
        load_compute_policy({"UNIRIDE_COMPUTE_MAX_STUDENTS": value})


def test_request_rejects_unknown_and_boolean_budget_values(monkeypatch):
    monkeypatch.setenv("UNIRIDE_COMPUTE_MAX_STUDENTS", "250")
    base = {"algorithm": "ga", "students": [], "depot": {"id": "D", "lat": 0, "lng": 0}}
    with pytest.raises(ValidationError):
        OptimizationRequest(**base, ga_config={"generations": 5})
    with pytest.raises(ValidationError):
        OptimizationRequest(**base, ga_config={"max_iterations": True})


def test_policy_metadata_is_additive_and_typed():
    response = OptimizationResponse(algorithm_used="greedy", success=True, routes=[])
    assert response.applied_policy is None
    metadata = AppliedComputePolicyInfo.model_validate({
        "profile_id": "production-conservative-v1",
        "algorithm_requested": "nearest_neighbor",
        "algorithm_canonical": "greedy",
        "student_count": 0,
        "vehicle_count": 0,
        "cancellation_mode": "none",
        "limits": {},
    })
    assert metadata.algorithm_canonical == "greedy"
```

- [ ] **Step 2: Run the focused file and verify RED**

```powershell
python -m pytest optimizer_api/tests/test_package_b_compute_policy.py -q -p no:cacheprovider --tb=short
```

Expected: missing module/models/validators.

- [ ] **Step 3: Implement the frozen profile, strict environment parser, and startup hook**

Create `compute_policy.py` with this public shape:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import os
from collections.abc import Mapping
from typing import Any

PROFILE_ID = "production-conservative-v1"
DEFAULT_COMPARE_ALGORITHMS = (
    "greedy", "two_opt", "genetic_algorithm", "ga_split", "pso_split", "ortools_cvrp",
)


@dataclass(frozen=True)
class ComputePolicy:
    profile_id: str = PROFILE_ID
    max_students: int = 250
    max_vehicles: int = 50
    max_algorithms: int = 6
    max_workers: int = 2
    deadline_seconds: int = 120
    solver_seconds: int = 60
    max_iterations: int = 2_000
    max_population: int = 250
    local_search_seconds: int = 2


HARD_CEILINGS = ComputePolicy()
ENV_FIELDS = {
    "UNIRIDE_COMPUTE_MAX_STUDENTS": "max_students",
    "UNIRIDE_COMPUTE_MAX_VEHICLES": "max_vehicles",
    "UNIRIDE_COMPUTE_MAX_ALGORITHMS": "max_algorithms",
    "UNIRIDE_COMPUTE_MAX_WORKERS": "max_workers",
    "UNIRIDE_COMPUTE_DEADLINE_SECONDS": "deadline_seconds",
    "UNIRIDE_COMPUTE_SOLVER_SECONDS": "solver_seconds",
    "UNIRIDE_COMPUTE_MAX_ITERATIONS": "max_iterations",
    "UNIRIDE_COMPUTE_MAX_POPULATION": "max_population",
    "UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS": "local_search_seconds",
}


def load_compute_policy(environ: Mapping[str, str] | None = None) -> ComputePolicy:
    source = os.environ if environ is None else environ
    changes: dict[str, int] = {}
    for env_name, field_name in ENV_FIELDS.items():
        raw = source.get(env_name)
        if raw is None:
            continue
        if not raw.isdecimal() or int(raw) < 1:
            raise ValueError(f"{env_name} must be a positive integer")
        value = int(raw)
        ceiling = getattr(HARD_CEILINGS, field_name)
        if value > ceiling:
            raise ValueError(f"{env_name} cannot exceed hard ceiling {ceiling}")
        changes[field_name] = value
    if changes.get("max_algorithms", HARD_CEILINGS.max_algorithms) < len(DEFAULT_COMPARE_ALGORITHMS):
        raise ValueError(
            "UNIRIDE_COMPUTE_MAX_ALGORITHMS cannot be lower than the six-algorithm default set"
        )
    return replace(HARD_CEILINGS, **changes)
```

After `compute_policy.py` exists, append policy validation to the Task 1 startup authority in `runtime_config.py` while preserving both import modes:

```python
# final lines of validate_runtime_configuration()
try:
    from optimizer_api.compute_policy import load_compute_policy
except ModuleNotFoundError:  # direct `python optimizer_api/main.py` compatibility
    from compute_policy import load_compute_policy
load_compute_policy()
```

Define the six exhaustive public allowlists exactly once in `compute_policy.py`:

```python
TUNING_ALLOWLISTS = {
    "ga_config": frozenset({"crossover_rate", "diversify_threshold", "elite_count", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "mutation_rate", "population_size", "seed", "tournament_size"}),
    "pso_config": frozenset({"cognitive_weight", "inertia_min", "inertia_weight", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "max_velocity_size", "reinit_interval", "seed", "social_weight", "swarm_size", "velocity_clamp"}),
    "gwo_config": frozenset({"exploration_rate", "initial_a", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "population_size", "seed"}),
    "hho_config": frozenset({"initial_energy", "jump_probability", "levy_flight_scale", "local_search_interval", "local_search_type", "max_iterations", "max_no_improvement", "population_size", "seed"}),
    "two_opt_config": frozenset({"first_improvement", "max_iterations", "multi_start", "num_starts", "seed"}),
    "sota_config": frozenset({"acceptance_types", "crossover_rate", "delta_threshold", "destroy_ops_pool", "diversity_check_interval", "diversity_injection_rate", "diversity_threshold", "entropy_check_interval", "entropy_threshold", "gamma", "genome_injection_rate", "genome_population_size", "h_end", "h_start", "injection_rate", "lahc_history", "learn_period", "ls_intensity_compress", "ls_intensity_constructive", "ls_intensity_destructive", "ls_intensity_moderate", "ls_intensity_normal", "ls_time_limit", "max_iterations", "meta_evolution_interval", "mutation_rate", "n_edges_aggressive", "n_edges_normal", "p_best", "p_gbest", "population_size", "pulse_injection_rate", "remove_ratio", "remove_ratio_range", "repair_ops_pool", "sa_cooling_rate", "sa_end_temp", "sa_start_temp_factor", "seed", "segment_size", "theta_base", "three_opt_window", "time_limit", "tournament_k", "tournament_size"}),
}
```

Implement the validator with exhaustive categories; the final `else` is deliberately fail-closed:

```python
from numbers import Real

BOOL_KEYS = frozenset({"first_improvement", "multi_start"})
ITERATION_KEYS = frozenset({"max_iterations", "max_no_improvement", "diversify_threshold", "local_search_interval", "reinit_interval", "entropy_check_interval", "diversity_check_interval", "learn_period", "meta_evolution_interval"})
ALLOCATION_KEYS = frozenset({"population_size", "swarm_size", "genome_population_size", "elite_count", "tournament_size", "tournament_k", "num_starts", "lahc_history"})
STRUCTURAL_KEYS = frozenset({"max_velocity_size", "three_opt_window", "segment_size", "n_edges_normal", "n_edges_aggressive"})
UNIT_INTERVAL_KEYS = frozenset({"crossover_rate", "mutation_rate", "exploration_rate", "jump_probability", "velocity_clamp", "diversity_injection_rate", "diversity_threshold", "entropy_threshold", "genome_injection_rate", "injection_rate", "p_best", "p_gbest", "pulse_injection_rate", "remove_ratio", "inertia_min", "inertia_weight", "h_start", "h_end", "gamma", "delta_threshold", "theta_base"})
POSITIVE_REAL_KEYS = frozenset({"cognitive_weight", "social_weight", "initial_a", "initial_energy", "levy_flight_scale", "sa_start_temp_factor", "sa_end_temp"})
INTENSITY_KEYS = frozenset({"ls_intensity_compress", "ls_intensity_constructive", "ls_intensity_destructive", "ls_intensity_moderate", "ls_intensity_normal"})


def _finite_real(key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{key} must be a finite number")
    return float(value)


def _positive_int(key: str, value: Any, ceiling: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > ceiling:
        raise ValueError(f"{key} must be an integer in [1, {ceiling}]")
    return value


def _operator_list(key: str, value: Any, allowed: frozenset[str]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a non-empty string list")
    normalized = tuple(value)
    if not set(normalized) <= allowed:
        raise ValueError(f"{key} contains an unsupported value")
    return normalized


def validate_tuning_dict(
    field_name: str,
    value: Mapping[str, Any],
    policy: ComputePolicy,
    student_count: int,
) -> dict[str, Any]:
    if student_count < 0 or student_count > policy.max_students:
        raise ValueError("student_count is outside the effective policy")
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    unknown = set(value) - TUNING_ALLOWLISTS[field_name]
    if unknown:
        raise ValueError(f"{field_name} contains unsupported keys: {sorted(unknown)}")
    result = dict(value)
    for key, item in result.items():
        if key in BOOL_KEYS:
            if not isinstance(item, bool):
                raise ValueError(f"{key} must be a boolean")
        elif key == "seed":
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError("seed must be an integer")
        elif key in ITERATION_KEYS:
            result[key] = _positive_int(key, item, policy.max_iterations)
        elif key in ALLOCATION_KEYS:
            result[key] = _positive_int(key, item, policy.max_population)
        elif key in STRUCTURAL_KEYS:
            result[key] = _positive_int(key, item, min(policy.max_students, policy.max_population))
        elif key == "time_limit":
            number = _finite_real(key, item)
            if not 0 < number <= policy.solver_seconds:
                raise ValueError(f"time_limit must be in (0, {policy.solver_seconds}]")
            result[key] = number
        elif key == "ls_time_limit":
            number = _finite_real(key, item)
            if not 0 < number <= policy.local_search_seconds:
                raise ValueError(f"ls_time_limit must be in (0, {policy.local_search_seconds}]")
            result[key] = number
        elif key in UNIT_INTERVAL_KEYS:
            number = _finite_real(key, item)
            if not 0 <= number <= 1:
                raise ValueError(f"{key} must be in [0, 1]")
            result[key] = number
        elif key in POSITIVE_REAL_KEYS:
            number = _finite_real(key, item)
            if number <= 0:
                raise ValueError(f"{key} must be positive")
            result[key] = number
        elif key == "sa_cooling_rate":
            number = _finite_real(key, item)
            if not 0 < number < 1:
                raise ValueError("sa_cooling_rate must be in (0, 1)")
            result[key] = number
        elif key == "local_search_type":
            if item not in {"none", "two_opt", "three_opt", "or_opt", "hybrid"}:
                raise ValueError("local_search_type is unsupported")
        elif key in INTENSITY_KEYS:
            if item not in {"light", "moderate"}:
                raise ValueError(f"{key} is unsupported")
        elif key == "destroy_ops_pool":
            result[key] = _operator_list(key, item, frozenset({"random", "worst", "shaw", "related"}))
        elif key == "repair_ops_pool":
            result[key] = _operator_list(key, item, frozenset({"greedy", "regret2", "regret3"}))
        elif key == "acceptance_types":
            result[key] = _operator_list(key, item, frozenset({"sa", "lahc"}))
        elif key == "remove_ratio_range":
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("remove_ratio_range must contain two numbers")
            low, high = (_finite_real(key, part) for part in item)
            if not 0 <= low <= high <= 1:
                raise ValueError("remove_ratio_range must satisfy 0 <= low <= high <= 1")
            result[key] = (low, high)
        else:
            raise ValueError(f"{key} has no production validation rule")
    if "h_start" in result and "h_end" in result and result["h_end"] > result["h_start"]:
        raise ValueError("h_end cannot exceed h_start")
    if "inertia_min" in result and "inertia_weight" in result and result["inertia_min"] > result["inertia_weight"]:
        raise ValueError("inertia_min cannot exceed inertia_weight")
    if "n_edges_normal" in result and "n_edges_aggressive" in result and result["n_edges_normal"] > result["n_edges_aggressive"]:
        raise ValueError("n_edges_normal cannot exceed n_edges_aggressive")
    population = result.get("population_size", result.get("swarm_size", policy.max_population))
    for dependent in ("elite_count", "tournament_size", "tournament_k", "genome_population_size"):
        if dependent in result and result[dependent] > population:
            raise ValueError(f"{dependent} cannot exceed effective population")
    return result
```

- [ ] **Step 4: Add typed response metadata and request admission validators**

Add these models before `OptimizationResponse` in `schemas.py`:

```python
class PolicyValueSource(str, Enum):
    PROFILE_DEFAULT = "profile_default"
    SERVER_OVERRIDE = "server_override"
    CALLER = "caller"
    STRATEGY_DEFAULT = "strategy_default"


class AppliedPolicyLimitInfo(BaseModel):
    value: float
    source: PolicyValueSource
    enforcement: str


class AppliedComputePolicyInfo(BaseModel):
    profile_id: str
    algorithm_requested: Optional[str] = None
    algorithm_canonical: Optional[str] = None
    student_count: int = 0
    vehicle_count: int = 0
    cancellation_mode: Literal["none", "soft_response_deadline"] = "none"
    limits: Dict[str, AppliedPolicyLimitInfo] = Field(default_factory=dict)
```

Add these backward-compatible fields:

```python
# OptimizationResponse
algorithm_requested: Optional[str] = None
applied_policy: Optional[AppliedComputePolicyInfo] = None

# AlgorithmResult
algorithm_requested: Optional[str] = None
applied_policy: Optional[AppliedComputePolicyInfo] = None

# CompareResponse
applied_policy: Optional[AppliedComputePolicyInfo] = None
```

Add separate after-model validators (do not replace `OptimizationRequest.validate_students`):

```python
# OptimizationRequest
@model_validator(mode="after")
def validate_compute_admission(self) -> "OptimizationRequest":
    try:
        from optimizer_api.compute_policy import (
            TUNING_ALLOWLISTS,
            load_compute_policy,
            validate_tuning_dict,
        )
    except ModuleNotFoundError:  # direct-module compatibility
        from compute_policy import TUNING_ALLOWLISTS, load_compute_policy, validate_tuning_dict

    policy = load_compute_policy()
    if len(self.students) > policy.max_students:
        raise ValueError(f"students cannot exceed {policy.max_students}")
    if self.vehicles is not None and len(self.vehicles) > policy.max_vehicles:
        raise ValueError(f"vehicles cannot exceed {policy.max_vehicles}")
    if self.local_search_type not in {None, "none", "two_opt", "three_opt", "or_opt", "hybrid"}:
        raise ValueError("local_search_type is unsupported")
    for field_name in TUNING_ALLOWLISTS:
        supplied = getattr(self, field_name)
        if supplied is not None:
            setattr(
                self,
                field_name,
                validate_tuning_dict(field_name, supplied, policy, len(self.students)),
            )
    return self


# CompareRequest
@model_validator(mode="after")
def validate_compute_admission(self) -> "CompareRequest":
    try:
        from optimizer_api.compute_policy import load_compute_policy
    except ModuleNotFoundError:  # direct-module compatibility
        from compute_policy import load_compute_policy

    policy = load_compute_policy()
    if len(self.students) > policy.max_students:
        raise ValueError(f"students cannot exceed {policy.max_students}")
    if self.algorithms is not None and len(self.algorithms) > policy.max_algorithms:
        raise ValueError(f"algorithms cannot exceed {policy.max_algorithms}")
    return self
```

Keep zero-student requests valid for backward compatibility. The DTO’s raw algorithm-list bound intentionally rejects alias floods early; Task 5 separately enforces the authoritative canonical deduplicated bound after resolution.

- [ ] **Step 5: Run focused policy tests**

```powershell
python -m pytest optimizer_api/tests/test_package_b_compute_policy.py optimizer_api/tests/test_phase0_auth_guard.py optimizer_api/tests/test_manifest_contracts.py -q -p no:cacheprovider --tb=short
```

Expected: all pass; no existing response field is removed.

- [ ] **Step 6: Commit**

```powershell
git add optimizer_api/compute_policy.py optimizer_api/runtime_config.py optimizer_api/models/schemas.py optimizer_api/tests/test_package_b_compute_policy.py
git diff --cached --check
git commit -m "feat(api): add conservative compute profile"
```

### Task 3: Canonical Alias Resolver and Fresh Strategy Factories

**Files:**
- Create: `optimizer_api/strategies/canonical.py`
- Create: `optimizer_api/tests/test_package_b_canonical_resolution.py`
- Verify unchanged: `optimizer_api/strategies/__init__.py`
- Verify unchanged: `academic_benchmark/tests/test_production_registry_snapshot.py`

**Interfaces:**
- Produces: `ResolvedStrategy`, `resolve_strategy(key)`, and `resolve_unique_strategies(keys)`.
- Consumes: existing `STRATEGY_REGISTRY` and `STRATEGY_FACTORIES` without changing their key sets.

- [ ] **Step 1: Write exhaustive RED alias tests**

```python
import pytest

from optimizer_api.strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY
from optimizer_api.strategies.canonical import (
    StrategyUnavailableError,
    UnknownStrategyError,
    resolve_strategy,
    resolve_unique_strategies,
)


def test_every_registry_key_resolves_to_existing_canonical_identity():
    assert set(STRATEGY_REGISTRY) == set(STRATEGY_FACTORIES)
    for key, singleton in STRATEGY_REGISTRY.items():
        resolution = resolve_strategy(key, require_available=False)
        assert resolution.requested == key.lower()
        if singleton is not None:
            assert resolution.canonical == singleton.name
            assert resolution.create().name == singleton.name
            assert resolution.create() is not resolution.create()


def test_aliases_deduplicate_in_first_requested_order():
    resolved = resolve_unique_strategies(["ga", "genetic_algorithm", "nearest_neighbor", "greedy"])
    assert [item.canonical for item in resolved] == ["genetic_algorithm", "greedy"]
    assert resolved[0].requested_aliases == ("ga", "genetic_algorithm")


def test_unknown_and_unavailable_are_distinct(monkeypatch):
    with pytest.raises(UnknownStrategyError):
        resolve_strategy("missing")
    monkeypatch.setitem(STRATEGY_FACTORIES, "pyvrp", None)
    with pytest.raises(StrategyUnavailableError):
        resolve_strategy("pyvrp")
```

- [ ] **Step 2: Run and verify RED**

```powershell
python -m pytest optimizer_api/tests/test_package_b_canonical_resolution.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 3: Implement the resolver**

Create `canonical.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

try:
    from optimizer_api.strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY
    from optimizer_api.strategies.base_strategy import BaseRoutingStrategy
except ModuleNotFoundError:  # direct-module compatibility
    from strategies import STRATEGY_FACTORIES, STRATEGY_REGISTRY
    from strategies.base_strategy import BaseRoutingStrategy

_OPTIONAL_CANONICAL = {
    "pyvrp": "pyvrp", "hgs": "pyvrp", "pyvrp_alt": "pyvrp_alt",
    "vroom": "vroom", "vroom_fallback": "vroom_fallback",
}


class UnknownStrategyError(ValueError):
    pass


class StrategyUnavailableError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedStrategy:
    requested: str
    canonical: str
    factory: Callable[[], BaseRoutingStrategy] | None
    requested_aliases: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.factory is not None

    def create(self) -> BaseRoutingStrategy:
        if self.factory is None:
            raise StrategyUnavailableError(f"Algorithm '{self.requested}' is unavailable")
        return self.factory()


def resolve_strategy(key: str, *, require_available: bool = True) -> ResolvedStrategy:
    requested = key.strip().lower()
    if requested not in STRATEGY_FACTORIES:
        raise UnknownStrategyError(f"Unknown algorithm '{requested}'")
    singleton = STRATEGY_REGISTRY[requested]
    canonical = singleton.name if singleton is not None else _OPTIONAL_CANONICAL[requested]
    result = ResolvedStrategy(requested, canonical, STRATEGY_FACTORIES[requested], (requested,))
    if require_available and not result.available:
        raise StrategyUnavailableError(f"Algorithm '{requested}' is unavailable")
    return result


def resolve_unique_strategies(keys: list[str] | tuple[str, ...]) -> list[ResolvedStrategy]:
    unique: dict[str, ResolvedStrategy] = {}
    for key in keys:
        item = resolve_strategy(key)
        previous = unique.get(item.canonical)
        if previous is None:
            unique[item.canonical] = item
        else:
            unique[item.canonical] = replace(
                previous,
                requested_aliases=previous.requested_aliases + (item.requested,),
            )
    return list(unique.values())
```

Do not edit registry mappings. If a test reveals a canonical name not covered for an unavailable optional strategy, add only that explicit name to `_OPTIONAL_CANONICAL`.

- [ ] **Step 4: Run resolver and registry snapshot gates**

```powershell
python -m pytest optimizer_api/tests/test_package_b_canonical_resolution.py optimizer_api/tests/test_strategy_registry_minor1.py academic_benchmark/tests/test_production_registry_snapshot.py -q -p no:cacheprovider --tb=short
```

Expected: all pass and production registry keys remain identical.

- [ ] **Step 5: Commit**

```powershell
git add optimizer_api/strategies/canonical.py optimizer_api/tests/test_package_b_canonical_resolution.py
git diff --cached --check
git commit -m "feat(api): canonicalize strategy aliases"
```

### Task 4: Evidence-Gated Tuning Applicability and Request-Local Budgeting

**Files:**
- Modify: `optimizer_api/compute_policy.py`
- Modify: `optimizer_api/strategies/ortools_cvrp.py`
- Modify: `optimizer_api/strategies/pyvrp_strategy.py`
- Create: `optimizer_api/tests/test_package_b_tuning_applicability.py`
- Create: `optimizer_api/tests/test_package_b_native_runtime.py`

**Interfaces:**
- Produces: `PolicyValidationError`, `apply_compute_policy(request, resolution, strategy, policy)` returning `(effective_request, metadata)`.
- Consumes: Task 2 profile/metadata and Task 3 `ResolvedStrategy`.

- [ ] **Step 1: Write the exhaustive table-driven RED gate**

Define `STANDARD_APPLICABLE_KEYS` in the test with the same sets shown in Step 3. Generate every `(canonical strategy, request field, allowlisted key)` combination. For a key in the applicable set, assert the policy returns a copied request containing the normalized sample value (`tuple(sample)` for operator/range lists). For every other combination, assert `PolicyValidationError` and no strategy call. Use this deterministic sample generator:

```python
def valid_sample(key: str):
    if key in {"first_improvement", "multi_start"}:
        return True
    if key == "local_search_type":
        return "two_opt"
    if key.startswith("ls_intensity_"):
        return "light"
    if key == "destroy_ops_pool":
        return ["random"]
    if key == "repair_ops_pool":
        return ["greedy"]
    if key == "acceptance_types":
        return ["sa"]
    if key == "remove_ratio_range":
        return [0.1, 0.2]
    if key == "seed":
        return 7
    if key in {"max_iterations", "max_no_improvement", "diversify_threshold", "local_search_interval", "reinit_interval", "entropy_check_interval", "diversity_check_interval", "learn_period", "meta_evolution_interval", "population_size", "swarm_size", "genome_population_size", "elite_count", "tournament_size", "tournament_k", "num_starts", "lahc_history", "max_velocity_size", "three_opt_window", "segment_size", "n_edges_normal", "n_edges_aggressive"}:
        return 1
    return 0.5
```

Also assert:

```python
effective, metadata = apply_compute_policy(request, resolution, resolution.create(), policy)
assert effective is not request
assert effective.ga_config is not request.ga_config
assert metadata.algorithm_requested == "ga"
assert metadata.algorithm_canonical == "genetic_algorithm"
```

- [ ] **Step 2: Run and verify RED**

```powershell
python -m pytest optimizer_api/tests/test_package_b_tuning_applicability.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 3: Add explicit live-consumption bindings**

Add to `compute_policy.py`:

```python
CONFIG_FIELD_BY_CANONICAL = {
    "genetic_algorithm": "ga_config", "ga_split": "ga_config", "ga_split_enhanced": "ga_config",
    "pso": "pso_config", "pso_split": "pso_config",
    "gwo": "gwo_config", "gwo_split": "gwo_config",
    "hho": "hho_config", "hho_split": "hho_config",
    "two_opt": "two_opt_config",
    "e2bso": "sota_config", "r2dma": "sota_config", "paoea": "sota_config",
}

STANDARD_APPLICABLE_KEYS = {
    "genetic_algorithm": frozenset({"population_size", "max_iterations", "max_no_improvement", "elite_count", "tournament_size", "crossover_rate", "mutation_rate", "seed"}),
    "ga_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "elite_count", "tournament_size", "crossover_rate", "mutation_rate", "local_search_interval", "local_search_type", "diversify_threshold", "seed"}),
    "ga_split_enhanced": frozenset({"population_size", "max_iterations", "max_no_improvement", "elite_count", "tournament_size", "crossover_rate", "mutation_rate", "local_search_interval", "local_search_type", "diversify_threshold", "seed"}),
    "pso": frozenset({"swarm_size", "max_iterations", "max_no_improvement", "max_velocity_size", "reinit_interval", "inertia_weight", "cognitive_weight", "social_weight", "seed"}),
    "pso_split": frozenset({"swarm_size", "max_iterations", "max_no_improvement", "local_search_interval", "local_search_type", "inertia_weight", "inertia_min", "cognitive_weight", "social_weight", "velocity_clamp", "seed"}),
    "gwo": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_a", "exploration_rate", "local_search_type", "seed"}),
    "gwo_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_a", "exploration_rate", "local_search_interval", "local_search_type", "seed"}),
    "hho": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_energy", "jump_probability", "local_search_type", "seed"}),
    "hho_split": frozenset({"population_size", "max_iterations", "max_no_improvement", "initial_energy", "jump_probability", "levy_flight_scale", "local_search_interval", "local_search_type", "seed"}),
    "two_opt": TUNING_ALLOWLISTS["two_opt_config"],
}
```

For SOTA strategies, derive applicability from the live dataclass rather than copying another list:

```python
from dataclasses import fields, is_dataclass


def applicable_keys(canonical: str, strategy: object) -> frozenset[str]:
    if canonical in STANDARD_APPLICABLE_KEYS:
        return STANDARD_APPLICABLE_KEYS[canonical]
    config = getattr(strategy, "_config", None)
    if canonical in {"e2bso", "r2dma", "paoea"} and is_dataclass(config):
        return frozenset(field.name for field in fields(config)) & TUNING_ALLOWLISTS["sota_config"]
    return frozenset()
```

- [ ] **Step 4: Implement request-local policy application**

Use these helpers and preserve this precedence:

```python
class PolicyValidationError(ValueError):
    pass


BUDGET_KEYS = ITERATION_KEYS | ALLOCATION_KEYS | STRUCTURAL_KEYS | {
    "time_limit", "ls_time_limit"
}


def _ceiling_for(key: str, policy: ComputePolicy) -> float:
    if key in ITERATION_KEYS:
        return policy.max_iterations
    if key in ALLOCATION_KEYS:
        return policy.max_population
    if key in STRUCTURAL_KEYS:
        return min(policy.max_students, policy.max_population)
    if key == "time_limit":
        return policy.solver_seconds
    if key == "ls_time_limit":
        return policy.local_search_seconds
    raise KeyError(key)


def _registered_config(strategy: object) -> dict[str, Any]:
    raw = getattr(strategy, "config", None)
    if raw is None:
        raw = getattr(strategy, "_config", None)
    if raw is None:
        return {}
    if is_dataclass(raw):
        return {field.name: getattr(raw, field.name) for field in fields(raw)}
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    if isinstance(raw, Mapping):
        return dict(raw)
    raise PolicyValidationError("strategy configuration is not inspectable")


def _source_for_default(key: str, registered: float, effective: float, policy: ComputePolicy):
    ceiling = _ceiling_for(key, policy)
    hard_ceiling = _ceiling_for(key, HARD_CEILINGS)
    if effective == registered:
        return PolicyValueSource.STRATEGY_DEFAULT
    if ceiling < hard_ceiling:
        return PolicyValueSource.SERVER_OVERRIDE
    return PolicyValueSource.PROFILE_DEFAULT
```

Implement `apply_compute_policy` in this order:

```python
def apply_compute_policy(request, resolution, strategy, policy: ComputePolicy):
    effective = request.model_copy(deep=True)
    canonical = resolution.canonical
    selected_field = CONFIG_FIELD_BY_CANONICAL.get(canonical)

    for field_name in TUNING_ALLOWLISTS:
        supplied = getattr(effective, field_name)
        if supplied and field_name != selected_field:
            raise PolicyValidationError(
                f"{field_name} does not apply to {canonical}"
            )

    limits: dict[str, AppliedPolicyLimitInfo] = {}
    if selected_field is not None:
        caller = dict(getattr(effective, selected_field) or {})
        allowed = applicable_keys(canonical, strategy)
        rejected = set(caller) - allowed
        if rejected:
            raise PolicyValidationError(
                f"{selected_field} keys not consumed by {canonical}: {sorted(rejected)}"
            )
        registered = _registered_config(strategy)
        merged = dict(caller)
        for key in sorted(allowed & BUDGET_KEYS):
            ceiling = _ceiling_for(key, policy)
            if key in caller:
                value = caller[key]  # already type/range checked by Task 2
                source = PolicyValueSource.CALLER
            elif key in registered:
                value = min(registered[key], ceiling)
                source = _source_for_default(key, registered[key], value, policy)
            else:
                continue
            merged[key] = value
            limits[key] = AppliedPolicyLimitInfo(
                value=value,
                source=source,
                enforcement=f"request-local {selected_field}.{key}",
            )
        validate_effective_relations(merged, policy)
        setattr(effective, selected_field, merged)

    if canonical in {"ortools_cvrp", "pyvrp", "pyvrp_alt"}:
        registered_seconds = strategy.time_limit_seconds
        strategy.time_limit_seconds = min(registered_seconds, policy.solver_seconds)
        limits["solver_seconds"] = AppliedPolicyLimitInfo(
            value=strategy.time_limit_seconds,
            source=_source_for_default(
                "time_limit", registered_seconds, strategy.time_limit_seconds, policy
            ),
            enforcement="request-local native solver limit",
        )

    metadata = AppliedComputePolicyInfo(
        profile_id=policy.profile_id,
        algorithm_requested=resolution.requested,
        algorithm_canonical=canonical,
        student_count=len(effective.students),
        vehicle_count=len(effective.vehicles or []),
        cancellation_mode="none",
        limits=limits,
    )
    return effective, metadata
```

`validate_effective_relations` rechecks `elite_count`, `tournament_size`, `tournament_k`, and `genome_population_size` against the effective population after registered defaults are merged. It also rechecks `h_end <= h_start`, `inertia_min <= inertia_weight`, and `n_edges_normal <= n_edges_aggressive` against the effective values, not merely caller-provided pairs.

Expose the two existing 30-second native limits on fresh strategy instances; do not add a global mutable limit:

```python
# optimizer_api/strategies/ortools_cvrp.py
class ORToolsCVRPStrategy(BaseRoutingStrategy):
    def __init__(self, time_limit_seconds: float = 30.0) -> None:
        if time_limit_seconds <= 0:
            raise ValueError("time_limit_seconds must be positive")
        self.time_limit_seconds = float(time_limit_seconds)

    # solve_ortools_cvrp(..., time_limit_seconds=self.time_limit_seconds)


# optimizer_api/strategies/pyvrp_strategy.py
class PyVRPStrategy(BaseRoutingStrategy):
    def __init__(self, time_limit_seconds: float = 30.0) -> None:
        if time_limit_seconds <= 0:
            raise ValueError("time_limit_seconds must be positive")
        self.time_limit_seconds = float(time_limit_seconds)

class PyVRPAlternativeStrategy(BaseRoutingStrategy):
    def __init__(self, time_limit_seconds: float = 30.0) -> None:
        if time_limit_seconds <= 0:
            raise ValueError("time_limit_seconds must be positive")
        self.time_limit_seconds = float(time_limit_seconds)

# _optimize_with_pyvrp(..., time_limit_seconds=strategy.time_limit_seconds)
```

Tests must monkeypatch the core solver calls and assert exact forwarded seconds for default `30`, lowered server policy `10`, and two simultaneous fresh instances with different values. Report no solver-native runtime for engines without an enforceable native clock. Never mutate the input request, registry compatibility instances, promoted config, or core global state.

- [ ] **Step 5: Run applicability, policy, and concurrency-safety gates**

```powershell
python -m pytest optimizer_api/tests/test_package_b_tuning_applicability.py optimizer_api/tests/test_package_b_native_runtime.py optimizer_api/tests/test_package_b_compute_policy.py optimizer_api/tests/test_strategy_registry_minor1.py optimizer_api/tests/test_sota_config_parity.py optimizer_api/tests/test_holistic_strategy_core_delegation.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 6: Commit**

```powershell
git add optimizer_api/compute_policy.py optimizer_api/strategies/ortools_cvrp.py optimizer_api/strategies/pyvrp_strategy.py optimizer_api/tests/test_package_b_tuning_applicability.py optimizer_api/tests/test_package_b_native_runtime.py
git diff --cached --check
git commit -m "feat(api): apply request-local compute budgets"
```

### Task 5: Canonical Endpoint Execution, Total Deadline, and Ranking

**Files:**
- Modify: `optimizer_api/routers/optimization.py:43-278`
- Create: `optimizer_api/tests/test_package_b_optimize_boundary.py`
- Create: `optimizer_api/tests/test_package_b_compare_orchestration.py`
- Re-run: `optimizer_api/tests/test_feasibility_certificate_attachment.py`
- Re-run: `optimizer_api/tests/test_production_feasibility_boundary.py`

**Interfaces:**
- Consumes: Tasks 2–4 resolver/policy interfaces.
- Produces: canonical `/optimize` and `/compare` responses, deterministic ranking, and one total soft deadline.

- [ ] **Step 1: Write RED optimize canonicalization tests**

Cover alias `ga` returning `algorithm_used="genetic_algorithm"` and `algorithm_requested="ga"`; fresh instances across two calls; unknown and unavailable 400 before `optimize`; recognized-but-inapplicable tuning 422; and applied metadata on success, solver failure, exception, and `None` result. Assert 400/403/422 errors contain no `applied_policy` because execution did not start.

- [ ] **Step 2: Write RED comparison tests**

Use stub `_run_single_algorithm` and fake executor/wait objects to prove:

```python
response = compare_algorithms(CompareRequest(
    students=[], depot=DEPOT,
    algorithms=["ga", "genetic_algorithm", "nearest_neighbor", "greedy"],
))
assert [result.algorithm for result in response.results] == ["genetic_algorithm", "greedy"]
assert executions == ["genetic_algorithm", "greedy"]
assert observed_max_workers == 2
assert shutdown_call == {"wait": False, "cancel_futures": True}
```

Ranking cases must prove:

```python
# Best: duration, vehicles, canonical name.
assert rank_best([
    result("zeta", duration=10, vehicles=2, seconds=1),
    result("alpha", duration=10, vehicles=1, seconds=2),
]) == "alpha"

# Fastest: execution seconds, canonical name.
assert rank_fastest([
    result("zeta", duration=9, vehicles=1, seconds=1),
    result("alpha", duration=10, vehicles=2, seconds=1),
]) == "alpha"
```

Include infeasible, uncertified, exception, and timed-out results and assert none can win.

- [ ] **Step 3: Run both files and verify RED**

```powershell
python -m pytest optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 4: Refactor `/optimize` around resolver and policy**

Replace direct `STRATEGY_REGISTRY` reads with:

```python
try:
    resolution = resolve_strategy(request.algorithm)
except (UnknownStrategyError, StrategyUnavailableError) as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from None

strategy = resolution.create()
try:
    effective_request, applied_policy = apply_compute_policy(
        request, resolution, strategy, load_compute_policy()
    )
except PolicyValidationError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from None

result = strategy.optimize(effective_request)
```

Canonicalize `result.algorithm_used`, set `result.algorithm_requested`, attach `applied_policy`, then preserve the existing scheduling, Package A certification, and profiler order. Every post-start failure builder receives the same truthful metadata.

- [ ] **Step 5: Implement bounded `/compare` orchestration**

Use these constants and stdlib imports:

```python
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from time import monotonic

from optimizer_api.compute_policy import DEFAULT_COMPARE_ALGORITHMS, load_compute_policy
```

Resolve all submitted keys before creating an executor. Use the six defaults only when omitted. Reject an explicit empty list, any unknown/unavailable explicit key, and a deduplicated canonical count above the effective limit. Then:

```python
executor: ThreadPoolExecutor | None = None
future_by_canonical = {}
pending = set()
try:
    executor = ThreadPoolExecutor(max_workers=min(policy.max_workers, len(resolutions)))
    for resolution in resolutions:
        future = executor.submit(_run_single_algorithm, resolution, opt_request, policy)
        future_by_canonical[resolution.canonical] = future
        pending.add(future)
    done, pending = wait(
        pending,
        timeout=policy.deadline_seconds,
        return_when=ALL_COMPLETED,
    )
    # collect completed futures without another timeout; create typed timeout
    # results for pending futures and preserve canonical request order
finally:
    for future in pending:
        future.cancel()
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)
```

Do not use the executor as a context manager. Record `soft_response_deadline` on comparison metadata and timed-out results. Running threads may continue, but the response must not wait for them.

Rank only `success and feasibility_certificate and feasibility_certificate.is_feasible` completed results:

```python
best = min(eligible, key=lambda r: (r.total_duration_minutes, r.total_vehicles, r.algorithm))
fastest = min(eligible, key=lambda r: (r.execution_time_seconds, r.algorithm))
```

- [ ] **Step 6: Run all boundary and Package A regression tests**

```powershell
python -m pytest optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py optimizer_api/tests/test_feasibility_certificate_attachment.py optimizer_api/tests/test_production_feasibility_boundary.py optimizer_api/tests/test_response_certifier.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 7: Commit**

```powershell
git add optimizer_api/routers/optimization.py optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py optimizer_api/tests/test_feasibility_certificate_attachment.py
git diff --cached --check
git commit -m "feat(api): bound canonical comparison execution"
```

### Task 6: Exact TSP Fail-Fast Correctness Repair

**Files:**
- Modify: `uniride_core/algorithms/string_exact_tsp.py:1-52`
- Modify: `uniride_core/tests/test_string_exact_tsp.py:38-47`
- Modify: `optimizer_api/routers/optimization.py`
- Modify: `optimizer_api/tests/test_package_b_optimize_boundary.py`
- Modify: `optimizer_api/tests/test_package_b_compare_orchestration.py`

**Interfaces:**
- Produces: `ExactTSPSizeError(ValueError)` and sanitized production failure results.
- Consumes: Package A failure certificate and Task 5 applied-policy metadata builders.

- [ ] **Step 1: Replace the truncation test with RED rejection tests**

```python
import pytest
from uniride_core.algorithms.string_exact_tsp import ExactTSPSizeError


def test_solve_exact_tsp_route_rejects_oversize_search():
    with pytest.raises(ExactTSPSizeError, match="3 waypoints exceeds exact-search limit 2"):
        solve_exact_tsp_route(
            ["A", "B", "C"], "D", lambda origin, destination: 1,
            max_permutation_size=2,
        )
```

Add API cases for 11 students under `permutation`, `exact`, and explicit comparison. Assert the solver method is never called, the result is unsuccessful, all 11 occurrence identities remain represented in the request, error text is sanitized, the result is unranked, and applied-policy metadata is truthful.

- [ ] **Step 2: Run exact/core/API tests and verify RED**

```powershell
python -m pytest uniride_core/tests/test_string_exact_tsp.py optimizer_api/tests/test_permutation_tsp_core_delegation.py optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 3: Replace slicing with a documented exception**

```python
class ExactTSPSizeError(ValueError):
    """Raised before factorial work when an exact TSP request exceeds its limit."""


# inside solve_exact_tsp_route
search_waypoints = list(waypoints)
if len(search_waypoints) > max_permutation_size:
    raise ExactTSPSizeError(
        f"{len(search_waypoints)} waypoints exceeds exact-search limit {max_permutation_size}"
    )
```

Export the exception in `__all__`. In the production router, preflight canonical `permutation_tsp` requests above ten and build the same sanitized unsuccessful result shape used for a solver that produced no valid result. Do not expose waypoint content or a traceback. In comparison, only that canonical run fails; other eligible runs continue.

- [ ] **Step 4: Run the focused exact and feasibility gates**

```powershell
python -m pytest uniride_core/tests/test_string_exact_tsp.py optimizer_api/tests/test_permutation_tsp_core_delegation.py optimizer_api/tests/test_occurrence_identity_strategies.py optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py optimizer_api/tests/test_production_feasibility_boundary.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 5: Commit**

```powershell
git add uniride_core/algorithms/string_exact_tsp.py uniride_core/tests/test_string_exact_tsp.py optimizer_api/routers/optimization.py optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py
git diff --cached --check
git commit -m "fix(core): reject oversized exact TSP requests"
```

### Task 7: Server-Only Next.js Optimizer Transport

**Files:**
- Create: `src/lib/optimizer-server.ts`
- Create: `src/services/optimizer-types.ts`
- Modify: `src/services/optimizer-service.ts:1-438`
- Modify: `src/services/optimizer-service.test.ts`
- Modify: `src/app/api/optimize-route/route.ts`
- Modify: `src/app/api/compare-algorithms/route.ts`
- Modify: `src/app/api/calculate-vehicles/route.ts`
- Modify: `src/app/api/sandbox/route.ts:174-187`
- Modify: `src/services/doubus/multi-vehicle-routing.ts:12-22,266-279`
- Modify: `src/app/(app)/admin/compare/page.tsx:12`
- Create: `src/lib/optimizer-server.test.ts`
- Create: `src/services/optimizer-boundary.test.ts`

**Interfaces:**
- Produces: `optimizerFetch(path, init)`, browser-safe optimizer DTO types, and metadata-preserving BFF responses.
- Consumes: server-only `OPTIMIZER_INTERNAL_API_KEY` and existing `OPTIMIZER_API_URL`.

- [ ] **Step 1: Write RED transport and boundary tests**

`optimizer-server.test.ts`:

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
import { optimizerFetch } from "./optimizer-server";

describe("optimizerFetch", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    process.env.OPTIMIZER_INTERNAL_API_KEY = "server-secret";
  });

  it("injects the key without changing caller headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    await optimizerFetch("/api/v1/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({
      "Content-Type": "application/json",
      "X-Internal-API-Key": "server-secret",
    });
  });

  it("fails before fetch when the server key is missing", async () => {
    delete process.env.OPTIMIZER_INTERNAL_API_KEY;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(optimizerFetch("/api/v1/optimize", { method: "POST" }))
      .rejects.toThrow("Optimizer service is not configured");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
```

Make `optimizer-boundary.test.ts` an executable source-boundary gate using only Node’s standard library:

```typescript
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const read = (path: string) => readFileSync(join(root, path), "utf8");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe("optimizer server boundary", () => {
  it("contains no public optimizer-key variable", () => {
    const forbidden = ["NEXT", "PUBLIC", "OPTIMIZER", "INTERNAL", "API", "KEY"].join("_");
    for (const file of sourceFiles(join(root, "src"))) {
      expect(readFileSync(file, "utf8"), file).not.toContain(forbidden);
    }
  });

  it("keeps the compare client on type-only browser-safe imports", () => {
    const page = read("src/app/(app)/admin/compare/page.tsx");
    expect(page).toContain("import type");
    expect(page).toContain("@/services/optimizer-types");
    expect(page).not.toContain("@/services/optimizer-service");
  });

  it.each([
    ["src/services/optimizer-service.ts", ["/api/v1/optimize", "/api/v1/compare"]],
    ["src/app/api/sandbox/route.ts", ["/api/v1/optimize"]],
    ["src/services/doubus/multi-vehicle-routing.ts", ["/api/v1/optimize"]],
  ])("routes heavy calls in %s through optimizerFetch", (path, endpoints) => {
    const source = read(path);
    expect(source).toContain("optimizerFetch");
    for (const endpoint of endpoints) expect(source).toContain(endpoint);
    expect(source).not.toMatch(/fetch\s*\(\s*[`'"][^`'"]*\/api\/v1\/(optimize|compare|vehicle-calculator)/);
  });

  it("keeps server-only transport out of client components", () => {
    for (const file of sourceFiles(join(root, "src"))) {
      const source = readFileSync(file, "utf8");
      if (/^[\s\n]*["']use client["'];/m.test(source)) {
        expect(source, file).not.toContain("optimizer-server");
      }
    }
  });
});
```

Extend `optimizer-service.test.ts` so `algorithm_requested`, `feasibility_certificate`, and `applied_policy` survive mapping for optimize and compare.

- [ ] **Step 2: Run Vitest and verify RED**

```powershell
npm test -- --run src/lib/optimizer-server.test.ts src/services/optimizer-service.test.ts src/services/optimizer-boundary.test.ts
```

- [ ] **Step 3: Create the server-only transport**

```typescript
import "server-only";
import { OPTIMIZER_API_URL } from "@/lib/config";

export async function optimizerFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const key = process.env.OPTIMIZER_INTERNAL_API_KEY;
  if (!key) throw new Error("Optimizer service is not configured");
  const headers = new Headers(init.headers);
  headers.set("X-Internal-API-Key", key);
  return fetch(`${OPTIMIZER_API_URL}${path}`, { ...init, headers });
}
```

Move only interfaces/types used by client code into `optimizer-types.ts`. Re-export them as types from `optimizer-service.ts` for server callers. Change the compare page import to:

```typescript
import type { CompareResult, AlgorithmCompareResult } from "@/services/optimizer-types";
```

- [ ] **Step 4: Route every heavy server call through `optimizerFetch`**

Use public raw `fetch` only for `/health` and `/api/v1/strategies`. Use `optimizerFetch` for optimize, compare, sandbox reoptimization, and legacy DouBus optimization. Preserve existing retry behavior by making the retry helper accept a fetch function or by retrying `optimizerFetch`; never copy the key into payloads or log it.

Add the new typed fields to `optimizer-types.ts`:

```typescript
export interface AppliedPolicyLimitInfo {
  value: number;
  source: "profile_default" | "server_override" | "caller" | "strategy_default";
  enforcement: string;
}

export interface AppliedComputePolicyInfo {
  profile_id: string;
  algorithm_requested?: string;
  algorithm_canonical?: string;
  student_count: number;
  vehicle_count: number;
  cancellation_mode: "none" | "soft_response_deadline";
  limits: Record<string, AppliedPolicyLimitInfo>;
}
```

Preserve `algorithm_requested`, `feasibility_certificate`, and `applied_policy` through `optimizeRoutes`, `compareAllAlgorithms`, `/api/optimize-route`, `/api/compare-algorithms`, and the calculate-vehicles metadata. Keep browser response errors free of secret/config values.

- [ ] **Step 5: Run focused frontend gates**

```powershell
npm test -- --run src/lib/optimizer-server.test.ts src/services/optimizer-service.test.ts src/services/optimizer-boundary.test.ts src/app/api/optimize-route/route.test.ts
npm run typecheck
```

Expected: all tests and TypeScript pass; no client component imports the server transport.

- [ ] **Step 6: Commit**

```powershell
git add src/lib/optimizer-server.ts src/lib/optimizer-server.test.ts src/services/optimizer-types.ts src/services/optimizer-service.ts src/services/optimizer-service.test.ts src/services/optimizer-boundary.test.ts src/app/api/optimize-route/route.ts src/app/api/compare-algorithms/route.ts src/app/api/calculate-vehicles/route.ts src/app/api/sandbox/route.ts src/services/doubus/multi-vehicle-routing.ts 'src/app/(app)/admin/compare/page.tsx'
git diff --cached --check
git commit -m "feat(web): authenticate server optimizer calls"
```

### Task 8: Documentation Synchronization and Final Verification

**Files:**
- Modify: `README.md:80-105`
- Modify: `CURRENT_ARCHITECTURE.md`
- Modify: `ACTIVE_ROADMAP.md`
- Modify: `WORKLOG.md`

**Interfaces:**
- Consumes: exact final code, commit SHAs, and test output from Tasks 1–7.
- Produces: current operational instructions and an auditable completion record.

- [ ] **Step 1: Run the focused Package B gate before editing claims**

```powershell
python -m pytest optimizer_api/tests/test_package_b_compute_auth.py optimizer_api/tests/test_package_b_compute_policy.py optimizer_api/tests/test_package_b_canonical_resolution.py optimizer_api/tests/test_package_b_tuning_applicability.py optimizer_api/tests/test_package_b_native_runtime.py optimizer_api/tests/test_package_b_optimize_boundary.py optimizer_api/tests/test_package_b_compare_orchestration.py uniride_core/tests/test_string_exact_tsp.py academic_benchmark/tests/test_production_registry_snapshot.py -q -p no:cacheprovider --tb=short
```

Expected: zero failures and zero unexpected skips.

- [ ] **Step 2: Run full affected Python suites**

```powershell
python -m pytest optimizer_api/tests uniride_core/tests academic_benchmark/tests/test_production_registry_snapshot.py -q -p no:cacheprovider --tb=short
```

Record exact pass/fail/skip/warning counts. Environment-only failures are not silently waived; compare them against the clean base and report them separately.

- [ ] **Step 3: Run full frontend gates**

```powershell
npm test -- --run
npm run typecheck
npm run lint
npm run build
```

The existing temporary ESLint-warning and Supabase-build waivers may be reported only if the failures reproduce on clean `WIP`. Package B may not introduce new warnings, errors, or secret exposure.

- [ ] **Step 4: Update core documentation from verified output**

Update `README.md` with:

- FastAPI `INTERNAL_API_KEY`;
- Next.js server-only `OPTIMIZER_INTERNAL_API_KEY` with the same secret value;
- local/test-only `UNIRIDE_DISABLE_AUTH=1` and its production prohibition;
- all nine `UNIRIDE_COMPUTE_*` variables and the fact that they may only lower defaults;
- the `production-conservative-v1` ceilings and soft-deadline limitation.

Update `CURRENT_ARCHITECTURE.md` with the BFF → internal-key FastAPI boundary, canonical resolver, request-scoped factories, immutable profile, and Package A certificate/ranking sequence.

Update `ACTIVE_ROADMAP.md` by marking Package B implemented only if every acceptance gate is green. Keep Package C hard cancellation/process isolation/durable jobs explicitly pending.

Append a dated `WORKLOG.md` entry with exact commit list, changed boundaries, exact test commands/counts, waivers, and remaining risks. Do not claim hard cancellation, rate limiting, academic fairness changes, or solver-quality improvement.

- [ ] **Step 5: Run documentation and repository integrity checks**

```powershell
rg -n -i '\b(T[O]DO|T[B]D|FIX[M]E|PLACE[H]OLDER)\b' docs/superpowers/plans/2026-08-12-package-b-compute-policy.md README.md CURRENT_ARCHITECTURE.md ACTIVE_ROADMAP.md WORKLOG.md
git diff --check
git status --short --branch
```

Expected: no unfinished-work markers, no whitespace errors, and only the intended documentation paths remain uncommitted.

- [ ] **Step 6: Commit documentation**

```powershell
git add README.md CURRENT_ARCHITECTURE.md ACTIVE_ROADMAP.md WORKLOG.md
git diff --cached --check
git commit -m "docs: record production compute policy"
```

- [ ] **Step 7: Perform final branch review without merging or pushing**

```powershell
git log --oneline --decorate origin/WIP..HEAD
git diff --stat origin/WIP...HEAD
git diff --check origin/WIP...HEAD
git status --short --branch
```

Require a correctness review of auth, policy truthfulness, alias identity, concurrency, exact-TSP behavior, and browser secret containment. Return exact commands/counts and request explicit authorization before local WIP merge or GitHub push.

## Final Acceptance Checklist

- [ ] All three heavy endpoints deny missing/wrong keys and accept the correct key.
- [ ] Public health, strategy, and transformation endpoints remain public.
- [ ] Production rejects `UNIRIDE_DISABLE_AUTH=1` at startup.
- [ ] Every environment override is validated and can only lower its hard ceiling.
- [ ] Every public tuning key has applicable and inapplicable strategy coverage.
- [ ] Every alias resolves to one canonical identity and creates fresh instances.
- [ ] Explicit alias duplicates execute exactly once.
- [ ] Default comparison order is exactly the approved six canonical algorithms.
- [ ] Comparison uses at most two workers and one total 120-second soft deadline.
- [ ] Timed-out, failed, infeasible, or uncertified results are never ranked.
- [ ] Best and fastest tie-breakers are deterministic.
- [ ] Applied-policy metadata describes only behavior actually enforced.
- [ ] Exact TSP rejects more than ten waypoints without truncation.
- [ ] The internal key cannot enter client bundles, responses, or logs.
- [ ] Package A and production registry snapshot gates remain green.
- [ ] Python, Vitest, TypeScript, lint, build, and `git diff --check` results are recorded exactly.
- [ ] No merge or push occurs without explicit authorization.
