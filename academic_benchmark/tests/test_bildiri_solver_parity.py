"""Freeze deterministic Bildiri GWO/HHO behavior before solver relocation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Literal, Mapping, TypedDict

import numpy as np
import pytest

from academic_benchmark.bildiri2026.core import numba_accel as _legacy_nb
from academic_benchmark.bildiri2026.core.gwo_solver import (
    GWOOptimizer as LegacyGWOOptimizer,
)
from academic_benchmark.bildiri2026.core.hho_solver import (
    HHOOptimizer as LegacyHHOOptimizer,
)
from uniride_core.algorithms import numba_accel as _canonical_nb
from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import (
    GWOOptimizer as CanonicalGWOOptimizer,
)
from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import (
    HHOOptimizer as CanonicalHHOOptimizer,
)

FIXTURE_SCHEMA_VERSION = "uniride-bildiri-parity/v1"
FIXTURE_PATH = Path(__file__).with_name("fixtures") / "bildiri_gwo_hho_v1.json"
SEED = 1729
EVALUATION_BUDGET = 100


class ParityRecord(TypedDict):
    directed: bool
    normalized_tour: list[int]
    tour_length: float
    iterations: int
    objective_evaluations: int
    evaluation_budget: int
    budget_terminated: bool
    variant: Literal["pure", "memetic_2opt"]
    observed_execution_backend: str
    seed: int


def _symmetric_matrix() -> list[list[float]]:
    return [
        [0, 7, 9, 11, 8, 10],
        [7, 0, 6, 5, 12, 9],
        [9, 6, 0, 4, 7, 13],
        [11, 5, 4, 0, 6, 8],
        [8, 12, 7, 6, 0, 5],
        [10, 9, 13, 8, 5, 0],
    ]


def _directed_matrix() -> list[list[float]]:
    return [
        [0, 9, 4, 12, 7, 15],
        [3, 0, 11, 5, 14, 6],
        [13, 8, 0, 10, 2, 9],
        [6, 16, 3, 0, 8, 4],
        [11, 5, 17, 1, 0, 12],
        [7, 14, 6, 13, 3, 0],
    ]


def closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    return sum(
        float(matrix[node][tour[(index + 1) % len(tour)]])
        for index, node in enumerate(tour)
    )


def normalize_cycle(tour: list[int], *, directed: bool) -> tuple[int, ...]:
    route = tuple(tour)
    rotations = [route[index:] + route[:index] for index in range(len(route))]
    candidates = rotations
    if not directed:
        reversed_route = tuple(reversed(route))
        candidates += [
            reversed_route[index:] + reversed_route[:index]
            for index in range(len(route))
        ]
    return min(candidates)


CASE_SPECS = (
    ("gwo_pure_symmetric_tsp", "gwo", "pure", False),
    ("gwo_pure_directed_atsp", "gwo", "pure", True),
    ("gwo_memetic_2opt_symmetric_tsp", "gwo", "memetic_2opt", False),
    ("gwo_memetic_2opt_directed_atsp", "gwo", "memetic_2opt", True),
    ("hho_pure_symmetric_tsp", "hho", "pure", False),
    ("hho_pure_directed_atsp", "hho", "pure", True),
    ("hho_memetic_2opt_symmetric_tsp", "hho", "memetic_2opt", False),
    ("hho_memetic_2opt_directed_atsp", "hho", "memetic_2opt", True),
)

MATHEMATICAL_AND_ACCOUNTING_FIELDS = (
    "directed",
    "normalized_tour",
    "tour_length",
    "iterations",
    "objective_evaluations",
    "evaluation_budget",
    "budget_terminated",
    "variant",
    "seed",
)


def _validate_record(record: Mapping[str, Any], *, matrix_size: int) -> None:
    """Reject incomplete or non-replayable capture records before persistence."""
    expected_keys = set(ParityRecord.__annotations__)
    if set(record) != expected_keys:
        raise ValueError(f"record keys must be exactly {sorted(expected_keys)}")

    if not isinstance(record["directed"], bool):
        raise ValueError("capture directed flag must be bool")

    normalized_tour = record["normalized_tour"]
    if not isinstance(normalized_tour, list) or len(normalized_tour) != matrix_size:
        raise ValueError("capture route must contain every matrix node exactly once")
    if any(not isinstance(node, int) or isinstance(node, bool) for node in normalized_tour):
        raise ValueError("capture route nodes must be non-bool integers")
    if set(normalized_tour) != set(range(matrix_size)):
        raise ValueError("capture route must contain every matrix node exactly once")

    cost = record["tour_length"]
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or not math.isfinite(cost):
        raise ValueError("capture cost must be finite")

    iterations = record["iterations"]
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 0:
        raise ValueError("capture iterations must be a non-bool integer >= 0")

    evaluations = record["objective_evaluations"]
    if not isinstance(evaluations, int) or isinstance(evaluations, bool) or evaluations <= 0:
        raise ValueError("capture objective evaluation count must be positive")

    evaluation_budget = record["evaluation_budget"]
    if (
        not isinstance(evaluation_budget, int)
        or isinstance(evaluation_budget, bool)
        or evaluation_budget != EVALUATION_BUDGET
    ):
        raise ValueError(f"capture evaluation budget must be {EVALUATION_BUDGET}")

    if not isinstance(record["budget_terminated"], bool):
        raise ValueError("capture budget_terminated flag must be bool")

    variant = record["variant"]
    if variant not in {"pure", "memetic_2opt"}:
        raise ValueError("capture variant must be pure or memetic_2opt")

    backend = record["observed_execution_backend"]
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("capture execution backend label is required")

    seed = record["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or seed != SEED:
        raise ValueError(f"capture seed must be {SEED}")

def test_capture_record_rejects_missing_backend_label() -> None:
    record: ParityRecord = {
        "directed": False,
        "normalized_tour": [0, 1, 2],
        "tour_length": 3.0,
        "iterations": 1,
        "objective_evaluations": 1,
        "evaluation_budget": 100,
        "budget_terminated": False,
        "variant": "pure",
        "observed_execution_backend": "",
        "seed": 1729,
    }

    with pytest.raises(ValueError, match="backend"):
        _validate_record(record, matrix_size=3)



def _valid_record() -> ParityRecord:
    return {
        "directed": False,
        "normalized_tour": [0, 1, 2],
        "tour_length": 3.0,
        "iterations": 1,
        "objective_evaluations": 1,
        "evaluation_budget": 100,
        "budget_terminated": False,
        "variant": "pure",
        "observed_execution_backend": "numba-objective",
        "seed": 1729,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("directed", 1, "directed"),
        ("normalized_tour", [False, 1, 2], "route"),
        ("normalized_tour", [0, 1, 1], "route"),
        ("tour_length", float("inf"), "finite"),
        ("iterations", -1, "iterations"),
        ("objective_evaluations", True, "objective"),
        ("evaluation_budget", True, "budget"),
        ("budget_terminated", "false", "budget_terminated"),
        ("variant", "other", "variant"),
        ("seed", 0, "seed"),
    ],
)
def test_capture_record_rejects_complete_contract(
    field: str, value: object, message: str
) -> None:
    record = _valid_record()
    record[field] = value
    with pytest.raises(ValueError, match=message):
        _validate_record(record, matrix_size=3)


def test_read_fixture_rejects_forbidden_record_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["records"]["gwo_pure_symmetric_tsp"]["elapsed_ms"] = 1.0
    malformed_fixture = tmp_path / "malformed_fixture.json"
    malformed_fixture.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(__import__(__name__), "FIXTURE_PATH", malformed_fixture)

    with pytest.raises(ValueError, match="keys"):
        _read_fixture()
def _require_working_jit() -> None:
    """Skip only before JIT is available; compilation problems must fail."""
    if not _legacy_nb.NUMBA_AVAILABLE or not _canonical_nb.NUMBA_AVAILABLE:
        pytest.skip("Numba JIT unavailable: parity is not JIT-validated in this interpreter")

    matrix = np.ascontiguousarray(
        np.array([[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]]),
        dtype=np.float64,
    )
    route = np.ascontiguousarray(np.array([0, 1, 2], dtype=np.int64))
    for backend in (_legacy_nb, _canonical_nb):
        assert backend._calculate_tour_length_atsp_numba(route, matrix) == pytest.approx(9.0)
        assert backend._calculate_tour_length_atsp_numba.nopython_signatures, (
            "Numba reported available but the matrix objective did not compile in "
            "nopython mode"
        )


def _solver_for_case(
    solver_name: str,
    variant: Literal["pure", "memetic_2opt"],
    *,
    implementation: Literal["legacy", "canonical"] = "legacy",
):
    common = {
        "max_iterations": 1,
        "random_seed": SEED,
        "polish_enabled": variant == "memetic_2opt",
        "polish_interval": 1,
        "polish_iters": 1,
        "final_polish_iters": 1,
        "evaluation_budget": EVALUATION_BUDGET,
    }
    solver_classes = {
        "legacy": {"gwo": LegacyGWOOptimizer, "hho": LegacyHHOOptimizer},
        "canonical": {
            "gwo": CanonicalGWOOptimizer,
            "hho": CanonicalHHOOptimizer,
        },
    }
    if solver_name == "gwo":
        return solver_classes[implementation][solver_name](pack_size=4, **common)
    if solver_name == "hho":
        return solver_classes[implementation][solver_name](
            hawks=4, dive_count=0, **common
        )
    raise ValueError(f"unknown Bildiri solver {solver_name!r}")


def _capture_case(
    solver_name: str,
    variant: Literal["pure", "memetic_2opt"],
    directed: bool,
    *,
    implementation: Literal["legacy", "canonical"] = "legacy",
) -> ParityRecord:
    matrix = _directed_matrix() if directed else _symmetric_matrix()
    result = _solver_for_case(
        solver_name, variant, implementation=implementation
    ).solve_with_matrix(
        matrix, closed_tsp=True, recalculate=False
    )

    assert len(result.tour) == len(matrix)
    assert set(result.tour) == set(range(len(matrix)))
    assert result.tour_length == pytest.approx(closed_cost(result.tour, matrix), abs=0.0)

    extra_stats = result.extra_stats
    record: ParityRecord = {
        "directed": directed,
        "normalized_tour": list(normalize_cycle(result.tour, directed=directed)),
        "tour_length": float(result.tour_length),
        "iterations": int(result.iterations),
        "objective_evaluations": int(extra_stats["objective_evaluations"]),
        "evaluation_budget": int(extra_stats["evaluation_budget"]),
        "budget_terminated": bool(extra_stats["budget_terminated"]),
        "variant": str(extra_stats["variant"]),
        "observed_execution_backend": str(extra_stats.get("execution_backend", "")),
        "seed": int(result.seed),
    }
    _validate_record(record, matrix_size=len(matrix))
    return record


def test_capture_case_uses_solver_reported_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tour = list(range(6))

    class FakeSolver:
        def solve_with_matrix(self, *_args: object, **_kwargs: object) -> object:
            return type(
                "FakeResult",
                (),
                {
                    "tour": tour,
                    "tour_length": closed_cost(tour, _symmetric_matrix()),
                    "iterations": 1,
                    "extra_stats": {
                        "objective_evaluations": 1,
                        "evaluation_budget": EVALUATION_BUDGET,
                        "budget_terminated": False,
                        "variant": "memetic_2opt",
                        "execution_backend": "python",
                    },
                    "seed": SEED,
                },
            )()

    monkeypatch.setitem(
        globals(), "_solver_for_case", lambda *_args, **_kwargs: FakeSolver()
    )

    record = _capture_case("gwo", "pure", False)

    assert record["variant"] == "memetic_2opt"


def _capture_all_cases() -> dict[str, ParityRecord]:
    _require_working_jit()
    return {
        case_name: _capture_case(solver_name, variant, directed)
        for case_name, solver_name, variant, directed in CASE_SPECS
    }


def _fixture_payload(records: Mapping[str, ParityRecord]) -> dict[str, object]:
    expected_names = {case_name for case_name, *_ in CASE_SPECS}
    if set(records) != expected_names:
        raise ValueError("fixture must contain exactly the eight named Bildiri cases")
    return {"schema_version": FIXTURE_SCHEMA_VERSION, "records": dict(records)}


def _write_capture(path: Path) -> None:
    payload = _fixture_payload(_capture_all_cases())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if set(payload) != {"schema_version", "records"}:
        raise ValueError("fixture top-level keys are invalid")
    if payload["schema_version"] != FIXTURE_SCHEMA_VERSION:
        raise ValueError("fixture schema version is invalid")
    records = payload["records"]
    if not isinstance(records, dict):
        raise ValueError("fixture records must be an object")
    if set(records) != {case_name for case_name, *_ in CASE_SPECS}:
        raise ValueError("fixture must contain exactly the eight named Bildiri cases")

    for case_name, _solver_name, variant, directed in CASE_SPECS:
        record = records[case_name]
        if not isinstance(record, Mapping):
            raise ValueError(f"fixture record {case_name} must be an object")
        _validate_record(record, matrix_size=6)
        if record["directed"] is not directed:
            raise ValueError(f"fixture record {case_name} has inconsistent directed metadata")
        if record["variant"] != variant:
            raise ValueError(f"fixture record {case_name} has inconsistent variant metadata")
    return payload


@pytest.mark.parametrize("case_name,solver_name,variant,directed", CASE_SPECS)
def test_fixed_seed_bildiri_solver_matches_golden_fixture(
    case_name: str,
    solver_name: str,
    variant: Literal["pure", "memetic_2opt"],
    directed: bool,
) -> None:
    """The legacy solver must preserve its deterministic direct-matrix output."""
    _require_working_jit()
    expected = _read_fixture()["records"][case_name]
    actual = _capture_case(solver_name, variant, directed)
    for field in ParityRecord.__annotations__:
        assert actual[field] == expected[field]


@pytest.mark.parametrize("case_name,solver_name,variant,directed", CASE_SPECS)
def test_relocated_solver_preserves_math_with_runtime_backend(
    case_name: str,
    solver_name: str,
    variant: Literal["pure", "memetic_2opt"],
    directed: bool,
) -> None:
    """Canonical math stays frozen while runtime metadata supersedes provenance."""
    _require_working_jit()
    expected = _read_fixture()["records"][case_name]
    legacy = _capture_case(solver_name, variant, directed, implementation="legacy")
    canonical = _capture_case(
        solver_name, variant, directed, implementation="canonical"
    )
    for field in MATHEMATICAL_AND_ACCOUNTING_FIELDS:
        assert legacy[field] == expected[field], (case_name, field)
        assert canonical[field] == expected[field], (case_name, field)

    assert legacy["observed_execution_backend"] == expected[
        "observed_execution_backend"
    ]
    expected_polish = "python" if variant == "memetic_2opt" else "none"
    assert canonical["observed_execution_backend"] == (
        f"objective=numba;polish={expected_polish}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    _write_capture(args.capture)


if __name__ == "__main__":
    main()
