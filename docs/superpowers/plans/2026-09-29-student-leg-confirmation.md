# Dudullu Per-Leg Student Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist explicit pickup/dropoff decisions per student and service date, then admit only eligible confirmed legs into the Dudullu daily preview.

**Architecture:** Add one latest-state `student_leg_decisions` table, expose it only through the authenticated student BFF, and update the existing student card to act on each direction independently. The admin preview reuses `buildScheduleDemands` and `classifyScheduleDecision`, blocks ambiguous legacy states, and calls the existing content-addressed matrix/optimizer path only for admitted exact-anchor groups.

**Tech Stack:** PostgreSQL/Supabase SQL, TypeScript, Next.js route handlers, Zod, React, Vitest, existing FastAPI optimizer endpoints.

## Global Constraints

- Preserve the previous-day 22:00 confirmation cutoff in `Europe/Istanbul`.
- Never infer consent from a schedule, request status, address order, notes, or legacy row.
- Use `(user_id, service_date, direction)` as the primary key; absent decision means pending.
- A repeated identical decision and flexibility value must not refresh `decided_at`; changed state gets a server/database timestamp.
- Authenticate with the JWT, derive `user_id` from it, and verify the database role is `student` before decision or legacy-row access.
- Reject writes unless the student's linked weekly schedule has a Dudullu entry on the requested service date's weekday.
- Enable RLS on the new table and create no anon/authenticated table policies; access is through the server-side BFF only.
- Keep the legacy whole-day `change` action separate; it never creates or overwrites a per-leg decision.
- Legacy `pending_admin_approval`, `cancelled_by_admin`, or `in_progress` rows block both directions; `completed` rows are not candidates for a new plan.
- Reuse `buildScheduleDemands` and `classifyScheduleDecision`; do not duplicate the cutoff rule.
- With zero admitted demand, do not load vehicles, request a matrix, or call the optimizer.
- Preserve matrix, certificate, arc, exact-anchor, and physical-fleet validation. The admitted-demand solver path and two-anchor route case are now implemented locally; Package 2 remains incomplete until its separate 28-student gate passes.
- Do not apply a migration to Supabase, query live rows, backfill, publish, or deploy.
- Preserve unrelated dirty-tree changes. Existing `src/services/dudullu-preview.ts` edits and untracked `src/app/api/admin/dudullu-preview/` files are in-scope WIP: inspect and extend them, never replace them wholesale. Do not stage unrelated files.

---

**Approved design:** [student-leg confirmation design](../specs/2026-09-29-student-leg-confirmation-design.md), approved by the user on 2026-09-29.

**Starting evidence:** `src/services/daily-planning.ts` already models pickup/dropoff decisions and late-confirmation admission. The student endpoint still writes directionless `ride_requests`; the current student card sends whole-day actions. The admin preview route/service is in the working tree as Task 4 WIP and currently returns a fail-closed pending/legacy result without the new decision source or solver orchestration.

**Working-tree boundary:** Unrelated existing changes include `.gitignore`, `ACTIVE_ROADMAP.md`, `AGENTS.md`, `docs/UNIRIDE_WORKSTATE.md`, `docs/superpowers/plans/2026-09-24-dudullu-package2-daily-preview.md`, decoder files/tests under `uniride_core/`, and `INSTRUCTION_REVIEW_2026-09-07.md`. Keep these out of task staging unless a later, separately authorized task needs them.

## File Map and Interfaces

| File | Responsibility |
|---|---|
| `supabase/migrations/20260929_create_student_leg_decisions.sql` | Add the constrained latest-state table, timestamp trigger, and RLS with no client policies. |
| `supabase/schema.sql`, `supabase/rls_policies.sql` | Keep canonical schema and RLS enablement consistent with the migration. |
| `src/types/db.ts`, `src/lib/supabase.ts` | Type the stored row and register the table with Supabase's `Database` type. |
| `src/services/istanbul-service-date.ts` | Export `isRealServiceDate(value: string): boolean` and `serviceDateBounds(serviceDate: string): { start: string; end: string }` for both APIs. |
| `src/services/istanbul-service-date.test.ts` | Check invalid date rejection and the local-day `[start, end)` conversion. |
| `src/app/api/ride-confirmation/route.ts` | Student JWT/role boundary, directional GET/POST, active-schedule check, and preserved legacy `change` path. |
| `src/app/api/ride-confirmation/route.test.ts` | Auth, validation, ownership, schedule eligibility, directional independence, legacy action, and redaction tests. |
| `src/components/student/schedule-confirmation-card.tsx` | Display and mutate pickup/dropoff decisions independently; retain the legacy change-request action. |
| `src/components/student/schedule-confirmation-card.test.tsx` | Verify each control sends only its direction and renders refreshed state. |
| `messages/en.json`, `messages/tr.json` | Add matching localized labels/statuses for the two legs and legacy admin blocker. |
| `src/app/api/admin/dudullu-preview/route.ts` | Load decisions and blockers, admit valid legs, and orchestrate the existing snapshot/optimizer path. |
| `src/app/api/admin/dudullu-preview/route.test.ts` | Verify zero-work behavior, blockers, and exact-anchor solver calls at the transport boundary. |
| `src/services/daily-planning.test.ts` | Keep classifier and decision mapping behavior covered, including the cutoff. |
| `src/services/dudullu-preview.ts`, `src/services/dudullu-preview.test.ts` | Preserve and exercise the existing pure route/certificate/arc/fleet gates. |

**Stored row:**

```ts
interface DbStudentLegDecision {
  user_id: string;
  service_date: string;
  direction: "pickup" | "dropoff";
  decision: "confirmed" | "cancelled";
  decided_at: string;
  flexibility_minutes: number;
}
```

**Student read response:**

```ts
import type { DemandAdmission } from "@/services/daily-planning";

interface StudentLegView {
  decision: "pending" | "confirmed" | "cancelled";
  admission: DemandAdmission;
}

interface StudentLegStateResponse {
  legs: Record<"pickup" | "dropoff", StudentLegView>;
  legacyBlocker: boolean;
}
```

`admission` is produced by `classifyScheduleDecision` so a stored late `confirmed` decision can still display as `pending_admin_approval`. The stored `decision` remains the student's choice; the view does not turn an unapproved late confirmation into demand.

## Task 1: Add the per-leg database contract

**Files:** Create the numbered migration; modify `supabase/schema.sql`, `supabase/rls_policies.sql`, `src/types/db.ts`, and `src/lib/supabase.ts`.

**Produces:** `student_leg_decisions` with a database-enforced key/domain, server-owned `decided_at`, RLS enabled, and matching TypeScript table types.

- [ ] **Step 1: Add the table and timestamp trigger to the migration.** Use the same DDL in the canonical schema. Do not add `created_at`, `updated_at`, policies, history rows, or a second decision table.

```sql
CREATE TABLE IF NOT EXISTS public.student_leg_decisions (
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  service_date DATE NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('pickup', 'dropoff')),
  decision TEXT NOT NULL CHECK (decision IN ('confirmed', 'cancelled')),
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  flexibility_minutes INTEGER NOT NULL DEFAULT 0
    CHECK (flexibility_minutes BETWEEN 0 AND 1439),
  PRIMARY KEY (user_id, service_date, direction)
);

CREATE OR REPLACE FUNCTION public.set_student_leg_decided_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.decided_at := clock_timestamp();
  ELSIF ROW(NEW.decision, NEW.flexibility_minutes) IS DISTINCT FROM
        ROW(OLD.decision, OLD.flexibility_minutes) THEN
    NEW.decided_at := clock_timestamp();
  ELSE
    NEW.decided_at := OLD.decided_at;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS student_leg_decisions_set_decided_at
  ON public.student_leg_decisions;
CREATE TRIGGER student_leg_decisions_set_decided_at
BEFORE INSERT OR UPDATE ON public.student_leg_decisions
FOR EACH ROW EXECUTE FUNCTION public.set_student_leg_decided_at();

ALTER TABLE public.student_leg_decisions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.student_leg_decisions FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.student_leg_decisions TO service_role;
```

Expected: the table has exactly one row per student/date/direction; an update with the same decision/flexibility preserves `decided_at`; a changed state receives database time. There is deliberately no direct client policy.

- [ ] **Step 2: Mirror the table and RLS state in the canonical files.** Add the table/trigger once in `supabase/schema.sql`; add only `ALTER TABLE public.student_leg_decisions ENABLE ROW LEVEL SECURITY;` to the RLS enablement list in `supabase/rls_policies.sql`. Do not create select/insert/update policies.

- [ ] **Step 3: Add the database row and Supabase table typing.** Define `DbStudentLegDecision` in `src/types/db.ts`; import it in `src/lib/supabase.ts` and register:

```ts
student_leg_decisions: {
  Row: DbStudentLegDecision;
  Insert: Omit<DbStudentLegDecision, "decided_at">;
  Update: Partial<Pick<DbStudentLegDecision, "decision" | "flexibility_minutes">>;
  Relationships: [];
};
```

- [ ] **Step 4: Verify the declarative contract without touching a live database.** Run `npm.cmd run typecheck` and `git diff --check`; compare migration, canonical schema, RLS, grants, and TypeScript columns/checks/key manually. The repo has no local SQL test harness in this workflow, so record that DDL was reviewed for parity but not executed; do not add a live-DB dependency. Expected: typecheck exits 0; no whitespace errors; no Supabase migration is applied.

## Task 2: Implement the student BFF contract

**Files:** Modify `src/app/api/ride-confirmation/route.ts` and its existing `route.test.ts`; add `src/services/istanbul-service-date.ts` and its test; update the preview route to reuse the shared day-boundary helper instead of retaining a second copy.

**Consumes:** Task 1 table. **Produces:** `GET ?date=YYYY-MM-DD` returning both leg decisions/admissions plus a legacy blocker, and directional `POST` for one leg.

- [ ] **Step 1: Add failing authentication and strict-body tests.** Cover unauthenticated requests with no Supabase client; non-student requests with no decision/legacy reads; and rejection of missing direction, body-supplied `userId`, unknown fields, invalid calendar date, invalid direction, and flexibility outside `0..1439`.

```ts
const request = new Request("http://localhost/api/ride-confirmation", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({
    action: "confirm",
    rideDate: "2026-09-30",
    direction: "pickup",
  }),
});
```

Run: `npm.cmd test -- --run src/app/api/ride-confirmation/route.test.ts`
Expected before handler changes: new strict directional-body tests fail against the current whole-day implementation.

- [ ] **Step 2: Add failing per-leg POST and active-schedule tests.** Verify a valid pickup writes only the pickup key; a dropoff decision remains unchanged; an identical retry performs no upsert and never supplies `decided_at`; and a date without a scheduled Dudullu entry returns the fixed `409` without a decision write.

- [ ] **Step 3: Add failing GET and legacy-change tests.** Assert both leg states are returned only for the JWT user, a pending-admin-approval legacy row sets `legacyBlocker`, `action: "change"` still takes only the legacy review path, and a Supabase failure returns a fixed redacted error.

- [ ] **Step 4: Add failing tests for the shared local-date helper.** Test `isRealServiceDate("2026-02-30") === false` and `serviceDateBounds("2026-09-30")` equals `[2026-09-29T21:00:00.000Z, 2026-09-30T21:00:00.000Z)`.

- [ ] **Step 5: Implement the shared helper and remove the preview route's duplicate.** Move the strict `YYYY-MM-DD` round-trip check and Istanbul `[start, end)` conversion into `src/services/istanbul-service-date.ts`; export `isRealServiceDate(value: string): boolean` and `serviceDateBounds(serviceDate: string): { start: string; end: string }`; use both from the student and preview routes. Keep this module free of database/network dependencies. Run: `npm.cmd test -- --run src/services/istanbul-service-date.test.ts`. Expected: PASS.

- [ ] **Step 6: Implement authentication and strict input validation.** Authenticate with `getCurrentUserFromRequest`; accept only a strict directional `confirm`/`cancel` body or the existing legacy `change` schema; reject invalid calendar dates with `isRealServiceDate` before decision/legacy reads or writes. Derive the only `userId` from the JWT. Return fixed redacted errors.

```ts
const directionalSchema = z.object({
  action: z.enum(["confirm", "cancel"]),
  rideDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  direction: z.enum(["pickup", "dropoff"]),
  flexibilityMinutes: z.number().int().min(0).max(1439).default(0),
}).strict();
```

- [ ] **Step 7: Implement role and active-schedule gates.** Read `users.role` and `weekly_schedule_id` only after JWT/body/date validation; require `student`, load the linked schedule, verify its `user_id`, then require a Dudullu entry for `serviceDayOfWeek(rideDate)`. Return a fixed `409` if no matching service exists. Do not select decision/legacy rows or write before these gates pass.

- [ ] **Step 8: Upsert exactly one decision row and keep `change` isolated.** Read the current key after all auth/role/schedule gates; if decision and flexibility are identical, return without an upsert. Otherwise `confirm` writes `decision: "confirmed"`; `cancel` writes `decision: "cancelled"` and flexibility `0`. Use conflict key `user_id,service_date,direction`; omit `decided_at` so the database trigger owns it and handles concurrent identical updates. Do not create/update `ride_requests` for directional actions. Route `change` through the existing whole-day administrator-review behavior and never modify a decision row.

```ts
await adminClient.from("student_leg_decisions").upsert(
  {
    user_id: authUser.id,
    service_date: rideDate,
    direction,
    decision: action === "confirm" ? "confirmed" : "cancelled",
    flexibility_minutes: action === "confirm" ? flexibilityMinutes : 0,
  },
  { onConflict: "user_id,service_date,direction" },
);
```

- [ ] **Step 9: Implement GET projection and run the route tests.** Query decisions by JWT user ID and exact service date; query legacy rows for that user's Istanbul service-day interval; only `pending_admin_approval`, `cancelled_by_admin`, and `in_progress` set `legacyBlocker`. Derive `decision` from the stored row, map it into the existing `StudentLegDecision` union, and use `classifyScheduleDecision` for effective `admission`. Missing rows return `pending`/`pending_student_confirmation`. Run: `npm.cmd test -- --run src/app/api/ride-confirmation/route.test.ts src/services/istanbul-service-date.test.ts`. Expected: all pass.

## Task 3: Split the student controls by direction

**Files:** Modify `src/components/student/schedule-confirmation-card.tsx`, `messages/en.json`, and `messages/tr.json`; create `src/components/student/schedule-confirmation-card.test.tsx`.

**Consumes:** Task 2 GET/POST contract. **Produces:** independent pickup/dropoff states and actions in the current dashboard card.

- [ ] **Step 1: Add a failing component test for pickup-only confirmation.** Mock the authenticated fetch and translations using the repository's Vitest/Testing Library setup. Render the card for `2026-09-30`, confirm pickup, and assert the POST body contains `direction: "pickup"` while dropoff remains pending.

```ts
expect(fetchMock).toHaveBeenCalledWith("/api/ride-confirmation", expect.objectContaining({
  method: "POST",
  body: JSON.stringify({
    action: "confirm",
    rideDate: "2026-09-30",
    direction: "pickup",
  }),
}));
```

Run: `npm.cmd test -- --run src/components/student/schedule-confirmation-card.test.tsx`
Expected before component changes: FAIL because the current card submits a whole-day action without `direction`.

- [ ] **Step 2: Add a failing dropoff-cancellation test.** Confirm pickup first, cancel dropoff second, and assert the second request has `direction: "dropoff"`; verify pickup remains confirmed after GET refresh.

- [ ] **Step 3: Load and render two leg states from GET.** Keep one shared fetch/auth helper, store `pickup` and `dropoff` independently, and use `admission` for late-confirmation display. Make `rideDate` required on `ScheduleConfirmationCardProps`; the existing dashboard already supplies it and mounts the card only when `hasRide` is true. A single `busyDirection: "pickup" | "dropoff" | null` prevents duplicate submission while leaving the other leg's state intact.

- [ ] **Step 4: Send only directional confirm/cancel actions and refresh state.** Use the exact required `rideDate`; remove the current `getNextWeekday()` fallback. The directional request body contains `action`, `rideDate`, `direction`, and no student ID or displayed service times. After success, reload GET state; preserve the current `change` action as a whole-day review request that does not write a leg decision.

- [ ] **Step 5: Add matching English/Turkish labels and run the component test.** Add translations for pickup, dropoff, pending, confirmed, cancelled, pending administrator review, confirm/cancel leg, and legacy blocker. Keep key structure aligned across both JSON files. Run `npm.cmd test -- --run src/components/student/schedule-confirmation-card.test.tsx`; expected: independent controls and rendered states pass.

## Task 4: Admit only explicit legs in the preview data boundary

**Files:** Extend the existing dirty `src/app/api/admin/dudullu-preview/route.ts` and `route.test.ts`; adjust `src/services/daily-planning.test.ts` only for required decision-classification coverage.

**Consumes:** Task 1 table and `classifyScheduleDecision`; **produces:** one date-scoped demand set with explicit decisions and fail-closed legacy blockers.

- [ ] **Step 1: Add failing no-decision and one-leg tests.** With no decision rows, assert both legs remain pending and `NO_ADMITTED_DEMAND` is returned with no vehicles/matrix/optimizer calls. With pickup confirmed and dropoff cancelled, assert only pickup is eligible.

```ts
expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
expect(optimizerFetchMock).not.toHaveBeenCalled();
expect(client.queries.map((query) => query.table)).not.toContain("vehicles");
expect(client.queries.map((query) => query.table)).toContain("student_leg_decisions");
```

In this no-decision fixture, assert the decision query is restricted to the Dudullu student IDs and requested service date. Add a separate no-Dudullu-schedule fixture and assert it does not query `student_leg_decisions`.

- [ ] **Step 2: Add failing cutoff and legacy-status tests.** A late explicit confirmation must be `pending_admin_approval`; each of `pending_admin_approval`, `cancelled_by_admin`, and `in_progress` blocks both legs. Legacy `confirmed`, `pending_student_confirmation`, `cancelled_by_student`, and `completed` rows never become positive demand; an old confirmed row does not override a new explicit decision.

- [ ] **Step 3: Load and map date-scoped decisions.** Query `student_leg_decisions` only for the target service date and Dudullu student IDs. Map `confirmed` to `{ status: "confirmed", confirmedAt: decided_at, flexibilityMinutes }`; map `cancelled` to `{ status: "cancelled", decidedAt: decided_at }`; absent rows remain undefined. Pass both directions through `buildScheduleDemands`.

- [ ] **Step 4: Apply legacy blockers without promoting old rows.** Query requests over the shared Istanbul `[start,end)` service-day bounds. A blocking legacy status prevents both of that student's legs from admission and adds `LEGACY_AMBIGUOUS_CONFIRMATION`; old directionless `confirmed` and pending-student rows never become positive demand. Preserve `SCHEDULE_DATA_INVALID` on malformed users/schedules/decision rows and return the existing fixed 503 on read errors.

- [ ] **Step 5: Run focused admission tests.** Run `npm.cmd test -- --run src/services/daily-planning.test.ts src/app/api/admin/dudullu-preview/route.test.ts`; expected: cutoff, directional, legacy-blocker, and zero-demand cases pass without matrix/optimizer calls.

## Task 5: Connect admitted exact-anchor groups to the existing preview solver path

**Files:** Extend `src/app/api/admin/dudullu-preview/route.ts`, its route tests, and the existing pure service/test only if its established input/result contract needs a gap closed.

**Consumes:** Task 4 admitted demands; existing `/api/v1/internal/matrix-snapshot`, `/api/v1/optimize`, `buildDudulluPreview`, certificate/arc/interval verification, and physical-fleet assignment. **Produces:** a nonpublishable preview that solves only explicitly admitted groups.

- [ ] **Step 1: Add a failing zero-demand transport test.** Assert zero admitted demand makes no vehicles query, matrix request, or optimizer call and returns the existing honest blocked/empty result.

- [ ] **Step 2: Add failing exact-anchor and solver-error tests.** Assert one admitted anchor makes one solver request; two distinct admitted anchors make exactly two requests with exact `target_time` values; no request includes a pending/cancelled occurrence. A failed snapshot, optimizer error, missing certificate, or invalid result must return a fixed blocked/indeterminate preview and never `publishable: true`.

```ts
const optimizationCalls = optimizerFetchMock.mock.calls
  .filter(([path]) => path === "/api/v1/optimize");
expect(optimizationCalls).toHaveLength(2);
const requestBodies = optimizationCalls.map(([, init]) =>
  JSON.parse((init as RequestInit).body as string),
);
expect(requestBodies.map((body) => body.target_time).sort()).toEqual(["08:30", "17:15"]);
expect(requestBodies.every((body) => body.expected_matrix_sha256 === "a".repeat(64))).toBe(true);
```

- [ ] **Step 3: Short-circuit before fleet, snapshot, and solver work when no leg is admitted.** Return the current honest empty/blocked result with pending/legacy reason codes. Do not manufacture a job from schedules or directionless rows.

- [ ] **Step 4: For admitted demand, load validated active vehicles and request one protected content-addressed matrix snapshot.** Use the canonical optimizer transport `optimizerFetch`; bind each `/api/v1/optimize` request to the returned SHA-256.

- [ ] **Step 5: Send one optimizer job per exact anchor.** Use `ga_split`, the exact date/direction/anchor, and only admitted occurrences. Process groups sequentially; do not merge distinct anchors to reduce calls.

- [ ] **Step 6: Pass every result through `buildDudulluPreview`.** Require solver success and certificate, independently validate all directed arcs/totals/occurrence coverage and full service-day intervals, then run physical-fleet assignment with wheelchair/seating capacity and cooldown. Preserve all existing fixed reason codes and never claim a global fleet optimum or publishability.

- [ ] **Step 7: Run preview-focused tests.** Run `npm.cmd test -- --run src/app/api/admin/dudullu-preview/route.test.ts src/services/dudullu-preview.test.ts`; expected: zero-call, one-group, two-anchor, certificate, arc, and fleet cases pass.

## Final Verification and Handoff

- [ ] Run `npm.cmd test -- --run src/app/api/ride-confirmation/route.test.ts src/services/istanbul-service-date.test.ts src/services/daily-planning.test.ts src/components/student/schedule-confirmation-card.test.tsx src/app/api/admin/dudullu-preview/route.test.ts src/services/dudullu-preview.test.ts`. Expected: all focused tests pass.
- [ ] Run `npm.cmd run typecheck`, `npm.cmd run lint -- --quiet`, and `git diff --check`; report exact exit results.
- [ ] Review the final diff and staged paths; preserve unrelated dirty changes and do not apply the SQL migration to Supabase or use live student data.
- [ ] Record the implementation checkpoint only after checks pass. Do not mark Package 2 complete until its deterministic 28-student gate and any required local readiness/smoke evidence pass. The current local implementation state and live-data boundary are recorded in `docs/UNIRIDE_WORKSTATE.md`.

## Self-Review

- Spec coverage: schema/constraints/RLS/types are Task 1; auth, strict inputs, active schedule, idempotency, date bounds, GET/POST and legacy `change` are Task 2; independent student UI is Task 3; explicit/late/cancelled/legacy admission is Task 4; zero-work and exact-anchor solver behavior with unchanged verification gates is Task 5; no-live-data and separate 28-student gate are global/final constraints.
- Type consistency: persisted `decision` maps into the existing `StudentLegDecision`; the API view carries both stored `decision` and `DemandAdmission`; planner demands retain `TripDirection`; optimizer jobs retain the existing service date/direction/exact anchor contract.
- Scope check: the DB, API, UI, and preview are one dependency chain required by the approved feature, not separately shippable independent subsystems. No driver, publication, notification, backfill, deployment, or unrelated roadmap/decoder work is included.
