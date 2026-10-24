"""Cost estimator for a study profile and a candidate run plan (Gate D, D-04b1; plan 2026-10-23 item D-04b, DECISION_LOG A18).

``python -m academic_benchmark.studies.estimate --study <repository-relative study.json> --out <dir outside the repository>``

For a profile and a candidate run plan (run count, level indices, instances, algorithms) the tool prints

* the number of runs and the **evaluation upper bound** per cell (dataset, algorithm, level index): ``level x runs`` for fixed-budget
  cells (local searches may stop earlier at a local optimum, so it is an upper bound); native cells have no evaluation bound;
* an **estimated wall time** from a measured **calibration slice** on the machine where it runs: one replicate per algorithm on the
  smallest and on the largest instance of the profile at the lowest level (plus one discarded warm-up replicate of the same cell on
  the smallest instance, so Numba compilation is not counted; ``--no-warmup`` drops it). The seconds per evaluation of an
  algorithm at the size of any other instance are interpolated linearly in the dimension between the two measured sizes;
* the seconds per evaluation of the Numba objective and of the Python polish, **separately** (``backend split``): from the stage
  records of a composite row, from a row without polish, or derived from a row with 2-opt polish and the objective rate of the
  polish-free rows of the same instance (the source of each figure is printed);
* for native runs, the time per iteration (and per stage for composites) at **provisional** limits. Every line that shows a native
  limit or a native time carries the label ``PROVISIONAL, NOT A SCIENTIFIC SETTING``; the limits are inputs for the owner's choice
  (OQ-4), not a setting;
* for the memetic GWO/HHO IDs, per instance, the iterations reached, the evaluations per iteration (objective and polish
  separately) and the projected iteration count at the top level (``level / evaluations per iteration``); with ``--probe-250x``
  one replicate of each of these IDs runs at the top level (250x n(n-1)/2) on the largest instance to show whether
  ``max_iterations`` / ``max_no_improvement`` binds before the budget (input to OQ-16).

The clock and the solver are injected, so the unit tests use no real timing. Levels are chosen by **level index**: a profile with
instance-scaled levels has a different raw budget on every instance, so a plan that names a raw level for more than one instance
is refused. Output goes to a folder outside the repository (``estimate.txt`` and ``estimate.json``) with the machine and the commit.
The numbers are planning numbers, not evidence: they say nothing about the quality of any algorithm. The tool changes no profile
value, algorithm, exposure or protocol; it opens no ``tsplib.db`` and runs no solver other than through the governed gateway.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from academic_benchmark.analysis.manifests import collect_environment
from academic_benchmark.composite_protocol import is_composite_algorithm
from academic_benchmark.fair_pilot import (
    FairPilotError,
    _execute_preflighted_run,
    _git_metadata,
    _is_within,
    _registered_algorithm_ids,
    _registry_executor,
)
from academic_benchmark.core.preflight import probe_runtime_backends
from academic_benchmark.studies.run import StudyRunError, _main_working_tree, build_artifact_loader
from academic_benchmark.studies.service import (
    DEFAULT_BACKEND_POLICY,
    PlanRow,
    ResolvedDataset,
    StudyPlan,
    StudyServiceError,
    _native_algorithm_ids,
    build_study_plan,
    check_budget_levels,
)
from academic_benchmark.studies.smoke import (
    StudySmokeError,
    _fixed_config,
    _native_config,
    _row_params,
    assert_no_ranking_words,
)
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from uniride_core.algorithms.capabilities import ExecutionProtocol

PROVISIONAL_LABEL = "PROVISIONAL, NOT A SCIENTIFIC SETTING"
NOTICE = (
    "Planning numbers, not evidence: measured on a calibration slice on this machine. They say nothing about any algorithm; "
    "evaluation counts are upper bounds (local searches may stop earlier)."
)
SCHEMA = "uniride-cost-estimate/v1"
MEMETIC_GWO_HHO_IDS = ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt")
TEXT_FILE = "estimate.txt"
JSON_FILE = "estimate.json"

Clock = Callable[[], float]


class EstimateError(ValueError):
    """The candidate plan, the calibration or the output location was refused."""


# --------------------------------------------------------------------------------------------------- data classes
@dataclass(frozen=True)
class RunPlanSpec:
    """A candidate run plan. ``None`` means "the profile's value" (all instances, all algorithms, all level indices).

    ``level_indices`` selects levels by their position in the profile's level list (the same index on every instance);
    ``raw_levels`` names raw budgets and is accepted only where one raw value is one level index on every selected instance.
    """

    run_count: Optional[int] = None
    level_indices: Optional[Tuple[int, ...]] = None
    raw_levels: Optional[Tuple[int, ...]] = None
    dataset_ids: Optional[Tuple[str, ...]] = None
    algorithm_ids: Optional[Tuple[str, ...]] = None
    include_native: bool = True


@dataclass(frozen=True)
class NativeLimits:
    """Provisional iteration limits of the native calibration rows (never a scientific setting)."""

    global_iterations: int = 2
    polish_iterations: int = 2

    label = PROVISIONAL_LABEL


@dataclass(frozen=True)
class Cell:
    dataset_id: str
    problem_name: str
    dimension: int
    algorithm_id: str
    protocol: ExecutionProtocol
    level_index: Optional[int]
    level: Optional[int]
    runs: int
    evaluation_upper_bound: Optional[int]


@dataclass(frozen=True)
class SolverOutcome:
    objective_evaluations: int
    iterations: Optional[int] = None
    polish_evaluations: int = 0
    termination_reason: Optional[str] = None
    stages: Tuple[Mapping[str, Any], ...] = ()


Solver = Callable[[PlanRow, Mapping[str, Any]], SolverOutcome]


@dataclass(frozen=True)
class CalibrationPoint:
    dataset_id: str
    dimension: int
    algorithm_id: str
    protocol: ExecutionProtocol
    level: Optional[int]
    elapsed_seconds: float
    outcome: SolverOutcome
    warmup_seconds: Optional[float] = None

    @property
    def seconds_per_evaluation(self) -> float:
        if self.outcome.objective_evaluations <= 0:
            raise EstimateError(f"{self.algorithm_id} on {self.dataset_id}: the calibration row consumed no evaluation")
        return self.elapsed_seconds / self.outcome.objective_evaluations


@dataclass(frozen=True)
class SplitRow:
    dataset_id: str
    dimension: int
    algorithm_id: str
    objective_seconds_per_evaluation: Optional[float]
    polish_seconds_per_evaluation: Optional[float]
    source: str


@dataclass(frozen=True)
class MemeticPoint:
    dataset_id: str
    dimension: int
    algorithm_id: str
    level: int
    top_level: int
    iterations: Optional[int]
    objective_evaluations_per_iteration: Optional[float]
    polish_evaluations_per_iteration: Optional[float]
    evaluations_per_iteration: Optional[float]
    projected_iterations_at_top_level: Optional[float]
    max_iterations: Optional[int]
    max_no_improvement: Optional[int]


@dataclass(frozen=True)
class ProbePoint:
    algorithm_id: str
    dataset_id: str
    level: int
    consumed_evaluations: int
    polish_evaluations: int
    iterations: Optional[int]
    termination_reason: Optional[str]
    elapsed_seconds: float
    limit_binds_before_budget: bool
    max_iterations: Optional[int]
    max_no_improvement: Optional[int]


@dataclass(frozen=True)
class NativePoint:
    dataset_id: str
    dimension: int
    algorithm_id: str
    limits: str
    elapsed_seconds: float
    iterations: Optional[int]
    seconds_per_iteration: Optional[float]
    stage_seconds_per_iteration: Mapping[str, Optional[float]]
    limits_label: str = PROVISIONAL_LABEL


def _interpolate(points: Sequence[Tuple[int, float]], n: int) -> float:
    ordered = sorted(points)
    if len(ordered) == 1:
        return ordered[0][1]
    (n0, v0), (n1, v1) = ordered[0], ordered[-1]
    if n1 == n0:
        return sum(v for _, v in ordered) / len(ordered)
    share = min(max((n - n0) / (n1 - n0), 0.0), 1.0)
    return v0 + share * (v1 - v0)


@dataclass(frozen=True)
class Calibration:
    fixed: Tuple[CalibrationPoint, ...] = ()
    native: Tuple[CalibrationPoint, ...] = ()
    memetic: Tuple[MemeticPoint, ...] = ()
    probes: Tuple[ProbePoint, ...] = ()
    native_limits: NativeLimits = field(default_factory=NativeLimits)
    native_descriptions: Mapping[str, str] = field(default_factory=dict)
    smallest_dataset_id: Optional[str] = None
    largest_dataset_id: Optional[str] = None

    def seconds_per_evaluation(self, algorithm_id: str, dimension: int) -> float:
        points = [(p.dimension, p.seconds_per_evaluation) for p in self.fixed if p.algorithm_id == algorithm_id]
        if not points:
            raise EstimateError(f"no calibration row for {algorithm_id}: no wall-time estimate is possible")
        return _interpolate(points, dimension)

    def native_seconds_per_run(self, algorithm_id: str, dimension: int) -> float:
        points = [(p.dimension, p.elapsed_seconds) for p in self.native if p.algorithm_id == algorithm_id]
        if not points:
            raise EstimateError(f"no native calibration row for {algorithm_id}")
        return _interpolate(points, dimension)

    def backend_split(self) -> Tuple[SplitRow, ...]:
        references: Dict[str, List[float]] = {}
        for point in self.fixed:  # objective rate of the rows without any polish, per instance
            if point.outcome.polish_evaluations == 0 and not point.outcome.stages:
                references.setdefault(point.dataset_id, []).append(point.seconds_per_evaluation)
        rows = []
        for point in self.fixed:
            rows.append(_split(point, references.get(point.dataset_id)))
        return tuple(rows)

    def native_points(self) -> Tuple[NativePoint, ...]:
        return tuple(self._native_point(p) for p in self.native)

    def _native_point(self, point: CalibrationPoint) -> NativePoint:
        iterations = point.outcome.iterations
        stage_rates: Dict[str, Optional[float]] = {}
        for stage in point.outcome.stages:
            count, elapsed = stage.get("iterations"), stage.get("elapsed_sec")
            stage_rates[str(stage.get("name"))] = (
                float(elapsed) / count if isinstance(count, int) and count > 0 and isinstance(elapsed, (int, float)) else None
            )
        return NativePoint(
            dataset_id=point.dataset_id, dimension=point.dimension, algorithm_id=point.algorithm_id,
            limits=self.native_descriptions.get(point.algorithm_id, ""), elapsed_seconds=point.elapsed_seconds,
            iterations=iterations,
            seconds_per_iteration=(point.elapsed_seconds / iterations if iterations else None),
            stage_seconds_per_iteration=stage_rates,
        )


def _split(point: CalibrationPoint, references: Optional[List[float]]) -> SplitRow:
    outcome = point.outcome
    base = (point.dataset_id, point.dimension, point.algorithm_id)
    stages = {str(s.get("name")): s for s in outcome.stages}
    if "global" in stages and "polish" in stages:
        def rate(stage: Mapping[str, Any]) -> Optional[float]:
            used, elapsed = stage.get("consumed_evaluations"), stage.get("elapsed_sec")
            return float(elapsed) / used if isinstance(used, int) and used > 0 and isinstance(elapsed, (int, float)) else None

        return SplitRow(*base, rate(stages["global"]), rate(stages["polish"]), "stage records of the composite row")
    if outcome.polish_evaluations == 0:
        return SplitRow(*base, point.seconds_per_evaluation, None, "row without polish (objective only)")
    if not references:
        return SplitRow(*base, None, None, "not separable: no polish-free row on this instance")
    objective_rate = sum(references) / len(references)
    objective_count = outcome.objective_evaluations - outcome.polish_evaluations
    polish_seconds = max(point.elapsed_seconds - objective_count * objective_rate, 0.0)
    return SplitRow(
        *base, objective_rate, polish_seconds / outcome.polish_evaluations,
        "derived: objective rate of the polish-free rows of this instance, polish = the remaining time",
    )


# ---------------------------------------------------------------------------------------------------- the cells
def _selected(study_ids: Sequence[str], wanted: Optional[Sequence[str]], what: str) -> Tuple[str, ...]:
    if wanted is None:
        return tuple(study_ids)
    unknown = [item for item in wanted if item not in study_ids]
    if unknown:
        raise EstimateError(f"{what} not in the profile: {unknown}")
    return tuple(item for item in study_ids if item in wanted)


def _levels(plan: StudyPlan) -> Dict[str, Tuple[int, ...]]:
    try:
        return check_budget_levels(plan.study, plan.datasets)
    except StudyServiceError as exc:
        raise EstimateError(f"budget levels refused: {exc}") from exc


def _level_indices(spec: RunPlanSpec, datasets: Sequence[ResolvedDataset], levels: Mapping[str, Tuple[int, ...]]) -> Tuple[int, ...]:
    if spec.level_indices is not None and spec.raw_levels is not None:
        raise EstimateError("name levels by level index or by raw value, not both")
    counts = {len(levels[d.dataset_id]) for d in datasets}
    if len(counts) != 1:
        raise EstimateError("the instances of the profile do not have the same number of levels")
    count = counts.pop()
    if spec.raw_levels is not None:
        indices = []
        for value in spec.raw_levels:
            found = {}
            for dataset in datasets:
                row = levels[dataset.dataset_id]
                if value not in row:
                    raise EstimateError(
                        f"raw level {value} is not a level of {dataset.dataset_id} {list(row)}: a plan that mixes levels "
                        "across instances by raw value is refused; name levels by level index"
                    )
                found[dataset.dataset_id] = row.index(value)
            if len(set(found.values())) != 1:
                raise EstimateError(
                    f"raw level {value} is level index {sorted(set(found.values()))} on different instances ({found}): a plan that "
                    "mixes levels across instances by raw value is refused; name levels by level index"
                )
            indices.append(next(iter(found.values())))
        return tuple(sorted(set(indices)))
    if spec.level_indices is None:
        return tuple(range(count))
    for index in spec.level_indices:
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < count:
            raise EstimateError(f"level index {index!r} is outside 0..{count - 1}")
    return tuple(sorted(set(spec.level_indices)))


def build_cells(plan: StudyPlan, spec: RunPlanSpec) -> Tuple[Cell, ...]:
    """The cells of the candidate plan with their evaluation upper bound (``level x runs``; native cells have none)."""
    study = plan.study
    runs = study.run_count if spec.run_count is None else spec.run_count
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1:
        raise EstimateError(f"run count must be a positive integer, got {runs!r}")
    dataset_ids = _selected([d.dataset_id for d in plan.datasets], spec.dataset_ids, "dataset ids")
    datasets = [d for d in plan.datasets if d.dataset_id in dataset_ids]
    algorithms = _selected(study.algorithm_ids, spec.algorithm_ids, "algorithm ids")
    levels = _levels(plan)
    indices = _level_indices(spec, datasets, levels)
    native_ids = [a for a in _native_algorithm_ids(study) if a in algorithms] if spec.include_native else []
    cells: List[Cell] = []
    for dataset in datasets:
        n = dataset.manifest.dimension
        for algorithm_id in algorithms:
            for index in indices:
                level = levels[dataset.dataset_id][index]
                cells.append(Cell(dataset.dataset_id, dataset.problem_name, n, algorithm_id,
                                  ExecutionProtocol.FIXED_BUDGET, index, level, runs, level * runs))
        for algorithm_id in native_ids:
            cells.append(Cell(dataset.dataset_id, dataset.problem_name, n, algorithm_id,
                              ExecutionProtocol.NATIVE_TERMINATION, None, None, runs, None))
    return tuple(cells)


# ----------------------------------------------------------------------------------------------- the calibration
def native_row_params(study: Any, row: PlanRow, limits: NativeLimits) -> Dict[str, Any]:
    """Parameters of a native calibration row: the study's block with the provisional iteration limits on every stage."""
    params = _row_params(study, row)
    if is_composite_algorithm(row.algorithm_id):
        params["global"] = {**params.get("global", {}), "max_iterations": limits.global_iterations}
        params["polish"] = {**params.get("polish", {}), "max_iterations": limits.polish_iterations}
    else:
        params["max_iterations"] = limits.global_iterations
    return params


def _describe_limits(algorithm_id: str, limits: NativeLimits) -> str:
    if is_composite_algorithm(algorithm_id):
        return f"global max_iterations={limits.global_iterations}, polish max_iterations={limits.polish_iterations}"
    return f"max_iterations={limits.global_iterations}"


def _first_row(plan: StudyPlan, dataset_id: str, algorithm_id: str, protocol: ExecutionProtocol, level: Optional[int]) -> PlanRow:
    for row in plan.rows:
        if (row.dataset_id == dataset_id and row.algorithm_id == algorithm_id and row.protocol is protocol
                and row.budget_level == level and row.replicate == 0):
            return row
    raise EstimateError(f"the study plan has no replicate-0 row for {algorithm_id} on {dataset_id} at level {level}")


def _extremes(datasets: Sequence[ResolvedDataset]) -> Tuple[ResolvedDataset, ResolvedDataset]:
    smallest = largest = datasets[0]
    for dataset in datasets[1:]:  # ties keep the first listed
        if dataset.manifest.dimension < smallest.manifest.dimension:
            smallest = dataset
        if dataset.manifest.dimension > largest.manifest.dimension:
            largest = dataset
    return smallest, largest


def calibrate(
    plan: StudyPlan, solver: Solver, clock: Clock, *, spec: Optional[RunPlanSpec] = None,
    native_limits: Optional[NativeLimits] = None, warmup: bool = True, probe_250x: bool = False,
    run_slice: bool = True, progress: Optional[Callable[[str], None]] = None,
) -> Calibration:
    """Measure the calibration slice (and, on request, the 250x probe) with the injected ``solver`` and ``clock``.

    The slice is one replicate per algorithm on the smallest and the largest instance of the profile at that instance's lowest
    level; with ``warmup`` the same cell is first run once on the smallest instance and discarded (its time is kept as
    ``warmup_seconds``). Native algorithms of the profile run once per extreme instance with the provisional ``native_limits``.
    """
    spec = spec or RunPlanSpec()
    limits = native_limits or NativeLimits()
    note = progress or (lambda _message: None)
    study = plan.study
    algorithms = _selected(study.algorithm_ids, spec.algorithm_ids, "algorithm ids")
    levels = _levels(plan)
    smallest, largest = _extremes(plan.datasets)
    extremes = [smallest] if smallest is largest else [smallest, largest]

    def timed(row: PlanRow, params: Mapping[str, Any], label: str) -> Tuple[SolverOutcome, float]:
        note(f"{label} ...")
        started = clock()
        outcome = solver(row, params)
        elapsed = clock() - started
        note(f"{label}: {outcome.objective_evaluations} evaluations, {elapsed:.3f} s")
        return outcome, elapsed

    fixed: List[CalibrationPoint] = []
    native: List[CalibrationPoint] = []
    memetic: List[MemeticPoint] = []
    descriptions: Dict[str, str] = {}
    if run_slice:
        for algorithm_id in algorithms:
            warm: Optional[float] = None
            for dataset in extremes:
                level = min(levels[dataset.dataset_id])
                row = _first_row(plan, dataset.dataset_id, algorithm_id, ExecutionProtocol.FIXED_BUDGET, level)
                params = _row_params(study, row)
                if warmup and dataset is smallest:
                    _outcome, warm = timed(row, params, f"warm-up {algorithm_id} on {dataset.dataset_id}")
                outcome, elapsed = timed(row, params, f"calibrate {algorithm_id} on {dataset.dataset_id} level {level}")
                n = dataset.manifest.dimension
                fixed.append(CalibrationPoint(dataset.dataset_id, n, algorithm_id, ExecutionProtocol.FIXED_BUDGET, level, elapsed,
                                              outcome, warm if dataset is smallest else None))
                if algorithm_id in MEMETIC_GWO_HHO_IDS:
                    memetic.append(_memetic_point(dataset, algorithm_id, level, max(levels[dataset.dataset_id]), outcome, params))
        native_ids = [a for a in _native_algorithm_ids(study) if a in algorithms] if spec.include_native else []
        for algorithm_id in native_ids:
            descriptions[algorithm_id] = _describe_limits(algorithm_id, limits)
            for dataset in extremes:
                row = _first_row(plan, dataset.dataset_id, algorithm_id, ExecutionProtocol.NATIVE_TERMINATION, None)
                params = native_row_params(study, row, limits)
                if warmup and dataset is smallest:
                    timed(row, params, f"warm-up native {algorithm_id} on {dataset.dataset_id}")
                outcome, elapsed = timed(row, params, f"calibrate native {algorithm_id} on {dataset.dataset_id} ({PROVISIONAL_LABEL})")
                native.append(CalibrationPoint(dataset.dataset_id, dataset.manifest.dimension, algorithm_id,
                                               ExecutionProtocol.NATIVE_TERMINATION, None, elapsed, outcome))
    probes: List[ProbePoint] = []
    if probe_250x:
        for algorithm_id in MEMETIC_GWO_HHO_IDS:
            if algorithm_id not in algorithms:
                continue
            top = max(levels[largest.dataset_id])
            row = _first_row(plan, largest.dataset_id, algorithm_id, ExecutionProtocol.FIXED_BUDGET, top)
            params = _row_params(study, row)
            outcome, elapsed = timed(row, params, f"probe {algorithm_id} on {largest.dataset_id} at level {top}")
            probes.append(ProbePoint(
                algorithm_id, largest.dataset_id, top, outcome.objective_evaluations, outcome.polish_evaluations,
                outcome.iterations, outcome.termination_reason, elapsed, outcome.objective_evaluations < top,
                params.get("max_iterations"), params.get("max_no_improvement"),
            ))
    return Calibration(tuple(fixed), tuple(native), tuple(memetic), tuple(probes), limits, descriptions,
                       smallest.dataset_id if run_slice else None, largest.dataset_id if run_slice else None)


def _memetic_point(dataset: ResolvedDataset, algorithm_id: str, level: int, top: int, outcome: SolverOutcome,
                   params: Mapping[str, Any]) -> MemeticPoint:
    iterations = outcome.iterations
    if iterations:
        polish = outcome.polish_evaluations / iterations
        objective = (outcome.objective_evaluations - outcome.polish_evaluations) / iterations
        total = outcome.objective_evaluations / iterations
        projected: Optional[float] = top / total if total > 0 else None
    else:
        polish = objective = total = projected = None
    return MemeticPoint(dataset.dataset_id, dataset.manifest.dimension, algorithm_id, level, top, iterations, objective, polish,
                        total, projected, params.get("max_iterations"), params.get("max_no_improvement"))


# ---------------------------------------------------------------------------------------------------- the estimate
@dataclass(frozen=True)
class CellEstimate:
    cell: Cell
    seconds: float


@dataclass(frozen=True)
class Estimate:
    cells: Tuple[CellEstimate, ...]
    fixed_runs: int
    fixed_evaluation_upper_bound: int
    fixed_seconds: float
    native_runs: int
    native_seconds: float  # at the provisional native limits of the calibration


def estimate(cells: Sequence[Cell], calibration: Calibration) -> Estimate:
    """Wall time per cell: fixed = evaluation upper bound x measured seconds per evaluation; native = runs x measured seconds per
    run at the provisional limits (reported separately and labelled)."""
    entries: List[CellEstimate] = []
    fixed_runs = bound = native_runs = 0
    fixed_seconds = native_seconds = 0.0
    for cell in cells:
        if cell.protocol is ExecutionProtocol.FIXED_BUDGET:
            seconds = cell.evaluation_upper_bound * calibration.seconds_per_evaluation(cell.algorithm_id, cell.dimension)
            fixed_runs += cell.runs
            bound += cell.evaluation_upper_bound
            fixed_seconds += seconds
        else:
            seconds = cell.runs * calibration.native_seconds_per_run(cell.algorithm_id, cell.dimension)
            native_runs += cell.runs
            native_seconds += seconds
        entries.append(CellEstimate(cell, seconds))
    return Estimate(tuple(entries), fixed_runs, bound, fixed_seconds, native_runs, native_seconds)


# ---------------------------------------------------------------------------------------------------- the report
def collect_provenance(repository_root: Path) -> Dict[str, Any]:
    git = _git_metadata(Path(repository_root))
    environment = collect_environment()
    return {
        "commit": git.get("revision"), "dirty": git.get("dirty"), "git_error": git.get("git_error"),
        "machine": {
            "cpu": environment.cpu, "cpu_count": os.cpu_count(), "operating_system": environment.operating_system,
            "python": environment.python, "numpy": environment.numpy, "numba": environment.numba,
            "llvmlite": environment.llvmlite, "node": platform.node(),
        },
    }


def _hours(seconds: float) -> str:
    return f"{seconds:,.1f} s ({seconds / 3600.0:,.2f} h)"


def _num(value: Optional[float], digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:,.{digits}f}"


def _micro(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value * 1e6:,.2f} us"


def _plan_summary(plan: StudyPlan, spec: RunPlanSpec, cells: Sequence[Cell]) -> Dict[str, Any]:
    fixed = [c for c in cells if c.protocol is ExecutionProtocol.FIXED_BUDGET]
    return {
        "run_count": cells[0].runs if cells else None,
        "datasets": sorted({c.dataset_id for c in cells}),
        "algorithms": sorted({c.algorithm_id for c in fixed}),
        "native_algorithms": sorted({c.algorithm_id for c in cells if c.protocol is ExecutionProtocol.NATIVE_TERMINATION}),
        "level_indices": sorted({c.level_index for c in fixed}),
        "include_native": spec.include_native,
    }


def render_report(plan: StudyPlan, spec: RunPlanSpec, cells: Sequence[Cell], calibration: Calibration, result: Optional[Estimate],
                  provenance: Mapping[str, Any]) -> str:
    study = plan.study
    machine = provenance.get("machine", {})
    summary = _plan_summary(plan, spec, cells)
    lines = [
        f"Cost estimate for study {study.study_id} (profile status: {study.status})",
        NOTICE,
        f"commit: {provenance.get('commit')}  dirty: {provenance.get('dirty')}",
        "machine: " + ", ".join(f"{key}={value}" for key, value in machine.items()),
        f"backend policy: {plan.backend_policy.value}",
        "",
        f"Candidate plan: {summary['run_count']} runs per cell, instances {summary['datasets']}, level indices {summary['level_indices']}, "
        f"{len(summary['algorithms'])} fixed-budget algorithms, {len(summary['native_algorithms'])} native algorithms",
    ]
    fixed = [c for c in cells if c.protocol is ExecutionProtocol.FIXED_BUDGET]
    lines += ["", "Evaluation upper bound per instance and level index (all algorithms, all runs of the plan)"]
    groups: Dict[Tuple[str, int], List[Cell]] = {}
    for cell in fixed:
        groups.setdefault((cell.dataset_id, cell.level_index), []).append(cell)
    for (dataset_id, index), group in groups.items():
        lines.append(
            f"  {dataset_id}  level index {index}  level {group[0].level:,}  runs {sum(c.runs for c in group)}  "
            f"evaluation upper bound {sum(c.evaluation_upper_bound for c in group):,}"
        )
    lines.append(f"  total fixed-budget runs {sum(c.runs for c in fixed)}, evaluation upper bound {sum(c.evaluation_upper_bound for c in fixed):,}")
    if calibration.fixed:
        lines += ["", "Calibration slice (one replicate per algorithm, lowest level; seconds per evaluation measured on this machine)"]
        for point in calibration.fixed:
            warm = "" if point.warmup_seconds is None else f"  warm-up {point.warmup_seconds:,.3f} s (discarded)"
            lines.append(
                f"  {point.algorithm_id}  {point.dataset_id} (n={point.dimension})  level {point.level:,}  evaluations "
                f"{point.outcome.objective_evaluations:,}  {point.elapsed_seconds:,.3f} s  {_micro(point.seconds_per_evaluation)}/evaluation"
                f"  stop: {point.outcome.termination_reason}{warm}"
            )
        lines += ["", "Backend split: seconds per evaluation of the Numba objective and of the Python polish"]
        for row in calibration.backend_split():
            lines.append(
                f"  {row.algorithm_id}  {row.dataset_id} (n={row.dimension})  objective {_micro(row.objective_seconds_per_evaluation)}  "
                f"polish {_micro(row.polish_seconds_per_evaluation)}  [{row.source}]"
            )
    if calibration.memetic:
        lines += ["", "Memetic GWO/HHO per instance: iterations reached, evaluations per iteration, projected iterations at the top level"]
        for m in calibration.memetic:
            flag = ""
            if m.projected_iterations_at_top_level is not None and m.max_iterations is not None:
                flag = f"  projected iterations {'exceed' if m.projected_iterations_at_top_level > m.max_iterations else 'stay within'} max_iterations"
            lines.append(
                f"  {m.algorithm_id}  {m.dataset_id} (n={m.dimension})  iterations reached {m.iterations}  evaluations per iteration: objective "
                f"{_num(m.objective_evaluations_per_iteration)}, polish {_num(m.polish_evaluations_per_iteration)}, total "
                f"{_num(m.evaluations_per_iteration)}  projected iterations at level {m.top_level:,}: "
                f"{_num(m.projected_iterations_at_top_level, 0)}  (max_iterations {m.max_iterations}, max_no_improvement {m.max_no_improvement}){flag}"
            )
    if calibration.probes:
        lines += ["", "250x probe: one replicate of each memetic GWO/HHO ID at the top level of the largest instance"]
        for p in calibration.probes:
            verdict = "limit binds before the budget" if p.limit_binds_before_budget else "budget spent, limit did not bind"
            lines.append(
                f"  {p.algorithm_id}  {p.dataset_id}  level {p.level:,}  consumed {p.consumed_evaluations:,} (polish {p.polish_evaluations:,})  "
                f"iterations {p.iterations}  stop: {p.termination_reason}  {p.elapsed_seconds:,.1f} s  "
                f"(max_iterations {p.max_iterations}, max_no_improvement {p.max_no_improvement})  -> {verdict}"
            )
    if calibration.native:
        lines += ["", f"Native limits and times ({PROVISIONAL_LABEL}); the limits are inputs for the owner's choice, not a setting"]
        for algorithm_id, text in calibration.native_descriptions.items():
            lines.append(f"  Native limit {algorithm_id}: {text}  [{PROVISIONAL_LABEL}]")
        for point in calibration.native_points():
            stages = ", ".join(f"{name} {_num(rate, 4)} s/iteration" for name, rate in point.stage_seconds_per_iteration.items())
            lines.append(
                f"  Native {point.algorithm_id}  {point.dataset_id} (n={point.dimension})  run {point.elapsed_seconds:,.3f} s, "
                f"{_num(point.seconds_per_iteration, 4)} s/iteration over {point.iterations} iterations"
                f"{'  [' + stages + ']' if stages else ''}  [{PROVISIONAL_LABEL}]"
            )
    if result is not None:
        lines += ["", "Estimated wall time (serial, this machine; planning number)"]
        lines.append(
            f"  fixed budget: {result.fixed_runs} runs, evaluation upper bound {result.fixed_evaluation_upper_bound:,}, "
            f"estimated {_hours(result.fixed_seconds)}"
        )
        per_algorithm: Dict[str, float] = {}
        for entry in result.cells:
            if entry.cell.protocol is ExecutionProtocol.FIXED_BUDGET:
                per_algorithm[entry.cell.algorithm_id] = per_algorithm.get(entry.cell.algorithm_id, 0.0) + entry.seconds
        for algorithm_id, seconds in per_algorithm.items():
            lines.append(f"    {algorithm_id}: {_hours(seconds)}")
        if result.native_runs:
            lines.append(
                f"  native at the provisional limits: {result.native_runs} runs, estimated {_hours(result.native_seconds)}  [{PROVISIONAL_LABEL}]"
            )
    text = "\n".join(lines) + "\n"
    assert_no_ranking_words(text)
    return text


def report_payload(plan: StudyPlan, spec: RunPlanSpec, cells: Sequence[Cell], calibration: Calibration, result: Optional[Estimate],
                   provenance: Mapping[str, Any]) -> Dict[str, Any]:
    def point(p: CalibrationPoint) -> Dict[str, Any]:
        return {
            "dataset_id": p.dataset_id, "dimension": p.dimension, "algorithm_id": p.algorithm_id, "level": p.level,
            "elapsed_seconds": p.elapsed_seconds, "warmup_seconds": p.warmup_seconds,
            "objective_evaluations": p.outcome.objective_evaluations, "polish_evaluations": p.outcome.polish_evaluations,
            "iterations": p.outcome.iterations, "termination_reason": p.outcome.termination_reason,
            "seconds_per_evaluation": p.seconds_per_evaluation,
        }

    return {
        "schema": SCHEMA, "study_id": plan.study.study_id, "profile_status": plan.study.status, "notice": NOTICE,
        "provenance": dict(provenance), "backend_policy": plan.backend_policy.value, "plan": _plan_summary(plan, spec, cells),
        "cells": [
            {**{k: v for k, v in asdict(c).items() if k != "protocol"}, "protocol": c.protocol.value,
             "seconds": next((e.seconds for e in result.cells if e.cell == c), None) if result else None}
            for c in cells
        ],
        "calibration": [point(p) for p in calibration.fixed],
        "backend_split": [asdict(row) for row in calibration.backend_split()],
        "memetic": [asdict(m) for m in calibration.memetic],
        "probes": [asdict(p) for p in calibration.probes],
        "native_limits": {
            "label": PROVISIONAL_LABEL, "global_iterations": calibration.native_limits.global_iterations,
            "polish_iterations": calibration.native_limits.polish_iterations,
        },
        "native_calibration": [{**asdict(p), "limits_label": PROVISIONAL_LABEL} for p in calibration.native_points()],
        "native_estimate": {
            "label": PROVISIONAL_LABEL, "runs": result.native_runs if result else None,
            "seconds": result.native_seconds if result else None,
        },
        "estimate": None if result is None else {
            "fixed_runs": result.fixed_runs, "fixed_evaluation_upper_bound": result.fixed_evaluation_upper_bound,
            "fixed_seconds": result.fixed_seconds,
        },
    }


# ---------------------------------------------------------------------------------------------------- output
def _check_output_dir(output_dir: str | Path, repository_root: Path, *, overwrite: bool) -> Path:
    output = Path(output_dir).expanduser().resolve()
    root = Path(repository_root).resolve()
    main_tree = _main_working_tree(root)
    if _is_within(output, root) or (main_tree is not None and _is_within(output, main_tree)):
        raise EstimateError(f"output directory is inside the repository: {output}")
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise EstimateError(f"output directory is not empty: {output} (use --overwrite)")
    return output


def write_outputs(output_dir: str | Path, text: str, payload: Mapping[str, Any], *, repository_root: Path,
                  overwrite: bool = False) -> List[str]:
    """Write ``estimate.txt`` and ``estimate.json`` atomically into a folder outside the repository."""
    output = _check_output_dir(output_dir, repository_root, overwrite=overwrite)
    output.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in ((TEXT_FILE, text), (JSON_FILE, json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")):
        target = output / name
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, target)
        written.append(str(target))
    return written


# ---------------------------------------------------------------------------------------------- the real solver
def make_real_solver(plan: StudyPlan, repository_root: Path) -> Solver:
    """A solver that runs one plan row through the decision-bound gateway on the committed dataset artifact."""
    loader = build_artifact_loader(plan, repository_root)
    registered = _registered_algorithm_ids()
    runtime = probe_runtime_backends()
    problems: Dict[str, Any] = {}

    def solve(row: PlanRow, params: Mapping[str, Any]) -> SolverOutcome:
        problem = problems.get(row.problem_name)
        if problem is None:
            problem = problems[row.problem_name] = loader(row.problem_name)
        fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
        config: Any = _fixed_config(plan, row.problem_name, row.budget_level) if fixed else _native_config(plan, row.problem_name)
        run_params = dict(params)
        run_params["fair_comparison" if fixed else "native_comparison"] = config.fair_comparison if fixed else config.native_comparison
        result, _decision, _elapsed_ms = _execute_preflighted_run(
            requested_algorithm_id=row.algorithm_id, identifier_source=IdentifierSource.MANIFEST, problem=problem, params=run_params,
            seed=row.seed, run_idx=row.replicate, protocol=row.protocol, backend_policy=plan.backend_policy,
            evaluation_budget=row.budget_level, registered_algorithm_ids=registered, runtime_backends=runtime,
            registry_getter=_registry_executor,
        )
        composition = getattr(result, "composition", None) or {}
        stages = tuple(dict(stage) for stage in composition.get("stages", []) if isinstance(stage, Mapping))
        polish = getattr(result, "polish_policy", None) or {}
        counted = polish.get("evaluations") if isinstance(polish, Mapping) else None
        polish_total = sum(int(v) for v in counted.values()) if isinstance(counted, Mapping) else 0
        for stage in stages:
            if stage.get("name") == "polish" and isinstance(stage.get("consumed_evaluations"), int):
                polish_total = stage["consumed_evaluations"]
        return SolverOutcome(
            objective_evaluations=int(getattr(result, "objective_evaluations", 0) or 0),
            iterations=getattr(result, "iterations", None), polish_evaluations=polish_total,
            termination_reason=getattr(result, "termination_reason", None), stages=stages,
        )

    return solve


# ---------------------------------------------------------------------------------------------------- CLI
def _ints(text: Optional[str]) -> Optional[Tuple[int, ...]]:
    return None if text is None else tuple(int(item) for item in text.split(",") if item.strip())


def _names(text: Optional[str]) -> Optional[Tuple[str, ...]]:
    return None if text is None else tuple(item.strip() for item in text.split(",") if item.strip())


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Cost estimator and calibration slice for a study profile (Gate D, D-04b1)")
    parser.add_argument("--study", required=True, help="repository-relative path of the study.json")
    parser.add_argument("--out", required=True, help="output directory (outside the repository)")
    parser.add_argument("--overwrite", action="store_true", help="reuse a non-empty output directory")
    parser.add_argument("--run-count", type=int, default=None, help="runs per cell of the candidate plan (default: the profile's)")
    parser.add_argument("--levels", default=None, help="comma-separated level indices (default: all)")
    parser.add_argument("--raw-levels", default=None, help="comma-separated raw budgets; refused where they mix instances")
    parser.add_argument("--datasets", default=None, help="comma-separated dataset ids (default: all)")
    parser.add_argument("--algorithms", default=None, help="comma-separated algorithm ids (default: all)")
    parser.add_argument("--no-native", action="store_true", help="leave the native protocol out of the plan and the slice")
    parser.add_argument("--no-warmup", action="store_true", help="do not run the discarded warm-up replicate")
    parser.add_argument("--native-global-iterations", type=int, default=2, help=f"native global max_iterations ({PROVISIONAL_LABEL})")
    parser.add_argument("--native-polish-iterations", type=int, default=2, help=f"native polish max_iterations ({PROVISIONAL_LABEL})")
    parser.add_argument("--probe-250x", action="store_true",
                        help="after the slice, run one replicate of each memetic GWO/HHO ID at the top level of the largest instance")
    parser.add_argument("--only-probe-250x", action="store_true", help="run only the 250x probe (no slice, no estimate)")
    parser.add_argument("--repository-root", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = (Path(args.repository_root) if args.repository_root else Path(__file__).resolve().parents[2]).resolve()
    try:
        _check_output_dir(args.out, root, overwrite=args.overwrite)  # before anything runs
        spec = RunPlanSpec(
            run_count=args.run_count, level_indices=_ints(args.levels), raw_levels=_ints(args.raw_levels),
            dataset_ids=_names(args.datasets), algorithm_ids=_names(args.algorithms), include_native=not args.no_native,
        )
        plan = build_study_plan(args.study, repository_root=root)
        cells = build_cells(plan, spec)
        limits = NativeLimits(args.native_global_iterations, args.native_polish_iterations)
        for name, value in (("native global iterations", limits.global_iterations), ("native polish iterations", limits.polish_iterations)):
            if value < 1:
                raise EstimateError(f"{name} must be at least 1")

        def progress(message: str) -> None:
            print(message, file=sys.stderr, flush=True)

        calibration = calibrate(
            plan, make_real_solver(plan, root), time.perf_counter, spec=spec, native_limits=limits, warmup=not args.no_warmup,
            probe_250x=args.probe_250x or args.only_probe_250x, run_slice=not args.only_probe_250x, progress=progress,
        )
        result = None if args.only_probe_250x else estimate(cells, calibration)
        provenance = collect_provenance(root)
        text = render_report(plan, spec, cells, calibration, result, provenance)
        written = write_outputs(args.out, text, report_payload(plan, spec, cells, calibration, result, provenance),
                                repository_root=root, overwrite=args.overwrite)
    except (EstimateError, StudyServiceError, StudyRunError, StudySmokeError, FairPilotError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(text)
    print("written: " + ", ".join(written))
    return 0


__all__ = [
    "Calibration", "Cell", "EstimateError", "NativeLimits", "PROVISIONAL_LABEL", "RunPlanSpec", "SolverOutcome",
    "build_cells", "calibrate", "estimate", "main", "make_real_solver", "render_report", "report_payload", "write_outputs",
]

if __name__ == "__main__":
    sys.exit(main())
