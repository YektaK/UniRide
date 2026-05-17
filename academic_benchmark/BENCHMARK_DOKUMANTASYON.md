# UniRide Akademik Benchmark Framework — Kapsamlı Dokümantasyon

> **Versiyon:** 3.3 | **Tarih:** 2026-05-16
> **İngilizce özet ve akademik metodoloji için [Bölüm 6](#6-academic-methodology-english)'ya bakın.**

---

## 1. Sistem Genel Bakış

UniRide Akademik Benchmark Framework, Gezgin Satıcı Problemi (TSP) ve Asimetrik TSP (ATSP) algoritmalarını TSPLIB problemleri üzerinde test etmek için tasarlanmış **çift motorlu (dual-engine)** bir sistemdir.

### 1.1 Mimari

```
academic_benchmark/
├── smart_benchmark.py          # Unified CLI (tek giriş noktası)
├── master_numba_engine.py      # Numba Motoru (klasik meta-sezgiseller)
├── master_sota_engine.py       # SOTA Motoru (modern çözücüler)
├── engine_core.py              # AlgorithmRegistry (merkezi kayıt)
├── benchmark_utils.py          # Paylaşılan yardımcı fonksiyonlar
├── tsplib_manager.py           # SQLite DB yöneticisi
├── param_db.py                 # JSON parametre veritabanı
├── dashboard.py                # Streamlit görselleştirme
├── bildiri2026/core/           # Numba hızlandırılmış solver'lar
├── sota_tsp/                   # SOTA çözücü implementasyonları
└── tests/                      # Test paketi (45 test)
```

### 1.2 İki Motor Karşılaştırma

| Özellik | Numba Motoru | SOTA Motoru |
|---------|-------------|-------------|
| **Algoritmalar** | GA, PSO, GWO, HHO, 2-opt, 3-opt-bounded, Or-opt, Swap, Hybrid, B-PSO, B-GA | E2BSO-TSP, E2BSO-TSP-CPSO, R2DMA-TSP, P-AOEA-TSP, CGO-TSP, RUN-TSP |
| **Hızlandırma** | Numba JIT (`@njit(nogil=True)`) | Saf Python + Numba destekli LS |
| **Parametre** | Grid/Fractional/Bayesian (Optuna) | Grid/Fractional/Bayesian (Optuna) |
| **Paralel** | ProcessPoolExecutor | ProcessPoolExecutor |
| **ATSP** | ✅ Tam destek | ✅ Tam destek |
| **Toplam** | 11 algoritma | 6 algoritma |

### 1.3 Algoritma Listesi (17 Toplam)

| # | Algoritma | Motor | Tür | ATSP | Karmaşıklık |
|---|-----------|-------|-----|------|-------------|
| 1 | Numba-2-opt | Numba | Local Search | ✅ | O(n²) |
| 2 | Numba-3-opt-bounded | Numba | Local Search | ✅ | O(n·w²) |
| 3 | Numba-Or-opt | Numba | Local Search | ✅ | O(n²) |
| 4 | Numba-Swap | Numba | Local Search | ✅ | O(n²) |
| 5 | Numba-Hybrid | Numba | Local Search | ✅ | O(n³) |
| 6 | Numba-GA | Numba | Meta-sezgisel | ✅ | O(pop·gen·n) |
| 7 | Numba-PSO | Numba | Meta-sezgisel | ✅ | O(swarm·iter·n) |
| 8 | Numba-GWO | Numba | Meta-sezgisel | ✅ | O(pop·iter·n) |
| 9 | Numba-HHO | Numba | Meta-sezgisel | ✅ | O(pop·iter·n) |
| 10 | B-PSO | bildiri2026 | Meta-sezgisel | ✅ | O(swarm·iter·n) |
| 11 | B-GA | bildiri2026 | Meta-sezgisel | ✅ | O(pop·gen·n) |
| 12 | E2BSO-TSP | SOTA | Hibrit (Entropy+ALNS) | ✅ | O(pop·iter·n²) |
| 13 | E2BSO-TSP-CPSO | SOTA | Hibrit (Canonical PSO) | ✅ | O(pop·iter·n²) |
| 14 | R2DMA-TSP | SOTA | Hibrit (Rezonans+ALNS) | ✅ | O(pop·iter·n²) |
| 15 | P-AOEA-TSP | SOTA | Hibrit (Genom+ALNS) | ✅ | O(pop·iter·n²) |
| 16 | CGO-TSP | SOTA | Hibrit (Chaos Game+OX) | ✅ | O(pop·iter·n²) |
| 17 | RUN-TSP | SOTA | Hibrit (RK4+ESQ) | ✅ | O(pop·iter·n²) |

### 1.4 Sonuç Değerlendirme Sembolleri

| Sembol | GAP | Anlam |
|--------|-----|-------|
| ★ | ≤ 1% | Mükemmel (optimala çok yakın) |
| ✓ | ≤ 5% | İyi |
| ○ | ≤ 10% | Orta |
| ✗ | > 10% | Zayıf |

**Bilinmeyen optimal problemler için:** `BSF Gap` gösterilir — mevcut çalıştırmadaki en iyi çözüme göre relatif fark.

---

## 2. Kurulum ve Çalıştırma

### 2.1 Bağımlılıklar

```bash
pip install numpy numba scipy streamlit plotly pandas
```

### 2.2 Çalışma Modları

Her iki motor da iki modda çalışır:

| Mod | Açıklama | Kullanım |
|-----|----------|----------|
| **DEFAULT** | Adaptif varsayılan parametrelerle doğrudan benchmark | Final performans değerlendirmesi |
| **TUNING** | Parametre optimizasyonu → en iyi parametrelerle benchmark | Parametre optimizasyonu |

### 2.3 Tuning Stratejileri

TUNING modunda 3 strateji mevcuttur:

| Strateji | Açıklama | Avantaj | Dezavantaj |
|----------|----------|---------|------------|
| **[G] Grid Search** | Tüm kombinasyonları test eder, en iyi testi seçer | Kapsamlı, deterministik | Çok yavaş (kombinasyon sayısı üssel) |
| **[F] Fractional** | Grid'den random alt-örneklem | Daha hızlı | Optimal kombinasyonu kaçırabilir |
| **[B] Bayesian (Optuna)** | TPE surrogate model, test edilmemiş noktaları keşfeder | En iyi sonuç, arada değer bulur | Probabilistik, tekrarlar farklı sonuç verebilir |

**Optuna vs Response Surface (Design-Expert) Karşılaştırması:**

| Özellik | Optuna (TPE) | Response Surface (Design-Expert) |
|---------|-------------|----------------------------------|
| **Model** | Probabilistik (kernel density) | Deterministik (kuadratik polinom) |
| **Optimum konumu** | Uzayda herhangi bir yer | Kuadratik yüzey ile sınırlı |
| **Kategorik parametreler** | Doğal destek | Dummy değişkenler gerekir |
| **Doğrusal olmayan etkileşimler** | Karmaşık paternleri yakalar | Sadece kuadratik etkileşimler |
| **Örnek verimliliği** | Yüksek (adaptif örnekleme) | Yapılandırılmış tasarım noktaları gerekir |
| **Çıktı** | En iyi nokta + belirsizlik | Denklem: y = β₀ + Σβᵢxᵢ + Σβᵢᵢxᵢ² |

> **Not:** Meta-sezgisel algoritma tuning için Optuna genellikle daha iyidir çünkü yanıt yüzeyleri nadiren kuadratiktir — platolar, uçurumlar ve düzensiz bölgeler içerir. Pratikte Optuna, grid noktaları arasında arama yapabildiği ve kategorik parametreleri doğal olarak işleyebildiği için %5-15 daha iyi çözümler bulur. Response Surface yalnızca akademik analiz için analitik denklem gerekiyorsa eklenmelidir (örn. "population_size en güçlü ana etkiye sahiptir, β=0.42").

### 2.4 Problem Sıralama

Problemler boyutlarına göre küçükten büyüğe sıralanır:

```
[01] eil51      n=   51  Optimal: 426       [small ]
[02] berlin52   n=   52  Optimal: 7542      [small ]
[03] eil76      n=   76  Optimal: 538       [small ]
[04] kroA100    n=  100  Optimal: 21282     [small ]
...
[15] pr1002     n= 1002  Optimal: 259045    [large ]
```

Bu sıralama, kullanıcıların küçük problemlerle başlayıp kademeli olarak büyük problemlere geçmesini kolaylaştırır.

### 2.5 CLI Argümanları

| Argüman | Açıklama | Örnek |
|---------|----------|-------|
| `--mode` | Çalışma modu (`default` veya `tuning`) | `--mode default` |
| `--algos` | Virgülle ayrılmış algoritma listesi | `--algos GA,PSO,E2BSO-TSP` |
| `--problems` | Virgülle ayrılmış problem listesi | `--problems berlin52,eil51` |
| `--select` | Evrensel problem seçim sentaksı | `--select "small,medium"` |
| `--runs` | Tekrar sayısı | `--runs 5` |
| `--size-limit` | Maksimum problem boyutu | `--size-limit 200` |
| `--workers` | Paralel worker sayısı | `--workers 4` |

### 2.4 Örnek Komutlar

```bash
# Numba motoru — DEFAULT mod, GA+PSO, 3 tekrar, n≤150
python academic_benchmark/master_numba_engine.py --mode default --algos GA,PSO --runs 3 --size-limit 150

# SOTA motoru — TUNING mod, tüm algoritmalar
python academic_benchmark/master_sota_engine.py --mode tuning --runs 3

# Interaktif menü (varsayılan)
python academic_benchmark/master_numba_engine.py
python academic_benchmark/master_sota_engine.py
```

### 2.6 E2BSO-TSP vs E2BSO-TSP-CPSO

| Özellik | E2BSO-TSP (Edge-Heritage) | E2BSO-TSP-CPSO (Canonical PSO) |
|---------|--------------------------|-------------------------------|
| **Swarm Update** | Edge-force injection (3-5 kenar) | Swap-sequence velocity (v = w·v + c1·r1·Δpbest + c2·r2·Δgbest) |
| **Parametreler** | `p_best`, `p_gbest`, `n_edges` | `c1`, `c2`, `inertia`, `velocity_max_ratio` |
| **DoE Uzayı** | gamma, injection_rate, remove_ratio | c1:[1.0,1.5,2.0], c2:[1.0,1.5,2.0], inertia:[0.5,0.7,0.9] |
| **Kullanım** | TSP-native, kenar yapısına odaklı | Genel amaçlı, momentum tabanlı yakınsama |

---

## 3. Sonuç Yönetimi

### 3.1 Çıktı Dosyaları

| Dosya | Konum | İçerik |
|-------|-------|--------|
| `benchmark_summary.csv` | `sota_results/` veya `numba_results/` | Agrega sonuçlar (ortalama gap, süre) |
| `benchmark_progress.csv` | `sota_results/` veya `numba_results/` | Ham çalışma verileri (box-plot için) |
| `tuning_progress.csv` | `sota_results/doe_sota/` veya `numba_results/doe/` | DoE tarama sonuçları |
| `metadata.json` | `benchmark_db/` | Önbellek durumu, hash takibi |
| `smart_*.csv` | `benchmark_db/history/` | Convergence profilleri |
| `param_db.json` | `benchmark_db/` | En iyi parametre kayıtları |
| `tsplib.db` | `tsplib_data/` | SQLite: problemler, mesafe matrisleri, en iyi çözümler |

### 3.2 CSV Şemaları

**benchmark_summary.csv:**
```
problem, strategy, avg_length, avg_gap, avg_time_ms, n_runs
```

**benchmark_progress.csv:**
```
timestamp, problem, strategy, avg_length, avg_gap, avg_time_ms, n_runs, result_type, params_json
```
- `result_type = "raw"`: tekil çalışma (SOTA motoru)
- `result_type = "aggregate"`: parametre combo ortalaması (Numba motoru)

### 3.3 Önbellek ve Devam Ettirme

- `metadata.json` dosya hash'lerini takip eder — kod değişince otomatik yeniden test
- `skip_cached=True` ile tamamlanmış çalışmalar atlanır
- `Ctrl+C` ile güvenli çıkış — tamamlanan sonuçlar kaydedilir
- Yarım kalan çalışmalar `interrupted_*.csv` olarak kaydedilir

### 3.4 TSPLIB SQLite DB

`tsplib_manager.py` ile yönetilir:

```bash
# Problemleri arşivden çıkar (tek sefer)
python academic_benchmark/tsplib_manager.py extract

# Mesafe matrislerini önceden hesapla (tek sefer, ~5-15 dk)
python academic_benchmark/tsplib_manager.py compute-dm

# Durum kontrolü
python academic_benchmark/tsplib_manager.py status
```

DB tabloları:
- `problems`: problem metadata (ad, boyut, optimal, edge_weight_type)
- `coordinates`: düğüm koordinatları
- `distance_matrices`: önceden hesaplanmış mesafe matrisleri (zlib sıkıştırılmış)
- `opt_tours`: bilinen optimal turlar
- `best_solutions`: benchmark sırasında bulunan en iyi çözümler

---

## 4. Developer Guide

### 4.1 Yeni Algoritma Ekleme (5 Adım)

**Adım 1:** Solver sınıfını yazın (`sota_tsp/yeni_algo.py` veya `bildiri2026/core/yeni_algo.py`)

```python
from .base_solver import BaseTSPSolver, TSPResult

@dataclass
class YeniAlgoConfig:
    population_size: int = 40
    max_iterations: int = 500
    seed: int = 42

class YeniAlgo(BaseTSPSolver):
    def __init__(self, config=None):
        super().__init__("YeniAlgo", config.seed if config else 42)
        self.cfg = config or YeniAlgoConfig()

    def solve(self, coordinates):
        self._set_problem(coordinates)
        # ... algoritma implementasyonu ...
        return TSPResult(algorithm="YeniAlgo", tour=best, tour_length=best_cost, ...)
```

**Adım 2:** `sota_tsp/__init__.py` (veya `bildiri2026/core/__init__.py`) içine export ekleyin

```python
from .yeni_algo import YeniAlgo, YeniAlgoConfig
__all__ = [..., "YeniAlgo", "YeniAlgoConfig"]
```

**Adım 3:** `master_sota_engine.py` (veya `master_numba_engine.py`) içinde:

```python
# ALL_ALGOS listesine ekle
ALL_ALGOS = [..., "YENI-ALGO"]

# _make_solver_config'e ekle
"YENI-ALGO": {"population_size": pop, "max_iterations": max_iter, ...}

# _build_sota_parameter_space'e ekle
if algo_name == "YENI-ALGO":
    return {"population_size": [24, 36, 48], ...}

# _make_solver factory'e ekle
if algo_name == "YENI-ALGO":
    return YeniAlgo(YeniAlgoConfig(seed=seed, **cfg))
```

**Adım 4:** Test yazın (`tests/test_yeni_algo.py`)

**Adım 5:** Testleri çalıştırın

```bash
python -m pytest academic_benchmark/tests/ -v --tb=short
```

### 4.2 Yeni Problem Ekleme

TSPLIB problemleri `ALL_tsp.tar.gz` arşivinden otomatik yüklenir. Manuel eklemek için:

```bash
# Tek bir problem ekle
python academic_benchmark/tsplib_manager.py extract --problems berlin52

# Boyut limiti ile
python academic_benchmark/tsplib_manager.py extract --size-limit 200
```

Özel time_matrix JSON problemleri için `academic_benchmark/data/` klasörüne JSON dosyası ekleyin.

### 4.3 Test Çalıştırma

```bash
# Tüm testler
python -m pytest academic_benchmark/tests/ -v --tb=short

# Belirli test dosyası
python -m pytest academic_benchmark/tests/test_sota_e2e.py -v

# Coverage ile
python -m pytest academic_benchmark/tests/ --cov=academic_benchmark
```

### 4.4 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `ImportError: No module named ...` | Proje kökünden çalıştırın (`cd UniRide`) |
| `Gap: ERR` veya `nan` | Problem `TSPLIB_OPTIMALS` dict'inde yok — BSF Gap gösterilir |
| `Matrix comes back None` | `tsplib_manager.py compute-dm` çalıştırın |
| `Numba compilation error` | `pip install --upgrade numba numpy` |
| `ProcessPoolExecutor hang` | `--workers 1` ile tek worker deneyin |
| `Streamlit dashboard açılmıyor` | `pip install streamlit plotly scipy` |

---

## 5. Görselleştirme (Dashboard)

### 5.1 Çalıştırma

```bash
streamlit run academic_benchmark/dashboard.py
```

Veya engine menüsünden `[D] Dashboard` seçeneğini kullanın.

### 5.2 Sekmeler

| Sekme | İçerik |
|-------|--------|
| 🏆 **Leaderboard & LaTeX** | Performans özeti, en iyi değerler yeşil, LaTeX export |
| 📊 **Statistical Robustness** | Box-plot ile varyans analizi (çoklu çalıştırma verisi) |
| 🎛️ **DoE Parameter Analysis** | Parametre tarama sonuçları, scatter plot |
| 🔬 **Wilcoxon Test** | Pairwise istatistiksel anlamlılık testi (p < 0.05) |
| 📉 **Convergence Curves** | İterasyon bazlı yakınsama grafikleri |
| ⚔️ **Algorithm Comparison** | Pairwise gap karşılaştırma matrisi (all vs all) |

### 5.3 LaTeX Export

Dashboard otomatik olarak makale-hazır LaTeX tabloları üretir:
- `booktabs` formatı (journal için)
- `longtable` formatı (çok satır için)
- En iyi değerler `\textbf{}` ile vurgulanır
- Wilcoxon test sonuçları LaTeX formatında

---

## 6. Academic Methodology (English)

### 6.1 Classical Paper Methodology

*The following section is adapted from `CLASSICAL_PAPER_METHODOLOGY.md` and is ready for inclusion in academic publications.*

To rigorously evaluate the performance of classical meta-heuristic algorithms (e.g., Genetic Algorithm, Particle Swarm Optimization, Grey Wolf Optimizer, and Harris Hawks Optimization) on the Traveling Salesman Problem (TSP), a custom, high-performance computational infrastructure was developed. This custom-built "Numba-Accelerated Benchmark Engine" was designed to bridge the gap between high-level algorithmic flexibility and low-level computational efficiency, establishing a standardized environment for fair comparative analysis.

#### 6.1.1 JIT-Optimized Meta-heuristic Implementation

A primary challenge in benchmarking complex meta-heuristics using high-level interpreted languages, such as Python, is the inherent execution overhead that can skew computational time analyses. To resolve this, the proposed framework integrates Just-In-Time (JIT) compilation technology via the Numba library. Core algorithmic routines, including fitness evaluations, population updates, and local search operations, were compiled directly into optimized machine code (`@njit(nogil=True)`). This approach effectively eliminated interpreter latency, achieving execution speeds comparable to native C++ implementations while preserving the dynamic adaptability required for algorithmic modifications.

To maintain strict computational rigor, a mandatory "Warm-up" protocol was instituted. Since JIT compilation requires an initial overhead during the first execution of any compiled function, this compilation time was explicitly isolated and excluded from all benchmark measurements. Consequently, the reported execution times strictly reflect the mathematical efficiency and convergence speed of the algorithms, rather than the underlying language mechanics.

#### 6.1.2 Parameter Standardization via Design of Experiments

In heuristic-based optimization, algorithm performance is highly sensitive to hyperparameter configurations. To eliminate human bias and prevent overfitting to specific problem topologies, hyperparameters were neither manually selected nor randomly assigned. Instead, a rigorous "Design of Experiments" (DoE) methodology was implemented.

Prior to the formal benchmarking phase, a dedicated DoE module performed a systematic grid search across the multidimensional parameter space of each algorithm. This procedure evaluated various combinations of parameters across a representative subset of TSPLIB instances. The configurations yielding the optimal balance between solution quality (gap percentage) and convergence stability were extracted and uniformly applied during the final evaluation phase.

#### 6.1.3 Parallel Execution and Computational Stability

Given the combinatorial explosion inherent to the TSP and the necessity for statistically significant trial repetitions, the framework was engineered for massive scalability. A robust, Windows-safe parallel processing architecture was deployed utilizing a `ProcessPoolExecutor`. Unlike traditional multi-processing models that are prone to memory leaks and synchronization deadlocks on certain operating systems, this isolated memory-space approach ensured high throughput and process stability across multi-core architectures.

Furthermore, strict protocols for data integrity and reproducibility were established. An incremental result persistence mechanism was designed to log experimental outputs (e.g., route lengths, convergence gaps, and execution times) into distinct Comma-Separated Values (CSV) files in real time. This was coupled with a metadata-driven state management system (`metadata.json`) that continuously tracked the execution status of the benchmark matrix.

### 6.2 SOTA Paper Methodology

*The following section is adapted from `SOTA_PAPER_METHODOLOGY.md` and is ready for inclusion in academic publications.*

To ensure a high-fidelity evaluation of complex, modern solvers for the Traveling Salesman Problem (TSP)—specifically State-of-the-Art (SOTA) algorithms such as E²BSO, R²DMA, P-AOEA, CGO, and RUN—a custom "Unified SOTA Benchmark Engine" was conceptualized and developed.

#### 6.2.1 Unified Evaluation Framework for SOTA Solvers

Evaluating SOTA algorithms necessitates an architecture that accommodates significant variations in algorithmic complexity, structural memory footprints, and search paradigms. The developed framework employs a consolidated architectural pattern, standardizing the input-output interfaces across entirely different solver topologies.

To bridge the operational differences between these algorithms, an adaptive evaluation methodology was introduced. This methodology incorporates dynamically assigned local search budgets and time-matrix integrations, ensuring that algorithms are not only tested under idealized distance models but also under realistic, varied constraint scenarios.

#### 6.2.2 Algorithmic Adaptations for Large-Scale Stability

While the core generative mechanisms and mathematical operators of E²BSO, R²DMA, P-AOEA, CGO, and RUN were strictly preserved to ensure theoretical fidelity, several critical architectural adaptations were engineered to facilitate large-scale, production-grade execution:

1. **Adaptive Local Search Budgets:** Canonical implementations frequently rely on unbounded local search neighborhoods. On massive instances (exceeding 1,000 nodes), this induces a combinatorial explosion (O(N²) to O(N³)), leading to severe computational deadlocks. To resolve this, a dimension-adaptive budget manager was integrated, dynamically bounding search depths based on the problem size (N).

2. **Distance Metric Agnosticism (Asymmetric Capability):** Original SOTA solvers are predominantly hardcoded to process symmetric 2D Euclidean spatial graphs. Our framework abstracts the evaluation objective function entirely, rendering the solvers "metric agnostic." This adaptation allows the algorithms to seamlessly transition from standard TSPLIB Euclidean calculations to processing custom, non-Euclidean, and asymmetric real-world transit networks.

3. **Dynamic Parameter Abstraction:** In conventional academic codebases, hyperparameters are typically hardcoded or statically assigned. Our implementation entirely decoupled the hyperparameter definitions from the core solver logic. By abstracting variables into a dynamic `StrategySpec` payload, the algorithms were rendered fully compatible with our external Design of Experiments (DoE) module.

---

## 7. Roadmap & Future Work

### 7.1 RL Parameter Control (Öncelikli — 3. Makale Adayı)

**Durum:** Tasarım aşamasında. Detaylar için `.opencode/plans/2026-05-15-docs-dashboard-roadmap-plan.md`

**Özet:** Q-Learning tabanlı dinamik parametre adaptasyonu. Algoritma çalışırken stagnasyon, çeşitlilik ve gap durumuna göre mutation rate, popülasyon boyutu ve local search bütçesini otomatik ayarlar.

**Mimari:**
- **State space:** 144 durum (çeşitlilik × stagnasyon × gap × ilerleme)
- **Action space:** 6 aksiyon (↑mutation, ↓mutation, ↑ls, ↓ls, ↑exploration, ↓exploration)
- **Reward:** `-Δgap` (iyileşme = pozitif ödül)

**Tahmini süre:** 2-3 hafta
**Makale potansiyeli:** Yüksek — RL tabanlı meta-sezgisel kontrol TSP literatüründe az çalışılmış bir alandır.

### 7.2 LKH-3 Entegrasyonu (Gelecek Çalışma Notu)

**Durum:** Düşük öncelikli, not olarak saklanmıştır.

**Özet:** Lin-Kernighan-Helsgaun (LKH-3) heuristic'inin local search operatörü olarak entegrasyonu.

**Değerlendirme:**
- n > 2000 problemlerde ~1-2% gap iyileştirmesi beklenir
- C tabanlı, wrapper gerektirir
- Mevcut SOTA algoritmalar n ≤ 1000'de zaten rekabetçi sonuçlar veriyor
- **Öneri:** Makale odaklı çalışmalar için gerekli değil, büyük ölçekli endüstriyel uygulamalar için değerlendirilebilir

### 7.3 GPU Hızlandırma (Düşük Öncelik)

**Durum:** Öncelik dışı.

**Değerlendirme:**
- Numba CUDA (`@cuda.jit`) ile fitness eval loop'larının GPU'ya taşınması
- NVIDIA GPU gerektirir
- TSP'de bottleneck local search (memory-bound), fitness compute (compute-bound) değil
- **Öneri:** ROI düşük — CPU Numba JIT zaten yeterli performans sağlıyor

---

## 8. Versiyon Geçmişi

| Versiyon | Tarih | Değişiklikler |
|----------|-------|---------------|
| 3.3 | 2026-05-16 | 3 tuning stratejisi (Grid/Fractional/Bayesian), Optuna SOTA'ya eklendi, problem boyut sıralaması |
| 3.2 | 2026-05-16 | RUN-TSP eklendi (Runge Kutta Optimizer), 17 algoritma, metaphor-free solver |
| 3.1 | 2026-05-16 | CGO-TSP eklendi (Chaos Game Optimization), 16 algoritma, 45 test |
| 3.0 | 2026-05-15 | Çift motor mimari, 15 algoritma, CPSO variant, BSF fallback, Streamlit dashboard, RL roadmap |
| 2.0 | 2026-05-09 | SOTA engine konsolidasyonu, DoE tuning, ProcessPoolExecutor |
| 1.0 | 2026-04-06 | İlk benchmark sistemi, V1/V2, multiprocessing |

---

*Bu dokümantasyon 2026-05-16 tarihinde güncellenmiştir (v3.3).*
