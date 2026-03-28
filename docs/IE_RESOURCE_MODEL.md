# IE Resource Model - Heterojen Filo Kaynak Yönetimi

> **Tarih:** 28 Mart 2026  
> **Versiyon:** 1.0  
> **Referans:** [Heterojen Filo Tasarımı](./superpowers/specs/2026-03-27-heterogeneous-fleet-design.md) | [IE Plan](./superpowers/plans/2026-03-27-heterogeneous-fleet-ie.md) | [Konuşma Geçmişi](../konusma_gecmisi.txt)

---

## 1. Genel Bakış

Bu doküman, UniRide sisteminin **Endüstri Mühendisliği (IE) Kaynak Yönetimi** yaklaşımını tanımlar. Heterojen araç filoları, günlük planlama ve admin fine-tune özelliklerini kapsar.

### 1.1 Temel Kavramlar

| Kavram | Açıklama |
|--------|----------|
| **Standart Araç** | 4 Sw + 5 So = 9 kapasiteli minibüs |
| **Heterojen Filo** | Farklı Sw/So kapasitelerine sahip araçlar |
| **Resource Leveling** | Kaynak ihtiyacını zaman içinde dengeleme |
| **Directional Blocking** | Pickup/Dropoff için ayrı zaman blokları |
| **Slack Time** | Öğrenci hareket zamanını esnetme (±60 dk) |

---

## 2. Sistem Modları

### 2.1 Ideal (Benchmark) Mode

**Amaç:** Mevcut araçlara bakmadan teorik minimum araç sayısını hesapla

```
Input: Öğrenci listesi, time matrix, kapasite kısıtları
Output: Standart minibüs cinsinden araç ihtiyacı, saatlik histogram
```

**Kullanım:**
- Admin "kaç araca ihtiyacım var?" sorusunun cevabını alır
- Operasyonel verimliliğin "ideal"e ne kadar uzak olduğunu görür
- Kaynak planlaması için baseline oluşturur

### 2.2 Fine-tune (Sandbox) Mode

**Amaç:** Adminin mevcut araçlarla planlama yapması

```
Input: Mevcut araç listesi, öğrenci listesi, manual adjustments
Output: Optimized routes with admin interventions
```

**Admin Eylemleri:**
- Araç ekleme/çıkarma
- Öğrenci zaman kaydırma
- Manuel route block ekleme
- Before/After karşılaştırma

---

## 3. Kaynak Profil Hesaplama

### 3.1 Standart Araç İhtiyacı

```python
def calculate_standard_vehicle_needs(students: List[Student], 
                                       time_matrix: dict,
                                       max_tour_time: int = 120) -> int:
    """
    Her öğrenci için en yakın standart minibüs eşdeğeri hesapla.
    Dönüş: Kaç adet 4 Sw + 5 So minibüs gerekir
    """
```

**Örnek:**
- 30 öğrenci → 4 minibüs (16 Sw + 14 So)
- 45 öğrenci → 5 minibüs (20 Sw + 25 So)

### 3.2 Saatlik Talep Histogramı

```python
def generate_hourly_demand(students: List[Student], 
                           pickup_times: dict,
                           dropoff_times: dict) -> dict:
    """
    Her saat için Sw/So kırılımı
    
    Output:
    {
        "08:00": {
            "pickup": {"sw": 2, "so": 3},
            "dropoff": {"sw": 0, "so": 0}
        },
        "09:00": {
            "pickup": {"sw": 4, "so": 5},
            "dropoff": {"sw": 1, "so": 2}
        },
        ...
    }
    """
```

### 3.3 Darboğaz Tespiti

```python
def identify_bottlenecks(hourly_demand: dict, 
                        available_vehicles: List[VehicleConfig]) -> List[dict]:
    """
    Infeasible veya verimsiz zaman dilimlerini tespit et
    
    Bottleneck Türleri:
    - "infeasible": Kapasite yetersiz
    - "low_efficiency": <50% doluluk
    - "resource_conflict": Directional blocking ihlali
    """
```

---

## 4. Directional Blocking (Yönsel Bloklama)

### 4.1 Zaman Bloğu Hesaplama

```
Pickup Rotası (Okula Geliş):
├── Araç kampüsten çıkış: T - max_tour_duration
├── Tur süresi: max_tour_time (120 dk)
└── Okula varış: T

Dropoff Rotası (Okuldan Dönüş):
├── Okuldan ayrılış: T
├── Tur süresi: max_tour_time (120 dk)
└── Eve varış: T + max_tour_duration
```

### 4.2 Çakışma Kontrolü

```python
def check_directional_conflict(vehicle: VehicleConfig, 
                               pickup_block: tuple, 
                               dropoff_block: tuple) -> bool:
    """
    Aynı araç için pickup ve dropoff zaman blokları çakışıyor mu?
    
    Örnek:
    - Pickup: 10:00-12:00 (okula 12:00'de varır)
    - Dropoff: 11:00-13:00 (okuldan 11:00'de ayrılır)
    - ÇAKIŞMA: Araç aynı anda iki yerde olamaz
    """
    return not (pickup_block[1] <= dropoff_block[0] or 
                dropoff_block[1] <= pickup_block[0])
```

### 4.3 Cooldown Süresi

Rotalar arası 15 dakika geçiş süresi:

```
Araç 1: 10:00-12:00 (pickup)
Araç 1: 12:15+ (bir sonraki rota başlayabilir)
```

---

## 5. Slack Time (Esneklik Payı)

### 5.1 Zaman Kaydırma Önerileri

```python
def suggest_time_shifts(hourly_demand: dict, 
                       slack_window: int = 60) -> List[dict]:
    """
    Pik saat yığılmasını azaltmak için öğrenci zaman kaydırma önerileri
    
    Örnek:
    - Saat 12:00: 10 öğrenci (infeasible - kapasite 9)
    - Öneri: 2 öğrenciyi 11:00'e kaydır → 8 öğrenci (feasible)
    - Tasarruf: 1 araç
    """
```

### 5.2 Optimizasyon Dahil Edilmiş Hesaplama

```python
def optimize_with_slack(students: List[Student],
                        allow_time_shift: bool = True,
                        slack_window_minutes: int = 60) -> OptimizationResult:
    """
    Slack time dahil edilerek optimizasyon
    -allow_time_shift=True ise öğrenci zamanları esnetilebilir
    """
```

---

## 6. UI Bileşenleri

### 6.1 Resource Histogram

```
┌─────────────────────────────────────────────────────────────────┐
│                    SAATLİK ARAÇ İHTİYACI                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 08:00  ██░░░░░░░░  2 araç  [Pickup: 2 Sw, 3 So]                │
│        ░░░░░░░░░░░  [Dropoff: -]                               │
│                                                                  │
│ 09:00  ████░░░░░░░  4 araç  [Pickup: 4 Sw, 5 So]               │
│        ░░░░░░░░░░░  [Dropoff: 1 Sw, 2 So]                      │
│                                                                  │
│ 12:00  ██████░░░░░  ⚠️ 6 araç gerekli ama 5 var (INFEASIBLE)   │
│                                                                  │
│ 14:00  ███░░░░░░░░  3 araç  [Dropoff: 3 Sw, 4 So]               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Renk Kodu:
█ = Pickup (Mavi)   ▒ = Dropoff (Turuncu)   ░ = Boş
```

### 6.2 Resource Tracks (Gantt)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARAÇ KULLANIM ZAMAN ÇİZELGESİ               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Araç 1  [08:00-10:00] ████████ Pickup                          │
│          [12:00-14:00] ████████ Dropoff                        │
│                                                                  │
│ Araç 2  [09:00-11:00] ████████ Pickup                          │
│          [14:00-16:00] ████████ Dropoff                        │
│                                                                  │
│ Araç 3  [10:00-12:00] ████████ Pickup                          │
│          [░░░░░░░░░░░░░] Boş (cooldown)                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Sandbox Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                        SANDBOX MODE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Mevcut Araçlar:                                                 │
│ ├── [Araç 1] 4 Sw + 5 So  (Standart Minibüs)                   │
│ ├── [Araç 2] 2 Sw + 3 So  (Küçük Van)                          │
│ └── [+ Araç Ekle]                                              │
│                                                                  │
│ Optimizasyon Sonucu:                                            │
│ ├── Toplam Araç: 4                                             │
│ ├── Infeasible: Saat 12:00 (6 araç gerekli, 5 var)             │
│ └── Öneri: "2 öğrenciyi ±60 dk esnet"                          │
│                                                                  │
│ Manual Müdahaleler:                                            │
│ ├── [X] Öğrenci #15 → 12:00 → 11:00 (Shift)                    │
│ ├── [+] Araç 3 ekle (3 Sw + 4 So)                              │
│ └── [⟳] Yeniden Hesapla                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. API Entegrasyonu

### 7.1 Request Schema

```python
class OptimizationRequest(BaseModel):
    # Mevcut alanlar
    algorithm: str
    students: List[StudentNode]
    depot: Location
    sw_capacity: int = 4
    so_capacity: int = 5
    max_travel_time: int = 120
    
    # 🆕 YENİ: IE Engine alanları
    vehicles: Optional[List[VehicleConfig]] = None
    allow_time_shift: bool = False
    slack_window_minutes: int = 60
    mode: str = "benchmark"  # "benchmark" veya "sandbox"

class VehicleConfig(BaseModel):
    vehicle_id: str
    sw_capacity: int = 4
    so_capacity: int = 5
    cooldown_minutes: int = 15
```

### 7.2 Response Schema

```python
class OptimizationResponse(BaseModel):
    routes: List[Route]
    total_vehicles: int
    total_duration_minutes: float
    
    # 🆕 YENİ: IE Engine çıktıları
    standard_vehicles_needed: int  # Kaç standart minibüs gerekli
    hourly_demand: dict            # Saatlik Sw/So kırılımı
    bottlenecks: List[dict]         # Darboğaz analizi
    time_shift_suggestions: List[dict]  # Slack time önerileri
```

---

## 8. Konuşma Geçmişi Talepleri ile Eşleşme

| Konuşma Geçmişi Madde | Talep | IE Model Karşılığı |
|-----------------------|-------|-------------------|
| 3 | Araç tipleri farklı olabilir | `VehicleConfig` - farklı Sw/So |
| 5 | Bütünsel yaklaşım | `standard_vehicles_needed` - teorik minimum |
| 7 | Gün içi yeniden planlama | `POST /api/v1/reoptimize` |
| 14 | Verimsiz noktaları görüp planlama | `Sandbox Mode` - manual interventions |
| 19 | Toplayıcı/Dağıtıcı araç ayrımı | `Directional Blocking` |
| 21 | Standart araç ihtiyacı tablosu | `Resource Histogram` |
| 23 | So/Sw kırılımı görme | `hourly_demand` - Sw/So breakdown |

---

## 9. Bağımlılıklar

```
┌─────────────────────────────────────────────────────────────────┐
│                     BAĞIMLILIK HARİTASI                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  optimizer_api/models/schemas.py                                │
│       │                                                         │
│       ├──→ VehicleConfig (sw_capacity, so_capacity)            │
│       └──→ allow_time_shift, slack_window_minutes               │
│                                                                  │
│  optimizer_api/utils/resource_profiler.py                       │
│       │                                                         │
│       ├──→ calculate_standard_vehicle_needs()                  │
│       ├──→ generate_hourly_demand()                             │
│       ├──→ identify_bottlenecks()                              │
│       ├──→ check_directional_conflict()                        │
│       └──→ suggest_time_shifts()                               │
│                                                                  │
│  optimizer_api/strategies/pyvrp_strategy.py                    │
│       │                                                         │
│       └──→ heterojen araç desteği (mevcut)                     │
│                                                                  │
│  optimizer_api/strategies/vroom_strategy.py                   │
│       │                                                         │
│       └──→ heterojen araç desteği (mevcut)                     │
│                                                                  │
│  src/components/admin/                                          │
│       │                                                         │
│       ├──→ resource-histogram.tsx                               │
│       ├──→ resource-tracks.tsx                                  │
│       └──→ sandbox/page.tsx                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Test Senaryoları

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| T1 | 30 öğrenci, standart araç | 4 minibüs, feasible |
| T2 | 45 öğrenci, heterojen araç (2x 4Sw, 1x 5Sw) | 3 araç, feasible |
| T3 | Pickup + Dropoff çakışması | Conflict tespiti |
| T4 | 12:00'de 10 öğrenci | Bottleneck: infeasible |
| T5 | Slack time ile optimizasyon | 2 öğrenci kaydı, 4 araç |

---

## 10. Implementation Status

> **Son Güncelleme:** 28 Mart 2026

### 10.1 Backend Implementation

| Bileşen | Dosya | Durum | Notlar |
|---------|-------|-------|--------|
| VehicleConfig Schema | `models/schemas.py` | ✅ Tamamlandı | sw_capacity, so_capacity, cooldown_minutes |
| OptimizationRequest | `models/schemas.py` | ✅ Tamamlandı | vehicles, allow_time_shift, mode |
| IEResponseData | `models/schemas.py` | ✅ Tamamlandı | hourly_demand, bottlenecks, suggestions |
| Split Decoder | `utils/split_decoder.py` | ✅ Tamamlandı | Giant Tour → Routes dönüşümü |
| Split Decoder V2 | `utils/split_decoder.py` | ⚠️ Kısmi | Heterojen kapasite desteği eksik |
| Resource Profiler | `utils/resource_profiler.py` | ❌ Yok | **IE Engine ana dosyası - henüz implemente edilmedi** |
| PyVRP Strategy | `strategies/pyvrp_strategy.py` | ✅ Tamamlandı | HGS çözücü entegrasyonu |
| VROOM Strategy | `strategies/vroom_strategy.py` | ✅ Tamamlandı | C++ çözücü entegrasyonu |
| GA-Split | `strategies/ga_split_strategy.py` | ✅ Tamamlandı | GA + Split entegrasyonu |
| PSO-Split | `strategies/pso_split_strategy.py` | ❌ Yok | **Eksik** |
| HHO-Split | `strategies/hho_split_strategy.py` | ❌ Yok | **Eksik** |
| GWO-Split | `strategies/gwo_split_strategy.py` | ❌ Yok | **Eksik** |
| Hybrid Base | `strategies/hybrid_base_strategy.py` | ❌ Yok | **Eksik** |
| Strategy Registry | `strategies/__init__.py` | ⚠️ Kısmi | Yeni stratejiler eklenmemiş |

### 10.2 Frontend Implementation

| Bileşen | Dosya | Durum | Notlar |
|---------|-------|-------|--------|
| Resource Histogram | `components/admin/resource-histogram.tsx` | ❌ Yok | **IE Dashboard - henüz implemente edilmedi** |
| Resource Tracks | `components/admin/resource-tracks.tsx` | ❌ Yok | **Gantt görünüm - henüz implemente edilmedi** |
| Sandbox Mode | `app/(app)/admin/sandbox/page.tsx` | ❌ Yok | **Fine-tune UI - henüz implemente edilmedi** |
| Bottleneck Indicator | `components/admin/bottleneck-indicator.tsx` | ❌ Yok | **Uyarı bileşeni - henüz implemente edilmedi** |

### 10.3 Implementation Plan

Detaylı uygulama planı için bkz: [IMPLEMENTATION_PLAN_1_5X.md](./IMPLEMENTATION_PLAN_1_5X.md)

---

*Bu doküman ROADMAP.md ve ARCHITECTURE.md'yi tamamlar.*