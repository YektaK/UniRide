import pytest
from pydantic import ValidationError

from optimizer_api.models.schemas import BenchmarkRunRequest


def _valid_payload():
    return {
        "run_id": "matrix-native-schema-test",
        "algorithms": [{"name": "Core-Greedy-Routing", "params": {"seed": 7}}],
        "problems": ["smoke-cvrp"],
        "settings": {"execution_mode": "matrix_native", "n_runs": 1, "seed": 7},
    }


def test_benchmark_run_request_accepts_matrix_native_payload():
    request = BenchmarkRunRequest.model_validate(_valid_payload())

    assert request.run_id == "matrix-native-schema-test"
    assert request.algorithms[0]["name"] == "Core-Greedy-Routing"
    assert request.problems == ["smoke-cvrp"]
    assert request.settings["execution_mode"] == "matrix_native"


@pytest.mark.parametrize(
    "field,value",
    [
        ("algorithms", []),
        ("problems", []),
        ("run_id", ""),
    ],
)
def test_benchmark_run_request_rejects_empty_required_values(field, value):
    payload = _valid_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(payload)


def test_benchmark_run_request_rejects_algorithm_without_name():
    payload = _valid_payload()
    payload["algorithms"] = [{"params": {"seed": 7}}]

    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(payload)


def test_benchmark_run_request_rejects_invalid_execution_mode():
    payload = _valid_payload()
    payload["settings"] = {"execution_mode": "production_request"}

    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(payload)


def test_benchmark_run_request_rejects_invalid_run_count():
    payload = _valid_payload()
    payload["settings"] = {"execution_mode": "matrix_native", "n_runs": 0}

    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(payload)
