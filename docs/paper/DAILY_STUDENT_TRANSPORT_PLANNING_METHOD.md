# Daily student transport planning with separate passenger capacities

[EKSİK: dated method-note review provenance file] Checked code baseline: `f7b8570`. [EKSİK: committed method-note review provenance for this baseline] The sensitivity campaign and the heterogeneous fleet and Pareto analyses were executed and archived. The exact-reference work packages for the week of 2026-10-05 (route enumeration, AMPL set partitioning, the single-type and typed gap campaigns, the union-menu day level and the gap report), the mixed-fleet GA re-run for the typed exact comparison and the joint day model (WP-E11) were executed and merged between 2026-10-15 and 2026-10-22; Section 7 reflects the repository at commit `c42a79e0`.

## 1. Problem setting

A single campus provides transport for students with weekly class timetables. For a selected service date, the corresponding weekday determines each student's first class start and last class end. An eligible student generates a pickup leg before the first class and a drop-off leg after the last class. These are separate demand occurrences: one student can contribute two daily passenger trips. Students without an applicable class are excluded from that day's timetable demand.

Passengers use two separate capacity pools: wheelchair positions (Sw) and seated positions (So). An empty seated position cannot replace a wheelchair position. Each vehicle has capacities for both types. Each route starts and ends at the campus depot, serves its assigned demand occurrences once, and respects both capacities. Occurrence identifiers distinguish passengers even when they share a physical stop.

Admission is an input to planning. A hypothetical scenario can treat pending legs as admitted while retaining cancellations. This preview is explicitly non-publishable and does not create confirmations. Operational demand and a hypothetical timetable scenario must be reported separately: their passenger sets and inferred fleet requirements can differ.

## 2. Travel-time data

Let c(i,j) denote travel time in minutes from physical location i to location j. Planning uses a stored, directed matrix derived from road-network routing. c(i,j) may differ from c(j,i). Straight-line distances and coordinate-based travel-time approximations are not used in this operational method. Missing or invalid required arcs prevent certification rather than being silently assigned zero travel time.

The matrix is not assumed to satisfy the triangle inequality. A direct campus-to-stop time is therefore not a certified lower bound on a route reaching that stop through other stops. A wave cannot be rejected solely because a direct arc exceeds its ride limit. Different passenger occurrences at one physical location may have a zero connecting hop; this does not justify zero travel between different locations.

A matrix snapshot is captured before solving. Wave requests are bound to its identity, and route verification uses the captured authoritative arc values. Experiments must record the snapshot identity and provenance. The archived analysis uses a fixed travel-time matrix, with no traffic, boarding times or driver assignment.

Current fleet selection sends centi-minute endpoints and cooldowns with `time_scale = 100`, rejecting off-grid values. T08 defers a two-decimal constraint on `time_matrix.duration_minutes` and plans integer-second Google storage, minutes derived as seconds / 60, and fleet selection with `time_scale = 60` when that integration starts. Google duration units and fractional-second handling have not been verified for the planned integration. [EKSİK: live Google response confirming the duration units and fractional-second handling] [EKSİK: pending fractional-second research report is outside the checked repository snapshot]

## 3. Demand waves and constraints

Demands are grouped by direction and exact anchor time. A pickup anchor is the first class start minus a 15-minute arrival buffer: a 09:00 class produces an 08:45 campus arrival anchor. Drop-off departure is anchored at the last class end plus a 15-minute departure buffer. Groups within the same clock hour but at different anchors remain separate waves. The current method does not solve individual passenger time windows within a wave.

For a closed route D, v1, …, vk, D, tour duration is the sum of all directed arcs, including the empty outbound or return journey. This sum must not exceed the tour cap T. Passenger ride time has a separate definition:

- Pickup: a passenger boarding at vi experiences the arc sum from vi through the remaining stops to D. The empty initial journey from D is excluded.
- Drop-off: a passenger alighting at vi experiences the arc sum from D through preceding stops to vi. The final return to D is excluded.

Every passenger ride must be at most R. These definitions include travel only; boarding time and waiting are not added in the current anchored-wave calculation. Capacity is checked separately for Sw and So. Defaults are R = 90 minutes and T = 150 minutes, with selectable ranges of 15–240 and 30–300 minutes respectively. These are different service constraints.

For identical vehicles with capacities qSw and qSo, a wave containing nSw and nSo passengers has the necessary seat-capacity floor

**Lseat = max(⌈nSw / qSw⌉, ⌈nSo / qSo⌉).**

This floor ignores ride limits, tour limits, and inter-wave reuse. It is a minimum imposed by seats, not the number of feasible routes or a proof of the minimum daily fleet. Its maximum across the day's waves is also a necessary daily lower bound.

## 4. Solution method

### 4.1 Route-first, cluster-second search

Each wave uses a genetic algorithm (GA) over a permutation of passenger occurrences, called a giant tour. A split decoder partitions consecutive subsequences into depot-closed vehicle routes. This follows the route-first, cluster-second representation associated with [Prins (2004)](https://doi.org/10.1016/S0305-0548(03)00158-8). The present implementation has its own constraints and acceptance checks; no comparative performance claim is inferred from the reference.

Initialization combines randomized permutations and a nearest-neighbour tour. Tournament selection, order crossover, mutation, and elitism generate new candidates. Periodic local search modifies a selected giant tour, which is then decoded and evaluated again. The outer ranking prioritizes feasibility, then route count, then total travel time.

The decoder enumerates feasible contiguous segments under both passenger capacities and the tour and ride limits. Dynamic programming chooses a minimum-travel-time partition for a fixed permutation, preferring partitions without violations. This restricted calculation does not optimize all permutations, and its cost objective differs from the outer GA's route-count priority. Neither a decoded partition nor the final wave result proves globally minimum route count. With nonmetric travel, a duration violation also does not imply that every longer segment violates the limit; alternatives must still be examined.

The single-type daily planner selects `ga_split` and supplies no per-request algorithm configuration; the heterogeneous campaign additionally calls `ga_split_hf` to build quota options. The following are the strategy's declared defaults.

| Parameter | Declared default | Interpretation | Source |
|---|---:|---|---|
| Population size | 50 | Candidate giant tours | |
| Maximum generations | 100 | Upper limit; early stopping can intervene | |
| Crossover probability | 0.85 | Applied when generating offspring | |
| Mutation probability | 0.20 | Applied to each offspring | |
| Elite count | 3 | Retained candidates | |
| Tournament size | 4 | Selection sample | |
| Local search | Hybrid | Education of a selected giant tour | |
| Local-search interval | 10 generations | Checked at zero-based indices 0, 10, … | |
| No-improvement stop | 25 generations | Consecutive lack of improvement | |
| Diversification threshold | 30 stagnant generations | Configured, but unreachable under the preceding default stop | |
| Seed setting | None | Seed helper resolves this to effective seed 42 | |

The constructor can overlay promoted parameters on the defaults. [EKSİK: method-note deployment-inspection record] The sensitivity manifest records a locally resolved effective configuration equal to the defaults above and an effective seed of 42, with the qualification that the optimizer must use the same checkout and environment. An absent or None seed resolves to 42. A fixed seed alone does not establish reproducibility when demand ordering, matrix data or configuration changes; those inputs must also be archived.

The defaults were not demonstrated to be tuned for this campus problem. Correctness and feasibility tests do not establish solution quality or comparative superiority. Current termination uses iterations and stagnation; it is not a fixed objective-evaluation-budget experiment.

### 4.2 Independent certification

An independent certificate reconstructs every route using the captured matrix. It checks required occurrence coverage, continuity, depot closure, passenger counts and capacities, tour duration, and direction-specific ride limits. A 0.005-minute tolerance per reported arc accommodates two-decimal formatting, with corresponding aggregate formatting checks; it is not extra operational ride allowance. Solver-reported durations alone do not establish feasibility. The preview also checks whether accepted output can form consistent daily route jobs.

Only accepted routes proceed to vehicle assignment. A failed certificate establishes that the returned candidate is unacceptable. Failure to generate a candidate or exhaustion of a search budget does not prove that no feasible routing exists. A feasibility certificate is not an optimality certificate.

### 4.3 Vehicle reuse across waves

A pickup route with duration t and arrival anchor a becomes the interval [a−t, a]; a drop-off route becomes [a, a+t]. Intervals outside the service day are rejected. A vehicle can serve multiple routes if both capacity pools suffice and each next route starts no earlier than the preceding route's end plus its cooldown.

Daily assignment searches for the fewest distinct vehicles for these fixed route jobs. It explores assignments in time order, uses concurrency lower bounds, and avoids equivalent branches for vehicles with matching capacities, cooldowns, and availability. The default budget is 50,000 visited nodes. A completed search, or a feasible witness meeting a valid lower bound, can prove the minimum for the given routes. If the budget is exhausted before proof, the result is indeterminate; an available witness gives only an upper bound. Completed failure establishes a shortage for the fixed routes and candidate fleet, not for every alternative routing.

For identical virtual vehicles this provides a conditional fleet minimum after heuristic routing. It is not a joint minimum over all possible routes; the separate day-level exact model is reported in §7 (Joint day model, WP-E11). Comparing its count with a heterogeneous real fleet's vehicle count is insufficient: physical capacities, cooldowns, and assignment feasibility require separate evidence.

## 5. Planning workflow

The planner selects the service date, admission scenario, ride cap, tour cap, and fleet mode, then inspects the routes and fleet requirement. The fleet template is supplied as a parameter; this study uses the physical minibus layout, 4 Sw + 5 So, with a 10-minute cooldown. Template capacities are effective scenario inputs, although the current planning screen does not expose them as freely editable parameters.

Results include waves, routes, longest passenger ride, capacity floors, and assignment status. A proven minimum, an unproven witness, and a shortage have different meanings. Re-running with different limits supports exploring service-level trade-offs. Vehicles above the seat floor can be associated with routing constraints, overlap, or cooldown, but the observed gap does not measure each cause.

Mean passenger ride is recorded in the archived study CSVs, although it is absent from the planning view's route fields. It is computed from each admitted occurrence's cumulative travel time and weighted by passenger trips, rather than by route maxima. Students, daily legs, routes and vehicles remain distinct quantities.

## 6. Sensitivity experiment

The executed sensitivity campaign crossed five weekdays with R ∈ {50, 60, 70, 90} minutes, giving 20 scenario cells, with T = 150 minutes and the 4 Sw / 5 So template with a 10-minute cooldown. Every archived response uses that template and the same declared matrix snapshot. For a future paired comparison, timetable data, admission rules, passenger ordering and the matrix must also be held fixed.

This campaign used one run per cell with effective GA seed 42 under native termination. The manifest records effective parameters, per-run files and matrix provenance; it does not turn a single-seed result into evidence about variation across seeds. Multi-seed robustness remains further study.

The archived summaries record daily vehicles V, routes K, waves W, the seat floor Lseat, gap V−Lseat, maximum and passenger-weighted mean ride, and total vehicle travel-minutes. Vehicle-minutes sum closed-route travel times and exclude cooldown; resource busy time includes cooldown. Indeterminate assignments must remain visible; witness counts must not be reported as optima, and route generation remains heuristic.

### Results: week of 2026-10-05 (4 Sw / 5 So template)

These are archived results for one snapshot week, one run per cell (GA seed 42, native termination), under assumed confirmations and the 4 Sw / 5 So template. Raw files and provenance are in [results/week-2026-10-05-4sw5so/](results/week-2026-10-05-4sw5so/). An earlier campaign used an incorrect 4 Sw / 10 So capacity record and is labelled INVALID and superseded; its result values are not used here. Every row is `preview_ready`, and V is proven only for the generated fixed routes; gap = V−Lseat.

| Weekday | R (min) | V / proof status | K (routes) | Lseat / gap | Max / mean ride (min) | Vehicle-minutes | Routes/waves (exact count ratio) | Source |
|---|---:|---|---|---|---|---|---|---|
| Monday | 50 | 6 (proven for fixed routes) | 26 | 3 / 3 | 50 / 28.314815 | 1600 | 26/12 | |
| Monday | 60 | 5 (proven for fixed routes) | 21 | 3 / 2 | 60 / 31.796296 | 1475 | 21/12 | |
| Monday | 70 | 4 (proven for fixed routes) | 17 | 3 / 1 | 70 / 36.166667 | 1355 | 17/12 | |
| Monday | 90 | 4 (proven for fixed routes) | 17 | 3 / 1 | 90 / 40.925926 | 1338 | 17/12 | |
| Tuesday | 50 | 5 (proven for fixed routes) | 22 | 2 / 3 | 50 / 26.595238 | 1334 | 22/13 | |
| Tuesday | 60 | 4 (proven for fixed routes) | 20 | 2 / 2 | 58 / 29.238095 | 1307 | 20/13 | |
| Tuesday | 70 | 4 (proven for fixed routes) | 18 | 2 / 2 | 67 / 31.761905 | 1237 | 18/13 | |
| Tuesday | 90 | 3 (proven for fixed routes) | 14 | 2 / 1 | 88 / 42.904762 | 1164 | 14/13 | |
| Wednesday | 50 | 6 (proven for fixed routes) | 20 | 2 / 4 | 50 / 28.891304 | 1302 | 20/11 | |
| Wednesday | 60 | 6 (proven for fixed routes) | 18 | 2 / 4 | 57 / 31.565217 | 1252 | 18/11 | |
| Wednesday | 70 | 6 (proven for fixed routes) | 18 | 2 / 4 | 69 / 34.652174 | 1209 | 18/11 | |
| Wednesday | 90 | 4 (proven for fixed routes) | 14 | 2 / 2 | 88 / 42.608696 | 1141 | 14/11 | |
| Thursday | 50 | 5 (proven for fixed routes) | 24 | 2 / 3 | 50 / 28.043478 | 1494 | 24/13 | |
| Thursday | 60 | 4 (proven for fixed routes) | 20 | 2 / 2 | 60 / 31.978261 | 1387 | 20/13 | |
| Thursday | 70 | 4 (proven for fixed routes) | 16 | 2 / 2 | 69 / 38.217391 | 1294 | 16/13 | |
| Thursday | 90 | 4 (proven for fixed routes) | 16 | 2 / 2 | 81 / 39.304348 | 1286 | 16/13 | |
| Friday | 50 | 6 (proven for fixed routes) | 17 | 2 / 4 | 50 / 29.078947 | 1092 | 17/8 | |
| Friday | 60 | 5 (proven for fixed routes) | 15 | 2 / 3 | 60 / 31.263158 | 1029 | 15/8 | |
| Friday | 70 | 5 (proven for fixed routes) | 13 | 2 / 3 | 65 / 31.210526 | 958 | 13/8 | |
| Friday | 90 | 4 (proven for fixed routes) | 12 | 2 / 2 | 89 / 40.710526 | 933 | 12/8 | |

Weekly fleet need is the maximum daily V over the five weekdays, for this single snapshot and native-termination run at GA seed 42.

| R (min) | Weekly fleet need | Mon | Tue | Wed | Thu | Fri | Total vehicle-minutes | Source |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 50 | 6 | 6 | 5 | 6 | 5 | 6 | 6822 | |
| 60 | 6 | 5 | 4 | 6 | 4 | 5 | 6450 | |
| 70 | 6 | 4 | 4 | 6 | 4 | 5 | 6053 | |
| 90 | 4 | 4 | 3 | 4 | 4 | 4 | 5862 | |

In this single snapshot week (one run per cell, GA seed 42, native termination), weekly fleet need was 6 vehicles at R = 50, 60 and 70 minutes and 4 at R = 90 minutes. Wednesday required 6 vehicles through R = 70 and 4 at R = 90. Weekly vehicle-minutes were 6822, 6450, 6053 and 5862 at R = 50, 60, 70 and 90, respectively. The daily mean rides, reproduced at the CSV's precision in the table, range from 26.595238 to 29.078947 minutes at R = 50, 29.238095 to 31.978261 at R = 60, 31.210526 to 38.217391 at R = 70, and 39.304348 to 42.904762 at R = 90. Daily seat floors are 2 or 3, vehicle counts are 3 to 6, and every floor gap is positive (1 to 4). The maximum ride equals R on every day at R = 50, on Monday, Thursday and Friday at R = 60, and on Monday alone at R = 70 and 90. These values describe heuristic routes under assumed admissions, and the vehicle proof is conditional on those routes.

#### Resource requirement profile

For this snapshot week (one run per cell, GA seed 42, native termination), the [resource step charts](results/week-2026-10-05-4sw5so/figures/) count vehicles on routes and vehicles busy through the 10-minute cooldown. The figure below compares the four ride limits on Wednesday.

![Busy vehicles including cooldown by ride limit R, Wednesday 2026-10-07](results/week-2026-10-05-4sw5so/figures/resource_compare_2026-10-07.svg)

On Wednesday, R = 50, 60 and 70 each require 6 vehicles; the busy peak occurs at 12:34–12:46 and the on-route peak at 12:34–12:36. Tuesday at R = 50 has an on-route peak of 4 and a busy peak of 5, with busy-peak windows 08:48–08:55 and 12:15–12:16; the other 19 rows have equal peak counts, although their peak windows can differ. For the fixed routes, adding cooldown changes the resource intervals, but these observations do not isolate causes of the observed fleet differences. On Monday, the busy peak starts at 08:11, 07:43, 07:31 and 07:33 for R = 50, 60, 70 and 90, respectively. Wednesday to Friday generally peak around midday; Thursday at R = 60 also has a busy-peak window at 16:15–16:42 and another at 13:35–13:44. The [weekly chart at R = 50](results/week-2026-10-05-4sw5so/figures/resource_week_R50.svg) stacks the weekdays. For Wednesday at R = 50, 60 and 70, outside the reported busy-peak window at most 5 vehicles are busy; outside the on-route peak window at most 5 are on routes. Thursday's busy-peak windows at R = 50, 70 and 90 are 12:39–12:55, 13:35–13:53 and 13:35–13:52, respectively; Friday's at R = 50, 60, 70 and 90 are 13:15–13:35, 13:15–13:33, 13:16–13:33 and 13:15–13:33.

#### Heterogeneous fleet scenarios

The heterogeneous campaign uses a large minibus (4 Sw / 5 So) and sedans (0 Sw / 4 So), each with a 10-minute cooldown, the same R and tour limit 150, and the captured travel-time matrix. Sedan Sw = 0 is a scenario assumption, so any route with an Sw passenger must use a minibus. Fleet types are explicit CLI inputs; the vehicle table is not consulted. Scenario A computes the all-large minimum for the heuristic fixed routes; L1–L3 (B–D in the tables) fix 1, 2 or 3 minibuses and minimise the sedan count over the generated menus. These are single-snapshot results with one run per cell, GA seed 42 and native termination. The [archive](results/week-2026-10-05-fleet/) contains responses, statuses and manifests, and [weekly_summary.md](results/week-2026-10-05-fleet/weekly_summary.md) gives the recomputed weekly tables.

For each wave, a typed split decoder checks contiguous segments against each type's Sw and So pools, any shared total-capacity limit, and that type's ride and tour caps. Its dynamic programme minimises borrowed-type route count and then travel time, subject to the large-route quota, for a fixed giant tour. The campaign producer adds the `ga_split` all-large baseline and `ga_split_hf` quota options; the large+sedan campaign uses q = 0..3, the corrected minivan campaign q = 0..2, and L4 q = 0..4, bounded by the wave size. Duplicate GA options are removed by route partition, ignoring stop order. A CP-SAT model chooses one option per wave and labels its routes by feasible vehicle type, constraining the large-vehicle busy peak by L. In the selection code, the car type is the borrowed type, sedan in the large+sedan campaigns and minivan in the minivan campaign, and its count is the peak number of concurrently busy borrowed vehicles, cooldown included. The committed code behind the archived fleet campaigns (8ab88ca, 4200acb, afc7208) ranked lexicographically by borrowed-type count, borrowed-type route minutes, total vehicle-minutes and option-index sum; the manifests record dirty working trees, so this order is inferred from that code. The current implementation ranks borrowed-type count, total vehicle-minutes, borrowed-type route minutes and option-index sum, the originally specified order restored on 2026-10-13. Because the count is the first stage and all archived selections had status optimal over their generated menus, the archived borrowed-type counts are unaffected; their borrowed-type route minutes, total vehicle-minutes and selected options may differ under the current order. The current implementation shares one call's time allowance across the stages; it does not grant a fresh allowance to every stage. The archive records CP-SAT 9.15.6755, solver seed 20261008, one worker and a 30-second selection limit, separately from GA seed 42. The chosen fixed routes are independently assigned and checked in TypeScript for capacities, per-type ride/tour limits, overlap and cooldown before `proven_over_menu` is emitted. The archived verification reports 51 feasible runs passing its checks and 29 menu-infeasible rows with no routes.

Weekly results for one snapshot week, one run per cell (GA seed 42, native termination), under assumed confirmations: the archive records 226 passenger legs per R; daily student counts sum to 113 student-days. Weekly need is the largest daily need, representing the same fleet across weekdays; A proofs are conditional on fixed routes, while feasible L1–L3 rows are proven over menus and independently assigned.

| R (min) | Scenario | Weekdays feasible | Minibuses | Sedans (max per day) | Weekly vehicles | Sedans per day (Mon to Fri) | Source |
|---|---|---|---|---|---|---|---|
| 50 | A: none | 5/5 | 6 | 0 | 6 | - | |
| 50 | B: 1 | 0/5 | 1 | - | - | - | |
| 50 | C: 2 | 2/5 | 2 | - | - | x / 3 / x / x / 4 | |
| 50 | D: 3 | 5/5 | 3 | 4 | 7 | 4 / 2 / 4 / 2 / 3 | |
| 60 | A: none | 5/5 | 6 | 0 | 6 | - | |
| 60 | B: 1 | 0/5 | 1 | - | - | - | |
| 60 | C: 2 | 3/5 | 2 | - | - | x / 2 / x / 2 / 3 | |
| 60 | D: 3 | 5/5 | 3 | 3 | 6 | 2 / 1 / 3 / 1 / 2 | |
| 70 | A: none | 5/5 | 6 | 0 | 6 | - | |
| 70 | B: 1 | 0/5 | 1 | - | - | - | |
| 70 | C: 2 | 3/5 | 2 | - | - | 3 / x / x / 2 / 3 | |
| 70 | D: 3 | 5/5 | 3 | 3 | 6 | 1 / 1 / 3 / 1 / 2 | |
| 90 | A: none | 5/5 | 4 | 0 | 4 | - | |
| 90 | B: 1 | 0/5 | 1 | - | - | - | |
| 90 | C: 2 | 3/5 | 2 | - | - | 2 / x / x / 2 / 2 | |
| 90 | D: 3 | 5/5 | 3 | 1 | 4 | 1 / 0 / 1 / 1 / 0 | |

An x denotes a menu-infeasible weekday; a dash denotes an unavailable weekly count because at least one weekday is menu-infeasible. For A, daily minibus minima are 6 / 5 / 6 / 5 / 6 at R = 50, 5 / 4 / 6 / 4 / 5 at R = 60, 4 / 4 / 6 / 4 / 5 at R = 70, and 4 / 3 / 4 / 4 / 4 at R = 90.

![Weekly vehicles by scenario, R = 60](results/week-2026-10-05-fleet/figures/fleet_scenarios_R60.svg)

The following observations describe that single snapshot, one run per cell (GA seed 42, native termination), and the generated menus.

- **L1 has no feasible menu selection.** All 20 cells are `infeasible_for_L`: 15 are labelled `SW_DEMAND_EXCEEDS_LARGE_CAPACITY` and 5 `CROSS_WAVE_CONFLICT`. At R = 60, the largest Sw wave contains 5 passengers on Monday and Thursday, 4 on Friday, and 3 on Tuesday and Wednesday.
- **L2 is feasible on some weekdays.** It is feasible on 2 of 5 days at R = 50 and 3 of 5 at R = 60, 70 and 90, so none of these generated-menu scenarios provides a complete week with two minibuses. Of its 9 menu-infeasible cells, 2 are labelled `SW_DEMAND_EXCEEDS_LARGE_CAPACITY` (Monday at R = 50 and 60) and 7 `CROSS_WAVE_CONFLICT`.
- **L3 has a feasible selection on every weekday at every R.** Peak daily sedan need is 4, 3, 3 and 1 at R = 50, 60, 70 and 90, respectively; Tuesday and Friday need no sedan at R = 90. At R = 60, Wednesday's three sedan windows are 11:15–12:36, 11:51–12:45 and 12:15–13:07. At R = 60, the other L3 sedan windows are 07:12–16:50 and 07:43–08:45 on Monday, 07:23–13:36 on Tuesday, 13:15–16:49 on Thursday, and 07:37–17:28 and 13:02–13:45 on Friday.
- **Vehicle count and route minutes describe different resources.** L3 and A have weekly counts of 7 versus 6 at R = 50, and equal counts of 6, 6 and 4 at R = 60, 70 and 90. Their respective weekly route-minute totals are 6967 versus 6822, 6472 versus 6450, 6048 versus 6053, and 5838 versus 5862. At R = 60 the passenger-weighted mean rides are 31.221239 minutes for A and 31.172566 for L3. These are descriptive comparisons of heuristic route sets. Summing the L3 daily rows gives 29 of 111 sedan routes at R = 50, 16 of 94 at R = 60, 10 of 81 at R = 70 and 3 of 73 at R = 90. The sedan shares of route minutes are the exact ratios 1775/6967, 931/6472, 513/6048 and 156/5838, respectively.
- **Sedan borrowing days depend on R.** L3 uses sedans on every weekday at R = 50, 60 and 70 and on Monday, Wednesday and Thursday at R = 90.

The proof label `proven_over_menu` applies to borrowed-vehicle count over the generated menus; a different routing could change the count, and `infeasible_for_L` means infeasible over the generated menus (menu-infeasible), not that no feasible day plan exists. All timetable legs are assumed confirmed, all So students are assumed able to use the declared borrowed type, and sedan Sw = 0 remains an unverified scenario assumption. The recorded failure codes distinguish a wave requiring more large routes than L from cross-wave overlap; they are not causal estimates. The same fixed arc times apply to both types; cost, lender availability, drivers and boarding times are not modelled. The [earlier fixed-route fleet what-if](results/week-2026-10-05-4sw5so/fleet_mix_analysis.md) only reassigns routes built for the large vehicle and provides an upper bound; it is not the typed-menu evidence used above.

#### Multi-objective trade-off (Pareto) analysis

An option combines a fleet family with owned minibus count L and ride limit R: all-large A, large+sedan L1–L4, or large+Doblò L0–L2. Each campaign uses at most two types; the extra scenarios are L4 with sedans and the corrected minivan campaign, rather than a simultaneous three-type solve. Doblò is modelled as `minivan:1sw3so:cap3:cd10`: at most 1 Sw, at most 3 So, and at most 3 passengers in total, with a 10-minute cooldown; an Sw passenger occupies a seat while the wheelchair is stowed. This is an assumed scenario model, not verified service accessibility; no `1sw2so` variant was run. The earlier `extra/minivan/` campaign allowed four passengers and is SUPERSEDED by [extra/minivan-cap3/](results/week-2026-10-05-fleet/extra/minivan-cap3/). The approved brief records a one-vehicle increase in the pure-minivan peak at every R after that correction, unchanged L1/L2 minivan peaks, and borrowed-hour changes of at most 2.7 hours for L1/L2. The valid extra archives use the same snapshot week, matrix, R grid and tour limit, GA seed 42, native termination and assumed confirmations, with one archived run per cell.

The ε-constraint analysis fixes L and R and minimises each day's borrowed-vehicle count over its generated route menus; a weekly option requires a feasible selection on all five weekdays. The reported objectives are f1, owned minibuses; f2, maximum daily distinct borrowed vehicles; f3, weekly borrowed busy hours (route minutes plus the 10-minute cooldown after each borrowed route, divided by 60); f4, weekdays with any borrowing; and f5, R and realised passenger-weighted mean ride. Here f4 counts borrowing days, while the separate CSV field `borrowed_vehicle_days` sums vehicles over days. Dominance is evaluated on (f1, f2, f3) within R and on (f1, f2, f3, R) across R; equal objective vectors do not dominate one another. The archive contains 36 options, comprising 32 non-derived options and 4 day-level hybrids, of which 28 are feasible. The recorded route/CSV checks cover 131 feasible-day runs with zero violations and 29 menu-infeasible day runs with no routes. Owned utilisation uses busy minutes over the common service span times owned capacity; borrowed utilisation uses busy minutes over first-start to last-end-plus-cooldown loan windows, and the before-10:00 share uses borrowed busy time.

For this snapshot week (one run per cell, GA seed 42, native termination), the six non-dominated options at R = 60 are shown below at the precision printed in the archive.

| Option | f1 owned minibuses | f2 peak borrowed | f3 borrowed h/week | f4 borrowing days | Source |
|---|---:|---:|---:|---:|---|
| L0 + Doblò | 0 | 7 | 135.5 | 5 | |
| L1 + Doblò | 1 | 5 | 83.6 | 5 | |
| L2 + Doblò | 2 | 4 | 42.5 | 5 | |
| L3 + sedan | 3 | 3 | 18.2 | 5 | |
| L4 + sedan | 4 | 2 | 4.2 | 3 | |
| A | 6 | 0 | 0.0 | 0 | |

The same six option families form the per-R non-dominated sets at R = 50, 70 and 90; at R = 90, A and L4 have identical (f1, f2, f3) = (4, 0, 0), although their realised mean rides differ. Borrowed peaks and hours fall as L increases within each family in these runs; sedan options with L ≥ 3 use fewer borrowed hours than the tested Doblò options with L ≤ 2 but require more owned minibuses. The derived L2 day-level hybrid uses sedans on feasible sedan weekdays and minivans otherwise; it is dominated by pure L2+Doblò on (f1, f2, f3) at all four R. At R = 60, it uses minivans on 2 days rather than 5 and records 44.5 borrowed hours against 42.5 for pure L2+Doblò; that reduced minivan-day count is outside the stated dominance objectives. A wave-level hybrid with three types remains future work. At R = 60, owned utilisation is 34% in A and 49%–72% in the borrowing options; the options borrowing on five weekdays have borrowed utilisation 50%–54%, and the before-10:00 shares of borrowing options are 26%–32%, at the archive's printed precision.

![Pareto options per R](results/week-2026-10-05-fleet/figures/pareto_front_by_R.svg)

Figures (in `results/week-2026-10-05-fleet/figures/`, indexed in `index.html`): [pareto_front_by_R.svg](results/week-2026-10-05-fleet/figures/pareto_front_by_R.svg) and [pareto_front_combined.svg](results/week-2026-10-05-fleet/figures/pareto_front_combined.svg) (owned minibuses against borrowed hours, bubble size = peak borrowed); [pareto_service_vs_minibuses.svg](results/week-2026-10-05-fleet/figures/pareto_service_vs_minibuses.svg) (mean ride against owned minibuses); [pareto_borrowed_heatmap_R60.svg](results/week-2026-10-05-fleet/figures/pareto_borrowed_heatmap_R60.svg) (borrowed vehicles by hour and weekday); [pareto_parallel_coordinates.svg](results/week-2026-10-05-fleet/figures/pareto_parallel_coordinates.svg); [pareto_utilisation.svg](results/week-2026-10-05-fleet/figures/pareto_utilisation.svg).

The front is an approximation over the tested L and R values and heuristic menus. Borrowed count is proven only over those menus; f3 and f4 are reported outcomes rather than separately minimised objectives, so another count-minimal plan could change f3. The analysis concerns one week, one captured matrix, assumed confirmations and a single GA seed 42 under native termination. Capacities and accessibility of the borrowed types are scenario assumptions, and cost and lender availability are absent, so the analysis does not rank affordability or practical acceptability.

Achieved service level and fleet size can be studied descriptively, but these single-snapshot, single-seed native results do not support superiority, causal attribution or a global fleet optimum. Later algorithm comparisons require primary fixed objective-evaluation budgets; native-termination evidence must remain separately labelled.

**Corrections and their effect on reported results.** CX-01 replaced outward whole-minute interval rounding with centi-minute endpoints and cooldowns (`time_scale = 100`); off-grid values fail closed rather than being rounded. The recorded archive effect is none because the archived arcs and interval endpoints are whole minutes. (see `results/week-2026-10-05-fleet/cx01_replay_check.md`) CX-03 makes the typed GA decode cost-only for one type without an active quota, restoring the documented parity with the untyped GA; two-type quota decoding is unchanged. The typed campaigns used two types, and the single-type campaign used `ga_split`, so CX-03 does not change their reported routes. The core archives were produced at `6be127d`, `8ab88ca` and `4200acb`, before CX-01/CX-03, and each manifest records a dirty tree; L4 records `afc7208` and a dirty tree as well. These remain historical native, single-seed archives; the typed exact comparison in Section 7 uses a separate re-run of both mixed-fleet campaigns at one pinned commit (f29aa3d, clean working tree), and the historical rows are not pooled with the re-run rows.

## 7. Exact reference and optimality gap of the genetic algorithm

This section compares the route sets of one genetic algorithm (GA) run with a per-wave exact reference for one snapshot week. The comparison only measures the gap; it does not rank the two methods.

### Method

**Data and GA side.** The measurement uses a single snapshot week, 2026-10-05 to 2026-10-09, with 57 waves and 226 passenger legs, ride limits R = 50, 60, 70 and 90 minutes and a tour cap of 150 minutes. The GA side is a single run of the route-first, cluster-second GA of §4.1 with seed 42 under the native termination protocol, the secondary protocol. For the single-type fleet (4 wheelchair positions, Sw, and 5 seated positions, So) the GA routes come from the archived campaign, produced at commit 6be127d with a dirty working tree. For the two mixed fleets they come from a re-run at commit f29aa3d with a clean tree that archived every menu option. Every gap below is the gap of that run, not of the GA in general.

**Exact reference per wave.** The exact reference solves each wave separately. All feasible routes of the wave are enumerated, with one column per multiset of (location, class) and vehicle type, carrying the cheapest feasible stop order. Because the travel-time matrix is non-metric, a stop order may revisit a location. A set-partitioning model then selects routes with integer multiplicities. It is solved in two lexicographic stages: the first minimises the number of routes, the second minimises total route duration D with that count fixed. For the single type the count is K; for a mixed fleet it is K_m, the routes of the minimised type. A separate solve without a count objective gives a duration lower bound, D_LB_free.

**Mixed fleets.** Two mixed fleets were studied: large + sedan and large + Doblò. The large vehicle is the minibus (4 Sw / 5 So); the sedan has 0 Sw / 4 So; the Doblò minivan carries at most 1 Sw, 3 So and 3 passengers in total. For each wave the exact menu mirrors the GA menu: a base option that uses the large type only, and q options with at most q large routes that minimise the routes of the small type. The two fleets give 1872 options, 1004 for large + sedan and 868 for large + Doblò.

**Solvers and limits.** The per-wave models were solved through AMPL, with Gurobi 13.0.3 as the primary solver; the joint day model at the end of this section reverses the roles (HiGHS primary, Gurobi cross-check). Each solver call had a wall-clock limit of 60 s, or 600 s on the per-day peak wave, the wave with the most legs. Gurobi also had a deterministic work limit of 20 work units, or 200 on peak waves. Every call used one thread and seed 0. Every optimal result was re-solved with HiGHS 1.15.1, and any disagreement in a proven value was defined as blocking.

**Certification.** Each exact route set and the archived GA route set of the same wave were checked by the same independent certificate, the operational response certifier, on the same captured travel-time matrix. Route counts and durations were recomputed from the certified routes in integer arithmetic and had to equal the solver objective.

**Protocol and gap definitions.** Exact results form a separate protocol, `exact_reference_v1`, and are never ranked, averaged or tested together with heuristic results. The only quantity that crosses the protocols is the gap of a GA result against a certified exact value. K* and D* are the proven optimal route count and total route duration of the exact reference for a wave or option; K_GA and D_GA are the GA's values for the same wave or option. The route-count gap is dK = K_GA − K*. The duration gap is gD = (D_GA − D*)/D*. It is defined only where K_GA = K*; where K_GA > K*, gD is undefined.

**Day level.** For the mixed fleets, the day's vehicle selection was solved by CP-SAT for each (fleet, date, R, L) cell, where L is the number of owned minibuses and limits the minibus peak. Cars are the peak number of concurrently busy small-type vehicles, including the 10-minute cooldown; the selection minimises cars first, then total vehicle-minutes, then car-minutes. Each cell was solved twice: once over the GA menus alone, and once over the union menu, which combines the GA and per-wave exact menus. The TypeScript vehicle-assignment check independently confirmed every selection. The union-menu result is the minimum car count over that union menu, not a global day optimum, and a run labelled `infeasible_for_L` is infeasible over its menu, not proven infeasible for the day; a global day model, with certified and solver-proven day-level infeasibility, is reported separately under its own protocol at the end of this section (Joint day model, WP-E11). Results are never reported as min(GA, union).

**Reproducibility.** Every campaign is archived with a manifest that records the git commit, the solver and AMPL versions, the option strings and the input file hashes. The final mixed-fleet exact results come from a single clean serial run; an earlier parallel run was discarded. The exact routes are stored, so they can be re-certified without a solver licence.

### Results: week of 2026-10-05

**Single type (4 Sw / 5 So).** All 228 wave instances (57 waves × 4 values of R) were solved to proven optimality, and no solver limit was reached. HiGHS gave the same (K, D) and the same D_LB_free on all 228. Table 7.1 gives the gaps per R.

| R (min) | Waves with dK = 0 | Weekly routes, GA / exact | Waves with gD > 0 (of 56) | Mean gD | Max gD |
|---:|---:|---:|---:|---:|---:|
| 50 | 56 of 57 | 109 / 108 | 3 | 0.000552 | 0.018462 |
| 60 | 56 of 57 | 94 / 93 | 6 | 0.004200 | 0.089947 |
| 70 | 56 of 57 | 82 / 81 | 3 | 0.001067 | 0.027778 |
| 90 | 56 of 57 | 73 / 72 | 3 | 0.001135 | 0.034146 |

Table 7.1. Single type; one seed-42 GA run under native termination, single snapshot week. Mean and max gD are taken over the 56 waves per R with K_GA = K*.

In each R, one 08:45 pickup peak wave has dK = 1. Figure 7.1 (`figure_gap_single`; single type; per-wave duration gap against students per wave) has one panel per R; Figure 7.2 (`figure_gap_typed`) shows the two mixed fleets for each R, with base and q options separately; both are in `results/week-2026-10-05-exact/wp-e6-gap-report/`. Rows with dK ≥ 1 are not drawn, because their gD is undefined, and each panel gives their count.

**Mixed fleets, per-wave options.** Of the 1872 options, 1705 were solved to proven optimality and 167 were proven infeasible, all of them large + sedan q options. HiGHS agreed on every option: same (K, D) on the 1705 optimal options, same infeasibility on the 167 and same D_LB_free. In the 1703 option pairs where both sides had a solution, the exact optimum was never worse than the GA option of the same kind. In 2 options the GA found no solution while the exact model did; both are large + sedan options for the 2026-10-05 08:45 pickup wave with q = 2, at R = 50 and R = 60.

For the q options, dK compares K_m, the routes of the minimised small type (sedan or Doblò): dK = K_m,GA − K_m*. Per fleet and R, the share of q options with dK = 0 ranged from 0.9625 (large + Doblò, R = 50: 154 of 160) to 0.99375 (large + Doblò, R = 70 and 90: 159 of 160). dK never exceeded 1. Mean gD per (fleet, R) lay between 0.000339 and 0.003823. The largest single q-option value was 0.1317, for large + sedan at R = 90. The per-(fleet, R) values are in `results/week-2026-10-05-exact/wp-e6-gap-report/table_by_R.csv`. The base options of both mixed fleets repeat the single-type statistics exactly, because they use the same large type and the same GA base routes, so they are not independent results.

**Day level.** Table 7.2 gives the outcomes per fleet and L.

| Fleet | L | Cells | Both CP-SAT runs optimal and TypeScript-confirmed | Union one car fewer | Union same | Union more | Both menus infeasible | GA-menu run proven infeasible, union run optimal and confirmed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| large + sedan | 1 | 20 | 0 | – | – | – | 20 | 0 |
| large + sedan | 2 | 20 | 11 | 1 | 10 | 0 | 8 | 1 |
| large + sedan | 3 | 20 | 20 | 3 | 17 | 0 | 0 | 0 |
| large + Doblò | 0 | 20 | 20 | 3 | 17 | 0 | 0 | 0 |
| large + Doblò | 1 | 20 | 20 | 2 | 18 | 0 | 0 | 0 |
| large + Doblò | 2 | 20 | 20 | 2 | 18 | 0 | 0 | 0 |

Table 7.2. Day-level vehicle selection over the GA menus and over the union menu, per fleet and L; one seed-42 GA run, single snapshot week.

Where both runs are optimal and confirmed, the union menu needs one car fewer in 4 and the same number in 27 of 31 cells for large + sedan, and one fewer in 7 and the same in 53 of 60 for large + Doblò; it never needs more. The union-only cell (large + sedan, 2026-10-05, R = 60, L = 2) needs 3 cars. Every cell with one car fewer selects an exact option for the 08:45 pickup wave.

**Limitations.** These results cover one snapshot week and one GA seed. The certificate, the GA and the exact model all assume no waiting time at stops, and the travel-time matrix is a fixed snapshot without traffic.

### Joint day model (WP-E11)

The union-menu day level above (WP-E4b) picks one option per wave and gives the minimum car count over that menu, not a global day optimum. The day fleet depends on the busy intervals of the routes and their peak concurrency, not on per-wave (K, D), so a wave-optimal route set can be a poor day choice: a longer or extra route in one wave can free a vehicle for another wave. The joint day model of work package WP-E11 therefore chooses the routes of all waves of a date together, in one mixed-integer model per cell, from the full set of enumerated routes. The owner reopened this question, so the earlier decision that a global day model is out of scope no longer holds; the results form a separate protocol, intended for a second paper. "The prototype" below means the independent prototype scripts, with their own plan checker, that prompted WP-E11; their values serve only as reproduction targets.

#### Method

**Cells, fleets and notation.** The grid is the snapshot week 2026-10-05 to 2026-10-09, R = 50, 60, 70 and 90 minutes and a tour cap of 150 minutes. A cell is (fleet, date, R) for the single type and (fleet, date, R, L) for the mixed fleets, where at most L large vehicles may be used. The fleets are the single type (4 Sw / 5 So), 20 cells; large + sedan with L = 1, 2 or 3, 60 cells; and large + Doblò with L = 0, 1 or 2, 60 cells; 140 cells in all. Here V is the day vehicle count of the single type, the peak number of simultaneously busy vehicles, as §6 uses V for daily vehicles; the design file and the result files call this value K. S is the peak count of the minimised small type (sedan or Doblò), the cars of the day level above. K keeps its §7 meaning of a route count.

**Day plan.** As in production, a day plan covers each occurrence of every wave exactly once with routes that respect the tour, ride and capacity limits of the vehicle type assigned to them. Pickup routes end and dropoff routes start at the wave anchor, without waiting; a vehicle is busy until the end of its route plus the 10-minute cooldown, and the vehicles needed of a type are the peak count of simultaneously busy intervals.

**Objectives.** The objectives are lexicographic, each stage a separate solve. For the single type the model minimises V, then total vehicle minutes with V fixed; for the mixed fleets, with the large peak at most L, it minimises S, then total vehicle minutes, then car minutes. For the mixed fleets this is the order of the day level above; remaining ties are co-optimal alternatives, so results are compared on objective values, not on route identity.

**Columns and exactness.** For each wave the columns are the full output of the route enumeration for the cell's types, R and tour cap: one column per feasible (multiset of (location, class), type), the same candidate routes as in the per-wave exact reference above (WP-E3 for the single type, WP-E4a for the mixed-fleet menus); a route that both types accept gives two columns, so the column choice decides the type. Any feasible day plan maps to a model solution that is no worse in any objective, because the column of a route has a tour that is not longer and so a busy interval that is not wider. The model optimum is therefore the global day optimum under these rules only when every wave of the date was enumerated completely; otherwise the cell is labelled `not_run_enumeration_cap` and no day claim is made.

**Model.** Integer multiplicities choose the columns, since one column can be needed twice in a wave; covering constraints meet each item count of each wave exactly, and at each route start of a type the selected routes busy at that point may not exceed V, L or S. All coefficients are integers; the lower bounds below serve only the labels and are not added to the model.

**Lower bounds and certificates.** For the single type, LB0 is the largest sum, over the wave anchors, of the proven WP-E3 route minima of the waves whose routes must all be busy at that anchor, and LB0w widens these windows by each wave's smallest tour; LB0 comes from the prototype, and LB0w was added by owner decision. For the mixed fleets, LB_L does the same with the least numbers of large routes per wave, and LB_S subtracts L from the corresponding peak sum of least total route counts. If LB_L > L, no day plan with at most L large vehicles exists: tier 1, `certificate_capacity_floor`, uses only an arithmetic floor from Sw counts, and tier 2, `certificate_wave_min_large`, uses wave values on which both solvers agree. Certificates are valid but not complete: on a separate test set of oracle days with unequal type cooldowns, not this week, they certified 63 of 107 infeasible cells, and in this week 15 of the 26 cells without a plan are certified. Infeasibility without a certificate is accepted when both solvers prove it.

**Solvers and limits.** The solver roles are the reverse of the rest of §7: HiGHS 1.15.1 through the `highspy` package is the primary solver, and Gurobi 13.0.3 through AMPL is the cross-check. Both solvers receive the same model object, not the same MPS bytes; the canonical MPS file and its sha256 are archived, and AMPL presolve is off in the cross-check. Each day-model solver call (one per stage) had 600 s, one thread, seed 0, relative gap 0 and absolute gap 0.99, and a stage counts as `optimal` only if the runner's own check incumbent ≤ ceil(bound − 1e-6) holds. A calibration run of 15 cells, each solved twice without a work limit, used at most 3.68 Gurobi work units and at most 242.69 s per HiGHS call; the owner then set a Gurobi work limit of 200 for the campaign and kept 600 s as a safety net.

**Labels and proof claims.** Each cell is labelled `optimal`, `infeasible_certified` (tier named) or `infeasible_solver_proven` (no certificate), or with one of the labels for open or rejected cells. A proof claim needs a proof label and `proof_claim_allowed` true: `optimal` and `infeasible_solver_proven` need the day-level cross-check `agree` (both solvers proven, same status, value and fixed inputs), a tier-2 certificate needs agreement on the wave values, and tier 1 needs neither. In this text "no day plan with at most L large vehicles" is used only for `infeasible_certified`; `infeasible_solver_proven` is written "infeasible, solver-proven", and the WP-E4b labels stay "infeasible over the menu".

**Independent checker.** A separate checker that does not import the solver code rechecks every plan (coverage, capacities, arcs, tour and ride limits, anchored intervals, per-type peaks and objective values); wave routes are also certified with `certify_optimization_response`, and mixed-fleet plans are confirmed by `scripts/verify-typed-selection.ts`.

**Protocol and reproducibility.** The results form the protocol `exact_day_joint_v1`, its own pooling group, never pooled with `exact_reference_v1` wave rows, `union_day_v1` (WP-E4b) rows or heuristic rows, and never reported as a minimum across protocols. The campaign ran as one serial process without cache, at code commit `e45cd6bf` with a clean working tree, reading only committed source campaigns. In the calibration run the two runs of each cell differed only in wall times, a repeat check on one machine and software version. The record is the third attempt, because the first two stopped on a transient AMPL licence failure and wrote nothing; a retry rule for such failures was decided later, is not merged, and the record ran without it.

#### Results: week of 2026-10-05

**Labels.** Of the 140 cells, 114 are `optimal` (all 20 single-type, all 60 large + Doblò and 34 large + sedan cells), 15 are `infeasible_certified` and 11 are `infeasible_solver_proven`, the last two groups all large + sedan. Every cell carries a proof claim, and no blocking defect occurred. The proof is two-solver agreement on the day model in 125 cells, a tier-1 certificate in 8 and a tier-2 certificate with two-solver agreement on the wave values in 7; in the 15 certified cells the day model was not cross-checked. The independent checker passed all 114 plans, and the run checks against the union menu and the archived peaks passed wherever they applied.

**Single type (4 Sw / 5 So).** Table 7.3 gives V per date. Of the 20 cells, V is lower than the peak of the archived GA route set of the same date and R in 11 and equal in 9; against the peak of the WP-E3 route sets it is lower in 9 and equal in 11; it is higher in none.

| R (min) | 2026-10-05 | 2026-10-06 | 2026-10-07 | 2026-10-08 | 2026-10-09 |
|---:|---:|---:|---:|---:|---:|
| 50 | 6 | 4 | 5 | 4 | 6 |
| 60 | 4 | 4 | 5 | 4 | 5 |
| 70 | 4 | 4 | 5 | 3 | 4 |
| 90 | 3 | 3 | 4 | 3 | 3 |

Table 7.3. Single type; day vehicle count V per date, protocol `exact_day_joint_v1`, single snapshot week; every cell `optimal` with two-solver agreement. The GA-side comparison uses one seed-42 GA run under native termination and is descriptive, not a ranking.

**Mixed fleets against the union menu.** Table 7.4 compares S with the car count over the WP-E4b union menu. For large + Doblò, S is lower in 28 and equal in 32 of the 60 cells. For large + sedan, both protocols have a plan in 12 cells at L = 2 and 20 at L = 3; S is lower in 4 and 8 of them and equal in 8 and 12. At L = 1 the joint model is infeasible in all 20 cells (15 certified, 5 solver-proven) and the union menu is infeasible over the menu; at L = 2, 6 cells are infeasible, solver-proven, and infeasible over the menu. In no cell does the union menu have a plan where the joint model has none. In two large + sedan cells (2026-10-06, R = 70 and 90, L = 2) the union menu is infeasible over the menu, while the joint model finds S = 2.

| Fleet | L | Cells | Joint: fewer cars | Equal | Joint: more cars | Joint plan, union infeasible over the menu | Joint infeasible (union infeasible over the menu) |
|---|---:|---:|---:|---:|---:|---:|---:|
| large + sedan | 1 | 20 | – | – | – | 0 | 20 |
| large + sedan | 2 | 20 | 4 | 8 | 0 | 2 | 6 |
| large + sedan | 3 | 20 | 8 | 12 | 0 | 0 | 0 |
| large + Doblò | 0 | 20 | 11 | 9 | 0 | 0 | 0 |
| large + Doblò | 1 | 20 | 9 | 11 | 0 | 0 | 0 |
| large + Doblò | 2 | 20 | 8 | 12 | 0 | 0 | 0 |

Table 7.4. Mixed fleets; small-type peak S of the joint day model (`exact_day_joint_v1`) against the car count over the WP-E4b union menu (`union_day_v1`), per fleet and L. The two protocols are shown side by side and not pooled; one seed-42 GA run, single snapshot week; descriptive, no ranking. Joint infeasible: L = 1, 15 certified and 5 solver-proven; L = 2, 6 solver-proven.

**Weekly values.** Table 7.5 gives, per fleet, L and R, the weekly maximum of V or S and the sum over the five dates. For large + sedan, L = 1 is infeasible on every date (certified or solver-proven) and L = 2 has plans on 2 of 5 dates at R = 50 and on 4 of 5 at the other values of R, so no weekly value is given for them.

| Fleet | L | R = 50 | R = 60 | R = 70 | R = 90 |
|---|---:|---:|---:|---:|---:|
| single type (4 Sw / 5 So) | – | 6 (25) | 5 (22) | 5 (20) | 4 (16) |
| large + sedan | 3 | 3 (11) | 2 (7) | 2 (5) | 1 (1) |
| large + Doblò | 0 | 7 (27) | 7 (26) | 7 (26) | 7 (26) |
| large + Doblò | 1 | 5 (20) | 5 (19) | 4 (16) | 4 (15) |
| large + Doblò | 2 | 4 (15) | 3 (13) | 3 (10) | 2 (8) |

Table 7.5. Weekly maximum of V or S (`weekly_fleet_max`) and, in brackets, the sum over the five dates (`vehicle_days_sum`), from `day_joint_week.csv`; protocol `exact_day_joint_v1`, single snapshot week, every cell with a proof claim; descriptive, no ranking. For the mixed fleets both values are of S, the small type only; the large vehicles (at most L) are not counted.

**Reproduction of the prototype.** The prototype results that prompted WP-E11 are reproduction targets, never run inputs or tuning targets. All 20 single-type cells and 59 of the 60 large + sedan cells are `equal`; the remaining large + sedan cell (2026-10-05, R = 90, L = 2) is `prototype_open`, where the prototype left S in {1, 2} and the campaign proves S = 2; the 60 large + Doblò cells have no external target. The weekly design targets (single-type fleet 6/5/5/4, 83 vehicle-days, 12 of 60 large + sedan cells with fewer sedans than the union menu, sedans 3/2/2/1 at L = 3) are equal on both sides; the minute targets were not recomputed. The prototype plans are not in the repository and were not checked, so this is agreement with unverified data.

**First run and rerun.** A first full run (code `f77c2484`) left the large + Doblò cell 2026-10-08, R = 50, L = 2 without a proof claim, because the integrality test was applied to Gurobi's raw stage-3 objective 539.9999877; the fix tests the variable values and recomputes the objective from the rounded values. In this cell S = 2 against 3 cars over the union menu. In the full rerun, labels, V or S, minutes, plans and MPS hashes are equal to the first run in 140 of 140 cells, the repaired cell carries a claim, and 113 cells differ only in raw Gurobi bound values; the first run is kept as a superseded record and never pooled.

**Runtimes.** The campaign took 10060.5 s of wall time; the longest cell took 568.31 s, the longest HiGHS call 110.25 s and the longest Gurobi call 3.64 s, and no day-model stage call came near the 600 s or the work limit; the wave-value calls are not recorded in the stage files and their times are not reported.

**Limitations.** These rows describe one snapshot week, one GA seed (42, on the GA side), one machine and one software version; they are descriptive and support no superiority, causality or generality claim. Certificate coverage is not complete. The global day claim holds only where every wave is fully enumerated. A scaling probe found complete enumeration up to about 80 students per wave at R = 50 and about 30 at R = 70 and 90 (26 stops); in this week no cell was labelled `not_run_enumeration_cap`. Larger waves would turn the model into a restricted master problem without a global claim, and the named upgrade path, branch-and-price, is not implemented. The day plan assumes no waiting at stops.

## 8. Further study

Further studies can add individual passenger windows, boarding times, driver assignment, traffic-aware matrices and publication of approved daily plans, subject to separate contracts and evidence. Further work could examine anchor shifts, cooldown variation and class staggering as possible changes to the peak resource requirement. Heterogeneous routing with Sw/So pools is now represented by the archived scenarios, while a joint day optimum over all fully enumerated routes and vehicle types is reported separately, for one snapshot week, in §7 (Joint day model, WP-E11). Matrix-based clustering remains a separate research question; geometric grouping does not replace road-network evaluation.

Section 7 reports the executed exact reference, the mixed-fleet GA re-run and the gap report. The compact fallback model (WP-E5) was not needed: no wave reached the enumeration caps (2 000 000 columns, 5 000 000 labels), and at most 47 027 columns and at most 171 053 labels were needed in any wave. For waves larger than those of this week, the exact-reference design names branch-and-price (column generation) as the upgrade path if complete enumeration becomes too large; it is not implemented. Exact references for TSP/ATSP benchmark instances (GOAL 2, WP-E7 and WP-E8) were executed and merged under the instance set and limits decided by the owner; CVRP references (WP-E9) and instances with n > 100 are deferred.

## 9. Validity and scope

The archived daily student counts are 27, 21, 23, 23 and 19 from Monday to Friday, and full-snapshot matrix provenance records 29 locations. Earlier planning notes reported 28 students in a D0 read-only inventory dated 2026-10-04. The archived matrices are per-date slices: their declared snapshot hash and location count describe the full snapshot and cannot be recomputed from the slice alone. Larger networks, multiple campuses, wheelchair handling delays and variable traffic require new evidence.

The sensitivity, heterogeneous fleet and Pareto analyses were executed for one snapshot week with one run per cell, GA seed 42 and native termination; the exact-reference solves, the WP-E10 mixed-fleet re-run and the WP-E11 joint day campaign were executed and merged, and the historical fleet archives remain historical and are not pooled with the re-run rows. Validity limits include assumed confirmations, a captured matrix, heuristic route generation, assignment proofs conditional on fixed routes, and fleet minima conditional on generated menus. The approximate Pareto front excludes cost and lender availability and does not validate service accessibility, traffic realism or boarding-time assumptions. No superiority, causality or validated service quality is claimed; global day optimality or infeasibility is claimed only for the WP-E11 cells that carry a proof claim, under the day-plan rules of that subsection, over fully enumerated routes and for one snapshot week.

## References and implementation provenance

Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem. *Computers & Operations Research*, 31(12), 1985–2002. [doi:10.1016/S0305-0548(03)00158-8](https://doi.org/10.1016/S0305-0548(03)00158-8).

Review metadata: [EKSİK: method-note review date, checked baseline and access-history record]. [EKSİK: committed provenance confirming the source blobs at the checked baseline] [EKSİK: pending research-note provenance is outside the checked repository snapshot] These repository links support maintenance and can be omitted from a publication.

- [Timetable demand](../../src/services/daily-planning.ts), [daily orchestration](../../src/services/daily-plan-run.ts), and [preview endpoint](../../src/app/api/admin/dudullu-preview/route.ts).
- [Route jobs and bounded assignment](../../src/services/dudullu-preview.ts) and [displayed metrics](../../src/services/daily-plan-view.ts).
- [GA defaults and overlays](../../optimizer_api/strategies/ga_split_strategy.py), [seed resolution](../../optimizer_api/strategies/seed_utils.py), [GA engine](../../uniride_core/algorithms/ga_split_engine.py), and [split decoder](../../uniride_core/algorithms/string_split_decoder.py).
- [Core feasibility](../../uniride_core/algorithms/feasibility_certificate.py), [independent certificate](../../optimizer_api/verification/response_certifier.py), and [matrix binding](../../optimizer_api/routers/optimization.py).
- [Typed decoder](../../uniride_core/algorithms/typed_split_decoder.py), [typed GA](../../uniride_core/algorithms/ga_split_typed_engine.py), [day selection](../../uniride_core/planning/typed_day_selection.py), and [fleet-selection router](../../optimizer_api/routers/fleet_selection.py).
- [Fleet-scenario producer](../../src/services/fleet-scenario-run.ts), [typed vehicle assignment](../../src/services/typed-fleet-assignment.ts), and [archived ride-metric computation](../../src/services/plan-experiments.ts).
- [WP-E0 contracts](../../uniride_core/exact/wave_instance.py), [archive loader](../../scripts/exact_archive_loader.py), [exact-reference code](../../uniride_core/exact/) (route enumeration, AMPL backend, certification), [single-type gap runner](../../scripts/run_exact_wave_gaps.py), [typed exact menus](../../scripts/run_exact_typed_menus.py), [union-menu day level](../../scripts/run_exact_union_day.py), [gap report](../../scripts/plan_exact_gap_report.py), [exact-reference results](results/week-2026-10-05-exact/), [large + sedan re-run](results/week-2026-10-05-fleet-rerun-large-sedan/), [large + Doblò re-run](results/week-2026-10-05-fleet-rerun-doblo-cap3/), [exact-reference plan](../designs/EXACT_SOLVER_AMPL_DESIGN.md), and [heterogeneous fleet design](../designs/HETEROGENEOUS_FLEET_DESIGN.md).
- [WP-E11 joint day model design](../designs/JOINT_DAY_MODEL_DESIGN.md), [joint day runner](../../scripts/run_exact_day_joint.py), [run comparison](../../scripts/compare_exact_day_joint_runs.py), and [joint day results](results/week-2026-10-05-exact/wp-e11-joint-day/).
- [Exact single-route helper](../../uniride_core/algorithms/string_exact_tsp.py) (not a capacitated multi-route or day-level reference), [architecture](../../CURRENT_ARCHITECTURE.md), and [fair comparison protocol](../../ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md).
- [Prior planning notes](../DEMO_ROADMAP_2026-10-04.md) and [decision library](../DECISION_LOG.md).
