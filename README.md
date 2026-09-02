# UniRide Dual-Engine Routing Platform

UniRide is one repository with two deliberately separate execution engines that share `uniride_core`:

- **Production engine:** a Next.js application and FastAPI optimization service for student transportation operations.
- **Academic engine:** TSPLIB/CVRPLIB datasets, controlled solver studies, DOE/tuning, and reproducible analysis.

The engines may share neutral models and solver implementations, but they do not share operational authority, job lifecycle, or scientific evidence. A passing benchmark is not a production release decision, and a production request must not acquire TSPLIB/DOE concerns.

## Current verified status

The latest verification was run on 2026-08-24 against the remediation working tree based on `WIP` commit `fef5a2b537da7068b51b3b3a50c6d633a2853404`. The evidence was captured before integration.

| Gate | Verified result |
| --- | --- |
| Full Python discovery | 3,355 passed, 1 skipped, 45 warnings, 429.17s |
| Frontend Vitest | 21 files, 58 tests passed, 78.99s |
| TypeScript | passed |
| ESLint | 0 errors, 158 warnings (temporary waiver) |
| Production build | passed on Next.js 16.1.6; 57 dynamic, server-rendered routes |
| `npm audit --omit=dev --json` | last recorded baseline: 84 findings (2 critical, 22 high, 59 moderate, 1 low); not refreshed on 2026-08-24 |

UniRide is still experimental. The passing build and test gates do **not** close the remaining hard solver cancellation, process isolation, durable-job, distributed rate-limit storage, matrix-provenance, GIS, lint-warning, or dependency-security boundaries. Read [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) before planning work.

The Dudullu Package 0 launcher and redacted readiness boundaries are implemented and test-gated at `d983375`, but the 2026-09-02 live aggregate gate is **`BLOCKED-CONFIG`** because no administrator access token was available. Current student, matrix, driver, and vehicle readiness is not verified. See [Dudullu runtime readiness evidence](docs/DUDULLU_RUNTIME_READINESS.md).

## Repository map

| Path | Responsibility |
| --- | --- |
| `src/` | Next.js UI and authenticated same-origin API/BFF routes |
| `optimizer_api/` | FastAPI production optimizer, DTOs, and benchmark control-plane code |
| `uniride_core/` | shared routing models, constraints, algorithms, validation, and matrix contracts |
| `academic_benchmark/` | academic datasets, studies, experiment protocols, registry adapters, and analysis |
| `supabase/` | schema, migrations, and RLS policy material |
| `docs/` | active design and operational documentation |
| `archive/` | historical evidence only; never current architecture truth |

## Architecture in one view

```text
Browser UI
  -> authenticated Next.js BFF routes
  -> FastAPI production adapters
  -> uniride_core

Academic CLI / study runners
  -> academic adapters and manifests
  -> uniride_core
```

Production owns user/service authorization, authoritative locations, travel-time providers, geometry, and operational persistence. Academic tooling owns instance sources, BKS/gaps, DOE metadata, seeds, environment manifests, and scientific reporting. The core must remain neutral.

## Setup

### JavaScript

```powershell
npm ci
```

### Python

Use a clean virtual environment. The full solver/test profile used during the latest validation installed the repository-declared test and solver extras plus the two optimizer requirement files.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ".[test]"
python -m pip install ".[solvers]"
python -m pip install -r optimizer_api\requirements.txt
python -m pip install -r optimizer_api\requirements-benchmark.txt
```

Optional solvers can require native tooling or a system binary. Their absence must be represented as unavailable, not as a failed registry dereference.

## Environment variables

Keep local values outside version control. Never put credential values in documents, browser bundles, logs, or commits.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | browser / Next.js | public Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | browser / Next.js | public Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | server only | privileged Supabase operations |
| `SUPABASE_URL` | Python/server | backend Supabase URL where configured |
| `OPTIMIZER_API_URL` | Next.js server | FastAPI URL for server-side adapters/BFF routes |
| `ALLOWED_ORIGINS` | FastAPI | comma-separated CORS allowlist |
| `APP_ENV` | FastAPI | runtime environment name; `production` forbids disabling auth |
| `ALLOW_PUBLIC_BIND` | FastAPI | explicit `1` opt-in required for a non-loopback optimizer bind |
| `OPTIMIZER_PORT` | FastAPI | optimizer service port |
| `UNIRIDE_PYTHON` | local launcher | optional Python interpreter path used by `npm run dev:dudullu`; otherwise the launcher checks the repository `.venv` and then `PATH` |
| `TIME_MATRIX_CACHE_TTL_SECONDS` | FastAPI | production matrix-cache lifetime |
| `TIME_MATRIX_PROVIDER_TIMEOUT_SECONDS` | FastAPI | travel-time provider timeout |
| `INTERNAL_API_KEY` | FastAPI | required key for the three production compute endpoints plus protected `GET /api/v1/internal/readiness` and `POST /api/v1/internal/readiness/time-matrix`; never log, return, or expose it |
| `OPTIMIZER_INTERNAL_API_KEY` | Next.js server only | server-only FastAPI internal key for `optimizerFetch`; set to the same secret value as `INTERNAL_API_KEY`; never expose through a `NEXT_PUBLIC_*` variable |
| `UNIRIDE_DISABLE_AUTH` | FastAPI local/test only | explicit `1` opt-out for loopback/local/test development; a startup error when `APP_ENV=production`; never set in production |
| `UNIRIDE_TENANT_KEYS` | FastAPI server only | optional JSON object mapping a non-empty tenant ID to a unique secret; `internal` is reserved and tenant secrets cannot reuse `INTERNAL_API_KEY` |
| `UNIRIDE_RATE_LIMIT_REQUESTS` | FastAPI | optional lowering-only fixed-window request limit (default 30) |
| `UNIRIDE_RATE_LIMIT_WINDOW_SECONDS` | FastAPI | optional lowering-only rate window in seconds (default 60) |
| `UNIRIDE_COMPUTE_MAX_STUDENTS` | FastAPI | optional override of the `production-conservative-v1` ceiling (250); may only lower it |
| `UNIRIDE_COMPUTE_MAX_VEHICLES` | FastAPI | optional override of the ceiling (50); may only lower it |
| `UNIRIDE_COMPUTE_MAX_ALGORITHMS` | FastAPI | optional override of the ceiling (6); may only lower it and never below the six-algorithm default set |
| `UNIRIDE_COMPUTE_MAX_WORKERS` | FastAPI | optional override of the ceiling (2); may only lower it |
| `UNIRIDE_COMPUTE_DEADLINE_SECONDS` | FastAPI | optional override of the 120-second soft response deadline; may only lower it |
| `UNIRIDE_COMPUTE_SOLVER_SECONDS` | FastAPI | optional override of the 60-second supported solver runtime; may only lower it |
| `UNIRIDE_COMPUTE_MAX_ITERATIONS` | FastAPI | optional override of the 2,000-iteration ceiling; may only lower it |
| `UNIRIDE_COMPUTE_MAX_POPULATION` | FastAPI | optional override of the 250 population/swarm-member ceiling; may only lower it |
| `UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS` | FastAPI | optional override of the 2-second local-search sublimit; may only lower it |
| `ENABLE_DEV_RESET` / `DEV_RESET_SECRET` | Next.js server | development reset control |
| `AZURE_AI_ENDPOINT`, `AZURE_AI_API_KEY`, `AZURE_AI_API_VERSION` | optional utility | Azure AI configuration |

### Compute policy (`production-conservative-v1`)

Heavy requests are admitted through `INTERNAL_API_KEY` and bounded by the frozen `production-conservative-v1` profile: **250 students, 50 vehicles, 6 canonical compare algorithms, 2 workers, a 120-second soft response deadline, 60 supported solver seconds, 2,000 iterations, 250 population/swarm members, and a 2-second local-search sublimit**. The nine `UNIRIDE_COMPUTE_*` variables may lower a ceiling, never raise it; invalid values fail at startup. Requests above the effective limits are rejected, never silently clamped. Exact/permutation requests with more than ten waypoints fail fast before the solver runs.

The deadline is a **soft** response deadline: `/compare` stops waiting after 120 seconds and running threads may continue in the background. A fixed-window in-memory limiter keys authenticated requests by tenant identity (with client-IP fallback when no tenant identity exists) and returns HTTP 429 with `Retry-After` after the configured budget. It is process-local, not a distributed quota. Package B does **not** provide hard solver cancellation, process isolation, or durable jobs.

The admin route-test page uses the authenticated same-origin `/api/optimize-route` BFF. Do not add a browser-direct FastAPI URL or expose an optimizer service address through a `NEXT_PUBLIC_*` variable.

## Run locally

The one-command Dudullu launcher is implemented and code-gated. It shares one internal key with both child processes, starts FastAPI and Next.js, and requires FastAPI health, the protected internal handshake, and the web listener before announcing readiness. The authenticated live inventory gate remains `BLOCKED-CONFIG` until an administrator bearer token is available; startup success is not a claim that current operational data is ready.

```powershell
npm run dev:dudullu
```

Validate interpreter, internal-key compatibility, and the web runner without starting either service:

```powershell
npm run dev:dudullu -- --check-only
```

For troubleshooting only, start the services separately in two terminals:

```powershell
Push-Location optimizer_api
python main.py
Pop-Location
```

```powershell
npm run dev
```

Configure matching `INTERNAL_API_KEY` and `OPTIMIZER_INTERNAL_API_KEY` values when starting separately, or let the combined launcher provide an in-memory ephemeral key. Never use `UNIRIDE_DISABLE_AUTH=1` in production.


Run academic CLI/help through the package entry point:

```powershell
python -m academic_benchmark.cli_engine --help
```

Do not publish benchmark evidence without a versioned dataset/matrix manifest, seed schedule, configuration, environment record, independent feasibility evidence, and the declared comparison protocol.

## Verification

The canonical Python suites are constrained in `pyproject.toml`; do not rely on broad repository discovery, which can collect manual scripts.

```powershell
python -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short
npm test -- --run
npm run typecheck
npm run lint
npm run build
npm audit --omit=dev --json
git diff --check
git status --short --branch
```

The last recorded `npm audit` exited nonzero with the 84 findings above; it was not refreshed in the 2026-08-24 remediation run. Record audit output as dated security evidence and never treat an unrefreshed count as current proof.

## Documentation authority

1. [UniRide_Ultimate_Audit.md](UniRide_Ultimate_Audit.md) — verified findings, historical rationale, and qualifications.
2. [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) — current structural boundaries and explicit open risks.
3. [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) — prioritized project state.
4. [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md) — dependency-ordered handoffs for future agents.
5. [WORKLOG.md](WORKLOG.md) — curated chronology and verification provenance.

If prose conflicts with live code or executable tests, live evidence wins. Archived documents are context, not authority.

## License

No repository license file is currently present. Confirm redistribution and usage terms with the repository owner.
