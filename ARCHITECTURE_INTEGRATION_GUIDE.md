# UniRide Architecture Integration Guide

## Quick Navigation

**[Frontend Architecture](#frontend-architecture)** | **[Backend Architecture](#backend-architecture)** | **[Database Layer](#database-layer)** | **[Integration Flows](#integration-flows)** | **[Adding Features](#adding-features)**

---

## System Overview at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16)                        │
│                      Port: 9002                                 │
│  Components → Context/Query → Services → API Routes → Python   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│                      Port: 8000                                 │
│  Strategies (GA/PSO/GWO/HHO) → Local Search → Utilities        │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                SUPABASE (PostgreSQL + Auth)                     │
│                  6 Core Tables + RLS Policies                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. FRONTEND ARCHITECTURE

### File Organization

#### `/src/app/` - Next.js App Router
```
├── (app)/                    → User-facing pages (dashboard, profile, etc)
├── (auth)/                   → Authentication pages (login, register)
├── api/                      → Route Handlers (servers -> Python backend)
│   ├── admin/               → Admin-only operations
│   ├── auth/                → Auth operations
│   ├── calculate-vehicles/  → Vehicle capacity calculations
│   ├── compare-algorithms/  → Compare all optimization algorithms
│   ├── driver/              → Driver operations
│   ├── optimize-route/      → PRIMARY OPTIMIZATION ENDPOINT ⭐
│   ├── profile/             → User profile operations
│   ├── ride-confirmation/   → Ride confirmation operations
│   ├── route-plans/         → Route plan CRUD
│   └── sandbox/             → IE Sandbox/Advanced mode
├── layout.tsx               → Root layout (providers, auth wrapper)
├── page.tsx                 → Home page
└── globals.css              → Global styles
```

#### `/src/services/` - External Service Clients
```
├── optimizer-service.ts      → 🌟 MAIN INTEGRATION POINT
│   ├── optimizeRoutes()      → Calls Python /api/v1/optimize
│   ├── compareAllAlgorithms() → Calls Python /api/v1/compare
│   └── Type definitions      → OptimizationOptions, StudentForOptimization, etc
├── route-plans.ts           → Route plan service
├── schedule-to-requests.ts  → Schedule conversion
├── sandbox-api.ts           → IE sandbox mode
└── doubus/ & excel/         → Data import/export utilities
```

#### `/src/lib/` - Core Utilities
```
├── config.ts                → 📌 CENTRALIZED CONFIGURATION
│   ├── OPTIMIZER_API_URL
│   ├── DEFAULT_*_CAPACITY
│   ├── TIME_WINDOW_MINUTES
│   └── Rate limiting constants
├── database.ts              → Unified DB adapter (exports all Supabase functions)
├── supabase.ts              → Supabase client initialization
├── supabase-auth.ts         → Authentication utilities
├── supabase-admin.ts        → Admin operations
├── supabase-db.ts           → Database query functions
├── algorithm-constants.ts   → Algorithm metadata
└── utils.ts                 → Helper utilities
```

#### `/src/contexts/` - Global State
```
├── auth-context.tsx         → 🔐 ONLY STATE CONTEXT IN SYSTEM
│   ├── AuthContext
│   ├── AuthProvider
│   └── useAuth() hook
```

#### `/src/hooks/` - Custom React Hooks
```
├── use-auth.ts             → Access AuthContext
├── use-mobile.tsx          → Detect mobile viewport
└── use-toast.ts            → Toast notifications (from shadcn)
```

#### `/src/types/` - TypeScript Definitions
```
index.ts contains:
- UserRole = "student" | "admin" | "driver"
- RideStatus = 11 possible states
- DirectionType = "pickup" | "dropoff"
- All database entity types
```

---

## 2. BACKEND ARCHITECTURE (Python FastAPI)

### Directory Structure

#### `/optimizer_api/main.py` - Entry Point
```python
FastAPI(
    title="UniRide Optimization Engine API",
    version="3.1.0"
)

# CORS Middleware
# Endpoints:
GET    /health                      → Status check
GET    /api/v1/strategies          → List algorithms
POST   /api/v1/optimize            → Main optimization
POST   /api/v1/compare             → Compare algorithms
POST   /api/v1/extract-time-windows → CVRPTW support
```

#### `/optimizer_api/strategies/` - Algorithm Implementations

**STRATEGY REGISTRY** (`__init__.py`):
- Singleton pattern for efficiency
- Dictionary-based registry for lookup
- Graceful fallback for optional deps (PyVRP, VROOM)

**Pipeline A (Cluster-First Route-Second):**
```
Input → Sweep Clustering → GA/PSO/GWO/HHO → Local Search → Routes
```
- `ga_strategy.py`
- `pso_strategy.py`
- `gwo_strategy.py`
- `hho_strategy.py`

**Pipeline B (Route-First Cluster-Second):**
```
Input → GA/PSO/GWO/HHO → Split Decoder → Optimal Routes
```
- `ga_split_strategy.py`
- `pso_split_strategy.py`
- `gwo_split_strategy.py`
- `hho_split_strategy.py`

**Holistic Solvers:**
- `ortools_cvrp.py` (default for CVRP)
- `pyvrp_strategy.py` (optional: SOTA 2021 winner)
- `vroom_strategy.py` (optional: ultra-fast C++)

**Quick Heuristics:**
- `two_opt_strategy.py`
- `greedy_heuristic.py`
- `permutation_tsp.py` (optimal for n ≤ 10)

#### `/optimizer_api/utils/` - Supporting Algorithms

```
├── local_search.py              → Refinement algorithms
│   ├── TwoOptLocalSearch
│   ├── ThreeOptLocalSearch
│   ├── OrOptLocalSearch
│   └── HybridLocalSearch
├── split_decoder.py             → Optimal split for clustered routes
├── linear_split_decoder.py      → Linear-time split variant
├── resource_profiler.py         → IE Resource Analysis
├── time_window_extractor.py     → CVRPTW time window parsing
├── distance_matrix_builder.py   → Precompute distances
└── clustering.py                → Sweep/CW clustering
```

#### `/optimizer_api/models/schemas.py` - Data Validation

**Request Models:**
```python
OptimizationRequest
├── students: List[StudentNode]
├── vehicles: List[VehicleConfig]
├── optimizer_config: Dict with all options
└── ...

CompareRequest
├── students: List[StudentNode]
├── algorithms: List[str] (optional)
└── ...
```

**Response Models:**
```python
OptimizationResponse
├── success: bool
├── algorithm_used: str
├── routes: List[VehicleRoute]
├── total_vehicles: int
├── total_duration_minutes: int
├── execution_time_seconds: float
└── ie_data: IERawData (optional)

VehicleRoute
├── vehicle_id: str
├── route_details: List[RouteStep]
├── total_duration_minutes: int
├── total_distance_km: float
├── sw_count, so_count: int
├── student_ids: List[str]
├── departure_time, arrival_times (CVRPTW)
```

---

## 3. DATABASE LAYER (Supabase PostgreSQL)

### Core Tables

#### `users`
```sql
id (UUID) → Primary key
email, name, role ("student"|"admin"|"driver")
student_number (unique)
home_address, home_coordinates (JSONB)
disability_type ("Sw"|"So")
location_code, weekly_schedule_id (FK)
created_at, updated_at
```

#### `weekly_schedules`
```sql
id (UUID) → Primary key
user_id (FK) → users.id
entries (JSONB) → Array of {day, start_time, end_time, ...}
last_updated, created_at, updated_at
```

#### `ride_requests`
```sql
id (UUID) → Primary key
user_id (FK) → users.id
type ("scheduled"|"adhoc")
requested_pickup_time, requested_dropoff_time (TIMESTAMPTZ)
pickup_location, dropoff_location (JSONB: {lat, lng})
status (pending_student_confirmation|confirmed|in_progress|completed|...)
vehicle_id (FK) → vehicles.id (nullable)
created_at, updated_at
```

#### `vehicles`
```sql
id (UUID) → Primary key
name, type ("minibus"|"bus"|"van")
plate_number
wheelchair_capacity, seating_capacity
status ("active"|"inactive"|"maintenance")
created_at, updated_at
```

#### `routes`
```sql
id (UUID) → Primary key
date (DATE), timeslot (TEXT)
type ("pickup"|"dropoff")
waypoints (TEXT[])
optimized_path (JSONB) → Detailed route
total_duration (INTEGER: minutes)
total_distance (DECIMAL: km)
vehicle_count
created_at
UNIQUE(date, timeslot)
```

#### `route_assignments`
```sql
id (UUID) → Primary key
date (DATE), vehicle_id (FK), driver_id (FK), route_id (FK)
student_ids (UUID[])
pickup_time, estimated_dropoff_time
status ("scheduled"|"in_progress"|"completed"|"cancelled")
created_at, updated_at
```

### RLS Policies
Located: `/supabase/rls_policies.sql`

**Principle:** Users can only see their own data (unless admin/driver)
- Students: See own schedules, ride requests
- Drivers: See assigned routes, vehicle data
- Admins: See all data

---

## 4. INTEGRATION FLOWS

### A. Single Route Optimization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER TRIGGERS OPTIMIZATION (Frontend Component)              │
│    e.g., Click "Calculate Route" button                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. FORM VALIDATION (React Hook Form + Zod)                     │
│    Validates:                                                   │
│    - Students list (min 1, all required fields)                 │
│    - Depot coordinates                                          │
│    - Algorithm choice                                           │
│    - Capacity constraints                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. CALL SERVICE FUNCTION (src/services/optimizer-service.ts)   │
│                                                                 │
│    optimizeRoutes(                                              │
│      students: StudentForOptimization[],                        │
│      depot: Depot,                                              │
│      options: OptimizationOptions                               │
│    )                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. NEXT.JS ROUTE HANDLER POST /api/optimize-route             │
│    - User auth check (requireAdmin)                            │
│    - Validate request body (Zod schema)                        │
│    - Transform field names (snake_case ↔ camelCase)            │
│    - Call optimizer-service                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. HTTP POST to Python API                                     │
│    POST http://127.0.0.1:8000/api/v1/optimize                 │
│    Headers: Content-Type: application/json                     │
│    Body: {                                                      │
│      "students": [...],                                        │
│      "vehicles": [...],                                        │
│      "optimizer_config": {...}                                 │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. PYTHON FASTAPI PROCESSING                                   │
│    - Validate with Pydantic schemas                            │
│    - Get algorithm from STRATEGY_REGISTRY                      │
│    - Execute algorithm: optimizer.optimize()                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. ALGORITHM EXECUTION                                          │
│    Path 1: Cluster-First (Sweep Clustering → GA/PSO/etc)       │
│    Path 2: Route-First (GA/PSO → Split Decoder)                │
│    Path 3: Holistic (OR-Tools/PyVRP/VROOM direct)              │
│                                                                 │
│    Optional: ApplyLocal Search (2-opt/3-opt/or-opt/hybrid)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. RESPONSE CONSTRUCTION                                        │
│    OptimizationResponse {                                       │
│      success: true,                                             │
│      algorithm_used: "ga_split",                                │
│      routes: [VehicleRoute, ...],                               │
│      total_vehicles: 2,                                         │
│      total_duration_minutes: 45,                                │
│      execution_time_seconds: 2.3,                               │
│      ie_data: {...}  // Optional                                │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 9. RESPONSE RETURNED TO FRONTEND                               │
│    - Automatically cached by React Query                        │
│    - Response intercepted by optimizer-service.ts              │
│    - Returned to component calling optimizeRoutes()            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 10. COMPONENT UPDATES UI                                        │
│     - Show optimized routes on map                             │
│     - Display vehicle assignments                              │
│     - Show resource analysis (if IE mode)                      │
│     - Optional: Save to database, notify users                 │
└─────────────────────────────────────────────────────────────────┘
```

### B. Algorithm Comparison Flow

Similar to A, but:
- **Endpoint:** `POST /api/v1/compare`
- **Python:** Executes ALL algorithms sequentially
- **Response:** `CompareResponse` with results for each algorithm
- **Use Case:** Benchmark, select best algorithm, analyze tradeoffs

### C. Time Window Extraction Flow (CVRPTW)

```
Weekly Schedule (JSONB)
    ↓
Extract target arrival/departure times
    ↓
Create time windows (with offset buffer)
    ↓
Return TimeWindow objects
    ↓
Include in optimization request (use_time_windows=true)
```

---

## 5. ADDING FEATURES

### Scenario: Add a New Optimization Algorithm

#### Step 1: Implement Strategy Class
**File:** `optimizer_api/strategies/my_algorithm_strategy.py`
```python
from strategies.base_strategy import BaseRoutingStrategy

class MyAlgorithmStrategy(BaseRoutingStrategy):
    def optimize(self, problem_data: Dict) -> List[List[int]]:
        """
        Args:
            problem_data: {
                'distance_matrix': np.ndarray,
                'num_vehicles': int,
                'max_time': int,
                'capacity': Dict,
                ...
            }
        Returns:
            List of routes (each route is list of node indices)
        """
        # Implement algorithm
        pass
```

#### Step 2: Register in Strategy Registry
**File:** `optimizer_api/strategies/__init__.py`
```python
from strategies.my_algorithm_strategy import MyAlgorithmStrategy

_my_algo_strategy = MyAlgorithmStrategy()

STRATEGY_REGISTRY = {
    "my_algorithm": _my_algo_strategy,
    # ... existing strategies
}
```

#### Step 3: Update Frontend Type Definitions
**File:** `src/services/optimizer-service.ts`
```typescript
export interface OptimizationOptions {
  algorithm?: "my_algorithm" | ... // Add new algorithm
  // ...
}
```

#### Step 4: Test
- Add test case to `optimizer_api/tests/`
- Test via `POST /api/optimize-route` with `algorithm: "my_algorithm"`
- Add to benchmark suite for comparison

---

### Scenario: Add a New API Endpoint

#### Step 1: Create Route Handler
**File:** `src/app/api/my-feature/route.ts`
```typescript
import { NextResponse } from "next/server";
import { z } from "zod";

const mySchema = z.object({
  // Define schema
});

export async function POST(request: Request) {
  try {
    // Authentication (if needed)
    await requireAdmin(request);
    
    // Validate
    const body = await request.json();
    const data = mySchema.parse(body);
    
    // Process (call service, database, etc)
    const result = await myService(data);
    
    // Return
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error.message },
      { status: 400 }
    );
  }
}
```

#### Step 2: Create Service Client (if calling external API)
**File:** `src/services/my-service.ts`
```typescript
export async function myServiceFunction(input: MyInput): Promise<MyOutput> {
  const response = await fetch("/api/my-feature", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  
  if (!response.ok) throw new Error("Request failed");
  return response.json();
}
```

#### Step 3: Use in Component
```typescript
import { myServiceFunction } from "@/services/my-service";

export function MyComponent() {
  const { mutate } = useMutation({
    mutationFn: myServiceFunction,
    onSuccess: (data) => {
      // Handle success
    },
  });
  
  return (
    <button onClick={() => mutate(input)}>
      Execute
    </button>
  );
}
```

---

### Scenario: Add a New Database Table/Field

#### Step 1: Create Migration
**File:** `supabase/migrations/TIMESTAMP_add_my_table.sql`
```sql
CREATE TABLE my_table (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add RLS policies
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can see their own data"
  ON my_table FOR SELECT
  USING (user_id = auth.uid());
```

#### Step 2: Update Schema
**File:** `supabase/schema.sql` - Add table definition

#### Step 3: Create Database Functions
**File:** `src/lib/supabase-db.ts`
```typescript
export async function getMyTableData(userId: string) {
  const { data, error } = await supabase
    .from("my_table")
    .select("*")
    .eq("user_id", userId);
  
  if (error) throw error;
  return data;
}
```

#### Step 4: Export and Use
**File:** `src/lib/database.ts`
```typescript
export { getMyTableData } from "./supabase-db";
```

#### Step 5: Use in Components/Services
```typescript
import { getMyTableData } from "@/lib/database";

const data = await getMyTableData(userId);
```

---

## 6. CONFIGURATION REFERENCE

### Environment Variables

#### Frontend (`.env.local`)
```
NEXT_PUBLIC_OPTIMIZER_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJxxxx
NODE_ENV=development
```

#### Backend (`optimizer_api/.env`)
```
ALLOWED_ORIGINS=http://localhost:9002,http://127.0.0.1:9002
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJxxxx
```

### Constants (`src/lib/config.ts`)
```typescript
OPTIMIZER_API_URL           → Backend API base URL
DEFAULT_TIME_WINDOW_MINUTES → 30 (CVRPTW default)
DEFAULT_MAX_TRAVEL_TIME     → 120 minutes
DEFAULT_SW_CAPACITY         → 4 (wheelchair capacity)
DEFAULT_SO_CAPACITY         → 5 (seating capacity)
```

---

## 7. KEY INTEGRATION POINTS SUMMARY

| Component | Location | Purpose | When to Modify |
|-----------|----------|---------|-----------------|
| **Frontend-Backend Bridge** | `src/services/optimizer-service.ts` | TypeScript interface to Python API | Adding optimization options, changing parameter names |
| **Route Handlers** | `src/app/api/*/route.ts` | Next.js edge layer, validates & forwards | Adding new API endpoints, changing request validation |
| **Database Access** | `src/lib/supabase-db.ts` | All database queries | Adding new DB operations, changing queries |
| **Global Config** | `src/lib/config.ts` | Constants used throughout app | Changing default capacities, API URLs, limits |
| **Algorithm Registry** | `optimizer_api/strategies/__init__.py` | Python algorithm lookup | Adding/removing algorithms |
| **FastAPI Endpoints** | `optimizer_api/main.py` | Main optimization endpoints | Changing response format, adding endpoints |
| **Database Schema** | `supabase/schema.sql` | Table definitions | Adding tables, changing columns |
| **RLS Policies** | `supabase/rls_policies.sql` | Data access control | Changing permission rules |
| **Type Definitions** | `src/types/index.ts` | TypeScript interfaces | Adding domain types, enums |

---

## 8. DEBUGGING CHECKLIST

When something doesn't work:

- [ ] Check **optimizer_api/.env** - ALLOWED_ORIGINS matching frontend port?
- [ ] Verify **Python API running** on port 8000: `curl http://127.0.0.1:8000/health`
- [ ] Check **frontend logs** (browser console) - HTTP error?
- [ ] Verify **Supabase connection** - env vars correct?
- [ ] Check **RLS policies** - user permission to table?
- [ ] Verify **request format** - match Pydantic schema?
- [ ] Check **algorithm choice** - exists in STRATEGY_REGISTRY?
- [ ] Look at **Python API logs** - algorithm error?

---

## 9. PERFORMANCE CONSIDERATIONS

| Layer | Optimization | Implementation |
|-------|-------------|-----------------|
| **Frontend** | Cache optimization results (React Query) | Auto-invalidation on parameter change |
| **Frontend** | Lazy load algorithm list | Fetch only when needed |
| **API Layer** | Parallel execution with ThreadPoolExecutor | `max_workers=5` in main.py |
| **Python** | Split problem into clusters first | Use Pipeline B (ga_split, pso_split, etc) |
| **Python** | Precompute distance matrix | Build once, reuse for all algorithms |
| **DB** | Index on user_id, date | Speed up queries on ride_requests, routes |
| **DB** | Use JSONB efficiently | Query nested data without full table scan |

---

## 10. SECURITY CONSIDERATIONS

- **Authentication:** All API routes require `requireAdmin()` check
- **Authorization:** RLS policies enforce row-level access control
- **Input Validation:** Zod (frontend), Pydantic (backend)
- **CORS:** Explicitly configured, not wildcard
- **Secrets:** Supabase keys in environment variables, never committed
- **Rate Limiting:** Constant defined but not yet implemented (TODO)

---

**Last Updated:** April 10, 2026 | **Version:** 3.1.0
