# UniRide CVRPTW - Mimari Tasarım

## Sürüm: 3.1.0 | Tarih: 17 Nisan 2026 (17.04.2026 - Ekleyen: Antigravity AI)

> **Son Güncelleme:** FAZ 0-3 SOTA Framework v3.0.0 tamamlandı. E²BSO, R²DMA, P-AOEA algoritmaları üretime hazır. Test coverage %64. DNA Coverage 10/10.

---

## 📐 Sistem Mimarisi Genel Bakış

UniRide, mikroservis tabanlı bir mimari ile tasarlanmış olup, frontend ve backend servisleri birbirinden bağımsız olarak çalışabilmektedir. Sistem, üç ana katmandan oluşmaktadır: Presentation Layer (Frontend), Business Logic Layer (Backend API), ve Data Layer (Database).

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Next.js Frontend (Port 3000)                │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │   Admin     │ │   Driver    │ │   Student   │       │   │
│  │  │   Panel     │ │   Interface │ │   Interface │       │   │
│  │  │ + SOTA UI   │ │             │ │             │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER (BFF)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Next.js API Routes                       │   │
│  │  /api/optimize-route  /api/admin/*  /api/benchmark/*    │   │
│  │  /api/faz0/status     /api/faz3/status                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              │ HTTP/REST                        │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Python Optimization Engine (Port 8099)           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │   │
│  │  │ Pipeline │ │ Pipeline │ │ Holistic │ │ SOTA v3.0  │ │   │
│  │  │    A     │ │    B     │ │ Solvers  │ │ E²BSO/R²DMA│ │   │
│  │  │(GA,PSO..)│ │(GA-Split)│ │ OR-Tools │ │ P-AOEA     │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SQL/ORM
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Supabase (PostgreSQL)                 │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │  users   │ │ vehicles │ │  routes  │ │requests  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Bileşen Detayları

### 1. Frontend (Next.js 16)

#### Teknoloji Stack
| Teknoloji | Sürüm | Amaç |
|-----------|-------|------|
| Next.js | 16.1.6 | App Router, SSR |
| TypeScript | 5.x | Type safety |
| React | 18.3.1 | UI components |
| react-dom | 18.3.1 | Virtual DOM rendering |
| Tailwind CSS | **4.x** | Utility-first styling (v4 — `@import "tailwindcss"`) |
| shadcn/ui | New York | UI component library (~38 bileşen) |
| Supabase JS | 2.98.0 | Database client |
| tw-animate-css | latest | Animasyon utiliteleri (Tailwind v4 ile) |

#### Dizin Yapısı
```
src/
├── app/                    # Next.js App Router
│   ├── (app)/             # Authenticated routes
│   │   ├── admin/         # Admin panel pages
│   │   │   ├── benchmark/ # Benchmark Suite (TSPLIB)
│   │   │   ├── sandbox/   # IE Sandbox
│   │   │   ├── compare/   # Algoritma karşılaştırma
│   │   │   └── ...
│   │   ├── driver/        # Driver interface
│   │   └── dashboard/     # Student dashboard
│   ├── (auth)/            # Authentication pages
│   ├── api/               # API route handlers (19+ dosya)
│   │   ├── benchmark/     # Benchmark proxy routes
│   │   ├── admin/         # Admin CRUD endpoints
│   │   ├── faz0/          # SOTA FAZ 0 status
│   │   ├── faz3/          # SOTA FAZ 3 status
│   │   └── ...
│   ├── globals.css        # Tailwind v4 + oklch color system
│   └── page.tsx           # SOTA Dashboard (FAZ 0-3)
├── components/            # React components
│   ├── ui/               # shadcn/ui components (~38)
│   ├── admin/            # Admin-specific (IE Dashboard, Bottleneck)
│   ├── auth/             # Auth components
│   └── student/          # Student components
├── services/             # Business logic services
│   ├── doubus/           # Multi-vehicle routing
│   │   └── multi-vehicle-routing.ts  # fetchWithRetry, RoutingError
│   ├── excel/            # Import/Export
│   ├── optimizer-service.ts  # Python API (CVRPTW support)
│   └── benchmark-service.ts  # Benchmark polling
├── lib/                  # Utilities and config
│   ├── config.ts         # OPTIMIZER_API_URL, centralized config
│   ├── supabase.ts       # Database client
│   ├── supabase-admin.ts # Server-side admin client (service_role)
│   ├── supabase-db.ts    # DB helpers (toCamelCase/toSnakeCase)
│   ├── algorithm-constants.ts  # ALGORITHM_KEYS, SSOT
│   └── utils.ts          # cn() ve genel utils
├── types/                # TypeScript types
│   ├── index.ts          # Genel tipler
│   ├── db.ts             # Veritabanı tipleri
│   └── ie-resource.ts    # IE kaynak analizi tipleri (IERawData vb.)
└── hooks/                # Custom React hooks
```

### 2. Backend (Python FastAPI)

#### Teknoloji Stack
| Teknoloji | Sürüm | Amaç |
|-----------|-------|------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.100+ | REST API framework |
| NumPy | 1.24+ | Numerical operations |
| OR-Tools | 9.6+ | Optimization solver |
| Pydantic | 2.x | Data validation |

#### Dizin Yapısı
```
optimizer_api/
├── main.py               # FastAPI v3.1.0 (16+ endpoints)
├── benchmark_runner.py   # Benchmark çalıştırıcı (daemon thread)
├── benchmark_state.py    # Thread-safe state (Lock + SingletonMeta)
├── faz0_interactive.py   # ★ Standalone CLI (2,251 satır, multiprocessing)
├── faz0_standalone_demo.py  # ★ Demo (web gerekmez)
├── models/
│   └── schemas.py        # Pydantic models
├── strategies/           # 20+ strateji dosyası
│   ├── __init__.py       # Strategy Registry (SSOT)
│   ├── base_strategy.py  # Abstract base class
│   ├── hybrid_base_strategy.py  # Shared base for split
│   ├── [Pipeline A: ga, pso, gwo, hho]
│   ├── [Pipeline B: ga_split, pso_split, gwo_split, hho_split]
│   ├── [Holistic: ortools_cvrp, pyvrp_strategy, vroom_strategy]
│   ├── [Heuristics: greedy_heuristic, two_opt_strategy, permutation_tsp]
│   ├── cvrptw_wrapper.py # CVRPTW time-window wrapper
│   └── sota_common/      # ★ FAZ 0-3 SOTA Framework
│       ├── __init__.py
│       ├── e2bso.py      # FAZ 1: E²BSO (978 satır)
│       ├── r2dma.py      # FAZ 2: R²DMA (~680 satır)
│       ├── paoea.py      # FAZ 3: P-AOEA (~1423 satır)
│       ├── multi_start_initializer.py  # DNA-6
│       ├── multi_layer_ls.py           # DNA-3
│       ├── penalty_manager.py          # DNA-4, DNA-9
│       ├── acceptance_criteria.py      # DNA-7
│       ├── destroy_operators.py        # DNA-1, DNA-2
│       ├── repair_operators.py         # DNA-1, DNA-2
│       └── diversity_controller.py     # DNA-4, DNA-8
└── utils/
    ├── constants.py             # Shared constants
    ├── patterns.py              # ★ SingletonMeta (thread-safe, double-checked locking)
    ├── haversine.py             # ★ Haversine distance (tek kaynak)
    ├── tsplib_parser.py         # TSPLIB EUC_2D + NINT rounding
    ├── data_loader.py           # Supabase data loader
    ├── split_decoder.py         # Prins (2004) split decoder
    ├── linear_split_decoder.py  # O(n) linear split
    ├── clustering.py            # K-Means (haversine_distance → data_loader)
    ├── clustering_strategies/   # 7 clustering stratejisi
    ├── local_search.py          # 8 local search tipi
    ├── local_search_numba.py    # Numba JIT hızlandırmalı
    ├── resource_profiler.py     # IE Resource Engine
    ├── time_window_extractor.py # TW extraction
    └── time_window_violation_tracker.py
```

### 3. Database (Supabase/PostgreSQL)

#### Tablo Şeması
```sql
-- Kullanıcılar
users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE,
  name TEXT,
  role TEXT CHECK (role IN ('student', 'admin', 'driver')),
  disability_type TEXT CHECK (disability_type IN ('Sw', 'So')),
  location_code TEXT,
  ...
)

-- Araçlar
vehicles (
  id UUID PRIMARY KEY,
  name TEXT,
  type TEXT CHECK (type IN ('minibus', 'bus', 'van')),
  wheelchair_capacity INTEGER,
  seating_capacity INTEGER,
  status TEXT CHECK (status IN ('active', 'inactive', 'maintenance'))
)

-- Rotalar
routes (
  id UUID PRIMARY KEY,
  date DATE,
  timeslot TEXT,
  type TEXT CHECK (type IN ('pickup', 'dropoff')),
  waypoints TEXT[],
  optimized_path JSONB,
  total_duration INTEGER,
  vehicle_count INTEGER
)

-- Ride Requests
ride_requests (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  type TEXT CHECK (type IN ('scheduled', 'adhoc')),
  requested_pickup_time TIMESTAMPTZ,
  requested_dropoff_time TIMESTAMPTZ,
  status TEXT,
  vehicle_id UUID,
  ...
)
```

---

## 🔄 Veri Akışı

### Rota Optimizasyonu Akışı
```
1. Kullanıcı seçimi (Frontend)
   └─> Student selection via checkboxes
   └─> Algorithm selection from dropdown

2. API Request (Frontend → Backend)
   └─> POST /api/calculate-vehicles
   └─> Body: { students, maxTourTime, swCapacity, soCapacity, strategy }

3. Python API Call (Next.js API → Python)
   └─> POST http://localhost:8000/api/v1/optimize
   └─> Body: { algorithm, students, depot, max_travel_time, capacities }

4. Optimization Process (Python)
   └─> Strategy selection from registry
   └─> K-Means clustering (multi-vehicle)
   └─> TSP solving per cluster
   └─> Route construction

5. Response Processing
   └─> OptimizationResponse with routes
   └─> Vehicle assignments
   └─> Duration calculations

6. UI Rendering (Frontend)
   └─> Display vehicle cards
   └─> Show route details
   └─> Export options
```

---

## 🚀 SOTA Framework Mimarisi (FAZ 0-3) — v3.0.0

> **17.04.2026 eklendi.** E²BSO, R²DMA ve P-AOEA algoritmalarının tamamı üretime hazır.

### DNA Faktör Matrisi (10/10 Coverage)

| DNA ID | Faktör | Modül(ler) | Durum |
|--------|--------|-----------|-------|
| D1 | Problem-Yapılı Operatörler | DestroyOperators, RepairOperators | ✅ |
| D2 | Büyük Komşuluk Araması (LNS) | DestroyOperators, RepairOperators | ✅ |
| D3 | Çok Katmanlı Lokal Arama | MultiLayerLS | ✅ |
| D4 | Adaptif Mekanizmalar | PenaltyManager, DiversityController | ✅ |
| D5 | Giant Tour + Split Temsil | sota_common | ✅ |
| D6 | Çoklu Başlangıç Çözümü | MultiStartInitializer | ✅ |
| D7 | Kabul Kriterleri (SA/LAHC) | AcceptanceCriterion | ✅ |
| D8 | Çeşitlilik Yönetimi | DiversityController | ✅ |
| D9 | Penalty-Based Relaxation | PenaltyManager | ✅ |
| D10 | Neural/ML via Evolutionary Genome | P-AOEA | ✅ |

### SOTA Algoritma Mimarisi

```
BaseRoutingStrategy (base_strategy.py)
│
├── SOTA Algorithms (sota_common/)
│   │
│   ├── FAZ 1: E²BSO — GeneticAlgorithmSOTA
│   │   DNA: D1✅ D2✅ D3✅ D4✅ D6✅ D7✅ D8✅
│   │   Benchmark: eil51=0.47%, berlin52=0.00% OPTIMAL
│   │
│   ├── FAZ 2: R²DMA — ResonanceSOTA
│   │   DNA: D1✅ D2✅ D3✅ D4✅ D6✅ D7✅ D8✅ D9✅
│   │   6-boyutlu rezonans (Jaccard, LCS, Shaw, Kapasite, TW)
│   │   3 crossover modu: Constructive / Moderate / Destructive
│   │   Benchmark: eil51=0.47%, berlin52=0.00% OPTIMAL
│   │
│   └── FAZ 3: P-AOEA — PhysicsOperatorEvo
│       DNA: D1✅ D2✅ D3✅ D4✅ D5✅ D6✅ D7✅ D8✅ D9✅ D10✅
│       20+ atomic op, meta-evrim (tournament/crossover/mutation)
│       Benchmark: eil51=0.00% OPTIMAL, berlin52=0.00% OPTIMAL 🏆
│
├── FAZ 0: Ortak Altyapı Modülleri (sota_common/)
│   ├── MultiStartInitializer  — NN + CW + Regret-2 + Random
│   ├── MultiLayerLS           — 2-opt → Or-opt → 3-opt → Swap
│   ├── PenaltyManager         — α_tw, α_cap, iterated penalty
│   ├── AcceptanceCriterion    — SA + LAHC + RTR
│   ├── DestroyOperators       — Random/Worst/Shaw/Related
│   ├── RepairOperators        — Greedy/Regret-2/Regret-3
│   └── DiversityController    — Edge entropy, Hamming
│
└── [Mevcut Pipeline A / B / Holistic / Heuristic stratejileri]
```

### Haversine Tek Kaynak Kuralı

> **Kural:** Tüm coğrafi mesafe hesaplamaları `optimizer_api/utils/haversine.py`'den gelir.
> `clustering.py`, `data_loader.py` ve tüm stratejiler bu modülü `import` eder.
> Duplicate haversine implementasyonu yasaktır. (**FIX-07** ile tesis edildi.)

### Thread-Safety Mimarisi

```python
# optimizer_api/utils/patterns.py
class SingletonMeta(type):
    """Thread-safe singleton — double-checked locking."""
    _instances = {}
    _lock = threading.Lock()  # Sınıf seviyesinde paylaşılan kilit

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:  # double-check
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
```

Uygulanan sınıflar: `DataLoader`, `BenchmarkStateManager`

### TSPLIB Akademik Doğruluk

```python
# optimizer_api/utils/tsplib_parser.py
def tsplib_euc_2d_distance(x1, y1, x2, y2) -> int:
    """EUC_2D NINT rounding — TSPLIB standardına tam uyumlu."""
    return int(math.sqrt((x1-x2)**2 + (y1-y2)**2) + 0.5)
```

| Algoritma | eil51 Optimal (426) | Gap | Berlin52 Optimal (7542) | Gap |
|-----------|--------------------|----|------------------------|----|
| Greedy | 511 | 19.95% | - | - |
| Two-Opt | 453 | 6.34% | - | - |
| E²BSO | 428 | **0.47%** | 7542 | **0.00%** |
| R²DMA | 428 | **0.47%** | 7542 | **0.00%** |
| P-AOEA | **426** | **0.00% 🏆** | **7542** | **0.00% 🏆** |

---

## 🧮 Optimizasyon Algoritmaları

> **Güncel Liste** (09.04.2026 - Ekleyen: Copilot AI — önceki liste yalnızca GA/PSO/Greedy/OR-Tools'u kapsıyordu)

### Pipeline A: Cluster-First, Route-Second (Klasik CVRP)

| Algoritma | Anahtar(lar) | Açıklama |
|---|---|---|
| Genetic Algorithm | `genetic_algorithm`, `ga` | OX1 crossover, swap/inversion mutation |
| PSO | `pso` | Swap-based velocity, discrete PSO |
| GWO | `gwo`, `grey_wolf` | Grey Wolf Optimizer |
| HHO | `hho`, `harris_hawks` | Harris Hawks Optimization |

### Pipeline B: Route-First, Split Decoder (CVRPTW uyumlu)

| Algoritma | Anahtar(lar) | Açıklama |
|---|---|---|
| GA-Split | `ga_split`, `ga-split` | GA + DP Split Decoder |
| PSO-Split | `pso_split` | PSO + DP Split Decoder |
| GWO-Split | `gwo_split` | GWO + DP Split Decoder |
| HHO-Split | `hho_split` | HHO + DP Split Decoder |

### Holistic Solvers

| Algoritma | Anahtar(lar) | Açıklama |
|---|---|---|
| OR-Tools | `ortools_cvrp`, `ortools` | Google OR-Tools CVRP |
| PyVRP | `pyvrp`, `hgs` | DIMACS 2021 winner — opsiyonel |
| VROOM | `vroom` | Açık kaynak VRP çözücü — opsiyonel |

### Heuristics

| Algoritma | Anahtar(lar) | Açıklama |
|---|---|---|
| Greedy | `greedy`, `nearest_neighbor` | Nearest Neighbor |
| Two-Opt | `two_opt`, `2opt` | 2-opt local search |
| Permutation TSP | `permutation_tsp` | Optimal (n≤10) |

### Genetic Algorithm (GA) — Parametreler
```python
population_size: 50
max_iterations: 100
crossover_rate: 0.85
mutation_rate: 0.15
elite_count: 2
tournament_size: 3

Selection: Tournament Selection
Crossover: Order Crossover (OX1)
Mutation: Swap / Inversion
```

### Particle Swarm Optimization (PSO) — Parametreler
```python
swarm_size: 30
max_iterations: 100
inertia_weight: 0.7
cognitive_weight: 1.5
social_weight: 1.5

v(t+1) = w*v(t) + c1*r1*(pbest-x) + c2*r2*(gbest-x)
```

### Karmaşıklık Analizi
| Algoritma | Zaman Karmaşıklığı | Uzay Karmaşıklığı |
|-----------|-------------------|-------------------|
| GA | O(g × p × n²) | O(p × n) |
| PSO | O(i × s × n²) | O(s × n) |
| Greedy | O(n²) | O(n) |
| OR-Tools | O(n³) worst case | O(n²) |
| Permutation | O(n!) | O(n) |

---

## 🔐 Güvenlik

### Authentication Flow
```
1. Login Request
   └─> Supabase Auth API
   └─> JWT Token generation

2. Token Storage
   └─> HttpOnly cookies
   └─> Session management

3. API Requests
   └─> Bearer token in headers
   └─> Token validation on server
```

### Row Level Security (RLS)
```sql
-- Örnek RLS Politikası
CREATE POLICY "Users can only see own data"
ON users FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "Admins can see all data"
ON users FOR ALL
USING (
  EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
);
```

---

## 📊 Performans Optimizasyonları

### Frontend
- **Code Splitting:** Dynamic imports for admin pages
- **Image Optimization:** Next.js Image component
- **Caching:** React Query / SWR for API calls
- **Lazy Loading:** Components loaded on demand

### Backend
- **Connection Pooling:** Database connection reuse
- **Caching:** Redis for frequent queries (planlı — henüz implement edilmemiş)
- **Async Processing:** Background tasks for long operations (planlı — optimizer şu an senkron)
- **Rate Limiting:** Yalnızca `/api/auth/hint` endpoint'inde uygulanmıştır (5 req/min/IP). Genel rate limiting henüz aktif değil. (09.04.2026 - Ekleyen: Copilot AI: "60 req/min per IP" iddiası yanlıştı, düzeltildi)

### Database
- **Indexing:** Indexed columns for frequent queries
- **Partitioning:** Date-based partitioning for routes
- **Denormalization:** Pre-computed aggregations

---

## 🚀 Deployment

### Development
```bash
# Frontend
npm run dev

# Backend
cd optimizer_api && uvicorn main:app --reload
```

### Production
```yaml
# docker-compose.yml
services:
  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      
  backend:
    build: ./optimizer_api
    ports:
      - "8000:8000"
    
  redis:
    image: redis:alpine
```

---

## 📈 Monitoring & Logging

### Metrics
- API response times
- Optimization duration
- Error rates
- User activity

### Logging
```typescript
// Structured logging
logger.info({
  event: 'optimization_completed',
  algorithm: 'ga',
  students: 25,
  duration_ms: 2500,
  vehicles: 4
});
```

---

## 🔮 Gelecek Geliştirmeler

### Tamamlanan (17.04.2026 itibarıyla)
1. ✅ SOTA Framework FAZ 0-3 (E²BSO, R²DMA, P-AOEA)
2. ✅ TSPLIB EUC_2D NINT rounding — tam akademik standart
3. ✅ Thread-safe SingletonMeta
4. ✅ Haversine tek kaynak (`utils/haversine.py`)
5. ✅ Test coverage %64
6. ✅ CLI → Web Import Bridge
7. ✅ CSP + Security headers (`next.config.ts`)
8. ✅ RLS write policies (vehicles, routes, assignments)
9. ✅ Admin role guard (12 admin route)

### Kısa Vadeli (Nisan-Mayıs 2026)
1. Solomon CVRPTW benchmark testleri
2. Frontend CVRPTW zaman penceresi UI
3. Akademik makale yazımı (GECCO 2026 deadline'ı)
4. Sürücü atama UI

### Orta Vadeli (Haziran-Temmuz 2026)
1. Real-time vehicle tracking
2. Push notifications
3. Docker + CI/CD
4. Redis-backed rate limiting

### Uzun Vadeli
1. Machine learning ile talep tahmini
2. Multi-campus support
3. Mobile app (React Native)
4. Heterojen filo aktivasyonu

---

*Bu mimari doküman proje gereksinimlerine göre güncellenecektir.*


> (10.04.2026 - AI Audit): TSP Benchmark Studio entegrasyonu kod düzeyinde incelendi. /api/benchmark/run rotaları, FastAPI backend benchmark_runner mekanizmaları ve ilgili Python (Numba JIT vb.) strateji dosyalarının projenin 'Dual-Track' SOTA (State of the Art) ve ticari hibrit motor yapısına uygun olarak ayrı bir execution branch olarak (academic_benchmark) başarıyla entegre edildiği doğrulandı. Optimizasyon hedefleri ve izolasyon kurallarıyla uyumlu.
