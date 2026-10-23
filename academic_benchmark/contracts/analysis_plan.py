"""Analysis-plan contract ``uniride-analysis-plan/v1`` (Gate D, D-09).

An analysis plan predeclares how a study's results are analysed (design "Statistical Protocol"):
the response variable, the matched unit, the comparison families, the omnibus and post-hoc tests,
the post-hoc rule, the correction, alpha, effect sizes, the descriptive columns and the
standard-deviation convention, the failure policy and the exact-reference link. The statistics and
report code (D-05, D-07) reads these fields; it carries no defaults of its own.

Every value is an owner decision (DECISION_LOG A18, OQ-5, OQ-6, OQ-8, OQ-9, OQ-15). Values that
still wait for a decision or a measurement (for example the run count and the minimum sample size,
D-04b1) are not guessed: the plan stays ``draft`` and lists them in ``unresolved``. Paper mode
refuses a plan that is not ``active``; an ``active`` plan has nothing unresolved.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from .common import StrictContract

PlanProblemType = Literal["TSP", "ATSP"]
ID_PATTERN = r"^[a-z0-9][a-z0-9._-]*$"

# test families: independent samples (per instance) versus matched units (across instances)
INDEPENDENT_OMNIBUS = "kruskal_wallis"
INDEPENDENT_POST_HOC = "mann_whitney_u"
MATCHED_OMNIBUS = "friedman"
MATCHED_POST_HOC = "wilcoxon_signed_rank"


class UnresolvedValueV1(StrictContract):
    """A value the plan does not fix yet and the decision or measurement it waits for."""

    field: str = Field(min_length=1)
    pending: str = Field(min_length=1)


class ResponseV1(StrictContract):
    variable: Literal["relative_gap_to_exact_reference"]
    unit: Literal["percent"]


class MatchedUnitV1(StrictContract):
    """The per-instance summary that is the matched unit of the cross-instance tests."""

    per: Literal["instance"]
    summary: Literal["median"]
    over: Literal["replicates"]


class OmnibusV1(StrictContract):
    test: Literal["kruskal_wallis", "friedman"]
    effect_size: Literal["epsilon_squared", "kendalls_w"]


class PostHocV1(StrictContract):
    test: Literal["mann_whitney_u", "wilcoxon_signed_rank"]
    rule: Literal["only_after_significant_omnibus", "always_over_declared_family"]
    correction: Literal["holm"]
    effect_size: Literal["vargha_delaney_a12"]


class ComparisonFamilyV1(StrictContract):
    family_id: str = Field(min_length=1, pattern=ID_PATTERN)
    scope: Literal["per_instance", "across_instances"]
    problem_types: list[PlanProblemType] = Field(min_length=1)
    dataset_ids: list[str] = Field(min_length=1)
    # one family is always inside one comparison cell (D-01): one protocol, one budget level
    algorithm_set: Literal["all_algorithms_of_the_comparison_cell"]
    omnibus: OmnibusV1
    post_hoc: PostHocV1

    @model_validator(mode="after")
    def validate_family(self) -> "ComparisonFamilyV1":
        if len(set(self.problem_types)) != len(self.problem_types):
            raise ValueError("problem_types must be unique")
        if len(set(self.dataset_ids)) != len(self.dataset_ids):
            raise ValueError("dataset_ids must be unique")
        if self.scope == "per_instance":
            expected = (INDEPENDENT_OMNIBUS, INDEPENDENT_POST_HOC)
        else:
            expected = (MATCHED_OMNIBUS, MATCHED_POST_HOC)
            if self.problem_types != ["TSP"]:
                # OQ-8 a): the cross-instance test pools TSP instances only; ATSP is per instance
                raise ValueError("an across_instances family must have problem_types ['TSP'] only")
        if (self.omnibus.test, self.post_hoc.test) != expected:
            raise ValueError(
                f"a {self.scope} family uses the omnibus {expected[0]} and the post-hoc "
                f"{expected[1]} (independent samples per instance, matched units across instances)"
            )
        return self


class DescriptiveV1(StrictContract):
    columns: list[Literal["n", "median", "iqr", "min", "max", "mean", "sd"]] = Field(min_length=1)
    sd_convention: Literal["sample_n_minus_1", "population_n"]
    variables: list[
        Literal["cost", "gap", "evaluations_consumed", "evaluation_budget_share"]
    ] = Field(min_length=1)
    counts: list[Literal["termination_reason_counts", "failed_run_count"]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique(self) -> "DescriptiveV1":
        for name in ("columns", "variables", "counts"):
            values = getattr(self, name)
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must be unique")
        return self


class FailurePolicyV1(StrictContract):
    on_failed_run: Literal["record_and_continue", "stop_campaign", "retry_once_then_record"]
    inference: Literal["exclude_cell"]
    reporting: Literal["report_exclusions"]


class ExactReferenceLinkV1(StrictContract):
    """How the exact reference reaches the analysis (D-06): as a reference, never as pooled data."""

    reader: Literal["exact_reference_v1"]
    join_identity: Literal["normalised_tsplib_problem_name"]
    pooling: Literal["reference_only"]


class AnalysisPlanV1(StrictContract):
    model_config = StrictContract.model_config | {
        "json_schema_extra": {"$id": "uniride-analysis-plan/v1"}
    }

    schema_version: Literal["uniride-analysis-plan/v1"]
    analysis_plan_id: str = Field(min_length=1, pattern=ID_PATTERN)
    study_id: str = Field(min_length=1, pattern=ID_PATTERN)
    status: Literal["draft", "active", "archived"]
    decisions: list[str] = Field(min_length=1)
    unresolved: list[UnresolvedValueV1]
    response: ResponseV1
    matched_unit: MatchedUnitV1
    families: list[ComparisonFamilyV1] = Field(min_length=1)
    alpha: float = Field(gt=0, lt=1)
    descriptive: DescriptiveV1
    # null = not decided yet; it must then be listed in ``unresolved`` (it waits for the run count)
    minimum_n_per_cell: PositiveInt | None
    failure_policy: FailurePolicyV1
    exact_reference: ExactReferenceLinkV1

    @model_validator(mode="after")
    def validate_status_and_unresolved(self) -> "AnalysisPlanV1":
        listed = [item.field for item in self.unresolved]
        if len(set(listed)) != len(listed):
            raise ValueError("unresolved fields must be unique")
        family_ids = [family.family_id for family in self.families]
        if len(set(family_ids)) != len(family_ids):
            raise ValueError("family_id values must be unique")
        if self.minimum_n_per_cell is None and "minimum_n_per_cell" not in listed:
            raise ValueError(
                "minimum_n_per_cell is null, so it must be listed in unresolved (it is never guessed)"
            )
        if self.minimum_n_per_cell is not None and "minimum_n_per_cell" in listed:
            raise ValueError("minimum_n_per_cell is set but still listed as unresolved")
        if self.status == "active" and self.unresolved:
            raise ValueError(
                f"an active plan has nothing unresolved; still unresolved: {', '.join(listed)}"
            )
        if self.status == "active" and self.minimum_n_per_cell is None:
            raise ValueError("an active plan needs minimum_n_per_cell")
        return self
