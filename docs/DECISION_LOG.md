# Decision library

Recorded 2026-10-07 against WIP `6f09e5a`. This is a retrieval guide to decisions and their evidence, not a new acceptance test or a declaration of production readiness. Dates below are decision/source dates; merge dates may differ.

Evidence labels: **owner decision** = approved scope in the owner/lead handoff or roadmap; **documented contract** = an approved specification; **source checked** = current source inspected during this documentation task; **reported measurement/test** = a historical source's result, not rerun here; **proposal** = not accepted or implemented by this log. Git existence, dates and ancestry of the principal seed merges were checked locally. No live database or application test was run for this document. Where options or dead ends are absent from the source, “none recorded” means exactly that.

| ID | Theme | Decision | Status |
|---|---|---|---|
| D01 | Demo scope | Hypothetical admission without writes (K1) | Owner decision |
| D02 | Demo scope | Identical virtual template (K2) | Owner mode; developer template policy |
| D03 | Demo scope | Planner chooses date (K3) | Owner decision |
| D04 | Demo scope | Read-only local preview; publication deferred | Owner decision |
| D05 | Demo scope | Reuse `ga_split`; distinguish configured/effective seed | Owner rationale; source correction |
| T01 | Travel-time data | Stored directed matrix only for operations | Accepted; C2 remediation |
| T02 | Travel-time data | Injectable repository, clock and facade | Documented contract |
| T03 | Travel-time data | Retry and preserve last-known-good | Accepted; retry policy superseded |
| T04 | Travel-time data | Pagination/provenance; freshness remains open | Partial MT2 |
| T05 | Travel-time data | Matrix clustering vs geometric grouping | Accepted distinction |
| T06 | Travel-time data | Correct TSPLIB GEO assertion, preserve metric | Historical decision |
| O01 | Optimizer/certificate | Independent matrix re-costing before solve | Accepted; C2 remediation |
| O02 | Optimizer/certificate | Conservative operational OR-Tools rounding | Accepted; academic parity retained |
| O03 | Optimizer/certificate | Separate student ride and vehicle tour limits (K5) | Owner decision |
| O04 | Optimizer/certificate | Remove direct-arc infeasibility precheck | Reversal landed |
| O05 | Optimizer/certificate | Feasibility-first lexicographic ranking | Documented contract |
| O06 | Optimizer/certificate | Strict missing arcs; explicit time-window modes | Documented contract; residual N1 |
| O07 | Optimizer/certificate | Typed success certificates | Documented contract |
| O08 | Optimizer/certificate | Legacy benchmark corrections break comparability | Accepted correction |
| V01 | Vehicle assignment | Bounded search with lower bound/symmetry | Accepted; conditional proof |
| V02 | Vehicle assignment | Physical assignment evidence establishes adequacy | Reversal landed |
| U01 | UI wording/claims | Location codes with placeholder names (K4) | Owner decision |
| U02 | UI wording/claims | Explain capacity floor; possible causes only | Accepted review correction |
| U03 | UI wording/claims | Aggregate readiness view, stable direction | Documented contracts |
| P01 | Process | Isolated workers, independent review, no-ff integration | Owner process |
| P02 | Process | Existing CLIs for isolated demo; disable reload | Reversed launcher proposal |
| P03 | Process | Preserve dirty checkout; reconstruct selected work | Historical process |
| P04 | Process | Evidence before current-status claims | Continuing rule |
| A01 | Academic boundaries | Quarantine, extract, catalog, publish in gates | Approved contract |
| A02 | Academic boundaries | Claim-specific capabilities and governed gateway | Documented contract |
| A03 | Academic boundaries | Or-opt/ALNS evidence before promotion | Documented contract |
| A04 | Academic boundaries | Fixed evaluation primary; native separate | Approved contract |
| S01 | Service boundaries | Authenticated bounded compute; fresh strategies | Documented contract |
| S02 | Service boundaries | Per-run ownership tokens | Documented design; present security not inferred |
| S03 | Service boundaries | Narrow remediation and explicit waivers | Historical bounded scope |
| S04 | Service boundaries | Role and ride status locked in RLS; student-only self-registration | Lead decision 2026-10-09 |
| S05 | Service boundaries | route_plans readable only by authenticated drivers/admins; legacy rls_policies.sql retired | Lead decision 2026-10-09 |
| S06 | Service boundaries | H1 password-hint endpoint deliberately deferred until go-live | Owner decision 2026-10-09 |
| W01 | Daily workflow | Separate legs, exact anchors, confirmed admission | Approved production contract |
| W02 | Daily workflow | Preview orchestration before publication/operations | Approved staged design |
| X01 | Data errors | Vehicle capacity sources disagreed (DB 4/10 vs physical/decoder 4/5); DB corrected | Owner decision; data error |
| H01 | Heterogeneous fleet | Typed split, exact day selection, typed assignment; additive only; academic code untouched | Owner approved 2026-10-08 |
| H02 | Heterogeneous fleet | Q1: can a sedan carry any Sw (`sedan:1sw3so`)? | **Open question** |
| H03 | Heterogeneous fleet | Optional shared seat limit `total_capacity`; Doblo = 3 seats total, max 1 Sw | Owner decision 2026-10-09 |

## Demo scope

### D01 — K1: hypothetical admission without database writes

- **Date/status:** 2026-10-04; owner decision. **Chosen/rationale:** `assume_confirmed` permits a schedule-based demonstration despite missing/late decisions; the assumption remains visible, hypothetical and non-publishable. Recorded cancellation and legacy blockers follow the roadmap's explicit rules.
- **Rejected/why:** writing confirmations to the database merely to unlock the demo; it would fabricate consent and require live mutation. **Dead ends:** using newly inserted confirmations for past dates would cross the previous-day cutoff. **Reversal:** a narrow owner-approved preview exception to production's no-inferred-consent rule, not its replacement.
- **Evidence:** [demo roadmap §D1c/§4](DEMO_ROADMAP_2026-10-04.md), merges `d05e7fd`/`23ec2b5` (2026-10-04, Git history). **Check first:** admission mode and `publishable` before treating a preview as an operational plan.

### D02 — K2: one identical virtual fleet template

- **Date/status:** 2026-10-04; owner approved virtual as the demo UI default. **Chosen/rationale:** decouple route requirements from available live vehicles. Developer template policy selects the single live signature, otherwise the most common `(Sw, So, cooldown)` signature (capacity tie-break), otherwise `4 Sw / 10 So / 10 min`; create enough identical copies for admitted legs. The API default remains recorded/live.
- **Rejected/why:** live-fleet-only demo blocks exploration when that fleet cannot accommodate routes. **Dead ends:** earlier all-live-types virtual proposal enlarged heterogeneous assignment search. **Superseded:** roadmap's “each type” draft; template selection is developer policy, not a separate owner capacity decision.
- **Evidence:** [roadmap §D1c/§4](DEMO_ROADMAP_2026-10-04.md), `d05e7fd`/`23ec2b5`. **Check first:** actual selected template and returned `fleetMode`; virtual count cannot establish real-fleet sufficiency (V02).

### D03 — K3: the planner selects the service date

- **Date/status:** 2026-10-04; owner decision. **Chosen/rationale:** expose a day selector so the demonstration follows the chosen weekday's demand. **Rejected:** none recorded. **Dead ends:** none recorded. **Reversal:** none recorded.
- **Evidence:** [roadmap owner decisions and D2](DEMO_ROADMAP_2026-10-04.md), `ab92691` (2026-10-04). **Check first:** `serviceDate` and Istanbul weekday/cutoff derivation; never silently substitute today's date.

### D04 — local preview scope and deferred operations

- **Date/status:** 2026-10-04; owner decision. **Chosen/rationale:** demonstrate schedules, waves, computed routes and vehicle reuse using read-only live data. Solver speed/optimality are not demo requirements. **Rejected/why:** deployment before QW1/QW2 security closure is outside the approved gate. **Dead ends:** none recorded. **Superseded:** none; publication, driver assignment and live changes remain separate packages.
- **Evidence:** [roadmap §1](DEMO_ROADMAP_2026-10-04.md), [safe-fixes limits](DEMO_SAFE_FIXES_RAPORU_2026-10-06.md). **Check first:** security backlog and publication authority before extending a demo result into service operation.

### D05 — reuse the existing GA split strategy, with truthful defaults

- **Date/status:** owner rationale reported in 2026-10-07 lead handoff; current source checked by the documentation orchestrator. **Chosen/rationale:** daily preview hardcodes `ga_split` and supplies no request `ga_config`/seed; reuse matches D04's demonstration goal. Declared defaults are population 50, iterations 100, crossover 0.85, mutation 0.20, local search every 10, diversification after 30 stagnant generations, maximum no-improvement 25, configured seed `None`.
- **Rejected:** exact routing methods were **never evaluated**, so they are an open research question, not a rejected alternative. **Dead ends:** none recorded. **Correction:** configured `None` does not mean unseeded randomness: `resolve_seed(None)` returns 42, used in request-local `Random`. With literal defaults, stop threshold 25 precedes diversification threshold 30. Constructor `config=None` can select a promoted configuration; effective runtime parameters are unverified here. No tuning or quality claim follows from correctness tests.
- **Evidence:** [preview caller](../src/app/api/admin/dudullu-preview/route.ts), [strategy defaults/configuration](../optimizer_api/strategies/ga_split_strategy.py), [seed resolver](../optimizer_api/strategies/seed_utils.py), [RNG design](superpowers/specs/2026-08-06-1d-rng-determinism-design.md). **Check first:** effective configuration and resolved seed, then fixed-seed repeated experiments and appropriate exact lower bounds.

## Travel-time data

### T01 — authoritative directed road-network travel times

- **Date/status:** 2026-10-05; owner requirement and documented C2 remediation. **Chosen/rationale:** operational times only from stored `time_matrix`; unavailable matrix/missing arcs fail closed. Directed durations must not be replaced by straight-line estimates. The 29 locations/812 arcs and Google-derived provenance are owner/roadmap-reported inventory, not newly queried measurements.
- **Rejected/why:** haversine, Euclidean and all-zero operational fallback invent costs. Development coordinate opt-in is forbidden in production; academic coordinate scope is a distinct metric domain. **Dead ends/reversal:** earlier first-load coordinate fallback and permissive 15-minute stand-ins superseded; no operational caller may depend on them.
- **Evidence:** [architecture §3/§5](../CURRENT_ARCHITECTURE.md), [audit Appendix J C2](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md); merge `0b52ad9` (2026-10-05). **Check first:** authoritative snapshot/domain and strict error mapping; freshness remains T04.

### T02 — injectable matrix repository behind DataLoader

- **Date/status:** 2026-08-07; documented contract. **Chosen/rationale:** separate provider I/O, cache lifecycle and lookups using an injectable provider/clock; preserve DataLoader as the compatibility facade. Typed incomplete-arc errors live in the production repository and are re-exported by the facade.
- **Rejected/why:** relocating that production-specific error into core was unnecessary churn; no new academic consumer was established. **Dead ends:** documentation initially claimed an absent re-export; audit follow-up corrected it. **Superseded:** singleton facade survives, but dual module import roots were fixed in `5796d93`/`d672dc7` (2026-10-04).
- **Evidence:** [repository design](superpowers/specs/2026-08-07-2a-matrix-repository-design.md), [autonomous decisions](superpowers/decisions/2026-08-07-autonomous-session.md), [Appendix J H5](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md). **Check first:** provider seam and actual module origin before diagnosing cache/snapshot divergence.

### T03 — preserve last-known-good and retry failed loads

- **Date/status:** 2026-08-07/08, revised 2026-10-05; documented remediation. **Chosen/rationale:** keep loaded data on refresh failure, expose error/staleness, and apply exponential retry starting at 30 seconds, doubling to cache TTL (default 600), resetting on success. SDK timeout wiring was version-guarded; inspect supported configuration rather than assuming enforcement.
- **Rejected/why:** clearing usable cached data worsens availability; flat TTL backoff imposes a ten-minute initial outage. **Dead ends:** no-backoff fetch storm and never-retried failed first load. **Superseded:** August flat-TTL retry and first-load coordinate fallback by T01/current retry policy. Preserved data is not a declared unlimited staleness license.
- **Evidence:** [autonomous log D2/D3](superpowers/decisions/2026-08-07-autonomous-session.md), [architecture §3](../CURRENT_ARCHITECTURE.md); `dbde785`, merge `0b52ad9` (2026-10-05). **Check first:** retry deadline, failure count and matrix age, then MT2 maximum-staleness policy.

### T04 — paginate and attach provenance, keep MT2 partial

- **Date/status:** 2026-10-05; partial remediation. **Chosen/rationale:** fetch 1000-row pages until a short page and return optional digest/source/load-age provenance bound to solved/certified arcs. This avoids truncation above roughly 32 locations and preserves existing response compatibility.
- **Rejected:** none recorded. **Dead ends:** treating the provider's first page as the entire matrix. **Reversal:** no claim that provenance closes the whole matrix contract; domain enum, maximum staleness and row-count check remain open.
- **Evidence:** [Appendix J MT2](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md), [architecture §5](../CURRENT_ARCHITECTURE.md); `1de70a5`, merge `6135319`. **Check first:** captured provenance plus paging/completeness tests before adding a freshness or domain claim.

### T05 — distinguish matrix grouping from geometric grouping

- **Date/status:** 2026-10-05; documented accepted distinction. **Chosen/rationale:** k-medoids and Clarke-Wright use the directed matrix; directed saving is `c(i,D)+c(D,j)-c(i,j)` with ordered tail-to-head merges. K-means/FCM/sweep/hierarchical geometric grouping stays coordinate-based; grouping is not a travel-time substitution.
- **Rejected/why:** haversine fallback for matrix clustering violates T01; one-direction-only saving gives the wrong closed-tour merge cost. **Dead ends:** depot lacking location code caused fallback; corrected. **Superseded:** listed-direction saving by `84f70e3`; geometric methods remain a separate future comparison, not rejected algorithms.
- **Evidence:** [architecture §5](../CURRENT_ARCHITECTURE.md), [Appendix J follow-ups](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md); merge `6135319`. **Check first:** algorithm's grouping metric, depot code and merge orientation.

### T06 — correct the GEO test bound, preserve TSPLIB metric

- **Date/status:** 2026-08-07; historical recorded decision. **Chosen/rationale:** derive the test maximum from the canonical radius (`int(pi*6378.388)+1`, 20039), retaining the TSPLIB formula. **Rejected/why:** altering the correct metric to fit the test's 20000 bound changes benchmark costs. **Dead ends:** interpreting a failing assertion as production travel-time corruption. **Reversal:** none recorded.
- **Evidence:** [autonomous log D1](superpowers/decisions/2026-08-07-autonomous-session.md) reports 45 module/5 GEO tests; not rerun. **Check first:** metric provenance and canonical formula before changing academic distances.

## Optimizer and certificate

### O01 — certify on captured authoritative arcs

- **Date/status:** 2026-10-05; documented C2 closure. **Chosen/rationale:** independently re-cost every response step on the snapshot or an atomic pre-solve copy; per-arc tolerance 0.005 minutes absorbs two-decimal formatting, with corresponding aggregate formatting checks. It is not extra ride-time allowance. Certify constraints on authoritative costs.
- **Rejected/why:** solver-reported durations self-certify; post-solve live lookup admits a refresh race. **Dead ends:** earlier response-derived matrix. **Reversal:** re-costing replaces self-reference; benchmark certification stays in its own problem domain.
- **Evidence:** [architecture §5](../CURRENT_ARCHITECTURE.md), [Appendix J C2 certifier](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md); `c6684f3`, `9e34a2f`, merge `0b52ad9`. Historical integrated suites are reported there, not rerun here. **Check first:** captured arc identity/digest and independent mismatch tests.

### O02 — operational conservative rounding, academic nearest

- **Date/status:** 2026-10-05; accepted correction. **Chosen/rationale:** operational OR-Tools ceilings arcs/service and floors tour limits; report true unscaled times. Keep engine/academic default `nearest` for parity.
- **Rejected/why:** changing academic default would silently alter comparison evidence. **Dead ends:** nearest rounding in operations could admit a true-duration overrun. **Superseded:** universal conservative behavior by explicit mode/scope separation.
- **Evidence:** [architecture §5](../CURRENT_ARCHITECTURE.md), `43311d8`/`0a6746f`, merge `0b52ad9`; `test_ortools_rounding_conservative.py` named in [tracker](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md). **Check first:** `arc_rounding` and execution domain; PyVRP scaling/time-window rounding remain open.

### O03 — K5: two independent duration limits

- **Date/status:** 2026-10-04; owner decision. **Chosen/rationale:** student in-vehicle limit defaults to 90 min (UI 15–240); closed vehicle tour defaults to 150 (UI 30–300). Pickup ride runs stop→campus including closing arc; dropoff campus→stop. This separates service level from vehicle duty.
- **Rejected/why:** using tour duration alone as “max travel time” failed to express the owner's concern about a three-vehicle result. **Dead ends:** ambiguous single-limit interpretation. **Reversal:** earlier 120-minute tour-only demo replaced. Decoder construction and final certificate both matter; fallback is certificate-gated.
- **Evidence:** [roadmap R1/R2](DEMO_ROADMAP_2026-10-04.md), [architecture §5](../CURRENT_ARCHITECTURE.md); `5881570`, `45cedd2`, `be74961` (2026-10-04). **Check first:** which limit is being discussed and whether waiting is represented (N1/H2).

### O04 — reverse the direct-arc lower-bound precheck

- **Date/status:** removed 2026-10-06, integrated 2026-10-07. **Chosen/rationale:** consult the solver even when a direct campus arc exceeds the ride limit; this directed matrix need not satisfy triangle inequality. Keep actual route validation and `ride_time_violation`; nullable `minimumFeasibleRideMinutes` remains `null`.
- **Rejected/why:** direct arcs are not global ride-time lower bounds; “above 240 unreachable” was unsupported. **Dead end/reversal:** R2 precheck and R3 unreachable hint were tried then removed. Owner handoff reports 5 faster indirect dropoff stops (up to 6 min), 16/21,924 nonmetric triplets; these measurements were not reproduced.
- **Evidence:** [safe-fixes report §1](DEMO_SAFE_FIXES_RAPORU_2026-10-06.md), task-1 process files in triage; `4bae8dd`, merge `6f09e5a`. Reported regression: direct100, indirect20, limit50, both directions; 246 focused tests. **Check first:** nonmetric regression and computed-route certificate before claiming global infeasibility.

### O05 — consistent lexicographic ranking

- **Date/status:** 2026-08-06; documented contract. **Chosen/rationale:** use feasibility, then route/vehicle count, then travel cost consistently for fitness/incumbent/reporting. For a fixed giant tour the split DP minimizes cost among feasible contiguous partitions; that inner objective is distinct from GA outer ranking.
- **Rejected:** none recorded. **Dead ends:** inconsistent fitness/incumbent/reporting objectives documented in the design. **Superseded:** divergent scalar ranking, subject to each audited adapter's remaining scope.
- **Evidence:** [objective design](superpowers/specs/2026-08-06-1d-objective-design.md), [split decoder](../uniride_core/algorithms/string_split_decoder.py); source distinction checked by orchestrator. **Check first:** all three comparison sites and adapter objective; M26 remains open.

### O06 — strict arcs and explicit time-window modes

- **Date/status:** 2026-08-06, strict follow-ups 2026-10-05. **Chosen/rationale:** reject missing directed arcs, separate strict/soft time-window modes, enumerate feasible pickup prefixes and wire independent certificates. DP uses infeasibility rather than invented travel costs.
- **Rejected/why:** fabricated missing-arc values mask infeasibility; a blanket exception inside a hot GA decode path was not the chosen initial design. **Dead ends:** unexplored pickup prefixes and omitted depot predecessor handling. **Reversal:** remaining 15-minute defaults removed in `6c9cebe`/`6135319`.
- **Evidence:** [ATSP/split design](superpowers/specs/2026-08-06-1c-split-decoder-atsp-repairs-design.md), [tracker N1](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md). **Check first:** direction/time-window branch and certificate; N1 phantom wait/ignored fallback error remain open. Current demo sets `use_time_windows:false`, so demo success does not close H2–H4.

### O07 — typed success certificates without breaking errors

- **Date/status:** 2026-08-11; approved design. **Chosen/rationale:** optional typed certificate DTOs on successful and failed responses expose checks while retaining existing `error_message` compatibility. **Rejected/why:** arbitrary dictionaries permit malformed schema; replacing errors with certificates breaks existing consumers. **Dead ends:** successful results enforced internally but discarded certificates. **Reversal:** additive disclosure, not a universal security/feasibility claim.
- **Evidence:** [certificate DTO design](superpowers/specs/2026-08-11-package-a-success-certificate-dto-design.md). **Check first:** DTO invariants and response/persistence admission gates on the affected endpoint.

### O08 — retain legacy-runner correctness changes, invalidate old comparisons

- **Date/status:** 2026-10-05; accepted review correction. **Chosen/rationale:** split strategies in academic coordinate scope use problem coordinates instead of zeros; sweep pivots at request depot. **Rejected/why:** preserving incorrect zero-matrix/depot behavior merely for numeric parity. **Dead ends/reversal:** earlier “legacy runner unchanged” statement corrected. `academic_benchmark` is a different path and was not changed by this fix.
- **Evidence:** [architecture §5](../CURRENT_ARCHITECTURE.md), [Appendix J C2 review](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md), `0a6746f`/`57259fa`. Reported tiny12 seed42: GA split556→264; PSO/GWO/HHO split468→264; two-opt276→274. Not independently rerun. **Check first:** runner/domain/commit when comparing old results; do not pool pre/post-correction numbers.

## Vehicle assignment

### V01 — bounded physical search and conditional minimality

- **Date/status:** 2026-10-04; documented D1b implementation. **Chosen/rationale:** search fixed route intervals with cooldown, peak concurrency lower bound and identical-signature symmetry breaking; default 50,000 search nodes. `minimumProven` requires completed search or matching lower bound. A complete feasible witness after budget exhaustion is an upper bound, not a proven minimum.
- **Rejected:** none recorded. **Dead ends:** exhaustive symmetric exploration exhausted budget even with a lower-bound solution. **Superseded:** unconditional exact-minimum wording; route generation itself remains heuristic.
- **Evidence:** [roadmap D1b](DEMO_ROADMAP_2026-10-04.md), `0883313`/`b9f6655`; [assignment producer](../src/services/dudullu-preview.ts) inspected by orchestrator. **Check first:** `minimumProven`, node-budget outcome and witness completeness before quoting minimum vehicles.

### V02 — adequacy follows assignment evidence, not count difference

- **Date/status:** fixed 2026-10-06, integrated 2026-10-07. **Chosen/rationale:** virtual-mode real sufficiency is unknown; live positive conclusion requires complete matching physical-assignment evidence, even if minimality is indeterminate. Producer owns physical capacity/cooldown checks; view validates the witness structure. Live shortage concerns these computed routes.
- **Rejected/why:** virtual-required minus real-active counts cannot prove heterogeneous capacity/cooldown adequacy, spare vehicles or exact shortage. **Dead end/reversal:** earlier enough/missing arithmetic replaced; live shortage card aligned with header by polish.
- **Evidence:** [safe-fixes report §2](DEMO_SAFE_FIXES_RAPORU_2026-10-06.md), task-2/final-review process files; `54a8af1`, `8f73e67`, `6f09e5a`. Historical 224-test green and 15-failure red reported, not rerun. **Check first:** mode, complete route/occurrence identities and actual assignment witness; optional identity metadata absent on older envelopes remains a trust limitation.

## UI wording and claims

### U01 — K4: location codes with placeholder names

- **Date/status:** 2026-10-04; owner decision. **Chosen/rationale:** use So1/Sw1-style stop codes and placeholders instead of exposing names. **Rejected:** none recorded. **Dead ends:** none recorded. **Reversal:** none recorded.
- **Evidence:** [roadmap K4/D2](DEMO_ROADMAP_2026-10-04.md). **Check first:** rendered labels/export contents before adding student detail to demo artifacts.

### U02 — capacity floor explains counts, not causality

- **Date/status:** 2026-10-04; review-corrected R3 decision. **Chosen/rationale:** separate Sw/So pools yield `max(ceil(Sw/capSw),ceil(So/capSo))`; show an explanatory lower bound and possible timing/overlap/cooldown causes only. **Rejected/why:** naming the extra vehicle's actual cause without measuring it. **Dead ends:** causal wording in initial R3; corrected. **Superseded:** unreachable direct-limit hint by O04.
- **Evidence:** [roadmap R1/R2 live-run note](DEMO_ROADMAP_2026-10-04.md), `0c9ada4`, merge `1914e4d`. Owner/source-reported Monday: 28 total students, 27 that day, peak20 (5Sw/15So), capacity floor2, result3 vehicles/16 routes/12 waves/longest89 at ride90/tour150. Exploration ride60→5–6 routes at08:45; ride45→7 is handoff-reported only. **Check first:** snapshot, parameters, floor formula and measured attribution; no bug or superiority claim follows from three vehicles alone.

### U03 — readiness aggregates and truthful direction

- **Date/status:** 2026-09-03/08; documented contracts. **Chosen/rationale:** dedicated aggregate readiness page through existing authenticated client, strict DTO/no-store/redacted errors; normalize omitted request direction to pickup, reject malformed/conflicting successful responses, persist the calculation's direction.
- **Rejected/why:** settings embedding mixes responsibilities; console tokens unsafe; broad monitoring dashboard outside gate. Widening direction types/fabricating successful response direction hides contract errors. **Dead ends:** none beyond documented defects. **Reversal:** none recorded.
- **Evidence:** [readiness design](superpowers/specs/2026-09-03-dudullu-readiness-admin-view-design.md), [DUD-01 design](superpowers/specs/2026-09-08-dud01-auth-direction-repair-design.md). **Check first:** PASS vs BLOCKED-DATA/BLOCKED-CONFIG and response direction; old implementation tests do not establish current live readiness.

## Process

### P01 — isolated implementation and independent integration review

- **Date/status:** 2026-10-04/07; owner/lead process. **Chosen/rationale:** Claude lead orchestration, worktree per implementation agent, independent reviewer before merge, maximum three fix rounds, `merge --no-ff`, push after each owner-authorized integration merge. **Rejected:** none recorded. **Dead ends:** none recorded. **Reversal:** none; task-specific no-push/no-main scopes still govern workers.
- **Evidence:** [roadmap §3](DEMO_ROADMAP_2026-10-04.md), [safe-fixes branch/report](DEMO_SAFE_FIXES_RAPORU_2026-10-06.md); max-round/push instructions owner-handoff reported. **Check first:** current authorization, branch and dirty-tree boundaries; process notes do not authorize deployment or database writes.

### P02 — existing CLIs for the isolated demo, no auto-reload

- **Date/status:** 2026-10-04/06; accepted/reversed proposal. **Chosen/rationale:** use two existing terminal CLIs on web9003/optimizer8001 with candidate-first Python import paths; disable optimizer reload because Windows reload killed the stack. Reuse installed runtimes/dependencies.
- **Rejected/why:** new isolated launcher/service-manager implementation was superseded as unnecessary for the requested demo. **Dead end:** task-3 brief originally specified a launcher and tests, then explicitly revised it to documentation only. **Reversal:** revised brief governs old paragraphs. Code/port isolation is not database isolation.
- **Evidence:** task-3 brief triage, [demo runbook](DEMO_SAFE_FIXES_KULLANIM.md), [safe-fixes report](DEMO_SAFE_FIXES_RAPORU_2026-10-06.md); reload merge `5eb0229`. **Check first:** source origins, occupied ports and shared-key equality without printing values; health smoke is not authenticated preview verification.

### P03 — preserve rescue state and consolidate selectively

- **Date/status:** 2026-08-01/09-22; historical process. **Chosen/rationale:** preserve dirty bytes/patches/checksums, keep WIP authoritative, reconstruct only classified current-context changes over the academic spine. **Rejected/why:** broad rescue merge/range cherry-pick risks importing unclassified defects; unclassified hunks default reject. **Dead ends:** none recorded. **Superseded:** rescue history is provenance, not executable scientific evidence.
- **Evidence:** [preservation plan](superpowers/plans/2026-08-01-dirty-checkout-preservation-doc-sync.md), [consolidation design](superpowers/specs/2026-08-01-wip-branch-consolidation-design.md), [recovery plan](superpowers/plans/2026-09-22-uniride-recovery-and-continuation.md). **Check first:** preservation inventory and integration manifest; never clean/reset original rescue work to simplify a task.

### P04 — evidence labels remain scoped and dated

- **Date/status:** continuing rule; recorded 2026-10-07. **Chosen/rationale:** retain exact commands/results and distinguish source review, mocked regression, service smoke, authenticated preview, scientific parity and publication evidence. **Rejected/why:** “all tests pass”/repository clean from partial checks overstates evidence. **Dead ends:** interrupted/no-output runs are blockers, never passes. **Reversal:** historical partial C1 reports were later superseded by explicitly recorded closure, not erased.
- **Evidence:** [C1 final gate report](../.superpowers/sdd/task-c1-10-report.md), [safe-fixes report verification/limits](DEMO_SAFE_FIXES_RAPORU_2026-10-06.md), [jury review](superpowers/reports/2026-08-06-jury-roadmap-conformance-review.md). **Check first:** exact command, interpreter, commit and scope before borrowing a historical green result. This Markdown task ran no application tests.

## Academic and service boundaries

### A01 — four gates, canonical ownership and quarantine

- **Date/status:** 2026-07-22/24; approved architecture. **Chosen/rationale:** quarantine YAEM and establish contracts; parity-preserving Bildiri extraction into core; then catalog/composition/services; analysis/publication last. Studies become thin profiles; archive only after parity and zero-active-import gates.
- **Rejected/why:** active independent study solvers/duplicate kernels undermine ownership; B-GA/B-PSO get migration guidance, not false compatibility aliases. **Dead ends:** invalid/historical evidence must not be repaired in place into scientific evidence. **Superseded:** legacy engines/names by truthful canonical ownership; `GWO-LKH`/`HHO-LKH` are not valid active labels without actual LKH.
- **Evidence:** [unification design](../ACADEMIC_STUDY_UNIFICATION_DESIGN.md), [Package A plan](superpowers/plans/2026-07-22-yaem-quarantine-contract-foundation.md), [Package B plan](superpowers/plans/2026-07-24-bildiri-canonical-extraction.md), [quarantine guard report](../.superpowers/sdd/task-7-hardening-report.md). **Check first:** gate evidence and archive classifications (`INVALID`, `HISTORICAL_UNVERIFIED`, `REFERENCE_ONLY`, `WITHHELD_SENSITIVE`); historical passes are not current reruns.

### A02 — evidence-specific capabilities and immutable preflight

- **Date/status:** 2026-07-28/29; approved C1 contract and historical closure. **Chosen/rationale:** registry existence is implementation, not scientific selectability; exact TSP/ATSP/protocol/backend/composition claims need executable evidence. Resolve/preflight before registry lookup, postflight actual results, preserve full immutable decision provenance at CLI/Smart worker and persistence boundaries.
- **Rejected/why:** candidate/planned/alias manifest declarations and study-specific exemptions bypass evidence. **Dead ends/reversal:** interim candidate-manifest allowance was superseded by evidence promotion `406a1ab` and verified-only manifests `15a45ff` (both Git-verified ancestors dated2026-07-29). Backend mismatch requires a new decision, not silent fallback.
- **Evidence:** [C1 design](superpowers/specs/2026-07-28-academic-capability-catalog-preflight-design.md), [final review plan](superpowers/plans/2026-07-29-c1-final-review-fixes.md), [C1 reports](../.superpowers/sdd/task-c1-10-report.md). **Check first:** exact claim/evidence node and request-bound canonical identity; H13 current audit remains open despite old scoped closure.

### A03 — Or-opt and ALNS promotion needs its own evidence

- **Date/status:** 2026-08-02/03; documented evidence plans. **Chosen/rationale:** canonical core owns moves/search/accounting; academic adapter owns strict scientific protocol/schema. Establish directed correctness, complete-tour evaluation accounting and deterministic replay before changing lifecycle claims.
- **Rejected/why:** inferring counts from iterations or treating implementation availability as verification. **Dead ends:** none recorded. **Reversal:** none claimed here; a plan is not an executed promotion.
- **Evidence:** [Or-opt plan](superpowers/plans/2026-08-02-c2-oropt-evidence.md), [ALNS design](superpowers/specs/2026-08-03-c3-alns-evidence-design.md). **Check first:** current catalog lifecycle and exact evidence nodes before selecting algorithms for a study.

### A04 — scientific budget and problem boundaries

- **Date/status:** approved protocol, retained 2026-10-07. **Chosen/rationale:** fixed objective-evaluation budgets are primary; native termination is separately labelled secondary. Hybrid stages share accounting without hidden polish; Hamiltonian TSP/ATSP and multi-route CVRP/CVRPTW validation differ.
- **Rejected/why:** pooled fixed/native results, uncounted polish and smoke/pilot superiority claims cannot support fair comparisons. **Dead ends:** none recorded here. **Reversal:** false historical algorithm labels must not re-enter active reporting.
- **Evidence:** [fairness protocol](../ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md), [canonical 3-opt contract](../CANONICAL_THREE_OPT_DESIGN.md), [jury review](superpowers/reports/2026-08-06-jury-roadmap-conformance-review.md). **Check first:** problem/profile, budget units, stage accounting, seed and termination label before any numeric comparison.

### S01 — authenticated bounded compute and request-scoped strategies

- **Date/status:** 2026-08-07/12; approved service contracts. **Chosen/rationale:** authenticated BFF→internal-key service, lowering-only versioned ceilings, canonical alias deduplication, fresh strategies, two comparison workers and a total soft deadline. Fail closed on invalid key/config; exact TSP>10 rejects rather than truncates.
- **Rejected/why:** public validation-only or rate-limit-only compute does not establish authorization; mutable registry singletons share configuration across requests. **Dead ends:** per-future timeout/full-context shutdown did not bound total response wait. **Superseded:** soft deadline improves response bounds but is not hard solver cancellation.
- **Evidence:** [auth design](superpowers/specs/2026-08-07-p0-auth-failclosed-design.md), [compute policy design](superpowers/specs/2026-08-12-package-b-compute-policy-design.md), [architecture §2/§6](../CURRENT_ARCHITECTURE.md). **Check first:** endpoint-specific auth and actual cancellation; C4/H7 remain open in October tracker.

### S02 — per-run ownership token design

- **Date/status:** 2026-08-06; documented design, not a blanket current closure. **Chosen/rationale:** unique bearer token per run, store digest, gate stop/status/results and use an HTTP-only BFF cookie. **Rejected/why:** shared service key alone does not isolate callers' jobs. **Dead ends:** none recorded. **Reversal:** none recorded.
- **Evidence:** [P3 design](superpowers/specs/2026-08-06-p3-benchmark-run-owner-tokens-design.md). **Check first:** active legacy endpoint and token enforcement; C4 must be locally reverified before remediation.

### S04 — lock user role and ride-request status in RLS (QW1)

- **Date/status:** 2026-10-09; lead decision, repo fix landed on `fix/qw1-users-role-rls`, live apply pending the owner. **Chosen/rationale:** the live DB had no role trigger and no `is_admin()`, so the migration does not depend on either: insert policy `role = 'student'`, update policy with WITH CHECK, `prevent_role_change()` (invoker, empty search_path) on INSERT and UPDATE OF role with a service_role exemption; the migration aborts if a FOR ALL policy exists on the two tables; student cancel only from pending/confirmed rows without vehicle/actual times, ride_request writes limited to pending statuses and self-cancellation, and the two SECURITY DEFINER RPCs get a pinned `search_path` and no PUBLIC/anon/authenticated EXECUTE (no caller exists). `signUp` loses its role parameter; admin/driver accounts stay on the service-role admin route.
- **Rejected/why:** keeping `authenticated` EXECUTE on the RPCs (no browser caller found); relying on `is_admin()` (absent live). **Dead ends:** no local Postgres/Supabase, so behaviour is proven only by the owner-run script `supabase/tests/20261009_role_lock.sql` plus a static clause test. **Reversal:** none recorded.
- **Evidence:** [audit C1/C1.b](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md), `supabase/migrations/20261009_lock_user_role_and_ride_status.sql`. **Check first:** that the migration was applied and `pg_policies`/`pg_trigger` match it; server-side creation of the `users` row remains open.

### S05 — route_plans read lock; retire the drop-all RLS script (C1.d, M21)

- **Date/status:** 2026-10-09; lead decision, repo fix on `fix/route-plans-rls-m21`, live apply pending the owner. **Chosen/rationale:** the live `route_plans` read policy was `{public}` with no auth check, so anon could read published plans. The migration `20261010_route_plans_read_lock.sql` makes it `TO authenticated` and requires `users.role` in driver/admin (trustworthy since S04 locked the role); admin `ALL` policies on `route_plans`/`sandbox_scenarios` become `TO authenticated` with WITH CHECK; `admin_settings`/`routes`/`vehicles` select_all become `TO authenticated` with the same qual. The only reader of `route_plans` is the BFF (`requireAdmin` + service-role key), so no student or driver path needed broader access. `supabase/rls_policies.sql` is kept as a legacy reference: the drop-all loop is removed and an aborting guard inside `BEGIN … COMMIT` stops any run, so it can neither drop migration-owned policies nor recreate pre-lock policies.
- **Rejected/why:** deleting `rls_policies.sql` (loses history, other docs link to it); keeping the loop with exclusions (would still recreate older policy text); granting students read access (no student reader exists). **Dead ends:** no local Postgres, so behaviour is proven only by the owner-run script `supabase/tests/20261010_route_plans_read_lock.sql` and a static clause test. **Reversal:** none recorded.
- **Evidence:** [audit Appendix J C1.d, M21](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md). **Check first:** that the migration was applied and `pg_policies` shows no `{public}`/`anon` role on the five tables; consolidating all policy into migrations stays MT8.

### S06 — H1 password-hint endpoint deferred until go-live

- **Date/status:** 2026-10-09; owner decision. H1 (the password-hint endpoint answers without login) is deliberately DEFERRED until go-live. **Chosen/rationale:** the system is single-user (owner only); the hints are owner-only mnemonics for the student/driver/admin test accounts. The code (`src/app/api/auth/hint/route.ts`) is not changed.
- **Rejected/why:** fixing now (no outside users, the hints are the owner's test-account mnemonics). **Dead ends:** none. **Reversal:** none recorded.
- **Evidence:** [audit H1](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md), Appendix J status DEFERRED. **Check first:** H1 must be closed in the pre-go-live checklist; re-open before any outside user gets an account.

### S07 — benchmark BFF requires admin; landing page gated (C4 BFF half, QW2 minus H1)

- **Date/status:** 2026-10-09; lead decision, repo fix on `fix/qw2-benchmark-bff-auth` (pending merge). **Chosen/rationale:** every `/api/benchmark/*` handler first calls `denyUnlessBenchmarkAdmin` (`src/lib/benchmark-auth.ts`, wraps `requireAdmin` and maps errors with `handleApiError` as the admin routes do: 401 anonymous, 403 non-admin). The `src/proxy.ts` matcher also covers `/api/benchmark/:path*` (bearer check only, defence in depth). `benchmark-service.ts` sends the Supabase bearer token via `getAuthToken` from `admin-api.ts` and sends nothing without a session. The landing page `/` is the benchmark suite, so `BenchmarkSuitePage` now mounts the suite only for an admin session; others see a short sign-in prompt and trigger no benchmark call. `run`, `run/status` and `run/stop` read the FastAPI `detail` field so a 429 message is shown.
- **Rejected/why:** keeping the landing benchmark anonymous (the BFF key then unlocks compute for anyone; audit C4); redesigning the landing page (out of scope). **Dead ends:** none. **Reversal:** none recorded. H1 (`/api/auth/hint`) untouched per S06.
- **Evidence:** [audit C4, Appendix J C4](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md). **Check first:** this is the BFF half only; the backend half (QW4, stop really stops, slots) is on `fix/qw4-benchmark-stop`. Owner cookies (`benchmark-owner-cookie`) still apply on top of admin auth.

### S03 — bounded quick fixes, hermetic discovery and explicit waivers

- **Date/status:** 2026-08-10/24; approved historical scope. **Chosen/rationale:** repair easy build/provider/optional-solver/discovery failures while documenting remaining security/feasibility debt; canonical tests exclude historical/manual scripts and unrelated worktrees; tenant configuration rejects blank/reserved/duplicate identities/secrets.
- **Rejected/why:** documentation-only left easy defects; full hardening package mixed too many risk surfaces. **Dead ends:** eager Supabase client construction broke page-data collection; broad test discovery imported manual scripts/local artifacts. **Superseded:** historical warning/build/dependency waivers stay dated, not current clean-state claims.
- **Evidence:** [quickfix design](superpowers/specs/2026-08-10-post-audit-quickfixes-design.md), [remediation design](superpowers/specs/2026-08-24-audit-remediation-design.md), [architecture historical baseline](../CURRENT_ARCHITECTURE.md). **Check first:** waiver scope/date and canonical test discovery before upgrading/deleting dependencies or asserting release readiness.

### A06 - benchmark stop is cooperative; slots held until the worker exits (C4/QW4)

- **Date/status:** 2026-10-09; implemented on `fix/qw4-benchmark-stop` (backend half). **Chosen/rationale:** `stop_run` sets a per-run `threading.Event`; the run stays RUNNING and keeps its `MAX_CONCURRENT_BENCHMARKS` slot while its registered worker thread is alive; the runner checks the flag between experiments and the worker marks STOPPED on exit. `/stop` answers `stopping` while the worker is alive. Tuning params are bounded with `compute_policy.validate_tuning_dict` (iterations, population, `max_no_improvement`, `time_limit`; ceilings from `load_compute_policy`, env-overridable up to `HARD_CEILINGS`) at the router (422) and again in `_apply_algorithm_params`. The compute-starting endpoints (`/run`, `/import`, `/download`) get a scoped rate-limit dependency (bucket prefix `benchmark:`, separate from production `/optimize`); `/status` and `/stop` are not limited because the UI polls every 2 s. Matrix-native params (iteration, population, `time_limit`, `time_limit_seconds`) are bounded by the same policy ceilings.
- **Rejected/why:** killing threads (unsafe in Python); freeing the slot at stop time (reproduces H.5 thread pile-up). **Academic fairness:** for in-policy params the parameter assignment, seeds and result values on the benchmark-runner path are unchanged (`_apply_algorithm_params` used a legacy mapping) except for `ga_split_enhanced` / `ga_split_hf`, see the decision below. DECIDED and FIXED 2026-10-09 (owner decision, branch `fix/ga-split-variants-params-seed`): `ga_split_enhanced` / `ga_split_hf` previously ignored params and used seed 42 for every run on the benchmark-runner path; they now receive their params and the per-run seed like the other GA strategies (`_apply_algorithm_params` uses `config_field_for_algorithm`, i.e. `CONFIG_FIELD_BY_CANONICAL`; no other algorithm's mapping changed). NO POOLING: the benchmark-runner path keeps results in memory (benchmark_state_manager) and does not persist them to tsplib.db; the real DB had 0 rows for these algorithms on 2026-10-09 (read-only check). `mark_obsolete_ga_split_variant_results.py` and the `include_obsolete` reader filter are a guard for rows copied into tsplib.db and for result files; results exported before the fix (downloaded JSON, browser copies, POST /import) cannot be marked automatically and must not be pooled with results after the fix. The readers (`results_reader.get_benchmark_rows`, `matrix_run_summary.summarize_run`, `promoted_configs`, dashboard) exclude obsolete rows by default, filtered in SQL before LIMIT; `include_obsolete=True` (dashboard sidebar checkbox) is an explicit opt-in. Old and new results must never be pooled; the paper fleet campaign (`docs/paper/results/week-2026-10-05-fleet`) used the production path, not the runner, and is unaffected. The matrix-native path gets the stop check and the same policy bounds. Params above the production ceilings (for example `max_iterations` above 2000) are now refused on the web quick-runner; larger fixed-budget evidence must come from the CLI/`academic_benchmark` path, not this endpoint. Unknown param keys keep legacy pass-through.
- **Evidence:** [audit C4](ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md), `optimizer_api/tests/test_benchmark_stop_bounded.py`. **Check first:** an experiment already inside `strategy.optimize` cannot be interrupted, so stop latency is one experiment; a total-experiment cap is still open.

## Daily workflow

### W01 — independent legs and production admission

- **Date/status:** 2026-08-25/09-29; approved domain/confirmation contracts. **Chosen/rationale:** schedules produce separate pickup/dropoff occurrences; 15-minute pickup-before-first-class and dropoff-after-last-class buffers; hourly reporting with exact execution anchors. Production admits explicit per-date/per-direction consent by previous-day22:00 Istanbul cutoff; no demand means no matrix/solve.
- **Rejected/why:** directionless legacy rows cannot prove independent consent; no backfill/inferred consent. Duplicate event history/timestamps not required for latest-state confirmation. **Dead ends:** whole-day confirm/cancel semantics cannot represent either/both/neither. **Superseded:** demo D01 is a labelled exception, never persisted production consent.
- **Evidence:** [daily operations design](superpowers/specs/2026-08-25-dudullu-daily-operations-planner-design.md), [leg confirmation design](superpowers/specs/2026-09-29-student-leg-confirmation-design.md), [domain plan](superpowers/plans/2026-08-25-dudullu-daily-demand-domain.md). **Check first:** per-leg record, local service date, cutoff and legacy blocker before interpreting demand counts.

### W02 — production daily orchestrator, staged publication

- **Date/status:** 2026-08-25/09-24; approved design. **Chosen/rationale:** TypeScript orchestrates demand and exact-anchor jobs through canonical FastAPI/core, independently checks matrix-bound routes, then assigns physical vehicles across full depot-to-depot intervals. Keep preview read-only; transactional versioned multi-wave publication and driver operations are later gates.
- **Rejected/why:** extending legacy DouBus island duplicates/violates canonical routing; moving all product orchestration into FastAPI/core crosses ownership boundaries. **Dead ends:** per-wave route count alone cannot establish daily physical resource need. **Superseded:** response-derived timing/certification alone is insufficient without source arcs/full closing chain.
- **Evidence:** [daily operations design §4/§10](superpowers/specs/2026-08-25-dudullu-daily-operations-planner-design.md), [Package2 plan](superpowers/plans/2026-09-24-dudullu-package2-daily-preview.md). **Check first:** package-specific acceptance evidence before claiming persistence, publication, driver assignment or certified shift savings.

## Heterogeneous fleet and data errors

### X01 - vehicle capacity sources disagreed; DB corrected

- **Date/status:** 2026-10-07/08; owner decision, data error. **Finding:** the database vehicle record said 4 Sw + 10 So, while the physical layout and the decoder default (`SplitDecoder`, 4/5) said 4 Sw + 5 So. The owner corrected the DB record to 4/5 on 2026-10-07. Every earlier fleet number computed from the DB used 4/10.
- **Consequence:** the 4/10 results are removed from the paper and replaced by the corrected 4/5 campaign. The 4/10 archive stays in git, labelled invalid due to a data error; it must not be cited as evidence.
- **Check first:** when sources disagree on a capacity, check the physical layout first, then the DB and code defaults. **Evidence:** [design section 1.1 (F6) and owner decisions](designs/HETEROGENEOUS_FLEET_DESIGN.md).

### H01 - heterogeneous fleet design

- **Date/status:** 2026-10-08; owner approved. **Chosen/rationale:** typed split decoder with a large-route quota per wave, exact CP-SAT day selection over the wave menu, typed fixed-route assignment in TypeScript; all additive, optional fields only. Sedan Sw = 0, minibus 4/5, same travel times, ride limit and cooldown 10, cars unlimited, 30 s per (day, R, L), tie-break on car-minutes with weekly max and per-day need both reported.
- **Academic boundary:** default `ga_split` and the shared decoder stay unchanged. WP0 adds byte-identical goldens (`uniride_core/tests/golden/split_parity.json`, `test_split_parity_golden.py`) and a zero-import guard for the new modules. **Rejected:** greedy quota repair as primary (weaker guarantee).
- **Evidence:** [design](designs/HETEROGENEOUS_FLEET_DESIGN.md), owner decisions 2026-10-08. **Check first:** P1 goldens green before any later work package.

### H02 - Q1 open: can a sedan carry Sw?

- **Date/status:** 2026-10-08; **open question**. The current answer is sedan Sw = 0. Whether a Fiat Linea can safely carry 1-2 Sw (folding, transfer seat, ramp) is not verified. It can be tested later as `sedan:1sw3so` with no code change; any such result must be labelled as a scenario, not as validated practice.

### H03 - optional shared seat limit; Doblo is 3 seats in total

- **Date/status:** 2026-10-09; owner decision. **Chosen:** vehicle types gain an optional `total_capacity` (API `total_capacity`, TS `totalCapacity`, CLI `:capN`). Feasible iff Sw <= sw, So <= so and, when set, Sw + So <= total. Unset is byte-identical to before. Fiat Doblo = 3 passenger seats (1 front + 2 rear), at most 1 Sw who sits in a seat while the chair is stowed: `doblo:1sw3so:cap3`. Minibus (4 Sw + 5 So pools) and sedan (0 + 4) unchanged.
- **Superseded:** the earlier minivan campaigns that used `minivan:1sw3so` overstated capacity (they allowed 1 Sw + 3 So = 4 passengers); their results must not be cited as Doblo evidence and are to be rerun with `:cap3`. **Rejected:** changing `string_split_decoder`/`ga_split` (academic parity); the `ga_split` baseline therefore cannot enforce a limit on the fixed type and fails closed.
- **Evidence:** [design](designs/HETEROGENEOUS_FLEET_DESIGN.md), tests `test_typed_split_decoder.py`, `test_typed_certificate_checks.py`, `test_heterogeneous_fleet_wp3.py`, `typed-fleet-assignment.test.ts`, `fleet-scenario-args.test.ts`.

### T07 - TSPLIB matrix cache v2: lossless upper-triangle lzma

- **Date/status:** 2026-10-09; owner instruction (shrink the 2.77 GB local `tsplib.db`, do not delete data). **Chosen:** `distance_matrices.version=2` stores only the strict upper triangle, lzma preset 6, original dtype; used only for symmetric matrices with an all-zero diagonal and only if the encode/decode round trip is byte-identical (otherwise v1 zlib full matrix is kept, e.g. ATSP/ft53). Readers (`get_distance_matrix`, ATSP path of `get_all_problems`) decode v1 and v2 through `academic_benchmark/tsplib_matrix_codec.py`; new writes use v2 when eligible. Converter: `academic_benchmark/tools/compress_tsplib_matrices.py` (backup copy first, per-row SHA-256 + `array_equal` verification, idempotent, `--dry-run`, VACUUM).
- **Rejected:** deleting or recomputing matrices; storing the diagonal (a nonzero diagonal or asymmetry simply stays v1); lossy narrowing to uint16. Academic results are unchanged because decoded matrices are bit-identical.
- **Evidence:** `academic_benchmark/tests/test_tsplib_matrix_compression.py`.

## Open questions and evidence limits

The October audit remains authoritative for its unresolved tracker entries, subject to fresh source verification before fixes. This log closes no audit item. In particular:

- C1/C1.b registration/role and request-status RLS, C4 anonymous benchmark compute, H1 password hints, C3 `id()`-keyed cache remain **open**, not newly investigated here.
- MT2 domain enum, row-count check and maximum staleness; PyVRP scaling; OR-Tools time-window rounding remain **open**. Provenance/pagination do not close them.
- N1 dropoff phantom wait/ignored fallback error, H2–H4 timing/search and M26 adapter objectives remain **open**. Demo `use_time_windows:false` limits relevance; it does not establish compliance elsewhere.
- Exact routing for small waves, quality/tuning comparisons, effective promoted GA settings, fixed-seed/repeated experiments and optimality gaps are **not evaluated**. The existing ≤10-stop exact helper is a single-route TSP helper, not an exact daily capacitated routing method.
- Monday illustration and strict-limit exploration are historical owner/source-reported measurements. Mean student ride time is a proposed analysis metric; this task did not find a displayed implementation or run experiments.
- Safe-fixes historical report records combined48 files/552 Vitest tests, typecheck success, lint0 errors/167 warnings, health/handshake/page200 and anonymousAPI401. It explicitly excludes authenticated live preview, user E2E, production build and new Python/scientific suites. These are **reported results**, not this documentation branch's tests.
- Architecture/roadmap contain historical status text (“PLANNED”, old Package2 blocked language, R3 pending, no-landed-fixes placeholder) alongside later implementation/tracker entries. Use dated specific evidence and Git ancestry; do not copy a stale status wholesale.

- **2026-10-07 batch follow-up proposal — not approved/implemented:** add weekly and single-wave options on the planning page using `runDailyPlan`, expose seed/algorithm/parameter selection, and evaluate an exact small-wave capacitated solver with optimality gaps. The [batch runner](PLAN_EXPERIMENTS.md) only exports the existing operational computation; these page and solver additions remain a separate scope and require their own contracts and verification.

## Triage of process files

All 51 tracked files and 12 distinct untracked process files were inventoried and read as source material. The six tracked `.superpowers/sdd` baseline reports copied into each old worktree are counted once, below, not as eighteen additional untracked files. Verdicts are recommendations only: nothing moved or deleted. `archive candidate` means a historical execution plan can be relocated only in a separately authorized cleanup; source links must remain recoverable. `discard` means no reusable policy beyond extracted decisions, not deletion authority.

### Tracked inventory — 51 files

| File (repository relative) | Verdict | Decision/use |
|---|---|---|
| `.superpowers/sdd/task-7-hardening-report.md` | extracted | A01/P04 quarantine guard evidence |
| `.superpowers/sdd/task-c1-10-report.md` | extracted | A02/P04 partial→closure chronology |
| `.superpowers/sdd/task-c1-6-report.md` | extracted | A02 evidence tuple/withheld promotion |
| `.superpowers/sdd/task-c1-7-report.md` | extracted | A02 manifest-lifecycle reversal |
| `.superpowers/sdd/task-c1-8-report.md` | extracted | A02 pilot gateway migration |
| `.superpowers/sdd/task-c1-final-review-fixes-report.md` | extracted | A02 worker/provenance hardening |
| `docs/superpowers/decisions/2026-08-07-autonomous-session.md` | extracted | T02/T03/T06 history |
| `docs/superpowers/plans/2026-07-22-yaem-quarantine-contract-foundation.md` | extracted | A01 gates/archive contract |
| `docs/superpowers/plans/2026-07-24-bildiri-canonical-extraction.md` | extracted | A01 extraction/parity |
| `docs/superpowers/plans/2026-07-28-academic-capability-catalog-preflight.md` | extracted | A02 evidence/preflight |
| `docs/superpowers/plans/2026-07-29-c1-final-review-fixes.md` | extracted | A02 worker requests/provenance |
| `docs/superpowers/plans/2026-08-01-dirty-checkout-preservation-doc-sync.md` | extracted | P03 preservation/waivers |
| `docs/superpowers/plans/2026-08-01-wip-branch-consolidation.md` | extracted | P03 selected reconstruction |
| `docs/superpowers/plans/2026-08-02-c2-oropt-evidence.md` | extracted | A03 Or-opt evidence gate |
| `docs/superpowers/plans/2026-08-03-c3-alns-evidence.md` | extracted | A03 ALNS evidence gate |
| `docs/superpowers/plans/2026-08-06-1c-split-decoder-atsp-repairs.md` | extracted | O06 strict directed decode |
| `docs/superpowers/plans/2026-08-06-1d-objective.md` | extracted | O05 consistent ranking |
| `docs/superpowers/plans/2026-08-06-1d-rng-determinism.md` | extracted | D05 seed/RNG contract |
| `docs/superpowers/plans/2026-08-06-p3-benchmark-run-owner-tokens.md` | extracted | S02 run ownership |
| `docs/superpowers/plans/2026-08-07-2a-matrix-repository.md` | extracted | T02 provider/cache seam |
| `docs/superpowers/plans/2026-08-07-p0-auth-failclosed.md` | extracted | S01 fail-closed auth |
| `docs/superpowers/plans/2026-08-10-post-audit-quickfixes.md` | extracted | S03 bounded fixes |
| `docs/superpowers/plans/2026-08-11-package-a-success-certificate-dto.md` | extracted | O07 certificate disclosure |
| `docs/superpowers/plans/2026-08-12-package-b-compute-policy.md` | extracted | S01 admission/identity/soft deadline |
| `docs/superpowers/plans/2026-08-24-audit-remediation.md` | extracted | S03 hermetic discovery/tenant validation |
| `docs/superpowers/plans/2026-08-25-dudullu-daily-demand-domain.md` | extracted | W01 leg/anchor domain |
| `docs/superpowers/plans/2026-09-01-dudullu-package0-runtime-readiness.md` | extracted | U03/W02 readiness gate |
| `docs/superpowers/plans/2026-09-03-dudullu-readiness-admin-view.md` | extracted | U03 diagnostic UI |
| `docs/superpowers/plans/2026-09-08-dud01-auth-direction-repair.md` | extracted | U03 stable direction/auth |
| `docs/superpowers/plans/2026-09-22-uniride-recovery-and-continuation.md` | extracted | P03 recovery boundaries |
| `docs/superpowers/plans/2026-09-24-dudullu-package2-daily-preview.md` | extracted | W02 preview gates |
| `docs/superpowers/plans/2026-09-29-student-leg-confirmation.md` | extracted | W01 per-leg consent |
| `docs/superpowers/reports/2026-08-06-jury-roadmap-conformance-review.md` | extracted | A04/P04 claim discipline |
| `docs/superpowers/specs/2026-07-28-academic-capability-catalog-preflight-design.md` | extracted | A02 canonical evidence |
| `docs/superpowers/specs/2026-08-01-wip-branch-consolidation-design.md` | extracted | P03 authoritative spine |
| `docs/superpowers/specs/2026-08-03-c3-alns-evidence-design.md` | extracted | A03 accounting/promotion |
| `docs/superpowers/specs/2026-08-05-phase0-api-hardening-audit.md` | keep | S01/S02 historical threat/test inventory; not current closure |
| `docs/superpowers/specs/2026-08-06-1c-split-decoder-atsp-repairs-design.md` | extracted | O06 directed/time-window modes |
| `docs/superpowers/specs/2026-08-06-1d-objective-design.md` | extracted | O05 ranking |
| `docs/superpowers/specs/2026-08-06-1d-rng-determinism-design.md` | extracted | D05 effective seed |
| `docs/superpowers/specs/2026-08-06-p3-benchmark-run-owner-tokens-design.md` | extracted | S02 ownership |
| `docs/superpowers/specs/2026-08-07-2a-matrix-repository-design.md` | extracted | T02 injectable repository |
| `docs/superpowers/specs/2026-08-07-p0-auth-failclosed-design.md` | extracted | S01 authenticated boundary |
| `docs/superpowers/specs/2026-08-10-post-audit-quickfixes-design.md` | extracted | S03 explicit rejected scopes |
| `docs/superpowers/specs/2026-08-11-package-a-success-certificate-dto-design.md` | extracted | O07 typed additive DTO |
| `docs/superpowers/specs/2026-08-12-package-b-compute-policy-design.md` | extracted | S01 bounds/fresh strategies |
| `docs/superpowers/specs/2026-08-24-audit-remediation-design.md` | extracted | S03 deferrals |
| `docs/superpowers/specs/2026-08-25-dudullu-daily-operations-planner-design.md` | extracted | W01/W02 architecture |
| `docs/superpowers/specs/2026-09-03-dudullu-readiness-admin-view-design.md` | extracted | U03 considered alternatives |
| `docs/superpowers/specs/2026-09-08-dud01-auth-direction-repair-design.md` | extracted | U03 direction contracts |
| `docs/superpowers/specs/2026-09-29-student-leg-confirmation-design.md` | extracted | W01 no inferred consent |

Tracked summary: **50 extracted, 1 keep, 0 archive candidate**. Keeping detailed historic plans is justified by unreplaced acceptance evidence and open related contracts; this task proposes no archival operation.

### Untracked inventory — 12 files

Paths below are relative to the original repository root. They are process provenance, not portable links: an isolated checkout does not contain sibling old worktrees. Durable conclusions are linked to committed sources above.

| File | Verdict | Decision/use |
|---|---|---|
| `.temp/worktrees/codex-ride-limit-fix/.superpowers/sdd/task-1-brief.md` | extracted | O04 authorized nonmetric scope/regression |
| `.temp/worktrees/codex-ride-limit-fix/.superpowers/sdd/task-1-edit.mjs` | discard | One-off literal edits; O04 already extracted; unsafe as general migration |
| `.temp/worktrees/codex-ride-limit-fix/.superpowers/sdd/task-1-report.md` | extracted | O04/P04 commands/interruption evidence |
| `.temp/worktrees/codex-ride-limit-fix/.superpowers/sdd/task-1-review.diff` | extracted | O04 exact removed gate/wording |
| `.temp/worktrees/codex-fleet-evidence-fix/.superpowers/sdd/task-2-brief.md` | extracted | V02 trust boundary/unknown virtual sufficiency |
| `.temp/worktrees/codex-fleet-evidence-fix/.superpowers/sdd/task-2-report.md` | extracted | V02/P04 root-verified finish |
| `.temp/worktrees/codex-fleet-evidence-fix/.superpowers/sdd/task-2-review.diff` | extracted | V02 complete witness checks |
| `.temp/worktrees/codex-demo-safe-fixes/.superpowers/sdd/task-3-brief.md` | extracted | P02 revised CLI-only decision |
| `.temp/worktrees/codex-demo-safe-fixes/.superpowers/sdd/final-review.diff` | extracted | O04/V02 combined source scope |
| `.temp/worktrees/codex-demo-safe-fixes/.superpowers/sdd/final-review-report.md` | extracted | P04 scoped review limitations/zero-duration conservative guard |
| `.temp/worktrees/codex-demo-safe-fixes/.superpowers/sdd/demo-env-check.mjs` | useful script → propose scripts/demo-env-check.mjs | P02 source-origin/key-equality probe; adapt candidate-path assumptions and remove implicit configuration mutation before reuse |
| `.temp/worktrees/codex-demo-safe-fixes/.superpowers/sdd/demo-smoke.mjs` | useful script → propose scripts/demo-smoke.mjs | P02 bounded ports/health/handshake/anon-auth smoke; adapt fixed candidate/ports; not an authenticated preview check |

Untracked summary: **9 extracted, 2 useful script proposals, 1 discard**. Scripts were inspected only, not executed, moved or promoted. Extra ignored progress ledger, where present, is outside the requested 12-file inventory; it is not counted as decision evidence.
