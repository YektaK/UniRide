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

## Demo runbook (Demo çalıştırma)

Purpose: repeat the daily-plan demo (`/admin/daily-plan`) on a local machine. The page is a
read-only preview. Source of truth for scope and limits: `docs/DEMO_ROADMAP_2026-10-04.md`.

### Prerequisites

- Run from the **main checkout** on the `WIP` branch with D0-D3 merged. The optimizer's
  editable install points at the main checkout (roadmap F9), so a worktree would load the
  wrong `optimizer_api` modules.
- `.env.local` holds the Next.js Supabase variables and `optimizer_api/.env` holds the
  optimizer variables (roadmap D0 step 2). Never print their values.
- The Python environment is `.venv-jit`. The launcher now detects it automatically; set
  `UNIRIDE_PYTHON` (absolute path) only to override it.
- The Supabase project is active (owner action) and a Supabase Auth user with
  `public.users.role = 'admin'` exists. Do not create the admin through the sign-up form.

### Start

1. `node scripts/start-dudullu-local.mjs --check-only` (optional). The interpreter line must
   show the `.venv-jit` path.
2. `npm run dev:dudullu`. It prints when the FastAPI optimizer (`127.0.0.1:8000`) and Next.js
   (`http://127.0.0.1:9002`) are both ready.
3. Open `http://127.0.0.1:9002` and sign in as the admin.
4. Sidebar: **Günlük Plan** (`/admin/daily-plan`).
5. Optional: `/admin/readiness` should show 0 missing matrix arcs (812/812 on 2026-10-04).

### Using the page

1. Pick a date. **Monday has the most students** (27 students, 12 waves, 54 trips on
   2026-10-05), so it is the best demo day. Days with no confirmed trips show the empty-day card.
2. Leave both toggles on for the demo, then press **Planı oluştur**. Expect about 20 s for a
   full Monday (17.7 s measured on 2026-10-04); the client gives up after 60 s.
3. Read the cards: **Bu rotalar için gereken araç** (vehicles needed for these fixed routes; an
   "en fazla" badge means the assignment search did not finish), student and route counts,
   live fleet and the shortage. Then the waves with stop times, the vehicle schedule and the
   status notes.

### What the toggles mean

| Toggle | On | Off |
|---|---|---|
| Öğrenci onaylarını varsay (demo) | Every pending trip counts as confirmed (`admissionMode: assume_confirmed`); recorded cancellations are kept. | Only recorded decisions count (`recorded`). The decision table does not exist yet, so an empty day or `LEG_DECISIONS_UNAVAILABLE` is the expected result. |
| Sanal filo (gereken araç) | Identical virtual vehicles (template taken from the active vehicles; 4 Sw / 10 So / 10 min cooldown on 2026-10-04) are generated, so the page can answer "how many vehicles are needed" (`fleetMode: virtual`). | Only the real active vehicles are used (`live`); the page reports the shortage. |

### Read-only guarantees

- The route `POST /api/admin/dudullu-preview` is admin-only and writes nothing to Supabase.
- Every response is `publishable: false`; the page has no publish, save or assign action and
  always shows the "Önizleme - yayınlanamaz" banner.
- No student names are shown, only location codes (So1, Sw3).
- The assume-confirmed mode is a preview-only, owner-approved exception (roadmap K1).

### Known limits (also shown on the page)

The solver is not optimal and the route count is not a true minimum (only the vehicle
assignment is proven). The time model is simple: each wave is tied to a single arrival or
departure time (`use_time_windows: false`); waiting and return-to-campus checks are not made
(H2, H4). Do not claim savings from this page.

### Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Önizleme hizmeti şu anda kullanılamıyor" | Optimizer or Supabase not reachable; check the launcher output and `/admin/readiness`. |
| "İstek zaman aşımına uğradı" | Run exceeded 60 s; pick a day with fewer waves. |
| "Yönetici oturumu doğrulanamadı" | Sign in again as the admin. |
| Python interpreter without fastapi in `--check-only` | `UNIRIDE_PYTHON` points to a missing path (for example from a worktree); fix the absolute path. |

The manual end-to-end checklist is section 6 of `docs/DEMO_ROADMAP_2026-10-04.md`.
