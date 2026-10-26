"""Descriptive reports for smoke and paper campaigns (Gate D, D-07; plan 2026-10-23 section 3; DECISION_LOG A18 OQ-15 and D-09).

``build_report`` turns the verified rows of one campaign (rows with the D-06 gap columns, each with its run manifest) into

* a **banner**: mode and git state of the campaign (both read from the verified ``RunIndexV2``, not from arguments), the dirty
  flag, the study profile status, the analysis plan and its status, the sha256 of ``run_index.json`` and the statistics library;
* one **descriptive table per comparison cell** (D-01: one pooling group, protocol version, study, dataset, budget level, one
  code commit; only the algorithm varies inside a table). A table lists, for each variable of the analysis plan (cost, gap to the
  exact reference, evaluations consumed, evaluation-budget share), exactly the columns of the plan (OQ-15: n, median, IQR,
  min, max, mean, sample SD) and nothing else, plus the plan's count fields (termination reasons, failed runs). The statistics
  come from ``statistics.describe_sample`` (D-05), which reads the SD convention and the quantile method from the plan; this module
  computes no other statistic;
* the **gap column** as D-06 left it: a negative gap (cost below the proven exact optimum) is reported as computed and flagged
  ``NEGATIVE GAP`` in the table; a row without an exact reference shows ``null`` with its reason, never a substitute value;
* in **paper mode only**, the **inferential section**: the text and fields of ``statistics.analyse_family`` quoted as they are
  (method used per pair, exclusions, the reasons inference was not performed). Nothing is recomputed here. A smoke report refuses
  an inferential section: smoke runs support no claim.

The report is not covered by a checksum, like ``run_report``: it quotes the index checksum, so the index cannot list it, and nothing ever
reads a descriptive report back as input (the rows and manifests it describes are the verified campaign files).

Smoke reports pass the no-ranking wording check (``studies.smoke.assert_no_ranking_words``, A15) before they are returned or written.
Every refusal raises ``ReportError`` naming the reason: a plan without a column or variable list, rows of two comparison cells in
one table, a row without a manifest, an exact/union/joint row, a row without gap columns, a campaign whose index does not list the
manifests, a dirty paper campaign.
"""
from __future__ import annotations

import math
import os
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from academic_benchmark.analysis.identity import (
    VARY_DIMENSIONS,
    ComparisonIdentityError,
    assert_single_comparison_family,
    comparison_cell_key,
)
from academic_benchmark.analysis.statistics import FamilyAnalysis, describe_sample
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.contracts.run_index import RunIndexV2
from academic_benchmark.contracts.study import StudyManifestV1
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.obsolete_results import CURRENT_EVIDENCE, evidence_refusal
from academic_benchmark.studies.smoke import StudySmokeError, assert_no_ranking_words

REPORT_SCHEMA = "uniride-descriptive-report/v1"
REPORT_TEXT_FILE = "descriptive_report.txt"
REPORT_JSON_FILE = "descriptive_report.json"
GAP_COLUMN = "gap_to_exact_reference"
GAP_UNIT_COLUMN = "gap_unit"
GAP_REASON_COLUMN = "gap_missing_reason"
COST_FIELD = "objective_cost"
EVALUATIONS_FIELD = "objective_evaluations"
BUDGET_FIELD = "evaluation_budget"
FIXED_GROUP = "fixed_budget"
NATIVE_GROUP = "native"
NO_REASON = "no reason recorded"
VARIABLE_LABELS = {
    "cost": "tour cost (objective_cost)",
    "gap": "gap to the exact reference (percent)",
    "evaluations_consumed": "objective evaluations consumed",
    "evaluation_budget_share": "share of the evaluation budget consumed (fixed budget only)",
}


class ReportError(ValueError):
    """The report was refused; the message names the reason."""


@dataclass(frozen=True)
class DescriptiveReport:
    text: str
    data: dict
    mode: str


# ------------------------------------------------------------------------------------------------ guards
def _check_plan(plan: Any) -> AnalysisPlanV1:
    if not isinstance(plan, AnalysisPlanV1):
        raise ReportError(f"the report is defined by an AnalysisPlanV1, not {type(plan).__name__}")
    if not list(plan.descriptive.columns):
        raise ReportError(f"analysis plan {plan.analysis_plan_id!r} lists no descriptive column: the report column set comes from the plan")
    if not list(plan.descriptive.variables):
        raise ReportError(f"analysis plan {plan.analysis_plan_id!r} lists no descriptive variable: the report has nothing to describe")
    if plan.response.unit != "percent":
        raise ReportError(f"the plan's gap unit {plan.response.unit!r} is not the implemented 'percent'")
    return plan


def _is_failed(row: Mapping[str, Any]) -> bool:
    return row.get("record_kind") == "failed_run" or row.get("validation_status") == "failed"


def _number(row: Mapping[str, Any], field: str, what: str) -> float:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ReportError(f"{what}: a completed row needs a finite numeric {field!r}, got {value!r}")
    return float(value)


def _failed_cell(row: Mapping[str, Any]) -> tuple:
    algorithm, problem = row.get("algorithm_id"), row.get("problem")
    if not isinstance(algorithm, str) or not isinstance(problem, str) or not problem.strip():
        raise ReportError("a failed run needs its algorithm_id and problem name to be reported")
    group = FIXED_GROUP if row.get("comparison_regime") == "fixed_evaluation_budget" else NATIVE_GROUP
    return normalize_problem(problem), group, row.get(BUDGET_FIELD), algorithm


def _split(items: Iterable[tuple]) -> tuple:
    good, failed = [], []
    for item in items:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ReportError("items must be (row, manifest) pairs; a failed run is (row, None)")
        row, manifest = item
        if not isinstance(row, Mapping):
            raise ReportError(f"a row must be a mapping, not {type(row).__name__}")
        if _is_failed(row):
            failed.append(row)
            continue
        if manifest is None:
            raise ReportError(
                f"{row.get('algorithm_id')!r} on {row.get('problem')!r}: a completed row has no run manifest, so it has no comparison identity"
            )
        if row.get("evidence_class") not in CURRENT_EVIDENCE:
            raise ReportError(f"evidence_class {row.get('evidence_class')!r}: historical_unverified and invalid rows are never reported (A13)")
        reason = evidence_refusal(row)  # INVALID marker (A06), Gate D D-08b
        if reason:
            raise ReportError(reason)
        if GAP_COLUMN not in row:
            raise ReportError(f"a row has no {GAP_COLUMN} column: rows must come through analysis.gaps.add_gap_columns (D-06)")
        good.append((row, manifest))
    return good, failed


# ------------------------------------------------------------------------------------------------ one table
def _describe(values: Sequence[float], plan: AnalysisPlanV1) -> dict:
    if values:
        return describe_sample(values, plan.descriptive)
    return {column: (0 if column == "n" else None) for column in plan.descriptive.columns}


def _algorithm_summary(rows: Sequence[Mapping[str, Any]], failed_count: int, plan: AnalysisPlanV1, algorithm: str) -> tuple:
    values: dict = {name: [] for name in plan.descriptive.variables}
    missing_reasons: Counter = Counter()
    flags = []
    unit = plan.response.unit
    for row in sorted(rows, key=lambda r: r.get("replicate", 0)):
        what = f"{algorithm} replicate {row.get('replicate')}"
        cost = _number(row, COST_FIELD, what)
        consumed = _number(row, EVALUATIONS_FIELD, what)
        gap = row[GAP_COLUMN]
        if gap is None:
            missing_reasons[row.get(GAP_REASON_COLUMN) or NO_REASON] += 1
        else:
            if row.get(GAP_UNIT_COLUMN) != unit:
                raise ReportError(f"{what}: gap unit {row.get(GAP_UNIT_COLUMN)!r} differs from the plan's {unit!r}")
            gap = _number(row, GAP_COLUMN, what)
            if gap < 0:
                flags.append({
                    "kind": "negative_gap", "algorithm_id": algorithm, "replicate": row.get("replicate"), "gap": gap,
                    "message": (
                        f"NEGATIVE GAP: {algorithm} replicate {row.get('replicate')} has gap {gap:.6g} percent, i.e. a cost below "
                        "the proven exact optimum; it is reported as computed, never clamped, and the exact reference or the "
                        "run validation needs a check"
                    ),
                })
        budget = row.get(BUDGET_FIELD)
        for name in plan.descriptive.variables:
            if name == "cost":
                values[name].append(cost)
            elif name == "gap" and gap is not None:
                values[name].append(gap)
            elif name == "evaluations_consumed":
                values[name].append(consumed)
            elif name == "evaluation_budget_share" and isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0:
                values[name].append(consumed / float(budget))
    summary = {
        "algorithm_id": algorithm,
        "variables": {name: _describe(values[name], plan) for name in plan.descriptive.variables},
    }
    if "gap" in plan.descriptive.variables:
        summary["gap_missing"] = {"count": sum(missing_reasons.values()), "reasons": sorted(missing_reasons)}
    if "termination_reason_counts" in plan.descriptive.counts:
        counts = Counter(row.get("termination_reason") or "unrecorded" for row in rows)
        summary["termination_reason_counts"] = dict(sorted(counts.items()))
    if "failed_run_count" in plan.descriptive.counts:
        summary["failed_run_count"] = failed_count
    return summary, flags


def build_descriptive_table(items: Iterable[tuple], plan: AnalysisPlanV1, *, allow_dirty: bool = False) -> dict:
    """One descriptive table: the rows of ONE comparison cell (only the algorithm may vary) and the failed runs of that cell.

    ``items`` are ``(row, manifest)`` pairs, failed runs ``(row, None)``. Rows of two comparison cells (another instance, budget
    level, study, protocol version, commit...) are refused; exact, union and joint rows are refused; a completed row needs a
    manifest and the D-06 gap columns. Returns a JSON-serialisable mapping (``cell``, ``algorithms``, ``flags``)."""
    plan = _check_plan(plan)
    good, failed = _split(items)
    if not good:
        raise ReportError("a descriptive table needs at least one completed row")
    try:
        family = assert_single_comparison_family(good, vary=("algorithm",), allow_dirty=allow_dirty)
    except ValueError as exc:  # ComparisonIdentityError and the pooling-group refusal
        raise ReportError(f"the rows are not one comparison cell, so they do not form one table: {exc}") from exc
    shared = family.shared
    budgets = {row.get(BUDGET_FIELD) for row, _ in good}
    if len(budgets) != 1:
        raise ReportError(f"the rows of one comparison cell carry different evaluation budgets {sorted(map(str, budgets))}")
    budget = next(iter(budgets))
    cell = {
        "pooling_group": shared["pooling_group"], "protocol_version": shared["protocol_version"], "study_id": shared["study_id"],
        "dataset_identity": shared["dataset_identity"], "budget_level_index": shared["budget_level_index"],
        "evaluation_budget": budget,
    }
    failed_counts: Counter = Counter()
    for row in failed:
        identity, group, failed_budget, algorithm = _failed_cell(row)
        if (identity, group, failed_budget) != (cell["dataset_identity"], cell["pooling_group"], budget):
            raise ReportError(
                f"a failed run of {algorithm!r} on {row.get('problem')!r} belongs to another comparison cell than this table "
                f"({cell['dataset_identity']}, {cell['pooling_group']}, budget {budget})"
            )
        failed_counts[algorithm] += 1
    by_algorithm: dict = {}
    for row, _ in good:
        by_algorithm.setdefault(row["algorithm_id"], []).append(row)
    for algorithm in failed_counts:
        by_algorithm.setdefault(algorithm, [])
    algorithms, flags = [], []
    for algorithm in sorted(by_algorithm):
        summary, algorithm_flags = _algorithm_summary(by_algorithm[algorithm], failed_counts[algorithm], plan, algorithm)
        algorithms.append(summary)
        flags.extend(algorithm_flags)
    notes = []
    if "evaluation_budget_share" in plan.descriptive.variables and cell["pooling_group"] == NATIVE_GROUP:
        notes.append("evaluation_budget_share is not defined for native rows (no evaluation budget)")
    return {"cell": cell, "algorithms": algorithms, "flags": flags, "notes": notes}


# ------------------------------------------------------------------------------------------------ campaign checks
def _check_campaign(
    good: Sequence[tuple], *, study: Any, plan: AnalysisPlanV1, run_index: Any, index_sha256: Any
) -> RunIndexV2:
    if not isinstance(study, StudyManifestV1):
        raise ReportError(f"study must be the StudyManifestV1 profile, not {type(study).__name__}")
    if study.study_id != plan.study_id:
        raise ReportError(f"the study profile {study.study_id!r} and the analysis plan of study {plan.study_id!r} do not belong together")
    if plan.analysis_plan_id != study.analysis_plan_id:
        raise ReportError(
            f"the analysis plan {plan.analysis_plan_id!r} is not the one the study profile names (analysis_plan_id {study.analysis_plan_id!r})"
        )
    if not isinstance(run_index, RunIndexV2):
        raise ReportError(f"run_index must be the verified RunIndexV2 of the campaign, not {type(run_index).__name__}")
    if not isinstance(index_sha256, str) or len(index_sha256) != 64 or any(c not in "0123456789abcdef" for c in index_sha256):
        raise ReportError("index_sha256 must be the lower-case hex sha256 of run_index.json (the banner quotes it)")
    if run_index.study_id != study.study_id:
        raise ReportError(f"the run index belongs to study {run_index.study_id!r}, the study profile to {study.study_id!r}")
    if run_index.mode == "paper" and run_index.git.dirty:
        raise ReportError("the run index records a dirty working tree: a paper report needs one clean commit")
    listed = {entry.run_id: entry for entry in run_index.runs}
    for row, manifest in good:
        entry = listed.get(manifest.run_id)
        if entry is None:
            raise ReportError(f"manifest {manifest.run_id!r} is not listed in the run index: rows must come from the verified campaign")
        if manifest.git.commit != run_index.git.commit:
            raise ReportError(f"manifest {manifest.run_id!r} was written at commit {manifest.git.commit}, the run index at {run_index.git.commit}")
        try:
            digest = comparison_cell_key(row, manifest, allow_dirty=True).digest()
        except ComparisonIdentityError as exc:
            raise ReportError(f"the row of {manifest.run_id!r} does not belong to its manifest: {exc}") from exc
        if digest != entry.comparison_key_digest:
            raise ReportError(f"the comparison key digest of {manifest.run_id!r} differs from the run index entry")
    return run_index


def _cell_signature(row: Mapping[str, Any], manifest: Any, allow_dirty: bool) -> tuple:
    try:
        key = comparison_cell_key(row, manifest, allow_dirty=allow_dirty)
    except ComparisonIdentityError as exc:
        raise ReportError(f"{row.get('algorithm_id')!r} on {row.get('problem')!r}: {exc}") from exc
    masked = set(VARY_DIMENSIONS["algorithm"])
    return tuple((name, value) for name, value in sorted(key.as_dict().items()) if name not in masked)


# ------------------------------------------------------------------------------------------------ rendering
def _fmt(value: Any, column: str, n: Any) -> str:
    if value is None:
        return "undefined" if column == "sd" and n == 1 else "null"
    if isinstance(value, int):
        return str(value)
    return f"{value:.6g}"


def _render_table(table: dict, plan: AnalysisPlanV1) -> list:
    cell = table["cell"]
    level = "native protocol (no budget level)" if cell["budget_level_index"] is None else (
        f"budget level index {cell['budget_level_index']} (evaluation budget {cell['evaluation_budget']})"
    )
    lines = [
        f"Cell: dataset {cell['dataset_identity']} | protocol {cell['pooling_group']} ({cell['protocol_version']}) | {level} | study {cell['study_id']}"
    ]
    columns = list(plan.descriptive.columns)
    for variable in plan.descriptive.variables:
        lines.append(f"  Variable {variable}: {VARIABLE_LABELS[variable]}")
        lines.append("    " + " | ".join(["algorithm", *columns]))
        for algorithm in table["algorithms"]:
            stats = algorithm["variables"][variable]
            lines.append("    " + " | ".join([algorithm["algorithm_id"], *(_fmt(stats[c], c, stats.get("n")) for c in columns)]))
    for algorithm in table["algorithms"]:
        parts = []
        if "termination_reason_counts" in algorithm:
            reasons = ", ".join(f"{k}={v}" for k, v in algorithm["termination_reason_counts"].items()) or "none"
            parts.append(f"termination reasons {reasons}")
        if "failed_run_count" in algorithm:
            parts.append(f"failed runs {algorithm['failed_run_count']}")
        if parts:
            lines.append(f"  Counts {algorithm['algorithm_id']}: " + "; ".join(parts))
        missing = algorithm.get("gap_missing")
        if missing and missing["count"]:
            lines.append(
                f"  Gap is null for {missing['count']} row(s) of {algorithm['algorithm_id']}: " + "; ".join(missing["reasons"])
            )
    for note in table["notes"]:
        lines.append(f"  Note: {note}")
    for flag in table["flags"]:
        lines.append(f"  {flag['message']}")
    return lines


def _jsonable(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)  # 'inf' or 'nan' as text: the quoted D-05 text says what it means
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _inference_section(analysis: FamilyAnalysis) -> dict:
    inference = analysis.inference
    return _jsonable({
        "family_id": analysis.family_id, "scope": analysis.scope, "campaign_mode": analysis.campaign_mode,
        "analysis_plan_id": analysis.analysis_plan_id, "plan_status": analysis.plan_status,
        "statistics_library": analysis.statistics_library, "conventions": dict(analysis.conventions),
        "omnibus": asdict(inference.omnibus) if inference is not None else None,
        "post_hoc_ran": inference.post_hoc_ran if inference is not None else None,
        "post_hoc_reason": inference.post_hoc_reason if inference is not None else None,
        "pairs": [asdict(pair) for pair in inference.pairs] if inference is not None else [],
        "exclusions": [dict(item) for item in analysis.exclusions],
        "excluded_pairs": [dict(item) for item in analysis.excluded_pairs],
        "inference_refused": list(analysis.inference_refused),
        "text": analysis.text,
    })


def _check_inference(inference: Sequence[Any], *, mode: str, plan: AnalysisPlanV1) -> list:
    sections = list(inference)
    if not sections:
        return []
    if mode != "paper":
        raise ReportError(f"a {mode} report has no inferential section: only a paper campaign is analysed, and smoke runs support no claim")
    for analysis in sections:
        if not isinstance(analysis, FamilyAnalysis):
            raise ReportError(f"the inferential section comes from statistics.analyse_family, not {type(analysis).__name__}")
        if analysis.campaign_mode != "paper":
            raise ReportError(f"family {analysis.family_id!r} was analysed for campaign mode {analysis.campaign_mode!r}, not 'paper'")
        if analysis.analysis_plan_id != plan.analysis_plan_id:
            raise ReportError(
                f"family {analysis.family_id!r} was analysed under analysis plan {analysis.analysis_plan_id!r}, the report's plan is {plan.analysis_plan_id!r}"
            )
    return sections


# ------------------------------------------------------------------------------------------------ the report
def build_report(
    items: Iterable[tuple],
    *,
    study: StudyManifestV1,
    plan: AnalysisPlanV1,
    run_index: RunIndexV2,
    index_sha256: str,
    inference: Sequence[FamilyAnalysis] = (),
    notes: Sequence[str] = (),
) -> DescriptiveReport:
    """The descriptive report of one verified campaign.

    ``items`` are ``(row, manifest)`` pairs (failed runs ``(row, None)``); rows carry the D-06 gap columns. ``run_index`` is the
    ``RunIndexV2`` of the campaign the caller verified (``manifests.load_verified_campaign``) and ``index_sha256`` the sha256 of its
    ``run_index.json``. The mode (smoke or paper), commit and dirty flag in the banner are the index's. ``inference`` holds the
    ``analyse_family`` results of a paper campaign and is refused for a smoke campaign."""
    plan = _check_plan(plan)
    good, failed = _split(items)
    if not good and not failed:
        raise ReportError("the report has no rows")
    index = _check_campaign(good, study=study, plan=plan, run_index=run_index, index_sha256=index_sha256)
    mode = index.mode
    sections = _check_inference(inference, mode=mode, plan=plan)
    allow_dirty = mode == "smoke"
    cells: dict = {}
    for row, manifest in good:
        cells.setdefault(_cell_signature(row, manifest, allow_dirty), []).append((row, manifest))
    tables = []
    leftover = list(failed)
    for members in cells.values():
        shared = comparison_cell_key(members[0][0], members[0][1], allow_dirty=allow_dirty)
        budget = members[0][0].get(BUDGET_FIELD)
        own = []
        for row in list(leftover):
            identity, group, failed_budget, _ = _failed_cell(row)
            if (identity, group, failed_budget) == (shared.dataset_identity, shared.pooling_group, budget):
                own.append((row, None))
                leftover.remove(row)
        tables.append(build_descriptive_table([*members, *own], plan, allow_dirty=allow_dirty))
    tables.sort(key=lambda t: (t["cell"]["dataset_identity"], t["cell"]["pooling_group"], -1 if t["cell"]["budget_level_index"] is None else t["cell"]["budget_level_index"]))
    failed_only: dict = {}
    for row in leftover:
        identity, group, failed_budget, algorithm = _failed_cell(row)
        entry = failed_only.setdefault((algorithm, identity, group, failed_budget), {
            "algorithm_id": algorithm, "dataset_identity": identity, "protocol": group, "evaluation_budget": failed_budget,
            "failed_run_count": 0,
        })
        entry["failed_run_count"] += 1
    failed_only_cells = sorted(failed_only.values(), key=lambda e: (e["dataset_identity"], e["algorithm_id"], e["protocol"], str(e["evaluation_budget"])))

    banner = {
        "mode": mode, "commit": index.git.commit, "dirty": index.git.dirty, "study_id": study.study_id,
        "profile_status": study.status, "analysis_plan_id": plan.analysis_plan_id, "analysis_plan_status": plan.status,
        "manifest_index_sha256": index_sha256, "statistics_library": index.environment.statistics_library,
        # D-07 (run-index completeness): the plan file hash and the planned run count come from the verified index
        "analysis_plan_sha256": index.analysis_plan.sha256, "planned_runs": index.planned.runs,
        "planned_runs_per_cell": index.planned.runs_per_cell, "completed_runs": len(index.runs),
        "failed_runs": len(index.failed_runs),
    }
    spec = plan.descriptive
    descriptive_spec = {
        "columns": list(spec.columns), "variables": list(spec.variables), "counts": list(spec.counts),
        "sd_convention": spec.sd_convention, "quantile_method": spec.quantile_method,
    }
    head = [
        f"UniRide descriptive report ({mode} mode)",
        f"Mode: {mode}",
        f"Commit: {banner['commit']}",
        f"Working tree dirty: {'YES' if banner['dirty'] else 'no'}",
        f"Study profile: {study.study_id} (status {study.status})",
        f"Analysis plan: {plan.analysis_plan_id} (status {plan.status})",
        "Analysis plan sha256: " + (banner["analysis_plan_sha256"] or "not recorded (the analysis plan did not resolve)"),
        f"Planned runs: {banner['planned_runs']} ({banner['planned_runs_per_cell']} per cell); "
        f"completed {banner['completed_runs']}; failed {banner['failed_runs']}",
        f"Manifest index sha256: {index_sha256}",
        f"Statistics library: {banner['statistics_library']}",
    ]
    if mode == "smoke":
        head.append(
            "Smoke campaign: the tables describe a small slice and support no claim; the report states no comparison between algorithms."
        )
    body = [
        "Descriptive columns of the analysis plan (the same list for every variable): " + ", ".join(spec.columns)
        + f"; SD convention {spec.sd_convention}; quantile method {spec.quantile_method}; null = no value (reason given below the table).",
    ]
    for table in tables:
        body.append("")
        body.extend(_render_table(table, plan))
    for entry in failed_only_cells:
        where = "native protocol" if entry["protocol"] == NATIVE_GROUP else f"evaluation budget {entry['evaluation_budget']}"
        body.append("")
        body.append(
            f"Cell with no completed run: {entry['algorithm_id']} on {entry['dataset_identity']} ({entry['protocol']}, {where}): "
            f"{entry['failed_run_count']} failed run(s); no descriptive row"
        )
    for note in notes:
        body.append("")
        body.append(f"Note: {note}")
    descriptive_text = "\n".join([*head, "", *body])
    try:
        assert_no_ranking_words(descriptive_text)  # the descriptive part never carries ranking wording, in any mode
    except StudySmokeError as exc:
        raise ReportError(str(exc)) from exc
    parts = [descriptive_text]
    if sections:
        parts.append("")
        parts.append("Inferential results (D-05 statistics service, quoted verbatim; nothing is recomputed in this report)")
        for analysis in sections:
            parts.append("")
            parts.append(analysis.text)
    text = "\n".join(parts) + "\n"
    data = {
        "schema_version": REPORT_SCHEMA, "mode": mode, "banner": banner, "descriptive_spec": descriptive_spec,
        "tables": tables, "failed_only_cells": failed_only_cells, "notes": list(notes),
        "inference": [_inference_section(analysis) for analysis in sections],
    }
    return DescriptiveReport(text=text, data=_jsonable(data), mode=mode)


# ------------------------------------------------------------------------------------------------ writing
def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(content.encode("utf-8"))  # LF line ends on every platform
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_report(report: DescriptiveReport, directory: str | Path) -> list:
    """Write ``descriptive_report.txt`` and ``descriptive_report.json`` into ``directory`` (atomically) and return the paths.

    A smoke report is checked against the no-ranking wording list again (the whole text) before anything is written."""
    if report.mode == "smoke":
        try:
            assert_no_ranking_words(report.text)
        except StudySmokeError as exc:
            raise ReportError(str(exc)) from exc
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    text_path, json_path = target / REPORT_TEXT_FILE, target / REPORT_JSON_FILE
    payload = json.dumps(report.data, indent=2, sort_keys=True, allow_nan=False) + "\n"
    _write_atomic(text_path, report.text)
    _write_atomic(json_path, payload)
    return [text_path, json_path]


__all__ = [
    "DescriptiveReport", "REPORT_JSON_FILE", "REPORT_SCHEMA", "REPORT_TEXT_FILE", "ReportError", "build_descriptive_table",
    "build_report", "write_report",
]
