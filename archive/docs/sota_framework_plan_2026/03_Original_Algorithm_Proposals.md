# UniRide SOTA Framework — Orijinal Algoritma Önerileri

> **Tarih**: 2026-04-13 (Güncelleme: 2026-04-13 — 14 ek aday eklendi)
> **Durum**: Tasarım Aşaması (Design Phase)  
> **Hedef**: TSP ve CVRPTW için literatürde olmayan, yüksek performans potansiyeline sahip algoritmalar
> **Kapsam**: 3 orijinal + 14 aday = 17 algoritma profili  

---

## İçindekiler

1. [Mevcut Algoritma Portföyü Analizi](#1-mevcut-algoritma-portföyü-analizi)
2. [Literatür Boşlukları ve Fırsatlar](#2-literatür-boşlukları-ve-fırsatlar)
3. [Algoritma 1: RDMA — Resonance-Driven Memetic Algorithm](#3-algoritma-1-rdma--resonance-driven-memetic-algorithm)
4. [Algoritma 2: AOEA — Adaptive Operator Evolution Algorithm](#4-algoritma-2-aoea--adaptive-operator-evolution-algorithm)
5. [Algoritma 3: EBSO — Entropy-Balanced Swarm Optimization](#5-algoritma-3-ebso--entropy-balanced-swarm-optimization)
6. [Karşılaştırma Analizi](#6-karşılaştırma-analizi)
7. [Entegrasyon Planı](#7-entegrasyon-planı)
8. [Akademik Yayın Stratejisi](#8-akademik-yayın-stratejisi)
9. [14 Ek Aday Algoritma → Ayrı Dosya](04_Extended_Algorithm_Candidates.md) *(QASI, QAIMA, CGW2O, NEMA, ABCH, NGCO, GBCH, HOOP, EFO, HMFO, SEC, SACO, FDO, CARE)*
10. [Ağırlıklı Puanlama Matrisi](05_Algorithm_Scoring_Matrix.md) *(17 algoritmanın 9 kriter üzerinden sıralaması)*

---

## 1. Mevcut Algoritma Portföyü Analizi

### 1.1 Mevcut 16+ Algoritma

| Pipeline | Algoritma | Tür | TSP | CVRP | CVRPTW |
|----------|-----------|-----|-----|------|--------|
| **A** | GA, PSO, GWO, HHO | Meta-heuristic | ✅ | ⚠️ (cluster-first) | ❌ |
| **B** | GA-Split, PSO-Split, GWO-Split, HHO-Split | Meta-heuristic+Split | ✅ | ✅ | ⚠️ (TW only at decode) |
| **Holistic** | OR-Tools, PyVRP, VROOM | Exact/Solver | ✅ | ✅ | ✅ |
| **Heuristic** | Greedy, 2-Opt, Permutation | Heuristic/Exact | ✅ | ❌ | ❌ |

### 1.2 Kritik Eksikler (Gaps)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEVCUT PORTFÖY BOŞLUKLARI                     │
├─────────────────────────────────────────────────────────────────┤
│ 1. ALNS (Adaptive Large Neighborhood Search) — YOK             │
│ 2. Simulated Annealing (bağımsız) — YOK                       │
│ 3. Tabu Search — YOK                                           │
│ 4. Ant Colony Optimization — YOK                               │
│ 5. Variable Neighborhood Search — YOK                          │
│ 6. Iterated Local Search — YOK                                 │
│ 7. CVRPTW-aware evrim (sadece decode aşamasında) — KISITLI     │
│ 8. Adaptif parametre kontrolü — YOK                            │
│ 9. Çok-amaçlı optimizasyon — YOK                               │
│ 10. Popülasyon çeşitlilik yönetimi — KISITLI                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Tasarım İlkeleri

Her önerilen algoritma şu kriterleri karşılamalıdır:

1. **BaseRoutingStrategy uyumlu** — Mevcut optimize() arayüzüne uymalı
2. **TSP + CVRPTW çift destek** — Her iki problem tipini de çözebilmeli
3. **Split Decoder entegrasyonu** — Pipeline B ile uyumlu olmalı
4. **Numba JIT uyumlu** — Sıcak noktalar JIT ile hızlandırılabilir olmalı
5. **Orijinallik** — Literatürde doğrudan karşılığı olmalı
6. **Pratik başarı** — Teorik novadan ziyade gerçek benchmark sonuçları üretmeli

---

## 2. Literatür Boşlukları ve Fırsatlar

### 2.1 2022-2026 SOTA Trendleri

```
Trend                    │ Güç                            │ Boşluk
─────────────────────────┼────────────────────────────────┼──────────────────────
NCO (Neural CO)          │ GCRL-TSP, Poppy, BOPO          │ Yüksek GPU gereksinimi
LLM Algorithm Discovery  │ VRPAgent                       │ Black-box, kontrol zor
Quantum-Inspired         │ HQTS                           │ CVRPTW'de test edilmemiş
GPU Paralel              │ NVIDIA cuOpt                   │ Özel donanım gerekli
Preference Optimization  │ BOPO (ICML'25)                 │ Sadece construction phase
Physics-Inspired         │ EMLA, FSA                      │ Continuous -> discrete zor
```

### 2.2 Keşfedilmemiş Hibritizasyon Fırsatları

| Fırsat | Açıklama | Potansiyel |
|--------|----------|------------|
| **Rezonans + Memetic** | Fiziksel rezonans kavramı + memetik algoritma | 🔴 Yüksek |
| **Operator Evrimi** | Operatörlerin kendi başlarına evrilmesi | 🔴 Yüksek |
| **Entropi-bazlı kontrol** | Shannon entropisi ile adaptif çeşitlilik | 🟡 Orta-Yüksek |
| **Quantum + CVRPTW** | Kuantum tünelleme + time window | 🟡 Orta |
| **Market ekonomisi** | Arz-talep dengesi + routing | 🟡 Orta |

### 2.3 Neden Bu 3 Algoritma?

```
                    Orijinallik
                         ▲
                         │
              EBSO ●     │     ● AOEA
                         │
                         │
              RDMA ●     │
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    └────────────────────┼────────────────────┘
                         │
              Düşük ◄────┴────► Yüksek
                    Uygulanabilirlik
```

- **RDMA**: En dengeli — hem orijinal hem pratik
- **AOEA**: En yüksek novada — meta-evolüsyon kavramı tamamen yeni
- **EBSO**: En kontrol edilebilir — entropi matematiksel olarak rigor

---

## 3. Algoritma 1: RDMA — Resonance-Driven Memetic Algorithm

### 3.1 Konsept ve İlham

**İlham Kaynakları**: 
- Akustik rezonans (sympathetic vibration — iki uyumlu çatal aynı frekansta titreşir)
- Fizikte dalga interferansı (constructive + destructive)
- Carniege Mellon "Harmony Search" (Geem 2001) — ancak RDMA bunun **geometrik versiyonu**

**Temel Fikir**: Standart GA'da herhangi iki ebeveyn çaprazlanır. RDMA'da ise **sadece "rezonans" uyumuna sahip çözümler** birleştirilir. Rezonans, iki çözümün yapısal uyumunu ölçen yeni bir metriktir.

### 3.2 Çığır Açan Novada: Rezonans Metriği

#### Standart Yaklaşımlar vs RDMA

```
STANDART GA:
  Parent1: [A, B, C, D, E, F]    fitness: 450
  Parent2: [D, C, B, A, F, E]    fitness: 480
  → Rastgele OX crossover → Child
  
RDMA:
  Parent1: [A, B, C, D, E, F]    fitness: 450    rezonans_id: R1
  Parent2: [A, C, E, D, B, F]    fitness: 470    rezonans_id: R2
  
  Rezonans Analizi:
  ├─ Ortak kenar (A→B): ✓ (hem P1 hem P2'de var)
  ├─ Ortak kenar (D→E): ✓ 
  ├─ Ters kenar (B→C vs C→B): ✗ (çelişkili yön)
  ├─ Ortak alt-tur (A,B,C): similarity=0.75
  └─ REZONANS SKORU: 0.72 → YÜKSEK → BİRLEŞTİR!
  
  Parent3: [F, E, D, C, B, A]    fitness: 520    rezonans_id: R3
  
  Rezonans Analizi (P1 vs P3):
  ├─ Ortak kenar: 0
  ├─ Ters kenar: tümü çelişkili
  └─ REZONANS SKORU: 0.08 → DÜŞÜK → BİRLEŞTİRME!
```

#### Rezonans Skoru Formülü

```
R(P1, P2) = w1·E_common(P1,P2)/E_total + w2·S_sub(P1,P2) + w3·H_comp(P1,P2)

Burada:
  E_common = Ortak kenar sayısı (aynı yönde)
  E_total  = Toplam kenar sayısı
  S_sub    = En büyük ortak alt-tur benzerliği (LCS-based)
  H_comp   = Hamiltoniyen tamamlanabilirlik — P1+P2 birleştirilirse
             geçerli bir tur oluşturabilir mi? (Uzaysal uyum)
  
  w1 = 0.4, w2 = 0.3, w3 = 0.3 (adaptif ağırlıklar)
```

### 3.3 Algoritma Mimarisi

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RDMA AKIŞ DİYAGRAMI                         │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐     │
│  │ Başlangıç│───▶│ Popülasyon   │───▶│ Rezonans Matrisi Oluştur│     │
│  │ (NN+Rand)│    │ P = {S1..Sn} │    │ R[i][j] = rezonans(Si,Sj)│   │
│  └──────────┘    └──────────────┘    └───────────┬───────────┘     │
│                                                  │                  │
│                                                  ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  ANA DÖNGÜ (t = 1..T_max)                    │   │
│  │                                                              │   │
│  │  ┌─────────────────┐    ┌────────────────────────────┐      │   │
│  │  │ 1. REZONANS EŞLEŞT│───▶│ 2. INTERFERANS TABANLI     │      │   │
│  │  │    R ≥ θ_esik →  │    │    ÇAPRAZLAMA (Crossover)   │      │   │
│  │  │    Eşleş!        │    │    Constructive: Yüksek R   │      │   │
│  │  └─────────────────┘    │    Mutated: Düşük R (noise)  │      │   │
│  │                          └─────────────┬──────────────┘      │   │
│  │                                        │                      │   │
│  │                                        ▼                      │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ 3. DISSONANS FİLTRESİ (Destructive Interference)    │    │   │
│  │  │    Child'ın fitness'i < min(P1.f, P2.f) - δ         │    │   │
│  │  │    → Dissonance tespit → Child REDDET                 │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                        │                      │   │
│  │                                        ▼                      │   │
│  │  ┌─────────────────┐    ┌────────────────────────────┐      │   │
│  │  │ 4. LOKAL ARAMA   │───▶│ 5. REZONANS FREKANS GÜNCELLE│    │   │
│  │  │    (2-Opt, 3-Opt)│    │    Başarılı child → artır  │      │   │
│  │  │    Sadece en iyi │    │    Başarısız child → azalt  │      │   │
│  │  │    N çözüme uygula│    │    Adaptif θ_esik güncelle │      │   │
│  │  └─────────────────┘    └────────────────────────────┘      │   │
│  │                                        │                      │   │
│  │                                        ▼                      │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ 6. HARMONIC CONVERGENCE CHECK                        │    │   │
│  │  │    Popülasyon entropisi < ε → HARMONIC PULSE        │    │   │
│  │  │    (Yapılandırılmış çeşitlilik enjeksiyonu)          │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  SONUÇ: En iyi çözüm + Rezonans haritası                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 Rezonans Tabanlı Çaprazlama (Resonance Crossover)

Bu, RDMA'nın en orijinal operatörüdür. Standart crossover'ın yerine geçer:

```python
def resonance_crossover(parent1: Tour, parent2: Tour, resonance: float) -> Tour:
    """
    Rezonans skoruna göre adaptif çaprazlama:
    - Yüksek rezonans (R > 0.7): Ortak kenarları KORU, araları doldur
    - Orta rezonans (0.3 < R < 0.7): Standart OX + rezonans bias
    - Düşük rezonans (R < 0.3): Destructive crossover → noise ekle
    """
    common_edges = extract_common_edges(parent1, parent2)
    
    if resonance > 0.7:
        # CONSTRUCTIVE INTERFERENCE MODE
        # Ortak kenarları "iskelet" olarak kullan
        skeleton = build_skeleton_from_common_edges(common_edges)
        # Boşlukları nearest-neighbor ile doldur (rezonans-guided)
        child = guided_completion(skeleton, parent1, parent2)
        
    elif resonance > 0.3:
        # MODERATE MODE — OX with resonance bias
        child = order_crossover(parent1, parent2)
        # Yüksek-rezonans kenarları tercih et
        child = resonance_biased_repair(child, common_edges)
        
    else:
        # DESTRUCTIVE INTERFERENCE MODE — Exploration
        child = scramble_mutation(parent1 if random() < 0.5 else parent2)
        # Rastgele inversion + swap ile çeşitlilik yarat
        for _ in range(int(3 * (1 - resonance))):
            child = random_two_opt(child)
    
    return child
```

### 3.5 Harmonic Pulse — Çeşitlilik Enjeksiyonu

Standart rastgele restart yerine **yapılandırılmış** çeşitlilik enjeksiyonu:

```python
def harmonic_pulse(population: List[Tour], resonance_matrix: np.ndarray):
    """
    Popülasyon çok yakınsadığında (düşük entropi) tetiklenir.
    Amaç: Rastgele değil, "rezonans havzalarını" hedefleyen çeşitlilik.
    """
    # 1. Rezonans matrisinden "clusters" çıkar
    clusters = spectral_clustering(resonance_matrix, n_clusters=3)
    
    # 2. Her cluster'dan en iyi çözümü koru (cluster center)
    survivors = [best_in_cluster(c) for c in clusters]
    
    # 3. Cluster'lar arası "interference" child'lar üret
    for i in range(len(clusters)):
        for j in range(i+1, len(clusters)):
            c1 = random_from(clusters[i])
            c2 = random_from(clusters[j])
            R = compute_resonance(c1, c2)
            # Farklı cluster'lar → düşük rezonans → exploratif çocuk
            child = resonance_crossover(c1, c2, R)
            survivors.append(child)
    
    # 4. NN heuristic ile taze çözümler ekle
    for _ in range(population_size // 4):
        survivors.append(nearest_neighbor_tour(random_depot_permutation()))
    
    return survivors[:population_size]
```

### 3.6 CVRPTW Uyarlama

```
TSP Modu:
  - Giant tour optimizasyonu (tek tur)
  - Rezonans: Kenar benzerliği + sıra benzerliği
  - Lokal arama: 2-Opt, 3-Opt, Or-Opt

CVRPTW Modu (Split entegrasyonlu):
  - Giant tour optimizasyonu → Split Decoder ile araç rotalarına bölme
  - Rezonans hesaplamada EK BOYUT:
    R_cvrp(P1,P2) = R_tsp(P1,P2) + w_tw · TW_resonance(P1,P2) + w_cap · CAP_resonance(P1,P2)
    
    TW_resonance: İki çözümün time window satisfication pattern'ı ne kadar benzer?
    CAP_resonance: Kapasite kullanım profilleri ne kadar uyumlu?
    
  - Split decode sonrası CVRPTW fizibilite kontrolü
  - Time window violation'ları rezonans skoru üzerinde ceza uygular
```

### 3.7 Sözde Kod (Pseudocode)

```
ALGORITHM RDMA(problem, params):
  
  // --- BAŞLANGIÇ ---
  P ← InitializePopulation(problem, params.pop_size)
  S_best ← Best(P)
  
  // --- REZONANS MATRİSİ ---
  R ← ComputeResonanceMatrix(P)  // O(n²) ama cache'lenir
  
  FOR t = 1 TO T_max:
    
    // --- 1. REZONANS EŞLEŞTİRME ---
    θ ← AdaptiveThreshold(R, params.θ_base)
    Pairs ← []
    FOR each Si ∈ P (shuffled):
      Sj ← ResonantPartner(Si, P, R, θ)
      IF Sj ≠ NULL:
        Pairs.add((Si, Sj, R[Si][Sj]))
    
    // --- 2. INTERFERANS ÇAPRAZLAMASI ---
    Children ← []
    FOR (Si, Sj, r) IN Pairs:
      Ck ← ResonanceCrossover(Si, Sj, r)
      
      // --- 3. DISSONANS FİLTRESİ ---
      IF Fitness(Ck) < min(Fitness(Si), Fitness(Sj)) - δ:
        CONTINUE  // Destructive interference → reddet
      
      // --- 4. LOKAL ARAMA (seçici) ---
      IF ShouldApplyLS(r, t):
        Ck ← LocalSearch(Ck, SelectOperators(r))
      
      Children.add(Ck)
    
    // --- 5. SEÇİM ---
    P ← Select(P ∪ Children, params.pop_size)
    
    // --- 6. REZONANS GÜNCELLEME ---
    R ← IncrementalUpdate(R, P, Children)
    
    // --- 7. HARMONIC CONVERGENCE CHECK ---
    IF Entropy(P) < ε_harmonic:
      P ← HarmonicPulse(P, R)
      R ← RecomputeResonanceMatrix(P)
    
    // --- 8. EN İYİ GÜNCELLEME ---
    S_best ← min(S_best, Best(P))
  
  // --- SONUÇ ---
  IF problem.type == "cvrptw":
    RETURN SplitDecode(S_best, problem.constraints)
  ELSE:
    RETURN S_best
```

### 3.8 Karmaşıklık Analizi

| Bileşen | Karmaşıklık | Not |
|---------|-------------|-----|
| Rezonans Matrisi | O(n² · d) | d = boyut (TSP:1, CVRPTW:3) |
| Eşleştirme | O(n · log n) | Sorting-based partner selection |
| Çaprazlama | O(n) | Linear pass (constructive mode) |
| Lokal Arama | O(n²) | Per-child 2-opt |
| Toplam (iterasyon) | O(n² · d + n · log n + n²) | ≈ O(n² · d) |
| Incremental Update | O(n · k) | k = yeni child sayısı |

### 3.9 RDMA'nın Avantajları

1. **Verimli crossover**: Sadece uyumlu çözümler birleşir → gereksiz değerlendirme azalır
2. **Adaptif eşik**: θ_esik zamanla güncellenir → erken exploitaşon, geç exploration
3. **Yapılandırılmış çeşitlilik**: Harmonic Pulse rastgele restart'tan daha bilinçli
4. **CVRPTW doğal uzantı**: Rezonans metriği çok-boyutlu (kenar + TW + kapasite)
5. **Matematiksel temel**: Dalga interferansı analojisinde constructive/destructive ayrımı

---

## 4. Algoritma 2: AOEA — Adaptive Operator Evolution Algorithm

### 4.1 Konsept ve İlham

**İlham Kaynakları**:
- Genetic Programming (Koza 1992) — programları evriltme
- VRPAgent (ICLR 2025) — LLM ile operator keşfi
- Hyper-heuristics — algoritma seçimi/otomasyonu
- Biological evolution — doğal seçilimin kendisi de evrilir

**Temel Fikir**: Standart ALNS'de destroy/repair operatörleri **sabit** ve insan-tasarımlıdır. AOEA'da operatörlerin kendileri bir **genom** olarak temsil edilir ve çözümlerle birlikte **ko-evrilir**. Yani algoritma, problemin hangi operatörlere ihtiyaç duyduğunu **öğrenir**.

### 4.2 Çığır Açan Novada: Operator Genome

#### Standart ALNS vs AOEA

```
STANDART ALNS:
  Destroy Operatörleri (SABİT):
  ├─ Random Removal
  ├─ Worst Removal  
  ├─ Related Removal
  └─ Shaw Removal
  
  Repair Operatörleri (SABİT):
  ├─ Greedy Insertion
  ├─ Regret-2 Insertion
  └─ Regret-3 Insertion
  
  → İnsan tasarladı, sabit kodlanmış

AOEA:
  Operator Popülasyonu (EVRİLEN):
  ├─ Genome_1: [random_remove(0.3), worst_remove(0.4), related_remove(0.3)]
  │            → repair: [greedy(0.2), regret2(0.5), regret3(0.3)]
  │            → fitness: 78% improvement rate
  │
  ├─ Genome_2: [shaw_remove(0.6), worst_remove(0.2), tw_violation_remove(0.2)]
  │            → repair: [greedy(0.1), tw_aware_insert(0.6), capacity_fix(0.3)]
  │            → fitness: 85% improvement rate ← EN İYİ
  │
  └─ Genome_3: [cluster_remove(0.5), related_remove(0.5)]
               → repair: [regret2(0.7), regret3(0.3)]
               → fitness: 72% improvement rate
  
  → Problem NE öğreniyor, operator EVRİLİYOR
```

#### Operator Genome Yapısı

```python
@dataclass
class OperatorGenome:
    """
    Bir operator setinin genetik temsili.
    Her genom bir "destroy pipeline" ve bir "repair pipeline" tanımlar.
    """
    # Destroy pipeline: sıralı atomic operasyonlar
    destroy_genes: List[DestroyGene]
    # Repair pipeline: sıralı atomic operasyonlar  
    repair_genes: List[RepairGene]
    # Acceptance criterion
    accept_gene: AcceptanceGene
    # Fitness (kaç child'i iyileştirdi)
    fitness: float = 0.0
    # Age (kaç iterasyondur hayatta)
    age: int = 0
    # Success history (son N uygulama)
    success_history: Deque[bool] = field(default_factory=lambda: deque(maxlen=50))
    
@dataclass  
class DestroyGene:
    """Atomic destroy operasyonu ve ağırlığı"""
    operator_type: str  # "random", "worst", "related", "shaw", "cluster", ...
    intensity: float    # 0.0-1.0 (ne kadar node kaldırılacak)
    parameter: dict     # operator-parametre (örn: shaw'da relatedness threshold)

@dataclass
class RepairGene:
    """Atomic repair operasyonu ve ağırlığı"""
    operator_type: str  # "greedy", "regret2", "regret3", "tw_aware", ...
    ordering: str       # "random", "worst_first", "nearest_first", "tw_urgent"
    parameter: dict     # operator-parametre
```

### 4.3 Algoritma Mimarisi

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AOEA İKİ SEVİYELİ EVRİM                      │
│                                                                         │
│  SEVİYE 1: ÇÖZÜM EVRİMİ (Standart)           SEVİYE 2: OPERATÖR EVRİMİ│
│  ┌───────────────────────────┐                ┌──────────────────────┐  │
│  │ Solution Population       │                │ Operator Population  │  │
│  │ S = {s1, s2, ..., sm}    │                │ G = {g1, g2, ..., gk}│  │
│  │                           │                │                      │  │
│  │ İyileştirme süreci:       │                │ Evrim süreci:        │  │
│  │ s_i → destroy(g_j) →     │──── bağımlı ───→│ g_j bu turda         │  │
│  │      repair(g_j) → s_i'  │                │ başarı oranı?        │  │
│  │                           │                │                      │  │
│  └───────────────────────────┘                └──────────┬───────────┘  │
│                                                         │               │
│                    ┌────────────────────────────────────┘               │
│                    │                                                   │
│                    ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    META-EVOLÜSYON DÖNGÜSÜ                       │   │
│  │                                                                 │   │
│  │  Her Φ iterasyonda (örn. 100 çözüm iterasyonu = 1 meta iter):  │   │
│  │                                                                 │   │
│  │  1. DEĞERLENDİR: Her genome'in success_rate'ını hesapla        │   │
│  │  2. SEÇİM: En iyi k genome'i koru (elitizm)                    │   │
│  │  3. ÇAPRAZLAMA: Genome'leri çaprazla → yeni varyantlar         │   │
│  │  4. MUTASYON: Rastgele gen değişiklikleri                       │   │
│  │  5. YENİ DOĞAN: Rastgele genome'ler ekle (taze genetik materyal)│  │
│  │  6. SOY AĞACI: Başarısız genomleri (age > max) kaldır          │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Ko-Evolüsyon Mekanizması

```python
def coevolve(solution_pop, operator_pop, problem, n_iterations):
    """
    İki seviyeli ko-evolüsyon:
    - Düzey 1: Çözümler operator'ler kullanılarak iyileştirilir
    - Düzey 2: Operator'ler başarı oranlarına göre evrilir
    """
    s_best = best(solution_pop)
    meta_counter = 0
    META_INTERVAL = 100  # Her 100 iterasyonda operator evrimi
    
    for iteration in range(n_iterations):
        # DÜZEY 1: Çözüm iyileştirme
        s = tournament_select(solution_pop)
        g = roulette_wheel_select(operator_pop)  # fitness-based seçim
        
        s_destroyed = apply_destroy(s, g.destroy_genes, problem)
        s_new = apply_repair(s_destroyed, g.repair_genes, problem)
        
        # Acceptance (SA-criterion veya threshold)
        if accept(s_new, s, g.accept_gene, iteration):
            solution_pop.replace(s, s_new)
            g.record_success()  # ← Operator genome'e kaydet!
        else:
            g.record_failure()
        
        s_best = min(s_best, s_new)
        
        # DÜZEY 2: Meta-evolüsyon (periyodik)
        meta_counter += 1
        if meta_counter >= META_INTERVAL:
            meta_counter = 0
            operator_pop = evolve_operators(operator_pop)
            # ... (aşağıda detaylı)
    
    return s_best
```

### 4.5 Operator Evrimi (Meta-Level)

```python
def evolve_operators(operator_pop: List[OperatorGenome]) -> List[OperatorGenome]:
    """
    Operator populasyonunu evrimleştir.
    Her genom bir "operator seti"nin genetik kodudur.
    """
    # 1. FITNESS HESAPLA
    for g in operator_pop:
        g.fitness = np.mean(g.success_history) if g.success_history else 0.0
    
    # 2. ELİTİZM — En iyi 2'yi koru
    operator_pop.sort(key=lambda g: g.fitness, reverse=True)
    survivors = operator_pop[:2].copy()
    
    # 3. GENOME ÇAPRAZLAMASI
    while len(survivors) < len(operator_pop) - 2:
        p1, p2 = tournament_select_genomes(operator_pop, k=3)
        
        # Destroy genes crossover
        child_destroy = gene_crossover(p1.destroy_genes, p2.destroy_genes)
        # Repair genes crossover  
        child_repair = gene_crossover(p1.repair_genes, p2.repair_genes)
        # Acceptance gene crossover
        child_accept = gene_crossover_single(p1.accept_gene, p2.accept_gene)
        
        child = OperatorGenome(
            destroy_genes=child_destroy,
            repair_genes=child_repair,
            accept_gene=child_accept,
            fitness=0.0,  # Henüz test edilmedi
            age=0,
        )
        survivors.append(child)
    
    # 4. GENOME MUTASYONU
    for g in survivors[2:]:  # Elitler mutasyona uğramaz
        if random() < 0.3:
            g.destroy_genes = mutate_genes(g.destroy_genes)
        if random() < 0.3:
            g.repair_genes = mutate_genes(g.repair_genes)
    
    # 5. YENİ DOĞAN — Tamamen rastgele genome'ler
    for _ in range(2):
        survivors.append(random_genome(problem_features))
    
    # 6. YAŞ Sınırlaması — Çok yaşlı ve başarısız genomları kaldır
    survivors = [g for g in survivors 
                 if g.age < MAX_GENOME_AGE or g.fitness > MIN_FITNESS_THRESHOLD]
    
    # Population size'ı sabitle
    survivors = survivors[:POP_SIZE]
    while len(survivors) < POP_SIZE:
        survivors.append(random_genome())
    
    return survivors
```

### 4.6 Atomic Operasyon Kütüphanesi

AOEA'nın gücü **atomic operasyonların zenginliğinden** gelir. Her genom bu atomları kombinleyebilir:

```
┌─────────────────────────────────────────────────────────────────┐
│                   ATOMIC DESTROY OPERATIONS                     │
├───────────────────────┬─────────────────────────────────────────┤
│ random_remove(k)      │ Rastgele k node kaldır                  │
│ worst_remove(k)       │ En pahalı k kenarı kaldır              │
│ related_remove(k,λ)   │ λ-benzer node'ları kaldır              │
│ shaw_remove(k)        │ Shaw benzerliğine göre kaldır           │
│ cluster_remove(c)     │ c cluster'ından kaldır                  │
│ tw_violation_remove() │ Time window ihlali olanları kaldır      │
│ capacity_remove()     │ Kapasite baskısı olan rotaları kır     │
│ route_remove(r)       │ Tüm bir rotayı kaldır                  │
│ bridge_remove()       │ İki rota arası köprü kenarları kaldır  │
│ corridor_remove()     │ Dar corridor'daki node'ları kaldır     │
└───────────────────────┴─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   ATOMIC REPAIR OPERATIONS                      │
├───────────────────────┬─────────────────────────────────────────┤
│ greedy_insert(seq)    │ En iyi pozisyona sıralı ekleme          │
│ regret2_insert(seq)   │ 2-regret bazlı ekleme                   │
│ regret3_insert(seq)   │ 3-regret bazlı ekleme                   │
│ tw_aware_insert(seq)  │ Time window uyumlu ekleme               │
│ cap_aware_insert(seq) │ Kapasite uyumlu ekleme                  │
│ parallel_insert()     │ Paralel rotalara eşzamanlı ekleme      │
│ cheapest_insert()     │ Maliyet artışı minimum ekleme           │
│ penalty_insert(α,β)   │ Ceza fonksiyonlu yumuşak ekleme         │
│ reinsert(shuffle)     │ Kaldırılan node'ları farklı rotalara   │
│ local_search_insert() │ Her eklemede 2-opt yap                 │
└───────────────────────┴─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  ACCEPTANCE CRITERIA                             │
├───────────────────────┬─────────────────────────────────────────┤
│ sa_boltzmann(T₀,α)   │ Simulated Annealing (Boltzmann)         │
│ sa_exponential(T₀,β) │ SA (exponential cooling)                 │
│ threshold(δ)          │ Sabit eşik kabul                         │
│ improving_only()      │ Sadece iyileştirenleri kabul            │
│ great_deluge(λ)       │ Water level tabanlı                     │
│ record_to_record()    │ RTR acceptance (Genç 2008)              │
│ late_accept(ε)        │ Late acceptance hill climbing           │
└───────────────────────┴─────────────────────────────────────────┘
```

### 4.7 CVRPTW Uyarlama

```
CVRPTW Modunda Özel Atomic Operations:

DESTROY (CVRPTW-özel):
  - tw_violation_remove(): En çok TW ihlali yapan rotalardan node çıkar
  - tight_tw_remove(): Sıkışık TW'lu node'ları çıkar (yeniden yerleştirmek için)
  - capacity_remove(): Kapasite sınırına yaklaşan rotalardan node çıkar
  - schedule_conflict_remove(): Zaman çakışması olan node'ları çıkar

REPAIR (CVRPTW-özel):
  - tw_aware_insert(): Erken arrival → wait, late → reject mantığıyla ekle
  - cap_aware_insert(): Kapasite constraint'ini kontrol ederek ekle
  - schedule_insert(): Mevcut zaman çizelgesine uyumlu pozisyon bul
  - penalty_insert(α_tw, α_cap): TW ve kapasite cezalarıyla yumuşak ekleme

GENOME EVRİMİ (CVRPTW'de otomatik):
  - Başlangıçta random genome'ler
  - TW-ihlali fazla olan durumda: tw_violation_remove + tw_aware_insert içeren
    genomlar HIGHER fitness alır → doğal seçilim bunları tercih eder
  - Kapasite sorunu varsa: capacity_remove + cap_aware_insert genomları evrilir
  → Algoritma PROBLEME GÖRE OTOMATİK UYUMLANIR
```

### 4.8 Sözde Kod

```
ALGORITHM AOEA(problem, params):
  
  // --- ÇİFT POPÜLASYON BAŞLANGIÇ ---
  S ← InitializeSolutions(problem, params.sol_pop)
  G ← InitializeOperatorGenomes(problem.features, params.op_pop)
  S_best ← Best(S)
  
  FOR t = 1 TO T_total:
    
    // --- DÜZEY 1: ÇÖZÜM İYİLEŞTİRME ---
    s ← TournamentSelect(S)
    g ← FitnessSelect(G)  // Başarılı operator setini tercih et
    
    s' ← ApplyDestroy(s, g.destroy_genes)
    s' ← ApplyRepair(s', g.repair_genes)
    
    IF Accept(s', s, g.accept_gene, t):
      S.replace(s, s')
      g.record_success()
    ELSE:
      S.keep(s)
      g.record_failure()
    
    // Lokal arama (olasılıksal)
    IF random() < params.ls_prob:
      s'' ← LocalSearch(S.random(), operators=g.repair_genes)
      S.try_replace(s'')
    
    S_best ← min(S_best, Best(S))
    
    // --- DÜZEY 2: OPERATÖR EVRİMİ (periyodik) ---
    IF t % params.meta_interval == 0:
      G ← EvolveOperators(G)
      // Seed: Problem feature'larına göre yeni genome ekle
      G ← SeedDomainGenomes(G, problem.features)
  
  RETURN S_best
```

### 4.9 AOEA'nın Avantajları

1. **Problem-agnostik**: İnsan operator tasarımı gerektirmez
2. **Otomatik adaptasyon**: CVRPTW problemsine göre operator'ler evrilir
3. **Sürekli iyileşme**: Meta-evolüsyon sayesinde operatör seti zamanla optimize olur
4. **Transfer learning**: Bir problemde öğrenilen genome'ler benzer problemlere aktarılabilir
5. **Açıklanabilirlik**: Evrilmiş genome'ler hangi operatörlerin etkili olduğunu gösterir
6. **Literatür novada**: Operatör ko-evrimi kavramı routing optimizasyonunda literatürde yok

---

## 5. Algoritma 3: EBSO — Entropy-Balanced Swarm Optimization

### 5.1 Konsept ve İlham

**İlham Kaynakları**:
- Shannon Entropy (1948) — bilgi teorisinin temel metriği
- Thermodynamics — entropy maximization principle
- Particle Swarm Optimization (Kennedy & Eberhart 1995)
- Diversity-guided Evolutionary Algorithms (Ursem 2002)

**Temel Fikir**: Popülasyon tabanlı algoritmalarda **erken yakınsama** en büyük sorundur. EBSO, Shannon entropisini **birincil kontrol mekanizması** olarak kullanır. Popülasyon entropisi belirli bir aralıkta tutularak, exploration-exploitation dengesi **matematiksel olarak garanti edilir**.

### 5.2 Çığır Açan Novada: Entropi Denge Mekanizması

#### Standart Yaklaşımlar vs EBSO

```
STANDART PSO:
  - Sabit inertia weight (w = 0.729)
  - Sabit cognitive/social coefficients
  - Çeşitlilik = örtük (mutasyon oranı vs.)
  - Yakınsama kontrolü = YOK

STANDART GA:
  - Sabit mutasyon oranı (p = 0.01)
  - Turnuva seçimi sabit
  - Çeşitlilik = örtük

EBSO:
  - Entropi = BİRİNCİL KONTROL DEĞİŞKENİ
  - Her iterasyonda H(S) hesaplanır
  - H < H_min → ENTROPİ ENJEKSİYONU (exploration)
  - H > H_max → ENTROPİ SIKIŞTIRMA (exploitation)
  - H_min < H < H_max → NORMAL İYİLEŞTİRME
  - H_target(t) adaptif zamanla azalır (soğuma benzeri)
```

### 5.3 Tur Entropisi Tanımı

```python
def tour_entropy(population: List[Tour]) -> float:
    """
    Popülasyonun Shannon entropisini hesaplar.
    
    Her kenarın popülasyondaki frekansına dayalı olarak,
    popülasyonun ne kadar "çeşitli" olduğunu ölçer.
    """
    n = len(population[0])  # Tur uzunluğu
    N = len(population)     # Popülasyon boyutu
    
    # Kenar frekans matrisi
    edge_freq = defaultdict(int)
    for tour in population:
        edges = get_edges(tour)
        for edge in edges:
            edge_freq[edge] += 1
    
    # Kenar entropisi
    H_edge = 0.0
    for edge, count in edge_freq.items():
        p = count / (N * n)  # Normalize edilmiş olasılık
        if p > 0:
            H_edge -= p * log2(p)
    
    # Pozisyon entropisi (her pozisyondaki node çeşitliliği)
    H_pos = 0.0
    for pos in range(n):
        node_counts = defaultdict(int)
        for tour in population:
            node_counts[tour[pos]] += 1
        for count in node_counts.values():
            p = count / N
            if p > 0:
                H_pos -= p * log2(p)
    
    # Normalize edilmiş toplam entropi
    H_max_edge = log2(n * (n-1) / 2)  # Maksimum kenar entropisi
    H_max_pos = log2(n)  # Maksimum pozisyon entropisi
    
    H_norm = 0.5 * (H_edge / H_max_edge) + 0.5 * (H_pos / H_max_pos)
    
    return H_norm  # [0, 1] aralığında normalize edilmiş entropi
```

### 5.4 Algoritma Mimarisi

```
┌──────────────────────────────────────────────────────────────────────┐
│                        EBSO AKIŞ DİYAGRAMI                          │
│                                                                      │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │ Başlangıç│───▶│ Popülasyon   │───▶│ H(S) = Tur Entropisi     │   │
│  │ (Max     │    │ P = {S1..Sn} │    │ H ∈ [0, 1]              │   │
│  │  Entropi)│    │              │    └──────────┬───────────────┘   │
│  └──────────┘    └──────────────┘               │                   │
│                                               │                    │
│                    ┌──────────────────────────┼────────────────┐   │
│                    │                          │                │   │
│                    ▼                          ▼                ▼   │
│  ┌────────────────────────┐  ┌───────────────────┐  ┌──────────┐  │
│  │ H < H_min              │  │ H_min ≤ H ≤ H_max│  │H > H_max │  │
│  │                        │  │                   │  │          │  │
│  │  ENTROPİ ENJEKSİYONU   │  │  NORMAL İYİLEŞTİRME│  │ SIKIŞTIR │  │
│  │  ──────────────────    │  │  ──────────────────│  │ ──────── │  │
│  │  • Gradient-guided     │  │  • Swarm update    │  │ • Agresif│  │
│  │    perturbation        │  │    (gBest + pBest) │  │   conver-│  │
│  │  • Entropy wells       │  │  • Moderate LS     │  │   gence  │  │
│  │    hedefle             │  │  • Balanced        │  │ • Deep LS│  │
│  │  • Low-freq edges      │  │    exploration/    │  │ • pBest  │  │
│  │    ekle                │  │    exploitation    │  │   attract│  │
│  └────────────┬───────────┘  └─────────┬─────────┘  └────┬─────┘  │
│               │                        │                  │        │
│               └────────────────────────┼──────────────────┘        │
│                                        │                           │
│                                        ▼                           │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    ADAPTİF H_target(t)                     │    │
│  │                                                            │    │
│  │  H_target(t) = H_start · (1 - t/T)^γ + H_end             │    │
│  │                                                            │    │
│  │  γ > 1: Geç exploration, erken exploitation                │    │
│  │  γ < 1: Erken exploration, geç exploitation               │    │
│  │  γ = 1: Doğrusal soğuma                                  │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.5 Üç Fazlı Kontrol Mekanizması

#### Faz 1: Entropi Enjeksiyonu (H < H_min) — Exploration

```python
def entropy_injection(population, edge_freq, n_edges):
    """
    Düşük entropi = popülasyon çok benzeşti = exploration gerekli.
    Rastgele DEĞİL, entropi gradient'ine yönelik perturbation.
    """
    # 1. Entropi gradient hesapla
    #    Hangi kenarlar "az kullanılmış"? (düşük frekans = yüksek entropi katkısı)
    entropy_gradient = {}
    for edge, freq in edge_freq.items():
        # Bu kenar popülasyona eklense, entropi ne kadar artar?
        new_freq = freq + 1
        p_new = new_freq / (len(population) * len(population[0]))
        p_old = freq / (len(population) * len(population[0]))
        
        delta_H = -p_new * log2(p_new) + p_old * log2(p_old)
        entropy_gradient[edge] = delta_H  # Pozitif = entropiyi artırır
    
    # 2. En yüksek gradient'li kenarları seç
    top_edges = sorted(entropy_gradient.items(), key=lambda x: x[1], reverse=True)
    
    # 3. Rastgele seçilen çözümlere gradient-guided perturbation uygula
    for s in random.sample(population, k=len(population)//3):
        # Rastgele bir edge'i high-gradient edge ile değiştir
        current_edges = get_edges(s)
        remove_edge = random.choice(current_edges)
        add_edge = random.choice(top_edges[:10])[0]
        
        s_new = swap_edge(s, remove_edge, add_edge)
        if is_valid_tour(s_new):
            population[population.index(s)] = s_new
    
    return population
```

#### Faz 2: Normal İyileştirme (H_min ≤ H ≤ H_max) — Balanced

```python
def normal_optimization(population, distance_matrix, alpha, beta):
    """
    Dengeli bölge: Standart swarm güncellemesi + ılımlı lokal arama.
    PSO-inspired ama permutation uyumlu.
    """
    g_best = best(population)
    new_pop = []
    
    for s in population:
        p_best = personal_best(s)
        
        # Swarm update: g_best ve p_best'ten öğren
        s_new = swarm_recombine(s, p_best, g_best, alpha, beta)
        
        # Alpha: g_best'e çekim gücü (exploitation)
        # Beta: p_best'e çekim gücü (personal exploitation)
        # (1-alpha-beta): Mevcut yönü koruma (inertia)
        
        # İlımlı lokal arama (olasılıksal)
        if random() < 0.3:
            s_new = two_opt(s_new, distance_matrix, max_iterations=10)
        
        new_pop.append(s_new)
    
    return new_pop
```

#### Faz 3: Entropi Sıkıştırma (H > H_max) — Exploitation

```python
def entropy_compression(population, distance_matrix):
    """
    Yüksek entropi = popülasyon çok dağılmış = exploitation gerekli.
    Agresif convergence stratejileri.
    """
    g_best = best(population)
    
    # 1. Agresif pBest attraction
    for i, s in enumerate(population):
        if fitness(s) > fitness(personal_best(s)):
            population[i] = deepcopy(personal_best(s))
    
    # 2. g_best'e yakınlaştırma (agresif)
    for i, s in enumerate(population):
        if random() < 0.5:
            # g_best ile kısmi çaprazlama
            population[i] = partial_crossover(s, g_best, ratio=0.3)
    
    # 3. Deep lokal arama (sadece en iyi %20'ye)
    top_k = int(len(population) * 0.2)
    sorted_pop = sorted(population, key=fitness)[:top_k]
    for i, s in enumerate(sorted_pop):
        population[i] = variable_neighborhood_search(s, distance_matrix)
    
    return population
```

### 5.6 Swarm Recombine — Permutation PSO

```python
def swarm_recombine(s: Tour, p_best: Tour, g_best: Tour, alpha: float, beta: float):
    """
    PSO position update'in permutation versiyonu.
    
    s_new = s + c1·(p_best - s) + c2·(g_best - s)
    
    Permutation uzayında: "-" operatörü "fark" (ortak olmayan kenarlar)
    "+" operatörü "kenar ekleme/değiştirme"
    """
    n = len(s)
    
    # p_best'ten öğren: p_best'de var ama s'de yok olan kenarları ekle
    p_edges = set(get_edges(p_best))
    s_edges = set(get_edges(s))
    g_edges = set(get_edges(g_best))
    
    # Kaldırılacak kenarlar: s'de var ama p_best/g_best'de yok
    remove_candidates = list(s_edges - p_edges - g_edges)
    # Eklenecek kenarlar: p_best/g_best'de var ama s'de yok
    add_candidates = list((p_edges | g_edges) - s_edges)
    
    # Alpha: p_best'ten öğrenme oranı
    n_remove = int(len(remove_candidates) * alpha)
    n_add = int(len(add_candidates) * alpha)
    
    # Beta: g_best'ten öğrenme oranı  
    g_add_candidates = list(g_edges - s_edges)
    n_g_add = int(len(g_add_candidates) * beta)
    
    # Apply changes
    result = list(s)
    for edge in random.sample(remove_candidates, min(n_remove, len(remove_candidates))):
        result = remove_edge_from_tour(result, edge)
    for edge in random.sample(add_candidates, min(n_add + n_g_add, len(add_candidates) + len(g_add_candidates))):
        result = insert_edge_to_tour(result, edge)
    
    # Repair: Geçersiz turları düzelt
    result = repair_tour(result)
    
    return result
```

### 5.7 CVRPTW Uyarlama

```
CVRPTW Modunda Çok-Boyutlu Entropi:

  H_cvrp(S) = w_dist · H_edges(S) 
            + w_tw   · H_time_windows(S)
            + w_cap  · H_capacity(S)

  H_time_windows(S):
    Her node'un hangi zaman diliminde servis edildiğinin çeşitliliği
    → Aynı node farklı turlarda farklı saatlerde servis ediliyorsa H yüksek
    
  H_capacity(S):
    Araç kapasite kullanım profilinin çeşitliliği
    → Farklı turlar farklı kapasite seviyelerindeyse H yüksek

  Faz Geçişleri (CVRPTW):
    H < H_min:
      → TW-diversity enjeksiyonu: Farklı zaman dilimlerinde servis deneyen turlar ekle
      → Capacity-diversity: Farklı yük dağılımları dene
    
    H > H_max:
      → TW-convergence: En az TW ihlali yapan turlara yönel
      → Capacity-convergence: Dengeli yüklemeye yönel
      
  Adaptif Ağırlıklar:
    w_tw   = 1 + (TW ihlali sayısı / toplam ihlali)
    w_cap  = 1 + (Capacity aşımı sayısı / toplam aşım)
    → Problem hangi constraint'i zorluyorsa, o boyutun entropisi ağırlıklanır
```

### 5.8 Sözde Kod

```
ALGORITHM EBSO(problem, params):
  
  // --- BAŞLANGIÇ (Maksimum Entropi) ---
  P ← MaxEntropyPopulation(problem, params.pop_size)
  // Her birey farklı bir NN variant'ı + rastgele perturbation
  
  g_best ← Best(P)
  p_best[i] ← P[i]  FOR all i
  
  // --- Hedef Entropi Çizelgesi ---
  H_start ← 0.9
  H_end   ← 0.2
  γ       ← params.cooling_rate  // default: 0.8
  
  FOR t = 1 TO T_max:
    
    // --- 1. ENTROPİ HESAPLA ---
    H ← ComputeTourEntropy(P)
    H_target ← H_start · (1 - t/T_max)^γ + H_end
    
    // --- 2. FAZ KARARI ---
    IF H < H_target - Δ_low:
      // FAZ 1: Entropi Enjeksiyonu (Exploration)
      P ← EntropyInjection(P, EntropyGradient(P))
      α ← 0.2  // Düşük gBest çekimi
      β ← 0.1  // Düşük pBest çekimi
      
    ELIF H > H_target + Δ_high:
      // FAZ 3: Entropi Sıkıştırma (Exploitation)
      P ← EntropyCompression(P, g_best)
      α ← 0.8  // Yüksek gBest çekimi
      β ← 0.6  // Yüksek pBest çekimi
      
    ELSE:
      // FAZ 2: Normal İyileştirme (Balanced)
      α ← 0.5
      β ← 0.3
    
    // --- 3. SWARM GÜNCELLEME ---
    FOR i = 1 TO |P|:
      P[i] ← SwarmRecombine(P[i], p_best[i], g_best, α, β)
      
      IF Fitness(P[i]) < Fitness(p_best[i]):
        p_best[i] ← P[i]
      IF Fitness(P[i]) < Fitness(g_best):
        g_best ← P[i]
    
    // --- 4. LOKAL ARAMA (olasılıksal, faz-bağlı) ---
    IF H < H_target:
      ls_prob ← 0.1  // Exploration'da az LS
    ELIF H > H_target:
      ls_prob ← 0.6  // Exploitation'da çok LS
    ELSE:
      ls_prob ← 0.3  // Dengeli
    
    IF random() < ls_prob:
      idx ← random_index(P)
      P[idx] ← VNS(P[idx], problem)  // Variable Neighborhood Search
    
    // --- 5. SONUÇ GÜNCELLEME ---
    g_best ← min(g_best, Best(P))
  
  IF problem.type == "cvrptw":
    RETURN SplitDecode(g_best, problem.constraints)
  ELSE:
    RETURN g_best
```

### 5.9 EBSO'nun Avantajları

1. **Matematiksel garanti**: H_target çizelgesi ile exploration/exploitation oranı kontrol edilebilir
2. **Graduate descent benzeri**: Entropi gradient'i perturbation'u yönlendirir
3. **CVRPTW çok-boyutlu**: Her constraint boyutunda ayrı entropi takibi
4. **Parametre az**: Temel parametreler sadece H_start, H_end, γ — interpretasyonu kolay
5. **Adaptif**: İterasyon ilerledikçe otomatik olarak exploration'dan exploitation'a geçer
6. **Teorik temel**: Shannon entropisi literatürde iyi çalışılmış, rigor matematiksel altyapı

---

## 6. Karşılaştırma Analizi

### 6.1 Özellik Karşılaştırma Tablosu

| Özellik | RDMA | AOEA | EBSO | ALNS (planlı) |
|---------|------|------|------|---------------|
| **Ana Mekanizma** | Rezonans-guided crossover | Operator ko-evrimi | Entropi-destekli swarm | Sabit destroy/repair |
| **Novelty Level** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ (mevcut) |
| **TSP Uyumluluğu** | ✅ Doğrudan | ✅ Doğrudan | ✅ Doğrudan | ⚠️ CVRP-odaklı |
| **CVRPTW Uyumluluğu** | ✅ Çok-boyutlu rezonans | ✅ Evrilen operator'ler | ✅ Çok-boyutlu entropi | ✅ Native |
| **Adaptiflik** | θ_esik adaptif | Operator fitness adaptif | H_target adaptif | Roulette wheel |
| **Çeşitlilik Kontrolü** | Harmonic Pulse | Yeni genome doğuşu | 3-fazlı entropi kontrolü | Random restart |
| **Uygulanma Zorluğu** | 🟡 Orta | 🔴 Yüksek | 🟢 Düşük-Orta | 🟡 Orta |
| **Hesaplama Ek Maliyeti** | O(n²) rezonans matrisi | O(k·m) meta-evrim | O(n²) entropi hesabı | O(1) sabit |
| **Numba JIT Uyumu** | ✅ Rezonans hesabı JIT'lenebilir | ⚠️ Genome'ler dinamik | ✅ Entropi JIT'lenebilir | ✅ TAMAMEN JIT |
| **Açıklanabilirlik** | 🟢 Yüksek (rezonans haritası) | 🟡 Orta (evrilmiş genome) | 🟢 Çok yüksek (entropi grafiği) | 🟢 Yüksek |

### 6.2 Beklenen Performans Sınıflandırması

```
                    Kalite (Gap to Optimal)
                         ▲
                    5%  │
                        │         AOEA
                    4%  │       ●
                        │              RDMA
                    3%  │            ●
                        │
                    2%  │         EBSO
                        │       ●
                    1%  │  ALNS
                        │●
                    0%  ├──────────────────
                        │  Optimal
                    ────┼──────────────────────▶ Zaman
                       10s  60s  300s  1800s
```

| Algoritma | Küçük (n<50) | Orta (50-200) | Büyük (n>200) | Hız |
|-----------|-------------|---------------|---------------|-----|
| **RDMA** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Orta |
| **AOEA** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Yavaş (meta-evrim) |
| **EBSO** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Hızlı |
| **ALNS** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Hızlı |

### 6.3 Synergy Potansiyeli

```
RDMA + EBSO = "Rezonans Entropi Algoritması" (REA)
  → Rezonans-guided crossover + Entropi-destekli çeşitlilik kontrolü
  → RDMA'nın crossover kalitesi + EBSO'nun adaptif dengesi

AOEA + RDMA = "Operator-Rezonans Algoritması" (ORA)  
  → AOEA operator evrimi + RDMA rezonans eşleştirmesi
  → Evrilmiş operator'ler sadece yüksek-rezonans çözümlere uygulanır

AOEA + EBSO = "Entropi-Evrilen Operator Algoritması" (EEOA)
  → EBSO entropi kontrolü + AOEA operator adaptasyonu
  → Hangi fazdaysak (exploration/exploitation) o faz için evrilmiş operator'leri kullan
```

---

## 7. Entegrasyon Planı

### 7.1 Teknik Entegrasyon

Tüm 3 algoritma mevcut `BaseRoutingStrategy` arayüzüne uyar:

```python
# Her algoritma için implementasyon şablonu:
class RDMASplitStrategy(HybridSplitBaseStrategy):
    """RDMA with Split Decoder for CVRPTW"""
    name = "rdma_split"
    display_name = "RDMA + Split (Resonance-Driven)"
    description = "Resonance-guided memetic algorithm with optimal split decoding"
    
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        # 1. Problem hazırlığı (mevcut kod ile paylaşılır)
        # 2. RDMA optimizasyon
        # 3. Split decode
        # 4. Response oluşturma
        pass

class AOEAASplitStrategy(HybridSplitBaseStrategy):
    name = "aoea_split"
    display_name = "AOEA + Split (Operator Evolution)"
    description = "Co-evolutionary operator adaptation with optimal split decoding"
    pass

class EBSOSplitStrategy(HybridSplitBaseStrategy):
    name = "ebso_split" 
    display_name = "EBSO + Split (Entropy-Balanced)"
    description = "Entropy-controlled swarm optimization with optimal split decoding"
    pass
```

### 7.2 Geliştirme Sırası Önerisi

```
Aşama 1 (2 hafta): EBSO — En düşük karmaşıklık, en hızlı sonuç
  ├─ entropy.py: Tur entropisi hesaplama (Numba JIT)
  ├─ ebso_strategy.py: Temel EBSO implementasyonu
  ├─ ebso_split_strategy.py: Split decoder entegrasyonu
  └─ Benchmark: TSPLIB (eil51, kroA100, d198) + Solomon CVRPTW
  
Aşama 2 (3 hafta): RDMA — Orta karmaşıklık, yüksek potansiyel
  ├─ resonance.py: Rezonans matrisi hesaplama (Numba JIT)
  ├─ rdma_strategy.py: Rezonans crossover + harmonic pulse
  ├─ rdma_split_strategy.py: Split decoder entegrasyonu
  └─ Benchmark: Aynı set + karşılaştırma EBSO vs RDMA

Aşama 3 (4 hafta): AOEA — En yüksek karmaşıklık, en yüksek novada
  ├─ operator_genome.py: Genome veri yapısı
  ├─ atomic_operations.py: 20+ atomic destroy/repair
  ├─ aoea_strategy.py: Ko-evrim mekanizması
  ├─ aoea_split_strategy.py: CVRPTW adaptasyonu
  └─ Benchmark: Tüm set + karşılaştırma EBSO vs RDMA vs AOEA

Aşama 4 (2 hafta): Hibrit ve Synergy
  ├─ Cross-algorithm fusion denemeleri
  ├─ Akademik karşılaştırma tabloları
  └─ Paper draft hazırlığı
```

### 7.3 Registry Entegrasyonu

```python
# __init__.py'ye eklenecek:
STRATEGY_REGISTRY.update({
    # --- SOTA Novel Algorithms ---
    "rdma_split": _rdma_split_strategy,
    "rdma": _rdma_strategy,
    "aoea_split": _aoea_split_strategy,
    "aoea": _aoea_strategy,
    "ebso_split": _ebso_split_strategy,
    "ebso": _ebso_strategy,
})
```

---

## 8. Akademik Yayın Stratejisi

### 8.1 Potansiyel Yayın Hedefleri

| Algoritma | Hedef Konferans | Hedef Dergi | Novelty Claim |
|-----------|----------------|-------------|---------------|
| **RDMA** | GECCO 2027, CEC 2027 | Swarm and Evolutionary Computation | "Resonance-guided crossover for combinatorial optimization" |
| **AOEA** | AAAI 2027, IJCAI 2027 | Evolutionary Computation (MIT Press) | "Co-evolutionary operator adaptation for vehicle routing" |
| **EBSO** | ICDE 2027, WCCI 2027 | IEEE Trans. on Evolutionary Computation | "Shannon entropy-based diversity control for swarm optimization" |
| **Synergy** | N/A | Transportation Research Part C | "Synergistic novel metaheuristics for CVRPTW" |

### 8.2 Akademik Katkı Beyanları

1. **RDMA**: "İlk kez akustik rezonans kavramı kombinatoryal optimizasyona uygulanmıştır. Rezonans metriği, standart crossover'ın verimsizliğini gidermek için yapısal uyum tabanlı bir eşleştirme mekanizması sunar."

2. **AOEA**: "İlk kez operator'lerin bir genom olarak modellenip çözümlerle birlikte ko-evrilmesi önerilmiştir. Bu yaklaşım, insan-tasarımlı operator'lerin limitlerini aşarak problem-agnostik otomatik adaptasyon sağlar."

3. **EBSO**: "İlk kez Shannon entropisi, popülasyon tabanlı routing optimizasyonunda birincil kontrol mekanizması olarak kullanılmıştır. Üç-fazlı entropi kontrolü, exploration-exploitation dengesini matematiksel olarak garanti eder."

### 8.3 Benchmark Stratejisi

```
TSPLIB Benchmark (TSP):
  - Small:  eil51, st70, rat99, kroA100
  - Medium: d198, lin318, pcb442
  - Large:  rat783, pr1002, d1291
  
Solomon Benchmark (CVRPTW):
  - C category (clustered):     C101, C201
  - R category (random):         R101, R201
  - RC category (random-cluster): RC101, RC201
  
Vrptw Benchmark Set (kısıtlı TW):
  - 100, 200, 400, 600 customer instances

Karşılaştırma:
  - UniRide mevcut algoritmalar (GA, PSO, GWO, HHO)
  - PyVRP HGS (DIMACS 2021 winner)
  - ALNS (Ropke & Pisinger 2006)
  - Literature best-known solutions
```

---

## Ek A: Terminoloji Sözlüğü

| Terim | Tanım |
|-------|-------|
| **Rezonans** | İki çözümün yapısal uyum ölçüsü (ortak kenar + alt-tur benzerliği) |
| **Constructive Interference** | Uyumlu çözümlerin birleşiminde kalite artışı |
| **Destructive Interference** | Uyumsuz çözümlerin birleşiminde kalite düşüşü |
| **Harmonic Pulse** | Yakınsama tespitinde yapılan yapılandırılmış çeşitlilik enjeksiyonu |
| **Operator Genome** | Destroy/repair operatör setlerinin genetik temsili |
| **Ko-Evolüsyon** | Çözümler ve operator'lerin aynı anda evrilmesi |
| **Tur Entropisi** | Popülasyonun kenar frekans dağılımının Shannon entropisi |
| **Entropi Gradient** | Hangi kenarın eklenmesinin entropiyi en çok artıracağı |
| **H_target** | Adaptif entropi hedef çizelgesi (exploration→exploitation geçişi) |
| **Atomic Operation** | En küçük birim destroy/repair operasyonu |
| **Meta-Evolüsyon** | Operator populasyonu üzerindeki evrim süreci |

---

## Ek B: Referanslar

### Mevcut Algoritma Temelleri
- [1] Holland, J.H. (1975). Adaptation in Natural and Artificial Systems.
- [2] Kennedy, J. & Eberhart, R. (1995). Particle Swarm Optimization.
- [3] Mirjalili, S. et al. (2014). Grey Wolf Optimizer.
- [4] Heidari, A.A. et al. (2019). Harris Hawks Optimization.
- [5] Prins, C. (2004). A simple and effective evolutionary algorithm for the VRP.

### Modern İlgili Çalışmalar
- [6] Ropke, S. & Pisinger, D. (2006). An Adaptive Large Neighborhood Search Heuristic for the VRP.
- [7] Furelos-Blanco, D. et al. (2023). Poppy: Population-Based RL for CO (NeurIPS).
- [8] VRPAgent (2025). LLM-Driven Discovery of Heuristic Operators (ICLR Workshop).
- [9] BOPO (2025). Best-Anchored and Objective-guided Preference Optimization (ICML).
- [10] HQTS (2024). Hybrid Quantum Tabu Search (arXiv:2404.13203).

### Bilgi Teorisi ve Fizik
- [11] Shannon, C.E. (1948). A Mathematical Theory of Communication.
- [12] Ursem, R.K. (2002). Diversity-Guided Evolutionary Algorithms.

---

> **Sonraki Adım**: EBSO ile geliştirmeye başlanması önerilir (en düşük karmaşıklık, en hızlı sonuç). RDMA ikinci, AOEA üçüncü sırada implemente edilmelidir.
