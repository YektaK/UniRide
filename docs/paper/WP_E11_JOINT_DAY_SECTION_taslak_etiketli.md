### Joint day model (WP-E11)

The union-menu day level above (WP-E4b) picks one option per wave and gives the minimum car count over that menu, not a global day optimum [B20]. The day fleet depends on the busy intervals of the routes and their peak concurrency, not on per-wave (K, D), so a wave-optimal route set can be a poor day choice: a longer or extra route in one wave can free a vehicle for another wave [B20]. The joint day model of work package WP-E11 therefore chooses the routes of all waves of a date together, in one mixed-integer model per cell, from the full set of enumerated routes [B20, B24]. The owner reopened this question, so the earlier decision that a global day model is out of scope no longer holds; the results form a separate protocol, intended for a second paper [B34, B47]. "The prototype" below means the independent prototype scripts, with their own plan checker, that prompted WP-E11; their values serve only as reproduction targets [B34, B39, DL:668].

#### Method

**Cells, fleets and notation.** The grid is the snapshot week 2026-10-05 to 2026-10-09, R = 50, 60, 70 and 90 minutes and a tour cap of 150 minutes [B21]. A cell is (fleet, date, R) for the single type and (fleet, date, R, L) for the mixed fleets, where at most L large vehicles may be used [B21]. The fleets are the single type (4 Sw / 5 So), 20 cells; large + sedan with L = 1, 2 or 3, 60 cells; and large + Doblò with L = 0, 1 or 2, 60 cells; 140 cells in all [B1, B21]. Here V is the day vehicle count of the single type, the peak number of simultaneously busy vehicles, as §6 uses V for daily vehicles; the design file and the result files call this value K [B2, B23, B44]. S is the peak count of the minimised small type (sedan or Doblò), the cars of the day level above [B2, B23, B43]. K keeps its §7 meaning of a route count [B44].

**Day plan.** As in production, a day plan covers each occurrence of every wave exactly once with routes that respect the tour, ride and capacity limits of the vehicle type assigned to them [B22]. Pickup routes end and dropoff routes start at the wave anchor, without waiting; a vehicle is busy until the end of its route plus the 10-minute cooldown, and the vehicles needed of a type are the peak count of simultaneously busy intervals [B22].

**Objectives.** The objectives are lexicographic, each stage a separate solve [B23]. For the single type the model minimises V, then total vehicle minutes with V fixed; for the mixed fleets, with the large peak at most L, it minimises S, then total vehicle minutes, then car minutes [B23]. For the mixed fleets this is the order of the day level above; remaining ties are co-optimal alternatives, so results are compared on objective values, not on route identity [B23].

**Columns and exactness.** For each wave the columns are the full output of the route enumeration for the cell's types, R and tour cap: one column per feasible (multiset of (location, class), type), the same candidate routes as in the per-wave exact reference above (WP-E3 for the single type, WP-E4a for the mixed-fleet menus); a route that both types accept gives two columns, so the column choice decides the type [B20, B24, DL:587]. Any feasible day plan maps to a model solution that is no worse in any objective, because the column of a route has a tour that is not longer and so a busy interval that is not wider [B25]. The model optimum is therefore the global day optimum under these rules only when every wave of the date was enumerated completely; otherwise the cell is labelled `not_run_enumeration_cap` and no day claim is made [B24, B25].

**Model.** Integer multiplicities choose the columns, since one column can be needed twice in a wave; covering constraints meet each item count of each wave exactly, and at each route start of a type the selected routes busy at that point may not exceed V, L or S [B26]. All coefficients are integers; the lower bounds below serve only the labels and are not added to the model [B26].

**Lower bounds and certificates.** For the single type, LB0 is the largest sum, over the wave anchors, of the proven WP-E3 route minima of the waves whose routes must all be busy at that anchor, and LB0w widens these windows by each wave's smallest tour; LB0 comes from the prototype, and LB0w was added by owner decision [B27]. For the mixed fleets, LB_L does the same with the least numbers of large routes per wave, and LB_S subtracts L from the corresponding peak sum of least total route counts [B28]. If LB_L > L, no day plan with at most L large vehicles exists: tier 1, `certificate_capacity_floor`, uses only an arithmetic floor from Sw counts, and tier 2, `certificate_wave_min_large`, uses wave values on which both solvers agree [B29, B36]. Certificates are valid but not complete: on a separate test set of oracle days with unequal type cooldowns, not this week, they certified 63 of 107 infeasible cells, and in this week 15 of the 26 cells without a plan are certified [B3, B29]. Infeasibility without a certificate is accepted when both solvers prove it [B29].

**Solvers and limits.** The solver roles are the reverse of the rest of §7: HiGHS 1.15.1 through the `highspy` package is the primary solver, and Gurobi 13.0.3 through AMPL is the cross-check [B7, B30, B46]. Both solvers receive the same model object, not the same MPS bytes; the canonical MPS file and its sha256 are archived, and AMPL presolve is off in the cross-check [B30]. Each day-model solver call (one per stage) had 600 s, one thread, seed 0, relative gap 0 and absolute gap 0.99, and a stage counts as `optimal` only if the runner's own check incumbent ≤ ceil(bound − 1e-6) holds [B31]. A calibration run of 15 cells, each solved twice without a work limit, used at most 3.68 Gurobi work units and at most 242.69 s per HiGHS call; the owner then set a Gurobi work limit of 200 for the campaign and kept 600 s as a safety net [B19, B31].

**Labels and proof claims.** Each cell is labelled `optimal`, `infeasible_certified` (tier named) or `infeasible_solver_proven` (no certificate), or with one of the labels for open or rejected cells [B35]. A proof claim needs a proof label and `proof_claim_allowed` true: `optimal` and `infeasible_solver_proven` need the day-level cross-check `agree` (both solvers proven, same status, value and fixed inputs), a tier-2 certificate needs agreement on the wave values, and tier 1 needs neither [B36, B37]. In this text "no day plan with at most L large vehicles" is used only for `infeasible_certified`; `infeasible_solver_proven` is written "infeasible, solver-proven", and the WP-E4b labels stay "infeasible over the menu" [B35].

**Independent checker.** A separate checker that does not import the solver code rechecks every plan (coverage, capacities, arcs, tour and ride limits, anchored intervals, per-type peaks and objective values); wave routes are also certified with `certify_optimization_response`, and mixed-fleet plans are confirmed by `scripts/verify-typed-selection.ts` [B38].

**Protocol and reproducibility.** The results form the protocol `exact_day_joint_v1`, its own pooling group, never pooled with `exact_reference_v1` wave rows, `union_day_v1` (WP-E4b) rows or heuristic rows, and never reported as a minimum across protocols [B34, B39]. The campaign ran as one serial process without cache, at code commit `e45cd6bf` with a clean working tree, reading only committed source campaigns [B7, B32]. In the calibration run the two runs of each cell differed only in wall times, a repeat check on one machine and software version [B32]. The record is the third attempt, because the first two stopped on a transient AMPL licence failure and wrote nothing; a retry rule for such failures was decided later, is not merged, and the record ran without it [B8, B33].

#### Results: week of 2026-10-05

**Labels.** Of the 140 cells, 114 are `optimal` (all 20 single-type, all 60 large + Doblò and 34 large + sedan cells), 15 are `infeasible_certified` and 11 are `infeasible_solver_proven`, the last two groups all large + sedan [B3]. Every cell carries a proof claim, and no blocking defect occurred [B4]. The proof is two-solver agreement on the day model in 125 cells, a tier-1 certificate in 8 and a tier-2 certificate with two-solver agreement on the wave values in 7; in the 15 certified cells the day model was not cross-checked [B5]. The independent checker passed all 114 plans, and the run checks against the union menu and the archived peaks passed wherever they applied [B9].

**Single type (4 Sw / 5 So).** Table 7.3 gives V per date [B10]. Of the 20 cells, V is lower than the peak of the archived GA route set of the same date and R in 11 and equal in 9; against the peak of the WP-E3 route sets it is lower in 9 and equal in 11; it is higher in none [B10, B25].

| R (min) | 2026-10-05 | 2026-10-06 | 2026-10-07 | 2026-10-08 | 2026-10-09 |
|---:|---:|---:|---:|---:|---:|
| 50 | 6 | 4 | 5 | 4 | 6 |
| 60 | 4 | 4 | 5 | 4 | 5 |
| 70 | 4 | 4 | 5 | 3 | 4 |
| 90 | 3 | 3 | 4 | 3 | 3 |

Table 7.3. Single type; day vehicle count V per date, protocol `exact_day_joint_v1`, single snapshot week; every cell `optimal` with two-solver agreement. The GA-side comparison uses one seed-42 GA run under native termination and is descriptive, not a ranking [B5, B10, B34, B43].

**Mixed fleets against the union menu.** Table 7.4 compares S with the car count over the WP-E4b union menu [B12]. For large + Doblò, S is lower in 28 and equal in 32 of the 60 cells [B12]. For large + sedan, both protocols have a plan in 12 cells at L = 2 and 20 at L = 3; S is lower in 4 and 8 of them and equal in 8 and 12 [B12]. At L = 1 the joint model is infeasible in all 20 cells (15 certified, 5 solver-proven) and the union menu is infeasible over the menu; at L = 2, 6 cells are infeasible, solver-proven, and infeasible over the menu [B3, B12, comparison.csv]. In no cell does the union menu have a plan where the joint model has none [B12]. In two large + sedan cells (2026-10-06, R = 70 and 90, L = 2) the union menu is infeasible over the menu, while the joint model finds S = 2 [B13].

| Fleet | L | Cells | Joint: fewer cars | Equal | Joint: more cars | Joint plan, union infeasible over the menu | Joint infeasible (union infeasible over the menu) |
|---|---:|---:|---:|---:|---:|---:|---:|
| large + sedan | 1 | 20 | – | – | – | 0 | 20 |
| large + sedan | 2 | 20 | 4 | 8 | 0 | 2 | 6 |
| large + sedan | 3 | 20 | 8 | 12 | 0 | 0 | 0 |
| large + Doblò | 0 | 20 | 11 | 9 | 0 | 0 | 0 |
| large + Doblò | 1 | 20 | 9 | 11 | 0 | 0 | 0 |
| large + Doblò | 2 | 20 | 8 | 12 | 0 | 0 | 0 |

Table 7.4. Mixed fleets; small-type peak S of the joint day model (`exact_day_joint_v1`) against the car count over the WP-E4b union menu (`union_day_v1`), per fleet and L. The two protocols are shown side by side and not pooled; one seed-42 GA run, single snapshot week; descriptive, no ranking [B12, B34]. Joint infeasible: L = 1, 15 certified and 5 solver-proven; L = 2, 6 solver-proven [B3, B12].

**Weekly values.** Table 7.5 gives, per fleet, L and R, the weekly maximum of V or S and the sum over the five dates [B17]. For large + sedan, L = 1 is infeasible on every date (certified or solver-proven) and L = 2 has plans on 2 of 5 dates at R = 50 and on 4 of 5 at the other values of R, so no weekly value is given for them [B17].

| Fleet | L | R = 50 | R = 60 | R = 70 | R = 90 |
|---|---:|---:|---:|---:|---:|
| single type (4 Sw / 5 So) | – | 6 (25) | 5 (22) | 5 (20) | 4 (16) |
| large + sedan | 3 | 3 (11) | 2 (7) | 2 (5) | 1 (1) |
| large + Doblò | 0 | 7 (27) | 7 (26) | 7 (26) | 7 (26) |
| large + Doblò | 1 | 5 (20) | 5 (19) | 4 (16) | 4 (15) |
| large + Doblò | 2 | 4 (15) | 3 (13) | 3 (10) | 2 (8) |

Table 7.5. Weekly maximum of V or S (`weekly_fleet_max`) and, in brackets, the sum over the five dates (`vehicle_days_sum`), from `day_joint_week.csv`; protocol `exact_day_joint_v1`, single snapshot week, every cell with a proof claim; descriptive, no ranking [B4, B17]. For the mixed fleets both values are of S, the small type only; the large vehicles (at most L) are not counted [B2, B17].

**Reproduction of the prototype.** The prototype results that prompted WP-E11 are reproduction targets, never run inputs or tuning targets [B34, B39]. All 20 single-type cells and 59 of the 60 large + sedan cells are `equal`; the remaining large + sedan cell (2026-10-05, R = 90, L = 2) is `prototype_open`, where the prototype left S in {1, 2} and the campaign proves S = 2; the 60 large + Doblò cells have no external target [B15]. The weekly design targets (single-type fleet 6/5/5/4, 83 vehicle-days, 12 of 60 large + sedan cells with fewer sedans than the union menu, sedans 3/2/2/1 at L = 3) are equal on both sides; the minute targets were not recomputed [B16]. The prototype plans are not in the repository and were not checked, so this is agreement with unverified data [B15].

**First run and rerun.** A first full run (code `f77c2484`) left the large + Doblò cell 2026-10-08, R = 50, L = 2 without a proof claim, because the integrality test was applied to Gurobi's raw stage-3 objective 539.9999877; the fix tests the variable values and recomputes the objective from the rounded values [B14]. In this cell S = 2 against 3 cars over the union menu [B14]. In the full rerun, labels, V or S, minutes, plans and MPS hashes are equal to the first run in 140 of 140 cells, the repaired cell carries a claim, and 113 cells differ only in raw Gurobi bound values; the first run is kept as a superseded record and never pooled [B18].

**Runtimes.** The campaign took 10060.5 s of wall time; the longest cell took 568.31 s, the longest HiGHS call 110.25 s and the longest Gurobi call 3.64 s, and no day-model stage call came near the 600 s or the work limit; the wave-value calls are not recorded in the stage files and their times are not reported [B6, B7].

**Limitations.** These rows describe one snapshot week, one GA seed (42, on the GA side), one machine and one software version; they are descriptive and support no superiority, causality or generality claim [B34, B48]. Certificate coverage is not complete [B29]. The global day claim holds only where every wave is fully enumerated [B24, B25]. A scaling probe found complete enumeration up to about 80 students per wave at R = 50 and about 30 at R = 70 and 90 (26 stops) [B39, B50]; in this week no cell was labelled `not_run_enumeration_cap` [B3]. Larger waves would turn the model into a restricted master problem without a global claim, and the named upgrade path, branch-and-price, is not implemented [B39, B50, B51]. The day plan assumes no waiting at stops [B22].

---

## Proposed edits to existing sentences (for the lead)

Not applied to the method document.

1. M:3. Current: "... were executed and merged between 2026-10-15 and 2026-10-18. Section 7 reflects the repository at commit `6c02f9d`." Replacement: "The exact-reference work packages for the week of 2026-10-05 (route enumeration, AMPL set partitioning, the single-type and typed gap campaigns, the union-menu day level and the gap report), the mixed-fleet GA re-run for the typed exact comparison and the joint day model (WP-E11) were executed and merged between 2026-10-15 and 2026-10-22; Section 7 reflects the repository at commit [EKSİK: commit at which this subsection is inserted]." [B53, B40–B59 list item 1]

2. M:234. Current: "The union-menu result is the minimum car count over that union menu, not a global day optimum, because no day-level exact model was solved (out of scope); ..." Replacement: "The union-menu result is the minimum car count over that union menu, not a global day optimum; a global day model is reported separately under its own protocol at the end of this section (Joint day model, WP-E11); ..." [B20, B34, B47]

3. M:234. Current: "... for the same reason, a run labelled `infeasible_for_L` is infeasible over its menu, not proven infeasible for the day." Replacement: "... a run labelled `infeasible_for_L` is infeasible over its menu, not proven infeasible for the day; certified and solver-proven day-level infeasibility is reported only for the joint day model (WP-E11)." [B35, B55]

4. M:276. Current: "... while a joint optimum over all route sets and vehicle types remains outside their evidence." Replacement: "... while a joint day optimum over all fully enumerated routes and vehicle types is reported separately, for one snapshot week, in §7 (Joint day model, WP-E11)." [B25, B34, B51]

5. M:278. Current: "Exact references for TSP/ATSP and CVRP benchmark instances (GOAL 2, WP-E7 to WP-E9) are planned but not started; they wait for an owner decision on the instance set and time limits." Replacement: "Exact references for TSP/ATSP benchmark instances (GOAL 2, WP-E7 and WP-E8) were executed and merged under the instance set and limits decided by the owner; CVRP references (WP-E9) and instances with n > 100 are deferred." [B40–B59 list item 5]

6. M:284. Current (a): "... the exact-reference solves and the WP-E10 mixed-fleet re-run were executed and merged, ..." Replacement: "... the exact-reference solves, the WP-E10 mixed-fleet re-run and the WP-E11 joint day campaign were executed and merged, ..." [B52, B18] Current (b): "No superiority, causality, global optimality or validated service quality is claimed." Replacement: "No superiority, causality or validated service quality is claimed; global day optimality or infeasibility is claimed only for the WP-E11 cells that carry a proof claim, under the day-plan rules of that subsection, over fully enumerated routes and for one snapshot week." [B4, B25, B34]

7. M:82. Current: "It is not a joint minimum over all possible routes." Optional: add a cross-reference to the joint day subsection of §7 (WP-E11), so the two meanings of "joint" are not confused. [B40–B59 list item 7]

8. M:179-180 and M:185: no change needed; these sentences are scoped to generated menus and stay true (the joint model is also infeasible in all 20 L = 1 cells; it finds S = 2 in two L = 2 cells the menus call infeasible) [B12, B13]. Optional: a one-clause forward pointer to the joint subsection at M:180 and M:185.

9. M:127-136: no change needed; the table is scoped to fixed heuristic routes (GA seed 42), and the joint weekly fleet 6/5/5/4 is a different protocol [B17, B34]. Optional: a pointer at M:136; if the two are ever tabled together, they go in separate protocol-labelled columns [B34].

10. M:228. Current: "The models were solved through AMPL, with Gurobi 13.0.3 as the primary solver." Replacement: "The per-wave models were solved through AMPL, with Gurobi 13.0.3 as the primary solver; the joint day model at the end of this section reverses the roles (HiGHS primary, Gurobi cross-check)." [B46]
