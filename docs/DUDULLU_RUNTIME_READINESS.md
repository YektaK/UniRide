# Dudullu Runtime Readiness Evidence

**Gate state:** `BLOCKED-CONFIG`
**Captured:** 2026-09-02 08:45:46 +03:00 (`Europe/Istanbul`)
**Branch:** `codex/dudullu-package0-readiness-20260901`
**Commit:** `d983375d0307fa6b2ee7a995de9cbfa15fbf20e1`

## Outcome

Package 0's code and local process boundary are implemented and test-gated. A
live attempt started the FastAPI and Next.js services from the feature worktree
while using existing ignored environment files only through the child-process
environment. FastAPI `/health` returned HTTP 200 and the Next.js listener
returned HTTP 200. No credential value was printed, copied into the worktree,
or committed.

The authenticated aggregate gate did not complete. No administrator access
token was available in the local environment or connected browser session, so
`GET /api/admin/dudullu-readiness` correctly returned HTTP 401. The current
state is therefore `BLOCKED-CONFIG`, not `PASS`. No aggregate readiness report
was produced.

## Evidence

Commands and observed results:

```powershell
codegraph index C:\tmp\UniRide-dudullu-daily-planner-20260825
# 686 files indexed; 11,202 nodes and 29,058 edges.

# Existing ignored Supabase variables were loaded into the parent process; values were not printed.
$env:UNIRIDE_PYTHON = 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe'
npm run dev:dudullu
# FastAPI /health: HTTP 200.
# Next.js listener on http://127.0.0.1:9002: HTTP 200.

Invoke-WebRequest http://127.0.0.1:9002/api/admin/dudullu-readiness -UseBasicParsing -TimeoutSec 20
# HTTP 401 because no administrator bearer token was supplied.

node --test scripts/start-dudullu-local.test.mjs
# 20 passed, 0 failed.

npm run dev:dudullu -- --check-only
# Exit 0; Python and web runner probes passed; key value was not printed.

npm test -- --run src/services/dudullu-readiness.test.ts src/app/api/admin/dudullu-readiness/route.test.ts
# 2 files / 43 tests passed.

& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_dudullu_matrix_readiness.py -q -p no:cacheprovider --tb=short
# 25 passed.

npm run typecheck
# Passed.

npm run lint -- --quiet
# Passed with zero errors.
```

After the live attempt, the temporary process trees were terminated and ports
8000 and 9002 were verified free.

## Unverified runtime facts

Because the authenticated BFF request did not run, all current operational
inventory remains unverified, including:

- the current Dudullu-target student count;
- whether the historical 28-student expectation matches current data;
- whether the matrix contains 29 nodes or all required directed arcs;
- profile completeness, schedule-link consistency, configured drivers, and
  usable active vehicles;
- the final `ready` value and data/matrix/fleet reason codes.

Historical 28-student and 29-node material is context only and is not evidence
for this gate.

## Required follow-up

Start the stack from a credential-bearing local environment, authenticate as an
administrator, and call `GET /api/admin/dudullu-readiness` with the resulting
bearer token. Record only the redacted aggregate response. Classify the rerun as
`PASS` only when the endpoint returns HTTP 200 with `ready: true`; otherwise
record the returned fixed reason codes as `BLOCKED-DATA`, or the relevant
configuration/environment blocker. No Supabase row may be mutated during this
gate.

## Safety confirmation

The attempt was read-only. No user, schedule, request, plan, vehicle, driver,
matrix, or route record was created or modified. No identity, location-code
list, token, key, URL credential, or raw provider error was recorded here.
