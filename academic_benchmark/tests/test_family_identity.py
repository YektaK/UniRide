"""A paper report quotes only an analysis computed from the campaign it reports (A18 D-07 lead decision, precondition for wiring the
paper report into the paper run service).

``FamilyAnalysis`` carries the campaign identity it was computed from (the sha256 of ``run_index.json`` and the campaign commit);
the report compares it with the banner's verified index and refuses in paper mode when it differs or is unknown.
"""
from __future__ import annotations

import dataclasses
import json

import pytest

import test_analysis_report as tar
import test_analysis_statistics as fx
from academic_benchmark.analysis.report import ReportError
from academic_benchmark.analysis.statistics import analyse_family

plans, draft, active = tar.plans, tar.draft, tar.active  # the module fixtures of the report tests

INDEX_SHA = tar.SHA  # the sha256 ``tar._report`` gives the report as its verified index


def _analysis(active, *, index_sha256=INDEX_SHA):
    items = fx.per_instance_items(fx.SEPARATED)
    for row, _ in items:
        row.setdefault("objective_evaluations", row["evaluation_budget"])
        row.setdefault("termination_reason", "budget_exhausted")
    analysis = analyse_family(items, study=fx.study_for(items, active), plan=active, family_id=fx.PER_INSTANCE,
                              run_index=fx.index_for(items, "paper"), index_sha256=index_sha256)  # None is passed explicitly where a test needs it
    return items, analysis


def test_the_analysis_carries_the_run_index_sha256_and_the_campaign_commit(active):
    _items, analysis = _analysis(active)
    assert analysis.index_sha256 == INDEX_SHA
    assert analysis.campaign_commit == fx.COMMIT


def test_a_paper_report_accepts_an_analysis_of_its_own_campaign_and_names_the_identity(active):
    items, analysis = _analysis(active)
    report = tar._report(items, plan=active, mode="paper", inference=[analysis])
    section = report.data["inference"][0]
    assert section["index_sha256"] == INDEX_SHA and section["campaign_commit"] == fx.COMMIT
    assert report.data["banner"]["manifest_index_sha256"] == INDEX_SHA
    json.dumps(report.data)


def test_a_paper_report_refuses_an_analysis_computed_from_another_run_index(active):
    items, analysis = _analysis(active, index_sha256="d" * 64)
    with pytest.raises(ReportError, match="run index"):
        tar._report(items, plan=active, mode="paper", inference=[analysis])


def test_a_paper_report_refuses_an_analysis_of_another_campaign_commit(active):
    items, analysis = _analysis(active)
    other_commit = dataclasses.replace(analysis, campaign_commit="b" * 40)
    with pytest.raises(ReportError, match="commit"):
        tar._report(items, plan=active, mode="paper", inference=[other_commit])


def test_a_paper_report_refuses_an_analysis_that_does_not_know_its_campaign(active):
    items, analysis = _analysis(active, index_sha256=None)
    assert analysis.index_sha256 is None
    with pytest.raises(ReportError, match="run index"):
        tar._report(items, plan=active, mode="paper", inference=[analysis])
