# Independent verification of the 2026-10-01 UniRide ultimate audit

**Prepared:** 2026-10-01\
**Reviewer:** Codex, with one completed independent GPT-5.6 Sol security/frontend review\
**Repository:** UniRide (repository root of the local checkout)\
**Verified checkout:** a54b7864af263a639d3e251d803647c0389c43b0\
**Audit reviewed:** docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md, audit baseline 316cbab\
**Authorization:** read-only technical evaluation and this report artifact; no remediation, deployment, publication, database changes, or tracker closures.

## 1. Assessment

The audit's central warning is justified. There are real defects in authorization policy, matrix fallback and certification, benchmark admission/cancellation, legacy academic execution, and statistical reporting. Several defects survived the existing green tests. This is a release and scientific-evidence problem, not merely an accumulation of cosmetic debt.

I reproduced the legacy matrix-cache corruption: **four of six runs produced different costs when the cache was shared across problems**. I also reproduced a successful zero-cost route with a feasible certificate, a stopped-but-still-running worker freeing an admission slot, omitted school-return timing, conflicting response arrival times, duplicate DataLoader singletons, missing academic protocol metadata, and fractional-cost rejection. These are concrete reasons to act on the audit.

The report is stronger as a defect inventory than as a set of universal severity labels or an implementation plan. Some findings depend on deployed RLS, a public deployment, particular import layouts, legacy execution paths, or data already in an academic database. Some proposed changes overreach the approved contracts. Several broad statements need correction: CI has another test workflow; archive-aware YAEM tests already exist; pilots already emit manifests; App Router's bundled React is expected; repeated objective calls comply with the current budget definition; and some proposed dead-code deletions would remove live interfaces.

**My decision:** retain the experimental/non-release status; treat the confirmed trust-boundary defects as blockers for the affected operational or scientific use; correct the audit's overstatements before using it as a remediation specification. A wholesale rewrite is not justified by this review.

Earlier successful component tests remain useful evidence for their tested contracts. They did not establish that every browser entry point enforced user authorization, that certification used authoritative source costs, or that every academic entry point produced governed evidence. I should have made those limits clearer whenever describing progress as being on track. This review does not reconstruct every earlier conversation or attribute every defect to a particular author.

## 2. What was verified, and what was not

### Current source, rather than stale audit findings

Between 316cbab and a54b786, git reports changes only to AGENTS.md, UniRide_Ultimate_Audit.md, and the new audit document. **There is no application-source drift between the audited baseline and this checkout.**

The initial dirty tree contained only the pre-existing untracked INSTRUCTION_REVIEW_2026-09-07.md. This review leaves that file untouched and adds only this companion report. The original audit and its remediation tracker remain unchanged; no finding is marked fixed.

### Evidence labels used below

| Label | Meaning |
|---|---|
| R | Reproduced in a bounded, offline check during this review. |
| S | Verified against current source and relevant callers; the harmful runtime scenario was not exercised. |
| Q | The mechanism is real, but scope, severity, reachability, or a compound subclaim needs qualification. |
| U | Retained for triage, but this review did not independently establish the full claim. Original measurements are not fresh measurements. |

These labels assess evidence, not whether a finding is already remediated. Compound findings can have different labels for different parts. There is no fabricated aggregate accuracy score.

### Independent review and tool limitations

The Superpowers receiving-review and parallel-review workflows were used, together with the requested Ponytail whole-repository complexity lens. Three isolated GPT-5.6 Sol review lanes were dispatched because security, operational routing, and academic correctness require separate high-risk checks. The security/frontend reviewer completed and returned exact source references and six passing Vitest files. The production and academic reviewers hit account usage limits before returning conclusions. **Their outputs are not counted as completed independent reviews.** Codex performed the operational and academic checks reported here.

CodeGraph indexing was attempted, including the sandbox escalation retry, but the existing database could not be refreshed because of an EPERM/in-use failure. Initialization reported an existing project. CodeGraph node/explore was used before targeted lexical searches; current file content was also read directly. On-disk source references were checked, but graph dependency metadata is not certified freshly indexed. No index files were deleted and no unrelated processes were stopped.

Some shell launches failed with CreateProcessWithLogonW error 267. Necessary checks were retried with the permitted escalation and completed. A launch failure is not counted as a test failure.

No live Supabase policies, deployment exposure, production credentials, database result contents, dependency-audit totals, full production build, or paper-scale experiments were verified. The audit's full-suite and performance measurements remain its reported evidence unless explicitly rerun below.

## 3. Critical findings: disposition and practical impact

| ID | Evidence | Independent disposition |
|---|---|---|
| C1 | S/Q | Repository RLS permits a user to insert their own profile with role=admin. Critical if deployed policies and provisioning behavior match these files. Live exploitability was not tested. |
| C1.b | S/Q | Own-row ride policies do not constrain privileged statuses or operational fields. High on current evidence; Critical requires a verified current dispatch consequence. |
| C2 | R/S/Q | Missing-matrix fallback can produce zero costs that the response certificate accepts. Critical for treating affected results as operationally feasible. Snapshot-bound admission does fail closed when a required snapshot is unavailable. |
| C3 | R/S/Q | The legacy id()-keyed cache corrupts cross-problem runs. A scientific blocker for that execution path. This is not evidence that every governed fair/native result is corrupted. |
| C4 | R/S/Q | Anonymous BFF benchmark start plus status-only cancellation/admission creates an availability risk. Critical when publicly reachable and expensive workers are enabled; public reachability was not checked. |
| C5 | S/Q | Statistical claims are methodologically unsafe. Disable inferential/publication claims before using that dashboard as evidence. SciPy is absent in the inspected venv, so the tab was not executed here. |

### C1 and C1.b: internal API authentication does not cure browser database policy

The user insert policy checks only that auth.uid() equals the inserted id: [supabase/rls_policies.sql:46-48](<../supabase/rls_policies.sql:46>). The role guard is an UPDATE OF role trigger, not an insert restriction: [supabase/rls_policies.sql:59-81](<../supabase/rls_policies.sql:59>). The schema permits admin as a role. Client registration accepts a role argument and passes it into a browser-client user insert: [src/lib/supabase-auth.ts:121-157](<../src/lib/supabase-auth.ts:121>) and [src/lib/supabase-db.ts:130-155](<../src/lib/supabase-db.ts:130>). Administrative authorization then trusts the stored role: [src/lib/admin-auth.ts:70-99](<../src/lib/admin-auth.ts:70>) and [src/lib/admin-auth.ts:121-134](<../src/lib/admin-auth.ts:121>).

The ordinary registration form supplies student. That does not enforce a trust boundary against a modified browser or direct authenticated PostgREST call. However, repository SQL alone cannot establish the actual production policies, email-confirmation requirements, or a deployment-only user-provisioning trigger. The precise conclusion is **an unsafe repository policy**, with critical deployment impact conditional on live configuration.

Ride insert/update policies similarly restrict ownership without restricting operational state: [supabase/rls_policies.sql:104-116](<../supabase/rls_policies.sql:104>). The normal BFF deliberately writes pending_admin_approval, but an own-row database write is not equivalently constrained. Legacy routing reads confirmed rows. This confirms an authorization gap over the attacker's own request; it does not prove that an attacker can edit everyone else's rides or directly control the current day-planning publication workflow.

The smallest remedy is an authoritative insert/state-transition policy at the shared database boundary, verified on the deployed policy set. Additional UI checks are not an adequate substitute.

### C2: a certificate exists, but source-cost independence is incomplete

The response certifier explicitly documents its current internal-consistency scope and deferred source-matrix provenance: [optimizer_api/verification/response_certifier.py:3-7](<../optimizer_api/verification/response_certifier.py:3>) and [optimizer_api/verification/response_certifier.py:231-236](<../optimizer_api/verification/response_certifier.py:231>). It builds a matrix from the solver's reported route-detail durations: [optimizer_api/verification/response_certifier.py:374-390](<../optimizer_api/verification/response_certifier.py:374>), then runs duration/window checks against that constructed matrix: [optimizer_api/verification/response_certifier.py:473-481](<../optimizer_api/verification/response_certifier.py:473>).

With no loaded source matrix and no supplied coordinates, the repository can return a zero submatrix: [optimizer_api/utils/matrix_repository.py:294-305](<../optimizer_api/utils/matrix_repository.py:294>). An offline one-student ga_split request with four individuals and one generation returned:

~~~text
success True
duration 0.0
route arcs [[0.0, 0.0]]
certificate is_feasible True
~~~

This confirms the central fail-open claim. The final certificate is structurally separate from the solver, but it cannot independently detect incorrect source costs when it reconstructs those costs from solver output.

There is an important limit: the optional snapshot-binding checks in [optimizer_api/routers/optimization.py:211-234](<../optimizer_api/routers/optimization.py:211>) reject unavailable or changed snapshots. The entire endpoint is not universally fail-open. The original audit's separate OR-Tools rounding example was not rerun in this review; it should be covered when replacing reported-arc certification with authoritative re-costing.

A source-bound certificate should receive the same immutable authoritative matrix used for solving, validate used arcs and units, and independently simulate full routes. Adding another wrapper around the current self-reported durations would not fix the defect.

### C3: the cache corruption was independently reproduced

The cache key includes a frozenset of location labels and id(duration_func), while its stored value retains the matrix and labels but not the function: [uniride_core/algorithms/local_search_numba.py:109-136](<../uniride_core/algorithms/local_search_numba.py:109>). After the function is collected, its integer identity can be reused for a different matrix with the same labels. The lookup occurs before the new function's prebuilt matrix is considered.

The audit's Appendix H.1 script was executed unchanged in logic with the existing venv, offline. Exit code was zero:

~~~text
cache entries after 6 runs: 2
P1 seed=11 shared-process=6595.6 clean-cache=6595.6
P1 seed=12 shared-process=6564.6 clean-cache=6564.6
P2 seed=11 shared-process=31434.5 clean-cache=6744.7
P2 seed=12 shared-process=32994.0 clean-cache=6399.4
P3 seed=11 shared-process=30743.3 clean-cache=6413.1
P3 seed=12 shared-process=30523.0 clean-cache=6623.0
runs corrupted: 4 of 6
~~~

An earlier synthetic allocation experiment did not trigger identity reuse in 1,000 attempts. That non-reproduction does not refute the subsequent realistic six-run reproduction.

The fair/native manifest branches in [academic_benchmark/core/registry_setup.py:345-365](<../academic_benchmark/core/registry_setup.py:345>) use a different direct matrix/accounting path. Consequently, this reproduction invalidates confidence in affected legacy/shared-process runs, not every historical result indiscriminately. Identify result provenance before deciding which evidence requires quarantine or rerun.

The simplest fix is to remove reliance on recycled function identities and pass the already available matrix through the live callers. If any cache remains, its lifetime and matrix identity must be real, bounded, and tested; a second global cache is unnecessary.

### C4: stopping status is not stopping work

The browser-facing benchmark start handler has no user/admin authorization: [src/app/api/benchmark/run/route.ts:38-146](<../src/app/api/benchmark/run/route.ts:38>). The proxy's API authorization match covers admin routes: [src/proxy.ts:44-46](<../src/proxy.ts:44>). The benchmark BFF uses server-side optimizer transport that attaches the private optimizer key: [src/lib/optimizer-server.ts:5-14](<../src/lib/optimizer-server.ts:5>). Keeping that key private does not authorize the anonymous caller.

Admission counts runs whose status is RUNNING; stop changes status without necessarily ending the executing thread: [optimizer_api/benchmark_state.py:152-157](<../optimizer_api/benchmark_state.py:152>) and [optimizer_api/benchmark_state.py:241-248](<../optimizer_api/benchmark_state.py:241>). A bounded fake-worker reproduction established:

~~~text
initial_admit_more False
stopped_but_worker_alive True
replacement_admitted True
all_workers_joined True
~~~

This check used finite fake workers and joined them; it did not run a destructive denial-of-service workload. It proves that the status/admission invariant is wrong. Authenticating start and keeping work admitted until its worker actually exits are separate necessary fixes. Hard cancellation/process isolation remains the longer-term operational requirement.

### C5: statistical language must be removed before evidence use

The dashboard independently gathers avg_gap arrays by algorithm and checks only equal lengths before applying Wilcoxon: [academic_benchmark/dashboard.py:343-347](<../academic_benchmark/dashboard.py:343>). There is no verified pairing by replicate/seed_group, protocol, or implementation. It computes losses but omits them from the generated claim, and emits a significantly-outperforms sentence from the win summary: [academic_benchmark/dashboard.py:365-373](<../academic_benchmark/dashboard.py:365>).

SciPy describes Wilcoxon for related paired samples; equal array length alone does not establish pairing. See [SciPy Wilcoxon documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html).

Import probing confirmed scipy_installed False in this venv. The unsafe code is real, but no p-value was computed here. This is a scientific-reporting blocker if that UI is used on a machine with the required optional dependencies. It is not evidence that a submitted paper already contains fabricated claims.

Disable inference from these rows until the Package D analysis contract is implemented. Descriptive smoke output can remain clearly identified as such.

## 4. High findings: complete triage

| ID | Evidence | Evaluation and corrected scope |
|---|---|---|
| H1 | S/Q | Anonymous hint disclosure and account enumeration are real: [src/app/api/auth/hint/route.ts:40-101](<../src/app/api/auth/hint/route.ts:40>). The XFF-based limiter bypass depends on the deployment's trusted-header behavior. Remove secret-like hints from anonymous responses. |
| H2 | R/S | The pickup checker stops after the last customer and omits return/waiting feasibility: [uniride_core/algorithms/feasibility_certificate.py:206-277](<../uniride_core/algorithms/feasibility_certificate.py:206>). The reproduced route reaches school at 08:40 despite an 08:30 target and returns zero window violations. |
| H3 | R/S/Q | Response timing uses another backward schedule: [uniride_core/algorithms/route_scheduling.py:37-64](<../uniride_core/algorithms/route_scheduling.py:37>). Reproduced A=08:25 when A's latest is 08:00; current clients' use of these fields was not established. |
| H4 | S/Q | Split search evaluates capacity/duration-only decoding, with windows applied later: [uniride_core/algorithms/ga_split_engine.py:109-132](<../uniride_core/algorithms/ga_split_engine.py:109>) and corresponding GWO/PSO/HHO engines. This primarily causes rejection/poor search under window constraints; the certificate does not make the search window-aware. The audit's individual solver scenarios were not all rerun. |
| H5 | R/S/Q | Importing utils.data_loader and optimizer_api.utils.data_loader creates different classes and singletons. Direct identity reproduction returned False/False. The mixed imports exist in [optimizer_api/routers/readiness.py:10-17](<../optimizer_api/routers/readiness.py:10>) and [optimizer_api/routers/optimization.py:56](<../optimizer_api/routers/optimization.py:56>). The claimed deployed TTL frequency and end-to-end outage were not measured here. |
| H6 | S/Q | Async readiness handlers call synchronous refresh/health paths: [optimizer_api/routers/readiness.py:57-98](<../optimizer_api/routers/readiness.py:57>); repository refresh locks around provider loading at [optimizer_api/utils/matrix_repository.py:178-197](<../optimizer_api/utils/matrix_repository.py:178>). Event-loop blocking is a real mechanism; the audit's 2,703 ms measurement is not a new measurement. |
| H7 | S/Q | Per-request compare executors use shutdown(wait=False), and optimize directly calls the solver without an endpoint deadline: [optimizer_api/routers/optimization.py:228](<../optimizer_api/routers/optimization.py:228>) and [optimizer_api/routers/optimization.py:516-558](<../optimizer_api/routers/optimization.py:516>). No process-wide solver cap was established. Soft cancellation was already explicitly documented as open. Hour-scale estimates were not rerun. |
| H8 | S/Q | Production mounts/imports academic benchmarking and writers/readers lack the required governed separation: [optimizer_api/main.py:18](<../optimizer_api/main.py:18>) and [optimizer_api/main.py:109](<../optimizer_api/main.py:109>); [academic_benchmark/tsplib_manager.py:93-151](<../academic_benchmark/tsplib_manager.py:93>); [academic_benchmark/dashboard_utils.py:48-61](<../academic_benchmark/dashboard_utils.py:48>). Aggregate rows can be labelled as one raw run. Actual database contamination was not inspected. |
| H9 | S/Q | Core-GWO/HHO/TwoOpt names have different implementations across matrix factory and academic registry: [uniride_core/algorithms/engine_factory.py:28-34](<../uniride_core/algorithms/engine_factory.py:28>) and [academic_benchmark/core/registry_setup.py:791-837](<../academic_benchmark/core/registry_setup.py:791>). Registration overrides depend on successful imports. Do not pool results by these strings alone; every entry point was not dynamically exercised. |
| H10 | S/Q | SOTA local search still calls the old Numba 3-opt kernel: [uniride_core/algorithms/sota_tsp/ls_engine.py:142-150](<../uniride_core/algorithms/sota_tsp/ls_engine.py:142>). This conflicts with the broader canonical retirement requirement; the passing canonical integration suite does not prove this SOTA path uses the canonical operator. No spy run was repeated here. |
| H11 | S/Q | Layer execution depends on time.monotonic checks: [uniride_core/algorithms/sota_tsp/ls_engine.py:213-217](<../uniride_core/algorithms/sota_tsp/ls_engine.py:213>). Same-seed result variability is credible under warm-up/load. The audit's 288/280/280 costs were not reproduced here; do not treat wall-clock native termination as fixed-budget evidence. |
| H12 | S/Q | Clustering uses the global unseeded random module: [uniride_core/algorithms/clustering_strategies/kmeans.py:11-23](<../uniride_core/algorithms/clustering_strategies/kmeans.py:11>). Related strategy-private seeds do not control that shared state. The audit's six-partition counts were not rerun. |
| H13 | R/S/Q | Normal governed dispatch without injected fair/native manifests fails result validation. The gateway passes params through unchanged: [academic_benchmark/core/execution_gateway.py:204-219](<../academic_benchmark/core/execution_gateway.py:204>). CLI seeds also depend on combo index: [academic_benchmark/cli_engine.py:955-970](<../academic_benchmark/cli_engine.py:955>); Smart uses 42+run_idx. Three canonical algorithms were reproduced failing. This is a fail-closed functional defect, not acceptance of invalid governed evidence. |
| H14 | S/Q | Two-second async intervals, swallowed terminal errors, component-only ownership state, stale results and demo flips can race/orphan runs: [src/app/(app)/admin/benchmark/page.tsx:267-336](<../src/app/(app)/admin/benchmark/page.tsx:267>) and [src/app/page.tsx:577-631](<../src/app/page.tsx:577>). The completed independent reviewer traced the mechanisms; slow-network manifestations were not reproduced. |
| H15 | S | Users API returns snake_case while the page reads disabilityType: [src/app/api/admin/users/route.ts:41-55](<../src/app/api/admin/users/route.ts:41>) and [src/app/(app)/admin/vehicle-planning/page.tsx:62-102](<../src/app/(app)/admin/vehicle-planning/page.tsx:62>). The existing camelCase So-only fixture masks the Sw misclassification. High for accessibility planning; it does not establish that all optimizer inputs have this mapping defect. |
| H16 | S/Q | Solomon parsing leaves the default school-pickup direction, and that certificate omits depot due-time validation: [uniride_core/adapters/matrix_builder.py:328-338](<../uniride_core/adapters/matrix_builder.py:328>) and [uniride_core/algorithms/feasibility_certificate.py:206-277](<../uniride_core/algorithms/feasibility_certificate.py:206>). A dedicated forward CVRPTW contract is required. The specific Solomon numerical scenario was not rerun, nor was use in published evidence established. |
| H17 | S/Q | Production imports the academic promoted-config loader: [optimizer_api/strategies/promoted_config_loader.py:9-36](<../optimizer_api/strategies/promoted_config_loader.py:9>). That runtime dependency is real; the audit says the promoted parameter file is absent, and this review did not inspect evidence of active parameter contamination. |
| H18 | S/Q | Compatibility normalization reads distance_matrix for asymmetry while creating indexed coordinates, and production solving uses the DataLoader: [optimizer_api/models/schemas.py:246-287](<../optimizer_api/models/schemas.py:246>) and [optimizer_api/routers/optimization.py:183-184](<../optimizer_api/routers/optimization.py:183>). Reject unsupported explicit matrices or implement an explicit supported path; do not silently substitute costs. No end-to-end explicit-matrix request was repeated. |
| H19 | S/Q | Quick runner converts TSPLIB coordinates to production lat/lng, calls production strategies, then rescales with the TSPLIB metric: [optimizer_api/benchmark_runner.py:154-224](<../optimizer_api/benchmark_runner.py:154>) and [optimizer_api/benchmark_runner.py:369-401](<../optimizer_api/benchmark_runner.py:369>). Objective mismatch is real in the flow; instance-specific successes/NaNs were not rerun. |
| H20 | S/Q | WIP ci.yml executes eight focused Python files after full collection. benchmark.yml executes additional SOTA/regression tests. Therefore only-eight-repository-wide is too broad. Full canonical execution and build coverage still have gaps. See [.github/workflows/ci.yml:45-60](<../.github/workflows/ci.yml:45>) and [.github/workflows/benchmark.yml:34-47](<../.github/workflows/benchmark.yml:34>). |

### New bounded runtime evidence for H2, H3, H5, H13

For H2, the checked cycle has travel 10+20+20=50 minutes. Starting at 07:25, waiting at the first stop until 08:00 makes the second stop 08:20 and school return 08:40. The checker reported zero window and travel-duration violations. Waiting makes elapsed duration 75 minutes, beyond the checked 60-minute travel cap. The core certificate functions were called directly; this review did not repeat the full HTTP ga_split request for this timing case.

For H3, the returned schedule was:

~~~text
arrival_times {'LB': '08:30', 'LA': '08:25', 'D.Kampus': '08:15'}
departure 08:00
~~~

LA had pickup_time 08:00. This demonstrates a contradiction in the actual response-timing helper, independently of a UI consuming the values.

For H5:

~~~text
same_class False
same_singleton False
~~~

This directly tests the problematic dual import layout, not every deployment command.

For H13, with the installed Numba backend and prefer_numba_objective policy:

~~~text
Core-TwoOpt-TSP ResultContractViolation result algorithm_id must be the canonical algorithm_id selected by preflight
ALNS-TSP ResultContractViolation result algorithm_id must be the canonical algorithm_id selected by preflight
Core-GWO-TSP-Pure ResultContractViolation result algorithm_id must be the canonical algorithm_id selected by preflight
~~~

A Python-only first attempt rejected GWO/HHO at capability preflight before execution. That was not the post-run defect. The corrected policy reached the executors and reproduced the reported defect. The claim should be about the normal governed dispatch path without protocol parameters, rather than literally every conceivable call: supplying the appropriate manifest changes execution.

## 5. Medium findings: complete triage

| ID | Evidence | Evaluation and boundary |
|---|---|---|
| M1 | S/Q | Strategy sources do not read request.vehicles while certification handles heterogeneous capacities: [optimizer_api/verification/response_certifier.py:136-193](<../optimizer_api/verification/response_certifier.py:136>). Search may produce routes the supplied fleet cannot serve, then fail closed. This does not mean fleet is wholly ignored by the entire router. |
| M2 | S | Cross-direction fallback is present: [optimizer_api/models/schemas.py:350-357](<../optimizer_api/models/schemas.py:350>). Pickup can use dropoff_time. Fix the shared window builder, rather than each solver. |
| M3 | S/Q | Coordinate fallback uses Euclidean degrees: [optimizer_api/utils/matrix_repository.py:492-509](<../optimizer_api/utils/matrix_repository.py:492>). Those costs are not authoritative travel minutes or geographic kilometres. The exact 1/111 ratio is only an approximation and varies with latitude/axis. |
| M4 | S/Q | Failed refresh retains a matrix without a maximum usable age: [optimizer_api/utils/matrix_repository.py:165-191](<../optimizer_api/utils/matrix_repository.py:165>). Fetch pagination/count validation is absent. The live provider max_rows and actual matrix truncation were not checked; incomplete loaded matrices already fail closed. |
| M5 | S | Internal exception strings/paths enter benchmark responses: [optimizer_api/routers/benchmark.py:152-214](<../optimizer_api/routers/benchmark.py:152>) and [optimizer_api/routers/benchmark.py:653](<../optimizer_api/routers/benchmark.py:653>). Verified by the independent reviewer. |
| M6 | S/Q | IE tracks are fixed synthetic blocks, sandbox metrics are zero-filled, and demo results use predetermined ranges. Landing does have demo labels at [src/app/page.tsx:1156](<../src/app/page.tsx:1156>) and [src/app/page.tsx:1902](<../src/app/page.tsx:1902>). Unlabelled-everywhere is overstated; history/provenance and automatic switching still require correction. |
| M7 | S/Q | Date responses can overwrite newer state; exports use current selected date: [src/app/(app)/admin/drivers/page.tsx:31-57](<../src/app/(app)/admin/drivers/page.tsx:31>). Own-user browser RLS could hide assignment names, but the deployed select policies were not checked. |
| M8 | S/Q | Unescaped document.write interpolation is a real export sink: [src/services/excel/driver-export.ts:120-129](<../src/services/excel/driver-export.ts:120>) and [src/services/excel/driver-export.ts:248-285](<../src/services/excel/driver-export.ts:248>). Stored-XSS reachability depends on attacker-controlled data reaching the admin. CSP and persisted-session configuration increase impact; no exploit was run. |
| M9 | S/Q | Development-reset secret enforcement is optional and UI does not send it: [src/app/api/auth/dev-reset/route.ts:8-28](<../src/app/api/auth/dev-reset/route.ts:8>). Risk requires the endpoint to be enabled and reachable; production build behavior is already fail-closed. |
| M10 | S/Q | Password change permits a valid bearer token without step-up, and auth failures become 500: [src/app/api/profile/password/route.ts:20-57](<../src/app/api/profile/password/route.ts:20>). This is authenticated-session hardening plus an error-mapping bug, not an anonymous reset bypass. |
| M11 | S/Q | Tests and App Router use different React builds. Next supports React 18 and 19 and intentionally bundles App Router canary React. Low unless a concrete compatibility failure is demonstrated; a routine upgrade to React 19 alone does not guarantee bundled-canary parity. |
| M12 | S/Q | xlsx 0.18.5 parses uploaded files: [src/services/excel/import.ts:131-181](<../src/services/excel/import.ts:131>). Vendor advisories confirm affected versions. Crafted-file exploitation was not tested. Update the actual parser path and apply size/type limits; export-only use has a different threat profile. |
| M13 | S/Q | Async auth callback awaits a lookup without sequencing: [src/lib/supabase-auth.ts:230-257](<../src/lib/supabase-auth.ts:230>). Installed auth-js warns of lock-related async callback deadlocks. A stale callback can overwrite later state; multi-tab/deadlock reproduction was not run. Backend token checks still exist. |
| M14 | S/Q | Production hybrid local search has a separate three-opt case generator: [uniride_core/algorithms/local_search.py:168-206](<../uniride_core/algorithms/local_search.py:168>) and [uniride_core/algorithms/local_search.py:726-732](<../uniride_core/algorithms/local_search.py:726>). Contract drift is credible from source; this review did not enumerate candidate parity or prove the reported six-versus-seven count independently. |
| M15 | S/Q | Production exposure is a separate hard-coded registry, without a shared readiness gate: [optimizer_api/strategies/__init__.py:120-214](<../optimizer_api/strategies/__init__.py:120>). Do not filter production CVRP strategies through a permutation-TSP-only academic catalog without an approved compatibility plan. |
| M16 | S/Q | Core contains TSPLIB storage/downloading/BKS concerns: [uniride_core/algorithms/tsplib_parser.py:35-60](<../uniride_core/algorithms/tsplib_parser.py:35>) and [uniride_core/algorithms/tsplib_parser.py:323-330](<../uniride_core/algorithms/tsplib_parser.py:323>). The production adapter can mislabel explicit matrix units: [uniride_core/adapters/uniride_adapter.py:101-111](<../uniride_core/adapters/uniride_adapter.py:101>). Runtime unit enforcement needs work; not every core function performs I/O. |
| M17 | S/Q | Namespace importability/generic scan coverage needs review, but YAEM-specific tests already recognize archive imports: [academic_benchmark/tests/test_yaem_quarantine_boundary.py:39-49](<../academic_benchmark/tests/test_yaem_quarantine_boundary.py:39>). The generic test actually lives at uniride_core/tests/test_archive_boundaries.py, not the cited academic path. Do not claim all archive protection is ineffective. |
| M18 | R/S | GWO/HHO round tour_cost/objective_cost at [academic_benchmark/core/registry_setup.py:710-715](<../academic_benchmark/core/registry_setup.py:710>). On a fractional eight-node matrix both failed independent costing, while Core-TwoOpt-TSP passed at 24.008. This is a real fail-closed governed-run defect. |
| M19 | S/Q | Metadata flags come from polish_enabled rather than work actually performed: [academic_benchmark/core/registry_setup.py:767-779](<../academic_benchmark/core/registry_setup.py:767>). The zero-polish Bildiri profile is explicitly draft/smoke, [academic_benchmark/studies/bildiri2026/study.json:5](<../academic_benchmark/studies/bildiri2026/study.json:5>). Fix truthful configuration/work metadata; do not describe that draft fixture as a completed scientific study. |
| M20 | S/Q/U | Repeated objective calls still consume the contractual call budget. They are not an accounting violation. The audit's repeat percentages were not remeasured. Distinct-candidate telemetry is useful; caching that avoids counted calls changes the comparison protocol and requires approval/parity. |
| M21 | S/Q | The RLS script drops all public policies and definer functions lack a fixed search_path: [supabase/rls_policies.sql:17-36](<../supabase/rls_policies.sql:17>). Ordering can remove migration-owned policies and deny access. Live search-path exploitability/policy state was not checked; prefer a migration-owned policy set. |
| M22 | S/Q | main imports routers before load_dotenv: [optimizer_api/main.py:18-29](<../optimizer_api/main.py:18>). Import-time settings can be frozen too early. Test environment isolation matters; no credential values were inspected. The full range of older python-dotenv behavior was not tested here. |
| M23 | S/Q | Utility endpoint passes a model to a helper using entry.get: [optimizer_api/routers/utils.py:26](<../optimizer_api/routers/utils.py:26>) and [uniride_core/algorithms/time_window_extractor.py:119](<../uniride_core/algorithms/time_window_extractor.py:119>). TSPLIB downloader uses HTTP/unbounded read at [uniride_core/algorithms/tsplib_parser.py:323-330](<../uniride_core/algorithms/tsplib_parser.py:323>). Utility/input failure mechanisms are source-verified; no network download or full endpoint reproduction was run. |
| M24 | S/Q/U | Repeated analytics computation and top-level polling are visible in the reviewed UI. CPU/render hotspots and chart reanimation need profiling; line counts alone do not justify virtualization or more abstractions. |
| M25 | S/Q/U | Canonical three-opt generates/deduplicates candidate variants: [uniride_core/algorithms/three_opt.py:78-101](<../uniride_core/algorithms/three_opt.py:78>) and [uniride_core/algorithms/three_opt.py:151-171](<../uniride_core/algorithms/three_opt.py:151>). Reported 23.6/53-second timings were not rerun. Candidate-order/parity evidence must precede any optimized generator replacement. |
| M26 | S | SOTA adapter builds a student-only distance matrix and silently falls back to greedy: [uniride_core/adapters/sota_tsp_strategy_adapter.py:12-22](<../uniride_core/adapters/sota_tsp_strategy_adapter.py:12>) and [uniride_core/adapters/sota_tsp_strategy_adapter.py:61-67](<../uniride_core/adapters/sota_tsp_strategy_adapter.py:61>). It does not optimize the depot-anchored duration objective being reported. This deserves higher operational priority than its Medium label suggests. |

### Primary-source checks for dependency and framework claims

For M12, SheetJS states that CVE-2023-30533 affects reads through 0.19.2 and was fixed in 0.19.3; export-only workflows are not affected by that advisory. CVE-2024-22363 affects versions through 0.20.1 and was fixed in 0.20.2. The vendor rates those advisories Medium and High respectively. See [SheetJS prototype-pollution advisory](https://cdn.sheetjs.com/advisories/CVE-2023-30533) and [SheetJS ReDoS advisory](https://cdn.sheetjs.com/advisories/CVE-2024-22363). This does not refresh the repository's old aggregate npm-audit count.

For M11, the installed Next peer declaration supports both React 18 and 19. Next documents bundled canary React for App Router. See [Next.js installation documentation](https://nextjs.org/docs/app/getting-started/installation). Version differences justify targeted production-runtime checks, not a claim that React 18 usage necessarily makes the application broken.

For M13, the installed auth-js source documents async callback lock hazards, and the official API advises a safe synchronous callback. See [Supabase auth state-change reference](https://supabase.com/docs/reference/javascript/auth-onauthstatechange). This confirms the mechanism, not a reproduced deadlock in UniRide.

## 6. Low findings and deletion advice

| ID | Evidence | Evaluation |
|---|---|---|
| L1 | S | React Query is a direct dependency with no src useQuery/QueryClientProvider usage. Removal is simpler unless a real polling migration uses it. |
| L2 | S | Landing calls a missing /api/ai-advisor route: [src/app/page.tsx:555](<../src/app/page.tsx:555>). Remove the affordance or implement an explicitly scoped feature later; the audit is not authorization to build it now. |
| L3 | S/Q | Duplicate frontend page and legacy BFF callers are dead candidates. Backend compatibility shims/public exports need consumer checks. The core use_sota_engine flag is used by [uniride_core/algorithms/cvrptw_decoder.py:25-62](<../uniride_core/algorithms/cvrptw_decoder.py:25>); only the request-model field appears unused. Do not delete the whole clustering module, whose types/helpers remain live. |
| L4 | S | Missing server-only imports in admin client/auth modules are defense in depth. Actual browser bundling of a service secret was not demonstrated. |
| L5 | S | Raw unexpected errors and auth-to-500 mappings exist in reviewed BFFs: [src/lib/admin-auth.ts:154-167](<../src/lib/admin-auth.ts:154>) and [src/app/api/driver/assignments/route.ts:12-54](<../src/app/api/driver/assignments/route.ts:12>). |
| L6 | S/Q | x-user-id header has no discovered reader: [src/proxy.ts:38-41](<../src/proxy.ts:38>). Remove unused work, but do not replace independent authentication with an untrusted incoming header. |
| L7 | S | Admin layout navigates during render: [src/app/(app)/admin/layout.tsx:34-40](<../src/app/(app)/admin/layout.tsx:34>). Move the side effect to the existing lifecycle boundary. |
| L8 | S/Q | Executor termination metadata is synthesized instead of consistently using the search result: [academic_benchmark/core/registry_setup.py:221-226](<../academic_benchmark/core/registry_setup.py:221>). Source-verified; the exact no_improving_move demo was not rerun. |
| L9 | S/Q/U | Legacy global reseeding exists in registry/CLI; canonical/tolerance and dispersion subclaims need their own contract checks. Some initial-evaluation accounting differs between standalone and governed paths. Do not label the whole fair counter incorrect from that alone. |
| L10 | S/Q/U | Hash-salted synthetic coordinate factors exist in [optimizer_api/utils/matrix_repository.py:535-538](<../optimizer_api/utils/matrix_repository.py:535>). Dormant unseeded/default and numerical-tolerance paths were not all exercised. Keep latent issues separate from seeded governed execution. |
| L11 | S/Q | Adapter uses str(direction): [uniride_core/adapters/uniride_adapter.py:134](<../uniride_core/adapters/uniride_adapter.py:134>). Enum-string behavior is a real latent risk; this review did not establish a live production caller using that adapter. |
| L12 | S/Q/U | Capacity comparison checks only the shared dimensional length: [uniride_core/algorithms/feasibility_certificate.py:143](<../uniride_core/algorithms/feasibility_certificate.py:143>); window checker can skip a missing window node's travel at [uniride_core/algorithms/feasibility_certificate.py:239-241](<../uniride_core/algorithms/feasibility_certificate.py:239>). Sweep/default-capacity and dimensional-collapse subclaims were not all independently traced end to end. |
| L13 | S/Q/U | Shared packaging, production/academic imports and sys.path mutation are architecture hygiene issues. They are not all defects solely because a filename mentions a study or a root script exists. Root-script/generated-artifact reachability was not exhaustively classified. |
| L14 | S/Q | The documented local launcher starts main.py with reload behavior: [optimizer_api/main.py:117](<../optimizer_api/main.py:117>). That is a development path; it does not prove a deployed service is running with reload. A production entrypoint should be explicit. |
| L15 | S/Q | Driver date/user requests lack stale-response protection in the reviewed pages. The audit's classification of all 19 lint warnings was not independently recounted. Fresh lint totals are reported separately below. |

### Ponytail audit: ranked simplifications

These are deletion/simplification candidates, not changes applied in this task.

| Rank | Location | What to cut or simplify | Replacement / limit |
|---|---|---|---|
| 1 | vehicle-planning-page.tsx | Unimported duplicate page, approximately 388 substantive file lines. | Keep the active App Router page. |
| 2 | package.json | Unused @tanstack/react-query direct dependency. | Existing fetch/polling code; add a library only for a concrete adopted requirement. |
| 3 | uniride_core/algorithms/sota_common/penalty_manager.py | Approximately 224 substantive lines with no live solver caller found. | Delete only after resolving public re-exports/manual compatibility consumers. |
| 4 | [uniride_core/algorithms/clustering.py:40-133](<../uniride_core/algorithms/clustering.py:40>) | Duplicate k-means implementation. | Reuse clustering_strategies after preserving Point, Cluster, calculate_centroid, and capacity helpers. |
| 5 | Old benchmark run/status and run/stop BFFs; unused sandbox scenario persistence | Redundant endpoint surfaces and double-encoded JSONB path. | Retain the actually used endpoint/owner contract; verify external consumers before removal. |
| 6 | Legacy 3-opt variants and matrix reconstruction/cache plumbing | Parallel implementations and unsafe cache ownership. | Canonical operator and explicitly passed matrix, with parity/accounting gates. |

**Bounded estimated net:** the duplicate page plus conditional PenaltyManager removal represent roughly **600 lines**, and unused React Query represents **one direct dependency**. This is an estimate before compatibility edits, not measured savings from a patch. There were no deletions.

Do not delete the entire sota_common tree merely because current solvers do not call it: re-exports, compatibility tests and manual entry points exist. Do not add table virtualization, a queue framework, or another registry abstraction solely because the audit suggests one. Fix admission, authority and truthful results first; profile before performance architecture.

## 7. Corrections needed before adopting the audit's plan

1. **Deployment policy versus repository policy.** C1 and C1.b require a read-only deployed-policy/provisioning check before claiming live exploitation. Until then, the unsafe repository policy is still a release blocker.

2. **Certificate independence.** Calling a checker from another module establishes structural separation. Rebuilding costs from solver-reported arcs establishes internal consistency, not authoritative source-cost validation. Update broad closure wording accordingly.

3. **Legacy cache scope.** C3 is reproduced and serious. Fair/native manifest branches bypass the demonstrated cache path. Quarantine/rerun decisions must identify which path generated each result, rather than discard every result by association.

4. **Full CI scope.** ci.yml is limited to eight executed integration files, but benchmark.yml adds tests on relevant PRs/main/master changes. Neither discovery alone nor those combined subsets establish full canonical execution. Add actual execution/build evidence where required; do not describe the repository as literally running only eight files.

5. **Archive protection already exists.** The generic archive test path in M17 is wrong. YAEM-specific tests explicitly match archive.academic_benchmark.yaem2026_legacy. Their 85-test boundary/manifest group passed here. Namespace importability and dynamic/root scan scope can still require stronger enforcement; that is different from claiming there is no working quarantine.

6. **Gate A versus later requirements.** [ACADEMIC_STUDY_UNIFICATION_DESIGN.md:422-429](<../ACADEMIC_STUDY_UNIFICATION_DESIGN.md:422>) puts archive, schema, non-importability/checksum and academic-test checks in Gate A. Reproducibility emission and analysis are Package D work at [ACADEMIC_STUDY_UNIFICATION_DESIGN.md:451-460](<../ACADEMIC_STUDY_UNIFICATION_DESIGN.md:451>). The audit's Section 8.6 incorrectly bundles generic run-manifest emission and broad production/academic isolation into Gate A. Do not rewrite work-package acceptance retroactively without an approved plan.

7. **Manifests exist, but are not uniformly integrated.** [academic_benchmark/fair_pilot.py:583](<../academic_benchmark/fair_pilot.py:583>) and [academic_benchmark/native_pilot.py:596](<../academic_benchmark/native_pilot.py:596>) write manifest.json. RunManifestV1 exists at [academic_benchmark/contracts/run.py:65](<../academic_benchmark/contracts/run.py:65>) and is exercised by schema tests. The gap is uniform schema/governance integration across producers, storage and readers. Pilot manifest emission already exists.

8. **React split is expected framework behavior.** Treat concrete hydration/runtime incompatibility as a defect; do not infer it solely from React 18 package declarations plus bundled canary React. An upgrade alone does not create exact test/production parity.

9. **Counting repeat calls is contract-compliant.** The approved primary budget counts objective evaluations, not unique permutations. Memoization can alter algorithm identity, termination and comparison fairness. Record repeats if useful; do not silently change the budget meaning.

10. **Draft profile versus completed study.** The zero-polish Bildiri profile is explicitly draft and smoke-only. Truthful memetic metadata still matters. Published-result contamination or a completed false ablation has not been established.

11. **Production registry compatibility.** The approved unification contract preserves current API inventory while moving ownership. A permutation-TSP capability table cannot simply replace a heterogeneous CVRP/CVRPTW production registry. Readiness/identity enforcement needs explicit domain-aware migration and exposure parity.

12. **Dead-code claims need symbol-level precision.** The request field use_sota_engine is unused, while a core decoder option with that name is live. Point/Cluster/helpers in clustering.py are live even if its duplicate k-means is not. Public shims and tests are consumers that must be deliberately redirected or retired.

13. **Demo labels and authentication hardening.** Landing has demo markers. M10 requires an already valid bearer token. M8 has a confirmed injection sink but conditional attacker-to-admin reachability. Correct these scopes without dismissing their real risks.

14. **Schedule of work.** Contain confirmed authority/compute/certificate defects before live operational acceptance. Pure deterministic Package 2 fixture work can proceed independently if it uses no live student data and makes no acceptance claim. The audit's one-to-two-week estimates and instruction to postpone every next task are opinions, not measured commitments.

## 8. What prior green checks actually establish

Fresh checks in this review passed despite reproduced defects:

| Check | Fresh result |
|---|---|
| Five quarantine/schema/core-boundary Python files | 85 passed in 30.31 s, exit 0 |
| Eight gateway/fair/native/3-opt/registry/dashboard/clustering Python files | 122 passed in 14.33 s, exit 0 |
| Eight matrix/certifier/feasibility/snapshot/compare/benchmark-owner Python files | 180 passed in 13.61 s, exit 0 |
| Six security/frontend Vitest files, completed independent reviewer | 13 tests passed, six files passed, exit 0 |
| npm.cmd run typecheck | exit 0 |
| npm.cmd run lint | 0 errors, 163 warnings, exit 0 |
| Audit Appendix H.1 legacy cache script | Four corrupted runs out of six, exit 0 |
| Bounded zero-matrix/admission/timing/loader/gateway checks | Defects reproduced as described; Python process exited 0 |

There are **387 passing Python tests across the three selected command groups**, not a new full-canonical-suite run. The frontend group is not a rerun of all 315 tests. The zero exit codes of reproduction scripts mean the scripts completed, not that their printed behavior was correct.

The tests provide useful positive evidence for boundary structure, fair/native metadata, gateway validation, snapshot checks and the existing certificate attachment mechanisms. They miss some cross-boundary assumptions:

- Gateway unit tests can use contract-valid fake executors; they do not by themselves prove normal CLI/Smart dispatch injects a real protocol manifest.
- Integer-valued fair fixtures do not expose rounding at fractional cost.
- Vehicle-planning fixtures use camelCase and So-only users while the real API returns snake_case.
- A certificate can reject mutated payloads but still accept an invalid source-cost matrix if both solver output and reconstructed input agree.
- A status transition test can pass while the worker continues and releases logical admission too early.
- API-key tests do not establish user authorization on every public BFF that attaches that key.
- Static archive tests can work for known imports while missing other import mechanisms.

[CURRENT_ARCHITECTURE.md:39](<../CURRENT_ARCHITECTURE.md:39>) broadly says production compute is protected end to end, which the anonymous benchmark BFF contradicts. [CURRENT_ARCHITECTURE.md:58](<../CURRENT_ARCHITECTURE.md:58>) says academic execution remains separate from production lifecycles, contradicted by mounting the benchmark router and importing promoted academic configuration. [UniRide_Ultimate_Audit.md:48](<../UniRide_Ultimate_Audit.md:48>) describes independent duration/window/matrix checks more strongly than current authoritative-cost enforcement supports.

At the same time, [ACTIVE_ROADMAP.md:11](<../ACTIVE_ROADMAP.md:11>) explicitly states the project is experimental, and [ACTIVE_ROADMAP.md:133](<../ACTIVE_ROADMAP.md:133>) records hard cancellation as open. [CURRENT_ARCHITECTURE.md:46](<../CURRENT_ARCHITECTURE.md:46>) also explains soft deadlines. Those caveats are real and should be retained. The necessary correction is to narrow overstated guarantees and add missing acceptance evidence, not erase all demonstrated progress.

## 9. Recommended next work, within the approved gates

This is prioritization advice, not an implementation started in this review.

| Order | Bounded outcome | Related findings | Required closing evidence |
|---|---|---|---|
| 1 | Enforce user role and ride state transitions at the authoritative policy boundary. | C1, C1.b, M21 | Read-only live policy/trigger inventory; attacker-style own-profile insert/state tests; migration parity. |
| 2 | Require appropriate user/admin authorization on benchmark start; retain admitted capacity until actual exit; remove unsafe inferential claims. | C4, C5, H1, H14 | Anonymous-start denial; finite worker stop/admission regression; no unsupported claim emission. |
| 3 | Remove legacy cache identity aliasing and unify DataLoader import ownership. | C3, H5 | Original six-run script agrees with clean-cache controls; single loader identity under supported launch modes. |
| 4 | Reject missing/non-authoritative travel time and independently re-cost/simulate routes on the bound source snapshot. | C2, H2, H3, H4, H16, M1-M4 | Missing-matrix rejection; full depot return/waiting/service/fleet checks; response schedule equals validated schedule; source-arc tampering rejection. |
| 5 | Make academic gateway dispatch produce governed envelopes, keep fractional costs, and preserve distinct protocols/identities. | H8, H9, H13, M18, M19 | Real CLI/Smart integration; fractional TSP/ATSP; paired seeds; per-run provenance; readers reject unsupported evidence. |
| 6 | Close algorithm-contract divergence and residual randomness with targeted parity. | H10-H12, M14, M20, M25, M26 | Directed/symmetric candidate parity; truthful accounting/backend metadata; seeded concurrent checks; aligned reported/optimized objective. |
| 7 | Fix operational UI mappings/races and vulnerable upload path; broaden CI to the required gates. | H15, H20, M7-M13 | Snake-case Sw fixture; out-of-order/terminal polling; upload parser/advisory verification; actual canonical execution and production build. |

The sequence must preserve the evidence gates for Packages A, B, C and D, in that order. A narrow security or source-cost guard does not require a large architecture rewrite. Moving academic runtime surfaces, changing registries, revising budget semantics, or replacing solver implementations does require its own approved contract-aware plan and parity/exposure evidence.

The audit suggests a shared simulator. That is justified where four timing interpretations are already diverging, but introduce the smallest common function that actually owns the existing contract. Do not add a speculative generic scheduling framework. Likewise, a worker-held process-local admission guard is a useful immediate containment; it does not close multi-worker distributed admission or hard-cancellation requirements.

## 10. Exact fresh test commands

All Python commands ran from the repository root with the existing .venv-jit environment. No dependencies were installed. For the test groups:

~~~powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:SUPABASE_URL = ''
$env:SUPABASE_SERVICE_ROLE_KEY = ''

.\.venv-jit\Scripts\python.exe -B -m pytest academic_benchmark/tests/test_yaem_quarantine_boundary.py academic_benchmark/tests/test_bildiri_quarantine_boundary.py academic_benchmark/tests/test_manifest_contracts.py uniride_core/tests/test_architecture_boundaries.py uniride_core/tests/test_archive_boundaries.py -q -p no:cacheprovider --tb=short

.\.venv-jit\Scripts\python.exe -B -m pytest academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_fair_comparison_protocol.py academic_benchmark/tests/test_fair_protocol_v2_metadata.py academic_benchmark/tests/test_native_termination_protocol.py academic_benchmark/tests/test_canonical_three_opt_integration.py academic_benchmark/tests/test_production_registry_snapshot.py academic_benchmark/tests/test_dashboard_utils.py uniride_core/tests/test_clustering_core.py -q -p no:cacheprovider --tb=short

.\.venv-jit\Scripts\python.exe -B -m pytest optimizer_api/tests/test_matrix_repository.py optimizer_api/tests/test_response_certifier.py optimizer_api/tests/test_production_feasibility_boundary.py optimizer_api/tests/test_optimization_matrix_binding.py optimizer_api/tests/test_dudullu_matrix_readiness.py optimizer_api/tests/test_package_b_compare_orchestration.py optimizer_api/tests/test_benchmark_run_request_schema.py optimizer_api/tests/test_p3_owner_tokens.py -q -p no:cacheprovider --tb=short

npm.cmd run typecheck
npm.cmd run lint

npx.cmd vitest run src/app/api/benchmark/run/route.test.ts src/app/api/benchmark/run/stop/route.test.ts src/app/api/benchmark/stop/route.test.ts 'src/app/(app)/admin/vehicle-planning/page.test.tsx' src/lib/supabase-auth.test.ts src/proxy.test.ts
~~~

The last command was run by the completed independent reviewer. Its vehicle-planning fixture also emitted an existing DOM-nesting warning. A green test without a snake_case Sw case does not disprove H15.

Source/snapshot checks included:

~~~text
git rev-parse HEAD
git log -3
git diff --stat 316cbab HEAD
git status --short
codegraph index
codegraph init
codegraph node <inspected file>
codegraph explore <bounded question>
rg -n <targeted pattern> <reviewed modules>
~~~

The angle-bracket lines summarize multiple source queries, not literal executed commands or test claims. Indexing did not succeed; no claim depends on a successful refresh.

Runtime reproductions were invoked with .\.venv-jit\Scripts\python.exe -B -c and inline Python. C3 used the exact Python body under the original audit Appendix H.1. The other scripts blanked Supabase/dotenv first and used small in-memory inputs; the worker script used finite fake threads and joined all of them. No live benchmark, SQL, production route, or database write was used. The following retained snippet reproduces the academic fractional-cost check with the successful policy:

~~~python
import os
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""

from academic_benchmark.core import registry_setup  # registers real executors
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.preflight import RuntimeBackendAvailability
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol
from uniride_core.models import ProblemInstance

problem = ProblemInstance(
    name="review-fractional-8", dimension=8, coordinates=[], problem_type="tsp",
    dist_matrix=[
        [0.0 if i == j else abs(i - j) + 1.001 for j in range(8)]
        for i in range(8)
    ],
)
params = {
    "max_iterations": 2, "pack_size": 6, "hawks": 6,
    "polish_iters": 1, "final_polish_iters": 1, "dive_count": 2,
}
for algorithm in ("Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure", "Core-TwoOpt-TSP"):
    try:
        result, _ = execute_preflighted(
            requested_algorithm_id=algorithm, identifier_source=IdentifierSource.CLI,
            problem=problem,
            params=dict(params, fair_comparison={"evaluation_budget": 100, "base_seed": 77}),
            seed=41, run_idx=0, protocol=ExecutionProtocol.FIXED_BUDGET,
            backend_policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE, evaluation_budget=100,
            registered_algorithm_ids=frozenset(AlgorithmRegistry.list_algorithms()),
            runtime_backends=RuntimeBackendAvailability(True, True, "existing Numba installation"),
            registry_getter=AlgorithmRegistry.get_executor,
        )
        print(algorithm, "accepted cost", result.tour_cost)
    except Exception as exc:
        print(algorithm, type(exc).__name__, str(exc))
~~~

Observed:

~~~text
Core-GWO-TSP-Pure ResultContractViolation reported tour_cost does not equal the independently recomputed directed closed-cycle cost
Core-HHO-TSP-Pure ResultContractViolation reported tour_cost does not equal the independently recomputed directed closed-cycle cost
Core-TwoOpt-TSP accepted cost 24.008
~~~

Removing fair_comparison from params in that dispatch produced the H13 identity-contract failures for Core-TwoOpt-TSP, ALNS-TSP and Core-GWO-TSP-Pure. The supported backend/capability policy must be recorded when turning this into a regression test; preflight rejection under an unsupported policy is a different failure.

## 11. Inspected material and remaining checks

The review read the full original audit, relevant unification/fairness/3-opt specifications, master architecture/roadmap material, and current implementation paths. Core source inspection covered certification/scheduling, local-search cache and cost function, SOTA adapter/local-search layers, clustering, matrix factory/adapters and TSPLIB handling. Academic inspection covered gateway and registry executors, CLI/Smart dispatch, fair/native producers, dashboard normalization/statistics, study configuration, storage contracts and archive tests. Operational inspection covered optimization/readiness/matrix repository, benchmark state/admission, promoted configuration, and utility endpoints. The completed independent lane inspected RLS/auth, benchmark BFF/owner/polling, vehicle planning, driver/export, auth lifecycle/reset and dependency declarations.

The exact changed-file set is this report only. INSTRUCTION_REVIEW_2026-09-07.md was already untracked. Original findings/tracker, application source, dependencies, secrets and generated result stores were not edited.

Checks still required before a release or evidence acceptance decision:

- Read-only live RLS/function/trigger and user-provisioning inventory for C1/C1.b/M21.
- Actual internet/LAN exposure and trusted forwarded-header behavior for C4/H1/M9.
- Read-only provenance inventory of the academic result database on an authorized copy; determine which legacy paths generated which rows.
- Supported-launch-mode and deployed TTL tests for H5, and concurrent slow-provider latency/capacity tests for H6/H7.
- Full authoritative route timing/fleet/used-arc checks, with explicit school-arrival and duration semantics.
- Optional solver and genuine CVRPTW parity; the Solomon example and OR-Tools rounding case were not rerun here.
- Fresh full canonical suites, production build, and dependency advisory triage after any fixes; current selective passes are not a release certificate.
- Targeted algorithm candidate/parity/performance checks; original repeat-rate and 3-opt timing numbers were not remeasured.

## 12. Optional external consistency handoff

The repository's preferred broad consistency specialist is **Qwen 3.7 Max**, which is not callable in this environment. No Qwen, OpenCode HY3, Muse, Mimo, or Claude invocation was performed by this review. A final comparison of the two reports against the approved gates would be useful before adopting a cross-system remediation plan. That extra review is non-blocking for the reproduced defects and was not requested as another running chat. The self-contained handoff below stays within read-only review/report authority.

### External Agent Handoff - Qwen 3.7 Max

~~~text
Role and target model:
Qwen 3.7 Max, independent final repository/document consistency auditor.

Objective:
Verify the dispositions and work-package corrections in the Codex companion review against current UniRide code. Return only supported corrections, contradictions and remaining uncertainty. Do not implement fixes or certify deployment/publication readiness.

Repository and working directory:
<repository root of the UniRide checkout>

Verified context:
Codex inspected commit a54b7864af263a639d3e251d803647c0389c43b0.
Compared with audit baseline 316cbab, only AGENTS.md, UniRide_Ultimate_Audit.md and the original audit document changed; application source did not.
Initial dirty state was only untracked INSTRUCTION_REVIEW_2026-09-07.md; the companion review is a newly generated report.
Codex reproduced legacy cache corruption in four of six Appendix H.1 runs, zero-cost ga_split certification, status-only stop freeing capacity while a finite fake worker lived, omitted pickup depot return, conflicting arrival times, dual loader identity, missing governed-dispatch result metadata and fractional GWO/HHO rounding rejection.
Fresh selected Python groups passed 85, 122 and 180 tests. One completed GPT-5.6 Sol reviewer passed six frontend files/13 tests. Typecheck passed; lint had 0 errors/163 warnings.
These are scoped results, not a new full-suite, build, live-RLS, live-database or deployed exposure check.
CodeGraph indexing failed EPERM/in-use; current source reads worked. Do not assume fresh graph relationships.
Two other review agents failed usage limits; their conclusions were not used.

Scope:
docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md
docs/ULTIMATE_AUDIT_2026-10-01_CODEX_VERIFICATION.md
ACADEMIC_STUDY_UNIFICATION_DESIGN.md
ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md
CANONICAL_THREE_OPT_DESIGN.md
CURRENT_ARCHITECTURE.md
ACTIVE_ROADMAP.md
Relevant callers/tests under src, optimizer_api, uniride_core, academic_benchmark and supabase.
Focus on C1-C5 scope, H13/M18 fail-closed behavior, H20 CI wording, M17 archive tests, manifest emission, Gate A/B/C/D assignments, repeated-evaluation accounting, and production-registry compatibility.

Exclusions:
Do not alter application code, dependency files, original audit/tracker, unrelated dirty files, secrets, credentials, .env files, databases, generated/ignored result stores, worktrees or git history.
Do not run live Supabase queries, production benchmarks, destructive load, network downloads, DDL/DML, publishing or deployment.
Archived results are historical data, not current scientific evidence. Do not execute archived solver engines.

Authorization:
read-only review; artifact generation authorized only for a separate audit response/report. No remediation edits.

Required workflow:
Read applicable AGENTS.md and the relevant approved specs.
If .codegraph exists, try codegraph index before locating code and wait for completion. If locked, document the failure; do not delete it or stop unrelated processes. Use codegraph node/explore plus direct current-source confirmation, and disclose stale graph relationships.
For each finding provide exact existing file/line evidence and caller reachability.
Separate reproduced behavior, source-confirmed mechanisms, deployment-conditional claims, and unverified measurements.
Local evidence outranks confidence/severity labels. Keep fixed-budget and native evidence separate.
Preserve all unrelated changes.

Verification:
Use the existing .venv-jit\Scripts\python.exe -B with PYTHON_DOTENV_DISABLED=1, SUPABASE_URL="" and SUPABASE_SERVICE_ROLE_KEY="".
Start with the exact focused commands in section 10 of the companion report, rerunning only checks needed for a disputed conclusion.
For targeted academic disputes run:
.\.venv-jit\Scripts\python.exe -B -m pytest academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_fair_comparison_protocol.py academic_benchmark/tests/test_native_termination_protocol.py academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_yaem_quarantine_boundary.py uniride_core/tests/test_archive_boundaries.py -q -p no:cacheprovider --tb=short
Record exact commands, counts, exit codes, failures and environment blockers. Do not use "all tests pass" without scope.

Return package:
1. Outcome summary.
2. Confirmed findings/corrections with exact file and line references.
3. Uncertain findings and assumptions separately.
4. Exact inspected files and changed files.
5. Commands/tests, counts, exits, failures and environment blockers.
6. Concise suggested report patch if necessary; no application patch.
7. Remaining risks, unresolved questions and recommended next action.
8. Explicit statement that unrelated changes were not modified.

Return the complete response, including commands, results, caveats and any proposed report patch, for local verification by Codex.
~~~

## 13. Closing disposition

The audit materially changes the risk assessment for affected release and reporting paths. Its serious findings cannot be dismissed because many tests pass. Equally, its conditional risks, measured benchmarks, broad architecture claims and proposed deletions must not be accepted solely because the report sounds authoritative.

Keep the original tracker open until specific fixes have their closing evidence. Use the reproduced defects to prioritize small authoritative repairs, preserve verified component work, and advance each approved work package with its own evidence.
