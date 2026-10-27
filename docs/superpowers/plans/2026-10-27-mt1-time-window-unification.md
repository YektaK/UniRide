# MT1: Time-Window Unification (One Route Schedule per Profile, Truthful Schedules and Vehicle Counts)

> **Status: DRAFT for owner approval.** No MT1 code work starts before the owner (or the lead under the A20 delegation, for questions not reserved to the owner) answers section 6. For agentic workers: use `superpowers:subagent-driven-development` or `superpowers:executing-plans` item by item; steps use checkbox syntax.

**Goal:** close audit findings **H2** (pickup: return arc to school and waiting never checked), **H3** (returned `arrival_times`/`departure_time` come from a third, uncertified model), **H4** (production search ignores time windows), **H16** (Solomon CVRPTW judged with school-pickup rules), and the MT1 parts of **M1** (solvers ignore the fleet), **L12** (latent constraint gaps) and **N1** (phantom wait, ignored fallback flag). **M2** (pickup windows built from `dropoff_time`) is added because it lives in the same window builder.

**Product goal behind it:** the demo plans each day's student routes and answers "how many vehicles do we need". Speed and best cost are not the priority. Every plan the system shows must be feasible under one written timing rule, and every vehicle number must be honest: never fewer vehicles than a feasible plan needs, and a clear statement when no feasible plan was found.

**Base:** branch `WIP`, HEAD `3c88f0a8` (2026-10-27). Plan written in worktree `C:/wt/mt1-plan`, branch `docs/mt1-plan`. The planner ran one read-only repro script (section 1.0) and no test suites.

**Key:** **[F]** = verified in live code at `3c88f0a8` (file:line given) or by the repro; **[A]** = assumption the item's developer re-checks first; **[O]** = owner choice (section 6), never taken by a developer.

## Global constraints (every brief repeats these)

- **Python on Windows (top of every brief):** never open interactive Python (no bare `python`/`py`/`python3`, no `python -i`, no `python -`, no heredoc or stdin into Python, no `python -c`). Write scripts to a file under `C:\wt\<name>` and run them with `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`, with `PYTHONPATH` set to the worktree (the editable install points at the main checkout). Time-limit long commands, send output to a file and read it with `tail`/`grep`. Stop and report on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only your own PIDs. Never `git stash`; no checkout/switch in the main checkout. Temp folders only under `C:\wt\<name>`.
- Never read, copy, write or delete `academic_benchmark/tsplib_data/tsplib.db*`. No live database access or writes. Never write under `docs/paper/results`. No AMPL runs.
- Each item: own worktree and branch (`git worktree add C:/wt/<item> -b <branch> WIP`), red test first, frequent commits, no merge, no push. The lead merges with `--no-ff` after the reviewer's ONAY and passing tests. The developer report shows the red test failing with the fix reverted.
- Do not reopen decided questions: O01 (certify on captured authoritative arcs), O02 (conservative operational rounding), O03 (two duration limits: student ride and vehicle tour), O04 (direct arcs are not lower bounds), O05 (feasibility, then vehicles, then cost), O06 (strict arcs, explicit time-window modes), O07, V01/V02 (minimum is conditional; adequacy needs assignment evidence), U02, W01 (separate legs, exact anchors, 15-minute buffers), W02, H01 (typed fleet path additive; split goldens), H03-H06, S08, T09, A14 (no pooling across result-changing fixes), A20 L3/L5, A21 OQ-F7.
- Not changed by MT1: the academic study profiles and datasets (`academic_benchmark/studies/`, `academic_benchmark/datasets/`), production strategy exposure, the capability catalog, the exact-solver code (`uniride_core/exact/`), fleet selection (`uniride_core/planning/`), and the behaviour of every request with `use_time_windows=false` except for the additive schedule fields of MT1-03 (section 3.2).
- Each merged item updates Appendix J of `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md` for the IDs it closes (H2 `:2319`, H3 `:2320`, H4 `:2321`, H16 `:2334`, N1 `:2374`; M1, M2 and L12 get their own rows on first touch) and records decisions in a new `docs/DECISION_LOG.md` entry **O09 "MT1 time-window unification: plan and owner decisions"** (created when this plan is merged).

---

## 1. Verified current state (live code at `3c88f0a8`)

### 1.0 Repro (planner, read-only, in-memory)

Script `C:/wt/mt1-plan-scratch/repro_mt1.py` (not committed) called the core functions directly with the audit's numbers. Output:

```
H2 certificate violations: 0 (0 = accepted although school is reached at 08:40)
H2 decoder: routes [['A', 'B']] tw_violations 0
H3 schedule: {'LB': '08:30', 'LA': '08:25', 'D': '08:15'} departure 08:00
H4 decoder: routes [['A', 'B']] tw_violations 0
H4 certificate: ['Route 0 node 1 arrival 473.9 exceeds latest 473']
```

H2, H3 and H4 reproduce exactly as the audit describes.

### 1.1 Who is affected today: the demo does not use time windows

| # | Fact | Status | Evidence |
|---|---|---|---|
| D-a | The daily plan (demo) calls `/optimize` once per wave (direction, anchor) with `use_time_windows: false`, `target_time` = the wave anchor, no `offset_minutes` | **[F]** | `src/services/daily-plan-run.ts:604-623`; waves `:472-476` |
| D-b | The anchor already contains the 15-minute buffer (pickup: class start minus 15; drop-off: class end plus 15) and is the hard deadline (pickup) or hard ready time (drop-off) | **[F]** | `src/services/daily-planning.ts:24-25, 109-110, 553-554, 570-571`; W01 |
| D-c | The demo's timing model lives in TypeScript: pickup route interval `[anchor - total, anchor]`, drop-off `[anchor, anchor + total]`, total = sum of matrix steps including the return arc; start < 0 or end > day end is refused | **[F]** | `src/services/dudullu-preview.ts:509-519` |
| D-d | With one shared anchor per wave and no per-student windows, this model has no waiting, so it is correct for the demo. The server certificate does not check it (time windows are only checked when `use_time_windows` is true) | **[F]** | `optimizer_api/verification/response_certifier.py:645-659, 685-690` |
| D-e | No UI path sends `use_time_windows: true`. The fleet scenario runner also sends `false`; typed (`vehicle_types`) requests refuse time windows | **[F]** | `src/services/fleet-scenario-run.ts:417, 446`; `src/services/optimizer-service.ts:271, 381` (default false); `src/app/api/optimize-route/route.ts:147` (default false); `optimizer_api/models/schemas.py:370-371` |
| D-f | H2, H3 and H4 are reachable only through direct API calls with the internal key and `use_time_windows: true` (and through `/api/optimize-route` if a client sent it) | **[F]** | D-a..D-e |

Consequence for planning: the demo's plans are not wrong today because of H2-H4, but the server never certifies the demo's timing, the API's schedule fields are wrong whenever they are filled, and any future use of per-student windows would produce plans that look feasible and are not.

### 1.2 H2: return arc and waiting (pickup)

| # | Claim | Status | Evidence |
|---|---|---|---|
| H2-a | The certificate fixes the pickup start at `latest - route_cost - offset` and never searches another start | **HOLDS [F]** | `uniride_core/algorithms/feasibility_certificate.py:364-387` (audit cited `:206-277`; lines moved) |
| H2-b | It waits at early stops and stops at the last student; the arc back to school is never checked after waits | **HOLDS [F]** | `:395-433`; repro: 0 violations although school is reached at 08:40 |
| H2-c | Waiting is not counted against `max_travel_time`; ride time is pure travel | **HOLDS [F]** | `check_duration` `:241-268` (travel only); production call with service `None` `response_certifier.py:671-673`; `check_ride_time` docstring `:290-293` says waiting is not visible |
| H2-d | The split decoder does the same: fixed start `target - int(cost) - offset`, integer-truncated arcs, no return check after waits; tour limit checked on travel only | **HOLDS [F]** | `uniride_core/algorithms/string_split_decoder.py:446-450, 460-521` (`int(...)` at `:465, :488`); repro |
| H2-e | Three different meanings of `offset_minutes`: certificate and decoder arrive at school `offset` minutes before target; `route_scheduling` subtracts `offset` again from the depot departure; defaults differ (decoder 10, API 15, certifier fallback 15) | **NEW [F]** | `feasibility_certificate.py:379`; `string_split_decoder.py:138, 464-466`; `route_scheduling.py:61-62`; `schemas.py:274`; `response_certifier.py:689` |
| H2-f | The decoder ride-time check already adds waiting after the first pickup | **PARTLY FIXED [F]** | `string_split_decoder.py:483, 495-510` (R1 work, O03) |

### 1.3 H3: returned schedule

| # | Claim | Status | Evidence |
|---|---|---|---|
| H3-a | Pickup schedule anchors the last stop at its own window close and walks backwards with no waits and no return arc; default 09:00 | **HOLDS [F]** | `uniride_core/algorithms/route_scheduling.py:37-62` (`:47-48` default) |
| H3-b | Drop-off schedule starts at the first window's earliest, no waits; default 14:00 | **HOLDS [F]** | `:64-87` (`:74-75`) |
| H3-c | Computed only when `use_time_windows` and `success`, from the response's reported step durations (not the authoritative arcs), before certification; the certificate never reads it | **HOLDS [F]** | `optimizer_api/routers/optimization.py:298-305`; `response_certifier.py:330-700` has no reference to `arrival_times` |
| H3-d | `/compare` never fills the schedule | **[F]** | `optimization.py:444-500` |
| H3-e | Consumers (audit Q5): only TypeScript type declarations; no UI reads the fields | **[F]** | `src/services/optimizer-types.ts:32-33`; `src/types/index.ts:30-31` (grep of `src`) |
| H3-f | Repro: A shown at 08:25 (its window closed 08:00), departure 08:00 (offset subtracted twice) | **[F]** | section 1.0 |

### 1.4 H4: search ignores windows

| # | Claim | Status | Evidence |
|---|---|---|---|
| H4-a | GA/GWO/PSO/HHO split search decodes with the capacity-only `decode_giant_tour` and ranks by `objective_key` (feasible, vehicles, cost); windows appear only in the final decode | **HOLDS [F]** | `ga_split_engine.py:110, 135, 397-414`; `gwo_split_engine.py:123, 135, 222`; `pso_split_engine.py:146, 158, 248`; `hho_split_engine.py:164, 176, 272`; `meta_split_common.py:92-134` |
| H4-b | Decoder pickup anchor `self.target_time or 540` (09:00); drop-off uses only the first stop's window; drop-off `departure_time` recorded as `current - int(cost)` after waits | **HOLDS [F]** | `string_split_decoder.py:597, 524-526, 583` |
| H4-c | Repro: decoder says 0 violations, certificate rejects (473.9 > 473) although departing at 07:42 is feasible | **[F]** | section 1.0 |
| H4-d | OR-Tools now receives `max_route_duration` but no windows | **PARTLY FIXED [F]** | `optimizer_api/strategies/ortools_cvrp.py:65-77` |
| H4-e | PyVRP receives neither windows nor maximum duration nor ride limit | **HOLDS [F]** | `optimizer_api/strategies/pyvrp_strategy.py:102-110` |
| N1-a | `GASplitStrategy` returns `success=True` even when the decoder fell back to one route per student (`"error": "No feasible splitting found"`) | **HOLDS [F]** | `optimizer_api/strategies/ga_split_strategy.py:271-283`; fallback `string_split_decoder.py:244-255` |
| N1-b | Drop-off phantom wait (decoder departs at `min(target, earliest window)`, published schedule does not wait) | **HOLDS [F]** | `string_split_decoder.py:524-556`; `route_scheduling.py:64-87` |

The system fails closed (the certificate rejects), so the harm is false "no plan" answers, not false "feasible" answers, except for H2 where the certificate itself is wrong.

### 1.5 H16: Solomon CVRPTW

| # | Claim | Status | Evidence |
|---|---|---|---|
| H16-a | `from_solomon_text` sets no direction, so the profile defaults to `"pickup"` | **HOLDS [F]** | `uniride_core/adapters/matrix_builder.py:297-343`; default `uniride_core/models.py:30, 137` |
| H16-b | `certify_problem_instance` runs the pickup branch of `check_time_windows` (no target, offset default 10) on Solomon routes; depot due time never checked | **HOLDS [F]** | `feasibility_certificate.py:636-670` (`:661-664`) |
| H16-c | Split path and holistic engine disagree on Solomon violations | **[A]** not re-read (`split_decoder.py:128-142`, `base_engine.py:173-194`, `holistic_matrix_engine.py`); the developer re-runs the audit scenario first |
| H16-d | Q3: no active study uses CVRPTW: both profiles declare `"problem_families": ["TSP"]` | **[F]** | `academic_benchmark/studies/bildiri2026/study.json`, `yaem2026/study.json` |

H16 therefore affects academic CVRPTW tooling only, not any study result.

### 1.6 M1, M2, L12

| # | Claim | Status | Evidence |
|---|---|---|---|
| M1-a | No production strategy reads `request.vehicles`; only `ga_split_hf` reads `vehicle_types` | **HOLDS [F]** | grep `optimizer_api/strategies/*.py`; `ga_split_hf_strategy.py:80-83` |
| M1-b | The certificate enforces the fleet: one-to-one Sw/So matching and route count <= vehicle count; global caps off when a fleet is given | **HOLDS [F]** | `response_certifier.py:164-221, 375-381, 663` |
| M1-c | Demo: virtual mode sends identical copies (no effect); live mode sends the real fleet, and a `fleet_size_violation` becomes `FLEET_SHORTAGE` with status "shortage"; the view shows the fleet as "missing" without a number | **[F]** | `daily-plan-run.ts:573-577, 595-598, 643-648`; `daily-plan-view.ts:446-450` |
| M1-d | That shortage is a heuristic statement (the solver did not try to fit the fleet), not a proof | **[F]** by M1-a; wording owner choice **[O] OQ-MT1-8** |
| M2-a | A PICKUP request with only `dropoff_time` gets a morning window from it | **HOLDS [F]** | `optimizer_api/models/schemas.py:465-472` (audit cited `:350-357`) |
| L12-1 | Sweep clustering centred on hard-coded Dudullu coordinates; `vehicle_assignment` passes no depot | **MOSTLY FIXED [F]** | `vehicle_assignment.py:89, 126-127` passes the depot (O08); the fallback coordinates remain at `clustering_strategies/sweep.py:24` |
| L12-2 | `to_problem_instance` collapses `[sw, so]` to `sw`; `check_capacity_vectors` checks only `min(len(load), len(capacity))` dimensions | **HOLDS [F]** | `matrix_builder.py:129-136`; `feasibility_certificate.py:147` |
| L12-3 | `check_time_windows` skips travel into nodes beyond the window list | **HOLDS, latent [F]** | `feasibility_certificate.py:397-399`; the production certifier gives every node a window `(0, 1440)` (`response_certifier.py:649-652`) |
| L12-4 | Missing capacities default to total demand | **HOLDS [F]** | `uniride_core/algorithms/routing_demand_utils.py:67-68` |
| L12-5 | `is_asymmetric` defaults to False | **HOLDS, low impact [F]** | `schemas.py:289`; auto-set from a caller matrix `:346`; demo sends `true`; reverse-arc fallback only for a missing arc `string_split_decoder.py:306-313` |

### 1.7 What changed since the audit and matters here

- C2/O01: the production certificate re-costs every step on captured authoritative arcs (`response_certifier.py:504-583`). MT1 builds on that matrix; it must not reintroduce reported durations (H3-c does today).
- MT6-04 (A20 L4): the production hybrid now uses path 3-opt; it does not touch timing.
- S08 + A20 L2/L3: saved plans carry solver provenance and `solver_code_version`; MT1 results change only for `use_time_windows=true`, so no pooling note is needed for demo plans (A14 applies to TW requests).
- T09: stale matrix fails closed; unchanged.

---

## 2. Boundary and timing check

### 2.1 What the studies and guards use

The study run imports from `uniride_core`: `models` (`ProblemInstance`), `adapters.matrix_builder`, `algorithms.capabilities`, `tsplib_parser`, `three_opt`, `sota_tsp`, `composition`, `tsp_matrix_metaheuristics`, `objective_budget`, `engine_factory`, `numba_*`, `exact`, `planning` (grep of `academic_benchmark` without tests). It does **not** import `feasibility_certificate`, `string_split_decoder`, `route_scheduling`, the split engines, `meta_split_common` or `optimizer_api` **[F]**. Both profiles are TSP only (H16-d).

Guard set used by the MT6 follow-up close (`2026-10-27-mt6-followup-sota-common-shims-l3-l10.md:103`): `academic_benchmark/tests/test_fixed_budget_tables_unchanged.py`, the `uniride_core/tests/golden/gwo_hho_native_pre_schedule.json` tests, `uniride_core/tests/test_mt6_budgeted_tolerance.py`, the `academic_benchmark/tests/fixtures/fcm_tsp_golden_pre_refusal.json` tests, and an empty `git diff --stat` for `academic_benchmark/studies` and `academic_benchmark/datasets`.

A second, non-study guard matters: `uniride_core/tests/golden/split_parity.json` (H01) pins `decode_giant_tour`, `decode_with_time_windows` and GA split outputs, including time-window cases (`test_split_parity_golden.py:102-151`). The daily-planning paper archives (fleet campaign, WP-E10, WP-E4) were produced with `use_time_windows=false`; the non-TW golden entries prove they stay reproducible.

### 2.2 Per item

| Item | Changes | Study path? | Guards that must pass unedited | When it may merge |
|---|---|---|---|---|
| MT1-01 | new core module | No (nothing imports it) | all | now |
| MT1-02 | production certifier | No | all | now |
| MT1-03 | router, `route_scheduling`, response schema | No | all | now |
| MT1-04 | TypeScript daily plan / fleet runner | No | all + vitest | now |
| MT1-05 | `string_split_decoder` TW branch | No | all; `split_parity.json` non-TW entries byte-identical, TW entries regenerated in a separate commit | now |
| MT1-06 | split engines' search key when windows on | No | as MT1-05 | now (after 05) |
| MT1-07 | split strategies' success flag | No | all | now |
| MT1-08 | `schemas.get_time_windows` | No | all | now |
| MT1-09 | OR-Tools/PyVRP strategies; optional PyVRP core parameter (default keeps behaviour) | Shared core engine imported by the academic registry, behaviour unchanged by default | all | now |
| MT1-10 | TypeScript shortage wording and proof | No | all + vitest | now |
| MT1-11 | H16: `matrix_builder`, `models.ConstraintProfile`, core certificate forward branch, `split_decoder` | **Yes, shared modules imported by the study run** (results of TSP studies unchanged, academic CVRPTW results change) | all | **after the paper campaign** (A20 L5, A21 OQ-F7) [O] OQ-MT1-11 |
| MT1-12 | L12 capacity contract in core | Shared core (CVRP engines, `matrix_builder`) | all | **after the paper campaign** |
| MT1-13 | documents, tracker | No | n/a | last |

"Now" means: before the lead's pre-approval commit. Rule from A21 OQ-F7: no merge may change study code or study results between that commit and the campaign. MT1-01..10 change neither; whether they may still merge inside that window is **[O] OQ-MT1-12** (the recommendation keeps MT1-09 out of the window because it edits a core engine the academic registry imports).

---

## 3. Target design (smallest that makes the demo plan feasible and honestly reported)

### 3.1 One route simulator, three profiles

New core module `uniride_core/algorithms/route_schedule.py`: pure functions, exact floats (no `int()`), no I/O, no new dependency. One function per profile; all share the same output type.

```python
@dataclass(frozen=True)
class RouteSchedule:
    start: float                 # depot departure (minutes from midnight)
    arrivals: tuple[float, ...]  # arrival at each stop, in route order
    waits: tuple[float, ...]     # waiting at each stop before service
    end: float                   # arrival back at the depot (school)
    violations: tuple[ScheduleViolation, ...]   # empty = feasible
    # derived: tour = end - start; ride per student (definition below)

def simulate_school_pickup(route, arc, *, deadline, windows=None, service=None, day_start=0.0) -> RouteSchedule
def simulate_school_dropoff(route, arc, *, ready, windows=None, service=None, day_end=1440.0) -> RouteSchedule
def simulate_forward_tw(route, arc, *, depot_window, windows, service) -> RouteSchedule   # MT1-11, academic
```

`arc(i, j)` returns the authoritative directed travel time (the certifier passes its captured matrix; the decoder its dict).

| Profile | Used by | Rule |
|---|---|---|
| `school_pickup` | production `/optimize`, `/compare`, daily plan | Arrive at school by `deadline`. Depart as late as possible: one backward pass computes the latest arrival at every stop (`min(window close, next latest - service - arc)`), the depot departure is the first latest minus the first arc; a forward pass from there waits only where a window opens later. Feasible iff no window opens after its latest arrival and the departure is not before `day_start`. Exact for a fixed stop order. **[O] OQ-MT1-3** |
| `school_dropoff` | same | Leave school at `ready`. Forward pass; wait where a window opens later. Feasible iff every stop is reached by its window close and the return is by `day_end`. **[O] OQ-MT1-6** |
| `forward_tw` | academic CVRPTW (Solomon) only | Leave the depot at its ready time; wait if early; service at every customer; return by the depot due time. Separate contract (AGENTS.md: CVRP/CVRPTW validation is its own contract). MT1-11. |

Counted quantities (one definition, used everywhere):

- **Return arc:** always part of the route. Pickup: school arrival = last stop + its service + arc to school, checked against `deadline`. Drop-off: the return counts for the tour and the fleet interval, not for ride time.
- **Waiting:** part of the tour; part of a student's ride once the student is on board **[O] OQ-MT1-4**.
- **Tour (`max_travel_time`):** `end - start`. **Ride (`max_ride_time`):** pickup: from the student's boarding to school arrival; drop-off: from school departure to the student's arrival.
- **Service/dwell time:** default 0, as today; the parameter exists so the owner can set it **[O] OQ-MT1-5**.
- **`target_time` and `offset_minutes`:** one meaning: `deadline = target_time - offset_minutes` (pickup), `ready = target_time + offset_minutes` (drop-off) **[O] OQ-MT1-2**. The daily plan and the fleet runner send `offset_minutes: 0` because the anchor already holds the W01 buffer (D-b).
- **No `target_time`:** a `use_time_windows=true` request without `target_time` is refused with 422 (MT1-08) instead of being anchored at an invented 09:00 or 14:00. This closes the audit's H4 scenario 2 by refusal. Every demo request has `target_time`.

For the demo (one anchor, no windows, no service) the simulator gives exactly the TypeScript interval: start = anchor - total travel, end = anchor (pickup); start = anchor, end = anchor + total (drop-off). So demo plans do not change.

### 3.2 Schedule in the API response, and how it is certified

- After the solve, the router computes each route's schedule with the simulator on the **captured authoritative arcs** (the same `arc_lookup` the certificate uses), whenever the request has `target_time` or `use_time_windows`. `route_scheduling.calculate_scheduled_times` is replaced by this call (its callers are the router and tests).
- `VehicleRoute.departure_time` and `arrival_times` (HH:MM, kept for compatibility) come from that schedule. New optional exact fields (additive, omitted when no schedule): `schedule_start_minutes`, `schedule_end_minutes`, `arrival_minutes` (per occurrence key). Display rounding **[O] OQ-MT1-10b** (inside OQ-MT1-10).
- The certificate re-simulates every route independently and adds a violation `schedule_mismatch` if a returned exact time differs by more than `ARC_DURATION_TOLERANCE x (steps + 1)`. So "returned times equal the simulated times" is enforced, not assumed.
- The certificate's time checks (deadline, windows, tour with waits, ride with waits) use the simulator. The core `check_time_windows` stays as it is for the legacy benchmark certificate until MT1-11.
- `/compare` gets the same schedule fields (same function).

### 3.3 How search ranks candidates

- Decoder (split DP, inner level, O05): a trip (consecutive stops of the giant tour) is built only after `simulate_school_*` on that trip. Strict mode drops infeasible trips; soft mode keeps them with their violation count. DP key stays (violations, cost) as today.
- Outer search (GA/GWO/PSO/HHO split), only when `use_time_windows` is true: candidates are decoded with windows and ranked by **(violations, vehicles, cost)**; the final decode is the same decode, so "solver feasible" equals "certificate feasible". With `use_time_windows=false` nothing changes (golden).
- Strategies without time-window search (OR-Tools, PyVRP, VROOM, SOTA, holistic, typed) refuse `use_time_windows=true` with a clear 422 **[O] OQ-MT1-9**. PyVRP additionally receives `max_route_duration` so ordinary requests stop failing on the tour limit (H4-e).

### 3.4 Truthful vehicle count

| Rule | Mechanism |
|---|---|
| R1. A vehicle number is shown only for a plan whose every route passed the certificate | already true (`optimization.py:318`); MT1 makes the certificate check timing correctly |
| R2. Such a number is an upper bound ("this plan uses N"), never called "the minimum" unless V01 proves it or it equals the capacity floor (U02) | unchanged V01/U02 wording; MT1-10 checks the copy |
| R3. A fallback (one route per student because no feasible split was found) says so | MT1-07: `success=false` with reason `no_feasible_split` |
| R4. "Not enough vehicles" is called proven only when the per-wave capacity floor exceeds the live fleet; otherwise "the computed plan needs N, the fleet has M" | MT1-10 **[O] OQ-MT1-8** |
| R5. No infeasibility claim from a direct arc (O04) or from one heuristic run | MT1-10 wording; reason codes stay "not found", never "impossible" |

### 3.5 What is deliberately not built

No new scheduling framework, no time-dependent travel times, no OR-Tools/PyVRP time dimensions (refusal instead), no fleet-aware DP (certificate plus honest wording instead, OQ-MT1-8), no per-student windows in the daily plan (it uses anchors), no changes to the typed fleet path beyond the shared schedule fields.

---

## 4. Work items

Lanes: **A** (contract, serial) 01 -> 02 -> 03 -> 04; **B** (search, serial, after 01) 05 -> 06; **C** (independent, parallel with A and B) 07, 08, 09, 10; **D** (after the paper campaign) 11, 12; **E** close 13. Items closing a High finding (H2, H3, H4, H16) get an **Opus** reviewer (CLAUDE.md rule); the rest Sonnet. Every reviewer runs the tests and reverts the source change in a scratch worktree to show the red test fails.

### MT1-01 Core route simulator (school profiles)

- **Goal:** `uniride_core/algorithms/route_schedule.py` with `RouteSchedule`, `simulate_school_pickup`, `simulate_school_dropoff`, typed violations (`deadline`, `window`, `start_before_day`, `end_after_day`). No caller yet.
- **Files:** new module; new `uniride_core/tests/test_route_schedule.py`.
- **Red tests first:** (1) audit H2 scenario -> `deadline` violation (school 08:40 > 08:15 after offset); (2) audit H4 scenario (target 08:15, offset 0, arcs 10.9/10.9/10.2, A closes 07:53) -> feasible, start 462.1 (latest departure), A 473.0, school 494.1, no truncation; (3) audit H3 scenario -> start 07:50, A 08:00, B 08:05, school 08:15; (4) demo shape (no windows) -> start = deadline - travel, zero waits, end = deadline; (5) drop-off with a late-opening window -> wait counted; (6) property test (seeded, n <= 6, integer and decimal directed arcs, random windows): a feasible schedule replays clean under an independent naive forward check, and when the simulator says infeasible no departure on a 0.05-minute grid in `[0, deadline]` is feasible.
- **Acceptance:** tests green; module imported by nothing; `uniride_core/tests` green.
- **Risk:** contract-defining. **Opus reviewer.** Depends on OQ-MT1-2, -3, -4, -5, -6.

### MT1-02 Production certificate uses the simulator (H2)

- **Goal:** in `_certify_optimization_response` (`response_certifier.py:645-690`), when the request has `target_time` or `use_time_windows`, simulate every route on the captured matrix; report deadline/window violations as `time_window_violation`, tour with waits as `duration_violation`, ride with waits as `ride_time_violation`. Typed requests keep `_typed_fleet_violations` and gain only the deadline check.
- **Files:** `optimizer_api/verification/response_certifier.py`; new `optimizer_api/tests/test_mt1_certificate_schedule.py`.
- **Red tests:** the audit H2 scenario as a request/response pair with an injected `arc_lookup` -> today `is_feasible=True`, after the fix false; a demo-shaped request (`use_time_windows=false`, `target_time`, `offset_minutes=0`) -> still feasible and byte-identical certificate.
- **Acceptance:** `optimizer_api/tests` green; `test_certifier_authoritative_matrix.py`, `test_certifier_arc_sources.py`, `test_mutation_proof_strategies.py` unedited and green; `certify_benchmark_response` unchanged.
- **Risk:** fail-closed boundary. **Opus reviewer.** Depends on MT1-01.

### MT1-03 Returned schedule equals the certified schedule (H3)

- **Goal:** replace `calculate_scheduled_times` use in the router (`optimization.py:298-305`) with the simulator on `arc_lookup` arcs, for `/optimize` and `/compare`; add the optional exact fields; certificate adds `schedule_mismatch`.
- **Files:** `optimizer_api/routers/optimization.py`, `optimizer_api/models/schemas.py` (additive fields), `uniride_core/algorithms/route_scheduling.py` (thin wrapper over the simulator or removed after its test callers move), `response_certifier.py`, tests (`optimizer_api/tests/test_scheduling_utils.py`, `uniride_core/tests/test_route_scheduling.py`, `test_strict_arcs.py` updated with reasons).
- **Red tests:** audit H3 scenario through `/optimize` (TestClient, stubbed strategy) -> today LA 08:25; after: 08:00 and departure 07:50; a response whose `arrival_minutes` were edited -> `schedule_mismatch`; an equality test over every route of a seeded multi-route response.
- **Acceptance:** schedule never built from reported durations; registry snapshot unchanged.
- **Risk:** **Opus reviewer** (H3). Depends on MT1-02.

### MT1-04 Daily plan and fleet runner: one offset meaning, server schedule cross-check

- **Goal:** daily plan and fleet runner send `offset_minutes: 0`; the preview compares its own interval `[anchor - total, anchor]` (pickup) or `[anchor, anchor + total]` with the server's `schedule_start_minutes`/`schedule_end_minutes` when present; a mismatch blocks the plan with a new reason `SCHEDULE_MISMATCH` (tr/en copy).
- **Files:** `src/services/daily-plan-run.ts:604-623`, `src/services/fleet-scenario-run.ts:417, 446`, `src/services/dudullu-preview.ts:509-530`, the optimizer result zod schema, i18n messages, vitest files next to each.
- **Red tests:** request body contains `offset_minutes: 0`; a stub response with a shifted schedule is refused; an archived-shape response without the new fields is still accepted (older optimizer).
- **Acceptance:** vitest + `tsc --noEmit` clean; `scripts/research-tests` (fleet archive guard) green.
- **Risk:** low. Sonnet. Depends on MT1-03.

### MT1-05 Split decoder time-window branch uses the simulator (H2 decoder, H4-b, N1-b)

- **Goal:** `_build_trips_with_tw` (`string_split_decoder.py:~380-585`) calls `simulate_school_pickup`/`_dropoff` per candidate trip; remove `int()` truncation, the 09:00/14:00 defaults (no target and no windows -> the request is refused upstream, see MT1-08) and the first-stop-only drop-off start; `schedules` in the result come from the simulator.
- **Files:** `uniride_core/algorithms/string_split_decoder.py`; tests `uniride_core/tests/test_split_decoder_tw_modes.py`, `test_split_decoder_max_ride_time.py`, `optimizer_api/tests/test_cvrptw_phase2.py`, `test_cvrptw_phase3.py` (updated only where they pinned the defect, each with a reason); `split_parity.json` TW entries regenerated **in a separate commit** whose message lists every changed key.
- **Red tests:** H4 scenario -> decoder reports the trip feasible with schedule start 462.1, equal to MT1-01; H2 scenario strict -> trip [A,B] not admitted, soft -> 1 violation; N1 repro (3 students, drop-off, target 16:00, ride limit 45) -> 1 vehicle.
- **Acceptance:** non-TW golden entries byte-identical (`test_split_parity_golden.py`); `test_p2_academic_code_never_imports_heterogeneous_modules` green.
- **Risk:** **Opus reviewer** (H2, H4). Depends on MT1-01 and MT1-08 (the decoder raises `ValueError` if it is ever reached without a target; MT1-08 makes that unreachable from the API).

### MT1-06 Search ranks by (violations, vehicles, cost) when windows are on (H4-a)

- **Goal:** GA/GWO/PSO/HHO split evaluation decodes with windows when `use_time_windows` is true and ranks by (violations, vehicles, cost); non-TW path unchanged.
- **Files:** `ga_split_engine.py:~100-140`, `gwo_split_engine.py:~120-136`, `pso_split_engine.py:~146-158`, `hho_split_engine.py:~164-176`, `meta_split_common.py`, `objective_rank.py` (one helper); tests.
- **Red tests:** the audit H4 repro (section 1.0) through `ga_split` with `use_time_windows=true` -> certified success (today `success=false`); a seeded n = 5 instance where the capacity-only search ends on a TW-infeasible tour while a feasible one exists -> success after the fix; property test over seeded small instances: strategy `success` equals certificate `is_feasible`.
- **Acceptance:** `split_parity.json` non-TW entries unchanged, TW entries regenerated in a separate commit; MT6 regression command green.
- **Risk:** **Opus reviewer** (H4). Depends on MT1-05. Dropped if OQ-MT1-1 = c.

### MT1-07 Fallback is reported, not hidden (N1-a)

- **Goal:** GA/PSO/GWO/HHO split strategies return `success=false` with `error_message` reason `no_feasible_split` when the decoder fell back to one route per student.
- **Files:** `optimizer_api/strategies/ga_split_strategy.py:271-283` and the three sibling split strategies; tests.
- **Red test:** a request whose singleton trips break the tour limit -> today `success=True` from the strategy; after: false with the reason.
- **Risk:** low. Sonnet. Independent.

### MT1-08 Windows built for the right direction only (M2)

- **Goal:** `get_time_windows` (`schemas.py:448-495`) uses `pickup_time` for PICKUP and `dropoff_time` for DROPOFF only; a student without its direction's time gets no window (the route deadline then comes from `target_time`); a `use_time_windows=true` request without `target_time` is refused with 422 (section 3.1).
- **Files:** `optimizer_api/models/schemas.py`; tests `optimizer_api/tests/test_cvrptw_phase1.py` (updated with reason).
- **Red tests:** PICKUP, only `dropoff_time` 17:00 -> today window (16:30, 17:00); after: none. Audit H4 scenario 2 (one student with pickup 07:30, no `target_time`) -> today `ga_split` anchors at 09:00 and fails; after: 422 with a fixed message.
- **Risk:** low. Sonnet. Independent.

### MT1-09 Strategies without time-window search refuse it; PyVRP gets the tour limit (H4-d, H4-e)

- **Goal:** a capability flag `supports_time_windows` on strategies (true only for the split family after MT1-06, or for none if OQ-MT1-1 = c); `/optimize` and `/compare` refuse `use_time_windows=true` for the others with 422 before solving; PyVRP strategy passes `max_route_duration` (new optional core parameter, default `None` keeps the academic call identical).
- **Files:** `optimizer_api/strategies/*` (flag), `optimizer_api/routers/optimization.py`, `optimizer_api/strategies/pyvrp_strategy.py`, `uniride_core/algorithms/pyvrp_cvrp_engine.py`; tests (PyVRP tests skip when the package is missing; state it).
- **Red tests:** `ortools_cvrp` with `use_time_windows=true` -> today runs and fails at the certificate; after: 422 with a fixed message; PyVRP on an instance whose cheapest routes exceed `max_travel_time` -> after the fix no `duration_violation`.
- **Acceptance:** registry snapshot unchanged (keys); academic OR-Tools/PyVRP callers unchanged.
- **Risk:** **Opus reviewer** (H4). Independent of A and B.

### MT1-10 Honest fleet and vehicle-count wording (M1, R2-R5)

- **Goal:** per wave, compute the capacity floor (largest of ceil(Sw / max Sw seats), ceil(So / max So seats), and the total-seat floor when `total_capacity` is set); on `FLEET_SHORTAGE` show "the computed plan needs N vehicles at HH:MM; the live fleet has M" and say "proven" only when the floor exceeds M; copy for "no feasible plan found" avoids "impossible".
- **Files:** `src/services/daily-plan-run.ts:643-648`, `src/services/daily-plan-view.ts:~440-455`, i18n messages, page tests.
- **Red tests:** live fleet of 1 (X02), a wave whose floor is 2 -> "proven shortage"; a wave whose floor is 1 but the heuristic used 2 -> not "proven".
- **Risk:** low. Sonnet. Depends on OQ-MT1-8.

### MT1-11 Forward CVRPTW profile for Solomon (H16), after the paper campaign

- **Goal:** `from_solomon_text` marks the problem with an explicit forward profile (new optional `ConstraintProfile` field, default keeps "pickup" for existing callers); `certify_problem_instance` and the split path (`split_decoder.split_with_time_windows_result`) use `simulate_forward_tw`; dashboards treat only a feasible certificate as feasible.
- **Files:** `uniride_core/adapters/matrix_builder.py:297-343`, `uniride_core/models.py`, `feasibility_certificate.py`, `split_decoder.py`, `base_engine.py` (if the developer finds it needed), `academic_benchmark/dashboard_utils.py` [A: the audit's `:107-111` now holds problem-type code; the developer locates the "violation count 0 = feasible" rule]; tests.
- **Red tests:** audit H16 scenario (depot window (0, 45), customers (0, 50), service 10) -> infeasible on every path; a Solomon smoke test agrees with the holistic counter.
- **Acceptance:** full guard set unedited; academic CVRPTW results change (no pooling with earlier CVRPTW rows, A14 note in O09).
- **Risk:** **Opus reviewer** (H16, academic contract). Timing: OQ-MT1-11.

### MT1-12 Capacity contract gaps (L12-2, L12-3, L12-4), after the paper campaign

- **Goal:** a capacity vector shorter or longer than the demand vector is an error (`feasibility_certificate.py:147`); `to_problem_instance` keeps both dimensions (`matrix_builder.py:129-136`); missing capacities raise instead of defaulting to total demand (`routing_demand_utils.py:67-68`); `check_time_windows` treats a node without a window as unbounded but still adds its travel (`:397-399`).
- **Risk:** low (latent). Sonnet. After the campaign (shared core modules).

### MT1-13 Close

- **Goal:** `CURRENT_ARCHITECTURE.md` section 5 (the ride-time paragraph `:119` and the certificate paragraph `:121` describe waiting as invisible) and section on the schedule; DECISION_LOG O09 with every owner answer; Appendix J rows; DURUM; close evidence file with the demo acceptance (section 7.2). Fact-check by a Sonnet `olgu-denetcisi`.

---

## 5. Risks

| Risk | Control |
|---|---|
| Demo plans change unexpectedly | MT1-04 cross-check; demo acceptance replay (7.2) must show identical vehicles and durations |
| The daily-planning paper archives become irreproducible | non-TW `split_parity.json` entries byte-identical; `scripts/verify_fleet_rerun.py` tests and research tests green |
| Study results change before the campaign | MT1-11/12 wait; guard set per merge; empty diff of `studies/` and `datasets/` |
| The certificate starts rejecting archived exact-gap replays (`scripts/run_exact_wave_gaps.py` calls `certify_optimization_response`) | those requests have no windows, so the new check only adds the deadline, which a latest-start schedule always meets [A: the MT1-02 developer runs that script's tests] |
| A developer chooses a timing rule | rules are owner questions; briefs quote the answer |

---

## 6. Open questions for the owner

Each question lists options with pros (+) and cons (-) and a recommendation. None is decided here.

**OQ-MT1-1. How far should per-student time windows go in production now? (H2, H4)**
- (a) Full: simulator, certificate, schedule, and window-aware search for the split family (MT1-01..09). + per-student windows become usable (W01 already records `flexibilityMinutes` per leg); "solver feasible = certificate feasible". - two more Opus-reviewed items (05, 06) and a golden refresh.
- (b) Same as (a) but search only for `ga_split` (the API default), other split strategies refuse windows. + less work. - three strategies lose a feature they nominally have.
- (c) Simulator, certificate and schedule only; every strategy refuses `use_time_windows=true` until a product need appears. + smallest; the demo does not use windows; H2-H4 close by refusal. - per-student windows must be built later; the existing TW decoder code stays unused.
- **Recommendation: (a).** The decoder already exposes windows through the API; making that path correct costs two items, while (c) removes a capability the owner may need for flexible pickups.

**OQ-MT1-2. One meaning for `target_time` and `offset_minutes`. (H2-e; audit Q2)**
- (a) `deadline = target_time - offset` (pickup), `ready = target_time + offset` (drop-off); the daily plan sends 0 because its anchor already holds the W01 buffer. + matches the certificate and decoder today; one rule. - API callers that relied on `route_scheduling`'s second subtraction see a later departure.
- (b) `deadline = target_time`; `offset` only shifts the reported driver call time. + simple deadline. - changes the certificate and decoder meaning; a buffer would have to be added by every caller.
- (c) Remove `offset_minutes` (accept, ignore, document). + least ambiguity. - silent change for any caller that sends it.
- **Recommendation: (a).** Also please confirm that arriving by the deadline is a hard constraint (audit Q2); W01's `hardDeadlineMinutes` suggests yes.

**OQ-MT1-3. Which departure time for a pickup route? (audit Q7)**
- (a) The latest departure that still meets every window and the deadline. + shortest rides and least waiting; exact; accepts routes the current fixed rule wrongly rejects (H4 repro). - drivers may get slightly different times than the old rule.
- (b) The current fixed rule (deadline minus travel minus offset), rejecting any route that needs a wait. + no waiting ever. - rejects feasible routes; with windows it can still be wrong (H2).
- (c) The earliest possible departure. + more slack against traffic. - longer rides and waits for students.
- **Recommendation: (a).**

**OQ-MT1-4. Do waiting and service count in the tour limit and the ride limit? (O03 "check first"; audit Q2 second half)**
- (a) Tour = depot departure to return, all included. Ride = from boarding to school (pickup) or from school to the student's stop (drop-off), including waits and service after boarding. + matches what a vehicle and a student experience. - with windows, some routes now exceed limits that passed before.
- (b) Travel only for both. + no change. - a student can wait aboard without limit (the audit's H2 concern).
- (c) Tour includes waits; ride excludes them. + bounds the vehicle. - a student's real time aboard is not bounded.
- **Recommendation: (a).** No effect on the demo (no waits there).

**OQ-MT1-5. Service (dwell) time at a stop, including wheelchair boarding. (audit Q6)**
- (a) Keep 0 everywhere and state it in the UI and method text. + no result changes. - optimistic, especially for Sw students.
- (b) Two request parameters, default 0 now: a fixed dwell per stop and an extra boarding time per Sw student; the owner sets values later. + realistic when set; no change until set. - when set, vehicle counts and the paper's daily-planning numbers change (no pooling, A14).
- (c) Per-student service time from data. + most precise. - no such data today.
- **Recommendation: (b)**, with values chosen by the owner when known (for example from a timed boarding).

**OQ-MT1-6. Does drop-off need a mirrored per-student constraint?**
- (a) No: drop-off has only the ready time at school; tour and ride limits bound it. + matches the data (W01 has no home-arrival time). - no "home by" guarantee.
- (b) Yes: a latest arrival per student. + symmetric with pickup. - needs data that does not exist.
- (c) Supported by the simulator but not exposed in the API. + ready for later. - unused code path to test.
- **Recommendation: (a).**

**OQ-MT1-7. Maximum ride time per student.**
- (a) Keep one request-level limit (O03, UI default 90). + data has nothing finer. - cannot express shorter limits for some students.
- (b) Optional per-student override (for example for Sw students). + flexible. - no data; UI work.
- (c) Per vehicle type (already possible in `vehicle_types`). + exists. - per type, not per student.
- **Recommendation: (a).**

**OQ-MT1-8. What the daily plan says when the fleet is not enough or no feasible plan is found. (M1)**
- (a) Keep "blocked" with reason codes, and change the wording to "the computed plan needs N vehicles at HH:MM; the fleet has M", adding "proven" only when the capacity floor exceeds M (MT1-10). + truthful; small. - no plan is shown in that case.
- (b) Also show the best plan found with its violations highlighted. + the planner sees what fails. - an infeasible plan on screen can be misread as usable.
- (c) Also solve with the virtual fleet and show "with N vehicles this plan works" next to the shortage. + answers "how many do we need". - a second solve per wave; more UI.
- (d) Make the solver fleet-aware (route count capped by the fleet). + may find a fitting plan the heuristic misses. - new DP constraint; not needed for the demo's virtual fleet.
- **Recommendation: (a) now, (c) as a later small item.**

**OQ-MT1-9. Strategies without window-aware search. (H4-d, H4-e)**
- (a) Refuse `use_time_windows=true` with 422 (MT1-09). + honest, cheap. - those strategies cannot be compared on windowed requests.
- (b) Give OR-Tools and PyVRP real time dimensions. + more solvers with windows. - scaling and rounding work (O02 notes PyVRP scaling as open); more review.
- (c) Let them run and let the certificate reject. + no work. - "success=false" without a clear reason (today's state).
- **Recommendation: (a).**

**OQ-MT1-10. How the API and UI show times.**
- (a) Keep HH:MM truncation; add exact minutes. + no visible change. - a stop at 07:59.6 shows 07:59, and a school arrival at 08:14.6 shows 08:14.
- (b) Exact minutes in data; display stop times rounded down and the school arrival rounded up. + the display never looks better than reality at the deadline. - two rounding directions to explain.
- (c) Show seconds. + exact. - noisy for drivers.
- **Recommendation: (b).**

**OQ-MT1-11. When to fix H16 (Solomon CVRPTW).**
- (a) After the paper campaign. + no study-path module changes during the freeze; no study uses CVRPTW. - academic CVRPTW tooling stays wrong until then (label it).
- (b) Now, before the pre-approval commit. + done sooner. - touches `models` and `matrix_builder`, which the study run imports, right before a measured run.
- (c) Withdraw CVRPTW claims instead. + no work. - the unification design lists CVRPTW as supported.
- **Recommendation: (a)**, and a short "CVRPTW validation uses school rules (H16), do not cite" note in the dashboard until then.

**OQ-MT1-12. May production-only MT1 items merge between the pre-approval commit and the campaign?**
- (a) No merges in that window at all (as A21 OQ-F7 a for MT6F). + simplest rule. - MT1 stalls for the length of the window.
- (b) Yes, if the item changes no module the study run imports, the guard set passes unedited and `studies/`/`datasets/` are unchanged; the campaign runs from its pinned commit (A18 OQ-10). + the demo work continues. - one more rule for the lead to check.
- **Recommendation: (b)** for MT1-01..08 and MT1-10; MT1-09 (shared PyVRP engine) waits like MT1-11/12.

---

## 7. Verification plan

### 7.1 Per item

| Item | Suites (worktree, `PYTHONPATH` set) |
|---|---|
| every Python item | new red tests; `uniride_core/tests`; `optimizer_api/tests`; registry snapshot; study guard set (section 2.1); `split_parity` golden; `git diff --stat WIP -- academic_benchmark/studies academic_benchmark/datasets` empty |
| 05, 06, 11 | plus `academic_benchmark/tests`; the canonical 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:124-128`) |
| 02, 03 | plus `scripts/test_verify_fleet_rerun.py`, `scripts/test_plan_fleet_pareto.py` and the tests of `scripts/run_exact_wave_gaps.py` [A: the developer locates them] |
| 04, 10 | `npx vitest run` for the touched services and pages; `npx tsc --noEmit`; `scripts/research-tests` |
| reviewer | runs the same suites, then reverts only the source change in a scratch worktree and shows the red test fails |

### 7.2 Demo acceptance (before MT1-13, run by the lead or a developer)

1. **Replay:** the MT6-04 replay approach (A20 L4): archived Dudullu daily requests for week 2026-10-05 (4sw5so archive), API default `ga_split`, seed 42, in memory, before and after MT1. Required: identical vehicles per wave and day, identical total durations, every response certified.
2. **Schedule check:** for every replayed route, the server schedule equals the TypeScript interval (`[anchor - total, anchor]` pickup, `[anchor, anchor + total]` drop-off) within the arc tolerance; every pickup arrives at school by its anchor; no route starts before 00:00 or ends after the day end.
3. **Known number:** 2026-10-05 still needs 3 vehicles (memory note: data-driven, 27 students, capacity floor 2); the page wording says "this plan uses 3" and explains the floor, without calling 3 "the minimum" unless V01 proves it.
4. **Windowed sanity set:** the audit H2, H3, H4 and N1 scenarios through `/optimize` with `ga_split`: H2 refused or rerouted feasibly, H3 times as in MT1-01 test 3, H4 certified, N1 one vehicle.

These are acceptance checks, not evidence of algorithm quality; no superiority claim follows from them.

---

## 8. Out of scope and deferred

- **MT2 / H18:** `/optimize` ignores a caller-supplied `distance_matrix`; matrix domain enum. MT1 uses only the captured authoritative arcs.
- **MT3 / H7:** global solver cap, `/compare` threads, `/optimize` time limit.
- **MT4:** engine separation, one ID per implementation (H9 rest), L13 boundary hygiene, promoted-config import.
- **MT7:** frontend polling (H14), DTO mapper, `run/status` and `run/stop` routes.
- Time windows on the typed (`vehicle_types`) path; it keeps refusing them.
- Exact solver (E-series) and fleet selection: they consume archived route intervals and are not changed.
- Time-dependent or live (Google) travel times (T08).
- L12-1 (sweep fallback coordinates) and L12-5 (`is_asymmetric` default): low impact, left as polish.
