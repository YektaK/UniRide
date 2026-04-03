# UniRide Optimizer API - Test Kılavuzu

Bu klasör UniRide CVRPTW sistemi için Python optimizasyon API'sini içerir.

## 🚀 Hızlı Başlangıç

### 1. Gerekli Paketleri Kurun

```bash
# Temel gereksinimler
pip install pytest pandas openpyxl pydantic

# Dış solver'lar (opsiyonel ama önerilir)
pip install ortools pyvrp

# VROOM (C++ binary - ayrı kurulum gerekir)
# Ubuntu/Debian: sudo apt-get install vroom
# Windows: https://github.com/VROOM-PROJECT/vroom/releases
```

### 2. Veri Dosyasını Yerleştirin

`Veri.xlsx` dosyasını bu klasöre veya üst klasöre kopyalayın:
- Distance matrix (Time sayfası): 29 konum arası dakika cinsinden süreler
- Pickup/Dropoff verileri (Pick, Drop sayfaları)

### 3. Testleri Çalıştırın

```bash
# Tüm testler
python run_all_tests.py

# Sadece unit testler (hızlı)
python run_all_tests.py --quick

# Algoritma karşılaştırması
python run_all_tests.py --compare

# Exact çözüm ile karşılaştırma (9 öğrenci)
python run_all_tests.py --exact
```

## 📁 Dosya Yapısı

```
optimizer_api/
├── run_all_tests.py      # Ana test runner
├── test_strategies.py    # Strateji unit testleri
├── test_gwo.py           # GWO strateji testleri
├── test_hho.py           # HHO strateji testleri
├── test_comparison.py    # Algoritma karşılaştırma
├── test_split_strategies.py  # Split stratejileri + Crossover testleri
├── conftest.py           # Pytest config
├── strategies/           # Algoritma implementasyonları
│   ├── __init__.py       # Strategy Registry (29 strateji)
│   ├── ga_split_strategy.py
│   ├── gwo_split_strategy.py
│   ├── hho_split_strategy.py
│   ├── pso_split_strategy.py
│   └── ...
├── models/               # Pydantic modelleri
├── utils/                # Yardımcı araçlar
└── tests/                # Ek testler
```

## 🧪 Test Kategorileri

### Unit Tests
| Dosya | Test Sayısı | Kapsam |
|-------|-------------|--------|
| test_strategies.py | 5 | GA, PSO, Greedy, Permutation |
| test_gwo.py | 3 | Grey Wolf Optimizer |
| test_hho.py | 3 | Harris Hawks Optimizer |
| test_comparison.py | 1 | Algoritma karşılaştırma |
| test_split_strategies.py | 17 | Crossover + Split stratejileri |

### Crossover Tests
- **PMX**: Partially Mapped Crossover
- **CX2**: Cycle Crossover 2
- **OX1**: Order Crossover

### Algorithm Comparison
Gerçek distance matrix ile tüm algoritmaların karşılaştırması:
- Pipeline A: Cluster-First Route-Second (GA, PSO, GWO, HHO, Greedy)
- Pipeline B: Route-First Cluster-Second (GA-Split, PSO-Split, GWO-Split, HHO-Split)

## 📊 Örnek Çıktı

```
ALGORITHM COMPARISON (Real Distance Matrix)
======================================================================
Distance Matrix: 29 locations loaded

--- Full (28 students) ---
Algorithm                  Vehicles   Duration     Time (s)   
------------------------------------------------------------
GWO-Split (Route-First)    4          699          0.3662     
Greedy (En Yakın Komşu)    4          729          0.0003     
PSO-Split (Route-First)    4          732          0.3973     
HHO-Split (Route-First)    4          761          0.3369     
GA-Split Hybrid            4          776          0.1508     

Best: GWO-Split (699 dk, 4 vehicles)
```

## 🔧 Dış Solver Kurulumu

### OR-Tools (Google)
```bash
pip install ortools
```
- Hibrit solver: CPSAT + Guided Local Search
- CVRP, CVRPTW desteği

### PyVRP (HGS-CVRP)
```bash
pip install pyvrp
```
- Hybrid Genetic Search
- DIMACS 2021 yarışma kazananı
- CVRPTW desteği

### VROOM
```bash
# Linux
sudo apt-get install vroom

# macOS
brew install vroom

# Windows
# https://github.com/VROOM-PROJECT/vroom/releases
```
- C++ tabanlı, ultra hızlı
- Open-source routing engine

## 🐛 Sorun Giderme

### "ModuleNotFoundError: No module named 'pytest'"
```bash
pip install pytest
```

### "Veri.xlsx not found"
Dosyayı doğru konuma kopyalayın:
```bash
cp /path/to/Veri.xlsx ./optimizer_api/
```

### "SUPABASE credentials not found"
Bu uyarı öneml değil - coordinate-based hesaplama fallback olarak kullanılıyor.

### Import Errors (GWOStrategy, HHOStrategy)
Sınıf isimleri değişti, alias kullanılıyor:
```python
# Eski (hatalı)
from strategies.gwo_strategy import GWOStrategy

# Yeni (doğru)
from strategies.gwo_strategy import GreyWolfOptimizerStrategy as GWOStrategy
```

## 📝 Test Sonuçları (30 Mart 2026)

| Metrik | Değer |
|--------|-------|
| Toplam Test | 29 |
| Geçen | 29 |
| Başarısız | 0 |
| Düzeltilen Bug | 2 (PMX, CX2) |

### Exact vs Heuristic (9 öğrenci)
| Algoritma | Süre | Gap |
|-----------|------|-----|
| EXACT | 165 dk | 0% |
| GWO-Split | 249 dk | 50.9% |
| Greedy | 251 dk | 52.1% |

**Not:** Gap yüksek çünkü stratejiler coordinate-based hesaplama yapıyor.
Gerçek distance matrix entegrasyonu ile gap azalacaktır.

## 📚 Referanslar

- Prins, C. (2004). "A simple and effective evolutionary algorithm for the vehicle routing problem"
- Oliver, I. et al. (1987). "A study of permutation crossover operators on the traveling salesman problem"
- Goldberg, D. & Lingle, R. (1985). "Alleles, loci, and the traveling salesman problem"
