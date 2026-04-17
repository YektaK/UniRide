#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide FAZ 0 — Interaktif Optimizasyon Scripti
================================================

SOTA Common Infrastructure modülleri ile TSPLIB problemlerini çözer.

Özellikler:
  - TSPLIB problemlerini otomatik indirir
  - Çoklu problem seçimi (numara, aralık, kategori alias)
  - Çoklu pipeline karşılaştırma modu
  - Multi-Start + Multi-Layer LS + ALNS pipeline
  - SA / LAHC / RTR kabul kriteri seçimi
  - Destroy / Repair operatör seçimi
  - Çoklu çalıştırma (n_runs) ve detaylı istatistikler
  - Tam parametre kaydı (seçili + alternatifler)
  - Sonuçları JSON dosyasına kaydeder
  - Pipeline karşılaştırma tablosu ve özet raporu
  - Ctrl+C ile güvenli çıkış

Kullanım:
    cd optimizer_api
    python faz0_interactive.py

Gereksinimler: Sadece Python >= 3.8 (hiçbir dış bağımlılık yok)
"""

import sys
import os
import io
import json
import signal
import time
import math
import random
import platform
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from multiprocessing import Pool, cpu_count

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Multiprocessing: Windows spawn guard ──
# multiprocessing.Pool + spawn başlatma koruması (Windows'ta zorunlu)
_parallel_pool = None
NUM_WORKERS = min(cpu_count(), 4)  # default, kullanıcı değiştirebilir
_USE_PARALLEL = True  # paralel mod açık/kapalı

# multiprocessing için argüman hash'i (alt süreçte sys.path yeniden ayarla)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Path setup ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils.tsplib_parser import (
    get_available_problems,
    load_problem_coordinates,
    download_tsplib_problem,
    TSPLIB_OPTIMALS,
    tsplib_euc_2d_distance,
    TSPLIBProblemInfo,
)

from strategies.sota_common import (
    SOTA_INFRA_VERSION,
    MultiStartInitializer,
    MultiLayerLS,
    PenaltyManager,
    SimulatedAnnealing,
    LateAcceptanceHC,
    RecordToRecordTravel,
    RandomRemoval,
    WorstRemoval,
    ShawRemoval,
    RelatedRemoval,
    GreedyInsertion,
    Regret2Insertion,
    Regret3Insertion,
    DiversityController,
    E2BSO, E2BSOConfig, E2BSOResult,
    R2DMA, R2DMAConfig, R2DMAResult,
    PAOEA, PAOEAConfig, PAOEAResult,
)

# ═══════════════════════════════════════════════════════════════════
# Constants & Config
# ═══════════════════════════════════════════════════════════════════

RESULTS_DIR = os.path.join(SCRIPT_DIR, "faz0_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# CPU Detection & Worker Selection
# ═══════════════════════════════════════════════════════════════════

def get_cpu_info() -> dict:
    """CPU bilgilerini topla ve optimal worker sayısı öner."""
    physical_cores = cpu_count()
    logical_cores = cpu_count()
    has_smt = False

    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or cpu_count()
        logical_cores = psutil.cpu_count(logical=True) or cpu_count()
        has_smt = logical_cores > physical_cores
    except ImportError:
        pass

    # CPU-bound optimizasyon için fiziksel çekirdek sayısı optimal
    if has_smt:
        recommended = physical_cores
    else:
        recommended = max(1, physical_cores - 1)

    recommended = min(recommended, 16)

    return {
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "has_smt": has_smt,
        "recommended_workers": recommended,
        "platform": platform.processor() or platform.machine(),
    }


def select_worker_count() -> int:
    """Kullanıcıdan worker sayısını al veya otomatik öner."""
    global NUM_WORKERS
    cpu_info = get_cpu_info()

    print("\n" + "=" * 60)
    print("  ISLEMCI BILGILERI")
    print("=" * 60)
    print(f"  Platform          : {cpu_info['platform']}")
    print(f"  Fiziksel Cekirdek : {cpu_info['physical_cores']}")
    print(f"  Mantiksal Cekirdek: {cpu_info['logical_cores']}")
    if cpu_info['has_smt']:
        print(f"  SMT/Hyperthreading: Aktif")
    print()

    rec = cpu_info['recommended_workers']
    print(f"  [ONERI] Optimal worker: {rec}")
    print(f"    - CPU-bound islemler icin fiziksel cekirdek sayisi onerilir")
    print()
    print(f"  [1] {rec} (Onerilen)")
    print(f"  [2] {min(cpu_info['logical_cores'], 8)} (Standart)")
    print(f"  [3] {min(cpu_info['logical_cores'], 12)} (Yuksek performans)")
    print(f"  [4] {min(cpu_info['logical_cores'], 16)} (Maksimum)")
    print(f"  [C] Custom - Kendiniz girin")
    print(f"  [Enter] Varsayilan: {NUM_WORKERS}")

    choice = input("\n  Seciminiz: ").strip().upper()

    if choice == "" or choice == "1":
        NUM_WORKERS = rec
    elif choice == "2":
        NUM_WORKERS = min(cpu_info['logical_cores'], 8)
    elif choice == "3":
        NUM_WORKERS = min(cpu_info['logical_cores'], 12)
    elif choice == "4":
        NUM_WORKERS = min(cpu_info['logical_cores'], 16)
    elif choice == "C":
        try:
            custom = int(input(f"  Worker sayisi (1-{cpu_info['logical_cores']}): ").strip())
            NUM_WORKERS = max(1, min(custom, cpu_info['logical_cores']))
        except ValueError:
            print("  Gecersiz giris, onerilen kullanilacak")
            NUM_WORKERS = rec
    else:
        NUM_WORKERS = rec

    return NUM_WORKERS


def select_execution_mode() -> bool:
    """Seri veya paralel çalıştırma modu seç. True = paralel.

    Paralel mod seçildiğinde worker sayısı da burada belirlenir.
    Kullanıcı kendi worker sayısını girebilir (örn: 6 worker → PC responsive kalır).
    """
    global _USE_PARALLEL
    cpu_info = get_cpu_info()
    rec = cpu_info['recommended_workers']
    logical = cpu_info['logical_cores']

    print(f"\n  CALISTIRMA MODU")
    print(f"  ─" * 30)
    print(f"  CPU: {cpu_info['platform']}")
    print(f"  Fiziksel: {cpu_info['physical_cores']} çekirdek, Mantıksal: {logical} thread")
    if cpu_info['has_smt']:
        print(f"  SMT/Hyperthreading: Aktif")
    print()
    print(f"  [1] Paralel ({rec} worker) — ONERILEN (fiziksel cekirdek)")
    print(f"  [2] Paralel ({logical} worker) — Tum thread'ler")
    print(f"  [3] Paralel (custom) — Kendi worker sayinizi girin")
    print(f"  [4] Seri (tek thread) — detayli anlik progress")
    print()

    choice = input("  Seciminiz [1]: ").strip()

    if choice == "4":
        _USE_PARALLEL = False
        print("  → Seri mod secildi")
        return False
    elif choice == "2":
        NUM_WORKERS = logical
    elif choice == "3":
        print(f"\n  Worker sayisi girin (1-{logical}):")
        print(f"  PC responsive kalmasi icin fiziksel cekirdekten az kullanabilirsiniz")
        print(f"  Ornegin: {rec} cekirdek varsa, 5-6 worker iyi bir secim olabilir")
        try:
            custom = int(input(f"  Worker sayisi [6]: ").strip())
            NUM_WORKERS = max(1, min(custom, logical))
        except ValueError:
            NUM_WORKERS = 6
            print(f"  Gecersiz giris, varsayilan: 6")
    else:
        NUM_WORKERS = rec

    _USE_PARALLEL = True
    print(f"  → Paralel mod secildi ({NUM_WORKERS} worker)")
    return True

BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║          UniRide — SOTA Algoritma Gelistirme Interaktif Modu           ║
║     FAZ 0: Multi-Start · Local Search · ALNS · SA/LAHC/RTR             ║
║     FAZ 1: E2BSO — Entropy-Balanced Swarm Optimization               ║
║     FAZ 2: R2DMA — Resonance-Reinforced Destroy & Merge              ║
║     FAZ 3: PAOEA — Adaptive Operator Evolution Algorithm              ║
║     v{ver:<49s}║
╚══════════════════════════════════════════════════════════════════════╝
""".format(ver=SOTA_INFRA_VERSION)

# All parameter options available for selection (used in complete recording)
PARAMETER_OPTIONS = {
    "init_method": ["nn", "cw", "regret", "random", "multi"],
    "ls_intensity": ["none", "light", "medium", "heavy"],
    "destroy_operator": ["random", "worst", "shaw", "related", "adaptive"],
    "repair_operator": ["greedy", "regret2", "regret3", "adaptive"],
    "acceptance": ["sa", "lahc", "rtr"],
}

# Algorithm catalog for info display
ALGO_CATALOG = {
    "Multi-Start NN": {
        "desc": "En yakın komşu heuristiği ile başlangıç turları üretir",
        "complexity": "O(n²)",
        "best_for": "Hızlı, makul kaliteli başlangıç çözümleri",
    },
    "Multi-Start CW": {
        "desc": "Clarke-Wright Savings heuristiği ile tur oluşturur",
        "complexity": "O(n² log n)",
        "best_for": "TSP, dağıtım rotası başlangıcı",
    },
    "Multi-Start Regret": {
        "desc": "Regret-2 insertion heuristiği (TW urgency bonus)",
        "complexity": "O(n³)",
        "best_for": "CVRPTW, zaman penceresi olan problemler",
    },
    "Multi-Start Random": {
        "desc": "Rastgele permütasyon + perturbation",
        "complexity": "O(n)",
        "best_for": "Çeşitlilik, yerel minimumdan kaçış",
    },
    "2-opt": {
        "desc": "İki kenarı kaldırıp ters bağlar",
        "complexity": "O(n²)",
        "best_for": "Standart TSP iyileştirme",
    },
    "Or-opt": {
        "desc": "1-3 düğümlük segmenti başka yere taşır",
        "complexity": "O(n²)",
        "best_for": "Kümelenmiş düğümler, fine-tuning",
    },
    "3-opt": {
        "desc": "Üç kenarı kaldırıp 7 farklı yeniden bağlantı dener",
        "complexity": "O(n³)",
        "best_for": "Yüksek kalite, düşük n",
    },
    "Swap": {
        "desc": "İki düğümün yerini değiştirir",
        "complexity": "O(n²)",
        "best_for": "Hızlı fine-tuning",
    },
    "ALNS (Random+Greedy)": {
        "desc": "Rastgele düğüm kaldır + açgözlü ekle",
        "complexity": "O(q·n)",
        "best_for": "Çeşitli yapıda problemler",
    },
    "ALNS (Worst+Regret-2)": {
        "desc": "En kötü düğüm kaldır + regret-2 ekle",
        "complexity": "O(q·n²)",
        "best_for": "Akademik benchmark, yüksek kalite",
    },
    "ALNS (Shaw+Regret-3)": {
        "desc": "Shaw benzerlik kaldırma + regret-3 ekleme",
        "complexity": "O(q·n²)",
        "best_for": "CVRPTW, yapısal iyileştirme",
    },
    "SimulatedAnnealing": {
        "desc": "Geometrik soğutmalı SA kabul kriteri",
        "complexity": "O(1) per decision",
        "best_for": "Yerel minimumdan kaçış, geniş arama",
    },
    "LAHC": {
        "desc": "Late Acceptance Hill Climbing (L=500)",
        "complexity": "O(L) per decision",
        "best_for": "Dengeli keşif/sömürü, kararlı iyileştirme",
    },
    "RTR": {
        "desc": "Record-to-Record Travel threshold kabul",
        "complexity": "O(1) per decision",
        "best_for": "Hızlı yakınsama, erken iterasyonlarda esneklik",
    },
    "E2BSO": {
        "desc": "Enhanced Entropy-Balanced Swarm Optimization (FAZ 1)",
        "complexity": "O(pop × iter × n)",
        "best_for": "TSP akademik benchmark, yüksek kalite meta-heuristic",
    },
    "R2DMA": {
        "desc": "Resonance-Reinforced Destroy and Merge Algorithm (FAZ 2)",
        "complexity": "O(pop × iter × n²)",
        "best_for": "TSP/CVRPTW, rezonans tabanlı memetik algoritma",
        "dna": "D1✅ D2✅ D3✅ D4✅ D6✅ D7✅ D8✅ D9✅",
    },
    "PAOEA": {
        "desc": "Production Adaptive Operator Evolution Algorithm (FAZ 3)",
        "complexity": "O(pop × genome × iter × n²)",
        "best_for": "TSP/CVRPTW, meta-evolution of operator strategies",
        "dna": "D1✅ D2✅ D3✅ D4✅ D6✅ D7✅ D8✅ D9✅ D10✅",
    },
}

# Pipeline presets
PIPELINE_PRESETS = {
    "hizli": {
        "label": "Hızlı Pipeline",
        "desc": "NN başlangıç + 2-opt LS (küçük problemler için)",
        "init": "nn",
        "ls_intensity": "light",
        "alns_iters": 0,
        "acceptance": "sa",
    },
    "dengeli": {
        "label": "Dengeli Pipeline",
        "desc": "Multi-Start + Medium LS + 200 ALNS iterasyonu",
        "init": "multi",
        "ls_intensity": "medium",
        "alns_iters": 200,
        "acceptance": "sa",
    },
    "kaliteli": {
        "label": "Kaliteli Pipeline",
        "desc": "Multi-Start + Heavy LS + 500 ALNS iterasyonu + LAHC",
        "init": "multi",
        "ls_intensity": "heavy",
        "alns_iters": 500,
        "acceptance": "lahc",
    },
    "maksimum": {
        "label": "Maksimum Pipeline",
        "desc": "Multi-Start + Heavy LS + 1000 ALNS + Regret-3 polish",
        "init": "multi",
        "ls_intensity": "heavy",
        "alns_iters": 1000,
        "acceptance": "lahc",
    },
    "e2bso": {
        "label": "E2BSO (FAZ 1)",
        "desc": "Entropy-Balanced Swarm: pop=40, iter=500, ALNS+LS+LAHC",
        "init": "e2bso",
        "ls_intensity": "heavy",
        "alns_iters": 0,
        "acceptance": "lahc",
    },
    "r2dma": {
        "label": "R2DMA (FAZ 2)",
        "desc": "Rezonans tabanlı memetik: pop=60, iter=2000, ALNS+SA+LS",
        "init": "r2dma",
        "ls_intensity": "heavy",
        "alns_iters": 0,
        "acceptance": "sa",
    },
    "paoea": {
        "label": "PAOEA (FAZ 3)",
        "desc": "Operator Co-Evolution: pop=50, genomes=15, meta-evo, ALNS+SA+LS",
        "init": "paoea",
        "ls_intensity": "heavy",
        "alns_iters": 0,
        "acceptance": "sa",
    },
}


# ═══════════════════════════════════════════════════════════════════
# Problem Wrapper
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[int] = None
    dist_matrix: Dict[int, Dict[int, int]] = field(default_factory=dict, repr=False)
    node_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.node_names = [str(i) for i in range(self.dimension)]
        self.dist_matrix = {}
        for i in range(self.dimension):
            self.dist_matrix[i] = {}
            for j in range(self.dimension):
                self.dist_matrix[i][j] = (
                    tsplib_euc_2d_distance(self.coordinates[i], self.coordinates[j])
                    if i != j else 0
                )

    def tour_cost(self, tour: List[int]) -> int:
        if not tour or len(tour) < 2:
            return 0
        return sum(
            self.dist_matrix[tour[i]][tour[(i + 1) % len(tour)]]
            for i in range(len(tour))
        )

    def cost_fn(self, tour: List) -> float:
        return float(self.tour_cost([int(n) for n in tour]))

    def gap_pct(self, tour: List[int]) -> float:
        if not self.optimal:
            return float("nan")
        return (self.tour_cost(tour) - self.optimal) / self.optimal * 100


def load_problem(name: str) -> Optional[ProblemInstance]:
    coords = load_problem_coordinates(name)
    if not coords:
        return None
    # Case-insensitive optimal lookup (parser lowercases but OPTIMALS has mixed case)
    optimal = TSPLIB_OPTIMALS.get(name.lower())
    if optimal is None:
        for k, v in TSPLIB_OPTIMALS.items():
            if k.lower() == name.lower():
                optimal = v
                break
    return ProblemInstance(
        name=name,
        dimension=len(coords),
        coordinates=coords,
        optimal=optimal,
    )


# ═══════════════════════════════════════════════════════════════════
# FAZ 0 Solver Pipeline
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RunConfig:
    """Configuration for a single optimization run."""
    init_method: str = "multi"        # nn, cw, regret, random, multi
    ls_intensity: str = "medium"      # none, light, medium, heavy
    alns_iterations: int = 200
    destroy_operator: str = "random"  # random, worst, shaw, related, adaptive
    repair_operator: str = "regret2"  # greedy, regret2, regret3, adaptive
    acceptance: str = "sa"            # sa, lahc, rtr
    sa_temp: float = 50.0
    lahc_history: int = 500
    alns_remove_pct: float = 0.10     # fraction of nodes to remove
    seed: int = 42
    time_limit_ms: float = 30000      # 0 = no limit


@dataclass
class RunResult:
    result_id: str = ""
    problem_name: str = ""
    dimension: int = 0
    optimal: Optional[int] = None
    config: dict = field(default_factory=dict)
    tour: List[int] = field(default_factory=list)
    cost: int = 0
    gap: float = 0.0
    time_ms: float = 0.0
    timestamp: str = ""
    # Detailed stats
    init_cost: int = 0
    ls_cost: int = 0
    alns_cost: int = 0
    final_ls_cost: int = 0
    ls_improvements: int = 0
    alns_accepted: int = 0
    alns_total: int = 0
    # Complete parameter recording (selected + available options)
    all_parameters: dict = field(default_factory=dict)


def _build_distance_map(prob: ProblemInstance) -> Dict[str, Dict[str, float]]:
    dm: Dict[str, Dict[str, float]] = {}
    for i in range(prob.dimension):
        dm[prob.node_names[i]] = {}
        for j in range(prob.dimension):
            dm[prob.node_names[i]][prob.node_names[j]] = float(prob.dist_matrix[i][j])
    return dm


def solve_single(prob: ProblemInstance, config: RunConfig) -> RunResult:
    """Run one FAZ 0 optimization pass and return results."""
    t_start = time.perf_counter()
    rng = random.Random(config.seed)
    dm_str = _build_distance_map(prob)

    # ── Phase 1: Initialization ──
    init_cost = 0
    best_tour: List[int] = list(range(prob.dimension))

    if config.init_method == "multi":
        pop = MultiStartInitializer.generate_population(
            prob.node_names, dm_str,
            pop_size=max(4, min(8, prob.dimension // 5)),
            rng=rng, depot=prob.node_names[0],
        )
        int_pop = [[int(n) for n in sol] for sol in pop]
        costs = [prob.tour_cost(t) for t in int_pop]
        best_idx = costs.index(min(costs))
        best_tour = int_pop[best_idx]
        init_cost = costs[best_idx]
    elif config.init_method == "nn":
        tour = MultiStartInitializer.generate_population(
            prob.node_names, dm_str, pop_size=1, rng=rng, depot=prob.node_names[0],
        )
        best_tour = [int(n) for n in tour[0]]
        init_cost = prob.tour_cost(best_tour)
    elif config.init_method == "cw":
        # Force CW: generate 4 but take 2nd (index 1 = CW heuristic)
        tour = MultiStartInitializer.generate_population(
            prob.node_names, dm_str, pop_size=4, rng=rng, depot=prob.node_names[0],
        )
        # CW solutions are at indices 1..2 (per_method=1 + remainder)
        cw_candidates = [[int(n) for n in t] for t in tour[1:3]] if len(tour) > 1 else [[int(n) for n in tour[0]]]
        cw_costs = [prob.tour_cost(t) for t in cw_candidates]
        best_idx = cw_costs.index(min(cw_costs))
        best_tour = cw_candidates[best_idx]
        init_cost = cw_costs[best_idx]
    elif config.init_method == "regret":
        tour = MultiStartInitializer.generate_population(
            prob.node_names, dm_str, pop_size=4, rng=rng, depot=prob.node_names[0],
        )
        # Regret solutions are at indices 2..3
        regret_candidates = [[int(n) for n in t] for t in tour[2:4]] if len(tour) > 2 else [[int(n) for n in tour[0]]]
        regret_costs = [prob.tour_cost(t) for t in regret_candidates]
        best_idx = regret_costs.index(min(regret_costs))
        best_tour = regret_candidates[best_idx]
        init_cost = regret_costs[best_idx]
    else:
        rng.shuffle(best_tour)
        init_cost = prob.tour_cost(best_tour)

    # ── Phase 2: Local Search ──
    ls_cost = init_cost
    ls_improvements = 0
    if config.ls_intensity != "none":
        improved, ls_float, stats = MultiLayerLS.improve(
            best_tour, prob.cost_fn, rng, intensity=config.ls_intensity,
        )
        ls_cost = int(ls_float)
        ls_improvements = sum(stats.get("improves_per_layer", {}).values())
        if ls_cost < prob.tour_cost(best_tour):
            best_tour = improved

    # ── Phase 3: ALNS ──
    alns_cost = ls_cost
    alns_accepted = 0
    alns_total = config.alns_iterations

    if alns_total > 0:
        # Build acceptance criterion
        if config.acceptance == "sa":
            acc = SimulatedAnnealing(start_temp=config.sa_temp, end_temp=0.1, cooling_rate=0.99)
        elif config.acceptance == "lahc":
            acc = LateAcceptanceHC(history_length=config.lahc_history, warmup=max(10, alns_total // 50))
        elif config.acceptance == "rtr":
            acc = RecordToRecordTravel(initial_deviation=100.0, min_deviation=0.0, decay_rate=0.997)
        else:
            acc = SimulatedAnnealing()

        # Build operators
        destroy_ops = {
            "random": RandomRemoval(),
            "worst": WorstRemoval(),
            "shaw": ShawRemoval(),
            "related": RelatedRemoval(),
        }
        repair_ops = {
            "greedy": GreedyInsertion(),
            "regret2": Regret2Insertion(),
            "regret3": Regret3Insertion(),
        }

        # Adaptive mode: cycle through operators
        destroy_names = list(destroy_ops.keys())
        repair_names = list(repair_ops.keys())

        str_tour = [str(n) for n in best_tour]
        best_cost_f = float(prob.tour_cost(best_tour))
        q = max(3, int(prob.dimension * config.alns_remove_pct))

        for i in range(alns_total):
            # Check time limit
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            if config.time_limit_ms > 0 and elapsed_ms >= config.time_limit_ms:
                alns_total = i  # actual iterations completed
                break

            # Adaptive: rotate operators every ~20 iterations
            if config.destroy_operator == "adaptive":
                d_op = destroy_ops[destroy_names[i % len(destroy_names)]]
            else:
                d_op = destroy_ops.get(config.destroy_operator, destroy_ops["random"])

            if config.repair_operator == "adaptive":
                r_op = repair_ops[repair_names[i % len(repair_names)]]
            else:
                r_op = repair_ops.get(config.repair_operator, repair_ops["regret2"])

            removed, remaining = d_op.destroy(str_tour, q, rng, distance_matrix=dm_str)
            new_tour_str = r_op.repair(remaining, removed, distance_matrix=dm_str)

            new_tour_int = [int(n) for n in new_tour_str]
            new_cost_f = float(prob.tour_cost(new_tour_int))

            result = acc.decide(best_cost_f, new_cost_f, best_cost_f, i, rng)
            if result.accepted and new_cost_f < best_cost_f:
                best_tour = new_tour_int
                best_cost_f = new_cost_f
                str_tour = new_tour_str
                alns_accepted += 1

        alns_cost = int(best_cost_f)

    # ── Phase 4: Final LS Polish ──
    final_ls_cost = alns_cost
    if config.ls_intensity in ("medium", "heavy") and alns_total > 0:
        rng2 = random.Random(config.seed + 999)
        polished, pl_cost, _ = MultiLayerLS.improve(
            best_tour, prob.cost_fn, rng2, intensity="light",
        )
        pc = int(pl_cost)
        if pc < alns_cost:
            best_tour = polished
            final_ls_cost = pc

    # ── Final result ──
    t_end = time.perf_counter()
    final_cost = prob.tour_cost(best_tour)

    result = RunResult(
        result_id=f"{prob.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{config.seed}",
        problem_name=prob.name,
        dimension=prob.dimension,
        optimal=prob.optimal,
        config=asdict(config),
        tour=best_tour,
        cost=final_cost,
        gap=prob.gap_pct(best_tour),
        time_ms=(t_end - t_start) * 1000,
        timestamp=datetime.now().isoformat(),
        init_cost=init_cost,
        ls_cost=ls_cost,
        alns_cost=alns_cost,
        final_ls_cost=final_ls_cost,
        ls_improvements=ls_improvements,
        alns_accepted=alns_accepted,
        alns_total=alns_total,
    )

    # ── Complete Parameter Recording ──
    result.all_parameters = {
        "selected_parameters": {
            "init_method": config.init_method,
            "ls_intensity": config.ls_intensity,
            "alns_iterations": config.alns_iterations,
            "destroy_operator": config.destroy_operator,
            "repair_operator": config.repair_operator,
            "acceptance": config.acceptance,
        },
        "available_options": dict(PARAMETER_OPTIONS),
    }

    return result


def solve_multi_run(prob: ProblemInstance, config: RunConfig, n_runs: int) -> List[RunResult]:
    """Run multiple times with different seeds, return all results."""
    results = []
    for i in range(n_runs):
        run_cfg = RunConfig(**{**asdict(config), "seed": config.seed + i * 13})
        result = solve_single(prob, run_cfg)
        result.result_id = f"{prob.name}_run{i+1}"
        results.append(result)
    return results


# ═══════════════════════════════════════════════════════════════════
# FAZ 1: E²BSO Solver
# ═══════════════════════════════════════════════════════════════════

@dataclass
class E2BSORunConfig:
    """Configuration for E²BSO optimization."""
    population_size: int = 40
    max_iterations: int = 500
    h_start: float = 0.8
    h_end: float = 0.2
    gamma: float = 0.5
    lahc_history: int = 500
    ls_time_limit: float = 0.5
    remove_ratio_range: Tuple[float, float] = (0.10, 0.30)
    seed: int = 42


def solve_e2bso(prob: ProblemInstance, cfg: E2BSORunConfig) -> RunResult:
    """Run E²BSO on a TSPLIB problem and return a RunResult.

    Args:
        prob: ProblemInstance (TSPLIB).
        cfg: E²BSO configuration.

    Returns:
        RunResult compatible with the existing result display pipeline.
    """
    t_start = time.perf_counter()

    # Build E²BSO config
    e2cfg = E2BSOConfig(
        population_size=cfg.population_size,
        max_iterations=cfg.max_iterations,
        h_start=cfg.h_start,
        h_end=cfg.h_end,
        gamma=cfg.gamma,
        lahc_history=cfg.lahc_history,
        ls_time_limit=cfg.ls_time_limit,
        remove_ratio_range=cfg.remove_ratio_range,
        seed=cfg.seed,
    )

    solver = E2BSO(e2cfg)
    e2_result = solver.solve(prob)

    gap_val = e2_result.gap if not math.isnan(e2_result.gap) else -1.0

    stats = e2_result.stats or {}
    phase_dist = stats.get("phase_distribution", {})

    result = RunResult(
        result_id=f"{prob.name}_e2bso_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cfg.seed}",
        problem_name=prob.name,
        dimension=prob.dimension,
        optimal=prob.optimal,
        config={
            "algorithm": "e2bso",
            "population_size": cfg.population_size,
            "max_iterations": cfg.max_iterations,
            "h_start": cfg.h_start,
            "h_end": cfg.h_end,
            "gamma": cfg.gamma,
            "lahc_history": cfg.lahc_history,
            "ls_time_limit": cfg.ls_time_limit,
            "remove_ratio_range": list(cfg.remove_ratio_range),
            "seed": cfg.seed,
        },
        tour=e2_result.tour,
        cost=e2_result.cost,
        gap=gap_val,
        time_ms=e2_result.time_ms,
        timestamp=datetime.now().isoformat(),
        init_cost=e2_result.cost,  # E²BSO manages its own init
        ls_cost=e2_result.cost,
        alns_cost=e2_result.cost,
        final_ls_cost=e2_result.cost,
        ls_improvements=stats.get("ls_improvements", 0),
        alns_accepted=stats.get("alns_injections", 0),
        alns_total=cfg.max_iterations,
    )

    # Store E²BSO-specific stats in all_parameters
    result.all_parameters = {
        "selected_parameters": {
            "algorithm": "E2BSO (FAZ 1)",
            "population_size": cfg.population_size,
            "max_iterations": cfg.max_iterations,
        },
        "e2bso_stats": {
            "entropy_final": stats.get("entropy_final", 0),
            "phase_distribution": phase_dist,
            "injection_count": stats.get("injection_count", 0),
            "swarm_updates": stats.get("swarm_updates", 0),
            "alns_injections": stats.get("alns_injections", 0),
            "final_ls_improvement": stats.get("final_ls_improvement", 0.0),
            "h_min_final": stats.get("h_min_final", 0),
            "h_max_final": stats.get("h_max_final", 0),
        },
    }

    return result


def configure_e2bso() -> E2BSORunConfig:
    """Interactive E²BSO configuration."""
    cfg = E2BSORunConfig()

    print("\n  ── E2BSO YAPILANDIRMA (FAZ 1) ──")
    print("  Enhanced Entropy-Balanced Swarm Optimization")
    print()

    # Population size
    print("  Populasyon Buyuklugu:")
    print("    [1] 20  — Hizli (kucuk problemler)")
    print("    [2] 40  — Standart (onerilen)")
    print("    [3] 80  — Kaliteli (orta problemler)")
    print("    [4] 120 — Agresif (buyuk problemler)")
    pop_choice = input("  Seciminiz [2]: ").strip()
    pop_map = {"1": 20, "2": 40, "3": 80, "4": 120}
    cfg.population_size = pop_map.get(pop_choice, 40)

    # Max iterations
    print(f"\n  Maksimum Iterasyon Sayisi (0 = adaptif):")
    iter_input = input("  Sayi [500]: ").strip()
    try:
        cfg.max_iterations = max(100, int(iter_input))
    except ValueError:
        cfg.max_iterations = 500

    # Entropy schedule
    print(f"\n  Entropy Zamanlama (h_start -> h_end):")
    print("    [1] Agresif soğuma (0.8 → 0.1)")
    print("    [2] Dengeli (0.8 → 0.2) — onerilen")
    print("    [3] Yavaş soğuma (0.9 → 0.4)")
    ent_choice = input("  Seciminiz [2]: ").strip()
    if ent_choice == "1":
        cfg.h_start, cfg.h_end = 0.8, 0.1
    elif ent_choice == "3":
        cfg.h_start, cfg.h_end = 0.9, 0.4
    else:
        cfg.h_start, cfg.h_end = 0.8, 0.2

    # LS time limit
    print(f"\n  Lokal Arama Zaman Siniri (saniye, bireysel):")
    ls_input = input(f"  [0.5]: ").strip()
    try:
        cfg.ls_time_limit = max(0.1, float(ls_input))
    except ValueError:
        cfg.ls_time_limit = 0.5

    return cfg


def print_e2bso_result(result: RunResult):
    """Print E²BSO result with extra entropy/phase info."""
    print(f"\n  {'─' * 60}")
    sym = gap_symbol(result.gap)
    gap_str = f"{result.gap:.2f}%" if result.gap >= 0 else "N/A"

    print(f"  {result.problem_name} (n={result.dimension})", end="")
    print(f", optimal={result.optimal}" if result.optimal else ", optimal=?")
    print(f"\n  {'─' * 60}")
    print(f"  Algoritma: E²BSO (FAZ 1)")

    cfg = result.config
    print(f"    Populasyon: {cfg.get('population_size', '?')}")
    print(f"    Iterasyon:  {cfg.get('max_iterations', '?')}")
    print(f"    h_start:    {cfg.get('h_start', '?')}")
    print(f"    h_end:      {cfg.get('h_end', '?')}")
    print()

    # E²BSO specific stats
    e2_stats = result.all_parameters.get("e2bso_stats", {})
    if e2_stats:
        print(f"    Entropy (son): {e2_stats.get('entropy_final', '?'):.3f}")
        print(f"    h_min (son):   {e2_stats.get('h_min_final', '?'):.3f}")
        print(f"    h_max (son):   {e2_stats.get('h_max_final', '?'):.3f}")
        pd = e2_stats.get("phase_distribution", {})
        if pd:
            print(f"    Faz dagilimi: inject={pd.get('inject', 0)}, "
                  f"normal={pd.get('normal', 0)}, compress={pd.get('compress', 0)}")
        print(f"    Swarm guncelleme: {e2_stats.get('swarm_updates', 0)}")
        print(f"    ALNS enjeksiyon: {e2_stats.get('alns_injections', 0)}")
        print(f"    Cesitlilik enjeksiyon: {e2_stats.get('injection_count', 0)}")
        print()

    print(f"    SONUC:     cost={result.cost:>8d}  gap={gap_str} {sym}  "
          f"süre={result.time_ms:.0f}ms")
    print(f"  {'─' * 60}")


# ═══════════════════════════════════════════════════════════════════
# FAZ 2: R²DMA Solver
# ═══════════════════════════════════════════════════════════════════

@dataclass
class R2DMARunConfig:
    """Configuration for R²DMA optimization."""
    population_size: int = 60
    max_iterations: int = 2000
    theta_base: float = 0.5
    segment_size: int = 100
    ls_time_limit: float = 2.0
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    delta_threshold: float = 0.02
    entropy_threshold: float = 0.15
    pulse_injection_rate: float = 0.25
    diversity_check_interval: int = 50
    alns_destroy_operators: Tuple[str, ...] = ("random", "worst", "shaw", "related")
    alns_repair_operators: Tuple[str, ...] = ("greedy", "regret2", "regret3")
    remove_ratio_range: Tuple[float, float] = (0.15, 0.30)
    ls_constructive: str = "moderate"
    ls_moderate: str = "light"
    ls_destructive: str = "moderate"
    ls_final: str = "full"
    initial_alpha_tw: float = 10.0
    initial_alpha_cap: float = 5.0
    seed: int = 42


def solve_r2dma(prob: ProblemInstance, cfg: R2DMARunConfig) -> RunResult:
    """Run R²DMA on a TSPLIB problem and return a RunResult.

    Args:
        prob: ProblemInstance (TSPLIB).
        cfg: R²DMA configuration.

    Returns:
        RunResult compatible with the existing result display pipeline.
    """
    t_start = time.perf_counter()

    # Build R²DMA config
    r2cfg = R2DMAConfig(
        population_size=cfg.population_size,
        max_iterations=cfg.max_iterations,
        theta_base=cfg.theta_base,
        segment_size=cfg.segment_size,
        ls_time_limit=cfg.ls_time_limit,
        sa_start_temp_factor=cfg.sa_start_temp_factor,
        sa_end_temp=cfg.sa_end_temp,
        sa_cooling_rate=cfg.sa_cooling_rate,
        delta_threshold=cfg.delta_threshold,
        entropy_threshold=cfg.entropy_threshold,
        pulse_injection_rate=cfg.pulse_injection_rate,
        diversity_check_interval=cfg.diversity_check_interval,
        alns_destroy_operators=cfg.alns_destroy_operators,
        alns_repair_operators=cfg.alns_repair_operators,
        remove_ratio_range=cfg.remove_ratio_range,
        ls_constructive=cfg.ls_constructive,
        ls_moderate=cfg.ls_moderate,
        ls_destructive=cfg.ls_destructive,
        ls_final=cfg.ls_final,
        initial_alpha_tw=cfg.initial_alpha_tw,
        initial_alpha_cap=cfg.initial_alpha_cap,
        seed=cfg.seed,
    )

    solver = R2DMA(r2cfg)
    r2_result = solver.solve(prob)

    gap_val = r2_result.gap if not math.isnan(r2_result.gap) else -1.0

    stats = r2_result.stats or {}
    mode_dist = stats.get("mode_distribution", {})

    result = RunResult(
        result_id=f"{prob.name}_r2dma_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cfg.seed}",
        problem_name=prob.name,
        dimension=prob.dimension,
        optimal=prob.optimal,
        config={
            "algorithm": "r2dma",
            "population_size": cfg.population_size,
            "max_iterations": cfg.max_iterations,
            "theta_base": cfg.theta_base,
            "segment_size": cfg.segment_size,
            "ls_time_limit": cfg.ls_time_limit,
            "sa_start_temp_factor": cfg.sa_start_temp_factor,
            "sa_end_temp": cfg.sa_end_temp,
            "sa_cooling_rate": cfg.sa_cooling_rate,
            "delta_threshold": cfg.delta_threshold,
            "entropy_threshold": cfg.entropy_threshold,
            "pulse_injection_rate": cfg.pulse_injection_rate,
            "diversity_check_interval": cfg.diversity_check_interval,
            "remove_ratio_range": list(cfg.remove_ratio_range),
            "ls_constructive": cfg.ls_constructive,
            "ls_moderate": cfg.ls_moderate,
            "ls_destructive": cfg.ls_destructive,
            "ls_final": cfg.ls_final,
            "initial_alpha_tw": cfg.initial_alpha_tw,
            "initial_alpha_cap": cfg.initial_alpha_cap,
            "seed": cfg.seed,
        },
        tour=r2_result.tour,
        cost=r2_result.cost,
        gap=gap_val,
        time_ms=r2_result.time_ms,
        timestamp=datetime.now().isoformat(),
        init_cost=r2_result.cost,
        ls_cost=r2_result.cost,
        alns_cost=r2_result.cost,
        final_ls_cost=r2_result.cost,
        ls_improvements=stats.get("final_ls_improvement", 0),
        alns_accepted=stats.get("sa_acceptances", 0),
        alns_total=cfg.max_iterations,
    )

    # Store R²DMA-specific stats in all_parameters
    result.all_parameters = {
        "selected_parameters": {
            "algorithm": "R2DMA (FAZ 2)",
            "population_size": cfg.population_size,
            "max_iterations": cfg.max_iterations,
            "theta_base": cfg.theta_base,
        },
        "r2dma_stats": {
            "constructive_count": stats.get("constructive_count", 0),
            "moderate_count": stats.get("moderate_count", 0),
            "destructive_count": stats.get("destructive_count", 0),
            "theta_final": stats.get("theta_final", cfg.theta_base),
            "mode_distribution": mode_dist,
            "injection_count": stats.get("injection_count", 0),
            "sa_acceptances": stats.get("sa_acceptances", 0),
            "sa_rejections": stats.get("sa_rejections", 0),
            "theta_adjustments": stats.get("theta_adjustments", 0),
            "final_ls_improvement": stats.get("final_ls_improvement", 0.0),
            "improvement_count": len(stats.get("improvement_log", [])),
        },
    }

    return result


def configure_r2dma() -> R2DMARunConfig:
    """Interactive R²DMA configuration."""
    cfg = R2DMARunConfig()

    print("\n  ── R2DMA YAPILANDIRMA (FAZ 2) ──")
    print("  Resonance-Reinforced Destroy and Merge Algorithm")
    print()

    # Population size
    print("  Populasyon Buyuklugu:")
    print("    [1] 30  — Hizli (kucuk problemler)")
    print("    [2] 60  — Standart (onerilen)")
    print("    [3] 100 — Kaliteli (orta problemler)")
    print("    [4] 150 — Agresif (buyuk problemler)")
    pop_choice = input("  Seciminiz [2]: ").strip()
    pop_map = {"1": 30, "2": 60, "3": 100, "4": 150}
    cfg.population_size = pop_map.get(pop_choice, 60)

    # Max iterations
    print(f"\n  Maksimum Iterasyon Sayisi (0 = adaptif):")
    iter_input = input("  Sayi [2000]: ").strip()
    try:
        cfg.max_iterations = max(100, int(iter_input))
    except ValueError:
        cfg.max_iterations = 2000

    # Theta base
    print(f"\n  Rezonans Eşik Değeri (theta_base):")
    print("    [1] 0.3 — Düşük eşik (daha fazla partner eşleşmesi)")
    print("    [2] 0.5 — Dengeli — onerilen")
    print("    [3] 0.7 — Yüksek eşik (sadece yüksek rezonans)")
    theta_choice = input("  Seciminiz [2]: ").strip()
    theta_map = {"1": 0.3, "2": 0.5, "3": 0.7}
    cfg.theta_base = theta_map.get(theta_choice, 0.5)

    # Seed
    print(f"\n  Rastgele Tohum (seed):")
    seed_input = input(f"  [42]: ").strip()
    try:
        cfg.seed = int(seed_input)
    except ValueError:
        cfg.seed = 42

    return cfg


def print_r2dma_result(result: RunResult):
    """Print R²DMA result with resonance-specific stats."""
    print(f"\n  {'─' * 60}")
    sym = gap_symbol(result.gap)
    gap_str = f"{result.gap:.2f}%" if result.gap >= 0 else "N/A"

    print(f"  {result.problem_name} (n={result.dimension})", end="")
    print(f", optimal={result.optimal}" if result.optimal else ", optimal=?")
    print(f"\n  {'─' * 60}")
    print(f"  Algoritma: R²DMA (FAZ 2)")

    cfg = result.config
    print(f"    Populasyon: {cfg.get('population_size', '?')}")
    print(f"    Iterasyon:  {cfg.get('max_iterations', '?')}")
    print(f"    theta_base: {cfg.get('theta_base', '?')}")
    print()

    # R²DMA specific stats
    r2_stats = result.all_parameters.get("r2dma_stats", {})
    if r2_stats:
        print(f"    Constructive: {r2_stats.get('constructive_count', 0)}")
        print(f"    Moderate:     {r2_stats.get('moderate_count', 0)}")
        print(f"    Destructive:  {r2_stats.get('destructive_count', 0)}")
        print(f"    theta (son):  {r2_stats.get('theta_final', '?'):.3f}")
        md = r2_stats.get("mode_distribution", {})
        if md:
            print(f"    Mod dagilimi: constructive={md.get('constructive', 0)}, "
                  f"moderate={md.get('moderate', 0)}, destructive={md.get('destructive', 0)}")
        print(f"    SA kabul:      {r2_stats.get('sa_acceptances', 0)}")
        print(f"    SA red:         {r2_stats.get('sa_rejections', 0)}")
        print(f"    Theta ayar:     {r2_stats.get('theta_adjustments', 0)}")
        print(f"    Cesitlilik enj: {r2_stats.get('injection_count', 0)}")
        print(f"    Iyilestirme:    {r2_stats.get('improvement_count', 0)}")
        print()

    print(f"    SONUC:     cost={result.cost:>8d}  gap={gap_str} {sym}  "
          f"süre={result.time_ms:.0f}ms")
    print(f"  {'─' * 60}")


# ═══════════════════════════════════════════════════════════════════
# FAZ 3: PAOEA Solver
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PAOEARunConfig:
    """Configuration for P-AOEA optimization."""
    population_size: int = 50
    max_iterations: int = 1500
    genome_population_size: int = 15
    meta_evolution_interval: int = 100
    tournament_size: int = 3
    crossover_rate: float = 0.7
    mutation_rate: float = 0.3
    ls_time_limit: float = 1.0
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    entropy_threshold: float = 0.15
    diversity_check_interval: int = 50
    diversity_injection_rate: float = 0.2
    initial_alpha_tw: float = 10.0
    initial_alpha_cap: float = 5.0
    seed: int = 42


def solve_paoea(prob: ProblemInstance, cfg: PAOEARunConfig) -> RunResult:
    """Run P-AOEA on a TSPLIB problem and return a RunResult."""
    t_start = time.perf_counter()

    p_cfg = PAOEAConfig(
        population_size=cfg.population_size,
        max_iterations=cfg.max_iterations,
        genome_population_size=cfg.genome_population_size,
        meta_evolution_interval=cfg.meta_evolution_interval,
        tournament_size=cfg.tournament_size,
        crossover_rate=cfg.crossover_rate,
        mutation_rate=cfg.mutation_rate,
        ls_time_limit=cfg.ls_time_limit,
        sa_start_temp_factor=cfg.sa_start_temp_factor,
        sa_end_temp=cfg.sa_end_temp,
        sa_cooling_rate=cfg.sa_cooling_rate,
        entropy_threshold=cfg.entropy_threshold,
        diversity_check_interval=cfg.diversity_check_interval,
        diversity_injection_rate=cfg.diversity_injection_rate,
        initial_alpha_tw=cfg.initial_alpha_tw,
        initial_alpha_cap=cfg.initial_alpha_cap,
        seed=cfg.seed,
    )

    solver = PAOEA(p_cfg)
    pa_result = solver.solve(prob)

    gap_val = pa_result.gap if not math.isnan(pa_result.gap) else -1.0

    stats = pa_result.stats or {}
    genome_dist = stats.get("best_genome_info", {})

    result = RunResult(
        result_id=f"{prob.name}_paoea_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cfg.seed}",
        problem_name=prob.name,
        dimension=prob.dimension,
        optimal=prob.optimal,
        config={
            "algorithm": "paoea",
            "population_size": cfg.population_size,
            "max_iterations": cfg.max_iterations,
            "genome_population_size": cfg.genome_population_size,
            "meta_evolution_interval": cfg.meta_evolution_interval,
            "tournament_size": cfg.tournament_size,
            "crossover_rate": cfg.crossover_rate,
            "mutation_rate": cfg.mutation_rate,
            "ls_time_limit": cfg.ls_time_limit,
            "seed": cfg.seed,
        },
        tour=pa_result.tour,
        cost=pa_result.cost,
        gap=gap_val,
        time_ms=pa_result.time_ms,
        timestamp=datetime.now().isoformat(),
        init_cost=pa_result.cost,
        ls_cost=pa_result.cost,
        alns_cost=pa_result.cost,
        final_ls_cost=pa_result.cost,
        ls_improvements=stats.get("final_ls_improvement", 0),
        alns_accepted=stats.get("total_acceptances", 0),
        alns_total=cfg.max_iterations,
    )

    result.all_parameters = {
        "selected_parameters": {
            "algorithm": "PAOEA (FAZ 3)",
            "population_size": cfg.population_size,
            "max_iterations": cfg.max_iterations,
            "genome_population_size": cfg.genome_population_size,
        },
        "paoea_stats": {
            "meta_evolutions": stats.get("meta_evolutions", 0),
            "genome_elite_fitness": stats.get("genome_elite_fitness", 0),
            "best_genome_info": genome_dist,
            "diversity_injections": stats.get("diversity_injections", 0),
            "total_acceptances": stats.get("total_acceptances", 0),
            "total_rejections": stats.get("total_rejections", 0),
            "final_ls_improvement": stats.get("final_ls_improvement", 0.0),
            "improvement_count": len(stats.get("improvement_log", [])),
        },
    }

    return result


def configure_paoea() -> PAOEARunConfig:
    """Interactive P-AOEA configuration."""
    cfg = PAOEARunConfig()

    print("\n  ── PAOEA YAPILANDIRMA (FAZ 3) ──")
    print("  Production Adaptive Operator Evolution Algorithm")
    print("  Meta-evrim: Operator genomlari adaptif olarak gelisir")
    print()

    # Population size
    print("  Cozum Populasyonu Buyuklugu:")
    print("    [1] 30  — Hizli (kucuk problemler)")
    print("    [2] 50  — Standart (onerilen)")
    print("    [3] 80  — Kaliteli (orta problemler)")
    print("    [4] 120 — Agresif (buyuk problemler)")
    pop_choice = input("  Seciminiz [2]: ").strip()
    pop_map = {"1": 30, "2": 50, "3": 80, "4": 120}
    cfg.population_size = pop_map.get(pop_choice, 50)

    # Max iterations
    print(f"\n  Maksimum Iterasyon Sayisi:")
    iter_input = input("  Sayi [1500]: ").strip()
    try:
        cfg.max_iterations = max(100, int(iter_input))
    except ValueError:
        cfg.max_iterations = 1500

    # Genome population
    print(f"\n  Genome Populasyonu (farkli operator stratejileri):")
    print("    [1] 8   — Hizli meta-evrim")
    print("    [2] 15  — Standart (onerilen)")
    print("    [3] 25  — Zengin strateji havuzu")
    genome_choice = input("  Seciminiz [2]: ").strip()
    genome_map = {"1": 8, "2": 15, "3": 25}
    cfg.genome_population_size = genome_map.get(genome_choice, 15)

    # Meta-evolution interval
    print(f"\n  Meta-Evrim Araligi (her N iterasyonda genomlari evril)")
    print("    [1] 50   — Sik evrim (hizli adaptasyon)")
    print("    [2] 100  — Standart (onerilen)")
    print("    [3] 200  — Seyrek evrim (kararli)")
    meta_choice = input("  Seciminiz [2]: ").strip()
    meta_map = {"1": 50, "2": 100, "3": 200}
    cfg.meta_evolution_interval = meta_map.get(meta_choice, 100)

    # LS time limit
    print(f"\n  Lokal Arama Zaman Siniri (saniye, bireysel):")
    ls_input = input(f"  [1.0]: ").strip()
    try:
        cfg.ls_time_limit = max(0.1, float(ls_input))
    except ValueError:
        cfg.ls_time_limit = 1.0

    return cfg


def print_paoea_result(result: RunResult):
    """Print P-AOEA result with extra genome/meta-evolution info."""
    print(f"\n  {'─' * 60}")
    sym = gap_symbol(result.gap)
    gap_str = f"{result.gap:.2f}%" if result.gap >= 0 else "N/A"

    print(f"  {result.problem_name} (n={result.dimension})", end="")
    print(f", optimal={result.optimal}" if result.optimal else ", optimal=?")
    print(f"\n  {'─' * 60}")
    print(f"  Algoritma: PAOEA (FAZ 3)")

    cfg = result.config
    print(f"    Cozum Populasyonu: {cfg.get('population_size', '?')}")
    print(f"    Iterasyon:         {cfg.get('max_iterations', '?')}")
    print(f"    Genome Populasyonu: {cfg.get('genome_population_size', '?')}")
    print(f"    Meta-Evrim Araligi: {cfg.get('meta_evolution_interval', '?')}")
    print()

    # P-AOEA specific stats
    pa_stats = result.all_parameters.get("paoea_stats", {})
    if pa_stats:
        print(f"    Meta-Evrim Sayisi: {pa_stats.get('meta_evolutions', 0)}")
        print(f"    Genome Elite Fitness: {pa_stats.get('genome_elite_fitness', 0):.4f}")
        gi = pa_stats.get("best_genome_info", {})
        if gi:
            print(f"    En Iyi Genome:")
            print(f"      Destroy:   {gi.get('destroy_ops', [])}")
            print(f"      Repair:    {gi.get('repair_ops', [])}")
            print(f"      Acceptance: {gi.get('acceptance_type', '?')}")
            print(f"      LS Intensity: {gi.get('ls_intensity', '?')}")
        print(f"    Cesitlilik Enjeksiyon: {pa_stats.get('diversity_injections', 0)}")
        print(f"    Kabul/Red: {pa_stats.get('total_acceptances', 0)}/{pa_stats.get('total_rejections', 0)}")
        print(f"    Iyilestirme Sayisi: {pa_stats.get('improvement_count', 0)}")
        print()

    print(f"    SONUC:     cost={result.cost:>8d}  gap={gap_str} {sym}  "
          f"süre={result.time_ms:.0f}ms")
    print(f"  {'─' * 60}")


# ═══════════════════════════════════════════════════════════════════
# Display Helpers
# ═══════════════════════════════════════════════════════════════════

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}sn"
    elif seconds < 3600:
        return f"{int(seconds // 60)}dk {int(seconds % 60)}sn"
    else:
        return f"{int(seconds // 3600)}sa {int((seconds % 3600) // 60)}dk"


def gap_symbol(gap: float) -> str:
    if math.isnan(gap):
        return "?"
    if gap <= 1.0:
        return "*"
    if gap <= 3.0:
        return "+"
    if gap <= 5.0:
        return "o"
    return "x"


def progress_bar(completed: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "[]" * width
    filled = int((completed / total) * width)
    return "█" * filled + "░" * (width - filled)


# ═══════════════════════════════════════════════════════════════════
# Interactive Menus
# ═══════════════════════════════════════════════════════════════════

def _parse_number_selection(
    user_input: str,
    problem_map: Dict[int, TSPLIBProblemInfo],
    cat_ranges: Dict[str, Tuple[int, int]],
) -> Optional[List[str]]:
    """Parse number-based selection like '1,3-6,10' and return problem names."""
    selected_names: List[str] = []
    selected_indices: List[int] = []

    parts = user_input.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            try:
                s, e = part.split("-")
                start_num = int(s)
                end_num = int(e)
                for num in range(start_num, end_num + 1):
                    if num in problem_map and num not in selected_indices:
                        selected_indices.append(num)
                        selected_names.append(problem_map[num].name)
            except (ValueError, KeyError):
                return None
        else:
            try:
                i = int(part)
                if i in problem_map and i not in selected_indices:
                    selected_indices.append(i)
                    selected_names.append(problem_map[i].name)
            except (ValueError, KeyError):
                return None

    return selected_names if selected_names else None


def list_and_select_problems() -> Optional[List[str]]:
    """Show available problems and let user pick one or more.

    Returns a list of problem names. Supports:
      - Individual numbers: 1,5,7
      - Ranges: 3-6
      - Combined: 1,3-6,10
      - Category aliases: k=small, o=medium, b=large (returns all in category)
      - 'all' for everything
      - Direct name entry for download (returns single-element list)
    """
    print("\n" + "=" * 70)
    print("  PROBLEM SECIMI (Coklu Secim Destekli)")
    print("=" * 70)

    problems = get_available_problems()
    if not problems:
        print("\n  [!] Hicbir TSPLIB problemi bulunamadi.")
        print("  Indirmek icin problem adi yazin (orn: eil51, berlin52)")
        name = input("\n  Problem adi: ").strip().lower()
        if name:
            print(f"  Indiriliyor: {name}...")
            path = download_tsplib_problem(name)
            if path:
                print(f"  [OK] {name} indirildi!")
                return [name]
        return None

    categories = {"small": [], "medium": [], "large": []}
    for p in problems:
        if p.category in categories:
            categories[p.category].append(p)

    idx = 1
    problem_map: Dict[int, TSPLIBProblemInfo] = {}
    cat_ranges: Dict[str, Tuple[int, int]] = {}

    cat_labels = {"small": "KUCUK (n≤100)", "medium": "ORTA (101-500)", "large": "BUYUK (n>500)"}

    for cat_key in ["small", "medium", "large"]:
        probs = sorted(categories[cat_key], key=lambda x: x.dimension)
        if not probs:
            continue
        start_idx = idx
        print(f"\n  [{cat_labels[cat_key]}]")
        for p in probs:
            opt_val = TSPLIB_OPTIMALS.get(p.name)
            if opt_val is None:
                for k, v in TSPLIB_OPTIMALS.items():
                    if k.lower() == p.name.lower():
                        opt_val = v
                        break
            opt_str = f"opt={opt_val}" if opt_val else "opt=?"
            has_file = "✓" if p.file_path else "↓"
            print(f"    {idx:>3}. {p.name:<14} (n={p.dimension:>5}) {opt_str:<12} {has_file}")
            problem_map[idx] = p
            idx += 1
        cat_ranges[cat_key] = (start_idx, idx - 1)

    print(f"\n  Toplam: {len(problem_map)} problem")
    print("  ─" * 35)
    print("  Coklu secim: '1,5,7' veya '1,3-6,10' (virgul + aralik)")
    print("  Alias: 'k' = kucuk, 'o' = orta, 'b' = buyuk, 'all' = tumu")
    print("  Arama: Dogrudan problem adi yazin (orn: eil51, berlin52)")
    print("  Indir: Olmayan problem adini yazin → otomatik indirilir")
    print("  ─" * 35)

    user_input = input("\n  Seciminiz: ").strip().lower()

    # Alias: all
    if user_input in ("all", "tum", "tüm", "hepsi"):
        all_names = [problem_map[i].name for i in sorted(problem_map.keys())]
        print(f"\n  {len(all_names)} problem secildi:")
        print(f"    {', '.join(all_names)}")
        confirm = input("  Devam? [E/H]: ").strip().upper()
        if confirm == "E":
            return all_names
        return None

    # Alias: k = small
    if user_input in ("k", "kucuk", "küçük"):
        sr, er = cat_ranges.get("small", (0, 0))
        cat_names = [problem_map[i].name for i in range(sr, er + 1) if i in problem_map]
        print(f"\n  Kucuk kategori: {len(cat_names)} problem secildi")
        print(f"    {', '.join(cat_names)}")
        confirm = input("  Devam? [E/H]: ").strip().upper()
        if confirm == "E":
            return cat_names
        return None

    # Alias: o = medium
    if user_input in ("o", "orta"):
        sr, er = cat_ranges.get("medium", (0, 0))
        cat_names = [problem_map[i].name for i in range(sr, er + 1) if i in problem_map]
        print(f"\n  Orta kategori: {len(cat_names)} problem secildi")
        print(f"    {', '.join(cat_names)}")
        confirm = input("  Devam? [E/H]: ").strip().upper()
        if confirm == "E":
            return cat_names
        return None

    # Alias: b = large
    if user_input in ("b", "buyuk", "büyük"):
        sr, er = cat_ranges.get("large", (0, 0))
        cat_names = [problem_map[i].name for i in range(sr, er + 1) if i in problem_map]
        print(f"\n  Buyuk kategori: {len(cat_names)} problem secildi")
        print(f"    {', '.join(cat_names)}")
        confirm = input("  Devam? [E/H]: ").strip().upper()
        if confirm == "E":
            return cat_names
        return None

    # Number-based selection (single, comma-separated, ranges)
    parsed = _parse_number_selection(user_input, problem_map, cat_ranges)
    if parsed is not None:
        if len(parsed) == 1:
            print(f"\n  1 problem secildi: {parsed[0]}")
            return parsed
        print(f"\n  {len(parsed)} problem secildi:")
        print(f"    {', '.join(parsed)}")
        confirm = input("  Devam? [E/H]: ").strip().upper()
        if confirm == "E":
            return parsed
        return None

    # Direct name search / download
    name = user_input.strip()
    if name:
        # Check if it exists locally
        for p in problems:
            if p.name == name:
                print(f"\n  1 problem secildi: {name}")
                return [name]
        # Try to download
        print(f"\n  '{name}' yerel olarak bulunamadi, TSPLIB arsivinden indiriliyor...")
        path = download_tsplib_problem(name)
        if path:
            print(f"  [OK] {name} indirildi ve kullanima hazir!")
            return [name]
        else:
            print(f"  [HATA] '{name}' indirilemedi. TSPLIB arsivinde bulunamadi.")
            # Fuzzy match
            matches = [p.name for p in problems if name in p.name]
            if matches:
                print(f"  Benzer: {', '.join(matches[:5])}")
            return None

    return None


def select_pipeline() -> Tuple[str, RunConfig]:
    """Let user choose a pipeline preset or configure custom."""
    print("\n" + "=" * 70)
    print("  PIPELINE SECIMI")
    print("=" * 70)

    print("\n  Hazir Pipeline'lar:")
    for key, preset in PIPELINE_PRESETS.items():
        print(f"    [{key[0].upper()}] {preset['label']:<20} — {preset['desc']}")

    print(f"    [O] Ozel Ayarlar — Her parametreyi kendin sec")
    print()

    choice = input("  Seciminiz: ").strip().lower()

    preset_key = None
    for k in PIPELINE_PRESETS:
        if choice == k[0] or choice == k:
            preset_key = k
            break

    if preset_key:
        p = PIPELINE_PRESETS[preset_key]
        config = RunConfig(
            init_method=p["init"],
            ls_intensity=p["ls_intensity"],
            alns_iterations=p["alns_iters"],
            acceptance=p["acceptance"],
        )
        print(f"\n  ✓ {p['label']} secildi")
        return preset_key, config

    # Custom configuration
    return "ozel", configure_custom()


def select_pipelines() -> List[Tuple[str, RunConfig]]:
    """Let user select one or more pipelines for comparison.

    Returns a list of (pipeline_label, RunConfig) tuples.
    Supports:
      - Single preset letter: 'H' → [("Hızlı", config)]
      - Multiple presets: 'H,D' → [("Hızlı", ...), ("Dengeli", ...)]
      - All presets: 'all'
      - Mix presets + custom: 'H,O' → [("Hızlı", ...), ("Özel #1", ...)]
    """
    print("\n" + "=" * 70)
    print("  PIPELINE SECIMI (Karsilastirma Modu)")
    print("=" * 70)

    print("\n  Hazir Pipeline'lar (birden fazla secilebilir):")
    for key, preset in PIPELINE_PRESETS.items():
        print(f"    [{key[0].upper()}] {preset['label']:<20} — {preset['desc']}")

    print(f"    [O] Ozel Ayarlar — Her parametreyi kendin sec")
    print()
    print("  Kullanim:")
    print("    Tek:       'H' (sadece Hizli)")
    print("    Coklu:     'H,D,K' (Hizli + Dengeli + Kaliteli)")
    print("    Tum preset: 'all'")
    print("    Karisik:   'H,O' (Hizli + Ozel ayarlar)")
    print()

    choice = input("  Seciminiz: ").strip()

    if not choice:
        return []

    selected: List[Tuple[str, RunConfig]] = []
    custom_counter = 0

    # 'all' → all presets
    if choice.strip().lower() == "all":
        for key, preset in PIPELINE_PRESETS.items():
            config = RunConfig(
                init_method=preset["init"],
                ls_intensity=preset["ls_intensity"],
                alns_iterations=preset["alns_iters"],
                acceptance=preset["acceptance"],
            )
            selected.append((preset["label"], config))
        print(f"\n  ✓ {len(selected)} pipeline secildi (tum presetler)")
        return selected

    # Parse comma-separated choices
    parts = [c.strip() for c in choice.upper().split(",") if c.strip()]

    for part in parts:
        # Check if it matches a preset
        preset_key = None
        for k in PIPELINE_PRESETS:
            if part == k[0].upper() or part.lower() == k:
                preset_key = k
                break

        if preset_key:
            p = PIPELINE_PRESETS[preset_key]
            config = RunConfig(
                init_method=p["init"],
                ls_intensity=p["ls_intensity"],
                alns_iterations=p["alns_iters"],
                acceptance=p["acceptance"],
            )
            selected.append((p["label"], config))
        elif part == "O":
            # Custom pipeline
            custom_counter += 1
            print(f"\n  ── Ozel Pipeline #{custom_counter} ──")
            custom_config = configure_custom()
            selected.append((f"Özel #{custom_counter}", custom_config))
        else:
            print(f"  [!] '{part}' taninmadi, atlandi.")

    if not selected:
        print("  [!] Gecerli bir secim yapilmadi.")
        return []

    labels = [label for label, _ in selected]
    print(f"\n  ✓ {len(selected)} pipeline secildi: {', '.join(labels)}")
    return selected


def configure_custom() -> RunConfig:
    """Interactive custom configuration."""
    config = RunConfig()

    print("\n  ── OZEL AYARLAR ──")

    # Init method
    print("\n  Baslangic Yontemi:")
    print("    [1] Multi-Start (NN+CW+Regret+Random) — onerilen")
    print("    [2] Sadece Nearest Neighbor")
    print("    [3] Sadece Clarke-Wright")
    print("    [4] Sadece Regret Insertion")
    print("    [5] Sadece Random")
    init_choice = input("  Seciminiz [1]: ").strip()
    init_map = {"1": "multi", "2": "nn", "3": "cw", "4": "regret", "5": "random"}
    config.init_method = init_map.get(init_choice, "multi")

    # LS intensity
    print("\n  Yerel Arama Yoğunlugu:")
    print("    [1] Light  — Sadece 2-opt (hizli)")
    print("    [2] Medium — 2-opt + Or-opt + Swap")
    print("    [3] Heavy  — Tum katmanlar (2-opt + Or-opt + 3-opt + Swap)")
    print("    [0] Yok    — LS atlansin")
    ls_choice = input("  Seciminiz [2]: ").strip()
    ls_map = {"0": "none", "1": "light", "2": "medium", "3": "heavy"}
    config.ls_intensity = ls_map.get(ls_choice, "medium")

    # ALNS iterations
    print("\n  ALNS Iterasyon Sayisi (0 = ALNS yok):")
    alns_input = input("  Sayi [200]: ").strip()
    try:
        config.alns_iterations = max(0, int(alns_input))
    except ValueError:
        config.alns_iterations = 200

    # Destroy operator
    if config.alns_iterations > 0:
        print("\n  Destroy Operator:")
        print("    [1] Random Removal")
        print("    [2] Worst Removal")
        print("    [3] Shaw Removal (benzerlik tabanli)")
        print("    [4] Related Removal (baglanti tabanli)")
        print("    [5] Adaptive (dongude degisir) — onerilen")
        d_choice = input("  Seciminiz [5]: ").strip()
        d_map = {"1": "random", "2": "worst", "3": "shaw", "4": "related", "5": "adaptive"}
        config.destroy_operator = d_map.get(d_choice, "adaptive")

        # Repair operator
        print("\n  Repair Operator:")
        print("    [1] Greedy Insertion")
        print("    [2] Regret-2 Insertion — onerilen")
        print("    [3] Regret-3 Insertion")
        print("    [4] Adaptive (dongude degisir)")
        r_choice = input("  Seciminiz [2]: ").strip()
        r_map = {"1": "greedy", "2": "regret2", "3": "regret3", "4": "adaptive"}
        config.repair_operator = r_map.get(r_choice, "regret2")

        # Acceptance criterion
        print("\n  Kabul Kriteri:")
        print("    [1] Simulated Annealing (SA)")
        print("    [2] Late Acceptance HC (LAHC)")
        print("    [3] Record-to-Record Travel (RTR)")
        a_choice = input("  Seciminiz [1]: ").strip()
        a_map = {"1": "sa", "2": "lahc", "3": "rtr"}
        config.acceptance = a_map.get(a_choice, "sa")

    # Remove percentage
    print(f"\n  ALNS Kaldirma Orani (mevcut: {config.alns_remove_pct*100:.0f}%):")
    pct_input = input("  Yuzde [10]: ").strip()
    try:
        config.alns_remove_pct = max(0.05, min(0.50, int(pct_input) / 100))
    except ValueError:
        pass

    # Time limit
    print(f"\n  Zaman Siniri (ms, 0 = sinirsiz, mevcut: {config.time_limit_ms:.0f}):")
    tl_input = input("  ms [30000]: ").strip()
    try:
        config.time_limit_ms = max(0, float(tl_input))
    except ValueError:
        pass

    return config


def select_n_runs() -> int:
    """Ask how many runs to perform."""
    print("\n  Kac kez calistirilsin? (farkli seed'lerle)")
    print("    [1] 1 kez (hizli test)")
    print("    [3] 3 kez (onerilen — istatistikli)")
    print("    [5] 5 kez")
    print("    [10] 10 kez (guvenilir ortalama)")
    choice = input("  Seciminiz [3]: ").strip()
    try:
        return max(1, int(choice))
    except ValueError:
        return 3


# ═══════════════════════════════════════════════════════════════════
# Result Display & Persistence
# ═══════════════════════════════════════════════════════════════════

def print_single_result(result: RunResult):
    """Print one run result beautifully."""
    sym = gap_symbol(result.gap)
    gap_str = f"{result.gap:.2f}%" if not math.isnan(result.gap) else "N/A"

    print(f"\n  {'─' * 60}")
    print(f"  {result.problem_name} (n={result.dimension})", end="")
    print(f", optimal={result.optimal}" if result.optimal else ", optimal=?")
    print(f"\n  {'─' * 60}")
    print(f"  Pipeline: {result.config.get('init_method', '?')} → "
          f"LS({result.config.get('ls_intensity', '?')}) → "
          f"ALNS({result.config.get('alns_iterations', 0)} iter) → "
          f"{result.config.get('acceptance', '?').upper()}")
    print()
    print(f"    Baslangic:  cost={result.init_cost:>8d}")
    print(f"    + LS:       cost={result.ls_cost:>8d}  ({result.ls_improvements} iyilestirme)")
    if result.alns_total > 0:
        print(f"    + ALNS:     cost={result.alns_cost:>8d}  ({result.alns_accepted}/{result.alns_total} kabul)")
    if result.final_ls_cost != result.alns_cost:
        print(f"    + Polish:   cost={result.final_ls_cost:>8d}")
    print()
    print(f"    SONUC:     cost={result.cost:>8d}  gap={gap_str} {sym}  "
          f"süre={result.time_ms:.0f}ms")
    print(f"  {'─' * 60}")


def print_multi_summary(results: List[RunResult]):
    """Print summary table for multiple runs."""
    if not results:
        return

    r0 = results[0]
    costs = [r.cost for r in results]
    gaps = [r.gap for r in results if not math.isnan(r.gap)]
    times = [r.time_ms for r in results]

    best = min(results, key=lambda x: x.cost)
    worst = max(results, key=lambda x: x.cost)

    print(f"\n  {'═' * 60}")
    print(f"  OZET: {r0.problem_name} (n={r0.dimension})", end="")
    print(f", optimal={r0.optimal}" if r0.optimal else "")
    print(f"\n  {'═' * 60}")
    print(f"    Calistirma:  {len(results)} kez")
    if gaps:
        print(f"    Best GAP:    {min(gaps):.2f}%  (cost={best.cost})")
        print(f"    Avg GAP:     {sum(gaps)/len(gaps):.2f}%")
        print(f"    Worst GAP:   {max(gaps):.2f}%  (cost={worst.cost})")
    print(f"    Best Cost:   {min(costs)}")
    print(f"    Avg Cost:    {sum(costs)/len(costs):.1f}")
    print(f"    Avg Time:    {sum(times)/len(times):.0f}ms")
    print(f"    StdDev Cost: {(sum((c - sum(costs)/len(costs))**2 for c in costs) / len(costs)) ** 0.5:.1f}")

    # Per-run detail
    print(f"\n    {'Run':<6} {'Cost':>8} {'Gap':>8} {'Time':>8} {'Init':>8} {'LS':>8} {'ALNS':>8}")
    print(f"    {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for i, r in enumerate(results):
        g = f"{r.gap:.2f}%" if not math.isnan(r.gap) else "N/A"
        sym = gap_symbol(r.gap) if not math.isnan(r.gap) else "?"
        print(f"    Run{i+1:<3} {r.cost:>8d} {g:>8} {r.time_ms:>7.0f}ms {r.init_cost:>8d} {r.ls_cost:>8d} {r.alns_cost:>8d}")

    print(f"  {'═' * 60}")


def print_pipeline_comparison(
    problem_name: str,
    dimension: int,
    optimal: Optional[int],
    pipeline_results: List[Tuple[str, RunResult]],
):
    """Print a comparative table of pipeline results for a single problem.

    Args:
        problem_name: Name of the problem (e.g., 'eil51')
        dimension: Problem dimension
        optimal: Optimal value if known
        pipeline_results: List of (pipeline_label, RunResult) tuples
    """
    if not pipeline_results:
        return

    opt_str = str(optimal) if optimal else "?"
    header = f"KARSILASTIRMALI PIPELINE SONUCLARI: {problem_name} (n={dimension}, opt={opt_str})"

    print(f"\n  {header}")
    print(f"  {'═' * 72}")
    print(f"  {'Pipeline':<14} {'Init':<8} {'LS':<8} {'ALNS iter':>10} {'Accept':<7} "
          f"{'Cost':>7} {'Gap':>8} {'Time':>8}")
    print(f"  {'─' * 72}")

    for label, result in pipeline_results:
        cfg = result.config
        init_m = cfg.get("init_method", "?")
        ls_int = cfg.get("ls_intensity", "?")
        alns_it = cfg.get("alns_iterations", 0)
        acc = cfg.get("acceptance", "?").upper()
        gap_str = f"{result.gap:.2f}%" if not math.isnan(result.gap) else "N/A"

        # Format time nicely
        if result.time_ms < 1000:
            time_str = f"{result.time_ms:.0f}ms"
        else:
            time_str = f"{result.time_ms / 1000:.1f}s"

        print(f"  {label:<14} {init_m:<8} {ls_int:<8} {alns_it:>10} {acc:<7} "
              f"{result.cost:>7} {gap_str:>8} {time_str:>8}")

    print(f"  {'═' * 72}")

    # Best result highlight
    valid_results = [(lbl, r) for lbl, r in pipeline_results if not math.isnan(r.gap)]
    if valid_results:
        best_label, best_result = min(valid_results, key=lambda x: x[1].cost)
        best_gap_str = f"{best_result.gap:.2f}%"
        print(f"  ★ En İyi: {best_label} — cost={best_result.cost}, gap={best_gap_str}")
    elif pipeline_results:
        best_label, best_result = min(pipeline_results, key=lambda x: x[1].cost)
        print(f"  ★ En İyi: {best_label} — cost={best_result.cost} (optimal bilinmiyor)")


def save_results(results: List[RunResult], filename: Optional[str] = None):
    """Save results to JSON file."""
    if not results:
        return

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"faz0_results_{ts}.json"

    filepath = os.path.join(RESULTS_DIR, filename)
    data = {
        "version": SOTA_INFRA_VERSION,
        "timestamp": datetime.now().isoformat(),
        "total_runs": len(results),
        "runs": [asdict(r) for r in results],
    }

    # Summary
    if len(results) > 1:
        costs = [r.cost for r in results]
        gaps = [r.gap for r in results if not math.isnan(r.gap)]
        data["summary"] = {
            "problem": results[0].problem_name,
            "best_cost": min(costs),
            "avg_cost": sum(costs) / len(costs),
            "best_gap": min(gaps) if gaps else None,
            "avg_gap": sum(gaps) / len(gaps) if gaps else None,
            "avg_time_ms": sum(r.time_ms for r in results) / len(results),
        }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  [KAYIT] Sonuclar kaydedildi: {filepath}")
    return filepath


def save_comparison_results(
    all_results: List[RunResult],
    problem_names: List[str],
    pipeline_labels: List[str],
    comparison_summary: Dict,
    filename: Optional[str] = None,
):
    """Save multi-pipeline comparison results to JSON with rich metadata.

    Args:
        all_results: All RunResult objects from the experiment
        problem_names: List of problem names that were tested
        pipeline_labels: List of pipeline labels that were used
        comparison_summary: Per-problem comparison dict
        filename: Optional custom filename
    """
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"faz0_comparison_{ts}.json"

    filepath = os.path.join(RESULTS_DIR, filename)
    data = {
        "version": SOTA_INFRA_VERSION,
        "timestamp": datetime.now().isoformat(),
        "experiment_type": "multi_pipeline_comparison",
        "problems": problem_names,
        "pipelines_tested": pipeline_labels,
        "total_runs": len(all_results),
        "runs": [asdict(r) for r in all_results],
        "comparison_summary": comparison_summary,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  [KAYIT] Karsilastirma sonuclari kaydedildi: {filepath}")
    return filepath


def load_saved_results() -> Dict:
    """Load all previous results from JSON files."""
    all_results: Dict[str, List[dict]] = {}
    if not os.path.isdir(RESULTS_DIR):
        return all_results

    for fname in sorted(os.listdir(RESULTS_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(RESULTS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for run in data.get("runs", []):
                pname = run.get("problem_name", "")
                if pname not in all_results:
                    all_results[pname] = []
                all_results[pname].append(run)
        except Exception:
            pass

    return all_results


# ═══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════
# Graceful Shutdown & Incremental Save
# ══════════════════════════════════════════════════════════

_shutdown = False
_pending_results: List[RunResult] = []
_incremental_filepath: Optional[str] = None
_experiment_metadata: dict = {}


def _init_incremental_save(
    problem_names: List[str],
    pipeline_labels: List[str],
    n_runs: int,
    total_tasks: int,
) -> str:
    """Incremental kayıt dosyasını başlat. Her sonuç geldikçe append eder."""
    global _incremental_filepath, _experiment_metadata

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"faz0_incremental_{ts}.json"
    filepath = os.path.join(RESULTS_DIR, fname)

    _experiment_metadata = {
        "version": SOTA_INFRA_VERSION,
        "timestamp": datetime.now().isoformat(),
        "experiment_type": "multi_pipeline_comparison",
        "problems": problem_names,
        "pipelines_tested": pipeline_labels,
        "n_runs": n_runs,
        "total_tasks": total_tasks,
        "completed_tasks": 0,
        "runs": [],
        "status": "in_progress",
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(_experiment_metadata, f, indent=2, ensure_ascii=False, default=str)

    _incremental_filepath = filepath
    return filepath


def _append_incremental_result(result: RunResult):
    """Tek bir sonucu incremental dosyaya anında kaydet.
    Ctrl+C veya çökmelerde bile o ana kadar tüm sonuçlar korunur.
    Atomik write: temp → rename.
    """
    global _experiment_metadata, _incremental_filepath

    if not _incremental_filepath or not os.path.exists(_incremental_filepath):
        return

    try:
        with open(_incremental_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        data = dict(_experiment_metadata)

    data["runs"].append(asdict(result))
    data["completed_tasks"] = len(data["runs"])
    data["last_updated"] = datetime.now().isoformat()

    tmp_path = _incremental_filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp_path, _incremental_filepath)
    except Exception:
        try:
            with open(_incremental_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass


def _finalize_incremental_save(comparison_summary: dict = None):
    """Incremental dosyayı finalize et: status=completed."""
    global _incremental_filepath

    if not _incremental_filepath or not os.path.exists(_incremental_filepath):
        return

    try:
        with open(_incremental_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["status"] = "completed"
        data["finished_at"] = datetime.now().isoformat()
        if comparison_summary:
            data["comparison_summary"] = comparison_summary
        with open(_incremental_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass

    _incremental_filepath = None


def signal_handler(signum, frame):
    global _shutdown
    _shutdown = True
    print("\n\n  [!] Ctrl+C algilandi — calisma durduruluyor...")
    print(f"  [*] {len(_pending_results)} kaydedilmis sonuc var")

    if _incremental_filepath and os.path.exists(_incremental_filepath):
        print(f"  [OK] Tum sonuclar kaydedildi: {_incremental_filepath}")
        try:
            with open(_incremental_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["status"] = "interrupted"
            data["interrupted_at"] = datetime.now().isoformat()
            with open(_incremental_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass
    elif _pending_results:
        save_results(_pending_results, "ctrlc_interrupt.json")

    print("  [*] Tekrar calistirmak icin kaydedilen sonuclari yukleyebilirsiniz")
    print("  Guvenli cikis yapildi.\n")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)




# ═══════════════════════════════════════════════════════════════════
# Batch Mode
# ═══════════════════════════════════════════════════════════════════

def run_batch(category: str, config: RunConfig, n_runs: int):
    """Run all problems in a category."""
    problems = get_available_problems()
    if category == "small":
        target = [p for p in problems if p.category == "small"]
    elif category == "medium":
        target = [p for p in problems if p.category == "medium"]
    elif category == "large":
        target = [p for p in problems if p.category == "large"]
    else:
        target = problems

    target.sort(key=lambda x: x.dimension)
    if not target:
        print("  [!] Bu kategoride problem bulunamadi.")
        return

    print(f"\n  {len(target)} problem calistirilacak ({n_runs}'er kez)...")
    print(f"  Tahmini sure: ~{format_time(len(target) * n_runs * 2)}")

    confirm = input("\n  Devam? [E/H]: ").strip().upper()
    if confirm != "E":
        return

    all_results: List[RunResult] = []
    for i, pinfo in enumerate(target):
        if _shutdown:
            break

        prob = load_problem(pinfo.name)
        if not prob:
            print(f"  [SKIP] {pinfo.name} — koordinatlar yüklenemedi")
            continue

        print(f"\n  [{i + 1}/{len(target)}] {pinfo.name} (n={pinfo.dimension})...")
        results = solve_multi_run(prob, config, n_runs)
        all_results.extend(results)

        # Show best
        best = min(results, key=lambda x: x.cost)
        g = f"{best.gap:.2f}%" if not math.isnan(best.gap) else "N/A"
        print(f"    → best={best.cost}, gap={g}, time={best.time_ms:.0f}ms")

    if all_results:
        save_results(all_results, f"batch_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        # Print summary table
        print_summary_table(all_results)


def print_summary_table(all_results: List[RunResult]):
    """Print cross-problem summary table."""
    # Group by problem
    by_problem: Dict[str, List[RunResult]] = {}
    for r in all_results:
        by_problem.setdefault(r.problem_name, []).append(r)

    print(f"\n  {'═' * 72}")
    print(f"  KARSILASTIRMALI OZET TABLO")
    print(f"  {'═' * 72}")
    print(f"  {'Problem':<14} {'Dim':>5} {'Optimal':>8} {'Best':>8} {'Avg':>8} {'BestGap':>8} {'AvgGap':>8} {'Time':>7}")
    print(f"  {'─' * 14} {'─' * 5} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 7}")

    for pname in sorted(by_problem.keys()):
        runs = by_problem[pname]
        costs = [r.cost for r in runs]
        gaps = [r.gap for r in runs if not math.isnan(r.gap)]
        times = [r.time_ms for r in runs]
        r0 = runs[0]
        opt_str = str(r0.optimal) if r0.optimal else "?"
        best_gap = f"{min(gaps):.2f}%" if gaps else "N/A"
        avg_gap = f"{sum(gaps)/len(gaps):.2f}%" if gaps else "N/A"
        sym = gap_symbol(min(gaps)) if gaps else "?"
        print(f"  {pname:<14} {r0.dimension:>5} {opt_str:>8} {min(costs):>8} "
              f"{sum(costs)/len(costs):>8.1f} {best_gap:>7} {avg_gap:>7} "
              f"{sum(times)/len(times):>6.0f}ms {sym}")

    print(f"  {'═' * 72}")


# ═══════════════════════════════════════════════════════════════════
# Show Saved Results
# ═══════════════════════════════════════════════════════════════════

def show_saved_results():
    """Display previously saved results."""
    saved = load_saved_results()
    if not saved:
        print("\n  [!] Kayitli sonuc bulunamadi.")
        print(f"  Sonuçlar: {RESULTS_DIR}/")
        return

    print(f"\n  {'═' * 70}")
    print(f"  KAYITLI SONUCLAR")
    print(f"  {'═' * 70}")

    for pname in sorted(saved.keys()):
        runs = saved[pname]
        costs = [r["cost"] for r in runs]
        gaps = [r.get("gap", float("nan")) for r in runs]
        valid_gaps = [g for g in gaps if g is not None and not math.isnan(g)]
        r0 = runs[0]
        opt = r0.get("optimal")
        opt_str = str(opt) if opt else "?"
        best_g = f"{min(valid_gaps):.2f}%" if valid_gaps else "N/A"
        avg_g = f"{sum(valid_gaps)/len(valid_gaps):.2f}%" if valid_gaps else "N/A"
        times = [r.get("time_ms", 0) for r in runs]
        print(f"    {pname:<14} n={r0.get('dimension', '?'):>4} opt={opt_str:>7} "
              f"best={min(costs):>7} avg_gap={avg_g:>7} best_gap={best_g:>7} "
              f"({len(runs)} runs)")

    print(f"  {'═' * 70}")
    print(f"  Toplam: {len(saved)} problem, {sum(len(v) for v in saved.values())} calisma")


# ═══════════════════════════════════════════════════════════════════
# Algorithm Info
# ═══════════════════════════════════════════════════════════════════

def show_algorithm_info():
    """Display algorithm catalog."""
    clear_screen()
    print(f"\n  {'═' * 70}")
    print(f"  ALGORITMA KATALOGU (FAZ 0 — v{SOTA_INFRA_VERSION})")
    print(f"  {'═' * 70}")

    sections = {
        "BASLANGIC HEURISTIKLERI": [
            "Multi-Start NN", "Multi-Start CW", "Multi-Start Regret", "Multi-Start Random",
        ],
        "YEREL ARAMA (LS)": ["2-opt", "Or-opt", "3-opt", "Swap"],
        "ALNS OPERATORLERI": [
            "ALNS (Random+Greedy)", "ALNS (Worst+Regret-2)", "ALNS (Shaw+Regret-3)",
        ],
        "KABUL KRITERLERI": ["SimulatedAnnealing", "LAHC", "RTR"],
    }

    for section, keys in sections.items():
        print(f"\n  [{section}]")
        print(f"  {'─' * 66}")
        for key in keys:
            info = ALGO_CATALOG.get(key, {})
            print(f"    {key:<24} [{info.get('complexity', '?')}]")
            print(f"      {info.get('desc', '')}")
            print(f"      En iyi: {info.get('best_for', '')}")
            print()

    print(f"  {'─' * 66}")
    print(f"  PIPELINE PRESETS:")
    for key, preset in PIPELINE_PRESETS.items():
        print(f"    [{key[0].upper()}] {preset['label']:<20} {preset['desc']}")

    print(f"\n  {'─' * 66}")
    print(f"  PARAMETER OPTIONS:")
    for param_name, options in PARAMETER_OPTIONS.items():
        print(f"    {param_name:<20} → {', '.join(options)}")

    input("\n  Devam icin Enter...")


# ═══════════════════════════════════════════════════════════════════
# Multiprocessing Worker (top-level, picklable)
# ═══════════════════════════════════════════════════════════════════

def _mp_solve_worker(args: tuple) -> dict:
    """Worker function for multiprocessing.Pool.

    Her alt süreçte bağımsız çalışır. Sadece ilkel tip (dict, tuple)
    argümanlar alır — kompleks nesne pickle sorunu olmaz.

    Args: (problem_name, config_dict, pipeline_label, run_index, script_dir)
    Returns: dict with all result fields
    """
    problem_name, config_dict, pipeline_label, run_index, script_dir = args

    # Alt süreç sys.path'i yeniden ayarla
    import sys as _sys
    if script_dir not in _sys.path:
        _sys.path.insert(0, script_dir)

    from utils.tsplib_parser import (
        load_problem_coordinates, TSPLIB_OPTIMALS, tsplib_euc_2d_distance,
    )
    from strategies.sota_common import (
        MultiStartInitializer, MultiLayerLS,
        SimulatedAnnealing, LateAcceptanceHC, RecordToRecordTravel,
        RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval,
        GreedyInsertion, Regret2Insertion, Regret3Insertion,
    )

    # ── Problem yükle ──
    coords = load_problem_coordinates(problem_name)
    if not coords:
        return {"error": f"Cannot load {problem_name}", "problem_name": problem_name}

    dimension = len(coords)
    node_names = [str(i) for i in range(dimension)]

    # Optimal lookup
    optimal = None
    for k, v in TSPLIB_OPTIMALS.items():
        if k.lower() == problem_name.lower():
            optimal = v
            break

    # Distance matrix (int)
    dist_matrix = {}
    for i in range(dimension):
        dist_matrix[i] = {}
        for j in range(dimension):
            dist_matrix[i][j] = tsplib_euc_2d_distance(coords[i], coords[j]) if i != j else 0

    # Distance map (string keys, float values)
    dm_str = {}
    for i in range(dimension):
        dm_str[node_names[i]] = {}
        for j in range(dimension):
            dm_str[node_names[i]][node_names[j]] = float(dist_matrix[i][j])

    def tour_cost(tour):
        if not tour or len(tour) < 2:
            return 0
        return sum(dist_matrix[tour[i]][tour[(i + 1) % len(tour)]] for i in range(len(tour)))

    def cost_fn(tour):
        return float(tour_cost([int(n) for n in tour]))

    gap_pct = (lambda c: (c - optimal) / optimal * 100) if optimal else (lambda c: float("nan"))

    # ── Config al ──
    cfg = RunConfig(**config_dict)
    rng = __import__("random").Random(cfg.seed)

    t_start = __import__("time").perf_counter()

    # Phase 1: Initialization
    init_cost = 0
    best_tour = list(range(dimension))

    if cfg.init_method == "multi":
        pop = MultiStartInitializer.generate_population(
            node_names, dm_str, pop_size=max(4, min(8, dimension // 5)),
            rng=rng, depot=node_names[0],
        )
        int_pop = [[int(n) for n in sol] for sol in pop]
        costs = [tour_cost(t) for t in int_pop]
        best_idx = costs.index(min(costs))
        best_tour = int_pop[best_idx]
        init_cost = costs[best_idx]
    elif cfg.init_method == "nn":
        tour = MultiStartInitializer.generate_population(
            node_names, dm_str, pop_size=1, rng=rng, depot=node_names[0],
        )
        best_tour = [int(n) for n in tour[0]]
        init_cost = tour_cost(best_tour)
    elif cfg.init_method == "cw":
        tour = MultiStartInitializer.generate_population(
            node_names, dm_str, pop_size=4, rng=rng, depot=node_names[0],
        )
        cw_cands = [[int(n) for n in t] for t in tour[1:3]] if len(tour) > 1 else [[int(n) for n in tour[0]]]
        cw_costs = [tour_cost(t) for t in cw_cands]
        best_tour = cw_cands[cw_costs.index(min(cw_costs))]
        init_cost = min(cw_costs)
    elif cfg.init_method == "regret":
        tour = MultiStartInitializer.generate_population(
            node_names, dm_str, pop_size=4, rng=rng, depot=node_names[0],
        )
        reg_cands = [[int(n) for n in t] for t in tour[2:4]] if len(tour) > 2 else [[int(n) for n in tour[0]]]
        reg_costs = [tour_cost(t) for t in reg_cands]
        best_tour = reg_cands[reg_costs.index(min(reg_costs))]
        init_cost = min(reg_costs)
    else:
        rng.shuffle(best_tour)
        init_cost = tour_cost(best_tour)

    # Phase 2: Local Search
    ls_cost = init_cost
    ls_improvements = 0
    if cfg.ls_intensity != "none":
        improved, ls_float, stats = MultiLayerLS.improve(best_tour, cost_fn, rng, intensity=cfg.ls_intensity)
        ls_cost = int(ls_float)
        ls_improvements = sum(stats.get("improves_per_layer", {}).values())
        if ls_cost < tour_cost(best_tour):
            best_tour = improved

    # Phase 3: ALNS
    alns_cost = ls_cost
    alns_accepted = 0
    alns_total = cfg.alns_iterations

    if alns_total > 0:
        if cfg.acceptance == "sa":
            acc = SimulatedAnnealing(start_temp=cfg.sa_temp, end_temp=0.1, cooling_rate=0.99)
        elif cfg.acceptance == "lahc":
            acc = LateAcceptanceHC(history_length=cfg.lahc_history, warmup=max(10, alns_total // 50))
        elif cfg.acceptance == "rtr":
            acc = RecordToRecordTravel(initial_deviation=100.0, min_deviation=0.0, decay_rate=0.997)
        else:
            acc = SimulatedAnnealing()

        destroy_ops = {"random": RandomRemoval(), "worst": WorstRemoval(), "shaw": ShawRemoval(), "related": RelatedRemoval()}
        repair_ops = {"greedy": GreedyInsertion(), "regret2": Regret2Insertion(), "regret3": Regret3Insertion()}
        d_names = list(destroy_ops.keys())
        r_names = list(repair_ops.keys())

        str_tour = [str(n) for n in best_tour]
        best_cost_f = float(tour_cost(best_tour))
        q = max(3, int(dimension * cfg.alns_remove_pct))

        for i in range(alns_total):
            elapsed_ms = (__import__("time").perf_counter() - t_start) * 1000
            if cfg.time_limit_ms > 0 and elapsed_ms >= cfg.time_limit_ms:
                alns_total = i
                break

            d_op = destroy_ops[d_names[i % len(d_names)]] if cfg.destroy_operator == "adaptive" else destroy_ops.get(cfg.destroy_operator, destroy_ops["random"])
            r_op = repair_ops[r_names[i % len(r_names)]] if cfg.repair_operator == "adaptive" else repair_ops.get(cfg.repair_operator, repair_ops["regret2"])

            removed, remaining = d_op.destroy(str_tour, q, rng, distance_matrix=dm_str)
            new_tour_str = r_op.repair(remaining, removed, distance_matrix=dm_str)
            new_tour_int = [int(n) for n in new_tour_str]
            new_cost_f = float(tour_cost(new_tour_int))

            result_acc = acc.decide(best_cost_f, new_cost_f, best_cost_f, i, rng)
            if result_acc.accepted and new_cost_f < best_cost_f:
                best_tour = new_tour_int
                best_cost_f = new_cost_f
                str_tour = new_tour_str
                alns_accepted += 1

        alns_cost = int(best_cost_f)

    # Phase 4: Final LS Polish
    final_ls_cost = alns_cost
    if cfg.ls_intensity in ("medium", "heavy") and alns_total > 0:
        rng2 = __import__("random").Random(cfg.seed + 999)
        polished, pl_cost, _ = MultiLayerLS.improve(best_tour, cost_fn, rng2, intensity="light")
        pc = int(pl_cost)
        if pc < alns_cost:
            best_tour = polished
            final_ls_cost = pc

    t_end = __import__("time").perf_counter()
    final_cost = tour_cost(best_tour)

    return {
        "result_id": f"{problem_name}_{pipeline_label}_run{run_index}",
        "problem_name": problem_name,
        "dimension": dimension,
        "optimal": optimal,
        "config": config_dict,
        "tour": best_tour,
        "cost": final_cost,
        "gap": gap_pct(final_cost),
        "time_ms": (t_end - t_start) * 1000,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "init_cost": init_cost,
        "ls_cost": ls_cost,
        "alns_cost": alns_cost,
        "final_ls_cost": final_ls_cost,
        "ls_improvements": ls_improvements,
        "alns_accepted": alns_accepted,
        "alns_total": alns_total,
        "pipeline_label": pipeline_label,
        "all_parameters": {
            "selected_parameters": {
                "init_method": cfg.init_method,
                "ls_intensity": cfg.ls_intensity,
                "alns_iterations": cfg.alns_iterations,
                "destroy_operator": cfg.destroy_operator,
                "repair_operator": cfg.repair_operator,
                "acceptance": cfg.acceptance,
            },
            "available_options": dict(PARAMETER_OPTIONS),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Multi-Problem × Multi-Pipeline Experiment Runner
# ═══════════════════════════════════════════════════════════════════


def run_multi_problem_pipeline_experiment(
    problem_names: List[str],
    pipelines: List[Tuple[str, RunConfig]],
    n_runs: int = 1,
):
    """Run a multi-problem × multi-pipeline experiment with comparison output.

    Paralel veya seri modda çalışabilir. Paralel modda multiprocessing.Pool
    kullanarak tüm task'leri eşzamanlı çalıştırır.

    Incremental save: Her sonuç anında dosyaya yazılır. Ctrl+C'de kayıtlar korunur.
    """
    global _pending_results

    # ── Execution mode selection ──
    is_parallel = select_execution_mode()

    total_tasks = len(problem_names) * len(pipelines) * n_runs
    pipeline_labels = [label for label, _ in pipelines]

    # ── Estimate time ──
    if is_parallel and total_tasks > NUM_WORKERS:
        effective_parallel = min(total_tasks, NUM_WORKERS)
        speedup = effective_parallel
    else:
        speedup = 1

    sep = "─" * 60
    print(f"\n  {sep}")
    print("  DENey PLANI")
    print(f"  {sep}")
    print(f"  Mod:          {'Paralel (' + str(NUM_WORKERS) + ' worker)' if is_parallel else 'Seri'}")
    if is_parallel:
        print(f"  Hizlanma:     ~{speedup:.0f}x (tahmini)")
    print(f"  Problemler:   {len(problem_names)} adet")
    print(f"  Pipeline'ler: {len(pipelines)} adet ({', '.join(pipeline_labels)})")
    print(f"  Her birinin:  {n_runs} kez calistirilacak")
    print(f"  Toplam gorev: {total_tasks}")
    print(f"  {sep}")

    confirm = input("\n  Baslat? [E/H]: ").strip().upper()
    if confirm != "E":
        return

    _pending_results = []
    comparison_summary: Dict[str, dict] = {}

    # ── Incremental save ──
    inc_filepath = _init_incremental_save(problem_names, pipeline_labels, n_runs, total_tasks)
    print(f"  [*] Incremental kayit: {inc_filepath}")
    print(f"      (Ctrl+C'de bile sonuclar korunur)")

    all_results: List[RunResult] = []

    if is_parallel and total_tasks > 1:
        # ═════════════════════════
        # PARALLEL EXECUTION via multiprocessing.Pool
        # ═════════════════════════
        tasks = []
        for problem_name in problem_names:
            for pl_label, pl_config in pipelines:
                for run_i in range(n_runs):
                    run_cfg = RunConfig(
                        **{**asdict(pl_config), "seed": pl_config.seed + run_i * 13}
                    )
                    tasks.append((
                        problem_name,
                        asdict(run_cfg),
                        pl_label,
                        run_i + 1,
                        SCRIPT_DIR,
                    ))

        completed = 0
        t_all_start = time.perf_counter()

        print(f"\n  ⚡ Paralel calisma basladi ({NUM_WORKERS} worker)...")
        sep2 = "─" * 70
        print(f"  {sep2}")
        print(f"  {'#':<4} {'Problem':<14} {'Pipeline':<14} {'Cost':>7} {'Gap':>8} {'Time':>8} {'ETA':>8}  Progress")
        print(f"  {sep2}")

        try:
            with Pool(processes=NUM_WORKERS) as pool:
                for result_dict in pool.imap_unordered(_mp_solve_worker, tasks):
                    if _shutdown:
                        break

                    completed += 1

                    if "error" in result_dict:
                        print(f"  {completed:>3}. [HATA] {result_dict.get('problem_name', '?')}: {result_dict['error']}")
                        continue

                    rr = RunResult(**{k: v for k, v in result_dict.items() if k != "pipeline_label"})
                    _pending_results.append(rr)
                    all_results.append(rr)

                    # ── Incremental save (anında) ──
                    _append_incremental_result(rr)

                    g = f"{rr.gap:.2f}%" if not math.isnan(rr.gap) else "N/A"
                    sym = gap_symbol(rr.gap) if not math.isnan(rr.gap) else "?"
                    pl = result_dict.get("pipeline_label", "?")

                    elapsed = time.perf_counter() - t_all_start
                    avg_time = elapsed / completed
                    remaining = (total_tasks - completed) * avg_time
                    eta_str = format_time(remaining) if completed < total_tasks else "bitti"

                    print(f"  {completed:>3}. {rr.problem_name:<14} {pl:<14} "
                          f"{rr.cost:>7} {g:>8} {rr.time_ms:>6.0f}ms {eta_str:>8}  "
                          f"[{progress_bar(completed, total_tasks)}]")

        except KeyboardInterrupt:
            print("\n  [!] Paralel calisma kullanici tarafindan durduruldu.")

        elapsed_total = (time.perf_counter() - t_all_start) * 1000
        print(f"\n  {sep2}")
        print(f"  Paralel calisma tamamlandi ({completed}/{total_tasks} gorev)")
        print(f"  Toplam sure: {format_time(elapsed_total / 1000)}")
        if is_parallel and completed > 0:
            print(f"  Ortalama gorev suresi: {elapsed_total / completed:.0f}ms")

        # ── Sonuçları organize et ──
        problem_info = {}
        for pname in problem_names:
            prob = load_problem(pname)
            if prob:
                problem_info[pname] = prob

        for pname in problem_names:
            prob = problem_info.get(pname)
            if not prob:
                continue

            pipeline_results = []
            for pl_label, _ in pipelines:
                matching = [r for r in all_results
                           if r.problem_name == pname
                           and r.result_id.startswith(f"{pname}_{pl_label}_run")]
                if matching:
                    best_for_pl = min(matching, key=lambda x: x.cost)
                    pipeline_results.append((pl_label, best_for_pl))

            if not pipeline_results:
                continue

            print_pipeline_comparison(pname, prob.dimension, prob.optimal, pipeline_results)

            prob_summary = {}
            best_cost = float("inf")
            best_label = None
            best_gap = float("inf")

            for pl_label, pl_result in pipeline_results:
                prob_summary[pl_label] = {
                    "cost": pl_result.cost,
                    "gap": round(pl_result.gap, 4) if not math.isnan(pl_result.gap) else None,
                    "time_ms": round(pl_result.time_ms, 1),
                }
                if pl_result.cost < best_cost:
                    best_cost = pl_result.cost
                    best_label = pl_label
                    best_gap = pl_result.gap

            comparison_summary[pname] = {
                "best_pipeline": best_label,
                "best_cost": best_cost,
                "best_gap": round(best_gap, 4) if not math.isnan(best_gap) else None,
                "pipeline_results": prob_summary,
            }

    else:
        # ═════════════════════════
        # SEQUENTIAL EXECUTION
        # ═════════════════════════
        completed = 0
        t_all_start = time.perf_counter()

        for pi_idx, problem_name in enumerate(problem_names):
            if _shutdown:
                break

            prob = load_problem(problem_name)
            if not prob:
                print(f"\n  [SKIP] {problem_name} — koordinatlar yüklenemedi")
                continue

            print(f"\n  ╔{'═' * 66}╗")
            print(f"  ║  PROBLEM [{pi_idx + 1}/{len(problem_names)}]: {problem_name}"
                  f" (n={prob.dimension}, opt={prob.optimal or '?'})"
                  f"{' ' * max(0, 66 - 22 - len(problem_name) - len(str(prob.dimension)) - len(str(prob.optimal or '?')))}║")
            print(f"  ╚{'═' * 66}╝")

            pipeline_results: List[Tuple[str, RunResult]] = []

            for pl_idx, (pl_label, pl_config) in enumerate(pipelines):
                if _shutdown:
                    break

                print(f"\n  Pipeline [{pl_idx + 1}/{len(pipelines)}]: {pl_label}")

                for run_i in range(n_runs):
                    if _shutdown:
                        break

                    run_cfg = RunConfig(
                        **{**asdict(pl_config), "seed": pl_config.seed + run_i * 13}
                    )
                    result = solve_single(prob, run_cfg)
                    result.result_id = f"{problem_name}_{pl_label}_run{run_i + 1}"

                    _pending_results.append(result)
                    all_results.append(result)
                    completed += 1

                    # ── Incremental save (anında) ──
                    _append_incremental_result(result)

                    g = f"{result.gap:.2f}%" if not math.isnan(result.gap) else "N/A"
                    sym = gap_symbol(result.gap) if not math.isnan(result.gap) else "?"
                    print(f"    Run {run_i + 1}/{n_runs}: cost={result.cost:>7}  gap={g:>7} {sym}  "
                          f"{result.time_ms:.0f}ms  [{progress_bar(completed, total_tasks)}]")

                if n_runs > 1:
                    run_results = [r for r in all_results
                                   if r.problem_name == problem_name
                                   and r.result_id.startswith(f"{problem_name}_{pl_label}_run")]
                    best_for_pipeline = min(run_results, key=lambda x: x.cost) if run_results else result
                else:
                    best_for_pipeline = result
                pipeline_results.append((pl_label, best_for_pipeline))

            print_pipeline_comparison(
                problem_name=problem_name,
                dimension=prob.dimension,
                optimal=prob.optimal,
                pipeline_results=pipeline_results,
            )

            prob_summary: Dict[str, dict] = {}
            best_overall_label = None
            best_overall_cost = float("inf")
            best_overall_gap = float("inf")

            for pl_label, pl_result in pipeline_results:
                prob_summary[pl_label] = {
                    "cost": pl_result.cost,
                    "gap": round(pl_result.gap, 4) if not math.isnan(pl_result.gap) else None,
                    "time_ms": round(pl_result.time_ms, 1),
                }
                if pl_result.cost < best_overall_cost:
                    best_overall_cost = pl_result.cost
                    best_overall_label = pl_label
                    best_overall_gap = pl_result.gap

            comparison_summary[problem_name] = {
                "best_pipeline": best_overall_label,
                "best_cost": best_overall_cost,
                "best_gap": round(best_overall_gap, 4) if not math.isnan(best_overall_gap) else None,
                "pipeline_results": prob_summary,
            }

    # ── Final report & save ──
    if all_results:
        sep3 = "═" * 60
        print(f"\n  {sep3}")
        print("  DENEY SONUC RAPORU")
        print(f"  {sep3}")
        print(f"  Mod:          {'Paralel (' + str(NUM_WORKERS) + ' worker)' if is_parallel else 'Seri'}")
        print(f"  Toplam calisma: {len(all_results)}")

        if comparison_summary:
            print(f"\n  GENEL KARSILASTIRMA:")
            sep4 = "─" * 66
            print(f"  {sep4}")
            print(f"  {'Problem':<14} {'En İyi Pipeline':<18} {'Cost':>8} {'Gap':>8}")
            print(f"  {sep4}")
            for pname, summary in comparison_summary.items():
                bp = summary.get("best_pipeline", "?")
                bc = summary.get("best_cost", "?")
                bg = summary.get("best_gap")
                bg_str = f"{bg:.2f}%" if bg is not None else "N/A"
                print(f"  {pname:<14} {bp:<18} {bc:>8} {bg_str:>8}")
            print(f"  {sep4}")

        save_comparison_results(
            all_results=all_results,
            problem_names=problem_names,
            pipeline_labels=pipeline_labels,
            comparison_summary=comparison_summary,
        )

        _finalize_incremental_save(comparison_summary)
        print(f"  [OK] Incremental kayit finalize edildi: {inc_filepath}")

        _pending_results = []
    else:
        _finalize_incremental_save()


# Main Menu
# ═══════════════════════════════════════════════════════════════════

def main():
    global _pending_results

    print(BANNER)
    cpu = get_cpu_info()
    print(f"  Dizin: {RESULTS_DIR}/")
    print(f"  TSPLIB: {len(get_available_problems())} problem mevcut")
    print(f"  CPU: {cpu['physical_cores']}C/{cpu['logical_cores']}T"
          f"{' (SMT)' if cpu['has_smt'] else ''} — onerilen: {cpu['recommended_workers']} worker")

    while True:
        print(f"\n{'═' * 70}")
        print(f"  ANA MENU")
        print(f"{'═' * 70}")
        print(f"  [1] Problem Coz              — Problem(ler) + Pipeline(lar) sec + karsilastir (paralel)")
        print(f"  [2] Toplu Coz (Kucuk)       — Tum kucuk problemler (n≤100)")
        print(f"  [3] Toplu Coz (Orta)        — Tum orta problemler (101-500)")
        print(f"  [4] Toplu Coz (Buyuk)       — Tum buyuk problemler (n>500)")
        print(f"  [5] Kayitli Sonuclari Gor   — Onceki calismalar")
        print(f"  [6] Algoritma Bilgileri     — Tum operatorler ve presetler")
        print(f"  [7] Hizli Demo              — eil51 ile hizli pipeline demo")
        print(f"  [8] ★ E2BSO Coz (FAZ 1)   — Entropy-Balanced Swarm Optimizasyon")
        print(f"  [9] ★ R2DMA Coz (FAZ 2)   — Resonance-Reinforced Destroy & Merge")
        print(f"  [10] ★ PAOEA Coz (FAZ 3)  — Adaptive Operator Evolution")
        print(f"  [Q] Cikis")
        print()

        choice = input("  Seciminiz: ").strip().upper()

        if choice == "Q":
            print("\n  Gorusuruz!")
            break

        elif choice == "1":
            # ── Multi-Problem × Multi-Pipeline Mode ──
            problem_names = list_and_select_problems()
            if not problem_names:
                continue

            pipelines = select_pipelines()
            if not pipelines:
                continue

            n_runs = select_n_runs()

            run_multi_problem_pipeline_experiment(
                problem_names=problem_names,
                pipelines=pipelines,
                n_runs=n_runs,
            )

        elif choice in ("2", "3", "4"):
            cat_map = {"2": "small", "3": "medium", "4": "large"}
            cat_name = cat_map[choice]
            _, config = select_pipeline()
            n_runs = select_n_runs()
            run_batch(cat_name, config, n_runs)

        elif choice == "5":
            show_saved_results()

        elif choice == "6":
            show_algorithm_info()

        elif choice == "7":
            # Quick demo
            pname = "eil51"
            prob = load_problem(pname)
            if not prob:
                print(f"  [!] {pname} bulunamadi, indiriliyor...")
                download_tsplib_problem(pname)
                prob = load_problem(pname)
            if not prob:
                print(f"  [HATA] {pname} yüklenemedi.")
                continue

            config = RunConfig(
                init_method="multi", ls_intensity="medium",
                alns_iterations=200, acceptance="sa",
            )
            print(f"\n  Hizli Demo: {pname} (n={prob.dimension}, optimal={prob.optimal})")
            print(f"  Pipeline: Multi-Start → Medium LS → 200 ALNS (SA)")
            print(f"  {'─' * 50}")

            _pending_results = []
            for i in range(3):
                run_cfg = RunConfig(**{**asdict(config), "seed": 42 + i * 13})
                result = solve_single(prob, run_cfg)
                result.result_id = f"{pname}_demo_run{i + 1}"
                _pending_results.append(result)

            print_multi_summary(_pending_results)
            save_results(_pending_results)
            _pending_results = []

        elif choice == "8":
            # ── FAZ 1: E²BSO ──
            print(f"\n{'═' * 70}")
            print(f"  FAZ 1: E2BSO — Enhanced Entropy-Balanced Swarm Optimization")
            print(f"{'═' * 70}")
            print(f"  Kenar entropisi ile adaptif keşif/sömürü dengesi")
            print(f"  7 DNA faktoru entegre: MultiStart + LS + ALNS + LAHC + Penalty + Diversity")
            print()

            problem_names = list_and_select_problems()
            if not problem_names:
                continue

            e2cfg = configure_e2bso()
            n_runs = select_n_runs()

            print(f"\n  {'═' * 70}")
            print(f"  E2BSO Calistirmasi Basliyor...")
            print(f"  {'═' * 70}")
            print(f"  Problem(ler): {', '.join(problem_names)}")
            print(f"  Populasyon: {e2cfg.population_size}, Iterasyon: {e2cfg.max_iterations}")
            print(f"  Entropy: {e2cfg.h_start} → {e2cfg.h_end}, Runs: {n_runs}")
            print()

            _pending_results = []
            total_tasks = len(problem_names) * n_runs
            completed = 0

            for pname in problem_names:
                prob = load_problem(pname)
                if not prob:
                    print(f"  [!] {pname} bulunamadi, indiriliyor...")
                    download_tsplib_problem(pname)
                    prob = load_problem(pname)
                if not prob:
                    print(f"  [HATA] {pname} yüklenemedi, atlanıyor.")
                    continue

                for r in range(n_runs):
                    run_cfg = E2BSORunConfig(
                        **{**asdict(e2cfg), "seed": e2cfg.seed + r * 13}
                    )
                    print(f"\n  [{completed + 1}/{total_tasks}] {pname} run {r + 1}/{n_runs}...", end="", flush=True)
                    result = solve_e2bso(prob, run_cfg)
                    print(f" cost={result.cost} gap={result.gap:.2f}% ({result.time_ms:.0f}ms)")
                    _pending_results.append(result)
                    completed += 1

            # Save results
            if _pending_results:
                print(f"\n  {'═' * 70}")
                print(f"  E2BSO SONUCLARI OZETI")
                print(f"  {'═' * 70}")

                for r in _pending_results:
                    print_e2bso_result(r)

                # Multi-run summary if multiple runs
                per_problem: Dict[str, List[RunResult]] = {}
                for r in _pending_results:
                    per_problem.setdefault(r.problem_name, []).append(r)

                for pname, results in per_problem.items():
                    if len(results) > 1:
                        print_multi_summary(results)

                save_results(_pending_results, f"faz1_e2bso_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                _pending_results = []

        elif choice == "9":
            # ── FAZ 2: R²DMA ──
            print(f"\n{'═' * 70}")
            print(f"  FAZ 2: R2DMA — Resonance-Reinforced Destroy and Merge Algorithm")
            print(f"{'═' * 70}")
            print(f"  6-boyutlu rezonans metriği ile yapıya göre crossover seçimi")
            print(f"  Constructive (R≥0.7) / Moderate (0.3≤R<0.7) / Destructive (R<0.3)")
            print(f"  DNA: D1✅ D2✅ D3✅ D4✅ D6✅ D7✅ D8✅ D9✅")
            print()

            problem_names = list_and_select_problems()
            if not problem_names:
                continue

            r2cfg = configure_r2dma()
            n_runs = select_n_runs()

            print(f"\n  {'═' * 70}")
            print(f"  R2DMA Calistirmasi Basliyor...")
            print(f"  {'═' * 70}")
            print(f"  Problem(ler): {', '.join(problem_names)}")
            print(f"  Populasyon: {r2cfg.population_size}, Iterasyon: {r2cfg.max_iterations}")
            print(f"  theta_base: {r2cfg.theta_base}, Runs: {n_runs}")
            print()

            _pending_results = []
            total_tasks = len(problem_names) * n_runs
            completed = 0

            for pname in problem_names:
                prob = load_problem(pname)
                if not prob:
                    print(f"  [!] {pname} bulunamadi, indiriliyor...")
                    download_tsplib_problem(pname)
                    prob = load_problem(pname)
                if not prob:
                    print(f"  [HATA] {pname} yüklenemedi, atlanıyor.")
                    continue

                for r in range(n_runs):
                    run_cfg = R2DMARunConfig(
                        **{**asdict(r2cfg), "seed": r2cfg.seed + r * 13}
                    )
                    print(f"\n  [{completed + 1}/{total_tasks}] {pname} run {r + 1}/{n_runs}...", end="", flush=True)
                    result = solve_r2dma(prob, run_cfg)
                    print(f" cost={result.cost} gap={result.gap:.2f}% ({result.time_ms:.0f}ms)")
                    _pending_results.append(result)
                    completed += 1

            # Save results
            if _pending_results:
                print(f"\n  {'═' * 70}")
                print(f"  R2DMA SONUCLARI OZETI")
                print(f"  {'═' * 70}")

                for r in _pending_results:
                    print_r2dma_result(r)

                # Multi-run summary if multiple runs
                per_problem: Dict[str, List[RunResult]] = {}
                for r in _pending_results:
                    per_problem.setdefault(r.problem_name, []).append(r)

                for pname, results in per_problem.items():
                    if len(results) > 1:
                        print_multi_summary(results)

                save_results(_pending_results, f"faz2_r2dma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                _pending_results = []

        elif choice == "10":
            # ── FAZ 3: P-AOEA ──
            print(f"\n{'═' * 70}")
            print(f"  FAZ 3: PAOEA — Production Adaptive Operator Evolution Algorithm")
            print(f"{'═' * 70}")
            print(f"  Operator genomlari meta-evrimu ile adaptif strateji gelisimi")
            print(f"  20+ atomic operation, adaptif destroy intensity, structured injection")
            print(f"  DNA: D1✅ D2✅ D3✅ D4✅ D6✅ D7✅ D8✅ D9✅ D10✅")
            print()

            problem_names = list_and_select_problems()
            if not problem_names:
                continue

            pacfg = configure_paoea()
            n_runs = select_n_runs()

            print(f"\n  {'═' * 70}")
            print(f"  PAOEA Calistirmasi Basliyor...")
            print(f"  {'═' * 70}")
            print(f"  Problem(ler): {', '.join(problem_names)}")
            print(f"  Populasyon: {pacfg.population_size}, Iterasyon: {pacfg.max_iterations}")
            print(f"  Genomes: {pacfg.genome_population_size}, Meta-Evo: {pacfg.meta_evolution_interval}")
            print(f"  Runs: {n_runs}")
            print()

            _pending_results = []
            total_tasks = len(problem_names) * n_runs
            completed = 0

            for pname in problem_names:
                prob = load_problem(pname)
                if not prob:
                    print(f"  [!] {pname} bulunamadi, indiriliyor...")
                    download_tsplib_problem(pname)
                    prob = load_problem(pname)
                if not prob:
                    print(f"  [HATA] {pname} yüklenemedi, atlanıyor.")
                    continue

                for r in range(n_runs):
                    run_cfg = PAOEARunConfig(
                        **{**asdict(pacfg), "seed": pacfg.seed + r * 13}
                    )
                    print(f"\n  [{completed + 1}/{total_tasks}] {pname} run {r + 1}/{n_runs}...", end="", flush=True)
                    result = solve_paoea(prob, run_cfg)
                    print(f" cost={result.cost} gap={result.gap:.2f}% ({result.time_ms:.0f}ms)")
                    _pending_results.append(result)
                    completed += 1

            # Save results
            if _pending_results:
                print(f"\n  {'═' * 70}")
                print(f"  PAOEA SONUCLARI OZETI")
                print(f"  {'═' * 70}")

                for r in _pending_results:
                    print_paoea_result(r)

                # Multi-run summary if multiple runs
                per_problem: Dict[str, List[RunResult]] = {}
                for r in _pending_results:
                    per_problem.setdefault(r.problem_name, []).append(r)

                for pname, results in per_problem.items():
                    if len(results) > 1:
                        print_multi_summary(results)

                save_results(_pending_results, f"faz3_paoea_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                _pending_results = []

        input("\n  Devam etmek icin Enter'a basin...")


if __name__ == "__main__":
    main()
