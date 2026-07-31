# UniRide Worklog

This is the curated project chronology. Entries record work and evidence available at that time; they do not override the current architecture, roadmap, or audit.

## 2026-07-30 to 2026-07-31 - Phase 0 Completion (Containment & Reproducible Baseline)

### Scope

- Closed the remaining Phase 0 security and reproducibility items from `ACTIVE_ROADMAP.md`.
- Confirmed earlier containment work via `git log`: localhost binding (`main.py` `OPTIMIZER_HOST`), CLI endpoint auth, and the `_resolve_cli_filepath` path-traversal guard were already in place (commit `61c36c1`); the ESLint gate (`ea75581`) and Pydantic pins (`dcd5896`) were also committed.

### Changes made this session

- **Benchmark endpoint authentication:** Added `Depends(require_internal_api_key)` to `POST /api/v1/benchmark/run`, `/stop`, `/import`, and `/download/{problem_name}` in `optimizer_api/routers/benchmark.py`. Previously only the CLI endpoints were gated.
- **Path traversal hardening:** Added `_sanitize_problem_name()` in `uniride_core/algorithms/tsplib_parser.py` and applied it in `download_tsplib_problem()` and `download_atsp_problem()`, stripping everything outside `[a-z0-9_-]` so caller-supplied names cannot escape `TSPLIB_DATA_DIR`.
- **Python lock file:** Generated `requirements-lock.txt` via `pip-compile --generate-hashes` from `optimizer_api/requirements.txt`, pinning the full transitive closure (FastAPI, uvicorn, supabase, numpy, ortools, pandas, pytest, etc.) with SHA-256 hashes.
- **Lint rules re-enabled:** `react-hooks/purity` and `react-hooks/set-state-in-effect` set to `error` in `eslint.config.mjs` after clearing all 14 pre-existing violations. Verified that the react-hooks 7.x individual rules DO honor standard `eslint-disable-next-line` (an earlier config comment claiming they required Flow-style suppressions was wrong and was removed).
  - Purity fixes (4 sites): sandbox vehicle ids now come from a module-scope monotonic counter (`nextSandboxVehicleId`); the benchmark run panel's elapsed/estimated ETA moved to module-scope wall-clock helpers (`elapsedSeconds`, `estimateRemainingSeconds` in `src/app/page.tsx`); the sidebar skeleton width uses a lazy `useState` initializer instead of `useMemo` + `Math.random()`.
  - set-state-in-effect (10 sites): documented `eslint-disable-next-line` comments on deliberate fetch-on-mount loads (compare, drivers, sandbox, schedules edit, vehicle-planning, driver assignments, driver history) and auth-resolved loading-state syncs (dashboard, ride-history), plus the shadcn carousel embla subscription.
- **CI for Python:** Added a `python` job to `.github/workflows/ci.yml` — Python 3.14 (matching the lock), installs `requirements-lock.txt` + `hypothesis==6.164.0`, collects all three pytest suites, and runs a focused solver-regression subset.

### Verification

- Both edited Python files parse cleanly (`ast.parse`).
- `npm run lint`: 0 errors (159 pre-existing warnings; no unused-disable warnings, confirming every suppression comment is live).
- `npm run typecheck` (`tsc --noEmit`): clean.
- Python collection: **780 tests collected** across `optimizer_api`, `uniride_core`, and `academic_benchmark` (after repairing a corrupt partial `scipy` install and adding `hypothesis`/`pandas`).
- Focused solver regression subset (decoder, split-engine TSP/ATSP dispatch, ortools engine, split-decoder unit/audit, greedy strategy delegation, ft53 ATSP ingestion): **48 passed in ~9s**.
- Local environment aligned to the lock for `protobuf==6.33.6` (ortools requires `<6.34`).

### Roadmap updates

- `ACTIVE_ROADMAP.md` Phase 0: all 8 items complete. Notes document the inline disable comments, the `no-undef`-off rationale (TS/`tsc --noEmit` is the undefined-name gate), and the CI job shape.

## 2026-07-16 - Ultimate Audit and Documentation Consolidation

### Scope

- Completed a verification-only audit of the Next.js frontend, FastAPI backend, shared routing core, and academic benchmark framework.
- Used CodeGraph for AST source, call paths, callers, and blast radius.
- Ran targeted frontend and Python verification without editing application source.
- Read and classified all eligible root/`docs` Markdown files and the historical PDF report.

### Major verified findings

- Duplicate students at one physical `location_code` can overwrite identity/demand and break permutation crossover.
- Cluster-first strategies can return duration-violating routes as successful.
- The time-window split decoder mishandles positive-violation state and can omit feasible pickup prefixes.
- Missing travel arcs can silently become zero, Euclidean-degree, or generic fallback edges.
- FastAPI benchmark/CLI endpoints lack service authentication; CLI preview/import accepted caller-selected paths.
- Strategy factories exist, but production dispatch still uses shared executable instances.
- The DataLoader's claimed singleton lifecycle is ineffective.
- Benchmark admission is raceable and stop does not cancel work.
- Vehicle Planning and Sandbox contain missing-auth paths; direction propagation is incomplete.
- No active GIS renderer or route-geometry contract exists.
- Lint and typecheck gates are not healthy.

### Verification evidence

- Frontend unit tests: 15 passed across three files.
- Typecheck: failed because the installed tree lacked declared `next-intl`; implicit-`any` errors remained.
- Lint: failed because `next lint` is obsolete under the installed Next.js version.
- FastAPI/Python collection: blocked by incompatible `pydantic` and `pydantic-core`.
- Core/academic run: reached 370 passed and 2 skipped before 46 environment/temp-path errors.

### Historical knowledge preserved

- Dual-engine separation was intentional: production reliability and academic exploration have different criteria and lifecycles.
- Cluster-first and giant-tour/split pipelines were retained as alternative strategies.
- OR-Tools, PyVRP, and VROOM were chosen as reference solvers.
- ALNS, adaptive operator scoring, diversity control, layered local search, soft infeasibility, FCM ambiguity, and candidate metaheuristics were evaluated as research directions.
- Durable experimental principles include fixed/paired seeds, common budgets, repeated runs, held-out instances, effect sizes, and code/environment/dataset provenance.
- Unsupported performance percentages, “always feasible” claims, and stale completion statuses were excluded from current documentation.

### Documentation consolidation

- Created `UniRide_Ultimate_Audit.md`.
- Rewrote `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, and `README.md`.
- Replaced this worklog with a curated chronology.
- Archived 22 superseded Markdown files and one historical PDF while preserving their former paths under `archive/docs/`.
- Recreated only `docs/API_REFERENCE.md` and `docs/GITHUB_WORKFLOW.md` as active runbooks.
- Archived the Smart Benchmark manual pending environment, CLI, seed, and evaluation-accounting repair.

## Curated Historical Milestones

### April 2026 - Dual-engine and SOTA exploration

- Established the production-versus-academic track rationale.
- Compared cluster-first and giant-tour/split pipelines.
- Evaluated ALNS, adaptive acceptance, entropy/diversity control, operator evolution, and external baselines.
- Developed initial DOE and statistical-analysis concepts.

Raw documents contained projected improvements and speculative status; they are preserved in `archive/docs/`.

### May-June 2026 - Core migration and benchmark expansion

- Moved substantial algorithm functionality toward `uniride_core`.
- Expanded TSPLIB/ATSP parsing, distance semantics, benchmark registries, solver adapters, and regression tests.
- Added benchmark progress and configuration-promotion tooling.
- Consolidated parts of distance calculation and local search.

Later evidence showed several “complete” claims were premature, especially for feasibility, deterministic seeding, cache lifecycle, cancellation, and constraint-aware repair.

### 2026-06-30 - Distance and registry corrections

- Corrected TSPLIB distance formulas toward reference metric behavior.
- Corrected registry-backed GWO/HHO benchmark execution paths.

These did not close the broader production matrix-domain and feasibility issues found on 2026-07-16.

## Documentation Rule

Current truth is defined by:

1. `UniRide_Ultimate_Audit.md`
2. `CURRENT_ARCHITECTURE.md`
3. `ACTIVE_ROADMAP.md`
4. current code and verification output

Archived reports are historical reasoning only.
