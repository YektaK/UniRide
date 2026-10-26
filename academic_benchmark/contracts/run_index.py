"""Campaign index of run manifests (Gate D, D-02): ``uniride-run-index/v2``.

``RunManifestV1`` describes one run (one algorithm, dataset, budget level and replicate). A campaign (a smoke or paper
run of one study) writes one manifest per run plus this index, which lists every manifest with its checksum and holds
what is shared by the whole campaign: study, mode, git state, environment, base seed and the seed protocol version.
``uniride-run/v1`` has no seed-protocol field and is not changed (a schema change is a new version, design
"Study Manifests"); the seed protocol is recorded here instead.

The index and each manifest have a detached ``<file>.sha256``; the index also carries the checksums of the campaign's
result files. The index never lists itself or the report that quotes its checksum.

v2 (run-index completeness, closing D-10 gaps G1, G2, G3, G6 and G7; lead decision 2026-10-26) adds, all required: the profile
and analysis-plan sha256 the run service hashed (``profile``, ``analysis_plan``), the planned runs per cell and the planned
number of runs (``planned``), the output folder and the result of the outside-the-repository check made at start
(``output_location``) and one record per failed run (``failed_runs``). v1 indexes carry none of this and are refused by the
verifier (no paper evidence exists under v1; smoke campaigns are re-run).
"""
from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, Optional

from pydantic import Field, PositiveInt, field_validator, model_validator

from .common import ChecksumV1, OutputChecksumV1, RepositoryRelativePath, Sha256Digest, StrictContract
from .run import EnvironmentV1, GitStateV1


class RunIndexEntryV1(StrictContract):
    run_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    manifest_path: RepositoryRelativePath
    manifest_checksum: ChecksumV1
    # sha256 of the D-01 comparison key of the run's row (no timing field enters it)
    comparison_key_digest: Sha256Digest


class ProfileRefV1(StrictContract):
    """The study profile file the run service hashed (working-tree bytes, ``sha256`` of ``read_bytes()``)."""

    path: RepositoryRelativePath
    sha256: Sha256Digest


class AnalysisPlanRefV1(StrictContract):
    """The analysis plan the campaign names. ``path`` and ``sha256`` are ``None`` only when the plan did not resolve (no file, an
    invalid file, or a file that is not this study's plan), which a smoke campaign allows (descriptive output only; the reason is
    in the run report); a paper campaign always has both. The hash of a plan that did not resolve is never recorded."""

    analysis_plan_id: str = Field(min_length=1)
    path: Optional[RepositoryRelativePath]
    sha256: Optional[Sha256Digest]

    @model_validator(mode="after")
    def path_and_hash_come_together(self) -> "AnalysisPlanRefV1":
        if (self.path is None) != (self.sha256 is None):
            raise ValueError("the analysis plan file path and its sha256 are recorded together or not at all")
        return self


class PlannedRunsV1(StrictContract):
    """Runs this campaign planned: per cell (dataset, algorithm, budget level) and in total. A paper campaign plans the whole
    profile (``runs_per_cell`` = ``study.run_count``); a smoke campaign plans its slice."""

    runs_per_cell: PositiveInt
    runs: PositiveInt


class OutsideRepositoryCheckV1(StrictContract):
    """The outside-the-repository check made at start. A run inside the repository is refused before anything is written, so
    the only result an index can hold is ``outside_repository``; ``checked_against`` names the trees it was checked against."""

    result: Literal["outside_repository"]
    checked_against: list[str] = Field(min_length=1)


class OutputLocationV1(StrictContract):
    """The campaign folder as an absolute path (paths elsewhere in the index are relative to it). The user-home prefix is written as
    ``~`` (``~`` or ``~/<rest>``, A20 L8) so that the index does not carry the user name; indexes written before that keep their
    absolute path and stay valid."""

    path: str = Field(min_length=1)
    outside_repository_check: OutsideRepositoryCheckV1

    @field_validator("path")
    @classmethod
    def path_is_absolute(cls, value: str) -> str:
        if value == "~" or value.startswith("~/"):
            return value
        if not (PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()):
            raise ValueError("the output folder is recorded as an absolute path (or as ~/<path> under the user-home folder)")
        return value


class FailedRunV1(StrictContract):
    """One failed run as ``failed_runs.jsonl`` records it (the failure policy of OQ-9 a: recorded, excluded from inference)."""

    # The same rule as the validator below, for consumers of the exported JSON schema: a fixed-budget record needs an integer budget.
    model_config = StrictContract.model_config | {
        "json_schema_extra": {
            "if": {"properties": {"comparison_regime": {"const": "fixed_evaluation_budget"}}, "required": ["comparison_regime"]},
            "then": {"properties": {"evaluation_budget": {"type": "integer"}}, "required": ["evaluation_budget"]},
        }
    }

    algorithm_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    comparison_regime: str = Field(min_length=1)
    evaluation_budget: Optional[int]
    replicate: int = Field(ge=0)
    stage: str = Field(min_length=1)
    exception_category: str = Field(min_length=1)
    error: str

    @model_validator(mode="after")
    def fixed_budget_record_has_its_budget(self) -> "FailedRunV1":
        """A failed run of the fixed-budget regime names the budget it was given; null is for native runs only (no silent null)."""
        if self.comparison_regime == "fixed_evaluation_budget" and self.evaluation_budget is None:
            raise ValueError("a failed run of the fixed_evaluation_budget regime needs its evaluation_budget (null is for native runs)")
        return self


class RunIndexV2(StrictContract):
    """Campaign index: lists every run manifest of one campaign with its checksum, plus the campaign-wide fields.

    The manifests of native (algorithm_native_termination) runs carry ``budget.levels`` = [0] as a sentinel: the run
    contract requires one level entry and a native run has no budget level. No consumer may read that 0 as a budget level;
    the budget policy ``native_uncapped`` says there is none."""

    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-run-index/v2"}}

    schema_version: Literal["uniride-run-index/v2"]
    study_id: str = Field(min_length=1)
    mode: Literal["smoke", "paper"]
    status: Literal["passed", "failed"]
    seed_protocol_version: str = Field(min_length=1)
    base_seed: int
    git: GitStateV1
    environment: EnvironmentV1
    runs: list[RunIndexEntryV1]
    outputs: list[OutputChecksumV1]
    profile: ProfileRefV1
    analysis_plan: AnalysisPlanRefV1
    planned: PlannedRunsV1
    output_location: OutputLocationV1
    failed_runs: list[FailedRunV1]

    @model_validator(mode="after")
    def run_ids_are_unique(self) -> "RunIndexV2":
        ids = [entry.run_id for entry in self.runs]
        if len(set(ids)) != len(ids):
            raise ValueError("run ids in a campaign index must be unique")
        return self

    @model_validator(mode="after")
    def a_paper_index_names_its_plan_file(self) -> "RunIndexV2":
        if self.mode == "paper" and self.analysis_plan.sha256 is None:
            raise ValueError("a paper campaign records the sha256 of its analysis plan file")
        return self
