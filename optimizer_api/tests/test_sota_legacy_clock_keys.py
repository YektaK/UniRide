"""MT6-03 (audit H11): old SOTA request keys for one release.

``time_limit`` is mapped to ``deadline_seconds``; ``ls_time_limit`` is accepted
and ignored (there is no per-layer clock any more) and the ignore is recorded.
"""

import pytest

from optimizer_api.compute_policy import HARD_CEILINGS, apply_compute_policy
from optimizer_api.models.schemas import OptimizationRequest, PolicyValueSource
from optimizer_api.strategies.canonical import resolve_strategy
from optimizer_api.strategies.sota_config_utils import (
    merge_sota_config,
    split_legacy_sota_keys,
)
from uniride_core.adapters.sota_tsp_strategy_adapter import solve_student_order_with_sota_tsp
from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig


def test_time_limit_is_mapped_to_deadline_seconds():
    base = E2BSOTSPConfig(population_size=4, max_iterations=2)
    merged = merge_sota_config(base, {"time_limit": 12.5})
    assert merged.deadline_seconds == 12.5
    assert base.deadline_seconds is None  # request-local copy


def test_explicit_deadline_seconds_wins_over_time_limit():
    merged = merge_sota_config(E2BSOTSPConfig(), {"time_limit": 30.0, "deadline_seconds": 7.0})
    assert merged.deadline_seconds == 7.0


def test_ls_time_limit_is_accepted_and_ignored():
    base = E2BSOTSPConfig()
    assert merge_sota_config(base, {"ls_time_limit": 0.1}) == base
    clean, ignored = split_legacy_sota_keys({"ls_time_limit": 0.1, "population_size": 3})
    assert clean == {"population_size": 3}
    assert ignored == ("ls_time_limit",)


def test_policy_metadata_records_the_mapping_and_the_ignore():
    request = OptimizationRequest(
        algorithm="e2bso",
        depot={"id": "D", "lat": 0.0, "lng": 0.0},
        students=[{
            "id": "S1", "location_code": "S1",
            "coordinates": {"lat": 1.0, "lng": 0.0}, "disability_type": "Sw",
        }],
        sota_config={"time_limit": 9.0, "ls_time_limit": 0.3},
    )
    resolution = resolve_strategy("e2bso")
    effective, metadata = apply_compute_policy(request, resolution, resolution.create(), HARD_CEILINGS)

    assert metadata.limits["time_limit"].value == 9.0
    assert metadata.limits["time_limit"].source is PolicyValueSource.CALLER
    assert "deadline_seconds" in metadata.limits["time_limit"].enforcement
    assert "ignored" in metadata.limits["ls_time_limit"].enforcement
    assert effective.sota_config["time_limit"] == 9.0


def test_new_key_is_checked_against_the_solver_seconds_ceiling():
    # The request model already runs the compute policy; the ceiling is 60 s.
    with pytest.raises(ValueError, match="deadline_seconds"):
        OptimizationRequest(
            algorithm="e2bso",
            depot={"id": "D", "lat": 0.0, "lng": 0.0},
            students=[{
                "id": "S1", "location_code": "S1",
                "coordinates": {"lat": 1.0, "lng": 0.0}, "disability_type": "Sw",
            }],
            sota_config={"deadline_seconds": HARD_CEILINGS.solver_seconds + 1},
        )


def test_adapter_outcome_carries_termination_reason_and_reproducible():
    students = ["a", "b", "c", "d", "e", "f"]
    outcome = solve_student_order_with_sota_tsp(
        students, "D", lambda x, y: 0.0 if x == y else 1.0,
        E2BSO_TSP, E2BSOTSPConfig(population_size=4, max_iterations=2),
    )
    assert outcome.fallback_reason is None
    assert outcome.termination_reason == "iteration_limit"
    assert outcome.reproducible is True
