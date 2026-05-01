from academic_benchmark.sota_tsp import ls_engine
from academic_benchmark.sota_tsp.repair_ops import Regret3Insertion
from academic_benchmark.sota_tsp.r2dma_tsp import _compute_resonance


def test_full_intensity_runs_3opt_layer(monkeypatch):
    calls = {"3opt": 0}

    def fake_3opt(tour, dm, max_iterations=200):  # pragma: no cover - monkeypatch target
        calls["3opt"] += 1
        return tour[:], 10.0

    monkeypatch.setattr(ls_engine, "improve_3opt", fake_3opt)

    dm = [
        [0, 2, 9, 10, 7],
        [2, 0, 6, 4, 3],
        [9, 6, 0, 8, 5],
        [10, 4, 8, 0, 1],
        [7, 3, 5, 1, 0],
    ]
    tour = [0, 1, 2, 3, 4]

    ls_engine.MultiLayerLS.improve(tour, dm, intensity="full", max_iterations=5, time_limit=1.0)
    assert calls["3opt"] > 0


def test_regret3_insertion_repairs_all_removed_nodes():
    repair = Regret3Insertion()
    dm = [
        [0, 1, 2, 3, 4],
        [1, 0, 1, 2, 3],
        [2, 1, 0, 1, 2],
        [3, 2, 1, 0, 1],
        [4, 3, 2, 1, 0],
    ]
    partial = [0, 2]
    removed = [1, 3, 4]

    repaired = repair.repair(partial, removed, dm)
    assert sorted(repaired) == [0, 1, 2, 3, 4]
    assert len(repaired) == 5


def test_r2dma_resonance_uses_distance_signal():
    # Same positional pattern, but very different edge-length structure.
    t1 = [0, 1, 2, 3, 4, 5]
    t2 = [0, 2, 1, 3, 5, 4]
    n = len(t1)

    # Clustered distances should reward structurally similar edges
    dm_clustered = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dm_clustered[i][j] = abs(i - j)

    # Flat distances remove distance structure
    dm_flat = [[0.0 if i == j else 1.0 for j in range(n)] for i in range(n)]

    r_clustered = _compute_resonance(t1, t2, n, dm_clustered)
    r_flat = _compute_resonance(t1, t2, n, dm_flat)

    # When distance signal is used, these should diverge once function is parity-improved.
    assert r_clustered != r_flat
