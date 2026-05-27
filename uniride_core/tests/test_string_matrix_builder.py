from uniride_core.adapters.string_matrix_builder import build_string_distance_matrix


def test_build_string_distance_matrix_uses_lookup_and_zero_diagonal():
    values = {
        ("A", "B"): 4.0,
        ("B", "A"): 6.0,
        ("A", "C"): 2.0,
        ("C", "A"): 3.0,
        ("B", "C"): 5.0,
        ("C", "B"): 7.0,
    }

    matrix = build_string_distance_matrix(["A", "B", "C"], lambda origin, destination: values[(origin, destination)])

    assert matrix == {
        "A": {"A": 0.0, "B": 4.0, "C": 2.0},
        "B": {"A": 6.0, "B": 0.0, "C": 5.0},
        "C": {"A": 3.0, "B": 7.0, "C": 0.0},
    }
