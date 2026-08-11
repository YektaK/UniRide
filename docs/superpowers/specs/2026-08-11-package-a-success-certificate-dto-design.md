# Package A Success-Certificate DTO Design

**Status:** Typed-model approach selected; pending written specification approval
**Date:** 2026-08-11
**Implementation base:** `74087a2` (`feat(api): enforce production feasibility certificates`)
**Branch:** `codex/package-a-universal-feasibility-20260810`

## 1. Objective

Close the remaining Package A exit-gate gap by attaching the same structured
feasibility certificate to successful and unsuccessful `/optimize` and
`/compare` results. The extension must be backward compatible: existing fields
and legacy failure diagnostics remain available, while clients that understand
the new field receive a typed OpenAPI contract.

## 2. Verified Starting State

- Every production `/optimize` and `/compare` result is evaluated by
  `certify_optimization_response`.
- An infeasible result is demoted to `success=False` and its certificate is
  currently serialized into `error_message`.
- A feasible result is enforced internally but discards the certificate.
- `OptimizationResponse` and `AlgorithmResult` have no certificate field.
- The focused Package A and occurrence gate passed 86 tests.
- The complete `uniride_core/tests` plus `optimizer_api/tests` gate passed 833
  tests with 6 warnings.

## 3. Considered Approaches

### A. Typed optional certificate models — selected

Define typed Pydantic models for a violation and certificate, then add an
optional `feasibility_certificate` field to `OptimizationResponse` and
`AlgorithmResult`. This produces a stable OpenAPI schema and validates the
boundary payload without changing existing required fields.

### B. Optional `Dict[str, Any]`

This is the smallest implementation, but it leaves clients without a useful
schema and permits malformed certificate shapes. Rejected.

### C. Replace `error_message` with a certificate

This would remove the duplicated failure representation, but it is a breaking
change for existing clients. Rejected.

## 4. Contract

Add two response-only models in `optimizer_api/models/schemas.py`:

- `FeasibilityViolationInfo`
  - `type: str`
  - `severity: str`
  - `details: str`
  - `route_index: Optional[int] = None`
  - `node: Optional[int] = None`
- `FeasibilityCertificateInfo`
  - `is_feasible: bool`
  - `violation_count: int`
  - `violations: List[FeasibilityViolationInfo]`
  - `certify_error: Optional[str] = None`

Add the following optional field to both result DTOs:

```python
feasibility_certificate: Optional[FeasibilityCertificateInfo] = None
```

The field is optional so responses created by existing internal tests, older
strategies, and existing clients remain valid. No request DTO changes are
authorized.

## 5. Data Flow

### `/optimize`

1. Run the selected strategy and scheduling behavior already present.
2. Generate one certificate.
3. Validate the returned dictionary into `FeasibilityCertificateInfo`.
4. Attach it to `result.feasibility_certificate` for both feasible and
   infeasible outcomes.
5. If infeasible, retain the existing `success=False` demotion and JSON
   `error_message` for compatibility.

### `/compare`

1. Generate one certificate for each algorithm result.
2. Validate it into the same model.
3. Pass it into the corresponding `AlgorithmResult` regardless of feasibility.
4. Rank only results whose existing success and certificate checks both pass.

No certificate is recomputed solely for serialization.

## 6. Error Handling

- Certificate construction remains fail closed.
- A `certify_error` certificate is attached in structured form and causes the
  result to be unsuccessful.
- The certifier's sanitized error text remains the only internal-failure detail
  crossing the API boundary.
- DTO validation failure must not allow `success=True`; it follows the existing
  endpoint exception boundary and server-side logging policy.

## 7. Compatibility

- Existing request bodies are unchanged.
- Existing response fields retain their names and meanings.
- Failure `error_message` remains populated exactly as before this extension.
- The new field is additive and optional.
- No frontend changes are required to preserve current behavior.
- No solver, matrix, feasibility, ranking, or academic semantics change.

## 8. Test Design

RED tests must first prove the field is absent or unset under the current code:

1. A feasible `/optimize` result exposes a typed feasible certificate.
2. An infeasible `/optimize` result exposes a typed infeasible certificate and
   retains its legacy `error_message`.
3. Every `/compare` `AlgorithmResult` exposes its own typed certificate.
4. A fail-closed `certify_error` is represented by the same typed model.
5. Constructing legacy response DTOs without the new field remains valid and
   serializes it as `None` under the existing Pydantic defaults.
6. The generated FastAPI OpenAPI schema references the typed certificate model
   for both result DTOs.

After GREEN, run the focused production feasibility suite and the complete
core/API gate.

## 9. Exclusions

- No frontend consumption or rendering.
- No removal of `error_message`.
- No request-schema, solver, matrix-provenance, authentication, worker-budget,
  comparison-policy, academic, dependency, database, or generated-artifact
  changes.
- No merge or push without separate authorization.

## 10. Acceptance Criteria

- Successful and failed `/optimize` results carry the typed certificate.
- Every `/compare` result carries the same typed certificate schema.
- Hard violations still cannot return `success=True`.
- Existing clients can ignore the additive optional field.
- Focused RED-GREEN evidence is recorded.
- `uniride_core/tests` and `optimizer_api/tests` pass.
- `git diff --check` passes and only authorized paths change.

