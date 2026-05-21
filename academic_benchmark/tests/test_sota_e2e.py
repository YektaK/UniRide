"""
B7: Kapsamlı End-to-End testler — SOTA TSP solverları için.

Test kategorileri:
  1. Solver E2E: Her algoritma küçük bir problem üzerinde çalışır mı?
  2. Seed Reproducibility: Aynı seed ile aynı sonuç dönüyor mu?
  3. Tour Validity: Tur [0..n-1] aralığında unique indekslerden mi oluşuyor?
  4. Destroy Edge Cases: n_remove >= len(tour) durumları
  5. 6-Dim Resonance: Yeni rezonans metriği doğru çalışıyor mu?
  6. Diversity: compute_population_diversity() merkezi fonksiyon testi
"""

import math
import random
import sys
import os

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from uniride_core.algorithms.sota_tsp.e2bso_tsp import E2BSO_TSP, E2BSOTSPConfig
from uniride_core.algorithms.sota_tsp.r2dma_tsp import R2DMA_TSP, R2DMATSPConfig, _compute_resonance
from uniride_core.algorithms.sota_tsp.paoea_tsp import PAOEA_TSP, PAOEAConfig, OperatorGenome
from uniride_core.algorithms.sota_tsp.destroy_ops import RandomRemoval, WorstRemoval, ShawRemoval
from uniride_core.algorithms.sota_tsp.repair_ops import GreedyInsertion, Regret2Insertion, Regret3Insertion
from academic_benchmark.benchmark_utils import compute_population_diversity


# --- Yardımcı: küçük test problemi ---
SMALL_COORDS = [
    (0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (5.0, 5.0),
    (3.0, 7.0), (8.0, 2.0), (1.0, 9.0), (6.0, 4.0), (9.0, 8.0),
]

# Minimal config: hızlı çalışması için düşük iterasyon ve popülasyon
E2BSO_FAST = E2BSOTSPConfig(population_size=6, max_iterations=10, seed=42)
R2DMA_FAST = R2DMATSPConfig(population_size=6, max_iterations=10, seed=42, tournament_k=3)
PAOEA_FAST = PAOEAConfig(population_size=6, max_iterations=10, genome_population_size=3, seed=42)


def _validate_tour(tour, n):
    """Turun geçerliliğini doğrula: unique, tam, ve doğru aralıkta."""
    assert len(tour) == n, f"Tur uzunluğu {len(tour)} != beklenen {n}"
    assert len(set(tour)) == n, f"Turda tekrar eden şehir var: {sorted(tour)}"
    assert min(tour) == 0, f"Tur minimum indeksi {min(tour)} != 0"
    assert max(tour) == n - 1, f"Tur maksimum indeksi {max(tour)} != {n-1}"


# ============================
# 1. Solver E2E Testleri
# ============================

def test_e2bso_solve_returns_valid_result():
    solver = E2BSO_TSP(E2BSO_FAST)
    result = solver.solve(SMALL_COORDS)
    assert result.algorithm == "E2BSO-TSP"
    assert result.tour_length > 0
    assert result.elapsed_ms >= 0
    _validate_tour(result.tour, len(SMALL_COORDS))


def test_r2dma_solve_returns_valid_result():
    solver = R2DMA_TSP(R2DMA_FAST)
    result = solver.solve(SMALL_COORDS)
    assert result.algorithm == "R2DMA-TSP"
    assert result.tour_length > 0
    assert result.elapsed_ms >= 0
    _validate_tour(result.tour, len(SMALL_COORDS))


def test_paoea_solve_returns_valid_result():
    solver = PAOEA_TSP(PAOEA_FAST)
    result = solver.solve(SMALL_COORDS)
    assert result.algorithm == "P-AOEA-TSP"
    assert result.tour_length > 0
    assert result.elapsed_ms >= 0
    _validate_tour(result.tour, len(SMALL_COORDS))


# ============================
# 2. Seed Reproducibility
# ============================

def test_e2bso_seed_reproducibility():
    r1 = E2BSO_TSP(E2BSOTSPConfig(population_size=6, max_iterations=5, seed=123)).solve(SMALL_COORDS)
    r2 = E2BSO_TSP(E2BSOTSPConfig(population_size=6, max_iterations=5, seed=123)).solve(SMALL_COORDS)
    assert r1.tour == r2.tour, "Aynı seed farklı tur üretti"
    assert abs(r1.tour_length - r2.tour_length) < 1e-6


def test_r2dma_seed_reproducibility():
    cfg = R2DMATSPConfig(population_size=6, max_iterations=5, seed=123, tournament_k=3)
    r1 = R2DMA_TSP(cfg).solve(SMALL_COORDS)
    r2 = R2DMA_TSP(cfg).solve(SMALL_COORDS)
    assert r1.tour == r2.tour, "Aynı seed farklı tur üretti"
    assert abs(r1.tour_length - r2.tour_length) < 1e-6


def test_paoea_seed_reproducibility():
    cfg = PAOEAConfig(population_size=6, max_iterations=5, genome_population_size=3, seed=123)
    r1 = PAOEA_TSP(cfg).solve(SMALL_COORDS)
    r2 = PAOEA_TSP(cfg).solve(SMALL_COORDS)
    assert r1.tour == r2.tour, "Aynı seed farklı tur üretti"
    assert abs(r1.tour_length - r2.tour_length) < 1e-6


# ============================
# 3. Tour Validity (Edge Cases)
# ============================

def test_solver_with_minimum_cities():
    """En küçük anlamlı problem: 4 şehir."""
    tiny_coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for SolverCls, cfg in [
        (E2BSO_TSP, E2BSOTSPConfig(population_size=4, max_iterations=3, seed=42)),
        (R2DMA_TSP, R2DMATSPConfig(population_size=4, max_iterations=3, seed=42, tournament_k=2)),
        (PAOEA_TSP, PAOEAConfig(population_size=4, max_iterations=3, genome_population_size=2, seed=42)),
    ]:
        result = SolverCls(cfg).solve(tiny_coords)
        _validate_tour(result.tour, 4)
        assert result.tour_length > 0


# ============================
# 4. Destroy/Repair Edge Cases
# ============================

def test_destroy_n_remove_exceeds_tour_length():
    """n_remove turun uzunluğuna eşit veya büyük olduğunda çökmemeli."""
    tour = [0, 1, 2, 3, 4]
    dm = [[abs(i - j) for j in range(5)] for i in range(5)]
    rng = random.Random(42)

    for DestroyClass in [RandomRemoval, WorstRemoval, ShawRemoval]:
        removed, remaining = DestroyClass().destroy(tour, 10, rng, dm)
        assert set(removed) | set(remaining) == set(tour), \
            f"{DestroyClass.__name__}: nodes lost — removed={removed}, remaining={remaining}"
        if DestroyClass is RandomRemoval:
            assert len(remaining) == 0, "RandomRemoval with n_remove>=n should remove all"
        else:
            assert len(remaining) >= 2, \
                f"{DestroyClass.__name__}: remaining too small ({len(remaining)})"


def test_repair_empty_partial():
    """Boş partial tour ile repair çökmemeli."""
    dm = [[abs(i - j) for j in range(5)] for i in range(5)]
    for RepairClass in [GreedyInsertion, Regret2Insertion, Regret3Insertion]:
        result = RepairClass().repair([], [0, 1, 2, 3, 4], dm)
        assert sorted(result) == [0, 1, 2, 3, 4]


# ============================
# 5. 6-Dim Resonance (B2)
# ============================

def test_resonance_identical_tours_returns_high_score():
    """Aynı iki tur tam rezonans sağlamalı."""
    t = [0, 1, 2, 3, 4, 5]
    dm = [[abs(i - j) for j in range(6)] for i in range(6)]
    r = _compute_resonance(t, list(t), 6, dm)
    assert r > 0.9, f"Aynı turlar için rezonans çok düşük: {r}"


def test_resonance_reversed_tours_lower_than_identical():
    """Ters çevrilmiş tur daha düşük rezonans vermeli."""
    t1 = [0, 1, 2, 3, 4, 5]
    t2 = [5, 4, 3, 2, 1, 0]
    dm = [[abs(i - j) for j in range(6)] for i in range(6)]
    r_same = _compute_resonance(t1, list(t1), 6, dm)
    r_reverse = _compute_resonance(t1, t2, 6, dm)
    assert r_same > r_reverse, f"Aynı ({r_same}) <= Ters ({r_reverse})"


def test_resonance_has_6_dimensions():
    """Rezonans fonksiyonu 6 boyuttan oluşan ağırlıklı skor döndürmeli."""
    t1 = [0, 1, 2, 3, 4, 5]
    t2 = [0, 2, 1, 3, 5, 4]
    dm = [[abs(i - j) for j in range(6)] for i in range(6)]

    r = _compute_resonance(t1, t2, 6, dm)
    # Sonuç [0, 1] aralığında olmalı
    assert 0.0 <= r <= 1.0, f"Rezonans aralık dışı: {r}"


def test_resonance_distance_signal_matters():
    """Farklı mesafe matrisleri farklı rezonans skorları üretmeli."""
    t1 = [0, 1, 2, 3, 4, 5]
    t2 = [0, 2, 1, 3, 5, 4]
    n = 6
    dm_clustered = [[abs(i - j) for j in range(n)] for i in range(n)]
    dm_flat = [[0.0 if i == j else 1.0 for j in range(n)] for i in range(n)]

    r_clustered = _compute_resonance(t1, t2, n, dm_clustered)
    r_flat = _compute_resonance(t1, t2, n, dm_flat)
    assert r_clustered != r_flat, "Farklı dm'ler aynı rezonans üretmemeli"


# ============================
# 6. Diversity (B3 + B10)
# ============================

def test_compute_diversity_identical_population():
    """Tamamen aynı bireylerden oluşan popülasyon düşük çeşitlilik göstermeli."""
    tour = [0, 1, 2, 3, 4]
    pop = [list(tour) for _ in range(10)]
    d = compute_population_diversity(pop, 5)
    assert d < 0.1, f"Aynı popülasyon çeşitliliği çok yüksek: {d}"


def test_compute_diversity_random_population():
    """Rastgele popülasyon yüksek çeşitlilik göstermeli."""
    rng = random.Random(42)
    pop = []
    for _ in range(20):
        t = list(range(10))
        rng.shuffle(t)
        pop.append(t)
    d = compute_population_diversity(pop, 10)
    assert d > 0.5, f"Rastgele popülasyon çeşitliliği çok düşük: {d}"


def test_compute_diversity_sqrt_n_sampling():
    """√n örnekleme küçük popülasyonlar için tüm bireyleri kapsamalı."""
    tour = [0, 1, 2, 3, 4]
    pop = [list(tour) for _ in range(4)]  # √4 = 2+1 = 3 birey örneklenir
    d = compute_population_diversity(pop, 5)
    assert d < 0.1


def test_operator_genome_copy_preserves_fitness():
    """B5: copy() fitness, success_count ve total_trials'ı korumalı."""
    g = OperatorGenome(fitness=42.0, success_count=10, total_trials=20)
    g_copy = g.copy()
    assert g_copy.fitness == 42.0
    assert g_copy.success_count == 10
    assert g_copy.total_trials == 20
