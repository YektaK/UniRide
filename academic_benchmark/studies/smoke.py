"""Study smoke runner (Gate C, C-12): run a small slice of an expanded study plan and validate it.

A smoke run answers one question: do the runs complete, and are the output files well formed and
valid. It produces no claim about any algorithm (AGENTS.md: smoke or pilot runs cannot produce
superiority, causality or proof claims), so the report names no ranking and aggregates nothing.

Flow, per selected plan row, through the decision-bound gateway (``execute_preflighted``):

1. identity     ``normalize_problem(problem.name)`` must equal the normalised plan ``problem_name``
                (DECISION_LOG A17, C-11 note). The check also runs for every row before the first
                run, so a mismatch is refused before anything is executed or written;
2. execution    the gateway resolves, authorises, runs and validates the result;
3. record       the fair/native pilot record builders (reused, not copied) check the comparison
                manifest and the independent cost recomputation on the solver's own matrix;
4. hamiltonian  the standard-library validator recomputes the closed length from the committed
                dataset artifact and checks one cycle through every node.

Outputs go to a caller-provided directory that must lie outside the repository (the
``fair_pilot._prepare_output_dir`` rules). Valid fixed-budget rows go to ``fixed_runs.jsonl``,
valid native rows to ``native_runs.jsonl``; a file is refused when its rows span two pooling groups
or two budget levels. The first runtime failure stops the run (no further row is executed, nothing is
aggregated) and is recorded in ``failed_runs.jsonl`` as a structured failed-run row (design
"Error Handling": algorithm, problem, seed, stage, exception category, consumed budget); it is never
turned into a numeric observation.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from academic_benchmark.analysis.manifests import (
    DESCRIPTIVE_REPORT_FILES,
    PAPER_REPORT_FILES,
    INDEX_FILE,
    build_run_manifest,
    collect_environment,
    failed_run_entries,
    file_sha256,
    outside_location,
    write_run_campaign,
)
from academic_benchmark.composite_protocol import is_composite_algorithm, validate_composite_result
from academic_benchmark.contracts import OutputChecksumV1
from academic_benchmark.contracts.run import EnvironmentV1
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.core.preflight import RuntimeBackendAvailability, probe_runtime_backends
from academic_benchmark.core.problem_validation import validate_problem_for_preflight
from academic_benchmark.fair_pilot import (
    FairPilotConfig,
    _environment_metadata,
    _execute_preflighted_run,
    _git_metadata,
    _json_atomic,
    _jsonl_atomic,
    _prepare_output_dir,
    _registered_algorithm_ids,
    _registry_executor,
    _result_record,
)
from academic_benchmark.fairness import normalize_problem, require_fixed_budget_stopping_keys
from academic_benchmark.native_pilot import NativePilotConfig, _native_result_record
from academic_benchmark.native_protocol import NATIVE_PROTOCOL, NATIVE_TERMINATION_REGIME
from academic_benchmark.protocol_registry import assert_single_pooling_group
from academic_benchmark.studies.service import fixed_budget_levels_for
from academic_benchmark.studies.service import PlanRow, ResolvedDataset, StudyPlan
from academic_benchmark.validation.hamiltonian_cycle import (
    coordinate_cost,
    matrix_cost,
    parse_coordinates,
    parse_full_matrix,
    parse_header,
    validate_hamiltonian_cycle,
)
from uniride_core.algorithms.capabilities import ExecutionProtocol

SMOKE_MAX_REPLICATES = 3
FIXED_FILE = "fixed_runs.jsonl"
NATIVE_FILE = "native_runs.jsonl"
FAILED_FILE = "failed_runs.jsonl"
REPORT_TEXT_FILE = "smoke_report.txt"
REPORT_JSON_FILE = "smoke_report.json"
FIXED_GROUP = "fixed_budget"
NATIVE_GROUP = "native"

# Wording that implies a ranking or a superiority claim (A15 list, plus the single words a smoke
# report could drift into). A smoke report is checked against it before it is written.
RANKING_PHRASES = (
    "best performing", "paper-ready", "best values in bold", "row algorithm better",
    "column algorithm better", "top solutions", "leaderboard",
)
RANKING_WORDS = (
    "best", "better", "winner", "winners", "win", "wins", "outperform", "outperforms",
    "outperformed", "superior", "superiority", "rank", "ranks", "ranked", "ranking", "fastest",
)
_RANKING_PATTERN = re.compile(
    r"(?<![\w-])(?:" + "|".join(re.escape(w) for w in (*RANKING_PHRASES, *RANKING_WORDS)) + r")(?![\w-])",
    re.IGNORECASE,
)


class StudySmokeError(ValueError):
    """A smoke run was refused (identity mismatch, mixed pooling groups or levels, bad wording)."""


# Fields that are wall-clock timing by design: they stay in the exported rows (the run time is
# a result of the run) but never enter an identity or comparison view (``comparable_row``).
ROW_TIMING_FIELDS = ("elapsed_ms",)
STAGE_TIMING_FIELDS = ("elapsed_sec",)


def comparable_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """A copy of an exported row without its timing fields (comparison and identity view).

    Drops ``elapsed_ms`` and the per-stage ``elapsed_sec`` of a composite row's ``composition``
    record, nothing else. Two smoke runs with the same seed give identical comparable rows."""
    view = copy.deepcopy(dict(row))
    for name in ROW_TIMING_FIELDS:
        view.pop(name, None)
    composition = view.get("composition")
    if isinstance(composition, dict):
        for stage in composition.get("stages") or ():
            if isinstance(stage, dict):
                for name in STAGE_TIMING_FIELDS:
                    stage.pop(name, None)
    return view


class _RowFailure(Exception):
    def __init__(self, stage: str, cause: BaseException, consumed: Optional[int]):
        super().__init__(str(cause))
        self.stage, self.cause, self.consumed = stage, cause, consumed


@dataclass(frozen=True)
class SmokeReport:
    status: str  # "passed" or "failed"
    output_dir: str
    study_id: str
    budget_level: Any  # int, or {dataset_id: level} when the levels differ per dataset (C-19)
    replicates: int
    rows_written: Dict[str, int]
    planned_rows: int
    failed_rows: tuple
    text: str
    files: tuple = field(default_factory=tuple)
    run_index: Optional[Dict[str, Any]] = None  # {path, sha256, manifests} of the index this run wrote; None when it wrote no manifests


def assert_no_ranking_words(text: str) -> None:
    """Refuse a text that uses ranking or superiority wording."""
    found = sorted({m.group(0).lower() for m in _RANKING_PATTERN.finditer(text)})
    if found:
        raise StudySmokeError(f"smoke report wording implies a ranking: {found}")


def select_smoke_rows(
    plan: StudyPlan, *, replicates: int = SMOKE_MAX_REPLICATES, budget_level: Optional[int] = None
) -> tuple:
    """Smoke slice: at most ``SMOKE_MAX_REPLICATES`` replicates and one fixed-budget level per dataset.

    By default each dataset's lowest level (the same level for all datasets when the study has one
    level list); an explicit ``budget_level`` keeps the fixed rows of exactly that level (with
    instance-scaled levels, only the datasets that have it)."""
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 1:
        raise StudySmokeError("replicates must be an integer >= 1")
    cap = min(replicates, SMOKE_MAX_REPLICATES, plan.study.run_count)
    by_dataset = {d.dataset_id: fixed_budget_levels_for(plan.study, d) for d in plan.datasets}
    every_level = sorted({level for levels in by_dataset.values() for level in levels})
    if budget_level is None:
        chosen = {dataset_id: min(levels) for dataset_id, levels in by_dataset.items()}
    else:
        if budget_level not in every_level:
            raise StudySmokeError(f"budget level {budget_level!r} is not a level of the study {every_level}")
        chosen = {d: budget_level for d, levels in by_dataset.items() if budget_level in levels}
    return tuple(
        row for row in plan.rows
        if row.replicate < cap
        and (
            row.protocol is not ExecutionProtocol.FIXED_BUDGET
            or chosen.get(row.dataset_id) == row.budget_level
        )
    )


def write_rows_file(
    path: Path, rows: Sequence[Mapping[str, Any]], *, expected_group: str, per_dataset_levels: bool = False,
    levels_by_dataset: Optional[Mapping[str, Sequence[int]]] = None,
) -> None:
    """Write one rows file; refuse rows of two pooling groups, of the wrong group or of two budget levels.

    ``per_dataset_levels`` (instance-scaled studies, C-19): the fixed rows of each ``dataset_id``
    must share exactly one level, different datasets may have different levels.

    ``levels_by_dataset`` (full campaigns, D-03; plan X8): the file may hold every level of the study, but each fixed
    row's ``evaluation_budget`` must be one of the level list of its own ``dataset_id``; a row of an unknown dataset
    or with a foreign level is refused, and nothing is written. Levels are compared per dataset, never across
    instances by raw budget."""
    group = assert_single_pooling_group(rows)  # ValueError when groups meet
    if group != expected_group:
        raise StudySmokeError(f"{path.name}: rows belong to pooling group {group!r}, expected {expected_group!r}")
    levels = {row.get("evaluation_budget") for row in rows}
    if expected_group == FIXED_GROUP and levels_by_dataset is not None:
        bad = sorted(
            {f"{row.get('dataset_id')}@{row.get('evaluation_budget')}" for row in rows
             if row.get("evaluation_budget") not in tuple(levels_by_dataset.get(row.get("dataset_id"), ()))}
        )
        if bad:
            raise StudySmokeError(
                f"{path.name}: fixed-budget rows must use a budget level of their own dataset's level list, found {bad}"
            )
    elif expected_group == FIXED_GROUP and per_dataset_levels:
        by_dataset: Dict[Any, set] = {}
        for row in rows:
            by_dataset.setdefault(row.get("dataset_id"), set()).add(row.get("evaluation_budget"))
        bad = {str(d): sorted(map(str, v)) for d, v in by_dataset.items() if len(v) != 1 or None in v}
        if bad or None in by_dataset:
            raise StudySmokeError(f"{path.name}: fixed-budget rows must share exactly one budget level per dataset, found {bad}")
    elif expected_group == FIXED_GROUP and (len(levels) != 1 or None in levels):
        raise StudySmokeError(f"{path.name}: fixed-budget rows must share exactly one budget level, found {sorted(map(str, levels))}")
    if expected_group == NATIVE_GROUP and levels != {None}:
        raise StudySmokeError(f"{path.name}: native rows carry no evaluation budget")
    _jsonl_atomic(path, rows)


def _check_identity(problem: Any, row: PlanRow) -> None:
    got = normalize_problem(getattr(problem, "name", ""))
    expected = normalize_problem(row.problem_name)
    if got != expected:
        raise StudySmokeError(
            f"problem name mismatch for dataset {row.dataset_id!r}: loaded problem "
            f"{getattr(problem, 'name', None)!r} normalises to {got!r}, the plan seed identity is {expected!r}"
        )


def _independent_cost(dataset: ResolvedDataset, repository_root: Path):
    """``(n, cost)`` from the committed artifact, read with the standard-library validator only."""
    text = (repository_root / dataset.manifest.artifact_path).read_text(encoding="utf-8")
    header = parse_header(text)
    n = int(header["DIMENSION"])
    edge_weight_type = header.get("EDGE_WEIGHT_TYPE", "EXPLICIT").upper()
    if edge_weight_type == "EXPLICIT":
        return n, matrix_cost(parse_full_matrix(text))
    return n, coordinate_cost(edge_weight_type, parse_coordinates(text))


def _hamiltonian_check(row: Mapping[str, Any], n: int, cost) -> None:
    claimed = float(row["objective_cost"])
    claimed_int = int(round(claimed)) if abs(claimed - round(claimed)) < 1e-9 else None
    errors = validate_hamiltonian_cycle(row["tour"], n=n, node_base=1, cost=cost, claimed_length=claimed_int)
    if claimed_int is None:
        errors.append(f"claimed cost {claimed} is not an integer on an integer-metric instance")
    if errors:
        raise ValueError("; ".join(errors))


def _fixed_config(plan: StudyPlan, problem_name: str, level: int) -> FairPilotConfig:
    study = plan.study
    return FairPilotConfig(
        protocol_version=study.primary_protocol.protocol_version, problems=(problem_name,),
        algorithms={}, runs=1, evaluation_budget=level, base_seed=study.base_seed,
        budget_policy=study.primary_protocol.budget_policy, comparison_regime="fixed_evaluation_budget",
        workers=1, replay_replicates=(), allow_repository_output=False, overwrite=False,
    )


def _native_config(plan: StudyPlan, problem_name: str) -> NativePilotConfig:
    return NativePilotConfig(
        protocol_version=NATIVE_PROTOCOL, comparison_regime=NATIVE_TERMINATION_REGIME,
        problems=(problem_name,), algorithms={}, runs=1, base_seed=plan.study.base_seed, workers=1,
        replay_replicates=(), allow_repository_output=False, overwrite=False,
    )


def _row_params(study: Any, row: PlanRow) -> Dict[str, Any]:
    """Parameters of one plan row: the study's block, plus the protocol's termination for native rows.

    Composite IDs (GWO/HHO + final 3-opt or ALNS) keep their ``global``/``polish`` namespaces. A
    fixed-budget composite row needs ``global_fraction`` written explicitly in the study (A17 C-08:
    the executor has no default, so smoke does not supply one either); a native row never passes
    it, and the native termination keys apply to both stages (an unbounded native polish would make a smoke run last hours)."""
    params: Dict[str, Any] = copy.deepcopy(dict(study.algorithm_parameters[row.algorithm_id]))
    fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
    composite = is_composite_algorithm(row.algorithm_id)
    if composite and fixed and "global_fraction" not in params:
        raise StudySmokeError(
            f"{row.algorithm_id}: a fixed-budget composite run needs global_fraction written "
            "explicitly in the study's algorithm_parameters (no default, A17 C-08)"
        )
    if fixed:
        try:
            require_fixed_budget_stopping_keys(row.algorithm_id, params)  # A17 2026-10-23
        except ValueError as exc:
            raise StudySmokeError(str(exc)) from exc
        return params
    termination = copy.deepcopy(dict(study.secondary_protocol.termination))
    if composite:
        params.pop("global_fraction", None)  # native runs refuse it
        for stage in ("global", "polish"):  # the native stopping rule bounds every stage
            params[stage] = {**params.get(stage, {}), **termination}
    else:
        params.update(termination)
    return params


def _composite_row_errors(record: Mapping[str, Any], row: PlanRow, protocol_version: str) -> list:
    """Errors of the exported composite row, validated as written (not the in-memory result)."""
    result = SimpleNamespace(**record, evaluations=record.get("objective_evaluations"))
    return validate_composite_result(
        result,
        fixed_budget=row.budget_level if row.protocol is ExecutionProtocol.FIXED_BUDGET else None,
        protocol_version=protocol_version,
    )


def _run_row(
    row: PlanRow, problem: Any, dataset: ResolvedDataset, plan: StudyPlan, independent, *,
    registered: frozenset, runtime_backends: RuntimeBackendAvailability,
    registry_getter: Callable[[str], Any], gateway_executor: Callable[..., Any], smoke: bool = True,
) -> Dict[str, Any]:
    study = plan.study
    fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
    params = _row_params(study, row)
    if fixed:
        config: Any = _fixed_config(plan, row.problem_name, row.budget_level)
        params["fair_comparison"] = config.fair_comparison
    else:
        config = _native_config(plan, row.problem_name)
        params["native_comparison"] = config.native_comparison
    if row.seed != config.manifest.paired_seed(problem.name, row.replicate):
        raise StudySmokeError("plan seed differs from the contract seed of the problem and replicate")
    _check_identity(problem, row)
    stage, result, consumed = "execution", None, None
    try:
        result, decision, elapsed_ms = _execute_preflighted_run(
            requested_algorithm_id=row.algorithm_id, identifier_source=IdentifierSource.MANIFEST,
            problem=problem, params=params, seed=row.seed, run_idx=row.replicate, protocol=row.protocol,
            backend_policy=plan.backend_policy, evaluation_budget=row.budget_level,
            registered_algorithm_ids=registered, runtime_backends=runtime_backends,
            registry_getter=registry_getter, gateway_executor=gateway_executor,
        )
        consumed = getattr(result, "objective_evaluations", None)
        stage = "record"
        report = validate_problem_for_preflight(problem)
        builder = _result_record if fixed else _native_result_record
        record = builder(
            result, problem=problem, matrix=[list(r) for r in report.matrix],
            matrix_sha256=report.matrix_sha256, algorithm_id=row.algorithm_id,
            replicate=row.replicate, seed=row.seed, config=config, decision=decision,
            elapsed_ms=elapsed_ms, record_kind="primary",
        )
        stage = "hamiltonian_validation"
        n, cost = independent
        _hamiltonian_check(record, n, cost)
        if is_composite_algorithm(row.algorithm_id):
            stage = "composite_validation"
            errors = _composite_row_errors(record, row, config.protocol_version)
            if errors:
                raise ValueError("; ".join(errors))
    except StudySmokeError:
        raise
    except Exception as exc:  # recorded, never converted to a numeric observation
        raise _RowFailure(stage, exc, consumed) from exc
    record.update(
        {"study_id": study.study_id, "dataset_id": row.dataset_id, "smoke": smoke,
         "hamiltonian_validation": "passed"}
    )
    return record


def _failed_record(row: PlanRow, failure: _RowFailure, plan: StudyPlan, smoke: bool = True) -> Dict[str, Any]:
    fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
    return {
        "record_kind": "failed_run",
        "validation_status": "failed",
        "study_id": plan.study.study_id,
        "dataset_id": row.dataset_id,
        "smoke": smoke,
        "protocol_version": plan.study.primary_protocol.protocol_version if fixed else NATIVE_PROTOCOL,
        "comparison_regime": "fixed_evaluation_budget" if fixed else NATIVE_TERMINATION_REGIME,
        "problem": row.problem_name,
        "algorithm_id": row.algorithm_id,
        "replicate": row.replicate,
        "seed": row.seed,
        "seed_group": row.seed_group,
        "evaluation_budget": row.budget_level,
        "stage": failure.stage,
        "exception_category": type(failure.cause).__name__,
        "error": str(failure.cause)[:500],
        "consumed_budget": failure.consumed,
    }


_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _write_run_manifests(
    plan: StudyPlan, output: Path, completed: Sequence[tuple], written: Mapping[str, int], status: str,
    git: Mapping[str, Any], environment: EnvironmentV1, mode: str = "smoke", *, planned_runs: int, runs_per_cell: int,
    failed: Sequence[Mapping[str, Any]], output_location: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    """Run manifests, campaign index and detached checksums (D-02); ``None`` when the git state is unknown.

    A manifest needs the commit (``GitStateV1``): when git cannot answer, nothing is written and the report says so.
    The index also records what the plan hashed (profile and analysis plan files), the planned runs, the output location and
    the failed runs (``uniride-run-index/v2``; both modes fill the same fields, a smoke plan may be draft)."""
    revision, dirty = git.get("revision"), git.get("dirty")
    if not isinstance(revision, str) or not _COMMIT_PATTERN.match(revision) or not isinstance(dirty, bool):
        return None
    study = plan.study
    datasets = {d.dataset_id: d for d in plan.datasets}
    result_files = {
        name: OutputChecksumV1(path=name, checksum={"algorithm": "sha256", "value": file_sha256(output / name)})
        for name in (FIXED_FILE, NATIVE_FILE) if name in written
    }
    runs = []
    for row, record in completed:
        fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
        dataset = datasets[row.dataset_id]
        manifest = build_run_manifest(
            record, study_id=study.study_id, dataset=dataset.manifest, base_seed=study.base_seed,
            levels=fixed_budget_levels_for(study, dataset), configuration=_row_params(study, row),
            git={"commit": revision, "dirty": dirty}, environment=environment,
            outputs=[result_files[FIXED_FILE if fixed else NATIVE_FILE]],
        )
        runs.append((record, manifest))
    index = write_run_campaign(
        output, mode=mode, study_id=study.study_id, seed_protocol_version=study.seed_protocol_version,
        base_seed=study.base_seed, git={"commit": revision, "dirty": dirty}, environment=environment, status=status,
        runs=runs, output_files=list(written),
        profile={"path": plan.study_path, "sha256": plan.study_sha256},
        analysis_plan={
            "analysis_plan_id": study.analysis_plan_id, "path": plan.analysis_plan_path, "sha256": plan.analysis_plan_sha256,
        },
        planned={"runs_per_cell": runs_per_cell, "runs": planned_runs}, output_location=output_location,
        failed_runs=failed_run_entries(failed),
    )
    return {"path": INDEX_FILE, "sha256": file_sha256(output / INDEX_FILE), "manifests": len(index.runs)}


def _report_text(
    plan: StudyPlan, status: str, level: Any, replicates: int, written: Mapping[str, int],
    failed: Sequence[Mapping[str, Any]], git: Mapping[str, Any], run_index: Optional[Mapping[str, Any]] = None,
    analysis_plan_label: Optional[str] = None,
) -> str:
    lines = [
        "UniRide study smoke run (smoke mode, no claim)",
        f"Study: {plan.study.study_id} (status {plan.study.status})",
        f"Slice: up to {replicates} replicate(s) per cell (cap {SMOKE_MAX_REPLICATES}); "
        + (f"fixed-budget level {level}" if not isinstance(level, Mapping) else
         "fixed-budget level per dataset: " + ", ".join(f"{d} {v}" for d, v in level.items())),
    ]
    if git.get("dirty") or git.get("dirty") is None:
        lines.append("WARNING: the working tree is dirty or its state is unknown; "
                     f"revision {git.get('revision')}")
    else:
        lines.append(f"Working tree clean at revision {git.get('revision')}")
    if status == "passed":
        lines.append("Result: PASSED. Every planned run completed and every row passed validation.")
    else:
        item = failed[0]
        lines.append(
            f"Result: FAILED at stage {item['stage']} ({item['exception_category']}) for "
            f"{item['algorithm_id']} on {item['problem']}, replicate {item['replicate']}. "
            "Aggregation stopped; the failed-run record is in " + FAILED_FILE + "."
        )
    if analysis_plan_label:
        lines.append(f"Analysis plan: {analysis_plan_label}")
    for name, count in written.items():
        lines.append(f"File {name}: {count} row(s)")
    if run_index is not None:
        lines.append(
            f"Run manifests: {run_index['manifests']} in manifests/ with detached checksums; index {run_index['path']} "
            f"sha256 {run_index['sha256']}"
        )
    else:
        lines.append(
            "Run manifests: not written because the git state is unknown (a run manifest records the commit); "
            "the result files are not covered by checksums"
        )
    lines.append(
        "This smoke run checks only that runs complete and that the output files are well formed. "
        "It makes no comparison between algorithms and supports no claim. Fixed-budget and native "
        "rows are written to separate files and are never pooled."
    )
    return "\n".join(lines) + "\n"


def run_study_smoke(
    plan: StudyPlan,
    output_dir: str | Path,
    *,
    problem_loader: Callable[[str], Any],
    repository_root: Optional[Path] = None,
    replicates: int = SMOKE_MAX_REPLICATES,
    budget_level: Optional[int] = None,
    overwrite: bool = False,
    registry_getter: Callable[[str], Any] = _registry_executor,
    runtime_probe: Callable[[], RuntimeBackendAvailability] = probe_runtime_backends,
    registered_algorithms_provider: Callable[[], Iterable[str]] = _registered_algorithm_ids,
    gateway_executor: Callable[..., Any] = execute_preflighted,
    git_provider: Callable[[Path], Mapping[str, Any]] = _git_metadata,
    environment_provider: Callable[[], EnvironmentV1] = collect_environment,
    analysis_plan_label: Optional[str] = None,
) -> SmokeReport:
    """Run the smoke slice of ``plan``. ``problem_loader(problem_name)`` returns the problem object."""
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    rows = select_smoke_rows(plan, replicates=replicates, budget_level=budget_level)
    if not rows:
        raise StudySmokeError("the smoke slice selects no plan row")
    chosen = {r.dataset_id: r.budget_level for r in rows if r.protocol is ExecutionProtocol.FIXED_BUDGET}
    if budget_level is not None or len(set(chosen.values())) <= 1:
        level: Any = budget_level if budget_level is not None else next(iter(chosen.values()), None)
    else:
        level = dict(sorted(chosen.items()))
    scaled = plan.study.scaled_fixed_budget_levels is not None
    cap = min(replicates, SMOKE_MAX_REPLICATES, plan.study.run_count)
    datasets = {d.dataset_id: d for d in plan.datasets}
    problems: Dict[str, Any] = {}
    independent: Dict[str, Any] = {}
    for row in rows:  # parameters and identity first: nothing runs or is written on a refusal
        _row_params(plan.study, row)
        if row.problem_name not in problems:
            problems[row.problem_name] = problem_loader(row.problem_name)
        _check_identity(problems[row.problem_name], row)
    output = _prepare_output_dir(
        output_dir, SimpleNamespace(allow_repository_output=False, overwrite=overwrite), root
    )
    for name in (*DESCRIPTIVE_REPORT_FILES, *PAPER_REPORT_FILES):  # an overwritten folder must not keep a descriptive or paper report of an earlier run
        (output / name).unlink(missing_ok=True)
    runtime_backends = runtime_probe()
    registered = frozenset(registered_algorithms_provider())
    fixed_rows: List[Dict[str, Any]] = []
    native_rows: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    completed: List[tuple] = []
    for row in rows:
        dataset = datasets[row.dataset_id]
        try:
            if row.dataset_id not in independent:
                independent[row.dataset_id] = _independent_cost(dataset, root)
            record = _run_row(
                row, problems[row.problem_name], dataset, plan, independent[row.dataset_id],
                registered=registered, runtime_backends=runtime_backends,
                registry_getter=registry_getter, gateway_executor=gateway_executor,
            )
        except _RowFailure as failure:
            failed.append(_failed_record(row, failure, plan))
            break  # aggregation stops at the first failure
        completed.append((row, record))
        (fixed_rows if row.protocol is ExecutionProtocol.FIXED_BUDGET else native_rows).append(record)
    written: Dict[str, int] = {}
    if fixed_rows:
        write_rows_file(output / FIXED_FILE, fixed_rows, expected_group=FIXED_GROUP, per_dataset_levels=scaled)
        written[FIXED_FILE] = len(fixed_rows)
    if native_rows:
        write_rows_file(output / NATIVE_FILE, native_rows, expected_group=NATIVE_GROUP)
        written[NATIVE_FILE] = len(native_rows)
    if failed:
        _jsonl_atomic(output / FAILED_FILE, failed)
        written[FAILED_FILE] = len(failed)
    status = "failed" if failed else "passed"
    git = dict(git_provider(root))
    run_index = _write_run_manifests(
        plan, output, completed, written, status, git, environment_provider(), planned_runs=len(rows), runs_per_cell=cap,
        failed=failed, output_location=outside_location(output, [root]),
    )
    text = _report_text(plan, status, level, cap, written, failed, git, run_index, analysis_plan_label)
    assert_no_ranking_words(text)
    (output / REPORT_TEXT_FILE).write_text(text, encoding="utf-8")
    _json_atomic(output / REPORT_JSON_FILE, {
        "status": status, "study_id": plan.study.study_id, "mode": "smoke", "claims": "none",
        "budget_level": level, "replicates": cap, "planned_rows": len(rows), "rows_written": written,
        "git": git, "environment": _environment_metadata(), "run_index": run_index,
        "analysis_plan": analysis_plan_label, "statement": text,
    })
    return SmokeReport(
        status=status, output_dir=str(output), study_id=plan.study.study_id, budget_level=level,
        replicates=cap, rows_written=written, planned_rows=len(rows), failed_rows=tuple(failed),
        text=text, files=tuple(sorted(p.name for p in output.iterdir())), run_index=run_index,
    )


__all__ = [
    "ROW_TIMING_FIELDS", "STAGE_TIMING_FIELDS", "SmokeReport", "StudySmokeError",
    "assert_no_ranking_words", "comparable_row", "run_study_smoke",
    "select_smoke_rows", "write_rows_file",
]
