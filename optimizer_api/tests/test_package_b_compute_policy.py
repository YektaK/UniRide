"""Package B Task 2 tests: frozen compute profile, strict admission, typed metadata.

Covers the nine UNIRIDE_COMPUTE_* overrides, exhaustive tuning-key validation,
request admission bounds, additive applied-policy response metadata, and the
startup validation hook. See the approved Package B design and implementation
plan.
"""

import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from optimizer_api.compute_policy import (
    HARD_CEILINGS,
    TUNING_ALLOWLISTS,
    load_compute_policy,
    validate_tuning_dict,
)
from optimizer_api.models.schemas import (
    AlgorithmResult,
    AppliedComputePolicyInfo,
    CompareRequest,
    CompareResponse,
    OptimizationRequest,
    OptimizationResponse,
)
from optimizer_api import runtime_config

ENV_NAMES = (
    "UNIRIDE_COMPUTE_MAX_STUDENTS",
    "UNIRIDE_COMPUTE_MAX_VEHICLES",
    "UNIRIDE_COMPUTE_MAX_ALGORITHMS",
    "UNIRIDE_COMPUTE_MAX_WORKERS",
    "UNIRIDE_COMPUTE_DEADLINE_SECONDS",
    "UNIRIDE_COMPUTE_SOLVER_SECONDS",
    "UNIRIDE_COMPUTE_MAX_ITERATIONS",
    "UNIRIDE_COMPUTE_MAX_POPULATION",
    "UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS",
)

REDUCIBLE_OVERRIDES = {
    "UNIRIDE_COMPUTE_MAX_STUDENTS": ("max_students", 125),
    "UNIRIDE_COMPUTE_MAX_VEHICLES": ("max_vehicles", 25),
    "UNIRIDE_COMPUTE_MAX_ALGORITHMS": ("max_algorithms", 6),
    "UNIRIDE_COMPUTE_MAX_WORKERS": ("max_workers", 1),
    "UNIRIDE_COMPUTE_DEADLINE_SECONDS": ("deadline_seconds", 60),
    "UNIRIDE_COMPUTE_SOLVER_SECONDS": ("solver_seconds", 30),
    "UNIRIDE_COMPUTE_MAX_ITERATIONS": ("max_iterations", 1_000),
    "UNIRIDE_COMPUTE_MAX_POPULATION": ("max_population", 100),
    "UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS": ("local_search_seconds", 1),
}


def _students(count):
    return [
        {"id": f"s{i}", "location_code": f"L{i}", "disability_type": "So"}
        for i in range(count)
    ]


def _request(**overrides):
    payload = {
        "algorithm": "ga",
        "students": [],
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
    }
    payload.update(overrides)
    return payload


# --- Frozen profile and environment parser ---


def test_profile_defaults_and_lower_override():
    assert HARD_CEILINGS.max_students == 250
    assert HARD_CEILINGS.max_vehicles == 50
    assert HARD_CEILINGS.max_algorithms == 6
    assert HARD_CEILINGS.max_workers == 2
    assert HARD_CEILINGS.deadline_seconds == 120
    assert HARD_CEILINGS.solver_seconds == 60
    assert HARD_CEILINGS.max_iterations == 2_000
    assert HARD_CEILINGS.max_population == 250
    assert HARD_CEILINGS.local_search_seconds == 2
    policy = load_compute_policy({"UNIRIDE_COMPUTE_MAX_STUDENTS": "125"})
    assert policy.max_students == 125
    assert policy.profile_id == "production-conservative-v1"


@pytest.mark.parametrize("env_name", list(REDUCIBLE_OVERRIDES))
def test_each_reducible_limit_accepts_lower_override(env_name):
    field_name, lower = REDUCIBLE_OVERRIDES[env_name]
    policy = load_compute_policy({env_name: str(lower)})
    assert getattr(policy, field_name) == lower
    for other_field, default in REDUCIBLE_OVERRIDES.values():
        if other_field != field_name:
            assert getattr(policy, other_field) == getattr(HARD_CEILINGS, other_field)


@pytest.mark.parametrize("value", ["0", "251", "1.5", "yes"])
def test_student_override_must_be_positive_integer_at_or_below_ceiling(value):
    with pytest.raises(ValueError, match="UNIRIDE_COMPUTE_MAX_STUDENTS"):
        load_compute_policy({"UNIRIDE_COMPUTE_MAX_STUDENTS": value})


@pytest.mark.parametrize(
    ("env_name", "value"),
    [
        ("UNIRIDE_COMPUTE_MAX_VEHICLES", "0"),
        ("UNIRIDE_COMPUTE_MAX_VEHICLES", "-2"),
        ("UNIRIDE_COMPUTE_MAX_VEHICLES", "4.5"),
        ("UNIRIDE_COMPUTE_MAX_VEHICLES", "abc"),
    ],
)
def test_vehicle_override_must_be_positive_integer(env_name, value):
    with pytest.raises(ValueError, match="UNIRIDE_COMPUTE_MAX_VEHICLES"):
        load_compute_policy({env_name: value})


@pytest.mark.parametrize(
    ("env_name", "value"),
    [
        ("UNIRIDE_COMPUTE_MAX_VEHICLES", "51"),
        ("UNIRIDE_COMPUTE_MAX_ALGORITHMS", "7"),
        ("UNIRIDE_COMPUTE_MAX_WORKERS", "3"),
        ("UNIRIDE_COMPUTE_DEADLINE_SECONDS", "121"),
        ("UNIRIDE_COMPUTE_SOLVER_SECONDS", "61"),
        ("UNIRIDE_COMPUTE_MAX_ITERATIONS", "2001"),
        ("UNIRIDE_COMPUTE_MAX_POPULATION", "251"),
        ("UNIRIDE_COMPUTE_LOCAL_SEARCH_SECONDS", "3"),
    ],
)
def test_above_ceiling_values_rejected(env_name, value):
    with pytest.raises(ValueError, match=env_name):
        load_compute_policy({env_name: value})


def test_max_algorithms_below_six_rejected():
    with pytest.raises(ValueError, match="UNIRIDE_COMPUTE_MAX_ALGORITHMS"):
        load_compute_policy({"UNIRIDE_COMPUTE_MAX_ALGORITHMS": "5"})


def test_load_compute_policy_reads_process_environment(monkeypatch):
    monkeypatch.setenv("UNIRIDE_COMPUTE_MAX_STUDENTS", "125")
    policy = load_compute_policy()
    assert policy.max_students == 125
    monkeypatch.setenv("UNIRIDE_COMPUTE_MAX_VEHICLES", "25")
    assert load_compute_policy().max_vehicles == 25


def test_load_compute_policy_defaults_when_no_overrides(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    assert load_compute_policy() == HARD_CEILINGS


# --- validate_tuning_dict ---


def test_tuning_dict_rejects_unknown_key():
    with pytest.raises(ValueError, match="unsupported keys"):
        validate_tuning_dict("ga_config", {"generations": 5}, HARD_CEILINGS, 0)


def test_tuning_dict_distinguishes_bool_from_int():
    with pytest.raises(ValueError, match="max_iterations"):
        validate_tuning_dict("ga_config", {"max_iterations": True}, HARD_CEILINGS, 0)


def test_bool_keys_require_actual_boolean():
    with pytest.raises(ValueError, match="first_improvement"):
        validate_tuning_dict("two_opt_config", {"first_improvement": 1}, HARD_CEILINGS, 0)
    validated = validate_tuning_dict(
        "two_opt_config",
        {"first_improvement": True, "multi_start": False},
        HARD_CEILINGS,
        0,
    )
    assert validated["first_improvement"] is True
    assert validated["multi_start"] is False


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_tuning_dict_rejects_non_finite_numbers(bad):
    with pytest.raises(ValueError, match="finite"):
        validate_tuning_dict("ga_config", {"crossover_rate": bad}, HARD_CEILINGS, 0)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_unit_interval_keys_enforce_semantic_range(value):
    with pytest.raises(ValueError, match="crossover_rate"):
        validate_tuning_dict("ga_config", {"crossover_rate": value}, HARD_CEILINGS, 0)


def test_time_limit_respects_solver_second_ceiling():
    assert validate_tuning_dict(
        "sota_config", {"time_limit": 30.0}, HARD_CEILINGS, 0
    )["time_limit"] == 30.0
    with pytest.raises(ValueError, match="time_limit"):
        validate_tuning_dict(
            "sota_config", {"time_limit": HARD_CEILINGS.solver_seconds + 1}, HARD_CEILINGS, 0
        )
    with pytest.raises(ValueError, match="time_limit"):
        validate_tuning_dict("sota_config", {"time_limit": 0}, HARD_CEILINGS, 0)


def test_ls_time_limit_respects_local_search_ceiling():
    assert validate_tuning_dict(
        "sota_config", {"ls_time_limit": 1.5}, HARD_CEILINGS, 0
    )["ls_time_limit"] == 1.5
    with pytest.raises(ValueError, match="ls_time_limit"):
        validate_tuning_dict(
            "sota_config",
            {"ls_time_limit": HARD_CEILINGS.local_search_seconds + 1},
            HARD_CEILINGS,
            0,
        )


def test_structural_keys_capped_by_effective_student_limit():
    with pytest.raises(ValueError, match="n_edges_normal"):
        validate_tuning_dict("sota_config", {"n_edges_normal": 251}, HARD_CEILINGS, 0)


def test_dependent_allocation_cannot_exceed_effective_population():
    with pytest.raises(ValueError, match="elite_count"):
        validate_tuning_dict(
            "ga_config", {"population_size": 10, "elite_count": 11}, HARD_CEILINGS, 0
        )
    with pytest.raises(ValueError, match="tournament_size"):
        validate_tuning_dict(
            "ga_config", {"population_size": 4, "tournament_size": 5}, HARD_CEILINGS, 0
        )


def test_h_end_cannot_exceed_h_start():
    with pytest.raises(ValueError, match="h_end"):
        validate_tuning_dict(
            "sota_config", {"h_start": 0.8, "h_end": 0.9}, HARD_CEILINGS, 0
        )
    validated = validate_tuning_dict(
        "sota_config", {"h_start": 0.9, "h_end": 0.8}, HARD_CEILINGS, 0
    )
    assert validated["h_start"] == 0.9
    assert validated["h_end"] == 0.8


def test_inertia_min_cannot_exceed_inertia_weight():
    with pytest.raises(ValueError, match="inertia_min"):
        validate_tuning_dict(
            "pso_config", {"inertia_min": 0.5, "inertia_weight": 0.4}, HARD_CEILINGS, 0
        )


def test_n_edges_normal_cannot_exceed_n_edges_aggressive():
    with pytest.raises(ValueError, match="n_edges_normal"):
        validate_tuning_dict(
            "sota_config", {"n_edges_normal": 3, "n_edges_aggressive": 2}, HARD_CEILINGS, 0
        )


def test_operator_lists_validated():
    with pytest.raises(ValueError, match="unsupported value"):
        validate_tuning_dict(
            "sota_config", {"destroy_ops_pool": ["random", "nope"]}, HARD_CEILINGS, 0
        )
    validated = validate_tuning_dict(
        "sota_config", {"destroy_ops_pool": ["random", "worst"]}, HARD_CEILINGS, 0
    )
    assert validated["destroy_ops_pool"] == ("random", "worst")


def test_local_search_type_enum_validated():
    with pytest.raises(ValueError, match="local_search_type is unsupported"):
        validate_tuning_dict("ga_config", {"local_search_type": "banana"}, HARD_CEILINGS, 0)


def test_tuning_dict_does_not_mutate_caller_dict():
    supplied = {"max_iterations": 5, "population_size": 10}
    snapshot = dict(supplied)
    result = validate_tuning_dict("ga_config", supplied, HARD_CEILINGS, 0)
    assert supplied == snapshot
    assert result is not supplied


def test_tuning_dict_rejects_out_of_policy_student_count():
    with pytest.raises(ValueError, match="student_count"):
        validate_tuning_dict("ga_config", {"max_iterations": 5}, HARD_CEILINGS, 251)


# --- Request admission validation ---


def test_request_rejects_unknown_and_boolean_budget_values(monkeypatch):
    monkeypatch.setenv("UNIRIDE_COMPUTE_MAX_STUDENTS", "250")
    base = {"algorithm": "ga", "students": [], "depot": {"id": "D", "lat": 0, "lng": 0}}
    with pytest.raises(ValidationError):
        OptimizationRequest(**base, ga_config={"generations": 5})
    with pytest.raises(ValidationError):
        OptimizationRequest(**base, ga_config={"max_iterations": True})


def test_request_rejects_251_students(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError, match="students cannot exceed"):
        OptimizationRequest(**_request(students=_students(251)))


def test_request_accepts_250_students(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    request = OptimizationRequest(**_request(students=_students(250)))
    assert len(request.students) == 250


def test_request_rejects_51_vehicles(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    vehicles = [
        {"vehicle_id": f"V{i}", "sw_capacity": 4, "so_capacity": 5}
        for i in range(51)
    ]
    with pytest.raises(ValidationError, match="vehicles cannot exceed"):
        OptimizationRequest(**_request(vehicles=vehicles))


def test_compare_rejects_seven_algorithms(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    payload = {
        "students": [],
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
        "algorithms": [f"a{i}" for i in range(7)],
    }
    with pytest.raises(ValidationError, match="algorithms cannot exceed"):
        CompareRequest(**payload)


def test_compare_accepts_six_algorithms(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    payload = {
        "students": [],
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
        "algorithms": [f"a{i}" for i in range(6)],
    }
    assert len(CompareRequest(**payload).algorithms) == 6


def test_request_rejects_unsupported_local_search_type():
    with pytest.raises(ValidationError, match="local_search_type is unsupported"):
        OptimizationRequest(**_request(local_search_type="banana"))


def test_zero_student_request_remains_valid(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    request = OptimizationRequest(**_request())
    assert request.students == []
    compare = CompareRequest(
        students=[], depot={"id": "D", "lat": 0.0, "lng": 0.0}
    )
    assert compare.students == []


def test_valid_tuning_dict_is_normalized_in_place(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    request = OptimizationRequest(
        **_request(ga_config={"max_iterations": 5, "population_size": 10, "seed": 3})
    )
    assert request.ga_config == {"max_iterations": 5, "population_size": 10, "seed": 3}


# --- Typed applied-policy metadata (additive) ---


def test_policy_metadata_is_additive_and_typed():
    response = OptimizationResponse(algorithm_used="greedy", success=True, routes=[])
    assert response.applied_policy is None
    metadata = AppliedComputePolicyInfo.model_validate({
        "profile_id": "production-conservative-v1",
        "algorithm_requested": "nearest_neighbor",
        "algorithm_canonical": "greedy",
        "student_count": 0,
        "vehicle_count": 0,
        "cancellation_mode": "none",
        "limits": {},
    })
    assert metadata.algorithm_canonical == "greedy"


def test_algorithm_result_has_additive_metadata_fields():
    result = AlgorithmResult(
        algorithm="greedy",
        success=True,
        total_vehicles=1,
        total_duration_minutes=10.0,
        execution_time_seconds=0.5,
        routes=[],
    )
    assert result.algorithm_requested is None
    assert result.applied_policy is None


def test_compare_response_has_additive_metadata_field():
    response = CompareResponse(
        success=True,
        results=[],
        best_algorithm="greedy",
        fastest_algorithm="greedy",
        summary={},
    )
    assert response.applied_policy is None


# --- Startup validation hook and direct-module compatibility ---


def _unset_compute_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_runtime_config_validates_compute_policy_at_startup(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "guard-test-key")
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "0")
    monkeypatch.setenv("APP_ENV", "development")
    _unset_compute_env(monkeypatch)
    runtime_config.validate_runtime_configuration()


def test_runtime_config_rejects_invalid_compute_override(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "guard-test-key")
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "0")
    monkeypatch.setenv("APP_ENV", "development")
    _unset_compute_env(monkeypatch)
    monkeypatch.setenv("UNIRIDE_COMPUTE_MAX_STUDENTS", "999")
    with pytest.raises(ValueError, match="UNIRIDE_COMPUTE_MAX_STUDENTS"):
        runtime_config.validate_runtime_configuration()


def test_runtime_config_rejects_too_few_algorithms(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "guard-test-key")
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "0")
    monkeypatch.setenv("APP_ENV", "development")
    _unset_compute_env(monkeypatch)
    monkeypatch.setenv("UNIRIDE_COMPUTE_MAX_ALGORITHMS", "5")
    with pytest.raises(ValueError, match="UNIRIDE_COMPUTE_MAX_ALGORITHMS"):
        runtime_config.validate_runtime_configuration()


def _direct_probe(script_text, tmp_path, name):
    script = tmp_path / name
    script.write_text(script_text, encoding="utf-8")
    env = os.environ.copy()
    env["INTERNAL_API_KEY"] = "probe"
    env["UNIRIDE_DISABLE_AUTH"] = "0"
    env["APP_ENV"] = "development"
    for name in ENV_NAMES:
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result


def test_direct_module_runtime_config_fallback(tmp_path):
    optimizer_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = _direct_probe(
        "import sys\n"
        f"sys.path.insert(0, {optimizer_api_dir!r})\n"
        "from runtime_config import validate_runtime_configuration\n"
        "validate_runtime_configuration()\n"
        "print('DIRECT_RUNTIME_OK')\n",
        tmp_path,
        "direct_runtime_probe.py",
    )
    assert "DIRECT_RUNTIME_OK" in result.stdout


def test_direct_module_schemas_fallback(tmp_path):
    optimizer_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = _direct_probe(
        "import sys\n"
        f"sys.path.insert(0, {optimizer_api_dir!r})\n"
        "from models.schemas import OptimizationRequest\n"
        "request = OptimizationRequest(algorithm='ga', students=[], depot={'id': 'D', 'lat': 0.0, 'lng': 0.0})\n"
        "print('DIRECT_SCHEMAS_OK', len(request.students))\n",
        tmp_path,
        "direct_schemas_probe.py",
    )
    assert "DIRECT_SCHEMAS_OK" in result.stdout
