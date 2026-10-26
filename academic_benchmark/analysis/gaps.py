"""Gap columns against the exact reference (Gate D, D-06; plan 2026-10-23 section 3; DECISION_LOG E09, E10, E12, A18 OQ-6).

The response variable of both analysis plans is the relative gap to the exact reference in percent, ``100 * (cost - ref) / ref``
(A18 OQ-6 a). ``ref`` is the proven optimum of the ``exact_reference_v1`` TSP/ATSP reference (WP-E7 stage 1, read and validated by
``academic_benchmark.exact_reference.reader``), joined to a heuristic row by the normalised TSPLIB problem name (A17 C-11:
``fairness.normalize_problem``), never by file name or dataset id.

Rules that keep the reference a reference:

* exact rows are values of a ``ExactReferenceTable``, never data rows: ``add_gap_columns`` refuses exact, union-day and joint-day
  rows (``protocol_registry.assert_rankable``) and rows of two pooling groups (``assert_single_pooling_group``, called first);
* a gap exists only for a *proven* optimum of an independently validated tour whose value equals the published TSPLIB optimum;
  an instance without one gets ``None`` and a reason, never the database value (``problem.optimal``) or the published value;
* the pilots' own ``gap_pct`` / ``optimum`` columns (computed from ``problem.optimal``) are left untouched and are not reused;
  a row ``optimum`` that differs from the exact reference blocks (no silent choice);
* the module reads committed files only (through the reader), writes nothing and opens no database.

Nothing here is a statistic: ranking, tests and summaries are D-05 and D-07, which call this module for the response column.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.exact_reference import reader
from academic_benchmark.analysis.problem_contract import ProblemContractError, same_problem_contract
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.protocol_registry import assert_rankable, assert_single_pooling_group

GAP_COLUMN = "gap_to_exact_reference"
GAP_UNIT = "percent"
GAP_REASON_COLUMN = "gap_missing_reason"
REFERENCE_VALUE_COLUMN = "exact_reference_value"
GAP_UNIT_COLUMN = "gap_unit"
TSPLIB_DATA_RELATIVE = ("academic_benchmark", "tsplib_data")
COST_FIELD = "objective_cost"


class GapColumnError(ValueError):
    """A gap cannot be computed without a silent choice (the message says why)."""


class ReferenceCrossCheckError(GapColumnError):
    """The exact reference disagrees with another source of the same optimum, or is missing for a study instance."""


@dataclass(frozen=True)
class ExactReferenceValue:
    """The proven optimum of one instance, with the provenance of the row it came from."""

    instance_id: str
    value: int
    published_optimum: int
    problem_contract: str  # "TSP" or "ATSP"
    solver_name: str
    solver_version: str
    results_dir: str
    manifest_sha256: str
    ub_validated: bool


@dataclass(frozen=True)
class ExactReferenceTable:
    """Proven optima by normalised instance identity (``values``) and the reason an instance has none (``unproven``)."""

    values: Mapping[str, ExactReferenceValue] = field(default_factory=dict)
    unproven: Mapping[str, str] = field(default_factory=dict)

    def lookup(self, identity: str) -> tuple:
        """``(value, None)`` for a proven optimum, ``(None, reason)`` otherwise."""
        entry = self.values.get(identity)
        if entry is not None:
            return entry, None
        if identity in self.unproven:
            return None, self.unproven[identity]
        return None, f"no exact reference for instance {identity!r}"


def relative_gap_percent(cost: Any, reference: Any) -> float:
    """``100 * (cost - reference) / reference``; refuses a non-finite or negative cost and a non-positive reference."""
    for name, value in (("cost", cost), ("reference", reference)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise GapColumnError(f"gap {name} must be a finite number, got {value!r}")
    if reference <= 0:
        raise GapColumnError(f"the exact reference must be positive, got {reference!r}")
    if cost < 0:
        raise GapColumnError(f"a tour cost cannot be negative, got {cost!r}")
    return (float(cost) - float(reference)) / float(reference) * 100.0


def build_reference_table(sets: Iterable[Any]) -> ExactReferenceTable:
    """The reference table of the TSP/ATSP reference sets (``ExactReferenceSet`` of manifest kind ``tsp_reference``).

    Only ``primary`` Hamiltonian-cycle rows count. A row gives a value only when its status is ``optimal``, its tour was
    independently validated (``ub_validated``) and its ``ub`` equals the published TSPLIB optimum (``reference_optimum``); a
    difference raises ``ReferenceCrossCheckError``. Two sets that disagree on an instance raise. Wave campaigns and union-day
    results have no gap reference and are skipped; HiGHS verification rows never give a value."""
    values: dict = {}
    unproven: dict = {}
    for loaded in sets:
        if loaded.manifest_kind != reader.KIND_TSP:
            continue
        for row in loaded.rows:
            if row.solver_role != "primary" or row.solution_kind != "hamiltonian_cycle":
                continue
            identity = normalize_problem(row.instance_id)
            if row.status != "optimal":
                unproven.setdefault(
                    identity,
                    f"the exact reference for instance {identity!r} is not a proven optimum (status {row.status!r}); "
                    "no gap is defined against an unproven value",
                )
                continue
            if row.ub is None or row.reference_optimum is None or row.ub != row.reference_optimum:
                raise ReferenceCrossCheckError(
                    f"{identity}: the proven optimum {row.ub!r} differs from the published optimum {row.reference_optimum!r} (blocking)"
                )
            if not row.ub_validated:
                raise ReferenceCrossCheckError(
                    f"{identity}: the tour of the exact reference was not validated by the independent Hamiltonian-cycle validator"
                )
            entry = ExactReferenceValue(
                instance_id=row.instance_id, value=row.ub, published_optimum=row.reference_optimum,
                problem_contract=row.problem_contract, solver_name=row.solver_name, solver_version=row.solver_version,
                results_dir=loaded.results_dir, manifest_sha256=loaded.manifest_sha256, ub_validated=True,
            )
            earlier = values.get(identity)
            if earlier is not None:
                try:
                    same_contract = same_problem_contract(earlier.problem_contract, entry.problem_contract)
                except ProblemContractError as exc:
                    raise ReferenceCrossCheckError(
                        f"{identity}: reference contract {earlier.problem_contract!r} ({earlier.results_dir}) against "
                        f"{entry.problem_contract!r} ({entry.results_dir}): {exc}"
                    ) from exc
                if earlier.value != entry.value or not same_contract:
                    raise ReferenceCrossCheckError(
                        f"{identity}: two reference sets disagree ({earlier.results_dir}: {earlier.value}, {entry.results_dir}: {entry.value})"
                    )
            values.setdefault(identity, entry)
    for identity in values:
        unproven.pop(identity, None)
    return ExactReferenceTable(values=dict(sorted(values.items())), unproven=dict(sorted(unproven.items())))


def load_reference_table(repo_root: Any) -> ExactReferenceTable:
    """Reference table of the committed ``tsp_reference`` results listed in ``results_index.json`` (no glob discovery).

    Each directory is loaded with ``load_exact_reference`` (every output sha256 and the manifest checked), its manifest sha256
    must equal the index entry, and the independent validator recomputes every primary tour length from the tracked dataset
    artifacts (``validate_hamiltonian_rows``); any refusal propagates as ``ExactReferenceRefused``."""
    root = Path(repo_root)
    dataset_root = root.joinpath(*TSPLIB_DATA_RELATIVE)
    sets: List[Any] = []
    for entry in reader.read_index(root):
        if entry.get("manifest_kind") != reader.KIND_TSP:
            continue
        loaded = reader.load_exact_reference(entry["results_dir"], repo_root=root)
        if loaded.manifest_sha256 != entry.get("manifest_sha256") or len(loaded.rows) != entry.get("rows"):
            raise reader.ExactReferenceRefused(f"{entry['results_dir']}: manifest sha256 or row count differs from results_index.json")
        sets.append(reader.validate_hamiltonian_rows(loaded, dataset_root=dataset_root, repo_root=root))
    if not sets:
        raise reader.ExactReferenceRefused("results_index.json lists no tsp_reference results: there is no gap reference")
    return build_reference_table(sets)


def _identity(problem: Any) -> str:
    if not isinstance(problem, str) or not problem.strip():
        raise GapColumnError("row has no problem name (the TSPLIB identity of the instance)")
    return normalize_problem(problem)


def _check_plan(plan: Any) -> str:
    """The unit of the gap column, read from the analysis plan's declared response and exact-reference link."""
    if not isinstance(plan, AnalysisPlanV1):
        raise GapColumnError(f"the gap columns are defined by an AnalysisPlanV1, not {type(plan).__name__}")
    if plan.response.variable != "relative_gap_to_exact_reference" or plan.response.unit != GAP_UNIT:
        raise GapColumnError("the analysis plan's response is not the relative gap to the exact reference in percent")
    link = plan.exact_reference
    if (link.reader, link.join_identity, link.pooling) != ("exact_reference_v1", "normalised_tsplib_problem_name", "reference_only"):
        raise GapColumnError("the analysis plan's exact-reference link is not (exact_reference_v1, normalised name, reference_only)")
    return plan.response.unit


def _with_reason(row: Mapping[str, Any], unit: str, reason: str, value: Optional[int] = None) -> dict:
    out = dict(row)
    out.update({GAP_COLUMN: None, GAP_UNIT_COLUMN: unit, REFERENCE_VALUE_COLUMN: value, GAP_REASON_COLUMN: reason})
    return out


def add_gap_columns(rows: Iterable[Any], table: ExactReferenceTable, *, plan: AnalysisPlanV1) -> List[dict]:
    """Copies of ``rows`` with ``gap_to_exact_reference`` (percent), ``gap_unit``, ``exact_reference_value`` and
    ``gap_missing_reason``; the input rows are not modified.

    Order of the guards: ``assert_single_pooling_group`` (fixed, native and exact rows never meet), then ``assert_rankable``
    (exact, union-day and joint-day rows are references, never data), then per row. A failed run, or an instance without a
    proven exact optimum, gets a ``None`` gap with a reason; a valid row without a finite ``objective_cost``, an existing gap
    column, a row ``optimum`` or ``problem_type`` that differs from the reference all raise ``GapColumnError``."""
    unit = _check_plan(plan)
    items = list(rows)
    assert_single_pooling_group(items)
    assert_rankable(items)
    out: List[dict] = []
    for row in items:
        for column in (GAP_COLUMN, GAP_UNIT_COLUMN, REFERENCE_VALUE_COLUMN, GAP_REASON_COLUMN):
            if column in row:
                raise GapColumnError(f"row already has a {column!r} column; gap columns are never overwritten ({GAP_COLUMN})")
        identity = _identity(row.get("problem"))
        if row.get("record_kind") == "failed_run" or row.get("validation_status") == "failed":
            out.append(_with_reason(row, unit, "failed run: no tour cost, so no gap"))
            continue
        cost = row.get(COST_FIELD)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(float(cost)):
            raise GapColumnError(f"{identity}: a valid row needs a finite numeric {COST_FIELD}, got {cost!r}")
        entry, reason = table.lookup(identity)
        if entry is None:
            out.append(_with_reason(row, unit, reason))
            continue
        declared = row.get("problem_type")
        if declared is not None:
            # A20 L10: rows store the lowercase spelling, the reference the uppercase contract; compare canonical values
            try:
                same = same_problem_contract(declared, entry.problem_contract)
            except ProblemContractError as exc:
                raise GapColumnError(f"{identity}: row problem type {declared!r} against the exact reference contract {entry.problem_contract!r}: {exc}") from exc
            if not same:
                raise GapColumnError(
                    f"{identity}: row problem type {declared!r} differs from the exact reference contract {entry.problem_contract!r}"
                )
        optimum = row.get("optimum")
        if isinstance(optimum, (int, float)) and not isinstance(optimum, bool) and not math.isclose(float(optimum), entry.value, rel_tol=0.0, abs_tol=1e-9):
            raise GapColumnError(
                f"{identity}: the row optimum {optimum!r} differs from the exact reference {entry.value} (blocking, no silent choice)"
            )
        gap = relative_gap_percent(cost, entry.value)
        converted = dict(row)
        converted.update({GAP_COLUMN: gap, GAP_UNIT_COLUMN: unit, REFERENCE_VALUE_COLUMN: entry.value, GAP_REASON_COLUMN: None})
        out.append(converted)
    return out


def _same_number(left: Any, right: Any) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-9)


def cross_check_study_datasets(table: ExactReferenceTable, datasets: Iterable[Any]) -> List[str]:
    """Normalised identities of the study's datasets whose exact reference was confirmed by the dataset manifest.

    Each ``ResolvedDataset`` (``studies.service.resolve_datasets``: the instance name is the NAME header of the checksummed
    artifact) must have a proven exact optimum of the same problem contract, and its manifest ``best_known`` must be an
    ``optimal`` record with the same value (the manifest records the published TSPLIB optimum). Any difference, a missing
    reference or a ``best_known`` that is not an optimum raises ``ReferenceCrossCheckError``."""
    checked = []
    for dataset in datasets:
        identity = _identity(dataset.problem_name)
        entry, reason = table.lookup(identity)
        if entry is None:
            raise ReferenceCrossCheckError(f"{dataset.dataset_id}: {reason}")
        manifest = dataset.manifest
        try:
            same = same_problem_contract(manifest.problem_type, entry.problem_contract)
        except ProblemContractError as exc:
            raise ReferenceCrossCheckError(
                f"{dataset.dataset_id}: manifest problem type {manifest.problem_type!r} against the reference {entry.problem_contract!r}: {exc}"
            ) from exc
        if not same:
            raise ReferenceCrossCheckError(
                f"{dataset.dataset_id}: manifest problem type {manifest.problem_type!r} differs from the reference {entry.problem_contract!r}"
            )
        best = manifest.best_known
        if best.status != "optimal" or best.value is None:
            raise ReferenceCrossCheckError(
                f"{dataset.dataset_id}: manifest best_known is {best.status!r}, so it cannot confirm the exact reference {entry.value}"
            )
        if not _same_number(best.value, entry.value):
            raise ReferenceCrossCheckError(
                f"{dataset.dataset_id}: manifest best_known {best.value} differs from the exact reference {entry.value} (blocking)"
            )
        checked.append(identity)
    return sorted(set(checked))


def cross_check_problem_optimal(table: ExactReferenceTable, optima: Mapping[str, Any]) -> List[str]:
    """Identities whose ``problem.optimal`` (database value, given as ``{problem name: value}``) equals the exact reference.

    The caller reads the database; this module does not. A difference or a missing reference raises
    ``ReferenceCrossCheckError``."""
    checked = []
    for name, value in optima.items():
        identity = _identity(name)
        entry, reason = table.lookup(identity)
        if entry is None:
            raise ReferenceCrossCheckError(f"{name}: {reason}")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not _same_number(value, entry.value):
            raise ReferenceCrossCheckError(f"{identity}: problem.optimal {value!r} differs from the exact reference {entry.value} (blocking)")
        checked.append(identity)
    return sorted(checked)
