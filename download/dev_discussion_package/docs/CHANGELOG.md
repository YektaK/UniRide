# 📋 Değişiklik Günlüğü

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Son Güncelleme:** 27 Mart 2026 - Saat 14:30

---

## [1.8.0] - 27 Mart 2026 (Saat 16:00)

### ✨ Eklendi (Added)

#### Pipeline B - Metaheuristic Split Strategies

| Dosya | Açıklama |
|-------|----------|
| `strategies/metaheuristic_split_strategies.py` | PSO/HHO/GWO + Split Decoder (~25 KB) |
| `tests/test_meta_split.py` | Pipeline B karşılaştırma testi (~10 KB) |

**Yeni Stratejiler:**

| Strateji | Algoritma | Açıklama |
|----------|-----------|----------|
| `pso_split` | PSO + Split | Parçacık Sürü Optimizasyonu |
| `hho_split` | HHO + Split | Harris Hawks Optimizasyonu |
| `gwo_split` | GWO + Split | Grey Wolf Optimizasyonu |

**BaseSplitStrategy:**
- Ortak fonksiyonlar: `_evaluate_solution()`, `_educate()`, `_diversify()`
- `optimize()` metodu: Giant tour optimizasyonu + Split decoder
- Local search entegrasyonu

### 📊 Pipeline B Stratejileri (Tam Liste)

| Strateji | Algoritma | Pipeline |
|----------|-----------|----------|
| `ga_split` | GA + Split | B |
| `ga_split_enhanced` | GA + Split (HGS) | B |
| `pso_split` | PSO + Split | B |
| `hho_split` | HHO + Split | B |
| `gwo_split` | GWO + Split | B |

### 🔧 Değişen (Changed)

| Dosya | Değişiklik |
|-------|------------|
| `strategies/__init__.py` | PSO/HHO/GWO-Split stratejileri eklendi |

### 🧪 Test Komutları

```bash
cd dev_discussion_package/code

# Tüm Pipeline B stratejileri test et
python -m tests.test_meta_split

# Tek strateji test
python -c "from strategies import get_strategy; s = get_strategy('pso_split'); print(s.display_name)"
```

---

## [1.7.0] - 27 Mart 2026 (Saat 15:00)

### ✨ Eklendi (Added)

#### Time-Matrix Aware Clustering

| Dosya | Açıklama |
|-------|----------|
| `utils/clustering_strategies.py` | Time-matrix duyarlı clustering stratejileri (~20 KB) |
| `tests/test_clustering.py` | Clustering test ve karşılaştırma script'i (~12 KB) |

**Mevcut Stratejiler:**

| Algoritma | Time Matrix | Açıklama |
|-----------|-------------|----------|
| `kmeans` | ❌ Hayır | Klasik K-Means (koordinat bazlı) |
| `kmedoids` | ✅ Evet | K-Medoids (gerçek nokta merkezler) |
| `clarke_wright` | ✅ Evet | Savings algoritması (route-oriented) |
| `agglomerative` | ✅ Evet | Hierarchical clustering |
| `hybrid` | ✅ Evet | CW init + K-Medoids refinement |

**Kullanım:**
```python
# GA ile time-matrix aware clustering
strategy = GeneticAlgorithmStrategy(config={
    "clustering_algorithm": "clarke_wright"  # veya "kmedoids", "hybrid"
})
```

### 🔧 Değişen (Changed)

| Dosya | Değişiklik |
|-------|------------|
| `ga_strategy.py` | Varsayılan clustering: `clarke_wright` (time-matrix aware) |
| `clustering.py` | `time_matrix`, `depot` parametreleri eklendi |

### 📊 Clustering Karşılaştırması

| Algoritma | Time Matrix | Hız | Kalite | Öneri |
|-----------|-------------|-----|--------|-------|
| K-Means | ❌ | ⚡⚡⚡ | ⭐⭐ | Hız kritik |
| K-Medoids | ✅ | ⚡⚡ | ⭐⭐⭐ | Küçük problem |
| Clarke-Wright | ✅ | ⚡⚡⚡ | ⭐⭐⭐⭐ | **ÖNERİLEN** |
| Hybrid | ✅ | ⚡⚡ | ⭐⭐⭐⭐⭐ | Kalite kritik |

---

## [1.6.0] - 27 Mart 2026 (Saat 14:30)

### ✨ Eklendi (Added)

#### Pipeline B - Route-First, Cluster-Second

| Dosya | Açıklama |
|-------|----------|
| `utils/split_decoder.py` | Dynamic Programming tabanlı optimal Split Decoder (~12 KB) |
| `strategies/ga_split_strategy.py` | GA + Split Hybrid Strategy (~18 KB) |
| `tests/test_ga_split.py` | Pipeline B test ve karşılaştırma script'i (~8 KB) |

**Split Decoder Özellikleri:**
- Prins (2004) algoritması implementasyonu
- O(n²) zaman karmaşıklığı
- Optimal partition garantisi
- Heterojen fleet desteği (Sw/So kapasite)
- Max tour duration kısıtı
- Time windows desteği (V2)
- Heterogeneous fleet optimization (V2)

**GA-Split Hybrid Özellikleri:**
- Route-first, cluster-second yaklaşımı
- GA ile giant tour optimizasyonu
- Split Decoder ile optimal araç bölme
- Education (local search) entegrasyonu
- Diversification mekanizması
- HGS tarzı enhanced versiyon (PMX, CX2 crossover)

#### Güncellenen Dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `strategies/__init__.py` | Pipeline B stratejileri eklendi (`ga_split`, `ga_split_enhanced`) |

### 🔧 Değişen (Changed)

#### Strategy Registry Güncellemesi

**Yeni kayıtlar:**
```python
# Pipeline B
"ga_split": GASplitStrategy
"ga_split_enhanced": GAEnhancedSplitStrategy
```

**Öneri mantığı güncellendi:**
```
N ≤ 10  → permutation_tsp (quality) / greedy (speed)
N ≤ 30  → pyvrp/ga_split (quality) / ortools (speed) / ga_split (balanced)
N ≤ 100 → pyvrp/ga_split_enhanced (quality) / vroom (speed) / ga_split (balanced)
N > 100 → pyvrp/ga_split_enhanced (quality) / vroom (speed+balanced)
```

### 📊 Pipeline Karşılaştırması

| Yaklaşım | Açıklama | Avantaj | Dezavantaj |
|----------|----------|---------|------------|
| **Pipeline A** (Cluster-First) | K-Means → TSP | Basit, paralel | Suboptimal kümeleme |
| **Pipeline B** (Route-First) | Giant Tour → Split | Optimal bölme | Tek seferlik optimize |

**Teorik Performans:**
- Pipeline B genellikle %5-15 daha az araç kullanır
- Pipeline B çözüm kalitesi daha yüksek
- Pipeline A paralel çalıştırılabilir

---

## [1.5.0] - 27 Mart 2026 (Saat 10:15)

### ✨ Eklendi (Added)

#### Yeni Stratejiler - Bağımsız Holistik Çözücüler

| Dosya | Açıklama |
|-------|----------|
| `strategies/vroom_strategy.py` | VROOM ultra-hızlı C++ çözücü (15.8 KB) |
| `strategies/pyvrp_strategy.py` | PyVRP - DIMACS 2021 birincisi HGS (19.2 KB) |

**VROOM Özellikleri:**
- Ultra-hızlı: 1000+ nokta < 5 saniye
- PDPTW (Pickup-Delivery) desteği
- Multi-trip desteği
- OSRM entegrasyonu
- Canlı rota planlama için ideal
- Heterojen fleet native destek (Sw/So kapasite)
- Time window desteği

**PyVRP Özellikleri:**
- DIMACS 2021 Challenge birincisi
- Hybrid Genetic Search (HGS) algoritması
- Heterojen fleet native destek
- Time windows native destek
- En yüksek çözüm kalitesi
- Multi-depot destek
- Akademik referans kalitesinde

#### Güncellenen Dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `strategies/__init__.py` | Yeni stratejiler eklendi, `get_available_solvers()`, `get_recommended_strategy()` fonksiyonları eklendi |

#### Test Dosyaları

| Dosya | Açıklama |
|-------|----------|
| `tests/test_new_strategies.py` | VROOM ve PyVRP test ve karşılaştırma script'i (9.3 KB) |

#### Dokümantasyon

| Dosya | Açıklama |
|-------|----------|
| `docs/CHANGELOG.md` | Bu değişiklik günlüğü |
| `docs/IMPLEMENTATION_STATUS.md` | Uygulama durumu takibi |
| `docs/CHANGES_SUMMARY.md` | Değişiklik özeti |

---

### 🔧 Değişen (Changed)

#### Strategy Registry Güncellemesi

**Yeni kayıtlar:**
```python
# VROOM
"vroom": VROOMStrategy
"vroom_fallback": VROOMFallbackStrategy

# PyVRP
"pyvrp": PyVRPStrategy
"pyvrp_alt": PyVRPAlternativeStrategy
"hgs": PyVRPStrategy  # Alias
```

**Yeni yardımcı fonksiyonlar:**
- `get_available_solvers()` - Kurulu kütüphane durumunu döndürür
- `get_recommended_strategy(n_students, priority)` - Önerilen algoritmayı döndürür

**Öneri mantığı:**
```
N ≤ 10  → permutation_tsp (quality) / greedy (speed)
N ≤ 30  → pyvrp (quality) / ortools (speed) / pso (balanced)
N ≤ 100 → pyvrp (quality) / vroom (speed) / hho (balanced)
N > 100 → pyvrp (quality) / vroom (speed+balanced)
```

---

### 📊 Algoritma Karşılaştırması

| Algoritma | N≤30 | N≤100 | N>100 | Kullanım |
|-----------|------|-------|-------|----------|
| **VROOM** | ⚡ Hızlı | ⚡ Çok hızlı | ⚡ Ultra hızlı | Canlı rota |
| **PyVRP** | 🏆 En iyi kalite | 🏆 En iyi kalite | ✅ İyi | Offline plan |
| OR-Tools | ✅ İyi | ✅ İyi | ✅ İyi | Referans |
| GA/PSO/HHO/GWO | ✅ İyi | ⚠️ Yavaş | ❌ Çok yavaş | Pipeline A |

---

### 📦 Kurulum Gereksinimleri

```bash
# Mevcut (kurulu olmalı)
pip install ortools

# Yeni - VROOM (opsiyonel ama önerilen)
pip install pyvroom

# Yeni - PyVRP (opsiyonel ama önerilen)
pip install pyvrp
```

---

### 🧪 Test Komutları

```bash
cd dev_discussion_package/code
python -m tests.test_new_strategies
```

---

## [1.4.0] - 26 Mart 2026

### Eklendi
- `docs/ARCHITECTURE.md` - Çift pipeline mimarisi
- `docs/ALGORITHM_COMPARISON.md` - Algoritma karşılaştırması
- `docs/ANALYSIS.md` - Mevcut durum analizi
- `README.md` - Geliştirici tartışma paketi

### Tespit Edilen Sorunlar
- K-Means time matrix duyarsızlığı
- Tek öğrencilik rotalar (%15-20)
- Katı küme sınırları

---

## Gelecek Sürümler

### [1.6.0] - Planlanıyor

- `strategies/split_decoder.py` - DP tabanlı Split Decoder
- `strategies/hybrid_base_strategy.py` - Split base class
- `strategies/pso_split_strategy.py` - PSO + Split
- `strategies/hho_split_strategy.py` - HHO + Split
- `strategies/gwo_split_strategy.py` - GWO + Split
- `strategies/ga_split_strategy.py` - GA + Split

### [2.0.0] - İleriki

- Faz 2: Veri kalıcılığı
- Faz 3: İş akışı otomasyonu
- Faz 4: Canlı takip

---

## Sürüm Notları

| Sürüm | Tarih | Özellik |
|-------|-------|---------|
| 1.5.0 | 27.03.2026 | VROOM + PyVRP entegrasyonu |
| 1.4.0 | 26.03.2026 | Dokümantasyon güncellemesi |
| 1.3.0 | 25.03.2026 | Local search modülü |
| 1.2.0 | 24.03.2026 | K-Means clustering |
| 1.1.0 | 24.03.2026 | Base strategy pattern |
| 1.0.0 | 23.03.2026 | İlk sürüm |
