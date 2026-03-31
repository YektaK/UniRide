# UniRide CVRPTW - Mimari Tasarım

## Sürüm: 2.0.0 | Tarih: 30 Mart 2026

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
| React | 19.x | UI components |
| Tailwind CSS | 4.x | Styling |
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
│   └── api/               # API route handlers
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── admin/            # Admin-specific components
│   ├── auth/             # Auth components
│   └── student/          # Student components
├── services/             # Business logic services
│   ├── doubus/           # Route optimization
│   ├── excel/            # Import/Export
│   └── optimizer-service.ts
├── lib/                  # Utilities and config
│   ├── config.ts         # Centralized configuration
│   ├── supabase.ts       # Database client
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
├── main.py               # FastAPI application entry
├── models/
│   └── schemas.py        # Pydantic models
├── strategies/
│   ├── __init__.py       # Strategy registry
│   ├── base_strategy.py  # Abstract base class
│   ├── ga_strategy.py    # Genetic Algorithm
│   ├── pso_strategy.py   # Particle Swarm Optimization
│   ├── greedy_heuristic.py
│   ├── ortools_cvrp.py   # OR-Tools CVRP
│   ├── permutation_tsp.py
│   └── kmeans_tsp.py     # K-Means clustering
└── utils/
    ├── clustering.py     # Clustering utilities
    └── data_loader.py    # Data loading utilities
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

### Genetic Algorithm (GA)
```python
# Parametreler
population_size: 50
max_iterations: 100
crossover_rate: 0.85
mutation_rate: 0.15
elite_count: 2
tournament_size: 3

# Operatörler
Selection: Tournament Selection
Crossover: Order Crossover (OX1)
Mutation: Swap / Inversion
```

### Particle Swarm Optimization (PSO)
```python
# Parametreler
swarm_size: 30
max_iterations: 100
inertia_weight: 0.7
cognitive_weight: 1.5
social_weight: 1.5

# Velocity Update
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
- **Caching:** Redis for frequent queries
- **Async Processing:** Background tasks for long operations
- **Rate Limiting:** 60 req/min per IP

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

### Kısa Vadeli
1. CVRPTW time window desteği
2. GWO/HHO algoritma implementasyonu
3. Pickup/Dropoff direction UI

### Orta Vadeli
1. Real-time vehicle tracking
2. Push notifications
3. Mobile app (React Native)

### Uzun Vadeli
1. Machine learning ile talep tahmini
2. Dynamic pricing
3. Multi-campus support

---

*Bu mimari doküman proje gereksinimlerine göre güncellenecektir.*
