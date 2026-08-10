# UniRide Dual-Engine Routing Platform

UniRide is one repository with two deliberately separate execution engines that share `uniride_core`:

- **Production engine:** a Next.js application and FastAPI optimization service for student transportation operations.
- **Academic engine:** TSPLIB/CVRPLIB datasets, controlled solver studies, DOE/tuning, and reproducible analysis.

The engines may share neutral models and solver implementations, but they do not share operational authority, job lifecycle, or scientific evidence. A passing benchmark is not a production release decision, and a production request must not acquire TSPLIB/DOE concerns.

## Current verified status

The latest post-audit verification was run on 2026-08-10 from base `0b4bef6e77d4eda2812cbe773296978862c25599`; the last code-bearing commit was `ddd85e8b1cc5ed64a8163988b2e179a08c8cfd2f`.

| Gate | Verified result |
| --- | --- |
| Canonical Python suites | 1,676 passed, 48 warnings, 238.17s |
| Frontend Vitest | 17 files, 37 tests passed, 2.83s |
| TypeScript | passed |
| ESLint | 0 errors, 158 warnings |
| Credential-free production build | passed |
| `npm audit --omit=dev --json` | 84 findings: 2 critical, 22 high, 59 moderate, 1 low |

UniRide is still experimental. The passing build and test gates do **not** close the remaining feasibility, general compute-authentication, durable-job, provenance, GIS, lint-warning, or dependency-security boundaries. Read [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) before planning work.

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
| `OPTIMIZER_PORT` | FastAPI | optimizer service port |
| `TIME_MATRIX_CACHE_TTL_SECONDS` | FastAPI | production matrix-cache lifetime |
| `TIME_MATRIX_PROVIDER_TIMEOUT_SECONDS` | FastAPI | travel-time provider timeout |
| `INTERNAL_API_KEY` | FastAPI | internal benchmark/CLI boundary key |
| `ENABLE_DEV_RESET` / `DEV_RESET_SECRET` | Next.js server | development reset control |
| `AZURE_AI_ENDPOINT`, `AZURE_AI_API_KEY`, `AZURE_AI_API_VERSION` | optional utility | Azure AI configuration |

The admin route-test page uses the authenticated same-origin `/api/optimize-route` BFF. Do not add a browser-direct FastAPI URL or expose an optimizer service address through a `NEXT_PUBLIC_*` variable.

## Run locally

Start the FastAPI service:

```powershell
Push-Location optimizer_api
python main.py
Pop-Location
```

Start the web application:

```powershell
npm run dev
```

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

`npm audit` currently exits nonzero because the 84 findings above remain unresolved. Record it as security evidence; do not silently treat an audit finding as a test failure or a resolved issue.

## Documentation authority

1. [UniRide_Ultimate_Audit.md](UniRide_Ultimate_Audit.md) — verified findings, historical rationale, and qualifications.
2. [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) — current structural boundaries and explicit open risks.
3. [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) — prioritized project state.
4. [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md) — dependency-ordered handoffs for future agents.
5. [WORKLOG.md](WORKLOG.md) — curated chronology and verification provenance.

If prose conflicts with live code or executable tests, live evidence wins. Archived documents are context, not authority.

## License

No repository license file is currently present. Confirm redistribution and usage terms with the repository owner.
