"""Campaign index of run manifests (Gate D, D-02): ``uniride-run-index/v1``.

``RunManifestV1`` describes one run (one algorithm, dataset, budget level and replicate). A campaign (a smoke or paper
run of one study) writes one manifest per run plus this index, which lists every manifest with its checksum and holds
what is shared by the whole campaign: study, mode, git state, environment, base seed and the seed protocol version.
``uniride-run/v1`` has no seed-protocol field and is not changed (a schema change is a new version, design
"Study Manifests"); the seed protocol is recorded here instead.

The index and each manifest have a detached ``<file>.sha256``; the index also carries the checksums of the campaign's
result files. The index never lists itself or the report that quotes its checksum.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .common import ChecksumV1, OutputChecksumV1, RepositoryRelativePath, Sha256Digest, StrictContract
from .run import EnvironmentV1, GitStateV1


class RunIndexEntryV1(StrictContract):
    run_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    manifest_path: RepositoryRelativePath
    manifest_checksum: ChecksumV1
    # sha256 of the D-01 comparison key of the run's row (no timing field enters it)
    comparison_key_digest: Sha256Digest


class RunIndexV1(StrictContract):
    """Campaign index: lists every run manifest of one campaign with its checksum, plus the campaign-wide fields.

    The manifests of native (algorithm_native_termination) runs carry ``budget.levels`` = [0] as a sentinel: the run
    contract requires one level entry and a native run has no budget level. No consumer may read that 0 as a budget level;
    the budget policy ``native_uncapped`` says there is none."""

    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-run-index/v1"}}

    schema_version: Literal["uniride-run-index/v1"]
    study_id: str = Field(min_length=1)
    mode: Literal["smoke", "paper"]
    status: Literal["passed", "failed"]
    seed_protocol_version: str = Field(min_length=1)
    base_seed: int
    git: GitStateV1
    environment: EnvironmentV1
    runs: list[RunIndexEntryV1]
    outputs: list[OutputChecksumV1]

    @model_validator(mode="after")
    def run_ids_are_unique(self) -> "RunIndexV1":
        ids = [entry.run_id for entry in self.runs]
        if len(set(ids)) != len(ids):
            raise ValueError("run ids in a campaign index must be unique")
        return self
