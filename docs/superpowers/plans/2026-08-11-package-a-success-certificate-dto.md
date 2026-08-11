# Package A Success-Certificate DTO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach one validated, typed feasibility certificate to every successful or failed production optimization result without breaking existing response fields.

**Architecture:** Define response-only Pydantic certificate models and validate their internal invariants. Convert each raw certifier dictionary exactly once at the router boundary, attach the typed object, and retain the legacy JSON `error_message` for failed results. Error paths that cannot produce a strategy response attach one fixed sanitized unavailable certificate.

**Tech Stack:** Python 3.14, Pydantic 2, FastAPI, pytest.

## Global Constraints

- Work only in `C:\tmp\UniRide-package-a-feasibility` on `codex/package-a-universal-feasibility-20260810`.
- Preserve commits `74087a2`, `0180a58`, and `6b692bb`.
- Do not modify request DTOs, frontend code, solver mathematics, academic code, dependencies, databases, generated artifacts, other worktrees, or remotes.
- The new field is optional and additive; legacy `error_message` remains populated for failure compatibility.
- Certification is performed once per produced result; serialization never invokes the certifier again.
- Use RED-GREEN TDD and do not commit or push implementation without explicit authorization.

---

### Task 1: Typed Certificate DTO Contract

**Files:**
- Modify: `optimizer_api/models/schemas.py:349-370`
- Create: `optimizer_api/tests/test_feasibility_certificate_attachment.py`

**Interfaces:**
- Produces: `FeasibilityViolationInfo`, `FeasibilityCertificateInfo`.
- Produces: optional `feasibility_certificate` fields on `OptimizationResponse` and `AlgorithmResult`.
- Consumes: existing `BaseModel`, `model_validator`, `List`, and `Optional` imports.

- [ ] **Step 1: Write failing DTO and OpenAPI tests**

```python
import json

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from models import schemas
from routers import optimization


def _certificate_model():
    model = getattr(schemas, "FeasibilityCertificateInfo", None)
    assert model is not None, "typed certificate model is missing"
    return model


def test_certificate_model_enforces_invariants():
    model = _certificate_model()
    valid = model(is_feasible=True, violation_count=0, violations=[])
    assert valid.is_feasible is True

    with pytest.raises(ValidationError):
        model(is_feasible=False, violation_count=2, violations=[])
    with pytest.raises(ValidationError):
        model(
            is_feasible=True,
            violation_count=1,
            violations=[{"type": "x", "severity": "error", "details": "x"}],
        )
    with pytest.raises(ValidationError):
        model(
            is_feasible=True,
            violation_count=0,
            violations=[],
            certify_error="must fail closed",
        )


def test_certificate_field_is_optional_and_typed_in_openapi():
    assert "feasibility_certificate" in schemas.OptimizationResponse.model_fields
    assert "feasibility_certificate" in schemas.AlgorithmResult.model_fields

    app = FastAPI()
    app.include_router(optimization.router)
    components = app.openapi()["components"]["schemas"]
    for response_name in ("OptimizationResponse", "AlgorithmResult"):
        prop = components[response_name]["properties"]["feasibility_certificate"]
        assert "FeasibilityCertificateInfo" in json.dumps(prop)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api\tests\test_feasibility_certificate_attachment.py -q -p no:cacheprovider --tb=short
```

Expected: failures state that `FeasibilityCertificateInfo` and the response fields are missing.

- [ ] **Step 3: Implement the minimal typed models**

Add before `OptimizationResponse`:

```python
class FeasibilityViolationInfo(BaseModel):
    type: str
    severity: str
    details: str
    route_index: Optional[int] = None
    node: Optional[int] = None


class FeasibilityCertificateInfo(BaseModel):
    is_feasible: bool
    violation_count: int
    violations: List[FeasibilityViolationInfo]
    certify_error: Optional[str] = None

    @model_validator(mode="after")
    def validate_consistency(self) -> "FeasibilityCertificateInfo":
        if self.violation_count != len(self.violations):
            raise ValueError("violation_count must equal len(violations)")
        if self.is_feasible and (self.violations or self.certify_error is not None):
            raise ValueError("a feasible certificate cannot contain violations or certify_error")
        return self
```

Add to both result DTOs:

```python
feasibility_certificate: Optional[FeasibilityCertificateInfo] = None
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command. Expected: all tests pass.

---

### Task 2: Attach One Typed Certificate at Every Production Result Boundary

**Files:**
- Modify: `optimizer_api/routers/optimization.py:1-155`
- Modify: `optimizer_api/tests/test_feasibility_certificate_attachment.py`

**Interfaces:**
- Consumes: `FeasibilityCertificateInfo.model_validate(payload)`.
- Produces: `_typed_certificate(payload: dict | None) -> FeasibilityCertificateInfo`.
- Produces: populated `feasibility_certificate` on `/optimize` and every `AlgorithmResult`.

- [ ] **Step 1: Add failing endpoint tests**

Use a small stub strategy and monkeypatch `optimization.certify_optimization_response`. Assert:

```python
assert calls == 1
assert result.feasibility_certificate.model_dump(exclude_none=True) == payload
assert result.success is payload["is_feasible"]
```

For infeasible `/optimize` and `_run_single_algorithm`, additionally assert:

```python
assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)
```

Return an invalid payload such as
`{"is_feasible": True, "violation_count": 1, "violations": []}` and assert both boundaries attach the fixed sanitized fallback, set `success=False`, and omit the raw validation exception. Assert strategy-not-found and algorithm-exception `AlgorithmResult` objects also carry the same typed failure schema.

- [ ] **Step 2: Run endpoint tests and verify RED**

Run the Task 1 focused command. Expected: attachment assertions fail because router results still discard certificates.

- [ ] **Step 3: Implement one conversion helper and attachment**

Import `FeasibilityCertificateInfo` and add:

```python
_INVALID_CERTIFICATE_ERROR = "certification aborted: invalid certificate payload"
_UNAVAILABLE_CERTIFICATE_ERROR = "certification unavailable: algorithm produced no result"


def _typed_certificate(payload: dict | None) -> FeasibilityCertificateInfo:
    if payload is not None:
        try:
            return FeasibilityCertificateInfo.model_validate(payload)
        except Exception:  # validation must fail closed
            logger.exception("Invalid feasibility certificate payload")
    return FeasibilityCertificateInfo(
        is_feasible=False,
        violation_count=0,
        violations=[],
        certify_error=(
            _INVALID_CERTIFICATE_ERROR
            if payload is not None
            else _UNAVAILABLE_CERTIFICATE_ERROR
        ),
    )
```

In `/optimize`, call `certify_optimization_response` once after a real strategy result is available, pass that returned dictionary to `_typed_certificate` once, and retain the resulting object in a local `typed_certificate`. Set `success = typed_certificate.is_feasible`, attach `feasibility_certificate=typed_certificate`, and, only when it is unsuccessful, set:

```python
error_message=json.dumps(typed_certificate.model_dump(exclude_none=True))
```

Do not call the certifier while serializing the response. For an absent or unavailable strategy result, attach `_typed_certificate(None)`, set `success=False`, and use the same `model_dump(exclude_none=True)` JSON for the legacy failure `error_message`.

In `_run_single_algorithm`, use the identical sequence for every real algorithm result: certify once, validate once, derive `success` from the same typed object, and attach that object to the returned `AlgorithmResult`. Apply the unavailable typed certificate to every no-result boundary, including strategy-not-found, strategy exception, and compare timeout/unavailable paths. Those paths must return `success=False` and must use the fixed unavailable message, never raw exception text. An invalid DTO payload must instead use the fixed invalid-payload message, also without exposing Pydantic validation details.

When compare ranking filters results, require both the existing success check and `result.feasibility_certificate is not None and result.feasibility_certificate.is_feasible`; do not recertify results to rank them.

- [ ] **Step 4: Run endpoint tests and verify GREEN**

Run:

```powershell
C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api\tests\test_feasibility_certificate_attachment.py -q -p no:cacheprovider --tb=short
```

Expected: all focused DTO, `/optimize`, and `/compare` attachment tests pass; each real result has exactly one certifier call and all failure JSON equals its attached typed certificate payload.

- [ ] **Step 5: Commit the completed attachment boundary**

```powershell
git add optimizer_api/models/schemas.py optimizer_api/routers/optimization.py optimizer_api/tests/test_feasibility_certificate_attachment.py
git commit -m "feat(api): attach typed feasibility certificates"
```

Expected: one atomic Task 2 commit containing only the typed attachment DTO, router boundary, and focused test changes. Do not push.

---

### Task 3: Final Package A DTO Verification

**Files:**
- Verify: `optimizer_api/models/schemas.py`
- Verify: `optimizer_api/routers/optimization.py`
- Verify: `optimizer_api/tests/test_feasibility_certificate_attachment.py`
- Verify: `optimizer_api/tests/test_production_feasibility_boundary.py`
- Verify: `optimizer_api/tests/test_occurrence_identity_pipeline_a.py`
- Verify: `optimizer_api/tests/test_occurrence_identity_strategies.py`

**Interfaces:**
- Verifies: all result boundaries attach one validated `FeasibilityCertificateInfo`.
- Verifies: failed legacy `error_message` JSON equals `typed_certificate.model_dump(exclude_none=True)`.

- [ ] **Step 1: Run the focused Package A DTO and occurrence gate**

```powershell
C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api\tests\test_feasibility_certificate_attachment.py optimizer_api\tests\test_production_feasibility_boundary.py optimizer_api\tests\test_occurrence_identity_pipeline_a.py optimizer_api\tests\test_occurrence_identity_strategies.py -q -p no:cacheprovider --tb=short
```

Expected: all selected tests pass.

- [ ] **Step 2: Run the full core and API gate**

```powershell
C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest uniride_core\tests optimizer_api\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-package-a-dto-final --tb=short
```

Expected: all collected core and API tests pass; record any environment-only warnings separately from test failures.

- [ ] **Step 3: Inspect the final authorized diff**

```powershell
git diff --check
git status --short --branch
```

Expected: `git diff --check` is silent and status contains only authorized Package A DTO changes. This task makes no code edits unless a test exposes an approved-scope defect; if it does, return to the relevant RED-GREEN task, rerun both gates, and create a separate atomic corrective commit.

## Explicit Exclusions

- No frontend changes.
- No solver or production strategy-registry changes.
- No dependency changes.
- No merge or push changes.
