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

import re
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

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
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.native_pilot import NativePilotConfig, _native_result_record
from academic_benchmark.native_protocol import NATIVE_PROTOCOL, NATIVE_TERMINATION_REGIME
from academic_benchmark.protocol_registry import assert_single_pooling_group
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


class _RowFailure(Exception):
    def __init__(self, stage: str, cause: BaseException, consumed: Optional[int]):
        super().__init__(str(cause))
        self.stage, self.cause, self.consumed = stage, cause, consumed


@dataclass(frozen=True)
class SmokeReport:
    status: str  # "passed" or "failed"
    output_dir: str
    study_id: str
    budget_level: int
    replicates: int
    rows_written: Dict[str, int]
    planned_rows: int
    failed_rows: tuple
    text: str
    files: tuple = field(default_factory=tuple)


def assert_no_ranking_words(text: str) -> None:
    """Refuse a text that uses ranking or superiority wording."""
    found = sorted({m.group(0).lower() for m in _RANKING_PATTERN.finditer(text)})
    if found:
        raise StudySmokeError(f"smoke report wording implies a ranking: {found}")


def select_smoke_rows(
    plan: StudyPlan, *, replicates: int = SMOKE_MAX_REPLICATES, budget_level: Optional[int] = None
) -> tuple:
    """Smoke slice: at most ``SMOKE_MAX_REPLICATES`` replicates, one fixed-budget level (lowest by default)."""
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 1:
        raise StudySmokeError("replicates must be an integer >= 1")
    cap = min(replicates, SMOKE_MAX_REPLICATES, plan.study.run_count)
    levels = list(plan.study.fixed_budget_levels)
    level = min(levels) if budget_level is None else budget_level
    if level not in levels:
        raise StudySmokeError(f"budget level {level!r} is not a level of the study {sorted(levels)}")
    return tuple(
        row for row in plan.rows
        if row.replicate < cap
        and (row.protocol is not ExecutionProtocol.FIXED_BUDGET or row.budget_level == level)
    )


def write_rows_file(path: Path, rows: Sequence[Mapping[str, Any]], *, expected_group: str) -> None:
    """Write one rows file; refuse rows of two pooling groups, of the wrong group or of two budget levels."""
    group = assert_single_pooling_group(rows)  # ValueError when groups meet
    if group != expected_group:
        raise StudySmokeError(f"{path.name}: rows belong to pooling group {group!r}, expected {expected_group!r}")
    levels = {row.get("evaluation_budget") for row in rows}
    if expected_group == FIXED_GROUP and (len(levels) != 1 or None in levels):
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


def _run_row(
    row: PlanRow, problem: Any, dataset: ResolvedDataset, plan: StudyPlan, independent, *,
    registered: frozenset, runtime_backends: RuntimeBackendAvailability,
    registry_getter: Callable[[str], Any], gateway_executor: Callable[..., Any],
) -> Dict[str, Any]:
    study = plan.study
    fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
    params: Dict[str, Any] = dict(study.algorithm_parameters[row.algorithm_id])
    if fixed:
        config: Any = _fixed_config(plan, row.problem_name, row.budget_level)
        params["fair_comparison"] = config.fair_comparison
    else:
        config = _native_config(plan, row.problem_name)
        params.update(study.secondary_protocol.termination)
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
    except StudySmokeError:
        raise
    except Exception as exc:  # recorded, never converted to a numeric observation
        raise _RowFailure(stage, exc, consumed) from exc
    record.update(
        {"study_id": study.study_id, "dataset_id": row.dataset_id, "smoke": True,
         "hamiltonian_validation": "passed"}
    )
    return record


def _failed_record(row: PlanRow, failure: _RowFailure, plan: StudyPlan) -> Dict[str, Any]:
    fixed = row.protocol is ExecutionProtocol.FIXED_BUDGET
    return {
        "record_kind": "failed_run",
        "validation_status": "failed",
        "study_id": plan.study.study_id,
        "dataset_id": row.dataset_id,
        "smoke": True,
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


def _report_text(
    plan: StudyPlan, status: str, level: int, replicates: int, written: Mapping[str, int],
    failed: Sequence[Mapping[str, Any]], git: Mapping[str, Any],
) -> str:
    lines = [
        "UniRide study smoke run (smoke mode, no claim)",
        f"Study: {plan.study.study_id} (status {plan.study.status})",
        f"Slice: up to {replicates} replicate(s) per cell (cap {SMOKE_MAX_REPLICATES}); "
        f"fixed-budget level {level}",
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
    for name, count in written.items():
        lines.append(f"File {name}: {count} row(s)")
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
) -> SmokeReport:
    """Run the smoke slice of ``plan``. ``problem_loader(problem_name)`` returns the problem object."""
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    rows = select_smoke_rows(plan, replicates=replicates, budget_level=budget_level)
    if not rows:
        raise StudySmokeError("the smoke slice selects no plan row")
    level = min(plan.study.fixed_budget_levels) if budget_level is None else budget_level
    cap = min(replicates, SMOKE_MAX_REPLICATES, plan.study.run_count)
    datasets = {d.dataset_id: d for d in plan.datasets}
    problems: Dict[str, Any] = {}
    independent: Dict[str, Any] = {}
    for row in rows:  # identity first: nothing runs or is written on a mismatch
        if row.problem_name not in problems:
            problems[row.problem_name] = problem_loader(row.problem_name)
        _check_identity(problems[row.problem_name], row)
    output = _prepare_output_dir(
        output_dir, SimpleNamespace(allow_repository_output=False, overwrite=overwrite), root
    )
    runtime_backends = runtime_probe()
    registered = frozenset(registered_algorithms_provider())
    fixed_rows: List[Dict[str, Any]] = []
    native_rows: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
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
        (fixed_rows if row.protocol is ExecutionProtocol.FIXED_BUDGET else native_rows).append(record)
    written: Dict[str, int] = {}
    if fixed_rows:
        write_rows_file(output / FIXED_FILE, fixed_rows, expected_group=FIXED_GROUP)
        written[FIXED_FILE] = len(fixed_rows)
    if native_rows:
        write_rows_file(output / NATIVE_FILE, native_rows, expected_group=NATIVE_GROUP)
        written[NATIVE_FILE] = len(native_rows)
    if failed:
        _jsonl_atomic(output / FAILED_FILE, failed)
        written[FAILED_FILE] = len(failed)
    status = "failed" if failed else "passed"
    git = _git_metadata(root)
    text = _report_text(plan, status, level, cap, written, failed, git)
    assert_no_ranking_words(text)
    (output / REPORT_TEXT_FILE).write_text(text, encoding="utf-8")
    _json_atomic(output / REPORT_JSON_FILE, {
        "status": status, "study_id": plan.study.study_id, "mode": "smoke", "claims": "none",
        "budget_level": level, "replicates": cap, "planned_rows": len(rows), "rows_written": written,
        "git": git, "environment": _environment_metadata(), "statement": text,
    })
    return SmokeReport(
        status=status, output_dir=str(output), study_id=plan.study.study_id, budget_level=level,
        replicates=cap, rows_written=written, planned_rows=len(rows), failed_rows=tuple(failed),
        text=text, files=tuple(sorted(p.name for p in output.iterdir())),
    )


__all__ = [
    "SmokeReport", "StudySmokeError", "assert_no_ranking_words", "run_study_smoke",
    "select_smoke_rows", "write_rows_file",
]
