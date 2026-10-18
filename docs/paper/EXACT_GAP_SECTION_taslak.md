## Exact reference and optimality gap of the genetic algorithm

This section compares the route sets of one genetic algorithm (GA) run with a per-wave exact reference for one snapshot week. The comparison only measures the gap; it does not rank the two methods.

### Method

**Data and GA side.** The measurement uses a single snapshot week, 2026-10-05 to 2026-10-09, with 57 waves and 226 passenger legs, ride limits R = 50, 60, 70 and 90 minutes and a tour cap of 150 minutes. The GA side is a single run of the route-first, cluster-second GA of §4.1 with seed 42 under the native termination protocol, the secondary protocol. For the single-type fleet (4 wheelchair positions, Sw, and 5 seated positions, So) the GA routes come from the archived campaign, produced at commit 6be127d with a dirty working tree. For the two mixed fleets they come from a re-run at commit f29aa3d with a clean tree that archived every menu option. Every gap below is the gap of that run, not of the GA in general.

**Exact reference per wave.** The exact reference solves each wave separately. All feasible routes of the wave are enumerated, with one column per multiset of (location, class) and vehicle type, carrying the cheapest feasible stop order. Because the travel-time matrix is non-metric, a stop order may revisit a location. A set-partitioning model then selects routes with integer multiplicities. It is solved in two lexicographic stages: the first minimises the number of routes, the second minimises total route duration D with that count fixed. For the single type the count is K; for a mixed fleet it is K_m, the routes of the minimised type. A separate solve without a count objective gives a duration lower bound, D_LB_free.

**Mixed fleets.** Two mixed fleets were studied: large + sedan and large + Doblò. The large vehicle is the minibus (4 Sw / 5 So); the sedan has 0 Sw / 4 So; the Doblò minivan carries at most 1 Sw, 3 So and 3 passengers in total. For each wave the exact menu mirrors the GA menu: a base option that uses the large type only, and q options with at most q large routes that minimise the routes of the small type. The two fleets give 1872 options, 1004 for large + sedan and 868 for large + Doblò.

**Solvers and limits.** The models were solved through AMPL, with Gurobi 13.0.3 as the primary solver. Each solver call had a wall-clock limit of 60 s, or 600 s on the per-day peak wave, the wave with the most legs. Gurobi also had a deterministic work limit of 20 work units, or 200 on peak waves. Every call used one thread and seed 0. Every optimal result was re-solved with HiGHS 1.15.1, and any disagreement in a proven value was defined as blocking.

**Certification.** Each exact route set and the archived GA route set of the same wave were checked by the same independent certificate, the operational response certifier, on the same captured travel-time matrix. Route counts and durations were recomputed from the certified routes in integer arithmetic and had to equal the solver objective.

**Protocol and gap definitions.** Exact results form a separate protocol, `exact_reference_v1`, and are never ranked, averaged or tested together with heuristic results. The only quantity that crosses the protocols is the gap of a GA result against a certified exact value. K* and D* are the proven optimal route count and total route duration of the exact reference for a wave or option; K_GA and D_GA are the GA's values for the same wave or option. The route-count gap is dK = K_GA − K*. The duration gap is gD = (D_GA − D*)/D*. It is defined only where K_GA = K*; where K_GA > K*, gD is undefined.

**Day level.** For the mixed fleets, the day's vehicle selection was solved by CP-SAT for each (fleet, date, R, L) cell, where L is the number of owned minibuses and limits the minibus peak. Cars are the peak number of concurrently busy small-type vehicles, including the 10-minute cooldown; the selection minimises cars first, then total vehicle-minutes, then car-minutes. Each cell was solved twice: once over the GA menus alone, and once over the union menu, which combines the GA and per-wave exact menus. The TypeScript vehicle-assignment check independently confirmed every selection. The union-menu result is the minimum car count over that union menu, not a global day optimum, because no day-level exact model was solved (out of scope). Results are never reported as min(GA, union).

**Reproducibility.** Every campaign is archived with a manifest that records the git commit, the solver and AMPL versions, the option strings and the input file hashes. The final mixed-fleet exact results come from a single clean serial run; an earlier parallel run was discarded. The exact routes are stored, so they can be re-certified without a solver licence.

### Results: week of 2026-10-05

**Single type (4 Sw / 5 So).** All 228 wave instances (57 waves × 4 values of R) were solved to proven optimality, and no solver limit was reached. HiGHS gave the same (K, D) and the same D_LB_free on all 228. Table X gives the gaps per R.

| R (min) | Waves with dK = 0 | Weekly routes, GA / exact | Waves with gD > 0 (of 56) | Mean gD | Max gD |
|---:|---:|---:|---:|---:|---:|
| 50 | 56 of 57 | 109 / 108 | 3 | 0.000552 | 0.018462 |
| 60 | 56 of 57 | 94 / 93 | 6 | 0.004200 | 0.089947 |
| 70 | 56 of 57 | 82 / 81 | 3 | 0.001067 | 0.027778 |
| 90 | 56 of 57 | 73 / 72 | 3 | 0.001135 | 0.034146 |

Table X. Single type; one seed-42 GA run under native termination, single snapshot week. Mean and max gD are taken over the 56 waves per R with K_GA = K*.

In each R, one 08:45 pickup peak wave has dK = 1. Figure X (`figure_gap_single`; single type; per-wave duration gap against students per wave) has one panel per R; Figure Y (`figure_gap_typed`) shows the two mixed fleets for each R, with base and q options separately; both are in `docs/paper/results/week-2026-10-05-exact/wp-e6-gap-report/`. Rows with dK ≥ 1 are not drawn, because their gD is undefined, and each panel gives their count.

**Mixed fleets, per-wave options.** Of the 1872 options, 1705 were solved to proven optimality and 167 were proven infeasible, all of them large + sedan q options. HiGHS agreed on every option: same (K, D) on the 1705 optimal options, same infeasibility on the 167 and same D_LB_free. In the 1703 option pairs where both sides had a solution, the exact optimum was never worse than the GA option of the same kind. In 2 options the GA found no solution while the exact model did; both are large + sedan options for the 2026-10-05 08:45 pickup wave with q = 2, at R = 50 and R = 60.

For the q options, dK compares K_m, the routes of the minimised small type (sedan or Doblò): dK = K_m,GA − K_m*. Per fleet and R, the share of q options with dK = 0 ranged from 0.9625 (large + Doblò, R = 50: 154 of 160) to 0.99375 (large + Doblò, R = 70 and 90: 159 of 160). dK never exceeded 1. Mean gD per (fleet, R) lay between 0.000339 and 0.003823. The largest single q-option value was 0.1317, for large + sedan at R = 90. The per-(fleet, R) values are in `docs/paper/results/week-2026-10-05-exact/wp-e6-gap-report/table_by_R.csv`. The base options of both mixed fleets repeat the single-type statistics exactly, because they use the same large type and the same GA base routes, so they are not independent results.

**Day level.** Table Y gives the outcomes per fleet and L.

| Fleet | L | Cells | Both CP-SAT runs optimal and TypeScript-confirmed | Union one car fewer | Union same | Union more | Both menus infeasible | GA-menu run proven infeasible, union run optimal and confirmed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| large + sedan | 1 | 20 | 0 | – | – | – | 20 | 0 |
| large + sedan | 2 | 20 | 11 | 1 | 10 | 0 | 8 | 1 |
| large + sedan | 3 | 20 | 20 | 3 | 17 | 0 | 0 | 0 |
| large + Doblò | 0 | 20 | 20 | 3 | 17 | 0 | 0 | 0 |
| large + Doblò | 1 | 20 | 20 | 2 | 18 | 0 | 0 | 0 |
| large + Doblò | 2 | 20 | 20 | 2 | 18 | 0 | 0 | 0 |

Table Y. Day-level vehicle selection over the GA menus and over the union menu, per fleet and L; one seed-42 GA run, single snapshot week.

Where both runs are optimal and confirmed, the union menu needs one car fewer in 4 and the same number in 27 of 31 cells for large + sedan, and one fewer in 7 and the same in 53 of 60 for large + Doblò; it never needs more. The union-only cell (large + sedan, 2026-10-05, R = 60, L = 2) needs 3 cars. Every cell with one car fewer selects an exact option for the 08:45 pickup wave.

**Limitations.** These results cover one snapshot week and one GA seed. The certificate, the GA and the exact model all assume no waiting time at stops, and the travel-time matrix is a fixed snapshot without traffic.
