# Dudullu Package 2 Daily Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An admin-only, read-only daily preview that reports certified routes, complete route intervals, and assignable physical vehicles for a service date. It must fail closed when demand, matrix, certificate, timing, or fleet evidence is incomplete.

**Architecture:** Extend the protected Python matrix provider to capture a content-addressed snapshot and reject solver jobs that use another version. Keep daily-demand and preview verification/assignment pure in TypeScript; a thin authenticated Next BFF loads live inputs and calls the canonical optimizer once per exact anchor. Persist nothing in this package.

**Tech Stack:** Python/FastAPI/Pydantic/pytest; TypeScript/Next.js/Supabase client/Vitest; Python `hashlib` from the standard library.

## Global Constraints

- Status: proposed for separate Package 2 approval. This document authorizes no code or live-data mutation by itself.
- Campus code `D.Kampus`; timezone `Europe/Istanbul`; pickup and dropoff are independent demand legs.
- Fixed previous-day 22:00 confirmation cutoff and 120-minute exception lead rule stay in `daily-planning.ts`.
- Preserve unrelated dirty `.gitignore`, `AGENTS.md`, and `INSTRUCTION_REVIEW_2026-09-07.md`.
- No database migration, publication, UI, automatic student shift, or claimed fleet saving in Package 2.

---

**Entry evidence:** Local OPS-01 reached PASS on 2026-09-23: the user reported 29 matrix nodes and 812 directed arcs; local HTTP logs and a direct provider check corroborated the aggregate. This is a local gate, not deployment acceptance. Recheck it before live testing.

**Approved contract:** [Dudullu daily operations design](../specs/2026-08-25-dudullu-daily-operations-planner-design.md), Package 2. Package 1's pure domain is complete. This plan stops before Package 3 persistence/publication and Package 4 UI.

**Current constraints verified at planning time (WIP `2998f7c`):**

- `src/services/daily-planning.ts` already creates separate pickup/dropoff occurrences, admissions, hourly waves, and exact-minute anchor groups. Reuse it.
- `optimizer_api/strategies/ga_split_strategy.py` obtains directed costs through `DataLoader`, uses scalar Sw/So capacity, and returns a depot-to-depot `route_details` chain. `objective_rank.py` ranks feasible results by route count before travel cost, but GA-Split is heuristic and does not prove a global route-count optimum. Route node names can be occurrence keys rather than physical location codes when students share an address.
- `/api/v1/optimize` accepts one `target_time`; `response_certifier.py` checks a response-derived matrix. The BFF must check returned arcs against a separate captured matrix snapshot. Route-step durations are serialized to two decimals.
- `time_matrix` has unique directed rows but no durable version column. Package 2 can use a content-addressed, immutable request snapshot; Package 3 will persist the matrix/certificate snapshot with plan versions. No migration is needed here.
- Current `ride_requests` stores pickup and dropoff times in one directionless row. The confirmation route may create such a row with a default 08:00/17:00 pair. It cannot prove two admitted legs. These legacy rows must be reported as ambiguous, never silently promoted to confirmed pickup and dropoff demand. Live preview may therefore be `BLOCKED-DATA` until the explicit-leg migration/workflow in Package 3/4.
- Preserve the unrelated modified `.gitignore`, `AGENTS.md`, and untracked `INSTRUCTION_REVIEW_2026-09-07.md`.

## Result contract

`POST /api/admin/dudullu-preview` accepts `{ "serviceDate": "YYYY-MM-DD" }`, validates the date, and requires `requireAdmin`. A successful HTTP response contains a status (`preview_ready`, `shortage`, `blocked_data`, or `indeterminate`), `publishable: false` (Package 2 never publishes), service date, matrix `{ id, version, sha256, source }` when available, hourly Sw/So demand, exact-anchor jobs, full route intervals, physical assignments, unassigned occurrence IDs, and fixed reason codes. Student details are limited to what the authenticated admin needs. No route, assignment, or matrix row is written to Supabase. The status must never call a heuristic result a proven global fleet minimum; if the bounded exact assignment search is exhausted, return `indeterminate`.

For each job, the request and result use a single service date, direction, and exact anchor; only admitted `confirmed`/`approved` occurrences enter the solver. A `success` flag and feasible certificate are both required. Every returned student occurrence is covered exactly once. Every returned step maps to a captured directed matrix arc (including the final arc back to `D.Kampus`); same-physical-location transitions created by duplicate student homes are the sole valid zero-minute self arc. Compare each serialized two-decimal response duration with its source at that precision, then calculate timing from the unrounded source. Missing or nonfinite arcs, broken chain, mismatched totals, times outside the service day, or an unrecognized occurrence invalidate the draft.

Pickup campus arrival is no later than its hard deadline; route start is calculated backward from that arrival, and the complete interval ends after the closing campus-to-depot arc. Dropoff begins no earlier than its hard-ready anchor and includes the final home-to-depot arc. Physical vehicle `cooldown_minutes` extends the nonoverlap check. One vehicle may serve different waves only when these complete intervals do not conflict. Day-level fleet count is the number of distinct assigned physical vehicle IDs, never the sum of per-job route counts.

## File map and task interfaces

| File | Responsibility |
|---|---|
| `optimizer_api/utils/matrix_repository.py` | Locked immutable matrix snapshot and canonical digest. |
| `optimizer_api/routers/readiness.py` | Protected snapshot HTTP boundary, reusing readiness validation. |
| `optimizer_api/models/schemas.py`, `optimizer_api/routers/optimization.py` | Optional expected-hash field and pre/post solve guard. |
| `src/services/dudullu-preview.ts` | Pure demand/route verification, timing, and bounded physical assignment. |
| `src/app/api/admin/dudullu-preview/route.ts` | Admin auth, live reads, optimizer orchestration, redacted response. |

The Python snapshot response is `{id, version, sha256, source, arcs}`. Each arc has `{origin_code, destination_code, duration_minutes}`. `sha256` is lowercase 64-character hex over the full loaded matrix; `id` is `time_matrix:sha256:<digest>` and `version` is that digest. `buildDudulluPreview({ serviceDate, demands, vehicles, matrix, jobs })` returns the result contract above, where `jobs` retains each request's exact anchor and optimizer response. These are the only cross-task interfaces; test-only dependency injection stays at the BFF transport boundary.
### Task 1: Matrix snapshot and solver hash guard

**Files:** `optimizer_api/utils/matrix_repository.py`, `optimizer_api/routers/readiness.py`, `optimizer_api/models/schemas.py`, `optimizer_api/routers/optimization.py`; tests in `optimizer_api/tests/test_matrix_repository.py`, `optimizer_api/tests/test_dudullu_matrix_readiness.py`, and new `optimizer_api/tests/test_optimization_matrix_binding.py`.

- [ ] **Step 1:** Add failing tests for a stable SHA-256 over sorted physical location pairs and exact numeric minutes; same rows in a different fetch order must have the same hash, a changed duration a different hash. Copy the rows under the repository lock. Reject coordinate fallback, stale/error state, incomplete required arcs, and failed forced refresh.
  First red test in `test_matrix_repository.py` (the two matrices represent the same directed graph):

  ```python
  from utils.matrix_repository import matrix_sha256

  def test_matrix_digest_is_order_independent():
      forward = matrix_sha256(["D.Kampus", "H1"], [[0, 7], [9, 0]])
      reordered = matrix_sha256(["H1", "D.Kampus"], [[0, 9], [7, 0]])
      changed = matrix_sha256(["D.Kampus", "H1"], [[0, 8], [9, 0]])
      assert forward == reordered
      assert forward != changed
  ```

  Run: `.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_matrix_repository.py::test_matrix_digest_is_order_independent -q`. Expected before implementation: FAIL because `matrix_sha256` is absent.
- [ ] **Step 2:** Implement one internal-key-only `POST /api/v1/internal/matrix-snapshot` using the existing readiness router. It accepts the same bounded location-code set as readiness, forces refresh, and returns the requested directed arcs plus `{ id: "time_matrix:sha256:<digest>", version: <digest>, sha256: <digest>, source: "supabase" }`. The digest identifies the full loaded matrix, while the returned arcs are the requested subset. Return fixed redacted errors; never log codes or source rows.
  Canonical digest core in `matrix_repository.py`; the snapshot method copies `locations` and `time_matrix` under `self._lock` before calling it:

  ```python
  def matrix_sha256(locations: list[str], matrix: list[list[float]]) -> str:
      entries = [
          [origin, destination, float(matrix[i][j]).hex()]
          for i, origin in enumerate(locations)
          for j, destination in enumerate(locations)
          if i != j
      ]
      entries.sort(key=lambda row: (row[0], row[1]))
      payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
      return hashlib.sha256(payload.encode("utf-8")).hexdigest()
  ```

  Import `json` and `hashlib` from the standard library and export `matrix_sha256` alongside the repository class. Run the red test again; expected PASS. Then run the endpoint's missing/stale/forced-refresh cases before the hash-guard edit.
- [ ] **Step 3:** Add optional `expected_matrix_sha256` to `OptimizationRequest`. For a preview call, compare the repository digest immediately before and after the canonical solve. A missing/unhealthy or changed snapshot fails the job; existing callers without this field retain their behavior. The BFF still performs independent arc verification against its saved snapshot.
- [ ] **Step 4:** Run `.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_matrix_repository.py optimizer_api/tests/test_dudullu_matrix_readiness.py optimizer_api/tests/test_optimization_matrix_binding.py -q`. Expected: all pass; mutation/order/fallback cases reject correctly. Review the diff and commit only Task 1 files.

### Task 2: Pure preview verification and full intervals

**Files:** new `src/services/dudullu-preview.ts` and `src/services/dudullu-preview.test.ts`; read-only reference `src/services/daily-planning.ts` and `src/services/optimizer-types.ts`.

- [ ] **Step 1:** Write failing Vitest cases for two distinct anchors in one hourly wave, duplicate physical locations with distinct occurrence IDs, a missing/mutated matrix arc, a valid zero-minute same-home arc, a false or absent certificate, duplicate/missing student coverage, wrong route total, and an omitted or changed closing depot arc. Reject each with a fixed reason code.
- [ ] **Step 2:** Implement a pure assembler that accepts already-built admitted demands, captured matrix snapshot, and canonical optimizer results. Use the request's occurrence-to-physical-location map, including the solver's duplicate-location occurrence-key rule; test collision cases against `student_occurrence_keys` behavior. Do not trust response `duration` or scheduled times as the matrix source.
  Independent arc check in `dudullu-preview.ts`; all route totals and interval sums use its returned source minutes:

  ```ts
  function verifiedArcMinutes(
    step: { location1: string; location2: string; duration: number },
    nodeToLocation: ReadonlyMap<string, string>,
    arcByPair: ReadonlyMap<string, number>,
  ): number {
    const from = nodeToLocation.get(step.location1);
    const to = nodeToLocation.get(step.location2);
    if (from === undefined || to === undefined) throw new Error("UNKNOWN_ROUTE_NODE");
    const source = from === to ? 0 : arcByPair.get(JSON.stringify([from, to]));
    if (
      source === undefined || !Number.isFinite(source) ||
      (from !== to && source <= 0) || !Number.isFinite(step.duration) ||
      Math.abs(step.duration - source) > 0.005000001
    ) throw new Error("MATRIX_ARC_MISMATCH");
    return source;
  }
  ```

  Run: `npm.cmd test -- --run src/services/dudullu-preview.test.ts -t "closing arc"`. Expected before implementation: FAIL; after implementation: PASS.
- [ ] **Step 3:** Add route interval tests: pickup backward timing, dropoff not-before timing, the closing arc for both directions, service-day boundaries, and a noninteger source duration that is rounded only for response comparison. Reject unsupported cross-midnight routes instead of clamping them. Keep `route_scheduling.py`'s response-derived legacy timing out of operational evidence.
- [ ] **Step 4:** Run `npm.cmd test -- --run src/services/dudullu-preview.test.ts` and `npm.cmd run typecheck`. Expected: all tests and typecheck pass. Commit only Task 2 files.

### Task 3: Physical fleet assignment and truthful shortage

**Files:** extend `src/services/dudullu-preview.ts` and its test.

- [ ] **Step 1:** Add failing cases for compatible Sw/So capacity, heterogeneous vehicles, exact endpoint/cooldown nonoverlap, pickup/dropoff reuse, insufficient fleet, and an alternative assignment needing fewer distinct vehicles than a first-fit assignment.
- [ ] **Step 2:** Assign complete route intervals to real active vehicle IDs after route formation. Use deterministic branch-and-bound over the small daily pilot, minimizing distinct vehicles among feasible assignments. Prune capacity/time conflicts; cap search by a fixed node budget. Return `indeterminate` if the budget is exhausted, rather than a false optimum. If no full assignment exists, return the unassigned route/occurrence IDs and `shortage` for this draft; do not claim that every possible re-optimization is infeasible.
  Compatibility core; run it for every route already assigned to the candidate vehicle:

  ```ts
  function canAssign(
    vehicle: { swCapacity: number; soCapacity: number; cooldownMinutes: number },
    route: { start: number; end: number; sw: number; so: number },
    assigned: readonly { start: number; end: number }[],
  ): boolean {
    return route.sw <= vehicle.swCapacity &&
      route.so <= vehicle.soCapacity &&
      assigned.every(other =>
        other.end + vehicle.cooldownMinutes <= route.start ||
        route.end + vehicle.cooldownMinutes <= other.start
      );
  }
  ```

  Run: `npm.cmd test -- --run src/services/dudullu-preview.test.ts -t "cooldown"`. Expected before implementation: FAIL; after implementation: PASS.
- [ ] **Step 3:** Report hourly Sw/So demand from admitted occurrences and hourly occupied vehicles from full intervals. Keep per-job solver vehicle labels separate from physical IDs.
- [ ] **Step 4:** Run `npm.cmd test -- --run src/services/dudullu-preview.test.ts` and `npm.cmd run typecheck`. Expected: all pass. Commit only Task 3 files.

### Task 4: Admin BFF and live-data admission boundary

**Files:** new `src/app/api/admin/dudullu-preview/route.ts` and `route.test.ts`; reuse `src/lib/admin-auth.ts`, `src/lib/supabase-admin.ts`, `src/lib/optimizer-server.ts`, and the pure service.

- [ ] **Step 1:** Add route tests before implementation: non-admin 401/403 and zero downstream calls; malformed service date 400; read failure fixed/redacted 503; ambiguous legacy request produces `blocked_data` and no solve; two admitted exact-anchor groups produce two canonical jobs with one target time each; solver error/certificate/hash/arc failure is nonpublishable.
  Authenticate before parsing or loading any data:

  ```ts
  export async function POST(request: NextRequest) {
    try {
      await requireAdmin(request);
      const parsed = z.object({
        serviceDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      }).strict().safeParse(await request.json());
      if (!parsed.success || !isRealServiceDate(parsed.data.serviceDate)) {
        return NextResponse.json({ error: "INVALID_SERVICE_DATE" }, { status: 400 });
      }
      return NextResponse.json(await loadAndBuildPreview(parsed.data.serviceDate));
    } catch (error) {
      if (error instanceof AppError && [401, 403].includes(error.statusCode)) { return NextResponse.json({ error: "ADMIN_REQUIRED" }, { status: error.statusCode }); }
      return NextResponse.json({ error: "PREVIEW_UNAVAILABLE" }, { status: 503 });
    }
  }
  ```

  `isRealServiceDate` checks UTC round-trip equality with the input; `loadAndBuildPreview` is a route-local function that performs the read-only queries and solver calls in Steps 2–3. Run: `npm.cmd test -- --run src/app/api/admin/dudullu-preview/route.test.ts -t "non-admin"`. Expected before implementation: FAIL; after implementation: PASS.
- [ ] **Step 2:** Query only the service-date Dudullu users, schedules, relevant request rows, and active vehicles needed for this response. Parse and validate schedule entries and capacity/cooldown fields; do not treat a schedule or a directionless `ride_requests` row as confirmed transport. Surface missing explicit leg decisions as `pending_student_confirmation`/`legacy_ambiguous_confirmation` reason codes. A zero-admitted-demand day is an honest empty/blocked result, not a fabricated route.
- [ ] **Step 3:** Request one protected matrix snapshot for the required physical locations. For each admitted exact-anchor group, call `optimizerFetch("/api/v1/optimize", { method: "POST", body: JSON.stringify(jobRequest) })` sequentially with `ga_split`, one `target_time`, direction, the matrix digest, and scalar capacity no greater than the maximum active compatible vehicle capacity. GA-Split's virtual route labels are requirements, not physical assignments. Fail closed if no active capacity exists. Assemble/verify all jobs with the pure service, then assign physical vehicles.
- [ ] **Step 4:** Return fixed error codes and redacted messages. Never echo provider errors, keys, Supabase rows, or raw addresses on failure. No public unauthenticated test hook, database writes, route persistence, or UI in this package.
- [ ] **Step 5:** Run `npm.cmd test -- --run src/app/api/admin/dudullu-preview/route.test.ts src/services/dudullu-preview.test.ts src/app/api/admin/dudullu-readiness/route.test.ts` and `npm.cmd run typecheck`. Expected: all pass. Commit only Task 4 files.

### Task 5: 28-student gate, regression checks, and handoff

**Files:** the two new test files above; `docs/UNIRIDE_WORKSTATE.md` and the Dudullu package status in `ACTIVE_ROADMAP.md` only after results are verified.

- [ ] **Step 1:** Build the 28-student fixture in the test, not a new production data source: 28 distinct students, 29 physical nodes including `D.Kampus`, 812 directed arcs, mixed Sw/So, separate pickup/dropoff admissions, multiple exact anchors within an hourly wave, and a deterministic fleet. Stub only database/transport boundaries; run the real pure preview verifier and matcher. Assert a complete certified preview or a truthful `shortage` with unassigned occurrence IDs. Add a mutated used-arc case that fails even while the solver certificate says feasible.
  Fixture matrix in the Vitest file; all values are deterministic and contain no live student data:

  ```ts
  const locations = [
    "D.Kampus",
    ...Array.from({ length: 28 }, (_, i) => "H" + String(i + 1).padStart(2, "0")),
  ];
  const arcs = locations.flatMap(origin_code =>
    locations.filter(destination_code => destination_code !== origin_code)
      .map(destination_code => ({ origin_code, destination_code, duration_minutes: 8 }))
  );
  expect(locations).toHaveLength(29);
  expect(arcs).toHaveLength(812);
  ```
- [ ] **Step 2:** Run the focused Python and frontend commands from Tasks 1–4, then `npm.cmd run typecheck`, `npm.cmd run lint`, and `git diff --check`. Run the full suites only if the changed boundaries or focused failures justify them. Record exact counts and any environment blocker; no live publish, data mutation, or savings claim.
- [ ] **Step 3:** In a credential-bearing local environment, recheck authenticated `/admin/readiness`; only then smoke-test the admin preview on a chosen service date. Record redacted status and matrix hash, not student identities or tokens. If legacy rows block admission, record that as the expected Package 3/4 prerequisite, not a Package 2 success with invented demand.
- [ ] **Step 4:** Update work state/roadmap with the actual gate, remaining live-data limitation, commits, and next package. Review each task diff; keep unrelated dirty files unchanged. Push only the reviewable implementation commits when the Package 2 plan has been approved and tests are green.

## Acceptance and stop conditions

- Pass: admin-only read-only API; one compatible anchor per solver call; source-backed matrix hash on every job; certificate plus independent complete-arc/coverage/timing checks; exact interval and cooldown-aware physical assignment; 28-student fixture gate; no false `publishable` or savings claim.
- Stop with a visible blocker: matrix unavailable/stale/changed, ambiguous leg admission, invalid certificate/arc, no capacity, unassignable routes, or exhausted assignment search. Never repair live DB data or weaken checks inside this package.
- Deferred: explicit per-leg request schema and confirmation workflow, durable matrix and plan-version snapshots, transactional publication/RLS, admin operations UI, cross-wave recommendations, deployed-production acceptance.
