# UniRide Geliştirme Yol Haritası

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Sürüm:** 2.0 - Split Entegrasyonu  
> **Son Güncelleme:** 26 Mart 2026

---

## Mimari Kararlar

| # | Karar | Seçim | Durum |
|---|-------|-------|-------|
| KN1 | API Katmanı | Next.js Proxy | ✅ Tamamlandı |
| KN2 | Ölü Kod Temizliği | Tam silme | ✅ Tamamlandı |
| KN3 | Time Matrix | Sabit matris | ✅ Tamamlandı |
| KN4 | DB Şeması | Minimal JSON | ⬜ Bekliyor |
| KN5 | Onay/İptal | Hybrid | ⬜ Bekliyor |
| KN6 | Sürücü Atama | Manuel | ⬜ Bekliyor |
| KN7 | Canlı Takip | Supabase Realtime | ⬜ Bekliyor |
| KN8 | Algoritma Pipeline | Registry Pattern | ✅ Aktif |
| **KN9** | **Split Entegrasyonu** | **Giant Tour + Split** | 🔵 Planlanıyor |
| **KN10** | **Hibrit Algoritmalar** | **PSO/HHO/GWO/GA + Split** | 🔵 Planlanıyor |

---

## Faz Özeti

| Faz | Durum | Açıklama |
|-----|-------|----------|
| **Faz 1** | ✅ Tamamlandı | Kritik düzeltmeler |
| **Faz 1.5** | 🔵 Planlanıyor | **Split Entegrasyonu** |
| **Faz 2** | ⬜ Bekliyor | Veri kalıcılığı + Atama |
| **Faz 3** | ⬜ Bekliyor | İş akışı otomasyonu |
| **Faz 4** | ⬜ Bekliyor | İleri özellikler |

---

## Faz 1: Kritik Düzeltmeler ✅

### 1.1 Python API Bağlantısı
- **Durum:** ✅ Tamamlandı
- **Açıklama:** vehicle-planning → Python optimizer bağlantısı

### 1.2 Windows Encoding Fix
- **Durum:** ✅ Tamamlandı
- **Açıklama:** UTF-8 encoding düzeltmesi

### 1.3 Ölü Kod Temizliği
- **Durum:** ✅ Tamamlandı
- **Açıklama:** Eski TypeScript strateji dosyaları silindi

---

## Faz 1.5: Split Entegrasyonu 🔵

> **YENİ FAZ** - Hibrit algoritma mimarisi

### Görev 1.5.1: Split Decoder Modülü

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/utils/split_decoder.py`
- **Süre:** 3-4 saat
- **Öncelik:** 🔴 Kritik

**Yapılacaklar:**
- [ ] `SplitDecoder` sınıfı oluştur
- [ ] Dinamik programlama algoritması
- [ ] Capacity constraint entegrasyonu
- [ ] Time constraint entegrasyonu
- [ ] Unit testler yaz

**Kabul Kriterleri:**
- Giant tour input → Routes output
- Her route Sw ≤ 4, So ≤ 5
- Her route süresi ≤ max_tour_time
- Time matrix entegrasyonu
- Test coverage ≥ 80%

---

### Görev 1.5.2: Hibrit Base Strategy

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/hybrid_base_strategy.py`
- **Süre:** 1-2 saat
- **Bağımlılık:** Görev 1.5.1
- **Öncelik:** 🔴 Kritik

**Yapılacaklar:**
- [ ] `HybridSplitStrategy` base class
- [ ] `decode_tour()` metodu
- [ ] `_build_response()` yardımcı metotları
- [ ] Abstract `_optimize_giant_tour()` tanımı

---

### Görev 1.5.3: PSO-Split

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/pso_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `PSOSplitStrategy` sınıfı
- [ ] Swarm initialization
- [ ] Velocity update (swap operations)
- [ ] Fitness evaluation with Split decoder
- [ ] Test senaryoları

**Parametreler:**
```python
{
    "swarm_size": 30,
    "max_iterations": 100,
    "inertia_weight": 0.729,
    "cognitive_weight": 1.49445,
    "social_weight": 1.49445
}
```

---

### Görev 1.5.4: HHO-Split

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/hho_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `HHOSplitStrategy` sınıfı
- [ ] Hawk population initialization
- [ ] 4 siege strategy implementation
- [ ] Lévy Flight entegrasyonu
- [ ] Escape energy hesaplama

**Parametreler:**
```python
{
    "population_size": 30,
    "max_iterations": 100,
    "initial_energy": 1.0,
    "jump_probability": 0.5
}
```

---

### Görev 1.5.5: GWO-Split

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/gwo_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `GWOSplitStrategy` sınıfı
- [ ] Wolf pack initialization
- [ ] Alpha-Beta-Delta hierarchy
- [ ] Position update toward leaders

**Parametreler:**
```python
{
    "population_size": 30,
    "max_iterations": 100,
    "initial_a": 2.0
}
```

---

### Görev 1.5.6: GA-Split

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/ga_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `GASplitStrategy` sınıfı
- [ ] Population initialization
- [ ] Order Crossover (OX1)
- [ ] Swap/Inversion mutation
- [ ] Tournament selection + Elitism

**Parametreler:**
```python
{
    "population_size": 50,
    "max_iterations": 100,
    "crossover_rate": 0.85,
    "mutation_rate": 0.15,
    "elite_count": 2
}
```

---

### Görev 1.5.7: Local Search Modülü

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/utils/local_search.py`
- **Süre:** 1-2 saat
- **Öncelik:** 🟢 Orta

**Yapılacaklar:**
- [ ] 2-opt improvement
- [ ] Or-opt (relocate)
- [ ] Integration with hybrid strategies

---

### Görev 1.5.8: Strategy Registry Güncelleme

- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/__init__.py`
- **Süre:** 30 dk
- **Bağımlılık:** 1.5.3-1.5.6
- **Öncelik:** 🔴 Kritik

**Yapılacaklar:**
- [ ] Yeni stratejileri registry'ye ekle
- [ ] Factory metodunu güncelle
- [ ] Import'ları düzenle

```python
STRATEGY_REGISTRY = {
    # Mevcut
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    "hho": HarrisHawksStrategy,
    "gwo": GreyWolfStrategy,
    
    # YENİ
    "pso_split": PSOSplitStrategy,
    "hho_split": HHOSplitStrategy,
    "gwo_split": GWOSplitStrategy,
    "ga_split": GASplitStrategy,
}
```

---

### Görev 1.5.9: Frontend Güncelleme

- **Durum:** ⬜ Bekliyor
- **Dosya:** `src/lib/algorithm-constants.ts`
- **Süre:** 30 dk
- **Bağımlılık:** 1.5.8
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] Algoritma seçeneklerini güncelle
- [ ] Varsayılan algoritmayı değiştir (pso_split)

```typescript
export const ALGORITHM_OPTIONS = [
  // Önerilen
  { value: 'pso_split', label: 'PSO + Optimal Split (Önerilen)' },
  { value: 'hho_split', label: 'HHO + Optimal Split' },
  { value: 'gwo_split', label: 'GWO + Optimal Split' },
  { value: 'ga_split', label: 'GA + Optimal Split' },
  
  // Eski (opsiyonel)
  { value: 'genetic_algorithm', label: 'Genetik Algoritma (Eski)' },
  { value: 'pso', label: 'PSO (Eski)' },
];
```

---

### Görev 1.5.10: Benchmark Testleri

- **Durum:** ⬜ Bekliyor
- **Dosya:** `tests/benchmark_split.py`
- **Süre:** 3-4 saat
- **Bağımlılık:** Tüm 1.5.x görevleri
- **Öncelik:** 🟢 Orta

**Test Senaryoları:**

| ID | N | Sw% | So% | Açıklama |
|----|---|-----|-----|----------|
| S1 | 30 | 30% | 70% | Mevcut ölçek |
| S2 | 100 | 30% | 70% | Orta ölçek |
| S3 | 300 | 30% | 70% | Hedef ölçek |
| S4 | 100 | 50% | 50% | Dengeli |
| S5 | 100 | 70% | 30% | Ağır Sw |

**Metrikler:**
- Toplam araç sayısı
- Toplam süre
- Tek öğrencilik rota oranı
- Execution time
- Feasibility rate

---

## Faz 2: Veri Kalıcılığı + Atama ⬜

> Faz 1.5 tamamlandıktan sonra başlanacak

### 2.1 Route Plans DB
- Rota sonuçlarını veritabanına kaydet
- `route_plans` tablosu oluşturulacak

### 2.2 Sürücü Atama
- Manuel atama mekanizması
- Admin dropdown'dan seçer

### 2.3 Payload Düzeltmeleri
- Multi-vehicle-routing.ts güncellemesi

---

## Faz 3: İş Akışı Otomasyonu ⬜

> Faz 2 tamamlandıktan sonra başlanacak

### 3.1 Hybrid Onay/İptal
- Ders içi: Otomatik onay
- Ders dışı: Talep bazlı

### 3.2 Dashboard Güncellemeleri
- Öğrenci dashboard
- Sürücü dashboard

---

## Faz 4: İleri Özellikler ⬜

> Faz 3 tamamlandıktan sonra başlanacak

### 4.1 Canlı Takip
- Supabase Realtime
- Driver location updates

### 4.2 Dinamik Time Matrix
- Google Distance Matrix API
- Matris güncelleme mekanizması

---

## Bağımlılık Haritası

```
Görev 1.5.1 (Split Decoder)
    │
    ├──→ Görev 1.5.2 (Hybrid Base)
    │        │
    │        ├──→ Görev 1.5.3 (PSO-Split)
    │        ├──→ Görev 1.5.4 (HHO-Split)
    │        ├──→ Görev 1.5.5 (GWO-Split)
    │        └──→ Görev 1.5.6 (GA-Split)
    │                 │
    │                 └──→ Görev 1.5.8 (Registry)
    │                          │
    │                          └──→ Görev 1.5.9 (Frontend)
    │
    └──→ Görev 1.5.7 (Local Search) [Paralel]

Görev 1.5.10 (Benchmark) ← Tüm 1.5.x tamamlandıktan sonra

Faz 2 ← Faz 1.5 tamamlandıktan sonra
Faz 3 ← Faz 2 tamamlandıktan sonra
Faz 4 ← Faz 3 tamamlandıktan sonra
```

---

## Zaman Çizelgesi

| Hafta | Görevler | Tahmini Süre |
|-------|----------|--------------|
| Hafta 1 | 1.5.1 + 1.5.2 | 4-6 saat |
| Hafta 1-2 | 1.5.3-1.5.6 | 8-12 saat |
| Hafta 2 | 1.5.7 + 1.5.8 + 1.5.9 | 2-3 saat |
| Hafta 2-3 | 1.5.10 (Benchmark) | 3-4 saat |
| **TOPLAM** | **Faz 1.5** | **18-25 saat** |

---

## Görev Alma Kuralları

1. **Atanan alanını güncelle** - Görevi almadan önce
2. **Durumu değiştir** - Başladığında `in_progress`, bitirdiğinde `completed`
3. **CHANGELOG.md güncelle** - Her değişiklikte
4. **Bağımlılıklara dikkat et** - Önceki görevler tamamlanmadan başlama
5. **Test yaz** - Her yeni modül için unit test
6. **Dokümantasyon** - Kod içinde yeterli comment

---

## Akademik Yayın Takibi

| Aşama | Durum |
|-------|-------|
| Problem Tanımı | ✅ |
| Literatür Taraması | ✅ |
| Yöntem Seçimi | ✅ |
| Implementasyon | ⬜ Faz 1.5 |
| Deneyler | ⬜ Faz 1.5.10 |
| Yazım | ⬜ Sonraki |

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
