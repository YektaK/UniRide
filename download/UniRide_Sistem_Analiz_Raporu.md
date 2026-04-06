# UniRide CVRP Sistemi - Kapsamlı Analiz Raporu

**Tarih:** 25 Mart 2026  
**Analiz Kapsamı:** Tasarım dokümanları, mevcut kod yapısı, beklenen iş akışı

---

## 1. Genel Bakış

### 1.1 Proje Amacı
Engelli öğrencilerin evlerinden okula/okuldan eve taşınması için yardımcı servis uygulaması. Öğrenci kaydı, ders programı yönetimi, rota optimizasyonu ve araç ataması işlevlerini içerir.

### 1.2 Beklenen Sistem Akışı
```
┌─────────────────────────────────────────────────────────────────────┐
│                         KULLANICI KATMANI                           │
│  Öğrenci: Kayıt, Ders Programı, Onay/İptal, Canlı Takip            │
│  Admin: Öğrenci Yönetimi, Rota Planlama, Algoritma Seçimi          │
│  Şöför: Atamalar, Navigasyon                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      NEXT.JS API ROUTES                             │
│  /api/optimize-route      → Python API (optimizer-service.ts)       │
│  /api/calculate-vehicles  → ⚠️ KOPUK - TypeScript local kod        │
│  /api/compare-algorithms  → Python API                              │
│  /api/ride-confirmation   → Supabase                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                   PYTHON FASTAPI (localhost:8000)                   │
│  POST /api/v1/optimize   → Algoritma çalıştırır                     │
│  POST /api/v1/compare    → Tüm algoritmaları karşılaştırır          │
│  GET  /api/v1/strategies → Algoritma listesi                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                        SUPABASE                                     │
│  users, weekly_schedules, ride_requests, vehicles, time_matrix      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Algoritma Uyumluluk Analizi

### 2.1 Beklenen Algoritmalar
| Algoritma | Açıklama | Beklenen Konum |
|-----------|----------|----------------|
| `nearest-neighbor` | Greedy / En Yakın Komşu | Python + UI |
| `permutation` | Permütasyon (Optimal) | Python + UI |
| `two-opt` | Two-Opt Local Search | Python + UI |
| `genetic_algorithm` | Genetik Algoritma | Python + UI |
| `pso` | Parçacık Sürü Optimizasyonu | Python + UI |

### 2.2 Mevcut Durum - Python Backend

| Algoritma | Dosya Mevcut | Registry'de Kayıtlı | Durum |
|-----------|--------------|---------------------|-------|
| `genetic_algorithm` | ✅ `ga_strategy.py` | ✅ | ÇALIŞIYOR |
| `pso` | ✅ `pso_strategy.py` | ✅ | ÇALIŞIYOR |
| `gwo` | ✅ `gwo_strategy.py` | ❌ **HAYIR** | **KAYIT DIŞI** |
| `hho` | ✅ `hho_strategy.py` | ❌ **HAYIR** | **KAYIT DIŞI** |
| `two_opt` | ✅ `two_opt_strategy.py` | ❌ **HAYIR** | **KAYIT DIŞI** |
| `greedy` | ✅ `greedy_heuristic.py` | ✅ (`nearest_neighbor` alias) | ÇALIŞIYOR |
| `permutation_tsp` | ✅ `permutation_tsp.py` | ✅ (`permutation` alias) | ÇALIŞIYOR |
| `ortools_cvrp` | ✅ `ortools_cvrp.py` | ✅ | ÇALIŞIYOR |

**KRİTİK SORUN:** `gwo_strategy.py`, `hho_strategy.py`, `two_opt_strategy.py` dosyaları fiziksel olarak mevcut ANCAK `strategies/__init__.py` dosyasında STRATEGY_REGISTRY'ye kayıtlı DEĞİL!

### 2.3 Mevcut Durum - Frontend

| Algoritma | `algorithm-constants.ts` | `optimizer-service.ts` | UI'da Görünür |
|-----------|--------------------------|------------------------|---------------|
| `genetic_algorithm` | ✅ | ✅ | ✅ |
| `pso` | ✅ | ✅ | ✅ |
| `gwo` | ✅ | ✅ | ✅ |
| `hho` | ✅ | ✅ | ✅ |
| `two_opt` | ❌ **YOK** | ✅ (type) | ❌ **YOK** |
| `greedy` | ✅ | ✅ | ✅ |
| `permutation_tsp` | ✅ | ✅ | ✅ |

**SORUN:** Frontend'de `two_opt` standalone algoritması `ALGORITHM_OPTIONS` dizisine eklenmemiş.

### 2.4 Algoritma Key Uyumsuzlukları

| Frontend Key | Python Key | Uyumlu mu? |
|-------------|------------|------------|
| `genetic_algorithm` | `genetic_algorithm` | ✅ |
| `pso` | `pso` | ✅ |
| `gwo` | `gwo` | ❌ Registry'de yok |
| `hho` | `hho` | ❌ Registry'de yok |
| `two_opt` | `two_opt` | ❌ Registry'de yok |
| `greedy` | `greedy` | ✅ |
| `nearest_neighbor` | `nearest_neighbor` | ✅ (alias) |
| `permutation_tsp` | `permutation_tsp` | ✅ |
| `ortools_cvrp` | `ortools_cvrp` | ✅ |

---

## 3. Kritik Kopukluklar

### 3.1 🔴 KRİTİK: `vehicle-planning` Sayfası Python'a Bağlı Değil

**Beklenen Akış:**
```
vehicle-planning UI → /api/calculate-vehicles → optimizer-service.ts → Python API
```

**Mevcut Akış:**
```
vehicle-planning UI → /api/calculate-vehicles → vehicle-calculator.ts → doubus/route-strategies (TypeScript)
```

**Sorun:** `src/app/api/calculate-vehicles/route.ts` dosyası:
- `vehicle-calculator.ts` import ediyor (eski TypeScript kodu)
- `doubus/route-strategies` kullanıyor (ölü kod)
- Python API'ye hiç bağlanmıyor

**Etki:** Admin araç planlama sayfası çalışmıyor / yanlış sonuç veriyor.

### 3.2 🔴 KRİTİK: Python'da GWO, HHO, Two-Opt Kayıtlı Değil

**Dosya:** `optimizer_api/strategies/__init__.py`

**Mevcut Registry:**
```python
STRATEGY_REGISTRY: Dict[str, BaseRoutingStrategy] = {
    "genetic_algorithm": _ga_strategy,
    "ga": _ga_strategy,
    "pso": _pso_strategy,
    "greedy": _greedy_strategy,
    "nearest_neighbor": _greedy_strategy,
    "permutation_tsp": _permutation_strategy,
    "permutation": _permutation_strategy,
    "ortools_cvrp": _ortools_strategy,
    "ortools": _ortools_strategy,
}
# GWO, HHO, TWO_OPT YOK!
```

**Etki:** Frontend'den `gwo`, `hho`, `two_opt` algoritmaları seçilirse Python 400 hatası döner.

### 3.3 🟠 ORTA: TypeScript ve Python'da Farklı Strateji İsimleri

**TypeScript (`route-strategies/index.ts`):**
```typescript
const strategies: Record<string, RouteStrategy> = {
  "permutation": ...,
  "nearest-neighbor": ...,
  "two-opt": ...,
  "genetic-algorithm": ...,  // tireli!
  "pso": ...,
};
```

**Python (`__init__.py`):**
```python
STRATEGY_REGISTRY = {
    "genetic_algorithm": ...,  # alt tireli!
    "pso": ...,
    "greedy": ...,
    "permutation_tsp": ...,  # farklı isim!
}
```

**Etki:** Frontend'den `"genetic-algorithm"` gönderilirse Python bulamaz.

### 3.4 🟠 ORTA: Eski TypeScript Kodu Hala Mevcut

**Silinecek dosyalar (ROADMAP.md'de belirtilen):**
- `src/services/vehicle-calculator.ts` ← Hala kullanılıyor!
- `src/services/doubus/route-strategies/` ← Hala kullanılıyor!

**Etki:** Kod karmaşası, iki farklı algoritma implementasyonu, bakım zorluğu.

---

## 4. İşlevsellik Analizi

### 4.1 Hedef İşlevler vs Mevcut Durum

| # | Hedef İşlev | Durum | Açıklama |
|---|-------------|-------|----------|
| 1 | Öğrenci kendi kaydolabilir | ✅ ÇALIŞIYOR | `/register` sayfası mevcut |
| 2 | Merkezi öğrenci kaydı | ✅ ÇALIŞIYOR | Admin `/admin/users` |
| 3 | Ders programı girişi (öğrenci) | ✅ ÇALIŞIYOR | `/schedule` sayfası |
| 4 | Ders programı girişi (merkezi) | ✅ ÇALIŞIYOR | Admin `/admin/schedules` |
| 5 | Öğrenci onay/iptal mekanizması | ⚠️ KISMİ | UI var, deadline mantığı yok |
| 6 | Ders dışı talep girişi | ✅ ÇALIŞIYOR | `/request-ride` sayfası |
| 7 | Koordinat seçimi (manuel) | ✅ ÇALIŞIYOR | Sabit location_code |
| 8 | Koordinat seçimi (konum servis) | ❌ YOK | Planlanan faz |
| 9 | Admin rota oluşturma | ❌ ÇALIŞMIYOR | Python'a bağlı değil |
| 10 | 5 algoritma seçimi | ⚠ı KISMİ | UI'da var, Python'da eksik |
| 11 | Algoritma karşılaştırma | ✅ ÇALIŞIYOR | `/admin/compare` sayfası |
| 12 | Sw/So kapasite kısıtları | ✅ ÇALIŞIYOR | Python'da implemente |
| 13 | Max tur süresi kısıtı | ✅ ÇALIŞIYOR | Python'da implemente |
| 14 | Time matrix kullanımı | ⚠ı RİSK | Veri tam, encoding riski |
| 15 | Rota sonuçlarını kaydetme | ❌ YOK | DB'ye yazılmıyor |
| 16 | Sürücü atama | ❌ YOK | Planlanan faz |
| 17 | Öğrenci atama görüntüleme | ⚠ı KISMİ | Sonuçlar gösteriliyor, kalıcı değil |
| 18 | Şöför atama görüntüleme | ⚠ı KISMİ | Sayfa var, veri yok |
| 19 | Canlı konum takibi | ❌ YOK | Planlanan faz |
| 20 | Dinamik uzaklık güncelleme | ❌ YOK | Planlanan faz |

### 4.2 Sayfa Bazlı Çalışma Durumu

| Sayfa | Yol | Backend | Durum |
|-------|-----|---------|-------|
| Dashboard | `/dashboard` | Supabase | ✅ Çalışır |
| Schedule | `/schedule` | Supabase | ✅ Çalışır |
| Request Ride | `/request-ride` | Supabase | ✅ Çalışır |
| Admin Users | `/admin/users` | Supabase | ✅ Çalışır |
| Admin Schedules | `/admin/schedules` | Supabase | ✅ Çalışır |
| Admin Route Test | `/admin/route-test` | Python API | ✅ Çalışır |
| Admin Compare | `/admin/compare` | Python API | ✅ Çalışır |
| **Admin Vehicle Planning** | `/admin/vehicle-planning` | **TypeScript (eski)** | ❌ **ÇALIŞMIYOR** |
| Driver Assignments | `/driver/assignments` | Supabase | ⚠ı Veri yok |
| Track Ride | `/track-ride` | - | ⚠ı İşlevsiz |

---

## 5. Veritabanı Analizi

### 5.1 Mevcut Tablolar (Tahmini)

| Tablo | Durum | Açıklama |
|-------|-------|----------|
| `users` | ✅ | Kullanıcı bilgileri |
| `weekly_schedules` | ✅ | Ders programları |
| `ride_requests` | ✅ | Taşıma talepleri |
| `vehicles` | ✅ | Araç bilgileri |
| `time_matrix` | ✅ | 812 satır, 29 nokta |
| `route_plans` | ❌ YOK | Rota planları kaydedilmiyor |
| `driver_locations` | ❌ YOK | Canlı takip için gerekli |
| `driver_assignments` | ❌ YOK | Sürücü ataması için gerekli |

### 5.2 Time Matrix Doğrulama

| Kontrol | Beklenen | Gerçek | Durum |
|---------|----------|--------|-------|
| Toplam satır | 812 | 812 | ✅ |
| Origin sayısı | 29 | 29 | ✅ |
| Format | origin, dest, duration | Uyumlu | ✅ |
| Encoding | UTF-8 | Risk var | ⚠ı |

---

## 6. Önerilen Düzeltmeler

### 6.1 Öncelik 1 - Kritik (Hemen)

1. **Python STRATEGY_REGISTRY güncelle**
   ```python
   # optimizer_api/strategies/__init__.py'e ekle:
   from strategies.gwo_strategy import GWOSTrategy
   from strategies.hho_strategy import HHOStrategy
   from strategies.two_opt_strategy import TwoOptStrategy
   
   _gwo_strategy = GWOSTrategy()
   _hho_strategy = HHOStrategy()
   _two_opt_strategy = TwoOptStrategy()
   
   STRATEGY_REGISTRY.update({
       "gwo": _gwo_strategy,
       "grey_wolf": _gwo_strategy,
       "hho": _hho_strategy,
       "harris_hawks": _hho_strategy,
       "two_opt": _two_opt_strategy,
   })
   ```

2. **calculate-vehicles API route'unu Python'a bağla**
   ```typescript
   // src/app/api/calculate-vehicles/route.ts
   // ESKİ: import { calculateRequiredVehicles } from "@/services/vehicle-calculator"
   // YENİ: import { optimizeRoutes } from "@/services/optimizer-service"
   ```

3. **algorithm-constants.ts'e two_opt ekle**
   ```typescript
   TWO_OPT: "two_opt",
   ```

### 6.2 Öncelik 2 - Ölü Kod Temizliği

1. `src/services/vehicle-calculator.ts` sil
2. `src/services/doubus/route-strategies/` klasörünü sil
3. İlgili import'ları kaldır

### 6.3 Öncelik 3 - Veri Kalıcılığı

1. `route_plans` tablosu oluştur
2. Optimizasyon sonuçlarını kaydet
3. Öğrenci/şöför görüntüleme için kullan

---

## 7. Özet

### 7.1 Çalışan Özellikler ✅
- Kullanıcı kimlik doğrulama (Supabase Auth)
- Öğrenci kayıt ve profil yönetimi
- Ders programı yönetimi
- Ders dışı talep oluşturma
- Route Test sayfası (Python API)
- Algoritma karşılaştırma sayfası
- Time matrix verisi

### 7.2 Çalışmayan Özellikler ❌
- **Araç Planlama sayfası** (kritik kopukluk)
- **GWO, HHO, Two-Opt algoritmaları** (registry'de yok)
- Rota sonuçlarının kalıcı kaydı
- Sürücü ataması
- Canlı konum takibi

### 7.3 Kısmen Çalışan ⚠ı
- Onay/iptal mekanizması (UI var, mantık yok)
- Şöför sayfaları (boş)
- Dinamik koordinat seçimi

---

## 8. Sonuç

Sistem **%60 çalışır durumda**. Kritik sorun `vehicle-planning` sayfasının Python API'ye bağlı olmaması ve Python'da GWO/HHO/Two-Opt algoritmalarının registry'ye eklenmemiş olması.

**En kritik 3 düzeltme:**
1. Python STRATEGY_REGISTRY'ye GWO, HHO, Two-Opt ekle
2. `calculate-vehicles` route'unu Python'a bağla
3. Ölü TypeScript kodunu temizle

Bu düzeltmeler yapıldıktan sonra sistem operasyonel hale gelecektir.
