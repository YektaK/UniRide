from academic_benchmark import benchmark_utils


def test_validate_param_value_supports_optional_validators():
    validators = {"population_size": (1, 100, "int")}

    assert benchmark_utils.validate_param_value("population_size", "50", int, validators) == 50
    assert benchmark_utils.validate_param_value("population_size", "0", int, validators) is None


def test_parse_param_list_uses_shared_validator():
    assert benchmark_utils.parse_param_list("1, 2, 3", [10]) == [1, 2, 3]
    assert benchmark_utils.parse_param_list("bad", [10]) == [10]
