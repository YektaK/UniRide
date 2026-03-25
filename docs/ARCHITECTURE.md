# 🏗️ UniRide Mimari Dokümanı

> **Bu dosya projenin mimari kurallarını tanımlar. Tüm geliştiriciler ve AI agent'lar bu kurallara UYMAK ZORUNDADIR.**  
> Son güncelleme: 25 Mart 2026

---

## 1. Sistem Mimarisi

```
┌──────────────────────────────────────────────────────────────┐
│                     KULLANICI KATMANI                        │
│  Next.js Pages: dashboard, schedule, request-ride, profile   │
│  Admin Pages: vehicle-planning, route-test, compare, users   │
│  Driver Pages: assignments, navigation, history              │
└──────────────┬───────────────────────────────────────────────┘
               │ HTTP (fetch)
┌──────────────▼───────────────────────────────────────────────┐
│                    NEXT.JS API ROUTES                         │
│  /api/optimize-route     → optimizer-service.ts → Python API │
│  /api/compare-algorithms → optimizer-service.ts → Python API │
│  /api/calculate-vehicles → ⚠️ DÜZELTME GEREKLİ (Faz 1.1)   │
│  /api/ride-confirmation  → Supabase                          │
│  /api/admin/*            → Supabase                          │
└──────────────┬───────────────────────────────────────────────┘
               │ HTTP (localhost:8000)
┌──────────────▼───────────────────────────────────────────────┐
│              PYTHON FASTAPİ (optimizer_api)                   │
│  POST /api/v1/optimize   → Strategy Registry → Algoritma     │
│  POST /api/v1/compare    → Tüm algoritmalar paralel          │
│  GET  /api/v1/strategies → Kullanılabilir algoritma listesi  │
│                                                              │
│  Strategies: GA, PSO, GWO, HHO, Two-Opt, Greedy,           │
│              Permutation TSP, OR-Tools CVRP                  │
└──────────────┬───────────────────────────────────────────────┘
               │ SQL (supabase-py)
┌──────────────▼───────────────────────────────────────────────┐
│                      SUPABASE                                │
│  time_matrix: 812 satır, 29 nokta (D.Kampus + 9Sw + 19So)  │
│  users, weekly_schedules, ride_requests, vehicles            │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Temel Kural: Rota Optimizasyonu = Python API

```
✅ DOĞRU:  UI → Next.js API Route → optimizer-service.ts → Python /api/v1/optimize
❌ YANLIŞ: UI → Next.js API Route → vehicle-calculator.ts → doubus/route-strategies (TS)
```

**TypeScript tarafında rota hesaplama kodu YAZILMAZ.**  
Tüm rota optimizasyonu Python FastAPI microservice üzerinden yapılır.

---

## 3. Algoritma Key Kuralı

Her yerde **Python registry key'lerini** kullan. Eski key'ler kullanma.

| Canonical Key (KULLAN) | Eski Key (KULLANMA) | Açıklama |
|---|---|---|
| `genetic_algorithm` | — | Genetik Algoritma |
| `pso` | — | Parçacık Sürü Optimizasyonu |
| `gwo` | — | Gri Kurt Optimizasyonu |
| `hho` | — | Harris Hawks Optimizasyonu |
| `two_opt` | `two-opt` | Two-Opt Local Search |
| `greedy` veya `nearest_neighbor` | `nearest-neighbor` | Greedy / En Yakın Komşu |
| `permutation_tsp` | `permutation` | Permütasyon (Optimal) |
| `ortools_cvrp` | — | Google OR-Tools |

Eski key dönüşümü gerekiyorsa `src/lib/algorithm-constants.ts` → `normalizeAlgorithmName()` kullan.

---

## 4. Dosya Sorumluluk Haritası

### Python Backend (`optimizer_api/`)

| Dosya | Sorumluluk | Ne zaman değiştir? |
|---|---|---|
| `strategies/__init__.py` | Algoritma registry (STRATEGY_REGISTRY) | Yeni algoritma eklerken |
| `strategies/base_strategy.py` | Tüm stratejilerin base class'ı | Interface değişikliğinde |
| `strategies/*_strategy.py` | Bireysel algoritma implementasyonları | Algoritma düzeltme/ekleme |
| `main.py` | FastAPI endpoint tanımları | Yeni endpoint eklerken |
| `models/schemas.py` | Pydantic request/response modelleri | API kontratı değiştiğinde |
| `utils/data_loader.py` | Supabase time_matrix yükleme | DB yapısı değiştiğinde |
| `utils/clustering.py` | K-Means clustering + VehicleCalculator | Kümeleme algoritması eklerken |
| `utils/clustering_strategies/` | İleri kümeleme algoritmaları | Kümeleme eklerken |
| `utils/local_search.py` | 2-opt, 3-opt, Or-opt, Hybrid | Local search ekleme/iyileştirme |

### Frontend Services (`src/services/`)

| Dosya | Sorumluluk | Ne zaman değiştir? |
|---|---|---|
| `optimizer-service.ts` | Python API client (optimize, compare) | Python API değiştiğinde |
| `vehicle-calculator.ts` | ⛔ **ÖLÜ KOD** — Kullanma, Faz 1 sonrası silinecek | DOKUNMA |
| `doubus/route-strategies/` | ⛔ **ÖLÜ KOD** — Faz 1 sonrası silinecek | DOKUNMA |
| `doubus/multi-vehicle-routing.ts` | Zaman slotu bazlı rotalama | Faz 2.1'de düzeltilecek |
| `schedule-to-requests.ts` | Ders programı → ride request dönüşümü | İş akışı değiştiğinde |

### Frontend Constants (`src/lib/`)

| Dosya | Sorumluluk | Ne zaman değiştir? |
|---|---|---|
| `algorithm-constants.ts` | Algoritma sabitleri, normalizasyon | Yeni algoritma eklerken |
| `config.ts` | Ortam değişkenleri, sabit değerler | Konfigürasyon değiştiğinde |
| `admin-api.ts` | Admin API çağrıları | Admin endpoint eklerken |
| `supabase-db.ts` | Supabase veritabanı sorguları | Tablo yapısı değiştiğinde |

### API Routes (`src/app/api/`)

| Dosya | Hedef Backend | Ne zaman değiştir? |
|---|---|---|
| `optimize-route/route.ts` | Python API ✅ | API kontratı değiştiğinde |
| `compare-algorithms/route.ts` | Python API ✅ | API kontratı değiştiğinde |
| `calculate-vehicles/route.ts` | ⚠️ TypeScript (→ Faz 1.1'de Python'a çevrilecek) | Faz 1.1 |
| `ride-confirmation/route.ts` | Supabase | İş akışı değiştiğinde |

---

## 5. Yeni Algoritma Ekleme Prosedürü

Yeni bir optimizasyon algoritması eklemek için **tam olarak** şu adımları izle:

```
1. optimizer_api/strategies/ altına yeni_strategy.py oluştur
   → BaseRoutingStrategy'den türet
   → optimize(request) metodunu implement et

2. optimizer_api/strategies/__init__.py içine ekle:
   → Import satırı
   → Instance oluştur
   → STRATEGY_REGISTRY'ye kaydet (ana key + alias varsa)

3. src/lib/algorithm-constants.ts içine ekle:
   → ALGORITHM_KEYS'e yeni key
   → ALGORITHM_DISPLAY_NAMES'e Türkçe ad
   → ALGORITHM_DESCRIPTIONS'a açıklama
   → ALGORITHM_COMPLEXITY'ye karmaşıklık
   → ALGORITHM_OPTIONS dizisine yeni entry

4. BAŞKA HİÇBİR DOSYAYA DOKUNMA
   → UI dropdown'ları ALGORITHM_OPTIONS'dan otomatik beslenir
   → optimizer-service.ts generic çalışır, değişiklik gerekmez
   → Python main.py generic çalışır, değişiklik gerekmez
```

---

## 6. API Kontratları

### POST /api/v1/optimize (Python)

```json
// Request
{
  "algorithm": "genetic_algorithm",
  "students": [
    { "id": "s1", "name": "Ali", "location_code": "Sw1", "disability_type": "Sw" }
  ],
  "depot": { "id": "D.Kampus", "lat": 40.841, "lng": 31.148 },
  "max_travel_time": 120,
  "sw_capacity": 4,
  "so_capacity": 5,
  "local_search_type": "two_opt"
}

// Response
{
  "algorithm_used": "genetic_algorithm",
  "success": true,
  "routes": [
    {
      "vehicle_id": "vehicle_1",
      "route_details": [
        { "location1": "D.Kampus", "location2": "Sw1", "duration": 40.0 }
      ],
      "total_duration_minutes": 85.3,
      "sw_count": 2, "so_count": 3,
      "student_ids": ["s1", "s2"]
    }
  ],
  "total_vehicles": 3,
  "total_duration_minutes": 245.7,
  "execution_time_seconds": 1.234
}
```

### POST /api/v1/compare (Python)

```json
// Request
{
  "students": [...],
  "depot": {...},
  "algorithms": ["genetic_algorithm", "pso", "greedy"]
}

// Response
{
  "success": true,
  "results": [/* AlgorithmResult[] */],
  "best_algorithm": "genetic_algorithm",
  "fastest_algorithm": "greedy",
  "summary": { "genetic_algorithm": { "total_vehicles": 3, "total_duration_minutes": 245.7, ... } }
}
```

---

## 7. Engel Tipi Kodlaması

| Kod | Anlamı | Araç Kapasitesi Alanı |
|---|---|---|
| `Sw` | Tekerlekli sandalye (Wheelchair) | `sw_capacity` |
| `So` | Diğer engel tipleri (Other) | `so_capacity` |

Öğrenci location_code formatı: `Sw1`-`Sw9`, `So1`-`So19`, `D.Kampus` (depot)

---

## 8. Supabase Tablo Yapısı (Rota İlgili)

### time_matrix ✅ (Doğrulanmış)
```
origin_code (text) | destination_code (text) | duration_minutes (float)
D.Kampus           | Sw1                     | 40
...                | ...                     | ...
```
- 812 satır, 29 node, tam bağlantılı matris
- `distance_meters` mevcut ama çoğu `null`
