# UniRide API Reference

**Verified:** 2026-07-16
**Status:** endpoint inventory and integration guide, not a production-security certification

The archived predecessor described obsolete payloads. This reference is intentionally concise and reflects the live route inventory. Generate detailed schemas from FastAPI OpenAPI after the Python environment is repaired.

## 1. Service Boundaries

- Browser clients should call same-origin Next.js routes under `/api/*`.
- Next.js routes authenticate users and translate application payloads.
- Next.js server routes call the FastAPI optimizer through `OPTIMIZER_API_URL`.
- Direct browser calls to FastAPI are a known defect and must not be used in production.
- FastAPI currently has no service-authentication dependency; deploy it only on a trusted private boundary until Phase 2 of the roadmap.

## 2. FastAPI Endpoints

Default local base: `http://127.0.0.1:8000`

### Core optimization

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process/feature summary; currently vulnerable to optional-null strategy enumeration |
| GET | `/api/v1/strategies` | Strategy metadata and availability |
| POST | `/api/v1/optimize` | Run one optimization strategy |
| POST | `/api/v1/compare` | Compare requested strategies |
| POST | `/api/v1/vehicle-calculator` | Alias to the optimize flow |
| POST | `/api/v1/extract-time-windows` | Extract windows from schedule entries |
| POST | `/api/v1/schedule-to-students` | Convert schedule entries to student DTOs |

### Benchmark control and data

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/benchmark/problems` | List benchmark problems |
| GET | `/api/v1/benchmark/problems/{problem_name}` | Get problem metadata |
| POST | `/api/v1/benchmark/download/{problem_name}` | Download/register a problem |
| POST | `/api/v1/benchmark/import` | Import benchmark data |
| GET | `/api/v1/benchmark/param-spaces` | Parameter-space metadata |
| POST | `/api/v1/benchmark/run` | Start a benchmark run |
| GET | `/api/v1/benchmark/status` | Read run status |
| GET | `/api/v1/benchmark/results/{run_id}` | Read run results |
| POST | `/api/v1/benchmark/stop` | Request stop; currently does not cancel computation reliably |
| GET | `/api/v1/benchmark/academic/problems` | Academic problem inventory |
| GET | `/api/v1/benchmark/academic/leaderboard` | Academic leaderboard rows |
| GET | `/api/v1/benchmark/academic/best` | Best academic rows |
| GET | `/api/v1/benchmark/academic/benchmark-results` | Academic benchmark rows |
| GET | `/api/v1/benchmark/cli/files` | List CLI result files in configured directories |
| POST | `/api/v1/benchmark/cli/import` | Import CLI result JSON |
| GET | `/api/v1/benchmark/cli/preview` | Preview CLI result JSON |

### FastAPI security warning

The benchmark and CLI endpoints are not safe for untrusted exposure. In particular, the archived implementation of CLI preview/import accepted caller-selected paths. Phase 0 must remove this behavior and add service/admin authentication.

## 3. Core FastAPI Contracts

### Optimization request

The live `OptimizationRequest` uses top-level fields, not the obsolete nested `optimizer_config` structure.

Principal fields:

| Field | Meaning |
|---|---|
| `algorithm` | Strategy key; default currently `ga_split` |
| `students` | Student/customer nodes |
| `depot` | Depot node |
| `max_travel_time` | Maximum route duration |
| `sw_capacity`, `so_capacity` | Vector capacity dimensions |
| `direction` | `pickup` or `dropoff` |
| `use_time_windows` | Enables time-window extraction/scheduling |
| `target_time`, `offset_minutes` | Scheduling inputs |
| `vehicles` | Optional heterogeneous fleet configuration |
| `local_search_type` | Local-search selection |
| `ga_config`, `pso_config`, `gwo_config`, `hho_config` | Algorithm overrides |
| `two_opt_config`, `sota_config` | Additional overrides |
| `clustering_algorithm` | Cluster-first strategy choice |
| `is_asymmetric` | Directed-cost flag |

Current caveat: algorithm configuration dictionaries and major list fields need strict typed upper bounds.

### Optimization response

Principal fields:

- `algorithm_used`
- `success`
- `routes`
- `total_vehicles`
- `total_duration_minutes`
- `error_message`
- `execution_time_seconds`
- `direction`
- `time_windows_used`
- `ie_data`
- `total_time_window_violations`

Current caveat: `success=True` is not yet a reliable feasibility certificate.

### Compare request/response

`/api/v1/compare` accepts a `CompareRequest` and returns `CompareResponse`, including per-algorithm results, best/fastest keys, and a summary. It does not return the obsolete raw list described by the archived API reference.

## 4. Next.js Same-Origin API Routes

| Methods | Path |
|---|---|
| GET | `/api/` |
| GET, PUT, DELETE | `/api/admin/ride-requests` |
| GET, POST, PUT, DELETE | `/api/admin/users` |
| PATCH | `/api/admin/users/password` |
| GET, POST, PUT, DELETE | `/api/admin/vehicles` |
| POST | `/api/auth/dev-reset` |
| POST | `/api/auth/hint` |
| GET | `/api/benchmark/academic/best` |
| GET | `/api/benchmark/academic/leaderboard` |
| GET | `/api/benchmark/academic/problems` |
| GET | `/api/benchmark/health` |
| GET | `/api/benchmark/param-spaces` |
| GET | `/api/benchmark/problems` |
| GET | `/api/benchmark/results/[runId]` |
| POST | `/api/benchmark/run` |
| GET | `/api/benchmark/run/status` |
| POST | `/api/benchmark/run/stop` |
| GET | `/api/benchmark/status` |
| POST | `/api/benchmark/stop` |
| GET | `/api/benchmark/strategies` |
| POST | `/api/calculate-vehicles` |
| POST | `/api/compare-algorithms` |
| GET, PUT | `/api/driver/assignments` |
| GET, POST | `/api/optimize-route` |
| PATCH | `/api/profile/password` |
| GET, POST | `/api/ride-confirmation` |
| GET, POST, PATCH, DELETE | `/api/route-plans` |
| GET, POST, PUT, DELETE | `/api/sandbox` |

Dynamic-segment notation follows filesystem route names.

## 5. Authentication Model

- Browser Supabase sessions produce bearer tokens.
- Administrative Next.js routes should call the central role/auth helpers.
- `SUPABASE_SERVICE_ROLE_KEY` is server-only.
- Public anonymous keys are not secrets; authorization depends on validated sessions and RLS.
- Development-reset endpoints must require both explicit enablement and a secret.
- FastAPI requires a future service credential or private gateway policy.

Known integration defects are tracked in `ACTIVE_ROADMAP.md`; this reference does not imply every route currently applies its intended guard correctly.

## 6. Error and Timeout Conventions

Target convention:

- `400`: invalid request or unsupported strategy
- `401`: missing/invalid authentication
- `403`: insufficient role
- `404`: missing resource
- `409`: duplicate/idempotency conflict
- `422`: schema validation
- `429`: rate/work-budget limit
- `500`: sanitized internal failure
- `502/503/504`: upstream optimizer/provider failures

Clients must use abort signals and operation-specific timeouts. Long benchmark execution should return a run ID and be observed through durable job state.

## 7. OpenAPI Regeneration

After repairing the Python environment:

1. start FastAPI;
2. save/inspect `/openapi.json`;
3. compare generated paths and schemas with this inventory;
4. generate typed clients if adopted;
5. fail CI when committed API documentation drifts from OpenAPI.

Do not copy secrets or production URLs into generated artifacts.
