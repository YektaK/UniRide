# Daily student transport planning with separate passenger capacities

[EKSİK: dated method-note review provenance file] Checked code baseline: `f7b8570`. [EKSİK: committed method-note review provenance for this baseline] The sensitivity campaign and the heterogeneous fleet and Pareto analyses were executed and archived. The exact-reference solves and the fleet re-run for the typed exact comparison remain planned; the checked implementation contains only the WP-E0 contracts and offline archive loader.

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

For identical virtual vehicles this provides a conditional fleet minimum after heuristic routing. It is not a joint minimum over all possible routes. Comparing its count with a heterogeneous real fleet's vehicle count is insufficient: physical capacities, cooldowns, and assignment feasibility require separate evidence.

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

For each wave, a typed split decoder checks contiguous segments against each type's Sw and So pools, any shared total-capacity limit, and that type's ride and tour caps. Its dynamic programme minimises borrowed-type route count and then travel time, subject to the large-route quota, for a fixed giant tour. The campaign producer adds the `ga_split` all-large baseline and `ga_split_hf` quota options; the large+sedan campaign uses q = 0..3, the corrected minivan campaign q = 0..2, and L4 q = 0..4, bounded by the wave size. Duplicate GA options are removed by route partition, ignoring stop order. A CP-SAT model chooses one option per wave and labels its routes by feasible vehicle type, constraining the large-vehicle busy peak by L. The archived fleet campaigns used the lexicographic objective sedan count, sedan route minutes, total route minutes and option-index sum. The current implementation ranks sedan count, total route minutes, sedan route minutes and option-index sum, the originally specified order restored on 2026-10-13. Because sedan count is the first stage and all archived selections were solved to optimality, the archived sedan counts are unaffected; their sedan route minutes, total route minutes and selected options may differ under the current order. The current implementation shares one call's time allowance across the stages; it does not grant a fresh allowance to every stage. The archive records CP-SAT 9.15.6755, solver seed 20261008, one worker and a 30-second selection limit, separately from GA seed 42. The chosen fixed routes are independently assigned and checked in TypeScript for capacities, per-type ride/tour limits, overlap and cooldown before `proven_over_menu` is emitted. The archived verification reports 51 feasible runs passing its checks and 29 menu-infeasible rows with no routes.

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

An x denotes a menu-infeasible weekday; a dash denotes an unavailable weekly count because at least one weekday is infeasible. For A, daily minibus minima are 6 / 5 / 6 / 5 / 6 at R = 50, 5 / 4 / 6 / 4 / 5 at R = 60, 4 / 4 / 6 / 4 / 5 at R = 70, and 4 / 3 / 4 / 4 / 4 at R = 90.

![Weekly vehicles by scenario, R = 60](results/week-2026-10-05-fleet/figures/fleet_scenarios_R60.svg)

The following observations describe that single snapshot, one run per cell (GA seed 42, native termination), and the generated menus.

- **L1 has no feasible menu selection.** All 20 cells are `infeasible_for_L`: 15 are labelled `SW_DEMAND_EXCEEDS_LARGE_CAPACITY` and 5 `CROSS_WAVE_CONFLICT`. At R = 60, the largest Sw wave contains 5 passengers on Monday and Thursday, 4 on Friday, and 3 on Tuesday and Wednesday.
- **L2 is feasible on some weekdays.** It is feasible on 2 of 5 days at R = 50 and 3 of 5 at R = 60, 70 and 90, so none of these generated-menu scenarios provides a complete week with two minibuses. Of its 9 infeasible cells, 2 are labelled `SW_DEMAND_EXCEEDS_LARGE_CAPACITY` (Monday at R = 50 and 60) and 7 `CROSS_WAVE_CONFLICT`.
- **L3 has a feasible selection on every weekday at every R.** Peak daily sedan need is 4, 3, 3 and 1 at R = 50, 60, 70 and 90, respectively; Tuesday and Friday need no sedan at R = 90. At R = 60, Wednesday's three sedan windows are 11:15–12:36, 11:51–12:45 and 12:15–13:07. At R = 60, the other L3 sedan windows are 07:12–16:50 and 07:43–08:45 on Monday, 07:23–13:36 on Tuesday, 13:15–16:49 on Thursday, and 07:37–17:28 and 13:02–13:45 on Friday.
- **Vehicle count and route minutes describe different resources.** L3 and A have weekly counts of 7 versus 6 at R = 50, and equal counts of 6, 6 and 4 at R = 60, 70 and 90. Their respective weekly route-minute totals are 6967 versus 6822, 6472 versus 6450, 6048 versus 6053, and 5838 versus 5862. At R = 60 the passenger-weighted mean rides are 31.221239 minutes for A and 31.172566 for L3. These are descriptive comparisons of heuristic route sets. Summing the L3 daily rows gives 29 of 111 sedan routes at R = 50, 16 of 94 at R = 60, 10 of 81 at R = 70 and 3 of 73 at R = 90. The sedan shares of route minutes are the exact ratios 1775/6967, 931/6472, 513/6048 and 156/5838, respectively.
- **Sedan borrowing days depend on R.** L3 uses sedans on every weekday at R = 50, 60 and 70 and on Monday, Wednesday and Thursday at R = 90.

The proof label `proven_over_menu` applies to borrowed-vehicle count over the generated menus; a different routing could change the count, and `infeasible_for_L` means no feasible selection within those menus. All timetable legs are assumed confirmed, all So students are assumed able to use the declared borrowed type, and sedan Sw = 0 remains an unverified scenario assumption. The recorded failure codes distinguish a wave requiring more large routes than L from cross-wave overlap; they are not causal estimates. The same fixed arc times apply to both types; cost, lender availability, drivers and boarding times are not modelled. The [earlier fixed-route fleet what-if](results/week-2026-10-05-4sw5so/fleet_mix_analysis.md) only reassigns routes built for the large vehicle and provides an upper bound; it is not the typed-menu evidence used above.

#### Multi-objective trade-off (Pareto) analysis

An option combines a fleet family with owned minibus count L and ride limit R: all-large A, large+sedan L1–L4, or large+Doblò L0–L2. Each campaign uses at most two types; the extra scenarios are L4 with sedans and the corrected minivan campaign, rather than a simultaneous three-type solve. Doblò is modelled as `minivan:1sw3so:cap3:cd10`: at most 1 Sw, at most 3 So, and at most 3 passengers in total, with a 10-minute cooldown; an Sw passenger occupies a seat while the wheelchair is stowed. This is an assumed scenario model, not verified service accessibility; no `1sw2so` variant was run. The earlier `extra/minivan/` campaign allowed four passengers and is SUPERSEDED by [extra/minivan-cap3/](results/week-2026-10-05-fleet/extra/minivan-cap3/). The approved brief records a one-vehicle increase in the pure-minivan peak at every R after that correction, unchanged L1/L2 minivan peaks, and borrowed-hour changes of at most 2.7 hours for L1/L2. The valid extra archives use the same snapshot week, matrix, R grid and tour limit, GA seed 42, native termination and assumed confirmations, with one archived run per cell.

The ε-constraint analysis fixes L and R and minimises each day's borrowed-vehicle count over its generated route menus; a weekly option requires a feasible selection on all five weekdays. The reported objectives are f1, owned minibuses; f2, maximum daily distinct borrowed vehicles; f3, weekly borrowed busy hours (route minutes plus the 10-minute cooldown after each borrowed route, divided by 60); f4, weekdays with any borrowing; and f5, R and realised passenger-weighted mean ride. Here f4 counts borrowing days, while the separate CSV field `borrowed_vehicle_days` sums vehicles over days. Dominance is evaluated on (f1, f2, f3) within R and on (f1, f2, f3, R) across R; equal objective vectors do not dominate one another. The archive contains 36 options, comprising 32 non-derived options and 4 day-level hybrids, of which 28 are feasible. The recorded route/CSV checks cover 131 feasible-day runs with zero violations and 29 infeasible-day runs with no routes. Owned utilisation uses busy minutes over the common service span times owned capacity; borrowed utilisation uses busy minutes over first-start to last-end-plus-cooldown loan windows, and the before-10:00 share uses borrowed busy time.

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

**Corrections and their effect on reported results.** CX-01 replaced outward whole-minute interval rounding with centi-minute endpoints and cooldowns (`time_scale = 100`); off-grid values fail closed rather than being rounded. The recorded archive effect is none because the archived arcs and interval endpoints are whole minutes. (see `results/week-2026-10-05-fleet/cx01_replay_check.md`) CX-03 makes the typed GA decode cost-only for one type without an active quota, restoring the documented parity with the untyped GA; two-type quota decoding is unchanged. The typed campaigns used two types, and the single-type campaign used `ga_split`, so CX-03 does not change their reported routes. The core archives were produced at `6be127d`, `8ab88ca` and `4200acb`, before CX-01/CX-03, and each manifest records a dirty tree; L4 records `afc7208` and a dirty tree as well. These remain historical native, single-seed archives; the planned typed exact comparison requires a new campaign at one pinned commit.

## 7. Further study

Further studies can add individual passenger windows, boarding times, driver assignment, traffic-aware matrices and publication of approved daily plans, subject to separate contracts and evidence. Further work could examine anchor shifts, cooldown variation and class staggering as possible changes to the peak resource requirement. Heterogeneous routing with Sw/So pools is now represented by the archived scenarios, while a joint optimum over all route sets and vehicle types remains outside their evidence. Matrix-based clustering remains a separate research question; geometric grouping does not replace road-network evaluation.

The approved exact-reference plan uses complete feasible-route enumeration followed by two-stage set partitioning in AMPL: first route count for the single type, or borrowed-type route count under a large-route quota for a typed wave, then travel duration with the first-stage count fixed. Gurobi is the main solver and HiGHS the cross-check. Each solver call (stage 1, stage 2 and the free-duration-bound solve) has a 60-second wall limit, or 600 seconds on peak waves; a peak is the largest-leg wave per date, including ties. The archive census contains 57 waves and 226 legs per R, with 50 waves of 1–6 legs and a largest wave of 20; the five peak pickup waves are anchored at 08:45 and contain 20, 11, 11, 10 and 13 legs.

Before the typed comparison, WP-E10 will re-run both large+sedan and large+Doblò(cap3) campaigns at a clean pinned commit, using GA seed 42 and native termination, and archive every menu option's routes, minutes, intervals and certificate. A read-only preflight must match live inputs to the archive; mismatch stops the re-run for an owner decision, and archived input replay through the current production path is not the approved fallback. Historical typed rows will not be pooled with the re-run. The day comparison will solve GA menus and the union of GA and per-wave exact menus at one commit with `time_scale = 100`, without deduplicating exact options against GA options by partition alone. Only optimal results in both CP-SAT runs, with independent TypeScript assignment confirmation, can receive `proven_over_union_menu`; otherwise the prescribed labels include `union_not_proven` or `not_independently_confirmed`. A union solve lacking proof will be retried once at 60 seconds; none of these labels denotes a global day optimum.

Only WP-E0, the contracts and offline archive loader, is implemented at the checked baseline; no exact route enumeration, AMPL solve, WP-E10 re-run or exact-gap result is reported here. The existing exact single-route TSP helper is not a capacitated multi-route or day-level reference. Planned gap reporting distinguishes route-count bounds, duration bounds conditional on a proven first-stage count, and a separate free-count duration bound, with time-limited and unresolved cases labelled explicitly.

## 8. Validity and scope

The archived daily student counts are 27, 21, 23, 23 and 19 from Monday to Friday, and full-snapshot matrix provenance records 29 locations. Earlier planning notes reported 28 students in a D0 read-only inventory dated 2026-10-04. The archived matrices are per-date slices: their declared snapshot hash and location count describe the full snapshot and cannot be recomputed from the slice alone. Larger networks, multiple campuses, wheelchair handling delays and variable traffic require new evidence.

The sensitivity, heterogeneous fleet and Pareto analyses were executed for one snapshot week with one run per cell, GA seed 42 and native termination; the exact-reference solves and WP-E10 re-run remain planned. Validity limits include assumed confirmations, a captured matrix, heuristic route generation, assignment proofs conditional on fixed routes, and fleet minima conditional on generated menus. The approximate Pareto front excludes cost and lender availability and does not validate service accessibility, traffic realism or boarding-time assumptions. No superiority, causality, global optimality or validated service quality is claimed.

## References and implementation provenance

Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem. *Computers & Operations Research*, 31(12), 1985–2002. [doi:10.1016/S0305-0548(03)00158-8](https://doi.org/10.1016/S0305-0548(03)00158-8).

Review metadata: [EKSİK: method-note review date, checked baseline and access-history record]. [EKSİK: committed provenance confirming the source blobs at the checked baseline] [EKSİK: pending research-note provenance is outside the checked repository snapshot] These repository links support maintenance and can be omitted from a publication.

- [Timetable demand](../../src/services/daily-planning.ts), [daily orchestration](../../src/services/daily-plan-run.ts), and [preview endpoint](../../src/app/api/admin/dudullu-preview/route.ts).
- [Route jobs and bounded assignment](../../src/services/dudullu-preview.ts) and [displayed metrics](../../src/services/daily-plan-view.ts).
- [GA defaults and overlays](../../optimizer_api/strategies/ga_split_strategy.py), [seed resolution](../../optimizer_api/strategies/seed_utils.py), [GA engine](../../uniride_core/algorithms/ga_split_engine.py), and [split decoder](../../uniride_core/algorithms/string_split_decoder.py).
- [Core feasibility](../../uniride_core/algorithms/feasibility_certificate.py), [independent certificate](../../optimizer_api/verification/response_certifier.py), and [matrix binding](../../optimizer_api/routers/optimization.py).
- [Typed decoder](../../uniride_core/algorithms/typed_split_decoder.py), [typed GA](../../uniride_core/algorithms/ga_split_typed_engine.py), [day selection](../../uniride_core/planning/typed_day_selection.py), and [fleet-selection router](../../optimizer_api/routers/fleet_selection.py).
- [Fleet-scenario producer](../../src/services/fleet-scenario-run.ts), [typed vehicle assignment](../../src/services/typed-fleet-assignment.ts), and [archived ride-metric computation](../../src/services/plan-experiments.ts).
- [WP-E0 contracts](../../uniride_core/exact/wave_instance.py), [archive loader](../../scripts/exact_archive_loader.py), [exact-reference plan](../designs/EXACT_SOLVER_AMPL_DESIGN.md), and [heterogeneous fleet design](../designs/HETEROGENEOUS_FLEET_DESIGN.md).
- [Exact single-route helper](../../uniride_core/algorithms/string_exact_tsp.py), [architecture](../../CURRENT_ARCHITECTURE.md), and [fair comparison protocol](../../ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md).
- [Prior planning notes](../DEMO_ROADMAP_2026-10-04.md) and [decision library](../DECISION_LOG.md).
