# UniRide Architecture - Developer Quick Reference

## 🎯 Core System Overview

```
[Frontend: Next.js 16 @ 9002]
        ↓ HTTP/JSON
[Next.js API Layer @ Edge]
        ↓ HTTP/JSON
[Python FastAPI @ 8000]
        ↓ Query/Mutations
[Supabase PostgreSQL]
```

---

## 📍 Key File Locations

### Frontend Entry Points
| Path | Purpose | Key Exports |
|------|---------|------------|
| `src/app/layout.tsx` | Root layout | AuthProvider wrapper |
| `src/app/page.tsx` | Home page | Dashboard UI |
| `src/contexts/auth-context.tsx` | Global auth state | `useAuth()` hook |
| `src/services/optimizer-service.ts` | 🌟 Python API client | `optimizeRoutes()`, `compareAllAlgorithms()` |
| `src/lib/config.ts` | Configuration | `OPTIMIZER_API_URL`, capacities, constants |

### Backend Entry Points
| Path | Purpose | Port |
|------|---------|------|
| `optimizer_api/main.py` | FastAPI app | 8000 |
| `optimizer_api/strategies/__init__.py` | Algorithm registry | STRATEGY_REGISTRY dict |
| `optimizer_api/models/schemas.py` | Request/response models | Pydantic BaseModels |

### Database
| Path | Purpose |
|------|---------|
| `supabase/schema.sql` | Table definitions |
| `supabase/rls_policies.sql` | Access control |
| `src/lib/supabase-db.ts` | Query functions |

---

## 🔄 The Main Integration Path (Most Used)

### 1️⃣ Frontend Component Triggers Action
```typescript
// src/components/MyComponent.tsx
import { optimizeRoutes } from "@/services/optimizer-service";

await optimizeRoutes(students, depot, {
  algorithm: "ga_split",
  sw_capacity: 4,
  so_capacity: 5
})
```

### 2️⃣ Service Function Calls HTTP Endpoint
```typescript
// src/services/optimizer-service.ts
function optimizeRoutes(...) {
  return fetch("/api/optimize-route", {
    method: "POST",
    body: JSON.stringify(...)
  })
}
```

### 3️⃣ Next.js Route Handler Validates & Forwards
```typescript
// src/app/api/optimize-route/route.ts
export async function POST(request: Request) {
  const body = await request.json();
  const validated = optimizeRouteSchema.parse(body);
  
  // Call optimizer-service to forward to Python
  return optimizeRoutes(validated);
}
```

### 4️⃣ Python API Processes & Returns
```python
# optimizer_api/main.py
@app.post("/api/v1/optimize")
async def optimize(request: OptimizationRequest):
    strategy = get_strategy(request.algorithm)
    result = strategy.optimize(request.to_dict())
    return OptimizationResponse(...)
```

### 5️⃣ Response Cached by React Query
```typescript
// Automatic via React Query in component
const { data, isLoading, error } = useQuery({
  queryKey: ["optimize", params],
  queryFn: () => optimizeRoutes(...)
})
```

---

## 🛠️ Available Algorithms

### Quick Selection Guide

| Need | Use Algorithm | Pipeline |
|------|-----------------|-----------|
| **Fast + Good** | `ga_split` or `pso_split` | Route-First |
| **Best Quality** | `ga_split` + `local_search_type: "hybrid"` | Route-First + Refinement |
| **Time Windows** | Algorithm + `use_time_windows: true` | Any |
| **Comparison** | POST `/api/compare-algorithms` | All algorithms |
| **Very Small (n≤10)** | `permutation_tsp` | Brute force |

### Algorithm Complexity

```
Fast      → Greedy (O(n²))
           → OR-Tools (heuristic)
           → 2-Opt (O(n²) per iteration)
           
Medium    → GA/PSO/GWO/HHO (metaheuristics)
           → with local_search_type: "none"

Slow+Best → GA/PSO/GWO/HHO + split
           → with local_search_type: "hybrid"
           
SOTA      → PyVRP or VROOM (if installed)
```

---

## 📦 Key Data Structures

### Request (Frontend → Backend)
```typescript
{
  students: [
    { id, name, location_code, coordinates, disability_type, ...time_fields }
  ],
  depot: { id, lat, lng },
  algorithm: "ga_split",
  sw_capacity: 4,
  so_capacity: 5,
  
  // Optional CVRPTW
  direction: "pickup",
  use_time_windows: true,
  target_time: "09:00",
  time_window_size: 30,
  
  // Optional algo config
  ga_config: { population_size: 100, max_iterations: 200 }
}
```

### Response (Backend → Frontend)
```typescript
{
  success: true,
  algorithm_used: "ga_split",
  routes: [
    {
      vehicle_id: "v1",
      route_details: [...],
      total_duration_minutes: 45,
      total_distance_km: 28.5,
      sw_count: 2,
      so_count: 3,
      student_ids: ["s1", "s2", ...],
      departure_time: "09:00",  // CVRPTW
      arrival_times: { "s1": "09:15", ... }
    }
  ],
  total_vehicles: 2,
  total_duration_minutes: 45,
  execution_time_seconds: 2.3,
  ie_data: { ... }  // Optional resource analysis
}
```

---

## 🗄️ Database: Quick Reference

### Users (Core)
```sql
SELECT * FROM users WHERE id = $1
-- Fields: id, email, name, role, student_number, home_coordinates, disability_type, ...
```

### Ride Requests (Most Used)
```sql
SELECT * FROM ride_requests 
WHERE date_trunc('day', requested_pickup_time) = CURRENT_DATE
-- Use for daily optimization
```

### Routes (Output)
```sql
INSERT INTO routes (date, timeslot, optimized_path, ...) 
VALUES ($1, $2, $3, ...)
-- Store optimized results
```

---

## 🔐 Authentication & Authorization

### Check User Permissions
```typescript
// Frontend
import { useAuth } from "@/hooks/use-auth";
const { user, isLoading } = useAuth();
if (user?.role !== "admin") return <div>Access Denied</div>;

// Backend (Route Handler)
import { requireAdmin } from "@/lib/admin-auth";
await requireAdmin(request);  // Throws if not admin
```

### Database Row-Level Security (RLS)
```sql
-- Student can only see own ride requests
CREATE POLICY "student_policy" ON ride_requests
  FOR SELECT USING (user_id = auth.uid());

-- Admin can see all
CREATE POLICY "admin_policy" ON ride_requests
  FOR ALL USING (auth.jwt() -> 'app_metadata' ->> 'role' = 'admin');
```

---

## 🚀 Deployment Checklist

- [ ] **Frontend:** `npm run build` succeeds
- [ ] **Backend:** `python -m pytest` all pass
- [ ] **Env Vars:** All required `.env` variables set in production
- [ ] **CORS:** `ALLOWED_ORIGINS` includes production frontend URL
- [ ] **Database:** Schema migrations applied, RLS policies enabled
- [ ] **Ports:** 9002 (frontend) and 8000 (backend) accessible
- [ ] **Secrets:** API keys never committed, use managed secrets

---

## 🔍 Debugging Commands

### Frontend
```bash
# Dev server
npm run dev          # Port 9002

# Type check
npm run typecheck

# Run tests
npm run test
npm run test:ui
```

### Backend
```bash
# Start API
uvicorn main:app --reload --port 8000

# Health check
curl http://127.0.0.1:8000/health

# List algorithms
curl http://127.0.0.1:8000/api/v1/strategies

# Test optimization
curl -X POST http://127.0.0.1:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d @request.json
```

### Database
```sql
-- Check table structure
\d ride_requests

-- View recent records
SELECT * FROM ride_requests ORDER BY created_at DESC LIMIT 5;

-- Test RLS policies
SELECT * FROM ride_requests;  -- Should filter based on user
```

---

## ⚡ Performance Tips

### Reduce Optimization Time
```typescript
// ❌ Slow: Default settings
await optimizeRoutes(students, depot, { algorithm: "ga" })

// ✅ Fast: Configured for speed
await optimizeRoutes(students, depot, {
  algorithm: "greedy"  // or ga_split
})

// ✅ Best: Split + quick local search
await optimizeRoutes(students, depot, {
  algorithm: "ga_split",
  local_search_type: "two_opt",  // Not hybrid
  ga_config: { max_iterations: 50 }  // Fewer iterations
})
```

### Cache Results
```typescript
// React Query handles automatic caching
// But manually invalidate when needed:
const queryClient = useQueryClient();
queryClient.invalidateQueries({ queryKey: ["optimize"] });
```

### Database Optimization
```sql
-- Add indexes on frequently queried fields
CREATE INDEX idx_ride_requests_date ON ride_requests(
  date_trunc('day', requested_pickup_time), user_id
);
```

---

## 📚 Module Dependencies

### Frontend
```
Next.js 16 + TypeScript
React 18 + React Query 5
Radix UI (components) + Tailwind (styling)
React Hook Form (forms) + Zod (validation)
Supabase JS client
Recharts (charting)
```

### Backend
```
FastAPI 0.104+
Uvicorn (ASGI server)
Pydantic (validation)
NumPy + SciPy (math)
OR-Tools (optional: CVRP solver)
PyVRP + VROOM (optional: SOTA solvers)
Supabase Python client
```

### Database
```
Supabase (PostgreSQL + Auth)
Row-Level Security (RLS) policies
UUID primary keys
JSONB data types
```

---

## 🎓 Learning Path

### For Frontend Developers
1. Read `src/services/optimizer-service.ts` - understand API contract
2. Check `src/app/api/optimize-route/route.ts` - see validation
3. Study `src/contexts/auth-context.tsx` - global state pattern
4. Explore `src/components/` - find similar examples

### For Backend Developers
1. Review `optimizer_api/main.py` - FastAPI structure
2. Examine `optimizer_api/strategies/__init__.py` - algorithm registry
3. Check `optimizer_api/strategies/ga_split_strategy.py` - algorithm example
4. Test with curl or Postman

### For Full Stack
1. Trace the "Main Integration Path" above
2. Follow one complete request-response cycle
3. Modify something small (e.g., add a config constant)
4. Deploy and verify end-to-end

---

## 🔗 Quick Links

| Resource | Location |
|----------|----------|
| Full Architecture Guide | `ARCHITECTURE_INTEGRATION_GUIDE.md` |
| Session Benchmark State | `academic_benchmark/SESSION_HANDOFF_2026-04-08.md` |
| Database Schema | `supabase/schema.sql` |
| API Documentation | Python FastAPI docs @ `http://127.0.0.1:8000/docs` |
| Type Definitions | `src/types/index.ts` |
| Config Constants | `src/lib/config.ts` |

---

## 📞 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Failed to optimize" | Check Python API running on 8000 |
| "CORS error" | Verify frontend URL in `ALLOWED_ORIGINS` |
| "Algorithm not found" | Check STRATEGY_REGISTRY in strategies/__init__.py |
| "RLS policy denies access" | Verify user role and policy in rls_policies.sql |
| "Optimization takes forever" | Reduce population_size or max_iterations in ga_config |
| "Type errors in IDE" | Run `npm run typecheck` and check types/index.ts |

---

**Last Updated:** April 10, 2026 | **UniRide v3.1.0**
