# C-19 design note: instance-scaled fixed budget levels in the study contract (2026-10-21)

Owner decision (DECISION_LOG A17, 2026-10-21): the Bildiri profile's fixed budget levels are 20 x and 100 x n(n-1)/2 objective evaluations per instance (n = the dataset dimension), so every algorithm gets the same budget on a given instance, but the number differs between instances.

## Today

- `StudyManifestV1.fixed_budget_levels: list[PositiveInt]` (required) is one level list applied to every dataset.
- `studies/service.py:expand_plan` builds one fair manifest per level (`governed_comparison_manifest(FIXED_BUDGET, level, base_seed)`) and one row per (dataset, algorithm, level, replicate). Seeds do not depend on the level.
- `studies/smoke.py` selects `min(fixed_budget_levels)` and refuses a fixed rows file with more than one `evaluation_budget`.

A single list cannot state per-instance levels truthfully: any number put in it would be run on every dataset.

## Options

1. **Explicit per-dataset table plus the declared rule, recomputed by a validator (chosen).** New optional field `scaled_fixed_budget_levels` = `{rule: "two_opt_scan_multiples_v1", scan_multipliers: [20, 100], levels_by_dataset: {dataset_id: [levels]}}`. `fixed_budget_levels` becomes optional; exactly one of the two must be given.
2. Rule only (multipliers in the study, levels computed at plan time). Smaller JSON, but the study file no longer says which budgets run; a reader has to recompute them.
3. Sidecar budget file next to `study.json`. The study contract would still carry a `fixed_budget_levels` value that is not what runs. Rejected (not truthful).
4. Reuse `fixed_budget_levels` for the multipliers. Changes the meaning of an existing field; an older reader would run budgets of 20 and 100. Rejected.

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
