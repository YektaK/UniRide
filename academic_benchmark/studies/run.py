"""Study run service with smoke and paper modes (Gate D, D-03; plan 2026-10-23 section 3, DECISION_LOG A18).

``python -m academic_benchmark.studies.run --study <repository-relative study.json> --mode smoke|paper --out <dir>``

One entry point over the C-11 plan and the C-12 row runner (``studies.smoke``, reused, not copied):

* **smoke mode** keeps today's behaviour (a small slice, the first failure stops the run, draft profiles allowed) and adds
  the analysis-plan label to its report. Its output is descriptive only and supports no claim. After the campaign is written
  and verified, a descriptive report (D-07, ``analysis.report``: one table per comparison cell with the analysis plan's columns,
  the gap against the exact reference, a banner with the index checksum) is written next to it as ``descriptive_report.txt/json``.
* **paper mode** runs the whole plan and is built and tested here; Gate D does not use it for paper-scale runs. It refuses,
  before any execution or write: a study profile that is not ``active`` (A17 C-13 note, X9), an analysis plan that does not
  resolve or is not ``active`` (``load_study(mode="paper")``, D-09), a dirty working tree or an unknown git state (design
  "Reproducibility Manifest": a paper run needs a clean tree), an output directory inside the repository, a non-empty output
  directory (unless resuming) and an environment without the pinned statistics libraries (D-04a).

Failure policy (OQ-9 a): a failed run is recorded as a structured failed-run row, the campaign continues, the cell
(dataset, algorithm, budget level) is excluded from inference and listed in the report. A failed run is never retried, also
not on resume (the retry in OQ-9 c was not chosen). One campaign is one clean commit (OQ-10 a).

Atomic writes and resume (design ``:362``): while a paper campaign runs, each finished row is written atomically to
``checkpoint/rows/<plan index>.json`` (with its own digest) and the campaign fingerprint to ``checkpoint/campaign.json``.
The result files, run manifests and campaign index are derived from the checkpoint at the end, index last among the
checksummed files. The report is written after the index because it quotes the index checksum; the index therefore cannot
list it (``contracts/run_index.py``: the index never lists the report that quotes its checksum), so the report is not covered
by a checksum. The checkpoint folder is removed only after the report, ``checkpoint/campaign.json`` first, so a crash between
index and report leaves a folder that does not verify (``verify_manifests`` flags the checkpoint folder) and that ``--resume``
re-derives from the progress files, while a removal that stops half way can never be resumed. An interrupted campaign therefore has no ``run_index.json`` and does not verify as
complete (``verify_manifests`` also flags the checkpoint folder). ``--resume`` verifies every progress file, refuses a
changed profile, analysis plan, dataset artifact, plan row, commit, dirty state, environment, backend policy or seed
protocol, runs only the rows that are not done, and produces the same rows as an uninterrupted run (timing aside).

The service reads the committed dataset artifacts only; it never opens ``tsplib.db``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from academic_benchmark.analysis.environment import (
    AnalysisEnvironmentError,
    require_analysis_environment,
    statistics_library_identifier,
)
from academic_benchmark.analysis.gaps import ExactReferenceTable, add_gap_columns, load_reference_table
from academic_benchmark.analysis.manifests import (
    INDEX_FILE,
    MANIFEST_DIR,
    SIDECAR_SUFFIX,
    ManifestError,
    collect_environment,
    load_verified_campaign,
)
from academic_benchmark.analysis.report import REPORT_TEXT_FILE, ReportError, build_report, write_report
from academic_benchmark.committed_bytes import GitQueryFailed, run_git
from academic_benchmark.contracts.run import EnvironmentV1
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.core.preflight import RuntimeBackendAvailability, probe_runtime_backends
from academic_benchmark.protocol_registry import classify_row
from academic_benchmark.fair_pilot import (
    FairPilotError,
    _git_metadata,
    _is_within,
    _json_atomic,
    _jsonl_atomic,
    _registered_algorithm_ids,
    _registry_executor,
)
from academic_benchmark.studies.service import (
    ANALYSIS_PLAN_FILENAME,
    DEFAULT_BACKEND_POLICY,
    PlanRow,
    ResolvedDataset,
    StudyPlan,
    StudyServiceError,
    build_study_plan,
    fixed_budget_levels_for,
    load_study,
    load_study_with_plan,
)
from academic_benchmark.studies.smoke import (
    FAILED_FILE,
    FIXED_FILE,
    FIXED_GROUP,
    NATIVE_FILE,
    NATIVE_GROUP,
    SMOKE_MAX_REPLICATES,
    StudySmokeError,
    _COMMIT_PATTERN,
    _RowFailure,
    _check_identity,
    _failed_record,
    _independent_cost,
    _row_params,
    _run_row,
    _write_run_manifests,
    assert_no_ranking_words,
    run_study_smoke,
    write_rows_file,
)
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol
from uniride_core.algorithms.tsplib_parser import parse_atsp_text, parse_tsplib_text
from uniride_core.models import ProblemInstance

MODES = ("smoke", "paper")
RUN_REPORT_TEXT_FILE = "run_report.txt"
RUN_REPORT_JSON_FILE = "run_report.json"
CHECKPOINT_DIR = "checkpoint"
CHECKPOINT_ROWS_DIR = "rows"
CHECKPOINT_CAMPAIGN_FILE = "campaign.json"
CAMPAIGN_FINGERPRINT_VERSION = "uniride-paper-campaign/v1"
EXCLUSION_REASON = "failed run recorded (OQ-9 a): the cell is excluded from inference"


class StudyRunError(ValueError):
    """A run was refused (profile, analysis plan, git state, output location, resume) or its checkpoint does not hold."""


@dataclass(frozen=True)
class RunReport:
    status: str  # "passed" or "failed"
    mode: str
    output_dir: str
    study_id: str
    rows_planned: int
    rows_completed: int
    rows_failed: int
    excluded_cells: tuple = field(default_factory=tuple)
    run_index: Optional[Dict[str, Any]] = None
    text: str = ""
    files: tuple = field(default_factory=tuple)


# ------------------------------------------------------------------------------------------------- problem loader
def build_artifact_loader(plan: StudyPlan, repository_root: Path) -> Callable[[str], Any]:
    """``problem_loader(problem_name)`` that builds each problem from the dataset's committed artifact.

    The distance matrix comes from the repository's TSPLIB code (``ProblemInstance.prepare_matrices``) or the explicit ATSP
    matrix; ``optimal`` is the dataset manifest's ``best_known.value`` (the pilots' records need it). The smoke runner
    still recomputes every tour length from the artifact with the standard-library validator, so the solver's matrix is
    checked against an independent reading. ``tsplib.db`` is never opened."""
    root = Path(repository_root).resolve()
    by_name = {dataset.problem_name: dataset for dataset in plan.datasets}

    def load(problem_name: str) -> Any:
        dataset = by_name.get(problem_name)
        if dataset is None:
            raise StudyRunError(f"no dataset of the study has the problem name {problem_name!r}")
        manifest = dataset.manifest
        if manifest.best_known.value is None:
            raise StudyRunError(
                f"dataset {manifest.dataset_id!r}: best_known has no value; the run records need problem.optimal"
            )
        text = (root / manifest.artifact_path).read_text(encoding="utf-8")
        hint = f"{problem_name}.{'atsp' if manifest.problem_type == 'ATSP' else 'tsp'}"
        if manifest.problem_type == "ATSP":
            parsed = parse_atsp_text(text, hint)
            if not parsed:
                raise StudyRunError(f"dataset {manifest.dataset_id!r}: the ATSP artifact cannot be parsed")
            matrix = [[float(value) for value in row] for row in parsed["explicit_matrix"]]
            problem = ProblemInstance(
                name=parsed["name"], dimension=parsed["dimension"], coordinates=[], optimal=float(manifest.best_known.value),
                problem_type="atsp", edge_weight_type="EXPLICIT", dist_matrix=matrix,
            )
        else:
            parsed = parse_tsplib_text(text, hint)
            if not parsed:
                raise StudyRunError(f"dataset {manifest.dataset_id!r}: the TSPLIB artifact cannot be parsed")
            problem = ProblemInstance(
                name=parsed["name"], dimension=parsed["dimension"], coordinates=list(parsed["coordinates"]),
                optimal=float(manifest.best_known.value), problem_type="tsp", edge_weight_type=parsed["edge_weight_type"],
            )
            problem.prepare_matrices()
        if problem.dimension != manifest.dimension or len(problem.dist_matrix) != manifest.dimension:
            raise StudyRunError(
                f"dataset {manifest.dataset_id!r}: the loaded problem has dimension {problem.dimension}, "
                f"the manifest says {manifest.dimension}"
            )
        return problem

    return load


# -------------------------------------------------------------------------------------------- campaign fingerprint
def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True)


def _plan_row_key(row: PlanRow) -> list:
    return [row.dataset_id, row.algorithm_id, row.protocol.value, row.budget_level, row.replicate, row.seed]


def _fingerprint(
    plan: StudyPlan, study_path: str, root: Path, git: Mapping[str, Any], environment: EnvironmentV1
) -> Dict[str, Any]:
    study_file = (root / study_path).resolve()
    plan_file = study_file.parent / ANALYSIS_PLAN_FILENAME
    rows = [
        {"row": _plan_row_key(row), "seed_group": row.seed_group, "problem_name": row.problem_name,
         "parameters": _row_params(plan.study, row)}
        for row in plan.rows
    ]
    return {
        "version": CAMPAIGN_FINGERPRINT_VERSION,
        "study_id": plan.study.study_id,
        "study_path": study_path,
        "study_sha256": _sha256_bytes(study_file.read_bytes()),
        "analysis_plan_sha256": _sha256_bytes(plan_file.read_bytes()),
        "dataset_artifacts": {d.dataset_id: d.artifact_sha256 for d in plan.datasets},
        "plan_digest": _sha256_bytes(_canonical(rows).encode("utf-8")),
        "plan_rows": len(plan.rows),
        "backend_policy": plan.backend_policy.value,
        "seed_protocol_version": plan.study.seed_protocol_version,
        "base_seed": plan.study.base_seed,
        "commit": git["revision"],
        "dirty": git["dirty"],
        "environment": environment.model_dump(mode="json"),
    }


_CATEGORIES = {
    "commit": ("commit", "dirty"),
    "environment": ("environment",),
    "profile": (
        "version", "study_id", "study_path", "study_sha256", "analysis_plan_sha256", "dataset_artifacts", "plan_digest",
        "plan_rows", "backend_policy", "seed_protocol_version", "base_seed",
    ),
}


def _fingerprint_differences(stored: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    changed = {key for key in set(stored) | set(current) if stored.get(key) != current.get(key)}
    messages = []
    for category, keys in _CATEGORIES.items():
        hit = sorted(changed & set(keys))
        if hit:
            messages.append(f"the {category} changed since the campaign started ({', '.join(hit)})")
    unknown = sorted(changed - {key for keys in _CATEGORIES.values() for key in keys})
    if unknown:
        messages.append(f"the campaign fingerprint differs in {', '.join(unknown)}")
    return messages


# ------------------------------------------------------------------------------------------------ progress files
def _wrapped(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {"digest": _sha256_bytes(_canonical(payload).encode("utf-8")), "payload": payload}


def _read_wrapped(path: Path) -> Dict[str, Any]:
    try:
        wrapped = json.loads(path.read_text(encoding="utf-8"))
        payload, digest = wrapped["payload"], wrapped["digest"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise StudyRunError(f"progress file {path.name} is not valid ({type(exc).__name__}); the campaign cannot resume") from exc
    if not isinstance(payload, dict) or _sha256_bytes(_canonical(payload).encode("utf-8")) != digest:
        raise StudyRunError(f"progress file {path.name}: checksum mismatch; the campaign cannot resume")
    return payload


def _progress_path(checkpoint: Path, index: int) -> Path:
    return checkpoint / CHECKPOINT_ROWS_DIR / f"{index:08d}.json"


def _read_progress(checkpoint: Path, rows: Sequence[PlanRow]) -> Dict[int, tuple]:
    """Every finished row of an interrupted campaign: ``{plan index: (outcome, record)}``, each file verified."""
    done: Dict[int, tuple] = {}
    folder = checkpoint / CHECKPOINT_ROWS_DIR
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.name.endswith(".tmp"):  # a write that did not finish: its row is simply not done
                path.unlink()
                continue
            if not (path.name.endswith(".json") and path.name[: -len(".json")].isdigit()):
                raise StudyRunError(f"unexpected file {path.name} in the progress folder; the campaign cannot resume")
            payload = _read_wrapped(path)
            index = payload.get("index")
            if index != int(path.name[: -len(".json")]) or not isinstance(index, int) or not 0 <= index < len(rows):
                raise StudyRunError(f"progress file {path.name}: its plan index does not match the plan")
            if payload.get("plan_row") != _plan_row_key(rows[index]):
                raise StudyRunError(f"progress file {path.name}: its plan row differs from the plan")
            if payload.get("outcome") not in ("completed", "failed") or not isinstance(payload.get("record"), dict):
                raise StudyRunError(f"progress file {path.name}: not a finished-row record")
            done[index] = (payload["outcome"], payload["record"])
    return done


# ------------------------------------------------------------------------------------------------------ git/outputs
def _main_working_tree(root: Path) -> Optional[Path]:
    """The main working tree of the repository ``root`` belongs to: the parent of ``git rev-parse --git-common-dir``.

    A linked worktree of this project lives inside the main checkout (``.claude/worktrees/<name>``), so an output folder
    in the main checkout is inside the repository even though it is outside the worktree. ``None`` when git cannot say."""
    try:
        common = run_git(["rev-parse", "--git-common-dir"], root).decode("utf-8", "replace").strip()
    except GitQueryFailed:
        return None
    if not common:
        return None
    path = Path(common)
    return ((root / path) if not path.is_absolute() else path).resolve().parent


def _require_clean_git(root: Path, git_provider: Callable[[Path], Mapping[str, Any]]) -> Dict[str, Any]:
    git = dict(git_provider(root))
    revision, dirty = git.get("revision"), git.get("dirty")
    if not isinstance(revision, str) or not _COMMIT_PATTERN.match(revision) or not isinstance(dirty, bool):
        raise StudyRunError(
            f"paper mode refuses an unknown git state (revision {revision!r}, dirty {dirty!r}, "
            f"error {git.get('git_error')!r}): a paper run records its commit and needs a clean tree"
        )
    if dirty:
        raise StudyRunError(
            f"paper mode refuses a dirty working tree at revision {revision}: commit or remove the changes first "
            "(one campaign is one clean commit, A18 OQ-10)"
        )
    return {"revision": revision, "dirty": False}


# ------------------------------------------------------------------------------------------------ paper-mode report
def _excluded_cells(failed: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    cells: Dict[tuple, Dict[str, Any]] = {}
    for record in failed:
        fixed = record.get("comparison_regime") == "fixed_evaluation_budget"
        key = (record.get("dataset_id"), record.get("algorithm_id"), fixed, record.get("evaluation_budget"))
        cell = cells.setdefault(key, {
            "dataset_id": record.get("dataset_id"), "algorithm_id": record.get("algorithm_id"),
            "protocol": FIXED_GROUP if fixed else NATIVE_GROUP, "budget_level": record.get("evaluation_budget"),
            "failed_replicates": [], "reason": EXCLUSION_REASON,
        })
        cell["failed_replicates"].append(record.get("replicate"))
    for cell in cells.values():
        cell["failed_replicates"].sort()
    return sorted(cells.values(), key=lambda c: (str(c["dataset_id"]), str(c["algorithm_id"]), c["protocol"], str(c["budget_level"])))


def _paper_report_text(
    plan: StudyPlan, status: str, planned: int, completed: int, written: Mapping[str, int],
    excluded: Sequence[Mapping[str, Any]], git: Mapping[str, Any], run_index: Mapping[str, Any], plan_label: str,
) -> str:
    lines = [
        "UniRide study run (paper mode)",
        f"Study: {plan.study.study_id} (status {plan.study.status})",
        f"Analysis plan: {plan_label}",
        f"Working tree clean at revision {git['revision']}",
        f"Rows: {planned} planned, {completed} completed, {planned - completed} failed",
    ]
    if status == "passed":
        lines.append("Result: PASSED. Every planned run completed and every row passed validation.")
    else:
        lines.append(
            "Result: COMPLETED WITH FAILED RUNS. Each failed run is a structured record in "
            + FAILED_FILE + " and no numeric observation."
        )
    for name, count in written.items():
        lines.append(f"File {name}: {count} row(s)")
    for cell in excluded:
        where = f"budget level {cell['budget_level']}" if cell["protocol"] == FIXED_GROUP else "native protocol"
        lines.append(
            f"Cell excluded from inference: {cell['algorithm_id']} on {cell['dataset_id']}, {where}, "
            f"failed replicate(s) {cell['failed_replicates']}"
        )
    lines.append(
        f"Run manifests: {run_index['manifests']} in {MANIFEST_DIR}/ with detached checksums; index {run_index['path']} "
        f"sha256 {run_index['sha256']}"
    )
    lines.append(
        "This report lists what ran and what failed. It makes no comparison between algorithms and supports no claim. "
        "Fixed-budget and native rows are written to separate files and are never pooled."
    )
    return "\n".join(lines) + "\n"


def _finalize_paper(
    plan: StudyPlan, output: Path, rows: Sequence[PlanRow], done: Mapping[int, tuple], git: Mapping[str, Any],
    environment: EnvironmentV1, plan_label: str,
) -> RunReport:
    """Derive result files, manifests, index and report from the finished rows; the checkpoint is removed last."""
    for name in (FIXED_FILE, NATIVE_FILE, FAILED_FILE, RUN_REPORT_TEXT_FILE, RUN_REPORT_JSON_FILE, INDEX_FILE,
                 INDEX_FILE + SIDECAR_SUFFIX):
        (output / name).unlink(missing_ok=True)
    shutil.rmtree(output / MANIFEST_DIR, ignore_errors=True)
    fixed_rows: List[Dict[str, Any]] = []
    native_rows: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    completed: List[tuple] = []
    for index, row in enumerate(rows):
        outcome, record = done[index]
        if outcome == "failed":
            failed.append(record)
            continue
        completed.append((row, record))
        (fixed_rows if row.protocol is ExecutionProtocol.FIXED_BUDGET else native_rows).append(record)
    levels_by_dataset = {d.dataset_id: fixed_budget_levels_for(plan.study, d) for d in plan.datasets}
    written: Dict[str, int] = {}
    if fixed_rows:
        write_rows_file(output / FIXED_FILE, fixed_rows, expected_group=FIXED_GROUP, levels_by_dataset=levels_by_dataset)
        written[FIXED_FILE] = len(fixed_rows)
    if native_rows:
        write_rows_file(output / NATIVE_FILE, native_rows, expected_group=NATIVE_GROUP)
        written[NATIVE_FILE] = len(native_rows)
    if failed:
        _jsonl_atomic(output / FAILED_FILE, failed)
        written[FAILED_FILE] = len(failed)
    status = "failed" if failed else "passed"
    run_index = _write_run_manifests(plan, output, completed, written, status, git, environment, mode="paper")
    if run_index is None:  # the git state was checked before the first run
        raise StudyRunError("run manifests could not be written: the git state is unknown")
    excluded = _excluded_cells(failed)
    text = _paper_report_text(plan, status, len(rows), len(completed), written, excluded, git, run_index, plan_label)
    assert_no_ranking_words(text)
    (output / RUN_REPORT_TEXT_FILE).write_text(text, encoding="utf-8")
    _json_atomic(output / RUN_REPORT_JSON_FILE, {
        "status": status, "study_id": plan.study.study_id, "mode": "paper", "rows_planned": len(rows),
        "rows_completed": len(completed), "rows_failed": len(failed), "excluded_cells": excluded, "git": dict(git),
        "environment": environment.model_dump(mode="json"), "analysis_plan": plan_label, "run_index": run_index,
        "rows_written": written, "statement": text,
    })
    # the marker goes first: a removal that stops half way leaves no campaign.json, so the rest can never be resumed
    # (a resume would re-run rows, and a recorded failure is never retried, OQ-9 a)
    (output / CHECKPOINT_DIR / CHECKPOINT_CAMPAIGN_FILE).unlink()
    shutil.rmtree(output / CHECKPOINT_DIR)
    return RunReport(
        status=status, mode="paper", output_dir=str(output), study_id=plan.study.study_id, rows_planned=len(rows),
        rows_completed=len(completed), rows_failed=len(failed), excluded_cells=tuple(excluded), run_index=run_index,
        text=text, files=tuple(sorted(p.name for p in output.iterdir())),
    )


# ---------------------------------------------------------------------------------------------------- paper mode
def _run_paper(
    study_path: str, output_dir: str | Path, *, root: Path, problem_loader: Optional[Callable[[str], Any]], resume: bool,
    git_provider: Callable[[Path], Mapping[str, Any]],
    environment_provider: Callable[[str], EnvironmentV1], backend_policy: BackendPolicy,
    registry_getter: Callable[[str], Any], runtime_probe: Callable[[], RuntimeBackendAvailability],
    registered_algorithms_provider: Callable[[], Iterable[str]], gateway_executor: Callable[..., Any],
) -> RunReport:
    # 1. profile and analysis plan (nothing runs or is written on a refusal)
    try:
        study = load_study(study_path, repository_root=root)
    except StudyServiceError as exc:
        raise StudyRunError(f"study profile refused: {exc}") from exc
    if study.status != "active":
        raise StudyRunError(
            f"paper mode refuses study profile {study.study_id!r}: status {study.status!r}, paper mode needs 'active' "
            "(A17 C-13 note); the profile becomes active only by an owner decision"
        )
    try:
        loaded = load_study_with_plan(study_path, repository_root=root, mode="smoke")  # label of the resolved plan
        load_study(study_path, repository_root=root, mode="paper")  # refuses an unresolved or non-active plan
    except StudyServiceError as exc:
        raise StudyRunError(f"paper mode refuses the analysis plan: {exc}") from exc
    plan_label = loaded.analysis_plan.label
    # 2. git state and output location
    git = _require_clean_git(root, git_provider)
    output = Path(output_dir).expanduser().resolve()
    main_tree = _main_working_tree(root)
    if _is_within(output, root) or (main_tree is not None and _is_within(output, main_tree)):
        raise StudyRunError(f"paper mode refuses an output directory inside the repository: {output}")
    checkpoint = output / CHECKPOINT_DIR
    if resume:
        if not (checkpoint / CHECKPOINT_CAMPAIGN_FILE).is_file():
            if (output / INDEX_FILE).is_file():
                raise StudyRunError(f"{output} holds a complete campaign (it has {INDEX_FILE}); there is nothing to resume")
            raise StudyRunError(f"{output} holds no started campaign; nothing to resume")
    elif output.exists() and any(output.iterdir()):
        raise StudyRunError(
            f"output directory {output} is not empty; start a new campaign in an empty directory or resume an "
            "interrupted one with resume (paper mode never overwrites)"
        )
    # 3. pinned analysis environment (D-04a): a missing library is a named error before any write
    require_analysis_environment()
    environment = environment_provider(statistics_library_identifier())
    # 4. plan, parameters and identity of every row
    try:
        plan = build_study_plan(study_path, repository_root=root, backend_policy=backend_policy)
    except StudyServiceError as exc:
        raise StudyRunError(f"study plan refused: {exc}") from exc
    rows = plan.rows
    loader = problem_loader or build_artifact_loader(plan, root)
    problems: Dict[str, Any] = {}
    for row in rows:
        _row_params(plan.study, row)
        if row.problem_name not in problems:
            problems[row.problem_name] = loader(row.problem_name)
        _check_identity(problems[row.problem_name], row)
    fingerprint = _fingerprint(plan, study_path, root, git, environment)
    # 5. start or resume
    if resume:
        differences = _fingerprint_differences(_read_wrapped(checkpoint / CHECKPOINT_CAMPAIGN_FILE), fingerprint)
        if differences:
            raise StudyRunError("resume refused: " + "; ".join(differences))
        done = _read_progress(checkpoint, rows)
    else:
        (checkpoint / CHECKPOINT_ROWS_DIR).mkdir(parents=True, exist_ok=True)
        _json_atomic(checkpoint / CHECKPOINT_CAMPAIGN_FILE, _wrapped(fingerprint))
        done = {}
    # 6. run the rows that are not done; every finished row (also a failed one) is persisted at once
    datasets = {d.dataset_id: d for d in plan.datasets}
    independent: Dict[str, Any] = {}
    runtime_backends = runtime_probe()
    registered = frozenset(registered_algorithms_provider())
    for index, row in enumerate(rows):
        if index in done:
            continue
        if row.dataset_id not in independent:
            independent[row.dataset_id] = _independent_cost(datasets[row.dataset_id], root)
        try:
            record = _run_row(
                row, problems[row.problem_name], datasets[row.dataset_id], plan, independent[row.dataset_id],
                registered=registered, runtime_backends=runtime_backends, registry_getter=registry_getter,
                gateway_executor=gateway_executor, smoke=False,
            )
            outcome = "completed"
        except _RowFailure as failure:
            record, outcome = _failed_record(row, failure, plan, smoke=False), "failed"
        record = json.loads(_canonical(record))  # the same JSON view whether the row is fresh or read back on resume
        _json_atomic(_progress_path(checkpoint, index), _wrapped({
            "index": index, "plan_row": _plan_row_key(row), "outcome": outcome, "record": record,
        }))
        done[index] = (outcome, record)
    return _finalize_paper(plan, output, rows, done, git, environment, plan_label)


# ----------------------------------------------------------------------------------------------------- smoke mode
def _smoke_descriptive_report(
    output: Path, loaded: Any, root: Path, reference_table_provider: Callable[[Path], ExactReferenceTable]
) -> List[str]:
    """Write the D-07 descriptive report of a smoke campaign; returns the lines to append to the run report text.

    The campaign is verified first (``load_verified_campaign``). The gap column comes from the exact reference table
    (``analysis.gaps``); when the table cannot be loaded every gap is ``null`` with its reason and the report says why. Nothing is
    written when there are no run manifests (unknown git state) or the analysis plan does not resolve; the lines say so."""
    if not (output / INDEX_FILE).is_file():
        return ["Descriptive report not written: there are no run manifests (the git state is unknown), so rows have no comparison identity."]
    resolution = loaded.analysis_plan
    if resolution.plan is None:
        return [f"Descriptive report not written: the analysis plan does not resolve ({resolution.problem})."]
    try:
        campaign = load_verified_campaign(output)
    except ManifestError as exc:
        raise StudyRunError(f"descriptive report refused: {exc}") from exc
    notes: List[str] = []
    try:
        table = reference_table_provider(root)
    except Exception as exc:  # noqa: BLE001 - the reference is optional for a smoke report; the reason is printed, never hidden
        table = ExactReferenceTable()
        notes.append(f"exact reference unavailable ({type(exc).__name__}: {exc}); every gap is null")
    groups: Dict[str, List[tuple]] = {}
    for row, manifest in campaign.items:
        groups.setdefault(classify_row(row).pooling_group, []).append((row, manifest))
    items: List[tuple] = []
    try:
        for members in groups.values():
            converted = add_gap_columns([row for row, _ in members], table, plan=resolution.plan)
            items.extend((new, manifest) for new, (_, manifest) in zip(converted, members))
        items.extend((row, None) for row in campaign.failed)
        report = build_report(
            items, study=loaded.study, plan=resolution.plan, run_index=campaign.index, index_sha256=campaign.index_sha256,
            notes=notes,
        )
    except (ValueError, ReportError) as exc:  # GapColumnError, ReportError, the wording check
        raise StudyRunError(f"descriptive report refused: {exc}") from exc
    write_report(report, output)
    return [f"Descriptive report: {REPORT_TEXT_FILE} ({len(report.data['tables'])} table(s), index sha256 {campaign.index_sha256})"]


def _run_smoke(
    study_path: str, output_dir: str | Path, *, root: Path, problem_loader: Optional[Callable[[str], Any]],
    replicates: int, budget_level: Optional[int], overwrite: bool, backend_policy: BackendPolicy,
    reference_table_provider: Callable[[Path], ExactReferenceTable] = load_reference_table, **providers: Any,
) -> RunReport:
    try:
        loaded = load_study_with_plan(study_path, repository_root=root, mode="smoke")
        plan = build_study_plan(study_path, repository_root=root, backend_policy=backend_policy)
    except StudyServiceError as exc:
        raise StudyRunError(f"study profile refused: {exc}") from exc
    loader = problem_loader or build_artifact_loader(plan, root)
    report = run_study_smoke(
        plan, output_dir, problem_loader=loader, repository_root=root, replicates=replicates,
        budget_level=budget_level, overwrite=overwrite, analysis_plan_label=loaded.analysis_plan.label,
        **providers,
    )
    written = dict(report.rows_written)
    completed = written.get(FIXED_FILE, 0) + written.get(NATIVE_FILE, 0)
    output = Path(report.output_dir)
    extra = _smoke_descriptive_report(output, loaded, root, reference_table_provider)
    return RunReport(
        status=report.status, mode="smoke", output_dir=report.output_dir, study_id=report.study_id,
        rows_planned=report.planned_rows, rows_completed=completed, rows_failed=len(report.failed_rows),
        text=report.text + "\n".join(extra) + "\n", files=tuple(sorted(p.name for p in output.iterdir())),
    )


# ------------------------------------------------------------------------------------------------------ service
def run_study(
    study_path: str,
    output_dir: str | Path,
    *,
    mode: str,
    repository_root: Optional[Path] = None,
    problem_loader: Optional[Callable[[str], Any]] = None,
    resume: bool = False,
    overwrite: bool = False,
    replicates: Optional[int] = None,
    budget_level: Optional[int] = None,
    backend_policy: BackendPolicy = DEFAULT_BACKEND_POLICY,
    registry_getter: Callable[[str], Any] = _registry_executor,
    runtime_probe: Callable[[], RuntimeBackendAvailability] = probe_runtime_backends,
    registered_algorithms_provider: Callable[[], Iterable[str]] = _registered_algorithm_ids,
    gateway_executor: Callable[..., Any] = execute_preflighted,
    git_provider: Callable[[Path], Mapping[str, Any]] = _git_metadata,
    environment_provider: Optional[Callable[[str], EnvironmentV1]] = None,
    reference_table_provider: Callable[[Path], ExactReferenceTable] = load_reference_table,
) -> RunReport:
    """Run one study in ``mode`` ("smoke" or "paper"); ``study_path`` is repository-relative.

    The backend policy is a service argument (A17 C-11 note); it is recorded in every run manifest through the row.
    ``environment_provider(statistics_library)`` builds the ``EnvironmentV1`` of the campaign (paper mode passes the
    pinned statistics library identifier, smoke mode the literal "none")."""
    if mode not in MODES:
        raise StudyRunError(f"unknown mode {mode!r}; use 'smoke' or 'paper'")
    root = (Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[2]).resolve()
    make_environment = environment_provider or collect_environment
    if mode == "paper":
        if replicates is not None or budget_level is not None or overwrite:
            raise StudyRunError("paper mode runs the whole plan: replicates, budget level and overwrite are smoke options")
        return _run_paper(
            study_path, output_dir, root=root, problem_loader=problem_loader, resume=resume, git_provider=git_provider,
            environment_provider=make_environment, backend_policy=backend_policy, registry_getter=registry_getter,
            runtime_probe=runtime_probe, registered_algorithms_provider=registered_algorithms_provider,
            gateway_executor=gateway_executor,
        )
    if resume:
        raise StudyRunError("smoke runs are not resumable: run the slice again in an empty directory")
    return _run_smoke(
        study_path, output_dir, root=root, problem_loader=problem_loader,
        replicates=SMOKE_MAX_REPLICATES if replicates is None else replicates,
        budget_level=budget_level, overwrite=overwrite, backend_policy=backend_policy, registry_getter=registry_getter,
        runtime_probe=runtime_probe, registered_algorithms_provider=registered_algorithms_provider,
        gateway_executor=gateway_executor, git_provider=git_provider,
        environment_provider=lambda: make_environment("none"), reference_table_provider=reference_table_provider,
    )


# --------------------------------------------------------------------------------------------------------- CLI
def _relative_study_path(value: str, root: Path) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError as exc:
            raise StudyRunError(f"study file {value} is not inside the repository {root}") from exc
    return path.as_posix()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a study profile in smoke or paper mode (Gate D, D-03)")
    parser.add_argument("--study", required=True, help="repository-relative path of the study.json")
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--out", required=True, help="output directory (outside the repository)")
    parser.add_argument("--resume", action="store_true", help="paper mode: continue an interrupted campaign")
    parser.add_argument("--overwrite", action="store_true", help="smoke mode: reuse a non-empty output directory")
    parser.add_argument("--replicates", type=int, default=None, help="smoke mode: replicates per cell (default and cap 3)")
    parser.add_argument("--budget-level", type=int, default=None, help="smoke mode: fixed-budget level (default: lowest)")
    parser.add_argument("--backend-policy", choices=[p.value for p in BackendPolicy], default=DEFAULT_BACKEND_POLICY.value)
    parser.add_argument("--repository-root", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = (Path(args.repository_root) if args.repository_root else Path(__file__).resolve().parents[2]).resolve()
    try:
        report = run_study(
            _relative_study_path(args.study, root), args.out, mode=args.mode, repository_root=root, resume=args.resume,
            overwrite=args.overwrite, replicates=args.replicates, budget_level=args.budget_level,
            backend_policy=BackendPolicy(args.backend_policy),
        )
    except (StudyRunError, StudySmokeError, StudyServiceError, AnalysisEnvironmentError, FairPilotError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(report.text)
    return 0 if report.status == "passed" else 1


__all__ = [
    "MODES", "RunReport", "StudyRunError", "build_artifact_loader", "main", "run_study",
]

if __name__ == "__main__":
    sys.exit(main())
