# Global joint day model (WP-E11): design

Status: **approved by the owner on 2026-10-20 (DECISION_LOG E14); implemented and run, J11 results merged at `a5885234` (status paragraph in §0).** Design date: 2026-10-20. Design addendum to [`EXACT_SOLVER_AMPL_DESIGN.md`](EXACT_SOLVER_AMPL_DESIGN.md) (cited below as "exact design"), written after DECISION_LOG **E13** reopened EQ3. Implementation plan: [`docs/superpowers/plans/2026-10-20-wp-e11-joint-day-model.md`](../superpowers/plans/2026-10-20-wp-e11-joint-day-model.md).

Binding context: `AGENTS.md` (core vs academic ownership, protocols never pooled, file/line evidence); DECISION_LOG E01-E13, H01, H03, H05, H06, A04, A13, A14 (nothing here reopens a decided question other than the EQ3 part that E13 reopened); exact design §0 (facts F1-F18), §1.1-§1.5, §3, §4, §8, §9.

Labels used below: **[fact]** = checked in source or committed results on 2026-10-20 at `f8aaff1b`, with file:line; **[prototype]** = read from the Claude Science prototype on the local branch `docs/science-review-2026-10` (commit `74f28f5e`), treated as data, not as verified truth; **[proposal]** = this design's choice, open for owner approval; **[assumption]** = not yet checked, to be measured by a plan item.

## 0. Why, and what is new

- [fact] WP-E3 proves the wave optimum (K*, D*) on all 228 single-type (wave, R) rows (exact design WP-E3 status paragraph); WP-E4b selects one option per wave over the union of GA and per-wave exact menus and claims only "minimum cars over the union ... not a global day optimum" (`uniride_core/planning/union_day_menu.py:32`, exact design §1.5).
- [fact] The day objective works on route busy intervals and their peak concurrency, not on (K, D) per wave (`uniride_core/planning/typed_day_selection.py:6-22`). A wave-optimal route set can therefore be a poor day choice: a longer or extra route in one wave can free a vehicle for another wave.
- [prototype] The comparison report `docs/science_review/2026-10-19_cs_cc_karsilastirma/CS_CC_228_DALGA_KARSILASTIRMA_2026-10-19.md` §3-§4 found, with a joint model over all enumerated routes: homogeneous weekly fleet 6 → 5 at R = 60 and 70, vehicle-days 94 → 83, one sedan fewer than the union menu in 12 of 60 large+sedan cells, and feasible plans in two cells our menus label infeasible. These are the motivation and the reproduction targets (§6.3), not results.

WP-E11 brings this model into `uniride_core`, with proofs, an independent checker and a separate protocol.

**WP-E11 status (2026-10-22; J11 results merged at `a5885234`).** The model, runner, checker and the J10 and J11 results are merged. The J11 record is `docs/paper/results/week-2026-10-05-exact/wp-e11-joint-day/`: one clean serial run of `scripts/run_exact_day_joint.py --work-limit 200` at code commit `e45cd6bf`, 140 cells (`single_4sw5so` 20, large+sedan 60, large+Doblò cap3 60), HiGHS primary, Gurobi through AMPL as cross-check, 600 s per solver call. It was the third attempt at that commit; attempts 1 and 2 stopped with `backend_unavailable` (Gurobi licence) and wrote nothing. Labels: 114 `optimal`, 15 `infeasible_certified`, 11 `infeasible_solver_proven`. All 140 cells carry a proof claim (125 two-solver day agreements, 8 tier-1 and 7 tier-2 certificates). Blocking defects: 0. Reproduction categories (§6.3): 79 `equal`, 1 `prototype_open` (large+sedan 2026-10-05 R90 L2, where production proves S = 2), 60 `no_external_target`. The first run (code `f77c2484`, results `2ea2c5a2`) is superseded and not pooled. The rerun has the same label, value, plan and MPS sha256 in all 140 cells. It differs from the first run in the proof claim of the Doblò cell 2026-10-08 R50 L2 (withheld in the first run because of an integrality-test defect fixed before the rerun; its Gurobi stage 3 is now accepted), and in the raw Gurobi `bound` column of 113 further cells (`bound_ceil` unchanged in those). Open after this merge: the licence-retry change of the runner (decided in E14, on a separate branch, not merged), a README pointer to `scripts/compare_exact_day_joint_runs.py`, and the paper and method wording through the writing line.

## 1. Problem

### 1.1 Scope

One **cell** is (fleet, service date, R) for the homogeneous fleet and (fleet, service date, R, L) for a typed fleet. The grid is the one of WP-E3/WP-E4: the week of 2026-10-05, five dates, R ∈ {50, 60, 70, 90}, T = 150.

| Fleet | Types (source) | Fixed / minimised | Decision | Cells |
|---|---|---|---|---|
| `single_4sw5so` | one type 4 Sw / 5 So, cooldown 10 (4sw5so archive, `scripts/exact_archive_loader.py:24-28`) | — | minimise K, the day fleet | 20 |
| `large+sedan` | large 4/5, sedan 0/4, cooldown 10 (WP-E10 re-run, `exact_archive_loader.py:31-34`; H01) | large fixed at most L, sedans minimised | minimise S for L ∈ {1, 2, 3} | 60 |
| `large+doblo_cap3` | large 4/5, Doblò 1/3 with `total_capacity` 3, cooldown 10 (WP-E10 re-run; H03) | large at most L, Doblòs minimised | minimise S for L ∈ {0, 1, 2} | 60 |

[fact] The L ranges are the WP-E4b ranges (exact design F6 and WP-E4b status: 120 typed cells). [fact] The prototype did not solve Doblò cap3 (report §5, row "Gün düzeyi kapsamı"); E13 puts it in scope.

### 1.2 Day plan semantics (identical to production)

A **day plan** chooses, for every wave of the date, a set of routes that covers each occurrence of the wave exactly once, and assigns each route a vehicle type that accepts it.

1. **Route.** `depot -> s1..sk -> depot`, no waiting; pickup ride = tour minus its first arc, dropoff ride = tour minus its closing arc; tour <= T_t, ride <= R_t, Sw <= sw_t, So <= so_t and, when set, Sw + So <= total_t; missing arcs are infeasible [fact: exact design F1-F4; `uniride_core/planning/fleet_selection_request.py:91-111`].
2. **Anchoring.** A pickup route ends at the wave anchor a and starts `a - tour`; a dropoff route starts at a and ends `a + tour` [fact: `scripts/run_exact_union_day.py:173-174`; `src/services/typed-selection-verify.ts:131-132`]. A route that starts before minute 0 or ends after minute 1440 is not a valid option [fact: `run_exact_union_day.py:68, 175-176`; `typed-selection-verify.ts:26, 134`].
3. **Busy-interval rule.** A vehicle of type t that serves a route is busy on the half-open interval `[start, end + cooldown_t)`, cooldown 10 minutes [fact: `typed_day_selection.py:11-12, 96, 188-192`; router default `fleet_selection_request.py:32, 160-162`].
4. **Fleet.** Routes of one type form an interval graph, so the vehicles of that type needed equal the peak number of simultaneously busy intervals, and it is enough to bound the load at every interval start [fact: `typed_day_selection.py:12-14, 87-92, 188-196`]. All routes start and end at the campus depot (F1), so a vehicle can take any later route once its cooldown has passed.
5. **Grid.** Production builds intervals in centi-minutes (`time_scale = 100`), with `end = max(start + 1, centi(end))` and a refusal for values off the grid [fact: `fleet_selection_request.py:29, 83-88, 137`]. All archived arcs are non-negative integers (F15), so every interval endpoint is an integer minute and the integer-minute model of §2 is exact on that grid. The independent checker (§5.1) recomputes the peaks at `time_scale = 100` as well.

### 1.3 Decisions and objectives

**Homogeneous (`single_4sw5so`).** K = peak concurrency of all routes. [proposal, owner question Q2] Lexicographic, one solver stage each:

1. minimise K;
2. minimise total vehicle-minutes `D = sum of route tours` with K fixed.

The route count is reported, not optimised. Reason: H06 ranks total vehicle-minutes directly after the vehicle count at day level (DECISION_LOG H06; `typed_day_selection.py:204-205`); at day level a route has no cost of its own beyond its minutes. [prototype] The prototype ranks K, then total routes, then minutes (`docs/science-review-2026-10:.../src/run_day_joint.py:2-4, 52, 57, 62`); K and the fleet targets do not depend on this choice, the minute targets do (§6.3).

**Typed.** The large type is fixed with peak <= L; the minimised type's peak is S. [proposal] Lexicographic, consistent with H06 where it applies:

1. minimise S (cars);
2. minimise total vehicle-minutes with S fixed;
3. minimise car-minutes with S and total minutes fixed.

H06's fourth key (sum of option indices, `typed_day_selection.py:203-205`) has no counterpart, because the joint model has no menu. Remaining ties are co-optimal alternatives; results are compared on the objective tuple, never on route identity (§5.4). The achieved large peak is reported, as `DaySelectionResult.large_peak` does (`typed_day_selection.py:78, 283`). [prototype] The prototype minimises S, then minutes, with large peak <= L (`run_day_typed.py:2-6, 55, 64`).

**Stage 1 not proven.** As exact design §1.1: if stage 1 ends with an incumbent but no proof, later stages run with the stage-1 incumbent value fixed, the row is `non_lexicographic: true`, and later-stage bounds are not reported as conditional lower bounds. If stage 1 has no incumbent, later stages are skipped.

## 2. Formulation

### 2.1 Column source

[fact] For each wave of the cell, the columns are the complete output of `enumerate_routes` (`uniride_core/exact/route_enumeration.py:165-321`) with the cell's types, R and T: one column per feasible ((location, class) multiset, type), carrying the type, the multiplicity vector, the stop order and `cost = tour` in integer minutes (`route_enumeration.py:73-80`). The kept order of each (multiset, type) minimises (tour, ride, end stop) in that order (`route_enumeration.py:247-264`). These are the same candidate routes as WP-E3/WP-E4a; the comparison report §2 found the single-type counts identical in both implementations (83 008 over the 228 (wave, R) rows), and the WP-E1 counts reproduce that total (3 717 + 8 838 + 18 497 + 51 956 at R = 50, 60, 70, 90; `docs/paper/results/week-2026-10-05-exact/wp-e1-enumeration/enumeration_counts.csv`).

A cell is modelled only if **every** wave of the date enumerated with status `complete` (`route_enumeration.py:41, 321`). Otherwise the cell is `not_run_enumeration_cap` and no day claim is made (E11: no compact fallback).

[fact] Typed enumerations take all types in one call and emit one column per (multiset, type) admitted by that type (`route_enumeration.py:202-207, 256-264`); a route both types accept appears as two columns, so the model chooses the route's type by choosing the column.

### 2.2 Exactness argument

Every feasible day plan of §1.2 maps to a feasible solution of the model with an objective vector that is no worse in any component: replace each route by the column of its (multiset, type). That column's tour is not longer (§2.1), so its busy interval is a subset of the route's interval (pickup: same end, later or equal start; dropoff: same start, earlier or equal end); the peak of every type cannot rise, and total and car minutes cannot rise. The service-day filter is monotone in the same way (a shorter tour cannot leave the day). Hence, **if every wave enumerated completely, the model optimum is the global day optimum under the semantics of §1.2**. This is the claim the joint rows may make; it is never made for a cell with an incomplete enumeration or an unproven stage.

Consequence (blocking check, §5.3): where both are proven, joint cars <= union-menu cars (WP-E4b) and joint K <= the peak of any archived route set of the same day, because every certified menu route is dominated by a column of its multiset and type.

### 2.3 Sets and data

- Waves `w in W` of the date; items `i in I_w` = (location, class) with multiplicity `n_wi`; anchor `a_w`; direction.
- Columns `c in C_w` after the service-day filter (the filtered count is reported): type `t_c`, multiplicities `a_ci`, tour `tau_c`, busy interval `B_c = [s_c, e_c + cd_{t_c})` with `(s_c, e_c) = (a_w - tau_c, a_w)` for pickup and `(a_w, a_w + tau_c)` for dropoff.
- Types: homogeneous `{f}`; typed `{l, m}` (l = fixed large type, m = minimised type).
- Event points `P_t = { s_c : t_c = t }`.

### 2.4 Variables and constraints

```text
lambda_c  integer, 0 <= lambda_c <= u_c,  u_c = min over i with a_ci > 0 of floor(n_wi / a_ci)   (E02)
K or S    integer >= 0

cover:        sum_{c in C_w} a_ci lambda_c = n_wi                       for all w, i in I_w
concurrency:  sum_{c: t_c = t, s_c <= p < e_c + cd_t} lambda_c <= Cap_t  for all t, p in P_t
              Cap_f = K (homogeneous);  Cap_l = L (constant);  Cap_m = S
optional:     S <= max_cars                                             (only if the source request sets max_cars)
```

`lambda_c` is integer, not binary, for the reason of E02: one column per multiset can be needed twice in a wave. Each copy has the same interval, so the concurrency rows stay linear. After the solve, columns are expanded to occurrence ids with `expand_selection` (`uniride_core/exact/ampl_backend.py:282`), per wave, exactly as WP-E2 does.

Objective stages (§1.3): stage 1 `min K` or `min S`; stage 2 `min sum tau_c lambda_c` with stage 1 fixed; typed stage 3 `min sum_{t_c = m} tau_c lambda_c` with stages 1-2 fixed. All coefficients are integers.

[proposal] **Duration aggregation** (an exact reformulation, to keep the matrix small): for each (w, t, tau) add `z_{w,t,tau} = sum_{c in C_w: t_c = t, tau_c = tau} lambda_c` and write the concurrency rows over `z`. Columns of one wave, type and tour have the same interval, so the model is unchanged; the number of concurrency nonzeros falls from one per (column, covered point) to one per (wave, type, tour, covered point). The red test is equality of the optimum with and without aggregation on the oracle instances (§5.2).

[proposal] No lower bound of §3 is added to the model. The solver's proof then depends on nothing outside the model; the bounds are used only for labels (§4.3).

### 2.5 Instance size (this week)

[fact, from `wp-e1-enumeration/enumeration_counts.csv`] The largest day is 2026-10-05 at R = 90 for every fleet: 45 302 columns (single type), 47 215 (large+sedan), 46 571 (large+Doblò cap3), 54 cover items; the 20-leg 08:45 pickup wave alone has 45 170 / 47 027 / 46 333 columns (exact design WP-E1 status). [prototype] The prototype's homogeneous model needed 598.9 s for 2026-10-05 R = 70 and stopped without a plan at 2026-10-05 R = 90 (status `-9` as recorded), with a 900 s limit per stage (`docs/science_review/2026-10-19_cs_cc_karsilastirma/cs_cc_gun_homojen_4sw5so_20.csv`; `run_day_joint.py:31`). [assumption] Production runtimes differ (other HiGHS build, multiplicity columns, aggregation); plan item J10 measures them.

## 3. Lower bounds and certificates

### 3.1 LB0 (homogeneous)

[prototype definition, `ASTRA6_YENI_ALGORITMA_TASARIMLARI_ClaudeScience.md:508` on the prototype branch] Let `k_w` be a proven lower bound on the number of routes of wave w (the WP-E3 stage-1 optimum K*_w at the cell's R). Every route of wave w is busy at least on `J_w = [a_w, a_w + cd)`, because `B_c` contains it for both directions (§2.3). Hence

```text
LB0 = max over p in { a_w } of  sum_{w: p in J_w} k_w   <=   K*_day
```

[proposal] **LB0w** (widened, still valid): `tau_min_w` = the smallest tour among the wave's columns; every route of the wave is busy on `[a_w - tau_min_w, a_w + cd)` (pickup) or `[a_w, a_w + tau_min_w + cd)` (dropoff); LB0w is the same maximum over these intervals and their start points, and LB0w >= LB0. Both are reported; LB0 alone is used for the reproduction check (§6.3).

`k_w` is computed in the run by the wave SP stage 1 (`ampl_backend.solve_wave`, `ampl_backend.py:675`) or the HiGHS wave path of §4.1, and must equal the committed WP-E3 `K*` (`wp-e3-goal1-single/wave_gaps.csv`); a difference blocks.

### 3.2 Typed bounds and the infeasibility certificate

- `l_w` = the minimum number of large routes in any feasible route set of wave w (typed wave SP, stage 1 minimising the large type, no quota). Arithmetic floor, needing no solver: if the minimised type carries no Sw (sedan: H01), `l_w >= ceil(Sw_w / sw_large)`; for Doblò (1 Sw, H03) the floor is 0.
- `LB_L = max over p of sum_{w: p in J_w} l_w`. **Certificate:** `LB_L > L` proves that no day plan with at most L large vehicles exists.
  - Tier 1, `certificate_capacity_floor`: uses only the arithmetic floor; checkable by hand from the Sw counts and anchors.
  - Tier 2, `certificate_wave_min_large`: uses the solver-proven `l_w` (two solvers agree, as for every proven wave value).
- `k_any_w` = the minimum total number of routes of wave w over both types (one-stage wave SP). `LB_S = max(0, max over p of sum_{w: p in J_w} k_any_w - L)`; valid because at most L of the busy vehicles are large.

[fact] Production's pre-check is the per-wave, per-option analogue: `_forced_large_peak` over menu routes that no car accepts, refusing a day only when one wave alone exceeds L (`typed_day_selection.py:95-97, 150-166`). The certificate above sums concurrent waves and uses all routes, so it is stronger and menu-free. [assumption] `solve_wave`/`solve_columns` may not yet support the two wave objectives above (minimise the large type with no quota; minimise all routes on a typed enumeration); plan item J2 checks this and adds the smallest needed option, under the WP-E2 oracle tests.

[prototype] The open cell 2026-10-05 R = 90 L = 2 was bracketed by the prototype as S in {1, 2} with "LB 1 (homogeneous min fleet 3 > L)" (`cs_cc_gun_tipli_large_sedan_60.csv`), which is the `LB_S` idea with the homogeneous day fleet in place of the per-wave sums.

## 4. Solvers and protocol

### 4.1 Solvers

- [fact] `.venv-jit` has `amplpy` 0.18.0 and `ortools` 9.15.6755, but neither `scipy` nor `highspy` nor `gurobipy` (`pip list`, 2026-10-20). HiGHS 1.15.1 and Gurobi 13.0.3 are reachable today only through AMPL (exact design F13), whose academic licence ends 2026-11-05 (DECISION_LOG E09 "Why").
- [proposal, owner question Q4] **Primary: HiGHS through `highspy`** (open source, no licence), pinned in `requirements-exact.txt` next to `amplpy`, imported lazily. The model is built once as a solver-neutral sparse MIP (`uniride_core/exact/day_joint.py`) and written as a canonical MPS file whose sha256 enters the manifest. **Cross-check: Gurobi** on the same MPS file (through `gurobipy` if the owner's licence, valid to about 2027-10, covers it; otherwise through AMPL while its licence lasts). Identical model bytes on both solvers is the strongest cross-check.
- Disagreement between two solvers on a proven optimal value or a proven infeasibility is a blocking defect (exact design §6).

### 4.2 Limits and determinism

- [proposal, owner question Q3] **600 s wall time per solver call** (each stage is one call, D-C). Reason: under D-B every service date has a peak wave and every day model contains it, so the peak limit of E01/D-C applies to every day call; E10 applies the 600 s budget per solver as well. Gurobi gets a deterministic work limit; its value is set from the J10 calibration (WP-E2 practice; the wave value 200 per peak call, E03, is the starting point). HiGHS has no work limit, so its time-limited rows are always `timing_dependent: true`.
- threads = 1, seed 0, MIP relative gap 0 and absolute gap 0.99 (integer objectives), as in `ampl_backend.py:41-53`; a stage is `optimal` only if `incumbent <= ceil(bound - 1e-6)` holds in the runner's own check. The exact option strings are stored verbatim.
- Determinism check: five cells solved twice give identical stage values and statuses (exact design §8 "Determinism").

### 4.3 Protocol `exact_day_joint_v1` and labels

[proposal] A new protocol id `exact_day_joint_v1` is defined in `academic_benchmark/exact_reference/protocol.py` (next to `exact_reference_v1` at `:25` and `union_day_v1` at `:243-253`) and registered in `academic_benchmark/protocol_registry.py` as its own pooling group, not rankable, no statistics (the registry table at `:1-18`; `assert_single_pooling_group` at `:96-104`). It is never pooled with `exact_reference_v1` wave rows, with `union_day_v1` (WP-E4b) rows or with heuristic rows (A04, E12).

Cell labels (`day_status`):

| Label | Meaning |
|---|---|
| `optimal` | every stage `optimal` on the primary solver; plan certified and checked (§5) |
| `optimal_stage1_by_bound` | stage-1 incumbent equals LB0, LB0w or LB_S although the solver stopped on a limit; later stages carry their own status |
| `feasible_with_gap` | certified incumbent and a bound below it; the bound reported is the best of the solver bound and §3 bounds, with its source named |
| `bound_only` | a bound, no incumbent |
| `infeasible_certified` | §3.2 certificate (tier named), independent of the day MIP |
| `infeasible_solver_proven` | the solver proves infeasibility, no certificate; the cross-check field says whether a second solver agrees |
| `not_run_enumeration_cap` | some wave of the date did not enumerate completely |
| `rejected` | certificate, checker or objective cross-check failed |
| `input_rejected` / `backend_unavailable` | as exact design §4 |

Every stage row carries `status`, `stop_reason`, `timing_dependent` and `non_lexicographic` with the meanings of exact design §4. Paper wording (E13): joint infeasibility is "no day plan exists with at most L large vehicles" only for `infeasible_certified`; `infeasible_solver_proven` is "infeasible, solver-proven"; WP-E4b's labels stay "infeasible over the menu".

## 5. Verification

### 5.1 Independent plan checker (`academic_benchmark/validation/day_plan.py`)

Separate from the solver path: standard library only, no import of `uniride_core.exact`, `uniride_core.planning` or `optimizer_api` (AST guard test, like the WP-E8 Hamiltonian validator). Inputs: the plan file, the archived per-date `*.matrix.json` slice, the archived wave definitions (anchor, direction, occurrences with location codes) and the fleet types from the source manifest. Checks:

1. coverage: every wave's occurrences are covered exactly once, and no route mixes waves;
2. per-type capacity (Sw, So, total), with the class taken from the location code and cross-checked with the archive;
3. every arc exists and is a non-negative integer;
4. tour <= T_t and ride <= R_t with the pickup/dropoff ride rule (§1.2.1);
5. anchored intervals and the service day (§1.2.2);
6. per-type peak of `[start, end + cd)` by a sweep, in integer minutes and again at `time_scale = 100` with `end = max(start + 1, ...)`: large <= L, car peak = S, homogeneous peak = K;
7. total minutes and car minutes equal the claimed values; the route count equals the claimed value.

### 5.2 Model tests (in `uniride_core/tests`)

- Day oracle: brute force over all route sets of tiny days (2-4 waves, <= 5 occurrences each, built from `brute_force.py` wave partitions) gives the same objective tuple as the model, with and without duration aggregation, for pickup and dropoff, overlapping and disjoint waves, cooldown 0 and 10, a column needed twice (E02) and a nonmetric revisit wave (F8).
- Interval parity: for every column, the model interval equals the interval `fleet_selection_request.build_selection_request` builds for the same route (`fleet_selection_request.py:134-141`), and the model peak of a fixed route set equals `typed_day_selection.peak_concurrency` (`:87-92`).
- Bound validity: LB0, LB0w, LB_L and LB_S never exceed the oracle optimum; a hand instance where LB_L > L must have no oracle solution.

### 5.3 Run checks (blocking)

- Certification of every wave's routes through `certify_optimization_response` via `uniride_core/exact/certification.py` (`response_payload :76`, `typed_response_payload :161`), as exact design §3, and the integer objective recomputation (`recompute_objective :111`, `recompute_typed_objective :204`).
- The checker of §5.1 on every plan.
- Typed fleets: the TypeScript confirmation CLI `scripts/verify-typed-selection.ts` (invoked as in `run_exact_union_day.py:69, 411`), with one synthetic option per wave holding the chosen routes and their type labels; it rebuilds intervals in TypeScript and runs `assignTypedVehicles` and `verifyTypedAssignment` (`src/services/typed-selection-verify.ts:1-20`). Homogeneous fleet: used only if the CLI accepts a single-type input (J9 checks); otherwise the checker alone, stated in the README.
- Bound consistency: a K or S below LB0, LB0w, LB_S or the solver bound, or any value below a proven optimum of the same cell, is an error, never a result.
- Joint vs menus (§2.2): where both are proven, joint S <= WP-E4b union cars, and joint K <= the peak of the archived GA routes and of the WP-E3 exact routes of that day.
- Two solvers agree on every `optimal` value and every `infeasible_solver_proven` cell used in a table (subject to Q5).

### 5.4 Co-optimal regression test

[fact] Of the 228 single-type (wave, R) rows, 7 have a different passenger grouping in the two implementations while (K*, D*) are equal (report §2; `cs_cc_dalga_karsilastirma_228.csv`, column `ayni_gruplama = False`): `2026-10-05:pickup:525` at R = 50 and R = 90, `2026-10-06:dropoff:975` R = 50, `2026-10-06:pickup:525` R = 50, `2026-10-07:pickup:705` R = 70, `2026-10-08:dropoff:735` R = 50, `2026-10-09:pickup:525` R = 90. A further 12 rows have the same grouping but a different stop order (column `ayni_sirali_rotalar`).

- Location: `academic_benchmark/tests/test_coopt_alternative_route_sets.py`, with a committed fixture `academic_benchmark/tests/fixtures/coopt_waves_2026-10-19.json` holding, for these 7 rows, the prototype's route sets copied from the prototype branch (provenance: branch, commit `74f28f5e`, source path and its sha256) and the WP-E3 route sets from `wp-e3-goal1-single/exact_routes.json`.
- Assertions: both route sets of each row pass the checker of §5.1 at wave level; both recompute to the committed (K*, D*) of `wp-e3-goal1-single/wave_gaps.csv`; the comparison function used by the reproduction step returns `co_optimal_alternative` (equal (K, D), different routes), never `mismatch`. A negative case: a route set with one minute more must return `mismatch`. The day-level comparison uses the same rule on (K or S, total minutes, car minutes).

## 6. Outputs and reproduction

### 6.1 Results folder

`docs/paper/results/week-2026-10-05-exact/wp-e11-joint-day/` (covered by `.gitattributes:7`, `-text`):

| File | Content |
|---|---|
| `README.md` | scope, claim wording, labels, limits, deviations, what is not claimed |
| `day_joint_manifest.json` | protocol `exact_day_joint_v1`; code commit and dirty flag; `python_provenance`; source manifests and their sha256 (4sw5so, both WP-E10 re-runs, WP-E3, WP-E4b); solver names, versions, verbatim options, limits, threads, seed; MPS sha256 per (cell, stage); enumeration caps and per-day column counts; `run_history` (E06); sha256 of every output file |
| `day_joint.csv` | one row per cell, columns in this order (`CSV_FIELDS` of `scripts/run_exact_day_joint.py`): `fleet, date, R, L, waves, legs, columns, columns_outside_day, day_status, K_or_S, large_peak, total_minutes, car_minutes, routes, lb0, lb0w, lb_L, lb_S, bound_used, bound_source, bound_proof, proof_claim_allowed, proof_claim_reason, reason, flags, unverified_bounds, certificate_tier, timing_dependent, non_lexicographic, crosscheck_solver, crosscheck_status, wave_values_status, checker_ok, ts_confirmation, wall_seconds, note` |
| `day_joint_stages.csv` | one row per (cell, solver, stage), columns in this order (`STAGE_FIELDS`): `fleet, date, R, L, solver, stage, status, stop_reason, objective, bound, bound_ceil, bound_source, timing_dependent, non_lexicographic, wall_seconds, work_units, solve_result, mps_sha256` (`work_units` for Gurobi only) |
| `day_joint_plans.json` | per cell and wave the chosen routes: type, ordered occurrence ids, start, end, tour |
| `day_joint_week.csv` | per (fleet, R, L), columns `fleet, R, L, dates, weekly_fleet_max, vehicle_days_sum, cells_not_proven, cells_without_value` (`WEEK_FIELDS`): weekly fleet = maximum over dates, sum of vehicle-days, cells without a proof claim, cells without a value |
| `lb0.csv` | one row per (cell, bound), columns `fleet, date, R, L, bound, value, point, contributions, wave_value_source, used_value, used_proof` (`LB_FIELDS`): LB0, LB0w, LB_L, LB_S with their argmax point and contributing waves, and the wave values (`wave_*` rows) with the value and proof tag the bounds really received |
| `comparison.csv` | descriptive, per cell: joint value; WP-E4b GA-menu and union cars with labels (typed); peaks of the archived GA routes and of the WP-E3 routes (homogeneous); never `min(...)` |
| `reproduction_check.csv` | per cell: prototype value, production value, category (§6.3) |
| `rerun_vs_first_run.csv` | only in a record that repeats an earlier run: per cell, the day-level and stage-level differences of the two runs, timing columns excluded. The J11 file was written by a scratch script recorded in the J11 README; `scripts/compare_exact_day_joint_runs.py` reproduces it byte for byte (sha256 `5ae2410ca49939eab415ac506602cbbee628c5f2c8671353717abb46ae2e83e9`) |

### 6.2 Run rules

- Offline runner `scripts/run_exact_day_joint.py`, reading only committed archives through `scripts/exact_archive_loader.py`; output-directory rule of E04.
- Clean serial run (E06): one invocation, `--jobs 1`, no cache, clean pinned commit, from a fresh short-path worktree with that worktree first on `PYTHONPATH` and the provenance check of E05 round 4 (5); a solver failure stops the run and the owner decides.
- The prototype's numbers are never inputs of the run.

### 6.3 Reproduction targets (expectations to check, not truths)

From the comparison report (§3-§4 and its CSVs):

| Target | Prototype value |
|---|---|
| Homogeneous weekly fleet, R = 50/60/70/90 | 6/5/5/4 (GA archive 6/6/6/4) |
| Homogeneous vehicle-days over 20 cells | 83 (GA 94, LB0 63) |
| large+sedan: cells with one sedan fewer than the union menu | 12 of 60 |
| 2026-10-06 R = 70 and R = 90, L = 2 | feasible, S = 2 |
| 2026-10-05 R = 90, L = 2 | open, S in {1, 2} |
| large+sedan weekly sedans at L = 3, R = 50/60/70/90 | 3/2/2/1 |
| Minutes | homogeneous +194 min over 19 cells against wave optima; large+sedan +257 min in the 12 cells |

The minute targets depend on the tie-break order (§1.3) and are compared only if the owner chooses the prototype order (Q2); otherwise production minutes are expected to be <= the prototype's at equal K or S.

Categories in `reproduction_check.csv` (`REPRODUCTION_CATEGORIES` in `academic_benchmark/exact_reference/day_compare.py`; every cell gets exactly one):

- `equal`: production and prototype have the same objective tuple, or both report the cell infeasible (production by proof).
- `co_optimal_alternative`: the objective tuples are equal and the routes differ (route identity is never compared, so the function returns this category only when its caller passes `same_routes=False`; `scripts/report_exact_day_joint.py` does not, so it writes no such row).
- `production_better`, in three cases: production's objective tuple is smaller than the prototype's; production has a value (`optimal`, `optimal_stage1_by_bound` or `feasible_with_gap`) where the prototype reports infeasibility; production proves infeasibility and the prototype's plan fails the checker. (Production proving infeasibility where the prototype also reports infeasibility is `equal`.) It is a described difference, not a blocking defect.
- `production_worse`: the prototype's tuple is smaller than production's and no blocking rule applies.
- `production_open`: production has no value or proof for the cell (`bound_only`, `not_run_enumeration_cap`, `input_rejected` or `backend_unavailable`) while the prototype has a result.
- `prototype_open`: the prototype has a target for the cell but no result, while production has a value or an infeasibility proof.
- `both_open`: production is open as above and the prototype is open too (E14, J9b owner decision); it counts as neither agreement nor disagreement.
- `no_external_target`: the fleet has no prototype target at all (large + Doblò cap3, E14 Q1); it says nothing about production and keeps the rule that every cell has a reproduction row.

**If production disagrees with the prototype:** report it in `reproduction_check.csv` and the README; never change limits, options or the model to approach a prototype number. Run the checker of §5.1 on the prototype plan of that cell (data copied with provenance). If the prototype plan passes the checker and is better than a production value labelled `optimal`, that is a **blocking defect** in production (a checked plan cannot beat a proven optimum). If production is better than a prototype "optimal", the prototype claim is wrong or its semantics differ; the difference is described, not blocking.

### 6.4 Paper use

A separate methodological contribution (second paper, E13): the day level with joint route choice. The joint rows are never pooled with WP-E4b `union_day_v1` rows or with wave rows; a table that shows both names both protocols in separate columns. Single snapshot week, GA seed 42 single run, descriptive comparison; no superiority, causality or generality claim (AGENTS.md). Paper text goes through the writing line.

## 7. Scaling note

- The day model exists only where every wave enumerates completely. [fact, E11 and `scaling-probe-enumeration/summary.md`] Complete enumeration reached 80 students per wave at R = 50 and about 30 at R = 70 and 90 with all 26 stops (single type and both typed fleets), the label cap (5 000 000) being the binding limit; near those sizes one wave alone has 0.3-1.1 million columns.
- [assumption] The MIP, not the enumeration, binds first: this week's largest day has about 45-47 thousand columns (§2.5), and the prototype needed nearly 600 s or more on the 2026-10-05 days at R = 70 and 90. J10 measures where production stops proving within 600 s; the README states the measured frontier, not an estimate.
- Beyond either limit the model is a restricted master problem over a partial column set and gives no global claim. The upgrade path is the branch-and-price study named in E11: price columns per wave against the duals of the cover and concurrency rows; a column's reduced cost then depends on its busy interval, so pricing is a resource-constrained path problem with the interval as an extra resource.

## 8. Facts and assumptions

- **Facts (checked at `f8aaff1b`):** interval, peak and objective rules (`typed_day_selection.py`), the centi grid (`fleet_selection_request.py`), anchoring and service day (`run_exact_union_day.py`, `typed-selection-verify.ts`), column content and dominance key (`route_enumeration.py`), backend limits and options (`ampl_backend.py`), protocol ids and registry (`protocol.py`, `protocol_registry.py`), column totals (`wp-e1-enumeration`), installed packages (`.venv-jit`).
- **Prototype data (not verified here):** all values in §2.5, §3.2 and §6.3 attributed to the prototype, and the prototype formulation (`run_day_joint.py`, `run_day_typed.py` on `docs/science-review-2026-10`).
- **Assumptions to be checked by plan items:** production runtimes and the tractability frontier (J10); `solve_wave` support for the §3.2 wave objectives (J2); whether the TS CLI accepts a single-type day (J9); whether the owner's Gurobi licence covers `gurobipy` (Q4).
