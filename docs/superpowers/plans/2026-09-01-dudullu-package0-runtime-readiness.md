# Dudullu Package 0 Runtime and Data Readiness Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to implement this plan task-by-task. Use `test-driven-development` for every production change and `finishing-a-development-branch` before integration.

**Goal:** Prove that the local Next.js/FastAPI stack can start with one command and produce an authenticated, redacted, read-only Dudullu readiness report from current Supabase and matrix data.

**Architecture:** Keep operational data ownership in the Next.js server boundary and matrix truth in the FastAPI `TimeMatrixRepository`. A protected internal FastAPI endpoint evaluates only the requested Dudullu location set. An admin-only Next.js BFF reads narrow Supabase projections, calls that endpoint server-to-server, and returns aggregate counts and reason codes only. A dependency-free Node launcher gives both services one in-memory shared key, starts both processes, and performs a protected smoke check. No route solving, publication, schema migration, or UI is part of Package 0.

**Tech Stack:** Next.js 16 route handlers, TypeScript, Vitest, Supabase service-role server client, FastAPI, Pydantic, pytest, Node standard library.

**Authoritative design:** `docs/superpowers/specs/2026-08-25-dudullu-daily-operations-planner-design.md:458-468`

**Baseline verified on 2026-09-01:**

- branch `codex/dudullu-package0-readiness-20260901` starts at `origin/WIP` `9972f820820f638e7d62a1aa1d1fbbf6f8c62ee6`;
- focused Vitest baseline: 40 passed;
- focused FastAPI matrix/auth baseline: 43 passed;
- live Supabase inventory was attempted without printing secrets or identities and was blocked by `HttpRequestException -> SocketException` before an HTTP response;
- the original WIP checkout's user-owned `.gitignore` change is outside this worktree and must remain untouched.

## Non-goals and hard boundaries

- Do not create or mutate schedules, requests, plans, vehicles, drivers, matrices, or users.
- Do not generate daily demand, call a solver, claim a vehicle saving, or publish a plan.
- Do not add matrix artifact ID/version/hash; Package 2 owns provenance binding.
- Do not add an administrator page; Package 0 exposes the authenticated report contract only.
- Do not log or return names, emails, student numbers, addresses, user IDs, schedule IDs, location-code lists, missing arc pairs, URLs, keys, or raw provider errors.
- Do not make historical `28 students / 29 nodes` an invariant. Report current counts and separate booleans comparing them with the historical expectation.
- Do not call the existing public `/health` a key-match proof. It remains public and unchanged.
- Do not describe driver accounts as active or available; the current schema has no driver availability/status field.

## Target readiness contract

The final admin response contains only aggregate data:

```json
{
  "ready": false,
  "historicalExpectation": {
    "studentCount": 28,
    "matrixNodeCount": 29,
    "matchesStudentCount": false,
    "matchesMatrixNodeCount": false
  },
  "students": {
    "total": 0,
    "completeProfiles": 0,
    "withDudulluSchedule": 0,
    "missingLocation": 0,
    "missingDisabilityType": 0,
    "missingOrMismatchedSchedule": 0,
    "distinctLocations": 0
  },
  "schedules": {
    "total": 0,
    "empty": 0,
    "malformed": 0,
    "orphaned": 0,
    "duplicateForStudent": 0
  },
  "fleet": {
    "configuredDrivers": 0,
    "vehicles": 0,
    "activeVehicles": 0,
    "usableActiveVehicles": 0
  },
  "matrix": {
    "source": "empty",
    "loaded": false,
    "stale": false,
    "hasError": true,
    "matrixLocationCount": 0,
    "requiredLocationCount": 0,
    "missingRequiredLocationCount": 0,
    "expectedRequiredDirectedArcCount": 0,
    "validRequiredDirectedArcCount": 0,
    "invalidOrMissingRequiredDirectedArcCount": 0,
    "depotPresent": false,
    "complete": false,
    "ready": false
  },
  "reasonCodes": ["dependency_unavailable"]
}
```

Reason codes are a fixed allowlist. They never embed IDs or provider text.

---

### Task 1: Add the protected FastAPI matrix-readiness contract

**Files:**

- Create: `optimizer_api/tests/test_dudullu_matrix_readiness.py`
- Modify: `optimizer_api/utils/matrix_repository.py`
- Create: `optimizer_api/routers/readiness.py`
- Modify: `optimizer_api/main.py`

**Step 1: Write failing repository tests**

Build tiny in-memory directed matrices through the existing fake provider seam. Test:

- complete asymmetric required set;
- required-code deduplication;
- a required code absent from the loaded matrix;
- missing, zero, negative, `NaN`, and infinite off-diagonal arcs;
- diagonal exclusion;
- missing `D.Kampus`;
- coordinate fallback;
- stale last-known-good data;
- provider error redaction.

The repository API should be:

```python
summary = repository.readiness_summary(
    required_locations=["D.Kampus", "Sw1", "So1"],
    depot_code="D.Kampus",
)
```

The returned dictionary must contain counts/booleans only and must not contain the location strings or `_last_error`.

**Step 2: Run the RED repository test**

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_dudullu_matrix_readiness.py -q -p no:cacheprovider --tb=short
```

Expected: FAIL because `readiness_summary` and the route do not exist.

**Step 3: Implement the smallest repository summary**

Under the existing repository lock:

- strip and deduplicate required codes without reordering requirements semantically;
- calculate `expected = n * (n - 1)` for the required set;
- treat an off-diagonal arc as valid only when `math.isfinite(value) and value > 0`;
- count missing required locations separately;
- count every unavailable required directed arc once;
- derive `has_error` from `_last_error is not None`, never return `_last_error`;
- set `ready` only when the source is Supabase, data is loaded and fresh, no provider error exists, the depot and all required locations exist, and every required directed arc is valid.

Do not change `health()` or lookup behavior in this task.

**Step 4: Write failing HTTP boundary tests**

Use `TestClient` and dependency-safe monkeypatching. Test:

- missing key -> 403;
- wrong key -> identical 403;
- shared internal key -> 200;
- tenant-only key -> 403;
- `UNIRIDE_DISABLE_AUTH=1` keeps the existing development/test opt-out;
- the route calls non-forced `refresh()` before measuring;
- request rejects an empty list, blank code, or excessive list;
- response serialization contains no submitted location code, key, URL, or fake provider error;
- readiness failure returns HTTP 200 with `ready=false` so diagnostics are preserved;
- public `/health` remains unauthenticated and unchanged.

**Step 5: Implement the internal endpoint**

Add:

```text
POST /api/v1/internal/readiness/time-matrix
```

- protect the router with `Depends(require_internal_api_key)`, not tenant authorization;
- accept only a bounded list of required location codes;
- call `DataLoader.get_instance().refresh()` without forcing provider backoff;
- return the repository's redacted summary;
- do not log the request body;
- include the router in `optimizer_api/main.py` without modifying public `/health`.

**Step 6: Run the focused gate**

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_dudullu_matrix_readiness.py optimizer_api/tests/test_matrix_repository.py optimizer_api/tests/test_package_b_compute_auth.py optimizer_api/tests/test_phase0_auth_guard.py -q -p no:cacheprovider --tb=short
```

Expected: PASS.

**Step 7: Commit**

```powershell
git add optimizer_api/tests/test_dudullu_matrix_readiness.py optimizer_api/utils/matrix_repository.py optimizer_api/routers/readiness.py optimizer_api/main.py
git commit -m "feat(runtime): add redacted Dudullu matrix readiness"
```

---

### Task 2: Add the pure redacted Dudullu inventory analyzer

**Files:**

- Create: `src/services/dudullu-readiness.test.ts`
- Create: `src/services/dudullu-readiness.ts`
- Modify: `src/services/daily-planning.ts`
- Modify: `src/services/daily-planning.test.ts`

**Step 1: Export and pin the existing campus predicate**

Rename/export the current private predicate as `isDudulluCampus()` without changing its semantics (`Dudullu` and `D.Kampus`, Turkish-locale case normalization). Add direct tests before reusing it.

**Step 2: Write failing analyzer tests**

Use small immutable fixtures with sentinel identities. Cover:

- 28 is compared, not required;
- consistent `users.weekly_schedule_id <-> weekly_schedules.id/user_id` mapping;
- missing and mismatched schedule links;
- malformed/non-array/empty schedule entries;
- orphaned and duplicate schedules;
- Dudullu schedule detection through `isDudulluCampus()`;
- missing location and disability type;
- duplicate physical locations count as separate students but one distinct location;
- driver accounts reported as `configuredDrivers`, never active drivers;
- active vehicle with zero total capacity is not usable;
- input objects are not mutated;
- serialized report contains none of the sentinel user IDs, schedule IDs, emails, names, or location codes;
- fixed reason codes are deterministic and sorted.

**Step 3: Run RED**

```powershell
npm test -- --run src/services/daily-planning.test.ts src/services/dudullu-readiness.test.ts
```

Expected: FAIL because the analyzer does not exist and the predicate is private.

**Step 4: Implement pure analysis**

Define minimal local input interfaces rather than accepting broad application DTOs. Treat schedule `entries` as `unknown` and narrow defensively. Return only the target aggregate contract.

Provide a separate helper for the route to obtain the deduplicated required matrix codes:

```typescript
requiredDudulluMatrixLocations(users): readonly string[]
```

This helper may return codes to the server-only caller, but `analyzeDudulluReadiness()` must never include them in its result.

The overall report is ready only when:

- every student has a valid location, disability type, consistent schedule link, and at least one Dudullu entry;
- at least one usable active vehicle and one configured driver exist;
- the matrix summary is ready and covers the same required distinct-location count;
- no malformed/orphaned/duplicate schedule condition exists.

Do not require exactly 28 students.

**Step 5: Run GREEN**

```powershell
npm test -- --run src/services/daily-planning.test.ts src/services/dudullu-readiness.test.ts
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add src/services/daily-planning.ts src/services/daily-planning.test.ts src/services/dudullu-readiness.ts src/services/dudullu-readiness.test.ts
git commit -m "feat(runtime): analyze Dudullu data readiness"
```

---

### Task 3: Add the authenticated admin readiness BFF

**Files:**

- Create: `src/app/api/admin/dudullu-readiness/route.test.ts`
- Create: `src/app/api/admin/dudullu-readiness/route.ts`

**Step 1: Write failing route tests**

Mock only Supabase and optimizer boundaries. Test:

- `requireAdmin()` runs before creating the service-role client or calling FastAPI;
- unauthorized requests cause zero data/optimizer calls;
- exact narrow selections are used:
  - users: `id,role,location_code,disability_type,weekly_schedule_id`;
  - schedules: `id,user_id,entries`;
  - vehicles: `status,wheelchair_capacity,seating_capacity`;
- all queries are read-only;
- only server-derived distinct location codes are sent in the internal POST body;
- `optimizerFetch()` is used and receives a bounded timeout signal;
- ordinary data deficiencies return 200 with `ready:false`;
- Supabase or optimizer transport failures return 503 with a fixed error code/message;
- `Cache-Control` is `private, no-store`;
- response and captured logs contain no sentinel identity, location list, raw Supabase error, URL, or key.

**Step 2: Run RED**

```powershell
npm test -- --run src/app/api/admin/dudullu-readiness/route.test.ts src/services/dudullu-readiness.test.ts src/lib/optimizer-server.test.ts
```

Expected: FAIL because the route does not exist.

**Step 3: Implement the route**

Flow:

1. `await requireAdmin(request)`.
2. Create the lazy service-role client.
3. Run the three narrow read-only queries.
4. Fail with a fixed redacted 503 response if any query fails.
5. Compute required codes server-side.
6. POST them through `optimizerFetch()` to the protected matrix endpoint with `AbortSignal.timeout(10_000)`.
7. Validate only the expected aggregate matrix shape; reject malformed upstream responses.
8. Call the pure analyzer and return its aggregate report.
9. Set `Cache-Control: private, no-store`.

Do not use the generic error helper for unexpected readiness failures because it can relay/log raw error objects. Do not add UI or `admin-api.ts` wiring yet.

**Step 4: Run GREEN**

```powershell
npm test -- --run src/app/api/admin/dudullu-readiness/route.test.ts src/services/dudullu-readiness.test.ts src/lib/optimizer-server.test.ts
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add src/app/api/admin/dudullu-readiness/route.ts src/app/api/admin/dudullu-readiness/route.test.ts
git commit -m "feat(runtime): expose admin Dudullu readiness report"
```

---

### Task 4: Provide one-command local startup and protected smoke

**Files:**

- Create: `scripts/start-dudullu-local.ts`
- Create: `scripts/start-dudullu-local.test.ts`
- Modify: `package.json`
- Modify: `.env.example` only if a discovered variable is absent; never add a real value

**Step 1: Write failing launcher unit tests**

Extract pure helpers and test:

- matching keys are accepted;
- mismatched configured keys fail without including either value;
- one configured side is copied only into the child-process environment;
- neither side configured produces an ephemeral cryptographically random shared key without writing a file;
- env parsing ignores comments/blanks and never returns values in diagnostics;
- child environment contains both key names with the same value;
- command/diagnostic rendering does not contain the key.

Do not start real processes in unit tests.

**Step 2: Run RED**

```powershell
npm test -- --run scripts/start-dudullu-local.test.ts
```

Expected: FAIL because the launcher does not exist.

**Step 3: Implement with Node standard library only**

Add `npm run dev:dudullu` using the already installed `tsx` runner. The launcher must:

- load only the two internal key names from process environment and the two local env files;
- reject a configured mismatch;
- create an in-memory ephemeral key when both are absent;
- pass the same key to both children without printing or persisting it;
- honor `UNIRIDE_PYTHON` or fall back to the documented `.venv` interpreter and then `python`;
- start `python main.py` with working directory `optimizer_api`;
- start `npm run dev` at the repository root;
- poll public FastAPI `/health`, the protected matrix readiness endpoint, and the Next.js HTTP listener;
- print only service status and aggregate matrix readiness counts;
- terminate both children when one exits unexpectedly or on Ctrl+C/SIGTERM;
- support `--check-only` for deterministic config/interpreter checks without starting services.

No new package dependency is allowed.

**Step 4: Run unit and check-only gates**

```powershell
npm test -- --run scripts/start-dudullu-local.test.ts
npm run dev:dudullu -- --check-only
```

The unit test must pass. `--check-only` may report a missing Python/Supabase runtime in this isolated worktree, but must do so without secrets and with a nonzero exit; classify that separately from a code defect.

**Step 5: Commit**

```powershell
git add scripts/start-dudullu-local.ts scripts/start-dudullu-local.test.ts package.json .env.example
git commit -m "feat(runtime): add one-command Dudullu local stack"
```

If `.env.example` did not change, omit it from `git add`.

---

### Task 5: Capture honest readiness evidence and synchronize active docs

**Files:**

- Create: `docs/DUDULLU_RUNTIME_READINESS.md`
- Modify: `README.md`
- Modify: `ACTIVE_ROADMAP.md`
- Modify: `WORKLOG.md`

**Step 1: Run the live gate without mutation**

From a checkout containing local credentials (never copy them into this worktree or commit them):

```powershell
npm run dev:dudullu
```

Authenticate as an administrator and request:

```text
GET /api/admin/dudullu-readiness
Authorization: Bearer <admin access token>
```

Do not paste or commit the token. Capture only the JSON aggregate report.

**Step 2: Decide gate state from evidence**

- `PASS`: both services start, protected smoke succeeds, BFF responds, and report `ready=true`.
- `BLOCKED-DATA`: services work but report contains data/matrix/fleet reason codes.
- `BLOCKED-CONFIG`: keys, credentials, interpreter, or service connectivity fail.
- `BLOCKED-ENVIRONMENT`: this execution environment cannot reach a dependency, as in the 2026-09-01 socket failure.

Never convert a blocked state to PASS from archived 28/29 claims.

**Step 3: Write the redacted evidence document**

Record:

- date/time/timezone;
- commit SHA;
- exact commands;
- aggregate report only;
- test/build results;
- explicit unverified fields and blocker category;
- confirmation that no data was mutated and no identity/secret was recorded.

**Step 4: Update active documentation**

- README: replace two-terminal instructions with `npm run dev:dudullu`, document `--check-only`, and retain individual service commands as troubleshooting only.
- ACTIVE_ROADMAP: correct the stale Package 1 branch wording, record Package 0 implementation/evidence state, and keep Package 2 blocked until Package 0 PASS.
- WORKLOG: append the Package 0 implementation and exact verification evidence.

Do not claim that 28 students or a 29-node complete matrix exists unless the live aggregate report proves it.

**Step 5: Commit**

```powershell
git add docs/DUDULLU_RUNTIME_READINESS.md README.md ACTIVE_ROADMAP.md WORKLOG.md
git commit -m "docs(runtime): record Dudullu readiness evidence"
```

---

### Task 6: Full verification and integration decision

**Step 1: Run focused frontend gates**

```powershell
npm test -- --run src/services/daily-planning.test.ts src/services/dudullu-readiness.test.ts src/app/api/admin/dudullu-readiness/route.test.ts src/lib/optimizer-server.test.ts scripts/start-dudullu-local.test.ts
npm run typecheck
npm run lint
```

**Step 2: Run focused and full production Python gates**

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_dudullu_matrix_readiness.py optimizer_api/tests/test_matrix_repository.py optimizer_api/tests/test_package_b_compute_auth.py optimizer_api/tests/test_phase0_auth_guard.py -q -p no:cacheprovider --tb=short
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests -q -p no:cacheprovider --tb=short
```

**Step 3: Run repository hygiene checks**

```powershell
git diff --check
git status --short --branch
git log --oneline origin/WIP..HEAD
```

**Step 4: Review before integration**

Use `requesting-code-review`. Reject the change if any response/log contains a sentinel identity, location list, raw provider error, or secret; if public `/health` was changed; or if Package 2 behavior slipped into this package.

**Step 5: Finish the branch**

Use `finishing-a-development-branch`. Merge to WIP only when code/test gates pass. If the live readiness gate remains blocked, merge only with explicit documentation that Package 0 is implemented but not operationally passed; Package 2 stays blocked.

## Recommended execution mode

Use subagent-driven execution in this task. Assign each task to a fresh bounded implementation agent, then run a specification review followed by a code-quality/security review before the next task. The primary agent owns final live-evidence classification and documentation consistency.
