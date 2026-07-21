# UniRide Worklog

This is the curated project chronology. Entries record work and evidence available at that time; they do not override the current architecture, roadmap, or audit.

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
