# Exact reference solver (AMPL): design

Status: **design only, no production code.** Date: 2026-10-09, revised 2026-10-10 (DUZELT round 1 and owner decisions D-A, D-B, D-C). Owner goals: GOAL 1, the optimality gap of the operational GA wave routes; GOAL 2, exact references and lower bounds for the academic benchmark suite.

Binding context: `AGENTS.md` (core vs academic ownership; fixed budget primary, native secondary, never pooled; four-gate work-package discipline), `docs/DECISION_LOG.md` (cited by ID below; nothing here reopens a settled item), `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`, `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`, `CURRENT_ARCHITECTURE.md` §5, `docs/designs/HETEROGENEOUS_FLEET_DESIGN.md`.

Naming: local facts are `F1`…`F18` (as in HETEROGENEOUS_FLEET_DESIGN.md §1.1); work packages are `WP-E0`…`WP-E10`; `E01` is the DECISION_LOG entry.

## 0. Facts verified in source (2026-10-09, extended 2026-10-10)

| # | Fact | Evidence |
|---|---|---|
| F1 | A route is `depot -> s1..sk -> depot`, no waiting. Pickup ride = arcs `s1 -> .. -> sk -> depot` (the tour minus its first arc). Dropoff ride = arcs `depot -> s1 .. sk` (the tour minus its closing arc). Tour = all arcs. | `typed_split_decoder.py:1-16, 132-149`; `feasibility_certificate.py:271-340` (`check_ride_time`); DECISION_LOG O03 |
| F2 | Students sharing a stop are separate nodes joined by zero-length arcs; they share one ride time. | `check_ride_time` docstring, `feasibility_certificate.py:280-283` |
| F3 | The ride limit is therefore a **per-route** quantity that depends only on the route's arc sum and its first (pickup) or last (dropoff) stop. No per-stop time propagation is needed. | follows from F1 |
| F4 | Typed feasibility: `Sw <= sw_t`, `So <= so_t`, and if set `Sw + So <= total_t`; per-type R and tour limits; at most `q` routes of the quota type; objective (routes of the minimised type, cost). Missing arcs are infeasible. | `typed_split_decoder.py:67-170`; `uniride_core/algorithms/ga_split_typed_engine.py:128` (GA key `(0, routes_by_type[m], cost)`); DECISION_LOG H01, H03, H04, O06 |
| F5 | Single-type waves: one `/optimize` call per (direction, anchor) with `algorithm: ga_split`, `is_asymmetric: true`, `use_time_windows: false`, `max_travel_time` = T, `max_ride_time` = R, capacities = max over the wave's virtual vehicles, vehicle cap `min(legs, 50)`. | `src/services/daily-plan-run.ts:43, 524-560` |
| F6 | Heterogeneous waves: one menu per (date, R), shared by every L file of the campaign: the baseline option `base` (`ga_split`, all routes on the fixed large type) plus quota options `q = 0..min(max L of the campaign, legs, 4)` of `ga_split_hf` calls with `max_routes(large) = q`, `minimize_type`, optional `total_capacity`. The bound uses the largest integer L of the campaign, not the L of each file (large+sedan: L1-L3, so q <= 3; Doblò cap3: L0-L2, so q <= 2; the archived L1 file of large+sedan holds q2 and q3 options). Within the GA menu, an option with the same route partition (sorted occurrence-id sets; stop order ignored) as an earlier option is skipped. A `total_capacity` on the fixed type makes the baseline fail closed (`BASELINE_TOTAL_CAPACITY_EXCEEDED`). CP-SAT then selects one option per wave. | `src/services/fleet-scenario-run.ts:41-42, 47, 383-387, 478, 485-525, 232-235`; manifests `parameters.scenarios`; `2026-10-05_R90_L1.response.json` and `minivan-cap3/2026-10-05_R90_L0.response.json` option ids; `uniride_core/planning/typed_day_selection.py:6-7`; DECISION_LOG H01, H03 |
| F7 | The GA ranks lexicographically: feasibility, then route count, then travel cost (O05). The split DP's inner objective is distinct from the outer ranking. | DECISION_LOG O05 |
| F8 | The matrix is directed and need not be metric (O04: reported nonmetric triplets). Indirect paths can be shorter than direct arcs. | DECISION_LOG O04, T01 |
| F9 | The final certificate is `certify_optimization_response(request, response, arc_lookup)`; it re-costs every arc on the captured matrix (O01) and checks capacity, typed capacity, quota, tour, ride time and fleet mix. It never raises; a missing `arc_lookup` fails closed. | `optimizer_api/verification/response_certifier.py:240-330` |
| F10 | Archived campaigns hold, per (date, R), a matrix file and a response. Each `*.matrix.json` is a **per-date slice** of the snapshot (e.g. 756 arcs on 10-05, 462 on 10-06) while its declared `sha256` (`bfb2dd85…`) and `provenance.location_count` (29) describe the full snapshot, so the sha cannot be recomputed from the slice. The single-type responses (`*_repeat1.response.json`) hold every wave's routes, `student_ids`, `sw_count`/`so_count` and certificate. **The fleet responses hold, per wave, a `menu` whose options carry only the fields `{optionId, kind, quota, status, reason, routes}`, where `routes` is a route count (int or null), not route data**; only the routes of the selected options are archived (`scenario.routes`). Routes, minutes and certificates of non-selected options are not in the archive (checked over all 140 fleet response files: 6 620 options, 1 596 wave menus). Valid sources: `week-2026-10-05-4sw5so/` (single type 4/5), `week-2026-10-05-fleet/` (large + sedan) and `week-2026-10-05-fleet/extra/minivan-cap3/` (Doblò `1sw3so:cap3`). `week-2026-10-05/` (4/10) and `extra/minivan/` are invalid or superseded (X01, H03) and must not be used. | `docs/paper/results/*/README.md`; read-only scan of `week-2026-10-05-fleet/*.response.json` and `extra/minivan-cap3/*.response.json` (2026-10-10) |
| F11 | Wave sizes (single type): 57 waves in the week (226 legs), per date 12 + 13 + 11 + 13 + 8; identical for R = 50, 60, 70, 90. 50 of 57 waves have 1-6 students; the largest are 20, 13, 11, 11 and 10. Both fleet campaigns list the same 57 menu `waveId`s in every (R, L) file. | archived `week-2026-10-05-4sw5so/*_R{50,60,70,90}_repeat1.response.json` (legs = `student_ids` summed over routes); fleet `menu[].waveId` (2026-10-10) |
| F12 | `tsplib.db`: `problems.optimal` holds published optimal values (80 of 93 TSP rows and ATSP `ft53` = 6905); `opt_tours` holds 24 published tours; **`best_solutions` holds this project's own algorithm runs, not published optima.** 17 TSP instances have n <= 100, of which 16 have `problems.optimal` (`rat99` has none); edge types GEO, ATT and EUC_2D. 34 have 101-500. CVRP instances are imported by `academic_benchmark/cvrplib_manager.py`. | read-only query of `academic_benchmark/tsplib_data/tsplib.db` (2026-10-09 and 2026-10-10); `tsplib_manager.py:70-110`; `cli_engine.py:2032` |
| F13 | `amplpy` 0.18.0 is installed in `.venv-jit`; AMPL bundles Gurobi 13.0.3, CPLEX 22.2.0, COPT 8.0.6 and HiGHS 1.15.1 (lead's verification). The existing `string_exact_tsp.py` is a single-route TSP helper, not a capacitated multi-route method (DECISION_LOG "Open questions"). | site-packages listing; DECISION_LOG |
| F14 | The archives predate CX-01 and CX-03. `run_manifest.json` `git_commit`: `6be127d` (4sw5so), `8ab88ca` (fleet), `4200acb` (minivan-cap3); all three have `dirty_working_tree: true` and `termination_protocol: "native"`, seed 42. Neither `b1889cf` (CX-03 merge) nor `eb54509` (CX-01 merge) is an ancestor of any of them (`git merge-base --is-ancestor`). The archived day selections were therefore computed on whole-minute intervals (at `8ab88ca`, `fleet-scenario-run.ts:530-548` floors starts, ceils ends via `toInt` and sends raw-minute cooldowns), before `time_scale = 100`. CX-03 leaves `ga_split_hf` with two types and a quota unchanged (H04), so archived typed GA routes remain valid as routes; the 4sw5so baseline uses `ga_split`, which CX-03 does not touch. | the three `run_manifest.json`; `git show 8ab88ca:src/services/fleet-scenario-run.ts` lines 530-548; `week-2026-10-05-4sw5so/README.md:18`; `fleet-scenario-run.ts:182, 545-566`; `typed_day_selection.py:3, 8`; DECISION_LOG H04, H05 |
| F15 | Every arc in the three valid campaigns is a non-negative integer: 60 `*.matrix.json` files (20 per campaign), 32 424 arc records (10 808 per campaign), 0 non-integer, 0 negative, one declared matrix sha256 (`bfb2dd85…`). The invalid or superseded directories (`week-2026-10-05/`, `extra/L4/`, `extra/minivan/`) are not counted. | read-only scan (2026-10-10); reviewer's recount agrees |
| F16 | `typed_day_selection.solve_day_selection` is a pure function with a 30 s default CP-SAT limit, `num_workers = 1` and a fixed seed; when its limit is hit it returns status `feasible` (a witness), not `optimal`, and the result may depend on machine speed. Its objective is (cars, car-minutes, total vehicle-minutes, sum of option indices) over per-route intervals `[start, end + cooldown)`. The HTTP router adds checks that a direct call bypasses: `MAX_OPTIONS_PER_WAVE = 6`, `MAX_ROUTES_PER_OPTION = 40`, `MAX_TOTAL_ROUTES = 1000`; cooldown `null` means `10 * time_scale`; the effective time limit is the requested value if it is at most the compute-policy `solver_seconds` (default 60), else the request is refused with 422 (none requested: min(30, policy)). The producer sends `time_limit_seconds` 30 (or the CLI value), centi-minute cooldowns, `max_cars` when set, `minutes` as `round6` (not scaled), and refuses `SELECTION_INTERVAL_PRECISION` for an endpoint off the centi-minute grid, never rounding. | `typed_day_selection.py:17-21, 27-30, 41, 120-128, 218-219`; `optimizer_api/routers/fleet_selection.py:40-42, 115-126, 180-182`; `optimizer_api/compute_policy.py:33`; `fleet-scenario-run.ts:198, 545-578` |
| F17 | AMPL driver options (checked 2026-10-10 with `.venv-jit` amplpy, AMPL 20260809): the bare Gurobi keyword `bestbound=1` is echoed as `cvt:pre:boundsbest = 1` and yields no `.bestbound` suffix; `mip:bestbound=1` yields `.bestbound` on Gurobi 13.0.3 and HiGHS 1.15.1; `lim:work`, `tech:seed` and `tech:threads` are accepted by Gurobi; `lim:time=5` is echoed as `lim:time = 5` and accepted by both Gurobi 13.0.3 and HiGHS 1.15.1. | lead's scratch scripts (not committed): `ampl_opts.py` (6 binary variables, one knapsack row; option strings and `.bestbound`), `ampl_opts2.py` (1 binary variable; echo of bare `bestbound=1`), `ampl_opts3.py` (1 binary variable; `lim:time=5` on both solvers); the reviewer's separate 2-variable integer test agrees |
| F18 | Peak waves under the D-B definition (largest leg count per service date, ties included): one per date, all pickup at anchor 525 (08:45): 2026-10-05 20 legs, 10-06 11, 10-07 11, 10-08 10, 10-09 13. Identical for all four R. | archived `week-2026-10-05-4sw5so/*_repeat1.response.json` (2026-10-10) |

Consequence of F3, which drives the whole design: **the "hard" ride-time constraint is easy at the route level** and only hard inside compact arc-based models.

## 1. Formulation for GOAL 1

### 1.1 Recommendation: exact route enumeration + set partitioning (SP), two lexicographic stages

**Instance (one wave).** Students `i in N` (one node per occurrence, F2), class `Sw` or `So`; depot `0` (campus); directed matrix `c` from the captured snapshot; direction `pickup | dropoff`; types `t in Tset` with `(sw_t, so_t, total_t, R_t, T_t)`; optional quota type `l` with quota `q`; minimised type `m` (typed case only). The loader asserts that every arc is a finite, non-negative integer (F15) and rejects the wave (`input_rejected`) otherwise; the pruning argument below needs `c >= 0`.

**Step A, enumeration (pure Python, no AMPL).** For every student subset `S` and type `t`, keep exactly one column: the minimum-duration order of `S` that satisfies `ride <= R_t`, `tour <= T_t` and the capacities of `t`. One column per (S, t) is enough because the per-route constraints are monotone in the path cost once the end stop is fixed:

- *Pickup.* Backward DP `g(S, f)` = cheapest path that starts at `f`, visits `S`, ends at the depot. Then ride = `g(S, f)` and tour = `c(0, f) + g(S, f)`. For fixed `f` both grow with `g`, so the minimum `g` dominates. Column cost = `min_f { c(0,f) + g(S,f) : g <= R_t, c(0,f) + g <= T_t }`.
- *Dropoff.* Forward DP `h(S, e)` = cheapest path depot -> .. -> `e` over `S`. Ride = `h`, tour = `h + c(e, 0)`; same argument.
- *Pruning.* Extend a label only while the path cost stays within `R_t` (with `c >= 0`, every extension of a pickup path adds to the ride; a dropoff prefix is itself a ride), the class counts stay within `(sw_t, so_t, total_t)` and all arcs are finite (O06). With R <= 90, T = 150 and at most 9 seats, labels die after a few stops.
- *Symmetry.* Co-located students of the same class are interchangeable (zero arcs, F2). Enumerate over (location, class) multiplicity vectors, with the stop **sequence** allowed to return to a location while it still has unserved students of that class. This keeps the nonmetric "revisit" routes that the GA can produce (F8: `B -> A -> campus` may beat `B -> campus`), so the exact search space contains the GA's.
- *Output.* Column `r`: type, multiplicity vector `a_{r,(loc,cls)}`, stop order, cost `d_r` (integer minutes), ride, tour. Column counts are logged.
- *Cap (deterministic only).* Enumeration is capped only by deterministic counts: at most 2 000 000 columns per wave (planning default) and a label cap [EKSİK: label-cap value, fixed in WP-E1 from the measured label counts]. If a count cap is hit, the wave is routed to §1.3 and the manifest records `model = compact` and the cap that fired. Enumeration also has a wall-clock safety limit (default 10 min); if that limit fires first, the wave is **aborted** with status `timing_dependent_abort` and no model switch, so whether a wave uses SP or the compact model never depends on machine speed.

**Step B, SP model in AMPL** (`wave_sp.mod`). `lambda_r in {0,1}`. Because columns are aggregated over (location, class), the cover is by multiplicity:

```text
cover:   sum_r a_{r,(loc,cls)} lambda_r = n_(loc,cls)    for all (loc,cls) with n_(loc,cls) > 0
quota:   sum_{r: type(r)=l} lambda_r <= q                (typed case, when q is set)
fleet:   sum_r lambda_r <= V_max                         (V_max = min(legs, 50), F5; non-binding in practice)
```

After the solve, the runner expands each selected column to occurrence ids deterministically (occurrences of each (loc, cls) taken in sorted id order, assigned to the selected columns in column order) before certification (§3). The occurrence-to-column assignment does not change K, D, rides or tours, because co-located same-class students are interchangeable (F2).

| Case | Stage 1 (minimise) | Stage 2 (minimise, with stage 1 fixed) | Matches |
|---|---|---|---|
| Single type | `K = sum_r lambda_r` | `D = sum_r d_r lambda_r` subject to `K = K*` | O05 ranking: routes, then travel cost |
| Typed, quota `q` | `K_m = sum_{type(r)=m} lambda_r` | `D` subject to `K_m = K_m*` | `decode_typed` objective (F4) |

**Stage 2 when stage 1 is not proven.** If stage 1 ends with an incumbent but no optimality proof, stage 2 is still run with `K` (or `K_m`) fixed to the stage-1 incumbent value `K_inc`. Its row is labelled `non_lexicographic: true`; its incumbent is a certified feasible solution, but its bound is a bound only under `K = K_inc` and is **not** reported as `D_LB` (only `D_LB_free` is reported, §1.2). If stage 1 has no incumbent, stage 2 is skipped (`skipped_no_stage1_incumbent`).

Two stages, not a weighted sum: each stage has its own proven bound and status, and no big weight is needed. A weighted single solve (`M*K + D` with `M > N*T`) is kept only as a cross-check in tests.

Why SP fits: the ride, tour and capacity constraints, the directed costs, the Sw/So pools, `total_capacity` and per-type limits are all checked once per column in exact integer arithmetic, so the MIP has no big-M. The SP LP relaxation is known to be tight for tightly constrained VRPs; with F11 sizes the solves are expected to be seconds. **Exactness:** if enumeration completes, the SP optimum is the global optimum of the wave problem under F1-F5 semantics (every feasible route is dominated by a column of the same subset and type).

### 1.2 Bounds and gaps under a time limit

A time-limited MIP solve returns an incumbent and a **dual (best) bound**; every value of the objective over the feasible set is at least the bound, so it is a valid lower bound. Integer data allow rounding up: a bound `b` is used as `ceil(b - 1e-6)`.

| Quantity | Definition |
|---|---|
| `K_LB` (single type) | The maximum of: `ceil(stage-1 dual bound - 1e-6)`; the capacity floors `max(ceil(Sw/sw), ceil(So/so), ceil((Sw+So)/total) if total is set)`; and the size of a clique of pairwise incompatible students, where `i` and `j` are incompatible only if **no enumerated column of any type contains both** (computed from the full column set after enumeration completed; omitted when the wave went to the compact model). The report names the source of the maximum. Capacity and clique floors bound the total route count, which equals `K` only in the single-type case. |
| `K_m_LB` (typed) | `ceil(stage-1 dual bound - 1e-6)` only. Capacity and clique floors bound the total route count, not the count of the minimised type, and are not used. |
| `D_LB` | Stage-2 dual bound, valid **conditional on** `K = K*`. Only reported when stage 1 is proven. |
| `D_LB_free` | Dual bound of `min D` with no count objective. Valid for any route count; reported always, so a duration bound exists even when stage 1 is not proven. |
| Routes gap | `dK = K_GA - K_LB` (absolute; small integers; typed: `K_m,GA - K_m_LB`). Proven exact when the LB equals `K*`. |
| Duration gap | If `K_GA = K*`: `gD = (D_GA - D_LB) / D_LB`. If `K_GA > K*`: the GA is already lexicographically worse; `gD` is "not comparable" and only the informative `gD_free = (D_GA - D_LB_free) / D_LB_free` is shown. |
| Day aggregation | `dK_day = sum_w dK_w`; `gD_day` = `(sum D_GA - sum D_LB) / sum D_LB` over waves where `gD` is defined, with the count of excluded waves stated. |

Note on the clique floor: on a nonmetric matrix (F8, O04), a 3-stop route through `k` can make `i` and `j` jointly feasible although the 2-stop route `{i, j}` is not, because removing a stop can lengthen the path. Incompatibility is therefore never inferred from 2-student columns.

**Limits (owner decisions EQ1 and D-C).** Each **solver call** of GOAL 1 (stage 1, stage 2 and the `D_LB_free` solve each count as one call) has its own wall-clock limit: 60 s, and 600 s for every call on a peak wave. **Peak wave (D-B):** for each service date, the wave(s) with the largest number of legs, all tied waves included, computed by the WP-E0 loader from the archive before any solve, identical across R and fleets, and listed in the manifest. In the current archive these are the five 08:45 pickup waves with 20, 11, 11, 10 and 13 legs (F18). The deterministic work limit and the 1-thread rule of §4 are unchanged.

`K_GA < K_LB` or `D_GA < D_LB` at equal K is an **error** (model or semantics mismatch), never a result.

### 1.3 Fallback and cross-check: compact two-index model (`wave_compact.mod`)

Used only when enumeration hits a deterministic count cap (§1.1), and as a cross-check on small waves. Arcs `x_ij` over `N + {0}`.

- Degree: in = out = 1 for every student; `sum_j x_0j = K`.
- Load (MTZ per class and total): every student has demand 1, so load strictly rises along a route; this also removes subtours **including zero-arc cycles between co-located students**, which a time-based MTZ alone cannot remove.
- Ride potential, pickup (`tau_i` = ride from `i` to the depot along the route): `tau_i >= 0`; `tau_i >= c_i0 * x_i0` (equivalently `tau_i >= c_i0 - M_i0 (1 - x_i0)`), so the direct arc to the depot is charged only when it is used; `tau_i >= c_ij + tau_j - M_ij (1 - x_ij)`; `tau_i <= R`; tour `c_0j + tau_j <= T + M (1 - x_0j)`. No unconditional `tau_i >= c_i0`: on a nonmetric matrix a route `i -> j -> depot` with `c_ij + c_j0 < c_i0` and `c_i0 > R` is feasible and must not be cut (F8, O04).
- Dropoff (mirror; `sigma_i` = ride from the depot to `i`): `sigma_i >= 0`; `sigma_i >= c_0i * x_0i`; `sigma_j >= sigma_i + c_ij - M_ij (1 - x_ij)`; `sigma_i <= R`; tour `sigma_i + c_i0 <= T + M (1 - x_i0)`. `M_ij = R + c_ij` (tight).
- Typed case: one commodity per type with type-indexed arcs `x_ijt` and per-type load and potential. This is heavier; it is used only if a typed wave hits the enumeration cap.

Its LP bound is weak (big-M), so a time-limited run usually yields `feasible_with_gap` or `bound_only`.

### 1.4 Alternatives considered

| Option | Verdict | Why |
|---|---|---|
| Compact MTZ/flow model as the primary model | rejected as primary; kept as fallback | Ride time needs big-M potentials; weak LP bound; zero-arc co-located students need extra load MTZ; typed fleets need 3-index variables. SP handles all of these exactly per column. |
| Branch-and-price (column generation with ESPPRC pricing) | deferred | Needed only if full enumeration fails; F11 sizes make complete enumeration the simpler exact method. It is the upgrade path if larger waves appear. |
| Brute force over all partitions and orders | test oracle only | Bell-number growth; feasible only for n <= 7 (§8). |
| CP-SAT routing | rejected | Owner chose amplpy for one model on several solvers; CP-SAT stays the day-selection tool (H01). |
| Location-aggregated nodes that forbid revisits | rejected | Would cut nonmetric revisit routes that the GA can produce (F8), so the "exact" optimum could exceed a GA route set. |

### 1.5 Heterogeneous fleet and the day level

**Per-wave exact menu.** For each wave the exact menu mirrors the GA menu (F6):

- exact baseline `xbase`: single-type SP with only the fixed large type. Like the GA baseline it fails closed when the fixed type has a `total_capacity` (`fleet-scenario-run.ts:383-387`); in both EQ2 fleets the large type has none;
- exact quota options `xq0..xqQ`: the typed SP with quota `q`, `q = 0..min(max L of the campaign, legs, 4)` (the same range as the GA menu, F6: q <= 3 for large+sedan, q <= 2 for Doblò cap3), giving `(K_m*(q), D*(q))`. Like the GA menu, there is one exact menu per (date, R), shared by all L.

**Per-option comparison.** Each exact option is compared with the GA option of the same kind (`base` vs `xbase`, `q` vs `xq`). The GA side comes **only** from the fleet re-run of WP-E10 (owner decision D-A), which archives every option's routes, minutes and certificates; the old fleet archives cannot supply non-selected options (F10) and predate CX-01/CX-03 (F14). They stay as historical evidence and are never pooled with re-run rows.

**Day level over the union menu.** At one commit and with `time_scale = 100`, the runner calls `solve_day_selection` (unchanged, F16) twice per (date, R, L): once over the GA menus alone (recomputed at this commit, not read from the archive) and once over the **union menu**: the GA options in their WP-E10 order (with the producer's own within-GA dedupe already applied), followed by the exact options in the order `xbase, xq0..xqQ`, all certified.

- *Dedupe.* An exact option is **never** deduped against a GA option: the producer's `signature()` (`fleet-scenario-run.ts:232-235`) compares only sorted occurrence-id sets and ignores stop order, so it would drop an exact option with the same partition but shorter routes in favour of the worse GA option. Exact options are deduped among themselves only when their routes are identical (partition, stop order and per-route minutes). The producer's signature is used only inside the GA menu, as in production.
- *Same inputs as the producer and the router (F16).* The direct call must reproduce what `fleet-scenario-run.ts:545-578` and `fleet_selection.py` do: interval endpoints and both cooldowns in centi-minutes through the same `centi` rule (cooldown `null` means `10 * time_scale`); `start + 1` minimum length; `minutes` = `round6` of real minutes, not scaled; `large_ok`/`car_ok` from `typeAccepts`; `max_cars` passed when set; an endpoint off the centi-minute grid refuses the day with `SELECTION_INTERVAL_PRECISION`, never rounding; time limit = the producer's value (30 s, or the recorded CLI value), which must not exceed the policy `solver_seconds` (60 by default; a larger request is a 422 at the router). The direct call is needed because a union menu can exceed the router caps (6 options per wave, 40 routes per option, 1000 routes in total); the runner records each cap a union request would have exceeded. WP-E4 accepts the port only if the Python recomputation over the GA menus reproduces the WP-E10 archived selection response for every (date, R, L): `status`, `cars`, `large_peak`, `car_minutes`, `total_minutes` and the `selection` with its labels.
- *Proof condition.* `solve_day_selection` returns `feasible` when its time limit is hit (F16), and the union model is larger. **Union cars <= GA-menu cars is claimed, and checked as a blocking test, only when both runs have status `optimal`.** If the union run is not optimal, only the union is re-run once with a longer limit [EKSİK: longer union limit, to be fixed by the lead before WP-E4 starts; the pure function is called with that recorded value], and the limit is recorded. If it is still not optimal, the row is labelled `union_not_proven`, no union <= GA claim is made, and `timing_dependent: true` is set. The report never shows `min(GA, union)`.
- *Independent confirmation.* As in the producer (`fleet-scenario-run.ts:611-631`), every selection is checked by the TypeScript typed assignment: `assignTypedVehicles` and `verifyTypedAssignment` (`src/services/typed-fleet-assignment.ts:160, 191`) and the `typeAccepts` recheck of each assigned route (`fleet-scenario-run.ts:625-631`). The Python runner calls a small TS CLI, `scripts/verify-typed-selection.ts` (run like `experiments:fleet`, `node --import tsx`), over the selection and interval JSON it writes; the CLI returns the assignment status, problems and recheck result as JSON. `typeAccepts` is module-private today (`fleet-scenario-run.ts:217`); WP-E4 exports it without behaviour change. A row whose CLI check is missing is labelled `not_independently_confirmed`; a failed check gives `verification_failed`.
- *Label and claim.* A union row that is optimal in both runs and confirmed is labelled `proven_over_union_menu`: **minimum cars over the union of the GA and per-wave exact menus; never above the GA-menu result (when both runs are optimal); not a global day optimum (EQ3).** Exact options alone do not dominate GA options at the day level: the day objective works on route intervals and concurrency (F16), while the per-wave exact objective is `(K_m, D)`, so cars over exact menus alone could exceed cars over GA menus; the union avoids this. A global day model is out of scope (EQ3).

## 2. Where the code lives

| Path | Content | Rule |
|---|---|---|
| `uniride_core/exact/__init__.py` | Public API; imports **no** `amplpy` at module import time. | Core owns canonical algorithms (AGENTS.md). |
| `uniride_core/exact/wave_instance.py` | Frozen dataclasses `WaveInstance`, `VehicleTypeSpec`, `ExactResult`; one integer matrix per instance; sha256 of the matrix slice. | Solver-agnostic. |
| `uniride_core/exact/route_enumeration.py` | §1.1 Step A (pure Python/NumPy). | Testable without AMPL. |
| `uniride_core/exact/models/*.mod` | `wave_sp.mod`, `wave_compact.mod`; GOAL 2: `tsp_dfj.mod`, `tsp_mtz.mod`, `cvrp_two_index.mod`. Shipped as package data. | One model, many solvers. |
| `uniride_core/exact/ampl_backend.py` | Locates AMPL (§7), lazy `import amplpy`, writes data through the amplpy API (no temp `.dat`), solves stage 1/2, reads status, incumbent, best bound and stop reason, records versions. Raises `ExactBackendUnavailable` when absent. | Optional dependency. |
| `uniride_core/exact/brute_force.py` | Oracle for n <= 7 (tests only). | |
| `academic_benchmark/exact_reference/protocol.py` | The **single** definition of the `exact_reference_v1` protocol, status labels and `exact_manifest.json` schema (written in WP-E2/WP-E3). | Protocols and manifests belong to `academic_benchmark` (AGENTS.md). |
| `scripts/run_exact_wave_gaps.py` | GOAL 1 runner: **offline**, reads an archive directory (the 4sw5so archive for single type; the WP-E10 re-run archive for the typed fleets), never the DB or HTTP; imports the manifest schema from `academic_benchmark/exact_reference`; writes a new results directory. | Paper scripts live in `scripts/` (like `plan_fleet_pareto.py`). |
| `scripts/plan_exact_gap_report.py` | Tables and the figure (§9 deliverable). | |
| `academic_benchmark/exact_reference/` (rest) | GOAL 2: dataset adapter, protocol runner and validation, reusing `protocol.py`. | Datasets/protocols belong to `academic_benchmark`. |
| `optimizer_api/requirements*.txt` | **No change.** `amplpy` goes into an optional extra (`requirements-exact.txt`). | Not operational. |

Guards (tests): `optimizer_api` and `src/` never import `uniride_core.exact` (AST import guard, like the H01 zero-import guard); `uniride_core.exact` is not registered in the production registry and not exposed through `/optimize` (`production_ready` stays false; no strategy file). Without AMPL every public entry point returns a typed `status = "backend_unavailable"` result instead of raising into callers, and the runners exit with a clear message and code 3.

## 3. Certification

An exact result must pass **the same certificate as the GA, on the same captured matrix**:

1. The runner loads the wave from the archive: students from `student_ids` (location code + occurrence), class from the location prefix, **cross-checked** against every archived route's `sw_count`/`so_count` (fail closed on mismatch); depot, direction, anchor, R, T and the fleet from the campaign manifest.
2. `arc_lookup` is built from the archived `*.matrix.json` arcs (a per-date slice, F10). The declared `matrix.sha256` of the matrix file and of the response must be equal, else the wave is `input_rejected`; the runner does not claim that the slice hashes to that sha. It additionally records its own sha256 of the slice (`wave_instance.py`). Non-integer or negative arcs are `input_rejected` (F15).
3. The exact routes (expanded to occurrence ids, §1.1) are wrapped in the operational response schema (routes, `route_details`, `vehicle_type`, `fleet_mix`) and the request is rebuilt in the operational request schema with the archived parameters, then passed to `certify_optimization_response(request, response, arc_lookup)` (F9). The typed path uses the same function with `vehicle_types`, quotas and `total_capacity`.
4. In the same run, the GA routes on the other side of every gap are re-certified by the same call: the archived 4sw5so routes for the single type, the WP-E10 re-run routes of every menu option for the typed fleets. Both sides of every gap are thus judged by identical code at one commit.
5. Objective cross-check: the runner recomputes `K` and `D` from the certified routes in integer arithmetic and requires equality with the solver objective (within 1e-6 for solver floating point).
6. A failed certificate makes the exact result `rejected`; it is never repaired or reported as a bound.

Note: the certificate has no waiting time (H2 open); neither do the GA or the model (F1). This is a shared limitation, stated in the paper.

## 4. Fairness, labels and reporting

**Protocol.** A new, separate protocol `exact_reference_v1`, defined once in `academic_benchmark/exact_reference/protocol.py` (§2). It is neither the fixed-budget primary protocol nor native termination (A04): no objective-evaluation budget, a solver time/work limit instead. Exact rows live in their own files and tables and are never ranked, averaged or tested statistically together with heuristic rows. The only cross-protocol quantity is the **gap** of a heuristic result against a certified exact value or bound, always shown with both labels (for the GA rows: `ga_protocol = native`, §9).

**Status labels (per stage).**

| Label | Meaning |
|---|---|
| `optimal` | Incumbent certified and solver reports optimal with `absgap < 1` (integer data). |
| `feasible_with_gap` | Certified incumbent and a valid bound, not closed within the limit. |
| `bound_only` | Valid bound, no incumbent. |
| `infeasible_proven` | Solver proves no feasible solution (e.g. no enumerated column covers some student). |
| `rejected` | Certificate or objective cross-check failed (error, investigated). |
| `backend_unavailable` / `input_rejected` | AMPL/license missing; archive inconsistent. |
| `timing_dependent_abort` | Enumeration hit its wall-clock safety limit before a count cap (§1.1); no model switch. |

Every stage row also carries `stop_reason` (`optimal`, `work_limit`, `wall_limit`, `infeasible`), `timing_dependent` (true whenever `stop_reason = wall_limit`, for any solver, and for every time-limited HiGHS row) and `non_lexicographic` (§1.1).

**Manifest** (`exact_manifest.json`, one per campaign): git commit and dirty flag; source campaign path and its manifest sha256; matrix sha256 per (date, R); the peak-wave list (§1.2); `ampl` version (`option version`), `amplpy` version, solver name and full version string, the verbatim solver option string, threads, seed, time limit, work limit, MIP gap tolerances; enumeration caps, the model per wave (SP or compact) and column/label counts per wave; runtimes and stop reasons; Python version; host OS. No absolute paths, usernames or license text.

**Determinism.** Proven optimal values do not depend on threads or seed. Time-limited bounds and incumbents do. Recommendation: `threads = 1`, fixed `seed = 0`, and Gurobi's deterministic work limit as the primary stop, with the wall-clock limit only as a safety net (60 s per solver call, 600 s per call on a peak wave; owner decisions EQ1, D-C). In WP-E2 the work limit is calibrated so that the wall limit is not the binding stop on the GOAL 1 grid; any row the wall limit did stop is still labelled `timing_dependent: true`. HiGHS has no work limit; its time-limited rows are always `timing_dependent: true`. Only fully qualified AMPL MP option names are used (F17): `mip:bestbound=1`, `lim:work`, `lim:time`, `tech:threads`, `tech:seed`; never the bare `bestbound=1`. They are confirmed again for the pinned versions in WP-E2, and the manifest stores the exact string used.

## 5. GOAL 2 extension plan

| Problem | Model | Mechanism | Realistic exact range (1 thread; time limit deferred, owner question EQ6) |
|---|---|---|---|
| TSP | `tsp_dfj.mod`: degree constraints + DFJ subtour cuts | Iterative cut loop in the Python driver: solve, find connected components of the integer solution, add violated `sum_{i,j in S} x_ij <= |S|-1`, re-solve (AMPL indexed constraint over a growing set of cuts) | n <= ~150-200 for most EUC instances proven optimal; up to a few hundred often closes; above, report `feasible_with_gap` or the LP/cut bound |
| ATSP | same with directed arcs (`x_ij` asymmetric) | same loop; strong-component separation | `ft53` (n = 53) expected optimal |
| TSP/ATSP small | `tsp_mtz.mod` | single solve, cross-check only | n <= ~40 |
| CVRP | `cvrp_two_index.mod` with rounded capacity cuts `x(delta(S)) >= 2 ceil(q(S)/Q)` separated heuristically in the same loop | cut loop; MTZ fallback for tiny | n <= ~30-50 proven; larger: bound only (two-index bounds are weak; branch-cut-price is out of scope) |

Range figures are planning estimates, not measurements; WP-E7 measures them and the paper reports only measured statuses.

**Published optima (F12).** Published TSPLIB optima are defined on TSPLIB integer distances (`nint` for EUC_2D, the ATT pseudo-Euclidean rule, the GEO rule; T06, and the academic `nearest` rounding of O02). Before any "reproduce exactly" check, WP-E7 asserts that the matrix it solves uses this convention. For TSPLIB instances with `problems.optimal`, the exact run must reproduce it (`optimal`) or bracket it (`LB <= optimal <= UB`); any violation is a defect. The published value is recorded as `reference_optimum` with source `tsplib`; it is **not** a computed result and is never labelled `optimal` by this protocol unless the solver proved it. `best_solutions` is our own heuristic history and must never be used as an optimum or a bound.

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
| Compact vs SP | n <= 12 waves, plus a nonmetric revisit instance where the only feasible route for `i` is `i -> j -> depot` with `c_ij + c_j0 < c_i0` and `c_i0 > R` (pickup and the dropoff mirror) | equal optimum; the compact model finds the revisit route; compact used as fallback only after this passes |
| Dominance | Property test: for each (S, t) the chosen column has the minimum tour among feasible orders | holds on all enumerated subsets for n <= 8 |
| Clique floor | Nonmetric instance where `{i, j}` alone is infeasible but `{i, k, j}` is feasible | `i`, `j` not marked incompatible; `K_LB <= K*` |
| Exact <= GA | Every wave: `K* <= K_GA`; if equal, `D* <= D_GA` (single type vs the 4sw5so archive; typed vs every WP-E10 option of the same kind) | holds on all waves where the exact stage is `optimal`; a violation blocks the campaign |
| Union day level | Per (date, R, L): cars over the union menu <= cars over the GA menus, both at `time_scale = 100` and one commit | checked and blocking **only when both CP-SAT runs are `optimal`**; otherwise the row is `union_not_proven` (§1.5) and not checked |
| Certificate | §3 on every exact and every GA result | all `is_feasible: true`; any failure blocks |
| Nonmetric revisit | Hand instance where `B -> A -> campus < B -> campus` | exact solution uses the revisit; certificate passes |
| Determinism | Re-run 5 waves with Gurobi, threads 1, same seed; enumeration caps count-based only | identical incumbents, bounds, columns and model choice |
| GOAL 2 (correctness verification subset, not the paper instance set; EQ6 open) | TSPLIB n <= 100 with published optima (16 instances, F12); `ft53` | TSPLIB distance convention asserted; reproduced exactly or bracketed |
| Boundary | AST import guard; registry check; no `amplpy` import at module import time | tests green with AMPL absent |

## 9. Work packages

Gate: each package is reviewed (code line rules: worktree, own branch, tests first, independent reviewer) before the next starts. GOAL 1 first. WP-E10 runs before WP-E4.

| WP | Scope | Files | Tests | Acceptance | Risk | Effort |
|---|---|---|---|---|---|---|
| WP-E0 | Wave instance contract + archive loader (offline) + peak-wave list (D-B) | `uniride_core/exact/wave_instance.py`, `scripts/exact_archive_loader.py` | loader on all valid campaigns; class cross-check; matrix sha check; arcs integer and >= 0; invalid campaigns refused; peak-wave list | all 57 waves x 4 R loaded (226 legs per R); counts equal archived; peak waves = the five 08:45 pickup waves (F18), same for every R and fleet | low | 0.5 d |
| WP-E1 | Route enumeration (single + typed, both directions, revisits, multiplicity columns, count caps) + brute-force oracle | `route_enumeration.py`, `brute_force.py` | oracle, dominance, nonmetric revisit, missing arc, clique floor | 500 instances identical; column and label counts logged for all archived waves; the label-cap value is fixed from the measured counts, written into this design (§1.1) and the manifest, and reviewed before WP-E2 starts | medium (column explosion on the 20-student wave at R = 90) | 1.5 d |
| WP-E2 | AMPL backend + `wave_sp.mod`, two stages, bounds, stop reasons, environment lookup, graceful absence; `exact_reference_v1` protocol and manifest schema in `academic_benchmark/exact_reference/protocol.py`; work-limit calibration | `ampl_backend.py`, `models/wave_sp.mod`, `requirements-exact.txt`, `protocol.py` | `requires_ampl` SP vs oracle (Gurobi, HiGHS); absence test; option/suffix confirmation (F17) | equal optima; `backend_unavailable` without AMPL; wall limit not binding on the calibration set | medium (driver option names, bound suffix) | 1.5 d |
| WP-E3 | Certification bridge + GOAL 1 runner, single type (limits per EQ1/D-C: 60 s per solver call, 600 s per call on a peak wave) | `scripts/run_exact_wave_gaps.py` | GA re-certification; exact certification; objective cross-check; exact <= GA | full grid (5 days x 4 R) for 4/5 fleet, all waves labelled, manifest complete | low | 1 d |
| WP-E10 | **Fleet campaign re-run** (owner decision D-A): both EQ2 fleets (large+sedan, large+Doblò cap3) at a pinned commit, GA seed 42, native termination, same labels, CLI fleet types and grid as the archive; extended archive format; read-only input preflight (rules below) | archive writer and schemas: `scripts/run-fleet-scenarios.ts:88-170`, `src/services/fleet-scenario-report.ts` (`fleetManifestSchema`, run records), `src/services/fleet-scenario-run.ts` (`MenuOptionRecord`/`MenuWaveRecord` at :136-150, menu builder); the preflight; their tests; new results directories next to the old ones. Optimisation logic unchanged. | archive-schema test (every option has routes, minutes, intervals and a certificate); preflight refusal tests (sha mismatch, occurrence mismatch, fleet-type mismatch, dirty tree, configuration mismatch); old archives untouched | (a)-(g) below all hold | medium (TS code path, live inputs, long run) | 1.5 d |
| WP-E4 | Typed runner: per-option exact menus (`xbase`, `xq`) vs the WP-E10 options; day selection over GA menus and over the union menu (§1.5); TS confirmation CLI | runner extension, Python interval port, `scripts/verify-typed-selection.ts` | quota respected; typed certificate; option comparison; interval parity with WP-E10; replay acceptance (below); union rule of §8 | large+sedan and large+Doblò(cap3) grids complete; **replay acceptance:** the Python recomputation over the GA menus reproduces the WP-E10 archived selection response for every (date, R, L): status, cars, large peak, car-minutes, total minutes and the selection with its labels; union rows labelled `proven_over_union_menu` or `union_not_proven` | medium | 1.5 d |
| WP-E5 | Compact fallback model | `models/wave_compact.mod` | compact vs SP on n <= 12 and the nonmetric revisit instance | equal optima; invoked only on a count cap | medium (weak bounds) | 1 d |
| WP-E6 | Gap report: tables + figure + paper method paragraph (via the writing line) | `scripts/plan_exact_gap_report.py`, `docs/paper/results/week-2026-10-05-exact/` | CSV schema test; recomputation of sums | §9 deliverable below | low | 1 d |
| WP-E7 | GOAL 2: `tsp_dfj.mod`/`tsp_mtz.mod` + cut loop; TSPLIB reproduction. Starts only after EQ6 is decided. | `uniride_core/exact/tsp.py`, models | distance-convention assertion; correctness verification subset (TSPLIB n <= 100 with published optima, not the paper instance set); ft53 | 16 published optima n <= 100 and ft53 all bracketed or proven | medium | 2 d |
| WP-E8 | GOAL 2: `exact_reference_v1` protocol runner in `academic_benchmark` (reusing `protocol.py` from WP-E2), validation, gap columns. Starts only after EQ6 is decided. Belongs to ACADEMIC_STUDY_UNIFICATION gate 3 (Package C, catalog/experiment services); gates 1-2 (Packages A-B) must have passed first (AGENTS.md work-package discipline). | `academic_benchmark/exact_reference/` | protocol separation (no pooling), validator reuse | rows validated; fixed-budget tables unchanged | medium (protocol plumbing) | 2 d |
| WP-E9 | GOAL 2: CVRP two-index + capacity cuts. Starts only after EQ6 is decided. | `cvrp_two_index.mod` | small CVRPLIB optima | measured exact range documented | high (weak bounds) | 2 d |

**WP-E10 input rule and acceptance.**

- *Input source (lead decision 2026-10-10).* The campaign reads demand from the live DB (`loadDailyPlanDemand`, `fleet-scenario-run.ts:276`), and `/optimize` loads its matrix from the live DB and refuses any request whose `expected_matrix_sha256` differs from the live snapshot or whose snapshot source is not `supabase` (`optimizer_api/routers/optimization.py:198-208, 240-252`). Fleet types are CLI parameters and the DB `vehicles` table is not consulted (`fleet-scenario-run.ts:38-39`; manifests `db_vehicles_consulted: false`), so a DB `seating_capacity` change (X01) cannot enter the run; the preflight still compares the CLI `fleet_types` with the old manifests. **Decision:** a read-only preflight compares the live inputs with the archive before any solve. If they match, the re-run uses the live DB. If they do not match, the run **stops and the owner is asked**; there is no replay from archived inputs. Justification: a replay through the same production code path is not possible today, because `/optimize` accepts only the live, sha-bound DB matrix; a replay would need a new matrix-injection path in production code, which is a different code path that needs its own design and review and could not serve as the reproducibility anchor (d). Inputs are never mixed: one run uses one live snapshot for every (date, R).
- (a) *Same inputs.* Abort unless every captured matrix declares sha256 `bfb2dd85…` and the occurrence ids per wave equal the archive (57 waves, 226 legs, F11); abort unless the CLI `fleet_types` equal the old manifests (large 4/5/cd 10; sedan 0/4/cd 10; minivan 1/3/cd 10/`totalCapacity` 3).
- (b) *Clean pinned tree.* `dirty_working_tree: false` at a pinned commit (all three old manifests were dirty, F14).
- (c) *Same GA behaviour.* `ga_effective_configuration` and `hf_effective_configuration` identical to the old fleet manifests (`population_size` 50, `max_iterations` 100, `crossover_rate` 0.85, `mutation_rate` 0.2, `elite_count` 3, `tournament_size` 4, `max_no_improvement` 25, `local_search_type` `hybrid`, `local_search_interval` 10, `diversify_threshold` 30), effective seeds 42; `selection_time_limit_seconds` 30 and `node_budget` 200 000 as before.
- (d) *Reproducibility anchor.* For every (date, R), the re-run `base` routes equal the 4sw5so archive routes (stop order, arc minutes, occurrence ids). This already holds between the two old archives: all 20 (date, R) cells of `week-2026-10-05-fleet/*_A.response.json` equal the 4sw5so routes (2026-10-05 R90: 17 routes), checked 2026-10-10. The baseline is `ga_split`, which CX-03 does not change (H04). The report also counts how many archived **selected** q-options are identical in the re-run; every difference is explained.
- (e) *Determinism.* One full day is run twice; all option routes are byte-identical.
- (f) *Extended archive.* Per (date, R): every menu option (`base`, `q0..qQ`) with its routes, stop order, `student_ids`, minutes, intervals and the certificate from `reply.result.feasibility_certificate` (`fleet-scenario-run.ts:177, 339-345`). Per (date, R, L): the exact `/internal/fleet-selection` request body and its response.
- (g) *History.* The old archives are untouched and labelled historical; they are never pooled with re-run rows. Manifests record the commit, `dirty_working_tree: false`, `termination_protocol`, seeds and configurations.

**Paper deliverable (WP-E6).** Results directory `docs/paper/results/week-2026-10-05-exact/` with README, manifest, and:

- `wave_gaps.csv`: date, R, fleet (`single_4sw5so`, `large+sedan`, `large+doblo_cap3`), option (`base`/`q`), quota, wave id, direction, anchor, students, peak flag, model (SP/compact), columns, `K_GA`, `K_LB`, `K*`, `D_GA`, `D_LB`, `D*`, `D_LB_free`, `dK`, `gD`, `gD_free`, status, `stop_reason`, `timing_dependent` and `non_lexicographic` per stage, solver, runtime; GA labels `ga_protocol` (`native`, from the source manifest), `ga_seed` (42), `ga_commit` and `ga_dirty_tree`. For the single type these come from the 4sw5so manifest (`6be127d`, dirty, F14); for the typed fleets from the WP-E10 re-run manifest. Archived typed rows, if shown at all, are labelled historical and kept in a separate file;
- `day_gaps.csv`: per (date, R, fleet) sums and `dK_day`, `gD_day`, excluded waves, plus, for the typed fleets, cars over the GA menus and cars over the union menu with its label (`proven_over_union_menu`, `union_not_proven`, `not_independently_confirmed`) and both CP-SAT statuses, at one commit and `time_scale = 100`; never `min(GA, union)`;
- Table: per R, the share of waves with `dK = 0`, mean and max `gD`, and statuses; Figure: per-wave `gD` (y) against students per wave (x), one panel per R, marker by `dK`.
- Paper text carries a short note on the HiGHS cross-check; the details go in the archive (owner decision EQ4).
- Wording rule: a single snapshot week; descriptive gap measurement, not a superiority claim; GA seed 42 single run under the native secondary protocol (the gap is of that run, not of the GA in general).

## 10. Owner decisions (2026-10-09, 2026-10-10)

The owner approved the lead's recommendations on 2026-10-09 ("Onaylıyorum"), with the values below, and added D-A, D-B and D-C on 2026-10-10.

| # | Question | Decision | Status |
|---|---|---|---|
| EQ1 | Time and work limits (GOAL 1)? | 60 s wall limit, 600 s on peak waves; deterministic work limit and 1 thread unchanged (§4). Scope per solver call: see D-C. Peak wave: see D-B. | Decided |
| EQ2 | Which typed fleets enter the paper table? | Both: large+sedan and large+Doblò (cap3) | Decided |
| EQ3 | Is "exact per wave, day = CP-SAT over menus" sufficient? | Sufficient for now; a global day-level model is out of scope. | Decided |
| EQ4 | Report HiGHS cross-check results in the paper or only in the archive? | The paper carries a short note on the HiGHS cross-check; details go in the archive | Decided |
| EQ5 | GA repeats: the archived GA is one seed (42). | GA at seed 42 now, labelled single-seed; a multi-seed gap measurement comes later | Decided; multi-seed later |
| EQ6 | GOAL 2 instance set and time limit | Deferred to a later decision; GOAL 2 stays planned (§5) but is not parameterised yet. WP-E7, WP-E8 and WP-E9 start only after EQ6 is decided. | Open / deferred |
| D-A | How is the GA side of the typed comparison obtained, given that the fleet archives hold option counts only (F10) and predate CX-01/CX-03 (F14)? | Re-run the fleet campaigns at the current commit (GA seed 42, the same native protocol and labels as the archive) and archive every menu option's routes, minutes and certificates (base + q = 0..L) for both typed fleets (EQ2). The GA-vs-exact comparison uses only this re-run, at one commit and `time_scale = 100`. The old archives stay as historical evidence and are not pooled. Work package WP-E10, before WP-E4, in the code pipeline. | Decided 2026-10-10 |
| D-B | Peak-wave definition | For each service date, the wave(s) with the largest number of legs (all tied waves included), computed by the WP-E0 loader from the archive before any solve, identical across R and fleets, and listed in the manifest. Currently the five 08:45 pickup waves (20/11/11/10/13 legs, F18). | Decided 2026-10-10 |
| D-C | Scope of the 60 s / 600 s wall limit | Per solver call: stage 1, stage 2 and `D_LB_free` each get their own limit. | Decided 2026-10-10 |

**Lead decisions (not owner decisions), 2026-10-10:**

- The day level runs over the union of the GA and per-wave exact menus with an exact `xbase` option (review fix B4; §1.5), under the dedupe and proof rules of §1.5 (review fixes N2, N3).
- WP-E10 input rule: live DB only if the read-only preflight matches the archive; otherwise stop and ask the owner, no replay (§9, review N1).
