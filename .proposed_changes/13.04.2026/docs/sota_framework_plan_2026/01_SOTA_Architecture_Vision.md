# UniRide SOTA Framework Plan — Architecture Vision (2026)

> **Belge:** SOTA Framework Plan #1  
> **Tarih:** 2026-04  
> **Durum:** Draft  
> **Yazar:** UniRide Optimizer Team

---

## Bölüm 1: Dual-Track Mimari Vizyonu

UniRide optimizer sistemi **iki paralel iz (track)** üzerine kuruludur. Bu yapı, hem ticari
ürün stabilitesini hem de akademik araştırma özgürlüğünü aynı anda sağlar.

```
┌─────────────────────────────────────────────────────────────────┐
│                    UniRide OPTIMIZER SYSTEM                     │
│                                                                 │
│  ┌──────────────────────────┐  ┌───────────────────────────┐   │
│  │   COMMERCIAL TRACK       │  │   ACADEMIC TRACK          │   │
│  │   (Production / Live)    │  │   (Research / Paper)      │   │
│  │                          │  │                           │   │
│  │  Pipeline A: Cluster-    │  │  ALNS (Planlanan)         │   │
│  │    First Route-Second    │  │  LinearSplit              │   │
│  │                          │  │  Smart Benchmark          │   │
│  │  Pipeline B: Route-      │  │  TSPLIB Compliance        │   │
│  │    First Cluster-Second  │  │  SHA256 Cache             │   │
│  │                          │  │                           │   │
│  │  SOTA Solvers            │  │  CLI Benchmark Tools      │   │
│  │  Heuristics              │  │                           │   │
│  │  Local Search (Numba)    │  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │   │
│  └────────────┬─────────────┘  └────────────┬──────────────┘   │
│               │                             │                   │
│  ┌────────────▼─────────────────────────────▼──────────────┐   │
│  │              SHARED INFRASTRUCTURE                      │   │
│  │  models/schemas.py | benchmark_runner.py | strategies/  │   │
│  │  utils/local_search_numba.py | utils/tsplib_parser.py  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Bölüm 1.1: Commercial Track (Live / Production)

Commercial Track, canlı prodüksiyon ortamında çalışan **stabil hybrid algoritmalar** içerir.
Bu algoritmalar gerçek kullanıcı rotaları için optimize edilmiştir ve UniRide web uygulaması
üzerinden erişilebilir.

### Pipeline A: Cluster-First, Route-Second

İlk önce kümeleme, sonra her küme için rota optimizasyonu yapılır.
Sweep / Clarke-Wright gibi klasik kümeleme stratejileri kullanılır.

| Algoritma | Strategy ID | Dosya | Durum |
|-----------|-------------|-------|-------|
| Genetic Algorithm | `ga` / `genetic_algorithm` | `strategies/ga_strategy.py` | ✅ AKTİF |
| PSO | `pso` | `strategies/pso_strategy.py` | ✅ AKTİF |
| GWO (Grey Wolf) | `gwo` / `grey_wolf` | `strategies/gwo_strategy.py` | ✅ AKTİF |
| HHO (Harris Hawks) | `hho` / `harris_hawks` | `strategies/hho_strategy.py` | ✅ AKTİF |

**Akış:**
```
Kullanici Istekleri → Sweep/CW Clustering → Her Kume icin Metaheuristic → Route Plan
```

### Pipeline B: Route-First, Cluster-Second (Split)

Tüm düğümleri tek dev bir giant tour olarak optimize eder, ardından Split Decoder
ile araç kapasitesine göre bölümler.

| Algoritma | Strategy ID | Dosya | Durum |
|-----------|-------------|-------|-------|
| GA + Split | `ga_split` | `strategies/ga_split_strategy.py` | ✅ AKTİF |
| PSO + Split | `pso_split` | `strategies/pso_split_strategy.py` | ✅ AKTİF |
| GWO + Split | `gwo_split` | `strategies/gwo_split_strategy.py` | ✅ AKTİF |
| HHO + Split | `hho_split` | `strategies/hho_split_strategy.py` | ✅ AKTİF |

**Akış:**
```
Kullanici Istekleri → Giant Tour (Metaheuristic) → Optimal Split Decoder → Route Plan
```

### SOTA Baseline Solvers

Endüstri standardı CVRP solver'ları. Commercial ve Academic track'lerde ortak kullanılır.

| Solver | Strategy ID | Dependency | Durum |
|--------|-------------|------------|-------|
| Google OR-Tools CVRP | `ortools_cvrp` / `ortools` | `ortools` (required) | ✅ AKTİF |
| PyVRP (HGS) | `pyvrp` / `hgs` | `pyvrp` (optional) | ⚠️ Optional |
| VROOM | `vroom` | `vroom` (optional) | ⚠️ Optional |

**Not:** PyVRP ve VROOM yüklü değilse OR-Tools'a fallback yapılır.
Kontroller `strategies/__init__.py` dosyasında `try/except` bloğu ile yapılır.

### Heuristics

| Algoritma | Strategy ID | Dosya | Karmaşıklık | Durum |
|-----------|-------------|-------|-------------|-------|
| Greedy / NN | `greedy` / `nearest_neighbor` | `strategies/greedy_heuristic.py` | O(n²) | ✅ AKTİF |
| Two-Opt | `two_opt` / `2opt` | `strategies/two_opt_strategy.py` | O(n²) | ✅ AKTİF |
| Permutation TSP | `permutation_tsp` / `exact` | `strategies/permutation_tsp.py` | O(n!) | ✅ AKTİF |

### Local Search Engine (Numba JIT)

`utils/local_search_numba.py` dosyasında Numba JIT derlemesi ile 10-50x hız artışı sağlanır.

| Operator | Karmaşıklık | GAP Beklenti | Durum |
|----------|-------------|--------------|-------|
| 2-opt | O(n²) | %3-10 | ✅ JIT |
| 3-opt | O(n³) | %1-5 | ✅ JIT |
| Or-opt | O(n²) | %2-8 | ✅ JIT |
| Swap | O(n²) | %5-15 | ✅ JIT |
| Cross Exchange | O(n²) | %2-6 | ✅ JIT |
| Time Window Aware | O(n²) | CVRPTW专用 | ✅ JIT |
| **Hybrid** (Sequential) | O(n³) | **%0.5-3** | ✅ JIT |

**Hybrid Sırası:** Swap → 2-opt → Or-opt → Cross Exchange → 3-opt → TW-Aware

---

## Bölüm 1.2: Academic Track (Research / Paper)

Academic Track, uluslararası makale yayınlanması için SOTA algoritma geliştirme
amaçlıdır. CLI benchmark araçları ve TSPLIB standard uyumlu test altyapısı içerir.

### Akademik Altyapı Özeti

```
┌──────────────────────────────────────────────────────────┐
│                ACADEMIC BENCHMARK PIPELINE               │
│                                                          │
│  run_smart_benchmark_numba.py                           │
│       │                                                  │
│       ▼                                                  │
│  run_interactive_benchmark_v2_numba.py                  │
│       │                                                  │
│       ▼                                                  │
│  local_search_numba.py  ← Numba JIT Core                │
│       │                                                  │
│       ▼                                                  │
│  46 TSPLIB Problemleri  (EUC_2D NINT)                   │
│       │                                                  │
│       ▼                                                  │
│  SHA256 Hash Cache Invalidation                         │
│       │                                                  │
│       ▼                                                  │
│  JSON/CSV Output → benchmark_results/                    │
└──────────────────────────────────────────────────────────┘
```

### Mevcut Akademik Komponentler

| Komponent | Dosya | Durum | Açıklama |
|-----------|-------|-------|----------|
| Smart Benchmark | `tests/run_smart_benchmark_numba.py` | ✅ Çalışıyor | Interactive CLI, multiprocessing |
| Interactive Benchmark v2 | `tests/run_interactive_benchmark_v2_numba.py` | ✅ Çalışıyor | Numba JIT test koşucusu |
| Local Search Numba | `utils/local_search_numba.py` | ✅ Çalışıyor | JIT compiled operators |
| TSPLIB Parser | `utils/tsplib_parser.py` | ✅ Çalışıyor | EUC_2D NINT rounding |
| Dataset Loader | `tests/dataset_loader.py` | ✅ Çalışıyor | TSPLIB dosya yükleme |
| Utility Benchmark | `tests/utils_benchmark.py` | ✅ Çalışıyor | Metadata & SHA256 cache |
| TSPLIB Data | `tests/tsplib_data/` (46 dosya) | ✅ Mevcut | Küçük/Orta/Büyük kategoriler |

### ALNS — Henüz Uygulanmadı

| Komponent | Durum | Öncelik |
|-----------|-------|---------|
| ALNS Framework | ❌ NOT IMPLEMENTED | 🔴 HIGH |
| Destroy Operators | ❌ Planlanıyor | 🔴 HIGH |
| Repair Operators | ❌ Planlanıyor | 🔴 HIGH |
| Adaptive Weights | ❌ Planlanıyor | 🟡 MEDIUM |

> ALNS geliştirme planı detayları için bkz: `02_ALNS_Development_Plan.md`

### TSPLIB Standard Uyumluluk

```
Mesafe Fonksiyonu (EUC_2D):
  d(i,j) = NINT( sqrt( (xi - xj)² + (yi - yj)² ) )

NINT = En yakın tam sayıya yuvarlama (TSPLIB standard)
Bu fonksiyon: utils/tsplib_parser.py → tsplib_euc_2d_distance()
```

### SHA256 Hash-Based Cache Invalidation

Benchmark sonuçları algoritma dosyasının SHA256 hash'ine göre invalidate olur:

```python
# utils_benchmark.py
# ALGORITHMS_TO_CHECK sözlüğü ile takip edilen dosyalar:
ALGORITHMS_TO_CHECK = {
    "LocalSearchEngine_NUMBA": "utils/local_search_numba.py",
}
# Dosya değiştiğinde → tüm cache temizlenir → yeniden benchmark
```

### Benchmark Sonuç Formatları

**CLI Benchmark JSON:**
```json
{
  "task_id": 1,
  "problem": "berlin52",
  "dimension": 52,
  "category": "small",
  "optimal": 7542,
  "strategy": "Hybrid",
  "avg_length": 7680.5,
  "avg_gap": 1.83,
  "best_length": 7612.0,
  "best_gap": 0.93,
  "avg_time_ms": 145.2,
  "n_runs": 3,
  "numba_optimized": true
}
```

**Web Benchmark (ExperimentResult):**
```python
@dataclass
class ExperimentResult:
    algorithm: str
    problem: str
    run_number: int
    tour_length: float
    elapsed_ms: float
    gap_percent: Optional[float]
    timestamp: str
    metadata: Dict
```

---

## Bölüm 1.3: Akademik Makale Hedefleri

### Performance Comparison Paper

| Kriter | Gereksinim |
|--------|-----------|
| **Hedef Dergi** | Uluslararası hakemli dergi / konferans |
| **Problem Set** | TSPLIB standard, 46+ problem |
| **Baseline Karşılaştırma** | OR-Tools, PyVRP (zorunlu) |
| **Gap Hesaplama** | `(found - optimal) / optimal × 100` |
| **Tekrarlanabilirlik** | Seed control, deterministic runs |
| **Çalışma Süresi** | Makul time limit (ör: 30sn-5dk) |
| **Metrikler** | GAP%, süre (ms), başarı oranı |

### SOTA Karşılaştırma Tablosu (Hedef)

| Algoritma | Tür | Küçük GAP% | Orta GAP% | Büyük GAP% | Hız |
|-----------|-----|-----------|----------|-----------|-----|
| OR-Tools CVRP | Baseline | ~0% | ~2% | ~5% | Hızlı |
| PyVRP (HGS) | Baseline | ~0% | ~1% | ~3% | Orta |
| UniRide Hybrid LS | Ours | ~1% | ~3% | ~5% | Çok Hızlı |
| UniRide ALNS | Ours (plan) | ~0% | ~1% | ~2% | Orta |

---

## Bölüm 1.4: CLI Benchmark vs Web Benchmark

İki ayrı benchmark sistemi vardır. Farklı kod yolları, farklı sonuç formatları.

```
┌─────────────────────────────────────────────────────────────┐
│                    BENCHMARK SYSTEMS                         │
│                                                             │
│  ┌─── CLI BENCHMARK ─────────────────────────────────────┐  │
│  │                                                       │  │
│  │  run_smart_benchmark_numba.py                        │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  run_interactive_benchmark_v2_numba.py               │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  local_search_numba.py (Direct Call)                 │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  Output: JSON + CSV → benchmark_results/              │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── WEB BENCHMARK ────────────────────────────────────┐  │
│  │                                                       │  │
│  │  main.py (FastAPI)                                   │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  benchmark_runner.py (BenchmarkRunner)               │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  strategies/ (via STRATEGY_REGISTRY)                 │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  benchmark_state.py (Progress Tracking)              │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  Output: ExperimentResult → Web UI / API             │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── IMPORT BRIDGE (CLI → Web) ────────────────────────┐  │
│  │  3 API endpoint ile CLI JSON → Web ExperimentResult  │  │
│  │  /api/benchmark/run | /status | /stop                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Farklar Tablosu

| Özellik | CLI Benchmark | Web Benchmark |
|---------|---------------|---------------|
| **Giriş** | Interaktif CLI menüsü | Web UI / REST API |
| **Algoritmalar** | Local Search (2-opt, 3-opt, Hybrid...) | Tüm strategies (GA, PSO, HHO, OR-Tools...) |
| **Paralellik** | multiprocessing Pool | asyncio + daemon thread |
| **Progress** | Terminal progress bar | benchmark_state.py + polling |
| **Output** | JSON + CSV dosyaları | ExperimentResult dataclass → API |
| **Numba** | Doğrudan çağrı | Strategy üzerinden间接 |
| **Cache** | SHA256 hash-based | Web state manager |
| **Kullanım** | Akademik araştırma | Canlı demo / karşılaştırma |

---

## Bölüm 1.5: Algoritma Karşılaştırma Tablosu (Tümü)

| # | Algoritma | Pipeline | Tür | Numba | TSP | CVRP | CVRPTW | Durum |
|---|-----------|----------|-----|-------|-----|------|--------|-------|
| 1 | GA | A | Metaheuristic | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 2 | PSO | A | Metaheuristic | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 3 | GWO | A | Metaheuristic | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 4 | HHO | A | Metaheuristic | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 5 | GA+Split | B | Metaheuristic+Split | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 6 | PSO+Split | B | Metaheuristic+Split | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 7 | GWO+Split | B | Metaheuristic+Split | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 8 | HHO+Split | B | Metaheuristic+Split | ❌ | ✅ | ✅ | ⚠️ | ✅ Aktif |
| 9 | OR-Tools | Holistic | MIP Solver | ❌ | ❌ | ✅ | ✅ | ✅ Aktif |
| 10 | PyVRP (HGS) | Holistic | ALNS-based | ❌ | ❌ | ✅ | ⚠️ | ⚠️ Optional |
| 11 | VROOM | Holistic | C++ Solver | ❌ | ❌ | ✅ | ✅ | ⚠️ Optional |
| 12 | Greedy/NN | Heuristic | Construction | ❌ | ✅ | ✅ | ✅ | ✅ Aktif |
| 13 | Two-Opt | Heuristic | Local Search | ✅ | ✅ | ✅ | ✅ | ✅ Aktif |
| 14 | Permutation TSP | Heuristic | Exact (n≤10) | ❌ | ✅ | ❌ | ❌ | ✅ Aktif |
| 15 | 2-opt (Numba) | CLI | Local Search | ✅ | ✅ | ❌ | ❌ | ✅ Aktif |
| 16 | 3-opt (Numba) | CLI | Local Search | ✅ | ✅ | ❌ | ❌ | ✅ Aktif |
| 17 | Hybrid LS (Numba) | CLI | Hybrid | ✅ | ✅ | ❌ | ❌ | ✅ Aktif |
| 18 | **ALNS** | **Academic** | **Metaheuristic** | ❌ | ❌ | ✅ | ✅ | **❌ Planlanan** |

---

## Bölüm 1.6: Implementation Status Dashboard

```
COMMERCIAL TRACK                     ████████████████████ 100%
├─ Pipeline A (Cluster-First)        ████████████████████ 100%  (4/4)
├─ Pipeline B (Route-First/Split)    ████████████████████ 100%  (4/4)
├─ SOTA Solvers                      ████████████████░░░░  67%  (2/3)
├─ Heuristics                        ████████████████████ 100%  (3/3)
└─ Local Search Numba                ████████████████████ 100%  (7/7)

ACADEMIC TRACK                       ████████████░░░░░░░░  60%
├─ TSPLIB Infrastructure             ████████████████████ 100%  (46 problems)
├─ Benchmark CLI Tools               ████████████████████ 100%
├─ SHA256 Cache Invalidation         ████████████████████ 100%
├─ EUC_2D NINT Compliance            ████████████████████ 100%
├─ Interactive Benchmark              ████████████████████ 100%
├─ JSON/CSV Output                   ████████████████████ 100%
├─ ALNS Framework                    ░░░░░░░░░░░░░░░░░░░░   0%  (NOT IMPLEMENTED)
└─ LinearSplit Optimization          ██████████████░░░░░░  70%

IMPORT BRIDGE                        ████████████████████ 100%
├─ /api/benchmark/run                ████████████████████ 100%
├─ /api/benchmark/status             ████████████████████ 100%
└─ /api/benchmark/stop               ████████████████████ 100%
```

---

## Bölüm 1.7: Önerilen Strateji Seçimi (Literatür-Based)

`strategies/__init__.py` → `get_recommended_strategy()` fonksiyonuna dayalı:

| Problem Büyüklüğü | Speed Öncelikli | Quality Öncelikli | Dengeli |
|-------------------|-----------------|-------------------|--------|
| N ≤ 30 | VROOM → PSO+Split | GA+Split | PSO+Split |
| 30 < N ≤ 100 | PSO | PyVRP → GA+Split | HHO+Split |
| N > 100 | VROOM → OR-Tools | PyVRP → OR-Tools | OR-Tools |

---

## Bölüm 1.8: Teknik Borç (Technical Debt) Özeti

| # | Madde | Öncelik | Tahmini Efor |
|---|-------|---------|-------------|
| 1 | **ALNS Implementation** | 🔴 CRITICAL | 3-4 hafta |
| 2 | **LinearSplit optimization** | 🟡 HIGH | 1 hafta |
| 3 | **CLI ↔ Web Benchmark birleştirme** | 🟡 MEDIUM | 2 hafta |
| 4 | **PyVRP entegrasyon testleri** | 🟢 LOW | 3 gün |
| 5 | **CVRPTW time window handling** | 🟡 HIGH | 1 hafta |
| 6 | **Makale benchmark pipeline** | 🔴 HIGH | 2 hafta |

---

## Bölüm 1.9: Dosya Yapısı Referansı

```
optimizer_api/
├── main.py                          # FastAPI web sunucusu
├── benchmark_runner.py              # Web benchmark koşucusu
├── benchmark_state.py               # Benchmark progress state
├── strategies/
│   ├── __init__.py                  # Strategy Registry (15+ algorithm)
│   ├── base_strategy.py             # BaseRoutingStrategy
│   ├── hybrid_base_strategy.py      # Hybrid base class
│   ├── ga_strategy.py               # Pipeline A: GA
│   ├── pso_strategy.py              # Pipeline A: PSO
│   ├── gwo_strategy.py              # Pipeline A: GWO
│   ├── hho_strategy.py              # Pipeline A: HHO
│   ├── ga_split_strategy.py         # Pipeline B: GA+Split
│   ├── pso_split_strategy.py        # Pipeline B: PSO+Split
│   ├── gwo_split_strategy.py        # Pipeline B: GWO+Split
│   ├── hho_split_strategy.py        # Pipeline B: HHO+Split
│   ├── ortools_cvrp.py              # SOTA: OR-Tools
│   ├── pyvrp_strategy.py            # SOTA: PyVRP (optional)
│   ├── vroom_strategy.py            # SOTA: VROOM (optional)
│   ├── greedy_heuristic.py          # Heuristic: Greedy/NN
│   ├── two_opt_strategy.py          # Heuristic: Two-Opt
│   ├── permutation_tsp.py           # Heuristic: Exact TSP
│   └── cvrptw_wrapper.py            # CVRPTW adapter
├── utils/
│   ├── local_search_numba.py        # Numba JIT local search
│   ├── local_search.py              # Pure Python local search
│   ├── tsplib_parser.py             # TSPLIB EUC_2D parser
│   ├── linear_split_decoder.py      # LinearSplit decoder
│   ├── split_decoder.py             # Optimal Split decoder
│   ├── clustering.py                # Clustering utilities
│   ├── data_loader.py               # Data loading
│   └── constants.py                 # Constants
├── models/
│   └── schemas.py                   # Pydantic models
└── tests/
    ├── run_smart_benchmark_numba.py        # CLI: Smart Benchmark
    ├── run_interactive_benchmark_v2_numba.py # CLI: Interactive v2
    ├── run_interactive_benchmark_v2.py      # CLI: Non-Numba fallback
    ├── utils_benchmark.py                   # CLI: SHA256 cache utils
    ├── dataset_loader.py                    # CLI: TSPLIB loader
    ├── tsplib_data/                         # 46 TSPLIB .tsp files
    └── benchmark_results/                   # JSON/CSV output
```

---

> **Sonraki Belge:** `02_ALNS_Development_Plan.md` — ALNS geliştirme planı detayları
