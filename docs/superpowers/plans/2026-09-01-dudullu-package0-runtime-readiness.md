# Dudullu Package 0 Runtime and Data Readiness Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to implement this plan task-by-task. Use `test-driven-development` for every production change and `finishing-a-development-branch` before integration.

**Goal:** Prove that the local Next.js/FastAPI stack can start with one command and produce an authenticated, redacted, read-only Dudullu readiness report from current Supabase and matrix data.

**Architecture:** Keep operational data ownership in the Next.js server boundary and matrix truth in the FastAPI `TimeMatrixRepository`. A protected internal FastAPI endpoint evaluates only the requested Dudullu location set. An admin-only Next.js BFF reads narrow Supabase projections, calls that endpoint server-to-server, and returns aggregate counts and reason codes only. A dependency-free Node launcher gives both services one in-memory shared key, starts both processes, and performs a protected smoke check. No route solving, publication, schema migration, or UI is part of Package 0.

**Tech Stack:** Next.js 16 route handlers, TypeScript, Vitest, Supabase service-role server client, FastAPI, Pydantic, pytest, Node standard library.

**Authoritative design:** `docs/superpowers/specs/2026-08-25-dudullu-daily-operations-planner-design.md:458-468`

**Baseline verified on 2026-09-01:**

- branch `codex/dudullu-package0-readiness-20260901` starts at `origin/WIP` `9972f820820f638e7d62a1aa1d1fbbf6f8c62ee6`;
- focused Vitest baseline (40 passed):
  ```powershell
  npm test -- --run src/services/daily-planning.test.ts src/lib/optimizer-server.test.ts
  ```
- focused FastAPI matrix/auth baseline (43 passed):
  ```powershell
  & C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_matrix_repository.py optimizer_api/tests/test_package_b_compute_auth.py optimizer_api/tests/test_phase0_auth_guard.py -q -p no:cacheprovider --tb=short
  ```
- the original checkout's local Next.js and FastAPI env files contain Supabase
  configuration but neither side currently contains its internal-key variable;
  no value was printed or copied;
- live Supabase inventory was attempted without printing secrets or identities
  and was blocked by `HttpRequestException -> SocketException` before an HTTP
  response; no current 28-student / 29-node claim is verified from this attempt;
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
    "allAccounts": 0,
    "dudulluTarget": 0,
    "nonDudulluScheduled": 0,
    "unclassifiedSchedule": 0,
    "completeTargetProfiles": 0,
    "targetMissingLocation": 0,
    "targetMissingDisabilityType": 0,
    "scheduleLinkMismatch": 0,
    "distinctTargetLocations": 0
  },
  "schedules": {
    "total": 0,
    "empty": 0,
    "malformed": 0,
    "orphanedRows": 0,
    "duplicateRowsForStudent": 0
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

Field semantics are fixed as follows:

- `dudulluTarget` counts students whose consistently linked, well-formed weekly
  schedule contains at least one Dudullu entry;
- `nonDudulluScheduled` counts students with a valid linked schedule but no
  Dudullu entry and does not block Dudullu readiness;
- `unclassifiedSchedule` counts student accounts whose missing, malformed, or
  inconsistent schedule prevents a truthful campus classification and does
  block readiness;
- `completeTargetProfiles` means a Dudullu-target student has a nonblank
  location and `disability_type` in `{Sw, So}`;
- `orphanedRows` counts schedule rows whose `user_id` is not a student row;
- `duplicateRowsForStudent` counts schedule rows beyond the first row for a
  student, not the number of affected students;
- `matchesStudentCount` compares `dudulluTarget === 28` and
  `matchesMatrixNodeCount` compares `matrix.matrixLocationCount === 29`;
- historical-expectation booleans never affect `ready`;
- a dependency-level 503 has the small fixed body
  `{ "ready": false, "reasonCodes": ["dependency_unavailable"] }`;
- allowed reason codes, in deterministic output order, are:
  `no_dudullu_students`, `target_profile_incomplete`,
  `schedule_classification_incomplete`, `schedule_data_invalid`,
  `no_configured_driver`, `no_usable_active_vehicle`, `matrix_unavailable`,
  `matrix_stale`, `matrix_incomplete`, `matrix_location_mismatch`, and
  `dependency_unavailable`.

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
    student_locations=["Sw1", "So1"],
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

- strip and deduplicate student home codes, then internally construct the
  required set as `{depot_code} union student_locations`;
- require at least one non-depot student location; empty or depot-only input is never complete or ready;
- calculate `expected = n * (n - 1)` for that internally constructed set;
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
- request accepts at most 250 student location codes and tests 250/251 boundaries;
- request rejects an empty list and blank code;
- invalid input uses a route-owned fixed 422 body rather than FastAPI's default
  validation body, which can echo rejected input;
- invalid and successful response serialization contains no submitted sentinel
  location code, key, URL, or fake provider error;
- readiness failure returns HTTP 200 with `ready=false` so diagnostics are preserved;
- public `/health` remains unauthenticated and unchanged.

**Step 5: Implement the internal endpoint**

Add:

```text
GET  /api/v1/internal/readiness
POST /api/v1/internal/readiness/time-matrix
```

- protect the router with `Depends(require_internal_api_key)`, not tenant authorization;
- make the GET endpoint a status-only internal-key handshake for the launcher;
  it is not matrix or live-data evidence;
- for POST, accept only `{"student_location_codes": [...]}` with 1-250 entries;
- parse/validate that small body inside the route (or catch Pydantic validation
  before FastAPI renders it) and return a fixed redacted 422 on failure;
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

- 28 Dudullu-target students is compared, not required;
- consistent `users.weekly_schedule_id <-> weekly_schedules.id/user_id` mapping;
- valid non-Dudullu scheduled accounts are reported but do not block readiness;
- missing, malformed, or mismatched schedule links remain unclassified and do block readiness;
- zero Dudullu-target students always yields `ready:false`;
- malformed/non-array/empty schedule entries;
- orphaned and duplicate schedules;
- Dudullu schedule detection through `isDudulluCampus()`;
- missing location and disability type within the Dudullu target;
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

Provide a separate helper for the route to obtain deduplicated Dudullu-target
student home codes; FastAPI adds the depot itself:

```typescript
requiredDudulluStudentLocations(users, schedules): readonly string[]
```

This helper may return codes to the server-only caller, but `analyzeDudulluReadiness()` must never include them in its result.

The overall report is ready only when:

- `students.dudulluTarget > 0`;
- every Dudullu-target student has a valid location and disability type;
- no student remains unclassified because of missing/malformed/inconsistent schedule data;
- at least one usable active vehicle and one configured driver exist;
- the matrix summary is ready and
  `matrix.requiredLocationCount === students.distinctTargetLocations + 1`,
  where the extra node is `D.Kampus`;
- no malformed/orphaned/duplicate schedule condition exists.

Do not require exactly 28 students, and do not make valid non-Dudullu accounts
release blockers.

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
- missing/invalid bearer tokens return 401 and authenticated non-admin users return 403;
- both auth failures cause zero Supabase/optimizer calls;
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
- the FastAPI payload passes a strict allowlist schema: `source` is a fixed
  enum, counts are finite nonnegative integers, booleans are booleans, and
  unknown fields are rejected;
- malicious upstream `source` values or extra `error`, `locations`, and
  `url` fields produce the same redacted 503 response;
- accepted fields are reconstructed individually and the upstream object is never spread;
- response and captured logs contain no sentinel identity, location list, raw Supabase error, URL, or key.

**Step 2: Run RED**

```powershell
npm test -- --run src/app/api/admin/dudullu-readiness/route.test.ts src/services/dudullu-readiness.test.ts src/lib/optimizer-server.test.ts
```

Expected: FAIL because the route does not exist.

**Step 3: Implement the route**

Flow:

1. Call `await requireAdmin(request)` in its own auth error boundary so the
   existing 401/403 `AppError` semantics are preserved.
2. Create the lazy service-role client.
3. Run the three narrow read-only queries.
4. Fail with a fixed redacted 503 response if any query fails.
5. Compute required codes server-side.
6. POST them through `optimizerFetch()` to the protected matrix endpoint with `AbortSignal.timeout(10_000)`.
7. Strictly validate the aggregate matrix response and reconstruct accepted
   fields one-by-one; never spread or forward the upstream object.
8. Reject unknown or malformed upstream fields with the fixed redacted 503.
9. Call the pure analyzer and return its aggregate report.
10. Set `Cache-Control: private, no-store`.

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

- Create: `scripts/start-dudullu-local.mjs`
- Create: `scripts/start-dudullu-local.test.mjs`
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
node --test scripts/start-dudullu-local.test.mjs
```

Expected: FAIL because the launcher does not exist.

**Step 3: Implement with Node standard library only**

Add `npm run dev:dudullu` as `node scripts/start-dudullu-local.mjs`. This is a
foreground, long-running startup command. It proves process health and
internal-key handshake only. The full redacted inventory still requires a
separate authenticated admin request. The launcher must:

- load only the two internal key names from process environment and the two local env files;
- reject a configured mismatch;
- create an in-memory ephemeral key when both are absent;
- pass the same key to both children without printing or persisting it;
- honor `UNIRIDE_PYTHON` or fall back to the documented `.venv` interpreter and then `python`;
- start `python main.py` with working directory `optimizer_api`;
- start `npm run dev` at the repository root;
- poll public FastAPI `/health`, the `GET /api/v1/internal/readiness` key
  handshake, and the Next.js HTTP listener;
- print only service status; do not print data-readiness counts from the launcher;
- terminate both children when one exits unexpectedly or on Ctrl+C/SIGTERM;
- support `--check-only` for deterministic config/interpreter checks without starting services.

No new package dependency is allowed.

**Step 4: Run unit and check-only gates**

```powershell
node --test scripts/start-dudullu-local.test.mjs
npm run dev:dudullu -- --check-only
```

The unit test must pass. `--check-only` may report a missing Python/Supabase runtime in this isolated worktree, but must do so without secrets and with a nonzero exit; classify that separately from a code defect.

**Step 5: Commit**

```powershell
git add scripts/start-dudullu-local.mjs scripts/start-dudullu-local.test.mjs package.json .env.example
git commit -m "feat(runtime): add one-command Dudullu local stack"
```

If `.env.example` did not change, omit it from `git add`.

---

### Task 5: Capture honest readiness evidence and synchronize active docs

**Files:**

- Create: `docs/DUDULLU_RUNTIME_READINESS.md`
- Modify: `README.md`
- Modify: `ACTIVE_ROADMAP.md`
- Modify: `CURRENT_ARCHITECTURE.md`
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

- README: replace two-terminal instructions with `npm run dev:dudullu`, document
  `--check-only`, and retain individual service commands as troubleshooting only.
  Describe the startup command as **verified** only if the live smoke actually
  passes. Otherwise state **implemented-but-blocked** with the specific blocker
  category and retain the troubleshooting commands.
- CURRENT_ARCHITECTURE.md: add the internal readiness endpoint and the admin
  readiness BFF route to the endpoint inventory; record Package 0 as the current
  open production boundary.
- ACTIVE_ROADMAP: correct the stale Package 1 branch wording, record Package 0 implementation/evidence state, and keep Package 2 blocked until Package 0 PASS.
- WORKLOG: append the Package 0 implementation and exact verification evidence.

Do not claim that 28 students or a 29-node complete matrix exists unless the live aggregate report proves it.

**Step 5: Commit**

```powershell
git add docs/DUDULLU_RUNTIME_READINESS.md README.md ACTIVE_ROADMAP.md CURRENT_ARCHITECTURE.md WORKLOG.md
git commit -m "docs(runtime): record Dudullu readiness evidence"
```

---

### Task 6: Full verification and integration decision

**Step 1: Run focused frontend gates**

```powershell
npm test -- --run src/services/daily-planning.test.ts src/services/dudullu-readiness.test.ts src/app/api/admin/dudullu-readiness/route.test.ts src/lib/optimizer-server.test.ts
node --test scripts/start-dudullu-local.test.mjs
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
