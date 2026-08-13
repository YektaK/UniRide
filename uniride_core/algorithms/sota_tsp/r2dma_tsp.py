"""
R²DMA-TSP — Resonance-Reinforced Destroy-and-Merge Algorithm (TSP variant)

Core pure-TSP implementation.
Uses integer-indexed tours and Numba-accelerated distance matrix.

Core DNA:
  - 6-dim resonance metric between solution pairs:
      (1) edge_similarity    — Jaccard on undirected edge sets
      (2) position_match     — fraction of positions with same city
      (3) distance_profile   — normalized edge-length distribution similarity
      (4) segment_length     — longest common segment ratio
      (5) common_subsequence — longest common subsequence approximation
      (6) cost_ratio         — relative tour cost similarity
  - 3-mode crossover: CONSTRUCTIVE (R>=0.7) / MODERATE (0.3<=R<0.7) / DESTRUCTIVE (R<0.3)
  - Tournament-based partner selection (k=5) for O(n_pop×k×n) complexity
  - OX crossover for moderate mode
  - ALNS destroy/repair for destructive mode
  - SA acceptance with dissonance filter
  - Adaptive theta threshold (success-rate tracking in segments)
  - Diversity pulse injection on entropy drop
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from .ls_engine import MultiLayerLS, improve_2opt, _tour_cost
from .destroy_ops import RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval
from .repair_ops import GreedyInsertion, Regret2Insertion, Regret3Insertion

from uniride_core.algorithms.utils import compute_population_diversity

# ── Numba JIT for pos_match (O(n²) bottleneck) ───────────────────────────────
try:
    import numba
    _NUMBA_OK = True
except ImportError:
    _NUMBA_OK = False

if _NUMBA_OK:
    @numba.njit(cache=True)
    def _pos_match_numba(t1, t2, n):
        """Rotation-normalized position match via Numba JIT.
        Uses position lookup array (O(1) per lookup) instead of dict.
        Returns best_match / n as float.
        """
        # Build position lookup: t2_pos[city] = index
        t2_pos = numba.typed.Dict.empty(key_type=numba.int64, value_type=numba.int64)
        for idx in range(n):
            t2_pos[numba.int64(t2[idx])] = numba.int64(idx)

        best = 0
        for r in range(n):
            match = 0
            for i in range(n):
                city = t1[(i + r) % n]
                if t2_pos.get(numba.int64(city), -1) == i:
                    match += 1
            if match > best:
                best = match
        return float(best) / float(n)

    def _fast_pos_match(t1, t2, n):
        """Numba-accelerated pos_match with pure-Python fallback."""
        if n > 200:
            return 0.0
        t2_set = set(t2)
        if len(t2_set) != n:
            return 0.0
        best_ratio = _pos_match_numba(
            numba.typed.List(t1), numba.typed.List(t2), n
        )
        return best_ratio if best_ratio > 0.0 else sum(1 for i in range(n) if t1[i] == t2[i]) / n
else:
    def _fast_pos_match(t1, t2, n):
        """Pure-Python fallback when Numba is unavailable."""
        if n > 200:
            return 0.0
        t2_set = set(t2)
        if len(t2_set) != n:
            return 0.0
        t2_pos = {city: idx for idx, city in enumerate(t2)}
        best = 0
        for r in range(n):
            match = 0
            for i in range(n):
                if t2_pos.get(t1[(i + r) % n]) == i:
                    match += 1
            if match > best:
                best = match
        best_ratio = best / n
        return best_ratio if best_ratio > 0.0 else sum(1 for i in range(n) if t1[i] == t2[i]) / n


@dataclass
class R2DMATSPConfig:
    population_size: int = 60
    max_iterations: int = 500
    theta_base: float = 0.5
    segment_size: int = 50
    remove_ratio: float = 0.20
    ls_intensity_constructive: str = "moderate"
    ls_intensity_moderate: str = "light"
    ls_intensity_destructive: str = "moderate"
    ls_time_limit: float = 0.5
    three_opt_window: int = 12
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    delta_threshold: float = 0.02
    entropy_threshold: float = 0.15
    pulse_injection_rate: float = 0.25
    diversity_check_interval: int = 50
    tournament_k: int = 5
    time_limit: float = 300.0
    seed: int = 42


class _SA:
    def __init__(self, start_temp: float, end_temp: float, cooling_rate: float, max_iter: int):
        self._temp = start_temp
        self._end = end_temp
        self._cooling = cooling_rate
        self._max_iter = max_iter

    def decide(self, current: float, new_cost: float, rng: random.Random) -> bool:
        if new_cost < current:
            return True
        if self._temp < 1e-12:
            return False
        delta = new_cost - current
        prob = math.exp(-delta / self._temp)
        return rng.random() < prob

    def cool(self):
        self._temp *= self._cooling
        if self._temp < self._end:
            self._temp = self._end


def _compute_resonance(t1: List[int], t2: List[int], n: int, dm: Optional[List[List[float]]] = None) -> float:
    """
    6-boyutlu rezonans metriği. İki tur arasındaki yapısal benzerliği ölçer.
    Boyutlar: edge_sim, pos_match, dist_sim, segment_len, common_subseq, cost_ratio
    """
    if n < 2:
        return 0.0

    # (1) Edge similarity: Jaccard on undirected edge sets — O(n)
    edges1 = set()
    for i in range(n):
        a, b = t1[i], t1[(i + 1) % n]
        edges1.add((min(a, b), max(a, b)))
    edges2 = set()
    for i in range(n):
        a, b = t2[i], t2[(i + 1) % n]
        edges2.add((min(a, b), max(a, b)))
    common_edges = len(edges1 & edges2)
    total_edges = len(edges1 | edges2)
    edge_sim = common_edges / total_edges if total_edges > 0 else 0.0

    # (2) Position match: rotation-normalized — Numba JIT accelerated
    pos_match = _fast_pos_match(t1, t2, n)

    # (3) Distance-profile similarity — O(n)
    dist_sim = 0.5
    d1 = None
    d2 = None
    if dm is not None:
        try:
            d1 = [dm[t1[i]][t1[(i + 1) % n]] for i in range(n)]
            d2 = [dm[t2[i]][t2[(i + 1) % n]] for i in range(n)]
            avg1 = sum(d1) / len(d1)
            avg2 = sum(d2) / len(d2)
            if avg1 > 1e-12 and avg2 > 1e-12:
                norm_diff = sum(abs((a / avg1) - (b / avg2)) for a, b in zip(d1, d2)) / n
                dist_sim = max(0.0, 1.0 - norm_diff / 2.0)
        except Exception:
            dist_sim = 0.5

    # (4) Segment length: en uzun ortak ardışık kenar zinciri — O(n)
    pos_map_2 = {city: idx for idx, city in enumerate(t2)}
    max_seg = 0
    current_seg = 0
    for i in range(n):
        next_in_t1 = t1[(i + 1) % n]
        pos_in_t2 = pos_map_2.get(t1[i], -1)
        if pos_in_t2 >= 0 and t2[(pos_in_t2 + 1) % n] == next_in_t1:
            current_seg += 1
            max_seg = max(max_seg, current_seg)
        else:
            current_seg = 0
    segment_len = max_seg / n if n > 0 else 0.0

    # (5) Common subsequence approximation: ardışık olmayan ortak sıra — O(n)
    pos_map_1 = {city: idx for idx, city in enumerate(t1)}
    ordered_count = 0
    for i in range(n - 1):
        city_a = t2[i]
        city_b = t2[i + 1]
        pos_a = pos_map_1.get(city_a, -1)
        pos_b = pos_map_1.get(city_b, -1)
        if pos_a >= 0 and pos_b >= 0 and pos_b > pos_a:
            ordered_count += 1
    common_subseq = ordered_count / max(1, n - 1)

    # (6) Cost ratio: tur maliyetleri arasındaki benzerlik — O(1) (d1/d2 zaten hesaplandı)
    cost_ratio = 0.5
    if d1 is not None and d2 is not None:
        cost1 = sum(d1)
        cost2 = sum(d2)
        if cost1 > 1e-12 and cost2 > 1e-12:
            cost_ratio = min(cost1, cost2) / max(cost1, cost2)

    # Ağırlıklı birleşim: 6-boyutlu rezonans skoru
    return (
        0.25 * edge_sim
        + 0.15 * pos_match
        + 0.15 * dist_sim
        + 0.20 * segment_len
        + 0.15 * common_subseq
        + 0.10 * cost_ratio
    )


class R2DMA_TSP(BaseTSPSolver):

    def __init__(self, config: Optional[R2DMATSPConfig] = None):
        super().__init__("R2DMA-TSP", config.seed if config else 42)
        self.cfg = config or R2DMATSPConfig()

    def _init_population(self, rng: random.Random) -> List[List[int]]:
        pop = []
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
        for i in range(self.cfg.population_size):
            if i < self.cfg.population_size // 4:
                start = rng.randrange(self._n)
                visited = {start}
                tour = [start]
                for _ in range(self._n - 1):
                    cur = tour[-1]
                    best_j = min((j for j in range(self._n) if j not in visited),
                                 key=lambda j: self._dist_matrix[cur][j])
                    tour.append(best_j)
                    visited.add(best_j)
            else:
                tour = list(range(self._n))
                rng.shuffle(tour)
            tour, _ = improve_2opt(tour, self._dist_matrix, dm_np, 50, True)
            pop.append(tour)
        return pop

    def _ox_crossover(self, p1: List[int], p2: List[int], rng: random.Random) -> List[int]:
        n = len(p1)
        a, b = sorted(rng.sample(range(n), 2))
        child = [None] * n
        child[a:b + 1] = p1[a:b + 1]
        segment = set(child[a:b + 1])
        idx = (b + 1) % n
        for gene in p2:
            if gene not in segment:
                while child[idx] is not None:
                    idx = (idx + 1) % n
                child[idx] = gene
        return child

    def _constructive_crossover(self, p1: List[int], p2: List[int], rng: random.Random) -> List[int]:
        edges1 = set()
        for i in range(len(p1)):
            a, b = p1[i], p1[(i + 1) % len(p1)]
            edges1.add((min(a, b), max(a, b)))  # Undirected edges for consistency with resonance
        edges2 = set()
        for i in range(len(p2)):
            a, b = p2[i], p2[(i + 1) % len(p2)]
            edges2.add((min(a, b), max(a, b)))  # Undirected edges for consistency with resonance
        common = list(edges1 & edges2)
        rng.shuffle(common)
        if not common:
            return self._ox_crossover(p1, p2, rng)
        adj: Dict[int, List[int]] = {}
        used = set()
        result = []
        for a, b in common:
            if a in used and b in used:
                continue
            if a not in used:
                result.append(a)
                used.add(a)
            if b not in used:
                result.append(b)
                used.add(b)
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        remaining = [x for x in range(self._n) if x not in used]
        rng.shuffle(remaining)
        result.extend(remaining)
        return result

    def _destructive_crossover(self, tour: List[int], rng: random.Random) -> List[int]:
        destroy_ops = [RandomRemoval(), WorstRemoval(), ShawRemoval(), RelatedRemoval()]
        repair_ops = [GreedyInsertion(), Regret2Insertion(), Regret3Insertion()]
        destroyer = rng.choice(destroy_ops)
        repairer = rng.choice(repair_ops)
        n_remove = max(2, int(self._n * self.cfg.remove_ratio))
        removed, remaining = destroyer.destroy(tour, n_remove, rng, self._dist_matrix)
        repaired = repairer.repair(remaining, removed, self._dist_matrix)
        return repaired

    def _perturb(self, tour: List[int], rng: random.Random) -> List[int]:
        result = list(tour)
        n = len(result)
        if n < 4:
            return result
        a, b = rng.sample(range(n), 2)
        result[a], result[b] = result[b], result[a]
        return result

    def _solve(self) -> TSPResult:
        rng = random.Random(self.cfg.seed)
        t_start = time.monotonic()
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None

        population = self._init_population(rng)
        pop_costs = [_tour_cost(t, self._dist_matrix) for t in population]

        gbest_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
        gbest = list(population[gbest_idx])
        gbest_cost = pop_costs[gbest_idx]

        sa = _SA(gbest_cost * self.cfg.sa_start_temp_factor,
                 self.cfg.sa_end_temp, self.cfg.sa_cooling_rate, self.cfg.max_iterations)

        theta = self.cfg.theta_base
        segment_results: List[bool] = []
        history: List[float] = []
        construct_count = moderate_count = destruct_count = 0

        for t in range(1, self.cfg.max_iterations + 1):
            offspring = []
            offspring_costs = []

            for i in range(len(population)):
                # B1: Tournament-based partner selection (k=tournament_k) — O(k×n)
                candidates = rng.sample(
                    [j for j in range(len(population)) if j != i],
                    min(self.cfg.tournament_k, len(population) - 1)
                )
                best_partner = None
                best_resonance = -1.0
                for j in candidates:
                    r = _compute_resonance(population[i], population[j], self._n, self._dist_matrix)
                    if r > best_resonance:
                        best_resonance = r
                        best_partner = j

                if best_partner is None or best_resonance < theta:
                    child = self._perturb(population[i], rng)
                    mode = "perturb"
                elif best_resonance >= 0.7:
                    child = self._constructive_crossover(population[i], population[best_partner], rng)
                    construct_count += 1
                    mode = "constructive"
                elif best_resonance >= 0.3:
                    child = self._ox_crossover(population[i], population[best_partner], rng)
                    moderate_count += 1
                    mode = "moderate"
                else:
                    child = self._destructive_crossover(population[i], rng)
                    destruct_count += 1
                    mode = "destructive"

                child_cost = _tour_cost(child, self._dist_matrix)

                if mode == "constructive":
                    child, child_cost, _ = MultiLayerLS.improve(
                        child, self._dist_matrix, dm_np, self.cfg.ls_intensity_constructive, 200, self.cfg.ls_time_limit,
                        self.cfg.three_opt_window)
                elif mode == "moderate":
                    child, child_cost, _ = MultiLayerLS.improve(
                        child, self._dist_matrix, dm_np, self.cfg.ls_intensity_moderate, 100, self.cfg.ls_time_limit,
                        self.cfg.three_opt_window)
                elif mode == "destructive":
                    child, child_cost, _ = MultiLayerLS.improve(
                        child, self._dist_matrix, dm_np, self.cfg.ls_intensity_destructive, 200, self.cfg.ls_time_limit,
                        self.cfg.three_opt_window)

                worse_parent = max(pop_costs[i], pop_costs[best_partner] if best_partner is not None else pop_costs[i])
                is_dissonant = child_cost > worse_parent * (1 + self.cfg.delta_threshold)
                accepted = sa.decide(pop_costs[i], child_cost, rng) and not is_dissonant

                if accepted:
                    offspring.append(child)
                    offspring_costs.append(child_cost)
                    if mode == "constructive":
                        segment_results.append(child_cost < worse_parent - 1e-10)
                else:
                    offspring.append(list(population[i]))
                    offspring_costs.append(pop_costs[i])

            population = offspring
            pop_costs = offspring_costs

            best_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
            if pop_costs[best_idx] < gbest_cost - 1e-10:
                gbest = list(population[best_idx])
                gbest_cost = pop_costs[best_idx]

            sa.cool()

            if t % self.cfg.segment_size == 0 and segment_results:
                success_rate = sum(segment_results) / len(segment_results)
                if success_rate > 0.6:
                    theta = max(0.2, theta - 0.05)
                elif success_rate < 0.3:
                    theta = min(0.8, theta + 0.05)
                segment_results = []

            if t % self.cfg.diversity_check_interval == 0:
                diversity = compute_population_diversity(population, self._n)
                if diversity < self.cfg.entropy_threshold:
                    n_inject = max(1, int(self.cfg.pulse_injection_rate * len(population)))
                    worst = sorted(range(len(pop_costs)), key=lambda i: pop_costs[i], reverse=True)[:n_inject]
                    for idx in worst:
                        population[idx] = self._destructive_crossover(population[idx], rng)
                        pop_costs[idx] = _tour_cost(population[idx], self._dist_matrix)

            history.append(gbest_cost)
            if time.monotonic() - t_start > self.cfg.time_limit:
                break

        remaining = max(0.0, self.cfg.time_limit - (time.monotonic() - t_start))
        final_ls_budget = min(self.cfg.ls_time_limit, remaining)
        if final_ls_budget > 0.0:
            gbest, gbest_cost, _ = MultiLayerLS.improve(
                gbest, self._dist_matrix, dm_np, "full", 500, final_ls_budget,
                self.cfg.three_opt_window,
            )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        return TSPResult(
            algorithm="R2DMA-TSP",
            tour=gbest,
            tour_length=gbest_cost,
            elapsed_ms=elapsed_ms,
            iterations=t,
            params={"population_size": self.cfg.population_size, "constructive": construct_count,
                    "moderate": moderate_count, "destructive": destruct_count},
            history=history,
            seed=self.cfg.seed,
        )
