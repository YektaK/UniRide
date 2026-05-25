from dataclasses import dataclass
from types import SimpleNamespace

import academic_benchmark.benchmark_utils as benchmark_utils
from academic_benchmark.benchmark_utils import ProblemSelector, _prob_category, _prob_dim, _prob_name, _prob_optimal
from academic_benchmark.cli_engine import _select_problems_from_args as select_numba_problems
from academic_benchmark.sota_engine import _select_problems_from_args as select_sota_problems


@dataclass
class MockProblem:
    name: str
    dimension: int
    category: str
    optimal: int = 0


MOCK_PROBLEMS = [
    MockProblem("berlin52", 52, "small", 7542),
    MockProblem("eil51", 51, "small", 426),
    MockProblem("eil76", 76, "small", 538),
    MockProblem("eil101", 101, "medium", 629),
    MockProblem("kroA100", 100, "small", 21282),
    MockProblem("rd100", 100, "small", 7910),
    MockProblem("a280", 280, "medium", 2579),
    MockProblem("pr1002", 1002, "large", 259045),
]


def test_prob_name_dict():
    assert _prob_name({"name": "x"}) == "x"


def test_prob_name_obj():
    assert _prob_name(MOCK_PROBLEMS[0]) == "berlin52"


def test_prob_dim_missing():
    assert _prob_dim({"name": "x"}) == 0


def test_prob_category_boundaries():
    assert _prob_category({"name": "a", "dimension": 100}) == "small"
    assert _prob_category({"name": "b", "dimension": 101}) == "medium"
    assert _prob_category({"name": "c", "dimension": 500}) == "medium"
    assert _prob_category({"name": "d", "dimension": 501}) == "large"


def test_prob_optimal_dict_fallback():
    original = benchmark_utils.TSPLIB_OPTIMALS.get("berlin52")
    try:
        assert _prob_optimal({"name": "berlin52"}) == 7542
    finally:
        assert benchmark_utils.TSPLIB_OPTIMALS.get("berlin52") == original or original == 7542


def test_sorted_by_dimension():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [_prob_name(problem) for problem in selector.sorted] == [
        "eil51", "berlin52", "eil76", "kroA100", "rd100", "eil101", "a280", "pr1002"
    ]


def test_token_all():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("all")] == [
        "eil51", "berlin52", "eil76", "kroA100", "rd100", "eil101", "a280", "pr1002"
    ]


def test_token_single_index():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("1")] == ["eil51"]


def test_token_multiple_indices():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("1,3,5")] == ["eil51", "eil76", "rd100"]


def test_token_range():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("1-4")] == ["eil51", "berlin52", "eil76", "kroA100"]


def test_token_range_reversed():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("4-1")] == ["eil51", "berlin52", "eil76", "kroA100"]


def test_token_category():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("small")] == ["eil51", "berlin52", "eil76", "kroA100", "rd100"]


def test_token_name_exact():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("berlin52")] == ["berlin52"]


def test_token_name_case():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("BERLIN52")] == ["berlin52"]


def test_token_exclude():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("small,!eil51")] == ["berlin52", "eil76", "kroA100", "rd100"]


def test_token_unknown_warns():
    selector = ProblemSelector(MOCK_PROBLEMS)
    selected, warnings = selector.resolve_tokens("unknown")
    assert selected == set()
    assert warnings and "Bilinmeyen token" in warnings[0]


def test_token_dedup():
    selector = ProblemSelector(MOCK_PROBLEMS)
    assert [p.name for p in selector.quick_select("1,1,2")] == ["eil51", "berlin52"]


def test_interactive_done_confirmation(monkeypatch):
    selector = ProblemSelector(MOCK_PROBLEMS)
    inputs = iter(["done", "e"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert selector.interactive_select() == []


def test_sota_problem_selection_priority():
    args = SimpleNamespace(select="small", problems="berlin52", size_limit=100)
    selected = select_sota_problems(args, MOCK_PROBLEMS)
    assert [p.name for p in selected] == ["eil51", "berlin52", "eil76", "kroA100", "rd100"]


def test_numba_problem_selection_priority():
    args = SimpleNamespace(select="small", problems="berlin52", size_limit=100)
    selected = select_numba_problems(args, MOCK_PROBLEMS)
    assert [p.name for p in selected] == ["eil51", "berlin52", "eil76", "kroA100", "rd100"]