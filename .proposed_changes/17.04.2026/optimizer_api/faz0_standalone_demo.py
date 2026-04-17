#!/usr/bin/env python3
"""
FAZ 0 — Standalone Demo Script
===============================

Web arayüzü (Next.js) OLMAZDAN doğrudan terminalde çalıştırılabilir.

Kullanım:
    cd optimizer_api
    python faz0_standalone_demo.py              # eil51 ile demo
    python faz0_standalone_demo.py berlin52      # farklı problem
    python faz0_standalone_demo.py --list        # mevcut problemleri listele

Hiçbir dış bağımlılık yoktur — sadece Python stdlib + mevcut sota_common modülleri.
FastAPI, Next.js, Supabase, veritabanı gerektirmez.
"""

import sys
import os
import math
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Path setup: optimizer_api/ dizininden çalıştırıldığını varsayar ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.tsplib_parser import (
    parse_tsplib_file,
    tsplib_euc_2d_distance,
    tsplib_tour_distance,
    get_available_problems,
    load_problem_coordinates,
    TSPLIB_OPTIMALS,
    TSPLIB_DATA_DIR,
)

from strategies.sota_common import (
    SOTA_INFRA_VERSION,
    MultiStartInitializer,
    MultiLayerLS,
    PenaltyManager,
    PenaltyState,
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
    DiversityState,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Helper: Problem Data Wrapper
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ProblemInstance:
    """TSPLIB problem instance wrapper for FAZ 0 modules."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[int] = None

    # Pre-computed distance matrix (TSPLIB EUC_2D NINT rounded)
    dist_matrix: Dict[int, Dict[int, int]] = field(default_factory=dict, repr=False)
    node_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Pre-compute distance matrix and node names."""
        self.node_names = [str(i) for i in range(self.dimension)]
        # Build full distance matrix (including 0 for self-distance)
        self.dist_matrix = {}
        for i in range(self.dimension):
            self.dist_matrix[i] = {}
            for j in range(self.dimension):
                if i != j:
                    self.dist_matrix[i][j] = tsplib_euc_2d_distance(
                        self.coordinates[i], self.coordinates[j]
                    )
                else:
                    self.dist_matrix[i][j] = 0

    def tour_cost(self, tour: List[int]) -> int:
        """Calculate tour cost using pre-computed distance matrix."""
        if not tour or len(tour) < 2:
            return 0
        total = 0
        for i in range(len(tour)):
            total += self.dist_matrix[tour[i]][tour[(i + 1) % len(tour)]]
        return total

    def cost_fn(self, tour: List[int]) -> float:
        """Cost function compatible with MultiLayerLS interface."""
        return float(self.tour_cost(tour))

    def dist_fn(self, tour: List) -> float:
        """Distance matrix lookup for destroy/repair operators (string-based)."""
        # Convert string tour to int tour for distance lookup
        int_tour = [int(n) for n in tour]
        return float(self.tour_cost(int_tour))

    def gap_pct(self, tour: List[int]) -> float:
        """Calculate optimality gap percentage."""
        if not self.optimal:
            return float("nan")
        return (self.tour_cost(tour) - self.optimal) / self.optimal * 100


def load_problem(name: str) -> Optional[ProblemInstance]:
    """Load a TSPLIB problem and wrap it for FAZ 0 usage."""
    coords = load_problem_coordinates(name)
    if not coords:
        print(f"  HATA: '{name}' probleminin koordinatları bulunamadı.")
        print(f"  TSPLIB data dizini: {TSPLIB_DATA_DIR}")
        return None

    optimal = TSPLIB_OPTIMALS.get(name.lower())
    return ProblemInstance(
        name=name,
        dimension=len(coords),
        coordinates=coords,
        optimal=optimal,
    )


# ═══════════════════════════════════════════════════════════════════════
# 2. Demo: Nearest Neighbor Baseline
# ═══════════════════════════════════════════════════════════════════════

def nearest_neighbor_tour(prob: ProblemInstance, start: int = 0) -> Tuple[List[int], int]:
    """Build a simple nearest-neighbor tour as baseline."""
    n = prob.dimension
    visited = [False] * n
    tour = [start]
    visited[start] = True

    for _ in range(n - 1):
        current = tour[-1]
        best_next = -1
        best_dist = float("inf")
        for j in range(n):
            if not visited[j] and prob.dist_matrix[current][j] < best_dist:
                best_dist = prob.dist_matrix[current][j]
                best_next = j
        tour.append(best_next)
        visited[best_next] = True

    return tour, prob.tour_cost(tour)


# ═══════════════════════════════════════════════════════════════════════
# 3. Demo Functions
# ═══════════════════════════════════════════════════════════════════════

def demo_multi_start(prob: ProblemInstance):
    """Demo 1: Multi-Start Initializer — 4 farklı başlangıç heuristiği."""
    print("\n" + "=" * 65)
    print(" DEMO 1: MultiStartInitializer")
    print("=" * 65)

    rng = random.Random(42)
    nodes = prob.node_names
    # Build string-keyed distance matrix for MultiStartInitializer
    dm_str = {}
    for i in range(prob.dimension):
        dm_str[nodes[i]] = {}
        for j in range(prob.dimension):
            dm_str[nodes[i]][nodes[j]] = float(prob.dist_matrix[i][j])

    t0 = time.perf_counter()
    population = MultiStartInitializer.generate_population(
        waypoints=nodes,
        distance_matrix=dm_str,
        pop_size=8,
        rng=rng,
        depot=nodes[0],
    )
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"  Problem: {prob.name} (n={prob.dimension})")
    print(f"  Popülasyon: {len(population)} çözüm")
    print(f"  Heuristikler: NearestNeighbor, ClarkeWright, Regret2, RandomPerturbation")
    print(f"  Süre: {elapsed:.1f}ms")

    # Evaluate each solution
    costs = []
    for i, sol in enumerate(population):
        int_tour = [int(n) for n in sol]
        cost = prob.tour_cost(int_tour)
        costs.append(cost)
        gap = prob.gap_pct(int_tour)
        gap_str = f"{gap:.2f}%" if prob.optimal else "N/A"
        print(f"    Sol-{i}: cost={cost:8d}  gap={gap_str}  len={len(sol)}")

    best_cost = min(costs)
    best_int_tour = [int(n) for n in population[costs.index(best_cost)]]
    best_gap = prob.gap_pct(best_int_tour)
    gap_info = f", gap={best_gap:.2f}%" if prob.optimal else ""
    print(f"\n  En iyi: cost={best_cost}{gap_info}")
    # Return int tours for downstream demos
    int_pop = [[int(n) for n in sol] for sol in population]
    return int_pop, costs


def demo_multi_layer_ls(prob: ProblemInstance, tour: List[int]):
    """Demo 2: Multi-Layer Local Search — 2-opt → Or-opt → 3-opt → Swap."""
    print("\n" + "=" * 65)
    print(" DEMO 2: MultiLayerLS (Katmanlı Yerel Arama)")
    print("=" * 65)

    initial_cost = prob.tour_cost(tour)
    initial_gap = prob.gap_pct(tour)

    for intensity in ["light", "medium", "heavy"]:
        rng = random.Random(42)
        t0 = time.perf_counter()

        improved_tour, final_cost, stats = MultiLayerLS.improve(
            tour.copy(),
            prob.cost_fn,
            rng,
            intensity=intensity,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        final_int_cost = int(final_cost)
        final_gap = prob.gap_pct(improved_tour)
        improvement = initial_cost - final_int_cost

        print(f"\n  [{intensity.upper()}]")
        print(f"    Başlangıç:  cost={initial_cost:8d}  gap={initial_gap:.2f}%")
        print(f"    Sonuç:      cost={final_int_cost:8d}  gap={final_gap:.2f}%")
        print(f"    İyileştirme: {improvement:5d}  ({improvement/initial_cost*100:.2f}%)")
        print(f"    Katman detayları:")
        for layer, count in stats.get("improves_per_layer", {}).items():
            print(f"      {layer}: {count} iyileştirme")
        print(f"    Toplam iterasyon: {stats.get('iterations', 'N/A')}")
        print(f"    Süre: {elapsed:.1f}ms")


def demo_alns(prob: ProblemInstance, tour: List[int]):
    """Demo 3: ALNS Destroy + Repair operatörleri."""
    print("\n" + "=" * 65)
    print(" DEMO 3: ALNS Destroy + Repair Operatörleri")
    print("=" * 65)

    initial_cost = prob.tour_cost(tour)
    print(f"  Problem: {prob.name} (n={prob.dimension})")
    print(f"  Başlangıç turu: cost={initial_cost}, gap={prob.gap_pct(tour):.2f}%")

    # Build string-based tour and distance matrix
    str_tour = [str(n) for n in tour]
    dm_str = {}
    for i in range(prob.dimension):
        dm_str[str(i)] = {}
        for j in range(prob.dimension):
            dm_str[str(i)][str(j)] = float(prob.dist_matrix[i][j])

    # Destroy operators
    destroys = [
        ("RandomRemoval", RandomRemoval()),
        ("WorstRemoval", WorstRemoval()),
        ("ShawRemoval", ShawRemoval()),
        ("RelatedRemoval", RelatedRemoval()),
    ]

    # Repair operators
    repairs = [
        ("GreedyInsertion", GreedyInsertion()),
        ("Regret-2", Regret2Insertion()),
        ("Regret-3", Regret3Insertion()),
    ]

    rng = random.Random(123)
    q = max(3, prob.dimension // 10)  # Remove ~10% of nodes

    results = []
    for dname, dest_op in destroys:
        for rname, rep_op in repairs:
            t0 = time.perf_counter()
            removed, remaining = dest_op.destroy(str_tour, q, rng, distance_matrix=dm_str)
            repaired = rep_op.repair(remaining, removed, distance_matrix=dm_str)
            elapsed = (time.perf_counter() - t0) * 1000

            int_repaired = [int(n) for n in repaired]
            new_cost = prob.tour_cost(int_repaired)
            gap = prob.gap_pct(int_repaired)
            diff = new_cost - initial_cost

            results.append({
                "destroy": dname,
                "repair": rname,
                "cost": new_cost,
                "gap": gap,
                "diff": diff,
                "time": elapsed,
                "q": q,
            })

    # Print results table
    print(f"\n  q={q} node kaldırıldı ({q}/{prob.dimension} = {q/prob.dimension*100:.0f}%)")
    print(f"  {'Destroy':<18} {'Repair':<18} {'Cost':>8} {'Gap':>8} {'Δ':>8} {'ms':>6}")
    print(f"  {'-'*18} {'-'*18} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")

    for r in results:
        gap_str = f"{r['gap']:.2f}%" if prob.optimal else "N/A"
        diff_str = f"{r['diff']:+d}"
        print(f"  {r['destroy']:<18} {r['repair']:<18} {r['cost']:>8d} {gap_str:>8} {diff_str:>8} {r['time']:>5.0f}")

    best = min(results, key=lambda x: x["cost"])
    worst = max(results, key=lambda x: x["cost"])
    print(f"\n  En iyi:  {best['destroy']} + {best['repair']} → cost={best['cost']}")
    print(f"  En kötü: {worst['destroy']} + {worst['repair']} → cost={worst['cost']}")


def demo_acceptance(prob: ProblemInstance):
    """Demo 4: SA, LAHC, RTR kabul kriterleri."""
    print("\n" + "=" * 65)
    print(" DEMO 4: Acceptance Criteria (SA / LAHC / RTR)")
    print("=" * 65)

    current_cost = prob.optimal * 1.10 if prob.optimal else 500.0  # Start 10% above optimal
    best_cost = current_cost

    criteria = {
        "SimulatedAnnealing": SimulatedAnnealing(
            start_temp=100.0, end_temp=0.01, cooling_rate=0.995
        ),
        "LateAcceptanceHC": LateAcceptanceHC(history_length=100, warmup=10),
        "RecordToRecordTravel": RecordToRecordTravel(
            initial_deviation=100.0, min_deviation=0.0, decay_rate=0.997
        ),
    }

    rng = random.Random(42)
    iterations = 500
    trial_range = 20  # Simulated trial cost variation

    for name, criterion in criteria.items():
        accepted_count = 0
        improved_count = 0
        curr = current_cost
        best = current_cost

        for i in range(iterations):
            # Simulate a random trial solution
            trial = curr + rng.uniform(-trial_range, trial_range)
            result = criterion.decide(curr, trial, best, i, rng)
            if result.accepted:
                accepted_count += 1
                curr = trial
                if result.improved:
                    improved_count += 1
                    best = trial

        accept_rate = accepted_count / iterations * 100
        improve_rate = improved_count / iterations * 100
        final_cost = curr
        gap = (final_cost - best_cost) / best_cost * 100 if best_cost else 0

        print(f"\n  {name}:")
        print(f"    Başlangıç: {current_cost:.1f}")
        print(f"    Sonuç:     {final_cost:.1f} (gap={gap:+.2f}%)")
        print(f"    Kabul:     {accepted_count}/{iterations} ({accept_rate:.1f}%)")
        print(f"    İyileşme:  {improved_count}/{iterations} ({improve_rate:.1f}%)")


def demo_penalty_manager():
    """Demo 5: PenaltyManager — adaptif ceza yönetimi."""
    print("\n" + "=" * 65)
    print(" DEMO 5: PenaltyManager (Adaptif Ceza Yönetimi)")
    print("=" * 65)

    pm = PenaltyManager()

    # Simulate optimization trajectory with infeasible solutions
    print(f"\n  {'Iter':>5} {'Faz':>8} {'α_tw':>8} {'α_cap':>8} {'Tw Viol':>8} {'Cap Viol':>8} {'Penalized':>12}")
    print(f"  {'-'*5} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*12}")

    rng = random.Random(42)
    base_cost = 1000.0
    best_feasible = base_cost

    for iteration in range(200):
        # Simulate oscillating feasibility
        tw_viol = max(0, rng.gauss(5, 3)) if iteration % 7 < 4 else 0
        cap_viol = max(0, rng.gauss(2, 2)) if iteration % 11 < 6 else 0
        is_feasible = tw_viol == 0 and cap_viol == 0
        current_cost = base_cost + rng.gauss(0, 10)

        penalized = pm.compute_penalized_cost(current_cost, tw_viol, cap_viol)
        state = pm.get_state()

        if is_feasible and current_cost < best_feasible:
            best_feasible = current_cost

        # Print key iterations
        if iteration in [0, 10, 25, 50, 75, 100, 125, 150, 175, 199]:
            print(f"  {iteration:>5} {state.phase:>8} {state.alpha_tw:>8.2f} {state.alpha_cap:>8.2f} "
                  f"{tw_viol:>8.1f} {cap_viol:>8.1f} {penalized:>12.1f}")

        pm.update(iteration=iteration, current_cost=current_cost, is_feasible=is_feasible)

    final = pm.get_state()
    print(f"\n  Son durum: faz={final.phase}, α_tw={final.alpha_tw:.2f}, α_cap={final.alpha_cap:.2f}")
    print(f"  En iyi uygun: {best_feasible:.1f}")
    print(f"  Toplam iterasyon: {final.iteration}")


def demo_diversity(prob: ProblemInstance, population: List[List]):
    """Demo 6: DiversityController — popülasyon çeşitlilik yönetimi."""
    print("\n" + "=" * 65)
    print(" DEMO 6: DiversityController (Çeşitlilik Yönetimi)")
    print("=" * 65)

    dc = DiversityController()
    n = len(population)

    # Initial diversity analysis
    state = dc.get_state(population)
    print(f"  Problem: {prob.name}")
    print(f"  Popülasyon: {n} çözüm")
    print(f"  Entropi: {state.entropy:.3f}")
    print(f"  Ort. Hamming: {state.avg_distance:.1f}")
    print(f"  Popülasyon boyutu: {state.population_size}")
    print(f"  Enjeksiyon sayısı: {state.injection_count}")

    # Diversity injection simulation
    print(f"\n  Çeşitlilik kontrolü simülasyonu:")
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    for t in thresholds:
        should_inject = dc.should_inject_diversity(population, threshold=t)
        print(f"    threshold={t:.1f} → inject={should_inject}")

    # Simulate convergence (gradually make solutions more similar)
    print(f"\n  Yakınsama simülasyonu:")
    converged_pop = [population[0][:] for _ in range(n)]
    # Gradually perturb less
    for i in range(min(10, n)):
        perturb = max(1, prob.dimension // (i + 1))
        rng = random.Random(42 + i)
        for j in range(perturb):
            a, b = rng.sample(range(prob.dimension), 2)
            converged_pop[i][a], converged_pop[i][b] = converged_pop[i][b], converged_pop[i][a]

    conv_state = dc.get_state(converged_pop)
    print(f"    Yakınsamış popülasyon: entropy={conv_state.entropy:.3f}, avg_hamming={conv_state.avg_distance:.1f}")
    should_inject = dc.should_inject_diversity(converged_pop, threshold=0.3)
    print(f"    Çeşitlilik enjeksiyonu gerekli mi? {should_inject}")


def demo_full_pipeline(prob: ProblemInstance):
    """Demo 7: Full Pipeline — Tüm FAZ 0 modülleri birleşik."""
    print("\n" + "=" * 65)
    print(" DEMO 7: Full Pipeline (Tüm Modüller Birleşik)")
    print("=" * 65)

    t_total = time.perf_counter()
    rng = random.Random(42)

    # Step 1: Multi-Start Initialization
    print(f"\n  [1/5] Multi-Start Initializer...")
    nodes = prob.node_names
    dm_str = {}
    for i in range(prob.dimension):
        dm_str[nodes[i]] = {}
        for j in range(prob.dimension):
            dm_str[nodes[i]][nodes[j]] = float(prob.dist_matrix[i][j])

    population = MultiStartInitializer.generate_population(
        waypoints=nodes, distance_matrix=dm_str,
        pop_size=4, rng=rng, depot=nodes[0],
    )

    # Convert to int tours and find best
    int_pop = [[int(n) for n in sol] for sol in population]
    costs = [prob.tour_cost(t) for t in int_pop]
    best_idx = costs.index(min(costs))
    best_tour = int_pop[best_idx]
    best_cost = costs[best_idx]

    print(f"    4 çözüm üretildi, en iyi: cost={best_cost}, gap={prob.gap_pct(best_tour):.2f}%")

    # Step 2: Multi-Layer Local Search
    print(f"  [2/5] Multi-Layer Local Search...")
    t0 = time.perf_counter()
    improved_tour, ls_cost, ls_stats = MultiLayerLS.improve(
        best_tour, prob.cost_fn, rng, intensity="heavy",
    )
    ls_time = (time.perf_counter() - t0) * 1000
    ls_int_cost = int(ls_cost)
    if ls_int_cost < best_cost:
        best_tour = improved_tour
        best_cost = ls_int_cost
    print(f"    Sonuç: cost={best_cost}, gap={prob.gap_pct(best_tour):.2f}%, süre={ls_time:.0f}ms")

    # Step 3: ALNS Iteration (100 iterations)
    print(f"  [3/5] ALNS Iterations (100 destroy/repair)...")
    str_tour = [str(n) for n in best_tour]

    destroy_ops = [RandomRemoval(), WorstRemoval(), ShawRemoval(), RelatedRemoval()]
    repair_ops = [GreedyInsertion(), Regret2Insertion(), Regret3Insertion()]

    sa = SimulatedAnnealing(start_temp=50.0, end_temp=0.1, cooling_rate=0.99)
    q = max(3, prob.dimension // 10)
    alns_accepted = 0

    t0 = time.perf_counter()
    for i in range(100):
        # Random operator selection
        d_op = rng.choice(destroy_ops)
        r_op = rng.choice(repair_ops)

        # Destroy + Repair
        removed, remaining = d_op.destroy(str_tour, q, rng, distance_matrix=dm_str)
        new_tour_str = r_op.repair(remaining, removed, distance_matrix=dm_str)

        new_tour_int = [int(n) for n in new_tour_str]
        new_cost = prob.tour_cost(new_tour_int)

        # Acceptance decision
        result = sa.decide(float(best_cost), float(new_cost), float(best_cost), i, rng)
        if result.accepted and new_cost < best_cost:
            best_tour = new_tour_int
            best_cost = new_cost
            str_tour = new_tour_str
            alns_accepted += 1

    alns_time = (time.perf_counter() - t0) * 1000
    print(f"    Kabul edilen: {alns_accepted}/100")
    print(f"    Sonuç: cost={best_cost}, gap={prob.gap_pct(best_tour):.2f}%, süre={alns_time:.0f}ms")

    # Step 4: Final Local Search polish
    print(f"  [4/5] Final Local Search Polish...")
    t0 = time.perf_counter()
    final_tour, final_cost, final_stats = MultiLayerLS.improve(
        best_tour, prob.cost_fn, rng, intensity="medium",
    )
    polish_time = (time.perf_counter() - t0) * 1000
    final_int_cost = int(final_cost)
    if final_int_cost < best_cost:
        best_tour = final_tour
        best_cost = final_int_cost
    print(f"    Sonuç: cost={best_cost}, gap={prob.gap_pct(best_tour):.2f}%, süre={polish_time:.0f}ms")

    # Step 5: Summary
    total_time = (time.perf_counter() - t_total) * 1000
    print(f"\n  {'═'*55}")
    print(f"  PIPELINE SONUÇLARI")
    print(f"  {'═'*55}")
    print(f"  Problem:      {prob.name} (n={prob.dimension})")
    print(f"  Optimal:      {prob.optimal}" if prob.optimal else f"  Optimal:      bilinmiyor")
    print(f"  Final Cost:   {best_cost}")
    print(f"  Final Gap:    {prob.gap_pct(best_tour):.2f}%")
    print(f"  Total Time:   {total_time:.0f}ms")
    print(f"  Modules Used: MultiStart + MultiLayerLS + ALNS + SA")

    return best_tour, best_cost


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def list_available_problems():
    """List all available TSPLIB problems."""
    problems = get_available_problems()
    if not problems:
        print("  Mevcut TSPLIB problemi bulunamadı.")
        return

    print(f"\n  {len(problems)} TSPLIB problemi mevcut:\n")
    print(f"  {'Name':<14} {'Dim':>5} {'Optimal':>8} {'Category':>10} {'File':>5}")
    print(f"  {'-'*14} {'-'*5} {'-'*8} {'-'*10} {'-'*5}")

    for p in sorted(problems, key=lambda x: x.dimension):
        opt_str = str(p.optimal) if p.optimal else "N/A"
        has_file = "✓" if p.file_path else "✗"
        print(f"  {p.name:<14} {p.dimension:>5} {opt_str:>8} {p.category:>10} {has_file:>5}")


def main():
    """Main entry point."""
    banner = r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║         FAZ 0 — Standalone Demo (Web Arayüzü Yok)          ║
    ║     SOTA Common Infrastructure v{ver:<30s}║
    ╚══════════════════════════════════════════════════════════════╝
    """.format(ver=SOTA_INFRA_VERSION)

    print(banner)

    # Parse arguments
    args = sys.argv[1:]
    if "--list" in args or "-l" in args:
        list_available_problems()
        return

    # Default problem
    problem_name = "eil51"
    for arg in args:
        if not arg.startswith("-"):
            problem_name = arg.lower()
            break

    print(f"  Problem: {problem_name}")
    print(f"  Bağımlılık kontrolü: Sadece Python stdlib (FastAPI/Next.js yok)")

    # Load problem
    prob = load_problem(problem_name)
    if not prob:
        print("\n  Kullanılabilir problemler:")
        list_available_problems()
        return

    print(f"  Boyut: {prob.dimension} node")
    print(f"  Optimal: {prob.optimal}" if prob.optimal else "  Optimal: bilinmiyor")

    # ── Demo 1: Multi-Start ──
    population, costs = demo_multi_start(prob)
    best_idx = costs.index(min(costs))
    best_tour = population[best_idx]  # Already int tour
    best_cost = costs[best_idx]

    # ── Demo 2: Multi-Layer LS ──
    demo_multi_layer_ls(prob, best_tour)

    # ── Demo 3: ALNS Destroy+Repair ──
    demo_alns(prob, best_tour)

    # ── Demo 4: Acceptance Criteria ──
    demo_acceptance(prob)

    # ── Demo 5: Penalty Manager ──
    demo_penalty_manager()

    # ── Demo 6: Diversity Controller ──
    demo_diversity(prob, population)  # Already int tours

    # ── Demo 7: Full Pipeline ──
    demo_full_pipeline(prob)

    # ── Final Summary ──
    print("\n" + "=" * 65)
    print(" ÖZET")
    print("=" * 65)
    print(f"""
  FAZ 0 modülleri web arayüzü olmadan bağımsız çalışır.
  
  7 modül test edildi:
    1. MultiStartInitializer  — 4 başlangıç heuristiği
    2. MultiLayerLS           — 4 katmanlı yerel arama
    3. PenaltyManager         — Adaptif ceza yönetimi
    4. SimulatedAnnealing     — SA kabul kriteri
    5. DestroyOperators       — 4 yok etme operatörü
    6. RepairOperators        — 3 onarma operatörü
    7. DiversityController    — Popülasyon çeşitlilik kontrolü

  Dış bağımlılıklar: HİÇBİRİ (sadece Python stdlib)
  Gerekli: python >= 3.8
""")


if __name__ == "__main__":
    main()
