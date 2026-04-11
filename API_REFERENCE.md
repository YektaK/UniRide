# UniRide API Reference

**Base URLs:**
- **Frontend API:** `http://localhost:9002/api`
- **Python Backend:** `http://127.0.0.1:8000/api/v1`

---

## Next.js Route Handlers (Frontend → Backend Layer)

### Route Optimization

#### `POST /api/optimize-route`
**Purpose:** Optimize a single set of students into routes using one algorithm

**Authentication:** Admin required

**Request Body:**
```json
{
  "students": [
    {
      "id": "student_001",
      "student_id": "2024001",
      "name": "Ahmet Yılmaz",
      "location_code": "K123",
      "coordinates": { "lat": 41.0082, "lng": 28.9784 },
      "home_coordinates": { "lat": 41.0100, "lng": 28.9800 },
      "disability_type": "Sw",
      "pickup_time": "09:00",
      "dropoff_time": "16:00"
    }
  ],
  "depot": {
    "id": "depot_01",
    "lat": 41.0050,
    "lng": 28.9700
  },
  "algorithm": "ga_split",
  "max_travel_time": 120,
  "sw_capacity": 4,
  "so_capacity": 5,
  "direction": "pickup",
  "use_time_windows": true,
  "target_time": "09:00",
  "time_window_size": 30,
  "local_search_type": "two_opt",
  "ga_config": {
    "population_size": 100,
    "max_iterations": 200,
    "crossover_rate": 0.8,
    "mutation_rate": 0.1
  }
}
```

**Response:**
```json
{
  "success": true,
  "algorithm_used": "ga_split",
  "routes": [
    {
      "vehicle_id": "v1",
      "route_details": [
        {
          "location1": "depot_01",
          "location2": "K123",
          "duration": 15,
          "distance": 3.2
        }
      ],
      "total_duration_minutes": 45,
      "total_distance_km": 28.5,
      "sw_count": 2,
      "so_count": 3,
      "student_ids": ["student_001", "student_002"],
      "departure_time": "09:00",
      "arrival_times": {
        "student_001": "09:15",
        "student_002": "09:42"
      },
      "time_window_violations": 0
    }
  ],
  "total_vehicles": 2,
  "total_duration_minutes": 45,
  "execution_time_seconds": 2.3
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request body
- `401` - Unauthorized (not admin)
- `500` - Server error

**Implementation:** `src/app/api/optimize-route/route.ts`

---

### Algorithm Comparison

#### `POST /api/compare-algorithms`
**Purpose:** Compare all available algorithms on the same problem

**Authentication:** Admin required

**Request Body:**
```json
{
  "students": [...],  // Same as optimize-route
  "depot": {...},
  "algorithms": ["ga_split", "pso_split", "gwo_split"],  // Optional: defaults to all
  "clusteringAlgorithm": "sweep"
}
```

**Response:**
```json
{
  "success": true,
  "comparisons": [
    {
      "algorithm": "ga_split",
      "total_vehicles": 2,
      "total_duration_minutes": 45,
      "total_distance_km": 28.5,
      "execution_time_seconds": 2.3,
      "routes": [...]
    },
    {
      "algorithm": "pso_split",
      "total_vehicles": 2,
      "total_duration_minutes": 48,
      "total_distance_km": 29.1,
      "execution_time_seconds": 1.9,
      "routes": [...]
    }
  ]
}
```

**Implementation:** `src/app/api/compare-algorithms/route.ts`

---

### Vehicle Calculations

#### `POST /api/calculate-vehicles`
**Purpose:** Calculate minimum vehicles needed

**Request Body:**
```json
{
  "students": [...],
  "sw_capacity": 4,
  "so_capacity": 5,
  "max_travel_time": 120
}
```

**Response:**
```json
{
  "min_vehicles": 2,
  "recommended_vehicles": 3,
  "analysis": {
    "sw_students": 5,
    "so_students": 8,
    "total_students": 13,
    "vehicles_for_sw": 2,
    "vehicles_for_so": 2,
    "time_based_vehicles": 1
  }
}
```

**Implementation:** `src/app/api/calculate-vehicles/route.ts`

---

### Route Plans Management

#### `GET /api/route-plans`
**Purpose:** Fetch all route plans for current user

**Query Parameters:**
- `date` (optional): Filter by date
- `status` (optional): "draft" | "confirmed" | "active" | "completed" | "cancelled"

**Response:**
```json
{
  "route_plans": [
    {
      "id": "rp_001",
      "date": "2026-04-10",
      "status": "confirmed",
      "routes": [...],
      "created_at": "2026-04-10T10:00:00Z"
    }
  ]
}
```

**Implementation:** `src/app/api/route-plans/route.ts`

---

#### `POST /api/route-plans`
**Purpose:** Create new route plan

**Request Body:**
```json
{
  "date": "2026-04-10",
  "routes": [...],  // From optimization result
  "notes": "Morning pickup routes"
}
```

**Response:**
```json
{
  "id": "rp_001",
  "date": "2026-04-10",
  "status": "draft",
  "routes": [...],
  "created_at": "2026-04-10T10:00:00Z"
}
```

---

#### `PATCH /api/route-plans/{id}`
**Purpose:** Update route plan status

**Request Body:**
```json
{
  "status": "confirmed",
  "notes": "Approved for execution"
}
```

---

### Ride Confirmation

#### `POST /api/ride-confirmation`
**Purpose:** Confirm or reject a ride request

**Request Body:**
```json
{
  "ride_request_id": "rr_001",
  "action": "confirm",  // "confirm" | "reject"
  "notes": "Optional confirmation notes"
}
```

**Response:**
```json
{
  "success": true,
  "ride_request_id": "rr_001",
  "status": "confirmed"
}
```

---

### Sandbox / IE Mode

#### `POST /api/sandbox/calculate`
**Purpose:** Calculate with custom vehicle configurations (IE Sandbox)

**Request Body:**
```json
{
  "students": [...],
  "vehicles": [
    {
      "vehicleId": "v1",
      "swCapacity": 4,
      "soCapacity": 5,
      "cooldownMinutes": 15
    }
  ],
  "algorithm": "ga_split"
}
```

**Response:** Same as `/api/optimize-route`

**Implementation:** `src/app/api/sandbox/route.ts`

---

### Admin Operations

#### `GET /api/admin/users`
**Purpose:** List all users (admin only)

**Authentication:** Admin required

**Query Parameters:**
- `role` (optional): "student" | "admin" | "driver"
- `limit` (optional): Number of results

**Response:**
```json
{
  "users": [
    {
      "id": "user_001",
      "email": "student@university.edu",
      "name": "Ahmet Yılmaz",
      "role": "student",
      "student_number": "2024001"
    }
  ],
  "total": 150
}
```

---

#### `POST /api/admin/users`
**Purpose:** Create new user (admin only)

**Request Body:**
```json
{
  "email": "student@university.edu",
  "name": "Ahmet Yılmaz",
  "role": "student",
  "student_number": "2024001",
  "disability_type": "Sw",
  "location_code": "K123"
}
```

---

#### `PATCH /api/admin/users/{id}`
**Purpose:** Update user info

**Request Body:**
```json
{
  "name": "New Name",
  "role": "admin",
  "disability_type": "So"
}
```

---

#### `DELETE /api/admin/users/{id}`
**Purpose:** Delete user (soft delete)

---

### Driver Operations

#### `GET /api/driver/assignments`
**Purpose:** Get driver's assigned routes

**Query Parameters:**
- `date` (optional): Filter by date
- `status` (optional): "scheduled" | "in_progress" | "completed"

**Response:**
```json
{
  "assignments": [
    {
      "id": "ra_001",
      "date": "2026-04-10",
      "vehicle_id": "v1",
      "route_id": "r_001",
      "student_ids": ["s1", "s2"],
      "pickup_time": "09:00",
      "estimated_dropoff_time": "16:00",
      "status": "scheduled"
    }
  ]
}
```

---

#### `PATCH /api/driver/assignments/{id}`
**Purpose:** Update assignment status

**Request Body:**
```json
{
  "status": "in_progress",
  "current_location": { "lat": 41.0082, "lng": 28.9784 },
  "notes": "Running 5 minutes late"
}
```

---

### Profile

#### `GET /api/profile`
**Purpose:** Get current user's profile

**Response:**
```json
{
  "id": "user_001",
  "email": "student@university.edu",
  "name": "Ahmet Yılmaz",
  "role": "student",
  "student_number": "2024001",
  "home_coordinates": { "lat": 41.0100, "lng": 28.9800 },
  "disability_type": "Sw",
  "location_code": "K123",
  "weekly_schedule": {
    "Monday": { "start": "09:00", "end": "16:30" },
    "Tuesday": { "start": "09:00", "end": "16:30" }
  }
}
```

---

#### `PATCH /api/profile`
**Purpose:** Update current user's profile

**Request Body:**
```json
{
  "name": "New Name",
  "home_coordinates": { "lat": 41.0100, "lng": 28.9800 },
  "disability_type": "So",
  "location_code": "K456",
  "weekly_schedule": {
    "Monday": { "start": "09:00", "end": "16:30" }
  }
}
```

---

### Authentication

#### `POST /api/auth/login`
**Purpose:** User login

**Request Body:**
```json
{
  "email": "student@university.edu",
  "password": "password123"
}
```

**Response:**
```json
{
  "user": {
    "id": "user_001",
    "email": "student@university.edu",
    "name": "Ahmet Yılmaz",
    "role": "student"
  },
  "session": {
    "access_token": "eyJhbGc...",
    "expires_in": 3600
  }
}
```

---

#### `POST /api/auth/logout`
**Purpose:** User logout

---

#### `GET /api/auth/session`
**Purpose:** Get current session info

**Response:**
```json
{
  "user": {...},
  "session": {...}
}
```

---

## Python FastAPI Endpoints (Backend)

### Core Endpoints

#### `GET /health`
**Purpose:** Health check

**Response:**
```json
{
  "status": "ok",
  "message": "UniRide Optimization Engine is running.",
  "version": "3.1.0",
  "features": ["CVRP", "CVRPTW", "Heterogeneous Fleet", "IE Resource Analysis"],
  "algorithms": ["genetic_algorithm", "pso", "gwo", "hho", ...]
}
```

---

#### `GET /api/v1/strategies`
**Purpose:** List all available optimization strategies

**Response:**
```json
[
  {
    "name": "ga_split",
    "display_name": "Genetic Algorithm with Split",
    "description": "Route-first approach using GA + optimal split decoder",
    "complexity": "O(generations × population × n²)",
    "recommended": true
  },
  {
    "name": "pso",
    "display_name": "Particle Swarm Optimization",
    "description": "Swarm intelligence metaheuristic",
    "complexity": "O(iterations × swarm × n²)",
    "recommended": true
  }
]
```

---

#### `POST /api/v1/optimize`
**Purpose:** Optimize routes with specified algorithm

**Request Body:**
```json
{
  "students": [
    {
      "id": "s1",
      "name": "Student 1",
      "location_code": "K123",
      "coordinates": { "lat": 41.0082, "lng": 28.9784 },
      "disability_type": "Sw",
      "pickup_time": "09:00",
      "dropoff_time": "16:00"
    }
  ],
  "vehicles": [
    {
      "vehicle_id": "v1",
      "sw_capacity": 4,
      "so_capacity": 5,
      "cooldown_minutes": 15
    }
  ],
  "optimizer_config": {
    "algorithm": "ga_split",
    "local_search_type": "two_opt",
    "use_time_windows": true,
    "direction": "pickup",
    "target_time": "09:00",
    "ga_config": {
      "population_size": 100,
      "max_iterations": 200
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "algorithm_used": "ga_split",
  "routes": [
    {
      "vehicle_id": "v1",
      "route_details": [...],
      "total_duration_minutes": 45,
      "total_distance_km": 28.5,
      "sw_count": 2,
      "so_count": 3,
      "student_ids": ["s1", "s2"],
      "departure_time": "09:00",
      "arrival_times": { "s1": "09:15", "s2": "09:42" },
      "time_window_violations": 0
    }
  ],
  "total_vehicles": 2,
  "total_duration_minutes": 45,
  "execution_time_seconds": 2.3,
  "ie_data": null
}
```

---

#### `POST /api/v1/compare`
**Purpose:** Compare multiple algorithms on same problem

**Request Body:**
```json
{
  "students": [...],
  "vehicles": [...],
  "optimizer_config": {
    "algorithms": ["ga_split", "pso_split", "gwo_split"],
    "direction": "pickup"
  }
}
```

**Response:**
```json
[
  {
    "algorithm": "ga_split",
    "success": true,
    "routes": [...],
    "execution_time_seconds": 2.3
  },
  {
    "algorithm": "pso_split",
    "success": true,
    "routes": [...],
    "execution_time_seconds": 1.9
  }
]
```

---

#### `POST /api/v1/extract-time-windows`
**Purpose:** Extract and validate time windows from weekly schedule

**Request Body:**
```json
{
  "weekly_schedule": {
    "Monday": { "start": "09:00", "end": "16:30" },
    "Tuesday": { "start": "09:00", "end": "16:30" }
  },
  "target_time": "09:00",
  "time_window_size": 30,
  "offset_minutes": 10,
  "direction": "pickup"
}
```

**Response:**
```json
{
  "time_windows": [
    {
      "day": "Monday",
      "earliest": 540,
      "latest": 570,
      "target": 555
    }
  ],
  "extraction_status": "success"
}
```

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 401 | Unauthorized (missing auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not found |
| 422 | Unprocessable entity (validation error) |
| 500 | Server error |

---

## Request/Response Timing

| Operation | Typical Duration |
|-----------|-----------------|
| Health check | < 10ms |
| List strategies | < 50ms |
| Small optimization (n=10) | 100-500ms |
| Medium optimization (n=30) | 500ms-2s |
| Large optimization (n=100) | 2-10s |
| Algorithm comparison | 5-30s (all algorithms) |

---

## Rate Limits (Planned)

Currently not enforced, but designed limit:
- **60 requests per minute** per API key

---

## Example Client Usage

### Using optimizer-service.ts (Recommended)
```typescript
import { optimizeRoutes } from "@/services/optimizer-service";

const result = await optimizeRoutes(students, depot, {
  algorithm: "ga_split",
  sw_capacity: 4,
  so_capacity: 5
});

console.log(`Total vehicles: ${result.total_vehicles}`);
console.log(`Execution time: ${result.execution_time_seconds}s`);
```

### Using Fetch Directly (Not Recommended)
```typescript
const response = await fetch("/api/optimize-route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    students: [...],
    depot: {...},
    algorithm: "ga_split"
  })
});

const result = await response.json();
```

### Using Python Requests
```python
import requests

response = requests.post(
  "http://127.0.0.1:8000/api/v1/optimize",
  json={
    "students": [...],
    "vehicles": [...],
    "optimizer_config": {
      "algorithm": "ga_split"
    }
  }
)

result = response.json()
print(f"Total vehicles: {result['total_vehicles']}")
```

---

**Last Updated:** April 10, 2026 | **UniRide API v3.1.0**
