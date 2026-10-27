"""The failed-run check of ``analyse_family`` is scoped to the analysed budget level (run-index polish 3 and 4).

A failure the verified index lists at another budget level than the analysed one is not a row of this analysis and must not be
demanded; a failure listed at the analysed level that the rows drop still is (D-05 follow-up, D-10 G7).
"""
from __future__ import annotations

import pytest

import academic_benchmark.tests.analysis_fixtures as ts
from academic_benchmark.analysis.statistics import StatisticsRefusal
from academic_benchmark.studies.service import load_study_with_plan

pytestmark = pytest.mark.requires_analysis_extra  # every test runs analyse_family (SciPy / statsmodels guard)


@pytest.fixture(scope="module")
def active():
    loaded = load_study_with_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=ts.REPO, mode="smoke")
    return ts.activate(loaded.analysis_plan.plan)


def _other_level(problem, algorithm="Core-GA-TSP", replicate=0):
    return ts.failed_item(problem, algorithm, replicate, evaluation_budget=ts._levels(problem)[1])


# ------------------------------------------------------------------------------------------------ polish 3
def test_a_failure_at_another_level_of_an_instance_without_rows_is_not_demanded(active):
    """rd100 has no row at the analysed level; its failure listed at level 1 is not a row of this analysis."""
    present = [name for name in ts.CROSS_INSTANCES if name != "rd100"]
    items = ts.cross_items(problems=present)
    result = ts.run(items, active, ts.ACROSS, mode="smoke", failed=[_other_level("rd100")])
    assert result.inference is None  # smoke: descriptive only, and the instance is reported as having no rows
    assert any(e["dataset_identity"] == "rd100" and e["algorithm_id"] is None for e in result.exclusions)


def test_a_failure_the_rows_do_list_for_an_instance_without_completed_rows_is_still_checked(active):
    """The level of an instance with no completed row comes from the failed rows given for it: a dropped failure at that level is
    demanded, one at the other level is not."""
    present = [name for name in ts.CROSS_INSTANCES if name != "rd100"]
    items = ts.cross_items(problems=present) + [ts.failed_item("rd100", "Core-GA-TSP", 0)]
    ts.run(items, active, ts.ACROSS, mode="smoke", failed=[ts.failed_item("rd100", "Core-GA-TSP", 0), _other_level("rd100", replicate=1)])
    with pytest.raises(StatisticsRefusal, match="missing from the rows"):
        ts.run(items, active, ts.ACROSS, mode="smoke",
               failed=[ts.failed_item("rd100", "Core-GA-TSP", 0), ts.failed_item("rd100", "Core-PSO-TSP", 3)])


# ------------------------------------------------------------------------------------------------ polish 4: budget filter
def test_a_failure_at_another_level_on_the_analysed_instance_is_not_demanded(active):
    items = ts.per_instance_items(ts.SEPARATED)  # eil51, level 0
    ts.run(items, active, study=ts.STUDY3, failed=[_other_level("eil51", "Core-PSO-TSP")])


def test_a_failure_at_the_analysed_level_that_the_rows_drop_is_demanded(active):
    items = ts.per_instance_items(ts.SEPARATED)
    with pytest.raises(StatisticsRefusal, match="missing from the rows"):
        ts.run(items, active, study=ts.STUDY3, failed=[ts.failed_item("eil51", "Core-PSO-TSP", 0)])


# ------------------------------------------------------------------------------------------------ gated pre-close polish 3
def test_an_index_failure_whose_budget_is_no_level_of_the_profile_is_refused_not_skipped(active):
    """The index lists a failure whose budget is in no level list of the profile: the analysed study is not the campaign's profile."""
    items = ts.per_instance_items(ts.SEPARATED)
    with pytest.raises(StatisticsRefusal, match="not a budget level of the study profile"):
        ts.run(items, active, study=ts.STUDY3, failed=[ts.failed_item("eil51", "Core-PSO-TSP", 0, evaluation_budget=987_654_321)])
