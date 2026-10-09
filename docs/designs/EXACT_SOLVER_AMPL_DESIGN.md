# Exact reference solver (AMPL): design

Status: **design only, no production code.** Date: 2026-10-09. Owner goals: GOAL 1, the optimality gap of the operational GA wave routes; GOAL 2, exact references and lower bounds for the academic benchmark suite.

Binding context: `AGENTS.md` (core vs academic ownership; fixed budget primary, native secondary, never pooled), `docs/DECISION_LOG.md` (cited by ID below; nothing here reopens a settled item), `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`, `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`, `CURRENT_ARCHITECTURE.md` §5, `docs/designs/HETEROGENEOUS_FLEET_DESIGN.md`.

## 0. Facts verified in source (2026-10-09)

| # | Fact | Evidence |
|---|---|---|
| E1 | A route is `depot -> s1..sk -> depot`, no waiting. Pickup ride = arcs `s1 -> .. -> sk -> depot` (the tour minus its first arc). Dropoff ride = arcs `depot -> s1 .. sk` (the tour minus its closing arc). Tour = all arcs. | `typed_split_decoder.py:1-16, 132-149`; `feasibility_certificate.py:271-340` (`check_ride_time`); DECISION_LOG O03 |
| E2 | Students sharing a stop are separate nodes joined by zero-length arcs; they share one ride time. | `check_ride_time` docstring, `feasibility_certificate.py:280-283` |
| E3 | The ride limit is therefore a **per-route** quantity that depends only on the route's arc sum and its first (pickup) or last (dropoff) stop. No per-stop time propagation is needed. | follows from E1 |
| E4 | Typed feasibility: `Sw <= sw_t`, `So <= so_t`, and if set `Sw + So <= total_t`; per-type R and tour limits; at most `q` routes of the quota type; objective (routes of the minimised type, cost). Missing arcs are infeasible. | `typed_split_decoder.py:67-170`; DECISION_LOG H01, H03, O06 |
| E5 | Single-type waves: one `/optimize` call per (direction, anchor) with `algorithm: ga_split`, `is_asymmetric: true`, `use_time_windows: false`, `max_travel_time` = T, `max_ride_time` = R, capacities = max over the wave's virtual vehicles, vehicle cap `min(legs, 50)`. | `src/services/daily-plan-run.ts:43, 526-560` |
| E6 | Heterogeneous waves: menu `q = 0..L` of `ga_split_hf` calls with `max_routes(large) = q`, `minimize_type`, optional `total_capacity`; then CP-SAT day selection over the menu. | `src/services/fleet-scenario-run.ts:42, 495-503`; `uniride_core/planning/typed_day_selection.py`; DECISION_LOG H01 |
| E7 | The GA ranks lexicographically: feasibility, then route count, then travel cost (O05). The split DP's inner objective is distinct from the outer ranking. | DECISION_LOG O05 |
| E8 | The matrix is directed and need not be metric (O04: reported nonmetric triplets). Indirect paths can be shorter than direct arcs. | DECISION_LOG O04, T01 |
| E9 | The final certificate is `certify_optimization_response(request, response, arc_lookup)`; it re-costs every arc on the captured matrix (O01) and checks capacity, typed capacity, quota, tour, ride time and fleet mix. It never raises; a missing `arc_lookup` fails closed. | `optimizer_api/verification/response_certifier.py:240-330` |
| E10 | Archived campaigns hold, per (date, R), the captured matrix (`*.matrix.json`: sha256, arcs) and the response with every wave's routes, `student_ids`, `sw_count`/`so_count` and certificate. The fleet campaigns hold a per-wave `menu` with one option per quota. Valid sources: `week-2026-10-05-4sw5so/` (single type 4/5), `week-2026-10-05-fleet/` (large + sedan) and `week-2026-10-05-fleet/extra/minivan-cap3/` (Doblò `1sw3so:cap3`). `week-2026-10-05/` (4/10) and `extra/minivan/` are invalid or superseded (X01, H03) and must not be used. | `docs/paper/results/*/README.md` |
| E11 | Wave sizes (single type, R = 90): 61 waves in the week; most have 1-6 students; the largest are 20, 13, 11, 11 and 10. | archived `*_R90_repeat1.response.json` |
| E12 | `tsplib.db`: `problems.optimal` holds published optimal values (80 of 93 TSP rows and ATSP `ft53` = 6905); `opt_tours` holds 24 published tours; **`best_solutions` holds this project's own algorithm runs, not published optima.** 17 TSP instances have n <= 100 and 34 have 101-500. CVRP instances are imported by `academic_benchmark/cvrplib_manager.py`. | read-only query of the local `tsplib.db`; `tsplib_manager.py:70-110`; `cli_engine.py:2032` |
| E13 | `amplpy` 0.18.0 is installed in `.venv-jit`; AMPL bundles Gurobi 13.0.3, CPLEX 22.2.0, COPT 8.0.6 and HiGHS 1.15.1 (lead's verification). The existing `string_exact_tsp.py` is a single-route TSP helper, not a capacitated multi-route method (DECISION_LOG "Open questions"). | site-packages listing; DECISION_LOG |

Consequence of E3, which drives the whole design: **the "hard" ride-time constraint is easy at the route level** and only hard inside compact arc-based models.

## 1. Formulation for GOAL 1

### 1.1 Recommendation: exact route enumeration + set partitioning (SP), two lexicographic stages

**Instance (one wave).** Students `i in N` (one node per occurrence, E2), class `Sw` or `So`; depot `0` (campus); directed matrix `c` from the captured snapshot; direction `pickup | dropoff`; types `t in Tset` with `(sw_t, so_t, total_t, R_t, T_t)`; optional quota type `l` with quota `q`; minimised type `m` (typed case only).

**Step A, enumeration (pure Python, no AMPL).** For every student subset `S` and type `t`, keep exactly one column: the minimum-duration order of `S` that satisfies `ride <= R_t`, `tour <= T_t` and the capacities of `t`. One column per (S, t) is enough because the per-route constraints are monotone in the path cost once the end stop is fixed:

- *Pickup.* Backward DP `g(S, f)` = cheapest path that starts at `f`, visits `S`, ends at the depot. Then ride = `g(S, f)` and tour = `c(0, f) + g(S, f)`. For fixed `f` both grow with `g`, so the minimum `g` dominates. Column cost = `min_f { c(0,f) + g(S,f) : g <= R_t, c(0,f) + g <= T_t }`.
- *Dropoff.* Forward DP `h(S, e)` = cheapest path depot -> .. -> `e` over `S`. Ride = `h`, tour = `h + c(e, 0)`; same argument.
- *Pruning.* Extend a label only while the path cost stays within `R_t` (every extension of a pickup path adds to the ride; a dropoff prefix is itself a ride), the class counts stay within `(sw_t, so_t, total_t)` and all arcs are finite (O06). With R <= 90, T = 150 and at most 9 seats, labels die after a few stops.
- *Symmetry.* Co-located students of the same class are interchangeable (zero arcs, E2). Enumerate over (location, class) multiplicity vectors, with the stop **sequence** allowed to return to a location while it still has unserved students of that class. This keeps the nonmetric "revisit" routes that the GA can produce (E8: `B -> A -> campus` may beat `B -> campus`), so the exact search space contains the GA's.
- *Output.* Column `r`: type, students, order, cost `d_r` (integer minutes), ride, tour. Column counts are logged; above a configured cap (default 2 000 000 columns or 10 min of enumeration) the wave falls back to §1.3.

**Step B, SP model in AMPL** (`wave_sp.mod`). `lambda_r in {0,1}`.

```text
cover:   sum_{r ∋ i} lambda_r = 1                        for all i in N
quota:   sum_{r: type(r)=l} lambda_r <= q                (typed case, when q is set)
fleet:   sum_r lambda_r <= V_max                         (V_max = min(legs, 50), E5; non-binding in practice)
```

| Case | Stage 1 (minimise) | Stage 2 (minimise, with stage 1 fixed) | Matches |
|---|---|---|---|
| Single type | `K = sum_r lambda_r` | `D = sum_r d_r lambda_r` subject to `K = K*` | O05 ranking: routes, then travel cost |
| Typed, quota `q` | `K_m = sum_{type(r)=m} lambda_r` | `D` subject to `K_m = K_m*` | `decode_typed` objective (E4) |

Two stages, not a weighted sum: each stage has its own proven bound and status, and no big weight is needed. A weighted single solve (`M*K + D` with `M > N*T`) is kept only as a cross-check in tests.

Why SP fits: the ride, tour and capacity constraints, the directed costs, the Sw/So pools, `total_capacity` and per-type limits are all checked once per column in exact integer arithmetic, so the MIP has no big-M. The SP LP relaxation is known to be tight for tightly constrained VRPs; with E11 sizes the solves are expected to be seconds. **Exactness:** if enumeration completes, the SP optimum is the global optimum of the wave problem under E1-E5 semantics (every feasible route is dominated by a column of the same subset and type).

### 1.2 Bounds and gaps under a time limit

A time-limited MIP solve returns an incumbent and a **dual (best) bound**; every value of the objective over the feasible set is at least the bound, so it is a valid lower bound. Integer data allow rounding up.

| Quantity | Definition |
|---|---|
| `K_LB` | `ceil(stage-1 dual bound)`; also at least `max(ceil(Sw/max_t sw_t), ceil(So/max_t so_t))` and the size of any clique of pairwise ride-incompatible students (computed from the 2-student columns). The report keeps the maximum and names its source. |
| `D_LB` | Stage-2 dual bound, valid **conditional on** `K = K*`. Only reported when stage 1 is proven. |
| `D_LB_free` | Dual bound of `min D` with no count objective. Valid for any route count; reported always, so a duration bound exists even when stage 1 is not proven. |
| Routes gap | `dK = K_GA - K_LB` (absolute; small integers). Proven exact when `K_LB = K*`. |
| Duration gap | If `K_GA = K*`: `gD = (D_GA - D_LB) / D_LB`. If `K_GA > K*`: the GA is already lexicographically worse; `gD` is "not comparable" and only the informative `gD_free = (D_GA - D_LB_free) / D_LB_free` is shown. |
| Day aggregation | `dK_day = sum_w dK_w`; `gD_day` = `(sum D_GA - sum D_LB) / sum D_LB` over waves where `gD` is defined, with the count of excluded waves stated. |

**Limits (owner decision EQ1, 2026-10-09).** GOAL 1 solves run with a 60 s wall-clock limit per wave and 600 s for the peak wave(s); peak wave: [EKSİK: peak-wave definition to be fixed in E0]. The deterministic work limit and 1 thread rules of §4 are unchanged.

`K_GA < K_LB` or `D_GA < D_LB` at equal K is an **error** (model or semantics mismatch), never a result.

### 1.3 Fallback and cross-check: compact two-index model (`wave_compact.mod`)

Used only when enumeration exceeds its cap, and as a cross-check on small waves. Arcs `x_ij` over `N + {0}`.

- Degree: in = out = 1 for every student; `sum_j x_0j = K`.
- Load (MTZ per class and total): every student has demand 1, so load strictly rises along a route; this also removes subtours **including zero-arc cycles between co-located students**, which a time-based MTZ alone cannot remove.
- Ride potential: pickup `tau_i >= c_i0`, `tau_i >= c_ij + tau_j - M_ij (1 - x_ij)`, `tau_i <= R`; tour `c_0j + tau_j <= T + M (1 - x_0j)`. Dropoff: the mirror forward potential from the depot. `M_ij = R + c_ij` (tight).
- Typed case: one commodity per type with type-indexed arcs `x_ijt` and per-type load and potential. This is heavier; it is used only if a typed wave exceeds the enumeration cap.

Its LP bound is weak (big-M), so a time-limited run usually yields `feasible_with_gap` or `bound_only`.

### 1.4 Alternatives considered

| Option | Verdict | Why |
|---|---|---|
| Compact MTZ/flow model as the primary model | rejected as primary; kept as fallback | Ride time needs big-M potentials; weak LP bound; zero-arc co-located students need extra load MTZ; typed fleets need 3-index variables. SP handles all of these exactly per column. |
| Branch-and-price (column generation with ESPPRC pricing) | deferred | Needed only if full enumeration fails; E11 sizes make complete enumeration the simpler exact method. It is the upgrade path if larger waves appear. |
| Brute force over all partitions and orders | test oracle only | Bell-number growth; feasible only for n <= 7 (§8). |
| CP-SAT routing | rejected | Owner chose amplpy for one model on several solvers; CP-SAT stays the day-selection tool (H01). |
| Location-aggregated nodes that forbid revisits | rejected | Would cut nonmetric revisit routes that the GA can produce (E8), so the "exact" optimum could exceed a GA route set. |

### 1.5 Heterogeneous fleet and the day level

For each wave and each `q = 0..L`, the typed SP gives the exact option `(K_m*(q), D*(q))`. The GA menu option for the same `q` (E6, E10) is compared option by option. The **day level** is then solved by re-running the existing CP-SAT selection (`typed_day_selection.py`, unchanged) over the **exact menus**; label `proven_over_exact_menu`. This is stronger than `proven_over_menu`, but it is still not a global day optimum: waves are optimised separately and the menu varies only the quota (HETEROGENEOUS_FLEET_DESIGN §3.4). A global day model is out of scope (owner question EQ3).

## 2. Where the code lives

| Path | Content | Rule |
|---|---|---|
| `uniride_core/exact/__init__.py` | Public API; imports **no** `amplpy` at module import time. | Core owns canonical algorithms (AGENTS.md). |
| `uniride_core/exact/wave_instance.py` | Frozen dataclasses `WaveInstance`, `VehicleTypeSpec`, `ExactResult`; one integer matrix per instance; sha256 of the matrix slice. | Solver-agnostic. |
| `uniride_core/exact/route_enumeration.py` | §1.1 Step A (pure Python/NumPy). | Testable without AMPL. |
| `uniride_core/exact/models/*.mod` | `wave_sp.mod`, `wave_compact.mod`; GOAL 2: `tsp_dfj.mod`, `tsp_mtz.mod`, `cvrp_two_index.mod`. Shipped as package data. | One model, many solvers. |
| `uniride_core/exact/ampl_backend.py` | Locates AMPL (§7), lazy `import amplpy`, writes data through the amplpy API (no temp `.dat`), solves stage 1/2, reads status, incumbent and best bound, records versions. Raises `ExactBackendUnavailable` when absent. | Optional dependency. |
| `uniride_core/exact/brute_force.py` | Oracle for n <= 7 (tests only). | |
| `scripts/run_exact_wave_gaps.py` | GOAL 1 runner: **offline**, reads an archived campaign directory, never the DB or HTTP; writes a new results directory. | Paper scripts live in `scripts/` (like `plan_fleet_pareto.py`). |
| `scripts/plan_exact_gap_report.py` | Tables and the figure (§9 deliverable). | |
| `academic_benchmark/exact_reference/` | GOAL 2: dataset adapter, `exact_reference_v1` protocol runner, manifest and validation. | Datasets/protocols belong to `academic_benchmark`. |
| `optimizer_api/requirements*.txt` | **No change.** `amplpy` goes into an optional extra (`requirements-exact.txt`). | Not operational. |

Guards (tests): `optimizer_api` and `src/` never import `uniride_core.exact` (AST import guard, like the H01 zero-import guard); `uniride_core.exact` is not registered in the production registry and not exposed through `/optimize` (`production_ready` stays false; no strategy file). Without AMPL every public entry point returns a typed `status = "backend_unavailable"` result instead of raising into callers, and the runners exit with a clear message and code 3.

## 3. Certification

An exact result must pass **the same certificate as the GA, on the same captured matrix**:

1. The runner loads the wave from the archive: students from `student_ids` (location code + occurrence), class from the location prefix, **cross-checked** against every archived route's `sw_count`/`so_count` (fail closed on mismatch); depot, direction, anchor, R, T and the fleet from the campaign manifest.
2. `arc_lookup` is built from the archived `*.matrix.json` arcs; its sha256 must equal the response's `matrix.sha256`, else the wave is `input_rejected`.
3. The exact routes are wrapped in the operational response schema (routes, `route_details`, `vehicle_type`, `fleet_mix`) and the request is rebuilt in the operational request schema with the archived parameters, then passed to `certify_optimization_response(request, response, arc_lookup)` (E9). The typed path uses the same function with `vehicle_types`, quotas and `total_capacity`.
4. In the same run, the archived GA routes are re-certified by the same call. Both sides of every gap are thus judged by identical code at one commit.
5. Objective cross-check: the runner recomputes `K` and `D` from the certified routes in integer arithmetic and requires equality with the solver objective (within 1e-6 for solver floating point).
6. A failed certificate makes the exact result `rejected`; it is never repaired or reported as a bound.

Note: the certificate has no waiting time (H2 open); neither do the GA or the model (E1). This is a shared limitation, stated in the paper.

## 4. Fairness, labels and reporting

**Protocol.** A new, separate protocol `exact_reference_v1`. It is neither the fixed-budget primary protocol nor native termination (A04): no objective-evaluation budget, a solver time/work limit instead. Exact rows live in their own files and tables and are never ranked, averaged or tested statistically together with heuristic rows. The only cross-protocol quantity is the **gap** of a heuristic result against a certified exact value or bound, always shown with both labels.

**Status labels (per stage).**

| Label | Meaning |
|---|---|
| `optimal` | Incumbent certified and solver reports optimal with `absgap < 1` (integer data). |
| `feasible_with_gap` | Certified incumbent and a valid bound, not closed within the limit. |
| `bound_only` | Valid bound, no incumbent. |
| `infeasible_proven` | Solver proves no feasible solution (e.g. one student's direct ride exceeds R on every type). |
| `rejected` | Certificate or objective cross-check failed (error, investigated). |
| `backend_unavailable` / `input_rejected` | AMPL/license missing; archive inconsistent. |

**Manifest** (`exact_manifest.json`, one per campaign): git commit and dirty flag; source campaign path and its manifest sha256; matrix sha256 per (date, R); `ampl` version (`option version`), `amplpy` version, solver name and full version string, the verbatim solver option string, threads, seed, time limit, work limit, MIP gap tolerances; enumeration cap and column counts per wave; runtimes; Python version; host OS. No absolute paths, usernames or license text.

**Determinism.** Proven optimal values do not depend on threads or seed. Time-limited bounds and incumbents do. Recommendation: `threads = 1`, fixed `seed = 0`, and Gurobi's deterministic work limit as the primary stop with a wall-clock limit only as a safety net (the wall limits are 60 s per wave and 600 s for the peak wave(s), owner decision EQ1), so that `feasible_with_gap` rows are reproducible on the same version and platform. HiGHS has no work limit; its time-limited rows are labelled `timing_dependent: true`. Driver option keywords and the best-bound suffix are taken from the AMPL MP driver documentation and confirmed in WP-E1; the manifest stores the exact string used.

## 5. GOAL 2 extension plan

| Problem | Model | Mechanism | Realistic exact range (1 thread; time limit deferred, owner question EQ6) |
|---|---|---|---|
| TSP | `tsp_dfj.mod`: degree constraints + DFJ subtour cuts | Iterative cut loop in the Python driver: solve, find connected components of the integer solution, add violated `sum_{i,j in S} x_ij <= |S|-1`, re-solve (AMPL indexed constraint over a growing set of cuts) | n <= ~150-200 for most EUC instances proven optimal; up to a few hundred often closes; above, report `feasible_with_gap` or the LP/cut bound |
| ATSP | same with directed arcs (`x_ij` asymmetric) | same loop; strong-component separation | `ft53` (n = 53) expected optimal |
| TSP/ATSP small | `tsp_mtz.mod` | single solve, cross-check only | n <= ~40 |
| CVRP | `cvrp_two_index.mod` with rounded capacity cuts `x(delta(S)) >= 2 ceil(q(S)/Q)` separated heuristically in the same loop | cut loop; MTZ fallback for tiny | n <= ~30-50 proven; larger: bound only (two-index bounds are weak; branch-cut-price is out of scope) |

Range figures are planning estimates, not measurements; WP-E7 measures them and the paper reports only measured statuses.

**Published optima (E12).** For TSPLIB instances with `problems.optimal`, the exact run must reproduce it (`optimal`) or bracket it (`LB <= optimal <= UB`); any violation is a defect. The published value is recorded as `reference_optimum` with source `tsplib`; it is **not** a computed result and is never labelled `optimal` by this protocol unless the solver proved it. `best_solutions` is our own heuristic history and must never be used as an optimum or a bound.

**Entry into `academic_benchmark`.** `exact_reference/` registers a protocol kind `exact_reference_v1`, writes rows with `solution_kind` (`hamiltonian_cycle` or `vehicle_routes`), status, LB, UB, solver identity and the manifest, and validates UB solutions with the existing independent validators (Hamiltonian and multi-route contracts are separate, A04). Gap columns for metaheuristic rows (`gap_to_LB`, `gap_to_reference_optimum`) are added by the analysis layer and carry both protocol labels. No exact row enters a fixed-budget ranking or statistical test.

## 6. Solver choice

| Role | Solver | Reason |
|---|---|---|
| Primary | Gurobi 13.0.3 (academic) | Strongest MIP; deterministic work limit; the paper states solver and version. |
| Reproducibility fallback | HiGHS 1.15.1 | Open source; anyone can rerun. All `optimal` GOAL 1 results are re-solved with HiGHS in the verification run. |
| Optional cross-check | CPLEX 22.2.0 or COPT 8.0.6 | Only if Gurobi and HiGHS disagree. |

Disagreement in a proven optimal value between two solvers is a blocking defect (model or numerical issue), not a footnote.

## 7. Licensing and environment

- AMPL is found through the environment variable `UNIRIDE_AMPL_DIR`, else an optional local config file (git-ignored), else `amplpy`'s own default lookup. Never a hard-coded path; the manifest records only that the local AMPL installation directory was used, never the path.
- `amplpy` is an optional extra (`requirements-exact.txt`), installed in `.venv-jit`. Missing AMPL or license gives `backend_unavailable`.
- Tests: pure enumeration, brute-force and certificate tests always run. AMPL tests carry a `requires_ampl` marker and are skipped (with reason) when AMPL or a license is absent; CI has no AMPL and must stay green.
- The Gurobi license is academic: results may be used for academic research and the paper, not for operational or commercial use. This is another reason the exact solver stays out of `/optimize` (v1). An operational use would need a HiGHS-only path and an owner decision.

## 8. Verification plan

| Check | Method | Acceptance |
|---|---|---|
| Enumeration vs oracle | Brute force over all set partitions and all orders, n <= 7, both directions, single and typed fleets with `total_capacity` and quota; 500 seeded random instances including nonmetric matrices and co-located students | identical lexicographic optimum `(K, D)` for every instance |
| SP vs oracle | Same instances through AMPL (Gurobi and HiGHS) | equal `(K*, D*)`; status `optimal` |
| Compact vs SP | n <= 12 waves | equal optimum; compact used as fallback only after this passes |
| Dominance | Property test: for each (S, t) the chosen column has the minimum tour among feasible orders | holds on all enumerated subsets for n <= 8 |
| Exact <= GA | Every archived wave: `K* <= K_GA`; if equal, `D* <= D_GA` | holds on all waves; a violation blocks the campaign |
| Certificate | §3 on every exact and every GA result | all `is_feasible: true`; any failure blocks |
| Nonmetric revisit | Hand instance where `B -> A -> campus < B -> campus` | exact solution uses the revisit; certificate passes |
| Determinism | Re-run 5 waves with Gurobi, threads 1, same seed | identical incumbents, bounds and columns |
| GOAL 2 | TSPLIB n <= 100 with published optima; `ft53` | reproduced exactly or bracketed |
| Boundary | AST import guard; registry check; no `amplpy` import at module import time | tests green with AMPL absent |

## 9. Work packages

Gate: each package is reviewed (code line rules: worktree, own branch, tests first, independent reviewer) before the next starts. GOAL 1 first.

| WP | Scope | Files | Tests | Acceptance | Risk | Effort |
|---|---|---|---|---|---|---|
| E0 | Wave instance contract + archive loader (offline) | `uniride_core/exact/wave_instance.py`, `scripts/exact_archive_loader.py` | loader on all valid campaigns; class cross-check; matrix sha check; invalid campaigns refused | all 61 waves x 4 R loaded; counts equal archived | low | 0.5 d |
| E1 | Route enumeration (single + typed, both directions, revisits) + brute-force oracle | `route_enumeration.py`, `brute_force.py` | oracle, dominance, nonmetric revisit, missing arc | 500 instances identical; column counts logged for all archived waves | medium (column explosion on the 20-student wave at R = 90) | 1.5 d |
| E2 | AMPL backend + `wave_sp.mod`, two stages, bounds, environment lookup, graceful absence | `ampl_backend.py`, `models/wave_sp.mod`, `requirements-exact.txt` | `requires_ampl` SP vs oracle (Gurobi, HiGHS); absence test; option/suffix confirmation | equal optima; `backend_unavailable` without AMPL | medium (driver option names, bound suffix) | 1.5 d |
| E3 | Certification bridge + GOAL 1 runner, single type (limits per EQ1: 60 s per wave, 600 s peak wave(s)) | `scripts/run_exact_wave_gaps.py` | GA re-certification; exact certification; objective cross-check; exact <= GA | full grid (5 days x 4 R) for 4/5 fleet, all waves labelled, manifest complete | low | 1 d |
| E4 | Typed runner: per-quota exact menus + CP-SAT day selection over exact menus | runner extension | quota respected; typed certificate; menu option comparison | large+sedan and large+Doblò(cap3) grids complete | medium | 1 d |
| E5 | Compact fallback model | `models/wave_compact.mod` | compact vs SP on n <= 12 | equal optima; invoked only above the cap | medium (weak bounds) | 1 d |
| E6 | Gap report: tables + figure + paper method paragraph (via the writing line) | `scripts/plan_exact_gap_report.py`, `docs/paper/results/week-2026-10-05-exact/` | CSV schema test; recomputation of sums | §9 deliverable below | low | 1 d |
| E7 | GOAL 2: `tsp_dfj.mod`/`tsp_mtz.mod` + cut loop; TSPLIB reproduction | `uniride_core/exact/tsp.py`, models | published optima n <= 100; ft53 | all bracketed or proven | medium | 2 d |
| E8 | GOAL 2: `exact_reference_v1` protocol in `academic_benchmark`, manifest, validation, gap columns | `academic_benchmark/exact_reference/` | protocol separation (no pooling), validator reuse | rows validated; fixed-budget tables unchanged | medium (protocol plumbing) | 2 d |
| E9 | GOAL 2: CVRP two-index + capacity cuts | `cvrp_two_index.mod` | small CVRPLIB optima | measured exact range documented | high (weak bounds) | 2 d |

**Paper deliverable (E6).** Results directory `docs/paper/results/week-2026-10-05-exact/` with README, manifest, and:

- `wave_gaps.csv`: date, R, fleet (`single_4sw5so`, `large+sedan`, `large+doblo_cap3`), quota, wave id, direction, anchor, students, columns, `K_GA`, `K_LB`, `K*`, `D_GA`, `D_LB`, `D*`, `D_LB_free`, `dK`, `gD`, `gD_free`, status per stage, solver, runtime;
- `day_gaps.csv`: per (date, R, fleet) sums and `dK_day`, `gD_day`, excluded waves, plus cars over exact menus vs cars over GA menus for the typed fleets;
- Table: per R, the share of waves with `dK = 0`, mean and max `gD`, and statuses; Figure: per-wave `gD` (y) against students per wave (x), one panel per R, marker by `dK`.
- Paper text carries a short note on the HiGHS cross-check; the details go in the archive (owner decision EQ4).
- Wording rule: a single snapshot week; descriptive gap measurement, not a superiority claim; GA seed 42 single run (the gap is of that run, not of the GA in general).

## 10. Owner decisions (2026-10-09)

The owner approved the lead's recommendations on 2026-10-09 ("Onaylıyorum"), with the values below.

| # | Question | Decision | Status |
|---|---|---|---|
| EQ1 | Time and work limits per stage (GOAL 1)? | 60 s wall per wave; 600 s for the peak wave(s). Deterministic work limit and 1 thread unchanged (§4). Peak wave: [EKSİK: peak-wave definition to be fixed in E0] | Decided; peak-wave definition open (E0) |
| EQ2 | Which typed fleets enter the paper table? | Both: large+sedan and large+Doblò (cap3) | Decided |
| EQ3 | Is "exact per wave, day = CP-SAT over exact menus" sufficient? | Sufficient for now; a global day-level model is out of scope | Decided |
| EQ4 | Report HiGHS cross-check results in the paper or only in the archive? | The paper carries a short note on the HiGHS cross-check; details go in the archive | Decided |
| EQ5 | GA repeats: the archived GA is one seed (42). | GA at seed 42 now, labelled single-seed; a multi-seed gap measurement comes later | Decided; multi-seed later |
| EQ6 | GOAL 2 instance set and time limit | Deferred to a later decision; GOAL 2 stays planned (§5) but is not parameterised yet | Open / deferred |
