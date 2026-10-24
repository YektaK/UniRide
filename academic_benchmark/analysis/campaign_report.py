"""Descriptive report of a written smoke campaign (Gate D, D-07), the analysis-layer glue behind ``studies.run``.

The gap columns come from the exact reference (``analysis.gaps``) and the rows are classified by ``protocol_registry``; both are
analysis-layer concerns, and the E12/D-06 boundary tests keep them out of the study modules (``studies/*.py``). The run service
therefore calls this one function and imports neither: it verifies the campaign folder, adds the gap columns, builds the report
(``analysis.report``) and writes ``descriptive_report.txt/json`` next to the campaign.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from academic_benchmark.analysis.gaps import ExactReferenceTable, add_gap_columns, load_reference_table
from academic_benchmark.analysis.manifests import INDEX_FILE, ManifestError, load_verified_campaign
from academic_benchmark.analysis.report import REPORT_TEXT_FILE, ReportError, build_report, write_report
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.contracts.study import StudyManifestV1
from academic_benchmark.protocol_registry import classify_row


class CampaignReportError(ValueError):
    """The campaign folder does not verify, a gap cannot be computed without a silent choice, or the report was refused."""


def write_smoke_descriptive_report(
    output: str | Path,
    *,
    study: StudyManifestV1,
    plan: Optional[AnalysisPlanV1],
    plan_problem: Optional[str],
    root: Path,
    reference_table_provider: Optional[Callable[[Path], Any]] = None,
) -> List[str]:
    """Write the descriptive report of the smoke campaign in ``output``; returns the lines to append to the run report text.

    The campaign is verified first (``load_verified_campaign``); a campaign that does not verify raises ``CampaignReportError``.
    The gap column comes from the exact reference table (``reference_table_provider(root)``, default ``load_reference_table``);
    when the table cannot be loaded every gap is ``null`` with its reason and the report says why. Nothing is written, and the
    returned lines say so, when there are no run manifests (unknown git state) or the analysis plan does not resolve."""
    output = Path(output)
    if not (output / INDEX_FILE).is_file():
        return ["Descriptive report not written: there are no run manifests (the git state is unknown), so rows have no comparison identity."]
    if plan is None:
        return [f"Descriptive report not written: the analysis plan does not resolve ({plan_problem})."]
    try:
        campaign = load_verified_campaign(output)
    except ManifestError as exc:
        raise CampaignReportError(str(exc)) from exc
    notes: List[str] = []
    try:
        table = (reference_table_provider or load_reference_table)(root)
    except Exception as exc:  # noqa: BLE001 - the reference is optional for a smoke report; the reason is printed, never hidden
        table = ExactReferenceTable()
        notes.append(f"exact reference unavailable ({type(exc).__name__}: {exc}); every gap is null")
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
    return [f"Descriptive report: {REPORT_TEXT_FILE} ({len(report.data['tables'])} table(s), index sha256 {campaign.index_sha256})"]


__all__ = ["CampaignReportError", "write_smoke_descriptive_report"]
