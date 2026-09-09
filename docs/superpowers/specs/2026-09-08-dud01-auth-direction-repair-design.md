# DUD-01 authentication and direction repair

Status: implemented and automatically verified; integrated into WIP. See docs/DUD01_VERIFICATION_2026-09-09.md for current evidence and the pending live gate.

## Scope

Repair the active administrator vehicle-planning page, its authenticated API client, the calculate-vehicles BFF, and route-plan serialization. Preserve unrelated checkout changes. No merge, push, live-data mutation, solver changes, or daily-planner redesign.

## Contract

- Use the existing authenticated admin client for vehicle calculation. Preserve authentication and authorization status codes.
- Normalize an omitted request direction to pickup before invoking the optimizer. Reject invalid explicit request directions.
- A successful optimizer response must explicitly carry pickup or dropoff and match the normalized request direction. Missing, invalid, or conflicting response directions cause a redacted upstream contract error, never a fabricated successful direction.
- Save the direction associated with the completed calculation, independent of later form selection changes. The serializer rejects missing, invalid, or conflicting direction information.
- Do not widen production direction types to accommodate malformed test fixtures.

## Verification

Write and observe failing regression tests before implementation. Cover client authentication, 401/403 preservation, both request directions, omitted request compatibility, malformed request rejection, malformed/missing/conflicting successful backend direction rejection, and save behavior after changing the selector. Use the real serializer in page tests. Model malformed runtime data explicitly at test boundaries.

Run focused Vitest files for the active page, calculate-vehicles route, admin client, and route-plan serializer; then typecheck, the frontend suite, and diff hygiene. Record exact commands, counts, failures, and skipped checks. Unexecuted patches are not verified implementations.
