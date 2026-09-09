# Dudullu Daily Operations Planner Design

**Status:** Approved direction; implementation authorized on 2026-08-25
**Target branch:** `codex/dudullu-daily-planner-20260825`
**Verified base:** `60161adeb81b18b3798a9e0c2024163cabf63e50`
**Campus scope:** Dudullu only (`D.Kampus`)
**Timezone:** `Europe/Istanbul`

## 1. Goal

Build a working daily student-transport product that uses the existing Dudullu
student schedules and travel-time matrix to:

1. derive independent pickup and dropoff demand;
2. collect student confirmations and administrator-approved exceptions;
3. solve hourly service waves with minute-accurate route timing;
4. calculate the minimum required vehicle count before assigning active physical
   vehicles;
5. show which students ride in which vehicle and at what time;
6. allow evidence-backed manual movement between compatible adjacent waves;
7. version, review, publish, and revise operational plans safely.

The first release targets the existing approximately 28 Dudullu student stops.
The repository claim that 28 schedules were imported is historical evidence,
not proof of the current Supabase contents. Data readiness is therefore a
release gate.

## 2. Evidence and historical decisions

Live code and tests outrank these historical records, but the records preserve
the intended operating model:

- `archive/docs/04_Changelog.md:784` records an earlier import of 28 students
  into `weekly_schedules`.
- `uniride_core/algorithms/resource_profiler.py:139` records conversation item
  21: calculate demand in standard-vehicle units.
- `uniride_core/algorithms/resource_profiler.py:209` records conversation item
  23: expose hourly Sw/So demand.
- `uniride_core/algorithms/resource_profiler.py:420` records conversation item
  19: prevent pickup and dropoff use of the same vehicle from overlapping.
- `uniride_core/algorithms/resource_profiler.py:461` records conversation item
  14: move student travel times to minimize vehicle resources.
- `src/components/admin/resource-histogram.tsx:7` states that the demand chart's
  x-axis is hourly and pickup/dropoff vehicle requirements are stacked.
- `src/components/admin/resource-tracks.tsx:7` states that vehicle-use blocks
  align to the same hourly axis.
- `archive/docs/API_REFERENCE.md:648` preserves the earlier `target_time`,
  `time_window_size`, and `offset_minutes` scheduling contract.
- `archive/docs/04_Changelog.md:757` records hybrid student confirmation,
  manual driver assignment, fixed location codes, and Supabase Realtime as
  approved product decisions.

The current implementation only partially represents that design. Its
time-shift suggestion uses aggregate placeholder identities and only reacts to
capacity overflow; it does not prove that shifting one or two real students
reduces a route or vehicle. The production IE dashboard also fabricates demo
resource blocks. Those behaviors are not accepted as the new planner.

## 3. Confirmed product decisions

### 3.1 Campus and matrix

- Only Dudullu is in scope.
- `D.Kampus` is the depot/campus identifier.
- Schedule entries for other campuses, including Çengelköy, are excluded and
  reported; they are never silently mapped to Dudullu.
- Ride confirmation persists the canonical Dudullu campus address and
  coordinates.
- Every demand retains the student occurrence identity separately from the
  physical location code. Students sharing a stop remain separate demand.

### 3.2 Independent trip legs

Each student/day may have two independent demands:

- `pickup`: home/registered stop to `D.Kampus`;
- `dropoff`: `D.Kampus` to home/registered stop.

A student can confirm either leg, both legs, or neither leg. A single database
row must not ambiguously represent both directions.

### 3.3 Default demand from the weekly schedule

- For pickup, use the first Dudullu class of the service date.
- For dropoff, use the last Dudullu class of the service date.
- Default campus-arrival deadline is 15 minutes before the first class.
- Default campus-departure time is 15 minutes after the last class.
- Both offsets are administrator-configurable and captured in the plan's
  immutable settings snapshot.
- Home pickup time is not `class start - 30 minutes`; it is calculated backward
  from the certified route and common campus-arrival deadline.

### 3.4 Demand admission

- Schedule-derived demands begin as candidates awaiting student confirmation.
- Normal confirmation closes at 22:00 on the previous calendar day in
  `Europe/Istanbul`.
- At cutoff, an idempotent job creates a draft daily plan.
- Late confirmation, a no-class ride, or a request for a different time enters
  `pending_admin_approval`.
- The minimum lead time for ordinary exceptions is configurable and defaults to
  120 minutes before the requested campus-arrival deadline (pickup) or
  campus-departure time (dropoff).
- Requests inside the lead-time boundary are marked emergency exceptions and
  require an explicit administrator reason. They are never auto-admitted.
- The administrator can add or remove demand before publication, with an audit
  record.

### 3.5 Hourly service waves with minute-accurate execution

The service wave is the hourly demand, reporting, and administrator decision
unit; it is not permission to round operational time or combine incompatible
deadlines:

- examples: `PICKUP-09:00`, `DROPOFF-17:00`;
- the wave groups students whose relevant first-class or last-class boundary
  belongs to that hour;
- the exact arrival/departure anchor remains a minute value such as 08:45 or
  17:15;
- every pickup demand carries a hard campus-arrival deadline and every dropoff
  demand carries a hard campus-ready/not-before time;
- demands in one hourly wave are partitioned into exact-anchor groups before a
  solver call. The current optimizer accepts one request-level `target_time`, so
  mixed anchors must not be sent in one request unless a later verified contract
  adds per-demand windows;
- pickup routes in one exact-anchor group share a campus-arrival deadline, but
  each vehicle's route start and each student's pickup time are calculated
  backward independently;
- dropoff routes in one exact-anchor group share the configured
  campus-departure anchor;
- dashboard reporting is hourly while route and resource intervals remain
  minute-accurate.

Non-hour class boundaries do not get their operational time rounded. They are
assigned to the containing hourly wave while retaining the exact anchor and an
anchor-group identity. For example, 09:00 and 09:30 class starts may appear in
the same `PICKUP-09:00` wave but are separate solver jobs unless their hard
windows are proven compatible.

Operational vehicle intervals are complete depot-to-depot intervals, including
the closing campus arc. The current route-scheduling helper's abbreviated
arrival/departure output is not accepted as operational evidence until Package
2 repairs and tests its full-chain timing semantics.

### 3.6 Two-stage vehicle planning

Stage 1 produces certified route requirements per exact-anchor group without
pretending that a physical plate has already been assigned:

1. satisfy all admitted occurrences and hard constraints;
2. minimize vehicle count;
3. minimize total route duration;
4. minimize the longest student ride and imbalance.

Each resulting route declares its Sw/So capacity requirement and exact occupied
time interval.

Stage 2 assigns active physical vehicles across the entire affected service day:

- a vehicle must cover the route's Sw and So load;
- vehicle intervals, including the vehicle's `cooldown_minutes`, must not
  overlap;
- the same vehicle can be reused across waves when its intervals do not overlap;
- assignment minimizes additional physical vehicles and then idle/repositioning
  cost where data exists;
- if the fleet cannot cover the certified route set, the result reports both
  theoretical need and operational shortage; it never reports success while
  hiding unassigned students.

The production resource objective is the minimum number of distinct physical
vehicles required by the complete day-level interval schedule. Summed route
count is diagnostic and remains the canonical per-solver-job objective; it is
not accepted as proof of a fleet saving across waves. Any unassigned admitted
demand or operational fleet shortage makes a draft non-publishable even when
each individual route is certificate-feasible.

### 3.7 Driver assignment

- Physical vehicles are assigned automatically.
- Drivers are assigned manually by an administrator in the first product
  release.
- The system rejects overlapping driver assignments.
- Driver assignment cannot weaken route feasibility or vehicle capacity.
- Automatic driver rostering is explicitly deferred.

### 3.8 Resource-shift decision support

Cross-wave movement changes a service promise and is not a hidden solver move.
The system generates recommendations; an administrator decides.

A candidate shift must:

1. keep the same service date, campus, and direction;
2. fall inside the student's declared flexibility window;
3. preserve the class-derived hard boundary unless the student explicitly
   requested an alternative time;
4. re-solve both source and destination waves;
5. re-run physical vehicle interval assignment for the affected day;
6. remain certificate-feasible;
7. report the exact changes in vehicle count, total duration, longest ride,
   affected students, vehicles, and drivers.

Here, `vehicle count` means the day-level distinct physical fleet required after
interval assignment. Per-wave route-count changes are reported separately.

Direction-safe defaults are:

- pickup may move to an earlier wave, not to a wave that violates the campus
  arrival deadline;
- dropoff may move to a later wave, not before the last class plus departure
  buffer;
- other movements require an explicit alternative-time request.

Student confirmation records a flexibility allowance per leg. Default is zero;
the UI may offer administrator-configurable presets such as 30 or 60 minutes.
If a proposed shift exceeds the already confirmed allowance, the new draft
requires student reconfirmation before publication.

A suggestion is admitted only when actual re-solving proves a lexicographic
improvement. A capacity-only estimate or the count `1-2 students` is a trigger
for evaluation, not evidence of savings.

### 3.9 Plan versions and late changes

- At 22:00, the system generates a draft, not an active plan.
- The administrator reviews routes, shortages, shift suggestions, and drivers.
- Every replan creates an affected-wave change set with one revision ID.
- Publication is atomic for the entire change set: all source/destination wave
  versions and dependent vehicle/driver assignments are published together, or
  none are.
- An approved late/exception demand creates a new draft change set containing
  the affected wave and every physical-vehicle assignment whose interval may
  conflict.
- The currently published version remains authoritative until the replacement
  is explicitly published.
- Publication stores the change-set ID, previous version links, settings
  snapshot, matrix artifact identity/version/hash, request IDs,
  solver/certificate metadata, administrator identity, and reason.
- Superseded versions are immutable and auditable.
- A changed published assignment produces notifications for affected students
  and drivers.

### 3.10 Objective and change stability

Initial production planning uses the strict ordering:

```text
feasible
  -> no shortage or unassigned admitted demand
  -> fewer day-level physical vehicles required
  -> fewer routes within each exact-anchor solver job
  -> lower total route duration
  -> lower maximum student ride / better balance
```

Replanning adds disruption only after those terms:

```text
feasible
  -> no shortage or unassigned admitted demand
  -> fewer day-level physical vehicles required
  -> fewer routes within each exact-anchor solver job
  -> lower total route duration
  -> lower maximum student ride / better balance
  -> fewer changed student-route and vehicle-route assignments
```

This extends, rather than contradicts, the existing canonical core objective
`(feasible, vehicles, travel_cost)`: core `vehicles` is the route count for one
solver job, while production compares day-level distinct physical vehicles
after interval assignment. Production orchestration owns shortage,
service-quality, fleet-reuse, and disruption terms; academic objectives remain
unchanged.

## 4. Selected architecture

### 4.1 Recommended approach: production daily-plan orchestrator

Keep product scheduling in the production boundary:

```text
weekly schedules + confirmations + admin exceptions
                    |
                    v
         pure DailyDemandBuilder
                    |
                    v
       hourly ServiceWave collection
                    |
                    v
 authenticated Next.js BFF / daily-plan service
                    |
                    v
 canonical FastAPI optimize per exact-anchor group
                    |
                    v
 feasibility certificate + minute route intervals
                    |
                    v
 physical vehicle interval assignment
                    |
                    v
 versioned draft -> reviewed -> published plan
```

Production owns schedules, consent, campus, dates, vehicles, drivers,
notifications, versions, and operational errors. `uniride_core` continues to
own neutral objectives, routing constraints, and certificates. No production
DTO or Supabase model moves into the academic engine.

### 4.2 Rejected: extend the legacy DouBus service island

`src/services/doubus` is not the base for the new planner. It duplicates the
canonical optimizer path, groups every confirmed request into both pickup and
dropoff, uses rolling rather than declared hourly waves, takes capacity from
the first active vehicle, and is not reached by the active planning page.
Useful historical intent is preserved in this specification; the code can be
retired after replacement gates pass.

### 4.3 Rejected: move the entire daily workflow into FastAPI/core

Schedules, confirmations, administrator approvals, Supabase identities,
drivers, notifications, and plan publication are product concerns. Moving them
into `uniride_core` would violate the repository's verified dual-engine
boundary and pollute academic contracts.

## 5. Minimal domain contracts

The first implementation package introduces pure TypeScript contracts without
database writes:

```typescript
type TripDirection = "pickup" | "dropoff";
type DemandSource = "schedule" | "student_exception" | "admin_override";
type DemandAdmission =
  | "pending_student_confirmation"
  | "confirmed"
  | "pending_admin_approval"
  | "approved"
  | "cancelled";

interface DailyPlanningSettings {
  campusCode: "D.Kampus";
  timezone: "Europe/Istanbul";
  pickupArrivalBufferMinutes: number;    // default 15
  dropoffDepartureBufferMinutes: number; // default 15
  confirmationCutoffHour: number;        // default 22
  exceptionLeadMinutes: number;          // default 120
}

interface DailyTripDemand {
  occurrenceId: string;
  studentId: string;
  locationCode: string;
  serviceDate: string;
  direction: TripDirection;
  source: DemandSource;
  admission: DemandAdmission;
  waveKey: string;
  anchorGroupKey: string;
  anchorMinutes: number;
  hardReadyMinutes?: number;    // dropoff: do not depart before this minute
  hardDeadlineMinutes?: number; // pickup: arrive on campus by this minute
  flexibilityMinutes: number;
}

interface ServiceAnchorGroup {
  key: string;
  anchorMinutes: number;
  demands: DailyTripDemand[];
}

interface ServiceWave {
  key: string;
  serviceDate: string;
  direction: TripDirection;
  classBoundaryHour: number;
  demands: DailyTripDemand[];
  anchorGroups: ServiceAnchorGroup[];
}
```

The exact names may change during test-first implementation only when doing so
reduces duplication and the specification's behavior remains pinned by tests.

## 6. Persistence evolution

Do not overload the current ambiguous `ride_requests` semantics further.
Migrations will be additive and reversible:

1. add an explicit direction and service date to each trip request;
2. record source, admission/approval metadata, anchor, wave, flexibility, and
   administrator decision fields;
3. add slot/version lineage and settings/certificate snapshots to route plans;
4. link operational route and assignment rows to the published plan version;
5. replace `UNIQUE(date, timeslot)` with version-safe route identity;
6. add an affected-wave change-set/revision identity;
7. publish every wave version and dependent assignment in a change set through
   one transactional Supabase RPC;
8. enforce one current published version per date/campus/direction/wave;
9. retain RLS: students see/change their own eligible requests, drivers see
   their assignments, administrators own planning and publication.

Existing records require an explicit migration classification. Unknown or
ambiguous rows are quarantined from automatic planning rather than guessed.

## 7. Product UI

The active administrator page becomes a daily operations page with:

- service date, cutoff state, plan version, and publication state;
- data-readiness warnings for missing schedules, disability type, location
  code, matrix arcs, vehicles, and confirmations;
- hourly pickup/dropoff Sw/So demand and required/available vehicle counts;
- exact anchor and per-route start/end times;
- students grouped by route and physical vehicle;
- shortage and unassigned-demand panels;
- shift recommendations with before/after evidence;
- a source/destination wave replan preview;
- manual driver assignment with collision validation;
- atomic publish and a version-diff view.

The current fabricated IE resource blocks are removed. Missing data is shown as
missing, not simulated. GIS remains deferred until a backend geometry contract
exists.

## 8. Runtime and automation

- Add one idempotent daily-plan generation operation usable by both an
  administrator action and a scheduler.
- The scheduler adapter calls the same authenticated operation shortly after
  22:00; it contains no planning logic.
- Re-running the same date/settings/input version returns the same draft or an
  explicit no-op, not duplicate requests/plans.
- Durable scheduling mechanism is deployment-specific and must be selected
  explicitly; the product operation itself must not depend on an in-process
  Next.js timer.
- All heavy solver calls continue through the authenticated server-only BFF and
  receive feasibility certificates.

## 9. Failure behavior

Fail closed and keep the last published plan authoritative when:

- Supabase or the optimizer is unavailable;
- the Dudullu matrix is missing/incomplete/stale under its declared policy;
- a confirmed occurrence is missing from the certificate;
- vehicle or driver intervals overlap;
- an exception lacks required approval or lead-time reason;
- a shift falls outside confirmed flexibility;
- publication RPC fails.

The UI distinguishes `no demand`, `not generated`, `draft infeasible`,
`operational shortage`, and `service unavailable`.

## 10. Delivery packages and gates

### Package 0 — Runtime and data readiness

- matching Next.js/FastAPI internal keys and health smoke;
- read-only Dudullu data inventory;
- verify 28 student profiles/schedules/locations and 29-node matrix rather than
  trusting archived claims;
- enumerate active vehicles and drivers;
- no student identity in logs/reports.

**Gate:** one reproducible local startup command and a redacted readiness
report.

### Package 1 — Pure daily-demand and service-wave domain

- deterministic Dudullu schedule filtering;
- first/last class rules;
- independent pickup/dropoff occurrences;
- 15-minute configurable anchors;
- hourly wave grouping with minute-accurate anchors;
- confirmation/exception/lead-time policy;
- direction-safe flexibility rules.

**Gate:** focused Vitest suite proves dates, timezone boundaries, campus
filtering, duplicate locations, independent legs, non-hour classes, and shift
eligibility. No DB or solver mutation.

### Package 2 — Daily-plan preview API

- authenticated admin BFF;
- schedule/request/fleet data loading;
- data-readiness failures;
- canonical optimize calls and certificates per exact-anchor group;
- authoritative matrix artifact identity/version/hash on every draft and
  independent verification of every used response arc against that source;
- complete depot-to-depot route interval calculation, including the closing
  campus arc;
- two-stage physical vehicle assignment;
- hourly demand and exact resource intervals.

**Gate:** an in-memory 28-student fixture produces a complete certified preview,
or a truthful shortage/unassigned result. Every solver job has one compatible
anchor contract, every interval includes the closing depot arc, and every used
arc matches the bound authoritative matrix artifact. The existing
response-derived certificate alone is necessary but not sufficient.

### Package 3 — Versioned persistence and publication

- additive migrations and RLS;
- idempotent draft generation;
- transactional multi-wave change-set publication;
- route/vehicle/driver assignment persistence;
- immutable settings, matrix, and certificate snapshots.

**Gate:** concurrent publish tests prove one current published version per wave,
no partial source/destination publication, and no partial assignment state.

### Package 4 — Administrator daily operations UI

- real hourly demand and resource tracks;
- route/student/vehicle details;
- shortage, approval, driver, and publication workflows;
- remove demo data and retire the active manual-selection calculation flow.

**Gate:** browser/component tests cover loading, unavailable, infeasible,
shortage, draft, diff, and published states.

### Package 5 — Shift recommendation and affected-wave change-set replanning

- actual source/destination wave re-solves;
- lexicographic before/after comparison;
- flexibility and class-boundary enforcement;
- administrator preview/approval;
- versioned affected-wave change-set draft and notifications.

**Gate:** recommendations never claim savings without certified before/after
solutions, and a published plan is unchanged until explicit publication.

### Package 6 — Student and driver operational surfaces

- separate leg confirmation and exception request UI;
- next assignment and changed-plan notifications;
- driver assignment detail page;
- status transitions and audit visibility.

**Gate:** each role sees only authorized records; end-to-end fixture covers
confirmation through completed assignment.

### Deferred

- GIS/route geometry;
- automatic driver rostering;
- multi-campus planning;
- continuous real-time replanning;
- academic comparisons or algorithm promotion.

## 11. Verification strategy

- TDD for each behavioral addition: red test, minimal implementation, green
  focused suite, then regression suite.
- Pure domain tests use fixed Istanbul dates and in-memory records.
- API tests mock only external Supabase/optimizer boundaries, not domain logic.
- Solver outputs are independently certificate-checked.
- Persistence uses migration/RLS tests and transaction/concurrency tests.
- Each package runs `git diff --check`, TypeScript, relevant Vitest, relevant
  Python suites, and a clean-status audit before integration.

## 12. Documentation impact

After a package is verified, update:

- `ACTIVE_ROADMAP.md` to make working Dudullu daily operations the top product
  priority and record actual package status;
- `CURRENT_ARCHITECTURE.md` with the new production orchestration path;
- `WORKLOG.md` with commands and exact results;
- `UniRide_Ultimate_Audit.md` only when an audited gap is genuinely closed;
- `README.md` with reproducible two-service startup once Package 0 passes.

Documentation must not mark future packages complete based on this design.
