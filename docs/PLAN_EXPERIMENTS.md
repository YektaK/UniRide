# Daily plan experiment exports

The CLI and daily-plan API call the same server-only `runDailyPlan`. Authentication and body validation remain in the API. The CLI fixes admission to `assume_confirmed`; virtual mode uses the page's automatically selected identical-vehicle template. It performs SELECTs only and calls the optimizer in sandbox mode.

## Run

Use the branch checkout with its Node dependencies installed. The local optimizer must run from **the same checkout and configuration**. Configure Supabase credentials in the ignored `.env.local` / `optimizer_api/.env` or the parent environment. The CLI loads these files before importing server clients. Both processes need the same internal key; conflicting keys fail with a redacted error. A key generated privately inside `dev:dudullu` is not automatically shared with a separately launched CLI.

For a Python-only local start from a configured checkout, this PowerShell example generates a shared key only in memory, hides the optimizer window, and stops only that process:

```powershell
$env:INTERNAL_API_KEY = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:OPTIMIZER_INTERNAL_API_KEY = $env:INTERNAL_API_KEY
$env:UNIRIDE_API_RELOAD = "0"
$optimizer = Start-Process -FilePath ".\.venv-jit\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "optimizer_api" -WindowStyle Hidden -PassThru
try {
  # Wait until http://127.0.0.1:8000/health is healthy, then run the smoke first.
  npm run experiments:plan -- --dates 2026-10-05 --ride-limits 90 --out .temp/experiments/monday-smoke
} finally {
  Stop-Process -Id $optimizer.Id -ErrorAction SilentlyContinue
}
```

Use `UNIRIDE_PYTHON` for an existing Python runtime outside the checkout; do not copy secrets into tracked files. An already configured optimizer started via `npm run dev:dudullu` is also usable. `OPTIMIZER_API_URL` selects its address. `--help` and invalid argument checks do not access live services.

First compare the Monday R90 smoke against the reference: **27 students, 3 vehicles, 16 routes, 12 waves, maximum ride 89 min**. If it differs, retain the result and investigate; do not launch the full campaign.

After a matching smoke, run five weekdays × four ride limits:

```text
npm run experiments:plan -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 --fleet virtual
```

Add `--repeat 2` for two runs per combination (40 computations). Explicit comma-separated `--dates` replaces `--week-of`; the latter must be Monday. Dates/limits must be distinct. The accepted limits match the API: ride 15–240, tour 30–300 minutes. Repetition supports 1 or 2. A fresh output directory is required; existing campaigns are never overwritten. Default output is `.temp/experiments/<timestamp>/`, ignored by Git.

## Artifacts and interpretation

- `*.response.json`: full preview response with location-based student aliases, anonymous vehicle labels, and recursively anonymized keys/values, including certificates. Names/emails are redacted. Aliases distinguish multiple students at one physical location; they do not support linking identities across campaigns.
- `*.matrix.json`: authoritative requested physical arcs and response provenance. The hash/location count describe the stored matrix, not only this subset. `loaded_at` comes from the optimizer response, not the CLI clock.
- `summary.csv`: required daily columns plus `repeat_index` and `is_empty_day`. Counts, maximum ride and capacity floor reuse the page's view model. Maximum ride retains the page's integer rounding. Mean ride is passenger-leg weighted over authoritative arcs: pickup stop→campus, dropoff campus→stop. Vehicle-minutes include the closed depot tour and exclude cooldown. Additional time metrics are rounded to six decimal places. Unavailable metrics are blank; an empty healthy day has zero vehicle-minutes and no mean ride.
- `weekly.csv`: first repeat only, grouped by Monday/ride/tour limit. The maximum is a requirement for the computed weekday routes, conditional on the recorded assignment proof. `weekly_fleet_need` and full-week minutes remain blank unless all five weekday results are known. Partial/failed coverage remains visible in `complete_week`, per-day status and `max_observed_vehicles`/`observed_vehicle_minutes`. Explicit weekend dates appear only in broader observations and per-day data, not certified weekday totals. Entirely unknown observed duration stays blank. A known indeterminate count is an upper bound; `vehicle_count_proven=false` preserves that distinction.
- `run_manifest.json`: Git commit/dirty state, timestamp, inputs, algorithm `ga_split`, local production constructor defaults/effective configuration/seed, template and response matrix provenance per run. Promoted settings are resolved by production Python code. This is local configuration evidence; it does not attest a separately deployed optimizer's configuration. Use the same checkout/environment for both processes.

The existing default resolves `seed=None` to **42**. The runner does not override GA parameters to force agreement: a promoted configuration must be recorded truthfully. Repeats compare every daily summary field except repeat index and also compare matrix hashes. Divergence is recorded and exits with code 2. `loaded_at` can legitimately differ. Responses/CSV/manifest are checkpointed after each completed run; a failed export preserves earlier results and marks the manifest failed. Preview/data failures are exported with their status/reasons rather than claimed as feasible plans.

These are descriptive operational sensitivity results under **native termination**, not fixed objective-evaluation-budget benchmark evidence. A proven vehicle assignment is minimal for the solver's fixed routes; it is not global routing optimality. Smoke/pilot output establishes neither algorithm superiority nor causality. Live schedules can change between runs; matrix hashes and status are captured, but these files do not freeze the underlying live database.

## Verification

Unit tests use fake data and transports, never the live DB/optimizer:

```text
npx vitest run
npx tsc --noEmit
npm run lint
git diff --check WIP...HEAD -- ':!tailwind.config.ts'
```

The nonempty route/direct-function parity fixture retains all prior route tests. Metric tests cover asymmetric tours, duplicate physical stops, missing costs/coverage, partial weeks and repeat counting; parser/privacy tests cover rejected inputs and nested identifiers. Page controls and exact small-wave solvers remain proposals in `DECISION_LOG.md`.
