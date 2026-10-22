# C-19 design note: instance-scaled fixed budget levels in the study contract (2026-10-21)

Owner decision (DECISION_LOG A17, 2026-10-21; revised the same day from 20 x / 100 x): the Bildiri profile's fixed budget levels are 50 x and 250 x n(n-1)/2 objective evaluations per instance (n = the dataset dimension), so every algorithm gets the same budget on a given instance, but the number differs between instances.

## Today

- `StudyManifestV1.fixed_budget_levels: list[PositiveInt]` (required) is one level list applied to every dataset.
- `studies/service.py:expand_plan` builds one fair manifest per level (`governed_comparison_manifest(FIXED_BUDGET, level, base_seed)`) and one row per (dataset, algorithm, level, replicate). Seeds do not depend on the level.
- `studies/smoke.py` selects `min(fixed_budget_levels)` and refuses a fixed rows file with more than one `evaluation_budget`.

A single list cannot state per-instance levels truthfully: any number put in it would be run on every dataset.

## Options

1. **Explicit per-dataset table plus the declared rule, recomputed by a validator (chosen).** New optional field `scaled_fixed_budget_levels` = `{rule: "two_opt_scan_multiples_v1", scan_multipliers: [50, 250], levels_by_dataset: {dataset_id: [levels]}}`. `fixed_budget_levels` becomes optional; exactly one of the two must be given.
2. Rule only (multipliers in the study, levels computed at plan time). Smaller JSON, but the study file no longer says which budgets run; a reader has to recompute them.
3. Sidecar budget file next to `study.json`. The study contract would still carry a `fixed_budget_levels` value that is not what runs. Rejected (not truthful).
4. Reuse `fixed_budget_levels` for the multipliers. Changes the meaning of an existing field; an older reader would run budgets of 50 and 250. Rejected.

## Choice and why

Option 1: the profile is self-describing (rule, multipliers and the resulting numbers are all in `study.json`), and nothing is trusted that can be recomputed:

- contract level (`StudyManifestV1`, no file access): multipliers unique and increasing; one level per multiplier for each dataset; every level is `multiplier x k` with the same `k` for all multipliers of a dataset, and `k` is `n(n-1)/2` for an integer `n >= 2`;
- service level (`expand_plan`, called by `build_study_plan`): the table keys equal the study's dataset ids exactly; each row of the table equals `multiplier x n(n-1)/2` with `n` = the dataset manifest `dimension`; in scaled mode the manifest `dimension` must also equal the `DIMENSION:` header of the checksum-verified artifact. Any mismatch is a `StudyServiceError`.

Fairness meaning is unchanged: every fixed row still carries one budget and one protocol manifest built for exactly that budget; all algorithms on one instance get the same levels; seeds are untouched; the pooling identity (`protocol_registry.assert_single_pooling_group`) is not changed. The schema change is backward-compatible: every document valid under the current `uniride-study/v1` stays valid with the same meaning (the old field is relaxed to optional, one optional field is added); an older reader refuses a scaled profile because `extra` is forbidden, so it can never misread one. The schema id stays `uniride-study/v1`; `study-v1.schema.json` is regenerated and its E12 pin updated with the `study.json` pin.

Smoke: the default slice takes the lowest level **per dataset** (identical to today for unscaled studies). For a scaled study the fixed rows file may hold one level per dataset (still exactly one level per instance); unscaled studies keep the one-level-per-file rule. The report names the level per dataset.

Not changed: `PaperMetadataV1` (the GA/PSO provenance note goes into the commit message and DECISION_LOG), the secondary (native) protocol of the profile, `PlanRow`, executors, solvers.

## Files

- `academic_benchmark/contracts/study.py`, `academic_benchmark/schemas/study-v1.schema.json` (regenerated)
- `academic_benchmark/studies/service.py`, `academic_benchmark/studies/smoke.py`
- `academic_benchmark/studies/bildiri2026/study.json`
- tests: `test_bildiri_study_profile.py`, new `test_scaled_budget_levels.py`, profile-dependent expectations in `test_study_service.py`, `test_study_smoke.py`, `test_memetic_polish_truthfulness.py`; pins in `test_exact_reference_boundaries.py` (and any other pin of the two files)

## Outcome (implementation, 2026-10-21)

- Implemented as chosen; no fairness meaning, pooling identity or executor changed. Mutants (service recomputation off, contract n(n-1)/2 check off, wrong multiplier, wrong n, artifact DIMENSION check off, GA population ignored, smoke global-minimum slice) were all caught.
- Parameter note: the C-04 `max_iterations`/`max_no_improvement` 60000 of pure GWO/HHO would stop them before the 100-scan budget (pure GWO spends about one evaluation per iteration; 100 x 1275 = 127500 > 60000), so the profile sets 495000 (the largest level) for the two pure entries; the memetic entries keep 60000 (they never reach it at these budgets).
- Smoke observation (one replicate, no claim): with the explicit C-16a/C-16b defaults the pure GA (population 20, 500 generations) stops at 9020 evaluations and the PSO (swarm 50, 500 iterations) at 25500, both by `max_iterations`, below every level of the profile; at the 20-scan level the memetic GA spends the whole budget after its 20 initial evaluations in the initial 2-opt (no generation).
- Provenance (plan section 1.4): the published Bildiri 2026 GA and PSO numbers came from the archived memetic GA and memetic PSO; the profile's `Core-GA-TSP` and `Core-PSO-TSP` are the pure canonical algorithms. `PaperMetadataV1` is not changed for this note.

## Revision after the first C-19 smoke (owner 2026-10-21, DECISION_LOG A17 "revising C-19")

- Levels are now 50 x and 250 x n(n-1)/2 (replacing 20 x / 100 x): eil51 63750/318750, berlin52 66300/331500, ft53 68900/344500, st70 120750/603750, eil76 142500/712500, kroA100 and rd100 247500/1237500.
- The budget is the stopping rule. Pure GA, PSO, memetic GA, pure GWO and pure HHO use `max_iterations` = `max_no_improvement` = 1237500, a value derived from the profile: the largest level (250 x 4950). Each generation or iteration of these algorithms spends at least one objective evaluation, so a limit equal to the largest budget cannot stop a run first. PSO `reinit_interval` 50 stays: it is a counted diversity step, not a stopping rule. Memetic GWO/HHO keep the C-04 value 60000. An upper estimate from the eil51 iteration rate (about 1150 iterations per 64000 evaluations) gives about 22000 iterations at the largest level; the measured count at the largest level is about 6125 (GWO) and 6025 (HHO) on kroA100 at 250 x, so 60000 does not bind (estimate checked by `test_bildiri_budget_is_the_stopping_rule.py`).
- 2-opt, 3-opt and Or-opt state the registry defaults of the fixed-budget path (`max_iterations` 1000, `first_improvement` false, `window` 12 for 3-opt and 3 for Or-opt); one iteration is at least one full scan, so the limit cannot fire before 250 scans. 2-opt and Or-opt can still stop earlier at a local optimum (`no_improving_move`, the documented stop of fairness design rule 6), with no restart: measured once (seed 1), 2-opt stopped this way on eil51 at both levels and on kroA100 at 250 x, but spent the whole budget on kroA100 at 50 x; Or-opt stopped this way only on eil51 at 250 x.
- This supersedes the parameter note and the smoke observation of the previous section (the 495000 value and the GA/PSO stops at 9020/25500 evaluations).

- Schedule dependency. For GWO and HHO, `max_iterations` is not only a stop limit: in the solvers as of this branch it also sets the explore-to-exploit schedule (GWO `a = initial_a*(1 - it/max_iterations)`, HHO escape energy `E = 2*e0*(1 - it/max_iterations)`), so with 1237500 the schedule would depend on instance and level. Owner decision (DECISION_LOG A17, 2026-10-22, "in fixed-budget runs the GWO/HHO schedule follows the budget"): in fixed-budget runs the GWO and HHO schedules, pure and memetic, decay with the share of the budget spent, native runs keep the iteration-based schedule, and `max_iterations` then only stops runs. That change is made in the solvers on the separate branch `feat/gwo-hho-budget-schedule`; this profile describes that end state, and the lead merges C-19 only after the schedule branch, so the limits above act as pure stop limits when the profile is used.
- Schema: the exactly-one rule is also stated in `study-v1.schema.json` (`oneOf`: `fixed_budget_levels` as an array with `scaled_fixed_budget_levels` absent or null, or the reverse), added through the model's `json_schema_extra`.
- Package D: result rows carry only the raw `evaluation_budget`. kroA100 and rd100 share raw levels (247500 and 1237500) while every other instance has its own, so Package D must group rows by the level index or the scan multiple (50 or 250), never by the raw budget value across instances.
