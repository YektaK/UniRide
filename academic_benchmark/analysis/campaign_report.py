"""Descriptive report of a written campaign folder (Gate D, D-07), the analysis-layer glue behind ``studies.run``.

The gap columns come from the exact reference (``analysis.gaps``) and the rows are classified by ``protocol_registry``; both are
analysis-layer concerns, and the E12/D-06 boundary tests keep them out of the study modules (``studies/*.py``). The run service
therefore calls ``write_smoke_descriptive_report`` and imports neither: it verifies the campaign folder, adds the gap columns, builds the
report (``analysis.report``) and writes ``descriptive_report.txt/json`` next to the campaign.

``rebuild_descriptive_report`` and ``python -m academic_benchmark.analysis.campaign_report <campaign dir> [--study <study.json>]`` build
the report again from an existing campaign folder (for example after a crash between the run index and the report). Exit codes as in
``studies.run``: 0 written, 1 written for a campaign whose run status is "failed", 2 refused (campaign folder inside the repository, a
folder that does not verify, an exact reference that fails its integrity checks or its cross-check with the published optima, a refused
report, a study profile or analysis plan that cannot be read from git at the campaign's commit, a profile whose committed bytes do not
match the recorded hash). The rebuild reads the study profile and the analysis plan as committed at the commit the campaign recorded
(``git show <commit>:<file>``), not the working-tree files, from the paths the run index recorded (``--study`` overrides the profile path;
the plan then lies next to it), and compares their hashes with the run index.

Hash comparison differs between the two entry points. The smoke run's own report (``write_smoke_descriptive_report``) compares exact
bytes: it holds the very file the run service hashed. Only the rebuild, which has git's stored bytes, accepts the LF and the CRLF
variant of those bytes as the recorded file (a checkout with ``core.autocrlf`` hashes other line endings than the stored blob; A20 L6):
the bytes as stored, all-LF and all-CRLF, nothing else (no whitespace tolerance, no mixed endings). The plan hash differing is a warning
for a smoke campaign and a refusal for a paper campaign; the profile hash differing refuses in both modes.

The exact reference is optional for a descriptive report, but only in one sense: when ``results_index.json`` is absent (or lists no
TSP reference) the gap column is ``null`` with its reason and the report and the run text say so. An integrity refusal of the reference
(``ExactReferenceRefused``: checksum, manifest or validation failure) is never turned into null gaps: it refuses the report.

``python -m academic_benchmark.analysis.campaign_report <campaign dir> --paper`` (``rebuild_paper_report``; DECISION_LOG A20 L12) is the
paper report. It accepts only a paper campaign (run index ``mode`` paper, verified complete by the verifier, clean, an active profile and
an active analysis plan read at the campaign commit; a plan whose committed bytes differ from the recorded hash refuses). For every
comparison family the plan declares it makes one ``analyse_family`` call per comparison cell (each protocol, each fixed-budget level,
and for a per-instance family each instance, so fixed-budget and native rows are never pooled), passing the run index, its sha256 and
through it the campaign commit, and writes ``paper_report.txt/json`` (the descriptive tables plus the inferential section, each analysis
labelled with its comparison cell) next to the campaign. The paper report JSON carries its own schema name ``uniride-paper-report/v1``
and the title "UniRide paper report"; the descriptive report keeps ``uniride-descriptive-report/v1`` (DECISION_LOG A20 L13). Exit codes as above: 0 written, 1 written for a campaign with failed runs, 2
refused (not a paper campaign, integrity, identity or plan mismatch, a refusal of the statistics service). Rows that belong to no declared
family and failed runs of a cell with no completed run are listed in the report notes; a failed run whose recorded dataset id is not
``tsplib-<normalised problem name>`` is refused. A folder inside the repository is refused first and nothing in it is touched; for a campaign folder outside the repository an old ``paper_report.*`` is removed once the folder checks pass, so a later refusal leaves none behind. The paper run service prints
this command at the end of every paper campaign (a campaign with failed runs also gets a line saying the command exits 1) and runs no
analysis itself.

Descriptive reports are not covered by a checksum (like ``run_report``: the run index quotes nothing of them and they quote the index
checksum) and nothing ever reads them back as input.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from academic_benchmark.analysis.environment import AnalysisEnvironmentError
from academic_benchmark.analysis.gaps import (
    ExactReferenceTable,
    ReferenceCrossCheckError,
    add_gap_columns,
    load_reference_table,
)
from academic_benchmark.analysis.identity import comparison_cell_key
from academic_benchmark.committed_bytes import GitQueryFailed, run_git
from academic_benchmark.analysis.manifests import (
    DESCRIPTIVE_REPORT_FILES,
    PAPER_REPORT_FILES,
    ManifestError,
    VerifiedCampaign,
    load_verified_campaign,
)
from academic_benchmark.analysis.problem_contract import ProblemContractError, canonical_problem_contract
from academic_benchmark.analysis.report import (
    PAPER_REPORT_TEXT_FILE,
    REPORT_TEXT_FILE,
    ReportError,
    build_report,
    write_report,
)
from academic_benchmark.analysis.statistics import NOT_A_LEVEL, StatisticsRefusal, analyse_family, level_index_of
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.contracts.study import StudyManifestV1
from academic_benchmark.exact_reference import reader as reference_reader
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.protocol_registry import classify_row


class CampaignReportError(ValueError):
    """The campaign folder does not verify, a gap cannot be computed without a silent choice, the reference failed its integrity
    checks, or the report was refused."""


def default_reference_table(root: Path) -> ExactReferenceTable:
    """The exact reference table of the repository at ``root``.

    Raises ``FileNotFoundError`` when there is no reference to read (``results_index.json`` absent, or no TSP reference listed): that is
    "not available". Everything else the reader refuses (``ExactReferenceRefused``) is an integrity failure and propagates."""
    index_path = Path(root) / reference_reader.INDEX_RELATIVE_PATH
    if not index_path.is_file():
        raise FileNotFoundError(f"{reference_reader.INDEX_RELATIVE_PATH} is not in {root}")
    entries = reference_reader.read_index(root)  # a corrupt index is ExactReferenceRefused, not "unavailable"
    if not any(isinstance(entry, Mapping) and entry.get("manifest_kind") == reference_reader.KIND_TSP for entry in entries):
        raise FileNotFoundError("results_index.json lists no tsp_reference results")
    return load_reference_table(root)


FIXED_GROUP = "fixed_budget"
NATIVE_GROUP = "native"


def _paper_analyses(
    items: Sequence[tuple], *, study: StudyManifestV1, plan: AnalysisPlanV1, campaign: VerifiedCampaign
) -> tuple:
    """``(analyses, cells, notes)``: ``analyse_family`` for every comparison family the plan declares, over the rows of the campaign.

    ``items`` are the ``(row, manifest)`` pairs of the campaign with their gap columns, failed runs as ``(row, None)``. One analysis is
    made for each comparison cell of a family: the protocols are never pooled (fixed budget and native are separate analyses), a
    fixed-budget family is analysed at each budget level separately, and a per-instance family one instance at a time; a family over
    all instances takes every instance of one protocol and level together. Each analysis gets the campaign's run index, its sha256 and
    (through the index) its commit. ``cells`` names the cell of each analysis for the report. Rows that belong to no declared family,
    and failed runs of a cell that has no completed run, are never dropped silently: they come back in ``notes``. A refusal of the
    statistics service raises ``CampaignReportError`` naming the family and the cell."""
    completed = [(row, manifest) for row, manifest in items if manifest is not None]
    failed = [row for row, manifest in items if manifest is None]
    keyed = []
    for row, manifest in completed:
        key = comparison_cell_key(row, manifest)
        keyed.append((row, manifest, key.pooling_group, key.budget_level_index, key.dataset_identity))
    analyses: List[Any] = []
    cells: List[Dict[str, Any]] = []
    notes: List[str] = []
    used_completed: set = set()
    used_failed: set = set()
    for family in plan.families:
        try:
            allowed = {canonical_problem_contract(problem_type) for problem_type in family.problem_types}
        except ProblemContractError as exc:
            raise CampaignReportError(f"family {family.family_id!r} declares a problem type that is not a TSP/ATSP contract: {exc}") from exc
        per_instance = family.scope == "per_instance"
        groups: Dict[tuple, tuple] = {}  # (protocol, level index, instance or None) -> (completed items, failed rows)
        for position, (row, manifest, pooling, level, identity) in enumerate(keyed):
            if manifest.dataset.dataset_id not in family.dataset_ids:
                continue
            try:
                if canonical_problem_contract(manifest.dataset.problem_type) not in allowed:
                    continue
            except ProblemContractError:
                continue  # not a TSP/ATSP row: outside every family of this plan
            groups.setdefault((pooling, level, identity if per_instance else None), ([], []))[0].append((row, manifest))
            used_completed.add(position)
        for position, row in enumerate(failed):
            problem = row.get("problem")
            if not isinstance(problem, str) or not problem.strip():
                raise CampaignReportError("a failed run of the campaign has no problem name, so it belongs to no comparison cell")
            identity = normalize_problem(problem)
            dataset_id = f"tsplib-{identity}"
            recorded = row.get("dataset_id")  # the run service records the dataset id of a failed run
            if recorded is not None and recorded != dataset_id:
                raise CampaignReportError(
                    f"a failed run of {row.get('algorithm_id')!r} on {problem!r} records dataset id {recorded!r}; a failed run is placed "
                    f"in its comparison cell by the id 'tsplib-<normalised problem name>' ({dataset_id!r}), the form of every dataset "
                    "id of the analysis plans, so a failed run of another dataset form cannot be analysed"
                )
            if dataset_id not in family.dataset_ids:
                continue
            level = level_index_of(study, dataset_id, row.get("evaluation_budget"))
            if level == NOT_A_LEVEL:
                raise CampaignReportError(
                    f"a failed run of {row.get('algorithm_id')!r} on {identity!r} has evaluation budget {row.get('evaluation_budget')}, "
                    "which is not a budget level of the study profile for that instance: the campaign did not run with this profile"
                )
            pooling = FIXED_GROUP if row.get("comparison_regime") == "fixed_evaluation_budget" else NATIVE_GROUP
            key = (pooling, level, identity if per_instance else None)
            used_failed.add(position)
            if key in groups:
                groups[key][1].append(row)
            else:
                notes.append(
                    f"family {family.family_id}: no analysis for protocol {pooling}, level index {level}"
                    + (f", instance {identity}" if per_instance else "")
                    + f": a failed run of {row.get('algorithm_id')} and no completed run in that cell"
                )
        for key in sorted(groups, key=lambda k: (k[0], -1 if k[1] is None else k[1], k[2] or "")):
            members, failures = groups[key]
            budget = members[0][0].get("evaluation_budget") if per_instance else None
            cell = {"pooling_group": key[0], "budget_level_index": key[1], "evaluation_budget": budget, "dataset_identity": key[2]}
            try:
                analysis = analyse_family(
                    [*members, *((row, None) for row in failures)], study=study, plan=plan, family_id=family.family_id,
                    run_index=campaign.index, index_sha256=campaign.index_sha256,
                )
            except StatisticsRefusal as exc:
                raise CampaignReportError(
                    f"the statistics service refused family {family.family_id!r} (protocol {key[0]}, level index {key[1]}"
                    + (f", instance {key[2]}" if per_instance else "") + f"): {exc}"
                ) from exc
            analyses.append(analysis)
            cells.append(cell)
    outside = len(keyed) - len(used_completed)
    if outside:
        notes.append(f"{outside} completed row(s) belong to no comparison family of the analysis plan and have no inferential analysis")
    outside_failed = len(failed) - len(used_failed)
    if outside_failed:
        notes.append(f"{outside_failed} failed run(s) belong to no comparison family of the analysis plan and are listed only in the descriptive tables")
    if not analyses:
        raise CampaignReportError("the analysis plan declares no comparison family that has a row in this campaign: there is nothing to analyse")
    return analyses, cells, notes


def _write_from_campaign(
    output: Path, campaign: VerifiedCampaign, *, study: StudyManifestV1, plan: AnalysisPlanV1, root: Path,
    reference_table_provider: Optional[Callable[[Path], Any]],
    plan_hashes: Optional[Sequence[str]] = None,
    paper: bool = False,
) -> List[str]:
    """Build and write the report. ``plan_hashes`` are the sha256 values that count as "the analysis plan file this report loaded"
    (one for the working-tree file; the caller may offer more than one for a file read from git, see ``_plan_bytes_hashes``).
    The plan hash the run index records must be one of them: a difference refuses a paper campaign's report and is a warning in the
    report and in the returned lines for a smoke campaign. The verifier's notes (checks it could not make) are shown in both.

    ``paper=True`` (the paper report, A20 L12) needs a paper campaign and adds the inferential section: every comparison family of
    the plan is analysed (``_paper_analyses``) and the result is written as ``paper_report.txt/json``; otherwise the descriptive
    report is written as before."""
    lines: List[str] = []
    notes: List[str] = []
    for verifier_note in campaign.notes:  # a note is not a pass: it is shown, never dropped
        notes.append(verifier_note)
        lines.append(f"Note: {verifier_note}")
    recorded_hash = campaign.index.analysis_plan.sha256
    if plan_hashes is None:
        notes.append("the analysis plan file was not compared with the plan hash of the run index (the caller gave no hash)")
    elif recorded_hash not in plan_hashes:
        difference = (
            f"the analysis plan differs: the plan this report loads has sha256 {plan_hashes[0]}, the run index records "
            f"{recorded_hash if recorded_hash is not None else 'no plan hash'}"
        )
        if campaign.index.mode == "paper":
            raise CampaignReportError(difference + " (a paper report needs the plan the campaign ran with)")
        notes.append("Warning: " + difference)
        lines.append("Warning: " + difference)
    try:
        table = (reference_table_provider or default_reference_table)(root)
    except FileNotFoundError as exc:  # no reference to read: the gap is null with its reason, and the text says so
        table = ExactReferenceTable()
        note = f"exact reference unavailable ({type(exc).__name__}: {exc}); every gap is null"
        notes.append(note)
        lines.append(f"Note: {note}")
    except reference_reader.ExactReferenceRefused as exc:  # an integrity failure is never turned into null gaps
        raise CampaignReportError(f"the exact reference was refused (integrity): {exc}") from exc
    except ReferenceCrossCheckError as exc:  # the reference disagrees with the published optimum or with another set: integrity too
        raise CampaignReportError(f"the exact reference failed its cross-check (integrity): {exc}") from exc
    groups: Dict[str, List[tuple]] = {}
    for row, manifest in campaign.items:
        groups.setdefault(classify_row(row).pooling_group, []).append((row, manifest))
    items: List[tuple] = []
    try:
        for members in groups.values():
            converted = add_gap_columns([row for row, _ in members], table, plan=plan)
            items.extend((new, manifest) for new, (_, manifest) in zip(converted, members))
        items.extend((row, None) for row in campaign.failed)
        analyses: List[Any] = []
        cells: List[Dict[str, Any]] = []
        if paper:
            analyses, cells, analysis_notes = _paper_analyses(items, study=study, plan=plan, campaign=campaign)
            notes.extend(analysis_notes)
            lines.extend(f"Note: {note}" for note in analysis_notes)
        report = build_report(
            items, study=study, plan=plan, run_index=campaign.index, index_sha256=campaign.index_sha256, notes=notes,
            inference=analyses, inference_cells=cells,
        )
    except (ValueError, ReportError) as exc:  # GapColumnError, ReportError (including the wording check)
        raise CampaignReportError(str(exc)) from exc
    if paper:
        write_report(report, output, names=PAPER_REPORT_FILES)
        lines.append(
            f"Paper report: {PAPER_REPORT_TEXT_FILE} ({len(report.data['tables'])} table(s), {len(analyses)} analysis result(s), "
            f"index sha256 {campaign.index_sha256})"
        )
        return lines
    write_report(report, output)
    lines.append(f"Descriptive report: {REPORT_TEXT_FILE} ({len(report.data['tables'])} table(s), index sha256 {campaign.index_sha256})")
    return lines


def write_smoke_descriptive_report(
    output: str | Path,
    *,
    study: StudyManifestV1,
    plan: Optional[AnalysisPlanV1],
    plan_problem: Optional[str],
    root: Path,
    run_index: Optional[Mapping[str, Any]],
    reference_table_provider: Optional[Callable[[Path], Any]] = None,
    plan_sha256: Optional[str] = None,
) -> List[str]:
    """Write the descriptive report of the smoke campaign in ``output``; returns the lines to append to the run report text.

    ``plan_sha256`` is the hash of the analysis plan file the caller loaded (``AnalysisPlanResolution.sha256``); it is compared with
    the plan hash of the run index (a difference is a warning in smoke mode and a refusal in paper mode). Without it the report
    says that the plan file was not compared.

    ``run_index`` is the summary the smoke run itself returned (``SmokeReport.run_index``: ``path``, ``sha256``, ``manifests``) or
    ``None`` when it wrote no manifests (unknown git state); whether manifests exist is taken from it, never from the files on disk.
    The campaign folder is verified (``load_verified_campaign``) and the index checksum must equal the one the run reported; any
    difference raises ``CampaignReportError``. Nothing is written, and the returned lines say so, when there are no run manifests or the
    analysis plan does not resolve. The exact reference is read with ``reference_table_provider(root)`` (default
    ``default_reference_table``): ``FileNotFoundError`` means unavailable (null gaps, noted in the report and in the returned lines),
    ``ExactReferenceRefused`` refuses the report."""
    output = Path(output)
    if run_index is None:
        return ["Descriptive report not written: there are no run manifests (the git state is unknown), so rows have no comparison identity."]
    if plan is None:
        return [f"Descriptive report not written: the analysis plan does not resolve ({plan_problem})."]
    try:
        campaign = load_verified_campaign(output, repository_root=root)
    except ManifestError as exc:
        raise CampaignReportError(str(exc)) from exc
    if campaign.index_sha256 != run_index.get("sha256"):
        raise CampaignReportError(
            f"the run index on disk has sha256 {campaign.index_sha256}, the smoke run reported {run_index.get('sha256')}: the folder changed after the run"
        )
    return _write_from_campaign(
        output, campaign, study=study, plan=plan, root=root, reference_table_provider=reference_table_provider,
        plan_hashes=None if plan_sha256 is None else (plan_sha256,),
    )


def _plan_bytes_hashes(plan_bytes: bytes) -> tuple:
    """The sha256 values that count as "this plan (or profile) file" for bytes read from git: the bytes as they are, with LF line endings and with
    CRLF line endings. The run service hashed the working-tree file, and a checkout with ``core.autocrlf`` holds the same committed
    blob with other line endings (the known G1 caveat); nothing else is tolerated."""
    lf = plan_bytes.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    hashes = [hashlib.sha256(variant).hexdigest() for variant in (plan_bytes, lf, crlf)]
    return tuple(dict.fromkeys(hashes))


def _rebuild(
    campaign_dir: str | Path, study_path: Optional[str], root: Path, reference_table_provider: Optional[Callable[[Path], Any]],
    paper: bool = False,
) -> tuple:
    """``(lines, run status)`` of a rebuilt report; ``paper=True`` builds the paper report (``--paper``, A20 L12) instead of the
    descriptive one and accepts only a paper campaign."""
    from academic_benchmark.studies.service import StudyServiceError  # local import, like the others below
    from academic_benchmark.fair_pilot import _is_within  # local imports: the run service imports this module
    from academic_benchmark.studies.run import _main_working_tree
    from academic_benchmark.studies.service import ANALYSIS_PLAN_FILENAME, load_study_bytes, resolve_analysis_plan_bytes

    output = Path(campaign_dir).expanduser().resolve()
    if not output.is_dir():
        raise CampaignReportError(f"{output} is not a campaign folder")
    main_tree = _main_working_tree(root)
    if _is_within(output, root) or (main_tree is not None and _is_within(output, main_tree)):
        raise CampaignReportError(f"the campaign folder {output} is inside the repository; reports are rebuilt only for output outside it")
    # only now, after every folder check passed (a folder inside the repository is refused above without touching anything): a refused
    # rebuild of a campaign folder must not leave an old report next to a campaign it no longer describes
    for name in (PAPER_REPORT_FILES if paper else DESCRIPTIVE_REPORT_FILES):
        (output / name).unlink(missing_ok=True)
    try:
        campaign = load_verified_campaign(output, repository_root=root)
    except ManifestError as exc:
        raise CampaignReportError(str(exc)) from exc
    if paper:
        if campaign.index.mode != "paper":
            raise CampaignReportError(
                f"--paper builds the paper report of a paper campaign; this run index records mode {campaign.index.mode!r} "
                "(smoke runs support no inferential claim)"
            )
        if campaign.index.git.dirty:
            raise CampaignReportError("the run index records a dirty working tree: a paper report needs one clean commit")
    # both files as they were when the campaign ran (git at the campaign's commit), not the working-tree files, which may have moved on;
    # the paths default to the ones the run index recorded (the plan lies next to the profile when the index recorded none)
    index = campaign.index
    commit = index.git.commit
    relative = study_path or index.profile.path
    plan_name = (
        index.analysis_plan.path if study_path is None and index.analysis_plan.path is not None
        else (PurePosixPath(relative).parent / ANALYSIS_PLAN_FILENAME).as_posix()
    )

    def committed(name: str, what: str) -> bytes:
        try:
            return run_git(["show", f"{commit}:{name}"], root)
        except GitQueryFailed as exc:
            raise CampaignReportError(
                f"the {what} {name} at the campaign commit {commit[:12]} cannot be read from git in {root} ({exc}); "
                f"the rebuild reads the {what} as it was when the campaign ran, so there is nothing to build the report from"
            ) from exc

    plan_bytes = committed(plan_name, "analysis plan")
    profile_bytes = committed(relative, "study profile")
    if index.profile.sha256 not in _plan_bytes_hashes(profile_bytes):  # the same line-ending rule as the plan (A20 L6)
        raise CampaignReportError(
            f"the study profile {relative} at the campaign commit {commit[:12]} has sha256 {_plan_bytes_hashes(profile_bytes)[0]}, the run "
            f"index records {index.profile.sha256}: the campaign did not run with the committed profile, so it cannot be rebuilt from it"
        )
    study = load_study_bytes(profile_bytes, relative)
    if paper and study.status != "active":
        raise CampaignReportError(f"the study profile {relative} at the campaign commit has status {study.status!r}; a paper report needs an active profile")
    try:
        resolution = resolve_analysis_plan_bytes(study, plan_name, plan_bytes, repository_root=root, mode="paper" if paper else "smoke")
    except StudyServiceError as exc:  # paper mode: an analysis plan that does not resolve or is not active
        raise CampaignReportError(str(exc)) from exc
    if resolution.plan is None:
        raise CampaignReportError(
            f"the analysis plan at the campaign commit {commit[:12]} does not resolve ({resolution.problem}); there is nothing to build the report from"
        )
    lines = _write_from_campaign(
        output, campaign, study=study, plan=resolution.plan, root=root, reference_table_provider=reference_table_provider,
        plan_hashes=_plan_bytes_hashes(plan_bytes), paper=paper,
    )
    return lines, campaign.index.status


def rebuild_descriptive_report(
    campaign_dir: str | Path,
    study_path: Optional[str] = None,
    *,
    repository_root: Optional[Path] = None,
    reference_table_provider: Optional[Callable[[Path], Any]] = None,
) -> List[str]:
    """Build ``descriptive_report.txt/json`` again from an existing campaign folder; returns the report lines.

    ``study_path`` is repository-relative (default: the run index's ``profile.path``). Refuses a folder
    inside the repository, a folder that does not verify and a reference that fails its integrity checks (``CampaignReportError``);
    any old descriptive report in the folder is removed first."""
    root = (Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[2]).resolve()
    return _rebuild(campaign_dir, study_path, root, reference_table_provider)[0]


def rebuild_paper_report(
    campaign_dir: str | Path,
    study_path: Optional[str] = None,
    *,
    repository_root: Optional[Path] = None,
    reference_table_provider: Optional[Callable[[Path], Any]] = None,
) -> List[str]:
    """Build ``paper_report.txt/json`` from a finished, verified, clean paper campaign; returns the report lines.

    Same arguments and refusals as ``rebuild_descriptive_report`` (``CampaignReportError``), plus: a campaign whose run index is not
    a paper campaign, a dirty one, a profile or plan that is not active, and any refusal of the statistics service. Any old paper
    report in the folder is removed first."""
    root = (Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[2]).resolve()
    return _rebuild(campaign_dir, study_path, root, reference_table_provider, paper=True)[0]


def main(argv: Optional[Sequence[str]] = None) -> int:
    from academic_benchmark.studies.service import StudyServiceError

    parser = argparse.ArgumentParser(
        description="Rebuild the descriptive report, or with --paper the paper report, of an existing campaign folder (Gate D, D-07; A20 L12)"
    )
    parser.add_argument("campaign_dir", help="campaign output directory (holds run_index.json), outside the repository")
    parser.add_argument("--study", default=None, help="repository-relative study.json (default: the run index's profile.path)")
    parser.add_argument(
        "--paper", action="store_true",
        help="build paper_report.txt/json (descriptive tables plus the inferential section) from a finished, verified paper campaign",
    )
    parser.add_argument("--repository-root", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = (Path(args.repository_root) if args.repository_root else Path(__file__).resolve().parents[2]).resolve()
    try:
        lines, status = _rebuild(args.campaign_dir, args.study, root, None, paper=args.paper)
    except (CampaignReportError, StudyServiceError, AnalysisEnvironmentError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0 if status == "passed" else 1


__all__ = [
    "CampaignReportError", "default_reference_table", "main", "rebuild_descriptive_report", "rebuild_paper_report",
    "write_smoke_descriptive_report",
]

if __name__ == "__main__":
    sys.exit(main())
