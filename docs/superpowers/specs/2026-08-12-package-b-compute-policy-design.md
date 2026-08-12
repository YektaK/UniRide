# Package B Compute Admission, Budget, and Alias Canonicalization Design

**Status:** Approved design baseline; written specification pending final user review
**Date:** 2026-08-12
**Base:** `WIP` at `b9becba1cded4dcfa897cecab9046b322b3be5d7`
**Profile identifier:** `production-conservative-v1`

## 1. Purpose

Package B makes production optimization admission explicit and bounded without changing solver mathematics or academic experiment protocols. It adds service-to-service authentication for heavy compute, validates production request sizes and tuning parameters before work starts, resolves aliases to one canonical execution identity, bounds `/compare` orchestration, and reports the effective policy applied to every result.

This package follows Package A's universal feasibility-certificate boundary. Feasibility remains the final condition for production success and ranking.

## 2. Verified Current Reality

The following facts were verified against live source, CodeGraph call paths, in-memory probes, and focused tests at the stated base:

- `/api/v1/optimize`, `/api/v1/compare`, and `/api/v1/vehicle-calculator` are not protected by a FastAPI dependency. The benchmark router is protected by `require_internal_api_key`.
- The existing internal-key header is `X-Internal-API-Key`.
- The production registry contains 38 keys resolving to 20 canonical names. Alias keys point to the same singleton strategy object.
- An explicit `/compare` list such as `["ga", "genetic_algorithm"]` currently executes the same singleton twice and returns two differently labelled results. Only the omitted/default algorithm list is deduplicated through canonical strategy names.
- `/compare` creates `len(algorithms)` workers and waits up to 120 seconds for each future in submission order. The executor context waits for running workers during shutdown, so this is not a total request deadline.
- `OptimizationRequest` exposes untyped algorithm configuration dictionaries. Existing production requests do not apply the benchmark DTO's parameter upper bounds.
- `sota_config` can override dataclass fields including `time_limit` and `ls_time_limit`; these values are currently untyped and unbounded.
- The exact TSP core truncates waypoint lists above ten. Package A certification demotes an incomplete API result, but direct core and strategy callers can still receive a truncated route.
- The principal optimization, comparison, and vehicle-calculation UI workflows already enter through admin-authenticated Next.js API routes. The older DouBus service contains a separate direct optimizer call and must not receive a browser-visible internal key.
- Focused Package B baseline: 182 tests passed with one Starlette/httpx deprecation warning.

## 3. Alternatives Considered

### 3.1 Public compute with validation only

This would preserve current connectivity but leave expensive solver execution available to any network caller. Input ceilings reduce amplification but do not establish an authorization boundary. Rejected.

### 3.2 Public compute with rate limiting

This would require a durable distributed limiter and an identity model before Package C. It does not solve alias duplication, per-request executor growth, or trusted service authentication. Deferred; rate limiting can be added after durable jobs and deployment topology are defined.

### 3.3 Authenticated heavy compute with bounded policy

Chosen. Next.js remains the authenticated user-facing boundary and calls FastAPI with a server-only internal key. Lightweight metadata and transformation endpoints remain public. Production requests are admitted under one versioned policy profile.

## 4. Authentication Boundary

### 4.1 Protected endpoints

The following endpoints require `X-Internal-API-Key`:

- `POST /api/v1/optimize`
- `POST /api/v1/compare`
- `POST /api/v1/vehicle-calculator`

The following remain public:

- `GET /health`
- `GET /api/v1/strategies`
- `POST /api/v1/extract-time-windows`
- `POST /api/v1/schedule-to-students`

Benchmark endpoints retain their existing internal-key and run-owner-token boundaries.

### 4.2 Secret handling

Next.js server code reads `OPTIMIZER_INTERNAL_API_KEY` and sends it as `X-Internal-API-Key`. The key must never use a `NEXT_PUBLIC_*` name, enter a client component, be returned in an API response, or be logged.

The shared optimizer HTTP client must be server-only. Existing admin-authenticated Next.js routes use it. The legacy DouBus direct caller must either use the same server-only client or remain inaccessible from client bundles; it must never embed the key in browser JavaScript.

### 4.3 Development opt-out

`UNIRIDE_DISABLE_AUTH=1` is the explicit local/test opt-out for both startup and internal-key endpoint checks. If `APP_ENV=production`, setting this flag is a startup error. Without this flag, a missing configured internal key fails closed.

Authentication failures retain the existing `403 Forbidden` behavior and reveal no key/configuration details.

## 5. Canonical Algorithm Identity

### 5.1 Resolution

One resolver maps a submitted key to:

- requested key;
- canonical strategy name;
- request-scoped strategy factory;
- availability state.

The existing registry keys and aliases remain accepted for backward compatibility. Strategy execution must use a fresh factory-created instance per canonical run; request execution must not use mutable registry singletons.

Unknown keys fail before work with HTTP 400. Explicitly requested optional strategies whose dependency is unavailable also fail before work with HTTP 400 and a sanitized availability message.

### 5.2 `/optimize` response naming

`algorithm_used` reports the canonical name. A new optional `algorithm_requested` field preserves the normalized submitted key. Existing response fields are not removed or renamed.

### 5.3 `/compare` deduplication

Explicit algorithm lists are resolved and deduplicated by canonical name before executor creation. First-requested canonical order is preserved. An alias pair therefore produces exactly one execution and one canonical result.

`results[].algorithm`, `best_algorithm`, `fastest_algorithm`, and `summary` keys are canonical. Optional requested-alias metadata may list every submitted key that resolved to that canonical run.

## 6. Versioned Compute Policy

### 6.1 Separation of defaults and ceilings

The policy has two layers:

1. **Operational defaults** may be lowered through validated server configuration without changing the API schema.
2. **Hard safety ceilings** are code-reviewed limits. Raising one requires a source change, tests, roadmap/worklog evidence, and a profile-version change.

Server configuration may lower a hard ceiling but may never raise it. The validated environment names are `UNIRIDE_COMPUTE_MAX_STUDENTS`, `UNIRIDE_COMPUTE_MAX_VEHICLES`, `UNIRIDE_COMPUTE_MAX_ALGORITHMS`, `UNIRIDE_COMPUTE_MAX_WORKERS`, `UNIRIDE_COMPUTE_DEADLINE_SECONDS`, `UNIRIDE_COMPUTE_SOLVER_SECONDS`, `UNIRIDE_COMPUTE_MAX_ITERATIONS`, `UNIRIDE_COMPUTE_MAX_POPULATION`, and `UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS`. Invalid or out-of-range configuration fails at startup; it must not silently fall back.

### 6.2 `production-conservative-v1` hard ceilings

| Limit | Operational default | Hard ceiling |
|---|---:|---:|
| Students per optimization request | request supplied | 250 |
| Vehicles per optimization request | request supplied | 50 |
| Canonical algorithms per comparison | six-algorithm set in Section 7 | 6 |
| Comparison workers | 2 | 2 |
| Total comparison response deadline | 120 seconds | 120 seconds |
| Solver runtime when supported | 60 seconds | 60 seconds |
| Iterations/generations | registered strategy default | 2,000 |
| Population/swarm/pack/hawks | registered strategy default | 250 |
| Local-search sublimit | registered strategy default | 2 seconds |

The values above are initial production-safe ceilings, not permanent algorithm claims. They may be revised through the change process in Section 12.

### 6.3 Request validation

Production DTOs enforce list-size limits and positive numeric bounds before strategy resolution or worker creation. Violations use normal Pydantic HTTP 422 validation responses.

`production-conservative-v1` freezes these exhaustive public tuning-key allowlists:

| Request field | Accepted keys |
|---|---|
| `ga_config` | `crossover_rate`, `diversify_threshold`, `elite_count`, `local_search_interval`, `local_search_type`, `max_iterations`, `max_no_improvement`, `mutation_rate`, `population_size`, `seed`, `tournament_size` |
| `pso_config` | `cognitive_weight`, `inertia_min`, `inertia_weight`, `local_search_interval`, `local_search_type`, `max_iterations`, `max_no_improvement`, `max_velocity_size`, `reinit_interval`, `seed`, `social_weight`, `swarm_size`, `velocity_clamp` |
| `gwo_config` | `exploration_rate`, `initial_a`, `local_search_interval`, `local_search_type`, `max_iterations`, `max_no_improvement`, `population_size`, `seed` |
| `hho_config` | `initial_energy`, `jump_probability`, `levy_flight_scale`, `local_search_interval`, `local_search_type`, `max_iterations`, `max_no_improvement`, `population_size`, `seed` |
| `two_opt_config` | `first_improvement`, `max_iterations`, `multi_start`, `num_starts`, `seed` |
| `sota_config` | `acceptance_types`, `crossover_rate`, `delta_threshold`, `destroy_ops_pool`, `diversity_check_interval`, `diversity_injection_rate`, `diversity_threshold`, `entropy_check_interval`, `entropy_threshold`, `gamma`, `genome_injection_rate`, `genome_population_size`, `h_end`, `h_start`, `injection_rate`, `lahc_history`, `learn_period`, `ls_intensity_compress`, `ls_intensity_constructive`, `ls_intensity_destructive`, `ls_intensity_moderate`, `ls_intensity_normal`, `ls_time_limit`, `max_iterations`, `meta_evolution_interval`, `mutation_rate`, `n_edges_aggressive`, `n_edges_normal`, `p_best`, `p_gbest`, `population_size`, `pulse_injection_rate`, `remove_ratio`, `remove_ratio_range`, `repair_ops_pool`, `sa_cooling_rate`, `sa_end_temp`, `sa_start_temp_factor`, `seed`, `segment_size`, `theta_base`, `three_opt_window`, `time_limit`, `tournament_k`, `tournament_size` |

A key outside its request-field allowlist is rejected with 422. After canonical strategy resolution, a key not consumed by the selected strategy is also rejected with 422 rather than silently ignored.

The budget-bearing key classification is exhaustive:

- iteration and interval controls (`max_iterations`, `max_no_improvement`, `diversify_threshold`, `local_search_interval`, `reinit_interval`, `entropy_check_interval`, `diversity_check_interval`, `learn_period`, and `meta_evolution_interval`) are positive and cannot exceed the 2,000-iteration ceiling where applicable;
- replicated-allocation controls (`population_size`, `swarm_size`, `genome_population_size`, `elite_count`, `tournament_size`, `tournament_k`, `num_starts`, and `lahc_history`) are positive and cannot exceed 250;
- clock controls (`time_limit` and `ls_time_limit`) cannot exceed 60 and 2 seconds respectively;
- structural search controls (`max_velocity_size`, `three_opt_window`, `segment_size`, `n_edges_normal`, and `n_edges_aggressive`) are positive and cannot exceed the smaller of the effective student limit and 250.

Listed non-budget tuning keys retain their existing meaning but receive typed validation: probabilities/rates stay finite in their semantic range, other numeric values stay finite, enum/operator values stay within the strategy's existing supported set, and relational constraints such as elite or tournament size not exceeding effective population are enforced.

Boolean values are not valid integers. Non-finite values, negative values, unknown budget aliases, and values above the applicable ceiling are rejected. Request values are never silently clamped.

Academic `BenchmarkRunRequest` bounds remain separate. Package B must not weaken, reuse as production truth, or silently change academic fairness limits.

### 6.4 Effective policy application

When callers omit a budget, the server applies the versioned operational default. When callers provide a lower valid value, the lower value becomes effective. Strategy defaults and promoted configuration cannot raise the effective value above the production profile.

The policy adapter translates the common effective budget into each supported strategy's existing configuration names using a request-local copy. It must not mutate registry instances, promoted configuration, request objects shared by concurrent runs, or core global state.

## 7. Default Comparison Set

When `CompareRequest.algorithms` is omitted, Package B runs this ordered canonical set:

1. `greedy`
2. `two_opt`
3. `genetic_algorithm`
4. `ga_split`
5. `pso_split`
6. `ortools_cvrp`

The set is intentionally limited to six distinct production roles. Exact enumeration, SOTA solvers with large native time limits, optional dependency variants, compatibility variants, and near-duplicate strategies are explicit opt-ins.

An unavailable explicit strategy fails before any comparison work. The default set must be validated at startup; an unavailable default is a deployment/configuration error rather than a silent substitution.

## 8. Comparison Execution and Ranking

### 8.1 Orchestration

Worker count is `min(effective_worker_limit, canonical_algorithm_count)` and never exceeds two under this profile. A single monotonic total deadline applies to the comparison response; timeouts are not multiplied by algorithm count or waited sequentially.

Pending futures are cancelled at the deadline. Executor shutdown must not wait for unfinished work before returning the response. Running Python threads cannot be forcibly terminated safely; therefore Package B provides bounded admission and response latency, not hard solver cancellation.

Package C owns cooperative cancellation, process isolation, durable job state, and proof that timed-out work actually stops. Package B response metadata must label its cancellation mode as `soft_response_deadline`.

### 8.2 Result eligibility

A result is rank-eligible only when:

- the strategy reports success;
- Package A's typed feasibility certificate exists;
- the certificate reports feasible;
- the result completed within the comparison response policy.

Failures, unavailable strategies, exceptions, uncertified results, infeasible results, and timed-out results are never ranked.

### 8.3 Ranking rules

`best_algorithm` is the eligible result with the lowest `total_duration_minutes`. Ties are resolved by lower `total_vehicles`, then canonical algorithm name.

`fastest_algorithm` is the eligible result with the lowest `execution_time_seconds`. Ties are resolved by canonical algorithm name.

`CompareResponse.success` is true only when at least one eligible result exists. If none exists, both ranking fields are empty strings and the response retains typed failure/certificate details for each run.

## 9. Applied-Policy Metadata

`OptimizationResponse`, `AlgorithmResult`, and `CompareResponse` receive backward-compatible optional typed policy metadata for every solver execution outcome. HTTP authentication, resolution, and DTO-validation errors remain ordinary sanitized FastAPI error responses because no solver execution occurred. Result metadata contains only non-secret operational facts:

- profile identifier;
- requested and canonical algorithm identity;
- effective student, vehicle, iteration/population, runtime, and local-search limits that apply;
- comparison worker ceiling and total deadline when relevant;
- cancellation/enforcement mode;
- whether each value came from the profile default or a lower caller declaration.

The metadata must describe actual applied behavior. It must never claim hard cancellation, an evaluation budget, or a solver-native time limit that the selected engine does not implement.

## 10. Exact-Solver Safety Repair

The exact TSP solver must reject waypoint counts above `max_permutation_size`; it must not slice the input. The production adapter must fail before factorial work and return a sanitized, certified failure. Direct core callers receive a documented exception.

This is a correctness repair, not a change to the maximum supported exact problem size. The limit remains ten.

## 11. File Ownership and Intended Change Surface

The implementation plan may assign exact filenames differently after fresh CodeGraph inspection, but responsibilities remain:

- `optimizer_api/compute_policy.py` — immutable profile, validated server overrides, effective-policy resolution, and metadata construction;
- `optimizer_api/strategies/canonical.py` — canonical alias resolution, availability, and request-scoped factory access;
- `optimizer_api/models/schemas.py` — additive typed budget/policy DTOs and pre-work validation;
- `optimizer_api/routers/optimization.py` — authenticated entry points, canonical execution, bounded orchestration, ranking, and metadata attachment;
- `optimizer_api/auth.py` and `optimizer_api/runtime_config.py` — unified internal-key/dev-opt-out semantics;
- `src/services/optimizer-service.ts` or a smaller server-only client — internal header injection without browser exposure;
- affected Next.js API routes and the legacy DouBus caller — server-only routing and compatibility;
- `uniride_core/algorithms/string_exact_tsp.py` — fail-fast size handling only;
- focused Python and TypeScript tests — RED-GREEN proof for each boundary.

No production registry alias is removed. No solver formula, academic registry, study profile, fairness protocol, dataset, dependency manifest, database, or generated evidence is changed.

## 12. Profile Change Process

A later profile revision is allowed. Every revision must:

1. change the profile identifier;
2. state which defaults or hard ceilings changed and why;
3. update focused boundary tests;
4. rerun Package B regression gates and the full affected Python/TypeScript suites;
5. update `ACTIVE_ROADMAP.md` and `WORKLOG.md`;
6. preserve prior profile identifiers in historical run/result metadata;
7. avoid presenting operational limits as academic fairness budgets.

Lower deployment-specific defaults may be applied through validated server configuration without a source profile revision, provided the effective values are emitted in response metadata. Raising a hard ceiling always requires the reviewed source process above.

## 13. Verification and Acceptance Gates

Implementation is accepted only when tests prove:

- missing/wrong internal keys deny all three heavy endpoints and correct keys allow them;
- public metadata/transformation endpoints remain public;
- no internal key appears in browser bundles, responses, or logs;
- every registry alias resolves to one canonical identity and a fresh strategy instance;
- explicit alias duplicates execute once;
- unknown and unavailable algorithms fail before work;
- all hard ceilings and lower caller declarations validate deterministically;
- invalid budget fields return 422 before strategy execution;
- comparison workers never exceed two and one total 120-second deadline is used;
- timed-out work is reported as soft-deadline failure and never ranked;
- ranking considers only certified feasible results and follows the documented tie-breakers;
- the default comparison set is exactly the six ordered canonical algorithms in Section 7;
- every solver-execution success or failure result contains truthful applied-policy metadata; authentication, resolution, and DTO-validation errors remain sanitized 403, 400, or 422 responses without execution metadata;
- exact TSP input above ten fails rather than truncates;
- Package A feasibility tests remain green;
- production registry snapshot tests remain green;
- focused frontend service/BFF tests, TypeScript, and `git diff --check` pass.

The implementation plan must start from an isolated clean branch based on the then-current `origin/WIP`, use RED-GREEN TDD, preserve unrelated worktrees, and require explicit authorization before merge or push.

## 14. Explicit Non-Goals

Package B does not implement:

- hard termination of running Python threads;
- process-isolated solver workers or durable job queues;
- distributed rate limiting;
- solver objective-evaluation counters or academic fixed-budget accounting;
- new solver algorithms or parameter tuning;
- paper-scale experiments or superiority claims;
- frontend UX redesign;
- GIS geometry or map rendering;
- dependency upgrades or security-debt remediation.

Those concerns remain assigned to later roadmap packages unless separately authorized.
