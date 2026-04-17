# UniRide SOTA Framework — İyileştirilmiş Algoritma Tasarımları (PLAN)

> **Tarih**: 2026-04-14
> **Durum**: Implementation Plan (Uygulama Planı)
> **Önceki Belge**: `06_Success_DNA_Analysis.md` — 10 Başarı DNA'sı
> **Kapsam**: FAZ 0 (Ortak Altyapı) + E²BSO + R²DMA + P-AOEA detaylı tasarım

---

## İçindekiler

1. [Genel Mimari](#1-genel-mimari)
2. [FAZ 0: Ortak Altyapı Modülleri](#2-faz-0-ortak-altyapı-modülleri)
3. [FAZ 1: E²BSO — Enhanced Entropy-Balanced Swarm Optimization](#3-faz-1-e2bso--enhanced-entropy-balanced-swarm-optimization)
4. [FAZ 2: R²DMA — Resonance-Driven Memetic Algorithm with ALNS](#4-faz-2-r2dma--resonance-driven-memetic-algorithm-with-alns)
5. [FAZ 3: P-AOEA — Production Adaptive Operator Evolution Algorithm](#5-faz-3-p-aoea--production-adaptive-operator-evolution-algorithm)
6. [Entegrasyon Planı ve Zaman Çizelgesi](#6-entegrasyon-planı-ve-zaman-çizelgesi)
7. [Performans Hedefleri ve Benchmark Stratejisi](#7-performans-hedefleri-ve-benchmark-stratejisi)

---

## 1. Genel Mimari

### 1.1 Mimari Vizyon

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    UNIRIDE SOTA ALGORITHM FRAMEWORK                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    FAZ 0: ORTAK ALTYAPI                                │  │
│  │                                                                        │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │  │
│  │  │ MultiStart   │ │ MultiLayer   │ │ Penalty      │ │ Acceptance   │  │  │
│  │  │ Initializer  │ │ LS Engine    │ │ Manager      │ │ Criteria     │  │  │
│  │  │              │ │              │ │              │ │ (SA/LAHC/RTR)│  │  │
│  │  │ NN+CW+Regret │ │ 2opt→Or→3opt │ │ α_tw, α_cap │ │              │  │  │
│  │  │ +Random      │ │ →Swap→Repeat  │ │ adaptive     │ │              │  │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘  │  │
│  └─────────┼────────────────┼────────────────┼────────────────┼──────────┘  │
│            │                │                │                │              │
│  ┌─────────┼────────────────┼────────────────┼────────────────┼──────────┐  │
│  │         │    ALGORİTMALAR │                │                │          │  │
│  │         ▼                ▼                ▼                ▼          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│  │  │   E²BSO     │  │   R²DMA     │  │   P-AOEA    │                │  │
│  │  │             │  │             │  │             │                │  │
│  │  │ Entropy +   │  │ Resonance + │  │ Operator    │                │  │
│  │  │ ALNS-LS +   │  │ ALNS + SA + │  │ Co-Evolution│                │  │
│  │  │ Penalty +   │  │ Penalty +   │  │ + ALNS Ops  │                │  │
│  │  │ MultiStart  │  │ MultiStart  │  │ + Penalty   │                │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                │  │
│  └─────────┼────────────────┼────────────────┼──────────────────────┘  │
│            │                │                │                          │
│            ▼                ▼                ▼                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │              HybridSplitBaseStrategy + Split Decoder               │  │
│  │              (Giant Tour → Vehicle Routes)                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│            │                                                             │
│            ▼                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │              Strategy Registry (STRATEGY_REGISTRY)                  │  │
│  │              + Benchmark Runner + Web UI                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Dosya Yapısı (Target)

```
optimizer_api/strategies/
├── base_strategy.py                    # ✅ Mevcut
├── hybrid_base_strategy.py             # ✅ Mevcut
├── sota_common/                        # 🆕 FAZ 0 — Ortak Altyapı
│   ├── __init__.py
│   ├── multi_start_initializer.py       # NN + CW + Regret + Random
│   ├── multi_layer_ls.py               # 2-opt → Or-opt → 3-opt → Swap
│   ├── penalty_manager.py              # Adaptive α_tw, α_cap
│   ├── acceptance_criteria.py           # SA, LAHC, RTR
│   ├── destroy_operators.py            # Random, Worst, Related, Shaw removal
│   ├── repair_operators.py             # Greedy, Regret-2, Regret-3 insertion
│   └── diversity_controller.py         # Entropy tracking, diversity injection
├── ebso_strategy.py                    # 🆕 FAZ 1 — E²BSO
├── rdma_strategy.py                    # 🆕 FAZ 2 — R²DMA
├── aoea_strategy.py                    # 🆕 FAZ 3 — P-AOEA
└── __init__.py                         # ✅ Güncellenecek (registry eklentileri)
```

### 1.3 DNA Coverage Matrisi

```
Modül / DNA        | D1 Problem-Aware | D2 LNS | D3 Multi-LS | D4 Adaptif | D5 Split | D6 MultiStart | D7 Accept | D8 Diversity | D9 Penalty | D10 Neural
───────────────────┼──────────────────┼────────┼─────────────┼────────────┼─────────┼───────────────┼───────────┼──────────────┼────────────┼──────────
MultiStartInit    │                  │        │             │            │         │ ✅            │           │              │            │
MultiLayerLS      │                  │        │ ✅          │            │         │               │           │              │            │
PenaltyManager    │                  │        │             │            │         │               │           │              │ ✅         │
AcceptanceCrit    │                  │        │             │            │         │               │ ✅        │              │            │
DestroyOps        │ ✅               │ ✅     │             │            │         │               │           │              │            │
RepairOps         │ ✅               │ ✅     │             │            │         │               │           │              │            │
DiversityCtrl     │                  │        │             │            │         │               │           │ ✅           │            │
E²BSO             │ ✅ (entropy)     │ ✅     │ ✅ (inherited)│ ✅ (H)   │ ✅      │ ✅ (inherited)│ ✅ (SA)  │ ✅ (entropy)  │ ✅        │
R²DMA             │ ✅ (resonance)   │ ✅     │ ✅ (inherited)│ ✅ (θ)   │ ✅      │ ✅ (inherited)│ ✅ (SA)  │ ✅ (pulse)   │ ✅        │
P-AOEA            │ ✅ (genome)      │ ✅     │ ✅ (inherited)│ ✅ (meta)│ ✅      │ ✅ (inherited)│ ✅ (ev)  │ ✅ (inject)  │ ✅ (ev)   │
```

---

## 2. FAZ 0: Ortak Altyapı Modülleri

### 2.1 MultiStartInitializer

**Amacı:** 4 farklı heuristic ile çoklu başlangıç çözümü üretmek. (DNA #6)

```python
# optimizer_api/strategies/sota_common/multi_start_initializer.py

from typing import List, Dict, Tuple, Optional, Callable
import random
import logging

logger = logging.getLogger(__name__)


class MultiStartInitializer:
    """
    Çoklu başlangıç çözümü üretici.
    4 farklı heuristic ile yapılandırılmış çeşitlilik sağlar.
    
    Heuristic'ler:
    1. Nearest Neighbor (NN) — Hızlı, yakın node'ları tercih eder
    2. Clarke-Wright Savings — Araç sayısı optimize eder
    3. Regret Insertion — En acil node'ları önceliklendirir
    4. Random + Perturbation — Maksimum çeşitlilik
    
    Her heuristic'ten popülasyonun ¼'ünü üretir.
    """
    
    @staticmethod
    def generate_population(
        waypoints: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        pop_size: int,
        rng: random.Random,
        depot: Optional[str] = None,
        demands: Optional[Dict[str, Tuple[int, int]]] = None,
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> List[List[str]]:
        """
        pop_size adet başlangıç turu üretir.
        Dağılım: NN(¼), CW(¼), Regret(¼), Random(¼)
        
        Args:
            waypoints: Müşteri lokasyon kodları (depot dışı)
            distance_matrix: Mesafe matrisi
            pop_size: Toplam popülasyon boyutu
            rng: Random instance (tekrar edilebilirlik)
            depot: Depot lokasyon kodu (CW için gerekli)
            demands: Müşteri talepleri (Regret için gerekli)
            time_windows: Zaman pencereleri (Regret için opsiyonel)
            
        Returns:
            List of tours (each tour = List[str] of location codes)
        """
        n = len(waypoints)
        if pop_size <= 0:
            return []
        
        quarter = max(1, pop_size // 4)
        remainder = pop_size - 4 * quarter
        population = []
        
        # 1. NN Seed'ler — Farklı başlangıç noktaları ile
        nn_variants = MultiStartInitializer._nn_variants(
            waypoints, distance_matrix, quarter, rng
        )
        population.extend(nn_variants)
        
        # 2. Clarke-Wright Savings Seed'ler
        cw_variants = MultiStartInitializer._cw_variants(
            waypoints, distance_matrix, quarter, rng, depot
        )
        population.extend(cw_variants)
        
        # 3. Regret Insertion Seed'ler
        regret_variants = MultiStartInitializer._regret_variants(
            waypoints, distance_matrix, quarter, rng, demands, time_windows
        )
        population.extend(regret_variants)
        
        # 4. Random + Perturbation Seed'ler
        random_variants = MultiStartInitializer._random_variants(
            waypoints, quarter + remainder, rng
        )
        population.extend(random_variants)
        
        return population[:pop_size]
    
    @staticmethod
    def _nn_variants(
        waypoints: List[str],
        dist: Dict, count: int, rng: random.Random
    ) -> List[List[str]]:
        """Farklı başlangıç noktaları ile NN turları."""
        tours = []
        for i in range(count):
            start_idx = i % len(waypoints)
            tour = MultiStartInitializer._nearest_neighbor(
                waypoints, dist, start_node=waypoints[start_idx]
            )
            tours.append(tour)
        return tours
    
    @staticmethod
    def _nearest_neighbor(
        waypoints: List[str],
        dist: Dict,
        start_node: Optional[str] = None
    ) -> List[str]:
        """NN heuristic — start_node'dan başla."""
        remaining = set(waypoints)
        if start_node and start_node in remaining:
            current = start_node
            remaining.remove(current)
        else:
            current = remaining.pop()
        
        tour = [current]
        while remaining:
            best_next = min(
                remaining,
                key=lambda x: dist.get(current, {}).get(x, float('inf'))
            )
            tour.append(best_next)
            remaining.remove(best_next)
            current = best_next
        return tour
    
    @staticmethod
    def _cw_variants(
        waypoints: List[str],
        dist: Dict, count: int, rng: random.Random,
        depot: Optional[str] = None
    ) -> List[List[str]]:
        """Clarke-Wright Savings heuristic varyantları."""
        tours = []
        for i in range(count):
            # Savings hesapla: s(i,j) = d(depot,i) + d(depot,j) - d(i,j)
            savings_list = []
            d0 = dist.get(depot, {}) if depot else {}
            
            for a_idx in range(len(waypoints)):
                for b_idx in range(a_idx + 1, len(waypoints)):
                    a, b = waypoints[a_idx], waypoints[b_idx]
                    di = d0.get(a, float('inf'))
                    dj = d0.get(b, float('inf'))
                    dij = dist.get(a, {}).get(b, float('inf'))
                    if di < float('inf') and dj < float('inf') and dij < float('inf'):
                        savings = di + dj - dij
                        savings_list.append((savings, a, b))
            
            # Farklı sıralama varyantları
            if i % 3 == 0:
                savings_list.sort(key=lambda x: -x[0])  # Descending
            elif i % 3 == 1:
                savings_list.sort(key=lambda x: x[0])   # Ascending
            else:
                rng.shuffle(savings_list)                # Random
            
            # Merge route construction
            routes = {wp: [wp] for wp in waypoints}
            for _, a, b in savings_list[:len(waypoints)]:
                if a in routes and b in routes and routes[a] is not routes[b]:
                    # Merge routes
                    if routes[a][-1] == a and routes[b][0] == b:
                        routes[a].extend(routes[b])
                        routes[b] = routes[a]
                    elif routes[b][-1] == b and routes[a][0] == a:
                        routes[b].extend(routes[a])
                        routes[a] = routes[b]
            
            # Flatten to giant tour
            seen = set()
            tour = []
            for wp in waypoints:
                if wp not in seen and wp in routes:
                    for node in routes[wp]:
                        if node not in seen:
                            tour.append(node)
                            seen.add(node)
            tours.append(tour if len(tour) == len(waypoints) else rng.sample(waypoints, len(waypoints)))
        return tours
    
    @staticmethod
    def _regret_variants(
        waypoints: List[str],
        dist: Dict, count: int, rng: random.Random,
        demands: Optional[Dict] = None,
        time_windows: Optional[Dict] = None
    ) -> List[List[str]]:
        """Regret-based insertion heuristic varyantları."""
        tours = []
        for i in range(count):
            # Rastgele başlangıç (1-3 seed node)
            seed_count = min(3, len(waypoints))
            seeds = rng.sample(waypoints, seed_count)
            tour = list(seeds)
            remaining = set(waypoints) - set(seeds)
            
            while remaining:
                best_node = None
                best_regret = -1
                best_pos = 0
                
                for node in remaining:
                    # Her pozisyon için ekleme maliyeti hesapla
                    costs = []
                    for pos in range(len(tour) + 1):
                        prev = tour[pos - 1] if pos > 0 else None
                        next_ = tour[pos] if pos < len(tour) else None
                        
                        cost = 0.0
                        if prev and next_:
                            cost = dist.get(prev, {}).get(node, float('inf')) \
                                 + dist.get(node, {}).get(next_, float('inf')) \
                                 - dist.get(prev, {}).get(next_, float('inf'))
                        elif prev:
                            cost = dist.get(prev, {}).get(node, float('inf'))
                        elif next_:
                            cost = dist.get(node, {}).get(next_, float('inf'))
                        costs.append((cost, pos))
                    
                    costs.sort(key=lambda x: x[0])
                    
                    # Regret-2 hesapla
                    if len(costs) >= 2:
                        regret = costs[1][0] - costs[0][0]
                    else:
                        regret = costs[0][0] if costs else 0
                    
                    # TW urgency bonus
                    if time_windows and node in time_windows:
                        tw_start, tw_end = time_windows[node]
                        window_width = tw_end - tw_start
                        regret += 10.0 / max(window_width, 1.0)
                    
                    if regret > best_regret:
                        best_regret = regret
                        best_node = node
                        best_pos = costs[0][1] if costs else 0
                
                if best_node:
                    tour.insert(best_pos, best_node)
                    remaining.remove(best_node)
            
            tours.append(tour)
        return tours
    
    @staticmethod
    def _random_variants(
        waypoints: List[str], count: int, rng: random.Random
    ) -> List[List[str]]:
        """Rastgele + NN-perturbation turlar."""
        tours = []
        nn_tour = MultiStartInitializer._nearest_neighbor(waypoints, {})
        
        for i in range(count):
            if i < count // 3:
                # Saf rastgele
                tour = rng.sample(waypoints, len(waypoints))
            elif i < 2 * count // 3:
                # NN + scramble mutasyon
                tour = nn_tour.copy()
                seg_start = rng.randint(0, len(tour) - 2)
                seg_end = rng.randint(seg_start + 1, len(tour))
                tour[seg_start:seg_end] = reversed(tour[seg_start:seg_end])
            else:
                # NN + swap mutasyon
                tour = nn_tour.copy()
                for _ in range(len(tour) // 3):
                    a, b = rng.randint(0, len(tour) - 1), rng.randint(0, len(tour) - 1)
                    tour[a], tour[b] = tour[b], tour[a]
            
            tours.append(tour)
        return tours
```

---

### 2.2 MultiLayerLS — Çok Katmanlı Lokal Arama Motoru

**Amacı:** LKH-stil zincirleme lokal arama (DNA #3)

```python
# optimizer_api/strategies/sota_common/multi_layer_ls.py

from typing import List, Callable, Optional, Tuple
import random
import logging
import time

logger = logging.getLogger(__name__)


class MultiLayerLS:
    """
    Çok katmanlı lokal arama motoru.
    LKH'nin yaklaşımını taklit eder: 2-opt → Or-opt → 3-opt → Swap → zincirle.
    
    Her katman "first-improvement" stratejisi ile çalışır.
    İyileşme olana kadar katmanlar arasında geçiş yapılır.
    
    DNA #3: Agresif ve çok katmanlı LS = <1% gap'ın anahtarı
    """
    
    def __init__(
        self,
        max_time_seconds: float = 2.0,
        max_no_improve_layers: int = 3,
        enable_3opt: bool = True,
        enable_swap: bool = True,
        enable_or_opt: bool = True,
        time_limit_per_layer: float = 0.5,
    ):
        self.max_time = max_time_seconds
        self.max_no_improve = max_no_improve_layers
        self.enable_3opt = enable_3opt
        self.enable_swap = enable_swap
        self.enable_or_opt = enable_or_opt
        self.time_per_layer = time_limit_per_layer
    
    def improve(
        self,
        tour: List[str],
        cost_func: Callable[[List[str]], float],
        rng: Optional[random.Random] = None,
        intensity: str = "full"  # "full", "moderate", "light"
    ) -> Tuple[List[str], float, dict]:
        """
        Tur'u çok katmanlı LS ile iyileştir.
        
        Args:
            tour: Başlangıç turu
            cost_func: Maliyet fonksiyonu tour → float
            rng: Random instance
            intensity: "full" (tüm katmanlar), "moderate" (2-opt+or-opt), 
                       "light" (sadece 2-opt)
                       
        Returns:
            (improved_tour, final_cost, stats_dict)
        """
        start = time.time()
        rng = rng or random.Random(42)
        
        current = tour.copy()
        current_cost = cost_func(current)
        initial_cost = current_cost
        
        stats = {
            "initial_cost": initial_cost,
            "2opt_improves": 0,
            "or_opt_improves": 0,
            "3opt_improves": 0,
            "swap_improves": 0,
            "total_layers_run": 0,
            "time_seconds": 0.0,
        }
        
        no_improve_count = 0
        
        while time.time() - start < self.max_time and no_improve_count < self.max_no_improve:
            improved_this_cycle = False
            
            # Layer 1: 2-opt (HER ZAMAN)
            current, current_cost, imp = self._layer_2opt(current, cost_func, rng, self.time_per_layer)
            stats["2opt_improves"] += imp
            if imp > 0:
                improved_this_cycle = True
                stats["total_layers_run"] += 1
            
            if time.time() - start >= self.max_time:
                break
            
            # Layer 2: Or-opt (Node relocate + segment relocate)
            if self.enable_or_opt and intensity in ("full", "moderate"):
                current, current_cost, imp = self._layer_or_opt(current, cost_func, rng, self.time_per_layer)
                stats["or_opt_improves"] += imp
                if imp > 0:
                    improved_this_cycle = True
                    stats["total_layers_run"] += 1
            
            if time.time() - start >= self.max_time:
                break
            
            # Layer 3: 3-opt (Sadece full intensity)
            if self.enable_3opt and intensity == "full":
                current, current_cost, imp = self._layer_3opt(current, cost_func, rng, self.time_per_layer)
                stats["3opt_improves"] += imp
                if imp > 0:
                    improved_this_cycle = True
                    stats["total_layers_run"] += 1
            
            if time.time() - start >= self.max_time:
                break
            
            # Layer 4: Swap (inter-node)
            if self.enable_swap and intensity in ("full", "moderate"):
                current, current_cost, imp = self._layer_swap(current, cost_func, rng, self.time_per_layer)
                stats["swap_improves"] += imp
                if imp > 0:
                    improved_this_cycle = True
                    stats["total_layers_run"] += 1
            
            if improved_this_cycle:
                no_improve_count = 0
            else:
                no_improve_count += 1
        
        stats["final_cost"] = current_cost
        stats["improvement_pct"] = ((initial_cost - current_cost) / initial_cost * 100) if initial_cost > 0 else 0
        stats["time_seconds"] = time.time() - start
        
        return current, current_cost, stats
    
    @staticmethod
    def _layer_2opt(
        tour: List[str], cost_func: Callable, rng: random.Random,
        time_limit: float
    ) -> Tuple[List[str], float, int]:
        """2-opt: Her kenar çiftini kontrol et, first-improvement."""
        start = time.time()
        n = len(tour)
        improves = 0
        
        while time.time() - start < time_limit:
            best_delta = 0
            best_i, best_j = -1, -1
            
            for i in range(n - 1):
                if time.time() - start >= time_limit:
                    break
                for j in range(i + 2, n):
                    # Kenar (i, i+1) ve (j, j+1) → (i, j) ve (i+1, j+1)
                    new_tour = tour[:i+1] + tour[i+1:j+1][::-1] + tour[j+1:]
                    delta = cost_func(tour) - cost_func(new_tour)
                    if delta > best_delta:
                        best_delta = delta
                        best_i, best_j = i, j
            
            if best_delta > 0:
                tour = tour[:best_i+1] + tour[best_i+1:best_j+1][::-1] + tour[best_j+1:]
                improves += 1
            else:
                break  # İyileşme yok → sonraki katmana geç
        
        return tour, cost_func(tour), improves
    
    @staticmethod
    def _layer_or_opt(
        tour: List[str], cost_func: Callable, rng: random.Random,
        time_limit: float
    ) -> Tuple[List[str], float, int]:
        """Or-opt: Tek node veya segment taşıma."""
        start = time.time()
        n = len(tour)
        improves = 0
        
        while time.time() - start < time_limit:
            best_delta = 0
            best_op = None  # (type, from_idx, to_idx)
            
            for i in range(n):
                if time.time() - start >= time_limit:
                    break
                for j in range(n):
                    if abs(i - j) <= 1:
                        continue
                    
                    # Or-opt-1: Tek node taşı
                    new_tour = tour[:i] + tour[i+1:]
                    new_tour.insert(j if j < i else j - 1, tour[i])
                    delta = cost_func(tour) - cost_func(new_tour)
                    if delta > best_delta:
                        best_delta = delta
                        best_op = ("relocate", i, j)
                    
                    # Or-opt-2: 2-node segment taşı
                    if i + 1 < n:
                        seg = tour[i:i+2]
                        new_tour2 = tour[:i] + tour[i+2:]
                        insert_pos = j if j < i else j - 2
                        insert_pos = max(0, min(insert_pos, len(new_tour2)))
                        new_tour2 = new_tour2[:insert_pos] + seg + new_tour2[insert_pos:]
                        if len(new_tour2) == n:
                            delta2 = cost_func(tour) - cost_func(new_tour2)
                            if delta2 > best_delta:
                                best_delta = delta2
                                best_op = ("segment2", i, j)
            
            if best_delta > 0 and best_op:
                op_type, from_i, to_j = best_op
                if op_type == "relocate":
                    node = tour[from_i]
                    new_tour = tour[:from_i] + tour[from_i+1:]
                    insert_pos = to_j if to_j < from_i else to_j - 1
                    insert_pos = max(0, min(insert_pos, len(new_tour)))
                    new_tour.insert(insert_pos, node)
                    tour = new_tour
                elif op_type == "segment2":
                    seg = tour[from_i:from_i+2]
                    new_tour = tour[:from_i] + tour[from_i+2:]
                    insert_pos = to_j if to_j < from_i else to_j - 2
                    insert_pos = max(0, min(insert_pos, len(new_tour)))
                    tour = new_tour[:insert_pos] + seg + new_tour[insert_pos:]
                improves += 1
            else:
                break
        
        return tour, cost_func(tour), improves
    
    @staticmethod
    def _layer_3opt(
        tour: List[str], cost_func: Callable, rng: random.Random,
        time_limit: float
    ) -> Tuple[List[str], float, int]:
        """3-opt: Her 3 kenar kombinasyonu. Sadece full intensity."""
        start = time.time()
        n = len(tour)
        improves = 0
        
        # 3-opt = 7 farklı yeniden bağlantı şeması
        # En yaygın: reverse-middle, cycle-break
        while time.time() - start < time_limit:
            best_delta = 0
            best_config = None
            
            for i in range(n - 2):
                if time.time() - start >= time_limit:
                    break
                for j in range(i + 2, n - 1):
                    for k in range(j + 2, min(n, j + 10)):  # Limit search range
                        # Schema 1: Reverse middle segment
                        new_tour = tour[:i+1] + tour[j:i:-1] + tour[k+1:]
                        if len(new_tour) == n:
                            delta = cost_func(tour) - cost_func(new_tour)
                            if delta > best_delta:
                                best_delta = delta
                                best_config = (i, j, k, "reverse_mid")
            
            if best_delta > 0 and best_config:
                i, j, k, schema = best_config
                tour = tour[:i+1] + tour[j:i:-1] + tour[k+1:]
                improves += 1
            else:
                break
        
        return tour, cost_func(tour), improves
    
    @staticmethod
    def _layer_swap(
        tour: List[str], cost_func: Callable, rng: random.Random,
        time_limit: float
    ) -> Tuple[List[str], float, int]:
        """Swap: İki node'un yerini değiştir."""
        start = time.time()
        n = len(tour)
        improves = 0
        
        while time.time() - start < time_limit:
            best_delta = 0
            best_pair = None
            
            for i in range(n):
                if time.time() - start >= time_limit:
                    break
                for j in range(i + 1, n):
                    tour[i], tour[j] = tour[j], tour[i]
                    delta = cost_func(tour)  # Simplified: actual delta would be incremental
                    tour[i], tour[j] = tour[j], tour[i]  # Swap back
                    
                    if delta > best_delta:
                        best_delta = delta
                        best_pair = (i, j)
            
            if best_delta > 0 and best_pair:
                i, j = best_pair
                tour[i], tour[j] = tour[j], tour[i]
                improves += 1
            else:
                break
        
        return tour, cost_func(tour), improves
```

---

### 2.3 PenaltyManager — Adaptif Ceza Yönetimi

**Amacı:** Infeasible bölgeleri keşfetmek için TW ve kapasite cezalarını adaptif yönetmek (DNA #9)

```python
# optimizer_api/strategies/sota_common/penalty_manager.py

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PenaltyState:
    """Ceza durumu snapshot."""
    iteration: int
    alpha_tw: float       # Time window ceza katsayısı
    alpha_cap: float      # Kapasite ceza katsayısı
    phase: str            # "relax", "moderate", "strict"
    feasible_best: float
    current_best: float


class PenaltyManager:
    """
    Adaptif ceza yöneticisi.
    SOTA yaklaşım: Serbest arama → Feasible bölgeye çek → Kesin feasible.
    
    Iterated Penalty Method (Gendreau et al.):
    Phase 1: Düşük cezalar → Infeasible bölgeyi keşfet
    Phase 2: Ceza artır → Feasible bölgeye çek
    Phase 3: Agresif ceza → Neredeyse kesin feasible
    
    Formül:
    cost(solution) = total_distance 
                   + α_tw × Σ max(0, arrival - latest) 
                   + α_cap × Σ max(0, demand - capacity)
    """
    
    def __init__(
        self,
        initial_alpha_tw: float = 10.0,
        initial_alpha_cap: float = 5.0,
        max_alpha_tw: float = 10000.0,
        max_alpha_cap: float = 5000.0,
        increase_factor: float = 1.5,       # Her phase geçişinde çarpım
        phase_iterations: int = 500,         # Her phase'de iterasyon sayısı
        warmup_iterations: int = 100,        # İlk serbest keşif iterasyonu
    ):
        self.alpha_tw = initial_alpha_tw
        self.alpha_cap = initial_alpha_cap
        self.max_alpha_tw = max_alpha_tw
        self.max_alpha_cap = max_alpha_cap
        self.increase_factor = increase_factor
        self.phase_iters = phase_iterations
        self.warmup_iters = warmup_iterations
        
        self._iteration = 0
        self._phase = "relax"
        self._feasible_best_cost = float('inf')
        self._current_best_cost = float('inf')
    
    def compute_penalized_cost(
        self,
        base_cost: float,
        tw_violation: float,
        cap_violation: float,
    ) -> float:
        """
        Ceza eklenmiş toplam maliyet.
        
        Args:
            base_cost: Temel mesafe maliyeti
            tw_violation: Toplam TW ihlali (Σ max(0, arrival - latest))
            cap_violation: Toplam kapasite ihlali (Σ max(0, demand - capacity))
            
        Returns:
            Penalized cost
        """
        return base_cost + self.alpha_tw * tw_violation + self.alpha_cap * cap_violation
    
    def update(self, iteration: int, current_cost: float, is_feasible: bool):
        """
        Her iterasyonda çağrılır. Phase geçişlerini yönetir.
        
        Args:
            iteration: Mevcut iterasyon numarası
            current_cost: Mevcut çözüm maliyeti
            is_feasible: Çözüm feasible mi?
        """
        self._iteration = iteration
        self._current_best_cost = min(self._current_best_cost, current_cost)
        
        if is_feasible:
            self._feasible_best_cost = min(self._feasible_best_cost, current_cost)
        
        # Phase geçiş kararları
        if iteration < self.warmup_iters:
            self._phase = "relax"
        elif iteration < self.warmup_iters + self.phase_iters:
            self._phase = "moderate"
            self.alpha_tw = min(self.alpha_tw * 1.001, self.max_alpha_tw * 0.1)
            self.alpha_cap = min(self.alpha_cap * 1.001, self.max_alpha_cap * 0.1)
        else:
            self._phase = "strict"
            self.alpha_tw = min(self.alpha_tw * self.increase_factor, self.max_alpha_tw)
            self.alpha_cap = min(self.alpha_cap * self.increase_factor, self.max_alpha_cap)
    
    def get_state(self) -> PenaltyState:
        """Mevcut ceza durumunu döndür."""
        return PenaltyState(
            iteration=self._iteration,
            alpha_tw=self.alpha_tw,
            alpha_cap=self.alpha_cap,
            phase=self._phase,
            feasible_best=self._feasible_best_cost,
            current_best=self._current_best_cost,
        )
    
    @property
    def phase(self) -> str:
        return self._phase
    
    @property
    def feasible_best(self) -> float:
        return self._feasible_best_cost
```

---

### 2.4 AcceptanceCriterion — Kabul Kriterleri Kütüphanesi

**Amacı:** SA, LAHC, RTR kriterleri ile kontrollü kötü çözüm kabulü (DNA #7)

```python
# optimizer_api/strategies/sota_common/acceptance_criteria.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import math
import random
from collections import deque

@dataclass
class AcceptResult:
    """Kabul kararı sonucu."""
    accepted: bool
    improved: bool
    is_new_best: bool


class AcceptanceCriterion(ABC):
    """Abstract base for acceptance criteria."""
    
    @abstractmethod
    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: random.Random,
    ) -> AcceptResult:
        pass


class SimulatedAnnealing(AcceptanceCriterion):
    """
    SA kabul kriteri.
    
    P(accept) = exp(-ΔE / T(t))
    T(t) = T₀ × α^t
    
    DNA #7: En yaygın ve dengeli kabul kriteri.
    """
    
    def __init__(
        self,
        start_temp: float = 0.4,      # İlk çözüm maliyetinin %40'ı
        end_temp: float = 0.0001,
        cooling_rate: float = 0.9995,
    ):
        self.T_start = start_temp
        self.T_end = end_temp
        self.alpha = cooling_rate
        self.T = start_temp
    
    def _compute_temp(self, iteration: int, max_iter: int):
        """Geometrik soğuma."""
        progress = min(iteration / max(max_iter, 1), 1.0)
        self.T = self.T_start * (self.T_end / self.T_start) ** progress
    
    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: random.Random,
        max_iter: int = 10000,
    ) -> AcceptResult:
        self._compute_temp(iteration, max_iter)
        delta = new_cost - current_cost
        
        is_new_best = new_cost < best_cost
        improved = new_cost < current_cost
        
        if delta <= 0:
            return AcceptResult(accepted=True, improved=improved, is_new_best=is_new_best)
        
        probability = math.exp(-delta / max(self.T, 1e-10))
        accepted = rng.random() < probability
        
        return AcceptResult(accepted=accepted, improved=False, is_new_best=False)


class LateAcceptanceHC(AcceptanceCriterion):
    """
    Late Acceptance Hill Climbing (LAHC).
    
    "Son L iterasyonun en kötüsünden daha iyiysem, kabul et."
    
    DNA #7: SA'dan daha deterministik, hafıza-bazlı.
    Özellikle EBSO için önerilen kabul kriteri.
    """
    
    def __init__(self, history_length: int = 500):
        self.L = history_length
        self.history = deque(maxlen=history_length)
        self._initialized = False
    
    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: random.Random,
        **kwargs,
    ) -> AcceptResult:
        is_new_best = new_cost < best_cost
        improved = new_cost < current_cost
        
        if not self._initialized:
            self.history.append(current_cost)
            if len(self.history) >= self.L:
                self._initialized = True
        
        # Karşılaştır: en kötü tarihî maliyet
        if self._initialized:
            worst_historical = max(self.history)
            accepted = new_cost <= worst_historical
        else:
            # Warmup: sadece iyileştirenleri kabul et
            accepted = improved
        
        if accepted:
            self.history.append(new_cost)
        else:
            self.history.append(current_cost)
        
        return AcceptResult(accepted=accepted, improved=improved, is_new_best=is_new_best)


class RecordToRecordTravel(AcceptanceCriterion):
    """
    Record-to-Record Travel (RTR).
    
    threshold = best + deviation
    deviation başlangıçta yüksek, zamanla azalır.
    
    DNA #7: Agresif exploitation. SA'dan daha hızlı yakınsama.
    """
    
    def __init__(
        self,
        initial_deviation: float = 0.4,
        min_deviation: float = 0.001,
        decay_rate: float = 0.999,
    ):
        self.deviation = initial_deviation
        self.min_dev = min_deviation
        self.decay = decay_rate
    
    def decide(
        self,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: random.Random,
        **kwargs,
    ) -> AcceptResult:
        threshold = best_cost * (1.0 + self.deviation)
        is_new_best = new_cost < best_cost
        improved = new_cost < current_cost
        accepted = new_cost <= threshold
        
        self.deviation = max(self.deviation * self.decay, self.min_dev)
        
        return AcceptResult(accepted=accepted, improved=improved, is_new_best=is_new_best)
```

---

### 2.5 Destroy & Repair Operatörleri

**Amacı:** ALNS-stil yapılandırılmış büyük komşuluk araması (DNA #1, #2)

```python
# optimizer_api/strategies/sota_common/destroy_operators.py

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
import random
import logging

logger = logging.getLogger(__name__)


class DestroyOperator(ABC):
    """Abstract base for destroy operators."""
    
    @abstractmethod
    def destroy(self, tour: List[str], q: int, rng: random.Random,
                distance_matrix: Optional[Dict] = None,
                demands: Optional[Dict] = None,
                time_windows: Optional[Dict] = None,
                ) -> Tuple[List[str], List[str]]:
        """
        q müşteriyi turdan kaldır.
        
        Returns:
            (remaining_tour, removed_customers)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass


class RandomRemoval(DestroyOperator):
    """Rastgele q müşteri kaldır. Basit ama gerekli exploration."""
    
    @property
    def name(self) -> str:
        return "random_removal"
    
    def destroy(self, tour, q, rng, **kwargs):
        q = min(q, len(tour))
        removed = rng.sample(tour, q)
        remaining = [x for x in tour if x not in set(removed)]
        return remaining, removed


class WorstRemoval(DestroyOperator):
    """En yüksek maliyetli q müşteriyi kaldır."""
    
    @property
    def name(self) -> str:
        return "worst_removal"
    
    def destroy(self, tour, q, rng, distance_matrix=None, **kwargs):
        if not distance_matrix:
            return RandomRemoval().destroy(tour, q, rng)
        
        # Her müşteri için kaldırma maliyeti
        costs = []
        for i, node in enumerate(tour):
            prev_node = tour[i - 1] if i > 0 else None
            next_node = tour[i + 1] if i < len(tour) - 1 else None
            
            if prev_node and next_node:
                removal_cost = (
                    distance_matrix.get(prev_node, {}).get(node, 0)
                    + distance_matrix.get(node, {}).get(next_node, 0)
                    - distance_matrix.get(prev_node, {}).get(next_node, 0)
                )
            else:
                removal_cost = 0
            
            costs.append((removal_cost, i, node))
        
        costs.sort(key=lambda x: -x[0])  # En pahalı önce
        q = min(q, len(costs))
        
        # Top-k arasından rastgele seç (degree of randomness)
        top_k = min(q * 3, len(costs))
        selected = rng.sample(costs[:top_k], q)
        removed = [s[2] for s in selected]
        remaining = [x for x in tour if x not in set(removed)]
        return remaining, removed


class ShawRemoval(DestroyOperator):
    """
    Shaw benzerlik fonksiyonuna göre ilişkili müşterileri kaldır.
    
    R(c₀, cⱼ) = μ₁·dist(c₀, cⱼ) + μ₂·|demand(c₀) - demand(cⱼ)|
    
    DNA #1: Problem-structure aware operator.
    """
    
    def __init__(self, mu_distance: float = 0.7, mu_demand: float = 0.3):
        self.mu_dist = mu_distance
        self.mu_demand = mu_demand
    
    @property
    def name(self) -> str:
        return "shaw_removal"
    
    def destroy(self, tour, q, rng, distance_matrix=None, demands=None, **kwargs):
        if not distance_matrix:
            return RandomRemoval().destroy(tour, q, rng)
        
        # İlk kaldırılacak müşteriyi rastgele seç
        c0_idx = rng.randint(0, len(tour) - 1)
        removed = [tour[c0_idx]]
        remaining = [x for x in tour if x != tour[c0_idx]]
        
        # Normalize demand
        all_demands = [1]  # Default
        if demands:
            all_demands = [d[0] + d[1] for d in demands.values() if d]
        max_demand = max(all_demands) if all_demands else 1
        
        # Normalize distance
        max_dist = 1.0
        for a in tour:
            for b in tour:
                if a != b:
                    d = distance_matrix.get(a, {}).get(b, 0)
                    max_dist = max(max_dist, d)
        
        while len(removed) < q and remaining:
            c0 = removed[-1]
            similarities = []
            
            for node in remaining:
                dist = distance_matrix.get(c0, {}).get(node, max_dist) / max(max_dist, 1e-10)
                dem = 0.0
                if demands and c0 in demands and node in demands:
                    dem = abs(sum(demands[c0]) - sum(demands[node])) / max(max_demand, 1e-10)
                
                similarity = self.mu_dist * dist + self.mu_demand * dem
                similarities.append((similarity, node))
            
            similarities.sort(key=lambda x: x[0])
            
            # İlk r arasından rastgele seç
            r = max(1, len(similarities) // 3)
            selected_idx = rng.randint(0, min(r - 1, len(similarities) - 1))
            selected_node = similarities[selected_idx][1]
            
            removed.append(selected_node)
            remaining.remove(selected_node)
        
        return remaining, removed


class RelatedRemoval(DestroyOperator):
    """Uzaklık bazlı ilişkili müşterileri kaldır."""
    
    @property
    def name(self) -> str:
        return "related_removal"
    
    def destroy(self, tour, q, rng, distance_matrix=None, **kwargs):
        if not distance_matrix:
            return RandomRemoval().destroy(tour, q, rng)
        
        c0_idx = rng.randint(0, len(tour) - 1)
        removed = [tour[c0_idx]]
        remaining = [x for x in tour if x != tour[c0_idx]]
        
        while len(removed) < q and remaining:
            c0 = removed[-1]
            # En yakın q müşteriyi bul
            distances = []
            for node in remaining:
                d = distance_matrix.get(c0, {}).get(node, float('inf'))
                distances.append((d, node))
            distances.sort(key=lambda x: x[0])
            
            # Yakın olanları tercih et ama rastgelelik ekle
            k = max(1, min(q - len(removed), len(distances)))
            selected_idx = rng.randint(0, min(k - 1, len(distances) - 1))
            selected_node = distances[selected_idx][1]
            
            removed.append(selected_node)
            remaining.remove(selected_node)
        
        return remaining, removed
```

```python
# optimizer_api/strategies/sota_common/repair_operators.py

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
import random
import logging

logger = logging.getLogger(__name__)


class RepairOperator(ABC):
    """Abstract base for repair operators."""
    
    @abstractmethod
    def repair(self, remaining: List[str], removed: List[str],
               distance_matrix: Dict, rng: random.Random,
               capacity: Optional[float] = None,
               demands: Optional[Dict] = None,
               time_windows: Optional[Dict] = None,
               ) -> List[str]:
        """Kaldırılan müşterileri geri ekle."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass


class GreedyInsertion(RepairOperator):
    """Her müşteriyi en iyi pozisyona ekle."""
    
    @property
    def name(self) -> str:
        return "greedy_insertion"
    
    def repair(self, remaining, removed, distance_matrix, rng, **kwargs):
        tour = remaining.copy()
        
        for node in removed:
            best_cost = float('inf')
            best_pos = 0
            
            for pos in range(len(tour) + 1):
                cost = 0.0
                if pos > 0 and pos < len(tour):
                    prev_node = tour[pos - 1]
                    next_node = tour[pos]
                    cost = (
                        distance_matrix.get(prev_node, {}).get(node, float('inf'))
                        + distance_matrix.get(node, {}).get(next_node, float('inf'))
                        - distance_matrix.get(prev_node, {}).get(next_node, 0)
                    )
                elif pos == 0 and len(tour) > 0:
                    cost = distance_matrix.get(node, {}).get(tour[0], float('inf'))
                elif pos == len(tour) and len(tour) > 0:
                    cost = distance_matrix.get(tour[-1], {}).get(node, float('inf'))
                
                if cost < best_cost:
                    best_cost = cost
                    best_pos = pos
            
            tour.insert(best_pos, node)
        
        return tour


class Regret2Insertion(RepairOperator):
    """
    Regret-2 bazlı ekleme.
    "Eğer şimdi eklemessen, ileride çok daha pahalı olacak" → Öncelik ver.
    
    DNA #1: Problem-structure aware repair operator.
    """
    
    @property
    def name(self) -> str:
        return "regret_2_insertion"
    
    def repair(self, remaining, removed, distance_matrix, rng, **kwargs):
        tour = remaining.copy()
        uninserted = list(removed)
        
        while uninserted:
            best_node = None
            best_regret = -1
            best_pos = 0
            
            for node in uninserted:
                # Her pozisyon için maliyet hesapla
                costs = []
                for pos in range(len(tour) + 1):
                    cost = 0.0
                    if pos > 0 and pos < len(tour):
                        prev_node = tour[pos - 1]
                        next_node = tour[pos]
                        cost = (
                            distance_matrix.get(prev_node, {}).get(node, float('inf'))
                            + distance_matrix.get(node, {}).get(next_node, float('inf'))
                            - distance_matrix.get(prev_node, {}).get(next_node, 0)
                        )
                    elif pos == 0 and len(tour) > 0:
                        cost = distance_matrix.get(node, {}).get(tour[0], float('inf'))
                    elif pos == len(tour) and len(tour) > 0:
                        cost = distance_matrix.get(tour[-1], {}).get(node, float('inf'))
                    costs.append((cost, pos))
                
                costs.sort(key=lambda x: x[0])
                
                # Regret-2: 2. en iyi - 1. en iyi
                regret = costs[1][0] - costs[0][0] if len(costs) >= 2 else costs[0][0]
                
                if regret > best_regret:
                    best_regret = regret
                    best_node = node
                    best_pos = costs[0][1]
            
            if best_node:
                tour.insert(best_pos, best_node)
                uninserted.remove(best_node)
        
        return tour


class Regret3Insertion(RepairOperator):
    """Regret-3 bazlı ekleme. En yüksek kalite, en yüksek maliyet."""
    
    @property
    def name(self) -> str:
        return "regret_3_insertion"
    
    def repair(self, remaining, removed, distance_matrix, rng, **kwargs):
        tour = remaining.copy()
        uninserted = list(removed)
        
        while uninserted:
            best_node = None
            best_regret = -1
            best_pos = 0
            
            for node in uninserted:
                costs = []
                for pos in range(len(tour) + 1):
                    cost = 0.0
                    if pos > 0 and pos < len(tour):
                        prev_node = tour[pos - 1]
                        next_node = tour[pos]
                        cost = (
                            distance_matrix.get(prev_node, {}).get(node, float('inf'))
                            + distance_matrix.get(node, {}).get(next_node, float('inf'))
                            - distance_matrix.get(prev_node, {}).get(next_node, 0)
                        )
                    elif pos == 0 and len(tour) > 0:
                        cost = distance_matrix.get(node, {}).get(tour[0], float('inf'))
                    elif pos == len(tour) and len(tour) > 0:
                        cost = distance_matrix.get(tour[-1], {}).get(node, float('inf'))
                    costs.append((cost, pos))
                
                costs.sort(key=lambda x: x[0])
                
                # Regret-3: 1.0×(2.best - 1.best) + 0.5×(3.best - 1.best)
                if len(costs) >= 3:
                    regret = 1.0 * (costs[1][0] - costs[0][0]) + 0.5 * (costs[2][0] - costs[0][0])
                elif len(costs) >= 2:
                    regret = costs[1][0] - costs[0][0]
                else:
                    regret = costs[0][0]
                
                if regret > best_regret:
                    best_regret = regret
                    best_node = node
                    best_pos = costs[0][1]
            
            if best_node:
                tour.insert(best_pos, best_node)
                uninserted.remove(best_node)
        
        return tour
```

---

### 2.6 DiversityController — Çeşitlilik Yönetimi

**Amacı:** Popülasyon çeşitliliğini takip et ve erken yakınsamayı engelle (DNA #8)

```python
# optimizer_api/strategies/sota_common/diversity_controller.py

from typing import List, Dict, Set
import random
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class DiversityController:
    """
    Popülasyon çeşitlilik kontrolcüsü.
    
    İki metrik:
    1. Kenar çeşitliliği: Popülasyondaki benzersiz kenar sayısı / toplam kenar
    2. Pozisyon çeşitliliği: Her pozisyondaki benzersiz node sayısı (Shannon entropisi)
    
    Eğer çeşitlilik threshold'ın altına düşerse → yapılandırılmış enjeksiyon.
    """
    
    def __init__(
        self,
        min_diversity: float = 0.3,       # Minimum çeşitlilik oranı [0, 1]
        injection_rate: float = 0.2,       # Enjeksiyon oranı
        check_interval: int = 50,          # Her N iterasyonda kontrol et
        use_entropy: bool = True,           # Shannon entropisi kullan
    ):
        self.min_diversity = min_diversity
        self.injection_rate = injection_rate
        self.check_interval = check_interval
        self.use_entropy = use_entropy
    
    def compute_diversity(self, population: List[List[str]]) -> float:
        """
        Popülasyon çeşitliliğini [0, 1] aralığında hesapla.
        
        Kenar bazlı çeşitlilik:
        diversity = |unique_edges| / (N × n)  — N=pop_size, n=tur_uzunluğu
        """
        if not population or len(population) < 2:
            return 1.0
        
        n = len(population[0])
        N = len(population)
        
        # Benzersiz kenarları say
        all_edges: Set[tuple] = set()
        for tour in population:
            for i in range(len(tour) - 1):
                all_edges.add((tour[i], tour[i + 1]))
        
        total_possible = N * n
        diversity = len(all_edges) / max(total_possible, 1)
        return min(diversity, 1.0)
    
    def needs_injection(self, population: List[List[str]], iteration: int) -> bool:
        """Çeşitlilik injection gerekli mi?"""
        if iteration % self.check_interval != 0:
            return False
        
        diversity = self.compute_diversity(population)
        return diversity < self.min_diversity
    
    def inject(
        self,
        population: List[List[str]],
        fresh_tours: List[List[str]],
        rng: random.Random,
    ) -> List[List[str]]:
        """
        Popülasyona taze turlar enjekte et.
        En kötü bireyleri değiştir.
        """
        if not fresh_tours:
            return population
        
        # Enjeksiyon sayısı
        n_inject = max(1, int(len(population) * self.injection_rate))
        n_inject = min(n_inject, len(fresh_tours))
        
        # Popülasyonu fitness'a göre sırala (ilk eleman = en iyi)
        # En kötü n_inject bireyi değiştir
        result = population[:len(population) - n_inject]
        result.extend(fresh_tours[:n_inject])
        
        return result
```

---

## 3. FAZ 1: E²BSO — Enhanced Entropy-Balanced Swarm Optimization

### 3.1 EBSO → E²BSO Değişiklik Özeti

| Bileşen | Orijinal EBSO | E²BSO (Enhanced) | DNA |
|---------|---------------|-------------------|-----|
| Başlangıç | Rastgele max-entropi | **MultiStartInitializer** (NN+CW+Regret+Random) | #6 |
| LS | Basit VNS | **MultiLayerLS** (2opt→Or→3opt→Swap) | #3 |
| Sıkıştırma Fazı | Standart swarm update | **ALNS destroy/repair** (Shaw+Regret) | #1, #2 |
| Kabul Kriteri | Sadece improving-only | **LAHC** (Late Acceptance HC) | #7 |
| Infeasible | Reddet | **PenaltyManager** (α_tw, α_cap adaptif) | #9 |
| Entropi Hesabı | Her iterasyonda tam | **Incremental + Fast Approx** | #4, #8 |
| Adaptif Parametreler | Sabit H_min, H_max | **Instance-adaptive** learning | #4 |

### 3.2 E²BSO Algoritma Mimarisi

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        E²BSO ALGORITHM FLOW                             │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 1. BAŞLANGIÇ: MultiStartInitializer                              │  │
│  │    NN(¼) + CW(¼) + Regret(¼) + Random(¼) → Popülasyon P₀       │  │
│  │    Her tour → MultiLayerLS(intensity="light") ile ön-iyileştir   │  │
│  └─────────────────────────┬─────────────────────────────────────────┘  │
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────────────────────┐  │
│  │ 2. PENALTY MANAGER BAŞLAT                                        │  │
│  │    α_tw = 10, α_cap = 5 (relax phase)                           │  │
│  │    Phase schedule: relax(0-100) → moderate(100-600) → strict(>600)│  │
│  └─────────────────────────┬─────────────────────────────────────────┘  │
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────────────────────┐  │
│  │ 3. LAHC ACCEPTANCE CRITERION BAŞLAT                               │  │
│  │    History length L = 500                                         │  │
│  └─────────────────────────┬─────────────────────────────────────────┘  │
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────────────────────┐  │
│  │ 4. ANA DÖNGÜ (t = 1..T_max)                                       │  │
│  │                                                                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │ 4.1 H(P) = Popülasyon Entropisi Hesapla (incremental)     │   │  │
│  │  │     Her 10 iterasyonda tam hesapla, arada cache kullan    │   │  │
│  │  └────────────┬───────────────────────────────────────────────┘   │  │
│  │               │                                                    │  │
│  │     ┌─────────┼──────────┐                                       │  │
│  │     ▼                   ▼                                       │  │
│  │  ┌──────────┐    ┌──────────────────────────────────────────┐  │  │
│  │  │ H < H_min│    │ H_min ≤ H ≤ H_max → NORMAL İYİLEŞTİRME  │  │  │
│  │  │          │    │  4.2a Swarm update (gBest + pBest)       │  │  │
│  │  │ ENJEKS-  │    │  4.2b MultiLayerLS(intensity="moderate")│  │  │
│  │  │ İYON     │    │       olasılık=100%                       │  │  │
│  │  │          │    │  4.2c LAHC kabul kriteri                  │  │  │
│  │  │ ALNS-stil│    │  4.2d PenaltyManager.update()            │  │  │
│  │  │ destroy  │    └──────────────────────────────────────────┘  │  │
│  │  │ + Shaw   │                                                   │  │
│  │  │ repair   │    ┌──────────────────────────────────────────┐  │  │
│  │  │ + Regret │    │ H > H_max → SIKIŞTIRMA                    │  │  │
│  │  │ + LS     │    │  4.3a Agresif swarm (pBest ağırlık ↑)    │  │  │
│  │  │          │    │  4.3b MultiLayerLS(intensity="full")      │  │  │
│  │  └──────────┘    │       olasılık=100%                       │  │  │
│  │                   │  4.3c LAHC kabul kriteri                  │  │  │
│  │                   │  4.3d PenaltyManager.update()            │  │  │
│  │                   └──────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │ 4.4 DIVERSITY CHECK (her 50 iterasyonda)                   │   │  │
│  │  │     diversity < threshold → inject taze turlar             │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  │                                                                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │ 4.5 H_min/H_max GÜNCELLEME (instance-adaptive)             │   │  │
│  │  │     İlk 200 iterasyonda: H_min ve H_max öğren              │   │  │
│  │  │     "Bu instance'da H_min=0.3 çok düşük kalıyor" → 0.4     │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  │                                                                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │ 4.6 PENALTY PHASE GEÇİŞİ                                  │   │  │
│  │  │     Iteration > warmup → α_tw ve α_cap artır              │   │  │
│  │  │     Phase 3'te: α_tw=10000, α_cap=5000 → ~kesin feasible  │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 5. FİNAL: En iyi feasible çözüm + MultiLayerLS(full)             │  │
│  │    Split Decoder ile araç rotalarına böl → OUTPUT                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 E²BSO Konfigürasyon Parametreleri

```python
E2BSO_CONFIG = {
    # Popülasyon
    "population_size": 60,
    "max_iterations": 2000,
    
    # Multi-start
    "multi_start_enabled": True,
    "nn_ratio": 0.25,
    "cw_ratio": 0.25,
    "regret_ratio": 0.25,
    "random_ratio": 0.25,
    
    # Entropi kontrolü
    "h_start": 0.8,            # Başlangıç entropi hedefi (yüksek → exploration)
    "h_end": 0.2,              # Bitiş entropi hedefi (düşük → exploitation)
    "gamma": 0.5,              # Soğuma eğrisi
    "entropy_check_interval": 10,  # Her N iterasyonda tam hesapla
    
    # Adaptive threshold learning
    "adapt_threshold": True,
    "threshold_learn_period": 200,  # İlk N iterasyonda öğren
    
    # Multi-layer LS
    "ls_time_limit": 2.0,
    "ls_exploration_intensity": "light",    # Exploration fazında
    "ls_exploitation_intensity": "full",     # Exploitation fazında
    
    # ALNS integration
    "alns_enabled": True,
    "destroy_operators": ["random", "worst", "shaw", "related"],
    "repair_operators": ["greedy", "regret_2", "regret_3"],
    "remove_ratio_range": (0.10, 0.40),
    
    # LAHC acceptance
    "lahc_history_length": 500,
    
    # Penalty management
    "initial_alpha_tw": 10.0,
    "initial_alpha_cap": 5.0,
    "max_alpha_tw": 10000.0,
    "max_alpha_cap": 5000.0,
    "warmup_iterations": 100,
    
    # Diversity
    "diversity_min": 0.3,
    "diversity_check_interval": 50,
    "injection_rate": 0.2,
    
    # Split decoder
    "use_split_decoder": True,
}
```

### 3.4 E²BSO DNA Coverage

```
DNA    | EBSO (Original) | E²BSO (Enhanced) | İyileştirme
───────┼─────────────────┼──────────────────┼───────────────
#1     | Kenar frekansı  | Shaw+Regret ops   | Problem-aware operatörler
#2     | Tek node update | ALNS destroy/repair| Büyük komşuluk araması
#3     | Basit VNS       | MultiLayerLS      | 4 katmanlı zincirleme LS
#4     | Adaptif H_target | Instance-adaptive | H_min/H_max öğrenme
#5     | ✅ Split        | ✅ Split          | Zaten mevcut
#6     | Random          | MultiStart (4 heuristic) | Yapılandırılmış başlangıç
#7     | Improving-only  | LAHC              | Hafıza bazlı kabul
#8     | Entropi kontrol | Entropi + injection| Fast approx + injection
#9     | Feasible-only   | Penalty relax     | Infeasible keşfet
#10    | —               | —                 | Gelecek (P3 sonrası)
```

---

## 4. FAZ 2: R²DMA — Resonance-Driven Memetic Algorithm with ALNS

### 4.1 RDMA → R²DMA Değişiklik Özeti

| Bileşen | Orijinal RDMA | R²DMA (Enhanced) | DNA |
|---------|---------------|------------------|-----|
| Başlangıç | NN + Random | **MultiStartInitializer** | #6 |
| Destructive Mode | Scramble mutation | **ALNS destroy/repair** (Shaw+Regret) | #1, #2 |
| LS | Sadece en iyi N'ye | **MultiLayerLS** (tüm child'lara, adaptif derinlik) | #3 |
| Kabul Kriteri | Dissonans filtresi | **Dissonans + SA** birleşik | #7 |
| Rezonans Metriği | Kenar + alt-tur | **Kenar + Shaw similarity + TW + kapasite** | #1, #9 |
| Adaptif θ_esik | Basit güncelleme | **Segment-based ALNS adaptive** | #4 |
| Harmonic Pulse | Spectral clustering | **Fast distance-based clustering** | #8 |
| Infeasible | Reddet | **Penalty-based relaxation** | #9 |

### 4.2 R²DMA Algoritma Mimarisi

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         R²DMA ALGORITHM FLOW                               │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ 1. BAŞLANGIÇ: MultiStartInitializer + MultiLayerLS(light)         │  │
│  │    4 heuristic seed → P₀ (popülasyon)                             │  │
│  │    Her birey → Rezonans ID hesapla                                │  │
│  │    Rezonans Matrisi R[i][j] oluştur                              │  │
│  └──────────────────────────┬─────────────────────────────────────────┘  │
│                             │                                             │
│  ┌──────────────────────────▼─────────────────────────────────────────┐  │
│  │ 2. SA + PENALTY MANAGER BAŞLAT                                     │  │
│  │    T₀ = initial_cost × 0.4, α = 0.9995                           │  │
│  │    α_tw = 10, α_cap = 5                                           │  │
│  └──────────────────────────┬─────────────────────────────────────────┘  │
│                             │                                             │
│  ┌──────────────────────────▼─────────────────────────────────────────┐  │
│  │ 3. ANA DÖNGÜ (t = 1..T_max)                                         │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3.1 REZONANS EŞLEŞTİRME                                       │  │  │
│  │  │     Her Si için en yüksek R(Si, Sj) ≥ θ_esik partneri bul   │  │  │
│  │  │     θ_esik = adaptive (segment-based, ρ=100 iter)             │  │  │
│  │  │                                                               │  │  │
│  │  │     Adaptif Mekanizma:                                        │  │  │
│  │  │     Son 100 iterasyonda:                                       │  │  │
│  │  │       Constructive mode success_rate → θ_esik GÜNCELLE        │  │  │
│  │  │       "Düşük R ile üretilen child'ler iyi" → θ DÜŞÜR         │  │  │
│  │  └────────────┬─────────────────────────────────────────────────┘  │  │
│  │               │                                                      │  │
│  │               ▼                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3.2 REZONANS TABANLI ÇAPRAZLAMA + ALNS                        │  │  │
│  │  │                                                               │  │  │
│  │  │  if R ≥ 0.7 (CONSTRUCTIVE):                                   │  │  │
│  │  │    → Ortak kenar iskeleti oluştur                             │  │  │
│  │  │    → NN-guided completion                                     │  │  │
│  │  │    → MultiLayerLS(moderate)                                   │  │  │
│  │  │                                                               │  │  │
│  │  │  elif 0.3 ≤ R < 0.7 (MODERATE):                              │  │  │
│  │  │    → Standart OX crossover + rezonans bias                    │  │  │
│  │  │    → MultiLayerLS(light)                                      │  │  │
│  │  │                                                               │  │  │
│  │  │  else (DESTRUCTIVE INTERFERENCE — ENHANCED):                  │  │  │
│  │  │    → ESKİ: Scramble mutation                                  │  │  │
│  │  │    → YENİ: ALNS destroy/repair                                │  │  │
│  │  │      • Destroy: Shaw removal (q = %15-30 of tour)            │  │  │
│  │  │      • Repair: Regret-2 insertion                             │  │  │
│  │  │      • MultiLayerLS(moderate)                                 │  │  │
│  │  │    → NEDEN? "Düşük rezonanslı ebeveynler arası yapısal        │  │  │
│  │  │       ilişki zayıf → Büyük değişiklik gerekli"                 │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3.3 PENALTY-BASED DİSSONANS FİLTRESİ + SA KABUL               │  │  │
│  │  │                                                               │  │  │
│  │  │  cost(child) = base_distance + α_tw × tw_viol + α_cap × cap │  │  │
│  │  │                                                               │  │  │
│  │  │  ESKİ: if cost(child) < min(cost(P1), cost(P2)) - δ: REDDET│  │  │
│  │  │                                                               │  │  │
│  │  │  YENİ: if cost(child) < min(cost(P1), cost(P2)) - δ:        │  │  │
│  │  │          SA.decide(current, child) → Kabul et                │  │  │
│  │  │        "Rezonans düşük ama SA kabul ettiyse, yine de al"     │  │  │
│  │  │        → Daha geniş arama alanı                               │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3.4 REZONANS GÜNCELLEME (incremental)                         │  │  │
│  │  │     Başarılı child → R frekans ARTIR                           │  │  │
│  │  │     Başarısız child → R frekans AZALT                         │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3.5 HARMONIC CONVERGENCE CHECK (fast)                         │  │  │
│  │  │     Entropy(P) < ε → DIVERSITY INJECTION                     │  │  │
│  │  │     ESKİ: Spectral clustering (pahalı)                        │  │  │
│  │  │     YENİ: Distance-based k-means (hızlı, O(n·k))            │  │  │
│  │  │     Cluster'lar arası cross-over → Structured diversity        │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3.6 REZONANS METRİĞİ GELİŞTİRME                               │  │  │
│  │  │                                                               │  │  │
│  │  │  ESKİ: R(P1,P2) = w1·E_common + w2·S_sub + w3·H_comp         │  │  │
│  │  │                                                               │  │  │
│  │  │  YENİ: R(P1,P2) = w1·E_common + w2·S_sub + w3·H_comp         │  │  │
│  │  │                  + w4·Shaw_similarity + w5·TW_resonance       │  │  │
│  │  │                  + w6·CAP_resonance                           │  │  │
│  │  │                                                               │  │  │
│  │  │  Shaw_similarity = Shaw removal benzerlik fonksiyonu        │  │  │
│  │  │  TW_resonance = İki çözümün TW satisfaction pattern'ı       │  │  │
│  │  │  CAP_resonance = Kapasite kullanım profili benzerliği        │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │ 4. FİNAL: En iyi çözüm → MultiLayerLS(full) → Split Decode → OUTPUT ││
│  └──────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Geliştirilmiş Rezonans Metriği

```python
def enhanced_resonance(
    tour1: List[str], tour2: List[str],
    distance_matrix: Dict,
    demands: Optional[Dict] = None,
    time_windows: Optional[Dict] = None,
    weights: Tuple[float, ...] = (0.25, 0.20, 0.15, 0.15, 0.15, 0.10)
) -> float:
    """
    6-boyutlu rezonans metriği.
    
    R = w1·E_common + w2·S_sub + w3·H_comp
      + w4·Shaw_sim + w5·TW_res + w6·CAP_res
    
    w1: Ortak kenar oranı
    w2: LCS-based alt-tur benzerliği  
    w3: Hamiltoniyen tamamlanabilirlik
    w4: Shaw benzerlik (mesafe + demand)
    w5: Time window satisfaction pattern benzerliği
    w6: Kapasite kullanım profili benzerliği
    """
    w1, w2, w3, w4, w5, w6 = weights
    
    # 1. Ortak kenar oranı
    edges1 = set()
    edges2 = set()
    for i in range(len(tour1) - 1):
        edges1.add((tour1[i], tour1[i+1]))
    for i in range(len(tour2) - 1):
        edges2.add((tour2[i], tour2[i+1]))
    common = edges1 & edges2
    total = edges1 | edges2
    e_common = len(common) / max(len(total), 1)
    
    # 2. LCS-based alt-tur benzerliği
    from difflib import SequenceMatcher
    s_sub = SequenceMatcher(None, tour1, tour2).ratio()
    
    # 3. Hamiltoniyen tamamlanabilirlik (basitleştirilmiş)
    # İki turu birleştirip geçerli tur oluşturulabilir mi?
    h_comp = len(common) / max(len(tour1), 1)
    
    # 4. Shaw benzerlik
    shaw_sim = _shaw_similarity(tour1, tour2, distance_matrix, demands)
    
    # 5. TW resonance (varsa)
    tw_res = 0.5  # Default
    if time_windows:
        tw_res = _tw_resonance(tour1, tour2, time_windows)
    
    # 6. Capacity resonance (varsa)
    cap_res = 0.5  # Default
    if demands:
        cap_res = _capacity_resonance(tour1, tour2, demands)
    
    return w1*e_common + w2*s_sub + w3*h_comp + w4*shaw_sim + w5*tw_res + w6*cap_res
```

### 4.4 R²DMA Konfigürasyon Parametreleri

```python
R2DMA_CONFIG = {
    # Popülasyon
    "population_size": 60,
    "max_iterations": 2000,
    
    # Multi-start
    "multi_start_enabled": True,
    
    # Rezonans
    "resonance_weights": (0.25, 0.20, 0.15, 0.15, 0.15, 0.10),
    "theta_base": 0.5,
    "segment_size": 100,           # Adaptif θ için
    
    # ALNS integration (destructive mode)
    "alns_destroy_when_low_r": True,
    "destroy_operators": ["shaw", "worst", "related", "random"],
    "repair_operators": ["regret_2", "regret_3", "greedy"],
    "remove_ratio": (0.15, 0.30),
    
    # LS
    "ls_constructive": "moderate",
    "ls_moderate": "light",
    "ls_destructive": "moderate",
    "ls_final": "full",
    "ls_time_limit": 2.0,
    
    # SA acceptance
    "sa_start_temp": 0.4,
    "sa_end_temp": 0.0001,
    "sa_cooling_rate": 0.9995,
    
    # Penalty
    "initial_alpha_tw": 10.0,
    "initial_alpha_cap": 5.0,
    
    # Dissonance
    "delta_threshold": 0.02,       # δ: %2 tolerans
    
    # Harmonic Pulse
    "entropy_threshold": 0.15,
    "pulse_injection_rate": 0.25,
    "clustering_method": "kmeans",  # spectral veya kmeans
    
    # Diversity
    "diversity_min": 0.3,
    "diversity_check_interval": 50,
}
```

---

## 5. FAZ 3: P-AOEA — Production Adaptive Operator Evolution Algorithm

### 5.1 AOEA → P-AOEA Değişiklik Özeti

| Bileşen | Orijinal AOEA | P-AOEA (Production) | DNA |
|---------|---------------|--------------------|-----|
| Başlangıç | Random | **MultiStartInitializer** | #6 |
| Atomic Ops | 10 basic | **20+ (CVRPTW-specific ek)** | #1 |
| Destroy İntensity | Sabit | **Adaptif** (erken: %30-40, geç: %10-15) | #2 |
| LS | Olasılıksal | **MultiLayerLS** (adaptif derinlik) | #3 |
| Meta-evrim Interval | Sabit Φ | **Adaptif** (erken: sık, geç: seyrek) | #4 |
| Acceptance | Evrilen genome | **SA + LAHC + RTR seed'leri** | #7 |
| Penalty | penalty_insert var | **Adaptif α parametreleri** (genome evrilir) | #9 |
| Newborn Genome | Tamamen random | **Structured injection** (en iyi genome mutasyonu) | #8 |

### 5.2 P-AOEA Zenginleştirilmiş Atomic Operations

```
┌─────────────────────────────────────────────────────────────────────────┐
│              P-AOEA ATOMIC OPERATIONS LIBRARY                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DESTROY (20+):                                                        │
│  ├── random_remove(k)               ✅ Orijinal                        │
│  ├── worst_remove(k)                 ✅ Orijinal                        │
│  ├── related_remove(k, λ)            ✅ Orijinal                        │
│  ├── shaw_remove(k)                  ✅ Orijinal                        │
│  ├── cluster_remove(c)               ✅ Orijinal                        │
│  ├── tw_violation_remove()           🆕 CVRPTW-specific                 │
│  ├── tight_tw_remove()               🆕 Sıkışık TW'lular                │
│  ├── capacity_remove()               🆕 Kapasite baskılı rotalar         │
│  ├── route_remove(r)                 ✅ Orijinal                        │
│  ├── bridge_remove()                 ✅ Orijinal                        │
│  ├── corridor_remove()               ✅ Orijinal                        │
│  ├── time_warp_remove()              🆕 TW sequence violation           │
│  ├── demand_cluster_remove()         🆕 Yüksek talepli cluster          │
│  ├── long_edge_remove()              🆕 En uzun kenarları kaldır        │
│  ├── distant_remove()                🆕 Merkezden uzak node'lar         │
│  └── random_segment_remove()         🆕 Rastgele segment kaldırma       │
│                                                                         │
│  REPAIR (20+):                                                         │
│  ├── greedy_insert(seq)               ✅ Orijinal                        │
│  ├── regret2_insert(seq)              ✅ Orijinal                        │
│  ├── regret3_insert(seq)              ✅ Orijinal                        │
│  ├── tw_aware_insert(seq)             🆕 CVRPTW-specific                 │
│  ├── cap_aware_insert(seq)            🆕 Kapasite uyumlu                │
│  ├── parallel_insert()                ✅ Orijinal                        │
│  ├── cheapest_insert()                ✅ Orijinal                        │
│  ├── penalty_insert(α_tw, α_cap)     🆕 Adaptive penalty               │
│  ├── reinsert(shuffle)                ✅ Orijinal                        │
│  ├── local_search_insert()            ✅ Orijinal                        │
│  ├── schedule_insert()                🆕 Zaman çizelgesi uyumlu          │
│  ├── urgent_tw_insert()               🆕 Acil TW'lu node öncelik         │
│  ├── best_worst_insert()              🆕 En iyi/kötü pozisyon analizi    │
│  ├── two_opt_insert()                 🆕 Her eklemede 2-opt              │
│  ├── sequential_insert()              🆕 Sıralı ekleme                    │
│  └── greedy_batch_insert()            🆕 Toplu greedy ekleme             │
│                                                                         │
│  ACCEPTANCE (7):                                                       │
│  ├── sa_boltzmann(T₀, α)             ✅ Orijinal                        │
│  ├── sa_exponential(T₀, β)            ✅ Orijinal                        │
│  ├── threshold(δ)                     ✅ Orijinal                        │
│  ├── improving_only()                  ✅ Orijinal                        │
│  ├── great_deluge(λ)                  ✅ Orijinal                        │
│  ├── record_to_record()                🆕 RTR                             │
│  └── late_acceptance(L)                🆕 LAHC                            │
│                                                                         │
│  GENOME MUTATION OPERATORS:                                             │
│  ├── intensity_mutate()               🆕 Destroy intensity değiştir     │
│  ├── swap_operator()                  🆕 İki atomic op değiştir          │
│  ├── add_operator()                   🆕 Yeni atomic op ekle              │
│  ├── remove_operator()                🆕 Atomic op kaldır                │
│  ├── weight_mutate()                  🆕 Operator ağırlıklarını değiştir │
│  └── parameter_mutate()               🆕 Operator parametrelerini değiştir│
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 P-AOEA Adaptive Destroy Intensity

```python
def adaptive_destroy_intensity(
    iteration: int,
    max_iterations: int,
    n_customers: int,
) -> float:
    """
    Erken iterasyonlarda yüksek, geç iterasyonlarda düşük destroy.
    
    Early (0-30%):   30-40% kaldır → Geniş keşif
    Middle (30-70%): 15-25% kaldır → Dengeli
    Late (70-100%):  10-15% kaldır → Hassas iyileştirme
    
    Neden?
      Erken iterasyonlarda popülasyon henüz yakınsamadı → 
        Büyük değişiklikler yeni bölgeleri keşfetmeye yardımcı olur.
      Geç iterasyonlarda popülasyon iyi bölgelere yakın →
        Küçük değişiklikler hassas tuning sağlar.
    """
    progress = iteration / max(max_iterations, 1)
    
    if progress < 0.3:
        # Erken: Yüksek intensity
        base = 0.35
        variation = 0.05 * (1 - progress / 0.3)
    elif progress < 0.7:
        # Orta: Dengeli
        base = 0.20
        variation = 0.05
    else:
        # Geç: Düşük intensity
        base = 0.12
        variation = 0.03
    
    # Büyük instance'larda biraz daha düşük (computational cost)
    if n_customers > 500:
        base *= 0.8
    elif n_customers > 200:
        base *= 0.9
    
    return max(0.10, min(0.40, base + variation * random.random()))
```

### 5.4 P-AOEA Structured Genome Injection

```python
def structured_genome_injection(
    best_genomes: List[OperatorGenome],
    n_new: int,
    rng: random.Random,
) -> List[OperatorGenome]:
    """
    Tamamen random yerine, en iyi genome'lerin mutasyonu.
    
    ESKİ AOEA: Yeni genome = tamamen random operator seçimi
    P-AOEA: Yeni genome = en iyi genome + mutasyon → Structured diversity
    
    Neden?
      Tamamen random genome'ler ilk iterasyonlarda çok zayıf performans gösterir.
      En iyi genome'in mutasyonu, başarılı özellikleri korurken
      yeterli çeşitlilik sağlar.
    """
    new_genomes = []
    
    if not best_genomes:
        # Henüz iyi genome yok → random (fallback)
        return [random_genome(rng) for _ in range(n_new)]
    
    for _ in range(n_new):
        # En iyi genome'lerden birini seç (roulette wheel)
        parent = roulette_wheel_select(best_genomes, rng)
        
        # Mutasyon uygula
        child = mutate_genome(parent, rng, mutation_rate=0.3)
        child.age = 0
        child.fitness = 0.0
        child.success_history.clear()
        
        new_genomes.append(child)
    
    # %10 tamamen random da ekle (tam çeşitlilik)
    n_random = max(1, n_new // 10)
    for _ in range(n_random):
        new_genomes.append(random_genome(rng))
    
    return new_genomes[:n_new]
```

---

## 6. Entegrasyon Planı ve Zaman Çizelgesi

### 6.1 Geliştirme Takvimi

```
HAFTA 1-2: FAZ 0 — Ortak Altyapı
├── multi_start_initializer.py        ████░░░░░░ 3 gün
├── multi_layer_ls.py                 ███░░░░░░ 2 gün
├── penalty_manager.py                ██░░░░░░░░ 1.5 gün
├── acceptance_criteria.py            ██░░░░░░░░ 1.5 gün
├── destroy_operators.py              ███░░░░░░ 2.5 gün
├── repair_operators.py               ███░░░░░░ 2.5 gün
├── diversity_controller.py           ██░░░░░░░░ 1.5 gün
└── sota_common/__init__.py           ░░░░░░░░░░ 0.5 gün
Toplam: ~15 gün

HAFTA 3-4: FAZ 1 — E²BSO
├── ebso_strategy.py (HybridSplitBase)  ██████░░░░ 5 gün
├── E²BSO entegrasyon testleri          ███░░░░░░░ 3 gün
├── TSPLIB benchmark validation         ██░░░░░░░░ 2 gün
└── __init__.py registry eklentisi      ░░░░░░░░░░ 0.5 gün
Toplam: ~10 gün

HAFTA 5-6: FAZ 2 — R²DMA
├── rdma_strategy.py (HybridSplitBase)  ███████░░░ 6 gün
├── R²DMA entegrasyon testleri          ███░░░░░░░ 3 gün
├── TSPLIB + CVRPTW benchmark           ███░░░░░░░ 3 gün
└── __init__.py registry eklentisi      ░░░░░░░░░░ 0.5 gün
Toplam: ~12 gün

HAFTA 7-9: FAZ 3 — P-AOEA (Opsiyonel)
├── aoea_strategy.py                   █████████░ 8 gün
├── 20+ atomic operations library       █████░░░░░ 5 gün
├── P-AOEA testleri                     ████░░░░░░ 4 gün
└── Benchmark validation                ███░░░░░░░ 3 gün
Toplam: ~20 gün

HAFTA 10: Dokümantasyon + Akademik Makale Hazırlık
├── Benchmark sonuçları analizi         ███░░░░░░░ 3 gün
├── Makale draft (E²BSO)                █████░░░░░ 5 gün
├── Makale draft (R²DMA)                █████░░░░░ 5 gün
└── Görselleştirme + tablolar            ██░░░░░░░░ 2 gün
Toplam: ~15 gün
```

### 6.2 Öncelik Sırası ve Karar Noktaları

```
Karar Noktası 1 (HaFTA 2 sonu):
  FAZ 0 tamamlanıp tamamlanmadığını değerlendir
  Eğer ortak altyapı stabilize değilse → FAZ 0'a devam
  
Karar Noktası 2 (HaFTA 4 sonu):
  E²BSO benchmark sonuçlarını kontrol et
  Hedef: TSPLIB eil51 gap < 3%, berlin52 gap < 2%
  ✅ Hedefe ulaşıldı → FAZ 2'ye geç
  ❌ Hedefe ulaşılamadı → E²BSO'yu tuning et, 1 hafta ek zaman ver
  
Karar Noktası 3 (HaFTA 6 sonu):
  R²DMA benchmark sonuçlarını kontrol et
  Hedef: TSPLIB eil51 gap < 2%, kroA100 gap < 2%
  ✅ Hedefe ulaşıldı → P-AOEA'ya başla
  ❌ Hedefe ulaşılamadı → R²DMA'yu tuning et
  
Karar Noktası 4 (HaFTA 9 sonu):
  P-AOEA'ya devam et veya durdur
  E²BSO + R²DMA yeterince güçlüyse → Makale yazımına geç
  P-AOEA da eklemek istiyorsak → Devam et
```

---

## 7. Performans Hedefleri ve Benchmark Stratejisi

### 7.1 TSPLIB Benchmark Hedefleri

```
Instance    | n     | Optimal | E²BSO Hedef | R²DMA Hedef | P-AOEA Hedef | Mevcut GA
────────────┼───────┼─────────┼─────────────┼─────────────┼──────────────┼──────────
eil51       | 51    | 426     | <3% (439)    | <2% (435)    | <2% (435)    | ~15%
eil76       | 76    | 538     | <3% (554)    | <2% (549)    | <2% (549)    | ~18%
berlin52    | 52    | 7542    | <2% (7693)   | <1.5% (7655) | <1% (7618)  | ~12%
kroA100     | 100   | 21282   | <4% (22133)  | <3% (21921)  | <2% (21707)  | ~20%
kroB100     | 100   | 22141   | <4% (23027)  | <3% (22805)  | <2% (22584)  | ~22%
lin318      | 318   | 42029   | <5% (44130)  | <4% (43710)  | <3% (43290)  | ~30%
pr226       | 226   | 80369   | <4% (83584)  | <3% (82780)  | <3% (82780)  | ~25%
```

### 7.2 CVRPTW Benchmark Hedefleri (Solomon Set)

```
Instance Sınıfı | Araç Hedef | Mesafe Gap Hedef | E²BSO | R²DMA | P-AOEA
────────────────┼────────────┼──────────────────┼───────┼───────┼───────
C1  (Clustered)  | ≤ BKS + 1  | <2%              | ✓✓✓   | ✓✓    | ✓✓✓
R1  (Random)     | ≤ BKS + 2  | <3%              | ✓✓    | ✓✓✓   | ✓✓✓
RC1 (RandClust)  | ≤ BKS + 2  | <3%              | ✓✓    | ✓✓    | ✓✓✓
C2  (Clustered)  | ≤ BKS + 0  | <1%              | ✓✓✓   | ✓✓✓   | ✓✓✓
R2  (Random)     | ≤ BKS + 1  | <2%              | ✓✓    | ✓✓    | ✓✓✓
RC2 (RandClust)  | ≤ BKS + 1  | <2%              | ✓     | ✓✓    | ✓✓
```

### 7.3 Karşılaştırma Benchmark Stratejisi

Akademik makale için karşılaştırılacak baseline'ler:

```
Kategori 1 — Mevcut UniRide Algoritmaları:
  GA-Split, PSO-Split, GWO-Split, HHO-Split, OR-Tools, PyVRP

Kategori 2 — Başlangıç Heuristic'leri:
  Nearest Neighbor, Clarke-Wright Savings, Greedy Insertion

Kategori 3 — Basit Meta-heuristic'ler:
  Standard GA (no split), Standard PSO, Standard GWO

Kategori 4 — İyileştirilmiş SOTA Algoritmalar:
  E²BSO, R²DMA, P-AOEA

Sonuç formatı:
  "Algoritma karşılaştırma tablosu: Instance × Algoritma → Gap (%)"
  + Wilcoxon signed-rank test (istatistiksel anlamlılık)
  + Friedman test (birden fazla karşılaştırma)
  + Ortalama çalışma süresi karşılaştırması
```

### 7.4 Akademik Yayın Stratejisi

```
MAKALE 1 (Hızlı Sonuç — FAZ 1 sonrası):
  Başlık: "E²BSO: Entropy-Balanced Swarm Optimization with 
           Adaptive Large Neighborhood Search for CVRPTW"
  Konferans: GECCO 2026 veya WCCI 2026
  Katkı: Entropi + ALNS hibridizasyonu + Penalty relaxation
  Benzersizlik: İlk entropy-controlled ALNS uygulaması
  
MAKALE 2 (Ana Katkı — FAZ 2 sonrası):
  Başlık: "R²DMA: Resonance-Driven Memetic Algorithm with 
           Problem-Aware Operators for Vehicle Routing"
  Konferans: AAAI 2027 veya IJCAI 2027
  Katkı: Rezonans metriği + Shaw similarity + ALNS destructive mode
  Benzersizlik: Yapısal uyum ölçüsü (rezonans) + ALNS entegrasyonu
  
MAKALE 3 (En Yenilikçi — FAZ 3 sonrası, opsiyonel):
  Başlık: "P-AOEA: Production-Grade Adaptive Operator Evolution
           for Real-Time Vehicle Routing"
  Dergi: IEEE TEVC veya Computers & OR
  Katkı: Operator ko-evolüsyonu + 20+ atomic ops + Structured injection
  Benzersizlik: Meta-evrim + problem-aware operator discovery
```

---

> **Önceki Belge:** `06_Success_DNA_Analysis.md` — 10 Başarı DNA'sı Analizi
> **Sonraki Belge:** `08_Implementation_Progress.md` — Uygulama İlerleme Takibi (PLAN)
