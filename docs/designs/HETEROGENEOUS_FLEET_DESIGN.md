# Heterogeneous fleet scenarios: design

Status: **proposal for owner review**. Nothing here is implemented. Base: `WIP @ 6be127d`, 2026-10-07.
Owner requirements: 2026-10-07 handoff, summarised in §1. Decision IDs refer to `docs/DECISION_LOG.md`. This document reopens none of them.

## 1. Problem and scope

University management wants a decision-support estimate: given the current students and their weekly timetables, roughly how many vehicles are needed, and with which mixes of large minibuses and borrowed sedans.

| Scenario | Large count L | Computed |
|---|---|---|
| A | minimised (all-large) | minimum L, cars = 0 |
| B / C / D | fixed at 1 / 2 / 3 | minimum cars |

Each scenario is reported per day and per week. The report covers the cars needed, the time windows and minutes in which cars are used, vehicle-minutes by type, and student ride-time statistics. The grid is 5 weekdays × R ∈ {50, 60, 70, 90}, with tour limit 150 and cooldown 10. The headline is probably R = 60.

**Vehicle types.** Each type has its own capacity pools (Sw and So do not substitute) and per-type limits:

| Type | Sw | So |
|---|---|---|
| Large minibus | 4 | 5 |
| Sedan (Fiat Linea) | 0 | 4 |

- Sedan Sw capacity is an open owner question (Q1 in §10), so it is a parameter.
- **Optional shared seat limit (owner requirement 2026-10-09).** A type may set `total_capacity`: a route is feasible on the type iff Sw <= `sw_capacity`, So <= `so_capacity` and, when set, Sw + So <= `total_capacity`. Unset means pools only (behaviour unchanged). API: `VehicleTypeSpec.total_capacity` (>= 1, <= sw + so, else 422). CLI: `:capN` token, e.g. `minivan:1sw3so:cap3:cd10`; recorded in the manifest as `totalCapacity`.
- **Fiat Doblo (owner decision 2026-10-09):** 3 passenger seats in total (1 front + 2 rear), at most 1 of them a wheelchair user. That student sits in a seat and the chair is stowed in the back. Valid loads: 0 Sw + up to 3 So, or 1 Sw + up to 2 So. Model: `doblo:1sw3so:cap3`. The earlier `minivan:1sw3so` runs allowed 4 passengers (1 Sw + 3 So) and are superseded. The minibus keeps its chairs in place (4 Sw places + 5 So seats as separate pools) and the sedan stays 0 Sw + 4 So.
- The scenario-A baseline uses `ga_split`, which only knows the pools. A shared limit on the fixed type therefore fails closed (`BASELINE_TOTAL_CAPACITY_EXCEEDED`) when a baseline route exceeds it; the limit is enforced for the minimised type and in typed split, certificate and assignment.
- R, tour limit 150 and cooldown 10 are shared by default and can be set per type.

**Objective.** The objective is lexicographic: (cars, total vehicle-minutes) with L fixed. Cars are unbounded by default, with an optional cap.

**Fleet source.** The live `vehicles` record wrongly says 10 seated. Scenario fleets are therefore declared **explicitly** (CLI/config), never read from the DB, and recorded in the run manifest.

**Out of scope:**
- planning-page UI changes, publication and live writes;
- time-window (`use_time_windows=true`) typed routing (it is rejected in v1, see §5);
- exact routing (D05: not evaluated, an open research question).

### 1.1 Facts verified in source (this task)

| # | Finding | Evidence |
|---|---|---|
| F1 | `SplitDecoder` has one global `(sw_capacity, so_capacity, max_tour_duration, max_ride_time)`. Trip arcs break on either pool. The DP minimises cost only, with violations first. | `uniride_core/algorithms/string_split_decoder.py:121-153, 311-369, 208-228` |
| F2 | `solve_ga_split` ranks by `objective_key` = (feasible, vehicles, cost). The RNG is consumed only by init/evolve/diversify/tournament, never by decoding. | `uniride_core/algorithms/ga_split_engine.py:71-95, 177-184, 251-295, 298-431` |
| F3 | The same decoder serves PSO/GWO/HHO split engines (`meta_split_common.py`) and `cvrptw_decoder.py`. A change to `SplitDecoder` therefore touches academic paths. | `grep` of importers |
| F4 | `OptimizationRequest.vehicles` already exists. The certifier then does a one-to-one SW/SO matching of the *returned routes of that call* to listed vehicles, plus `fleet_size_violation` when routes > vehicles. | `optimizer_api/models/schemas.py:120-125, 230`; `optimizer_api/verification/response_certifier.py:161-218, 299-300, 584` |
| F5 | `runDailyPlan` reads the DB `vehicles` table. Virtual mode picks the DB signature as template. Each wave is sent with `sw/so_capacity = max` over the slice. | `src/services/daily-plan-run.ts:403-445, 474-499` |
| F6 | The archived campaign `docs/paper/results/week-2026-10-05` ran with the template **4 Sw / 10 So / cd 10** (manifest `virtual_template`). `plan_fleet_mix.py` and the paper's fleet-mix paragraph also use large = 4/10. | `run_manifest.json:71-75`; `scripts/plan_schedule_report.py:23`; `docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md:92, 146` |
| F7 | `assignPhysicalVehicles` is a DFS over (route → vehicle id) with the following properties: it minimises distinct vehicles; its lower bound is the peak with min cooldown plus a clique capacity matching; it breaks symmetry by signature/free-time; its budget is 50 000 nodes; `minimumProven` means the search completed. | `src/services/dudullu-preview.ts:623-879` |
| F8 | Within a wave, every route shares the exact anchor: pickup routes end at it and dropoff routes start at it. All routes of one wave are therefore pairwise concurrent and need distinct vehicles. | `dudullu-preview.ts:489-510` (interval construction) |
| F9 | OR-Tools (CP-SAT) is already a runtime dependency. | `optimizer_api/requirements.txt:17` |

**Consequence of F6.** Every existing number (campaign, paper, `fleet_mix.csv`) assumes 10 So seats on the large vehicle. With the corrected 5 So, results will change materially. They must be published as a **new, labelled campaign** and must not silently replace the archived one (AGENTS: academic results must not change silently; P04).

## 2. Recommended approach in one picture

```text
per day, per R:
  waves (direction, anchor)  ──►  wave menu: for q = 0..Lmax  ga_split_hf(wave, large quota q)  ─┐
                                  + baseline option: scenario-A routes of the wave             │ certified per call
                                                                                               ▼
  per scenario L:  day selection (CP-SAT over menu)  ─►  chosen fixed routes + type labels
                   ─►  independent TS typed assignment (exact for fixed routes, node budget)
                   ─►  physical witness (vehicle ids per type), proven/witness status
```

- Scenario A is the existing single-type pipeline, run with the explicit template `large:4sw5so`. With a capped FIXED type (`:capN`), scenario A cannot be computed (`ga_split` does not know the shared limit), so the day fails closed with `BASELINE_TOTAL_CAPACITY_EXCEEDED`.
- One menu with `Lmax = 3` serves B, C and D. Each scenario uses only the options with `q ≤ L`.

## 3. Q1: routing with types

### 3.1 Wave level: a typed split decoder with a large-route quota

This new pure module is `uniride_core/algorithms/typed_split_decoder.py`. `SplitDecoder` is not modified.

For a giant tour `s_1..s_n` and types `T`, each type `t` has `(sw_t, so_t, R_t, tour_t)`. The minimised type is `m` (sedan) and a quota type `ℓ` (large) has quota `q`. The decoder then works as follows:

- **Arc feasibility.** Arc `(i, j]` is feasible for type `t` when the following hold for the segment: its Sw ≤ `sw_t`, its So ≤ `so_t`, its Sw + So ≤ `total_t` when `total_t` is set, its tour ≤ `tour_t`, and its longest ride ≤ `R_t`. The ride and tour definitions are the same as F1.
- **DP.** The DP is a resource-constrained shortest path with labels `V[j][k]`, where `k` = large routes used (0..q). The value is the lexicographic pair (routes of type `m`, cost).
- **Transitions.** A car arc adds `(1, c_ij)` and keeps `k`. A large arc adds `(0, c_ij)` and sets `k+1 ≤ q`.
- **Answer and labels.** The answer is `min_k V[n][k]`. Every route is returned with the type that realised it.
- **Complexity.** The cost is `O(n²·(q+1)·|T|)`. Waves have n ≲ 20 and q ≤ 3, so this is negligible.
- **Tie-breaking.** Ties break exactly as in `SplitDecoder`: strict `<` on the value, with the first predecessor kept. A one-type, unlimited-quota instance then reproduces `SplitDecoder` routes (parity test P3).
- **Infeasible tour.** If no feasible split exists, the decoder returns `feasible=False`. **There is no singleton fallback.** The `SplitDecoder` fallback is a known certificate-gated hazard (CURRENT_ARCHITECTURE §5), and a typed singleton could also exceed the quota.

The GA wrapper is `solve_ga_split_typed` in a new module `uniride_core/algorithms/ga_split_typed_engine.py`:
- It reuses the exported GA helpers (`initialize_population`, `evolve_population`, `diversify_population`, `educate_individual`, `tournament_selection`) and the same `rng` discipline.
- Its fitness key is `(infeasible, routes_m, cost)`.
- The typed GA loop body duplicates about 60 lines of the `solve_ga_split` loop. This is deliberate, so that `ga_split_engine.py` has **zero diff**. A later dedupe is allowed only behind parity gate P1.

**Why quota, not "cheapest type per segment".** Both types use the same matrix, so travel costs are equal. With lexicographic car minimisation and no quota, every segment would be labelled large and there would be no cars. Cars only appear because large routes are scarce. The scarcity is per wave (F8): a wave with `k` large routes needs `k` large vehicles at the same moment. That is why the quota `q ≤ L` is the natural wave-level coupling variable.

### 3.2 Day level: why the wave quota is not enough

L limits large routes that are active at the same time **across** waves:
- a large vehicle busy on the 09:00 pickup wave until `end + cooldown` cannot start the 09:00 dropoff wave;
- in practice it often cannot start a 10:00 pickup route that leaves at 09:05 either.

Choosing `q_w = L` in every wave is therefore generally infeasible at day level. Choosing `q_w` too small inflates cars. The true coupling is a resource profile over the whole day, per type, with each type's cooldown.

**Key structural fact.** Vehicles of one type are identical. Under cooldown, route `r` occupies `[start_r, end_r + cd_t)`, and two routes can share a vehicle of type `t` iff these extended intervals are disjoint. The routes of type `t` form an interval graph, which is perfect. The vehicles needed of type `t` therefore equal the **peak number of simultaneously active extended intervals**, and greedy first-fit in start order attains it. For fixed routes, the typed problem reduces to choosing a label per route such that:
- peak(large) ≤ L;
- peak(car) is minimised.

No search over vehicle identities is needed.

### 3.3 Recommended decomposition: wave menu + exact day selection over the menu

1. **Menu.** For each wave `w` and each `q = 0..min(Lmax, n_w)`, call `/optimize` with `algorithm: "ga_split_hf"` and `max_routes(large) = q` (seed as today, D05). This gives at most 4 options per wave, and certified, infeasible calls are simply absent. For example, `q = 0` is infeasible whenever the wave has a Sw student and the sedan has Sw = 0. Add the **baseline option**: the wave's scenario-A routes, labelled later by the master.
2. **Day selection (exact over the menu).** This is a new pure module `uniride_core/planning/typed_day_selection.py` using CP-SAT. It is exposed through an internal, key-protected endpoint `POST /api/v1/internal/fleet-selection` (see §6). The model:
   - Binary `y[w,o]` selects one option per wave.
   - Each route `r` of option `(w,o)` gets `x_r` (large) and `c_r = y − x_r` (car). `c_r = 0` when `r` is not car-feasible, and `x_r = 0` when not large-feasible.
   - At every route start time `e` (sufficient by perfectness), each of the following sums runs over the routes active at `e` under that type's cooldown:
     - `Σ x_r ≤ L`;
     - `Σ c_r ≤ C`.
   - Optional constraint: `C ≤ Cmax`.
   - Stage 1 minimises `C`. Stage 2 fixes `C*` and minimises total vehicle-minutes `Σ minutes·y`.
   - Stage 3 is a deterministic tie-break: fewer car-minutes, then the lowest option index (owner may change, Q5).
   - Settings: `num_workers=1`, a fixed solver seed, and a time limit.
   - Status: `OPTIMAL` → `proven_over_menu`; `FEASIBLE` → `witness`; `UNKNOWN` → `indeterminate`; `INFEASIBLE` → `infeasible_for_L`, with a diagnostic (see 3.4).
3. **Independent verification.** The chosen fixed routes and labels go to the TS typed assignment (§4). That code is a different implementation in a different language. It recomputes the minimum cars for those fixed routes, proves or refutes it, and emits the physical witness (V01/V02 producer/verifier separation).

**Properties that become tests:**
- **Monotonicity.** When the selections are proven (`OPTIMAL`), `cars(L=3) ≤ cars(L=2) ≤ cars(L=1)` holds by construction, because the menus are nested and a selection for L−1 is feasible for L.
- **Dominance over the fixed-route what-if.** The baseline option keeps the result no worse than `plan_fleet_mix.py`-style labelling of scenario-A routes. The comparison must use the same R, the same template and the same seed.
- **Zero cars at the scenario-A minimum.** `cars = 0` for every `L ≥ L_A*`.

### 3.4 Honest optimality limits

| Level | Claim allowed | Not claimed |
|---|---|---|
| Wave typed split | optimal labelling/partition **for a given giant tour** and quota | optimal routes (GA is heuristic; D05) |
| Menu | contains one GA solution per quota plus the baseline | that it contains the globally best route set |
| Day selection | minimum cars **over the menu**, when CP-SAT reports OPTIMAL | global minimum cars |
| TS typed assignment | exact minimum cars for the **chosen fixed routes** (proven or witness) | anything about other route sets |

**Known blind spots:**
- Wave routes are built without seeing other waves. A slightly longer route that ends after a neighbour wave's start is not penalised.
- The menu varies only the quota, not route duration.

**Possible later extension (not in this package).** Add a "short-routes" menu variant per (w, q) that minimises the latest route end. The day selection is unchanged.

**Structural infeasibility to expect.** Suppose the sedan has Sw = 0 and some wave has more than `4·L` Sw students, or Sw students too dispersed for R. Then L is infeasible whatever the cars. Scenario B (L = 1) can fail this way on a day whose single wave holds 5 Sw students. This is reported per day as `infeasible_for_L` with reason `SW_DEMAND_EXCEEDS_LARGE_CAPACITY`, and with the lower bound `L ≥ max_w ⌈Sw_w / 4⌉`. It is exactly where the sedan-Sw question (Q1) matters.

### 3.5 Alternatives considered

| Alternative | Verdict | Reason |
|---|---|---|
| Typed decoder labelling each segment with its cheapest feasible type, no quota | rejected | Equal costs plus car minimisation label every segment large, so there are no cars. It also ignores the L coupling entirely. |
| Post-hoc re-splitting of single-type routes into car-sized pieces | rejected as a method; kept as baseline | Routes were shaped for large capacity, and cutting them violates ride/tour structure or multiplies cars. Its fixed-route variant already exists (`plan_fleet_mix.py`) and enters the menu as the baseline option. |
| Full HFVRP extension of `ga_split` (types in the chromosome, HGS-style) | rejected | The split DP already labels optimally for a given tour, so a typed chromosome adds search space without benefit. Editing the shared engine also risks academic parity (F3). |
| Iterative quota repair (start `q_w = L`; on a day-level conflict decrement the cheapest wave; repeat) | rejected as primary; acceptable fallback if CP-SAT is vetoed | It is greedy and order-dependent, has no optimality statement over its own options and can cycle. CP-SAT over the same menu is exact and tiny (≈ 12 waves × 5 options × ≤ 6 routes). |
| Day-level DFS in TS over option × label | rejected | Options have different start times, so a chronological DFS must interleave option choice with labelling. The search becomes complex, and exactness is harder to argue than a 200-variable CP model. |
| CP-SAT / set-partitioning exact routing for small waves | deferred, not rejected | D05: exact routing has never been evaluated. It is a candidate for later optimality-gap measurement of the wave level. |

## 4. Q2: day-level typed assignment (TS)

There is a new sibling `assignTypedVehicles` in a new file `src/services/typed-fleet-assignment.ts`. It shares the interval types with `dudullu-preview.ts`. **`assignPhysicalVehicles` stays byte-identical**, so the planning page is unaffected.

**Input:**
- fixed intervals `{start, end, swCount, soCount, …}`;
- types `{typeId, sw, so, cooldownMinutes, role: "fixed" | "minimise", count?}`;
- for B/C/D: large `count = L`, sedan `minimise` with an optional cap;
- `nodeBudget`, default 200 000 and configurable.

**Algorithm (generalises `plan_fleet_mix.feasible`):**
1. **Eligibility per interval.** An interval may use a type only when its Sw and So fit that type's pools. Intervals no type can carry give `blocked_data` with `TYPE_CAPACITY_UNCOVERED`.
2. **Bounds.**
   - `LB_fixed`: the peak of intervals eligible *only* for the fixed type, with that type's cooldown; if it exceeds `L` the result is `infeasible_for_L`.
   - `LB_C`: the maximum over start times `e` of `active_all(e) − L`, using the smaller cooldown, floored at 0. A fixed type can serve any interval it fits, so this bound is sound when the fixed type dominates. When the types are not nested (e.g. a sedan with more Sw than the large), use `LB_C = peak(car-only intervals)`.
3. **Decision search.** For `C = LB_C, LB_C+1, …`, test `feasible(L, C)`. This is a DFS over intervals in start order, labelling each interval with one of its eligible types. The state is the sorted tuple of busy-until times per type, after dropping those ≤ the current start. A label is pruned when the type's active count would exceed its count. Dead states are memoised, as in `plan_fleet_mix.py`. There is no vehicle-identity branching (§3.2), which removes the F7 permutation blow-up.
4. **Status:**
   - `proven`: every `C' < C` was refuted with no budget hit;
   - `witness`: a feasible C was found but some smaller C hit the budget;
   - `indeterminate`: no feasible C was found within the budget;
   - `infeasible_for_L`: from step 2, or when C exceeds the cap.
5. **Physical witness.** Greedy first-fit per type in start order (optimal on interval graphs) gives the vehicle ids `L1..LL`, `C1..CC`. The witness is then independently re-checked against capacity per vehicle (Sw = 0 on a 0-Sw sedan is enforced here too) and against cooldown-separated non-overlap.
6. **Output additions:**
   - `countsByType`, `lowerBoundsByType` and `assignments[].vehicleType`;
   - `carUsageWindows`: per car the first start, last end, busy minutes, route count and waves;
   - `hourlyOccupiedVehiclesByType`.

**Single-type check.** With one type of role `minimise`, the result equals `assignPhysicalVehicles` (`minimumVehicles`, and proven status when that search completes). Test T6 checks this on the archived routes.

## 5. Q3: certificate

| Layer | New check | Violation type |
|---|---|---|
| `uniride_core/algorithms/feasibility_certificate.py` | `check_typed_capacity(routes, demands, route_types, type_caps)`: per route, Sw ≤ cap_sw(type) and So ≤ cap_so(type). An unknown or missing type is a violation. A sedan with `sw_capacity = 0` therefore rejects any Sw passenger. | `typed_capacity_violation`, `vehicle_type_unknown` |
| same | `check_type_quota(route_types, quotas)` per call | `type_quota_violation` |
| `optimizer_api/verification/response_certifier.py` | When `vehicle_types` is set, each route must carry `vehicle_type`. Capacity is checked per route against its type, not against the global caps. `check_duration` and `check_ride_time` run with the **type's** limits on the authoritative matrix (O01). The existing `vehicles` matching and global-cap branches are untouched when `vehicle_types` is absent. | as above |
| TS `validateRoute` / typed assignment | re-checks the route's Sw/So against the declared type and the assigned physical vehicle | `TYPE_CAPACITY_MISMATCH` reason code |

The fail-closed rules match today's. A typed response with a missing type label is infeasible, never defaulted to the large type.

## 6. Q4: API and contract changes (optional and additive only)

**`OptimizationRequest`** (`optimizer_api/models/schemas.py`):

```text
vehicle_types: Optional[List[VehicleTypeSpec]] = None     # 1..4 entries, unique type_id
minimize_type: Optional[str] = None                        # must name one of vehicle_types
VehicleTypeSpec:
  type_id: str  (pattern ^[a-z][a-z0-9_-]{0,31}$)
  sw_capacity: int >= 0;  so_capacity: int >= 0;  sw+so >= 1
  max_ride_time: Optional[int] (1..600)   # default: request.max_ride_time
  max_travel_time: Optional[int]          # default: request.max_travel_time
  max_routes: Optional[int] >= 0          # per-call quota; None = unlimited
```

**Validation (fail closed, 422):**
- `vehicle_types` requires `algorithm == "ga_split_hf"`, and `ga_split_hf` requires `vehicle_types`;
- `vehicle_types` and `vehicles` are mutually exclusive;
- `use_time_windows=true` with `vehicle_types` is rejected in v1;
- explicitly set `sw_capacity`/`so_capacity` must equal the maximum over the types (checked via `model_fields_set`), or else be omitted;
- the counts fall under the existing compute-policy ceilings.

**Rejected: reusing `vehicles` for types (F4).** Its semantics is a per-call physical list with `fleet_size_violation`, and virtual mode caps it at `OPTIMIZER_MAX_VEHICLES`. That cap would silently bound cars, and it carries no per-route type in the response.

**Response.**
- `VehicleRoute.vehicle_type: Optional[str]`.
- `OptimizationResponse.fleet_mix: Optional[Dict[str, int]]` (routes per type).
- `algorithm_used = "ga_split_hf"`.
- `vehicle_id` keeps its current free-text form.
- All new fields default to absent, so existing clients (`optimizerResultSchema` in TS, the planning page) parse unchanged.

**Strategy registration.** `ga_split_hf` is an operational strategy only. It is not registered in the academic catalog/capability manifests (A02), is not part of `/compare` defaults, and carries `termination_protocol: native` (A04). It has no evaluation-budget or superiority claims.

**New internal endpoint.** `POST /api/v1/internal/fleet-selection` is internal-key protected like `matrix-snapshot`:
- **Request:** options per wave with route intervals, labels feasibility and minutes, plus types, L, the optional car cap and a time limit.
- **Response:** the chosen option per wave, labels, C, minutes, `status` and the solver statistics.
- It has no DB access and no matrix access (pure).
- **Rejected alternative:** a Python subprocess from the CLI. It is lighter, but it would diverge from the W02 rule that TS orchestrates through canonical FastAPI/core, and it could not be reused by the planning page later.

**Planning layer.**
- `runDailyPlan` keeps its signature and behaviour.
- Extract and export, without behaviour change, the demand/matrix/wave-grouping steps as `loadDailyPlanInputs`. This is covered by the existing `daily-plan-view`/`dudullu-preview` tests plus a new "extraction parity" test.
- Add a new `runFleetScenarioDay` in a new file `src/services/fleet-scenario-run.ts`. It **never reads the `vehicles` table**; types come only from its parameters.
- The default single type stays as today.

## 7. Q5: academic parity

| ID | Test | Proves |
|---|---|---|
| P0 | **Golden capture at `6be127d` before any edit**. Fixed instances are tiny12 EUC and three synthetic Dudullu-like waves (pickup/dropoff, R ∈ {50, 90}). Seeds are 0, 42 and 1234. JSON goldens record `best_individual.chromosome`, routes, costs and `generations` for `solve_ga_split` and the PSO/GWO/HHO split engines. | baseline |
| P1 | Re-run P0 on every later commit and require byte-identical JSON. | default `ga_split` and the shared decoder unchanged |
| P2 | Zero-import guard: no module under `academic_benchmark/` or the academic registry imports `typed_split_decoder`, `ga_split_typed_engine` or `typed_day_selection`. | gating by construction |
| P3 | Property test (500 random instances, seeded): `TypedSplitDecoder` with one type and unlimited quota gives the same routes, costs and route count as `SplitDecoder` for both directions, with and without R. | typed generalises untyped |
| P4 | `solve_ga_split_typed` with one type and no quota gives the same routes and the same `generations` as `solve_ga_split` for the same seed. This holds because the RNG stream is identical (F2) and, for one type and no quota, the inner split decode is cost-only like the untyped DP (CX-03). With two or more types or a quota the typed inner decode is count-first (routes of `minimize_type`, then cost), which is intended for borrowed-vehicle minimisation and differs from the untyped objective by design (decision H04). | wrapper parity |
| P5 | Existing suites pass unchanged: the three canonical pytest suites (`uniride_core/tests`, `optimizer_api/tests` and the academic suite) and the Vitest suite. | no regression |
| P6 | API: a request without `vehicle_types` produces a response JSON byte-identical to `6be127d`, on mocked matrix fixtures. | additive contract |

## 8. Q6: experiment CLI and outputs

```text
npm run experiments:fleet -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 \
  --fleet-types large:4sw5so:cd10,sedan:0sw4so:cd10 --fixed-type large --minimize-type sedan \
  --scenarios A,1,2,3 [--max-cars N] [--node-budget 200000] [--selection-time-limit 30] --out .temp/experiments/fleet-<date>
```

- **Type grammar:** `<id>:<n>sw<m>so[:cd<min>][:r<R>][:t<T>]`. The optional per-type R and tour default to `--ride-limits` / `--tour-limit`. For example, `sedan:1sw3so` tests Q1 without code changes.
- **Scenarios:** `A` = all-large minimum, and integers are the fixed L.
- **Fail-closed behaviour:** an unknown type, a duplicate id or a missing `--fixed-type`/`--minimize-type` is a usage error. Like today, the runner refuses an existing `--out`.

| File | Content |
|---|---|
| `run_manifest.json` | Everything in the current manifest (commit, dirty flag, GA defaults/effective config/seed, matrix sha per run, rate-limit waits), plus: `fleet_types` exactly as parsed, `fleet_types_source: "cli"`, `db_vehicles_consulted: false`, scenarios, car cap, node budget, CP-SAT version/seed/time limit, menu sizes per wave, and a selection and assignment status per (day, R, scenario). |
| `scenario_daily.csv` | date, weekday, R, scenario, L, cars, cars_status, large_routes, car_routes, routes, waves, students, legs, large_vehicle_minutes, car_vehicle_minutes, total_vehicle_minutes, ride_mean, ride_median, ride_p90, ride_max, car_first_start, car_last_end, car_busy_minutes, reason_codes |
| `scenario_weekly.csv` | week_of, R, scenario, L, weekly_cars (max over days), cars_per_weekday (Mon..Fri), complete_week, all_proven, minutes by type, passenger-weighted ride mean, ride max |
| `car_usage_windows.csv` | date, R, scenario, car_id, window_start, window_end, busy_minutes, routes, waves |
| `<date>_R<R>_<scenario>.response.json` | anonymised as today (U01), with types and labels |

Ride statistics are passenger-weighted pure travel, measured on the authoritative arcs the way `routeMetrics` does it. Vehicle-minutes are route travel minutes, with cooldown and idle time excluded, the same definition as `total_vehicle_minutes` today.

The figures come from `scripts/plan_fleet_scenarios.py` (standard library, SVG, same style as `plan_resource_profile.py`):
1. **Scenario comparison.** Grouped bars of cars per weekday for B/C/D, with A shown as a reference line of `L_A*`. There is one panel per R and the R = 60 panel comes first. Unproven values are hatched.
2. **Resource profile by type.** Step chart of active large and active car vehicles (cooldown layer included) over the service day, per (day, R = 60, scenario).
3. **Frontier.** (L, cars) per R from the weekly table, overlaid on the archived fixed-route frontier. The overlay is labelled "4/10 archived", because those numbers are not comparable (F6).

## 9. Q7: verification plan

| Layer | Tests | Oracle |
|---|---|---|
| Typed decoder | Unit tests:<br>• Sw on a 0-Sw sedan is never labelled car;<br>• the quota is respected;<br>• per-type R and tour limits;<br>• a missing arc gives an infeasible result (FIX-10 analogue);<br>• no singleton fallback. | hand cases |
| Typed decoder | **Brute force**: n ≤ 8, all contiguous partitions × all type labels of a fixed tour; the lexicographic optimum must equal the DP. 1 000 seeded instances. | enumeration |
| Typed GA | P4, determinism (two runs give identical output), certificate always feasible on success | — |
| Certifier | One test per violation type; absence of `vehicle_types` is byte-identical (P6); type limits are applied on matrix durations | — |
| Day selection | **Brute force**: ≤ 4 waves × ≤ 3 options × ≤ 3 routes, enumerating all option and label combinations and computing per-type peaks; equal C and equal minutes. Monotonicity in L; zero cars at `L ≥ L_A*`; INFEASIBLE when Sw exceeds `4L`. | enumeration |
| TS typed assignment | **Brute force**: ≤ 9 intervals, all labellings × peaks. T6: single type equals `assignPhysicalVehicles` on archived routes. **T7**: on the archived week-2026-10-05 routes with types large 4/10 and car 0/4, it reproduces every (L, C) in `fleet_mix.csv` and the proven flags. Budget exhaustion returns `witness`/`indeterminate`, never `proven`. | enumeration, archived CSV |
| Orchestrator | Mocked optimizer/DB:<br>• the `vehicles` table is never queried;<br>• the manifest records the types;<br>• an infeasible menu entry is skipped and recorded;<br>• `loadDailyPlanInputs` extraction parity. | mocks |
| Regression | **R1 (offline, deterministic)**: replay the archived responses through scenario reporting with the single type `large:4sw10so`. vehicles_required, routes and total minutes equal `summary.csv`. **R2 (live, optional)**: run the CLI with `--fleet-types large:4sw10so --scenarios A`. It must reproduce `summary.csv` for every date/R whose matrix sha and demand equal the archive. Days where these differ are reported as divergent, not failed. | archived campaign |

## 10. Work packages

Each package gets its own worktree, branch and reviewer, and is merged with `--no-ff` (P01). The order is binding.

| WP | Content | Main files | Tests and acceptance | Risk | Effort |
|---|---|---|---|---|---|
| 0 | Parity harness and goldens at the base commit | `uniride_core/tests/golden/…`, `uniride_core/tests/test_split_parity_golden.py` | P0 captured; P1/P2 green on the base | low | 0.5 d |
| 1 | Typed split decoder (pure) | `uniride_core/algorithms/typed_split_decoder.py` + tests | brute force, P3, unit cases; P1 still green | medium | 1.5 d |
| 2 | TS typed fixed-route assignment | `src/services/typed-fleet-assignment.ts` + tests | brute force, T6, T7 (reproduces `fleet_mix.csv`) | medium | 1.5 d |
| 3 | Typed GA engine, `ga_split_hf` strategy, schema fields, typed certifier | `ga_split_typed_engine.py`, `optimizer_api/strategies/ga_split_hf_strategy.py`, `schemas.py`, `feasibility_certificate.py`, `response_certifier.py` | P4, P6, certifier violation tests, the 422 validation matrix, P5 | **high** (API and certificate contract) | 2 d |
| 4 | Day selection (CP-SAT) and internal endpoint | `uniride_core/planning/typed_day_selection.py`, the router, compute-policy bounds | brute force, monotonicity, infeasibility diagnostics, auth 403 test | medium | 2 d |
| 5 | Orchestrator and CLI | `src/services/fleet-scenario-run.ts`, `scripts/run-fleet-scenarios.ts`, `daily-plan-run.ts` (extraction only), `plan-experiments.ts` (parsers/CSV) | orchestrator mocks, R1, extraction parity, manifest schema | medium | 2 d |
| 6 | Figures and report section | `scripts/plan_fleet_scenarios.py`, results README | figures from the R1 fixture; unproven values are visibly marked | low | 1.5 d |
| 7 | Campaign run, corrected types (owner-gated) | `docs/paper/results/week-<date>-fleet/` (new directory, archive untouched) | R2 divergence report; all-proven flags reported; no superiority or causality wording (A04) | low technical / **high claim** | 1 d |

Total ≈ 12 developer days. Packages 1 and 2 can run in parallel after 0.

**Owner gates:**
- before WP7: Q1–Q4;
- before any paper text changes: Q6.

## 11. Open questions for the owner

| # | Question | Default until answered | Why it matters |
|---|---|---|---|
| Q1 | Can a Fiat Linea safely carry 1–2 Sw (e.g. 3 So + 1 Sw, or 2 + 2)? Powered chairs probably cannot be folded into the trunk; is there a transfer-seat option or a ramp vehicle? | `0sw4so` | Decides scenario B feasibility on days with >4 Sw in one wave (§3.4). It can be tested later with `sedan:1sw3so`, with no code change. |
| Q2 | Confirm large minibus = 4 Sw + 5 So at the same time, and the DB correction date. | 4/5 explicit | Every earlier number used 4/10 (F6). |
| Q3 | Same matrix travel times and ride limit R for both types? Cooldown 10 for borrowed cars (driver handover may differ)? | same; cd 10 | Per-type parameters exist; values change results. |
| Q4 | Can every So student ride in a sedan (assistance needs, front-seat needs, escort)? Is any student large-only? | all So car-eligible | Would add per-student eligibility (a small extension of the arc feasibility). |
| Q5 | Tie-break after cars and total minutes: fewer car-minutes (less borrowing) or fewer large-minutes? Report weekly cars as the max over days (same cars daily) or as the per-day need (borrow per day)? | car-minutes; report both | Changes the chosen plan and the headline number. |
| Q6 | How should the corrected-capacity campaign relate to the archived 4/10 results in the paper: new labelled section, or replacement with an erratum? | new labelled campaign; archive untouched | Results must not change silently. |
| Q7 | Default car cap (unlimited today) and selection time limit for the headline run. | unlimited; 30 s per (day, R, L) | A cap can turn a result into `infeasible_for_L`. |
| Q8 | Is CP-SAT for the day selection acceptable, or should the greedy quota-repair fallback be used (weaker guarantee, §3.5)? | CP-SAT | Changes WP4 only. |

## Owner decisions (2026-10-08)

The owner answered the open questions of section 11 as follows. These replace the defaults in that table.

| # | Decision |
|---|---|
| Q1 | Sedan Sw = 0 (`0sw4so`). A sedan carrying 1 Sw (`sedan:1sw3so`) can be tested later with no code change. |
| Q2 | Minibus = 4 Sw + 5 So confirmed. The DB record was corrected by the owner on 2026-10-07 from 4/10 to 4/5 (F6). |
| Q3 | Same travel times, same ride limit R and cooldown 10 for both vehicle types. |
| Q4 | All So students are sedan-eligible; no per-student eligibility is needed. |
| Q5 | Tie-break on car-minutes. Report both the weekly maximum and the per-day need. |
| Q6 | The 4/10 results are REMOVED from the paper and replaced by the corrected 4/5 campaign. The 4/10 archive stays in git, labelled invalid due to a data error. |
| Q7 | Cars unlimited. Selection time limit 30 s per (day, R, L). |
| Q8 | CP-SAT is accepted for the day selection. |

Q1 stays recorded as an open scenario question in `DECISION_LOG.md` (sedan Sw = 0 is the owner's current answer, not a safety verification of mixed loads).
