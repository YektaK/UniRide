# Academic Benchmark Geliştirici Kılavuzu

## 📋 Özet

Bu doküman, UniRide/DOURide projesindeki **tüm optimizasyon algoritmalarını** kapsayan kapsamlı bir akademik benchmark sistemi oluşturmak için hazırlanmıştır. Mevcut NUMBA-optimized local search benchmark yapısı korunarak, sezgisel (meta-heuristic) algoritmalar eklenmelidir.

---

## 🎯 Hedef

Tek bir benchmark çalıştırma dosyası ile:
- **Local Search Algoritmaları** (NUMBA optimized): 2-opt, 3-opt, Or-opt, Swap, Hybrid
- **Meta-Heuristic Algoritmalar**: GA, PSO, GWO, HHO
- **Hibrit Yaklaşımlar**: Local Search + Meta-Heuristic kombinasyonları

TSPLIB problemleri üzerinde karşılaştırılmalı performans analizi yapmak.

---

## 📁 Mevcut Proje Yapısı

```
DOURide/
├── academic_benchmark/
│   ├── run_smart_benchmark_numba.py    # Ana benchmark runner (GÜNCELLENECEK)
│   ├── utils_benchmark.py              # Metadata, cache utilities
│   ├── dataset_loader.py               # TSPLIB loader
│   └── benchmark_db/
│       ├── latest_metadata_numba.json  # Cache'lenmiş sonuçlar
│       └── history/                    # Geçmiş CSV/JSON sonuçlar
│
├── optimizer_api/
│   ├── tests/
│   │   └── run_interactive_benchmark_v2_numba.py  # STRATEGIES tanımı burada
│   │
│   ├── strategies/
│   │   ├── ga_strategy.py              # Genetic Algorithm
│   │   ├── pso_strategy.py             # Particle Swarm Optimization
│   │   ├── gwo_strategy.py             # Grey Wolf Optimizer
│   │   ├── hho_strategy.py             # Harris Hawks Optimization
│   │   └── __init__.py
│   │
│   └── utils/
│       └── local_search_numba.py       # NUMBA JIT local search
```

---

## 🔧 Mevcut Benchmark Mimarisi

### 1. STRATEGIES Yapısı (run_interactive_benchmark_v2_numba.py)

```python
# Satır 63-69
STRATEGIES = [
    ("2-opt", LocalSearchType.TWO_OPT, 2000),    # (isim, tip, max_iterations)
    ("3-opt", LocalSearchType.THREE_OPT, 200),
    ("Or-opt", LocalSearchType.OR_OPT, 1000),
    ("Swap", LocalSearchType.SWAP, 5000),
    ("Hybrid", LocalSearchType.HYBRID, 5),       # 5 cycle
]
```

### 2. Benchmark Akışı

```
1. Problemleri yükle (TSPLIB download & parse)
2. Metadata kontrol et (önceden çalıştırılmış mı?)
3. Seçilen problem/algoritma kombinasyonlarını çalıştır
4. Her algoritma sonucu anında kaydet (incremental save)
5. Ctrl+C ile güvenli çıkış (sonuçlar kaybolmaz)
6. Özet tablo ve istatistikler göster
```

### 3. Multiprocessing Desteği

```python
# run_smart_benchmark_numba.py
NUM_WORKERS = min(cpu_count(), 4)  # CPU sayısına göre otomatik

def run_single_benchmark_task(args):
    # Worker function - her process bağımsız çalışır
    ...
```

### 4. Sonuç Formatı

```python
{
    "problem": "berlin52",
    "dimension": 52,
    "category": "small",
    "optimal": 7542,
    "strategy": "2-opt",
    "avg_length": 7821.5,
    "avg_gap": 3.71,          # % GAP from optimal
    "best_gap": 2.45,
    "avg_time_ms": 45.2,
    "n_runs": 3,
    "timestamp": "2026-04-08T00:00:00",
    "numba_optimized": True
}
```

---

## ➕ Eklenecek Algoritmalar

### Meta-Heuristic Stratejileri

| Algoritma | Dosya | Parametreler |
|-----------|-------|--------------|
| **GA** (Genetic Algorithm) | `ga_strategy.py` | pop_size, generations, mutation_rate |
| **PSO** (Particle Swarm) | `pso_strategy.py` | swarm_size, iterations, w, c1, c2 |
| **GWO** (Grey Wolf) | `gwo_strategy.py` | pack_size, iterations |
| **HHO** (Harris Hawks) | `hho_strategy.py` | hawks, iterations |

### Önerilen Varsayılan Parametreler

```python
META_HEURISTIC_STRATEGIES = [
    # (isim, strateji_sınıfı, parametreler)
    ("GA", GAStrategy, {
        "pop_size": 50,
        "generations": 100,
        "mutation_rate": 0.1,
        "crossover_rate": 0.9,
        "elite_size": 5
    }),
    ("PSO", PSOStrategy, {
        "swarm_size": 30,
        "iterations": 100,
        "w": 0.7,      # Inertia weight
        "c1": 1.5,     # Cognitive coefficient
        "c2": 1.5      # Social coefficient
    }),
    ("GWO", GWOStrategy, {
        "pack_size": 30,
        "iterations": 100
    }),
    ("HHO", HHOStrategy, {
        "hawks": 30,
        "iterations": 100
    }),
]
```

### Hibrit Kombinasyonlar (Opsiyonel)

```python
HYBRID_STRATEGIES = [
    # Meta-heuristic + Local Search refinement
    ("GA+2opt", GAStrategy, {..., "local_search": "2-opt"}),
    ("PSO+2opt", PSOStrategy, {..., "local_search": "2-opt"}),
    ("GWO+Hybrid", GWOStrategy, {..., "local_search": "Hybrid"}),
]
```

---

## 📝 Geliştirici Görevleri

### Görev 1: Strateji Arayüzünü Standardize Et

Tüm stratejilerin aynı arayüzü uyguladığından emin ol:

```python
# optimizer_api/strategies/base_strategy.py

from abc import ABC, abstractmethod
from typing import List, Tuple, Callable, Dict, Any

class BaseStrategy(ABC):
    """Tüm optimizasyon stratejileri için temel sınıf"""

    @abstractmethod
    def optimize(
        self,
        initial_route: List[str],
        duration_func: Callable[[List[str]], float],
        **kwargs
    ) -> Tuple[List[str], float]:
        """
        Rotayı optimize et.

        Args:
            initial_route: Başlangıç rotası (location codes)
            duration_func: Rota süresini hesaplayan fonksiyon
            **kwargs: Algoritmaya özel parametreler

        Returns:
            Tuple of (optimized_route, duration)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strateji adı"""
        pass
```

### Görev 2: Benchmark Runner'ı Güncelle

`run_interactive_benchmark_v2_numba.py` dosyasında:

```python
# YENİ STRATEGIES tanımı
from optimizer_api.strategies import (
    GAStrategy, PSOStrategy, GWOStrategy, HHOStrategy
)

# Local Search (NUMBA) - mevcut
LOCAL_SEARCH_STRATEGIES = [
    ("2-opt", LocalSearchType.TWO_OPT, 2000),
    ("3-opt", LocalSearchType.THREE_OPT, 200),
    ("Or-opt", LocalSearchType.OR_OPT, 1000),
    ("Swap", LocalSearchType.SWAP, 5000),
    ("Hybrid", LocalSearchType.HYBRID, 5),
]

# Meta-Heuristic - yeni
META_HEURISTIC_STRATEGIES = [
    ("GA", GAStrategy, {"pop_size": 50, "generations": 100}),
    ("PSO", PSOStrategy, {"swarm_size": 30, "iterations": 100}),
    ("GWO", GWOStrategy, {"pack_size": 30, "iterations": 100}),
    ("HHO", HHOStrategy, {"hawks": 30, "iterations": 100}),
]

# Tüm stratejiler
ALL_STRATEGIES = LOCAL_SEARCH_STRATEGIES + META_HEURISTIC_STRATEGIES
```

### Görev 3: run_single_test Fonksiyonunu Güncelle

```python
def run_single_test(
    problem: TSPLIBProblem,
    strategy_name: str,
    strategy_instance,  # LocalSearchType veya Strategy sınıfı
    params: dict,       # Algoritma parametreleri
    seed: int
) -> Dict:
    """Tek bir test çalıştır - hem local search hem meta-heuristic için"""

    coordinates = problem.coordinates
    dimension = problem.dimension

    matrix = create_distance_matrix(coordinates)
    duration_func = create_duration_func(matrix)

    # Başlangıç rotası
    indices = list(range(1, dimension + 1))
    random.seed(seed)
    random.shuffle(indices)
    initial_route = [f"L{i}" for i in indices]

    start_time = time.time()

    # Local Search mi, Meta-Heuristic mi?
    if isinstance(strategy_instance, LocalSearchType):
        # NUMBA Local Search
        improved_route, _ = apply_local_search(
            initial_route, duration_func, strategy_instance,
            max_iterations=params.get("max_iterations", 1000)
        )
    else:
        # Meta-Heuristic Strategy
        improved_route, _ = strategy_instance.optimize(
            initial_route, duration_func, **params
        )

    elapsed = time.time() - start_time

    # Sonuç hesapla
    tour_indices = convert_route_to_indices(improved_route)
    tour_length = calculate_tour_length(tour_indices, coordinates)
    gap = ((tour_length - problem.optimal) / problem.optimal) * 100

    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
    }
```

### Görev 4: Benchmark DB Formatını Güncelle

Metadata dosyasına algoritma tipi ekle:

```json
{
    "algorithm_hashes": {
        "LocalSearchEngine_NUMBA": "abc123...",
        "GA_Strategy": "def456...",
        "PSO_Strategy": "ghi789...",
        "GWO_Strategy": "jkl012...",
        "HHO_Strategy": "mno345..."
    },
    "results": {
        "berlin52": {
            "2-opt": {..., "algorithm_type": "local_search"},
            "GA": {..., "algorithm_type": "meta_heuristic"}
        }
    }
}
```

### Görev 5: Algoritma Bilgi Ekranını Güncelle

```python
ALGORITHM_INFO = {
    # Local Search
    "2-opt": {
        "name": "2-opt",
        "type": "local_search",
        "description": "Klasik kenar değiştirme",
        "complexity": "O(n²)",
        "iterations": 2000,
    },
    # Meta-Heuristic
    "GA": {
        "name": "Genetic Algorithm",
        "type": "meta_heuristic",
        "description": "Popülasyon tabanlı evrimsel algoritma",
        "complexity": "O(pop × gen × n)",
        "parameters": "pop_size=50, generations=100",
    },
    "PSO": {
        "name": "Particle Swarm Optimization",
        "type": "meta_heuristic",
        "description": "Sürü zekası tabanlı optimizasyon",
        "complexity": "O(swarm × iter × n)",
        "parameters": "swarm=30, iterations=100",
    },
    # ...
}
```

---

## ⚠️ Önemli Notlar

### 1. NUMBA Optimizasyonunu Koru

Local search algoritmaları NUMBA JIT ile derlenmiş durumda. Bu performans avantajını **kaybetmeyin**. Meta-heuristic'ler için NUMBA kullanımı opsiyonel.

### 2. Incremental Save'i Koru

Her algoritma sonucu hemen kaydedilmeli. Ctrl+C ile çıkışta sonuçlar kaybolmamalı:

```python
def save_incremental_result(result, metadata, problem_name, strategy_name):
    # Mevcut yapıyı koru
    ...
```

### 3. Tutarlı Sonuç Formatı

Tüm algoritmalar aynı sonuç formatını döndürmeli:
- `tour_length`: Tur uzunluğu
- `gap`: Optimal'den sapma yüzdesi
- `time_ms`: Çalışma süresi (milisaniye)
- `n_runs`: Tekrar sayısı

### 4. Seed Kontrolü

Tekrarlanabilir sonuçlar için seed kullanımı:

```python
seed = (run + 1) * 42 + task_id
random.seed(seed)
np.random.seed(seed)
```

### 5. Multiprocessing Uyumluluğu

Meta-heuristic stratejileri multiprocessing ile çalışabilmeli. Her worker process bağımsız olmalı.

---

## 🧪 Test Adımları

### 1. Tek Problem Testi

```bash
cd DOURide
python academic_benchmark/run_smart_benchmark_numba.py
# Seç: [E] Özel Seçim
# Problem: berlin52
# Algoritmalar: all
```

### 2. Kategori Testi

```bash
# Sadece small problemler, tüm algoritmalar
# Tahmini süre: ~5-10 dakika
```

### 3. Full Benchmark

```bash
# Tüm problemler, tüm algoritmalar
# Tahmini süre: ~2-4 saat
```

### 4. Sonuç Doğrulama

```python
# Beklenen GAP aralıkları (küçük problemler):
# - 2-opt: %2-5
# - 3-opt: %0.5-3
# - Hybrid: %0.5-2
# - GA: %1-5
# - PSO: %2-6
# - GWO: %1-4
# - HHO: %1-4
```

---

## 📊 Beklenen Çıktı

### Özet Tablo Formatı

```
================================================================================
                    AKADEMİK BENCHMARK SONUÇLARI
================================================================================

Problem      | Dim  | Optimal  | Best Algo  | Best GAP | Avg GAP | Time(ms)
------------------------------------------------------------------------------
berlin52     | 52   | 7542     | Hybrid     | 0.82%    | 1.45%   | 125
eil51        | 51   | 426      | 3-opt      | 0.47%    | 1.12%   | 98
kroA100      | 100  | 21282    | GWO        | 1.23%    | 2.34%   | 456
...

------------------------------------------------------------------------------
ALGORITMA PERFORMANS ÖZETİ
------------------------------------------------------------------------------
Algorithm     | Type         | Avg GAP | Min GAP | Max GAP | Avg Time
------------------------------------------------------------------------------
Hybrid        | local_search | 1.45%   | 0.12%   | 4.56%   | 234ms
3-opt         | local_search | 1.89%   | 0.23%   | 5.12%   | 456ms
GWO           | meta_heuris  | 2.12%   | 0.45%   | 6.78%   | 1234ms
GA            | meta_heuris  | 2.56%   | 0.67%   | 7.23%   | 1567ms
2-opt         | local_search | 3.21%   | 0.89%   | 8.45%   | 123ms
PSO           | meta_heuris  | 3.45%   | 0.78%   | 9.12%   | 1456ms
Swap          | local_search | 8.45%   | 2.34%   | 18.9%   | 89ms
```

---

## 📁 Oluşturulacak/Güncellenecek Dosyalar

| Dosya | İşlem | Öncelik |
|-------|-------|---------|
| `run_interactive_benchmark_v2_numba.py` | Güncelle | Yüksek |
| `run_smart_benchmark_numba.py` | Güncelle | Yüksek |
| `utils_benchmark.py` | Güncelle (algoritma hash'leri) | Orta |
| `latest_metadata_numba.json` | Format güncelleme | Orta |

---

## 🔗 Referans Dosyalar

Bu dosyalar incelenmeli:

1. Mevcut benchmark runner yapısı (konuşma geçmişinde)
2. `local_search_numba.py` - NUMBA local search implementasyonu
3. `ga_strategy.py`, `pso_strategy.py`, `gwo_strategy.py`, `hho_strategy.py` - Mevcut stratejiler

---

## ✅ Tamamlandığında

1. Benchmark tüm algoritmalarla çalışmalı
2. Sonuçlar doğru formatta kaydedilmeli
3. Ctrl+C ile güvenli çıkış çalışmalı
4. Özet tablo doğru gösterilmeli
5. Multiprocessing düzgün çalışmalı

---

*Bu doküman Super Z (önceki AI geliştirici) tarafından hazırlandı.*
*Tarih: 2026-04-08*
