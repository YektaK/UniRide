# Bildiri 2026 - Engelsiz Ulaşım SBRP Optimizasyon Çalışması

Bu klasör, "Engelsiz Ulaşım" projesi kapsamında okul servisi rotalama problemi (SBRP) için algoritmik karşılaştırma deneylerini içerir. Projede sadece bağımsız Python kodları kullanılır; web arayüzüne gerek yoktur.

## 📁 Dizin Yapısı

```
bildiri2026/
├── core/                      # Temel algoritma modülleri
│   ├── __init__.py
│   ├── base_solver.py         # TTSPSolver arayüzü, TSPResult veri yapısı
│   ├── two_opt.py             # 2-opt Yerel Arama (Croes, 1958)
│   ├── three_opt.py           # 3-opt Yerel Arama (Lin, 1965)
│   ├── or_opt.py              # Or-opt Yerel Arama (Or, 1976)
│   ├── ga_solver.py           # Genetik Algoritma (Holland, 1975)
│   └── pso_solver.py          # Parçacık Sürü Optimizasyonu (Kennedy & Eberhart, 1995)
├── benchmarks/
│   ├── tsplib_benchmark.py    # TSPLIB problemlerinde kıyaslama (30 bağımsız çalışma)
│   └── timematrix_benchmark.py # 29 öğrenci time matrixi üzerinde kıyaslama
├── data/                      # TSPLIB .tsp dosyaları ve time matrix JSON
├── results/                   # Çıktı CSV ve JSON dosyaları
├── test_core.py               # Hızlı birim test
├── PARAMETRE_OPTIMIZASYONU.md # Parametre optimizasyonu rehberi
└── README.md                  # Bu dosya
```

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler

```bash
pip install numpy
```

### 2. Algoritmaları Test Et

```bash
cd academic_benchmark/bildiri2026
python test_core.py
```

Beklenen çıktı:
```
============================================================
Solver Quick Test - Simple 5-node TSP
============================================================

2-opt:
  Tour length: 4.00
  Time: 0.50 ms
  ...

All solvers completed successfully!
```

### 3. TSPLIB Benchmark Çalıştır

**30 bağımsız çalışma ile 5 TSPLIB problemi:**

```bash
cd academic_benchmark/bildiri2026/benchmarks
python tsplib_benchmark.py --runs 30 \
  --problems eil51 berlin52 st70 eil76 eil101 \
  --output ../results
```

**Sonuçlar:**
- `../results/benchmark_YYYYMMDD_HHMMSS.json` — ham veriler
- `../results/benchmark_YYYYMMDD_HHMMSS.csv` — analiz için

### 4. Time Matrix Benchmark Çalıştır

**29 öğrenci için örnek time matrix:**

```bash
cd academic_benchmark/bildiri2026/benchmarks
python timematrix_benchmark.py --runs 30 --output ../results
```

**Kendi verinizle:**

```bash
python timematrix_benchmark.py \
  --matrix-file ../data/student_matrix.json \
  --runs 30 \
  --output ../results
```

## 📊 Çıktı Formatı

### JSON Örneği

```json
{
  "timestamp": "20260423_120000",
  "num_runs": 30,
  "results": [
    {
      "problem": "eil51",
      "algorithm": "GA",
      "run": 1,
      "dimension": 51,
      "tour_length": 432.1,
      "optimal": 426,
      "gap_percent": 1.43,
      "elapsed_ms": 2340.5,
      "iterations": 300,
      "seed": 1000
    }
  ]
}
```

### CSV Örneği

| problem | algorithm | run | dimension | tour_length | optimal | gap_percent | elapsed_ms | iterations | seed |
|---------|-----------|-----|-----------|-------------|---------|-------------|------------|------------|------|
| eil51 | GA | 1 | 51 | 432.1 | 426 | 1.43 | 2340.5 | 300 | 1000 |
| eil51 | GA | 2 | 51 | 430.5 | 426 | 1.06 | 2280.3 | 300 | 1001 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## 🔬 Parametre Optimizasyonu

Detaylı rehber için `PARAMETRE_OPTIMIZASYONU.md` dosyasına bakın.

### Özet Yaklaşım

1. **Taguchi L8 Dizaynı** (8 kombinasyon × 3 tekrar = 24 deney)
2. **Latin Hypercube Sampling** (50 kombinasyon × 3 tekrar = 150 deney)
3. Her algoritma için en iyi parametre setini belirle
4. Bulunan parametrelerle 30 bağımsız çalışma yap

### Önerilen Parametreler (Varsayılan)

| Algoritma | Ana Parametreler |
|-----------|------------------|
| **GA** | pop=100, gen=300, cx=0.85, mut=0.15, elite=2 |
| **PSO** | swarm=50, iter=300, w=0.729, c1=c2=1.494 |
| **3-opt** | max_iter=1000, first_improvement=False |
| **Or-opt** | max_iter=1000, max_segment=3 |

## 📝 Metodoloji

### TSPLIB Deneyleri
- **Problemler:** eil51, berlin52, st70, eil76, eil101
- **Algoritmalar:** GA, PSO, 2-opt, 3-opt, Or-opt
- **Tekrar:** 30 bağımsız çalışma (farklı seed ile)
- **Metrik:** Gap (%), Hesaplama süresi (ms)
- **İstatistik:** Ortalama, standart sapma, en iyi değer

### 29 Öğrenci Deneyleri
- **Girdi:** Gerçek zaman matrixi (30×30)
- **Algoritmalar:** GA, PSO, 3-opt, Or-opt
- **Tekrar:** 30 bağımsız çalışma
- **Metrik:** Toplam süre (dk), Hesaplama süresi (ms)

## 📚 Kaynaklar

- Croes, G. (1958). A method for solving traveling salesman problems.
- Lin, S. (1965). Computer solutions of the traveling salesman problem.
- Or, I. (1976). Traveling salesman-type combinatorial problems.
- Holland, J. H. (1975). Adaptation in Natural and Artificial Systems.
- Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization.
- TSPLIB: http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/

---

**Proje:** UniRide - Engelsiz Ulaşım  
**Hazırlayan:** Bildiri 2026 Ekibi  
**Son Güncelleme:** 23 Nisan 2026