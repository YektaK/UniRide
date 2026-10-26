"""Descriptive report of a written campaign folder (Gate D, D-07), the analysis-layer glue behind ``studies.run``.

The gap columns come from the exact reference (``analysis.gaps``) and the rows are classified by ``protocol_registry``; both are
analysis-layer concerns, and the E12/D-06 boundary tests keep them out of the study modules (``studies/*.py``). The run service
therefore calls ``write_smoke_descriptive_report`` and imports neither: it verifies the campaign folder, adds the gap columns, builds the
report (``analysis.report``) and writes ``descriptive_report.txt/json`` next to the campaign.

``rebuild_descriptive_report`` and ``python -m academic_benchmark.analysis.campaign_report <campaign dir> [--study <study.json>]`` build
the report again from an existing campaign folder (for example after a crash between the run index and the report). Exit codes as in
``studies.run``: 0 written, 1 written for a campaign whose run status is "failed", 2 refused (campaign folder inside the repository, a
folder that does not verify, an exact reference that fails its integrity checks or its cross-check with the published optima, a refused
report, an analysis plan that cannot be read from git at the campaign's commit). The rebuild reads the analysis plan as committed at the
commit the campaign recorded (``git show <commit>:<plan>``), not the working-tree file, and compares its hash with the run index.

The exact reference is optional for a descriptive report, but only in one sense: when ``results_index.json`` is absent (or lists no
TSP reference) the gap column is ``null`` with its reason and the report and the run text say so. An integrity refusal of the reference
(``ExactReferenceRefused``: checksum, manifest or validation failure) is never turned into null gaps: it refuses the report.

Descriptive reports are not covered by a checksum (like ``run_report``: the run index quotes nothing of them and they quote the index
checksum) and nothing ever reads them back as input.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from academic_benchmark.analysis.gaps import (
    ExactReferenceTable,
    ReferenceCrossCheckError,
    add_gap_columns,
    load_reference_table,
)
from academic_benchmark.committed_bytes import GitQueryFailed, run_git
from academic_benchmark.analysis.manifests import (
    DESCRIPTIVE_REPORT_FILES,
    ManifestError,
    VerifiedCampaign,
    load_verified_campaign,
)
from academic_benchmark.analysis.report import REPORT_TEXT_FILE, ReportError, build_report, write_report
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.contracts.study import StudyManifestV1
from academic_benchmark.exact_reference import reader as reference_reader
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


def _write_from_campaign(
    output: Path, campaign: VerifiedCampaign, *, study: StudyManifestV1, plan: AnalysisPlanV1, root: Path,
    reference_table_provider: Optional[Callable[[Path], Any]],
    plan_hashes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Build and write the report. ``plan_hashes`` are the sha256 values that count as "the analysis plan file this report loaded"
    (one for the working-tree file; the caller may offer more than one for a file read from git, see ``_plan_bytes_hashes``).
    The plan hash the run index records must be one of them: a difference refuses a paper campaign's report and is a warning in the
    report and in the returned lines for a smoke campaign. The verifier's notes (checks it could not make) are shown in both."""
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
        report = build_report(
            items, study=study, plan=plan, run_index=campaign.index, index_sha256=campaign.index_sha256, notes=notes,
        )
    except (ValueError, ReportError) as exc:  # GapColumnError, ReportError (including the wording check)
        raise CampaignReportError(str(exc)) from exc
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
    """The sha256 values that count as "this plan file" for bytes read from git: the bytes as they are, with LF line endings and with
    CRLF line endings. The run service hashed the working-tree file, and a checkout with ``core.autocrlf`` holds the same committed
    blob with other line endings (the known G1 caveat); nothing else is tolerated."""
    lf = plan_bytes.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    hashes = [hashlib.sha256(variant).hexdigest() for variant in (plan_bytes, lf, crlf)]
    return tuple(dict.fromkeys(hashes))


def _rebuild(
    campaign_dir: str | Path, study_path: Optional[str], root: Path, reference_table_provider: Optional[Callable[[Path], Any]],
) -> tuple:
    """``(lines, run status)`` of a rebuilt report."""
    from academic_benchmark.fair_pilot import _is_within  # local imports: the run service imports this module
    from academic_benchmark.studies.run import _main_working_tree
    from academic_benchmark.studies.service import ANALYSIS_PLAN_FILENAME, load_study, resolve_analysis_plan_bytes

    output = Path(campaign_dir).expanduser().resolve()
    if not output.is_dir():
        raise CampaignReportError(f"{output} is not a campaign folder")
    main_tree = _main_working_tree(root)
    if _is_within(output, root) or (main_tree is not None and _is_within(output, main_tree)):
        raise CampaignReportError(f"the campaign folder {output} is inside the repository; reports are rebuilt only for output outside it")
    for name in DESCRIPTIVE_REPORT_FILES:  # a refused rebuild must not leave an old report next to a campaign it no longer describes
        (output / name).unlink(missing_ok=True)
    try:
        campaign = load_verified_campaign(output, repository_root=root)
    except ManifestError as exc:
        raise CampaignReportError(str(exc)) from exc
    relative = study_path or f"academic_benchmark/studies/{campaign.index.study_id}/study.json"
    study = load_study(relative, repository_root=root)
    # the plan as it was when the campaign ran (git at the campaign's commit), not the working-tree file, which may have moved on
    commit = campaign.index.git.commit
    plan_name = (PurePosixPath(relative).parent / ANALYSIS_PLAN_FILENAME).as_posix()
    try:
        plan_bytes = run_git(["show", f"{commit}:{plan_name}"], root)
    except GitQueryFailed as exc:
        raise CampaignReportError(
            f"the analysis plan {plan_name} at the campaign commit {commit[:12]} cannot be read from git in {root} ({exc}); "
            "the rebuild reads the plan as it was when the campaign ran, so there is nothing to build the report from"
        ) from exc
    resolution = resolve_analysis_plan_bytes(study, plan_name, plan_bytes, repository_root=root, mode="smoke")
    if resolution.plan is None:
        raise CampaignReportError(
            f"the analysis plan at the campaign commit {commit[:12]} does not resolve ({resolution.problem}); there is nothing to build the report from"
        )
    lines = _write_from_campaign(
        output, campaign, study=study, plan=resolution.plan, root=root, reference_table_provider=reference_table_provider,
        plan_hashes=_plan_bytes_hashes(plan_bytes),
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

    ``study_path`` is repository-relative (default ``academic_benchmark/studies/<study id of the run index>/study.json``). Refuses a folder
    inside the repository, a folder that does not verify and a reference that fails its integrity checks (``CampaignReportError``);
    any old descriptive report in the folder is removed first."""
    root = (Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[2]).resolve()
    return _rebuild(campaign_dir, study_path, root, reference_table_provider)[0]


def main(argv: Optional[Sequence[str]] = None) -> int:
    from academic_benchmark.studies.service import StudyServiceError

    parser = argparse.ArgumentParser(description="Rebuild the descriptive report of an existing campaign folder (Gate D, D-07)")
    parser.add_argument("campaign_dir", help="campaign output directory (holds run_index.json), outside the repository")
    parser.add_argument("--study", default=None, help="repository-relative study.json (default: the run index's study folder)")
    parser.add_argument("--repository-root", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = (Path(args.repository_root) if args.repository_root else Path(__file__).resolve().parents[2]).resolve()
    try:
        lines, status = _rebuild(args.campaign_dir, args.study, root, None)
    except (CampaignReportError, StudyServiceError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0 if status == "passed" else 1


__all__ = [
    "CampaignReportError", "default_reference_table", "main", "rebuild_descriptive_report", "write_smoke_descriptive_report",
]

if __name__ == "__main__":
    sys.exit(main())
