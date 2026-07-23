# UniRide SOTA Framework Plan — ALNS Development Plan (2026)

> **Belge:** SOTA Framework Plan #2  
> **Tarih:** 2026-04  
> **Durum:** Draft — NOT YET IMPLEMENTED  
> **Öncelik:** 🔴 CRITICAL — Akademik makale için zorunlu  
> **Yazar:** UniRide Optimizer Team

---

## Bölüm 1: ALNS Nedir? (What is ALNS?)

**Adaptive Large Neighborhood Search (ALNS)**, CVRP ve varyantları için literatürdeki
en başarılı meta-sezgisel algoritmalardan biridir. Ropke & Pisinger (2006) tarafından
tanımlanmış ve o zamandan beri DIMACS challenge'ları kazanan solver'ların (PyVRP/HGS)
temelini oluşturmuştur.

### Temel Mantık

```
1. Başlangıç çözümü oluştur (ör: Clarke-Wright savings heuristic)
2. Döngü:
   a. Destroy: Mevcut çözümden q müşteriyi kaldır
   b. Repair: Kaldırılan müşterileri geri ekle
   c. Kabul Kriteri: Simulated Annealing ile kabul/reddet
   d. Adaptif Ağırlık Güncelleme
3. Sonuç: En iyi bulunan çözüm
```

### Mimari Diyagram

```
┌───────────────────────────────────────────────────────────┐
│                    ALNS FRAMEWORK                          │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              INITIAL SOLUTION                        │  │
│  │  Clarke-Wright / Nearest Neighbor / Random          │  │
│  └────────────────────┬────────────────────────────────┘  │
│                       │                                    │
│                       ▼                                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              DESTROY PHASE                           │  │
│  │                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │  │
│  │  │  Random  │ │  Worst   │ │ Related  │ │  Shaw  │ │  │
│  │  │ Removal  │ │ Removal  │ │ Removal  │ │Removal │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ │  │
│  └────────────────────┬────────────────────────────────┘  │
│                       │                                    │
│                       ▼                                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              REPAIR PHASE                            │  │
│  │                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │  Greedy  │ │ Regret-2 │ │ Regret-3 │            │  │
│  │  │Insertion │ │Insertion │ │Insertion │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘            │  │
│  └────────────────────┬────────────────────────────────┘  │
│                       │                                    │
│                       ▼                                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         ACCEPTANCE CRITERION                         │  │
│  │  Simulated Annealing: T(start) → T(end) cooling     │  │
│  │  ΔE < 0 → Kabul    |    ΔE ≥ 0 → exp(-ΔE/T) > r    │  │
│  └────────────────────┬────────────────────────────────┘  │
│                       │                                    │
│                       ▼                                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         ADAPTIVE WEIGHT UPDATE                       │  │
│  │  Segment-based: her ρ iterasyonda bir segment sonu  │  │
│  │  Başarılı destroy/repair → ağırlık artır            │  │
│  │  Başarısız → ağırlık azalt                         │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              LOCAL SEARCH (Post-processing)          │  │
│  │  2-opt, 3-opt, Or-opt → Mevcut Numba altyapısı     │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## Bölüm 2: Destroy Operatörleri (Kaldırma Stratejileri)

Destroy operatörleri, mevcut çözümden q müşteriyi kaldırarak bir "kısmi çözüm" oluşturur.

### 2.1 Random Removal

```
Algoritma:
  1. Rota çözümünden rastgele q müşteri seç
  2. Seçilen müşterileri rotalarından kaldır
  3. Kaldırılan: L = {c₁, c₂, ..., c_q}

Parametreler:
  - q: Kaldırılacak müşteri sayısı (genelde %10-40 arası)
  - q hesaplama: q = min(max_q, ceil(random(0.1, 0.4) × n_customers))
```

**Zaman karmaşıklığı:** O(q)  
**Kalite etkisi:** Düşük-Orta (exploration)

### 2.2 Worst Removal

```
Algoritma:
  1. Her müşteri için kaldırma maliyetini hesapla:
     cost(i) = dist(i-1, i+1) - dist(i-1, i) - dist(i, i+1)
  2. Maliyetleri büyükten küçüğe sırala
  3. En yüksek maliyetli q müşteriyi kaldır
  4. Rastgelelik: top-k arasından seç

Parametreler:
  - q: Kaldırılacak müşteri sayısı
  - p: Rastgelelik parametresi (degree of destruction)
  - Seçim: from top-q', q' = ceil(q × p)
```

**Zaman karmaşıklığı:** O(n × q)  
**Kalite etkisi:** Yüksek (en kötü pozisyonlardaki müşterileri hedefler)

### 2.3 Related Removal

```
Algoritma:
  1. Kaldırılacak ilk müşteriyi rastgele seç: c₀
  2. Diğer tüm müşterilerle ilişki skorunu hesapla:
     relatedness(c₀, cⱼ) = w₁ × dist(c₀, cⱼ)⁻¹ 
                           + w₂ × |demand(c₀) - demand(cⱼ)|⁻¹
                           + w₃ × [c₀ ve cⱼ aynı rotada mı?]
  3. En ilişkili müşteriyi kaldır ve listeye ekle
  4. q müşteri kaldırılana kadar tekrarla

Parametreler:
  - w₁, w₂, w₃: İlişki ağırlıkları
  - Rastgelelik: top-k arasından seçim
```

**Zaman karmaşıklığı:** O(n × q)  
**Kalite etkisi:** Yüksek (birbirine yakın müşterileri birlikte kaldırır)

### 2.4 Shaw Removal

```
Algoritma:
  1. Kaldırılacak ilk müşteriyi rastgele seç: c₀
  2. Shaw ilişki fonksiyonunu hesapla:
     R(c₀, cⱼ) = μ₁ × dist(c₀, cⱼ) 
                 + μ₂ × |arrival(c₀) - arrival(cⱼ)| 
                 + μ₃ × |demand(c₀) - demand(cⱼ)|
  3. R skoruna göre sırala (küçük → yakın/ilişkili)
  4. Rastgelelik: ilk r arasından seç
  5. q müşteri kaldırılana kadar tekrarla

Parametreler:
  - μ₁, μ₂, μ₃: Shaw ağırlıkları (normalize edilmiş)
  - r: Rastgelelik penceresi
```

**Zaman karmaşıklığı:** O(n × q)  
**Kalite etkisi:** Çok Yüksek (benzer özellikli müşterileri hedefler)

### Destroy Operatör Karşılaştırma Tablosu

| Operator | Karmaşıklık | Exploration | Intensification | En İyi Senaryo |
|----------|-------------|-------------|-----------------|----------------|
| Random | O(q) | ★★★★★ | ★☆☆☆☆ | Early iterations, diversification |
| Worst | O(n×q) | ★★☆☆☆ | ★★★★★ | Late iterations, intensification |
| Related | O(n×q) | ★★★☆☆ | ★★★★☆ | Geographic clustering |
| Shaw | O(n×q) | ★★★☆☆ | ★★★★★ | CVRPTW with time windows |

---

## Bölüm 3: Repair Operatörleri (Ekleme Stratejileri)

Repair operatörleri, kaldırılan müşterileri kısmi çözüme en iyi pozisyonlara geri ekler.

### 3.1 Greedy Insertion

```
Algoritma:
  1. Kaldırılan müşteriler listesi: L = {c₁, c₂, ..., c_q}
  2. Her cᵢ için en iyi ekleme pozisyonunu bul:
     best_cost = min over all routes r, all positions p:
       insertion_cost(r, p, cᵢ) = dist(r[p], cᵢ) + dist(cᵢ, r[p+1]) - dist(r[p], r[p+1])
  3. Minimum maliyetli (cᵢ*, r*, p*) ikilisini ekle
  4. q müşteri eklenene kadar tekrarla

Kapasite kontrolü:
  if route_demand[r*] + demand[cᵢ*] > capacity:
    skip route r* (rota ihlali varsa atla)
```

**Zaman karmaşıklığı:** O(q × n × V) — V = araç sayısı  
**Kalite etkisi:** Orta (tek seferde en iyiyi seçer, geleceği düşünmez)

### 3.2 Regret-2 Insertion

```
Algoritma:
  1. Her cᵢ için tüm rotalarda en iyi ve 2. en iyi ekleme maliyetini hesapla:
     best₁(cᵢ) = min insertion cost over all routes
     best₂(cᵢ) = 2nd min insertion cost over all routes
  2. Regret hesapla:
     regret(cᵢ) = best₂(cᵢ) - best₁(cᵢ)
  3. En yüksek regret değerine sahip cᵢ'yi seç
  4. cᵢ'yi best₁ pozisyonuna ekle
  5. q müşteri eklenene kadar tekrarla

Mantık:
  "Eğer şimdi eklemessen, ileride çok daha pahalı olacak" → öncelik ver
```

**Zaman karmaşıklığı:** O(q × n × V²)  
**Kalite etkisi:** Yüksek (regret-based, gelecekteki maliyetleri dikkate alır)

### 3.3 Regret-3 Insertion

```
Algoritma:
  1. Regret-2'nin genişletilmiş versiyonu
  2. regret(cᵢ) = Σᵢ₌₁³ wᵢ × bestᵢ - best₁
  
  regret₃(cᵢ) = w₂ × (best₂ - best₁) + w₃ × (best₃ - best₁)
  
  Genellikle: w₂ = 1.0, w₃ = 0.5 (literatür standardı)

  3. En yüksek regret₃ değerine sahip cᵢ'yi ekle
```

**Zaman karmaşıklığı:** O(q × n × V³)  
**Kalite etkisi:** Çok Yüksek (3 seviye regret analizi)

### Repair Operatör Karşılaştırma Tablosu

| Operator | Karmaşıklık | Hız | Kalite | En İyi Senaryo |
|----------|-------------|-----|--------|----------------|
| Greedy | O(q×n×V) | ★★★★★ | ★★★☆☆ | Hızlı iterasyonlar |
| Regret-2 | O(q×n×V²) | ★★★☆☆ | ★★★★☆ | Dengeli kalite/hız |
| Regret-3 | O(q×n×V³) | ★★☆☆☆ | ★★★★★ | Maksimum kalite |

---

## Bölüm 4: Adaptif Ağırlık Mekanizması

ALNS'in "adaptive" olması, destroy/repair operatörlerinin performansına göre
ağırlıklarının dinamik olarak güncellenmesinden kaynaklanır.

### Segment-Based Weight Update (Ropke & Pisinger, 2006)

```
Parametreler:
  - σ₁ = 33  (new global best)
  - σ₂ = 9   (new current solution)
  - σ₃ = 13  (accepted but not improving)
  - ρ = 100  (segment length in iterations)
  - r_w = 0.1 (reaction factor, weight decay)

Her ρ iterasyonda (segment sonu):
  for each operator (destroy d, repair r):
    score[d][r] = Σ rewards in this segment
    weight[d][r] = (1 - r_w) × weight[d][r] + r_w × (score[d][r] / uses[d][r])
    score[d][r] = 0  (reset)
    uses[d][r] = 0   (reset)

Her iterasyonda:
  1. Seçilen (d*, r*) operatör çiftini ağırlıklara göre seç
     (roulette wheel selection)
  2. Destroy → Repair uygula → yeni çözüm
  3. Kabul kriteri ile değerlendir
  4. Reward hesapla:
     if new_solution < best_ever:     reward = σ₁
     elif new_solution < current:     reward = σ₂
     elif accepted by SA:             reward = σ₃
     else:                            reward = 0
  5. score[d*][r*] += reward
  6. uses[d*][r*] += 1
```

### Simulated Annealing Kabul Kriteri

```
T₀ = start_temperature (genelde ilk çözümün maliyetinin %20-40'ı)
T_min = end_temperature
α = cooling_rate (genelde 0.995-0.9995)

Her iterasyonda:
  T = T × α

  ΔE = new_cost - current_cost
  
  if ΔE < 0:
    accept (daha iyi çözüm)
  else:
    p = exp(-ΔE / T)
    if random(0,1) < p:
      accept (daha kötü ama有机会)
    else:
      reject
```

---

## Bölüm 5: Geliştirme Fazları (Development Phases)

### Genel Takvim

```
Phase A: Core Framework       ████░░░░░░░░░░░░  Hafta 1-2
Phase B: Standard Operators   ░░░░████░░░░░░░░░  Hafta 2-3
Phase C: CVRP Operators       ░░░░░░░░████░░░░░░  Hafta 3-4
Phase D: Adaptive Mechanism   ░░░░░░░░░░░░████░░  Hafta 4-5
Phase E: Integration          ░░░░░░░░░░░░░░░░████ Hafta 5-6
```

### Phase A: Core ALNS Framework (Hafta 1-2)

**Hedef:** ALNS çekirdek yapısını oluştur, destroy/repair base class'larını tanımla.

```
optimizer_api/strategies/alns/
├── __init__.py
├── alns_solver.py           # Ana ALNS solver sınıfı
├── base_destroy.py          # DestroyOperator abstract base
├── base_repair.py           # RepairOperator abstract base
├── acceptance_criterion.py  # Simulated Annealing
├── adaptive_weights.py      # Segment-based weight update
├── solution.py              # ALNS Solution wrapper
└── config.py                # ALNS hyperparameters
```

**Temel Sınıflar:**

```python
# base_destroy.py
class DestroyOperator(ABC):
    """Abstract base for destroy operators"""
    
    @abstractmethod
    def destroy(self, solution: ALNSSolution, q: int, rng: Random) -> RemovedCustomers:
        """
        Remove q customers from solution.
        
        Args:
            solution: Current ALNS solution
            q: Number of customers to remove
            rng: Random number generator (seed control)
            
        Returns:
            RemovedCustomers with customer list and original routes
        """
        pass


# base_repair.py
class RepairOperator(ABC):
    """Abstract base for repair operators"""
    
    @abstractmethod
    def repair(self, solution: ALNSSolution, removed: RemovedCustomers, 
               rng: Random) -> ALNSSolution:
        """
        Insert removed customers back into solution.
        
        Args:
            solution: Partial solution after destroy
            removed: Customers that were removed
            rng: Random number generator
            
        Returns:
            Complete ALNS solution
        """
        pass


# alns_solver.py
class ALNSSolver:
    """Main ALNS solver"""
    
    def __init__(self, config: ALNSConfig):
        self.destroy_operators: List[DestroyOperator] = []
        self.repair_operators: List[RepairOperator] = []
        self.acceptance = SimulatedAnnealing(config.sa_params)
        self.weights = AdaptiveWeightManager(config.adaptive_params)
        self.best_solution: Optional[ALNSSolution] = None
        
    def add_destroy(self, operator: DestroyOperator, weight: float = 1.0):
        ...
    
    def add_repair(self, operator: RepairOperator, weight: float = 1.0):
        ...
    
    def solve(self, initial_solution: ALNSSolution, 
              max_iterations: int, seed: int = 42) -> ALNSSolution:
        ...
```

**Milestone:** Framework compile ediyor, boş destroy/repair ile çalışıyor.

### Phase B: Standard Operators (Hafta 2-3)

**Hedef:** 4 destroy + 3 repair operatörünü uygula.

```
optimizer_api/strategies/alns/
├── destroy/
│   ├── __init__.py
│   ├── random_removal.py      # Phase B
│   ├── worst_removal.py       # Phase B
│   ├── related_removal.py     # Phase B
│   └── shaw_removal.py        # Phase B
└── repair/
    ├── __init__.py
    ├── greedy_insertion.py    # Phase B
    ├── regret2_insertion.py   # Phase B
    └── regret3_insertion.py   # Phase B
```

**Operatör Detayları:**

| Dosya | Sınıf | Base Class | Açıklama |
|-------|-------|------------|----------|
| `random_removal.py` | `RandomRemoval` | `DestroyOperator` | Rastgele q müşteri kaldır |
| `worst_removal.py` | `WorstRemoval` | `DestroyOperator` | En yüksek maliyetli q müşteriyi kaldır |
| `related_removal.py` | `RelatedRemoval` | `DestroyOperator` | Yakın ilişkili müşterileri kaldır |
| `shaw_removal.py` | `ShawRemoval` | `DestroyOperator` | Shaw benzerlik ile kaldır |
| `greedy_insertion.py` | `GreedyInsertion` | `RepairOperator` | Greedy en iyi pozisyona ekle |
| `regret2_insertion.py` | `Regret2Insertion` | `RepairOperator` | Regret-2 based insertion |
| `regret3_insertion.py` | `Regret3Insertion` | `RepairOperator` | Regret-3 based insertion |

**Milestone:** 7 operatör TSPLIB problemlerinde çalışıyor, GAP hesaplanabiliyor.

### Phase C: CVRP-Specific Operators (Hafta 3-4)

**Hedef:** UniRide'nin CVRPTW özel durumlarını destekleyen operatörler.

```
optimizer_api/strategies/alns/
├── destroy/
│   ├── capacity_aware_removal.py    # Phase C - NEW
│   ├── time_window_removal.py       # Phase C - NEW
│   └── route_based_removal.py       # Phase C - NEW
└── repair/
    ├── time_window_insertion.py     # Phase C - NEW
    └── capacity_penalty_insertion.py # Phase C - NEW
```

**CVRP-Special Operatörler:**

| Operator | Açıklama | Amaç |
|----------|----------|------|
| Capacity Aware Removal | Kapasite ihlali olan rotalardan öncelikli kaldırma | CVRP feasible çözüm |
| Time Window Removal | Time window kısıtı olan müşterileri hedefleme | CVRPTW |
| Route-Based Removal | Tüm bir rotayı kaldırma | Yoğun rotaları yeniden yapılandırma |
| TW Insertion | Time window uygunluğunu kontrol eden insertion | CVRPTW |
| Capacity Penalty Insertion | Kapasite cezası ile esnek insertion | Geçici infeasible çözümlere izin |

**Milestone:** CVRP ve CVRPTW problemlerinde feasible çözümler bulunabiliyor.

### Phase D: Adaptive Mechanism (Hafta 4-5)

**Hedef:** Segment-based adaptif ağırlık mekanizmasını uygula.

```
optimizer_api/strategies/alns/
├── adaptive_weights.py      # Phase D - TAM
├── acceptance_criterion.py  # Phase D - TAM (SA ile genişlet)
└── operators_stats.py       # Phase D - NEW (operator performans takibi)
```

**AdaptiveWeightManager API:**

```python
class AdaptiveWeightManager:
    def __init__(self, params: AdaptiveParams):
        self.weights: Dict[Tuple[str,str], float] = {}  # (destroy, repair) → weight
        self.scores: Dict[Tuple[str,str], float] = {}
        self.uses: Dict[Tuple[str,str], int] = {}
        self.segment_count = 0
        self.segment_size = params.segment_size  # ρ = 100
        self.reaction_factor = params.reaction_factor  # r_w = 0.1
        self.reward_params = params.rewards  # σ₁=33, σ₂=9, σ₃=13
    
    def select_operators(self, rng: Random) -> Tuple[str, str]:
        """Roulette wheel selection based on weights"""
        ...
    
    def update_score(self, destroy_name: str, repair_name: str, reward: float):
        """Add reward to current segment score"""
        ...
    
    def end_segment(self):
        """Update weights based on segment performance"""
        ...
    
    def get_stats(self) -> Dict:
        """Return operator usage statistics for analysis"""
        ...
```

**SimulatedAnnealing API:**

```python
class SimulatedAnnealing:
    def __init__(self, start_temp: float, end_temp: float, cooling_rate: float):
        self.T = start_temp
        self.T_min = end_temp
        self.alpha = cooling_rate
    
    def accept(self, current_cost: float, new_cost: float, 
               best_cost: float, rng: Random) -> AcceptResult:
        """
        Decide whether to accept new solution.
        Returns AcceptResult with: accepted, improved, new_best
        """
        ...
    
    def cool(self):
        """Apply cooling: T = T × α"""
        ...
```

**Milestone:** Adaptif ağırlıklar operator performansını takip ediyor ve geliştiriyor.

### Phase E: Integration (Hafta 5-6)

**Hedef:** ALNS'yi mevcut benchmark sistemine entegre et.

#### E.1: Strategy Registry Entegrasyonu

```python
# strategies/__init__.py'ye eklenecek:
from strategies.alns import ALNSSolver, ALNSStrategy

_alns_strategy = ALNSStrategy()

STRATEGY_REGISTRY["alns"] = _alns_strategy
STRATEGY_REGISTRY["adaptive_large_neighborhood_search"] = _alns_strategy
```

#### E.2: BenchmarkRunner Entegrasyonu

```python
# benchmark_runner.py'de:
# ALNS, normal bir strategy olarak çağrılır
# _benchmark_problem_to_optimization_request() zaten mevcut
# ALNSStrategy.optimize(OptimizationRequest) → OptimizationResponse
```

#### E.3: CLI Benchmark Entegrasyonu

```python
# run_interactive_benchmark_v2_numba.py'ye eklenecek:
ALNS_STRATEGIES = [
    ("ALNS-Greedy", LocalSearchType.NONE, ALNSRepairType.GREEDY),
    ("ALNS-Regret2", LocalSearchType.NONE, ALNSRepairType.REGRET2),
    ("ALNS-Regret3", LocalSearchType.NONE, ALNSRepairType.REGRET3),
    ("ALNS-Hybrid", LocalSearchType.HYBRID, ALNSRepairType.REGRET2),
]
```

#### E.4: Import Bridge Entegrasyonu

```
/api/benchmark/run  → ALNS'yi strategy olarak destekler
/api/benchmark/status → ALNS iterasyon progress gösterir
Web UI              → ALNS sonuçlarını karşılaştırma tablosunda gösterir
```

**Milestone:** ALNS hem CLI hem Web benchmark'ta çalışıyor, sonuçlar karşılaştırılabilir.

---

## Bölüm 6: Mevcut Durum (Current Status)

### Implementation Status

```
ALNS FRAMEWORK DEVELOPMENT PROGRESS

Phase A: Core Framework                    ░░░░░░░░░░░░░░░░░░░░   0%
├── alns_solver.py                         ❌ NOT STARTED
├── base_destroy.py                        ❌ NOT STARTED
├── base_repair.py                         ❌ NOT STARTED
├── acceptance_criterion.py                ❌ NOT STARTED
├── adaptive_weights.py                    ❌ NOT STARTED
├── solution.py                            ❌ NOT STARTED
└── config.py                              ❌ NOT STARTED

Phase B: Standard Operators                ░░░░░░░░░░░░░░░░░░░░   0%
├── random_removal.py                      ❌ NOT STARTED
├── worst_removal.py                       ❌ NOT STARTED
├── related_removal.py                     ❌ NOT STARTED
├── shaw_removal.py                        ❌ NOT STARTED
├── greedy_insertion.py                    ❌ NOT STARTED
├── regret2_insertion.py                   ❌ NOT STARTED
└── regret3_insertion.py                   ❌ NOT STARTED

Phase C: CVRP Operators                    ░░░░░░░░░░░░░░░░░░░░   0%
├── capacity_aware_removal.py              ❌ NOT STARTED
├── time_window_removal.py                 ❌ NOT STARTED
├── time_window_insertion.py               ❌ NOT STARTED
└── capacity_penalty_insertion.py          ❌ NOT STARTED

Phase D: Adaptive Mechanism                ░░░░░░░░░░░░░░░░░░░░   0%
└── operators_stats.py                     ❌ NOT STARTED

Phase E: Integration                       ░░░░░░░░░░░░░░░░░░░░   0%
├── Strategy Registry                      ❌ NOT STARTED
├── BenchmarkRunner                        ❌ NOT STARTED
├── CLI Benchmark                          ❌ NOT STARTED
└── Web UI                                 ❌ NOT STARTED

SUPPORTED BY EXISTING CODE                ████████████████████ 100%
├── Local Search (Numba)                   ✅ REUSE for post-processing
├── TSPLIB Parser                          ✅ REUSE for distance computation
├── Benchmark Infrastructure               ✅ REUSE for evaluation
└── Strategy Base Class                    ✅ EXTEND for ALNS strategy
```

### Technical Debt Assessment

| Madde | Etki | Aciliyet |
|-------|------|----------|
| ALNS hiç yok | Akademik makale imkansız | 🔴 CRITICAL |
| Adaptif mekanizma yok | Performans düşük | 🔴 HIGH |
| Destroy/Repair yok | ALNS çalışmaz | 🔴 CRITICAL |
| CVRPTW desteği yok | UniRide use case kaybedilir | 🟡 MEDIUM |

---

## Bölüm 7: ALNS Konfigürasyon Parametreleri

### Varsayılan Hyperparameters (Literatür-Based)

```python
@dataclass
class ALNSConfig:
    # --- General ---
    max_iterations: int = 25000
    seed: int = 42
    
    # --- Destroy ---
    min_removal: float = 0.10    # Min %10 müşteri kaldır
    max_removal: float = 0.40    # Max %40 müşteri kaldır
    
    # --- Simulated Annealing ---
    start_temperature: float = 0.4   # İlk çözüm maliyetinin %40'ı
    end_temperature: float = 0.001
    cooling_rate: float = 0.9995
    
    # --- Adaptive Weights ---
    segment_size: int = 100      # ρ = 100 iterasyon
    reaction_factor: float = 0.1  # r_w = 0.1
    reward_new_best: int = 33    # σ₁
    reward_improved: int = 9     # σ₂
    reward_accepted: int = 13    # σ₃
    
    # --- Post-Processing ---
    use_local_search: bool = True
    local_search_type: str = "hybrid"  # Mevcut Numba Hybrid
    
    # --- Time Limit ---
    max_time_seconds: float = 30.0  # Benchmark standard
```

---

## Bölüm 8: Referanslar

### Literatür

1. **Ropke, S., & Pisinger, D. (2006).** "An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows." *Transportation Science*, 40(4), 455-472.

2. **Pisinger, D., & Ropke, S. (2007).** "A general heuristic for vehicle routing problems." *Computers & Operations Research*, 34(8), 2403-2435.

3. **Shaw, P. (1998).** "Using constraint programming and local search methods to solve vehicle routing problems." *CP-98*, 417-431.

4. **Vidal, T., et al. (2012).** "A hybrid genetic algorithm with adaptive diversity management for a large class of vehicle routing problems with time-windows." *Computers & Operations Research*, 39(9), 2114-2128. (PyVRP HGS temeli)

5. **Drexl, M. (2012).** "Rich vehicle routing in theory and practice." *Logistics Research*, 5(1-2), 47-63.

### SOTA Solver Referansları

- **PyVRP:** https://pyvrp.org/ — DIMACS 2021 CVRP Challenge kazananı (HGS)
- **OR-Tools:** https://developers.google.com/optimization/ — Google Operations Research
- **VROOM:** https://github.com/VROOM-Project/vroom — Open-source routing engine

### Mevcut UniRide Kod Referansları

- `strategies/__init__.py` — Strategy Registry (15+ algoritma)
- `strategies/base_strategy.py` — BaseRoutingStrategy
- `strategies/hybrid_base_strategy.py` — Hybrid base class
- `utils/local_search_numba.py` — Numba JIT local search engine
- `utils/tsplib_parser.py` — TSPLIB EUC_2D distance
- `benchmark_runner.py` — Web benchmark runner
- `tests/run_smart_benchmark_numba.py` — CLI smart benchmark
- `tests/run_interactive_benchmark_v2_numba.py` — CLI interactive benchmark

---

## Bölüm 9: Sonraki Adımlar (Next Actions)

| # | Aksiyon | Sahip | Hedef Tarih |
|---|---------|-------|-------------|
| 1 | Phase A: Core ALNS framework oluştur | Developer | Hafta 2 |
| 2 | Phase B: 7 standart operatörü uygula | Developer | Hafta 3 |
| 3 | Phase B test: TSPLIB berlin52 ile validation | QA | Hafta 3 |
| 4 | Phase C: CVRP-specific operatörler | Developer | Hafta 4 |
| 5 | Phase D: Adaptif mekanizma | Developer | Hafta 5 |
| 6 | Phase E: Strategy Registry entegrasyonu | Developer | Hafta 5 |
| 7 | Phase E test: CLI benchmark entegrasyonu | QA | Hafta 6 |
| 8 | Phase E test: Web benchmark entegrasyonu | QA | Hafta 6 |
| 9 | Performance comparison: ALNS vs OR-Tools vs PyVRP | Researcher | Hafta 7 |
| 10 | Makale benchmark pipeline setup | Researcher | Hafta 8 |

---

> **Önceki Belge:** `01_SOTA_Architecture_Vision.md` — Dual-track mimari vizyon
