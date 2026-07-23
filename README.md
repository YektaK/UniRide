# UniRide Dual-Engine Routing Platform

UniRide is a vehicle-routing research and operations repository with two execution surfaces:

- **Production engine:** a Next.js application and FastAPI optimization service for student transportation planning.
- **Academic engine:** a TSPLIB/CVRPLIB/DOE benchmark framework for controlled algorithm experiments.

Both surfaces reuse `uniride_core`, but they have different contracts, lifecycle requirements, and evidence standards.

> **Current status (audited 2026-07-16): not production-ready.** Critical feasibility, matrix-integrity, authentication, benchmark-lifecycle, and frontend integration defects remain open. Treat solver output as experimental until it passes the planned shared feasibility certificate. See [UniRide_Ultimate_Audit.md](./UniRide_Ultimate_Audit.md) and [ACTIVE_ROADMAP.md](./ACTIVE_ROADMAP.md).

## Repository Map

| Path | Responsibility |
|---|---|
| `src/` | Next.js UI, browser services, and same-origin API routes |
| `optimizer_api/` | FastAPI production optimizer and web benchmark control plane |
| `uniride_core/` | Shared algorithms, decoders, adapters, distance functions, and routing models |
| `academic_benchmark/` | Dataset management, algorithm registry, DOE/tuning, repeated runs, and result analysis |
| `supabase/` | Database schema, migrations, and row-level-security policies |
| `docs/` | Verified operational references only |
| `archive/` | Superseded audits, speculative designs, and historical documentation; never a current source of truth |

## Architectural Summary

```text
Browser / Next.js UI
        |
        v
Next.js API routes -----> Supabase
        |
        v
FastAPI production service -----> production adapters ----+
                                                         |
Academic CLI / DOE -------------> academic adapters ------+--> uniride_core
```

The intended dependency rule is inward-only: production and academic adapters may import the shared core; the core must not depend on FastAPI, Next.js, TSPLIB persistence, or benchmark orchestration.

## Solver Families

- Cluster-first strategies: GA, PSO, GWO, and HHO followed by per-cluster TSP optimization.
- Giant-tour/split strategies: GA-Split, PSO-Split, GWO-Split, and HHO-Split.
- Reference and holistic solvers: OR-Tools and optional PyVRP/VROOM integrations.
- Local and exact baselines: greedy, 2-opt, and permutation search for very small instances.
- Research solvers and ALNS-related components under `uniride_core/algorithms/sota_*`.

Algorithm availability is not evidence of correctness. Current blockers include duplicate-customer identity handling, incorrect feasibility reporting, time-window split defects, incomplete travel matrices, and inconsistent deterministic seeding.

## Prerequisites

- Node.js 20 or newer
- npm with the committed lockfile
- Python 3.12 or 3.13 in a clean virtual environment
- A Supabase project for database-backed application flows

Optional academic solvers may require native build tools or external binaries.

## Installation

### Frontend

```powershell
npm ci
```

### Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r optimizer_api\requirements.txt
python -m pip install -e ".[test]"
```

Install optional solvers only when required:

```powershell
python -m pip install -e ".[solvers]"
```

Use a fresh environment. The audit machine had incompatible `pydantic` and `pydantic-core` installations, which prevented FastAPI test collection.

## Environment Variables

Create local environment files outside version control. Never commit credentials or copy real values into documentation.

| Variable | Surface | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Browser | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser | Public anonymous Supabase key; security must rely on RLS |
| `SUPABASE_SERVICE_ROLE_KEY` | Server only | Privileged Supabase operations; never expose to the browser |
| `SUPABASE_URL` | Python/server | Supabase URL for backend data access where supported |
| `OPTIMIZER_API_URL` | Next.js server | FastAPI service URL used by server-side routes |
| `NEXT_PUBLIC_OPTIMIZER_API_URL` | Legacy browser path | Direct browser optimizer URL; avoid in production |
| `ALLOWED_ORIGINS` | FastAPI | Comma-separated CORS allowlist |
| `OPTIMIZER_PORT` | FastAPI | Optimizer service port; default is `8000` |
| `TIME_MATRIX_CACHE_TTL_SECONDS` | FastAPI | Matrix cache lifetime; current loader lifecycle requires remediation |
| `ENABLE_DEV_RESET` | Next.js server | Enables the development reset endpoint |
| `DEV_RESET_SECRET` | Next.js server | Authorization secret for development reset |
| `AZURE_AI_ENDPOINT` | Optional utility | Azure AI endpoint |
| `AZURE_AI_API_KEY` | Optional utility | Azure AI credential |
| `AZURE_AI_API_VERSION` | Optional utility | Azure AI API version |

Other narrow utilities read `AZURE_OPENAI_API_KEY`, `BENCHMARK_PROFILE`, default pickup/dropoff-hour variables, `NODE_ENV`, and `VERCEL_ENV`.

## Running Locally

FastAPI service:

```powershell
Push-Location optimizer_api
python main.py
Pop-Location
```

Next.js development server:

```powershell
npm run dev
```

Defaults:

- Web application: `http://localhost:9002`
- FastAPI service: `http://127.0.0.1:8000`

Academic entry point:

```powershell
python -m academic_benchmark
```

Do not publish benchmark results until environment, seed schedule, matrix provenance, configuration, and independent feasibility are recorded.

## Verification Commands and Current Baseline

```powershell
npm test -- --run
npm run typecheck
npm run lint
python -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q --tb=short
```

Audit results on 2026-07-16:

| Gate | Result |
|---|---|
| Frontend unit tests | 15 passed across 3 files |
| TypeScript typecheck | Failed: local install lacked declared `next-intl`; two implicit-`any` errors remained |
| Lint | Failed: obsolete `next lint` script and disabled correctness rules |
| FastAPI/Python collection | Blocked by incompatible `pydantic`/`pydantic-core` environment |
| Core and academic tests | Reached 370 passed and 2 skipped before 46 temp-path/environment errors |

These are audit observations, not release certification.

## Documentation Authority

1. [UniRide_Ultimate_Audit.md](./UniRide_Ultimate_Audit.md) — definitive audit and historical rationale.
2. [CURRENT_ARCHITECTURE.md](./CURRENT_ARCHITECTURE.md) — current structural truth.
3. [ACTIVE_ROADMAP.md](./ACTIVE_ROADMAP.md) — prioritized remediation plan.
4. [WORKLOG.md](./WORKLOG.md) — curated chronology.
5. [docs/API_REFERENCE.md](./docs/API_REFERENCE.md) — verified endpoint inventory.
6. [docs/GITHUB_WORKFLOW.md](./docs/GITHUB_WORKFLOW.md) — contribution and verification workflow.

Everything under `archive/` is historical evidence and may contain false, contradictory, or superseded claims.

## License

No repository license file is currently present. Confirm usage and redistribution terms with the repository owner.
