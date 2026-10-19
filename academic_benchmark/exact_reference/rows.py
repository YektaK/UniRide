"""The ``exact_reference_v1`` row contract (WP-E8 Task 3; design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 4;
DECISION_LOG A04, E09, E12).

One row is one solver result of the ``exact_reference_v1`` protocol: a Hamiltonian-cycle result of the WP-E7 TSP/ATSP
verification run, or a stage result of a WP-E3/WP-E4a wave campaign. Rows are typed so that they cannot be mistaken for
heuristic rows:

* there is no ``algorithm_id``, no ``evaluation_budget`` and no ``gap_*`` field, and extra fields are forbidden (gap
  columns belong to Package D);
* ``solver_name``/``solver_version``/``option_string`` are copied verbatim from the committed manifest;
* a row is ``optimal`` only because the solver said so; ``ub == reference_optimum`` never makes a row optimal;
* ``reference_optimum`` is the published TSPLIB value (source ``tsplib``) and nothing else (our own heuristic runs are not
  a source);
* ``ub_validated`` is true only after the independent Hamiltonian-cycle validator recomputed the tour length
  (``ub_validation_basis`` = ``independent_hamiltonian_validator``). Wave rows keep ``ub_validated = false`` with the basis
  ``certified_by_producing_run`` (owner decision OQ3, 2026-10-18): WP-E8 checks their schema and fingerprints only.

The status, stop-reason and stage vocabularies are the ones of ``protocol.py``; nothing is duplicated here.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from academic_benchmark.contracts.common import RepositoryRelativePath, Sha256Digest, StrictContract
from academic_benchmark.exact_reference import protocol

ROW_SCHEMA_VERSION = "uniride-exact-reference-row/v1"
SOLUTION_KINDS = ("hamiltonian_cycle", "vehicle_routes")
PROBLEM_CONTRACTS = ("TSP", "ATSP", "uniride_wave")
SOLVER_ROLES = ("primary", "verification")
MANIFEST_KINDS = ("tsp_reference", "wave_campaign")
UB_VALIDATION_BASES = ("independent_hamiltonian_validator", "certified_by_producing_run", "not_validated")
REFERENCE_SOURCES = ("tsplib",)

_Status = Literal[tuple(protocol.STATUS_LABELS)]
_StopReason = Literal[tuple(protocol.STOP_REASONS)]
_Stage = Literal[tuple(protocol.STAGES)]
_SolutionKind = Literal[SOLUTION_KINDS]
_ProblemContract = Literal[PROBLEM_CONTRACTS]
_SolverRole = Literal[SOLVER_ROLES]
_ManifestKind = Literal[MANIFEST_KINDS]
_UbBasis = Literal[UB_VALIDATION_BASES]
_ReferenceSource = Literal[REFERENCE_SOURCES]


class ExactReferenceSourceV1(StrictContract):
    """Where the row came from: a committed results directory and the sha256 of its manifest."""

    results_dir: RepositoryRelativePath
    manifest_kind: _ManifestKind
    manifest_sha256: Sha256Digest
    work_package: str = Field(min_length=1)
    git_commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")


class ExactReferenceRowV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": ROW_SCHEMA_VERSION}}

    row_schema_version: Literal["uniride-exact-reference-row/v1"]
    protocol: Literal["exact_reference_v1"]
    solution_kind: _SolutionKind
    problem_contract: _ProblemContract
    instance_id: str = Field(min_length=1)
    stage: Optional[_Stage] = None
    solver_role: _SolverRole
    solver_name: str = Field(min_length=1)
    solver_version: str = Field(min_length=1)
    option_string: str = Field(min_length=1)
    status: _Status
    stop_reason: Optional[_StopReason] = None
    lb: Optional[int] = Field(default=None, strict=True)
    ub: Optional[int] = Field(default=None, strict=True)
    reference_optimum: Optional[int] = Field(default=None, strict=True)
    reference_optimum_source: Optional[_ReferenceSource] = None
    timing_dependent: bool = Field(strict=True)
    wall_seconds: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    ub_validated: bool = Field(strict=True)
    ub_validation_basis: _UbBasis
    source: ExactReferenceSourceV1

    @model_validator(mode="after")
    def _invariants(self) -> "ExactReferenceRowV1":
        problems = row_invariant_errors(self)
        if problems:
            raise ValueError("; ".join(problems))
        return self


def row_invariant_errors(row: ExactReferenceRowV1) -> list:
    """Cross-field rules of the contract (empty list: all hold). Kept separate so a reader can name them."""
    errors = []
    if row.protocol != protocol.PROTOCOL_ID:
        errors.append(f"protocol must equal {protocol.PROTOCOL_ID!r}")
    # solution kind and problem contract
    if row.solution_kind == "hamiltonian_cycle":
        if row.problem_contract not in ("TSP", "ATSP"):
            errors.append("hamiltonian_cycle rows belong to the TSP or ATSP contract")
        if row.stage is not None:
            errors.append("a hamiltonian_cycle row has no stage")
    else:
        if row.problem_contract != "uniride_wave":
            errors.append("vehicle_routes rows belong to the uniride_wave contract")
        if row.stage is None:
            errors.append("a vehicle_routes row needs a stage")
    if row.problem_contract == "uniride_wave" and row.solution_kind != "vehicle_routes":
        errors.append("the uniride_wave contract is vehicle_routes only")
    # stop reason and timing (rules of protocol.validate_stage_row)
    if row.stop_reason is None and row.solver_role == "primary" and row.status not in protocol._NO_RUN_STATUSES:
        errors.append(f"stop_reason missing for status {row.status!r}")
    if row.status == "optimal" and row.stop_reason not in (None, "optimal"):
        errors.append("status optimal needs stop_reason optimal")
    if row.stop_reason in protocol.TIMING_STOP_REASONS and not row.timing_dependent:
        errors.append(f"a {row.stop_reason} stop must be timing_dependent: true")
    # bounds
    if row.status == "optimal":
        if row.lb is None or row.ub is None:
            errors.append("an optimal row carries both lb and ub")
        elif not 0 <= row.ub - row.lb < 1:
            errors.append(f"an optimal row needs lb <= ub and ub - lb < 1 (lb {row.lb}, ub {row.ub})")
    elif row.status == "feasible_with_gap":
        if row.ub is None:
            errors.append("a feasible_with_gap row carries an incumbent ub")
        elif row.lb is not None and row.lb > row.ub:
            errors.append(f"lb {row.lb} exceeds ub {row.ub}")
    elif row.status in ("bound_only", "infeasible_proven") and row.ub is not None:
        errors.append(f"a {row.status} row has no incumbent: ub must be null")
    # published reference
    if (row.reference_optimum is None) != (row.reference_optimum_source is None):
        errors.append("reference_optimum and reference_optimum_source are both set or both null")
    if row.solution_kind == "vehicle_routes" and row.reference_optimum is not None:
        errors.append("wave rows carry no published reference optimum")
    # validation basis
    if row.ub_validated != (row.ub_validation_basis == "independent_hamiltonian_validator"):
        errors.append("ub_validated is true exactly when the basis is independent_hamiltonian_validator")
    if row.ub_validated and (row.solution_kind != "hamiltonian_cycle" or row.ub is None):
        errors.append("only a hamiltonian_cycle ub can be validated by the independent validator")
    if row.solution_kind == "vehicle_routes" and row.ub_validation_basis != "certified_by_producing_run":
        errors.append("wave rows are certified_by_producing_run (OQ3) and never validated here")
    if row.solution_kind == "hamiltonian_cycle" and row.ub_validation_basis == "certified_by_producing_run":
        errors.append("a hamiltonian_cycle row is validated by the independent validator or not validated")
    errors.extend(protocol.private_data_errors(row.model_dump(mode="json")))
    return errors
