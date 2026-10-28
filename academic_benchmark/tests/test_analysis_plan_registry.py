"""D-09: analysis-plan registry (``analysis_plan_id`` resolves to a committed, schema-valid plan).

Owner answers encoded by the committed plans (DECISION_LOG A18): OQ-5 a) per instance Kruskal-Wallis
then pairwise Mann-Whitney U with Holm only after a significant omnibus test, across instances
Friedman then Wilcoxon with Holm, alpha 0.05, effect sizes A12 / epsilon-squared / Kendall's W;
OQ-6 a) relative gap to the exact reference (%), per-instance median as the matched unit; OQ-8 a)
TSP-only cross-instance family, ft53 per instance only; OQ-9 a) failed runs recorded, cell excluded
from inference and reported; OQ-15 a) n, median, IQR, min, max, mean, sample SD (n-1).

Values that wait for the D-04b1 timing table are not in the plan; they stay listed as unresolved
and the plans stay ``draft``, so paper mode refuses them.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_benchmark.contracts import StudyManifestV1
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.contracts.export_schemas import MODELS, check_schemas, render_schemas
from academic_benchmark.studies import StudyServiceError, load_study
from academic_benchmark.studies.service import load_study_with_plan

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STUDIES = ("bildiri2026", "yaem2026")
PLAN_IDS = {"bildiri2026": "bildiri2026-reproduction-v1", "yaem2026": "yaem2026-draft-v1"}
BILDIRI_TSP = {
    "tsplib-berlin52", "tsplib-eil51", "tsplib-st70", "tsplib-kroa100", "tsplib-rd100", "tsplib-eil76",
}
YAEM_TSP = {"tsplib-berlin52", "tsplib-eil51", "tsplib-st70", "tsplib-kroa100"}


def _study_rel(study: str) -> str:
    return f"academic_benchmark/studies/{study}/study.json"


def _plan_path(study: str, root: Path = REPOSITORY_ROOT) -> Path:
    return root / "academic_benchmark" / "studies" / study / "analysis_plan.json"


def _plan_payload(study: str) -> dict:
    return json.loads(_plan_path(study).read_text(encoding="utf-8"))


def _family(plan: dict, scope: str) -> dict:
    found = [f for f in plan["families"] if f["scope"] == scope]
    assert len(found) == 1
    return found[0]


def _tmp_repo(tmp_path: Path, study: str, mutate=None, *, drop_plan: bool = False) -> Path:
    """Copy one study profile, its dataset manifests and (mutated) plan into a temporary repository."""
    root = tmp_path / "repo"
    study_dir = root / "academic_benchmark" / "studies" / study
    study_dir.mkdir(parents=True)
    shutil.copy(REPOSITORY_ROOT / _study_rel(study), study_dir / "study.json")
    profile = json.loads((study_dir / "study.json").read_text(encoding="utf-8"))
    for ref in profile["dataset_manifest_refs"]:
        target = root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPOSITORY_ROOT / ref, target)
    if not drop_plan:
        plan = _plan_payload(study)
        if mutate is not None:
            mutate(plan)
        _plan_path(study, root).write_text(json.dumps(plan), encoding="utf-8")
    return root


def _make_active(plan: dict) -> None:
    """A fully resolved plan as a test fixture (the value of ``minimum_n_per_cell`` is not an answer)."""
    plan["status"] = "active"
    plan["unresolved"] = []
    plan["minimum_n_per_cell"] = 5


# ---- the committed plans --------------------------------------------------------------------


@pytest.mark.parametrize("study", STUDIES)
def test_committed_plan_exists_validates_and_matches_the_profile(study):
    plan = AnalysisPlanV1.model_validate(_plan_payload(study))
    profile = StudyManifestV1.model_validate(
        json.loads((REPOSITORY_ROOT / _study_rel(study)).read_text(encoding="utf-8"))
    )
    assert plan.analysis_plan_id == profile.analysis_plan_id == PLAN_IDS[study]
    assert plan.study_id == profile.study_id == study


@pytest.mark.parametrize("study", STUDIES)
def test_committed_plans_encode_the_owner_answers(study):
    plan = _plan_payload(study)
    assert plan["alpha"] == 0.05
    assert plan["response"] == {"variable": "relative_gap_to_exact_reference", "unit": "percent"}
    assert plan["matched_unit"] == {"per": "instance", "summary": "median", "over": "replicates"}

    per_instance = _family(plan, "per_instance")
    assert per_instance["omnibus"] == {"test": "kruskal_wallis", "effect_size": "epsilon_squared"}
    assert per_instance["post_hoc"] == {
        "test": "mann_whitney_u",
        "rule": "only_after_significant_omnibus",
        "correction": "holm",
        "effect_size": "vargha_delaney_a12",
    }

    across = _family(plan, "across_instances")
    assert across["omnibus"] == {"test": "friedman", "effect_size": "kendalls_w"}
    assert across["post_hoc"] == {
        "test": "wilcoxon_signed_rank",
        "rule": "only_after_significant_omnibus",
        "correction": "holm",
        "effect_size": "matched_pairs_rank_biserial",
    }
    assert across["problem_types"] == ["TSP"]  # OQ-8 a)

    assert plan["descriptive"]["columns"] == ["n", "median", "iqr", "min", "max", "mean", "sd"]
    assert plan["descriptive"]["sd_convention"] == "sample_n_minus_1"
    assert plan["descriptive"]["quantile_method"] == "hyndman_fan_type_7"  # IQR: Q1, Q3 by linear interpolation

    assert plan["failure_policy"] == {
        "on_failed_run": "record_and_continue",
        "inference": "exclude_cell",
        "reporting": "report_exclusions",
    }
    assert plan["exact_reference"]["reader"] == "exact_reference_v1"
    assert plan["exact_reference"]["pooling"] == "reference_only"


def test_family_instance_sets_follow_oq8():
    bildiri = _plan_payload("bildiri2026")
    assert set(_family(bildiri, "across_instances")["dataset_ids"]) == BILDIRI_TSP
    assert set(_family(bildiri, "per_instance")["dataset_ids"]) == BILDIRI_TSP | {"tsplib-ft53"}
    yaem = _plan_payload("yaem2026")
    assert set(_family(yaem, "across_instances")["dataset_ids"]) == YAEM_TSP
    assert set(_family(yaem, "per_instance")["dataset_ids"]) == YAEM_TSP


@pytest.mark.parametrize("study", STUDIES)
def test_committed_plans_stay_draft_but_are_fully_resolved(study):
    # Owner 2026-10-28: minimum_n_per_cell = 30 (complete cells only) and the answered items left `unresolved`;
    # status stays draft until the D-10 approval commit.
    plan = AnalysisPlanV1.model_validate(_plan_payload(study))
    assert plan.status == "draft"
    assert plan.minimum_n_per_cell == 30
    assert plan.unresolved == []


@pytest.mark.parametrize("study", STUDIES)
def test_committed_plans_would_validate_as_active_without_being_active(study):
    payload = _plan_payload(study)
    assert payload["status"] == "draft"  # the committed file is not activated
    payload["status"] = "active"  # a scratch copy only: the contract accepts the resolved plan as activatable
    assert AnalysisPlanV1.model_validate(payload).status == "active"


# ---- schema validation ------------------------------------------------------------------------


def test_plan_with_an_unknown_test_name_fails_validation():
    for scope, path in (("per_instance", "omnibus"), ("per_instance", "post_hoc"), ("across_instances", "omnibus")):
        payload = _plan_payload("bildiri2026")
        _family(payload, scope)[path]["test"] = "anova_with_a_typo"
        with pytest.raises(ValidationError):
            AnalysisPlanV1.model_validate(payload)


@pytest.mark.parametrize("alpha", [None, 0, 1, 1.5, -0.05])
def test_plan_needs_an_alpha_inside_the_open_unit_interval(alpha):
    payload = _plan_payload("bildiri2026")
    if alpha is None:
        del payload["alpha"]
    else:
        payload["alpha"] = alpha
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)


def test_plan_without_a_column_list_fails_validation():
    payload = _plan_payload("bildiri2026")
    del payload["descriptive"]["columns"]
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)
    payload = _plan_payload("bildiri2026")
    payload["descriptive"]["columns"] = []
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)


def test_plan_without_a_post_hoc_rule_fails_validation():
    """The code has no default for the post-hoc rule (OQ-5): the plan must state it."""
    payload = _plan_payload("bildiri2026")
    del _family(payload, "per_instance")["post_hoc"]["rule"]
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)


def test_plan_rejects_unknown_fields_and_wrong_schema_version():
    payload = _plan_payload("bildiri2026")
    payload["surprise"] = 1
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AnalysisPlanV1.model_validate(payload)
    payload = _plan_payload("bildiri2026")
    payload["schema_version"] = "uniride-analysis-plan/v2"
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)


def test_cross_instance_family_may_not_contain_atsp():
    payload = _plan_payload("bildiri2026")
    _family(payload, "across_instances")["problem_types"] = ["TSP", "ATSP"]
    with pytest.raises(ValidationError, match="TSP"):
        AnalysisPlanV1.model_validate(payload)


def test_independent_and_matched_tests_may_not_be_swapped_between_scopes():
    payload = _plan_payload("bildiri2026")
    _family(payload, "per_instance")["omnibus"] = {"test": "friedman", "effect_size": "kendalls_w"}
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)


def test_active_plan_must_have_nothing_unresolved_and_a_minimum_n():
    payload = _plan_payload("bildiri2026")
    payload["status"] = "active"
    # the committed plan is now resolved, so the unresolved state is built here (reason: the old test relied on it)
    payload["unresolved"] = [{"field": "run_count", "pending": "fixture: a value still waiting for a decision"}]
    with pytest.raises(ValidationError, match="unresolved"):
        AnalysisPlanV1.model_validate(payload)
    _make_active(payload)
    payload["minimum_n_per_cell"] = None
    with pytest.raises(ValidationError, match="minimum_n_per_cell"):
        AnalysisPlanV1.model_validate(payload)


def test_a_missing_minimum_n_must_be_declared_unresolved():
    payload = _plan_payload("bildiri2026")
    payload["minimum_n_per_cell"] = None  # the committed plan now sets it (30); the missing state is built here
    payload["unresolved"] = []
    with pytest.raises(ValidationError, match="minimum_n_per_cell"):
        AnalysisPlanV1.model_validate(payload)


# ---- resolution through the study loader --------------------------------------------------------


@pytest.mark.parametrize("study", STUDIES)
def test_committed_profiles_resolve_in_smoke_mode_and_are_labelled_draft(study):
    loaded = load_study_with_plan(_study_rel(study), repository_root=REPOSITORY_ROOT, mode="smoke")
    resolution = loaded.analysis_plan
    assert resolution.plan is not None and resolution.plan.analysis_plan_id == PLAN_IDS[study]
    assert resolution.problem is None
    assert "draft" in resolution.label and "no inference" in resolution.label


@pytest.mark.parametrize("study", STUDIES)
def test_paper_mode_refuses_the_draft_plans(study):
    with pytest.raises(StudyServiceError, match="draft"):
        load_study(_study_rel(study), repository_root=REPOSITORY_ROOT, mode="paper")


def test_load_study_without_a_mode_keeps_its_previous_behaviour():
    study = load_study(_study_rel("bildiri2026"), repository_root=REPOSITORY_ROOT)
    assert study.study_id == "bildiri2026"


def test_unknown_plan_id_is_refused_in_paper_mode_and_labelled_in_smoke_mode(tmp_path):
    root = _tmp_repo(tmp_path, "bildiri2026", drop_plan=True)
    path = _study_rel("bildiri2026")
    with pytest.raises(StudyServiceError, match="analysis plan"):
        load_study(path, repository_root=root, mode="paper")
    loaded = load_study_with_plan(path, repository_root=root, mode="smoke")
    assert loaded.analysis_plan.plan is None
    assert "unresolved" in loaded.analysis_plan.label
    assert "bildiri2026-reproduction-v1" in loaded.analysis_plan.label
    assert loaded.study.study_id == "bildiri2026"


def test_plan_file_with_another_plan_id_does_not_resolve(tmp_path):
    root = _tmp_repo(tmp_path, "bildiri2026", lambda p: p.update(analysis_plan_id="some-other-plan-v1"))
    path = _study_rel("bildiri2026")
    with pytest.raises(StudyServiceError, match="some-other-plan-v1"):
        load_study(path, repository_root=root, mode="paper")
    loaded = load_study_with_plan(path, repository_root=root, mode="smoke")
    assert loaded.analysis_plan.plan is None and "unresolved" in loaded.analysis_plan.label


def test_plan_of_another_study_is_refused(tmp_path):
    root = _tmp_repo(tmp_path, "bildiri2026", lambda p: p.update(study_id="yaem2026"))
    path = _study_rel("bildiri2026")
    with pytest.raises(StudyServiceError, match="study_id"):
        load_study(path, repository_root=root, mode="paper")
    loaded = load_study_with_plan(path, repository_root=root, mode="smoke")
    assert loaded.analysis_plan.plan is None and "study_id" in loaded.analysis_plan.problem


def test_schema_invalid_plan_file_is_refused_in_paper_mode_and_labelled_in_smoke_mode(tmp_path):
    root = _tmp_repo(tmp_path, "bildiri2026", lambda p: p.pop("alpha"))
    path = _study_rel("bildiri2026")
    with pytest.raises(StudyServiceError, match="invalid"):
        load_study(path, repository_root=root, mode="paper")
    loaded = load_study_with_plan(path, repository_root=root, mode="smoke")
    assert loaded.analysis_plan.plan is None
    assert "invalid" in loaded.analysis_plan.label


def test_unreadable_plan_file_is_refused(tmp_path):
    root = _tmp_repo(tmp_path, "bildiri2026")
    _plan_path("bildiri2026", root).write_text("{not json", encoding="utf-8")
    with pytest.raises(StudyServiceError, match="analysis plan"):
        load_study(_study_rel("bildiri2026"), repository_root=root, mode="paper")


def test_resolved_active_plan_loads_in_paper_mode(tmp_path):
    root = _tmp_repo(tmp_path, "bildiri2026", _make_active)
    loaded = load_study_with_plan(_study_rel("bildiri2026"), repository_root=root, mode="paper")
    assert loaded.analysis_plan.plan.status == "active"
    assert loaded.analysis_plan.label == "analysis plan bildiri2026-reproduction-v1 (active)"
    assert load_study(_study_rel("bildiri2026"), repository_root=root, mode="paper").study_id == "bildiri2026"


def test_plan_naming_a_dataset_outside_the_study_is_refused(tmp_path):
    def mutate(plan):
        _make_active(plan)
        _family(plan, "per_instance")["dataset_ids"].append("tsplib-not-in-this-study")

    root = _tmp_repo(tmp_path, "bildiri2026", mutate)
    with pytest.raises(StudyServiceError, match="tsplib-not-in-this-study"):
        load_study(_study_rel("bildiri2026"), repository_root=root, mode="paper")


def test_atsp_dataset_in_the_cross_instance_family_is_refused_against_the_manifests(tmp_path):
    """OQ-8 a): ft53 (ATSP per its dataset manifest) is analysed per instance only."""

    def mutate(plan):
        _make_active(plan)
        _family(plan, "across_instances")["dataset_ids"].append("tsplib-ft53")

    root = _tmp_repo(tmp_path, "bildiri2026", mutate)
    with pytest.raises(StudyServiceError, match="tsplib-ft53"):
        load_study(_study_rel("bildiri2026"), repository_root=root, mode="paper")
    loaded = load_study_with_plan(_study_rel("bildiri2026"), repository_root=root, mode="smoke")
    assert loaded.analysis_plan.plan is None and "tsplib-ft53" in loaded.analysis_plan.problem


def test_unknown_mode_is_refused():
    with pytest.raises(StudyServiceError, match="mode"):
        load_study(_study_rel("bildiri2026"), repository_root=REPOSITORY_ROOT, mode="turbo")


# ---- schema snapshot ------------------------------------------------------------------------------


def test_analysis_plan_schema_snapshot_is_registered_and_current():
    assert MODELS["analysis-plan-v1.schema.json"] is AnalysisPlanV1
    assert check_schemas() == []
    schema = json.loads(render_schemas()["analysis-plan-v1.schema.json"])
    assert schema["properties"]["schema_version"]["const"] == "uniride-analysis-plan/v1"
    assert schema["additionalProperties"] is False


# ---- review answers (A18, D-09 review): quantile method and effect-size pairing --------------------


def test_plan_without_a_quantile_method_fails_validation():
    """The IQR method is stated by the plan, never defaulted by code."""
    payload = _plan_payload("bildiri2026")
    del payload["descriptive"]["quantile_method"]
    with pytest.raises(ValidationError, match="quantile_method"):
        AnalysisPlanV1.model_validate(payload)
    payload = _plan_payload("bildiri2026")
    payload["descriptive"]["quantile_method"] = "nearest_rank"
    with pytest.raises(ValidationError):
        AnalysisPlanV1.model_validate(payload)


def test_paired_wilcoxon_post_hoc_rejects_a12():
    payload = _plan_payload("bildiri2026")
    _family(payload, "across_instances")["post_hoc"]["effect_size"] = "vargha_delaney_a12"
    with pytest.raises(ValidationError, match="rank_biserial"):
        AnalysisPlanV1.model_validate(payload)


def test_independent_mann_whitney_post_hoc_rejects_a_paired_measure():
    payload = _plan_payload("bildiri2026")
    _family(payload, "per_instance")["post_hoc"]["effect_size"] = "matched_pairs_rank_biserial"
    with pytest.raises(ValidationError, match="vargha_delaney_a12"):
        AnalysisPlanV1.model_validate(payload)
