# Dudullu per-leg student confirmation

**Status:** Draft for user review. The user approved the separate per-leg data-source approach on 2026-09-29; implementation is not approved until this written specification is reviewed.

## Intent and constraints

Persist a student's pickup and dropoff decisions independently so the Dudullu preview can admit only explicitly confirmed legs. Preserve the existing 22:00 previous-day cutoff in `Europe/Istanbul`; never infer consent from a schedule, request status, address order, notes, or legacy row. Keep this as the smallest prerequisite that unblocks Package 2 Task 4. Do not apply a live migration or backfill data in this scope.

The approved daily-operations design already requires independent legs: a student may confirm pickup, dropoff, both, or neither, and one directionless row cannot represent both. This proposal pulls only the minimum confirmation UI forward from that design's later student-surface package; it does not pull forward driver operations, publication, notifications, or route management.

## Verified current behavior

- `ride_requests` stores pickup/dropoff timestamps and one whole-request `status`; it has no `service_date` or `direction` columns. `DbRideRequest` extends the directionless `RideRequest` type.
- `POST /api/ride-confirmation` accepts `confirm`, `cancel`, or `change` for a whole `rideDate`, then inserts or updates one request row. The student card presents both times and sends one whole-day action.
- The pure planner already models `StudentLegDecision` separately for `pickup` and `dropoff`. Missing decisions classify as `pending_student_confirmation`; a confirmation after cutoff classifies as `pending_admin_approval`.
- The legacy schedule generator may create direction-like request rows, but direction is not a persisted field. They are not a source for new decisions and must not be backfilled.
- The approved Package 2 plan explicitly says directionless request rows are not confirmed transport and that an empty admitted-demand set must not trigger a solve.

## Proposed data contract

Add an additive `student_leg_decisions` table as the current source of a student's intent for a scheduled service date and direction:

| Column | Contract |
|---|---|
| `user_id` | Non-null FK to `users.id`; identity comes from the authenticated session, never the request body. |
| `service_date` | Non-null PostgreSQL `DATE`, interpreted as the local service date in `Europe/Istanbul`. |
| `direction` | Non-null `pickup` or `dropoff`. |
| `decision` | Non-null `confirmed` or `cancelled`. No row means pending confirmation. |
| `decided_at` | Server/database timestamp for the latest state change; clients cannot supply it. |
| `flexibility_minutes` | Integer from 0 through 1439; defaults to 0, matching the existing planner contract. |

Use `(user_id, service_date, direction)` as the primary key. A repeated identical decision and flexibility value is idempotent and must not refresh `decided_at`; a changed decision or flexibility value gets a server timestamp. The first UI exposes no nonzero flexibility choice, so it uses the default 0. `decided_at` is sufficient for this latest-state record; do not add duplicate timestamps or immutable event history without an approved audit requirement.

Mapping to the pure planner is direct: absent row → no decision; `confirmed` → `{ status: "confirmed", confirmedAt, flexibilityMinutes }`; `cancelled` → `{ status: "cancelled", decidedAt }`. Reuse `classifyScheduleDecision`; do not duplicate cutoff logic in the API.

## Request and UI behavior

Reuse the existing student-authenticated `/api/ride-confirmation` boundary, but make scheduled confirmation directional:

- `POST` for `confirm` or `cancel` requires a strict body containing `action`, `rideDate` (`YYYY-MM-DD`), and `direction` (`pickup` or `dropoff`); optional `flexibilityMinutes` is an integer from 0 through 1439 and defaults to 0. Reject a missing direction; do not silently preserve whole-day semantics for these actions.
- Derive the user ID from `getCurrentUserFromRequest`; verify the database role is `student` before accessing the row. Keep fixed/redacted errors and authenticate before reads or writes.
- Before writing, verify the student's linked weekly schedule has a Dudullu entry for the requested service date's weekday. Reject an ineligible date without changing any decision; the planner's schedule-derived pickup/dropoff legs remain the source of which service exists.
- `GET ?date=YYYY-MM-DD` returns both leg states (`pending`, `confirmed`, or `cancelled`) for the authenticated student. It must not return another student's data.
- The schedule card shows the two leg states separately and each confirm/cancel control changes only its selected direction. The student can confirm either, both, or neither. Service times shown in the UI are not authoritative request fields.
- Preserve the existing whole-day `change` action and its legacy payload as an administrator-review request; it never creates or overwrites a per-leg confirmation. Legacy `pending_student_confirmation`, `confirmed`, and `cancelled_by_student` rows are never positive demand and do not override an explicit per-leg decision. A legacy `pending_admin_approval`, `cancelled_by_admin`, or `in_progress` row blocks both legs for that student/date; `completed` rows are not candidates for a new plan. The GET response exposes whether a legacy blocker exists so the UI can show the pending/admin-cancelled state.

Use the existing server-side Supabase admin client only after JWT identity and student-role verification. Enable RLS on the new table with no anon/authenticated table policies; the BFF is the only student read/write path, so timestamps and ownership cannot be spoofed from the browser. Keep the service-role key server-only.

## Preview admission

The Task 4 loader reads the exact service date's schedules and leg decisions, then passes the two decisions to `buildScheduleDemands`:

- no row remains `pending_student_confirmation`;
- on-time `confirmed` rows may be admitted;
- late confirmations remain `pending_admin_approval` and are not sent to the optimizer by this scope;
- `cancelled` rows are excluded;
- directionless rows never create positive demand; unresolved legacy change/admin-cancel/in-progress rows block both directions.

Only when at least one valid leg is admitted, load active vehicles, request a matrix snapshot, and call the optimizer. With zero admitted demand, return the honest pending/empty preview without matrix or optimizer calls. Existing matrix, certificate, arc, exact-anchor, and physical-fleet gates remain unchanged. Package 2 Task 4 is still incomplete until its admitted-demand solver path, two-anchor case, and Package 2 Task 5 fixture pass.

## Migration, access control, and compatibility

- Add one numbered SQL migration and update the canonical `supabase/schema.sql`, `supabase/rls_policies.sql`, and TypeScript `Database` types consistently.
- Use a database constraint for the composite key, direction, decision, and flexibility bounds. Enable RLS; the authenticated BFF is the only student read/write path.
- Do not alter, delete, or backfill existing `ride_requests`. Existing directionless records remain ambiguous and are handled by the current fail-closed blocker.
- Do not apply the migration to Supabase, query live rows, publish routes, or deploy as part of this design or its first implementation package.

## Verification and acceptance

Focused tests must prove:

1. Unauthenticated and non-student requests perform no decision reads/writes; body-supplied user IDs are rejected. A date without a matching active Dudullu schedule entry is rejected without a decision write.
2. Invalid dates/directions and unknown fields fail before decision/legacy-row reads or writes; errors do not expose Supabase rows or provider details.
3. Pickup and dropoff can be confirmed/cancelled independently; identical retries are idempotent; one direction never mutates the other.
4. Missing decisions, late confirmations, cancellations, unresolved legacy change requests, and admin-cancelled legacy requests produce the specified non-admitted outcomes.
5. The preview calls neither matrix nor optimizer for zero admitted demand, and calls them only for admitted exact-anchor groups.
6. The local migration and RLS/type definitions agree; no live database is used by tests.

Then run the focused confirmation, daily-planning, and preview suites; typecheck; lint; and `git diff --check`. The existing 28-student Package 2 gate remains a separate acceptance step.

## Explicitly out of scope

Admin approval of late confirmations, time-change/exception editing beyond the existing fail-closed legacy request, immutable decision history, live-data backfill, deployment, plan publication, driver/vehicle operations, and the remaining Package 6 student/driver surfaces.
