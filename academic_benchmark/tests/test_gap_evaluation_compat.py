from academic_benchmark import benchmark_utils
from academic_benchmark.core import evaluation


def test_core_evaluation_compute_gap_delegates_to_canonical_helper(monkeypatch):
    def fake_compute_gap(problem, cost, optimal=None):
        assert problem == "__direct__"
        assert cost == 123.0
        assert optimal == 100.0
        return 42.0, "optimal"

    monkeypatch.setattr(benchmark_utils, "compute_gap", fake_compute_gap)

    assert evaluation.compute_gap(123.0, 100.0) == 42.0
