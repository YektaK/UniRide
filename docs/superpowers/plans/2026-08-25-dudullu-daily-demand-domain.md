# Dudullu Daily Demand Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first production package: a pure, deterministic TypeScript domain that converts Dudullu weekly schedules and explicit student/admin decisions into independent pickup/dropoff demands, exact-anchor groups, hourly service waves, and policy assessments.

**Architecture:** Keep all code in one dependency-free production service with one focused Vitest file. The service accepts in-memory values and performs no Supabase, HTTP, solver, notification, or clock I/O. It preserves occurrence identity, groups for hourly reporting, partitions solver jobs by exact anchor, and exposes pure admission/shift decisions for later BFF orchestration.

**Tech Stack:** TypeScript, Vitest, existing Next.js path aliases, standard `Intl.DateTimeFormat` and `Date` APIs. No new package or lockfile change.

## Global Constraints

- Work only on `codex/dudullu-daily-planner-20260825` in `C:\tmp\UniRide-dudullu-daily-planner-20260825`.
- Treat `docs/superpowers/specs/2026-08-25-dudullu-daily-operations-planner-design.md` as authoritative.
- Dudullu only: schedule label `Dudullu` and depot code `D.Kampus`. Other or missing campus labels are reported, never guessed.
- Pickup and dropoff are separate occurrences and separate decisions.
- An hourly wave is a reporting/decision bucket. Different exact anchors inside the same hour must remain different anchor groups.
- This package performs no database write, API call, solver call, physical fleet assignment, driver assignment, publication, or cross-wave re-solve.
- Preserve the main `WIP` checkout and its user-owned `.gitignore` change.
- Use TDD for every behavior: write the failing assertion, run it and record the expected failure, implement the minimum code, rerun green.
- Do not add a date/time dependency. The policy timezone is fixed to `Europe/Istanbul` and wall-clock comparison must be explicit and covered by boundary tests.
- Throw on malformed service dates, times, negative buffers, duplicate student-direction occurrence IDs, or confirmed decisions without a valid timestamp. Do not silently normalize invalid inputs.
- Use stable sorting by service date, direction, boundary minute, anchor minute, and occurrence ID so repeated inputs are deterministic.

---

## Task 1: Pin the Pure Contracts, Settings, and Calendar Boundary

**Files:**

- Create: `src/services/daily-planning.test.ts`
- Create: `src/services/daily-planning.ts`

- [ ] **Step 1: Add the first failing contract/settings tests**

Create `src/services/daily-planning.test.ts` with imports from `./daily-planning` and tests that assert:

```typescript
expect(DEFAULT_DAILY_PLANNING_SETTINGS).toEqual({
  campusCode: "D.Kampus",
  timezone: "Europe/Istanbul",
  pickupArrivalBufferMinutes: 15,
  dropoffDepartureBufferMinutes: 15,
  confirmationCutoffHour: 22,
  exceptionLeadMinutes: 120,
});

expect(serviceDayOfWeek("2026-08-26")).toBe("wednesday");
expect(() => serviceDayOfWeek("2026-02-30")).toThrow("Invalid service date");
expect(parseClockMinutes("09:30")).toBe(570);
expect(() => parseClockMinutes("24:00")).toThrow("Invalid clock time");
```

- [ ] **Step 2: Run RED and record the expected missing-module/export failure**

Run:

```powershell
npm test -- --run src/services/daily-planning.test.ts
```

Expected: FAIL because `src/services/daily-planning.ts` or its exports do not exist.

- [ ] **Step 3: Add the minimum immutable contracts and validators**

Create `src/services/daily-planning.ts` and export:

```typescript
import type { ScheduleEntry } from "@/types";

export type TripDirection = "pickup" | "dropoff";
export type DemandSource = "schedule" | "student_exception" | "admin_override";
export type DemandAdmission =
  | "pending_student_confirmation"
  | "confirmed"
  | "pending_admin_approval"
  | "approved"
  | "cancelled";

export interface DailyPlanningSettings {
  readonly campusCode: "D.Kampus";
  readonly timezone: "Europe/Istanbul";
  readonly pickupArrivalBufferMinutes: number;
  readonly dropoffDepartureBufferMinutes: number;
  readonly confirmationCutoffHour: number;
  readonly exceptionLeadMinutes: number;
}

export const DEFAULT_DAILY_PLANNING_SETTINGS: Readonly<DailyPlanningSettings>;

export function parseClockMinutes(value: string): number;
export function serviceDayOfWeek(
  serviceDate: string,
): ScheduleEntry["dayOfWeek"];
```

Implementation requirements:

- `parseClockMinutes` accepts exactly `HH:mm` from `00:00` through `23:59`.
- `serviceDayOfWeek` validates a real `YYYY-MM-DD` calendar date using UTC calendar components, then maps Sunday through Saturday to the existing lowercase schedule enum.
- Freeze the default settings and validate copied settings at each public builder boundary; do not mutate caller input.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
npm test -- --run src/services/daily-planning.test.ts
npm run typecheck
```

Expected: all focused tests pass and TypeScript exits zero.

- [ ] **Step 5: Commit Task 1**

```powershell
git add src/services/daily-planning.ts src/services/daily-planning.test.ts
git commit -m "feat(planning): define Dudullu daily demand contracts"
```

---

## Task 2: Build Independent Schedule Demands and Exact-Anchor Waves

**Files:**

- Modify: `src/services/daily-planning.test.ts`
- Modify: `src/services/daily-planning.ts`

- [ ] **Step 1: Add failing schedule-demand tests**

Add fixtures for Wednesday `2026-08-26`:

- Dudullu class A: `09:30–11:00`.
- Dudullu class B: `14:15–17:05`.
- Çengelköy class: `08:00–09:00`.
- Two different students sharing physical location `L1`.

Assert:

```typescript
const result = buildScheduleDemands({
  studentId: "S1",
  locationCode: "L1",
  serviceDate: "2026-08-26",
  scheduleEntries: entries,
});

expect(result.demands).toMatchObject([
  {
    occurrenceId: "2026-08-26:pickup:S1",
    studentId: "S1",
    locationCode: "L1",
    campusCode: "D.Kampus",
    direction: "pickup",
    source: "schedule",
    admission: "pending_student_confirmation",
    classBoundaryMinutes: 570,
    anchorMinutes: 555,
    hardDeadlineMinutes: 555,
    waveKey: "PICKUP-09:00",
    anchorGroupKey: "PICKUP-09:00@555",
  },
  {
    occurrenceId: "2026-08-26:dropoff:S1",
    direction: "dropoff",
    classBoundaryMinutes: 1025,
    anchorMinutes: 1040,
    hardReadyMinutes: 1040,
    waveKey: "DROPOFF-17:00",
    anchorGroupKey: "DROPOFF-17:00@1040",
  },
]);

expect(result.excludedEntries).toEqual([
  { entryId: "cengel-1", reason: "other_campus", location: "Çengelköy" },
]);
```

Also assert:

- an entry with missing location is reported as `missing_campus`;
- a service day with no Dudullu class produces zero schedule demands;
- first Dudullu start and last Dudullu end are selected regardless of input order;
- custom 20/25-minute buffers alter only exact anchors, not hourly wave keys;
- the input schedule array is unchanged;
- two students at `L1` retain distinct occurrence IDs;
- two pickup demands with 09:00 and 09:30 boundaries share `PICKUP-09:00` but produce two anchor groups;
- grouping the same demands in reverse order returns the same ordered structure.

- [ ] **Step 2: Run RED**

```powershell
npm test -- --run src/services/daily-planning.test.ts
```

Expected: FAIL because the builders and contracts do not exist.

- [ ] **Step 3: Add the minimal schedule and wave contracts**

Export these shapes and functions:

```typescript
export interface DailyTripDemand {
  readonly occurrenceId: string;
  readonly studentId: string;
  readonly locationCode: string;
  readonly campusCode: "D.Kampus";
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly source: DemandSource;
  readonly admission: DemandAdmission;
  readonly classBoundaryMinutes: number;
  readonly waveKey: string;
  readonly anchorGroupKey: string;
  readonly anchorMinutes: number;
  readonly hardReadyMinutes?: number;
  readonly hardDeadlineMinutes?: number;
  readonly flexibilityMinutes: number;
  readonly emergencyException: boolean;
}

export interface ExcludedScheduleEntry {
  readonly entryId: string;
  readonly location?: string;
  readonly reason: "other_campus" | "missing_campus";
}

export interface BuildScheduleDemandsInput {
  readonly studentId: string;
  readonly locationCode: string;
  readonly serviceDate: string;
  readonly scheduleEntries: readonly ScheduleEntry[];
  readonly settings?: DailyPlanningSettings;
}

export function buildScheduleDemands(
  input: BuildScheduleDemandsInput,
): {
  readonly demands: readonly DailyTripDemand[];
  readonly excludedEntries: readonly ExcludedScheduleEntry[];
};

export interface ServiceAnchorGroup {
  readonly key: string;
  readonly anchorMinutes: number;
  readonly demands: readonly DailyTripDemand[];
}

export interface ServiceWave {
  readonly key: string;
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly classBoundaryHour: number;
  readonly demands: readonly DailyTripDemand[];
  readonly anchorGroups: readonly ServiceAnchorGroup[];
}

export function groupServiceWaves(
  demands: readonly DailyTripDemand[],
): readonly ServiceWave[];
```

Implementation rules:

- Match Dudullu with trimmed, Turkish-locale case-insensitive comparison to `Dudullu` or the canonical `D.Kampus` code.
- Filter by the service date's weekday before selecting first/last entries.
- Pickup uses first `startTime` minus pickup buffer as deadline.
- Dropoff uses last `endTime` plus dropoff buffer as ready time.
- Wave hour is the class boundary hour, not the buffered anchor hour.
- `groupServiceWaves` rejects duplicate occurrence IDs and never merges students at the same physical location.
- Return newly allocated arrays/objects. Do not mutate or sort caller arrays in place.

- [ ] **Step 4: Run GREEN and existing frontend boundary tests**

```powershell
npm test -- --run src/services/daily-planning.test.ts
npm test -- --run src/services/optimizer-boundary.test.ts src/services/optimizer-service.test.ts
npm run typecheck
```

Expected: all commands exit zero.

- [ ] **Step 5: Commit Task 2**

```powershell
git add src/services/daily-planning.ts src/services/daily-planning.test.ts
git commit -m "feat(planning): derive Dudullu service waves"
```

---

## Task 3: Apply Independent Confirmation Cutoff and Exception Admission

**Files:**

- Modify: `src/services/daily-planning.test.ts`
- Modify: `src/services/daily-planning.ts`

- [ ] **Step 1: Add failing independent-leg decision tests**

Define the discriminated decision contract:

```typescript
export type StudentLegDecision =
  | { readonly status: "pending"; readonly flexibilityMinutes?: number }
  | {
      readonly status: "confirmed";
      readonly confirmedAt: string;
      readonly flexibilityMinutes?: number;
    }
  | { readonly status: "cancelled"; readonly decidedAt: string };
```

At this task, extend `BuildScheduleDemandsInput` with:

```typescript
readonly decisions?: Partial<Record<TripDirection, StudentLegDecision>>;
```

The schedule builder must apply pickup and dropoff decisions independently.

For service date `2026-08-26`, assert:

- pickup confirmed at `2026-08-25T18:59:00Z` (21:59 Istanbul) is `confirmed`;
- dropoff confirmed at `2026-08-25T19:01:00Z` (22:01 Istanbul) is `pending_admin_approval`;
- an omitted leg remains `pending_student_confirmation`;
- a cancelled pickup does not cancel dropoff;
- confirmed decision without a parseable timestamp throws;
- negative flexibility throws.

- [ ] **Step 2: Run RED, implement the cutoff helper, then rerun GREEN**

Export:

```typescript
export function classifyScheduleDecision(
  decision: StudentLegDecision | undefined,
  serviceDate: string,
  settings?: DailyPlanningSettings,
): {
  readonly admission: DemandAdmission;
  readonly flexibilityMinutes: number;
};
```

Use one cached `Intl.DateTimeFormat` configured with `timeZone: "Europe/Istanbul"` and numeric date/time parts. Compare Istanbul wall-clock fields against previous-day 22:00. Never compare an unzoned local string or the host machine timezone.

Run:

```powershell
npm test -- --run src/services/daily-planning.test.ts
npm run typecheck
```

- [ ] **Step 3: Add failing no-class/late-exception tests**

Export and test:

```typescript
export interface ExceptionAdmissionInput {
  readonly requestId: string;
  readonly studentId: string;
  readonly locationCode: string;
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly requestedAnchorTime: string;
  readonly requestedAt: string;
  readonly flexibilityMinutes?: number;
  readonly adminApproval?: {
    readonly approved: boolean;
    readonly reason?: string;
  };
}

export function buildExceptionDemand(
  input: ExceptionAdmissionInput,
  settings?: DailyPlanningSettings,
): DailyTripDemand;
```

Assertions:

- no class is required to create an exception demand;
- source is `student_exception` and occurrence ID uses the request ID;
- all unapproved exceptions are `pending_admin_approval`;
- 150 minutes before the requested anchor is ordinary;
- 90 minutes before the requested anchor is `emergencyException: true`;
- emergency approval without a nonblank reason remains pending;
- emergency approval with a reason becomes `approved`;
- an ordinary approved exception becomes `approved`;
- pickup and dropoff requested anchors create independent demands and wave keys;
- invalid ISO timestamp, invalid anchor, empty IDs, or negative flexibility throws.

- [ ] **Step 4: Implement minimal exception admission and run GREEN**

Calculate lead time using Istanbul wall-clock minutes for the requested instant and service-date anchor. Do not call the database or current clock.

Run:

```powershell
npm test -- --run src/services/daily-planning.test.ts
npm run typecheck
```

- [ ] **Step 5: Commit Task 3**

```powershell
git add src/services/daily-planning.ts src/services/daily-planning.test.ts
git commit -m "feat(planning): enforce daily demand admission policy"
```

---

## Task 4: Pin Direction-Safe Shift Eligibility

**Files:**

- Modify: `src/services/daily-planning.test.ts`
- Modify: `src/services/daily-planning.ts`

- [ ] **Step 1: Add failing shift-assessment tests**

Export:

```typescript
export type ShiftRejectionReason =
  | "different_service_date"
  | "different_direction"
  | "unsafe_direction";

export interface ShiftAssessment {
  readonly canPreview: boolean;
  readonly requiresStudentReconfirmation: boolean;
  readonly deltaMinutes: number;
  readonly rejectionReason?: ShiftRejectionReason;
}

export function assessShiftEligibility(
  demand: DailyTripDemand,
  target: {
    readonly serviceDate: string;
    readonly direction: TripDirection;
    readonly anchorMinutes: number;
    readonly alternativeTimeRequested?: boolean;
  },
): ShiftAssessment;
```

Assert:

- pickup 60 minutes earlier with 60 minutes confirmed flexibility can preview without reconfirmation;
- dropoff 60 minutes later with 60 minutes flexibility can preview without reconfirmation;
- pickup later and dropoff earlier are rejected as `unsafe_direction` unless `alternativeTimeRequested` is true;
- a direction-safe movement beyond confirmed flexibility can be previewed but requires student reconfirmation;
- default zero flexibility therefore requires reconfirmation for any nonzero safe shift;
- same anchor requires no reconfirmation;
- different date or direction cannot preview;
- the function does not mutate the demand.

This function is only a policy precheck. Add a test name and comment stating that it must never claim vehicle savings; certified source/destination re-solves remain Package 5.

- [ ] **Step 2: Run RED, implement the pure comparator, and rerun GREEN**

```powershell
npm test -- --run src/services/daily-planning.test.ts
npm run typecheck
```

- [ ] **Step 3: Commit Task 4**

```powershell
git add src/services/daily-planning.ts src/services/daily-planning.test.ts
git commit -m "feat(planning): validate service-wave flexibility"
```

---

## Task 5: Package 1 Verification and Truthful Documentation

**Files:**

- Modify: `ACTIVE_ROADMAP.md`
- Modify: `CURRENT_ARCHITECTURE.md`
- Modify: `WORKLOG.md`
- Inspect, modify only if a specifically audited gap is closed: `UniRide_Ultimate_Audit.md`

- [ ] **Step 1: Run the Package 1 gate**

```powershell
npm test -- --run src/services/daily-planning.test.ts
npm test -- --run src/app/api/calculate-vehicles/route.test.ts src/app/api/optimize-route/route.test.ts src/services/optimizer-service.test.ts src/services/optimizer-boundary.test.ts src/app/api/driver/assignments/route.test.ts src/services/doubus/multi-vehicle-routing.test.ts
npm run typecheck
npm run lint
git diff --check
```

Acceptance:

- zero failed tests;
- zero TypeScript errors;
- zero ESLint errors; existing warning debt is reported separately and not silently increased;
- no database, generated CSV/report, dependency, lockfile, or Python solver file changed.

- [ ] **Step 2: Update only verified documentation**

Record:

- Package 1 is implemented and pure;
- Package 0 runtime/data readiness remains open;
- Package 2 preview API, authoritative matrix binding, full depot-chain timing, and fleet assignment remain open;
- Package 3+ remain planned;
- exact commands and results;
- branch and commit IDs;
- no claim that 28 live records were verified.

Do not mark the web product operational merely because the domain package passes.

- [ ] **Step 3: Run documentation checks and inspect the exact diff**

```powershell
git diff --check
git status --short --branch
git diff --stat
```

- [ ] **Step 4: Request an independent code review**

The reviewer must inspect correctness, timezone boundaries, deterministic grouping, occurrence preservation, mutation safety, scope compliance, and documentation truthfulness. Require exact file/line findings and rerun the focused test.

- [ ] **Step 5: Commit verified Package 1 documentation**

```powershell
git add ACTIVE_ROADMAP.md CURRENT_ARCHITECTURE.md WORKLOG.md UniRide_Ultimate_Audit.md
git commit -m "docs: track Dudullu planning domain foundation"
```

Omit `UniRide_Ultimate_Audit.md` from `git add` when it has no evidence-backed change.

---

## Archive Preconditions and Next Package Boundary

Package 2 must not begin until Package 1 passes every command above. Package 2 requires a separate approved plan covering:

1. read-only Dudullu data readiness;
2. authenticated admin BFF;
3. exact-anchor optimizer calls;
4. authoritative matrix artifact ID/version/hash and independent used-arc checks;
5. repaired full depot-to-depot timing;
6. two-stage day-level physical fleet assignment;
7. truthful shortage/non-publishable semantics.

Package 3 requires a separate migration/RLS plan and one transactional multi-wave change-set publication RPC. Package 5 may evaluate cross-wave savings only after Packages 2 and 3 are complete; it must compare certified before/after day-level physical fleet schedules and cannot use the legacy aggregate time-shift placeholder as evidence.