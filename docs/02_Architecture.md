# UniRide CVRPTW - Mimari Tasarım

## Sürüm: 2.2.0 | Tarih: 10 Nisan 2026 (10.04.2026 - Ekleyen: Antigravity AI)

---

## 📐 Sistem Mimarisi Genel Bakış

UniRide, mikroservis tabanlı bir mimari ile tasarlanmış olup, frontend ve backend servisleri birbirinden bağımsız olarak çalışabilmektedir. Sistem, üç ana katmandan oluşmaktadır: Presentation Layer (Frontend), Business Logic Layer (Backend API), ve Data Layer (Database).

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Next.js 16 Frontend                    │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │   Admin     │ │   Driver    │ │   Student   │       │   │
│  │  │   Panel     │ │   Interface │ │   Interface │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Next.js API Routes                       │   │
│  │  /api/optimize-route  /api/admin/*  /api/driver/*       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              │ HTTP/REST                        │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Python Optimization Engine                  │   │
│  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐    │   │
│  │  │  GA   │ │  PSO  │ │ Greedy│ │ORTOOLS│ │ KMean │    │   │
│  │  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘    │   │
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
| Next.js | 16.x | App Router, SSR |
| TypeScript | 5.x | Type safety |
| React | 18.x | UI components |
| Tailwind CSS | 3.x | Styling (`^3.4.1` — 4.x DEĞİL, 09.04.2026 - Ekleyen: Copilot AI) |
| shadcn/ui | latest | UI component library |
| Supabase JS | 2.x | Database client |

#### Dizin Yapısı
```
src/
├── app/                    # Next.js App Router
│   ├── (app)/             # Authenticated routes
│   │   ├── admin/         # Admin panel pages
│   │   ├── driver/        # Driver interface
│   │   └── dashboard/     # Student dashboard
│   ├── (auth)/            # Authentication pages
│   └── api/               # API route handlers (14 dosya)
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── admin/            # Admin-specific components (IE Dashboard dahil)
│   ├── auth/             # Auth components
│   └── student/          # Student components
├── services/             # Business logic services
│   ├── doubus/           # Route optimization
│   ├── excel/            # Import/Export
│   └── optimizer-service.ts
├── lib/                  # Utilities and config
│   ├── config.ts         # Centralized configuration
│   ├── supabase.ts       # Database client
│   ├── supabase-admin.ts # Server-side admin client (service_role)
│   └── algorithm-constants.ts
├── types/                # TypeScript types
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
├── main.py               # FastAPI application entry (7 endpoints)
├── models/
│   └── schemas.py        # Pydantic models
├── strategies/           # 18 strateji dosyası + base
│   ├── __init__.py       # Strategy registry (29 anahtar)
│   ├── base_strategy.py  # Abstract base class
│   ├── hybrid_base_strategy.py # Shared base for split strategies (10.04.2026)
│   ├── ga_strategy.py    # Genetic Algorithm (Pipeline A)
│   ├── pso_strategy.py   # Particle Swarm Optimization (Pipeline A)
│   ├── gwo_strategy.py   # Grey Wolf Optimizer (Pipeline A)
│   ├── hho_strategy.py   # Harris Hawks Optimization (Pipeline A)
│   ├── ga_split_strategy.py   # GA + Split Decoder (Pipeline B)
│   ├── pso_split_strategy.py  # PSO + Split Decoder (Pipeline B)
│   ├── gwo_split_strategy.py  # GWO + Split Decoder (Pipeline B)
│   ├── hho_split_strategy.py  # HHO + Split Decoder (Pipeline B)
│   ├── ortools_cvrp.py   # OR-Tools CVRP (Holistic)
│   ├── pyvrp_strategy.py # PyVRP / HGS (opsiyonel, Holistic)
│   ├── vroom_strategy.py # VROOM (opsiyonel, Holistic)
│   ├── greedy_heuristic.py # Greedy / Nearest Neighbor
│   ├── two_opt_strategy.py # Two-Opt local search
│   ├── permutation_tsp.py  # Permutation TSP
│   ├── cvrptw_wrapper.py   # CVRPTW time-window wrapper
│   └── _archived/          # Retired strategies (kmeans_tsp.py)
└── utils/
    ├── constants.py             # Shared constants (DEFAULT_TRAVEL_FALLBACK_MINUTES)
    ├── clustering.py            # Student clustering algorithms
    ├── clustering_strategies/   # 7 clustering algoritması
    ├── local_search.py          # 8 local search tipi
    ├── local_search_numba.py    # Numba JIT-hızlandırmalı varyant
    ├── split_decoder.py         # DP tabanlı split decoder
    ├── linear_split_decoder.py  # O(n) linear split variant
    ├── resource_profiler.py     # IE Resource Engine
    ├── time_window_extractor.py # TW extraction utilities
    └── data_loader.py           # Data loading (haversine canonical source)
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

### Kısa Vadeli (Nisan-Mayıs 2026)
1. FIX-04 Pipeline A genişletmesi (11 dosya)
2. FIX-07 haversine birleştirme tamamlama
3. Test coverage %25 → %60
4. Akademik benchmark sonuçları
5. Sürücü atama UI

### Orta Vadeli (Haziran-Temmuz 2026)
1. Real-time vehicle tracking
2. Push notifications
3. Docker + CI/CD
4. DataLoader TTL/invalidation
5. Redis-backed rate limiting

### Uzun Vadeli
1. Machine learning ile talep tahmini
2. Multi-campus support
3. Mobile app (React Native)
4. Heterojen filo aktivasyonu (stratejilerde)

---

*Bu mimari doküman proje gereksinimlerine göre güncellenecektir.*


> (10.04.2026 - AI Audit): TSP Benchmark Studio entegrasyonu kod düzeyinde incelendi. /api/benchmark/run rotaları, FastAPI backend benchmark_runner mekanizmaları ve ilgili Python (Numba JIT vb.) strateji dosyalarının projenin 'Dual-Track' SOTA (State of the Art) ve ticari hibrit motor yapısına uygun olarak ayrı bir execution branch olarak (academic_benchmark) başarıyla entegre edildiği doğrulandı. Optimizasyon hedefleri ve izolasyon kurallarıyla uyumlu.
