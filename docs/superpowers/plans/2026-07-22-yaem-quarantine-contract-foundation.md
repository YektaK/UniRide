# YAEM Quarantine and Contract Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Package A by transactionally quarantining the tracked YAEM 2026 legacy tree and establishing versioned, packaged study, dataset, run, and archive-manifest contracts with reproducible verification.

**Architecture:** Pydantic models are the runtime contract source of truth and deterministically export the three approved JSON Schema snapshots. A separate archival module inventories only Git-tracked legacy files, scans them before mutation, classifies evidence, writes a checksum manifest, and verifies the archived bytes. Boundary tests prove the legacy package is absent from active imports and distributions while the schemas remain importable package resources.

**Tech Stack:** Python 3.11+, Pydantic 2.13.4, pytest, setuptools, Git, PowerShell, SHA-256, JSON Schema Draft 2020-12.

## Global Constraints

- Work only in `C:\tmp\UniRide-reconcile` on `codex/reconcile-native-protocol`; never modify or pull into the rescue checkout.
- Follow `AGENTS.md`, `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`, `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`, and `CANONICAL_THREE_OPT_DESIGN.md` in that order after live code and tests.
- Package A only: YAEM quarantine, archive manifest, study/dataset/run contracts, import/package boundaries, and Gate A verification.
- Do not change solver behavior, registry identities, fairness accounting, Bildiri code, production API/frontend code, dependencies, lockfiles, generated benchmark results, or paper conclusions.
- Do not run full TSPLIB/CVRPLIB or paper-scale experiments.
- Archive only files reported by `git ls-files -- academic_benchmark/yaem2026`; ignored caches and local artifacts are not evidence and must not enter the archive.
- Preserve historical file bytes and directory structure. Do not edit archived evidence to make it appear valid.
- Use `INVALID`, `HISTORICAL_UNVERIFIED`, `REFERENCE_ONLY`, and `WITHHELD_SENSITIVE` exactly as defined by the approved design.
- Scan before moving or staging archive files. Confirmed credentials are deleted only from the integration worktree, recorded without secret content, and retained untouched in the rescue checkout. Ambiguous high-risk matches abort without mutation.
- JSON contracts use UTF-8, `additionalProperties: false` at every object, repository-relative paths only, and exact schema IDs `uniride-study/v1`, `uniride-dataset/v1`, and `uniride-run/v1`.
- Do not add a JSON Schema library; use the already pinned Pydantic runtime and deterministic checked-in schema snapshots.
- Commit each task separately. Do not push or open a pull request in Package A; publication is Package D.

---

## File Map

| Path | Responsibility |
|---|---|
| `academic_benchmark/contracts/__init__.py` | Public exports for the three v1 manifest models and schema export helper. |
| `academic_benchmark/contracts/common.py` | Shared strict model base, JSON value types, IDs, SHA-256 values, repository-relative paths, and small nested primitives. |
| `academic_benchmark/contracts/study.py` | Strict `uniride-study/v1` study-profile contract and cross-field validation. |
| `academic_benchmark/contracts/dataset.py` | Strict `uniride-dataset/v1` provenance, matrix semantics, and optimum/BKS contract. |
| `academic_benchmark/contracts/run.py` | Strict `uniride-run/v1` reproducibility envelope matching the approved manifest fields. |
| `academic_benchmark/contracts/export_schemas.py` | Deterministic schema generation/check CLI. |
| `academic_benchmark/schemas/__init__.py` | Makes checked-in schemas addressable through `importlib.resources`. |
| `academic_benchmark/schemas/*-v1.schema.json` | Generated JSON Schema Draft 2020-12 snapshots. |
| `academic_benchmark/archive_manifest.py` | Evidence classes, SHA-256 inventory, sensitive scan, transactional YAEM quarantine, manifest write, and verification CLI. |
| `academic_benchmark/tests/test_manifest_contracts.py` | TDD coverage for models, paths, extra fields, cross-field rules, and schema snapshot drift. |
| `academic_benchmark/tests/test_archive_manifest.py` | TDD coverage for evidence classification, redacted findings, atomic preflight, hashes, withholding, and tamper detection. |
| `academic_benchmark/tests/test_yaem_quarantine_boundary.py` | Gate A proof for zero active YAEM imports, no package discovery, archive inventory, and sensitive-content absence. |
| `.gitignore` | Narrow allowlist for the YAEM archive only; keep all other `archive/*` ignored. |
| `pyproject.toml` | Include checked-in schema JSON files as package data. |
| `archive/academic_benchmark/yaem2026_legacy/**` | Byte-preserved tracked legacy tree plus manifest and quarantine notice. |
| `archive/README.md` | Active archive index and evidence-use warning. |

---

### Task 1: Add Strict Shared Contract Primitives

**Files:**
- Create: `academic_benchmark/contracts/__init__.py`
- Create: `academic_benchmark/contracts/common.py`
- Test: `academic_benchmark/tests/test_manifest_contracts.py`

**Interfaces:**
- Produces: `StrictContract`, `RepositoryRelativePath`, `Sha256Digest`, `JsonValue`, `validate_repository_relative_path(value: str) -> str`, `ChecksumV1`, and `OutputChecksumV1`.
- Consumes: Pydantic 2.13.4 already pinned in `pyproject.toml`.

- [ ] **Step 1: Write failing tests for strict objects and repository-relative paths**

Create `academic_benchmark/tests/test_manifest_contracts.py` with:

```python
from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from academic_benchmark.contracts.common import (
    ChecksumV1,
    RepositoryRelativePath,
    StrictContract,
)


class _PathProbe(StrictContract):
    path: RepositoryRelativePath


@pytest.mark.parametrize(
    "value",
    ["academic_benchmark/datasets/ft53.json", "studies/yaem2026/study.json"],
)
def test_repository_relative_path_accepts_normalized_paths(value: str):
    assert _PathProbe(path=value).path == value


@pytest.mark.parametrize(
    "value",
    ["/absolute/file.json", r"C:\\secret\\file.json", "../escape.json", "a/../../escape.json", "", "."],
)
def test_repository_relative_path_rejects_absolute_or_traversal(value: str):
    with pytest.raises(ValidationError):
        _PathProbe(path=value)


def test_strict_contract_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ChecksumV1(algorithm="sha256", value="a" * 64, unexpected=True)


def test_sha256_contract_rejects_non_hex_or_wrong_length():
    with pytest.raises(ValidationError):
        ChecksumV1(algorithm="sha256", value="not-a-digest")
```

- [ ] **Step 2: Run the test and confirm the import failure**

Run:

```powershell
python -m pytest academic_benchmark/tests/test_manifest_contracts.py -q -p no:cacheprovider --tb=short
```

Expected: collection fails with `ModuleNotFoundError: No module named 'academic_benchmark.contracts'`.

- [ ] **Step 3: Implement the shared strict types**

Create `academic_benchmark/contracts/common.py`:

```python
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue, WithJsonSchema


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def validate_repository_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or normalized == ".":
        raise ValueError("path must identify a repository-relative file")
    if path.is_absolute() or (path.parts and ":" in path.parts[0]):
        raise ValueError("absolute paths are forbidden")
    if ".." in path.parts:
        raise ValueError("path traversal is forbidden")
    return path.as_posix()


RepositoryRelativePath = Annotated[
    str,
    AfterValidator(validate_repository_relative_path),
    WithJsonSchema({"type": "string", "format": "uniride-repository-relative-path"}),
]
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ChecksumV1(StrictContract):
    algorithm: Literal["sha256"]
    value: Sha256Digest


class OutputChecksumV1(StrictContract):
    path: RepositoryRelativePath
    checksum: ChecksumV1
```

Create `academic_benchmark/contracts/__init__.py` initially as:

```python
from .common import ChecksumV1, OutputChecksumV1, RepositoryRelativePath, StrictContract

__all__ = ["ChecksumV1", "OutputChecksumV1", "RepositoryRelativePath", "StrictContract"]
```

- [ ] **Step 4: Run the focused tests**

Run the Step 2 command again.

Expected: `10 passed` with no warnings from the new contract module.

- [ ] **Step 5: Commit the shared primitives**

```powershell
git add academic_benchmark/contracts academic_benchmark/tests/test_manifest_contracts.py
git commit -m "feat(academic): add strict manifest primitives"
```

---

### Task 2: Define Study, Dataset, and Run v1 Models

**Files:**
- Create: `academic_benchmark/contracts/study.py`
- Create: `academic_benchmark/contracts/dataset.py`
- Create: `academic_benchmark/contracts/run.py`
- Modify: `academic_benchmark/contracts/__init__.py`
- Modify: `academic_benchmark/tests/test_manifest_contracts.py`

**Interfaces:**
- Consumes: Task 1 types.
- Produces: `StudyManifestV1`, `DatasetManifestV1`, `RunManifestV1` and their nested strict models.

Package A validates contract shape, exact schema version, path safety, and algorithm/parameter-key consistency. Canonical registry lookup, compatibility-alias rejection, and capability matching remain explicit Package C preflight responsibilities; this plan does not claim those execution checks already exist.

- [ ] **Step 1: Append failing model-contract tests**

Append these helpers and tests to `academic_benchmark/tests/test_manifest_contracts.py`:

```python
from academic_benchmark.contracts import DatasetManifestV1, RunManifestV1, StudyManifestV1


def _study_payload() -> dict:
    return {
        "schema_version": "uniride-study/v1",
        "study_id": "yaem2026",
        "title": "YAEM 2026 Reproducible Study",
        "status": "draft",
        "algorithm_ids": ["Core-GWO-TSP-Pure"],
        "algorithm_parameters": {"Core-GWO-TSP-Pure": {"pack_size": 20}},
        "dataset_manifest_refs": ["academic_benchmark/datasets/ft53.json"],
        "primary_protocol": {
            "protocol_id": "fixed_evaluation_budget",
            "protocol_version": "uniride-fair-tsp-v2",
            "budget_policy": "atomic_upper_bound_v1",
        },
        "secondary_protocol": {
            "protocol_id": "algorithm_native_termination",
            "protocol_version": "uniride-native-tsp-v1",
            "termination": {"max_iterations": 250},
        },
        "fixed_budget_levels": [1000, 5000],
        "run_count": 30,
        "base_seed": 2026,
        "seed_protocol_version": "sha256-seed-v1",
        "problem_families": ["TSP", "ATSP"],
        "analysis_plan_id": "yaem2026-analysis-v1",
        "output_policy": {"repository_outputs": "smoke_only", "paper_scale_location": "external"},
        "paper_metadata": {"paper_id": "yaem2026", "year": 2026, "venue": "YAEM"},
    }


def _dataset_payload() -> dict:
    return {
        "schema_version": "uniride-dataset/v1",
        "dataset_id": "tsplib-ft53",
        "artifact_path": "academic_benchmark/tsplib_data/ft53.atsp",
        "source": {
            "authority_url": "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz",
            "retrieved_on": "2026-07-20",
        },
        "checksum": {"algorithm": "sha256", "value": "6" * 64},
        "problem_type": "ATSP",
        "dimension": 53,
        "matrix_semantics": {
            "directed": True,
            "edge_weight_type": "EXPLICIT",
            "edge_weight_format": "FULL_MATRIX",
            "diagonal_semantics": "sentinel",
        },
        "best_known": {
            "status": "optimal",
            "value": 6905.0,
            "provenance": "TSPLIB canonical optimum",
        },
    }


def _run_payload() -> dict:
    return {
        "schema_version": "uniride-run/v1",
        "run_id": "yaem2026-ft53-gwo-r00-b1000",
        "study_id": "yaem2026",
        "protocol_version": "uniride-fair-tsp-v2",
        "git": {"commit": "a" * 40, "dirty": False},
        "environment": {
            "python": "3.14.3", "operating_system": "Windows", "cpu": "test-cpu",
            "numpy": "2.4.6", "numba": "0.66.0", "llvmlite": "0.48.0",
            "statistics_library": "scipy-unavailable",
        },
        "dataset": _dataset_payload(),
        "algorithm": {
            "algorithm_id": "Core-GWO-TSP-Pure",
            "capabilities": {"problem_types": ["TSP", "ATSP"], "directed_costs": True},
            "configuration": {"pack_size": 20},
            "composition_stages": [],
        },
        "seeds": {"base_seed": 2026, "derived": {"replicate_0": 17}},
        "budget": {
            "levels": [1000], "policy": "atomic_upper_bound_v1",
            "objective_evaluations": 998, "stage_allocation": {},
        },
        "termination": {"reason": "evaluation_budget_exhausted", "runtime_seconds": 0.25},
        "validation": {"passed": True, "checks": ["complete_tour", "closed_cycle_cost"]},
        "outputs": [{"path": "academic_benchmark/results/smoke.json", "checksum": {"algorithm": "sha256", "value": "b" * 64}}],
    }


def test_all_v1_contracts_accept_complete_payloads():
    assert StudyManifestV1.model_validate(_study_payload()).study_id == "yaem2026"
    assert DatasetManifestV1.model_validate(_dataset_payload()).dimension == 53
    assert RunManifestV1.model_validate(_run_payload()).budget.objective_evaluations == 998


def test_study_requires_exact_parameter_keys_for_algorithm_ids():
    payload = _study_payload()
    payload["algorithm_parameters"] = {"different-id": {}}
    with pytest.raises(ValidationError, match="algorithm_parameters keys"):
        StudyManifestV1.model_validate(payload)


@pytest.mark.parametrize("model,payload", [
    (StudyManifestV1, _study_payload),
    (DatasetManifestV1, _dataset_payload),
    (RunManifestV1, _run_payload),
])
def test_v1_contracts_reject_unknown_top_level_fields(model, payload):
    value = payload()
    value["unknown"] = True
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model.model_validate(value)


def test_schema_versions_are_exact_not_heuristic():
    payload = _study_payload()
    payload["schema_version"] = "uniride-study/v2"
    with pytest.raises(ValidationError):
        StudyManifestV1.model_validate(payload)
```

- [ ] **Step 2: Run the tests and confirm missing exports**

Run the Task 1 focused command.

Expected: collection fails because `DatasetManifestV1`, `RunManifestV1`, and `StudyManifestV1` are not exported.

- [ ] **Step 3: Implement `study.py`**

```python
from __future__ import annotations

from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from .common import JsonValue, RepositoryRelativePath, StrictContract


ProblemFamily = Literal["TSP", "ATSP", "CVRP", "CVRPTW", "UniRide"]


class FixedBudgetProtocolV1(StrictContract):
    protocol_id: Literal["fixed_evaluation_budget"]
    protocol_version: str = Field(min_length=1)
    budget_policy: Literal["atomic_upper_bound_v1"]


class NativeProtocolV1(StrictContract):
    protocol_id: Literal["algorithm_native_termination"]
    protocol_version: str = Field(min_length=1)
    termination: dict[str, JsonValue]


class OutputPolicyV1(StrictContract):
    repository_outputs: Literal["smoke_only", "none"]
    paper_scale_location: Literal["external"]


class PaperMetadataV1(StrictContract):
    paper_id: str = Field(min_length=1)
    year: PositiveInt
    venue: str = Field(min_length=1)


class StudyManifestV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-study/v1"}}

    schema_version: Literal["uniride-study/v1"]
    study_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1)
    status: Literal["draft", "active", "archived"]
    algorithm_ids: list[str] = Field(min_length=1)
    algorithm_parameters: dict[str, dict[str, JsonValue]]
    dataset_manifest_refs: list[RepositoryRelativePath] = Field(min_length=1)
    primary_protocol: FixedBudgetProtocolV1
    secondary_protocol: NativeProtocolV1 | None = None
    fixed_budget_levels: list[PositiveInt] = Field(min_length=1)
    run_count: PositiveInt
    base_seed: int
    seed_protocol_version: str = Field(min_length=1)
    problem_families: list[ProblemFamily] = Field(min_length=1)
    analysis_plan_id: str = Field(min_length=1)
    output_policy: OutputPolicyV1
    paper_metadata: PaperMetadataV1

    @model_validator(mode="after")
    def validate_algorithm_parameter_keys(self) -> "StudyManifestV1":
        if len(set(self.algorithm_ids)) != len(self.algorithm_ids):
            raise ValueError("algorithm_ids must be unique")
        if set(self.algorithm_parameters) != set(self.algorithm_ids):
            raise ValueError("algorithm_parameters keys must exactly match algorithm_ids")
        if len(set(self.fixed_budget_levels)) != len(self.fixed_budget_levels):
            raise ValueError("fixed_budget_levels must be unique")
        return self
```

- [ ] **Step 4: Implement `dataset.py`**

```python
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from .common import ChecksumV1, RepositoryRelativePath, StrictContract


class DatasetSourceV1(StrictContract):
    authority_url: str = Field(min_length=1)
    retrieved_on: date


class MatrixSemanticsV1(StrictContract):
    directed: bool
    edge_weight_type: str = Field(min_length=1)
    edge_weight_format: str | None = None
    diagonal_semantics: Literal["zero", "sentinel", "problem_defined"]


class BestKnownV1(StrictContract):
    status: Literal["optimal", "best_known", "unknown"]
    value: float | None
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_value_for_known_status(self) -> "BestKnownV1":
        if self.status != "unknown" and self.value is None:
            raise ValueError("optimal and best_known records require value")
        return self


class DatasetManifestV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-dataset/v1"}}

    schema_version: Literal["uniride-dataset/v1"]
    dataset_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    artifact_path: RepositoryRelativePath
    source: DatasetSourceV1
    checksum: ChecksumV1
    problem_type: Literal["TSP", "ATSP", "CVRP", "CVRPTW", "UniRide"]
    dimension: PositiveInt
    matrix_semantics: MatrixSemanticsV1
    best_known: BestKnownV1
```

- [ ] **Step 5: Implement `run.py`**

```python
from __future__ import annotations

from typing import Literal

from pydantic import Field, NonNegativeFloat, NonNegativeInt

from .common import JsonValue, OutputChecksumV1, StrictContract
from .dataset import DatasetManifestV1


class GitStateV1(StrictContract):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    dirty: bool


class EnvironmentV1(StrictContract):
    python: str
    operating_system: str
    cpu: str
    numpy: str
    numba: str
    llvmlite: str
    statistics_library: str


class AlgorithmRunV1(StrictContract):
    algorithm_id: str = Field(min_length=1)
    capabilities: dict[str, JsonValue]
    configuration: dict[str, JsonValue]
    composition_stages: list[dict[str, JsonValue]]


class SeedScheduleV1(StrictContract):
    base_seed: int
    derived: dict[str, int]


class BudgetRecordV1(StrictContract):
    levels: list[int] = Field(min_length=1)
    policy: Literal["atomic_upper_bound_v1", "native_uncapped"]
    objective_evaluations: NonNegativeInt
    stage_allocation: dict[str, NonNegativeInt]


class TerminationRecordV1(StrictContract):
    reason: str = Field(min_length=1)
    runtime_seconds: NonNegativeFloat


class ValidationRecordV1(StrictContract):
    passed: bool
    checks: list[str]


class RunManifestV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-run/v1"}}

    schema_version: Literal["uniride-run/v1"]
    run_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    study_id: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    git: GitStateV1
    environment: EnvironmentV1
    dataset: DatasetManifestV1
    algorithm: AlgorithmRunV1
    seeds: SeedScheduleV1
    budget: BudgetRecordV1
    termination: TerminationRecordV1
    validation: ValidationRecordV1
    outputs: list[OutputChecksumV1]
```

- [ ] **Step 6: Export the models**

Replace `academic_benchmark/contracts/__init__.py` with:

```python
from .common import ChecksumV1, OutputChecksumV1, RepositoryRelativePath, StrictContract
from .dataset import DatasetManifestV1
from .run import RunManifestV1
from .study import StudyManifestV1

__all__ = [
    "ChecksumV1", "DatasetManifestV1", "OutputChecksumV1", "RepositoryRelativePath",
    "RunManifestV1", "StrictContract", "StudyManifestV1",
]
```

- [ ] **Step 7: Run the contract tests**

Run the Task 1 focused command.

Expected: all tests in `test_manifest_contracts.py` pass.

- [ ] **Step 8: Commit the v1 models**

```powershell
git add academic_benchmark/contracts academic_benchmark/tests/test_manifest_contracts.py
git commit -m "feat(academic): define v1 study dataset and run contracts"
```

---

### Task 3: Export and Package Deterministic JSON Schemas

**Files:**
- Create: `academic_benchmark/contracts/export_schemas.py`
- Create: `academic_benchmark/schemas/__init__.py`
- Create: `academic_benchmark/schemas/study-v1.schema.json`
- Create: `academic_benchmark/schemas/dataset-v1.schema.json`
- Create: `academic_benchmark/schemas/run-v1.schema.json`
- Modify: `academic_benchmark/tests/test_manifest_contracts.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: three top-level models from Task 2.
- Produces: `render_schemas() -> dict[str, str]`, `write_schemas(root: Path) -> None`, `check_schemas(root: Path) -> list[str]`, and CLI `python -m academic_benchmark.contracts.export_schemas {write|check}`.

- [ ] **Step 1: Add failing schema snapshot/resource tests**

Append:

```python
import json
from importlib.resources import files

from academic_benchmark.contracts.export_schemas import check_schemas, render_schemas


def test_schema_snapshots_match_models_and_have_exact_ids():
    assert check_schemas() == []
    expected_ids = {
        "study-v1.schema.json": "uniride-study/v1",
        "dataset-v1.schema.json": "uniride-dataset/v1",
        "run-v1.schema.json": "uniride-run/v1",
    }
    for name, rendered in render_schemas().items():
        schema = json.loads(rendered)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == expected_ids[name]
        assert schema["additionalProperties"] is False


def test_schema_snapshots_are_package_resources():
    root = files("academic_benchmark.schemas")
    for name in ("study-v1.schema.json", "dataset-v1.schema.json", "run-v1.schema.json"):
        assert json.loads(root.joinpath(name).read_text(encoding="utf-8"))["$id"]
```

- [ ] **Step 2: Run tests and confirm missing exporter/snapshots**

Run the focused contract command.

Expected: collection fails for missing `academic_benchmark.contracts.export_schemas`.

- [ ] **Step 3: Implement deterministic schema export/check**

Create `academic_benchmark/contracts/export_schemas.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import DatasetManifestV1
from .run import RunManifestV1
from .study import StudyManifestV1


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
MODELS = {
    "study-v1.schema.json": StudyManifestV1,
    "dataset-v1.schema.json": DatasetManifestV1,
    "run-v1.schema.json": RunManifestV1,
}


def render_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for filename, model in MODELS.items():
        schema = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        rendered[filename] = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return rendered


def write_schemas(root: Path = SCHEMA_DIR) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in render_schemas().items():
        (root / filename).write_text(content, encoding="utf-8", newline="\n")


def check_schemas(root: Path = SCHEMA_DIR) -> list[str]:
    stale: list[str] = []
    for filename, content in render_schemas().items():
        path = root / filename
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(filename)
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write or verify UniRide manifest schemas")
    parser.add_argument("action", choices=("write", "check"))
    args = parser.parse_args(argv)
    if args.action == "write":
        write_schemas()
        return 0
    stale = check_schemas()
    if stale:
        parser.error("stale schema snapshots: " + ", ".join(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `academic_benchmark/schemas/__init__.py` containing only:

```python
"""Checked-in JSON Schema resources for academic manifests."""
```

- [ ] **Step 4: Generate snapshots and add package-data configuration**

Run:

```powershell
python -m academic_benchmark.contracts.export_schemas write
```

Add to `pyproject.toml`:

```toml
[tool.setuptools.package-data]
"academic_benchmark.schemas" = ["*.schema.json"]
```

Expected: the three schema files are UTF-8 JSON, sorted deterministically, and have the exact approved `$id` values.

- [ ] **Step 5: Verify schemas are current and tests pass**

```powershell
python -m academic_benchmark.contracts.export_schemas check
python -m pytest academic_benchmark/tests/test_manifest_contracts.py -q -p no:cacheprovider --tb=short
```

Expected: both commands exit 0; all contract tests pass.

- [ ] **Step 6: Commit schemas and packaging**

```powershell
git add pyproject.toml academic_benchmark/contracts/export_schemas.py academic_benchmark/schemas academic_benchmark/tests/test_manifest_contracts.py
git commit -m "feat(academic): package deterministic v1 schemas"
```

---

### Task 4: Build Evidence Classification, Sensitive Scan, and Manifest Verification

**Files:**
- Create: `academic_benchmark/archive_manifest.py`
- Create: `academic_benchmark/tests/test_archive_manifest.py`

**Interfaces:**
- Produces: `EvidenceClass`, `ArchiveEntry`, `ArchiveManifest`, `SensitiveFinding`, `classify_yaem_evidence(path)`, `scan_sensitive_file(path)`, `sha256_file(path)`, `build_manifest(...)`, and `verify_manifest(...)`.
- The scan returns only rule, severity, path, and line number; it never stores or prints matched secret text.

- [ ] **Step 1: Write failing unit tests for classification, redaction, hashes, and tamper detection**

Create `academic_benchmark/tests/test_archive_manifest.py`:

```python
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest

from academic_benchmark.archive_manifest import (
    EvidenceClass,
    build_manifest,
    classify_yaem_evidence,
    scan_sensitive_file,
    verify_manifest,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("results/reports/FINAL_ANALYSIS.md", EvidenceClass.INVALID),
        ("results/benchmark_student_matrix.csv", EvidenceClass.INVALID),
        ("results/histories/convergence_eil51.json", EvidenceClass.HISTORICAL_UNVERIFIED),
        ("archive_20260701_0120/results/plots/eil51.png", EvidenceClass.HISTORICAL_UNVERIFIED),
        ("core/gwo_solver.py", EvidenceClass.REFERENCE_ONLY),
        ("data/student_matrix.json", EvidenceClass.REFERENCE_ONLY),
        ("yaem2026_sunum_slayt_sablonu.md", EvidenceClass.REFERENCE_ONLY),
    ],
)
def test_yaem_evidence_classification(path: str, expected: EvidenceClass):
    assert classify_yaem_evidence(PurePosixPath(path)) is expected


def test_sensitive_scan_never_returns_secret_value(tmp_path: Path):
    secret = "ghp_" + "A" * 36
    path = tmp_path / "settings.py"
    path.write_text(f'TOKEN = "{secret}"\n', encoding="utf-8")
    findings = scan_sensitive_file(path)
    assert [(finding.rule, finding.severity, finding.line) for finding in findings] == [
        ("github_token", "confirmed", 1)
    ]
    assert secret not in repr(findings)


def test_ambiguous_assignment_is_high_risk_without_secret_echo(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text('{"api_key": "long-non-placeholder-value-123456"}', encoding="utf-8")
    finding = scan_sensitive_file(path)[0]
    assert finding.rule == "credential_assignment"
    assert finding.severity == "ambiguous"
    assert "long-non-placeholder" not in repr(finding)


def test_manifest_hashes_archived_bytes_and_detects_tampering(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "core").mkdir(parents=True)
    (archive / "core" / "solver.py").write_text("print('legacy')\n", encoding="utf-8")
    manifest = build_manifest(
        archive_id="yaem2026_legacy",
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archived_root=archive,
        original_paths=[PurePosixPath("core/solver.py")],
        withheld=[],
    )
    assert verify_manifest(manifest, archive) == []
    (archive / "core" / "solver.py").write_text("tampered\n", encoding="utf-8")
    assert verify_manifest(manifest, archive) == ["checksum mismatch: core/solver.py"]
```

- [ ] **Step 2: Run and confirm the missing module failure**

```powershell
python -m pytest academic_benchmark/tests/test_archive_manifest.py -q -p no:cacheprovider --tb=short
```

Expected: collection fails with `ModuleNotFoundError: No module named 'academic_benchmark.archive_manifest'`.

- [ ] **Step 3: Implement the pure archival types, classifier, scanner, and verifier**

Create `academic_benchmark/archive_manifest.py` with these exact public contracts and policies:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Iterable, Literal

from pydantic import Field, model_validator

from academic_benchmark.contracts.common import RepositoryRelativePath, Sha256Digest, StrictContract


class EvidenceClass(StrEnum):
    INVALID = "INVALID"
    HISTORICAL_UNVERIFIED = "HISTORICAL_UNVERIFIED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    WITHHELD_SENSITIVE = "WITHHELD_SENSITIVE"


class ArchiveEntry(StrictContract):
    original_path: RepositoryRelativePath
    archive_path: RepositoryRelativePath | None
    byte_size: int = Field(ge=0)
    sha256: Sha256Digest
    classification: EvidenceClass

    @model_validator(mode="after")
    def validate_withholding(self) -> "ArchiveEntry":
        withheld = self.classification is EvidenceClass.WITHHELD_SENSITIVE
        if withheld != (self.archive_path is None):
            raise ValueError("only WITHHELD_SENSITIVE entries omit archive_path")
        return self


class ArchiveManifest(StrictContract):
    schema_version: Literal["uniride-archive/v1"]
    archive_id: str
    source_root: RepositoryRelativePath
    archive_root: RepositoryRelativePath
    entries: list[ArchiveEntry]


@dataclass(frozen=True)
class SensitiveFinding:
    path: str
    line: int
    rule: str
    severity: Literal["confirmed", "ambiguous"]


_CONFIRMED = (
    ("private_key", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,255}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
)
_AMBIGUOUS = (
    ("credential_assignment", re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password)\s*[\":=]+\s*[\"]?([A-Za-z0-9_./+\-=]{16,})"
    )),
)
_TEXT_SUFFIXES = {".py", ".json", ".csv", ".md", ".txt", ".toml", ".yaml", ".yml", ".ini", ".env"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_yaem_evidence(path: PurePosixPath) -> EvidenceClass:
    parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    in_results = "results" in parts
    in_reports = in_results and "reports" in parts
    if in_reports or (in_results and "student_matrix" in name):
        return EvidenceClass.INVALID
    if in_results:
        return EvidenceClass.HISTORICAL_UNVERIFIED
    return EvidenceClass.REFERENCE_ONLY


def scan_sensitive_file(path: Path) -> list[SensitiveFinding]:
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return []
    findings: list[SensitiveFinding] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            confirmed_on_line = False
            for rule, pattern in _CONFIRMED:
                if pattern.search(line):
                    findings.append(SensitiveFinding(path.as_posix(), line_number, rule, "confirmed"))
                    confirmed_on_line = True
            if not confirmed_on_line:
                for rule, pattern in _AMBIGUOUS:
                    match = pattern.search(line)
                    if match and not re.search(r"(?i)(example|placeholder|change[-_ ]?me|your[-_ ]|os\.environ|getenv)", line):
                        findings.append(SensitiveFinding(path.as_posix(), line_number, rule, "ambiguous"))
    return findings


def build_manifest(
    *, archive_id: str, source_root: PurePosixPath, archive_root: PurePosixPath,
    archived_root: Path, original_paths: Iterable[PurePosixPath], withheld: Iterable[ArchiveEntry],
) -> ArchiveManifest:
    entries = list(withheld)
    for relative in sorted(original_paths, key=lambda item: item.as_posix()):
        archived = archived_root / Path(*relative.parts)
        entries.append(ArchiveEntry(
            original_path=(source_root / relative).as_posix(),
            archive_path=(archive_root / relative).as_posix(),
            byte_size=archived.stat().st_size,
            sha256=sha256_file(archived),
            classification=classify_yaem_evidence(relative),
        ))
    entries.sort(key=lambda entry: entry.original_path)
    return ArchiveManifest(
        schema_version="uniride-archive/v1", archive_id=archive_id,
        source_root=source_root.as_posix(), archive_root=archive_root.as_posix(), entries=entries,
    )


def verify_manifest(manifest: ArchiveManifest, archived_root: Path) -> list[str]:
    errors: list[str] = []
    source_root = PurePosixPath(manifest.source_root)
    for entry in manifest.entries:
        relative = PurePosixPath(entry.original_path).relative_to(source_root)
        if entry.classification is EvidenceClass.WITHHELD_SENSITIVE:
            continue
        path = archived_root / Path(*relative.parts)
        if not path.is_file():
            errors.append(f"missing: {relative.as_posix()}")
        elif path.stat().st_size != entry.byte_size:
            errors.append(f"size mismatch: {relative.as_posix()}")
        elif sha256_file(path) != entry.sha256:
            errors.append(f"checksum mismatch: {relative.as_posix()}")
    return errors
```

Task 4 intentionally ends at pure verification. Task 5 owns the fully specified mutation and CLI transaction after these functions pass.

- [ ] **Step 4: Run archival unit tests**

Run the Step 2 command.

Expected: all tests in `test_archive_manifest.py` pass.

- [ ] **Step 5: Commit pure archival verification**

```powershell
git add academic_benchmark/archive_manifest.py academic_benchmark/tests/test_archive_manifest.py
git commit -m "feat(academic): add legacy evidence manifest verification"
```

---

### Task 5: Add an All-or-Nothing Quarantine Transaction and CLI

**Files:**
- Modify: `academic_benchmark/archive_manifest.py`
- Modify: `academic_benchmark/tests/test_archive_manifest.py`

**Interfaces:**
- Consumes: Task 4 primitives.
- Produces: `QuarantineBlocked`, `git_tracked_files(...)`, `quarantine_tracked_tree(...)`, `load_manifest(...)`, `write_manifest(...)`, and CLI subcommands `scan`, `quarantine`, and `verify`.

- [ ] **Step 1: Add failing transaction tests**

Append tests that create a temporary Git repository using `subprocess.run(..., check=True)`:

```python
import subprocess

from academic_benchmark.archive_manifest import QuarantineBlocked, quarantine_tracked_tree


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _legacy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    source = repo / "academic_benchmark" / "yaem2026"
    (source / "core").mkdir(parents=True)
    (source / "results" / "reports").mkdir(parents=True)
    (source / "core" / "solver.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "results" / "reports" / "analysis.md").write_text("legacy\n", encoding="utf-8")
    (source / "ignored.pyc").write_bytes(b"cache")
    (repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "add", ".gitignore", "academic_benchmark/yaem2026/core/solver.py", "academic_benchmark/yaem2026/results/reports/analysis.md")
    return repo


def test_quarantine_moves_only_tracked_files_and_writes_reproducible_manifest(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    manifest = quarantine_tracked_tree(
        repo_root=repo,
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archive_id="yaem2026_legacy",
    )
    archive = repo / "archive" / "academic_benchmark" / "yaem2026_legacy"
    assert (archive / "core" / "solver.py").is_file()
    assert (archive / "results" / "reports" / "analysis.md").is_file()
    assert not (archive / "ignored.pyc").exists()
    assert not (repo / "academic_benchmark" / "yaem2026" / "ignored.pyc").exists()
    assert verify_manifest(manifest, archive) == []
    assert json.loads((archive / "manifest.json").read_text(encoding="utf-8"))["entries"]


def test_ambiguous_sensitive_match_aborts_before_any_move(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    risky = repo / "academic_benchmark" / "yaem2026" / "config.json"
    risky.write_text('{"api_key": "ambiguous-real-looking-value-123"}', encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/config.json")
    with pytest.raises(QuarantineBlocked, match="ambiguous high-risk match"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
            archive_id="yaem2026_legacy",
        )
    assert risky.is_file()
    assert not (repo / "archive").exists()


def test_confirmed_secret_is_withheld_without_secret_content(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    secret = "ghp_" + "A" * 36
    risky = repo / "academic_benchmark" / "yaem2026" / "credential.txt"
    risky.write_text(secret, encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/credential.txt")
    manifest = quarantine_tracked_tree(
        repo_root=repo,
        source_root=PurePosixPath("academic_benchmark/yaem2026"),
        archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
        archive_id="yaem2026_legacy",
    )
    entry = next(item for item in manifest.entries if item.original_path.endswith("credential.txt"))
    assert entry.classification is EvidenceClass.WITHHELD_SENSITIVE
    assert entry.archive_path is None
    assert not risky.exists()
    manifest_text = (repo / "archive" / "academic_benchmark" / "yaem2026_legacy" / "manifest.json").read_text(encoding="utf-8")
    assert secret not in manifest_text


def test_untracked_user_file_blocks_without_mutation(tmp_path: Path):
    repo = _legacy_repo(tmp_path)
    note = repo / "academic_benchmark" / "yaem2026" / "local-note.bin"
    note.write_bytes(b"user data")
    with pytest.raises(QuarantineBlocked, match="untracked non-ignored"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
            archive_id="yaem2026_legacy",
        )
    assert note.is_file()
    assert not (repo / "archive").exists()


def test_manifest_failure_restores_moved_and_withheld_files(tmp_path: Path, monkeypatch):
    import academic_benchmark.archive_manifest as archive_module

    repo = _legacy_repo(tmp_path)
    secret = "ghp_" + "A" * 36
    credential = repo / "academic_benchmark" / "yaem2026" / "credential.txt"
    credential.write_text(secret, encoding="utf-8")
    _git(repo, "add", "academic_benchmark/yaem2026/credential.txt")

    def fail_write(*args, **kwargs):
        raise OSError("simulated manifest failure")

    monkeypatch.setattr(archive_module, "write_manifest", fail_write)
    with pytest.raises(OSError, match="simulated manifest failure"):
        quarantine_tracked_tree(
            repo_root=repo,
            source_root=PurePosixPath("academic_benchmark/yaem2026"),
            archive_root=PurePosixPath("archive/academic_benchmark/yaem2026_legacy"),
            archive_id="yaem2026_legacy",
        )
    assert credential.read_text(encoding="utf-8") == secret
    assert (repo / "academic_benchmark" / "yaem2026" / "core" / "solver.py").is_file()
    assert not (repo / "archive").exists()
```

- [ ] **Step 2: Run tests and confirm missing transaction interface**

Run the Task 4 focused command.

Expected: collection fails because `QuarantineBlocked` and `quarantine_tracked_tree` are missing.

- [ ] **Step 3: Implement the preflight-first transaction**

Extend the import block in `academic_benchmark/archive_manifest.py` with:

```python
import sys
import tempfile
from collections import Counter
```

Then add the complete transaction implementation:

```python
class QuarantineBlocked(RuntimeError):
    pass


def _git_paths(repo_root: Path, *arguments: str) -> list[PurePosixPath]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return sorted(
        (PurePosixPath(raw.decode("utf-8")) for raw in completed.stdout.split(b"\0") if raw),
        key=lambda item: item.as_posix(),
    )


def _git_directory(repo_root: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).resolve()


def _relative_paths(paths: Iterable[PurePosixPath], source_root: PurePosixPath) -> list[PurePosixPath]:
    try:
        return [path.relative_to(source_root) for path in paths]
    except ValueError as exc:
        raise QuarantineBlocked(f"Git returned a path outside {source_root}") from exc


def git_tracked_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    return _relative_paths(
        _git_paths(repo_root, "ls-files", "-z", "--", source_root.as_posix()),
        source_root,
    )


def _git_untracked_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    return _relative_paths(
        _git_paths(
            repo_root, "ls-files", "-z", "--others", "--exclude-standard",
            "--", source_root.as_posix(),
        ),
        source_root,
    )


def _git_ignored_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    return _relative_paths(
        _git_paths(
            repo_root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard",
            "--", source_root.as_posix(),
        ),
        source_root,
    )


def _is_disposable_cache(path: PurePosixPath) -> bool:
    return (
        "__pycache__" in path.parts
        or ".numba_cache" in path.parts
        or path.suffix.lower() in {".pyc", ".pyo", ".nbc", ".nbi"}
    )


def scan_tracked_tree(
    repo_root: Path,
    source_root: PurePosixPath,
) -> tuple[list[PurePosixPath], list[SensitiveFinding]]:
    tracked = git_tracked_files(repo_root, source_root)
    source_fs = repo_root / Path(*source_root.parts)
    findings: list[SensitiveFinding] = []
    for relative in tracked:
        for finding in scan_sensitive_file(source_fs / Path(*relative.parts)):
            findings.append(SensitiveFinding(
                path=(source_root / relative).as_posix(),
                line=finding.line,
                rule=finding.rule,
                severity=finding.severity,
            ))
    return tracked, findings


def write_manifest(manifest: ArchiveManifest, path: Path) -> None:
    content = json.dumps(
        manifest.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def load_manifest(path: Path) -> ArchiveManifest:
    return ArchiveManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _prune_empty_directories(source_root: Path) -> None:
    if not source_root.exists():
        return
    directories = sorted(
        (path for path in source_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        if not any(directory.iterdir()):
            directory.rmdir()
    if source_root.is_dir() and not any(source_root.iterdir()):
        source_root.rmdir()


def quarantine_tracked_tree(
    *,
    repo_root: Path,
    source_root: PurePosixPath,
    archive_root: PurePosixPath,
    archive_id: str,
) -> ArchiveManifest:
    repo_root = repo_root.resolve()
    source_fs = repo_root / Path(*source_root.parts)
    destination_root = repo_root / Path(*archive_root.parts)
    tracked, findings = scan_tracked_tree(repo_root, source_root)
    if not tracked:
        raise QuarantineBlocked(f"no tracked files under {source_root}")
    if destination_root.exists():
        raise QuarantineBlocked(f"archive destination already exists: {archive_root}")

    untracked = _git_untracked_files(repo_root, source_root)
    if untracked:
        names = ", ".join(path.as_posix() for path in untracked)
        raise QuarantineBlocked("untracked non-ignored files require review: " + names)
    ignored = _git_ignored_files(repo_root, source_root)
    unsafe_ignored = [path for path in ignored if not _is_disposable_cache(path)]
    if unsafe_ignored:
        names = ", ".join(path.as_posix() for path in unsafe_ignored)
        raise QuarantineBlocked("ignored non-cache files require review: " + names)

    ambiguous = [finding for finding in findings if finding.severity == "ambiguous"]
    if ambiguous:
        summary = ", ".join(
            f"{finding.path}:{finding.line}:{finding.rule}" for finding in ambiguous
        )
        raise QuarantineBlocked("ambiguous high-risk match; no files moved: " + summary)

    confirmed_paths = {
        PurePosixPath(finding.path).relative_to(source_root)
        for finding in findings
        if finding.severity == "confirmed"
    }
    backup_parent = _git_directory(repo_root)
    destination_root.mkdir(parents=True)
    moved: list[PurePosixPath] = []
    withheld: list[ArchiveEntry] = []

    with tempfile.TemporaryDirectory(prefix="uniride-quarantine-", dir=backup_parent) as backup_name:
        backup_root = Path(backup_name)
        for relative in confirmed_paths:
            source = source_fs / Path(*relative.parts)
            backup = backup_root / Path(*relative.parts)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
        try:
            for relative in tracked:
                source = source_fs / Path(*relative.parts)
                if relative in confirmed_paths:
                    withheld.append(ArchiveEntry(
                        original_path=(source_root / relative).as_posix(),
                        archive_path=None,
                        byte_size=source.stat().st_size,
                        sha256=sha256_file(source),
                        classification=EvidenceClass.WITHHELD_SENSITIVE,
                    ))
                    source.unlink()
                    continue
                destination = destination_root / Path(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
                moved.append(relative)

            manifest = build_manifest(
                archive_id=archive_id,
                source_root=source_root,
                archive_root=archive_root,
                archived_root=destination_root,
                original_paths=moved,
                withheld=withheld,
            )
            write_manifest(manifest, destination_root / "manifest.json")
            integrity_errors = verify_manifest(manifest, destination_root)
            if integrity_errors:
                raise QuarantineBlocked("; ".join(integrity_errors))

            for relative in ignored:
                cache_path = source_fs / Path(*relative.parts)
                cache_path.unlink(missing_ok=True)
            _prune_empty_directories(source_fs)
            return manifest
        except Exception:
            for relative in reversed(moved):
                destination = destination_root / Path(*relative.parts)
                source = source_fs / Path(*relative.parts)
                if destination.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    destination.replace(source)
            for relative in confirmed_paths:
                backup = backup_root / Path(*relative.parts)
                source = source_fs / Path(*relative.parts)
                if backup.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, source)
            shutil.rmtree(destination_root, ignore_errors=True)
            raise
```

This implementation blocks on non-ignored user files or ignored non-cache files, removes only recognized disposable caches after the manifest verifies, and restores confirmed-sensitive source files from a private Git-directory backup if any transaction step fails.

- [ ] **Step 4: Add the complete CLI**

Append:

```python
def _as_repo_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    if not normalized or normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        raise argparse.ArgumentTypeError("expected a repository-relative path without traversal")
    if ":" in PurePosixPath(normalized).parts[0]:
        raise argparse.ArgumentTypeError("absolute Windows paths are forbidden")
    return PurePosixPath(normalized)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan, quarantine, or verify legacy academic evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--repo-root", type=Path, required=True)
    scan_parser.add_argument("--source", type=_as_repo_path, required=True)

    quarantine_parser = subparsers.add_parser("quarantine")
    quarantine_parser.add_argument("--repo-root", type=Path, required=True)
    quarantine_parser.add_argument("--source", type=_as_repo_path, required=True)
    quarantine_parser.add_argument("--archive", type=_as_repo_path, required=True)
    quarantine_parser.add_argument("--archive-id", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=_as_repo_path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            tracked, findings = scan_tracked_tree(args.repo_root.resolve(), args.source)
            untracked = _git_untracked_files(args.repo_root.resolve(), args.source)
            ignored = _git_ignored_files(args.repo_root.resolve(), args.source)
            unsafe_ignored = [path for path in ignored if not _is_disposable_cache(path)]
            for finding in findings:
                print(f"{finding.path}:{finding.line}:{finding.rule}:{finding.severity}")
            print(
                f"tracked={len(tracked)} confirmed={sum(item.severity == 'confirmed' for item in findings)} "
                f"ambiguous={sum(item.severity == 'ambiguous' for item in findings)} "
                f"untracked={len(untracked)} unsafe_ignored={len(unsafe_ignored)}"
            )
            return 2 if (
                any(item.severity == "ambiguous" for item in findings)
                or untracked
                or unsafe_ignored
            ) else 0

        if args.command == "quarantine":
            manifest = quarantine_tracked_tree(
                repo_root=args.repo_root,
                source_root=args.source,
                archive_root=args.archive,
                archive_id=args.archive_id,
            )
            counts = Counter(entry.classification.value for entry in manifest.entries)
            print(f"archived={len(manifest.entries)} classifications={dict(sorted(counts.items()))}")
            return 0

        manifest_path = args.repo_root.resolve() / Path(*args.manifest.parts)
        manifest = load_manifest(manifest_path)
        archived_root = args.repo_root.resolve() / Path(*PurePosixPath(manifest.archive_root).parts)
        errors = verify_manifest(manifest, archived_root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"verified {len(manifest.entries)} entries")
        return 0
    except (OSError, subprocess.CalledProcessError, QuarantineBlocked, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

The supported commands are exactly:

```powershell
python -m academic_benchmark.archive_manifest scan --repo-root . --source academic_benchmark/yaem2026
python -m academic_benchmark.archive_manifest quarantine --repo-root . --source academic_benchmark/yaem2026 --archive archive/academic_benchmark/yaem2026_legacy --archive-id yaem2026_legacy
python -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/yaem2026_legacy/manifest.json
```

`scan` prints only counts plus `path:line:rule:severity`; `quarantine` prints entry/classification counts; `verify` prints `verified N entries` or redacted integrity errors. No command prints matched text.

- [ ] **Step 5: Run transaction tests and CLI help**

```powershell
python -m pytest academic_benchmark/tests/test_archive_manifest.py -q -p no:cacheprovider --tb=short
python -m academic_benchmark.archive_manifest --help
```

Expected: all archival tests pass and help lists `scan`, `quarantine`, and `verify`.

- [ ] **Step 6: Commit the transaction**

```powershell
git add academic_benchmark/archive_manifest.py academic_benchmark/tests/test_archive_manifest.py
git commit -m "feat(academic): add transactional legacy quarantine"
```

---

### Task 6: Preflight and Physically Archive YAEM

**Files:**
- Modify: `.gitignore`
- Create: `archive/academic_benchmark/yaem2026_legacy/QUARANTINE.md`
- Create: `archive/academic_benchmark/yaem2026_legacy/manifest.json`
- Move: the 159 currently tracked files under `academic_benchmark/yaem2026/**` to `archive/academic_benchmark/yaem2026_legacy/**`, except any confirmed sensitive entry, which is withheld.
- Modify: `archive/README.md`

**Interfaces:**
- Consumes: Task 5 CLI.
- Produces: byte-preserved archive, deterministic manifest, and no tracked active YAEM tree.

- [ ] **Step 1: Record the exact tracked inventory and branch state**

```powershell
git status --short --branch
$tracked = @(git ls-files -- academic_benchmark/yaem2026)
if ($tracked.Count -ne 159) { throw "YAEM inventory drift: expected 159, found $($tracked.Count)" }
$tracked | Set-Content -Encoding utf8NoBOM "$env:TEMP\yaem2026-tracked-before.txt"
```

Expected: branch is `codex/reconcile-native-protocol`; only intended Task 1-5 commits exist; inventory count is 159. If the count differs, stop and reconcile the plan with live Git state instead of forcing the move.

- [ ] **Step 2: Run the mandatory non-mutating sensitive preflight**

```powershell
python -m academic_benchmark.archive_manifest scan --repo-root . --source academic_benchmark/yaem2026
```

Expected: exit 0 with zero ambiguous findings. Confirmed findings, if any, are reported by path/rule only and will be withheld. Any ambiguous finding is a hard stop requiring user review; do not continue or stage archive content.

- [ ] **Step 3: Narrowly allow the YAEM archive in `.gitignore`**

Replace the archive ignore block with:

```gitignore
# Archive / legacy snapshots — not active source, excluded from codegraph index
.proposed_changes/
archive/*
!archive/README.md
!archive/docs/
!archive/docs/**
!archive/academic_benchmark/
archive/academic_benchmark/*
!archive/academic_benchmark/yaem2026_legacy/
!archive/academic_benchmark/yaem2026_legacy/**
scratch/
```

Expected: only the approved YAEM archive becomes trackable; future Bildiri allowlisting remains Package B.

- [ ] **Step 4: Run the quarantine transaction**

```powershell
python -m academic_benchmark.archive_manifest quarantine --repo-root . --source academic_benchmark/yaem2026 --archive archive/academic_benchmark/yaem2026_legacy --archive-id yaem2026_legacy
```

Expected: 159 manifest entries, consisting of archived files plus any `WITHHELD_SENSITIVE` entries; `academic_benchmark/yaem2026` contains no tracked files.

- [ ] **Step 5: Add the quarantine notice**

Create `archive/academic_benchmark/yaem2026_legacy/QUARANTINE.md`:

```markdown
# YAEM 2026 Legacy Evidence Quarantine

Status: historical archive; not executable evidence

This directory preserves the tracked bytes formerly located at
`academic_benchmark/yaem2026`. It is excluded from active packages, imports,
dataset discovery, benchmark execution, analysis, and current reports.

## Confirmed limitations

- Outputs derived from `student_matrix` are `INVALID` because the historical
  route construction omitted a real city from the optimized permutation.
- Historical statistical reports with invalid pairing are `INVALID`.
- Other generated results are `HISTORICAL_UNVERIFIED` unless a complete current
  provenance, fair-budget, environment, validation, and replay chain exists.
- Legacy source, configurations, presentations, and design notes are
  `REFERENCE_ONLY`; they may explain history but cannot support numerical claims.
- Historical `GWO-LKH` and `HHO-LKH` labels do not identify genuine LKH and must
  not be used by active studies.

## Permitted use

Use this archive only for provenance, design-history review, and reconstruction
of evaluated paths. Do not import its Python modules, execute its runners by
default, cite its numbers as current evidence, or relabel old results as valid.

`manifest.json` records the original path, archived path, byte size, SHA-256,
and evidence classification for each tracked source entry. A
`WITHHELD_SENSITIVE` entry intentionally has no archived path or secret content.
```

Do not add `QUARANTINE.md` as a manifest entry because it is new archival metadata, not a moved historical file.

- [ ] **Step 6: Update the archive index**

Add a YAEM entry to `archive/README.md` stating the archive path, quarantine date `2026-07-22`, manifest path, and the rule that no archived result is active scientific evidence.

- [ ] **Step 7: Verify byte inventory, checksums, and sensitive absence before staging**

```powershell
python -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/yaem2026_legacy/manifest.json
git ls-files -- academic_benchmark/yaem2026
git status --short
git check-ignore -v archive/academic_benchmark/yaem2026_legacy/manifest.json
```

Expected:
- verifier reports `verified 159 entries` counting withheld entries as metadata-only;
- active YAEM `git ls-files` output is empty;
- status shows deletions/renames plus the intended archive metadata and `.gitignore`/README edits;
- `git check-ignore` exits 1 for the manifest, proving it is not ignored.

Inspect `manifest.json` and confirm it contains no line text or secret values, only path, size, digest, and classification.

- [ ] **Step 8: Stage and inspect the archive-only diff**

```powershell
git add -A -- .gitignore archive/README.md archive/academic_benchmark/yaem2026_legacy academic_benchmark/yaem2026
git diff --cached --stat
git diff --cached --summary
git diff --cached --check
```

Expected: no file outside the stated scope is staged; Git reports renames for byte-identical files where detectable; `git diff --cached --check` exits 0. If any sensitive finding is staged, unstage the archive and stop.

- [ ] **Step 9: Commit the physical quarantine**

```powershell
git commit -m "chore(academic): quarantine legacy YAEM evidence"
```

---

### Task 7: Enforce Active Import and Distribution Boundaries

**Files:**
- Create: `academic_benchmark/tests/test_yaem_quarantine_boundary.py`
- Modify: `academic_benchmark/archive_manifest.py` only if verification needs a public helper already specified above.

**Interfaces:**
- Consumes: archive and manifest from Task 6; package discovery from setuptools; schema resources from Task 3.
- Produces: Gate A automated proof that legacy YAEM is not importable, referenced, packaged, or discoverable.

- [ ] **Step 1: Write the boundary test module**

Create:

```python
from __future__ import annotations

import ast
import json
from importlib.util import find_spec
from pathlib import Path

from setuptools.discovery import PEP420PackageFinder

from academic_benchmark.archive_manifest import (
    EvidenceClass,
    load_manifest,
    scan_sensitive_file,
    verify_manifest,
)


REPO = Path(__file__).resolve().parents[2]
ACTIVE_YAEM = REPO / "academic_benchmark" / "yaem2026"
ARCHIVE = REPO / "archive" / "academic_benchmark" / "yaem2026_legacy"


def _active_python_files():
    for root in (REPO / "academic_benchmark", REPO / "uniride_core", REPO / "optimizer_api"):
        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
                yield path


def test_legacy_yaem_package_is_absent_and_not_importable():
    assert not ACTIVE_YAEM.exists()
    assert find_spec("academic_benchmark.yaem2026") is None


def test_active_python_has_no_yaem_imports():
    violations = []
    for path in _active_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name == "yaem2026" or name.startswith("academic_benchmark.yaem2026") for name in names):
                violations.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert violations == []


def test_distribution_discovery_excludes_archive_and_yaem():
    packages = set(PEP420PackageFinder.find(str(REPO), include=["academic_benchmark*"]))
    assert not any("yaem2026" in package for package in packages)
    assert not any(package.startswith("archive") for package in packages)


def test_archive_manifest_covers_the_original_tracked_inventory_and_verifies():
    manifest = load_manifest(ARCHIVE / "manifest.json")
    assert manifest.schema_version == "uniride-archive/v1"
    assert len(manifest.entries) == 159
    assert len({entry.original_path for entry in manifest.entries}) == 159
    assert verify_manifest(manifest, ARCHIVE) == []
    assert {entry.classification for entry in manifest.entries} <= set(EvidenceClass)


def test_archive_contains_no_unmanifested_historical_files():
    manifest = load_manifest(ARCHIVE / "manifest.json")
    expected = {
        Path(entry.archive_path).relative_to(manifest.archive_root).as_posix()
        for entry in manifest.entries if entry.archive_path is not None
    }
    actual = {
        path.relative_to(ARCHIVE).as_posix()
        for path in ARCHIVE.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "QUARANTINE.md"}
    }
    assert actual == expected


def test_archive_rescan_has_no_sensitive_findings():
    findings = [
        finding
        for path in ARCHIVE.rglob("*")
        if path.is_file() and path.name != "manifest.json"
        for finding in scan_sensitive_file(path)
    ]
    assert findings == []


def test_manifest_has_no_sensitive_payload_fields():
    raw = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
    assert set(raw) == {"archive_id", "archive_root", "entries", "schema_version", "source_root"}
    assert all(set(entry) == {"archive_path", "byte_size", "classification", "original_path", "sha256"} for entry in raw["entries"])
```

- [ ] **Step 2: Run the boundary tests**

```powershell
python -m pytest academic_benchmark/tests/test_yaem_quarantine_boundary.py -q -p no:cacheprovider --tb=short
```

Expected: `7 passed`.

- [ ] **Step 3: Run the complete new Package A test set**

```powershell
python -m pytest academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_archive_manifest.py academic_benchmark/tests/test_yaem_quarantine_boundary.py -q -p no:cacheprovider --tb=short
```

Expected: all Package A tests pass with zero skips unless an existing platform-specific Git test is explicitly skipped with a reason.

- [ ] **Step 4: Commit boundary enforcement**

```powershell
git add academic_benchmark/tests/test_yaem_quarantine_boundary.py
git commit -m "test(academic): enforce YAEM quarantine boundaries"
```

---

### Task 8: Execute Gate A and Record the Exact Verification Result

**Files:**
- Modify: `WORKLOG.md`
- Do not modify generated benchmark artifacts.

**Interfaces:**
- Consumes: all Package A changes.
- Produces: exact, non-inflated verification evidence and a clean Package A boundary for Package B planning.

- [ ] **Step 1: Run schema and archive integrity checks**

```powershell
python -m academic_benchmark.contracts.export_schemas check
python -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/yaem2026_legacy/manifest.json
python -m pytest academic_benchmark/tests/test_manifest_contracts.py academic_benchmark/tests/test_archive_manifest.py academic_benchmark/tests/test_yaem_quarantine_boundary.py -q -p no:cacheprovider --tb=short
```

Expected: all exit 0; record exact pass/skip counts rather than copying the illustrative counts from this plan.

- [ ] **Step 2: Run the existing academic automated suite without cache artifacts**

```powershell
python -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short
```

Expected: all existing academic tests pass. If an optional environment issue occurs, separate the exact environment blocker from source defects and do not call Gate A green.

- [ ] **Step 3: Run packaging/import smoke checks**

```powershell
python -c "from importlib.resources import files; import academic_benchmark.contracts as c; assert c.StudyManifestV1; assert files('academic_benchmark.schemas').joinpath('study-v1.schema.json').is_file(); print('PACKAGE_OK')"
python -c "from importlib.util import find_spec; assert find_spec('academic_benchmark.yaem2026') is None; print('YAEM_NON_IMPORTABLE')"
```

Expected: `PACKAGE_OK` and `YAEM_NON_IMPORTABLE`.

- [ ] **Step 4: Audit the final diff and rescue-checkout boundary**

```powershell
git diff --check
git status --short --branch
git -C C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide status --short --branch
```

Expected: integration status contains only the pending WORKLOG entry; rescue checkout still contains the user's pre-existing dirty files and no Package A edits.

- [ ] **Step 5: Add an exact WORKLOG entry**

Append a dated `2026-07-22 — Package A: YAEM quarantine and contract foundation` entry containing:

- the physical archive path and manifest entry/classification counts;
- confirmed-sensitive withheld count without names or secret text in the prose (paths remain only in the manifest if approved);
- exact focused and full academic test commands and outcomes;
- schema/package/import smoke outcomes;
- explicit statement that no benchmark experiments ran;
- explicit statement that GitHub push remains deferred to Package D;
- any environment blockers, clearly separated from code defects.

Do not claim Gate A passed unless every required command above succeeded.

- [ ] **Step 6: Commit Gate A evidence**

```powershell
git add WORKLOG.md
git commit -m "docs: record Package A quarantine verification"
git status --short --branch
```

Expected: clean integration worktree, branch ahead of `origin/WIP`, no push performed.

---

## Gate A Acceptance Checklist

- [ ] Exactly the pre-move Git-tracked YAEM inventory is represented by the archive manifest.
- [ ] All non-withheld archived bytes reproduce their recorded byte size and SHA-256.
- [ ] Confirmed credentials, if any, are absent from staged archive content and represented only as `WITHHELD_SENSITIVE` metadata.
- [ ] No ambiguous sensitive finding remains unresolved.
- [ ] `academic_benchmark/yaem2026` is absent and non-importable.
- [ ] No active Python import references YAEM.
- [ ] Package discovery excludes YAEM and `archive/`.
- [ ] The three approved schemas have exact IDs, strict object contracts, path-traversal rejection, deterministic snapshots, and package-resource availability.
- [ ] Package A focused tests and the existing academic automated suite pass.
- [ ] No solver, registry, fairness, Bildiri, production API, frontend, dependency, or benchmark-output change appears in the diff.
- [ ] The rescue checkout is unchanged and GitHub publication remains deferred.

## Explicit Handoff Boundary

Stop after Gate A. Do not begin Bildiri extraction, canonical algorithm relocation, capability-catalog work, study-profile execution, statistical analysis, or publication. Those belong to Packages B, C, and D and require their own approved implementation plans.
