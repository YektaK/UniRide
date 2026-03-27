# 🏗️ UniRide Mimari Dokümanı

> **Bu dosya projenin mimari kurallarını tanımlar. Tüm geliştiriciler ve AI agent'lar bu kurallara UYMAK ZORUNDADIR.**  
> Son güncelleme: 26 Mart 2026

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
│  /api/calculate-vehicles → optimizer-service.ts → Python API │
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
│  Pipeline A: Sweep/CW → Kümeler → GA/PSO/HHO/GWO (TSP)     │
│  Pipeline B: GA/PSO/HHO/GWO (Giant Tour) → Split Decoder    │
│  Bağımsız:   OR-Tools CVRP, PyVRP (HGS), VROOM (C++)       │
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

---

## 3. Çift Pipeline Mimarisi (Faz 1.5)

> İki farklı VRP paradigması paralel olarak desteklenir.

### 3.1 Pipeline A — Cluster-First, Route-Second

```
Öğrenciler → Sweep / Clarke-Wright → Akıllı Kümeler → GA/PSO/HHO (küme-içi TSP) → Rotalar
```

- **Kümeleme:** Sweep veya Clarke-Wright (K-Means yerine, **time matrix duyarlı**)
- **Rotalama:** Her küme için ayrı meta-sezgisel TSP çözümü
- **Ölçeklenebilirlik:** ✅ N>100'de iyi (küçük alt problemler)
- **Feasibility:** Kümeleme kalitesine bağlı (~%95)
- **Risk:** Küme sınırlarındaki suboptimalite

**Kullanım:** N > 50 veya hız kritik senaryolarda önerilir.

### 3.2 Pipeline B — Route-First, Cluster-Second

```
Öğrenciler → GA/PSO/HHO (Giant Tour) → Split Decoder (DP) → Rotalar
```

- **Optimizasyon:** Tüm öğrenciler tek bir permütasyon olarak optimize edilir
- **Bölme:** Dinamik Programlama ile optimal ve **%100 feasible** bölme
- **Referans:** Prins, C. (2004)
- **Feasibility:** ✅ %100 garanti
- **Risk:** N>100'de Giant Tour arama uzayı büyür

**Kullanım:** N ≤ 50 veya kalite kritik senaryolarda önerilir.

### 3.3 Bağımsız (Holistik) Çözücüler

Aşağıdaki çözücüler her iki pipeline'ın **dışındadır**. Kendi internal kümeleme + rotalama mekanizmalarına sahiptirler.

| Çözücü | Motor | Avantaj | Akademik Referans |
|--------|-------|---------|-------------------|
| **OR-Tools** | C++ (Google) | Endüstri standardı, CP-SAT | — |
| **PyVRP** | C++ + Python (HGS) | DIMACS 2021 birincisi, heterojen fleet, TW, multi-depot | Vidal (2022) |
| **VROOM** | C++ (pyvroom) | Ultra-hızlı, HFVRP, PDPTW, multi-trip | — |

**PyVRP** özellikle güçlü çünkü:
- Hybrid Genetic Search (HGS-CVRP) tabanlı → akademik state-of-the-art
- Heterojen araç tipleri (farklı Sw/So kapasiteleri) native destek
- Time windows native destek
- Multi-depot desteği (ileride potansiyel)
- `pip install pyvrp` ile kurulum

**VROOM** özellikle güçlü çünkü:
- C++ motoru sayesinde 1000+ nokta < 5 saniye
- CVRPTW + HFVRP + PDPTW + Multi-trip
- `pip install pyvroom` ile kurulum
- Hız kritik senaryolarda ideal

### 3.4 Pipeline Seçim Matrisi

| N boyutu | Önerilen Pipeline | Gerekçe |
|----------|------------------|---------|
| N ≤ 30 | B (Split) | Arama uzayı yönetilebilir, %100 feasible |
| 30 < N ≤ 50 | B (Split) | Hâlâ yönetilebilir, kalite avantajı |
| 50 < N ≤ 100 | A veya B | Benchmark ile karar ver |
| N > 100 | A (Sweep/CW) veya PyVRP/VROOM | Giant Tour çok büyük, holistik çözücüler tercih |
| N > 100 (hibrit) | A ön-bölme → B Split | Her bölge kendi Split'ini çalıştırır |
| N > 300 | PyVRP veya VROOM | En iyi ölçeklenebilirlik |

---

## 4. Kısıt Referans Tablosu

> ⚠️ **Tüm dokümanlar ve kodlar bu değerleri referans almalıdır.**

| Kısıt | Değişken | Varsayılan | Açıklama |
|-------|----------|-----------|----------|
| Sw Kapasitesi | `sw_capacity` | **4** | Tekerlekli sandalye koltuğu |
| So Kapasitesi | `so_capacity` | **5** | Diğer engel koltuğu |
| Toplam Kapasite | `sw + so` | **≤ 9** | Aynı araçta max toplam |
| Max Tur Süresi | `max_tour_time` | **120 dk** | Araç kampüsten çıkış → dönüş |
| Max Öğrenci Süresi | `max_student_time` | **90 dk** | Öğrencinin araçta max süresi |

> **DP Formülasyonu Uyarısı:** `if sw_count > SW_CAP or so_count > SO_CAP or (sw_count + so_count) > 9: break`

---

## 5. Split Decoder Detayı (Pipeline B)

```python
class SplitDecoder:
    """
    Giant Tour → Optimal Routes (Dinamik Programlama)
    
    - Heterojen kapasite: Sw ≤ 4 AND So ≤ 5 AND toplam ≤ 9
    - Time: ≤ max_tour_time (time_matrix duyarlı)
    - Karmaşıklık: O(N²)
    """
    
    def decode(self, giant_tour, depot, time_matrix, 
               coordinates, student_data) -> (routes, cost):
        # DP tablosu ile optimal bölme noktalarını bul
        pass
```

```python
class HybridSplitStrategy(BaseRoutingStrategy):
    """Tüm Split tabanlı algoritmalar için temel sınıf"""
    
    def optimize(self, request):
        self.split_decoder = SplitDecoder(sw_cap, so_cap, max_time)
        waypoints = [s.location_code for s in request.students]
        best_tour = self._optimize_giant_tour(waypoints, ...)
        routes, cost = self.split_decoder.decode(best_tour, ...)
        routes = [self._local_search(r) for r in routes]  # 2-opt sonrası
        return self._build_response(routes, cost)
```

---

## 6. Algoritma Key Kuralı

| Canonical Key | Pipeline | Açıklama |
|---|---|---|
| `genetic_algorithm` | A (mevcut) | Genetik Algoritma + K-Means |
| `pso` | A (mevcut) | PSO + K-Means |
| `gwo` | A (mevcut) | GWO + K-Means |
| `hho` | A (mevcut) | HHO + K-Means |
| **`ga_split`** | **B (yeni)** | GA + Split Decoder |
| **`pso_split`** | **B (yeni)** | PSO + Split (Önerilen) |
| **`gwo_split`** | **B (yeni)** | GWO + Split |
| **`hho_split`** | **B (yeni)** | HHO + Split |
| `ortools_cvrp` | Bağımsız | OR-Tools (referans) |
| **`pyvrp`** | **Bağımsız** | **PyVRP HGS (state-of-the-art)** |
| **`vroom`** | **Bağımsız** | **VROOM (ultra-hızlı)** |
| `two_opt` | — | Local Search |
| `greedy` | — | Greedy heuristic |
| `permutation_tsp` | — | Exact TSP |

> **Not:** Pipeline A algoritmalarının kümeleme yöntemi Sweep/CW'ye geçirilecektir (Faz 1.5). Geçiş tamamlanana kadar mevcut K-Means ile çalışmaya devam eder.

---

## 7. Dosya Sorumluluk Haritası

### Python Backend (`optimizer_api/`)

| Dosya | Sorumluluk | Pipeline |
|---|---|---|
| `strategies/__init__.py` | Algoritma registry | Tümü |
| `strategies/base_strategy.py` | Base class | Tümü |
| `strategies/hybrid_base_strategy.py` | 🆕 Split base class | B |
| `strategies/*_split_strategy.py` | 🆕 Split hibrit algoritmalar | B |
| `strategies/*_strategy.py` | Mevcut algoritmalar | A |
| `strategies/pyvrp_strategy.py` | 🆕 PyVRP HGS çözücü | Bağımsız |
| `strategies/vroom_strategy.py` | 🆕 VROOM çözücü | Bağımsız |
| `utils/split_decoder.py` | 🆕 Giant Tour → Routes | B |
| `utils/clustering.py` | Kümeleme (Sweep/CW'ye güncellenecek) | A |
| `utils/local_search.py` | 2-opt, Or-opt | Tümü |
| `utils/data_loader.py` | Time matrix yükleme | Tümü |

### Frontend (`src/`)

| Dosya | Sorumluluk |
|---|---|
| `services/optimizer-service.ts` | Python API client |
| `lib/algorithm-constants.ts` | Algoritma sabitleri |
| `app/api/*/route.ts` | Next.js API proxy'leri |

---

## 8. Yeni Algoritma Ekleme Prosedürü

```
1. optimizer_api/strategies/ altına yeni_strategy.py oluştur
   → Pipeline B: HybridSplitStrategy'den türet
   → Pipeline A: BaseRoutingStrategy'den türet

2. STRATEGY_REGISTRY'ye kaydet (__init__.py)

3. ALGORITHM_OPTIONS'a ekle (algorithm-constants.ts)

4. BAŞKA HİÇBİR DOSYAYA DOKUNMA
```

---

## 9. API Kontratları

### POST /api/v1/optimize

```json
{
  "algorithm": "pso_split",
  "students": [{ "id": "s1", "name": "Ali", "location_code": "Sw1", "disability_type": "Sw" }],
  "depot": { "id": "D.Kampus", "lat": 40.841, "lng": 31.148 },
  "max_travel_time": 120,
  "sw_capacity": 4,
  "so_capacity": 5,
  "local_search_type": "two_opt"
}
```

---

## 10. Engel Tipi ve Supabase

| Kod | Anlamı | Kapasite |
|---|---|---|
| `Sw` | Tekerlekli sandalye | `sw_capacity` (4) |
| `So` | Diğer engel | `so_capacity` (5) |

**time_matrix:** 812 satır, 29 node, tam bağlantılı matris

---

## 11. Hedef Dosya Yapısı (Faz 1.5 Sonrası)

```
optimizer_api/
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── hybrid_base_strategy.py      # 🆕 Pipeline B base
│   ├── ga_strategy.py               # Pipeline A
│   ├── pso_strategy.py              # Pipeline A
│   ├── hho_strategy.py              # Pipeline A
│   ├── gwo_strategy.py              # Pipeline A
│   ├── ga_split_strategy.py         # 🆕 Pipeline B
│   ├── pso_split_strategy.py        # 🆕 Pipeline B
│   ├── hho_split_strategy.py        # 🆕 Pipeline B
│   ├── gwo_split_strategy.py        # 🆕 Pipeline B
│   ├── ortools_cvrp.py              # Bağımsız
│   ├── pyvrp_strategy.py            # 🆕 Bağımsız (HGS)
│   ├── vroom_strategy.py            # 🆕 Bağımsız (C++)
│   └── ...
└── utils/
    ├── data_loader.py
    ├── clustering.py               # Pipeline A (Sweep/CW'ye güncellenecek)
    ├── split_decoder.py            # 🆕 Pipeline B
    └── local_search.py             # Tümü

## 12. İnceleme Bulguları ve Uyarılar

> Bu bölüm 26 Mart 2026 tarihli teknik inceleme sonuçlarını içerir.

| # | Bulgu | Ciddiyet | Çözüm |
|---|-------|----------|-------|
| B1 | N>100'de Giant Tour arama uzayı patlar | ⚠️ Yüksek | Pipeline Seçim Matrisi (§3.4) |
| B2 | DP'de Sw+So AND kısıtı atlanabilir | 🔴 Kritik | §4 Kısıt Referans Tablosu |
| B3 | Performans rakamları tahmini | ⚠️ Orta | `[TAHMİNİ]` etiketi |
| B4 | Eski alg. UI'da karışıklık yaratır | ⚠️ Orta | Pipeline etiketi + sıralama |
| B5 | `max_tour_time` tutarsızlığı | 🔴 Kritik | §4 tek referans noktası |
| B6 | OR-Tools + Split anlamsız | ℹ️ Düşük | §3.3 belgelendi |
```
