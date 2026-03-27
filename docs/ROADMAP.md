# 🗺️ UniRide Geliştirme Yol Haritası

> **Her geliştirici yeni iş almadan önce bu dokümanı kontrol etmeli ve hangi faz/görevde çalıştığını belirtmelidir.**  
> Son güncelleme: 27 Mart 2026  
> Onaylanan mimari kararlar: [Tasarım Dokümanı](./superpowers/specs/2026-03-25-full-system-design.md)

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
| KN9 | Algoritma Pipeline | Registry Pattern (mevcut) | Mevcut |
| **KN10** | **Split Entegrasyonu** | **Giant Tour + Optimal Split (Prins, 2004)** | **Faz 1.5** |
| **KN11** | **Hibrit Algoritmalar** | **PSO/HHO/GWO/GA + Split Decoder** | **Faz 1.5** |
| **KN12** | **Çift Pipeline** | **Pipeline A (Sweep/CW) ∥ Pipeline B (Split)** | **Faz 1.5** |
| **KN13** | **Holistik Çözücüler** | **PyVRP (HGS) + VROOM (C++) bağımsız çözücüler** | **Faz 1.5** |

---

## Faz Durumu Özeti

| Faz | Durum | Açıklama |
|---|---|---|
| **Faz 1: Kritik Düzeltmeler** | ✅ Tamamlandı | Sistem çalışır hale geldi |
| **Faz 1.5: Çift Pipeline + Split** | 🔵 Devam Ediyor | Pipeline A (Sweep/CW) + Pipeline B (Giant Tour + Split) |
| **Faz 2: Veri Kalıcılığı + Atama** | ⬜ Bekliyor | Rota kaydı + sürücü ataması |
| **Faz 3: İş Akışı Otomasyonu** | ⬜ Bekliyor | Onay/iptal + bildirim |
| **Faz 4: İleri Özellikler** | ⬜ Bekliyor | Canlı takip + dinamik matris |

---

## Faz 1: Kritik Düzeltmeler 🔴

> Bu faz tamamlanmadan sistem operasyonel olarak **kullanılamaz**.

### Görev 1.1: `vehicle-planning` → Python API Bağlantısı (KN1)
- **Durum:** ✅ Tamamlandı
- **Atanan:** Antigravity AI
- **Tahmini süre:** 2-3 saat
- **Mimari karar:** İşlev bazlı proxy — her endpoint kendi amacına odaklı kalır

**Değiştirilecek dosyalar:**

#### A) `src/app/api/calculate-vehicles/route.ts` — YENİDEN YAZ
```
ESKİ akış: import { calculateRequiredVehicles } from "@/services/vehicle-calculator"
YENİ akış: import { optimizeRoutes } from "@/services/optimizer-service"
           import { normalizeAlgorithmName } from "@/lib/algorithm-constants"

1. Body'den strategy + clusteringAlgorithm al
2. normalizeAlgorithmName(strategy) ile dönüştür
3. Öğrencileri StudentForOptimization formatına çevir:
   { id, name, location_code, disability_type, coordinates }
4. optimizeRoutes(students, depot, options) çağır
5. Response'u UI formatına map et:
   Python döndürüyor → { routes[], total_vehicles, total_duration_minutes }
   UI bekliyor → { requiredVehicles, assignments[], totalDuration, message, meta }
   
   Her route → assignment mapping:
     vehicleIndex  = route.vehicle_id veya index+1
     students      = route.student_ids üzerinden öğrenci lookup
     route         = route.route_details
     totalDuration = route.total_duration_minutes
     swCount       = route.sw_count
     soCount       = route.so_count
```

#### B) `src/app/(app)/admin/vehicle-planning/page.tsx` — GÜNCELLE
```
1. SİL → satır 25-31'deki lokal strategies array
2. EKLE → import { ALGORITHM_OPTIONS } from "@/lib/algorithm-constants"
3. DEĞİŞTİR → Select'te ALGORITHM_OPTIONS kullan
4. DEĞİŞTİR → Default strategy = "genetic_algorithm"
5. handleCalculate() → body'ye clusteringAlgorithm'i de ekle (zaten gönderiliyor)
```

#### C) `src/services/vehicle-calculator.ts` — SONRA SİLİNECEK
- A+B tamamlanıp test edildikten sonra silinir (Görev 1.3 ile birlikte)

---

### Görev 1.2: Windows Encoding Fix (KN3)
- **Durum:** ✅ Tamamlandı
- **Atanan:** Antigravity AI
- **Tahmini süre:** 15 dakika
- **Dosya:** `optimizer_api/utils/data_loader.py`

```
Dosyanın başına ekle:
  import sys
  if sys.platform == 'win32':
      sys.stdout.reconfigure(encoding='utf-8', errors='replace')

Tüm print() mesajlarından Unicode özel karakterleri (✓, ✗ vb.) temizle
veya ASCII karşılıklarını kullan: [OK], [FAIL], [!]
```

---

### Görev 1.3: Ölü Kod Temizliği (KN2)
- **Durum:** ✅ Tamamlandı
- **Atanan:** Antigravity AI
- **Tahmini süre:** 30 dakika
- **Mimari karar:** Temiz silme — fallback tutmak iki ayrı bakım demek

> ⚠️ **Görev 1.1 tamamlanmadan bu göreve başlama** — bağımlılık kırılır.

```
Silinecek dosyalar:
  src/services/vehicle-calculator.ts
  src/services/doubus/route-strategies/ga-strategy.ts    (zaten yok)
  src/services/doubus/route-strategies/pso-strategy.ts   (zaten yok)
  src/services/doubus/route-strategies/index.ts          → import'ları sil veya dosyayı sil
  src/services/doubus/route-strategies/types.ts          → bağımlılık kontrolü yap
  src/services/doubus/route-strategies/nearest-neighbor-strategy.ts
  src/services/doubus/route-strategies/permutation-strategy.ts
  src/services/doubus/route-strategies/two-opt-strategy.ts

Kontrol et: src/services/doubus/ altındaki diğer dosyalar
  (multi-vehicle-routing.ts, route.ts vb.) route-strategies'i
  import ediyor mu? Ediyorsa import'ları kaldır.

Son olarak: calculate-vehicles/route.ts'in eski import'u kaldırıldığını doğrula.
```

---

## Faz 1.5: Çift Pipeline + Split Entegrasyonu 🟣

> **YENİ FAZ** — K-Means + Katı Kümeleme sorununu **iki paralel pipeline** ile çözer (KN12).  
> Pipeline A: K-Means → **Sweep/Clarke-Wright** + Sezgisel  
> Pipeline B: **Giant Tour + Split Decoder** (Prins, 2004)  
> Detaylı mimari → [ARCHITECTURE.md §3](./ARCHITECTURE.md)

### Sorun Özeti

Mevcut "Cluster-First, Route-Second" mimarisi K-Means ile kümeleme yapıp, süre kısıtı aşıldığında araç sayısını +1 artırarak tek öğrencilik verimsiz rotalar oluşturmaktadır (%15-20). Split Decoder, bu problemi ortadan kaldırır:

| Metrik | Mevcut (K-Means) | Hedef (Split) | İyileştirme |
|--------|------------------|---------------|-------------|
| Ort. Araç Sayısı | 7-8 | 5-6 | -20% |
| Tek Öğrenci Rotalar | %15-20 | <%5 | -75% |
| Feasibility | %92 | %100 | +8% |
| Time Matrix | Duyarsız | Duyarlı | ✓ |

---

### Görev 1.5.1: Split Decoder Modülü
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/utils/split_decoder.py`
- **Süre:** 3-4 saat
- **Öncelik:** 🔴 Kritik

**Yapılacaklar:**
- [ ] `SplitDecoder` sınıfı oluştur
- [ ] Dinamik programlama (DP) ile optimal bölme algoritması
- [ ] Sw/So heterojen kapasite constraint entegrasyonu
- [ ] Time matrix duyarlı süre constraint entegrasyonu
- [ ] Unit testler yaz

**Kabul Kriterleri:**
- Giant tour input → Routes output
- Her route: Sw ≤ 4, So ≤ 5
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
- [ ] `HybridSplitStrategy` base class (BaseRoutingStrategy'den türetilir)
- [ ] `decode_tour()` metodu → Split Decoder çağrısı
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
- [ ] Swarm initialization (giant tour permütasyonları)
- [ ] Velocity update (swap operations)
- [ ] Fitness evaluation → Split decoder ile maliyet hesaplama
- [ ] Test senaryoları

---

### Görev 1.5.4: HHO-Split
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/hho_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `HHOSplitStrategy` sınıfı
- [ ] 4 siege strategy (Soft/Hard Besiege ± Progressive Dives)
- [ ] Lévy Flight entegrasyonu (lokal optimumdan kaçış)
- [ ] Escape energy hesaplama

---

### Görev 1.5.5: GWO-Split
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/gwo_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `GWOSplitStrategy` sınıfı
- [ ] Alpha-Beta-Delta hierarchy
- [ ] Position update toward leaders

---

### Görev 1.5.6: GA-Split
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/ga_split_strategy.py`
- **Süre:** 2-3 saat
- **Bağımlılık:** Görev 1.5.2
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] `GASplitStrategy` sınıfı
- [ ] Order Crossover (OX1) + Selection
- [ ] Swap/Inversion mutation
- [ ] Tournament selection + Elitism

---

### Görev 1.5.7: Local Search Modülü Genişletme
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/utils/local_search.py`
- **Süre:** 1-2 saat
- **Öncelik:** 🟢 Orta (Paralel çalışılabilir)

**Yapılacaklar:**
- [ ] 2-opt improvement (mevcut, genişletilecek)
- [ ] Or-opt (relocate) ekleme
- [ ] Hibrit stratejilerle entegrasyon

---

### Görev 1.5.8: Strategy Registry Güncelleme
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/__init__.py`
- **Süre:** 30 dk
- **Bağımlılık:** Görev 1.5.3-1.5.6
- **Öncelik:** 🔴 Kritik

**Yapılacaklar:**
- [ ] Yeni hibrit stratejileri STRATEGY_REGISTRY'ye ekle
- [ ] Factory metodunu güncelle

```python
STRATEGY_REGISTRY = {
    # Mevcut
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    "hho": HarrisHawksStrategy,
    "gwo": GreyWolfStrategy,
    
    # YENİ: Split tabanlı
    "pso_split": PSOSplitStrategy,
    "hho_split": HHOSplitStrategy,
    "gwo_split": GWOSplitStrategy,
    "ga_split": GASplitStrategy,
}
```

---

### Görev 1.5.9: Frontend Algoritma Seçenekleri Güncelleme
- **Durum:** ⬜ Bekliyor
- **Dosya:** `src/lib/algorithm-constants.ts`
- **Süre:** 30 dk
- **Bağımlılık:** Görev 1.5.8
- **Öncelik:** 🟡 Yüksek

**Yapılacaklar:**
- [ ] Yeni Split algoritma seçeneklerini `ALGORITHM_OPTIONS`'a ekle
- [ ] Varsayılan algoritmayı `pso_split` olarak değiştir
- [ ] Split seçildiğinde "Kümeleme Yöntemi" dropdown'ını gizle

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
| S2 | 50 | 30% | 70% | Küçük büyüme |
| S3 | 100 | 30% | 70% | Orta ölçek |
| S4 | 300 | 30% | 70% | Hedef ölçek |
| S5 | 100 | 50% | 50% | Dengeli |
| S6 | 100 | 70% | 30% | Ağır Sw |

**Metrikler:** Toplam araç, toplam süre, tek öğrencilik rota %, execution time, feasibility rate  
**İstatistik:** Her senaryo 10 run → Mean, Std, Min, Max + ANOVA testi

---

### Görev 1.5.11: PyVRP Entegrasyonu
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/pyvrp_strategy.py`
- **Süre:** 2-3 saat
- **Öncelik:** 🟡 Yüksek
- **Bağımlılık:** Yok (bağımsız çözücü)
- **Paket:** `pip install pyvrp`

**Neden?**
PyVRP, Hybrid Genetic Search (HGS-CVRP) tabanlı, DIMACS 2021 VRPTW yarışması birincisi, state-of-the-art akademik çözücüdür. Heterojen araç tipleri, time windows, multi-depot native desteklenir.

**Yapılacaklar:**
- [ ] `pyvrp` paketini `requirements.txt`'e ekle
- [ ] `PyVRPStrategy` sınıfı oluştur (BaseRoutingStrategy'den)
- [ ] Sw/So heterojen kapasite → PyVRP `VehicleType` mapping
- [ ] Time matrix → PyVRP `Edge` / distance matrix mapping
- [ ] `max_tour_time` → duration constraint mapping
- [ ] Response → `OptimizationResponse` dönüşümü
- [ ] STRATEGY_REGISTRY'ye `pyvrp` key ile kaydet

---

### Görev 1.5.12: VROOM Entegrasyonu
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/strategies/vroom_strategy.py`
- **Süre:** 2-3 saat
- **Öncelik:** 🟡 Yüksek
- **Bağımlılık:** Yok (bağımsız çözücü)
- **Paket:** `pip install pyvroom`

**Neden?**
VROOM, C++ motoru sayesinde 1000+ nokta < 5 saniye çözer. CVRPTW, HFVRP, PDPTW, multi-trip native desteklenir. Hız kritik ve büyük ölçek senaryoları için idealdir.

**Yapılacaklar:**
- [ ] `pyvroom` paketini `requirements.txt`'e ekle
- [ ] `VROOMStrategy` sınıfı oluştur (BaseRoutingStrategy'den)
- [ ] Sw/So kapasite → VROOM `Vehicle` mapping
- [ ] Time matrix → VROOM matrix mapping
- [ ] `max_tour_time` → max_travel_time constraint mapping
- [ ] Response → `OptimizationResponse` dönüşümü
- [ ] STRATEGY_REGISTRY'ye `vroom` key ile kaydet

---

### Faz 1.5 Zaman Çizelgesi

| Hafta | Görevler | Tahmini Süre |
|-------|----------|--------------|
| Hafta 1 | 1.5.1 + 1.5.2 | 4-6 saat |
| Hafta 1-2 | 1.5.3-1.5.6 (paralel) | 8-12 saat |
| Hafta 2 | 1.5.7 + 1.5.8 + 1.5.9 | 2-3 saat |
| Hafta 2 | 1.5.11 + 1.5.12 (paralel, bağımsız) | 4-6 saat |
| Hafta 2-3 | 1.5.10 (Benchmark — tüm algoritmalar) | 3-4 saat |
| **TOPLAM** | **Faz 1.5** | **22-31 saat** |

---

## Faz 2: Veri Kalıcılığı ve Atama 🟡

> Faz 1.5 tamamlandıktan sonra başlanabilir.

### Görev 2.1: Rota Sonuçlarını Veritabanına Kaydet (KN4)
- **Durum:** ⬜ Bekliyor
- **Atanan:** —
- **Tahmini süre:** 4-5 saat
- **Mimari karar:** Minimal JSON — tek tablo, hızlı başlangıç

#### A) Supabase Migration
```sql
CREATE TABLE route_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_date DATE NOT NULL,
  direction TEXT CHECK (direction IN ('pickup', 'dropoff')),
  algorithm_used TEXT NOT NULL,
  clustering_used TEXT DEFAULT 'kmeans',
  total_vehicles INT NOT NULL,
  total_duration_minutes FLOAT NOT NULL,
  execution_time_seconds FLOAT,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft','confirmed','active','completed','cancelled')),
  routes JSONB NOT NULL,
  student_count INT,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  confirmed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

-- RLS
ALTER TABLE route_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins can CRUD" ON route_plans
  FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );
CREATE POLICY "Drivers can read assigned" ON route_plans
  FOR SELECT USING (status IN ('confirmed', 'active'));
```

#### B) API Endpoint
```
POST /api/route-plans       → Yeni plan kaydet
GET  /api/route-plans       → Planları listele (tarih/durum filtreli)
PATCH /api/route-plans/:id  → Durumu güncelle (confirm/cancel/complete)
```

#### C) UI Değişiklikleri
```
vehicle-planning sayfasına:
  - "Planı Kaydet" butonu → optimizasyon sonucu Supabase'e yazılır
  - "Kaydedilen Planlar" listesi → tarih + durum + algoritma gösterilir
  - Durum geçişleri: draft → confirmed → active → completed
```

---

### Görev 2.2: Manuel Sürücü Ataması (KN6)
- **Durum:** ⬜ Bekliyor
- **Atanan:** —
- **Tahmini süre:** 3-4 saat
- **Mimari karar:** Manuel atama — admin dropdown'dan seçer

#### A) DB Değişikliği
```sql
-- route_plans tablosuna veya ayrı bir tablo:
ALTER TABLE route_plans ADD COLUMN driver_assignments JSONB;
-- Format: [{ "vehicle_index": 1, "driver_id": "uuid" }, ...]
```

#### B) UI: Sürücü Atama Paneli
```
Confirmed plan açıldığında her araç için:
  - Sürücü dropdown (vehicles tablosundan aktif sürücüler)
  - "Ata" butonu → driver_assignments güncellenir
  - Tüm araçlara sürücü atandığında → "Planı Aktifleştir" butonu
```

---

### Görev 2.3: `multi-vehicle-routing.ts` Payload Düzeltmesi
- **Durum:** ⬜ Bekliyor
- **Dosya:** `src/services/doubus/multi-vehicle-routing.ts`

```
ESKİ payload:  { id: locationCode, type: type }
YENİ payload:  { id: userId, name: userName, location_code: locationCode, disability_type: type }

Python StudentNode schema'sına uyumlu olmalı.
```

---

### Görev 2.4: DataLoader Fallback İyileştirme
- **Durum:** ⬜ Bekliyor
- **Dosya:** `optimizer_api/utils/data_loader.py`

```
Mevcut: time_matrix yüklenmezse sıfır matris (tüm süreler 0)
Hedef: Fail-fast → sunucu başlatılırken hata ver, sıfır matris ile çalışma

  if self._use_coordinates or self.time_matrix is None:
      raise RuntimeError("time_matrix yüklenemedi. Supabase bağlantısını kontrol edin.")
```

---

## Faz 3: İş Akışı Otomasyonu 🟠

> Faz 2 tamamlandıktan sonra başlanabilir.

### Görev 3.1: Hybrid Onay/İptal Mekanizması (KN5)
- **Durum:** ⬜ Bekliyor
- **Atanan:** —
- **Tahmini süre:** 6-8 saat
- **Mimari karar:** Ders içi otomatik + ders dışı talep bazlı

#### A) Otomatik Talep Üretimi (Ders İçi)
```
Cron/Scheduled function: Her gece 00:00
  1. Ertesi günkü weekly_schedules kayıtlarını al
  2. Her ders girişi için ride_requests tablosuna "auto_confirmed" kayıt oluştur
  3. Kaynak: schedule_id referansı tut

ride_requests tablosuna yeni kolonlar:
  source TEXT DEFAULT 'manual' CHECK (source IN ('schedule', 'manual'))
  auto_confirmed BOOLEAN DEFAULT false
  cancellation_deadline TIMESTAMPTZ
```

#### B) İptal Penceresi (Ders İçi)
```
Öğrenci uygulamasında "Yarınki Seferlerim" kartı:
  - Otomatik oluşturulan talepler listelenir
  - "İptal Et" butonu → deadline öncesi çalışır (ör: 22:00)
  - Deadline sonrası iptal edilemez
```

#### C) Manuel Talep Akışı (Ders Dışı)
```
Mevcut request-ride sayfası korunur.
  - Öğrenci istediği zaman ek talep oluşturur
  - Bu talepler aktif onay gerektirir (auto_confirmed = false)
  - Admin onayladıktan sonra rota planlamasına dahil edilir
```

#### D) Rota Planlaması Entegrasyonu
```
Admin sabah rota planladığında:
  1. O günkü onaylı ride_requests filtrelenir
  2. source=schedule (auto + iptal edilmemiş) + source=manual (onaylı)
  3. Filtrelenmiş liste vehicle-planning'e aktarılır
```

---

### Görev 3.2: Öğrenci Dashboard Güncellemesi
- **Durum:** ⬜ Bekliyor

```
/dashboard sayfasına kartlar:
  - "Yarınki Seferlerim" → onay/iptal
  - "Bugünkü Seferim" → araç, sürücü, tahmini alınma saati
  - "Geçmiş Seferler" → son 30 gün
```

---

### Görev 3.3: Sürücü Dashboard Güncellemesi
- **Durum:** ⬜ Bekliyor

```
/driver/assignments sayfasına:
  - "Bugünkü Rotam" → öğrenci listesi, rota sırası, adresler
  - "Navigasyonu Başlat" → rota detayları
  - Veri kaynağı: route_plans tablosu (status = 'active')
```

---

## Faz 4: İleri Özellikler 🔵

> Faz 3 tamamlandıktan sonra başlanabilir.

### Görev 4.1: Canlı Konum Takibi (KN7)
- **Durum:** ⬜ Bekliyor
- **Mimari karar:** Supabase Realtime

```sql
CREATE TABLE driver_locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  driver_id UUID REFERENCES auth.users(id),
  route_plan_id UUID REFERENCES route_plans(id),
  lat FLOAT NOT NULL,
  lng FLOAT NOT NULL,
  heading FLOAT,
  speed_kmh FLOAT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Insert-only, son konum = en yeni kayıt
CREATE INDEX idx_driver_loc_latest ON driver_locations(driver_id, updated_at DESC);
```

```
Sürücü uygulaması: 10 sn aralıkla konum UPDATE
Öğrenci/Admin: Supabase realtime subscription ile dinle
ETA hesaplama: Mevcut konum + kalan rota durakları → time_matrix'ten toplam süre
```

---

### Görev 4.2: Hybrid Time Matrix Güncelleme (KN3-C evrim)
- **Durum:** ⬜ Bekliyor

```
Admin panele "Matrisi Güncelle" butonu:
  1. Google Distance Matrix API çağrısı
  2. Yeni/güncellenmiş edge'ler time_matrix'e yazılır
  3. DataLoader singleton cache'i invalidate edilir
  
Sadece ihtiyaç olduğunda çalışır — otomatik değil.
```

---

### Görev 4.3: Adres → En Yakın Kod Eşleme (KN8-B evrim)
- **Durum:** ⬜ Bekliyor

```
Öğrenci kayıt/profil sayfasında:
  1. Adres gir veya haritadan seç → geocode → lat/lng
  2. Tüm Sw/So kodlarının koordinatlarıyla karşılaştır
  3. En yakın kodu otomatik ata (haversine)
  4. Öğrenci onaylar veya düzeltir
```

---

### Görev 4.4: Sürücü Öneri + Onay (KN6-C evrim)
- **Durum:** ⬜ Bekliyor

```
Admin rota onaylayınca:
  1. Sistem müsait sürücüleri listeler
  2. Workload dengesi + bölge uyumu ile sıralama yapar
  3. Admin önerileni kabul eder veya değiştirir
```

---

## Görev Alma ve Takip Kuralları

1. Bir görevi almadan önce bu dosyada **"Atanan"** alanını güncelle
2. Görev tamamlandığında durumu `✅ Tamamlandı` olarak işaretle
3. `docs/CHANGELOG.md`'ye değişikliği kaydet
4. **Faz sırasını atlamadan ilerle** (1 → 1.5 → 2 → 3 → 4)
5. Aynı faz içinde görevler paralel yapılabilir

## Bağımlılık Haritası

```
Faz 1 (✅ Tamamlandı)
 1.1 (vehicle-planning fix) ✅
  ├── 1.3 (ölü kod silme) ✅
  └── Faz 1.5 (Split Entegrasyonu)

Faz 1.5 (Çift Pipeline + Split)
 1.5.1 (Split Decoder)
     │
     ├──→ 1.5.2 (Hybrid Base)
     │        │
     │        ├──→ 1.5.3 (PSO-Split)
     │        ├──→ 1.5.4 (HHO-Split)
     │        ├──→ 1.5.5 (GWO-Split)
     │        └──→ 1.5.6 (GA-Split)
     │                 │
     │                 └──→ 1.5.8 (Registry)
     │                          │
     │                          └──→ 1.5.9 (Frontend)
     │
     └──→ 1.5.7 (Local Search) [Paralel]

 1.5.11 (PyVRP)  → Bağımsız, paralel çalışılabilir
 1.5.12 (VROOM)  → Bağımsız, paralel çalışılabilir

 1.5.10 (Benchmark) ← Tüm 1.5.x tamamlandıktan sonra

Faz 2 ← Faz 1.5 tamamlandıktan sonra
 2.1 (rota kaydı) → 2.2 (sürücü ataması)
 2.3 (payload fix) → Bağımsız
 2.4 (DataLoader) → Bağımsız

Faz 3 ← Faz 2 tamamlandıktan sonra
 3.1 (onay/iptal) → 3.2 (öğrenci dashboard) + 3.3 (sürücü dashboard)

Faz 4 ← Faz 3 tamamlandıktan sonra
 4.1 (canlı takip) → 4.4 (sürücü öneri)
 4.2 (matris güncelleme) → Bağımsız
 4.3 (adres eşleme) → Bağımsız
```

## Akademik Yayın Takibi

| Aşama | Durum |
|-------|-------|
| Problem Tanımı | ✅ |
| Literatür Taraması | ✅ |
| Yöntem Seçimi (Giant Tour + Split) | ✅ |
| Implementasyon | ⬜ Faz 1.5 |
| Deneyler (Benchmark) | ⬜ Faz 1.5.10 |
| Yazım | ⬜ Sonraki |

**Önerilen Makale Başlığı:**
> "Hybrid Meta-Heuristic Algorithms with Optimal Split for Heterogeneous CVRPTW: A Case Study on Disabled Student Transportation"

