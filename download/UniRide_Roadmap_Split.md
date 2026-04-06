# 🗺️ UniRide Geliştirme Yol Haritası

> **Her geliştirici yeni iş almadan önce bu dokümanı kontrol etmeli ve hangi faz/görevde çalıştığını belirtmelidir.**  
> **Son güncelleme:** 26 Mart 2026  
> **Sürüm:** 2.0 - Split Entegrasyonu

---

## Onaylanan Mimari Kararlar

| # | Karar | Seçim | Referans |
|---|---|---|---|
| KN1 | API Katmanı | İşlev bazlı Next.js proxy | Faz 1.1 |
| KN2 | Ölü Kod | Temiz silme | Faz 1.3 |
| KN3 | Time Matrix | Sabit matris + encoding fix | Faz 1.2 |
| KN4 | DB Şeması | Minimal JSON (`route_plans`) | Faz 2.1 |
| KN5 | Onay/İptal | Hybrid (ders=otomatik, dışı=talep) | Faz 3.1 |
| KN6 | Sürücü Atama | Manuel atama | Faz 2.2 |
| KN7 | Canlı Takip | Supabase Realtime | Faz 4.1 |
| KN8 | Konum Sistemi | Sabit kodlar (şimdilik) | Mevcut |
| KN9 | Algoritma Pipeline | Registry Pattern | Mevcut |
| **KN10** | **Split Entegrasyonu** | **Giant Tour + Optimal Split** | **Faz 1.4** |
| **KN11** | **Hibrit Algoritmalar** | **PSO/HHO/GWO/GA + Split** | **Faz 1.5** |

---

## Faz Durumu Özeti

| Faz | Durum | Açıklama |
|---|---|---|
| **Faz 1: Kritik Düzeltmeler** | ✅ Tamamlandı | Sistem çalışır hale geldi |
| **Faz 1.4-1.5: Split Entegrasyonu** | 🔵 Planlanıyor | Yeni hibrit algoritmalar |
| **Faz 2: Veri Kalıcılığı + Atama** | ⬜ Bekliyor | Rota kaydı + sürücü ataması |
| **Faz 3: İş Akışı Otomasyonu** | ⬜ Bekliyor | Onay/iptal + bildirim |
| **Faz 4: İleri Özellikler** | ⬜ Bekliyor | Canlı takip + dinamik matris |

---

## Faz 1: Kritik Düzeltmeler 🔴

> Bu faz tamamlandı. Sistem operasyonel olarak kullanılabilir.

### Görev 1.1: `vehicle-planning` → Python API Bağlantısı (KN1)
- **Durum:** ✅ Tamamlandı
- **Mimari karar:** İşlev bazlı proxy

### Görev 1.2: Windows Encoding Fix (KN3)
- **Durum:** ✅ Tamamlandı
- **Dosya:** `optimizer_api/utils/data_loader.py`

### Görev 1.3: Ölü Kod Temizliği (KN2)
- **Durum:** ✅ Tamamlandı
- **Silinen dosyalar:** Eski TypeScript strateji dosyaları

---

## Faz 1.4-1.5: Split Entegrasyonu 🔵

> **YENİ FAZ** - Hibrit algoritma mimarisi

### Görev 1.4: Split Decoder Modülü (KN10)
- **Durum:** ⬜ Bekliyor
- **Atanan:** —
- **Tahmini süre:** 3-4 saat
- **Öncelik:** 🔴 Kritik

#### A) Yeni Dosya: `optimizer_api/utils/split_decoder.py`

```python
class SplitDecoder:
    """
    Optimal split decoder using dynamic programming.
    
    Features:
    - Giant tour → Multiple routes
    - Capacity constraints (Sw ≤ 4, So ≤ 5)
    - Time constraints (max 180 dk)
    - Time matrix aware
    """
    
    def decode(self, giant_tour, depot, time_matrix, 
               coordinates, student_data) -> Tuple[List[List[str]], float]:
        # DP implementation
        pass
```

#### B) Unit Tests

```
tests/
├── test_split_decoder.py
│   ├── test_single_student()
│   ├── test_capacity_constraint()
│   ├── test_time_constraint()
│   └── test_complex_scenario()
```

#### C) Kabul Kriterleri

- [ ] Giant tour input → Routes output
- [ ] Her route Sw ≤ 4, So ≤ 5
- [ ] Her route süresi ≤ max_tour_time
- [ ] Time matrix entegrasyonu
- [ ] Unit test coverage ≥ 80%

---

### Görev 1.5: Hibrit Strateji Temel Sınıfı (KN11)
- **Durum:** ⬜ Bekliyor
- **Atanan:** —
- **Tahmini süre:** 1-2 saat
- **Bağımlılık:** Görev 1.4

#### Dosya: `optimizer_api/strategies/hybrid_base_strategy.py`

```python
class HybridSplitStrategy(BaseRoutingStrategy):
    """
    Base class for hybrid meta-heuristic + split algorithms.
    
    Subclasses implement:
    - _optimize_giant_tour()
    """
    
    def optimize(self, request):
        # 1. Initialize split decoder
        # 2. Build data structures
        # 3. Optimize giant tour (meta-heuristic)
        # 4. Decode with split
        # 5. Build response
```

---

### Görev 1.5.1: PSO-Split Implementasyonu
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 2-3 saat
- **Dosya:** `optimizer_api/strategies/pso_split_strategy.py`

```python
class PSOSplitStrategy(HybridSplitStrategy):
    """
    Particle Swarm Optimization + Optimal Split
    
    Particle position = Giant tour
    Fitness = Split decoder → Total cost
    """
```

**Parametreler:**
- `swarm_size`: 30
- `max_iterations`: 100
- `inertia_weight`: 0.729
- `cognitive_weight`: 1.49445
- `social_weight`: 1.49445

---

### Görev 1.5.2: HHO-Split Implementasyonu
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 2-3 saat
- **Dosya:** `optimizer_api/strategies/hho_split_strategy.py`

```python
class HHOSplitStrategy(HybridSplitStrategy):
    """
    Harris Hawks Optimization + Optimal Split
    
    Hawk position = Giant tour
    Prey = Best solution
    Siege strategies: soft, hard, progressive dives
    """
```

**Parametreler:**
- `population_size`: 30
- `max_iterations`: 100
- `initial_energy`: 1.0
- `jump_probability`: 0.5

---

### Görev 1.5.3: GWO-Split Implementasyonu
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 2-3 saat
- **Dosya:** `optimizer_api/strategies/gwo_split_strategy.py`

```python
class GWOSplitStrategy(HybridSplitStrategy):
    """
    Grey Wolf Optimizer + Optimal Split
    
    Wolf position = Giant tour
    Alpha, Beta, Delta = Top 3 solutions
    """
```

**Parametreler:**
- `population_size`: 30
- `max_iterations`: 100
- `initial_a`: 2.0

---

### Görev 1.5.4: GA-Split Implementasyonu
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 2-3 saat
- **Dosya:** `optimizer_api/strategies/ga_split_strategy.py`

```python
class GASplitStrategy(HybridSplitStrategy):
    """
    Genetic Algorithm + Optimal Split
    
    Chromosome = Giant tour
    Crossover = Order Crossover (OX1)
    Mutation = Swap/Inversion
    """
```

**Parametreler:**
- `population_size`: 50
- `max_iterations`: 100
- `crossover_rate`: 0.85
- `mutation_rate`: 0.15

---

### Görev 1.6: Local Search Modülü
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 1-2 saat
- **Dosya:** `optimizer_api/utils/local_search.py`

```python
class LocalSearch:
    """Local search operators for route improvement"""
    
    @staticmethod
    def two_opt(route, duration_func) -> Tuple[List, float]:
        """2-opt improvement"""
        pass
    
    @staticmethod
    def or_opt(route, duration_func) -> Tuple[List, float]:
        """Or-opt (relocate) improvement"""
        pass
```

---

### Görev 1.7: Strategy Registry Güncellemesi
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 30 dk
- **Dosya:** `optimizer_api/strategies/__init__.py`

```python
STRATEGY_REGISTRY = {
    # Mevcut stratejiler
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    "hho": HarrisHawksOptimizerStrategy,
    "gwo": GreyWolfOptimizerStrategy,
    
    # YENİ: Split tabanlı stratejiler
    "ga_split": GASplitStrategy,
    "pso_split": PSOSplitStrategy,
    "hho_split": HHOSplitStrategy,
    "gwo_split": GWOSplitStrategy,
}
```

---

### Görev 1.8: Frontend Algorithm Seçimi Güncellemesi
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 30 dk
- **Dosya:** `src/lib/algorithm-constants.ts`

```typescript
export const ALGORITHM_OPTIONS = [
  // Mevcut
  { value: 'genetic_algorithm', label: 'Genetik Algoritma' },
  { value: 'pso', label: 'Parçacık Sürü Optimizasyonu' },
  
  // YENİ: Split tabanlı
  { value: 'pso_split', label: 'PSO + Optimal Split (Önerilen)' },
  { value: 'hho_split', label: 'HHO + Optimal Split' },
  { value: 'gwo_split', label: 'GWO + Optimal Split' },
  { value: 'ga_split', label: 'GA + Optimal Split' },
];
```

---

### Görev 1.9: Benchmark ve Karşılaştırma Testleri
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 3-4 saat
- **Bağımlılık:** 1.4, 1.5, 1.5.1-1.5.4

#### Test Senaryoları

| Senaryo | N (Öğrenci) | Açıklama |
|---------|-------------|----------|
| Small | 30 | Mevcut ölçek |
| Medium | 100 | Orta ölçek |
| Large | 300 | Hedef ölçek |
| Mixed | 100 | %30 Sw, %70 So |

#### Karşılaştırma Metrikleri

| Metrik | Açıklama |
|--------|----------|
| Toplam araç sayısı | Daha az = daha iyi |
| Ortalama tur süresi | Daha düşük = daha iyi |
| Tek öğrencilik rota oranı | Daha düşük = daha iyi |
| Execution time | Makul sınırlar içinde |
| Feasibility rate | %100 olmalı |

---

## Faz 2: Veri Kalıcılığı ve Atama 🟡

> Faz 1.4-1.5 tamamlandıktan sonra başlanabilir.

### Görev 2.1: Rota Sonuçlarını Veritabanına Kaydet (KN4)
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 4-5 saat

### Görev 2.2: Manuel Sürücü Ataması (KN6)
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 3-4 saat

### Görev 2.3: `multi-vehicle-routing.ts` Payload Düzeltmesi
- **Durum:** ⬜ Bekliyor

### Görev 2.4: DataLoader Fallback İyileştirme
- **Durum:** ⬜ Bekliyor

---

## Faz 3: İş Akışı Otomasyonu 🟠

> Faz 2 tamamlandıktan sonra başlanabilir.

### Görev 3.1: Hybrid Onay/İptal Mekanizması (KN5)
- **Durum:** ⬜ Bekliyor
- **Tahmini süre:** 6-8 saat

### Görev 3.2: Öğrenci Dashboard Güncellemesi
- **Durum:** ⬜ Bekliyor

### Görev 3.3: Sürücü Dashboard Güncellemesi
- **Durum:** ⬜ Bekliyor

---

## Faz 4: İleri Özellikler 🔵

> Faz 3 tamamlandıktan sonra başlanabilir.

### Görev 4.1: Canlı Konum Takibi (KN7)
- **Durum:** ⬜ Bekliyor

### Görev 4.2: Hybrid Time Matrix Güncelleme
- **Durum:** ⬜ Bekliyor

### Görev 4.3: Adres → En Yakın Kod Eşleme
- **Durum:** ⬜ Bekliyor

### Görev 4.4: Sürücü Öneri + Onay
- **Durum:** ⬜ Bekliyor

---

## Bağımlılık Haritası

```
Faz 1.4 (Split Decoder)
 ├── 1.5 (Hybrid Base) ← 1.4 bitmeden başlama
 │    ├── 1.5.1 (PSO-Split)
 │    ├── 1.5.2 (HHO-Split)
 │    ├── 1.5.3 (GWO-Split)
 │    └── 1.5.4 (GA-Split)
 │
 ├── 1.6 (Local Search) → Bağımsız, paralel yapılabilir
 ├── 1.7 (Registry) ← 1.5.1-1.5.4 tamamlanınca
 └── 1.8 (Frontend) ← 1.7 tamamlanınca

1.9 (Benchmark) ← 1.4, 1.5, 1.5.1-1.5.4 tamamlanınca

Faz 2 ← Faz 1.4-1.5 tamamlandıktan sonra
Faz 3 ← Faz 2 tamamlandıktan sonra
Faz 4 ← Faz 3 tamamlandıktan sonra
```

---

## Tahmini Zaman Çizelgesi

| Hafta | Görevler | Tahmini Süre |
|-------|----------|--------------|
| Hafta 1 | 1.4 (Split Decoder) | 3-4 saat |
| Hafta 1 | 1.5 (Hybrid Base) | 1-2 saat |
| Hafta 1-2 | 1.5.1-1.5.4 (4 Algoritma) | 8-12 saat |
| Hafta 2 | 1.6 (Local Search) | 1-2 saat |
| Hafta 2 | 1.7 + 1.8 (Registry + Frontend) | 1 saat |
| Hafta 2 | 1.9 (Benchmark) | 3-4 saat |
| **TOPLAM** | **Faz 1.4-1.5** | **18-25 saat** |

---

## Görev Alma ve Takip Kuralları

1. Bir görevi almadan önce bu dosyada **"Atanan"** alanını güncelle
2. Görev tamamlandığında durumu `✅ Tamamlandı` olarak işaretle
3. `CHANGELOG.md`'ye değişikliği kaydet
4. **Faz sırasını atlamadan ilerle** (1.4 → 1.5 → 1.5.x → 1.9 → 2)
5. Aynı faz içinde görevler paralel yapılabilir
6. Split entegrasyonu tamamlandıktan sonra eski algoritmalar **opsiyonel** kalır

---

## Akademik Yayın Takibi

| Aşama | Durum | Açıklama |
|-------|-------|----------|
| Problem Tanımı | ✅ Tamam | CVRPTW tanımlandı |
| Literatür Taraması | ✅ Tamam | HGS, PyVRP, VROOM |
| Yöntem Seçimi | ✅ Tamam | Split + Meta-sezgisel |
| Implementasyon | ⬜ Bekliyor | Faz 1.4-1.5 |
| Deneyler | ⬜ Bekliyor | Faz 1.9 |
| Yazım | ⬜ Bekliyor | Sonuçlar sonrası |

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
