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
- This audit initially reported the DataLoader singleton lifecycle as ineffective; the 2026-08-01 direct-source re-verification refuted that claim and retained only the separate provider-timeout/cache-health risks.
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

## 2026-07-22 — Package A: YAEM quarantine and contract foundation

- Quarantined the legacy YAEM evidence tree at `archive/academic_benchmark/yaem2026_legacy/`; its manifest represents 159 entries: 93 `HISTORICAL_UNVERIFIED`, 20 `INVALID`, 46 `REFERENCE_ONLY`, and 0 `WITHHELD_SENSITIVE`.
- `python -m academic_benchmark.contracts.export_schemas check` exited 0. `python -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/yaem2026_legacy/manifest.json` exited 0 and reported `verified 159 entries`.
- The Package A focused suite, `python -m pytest academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_archive_manifest.py academic_benchmark/tests/test_yaem_quarantine_boundary.py -q -p no:cacheprovider --tb=short`, passed: 81 passed in 15.96s. The full academic suite, `python -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short`, passed: 409 passed in 34.44s. Both pytest commands used a newly isolated elevated `C:\tmp` `--basetemp`.
- Package/import smokes passed: the schema-resource import check printed `PACKAGE_OK`, and `find_spec('academic_benchmark.yaem2026')` printed `YAEM_NON_IMPORTABLE`.
- Initial subagent test attempts were blocked only by sandbox `tmp_path` permissions for the default user Temp directory and then `C:\tmp`; the elevated isolated-basetemp rerun resolved that environment constraint. It was not a source-test failure.
- No benchmark experiments ran. GitHub push remains deferred to Package D.

## 2026-07-24 — Package B Gate B: Bildiri Canonical Extraction Complete

### Summary

All 11 tasks of the Bildiri Canonical Extraction plan are complete. GWO/HHO solvers have been mechanically relocated from `academic_benchmark/bildiri2026/core/` to `uniride_core/algorithms/tsp_matrix_metaheuristics/` with exact mathematical parity. All active callers have been redirected. Legacy Bildiri material (233 files) has been physically archived with manifest verification.

### Commits

| Hash | Description |
|------|-------------|
| `d959e84` | test(academic): freeze Bildiri solver parity (8-case golden fixture) |
| `38d097f` | refactor(core): own objective budget accounting |
| `e5de75c` | refactor(academic): relocate GWO/HHO to uniride_core |
| `37578f1` | fix(core): report executed solver backends |
| `3d197b2` | refactor(academic): route solvers through canonical core |
| `0ec1a9d` | refactor(academic): retire Bildiri CLI identities |
| `fb51e19` | test(academic): enforce pre-registry migration rejection |
| `bfc101d` | refactor(academic): generalize evidence quarantine classification and includes |
| `d157257` | feat(academic): add Bildiri study profile and ft53 dataset manifest |
| `fe5ffcf` | test(academic): enforce Bildiri extraction boundary |
| `de29083` | chore(academic): quarantine legacy Bildiri evidence |

### Backend Metadata Correction

The `observed_execution_backend` field was updated from availability-based labels (e.g. `mixed-numba-objective-python-polish`) to runtime-observed labels (e.g. `objective=numba;polish=python`). This is an intentional contract correction — the old labels were a known defect. The immutable golden mathematical/accounting fixture remains unchanged and intentionally excludes backend metadata from equality; runtime backend behavior is asserted separately. The native-pilot pure-JIT guard now requires the exact label `objective=numba;polish=none`.

### Verification

**Environment:** Python 3.14.3, NumPy 2.4.6, Numba 0.66.0, llvmlite 0.48.0 (`.venv-jit`)

**Focused JIT/fallback and fair-protocol suite:**
```
pytest test_numba_jit_parity.py test_fair_comparison_protocol.py test_fair_comparison_scientific_integrity.py test_atsp_integration.py test_solver_backend_reporting.py test_bildiri_solver_parity.py -q
```
Result: **115 passed** in 10.12s. No JIT parity skip. Objective kernel has nopython signatures.

**Contract, archive, CLI, production guards:**
```
academic_benchmark.archive_manifest verify --manifest archive/academic_benchmark/bildiri2026_legacy/manifest.json
```
Result: **verified 233 entries**.

```
pytest test_manifest_contracts.py test_archive_manifest.py test_yaem_quarantine_boundary.py test_bildiri_quarantine_boundary.py test_bildiri_study_profile.py test_production_registry_snapshot.py test_legacy_algorithm_migrations.py -q
```
Result: **141 passed** in 19.49s.

`python -m academic_benchmark.cli_engine --help` exits 0.

**Complete academic suite:**
```
pytest academic_benchmark/tests -q
```
Historical pre-fix baseline: **529 passed** in 28.93s. Zero failures. This count is superseded by the 2026-07-27 corrective verification below.

### Archive Inventory

- 233 entries archived to `archive/academic_benchmark/bildiri2026_legacy/`
- Manifest evidence classes: 133 `HISTORICAL_UNVERIFIED`, 7 `INVALID`, 93 `REFERENCE_ONLY`, and 0 `WITHHELD_SENSITIVE`
- SHA-256 checksums verified for all non-withheld entries
- Zero unresolved sensitive findings

### Active Import Audit

- Zero active Python files import `academic_benchmark.bildiri2026`
- `academic_benchmark/bildiri2026` directory is absent from the working tree
- AST boundary tests enforce zero Bildiri reachability

### Production Registry

- STRATEGY_REGISTRY and STRATEGY_FACTORIES remain exactly the approved 38-key set
- B-GA and B-PSO are retired with truthful migration guidance at CLI/smart_benchmark boundaries

### Bildiri Study Profile

- `academic_benchmark/studies/bildiri2026/study.json` is strict, explicit-ID-only, and ATSP-only
- ft53 is the only tracked TSP-family artifact with complete provenance (SHA-256: `692ae545...`)
- No TSP provenance was fabricated

### Explicit Statements

- No paper-scale benchmark ran
- No benchmark CSV or report was generated as part of Package B
- No dependencies, lockfiles, databases, frontend, FastAPI surface, Package A schemas, or YAEM archive were modified
- Rescue checkout (`codex/local-rescue-20260721`) retains its pre-existing dirty files; no Package B edits were merged into it

## 2026-07-27 — Package B Tasks 9–11 Corrective Verification

This corrective pass used strict red-green TDD. The initial red gate produced five expected failures: one ignored arbitrary `.db` evidence file was not blocked, and four inexact native backend labels were accepted. The minimal fixes narrowed disposable caches to actual Python/Numba cache suffixes and required the exact pure-native label `objective=numba;polish=none`. Completion review found two further boundary gaps; mutation tests then produced one expected exact-alias failure and two expected nested-control-filename failures before their fixes. A final independent review found incomplete executable-identity coverage and substring false positives; its focused mutation pair failed twice before the exact AST matcher was implemented. A subsequent strictness mutation then failed three times, proving the former whole-file exemptions hid executable identities appended outside the approved assignments.

The final Bildiri boundary gate now fails closed on missing or malformed manifests, parses active Python without suppressing syntax/decode failures, constrains package discovery to this worktree, rejects legacy and fallback imports (including top-level `core.*`), and rejects exact executable `B-GA`/`B-PSO` string identities plus `BILDIRI_GA`/`BILDIRI_PSO` identifier identities. Exemptions are limited to value nodes of the exact two-entry CLI/migration-test assignments and the boundary test's exact matcher-definition assignment; comments, docstrings, unrelated substrings, and executable identities elsewhere in those files remain fully scanned. The gate also inspects canonical GWO/HHO modules and verifies all 233 archive hashes and the exact manifest/archive content set. Only the archive-root `manifest.json` and `QUARANTINE.md` control files are excluded from that content comparison. Generated packaging metadata no longer lists removed Bildiri modules.

**Pinned `.venv-jit` verification:**

Focused JIT/fallback and fair-protocol suite:

```powershell
& 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark/tests/test_numba_jit_parity.py academic_benchmark/tests/test_fair_comparison_protocol.py academic_benchmark/tests/test_fair_comparison_scientific_integrity.py academic_benchmark/tests/test_atsp_integration.py academic_benchmark/tests/test_solver_backend_reporting.py academic_benchmark/tests/test_bildiri_solver_parity.py -q -p no:cacheprovider --tb=short --basetemp=C:\tmp\pytest-package-b-final-focused
```

Result: **115 passed** in 2.71s.

Final assignment-scoped Bildiri boundary suite:

```powershell
& 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark/tests/test_bildiri_quarantine_boundary.py -q -p no:cacheprovider --tb=short --basetemp=C:\tmp\pytest-package-b-scoped-boundary
```

Result: **21 passed** in 8.25s. The focused three-file mutation was red with 3 failures before the node-scoped fix and green with 3 passes afterward.

Contract, archive, study, registry, and migration suite after completion-review fixes:

```powershell
& 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_archive_manifest.py academic_benchmark/tests/test_yaem_quarantine_boundary.py academic_benchmark/tests/test_bildiri_quarantine_boundary.py academic_benchmark/tests/test_bildiri_study_profile.py academic_benchmark/tests/test_production_registry_snapshot.py academic_benchmark/tests/test_legacy_algorithm_migrations.py -q -p no:cacheprovider --tb=short --basetemp=C:\tmp\pytest-package-b-final-contracts-v4
```

Result: **149 passed** in 38.66s.

Complete academic suite after completion-review fixes:

```powershell
& 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short --basetemp=C:\tmp\pytest-package-b-final-full-v4
```

Result: **541 passed** in 50.56s.

Archive and schema checks:

```powershell
& 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/bildiri2026_legacy/manifest.json
& 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m academic_benchmark.contracts.export_schemas check
```

Results: **verified 233 entries**; schema check exit 0.

No paper-scale benchmark ran, no benchmark output was generated, and archive payload bytes, study/profile contracts, registries, dependencies, databases, and unrelated generated artifacts were not modified.


## 2026-08-01 — WIP Consolidation, Rescue Preservation, and Audit Correction

### Consolidation outcome

- The validated consolidation spine was promoted to local and remote `WIP` at `0ebd63d337dc3fca1a1c9e7644910ecf2e620a79` after rescue tags were pushed and remotely peel-verified.
- Final promotion evidence passed: academic suite 790 tests; `uniride_core` plus `optimizer_api` 461 tests with 1 skip; Numba JIT parity 9 tests with zero skips; frontend 21 tests; TypeScript passed; ESLint reported 0 errors and 159 warnings.
- The user explicitly approved the Supabase-configured production-build waiver and temporary 159-warning lint-cap waiver.
- The user accepted the 99 npm-audit advisories as consolidation debt. These dispositions are not build success, warning remediation, or vulnerability remediation.

### Dirty-checkout preservation

- The original `codex/local-rescue-20260721` checkout was not cleaned, restored, switched, staged, or committed.
- Eleven dirty files were copied with their relative paths to `C:\tmp\UniRide-dirty-preservation-20260801`; independently generated source and copied SHA-256 manifests matched exactly.
- The complete tracked binary patch was preserved as `tracked-diff.patch` with SHA-256 `9736B1604509DBFE3AB2B8F6C74D18B0D4483E2AD82EC6EA5268E7415D72152A`. The original status before and after preservation was identical.

### Audit corrections

- Direct source confirms `DataLoader` uses the thread-safe `SingletonMeta`; the old “new object on every `get_instance()` call” claim is retired.
- Still-open verified risks include PSO's wall-clock fallback seed, missing explicit Supabase provider timeout, stale predecessor handling after a depot token, production import of academic promoted configurations, promoted-name no-op risk, and the absence of a verified reusable GIS map/geometry abstraction.
- The master audit, current architecture, active roadmap, worklog, and consolidation manifest were synchronized while preserving historical evidence as dated context.
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
