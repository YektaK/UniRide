# UniRide Sistem Mimarisi

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Sürüm:** 2.0 - Split Entegrasyonu  
> **Tarih:** 26 Mart 2026

---

## 1. Mimari Özeti

UniRide, üç katmanlı bir mimari kullanmaktadır:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                │
│                              (Next.js 15)                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Admin     │  │   Driver    │  │   Student   │  │   Reports   │       │
│  │  Dashboard  │  │  Dashboard  │  │  Dashboard  │  │  Dashboard  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
│                         (Next.js API Routes)                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  /api/calculate-vehicles  →  Python Optimizer                        │  │
│  │  /api/route-plans         →  Route Plan CRUD                         │  │
│  │  /api/admin/*             →  Admin Operations                        │  │
│  │  /api/driver/*            →  Driver Operations                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPTIMIZATION LAYER                                 │
│                           (Python FastAPI)                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        STRATEGY REGISTRY                               │  │
│  │                                                                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │ GA-Split │ │PSO-Split │ │HHO-Split │ │GWO-Split │ │ OR-Tools │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  │       └────────────┴────────────┴────────────┴────────────┘          │  │
│  │                                │                                      │  │
│  │                                ▼                                      │  │
│  │                    ┌─────────────────────┐                            │  │
│  │                    │   SPLIT DECODER     │  ← Optimal Route Split    │  │
│  │                    └─────────────────────┘                            │  │
│  │                                │                                      │  │
│  │                                ▼                                      │  │
│  │                    ┌─────────────────────┐                            │  │
│  │                    │   LOCAL SEARCH      │  ← 2-opt, Or-opt          │  │
│  │                    └─────────────────────┘                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                          DATA LAYER                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │ Time Matrix  │  │  Coordinates │  │   Students   │                 │  │
│  │  │    Loader    │  │    Loader    │  │    Loader    │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA STORAGE                                       │
│                           (Supabase/PostgreSQL)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    users     │  │   vehicles   │  │ route_plans  │  │ time_matrix  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Bileşen Detayları

### 2.1 Presentation Layer (Next.js 15)

| Bileşen | Teknoloji | Açıklama |
|---------|-----------|----------|
| Admin Dashboard | React + shadcn/ui | Rota planlama, kullanıcı yönetimi |
| Driver Dashboard | React + shadcn/ui | Günlük rotalar, navigasyon |
| Student Dashboard | React + shadcn/ui | Sefer takibi, talep oluşturma |
| Reports | React + Chart.js | Performans metrikleri |

### 2.2 API Layer (Next.js API Routes)

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/calculate-vehicles` | POST | Rota optimizasyonu |
| `/api/route-plans` | GET/POST | Rota planı CRUD |
| `/api/admin/users` | GET/POST/PUT | Kullanıcı yönetimi |
| `/api/admin/vehicles` | GET/POST/PUT | Araç yönetimi |
| `/api/driver/assignments` | GET | Sürücü atamaları |

### 2.3 Optimization Layer (Python FastAPI)

**Strateji Pattern:**

```python
# Tüm algoritmalar bu arayüzü uygular
class BaseRoutingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        pass
```

---

## 3. Split Decoder Mimarisi

### 3.1 Temel Yapı

```python
class SplitDecoder:
    """
    Giant Tour → Optimal Routes dönüşümü
    
    Dinamik programlama kullanarak:
    - Tüm olası bölünmeleri değerlendirir
    - Capacity constraints entegre
    - Time matrix duyarlı
    """
    
    def __init__(
        self,
        sw_capacity: int = 4,      # Wheelchair capacity
        so_capacity: int = 5,      # Other capacity
        max_tour_time: float = 180.0,
        max_student_time: float = 120.0
    ):
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
        self.max_tour_time = max_tour_time
        self.max_student_time = max_student_time
    
    def decode(
        self,
        giant_tour: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        student_data: Dict
    ) -> Tuple[List[List[str]], float]:
        """
        Giant tour'u optimal rotalara böl
        
        Returns:
            (routes, total_cost)
        """
        pass
```

### 3.2 Algoritma Akışı

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SPLIT DECODER AKIŞI                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Input: Giant Tour [3,1,4,8,2,5,7,6,9,10]                          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              DİNAMİK PROGRAMLAMA TABLOSU                    │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │                                                             │    │
│  │  dp[0] = 0                                                  │    │
│  │                                                             │    │
│  │  i=0:                                                       │    │
│  │    j=0: [3]     Sw=1, So=0, Time=12dk  ✓ dp[1]=12         │    │
│  │    j=1: [3,1]   Sw=1, So=1, Time=25dk  ✓ dp[2]=25         │    │
│  │    j=2: [3,1,4] Sw=2, So=1, Time=42dk  ✓ dp[3]=42         │    │
│  │    j=3: [3,1,4,8] Sw=5  → ✗ Capacity exceeded!            │    │
│  │                                                             │    │
│  │  i=3: (8'den başla)                                        │    │
│  │    j=3: [8]     Sw=1, So=0, Time=10dk  ✓ dp[4]=52         │    │
│  │    j=4: [8,2]   Sw=1, So=1, Time=22dk  ✓ dp[5]=64         │    │
│  │    j=5: [8,2,5] Sw=1, So=2, Time=38dk  ✓ dp[6]=80         │    │
│  │    ...                                                       │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Output:                                                           │
│    Rota 1: [3,1,4]    → 42 dk                                      │
│    Rota 2: [8,2,5]    → 38 dk                                      │
│    Rota 3: [7,6,9,10] → 55 dk                                      │
│    Toplam: 135 dk, 3 araç                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Hibrit Strateji Mimarisi

### 4.1 Base Class

```python
class HybridSplitStrategy(BaseRoutingStrategy):
    """
    Tüm Split tabanlı algoritmalar için temel sınıf
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.split_decoder = None
    
    def _initialize_split_decoder(self, request):
        self.split_decoder = SplitDecoder(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time
        )
    
    def decode_tour(self, giant_tour, depot, time_matrix, 
                    coordinates, student_data):
        return self.split_decoder.decode(
            giant_tour, depot, time_matrix, 
            coordinates, student_data
        )
    
    @abstractmethod
    def _optimize_giant_tour(self, waypoints, depot, 
                             time_matrix, coordinates, student_data):
        """Alt sınıflar implement eder"""
        pass
    
    def optimize(self, request):
        # 1. Initialize
        self._initialize_split_decoder(request)
        
        # 2. Build data
        time_matrix, coordinates, student_data = self._build_data(request)
        
        # 3. Optimize giant tour
        best_tour = self._optimize_giant_tour(...)
        
        # 4. Split decode
        routes, cost = self.decode_tour(best_tour, ...)
        
        # 5. Response
        return self._build_response(routes, cost)
```

### 4.2 PSO-Split Örnek

```python
class PSOSplitStrategy(HybridSplitStrategy):
    """
    Particle Swarm Optimization + Split
    """
    
    @property
    def name(self) -> str:
        return "pso_split"
    
    def _optimize_giant_tour(self, waypoints, depot, 
                             time_matrix, coordinates, student_data):
        # Swarm başlat
        swarm = self._initialize_swarm(waypoints)
        global_best = None
        global_best_cost = float('inf')
        
        for iteration in range(self.max_iterations):
            for particle in swarm:
                # Split decoder ile değerlendir
                _, cost = self.decode_tour(
                    particle.position, depot,
                    time_matrix, coordinates, student_data
                )
                
                # Update bests
                if cost < particle.personal_best_cost:
                    particle.personal_best = particle.position.copy()
                    particle.personal_best_cost = cost
                    
                    if cost < global_best_cost:
                        global_best = particle.position.copy()
                        global_best_cost = cost
                
                # Velocity ve position güncelle
                particle.velocity = self._update_velocity(
                    particle, global_best
                )
                particle.position = self._apply_velocity(
                    particle.position, particle.velocity
                )
        
        return global_best
```

---

## 5. Veri Akışı

### 5.1 Optimizasyon Request Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Frontend                                                         │
│     │                                                                │
│     │ POST /api/calculate-vehicles                                  │
│     │ { students: [...], algorithm: "pso_split" }                   │
│     ▼                                                                │
│                                                                      │
│  2. Next.js API Route                                                │
│     │                                                                │
│     │ HTTP POST → Python API                                        │
│     ▼                                                                │
│                                                                      │
│  3. Python Optimizer                                                 │
│     │                                                                │
│     ├─→ DataLoader.get_instance()                                   │
│     │       ├─→ time_matrix (Supabase)                              │
│     │       └─→ coordinates                                          │
│     │                                                                │
│     ├─→ StrategyFactory.get("pso_split")                            │
│     │       └─→ PSOSplitStrategy()                                  │
│     │               ├─→ Initialize swarm (giant tours)              │
│     │               ├─→ For each particle:                          │
│     │               │       └─→ SplitDecoder.decode()               │
│     │               └─→ Return best tour + routes                   │
│     │                                                                │
│     └─→ OptimizationResponse                                        │
│             │                                                        │
│             │ JSON Response                                         │
│             ▼                                                        │
│                                                                      │
│  4. Next.js API Route                                                │
│     │                                                                │
│     │ Transform to UI format                                        │
│     ▼                                                                │
│                                                                      │
│  5. Frontend                                                         │
│     │                                                                │
│     └─→ Display routes, metrics                                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Request/Response Modelleri

```python
# Request
class OptimizationRequest(BaseModel):
    algorithm: str = "pso_split"
    students: List[StudentNode]
    depot: LocationNode
    max_travel_time: int = 180
    sw_capacity: int = 4
    so_capacity: int = 5
    
    class StudentNode(BaseModel):
        id: str
        name: str
        location_code: str
        coordinates: Optional[Dict]
        disability_type: str  # 'Sw' or 'So'

# Response
class OptimizationResponse(BaseModel):
    algorithm_used: str
    success: bool
    routes: List[VehicleRoute]
    total_vehicles: int
    total_duration_minutes: float
    execution_time_seconds: float
    
    class VehicleRoute(BaseModel):
        vehicle_id: str
        route_details: List[RouteStep]
        total_duration_minutes: float
        sw_count: int
        so_count: int
        student_ids: List[str]
```

---

## 6. Dosya Yapısı

### 6.1 Mevcut Yapı

```
optimizer_api/
├── main.py                          # FastAPI entry point
├── requirements.txt                 # Python dependencies
├── models/
│   └── schemas.py                   # Pydantic models
├── strategies/
│   ├── __init__.py                  # Strategy registry
│   ├── base_strategy.py             # Abstract base class
│   ├── ga_strategy.py               # Genetic Algorithm
│   ├── pso_strategy.py              # Particle Swarm
│   ├── hho_strategy.py              # Harris Hawks
│   ├── gwo_strategy.py              # Grey Wolf
│   ├── ortools_cvrp.py              # OR-Tools
│   └── ...
└── utils/
    ├── data_loader.py               # Time matrix loader
    ├── clustering.py                # K-Means (eski)
    └── local_search.py              # 2-opt, Or-opt
```

### 6.2 Hedef Yapı (Split Sonrası)

```
optimizer_api/
├── main.py
├── requirements.txt
├── models/
│   └── schemas.py
├── strategies/
│   ├── __init__.py                  # Updated registry
│   ├── base_strategy.py
│   ├── hybrid_base_strategy.py      # YENİ: Split base class
│   │
│   # Mevcut (opsiyonel)
│   ├── ga_strategy.py
│   ├── pso_strategy.py
│   ├── hho_strategy.py
│   ├── gwo_strategy.py
│   │
│   # YENİ: Split tabanlı
│   ├── ga_split_strategy.py
│   ├── pso_split_strategy.py
│   ├── hho_split_strategy.py
│   ├── gwo_split_strategy.py
│   │
│   └── ortools_cvrp.py
│
└── utils/
    ├── data_loader.py
    ├── clustering.py               # Opsiyonel kalır
    ├── split_decoder.py            # YENİ
    └── local_search.py             # YENİ/Genişletilmiş
```

---

## 7. Performans Optimizasyonları

### 7.1 Singleton Pattern (DataLoader)

```python
class DataLoader:
    _instance = None
    _time_matrix_cache = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

### 7.2 Parallel Evaluation

```python
from concurrent.futures import ThreadPoolExecutor

def _evaluate_swarm_parallel(self, swarm, ...):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                self.decode_tour, 
                p.position, depot, time_matrix, 
                coordinates, student_data
            )
            for p in swarm
        ]
        results = [f.result() for f in futures]
```

### 7.3 Early Termination

```python
no_improvement = 0
best_cost = float('inf')

for iteration in range(max_iterations):
    # ...
    if current_cost < best_cost:
        best_cost = current_cost
        no_improvement = 0
    else:
        no_improvement += 1
    
    if no_improvement >= MAX_NO_IMPROVEMENT:
        break  # Early termination
```

---

## 8. Hata Yönetimi

### 8.1 Constraint Violation

```python
def decode(self, giant_tour, ...):
    # DP calculation
    # ...
    
    if dp[n] == float('inf'):
        # No feasible solution - fallback
        return self._fallback_split(giant_tour)
```

### 8.2 Empty Input

```python
def optimize(self, request):
    if not request.students:
        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=[],
            total_vehicles=0
        )
```

---

## 9. Deployment

### 9.1 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY optimizer_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY optimizer_api/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.2 Environment Variables

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx
PYTHON_API_URL=http://localhost:8000
```

---

## 10. Test Stratejisi

### 10.1 Unit Tests

```python
# tests/test_split_decoder.py
def test_single_student():
    tour = ["LOC1"]
    routes, cost = decoder.decode(tour, ...)
    assert len(routes) == 1

def test_capacity_constraint():
    tour = ["SW1", "SW2", "SW3", "SW4", "SW5"]  # 5 Sw
    routes, cost = decoder.decode(tour, ...)
    assert len(routes) >= 2  # Must split

def test_time_constraint():
    # Test with long duration locations
    pass
```

### 10.2 Integration Tests

```python
def test_pso_split_optimize():
    request = OptimizationRequest(
        students=[...],
        depot=DepotNode(...),
        algorithm="pso_split"
    )
    
    strategy = PSOSplitStrategy()
    response = strategy.optimize(request)
    
    assert response.success
    assert all(r.sw_count <= 4 for r in response.routes)
    assert all(r.so_count <= 5 for r in response.routes)
```

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
