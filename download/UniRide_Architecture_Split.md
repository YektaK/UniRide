# UniRide Hibrit Mimari Tasarımı

> **Sürüm:** 2.0 - Split Entegrasyonu  
> **Son Güncelleme:** 26 Mart 2026  
> **Durum:** Tasarım Aşaması

---

## 1. Mimari Özeti

UniRide, engelli öğrenci taşımacılığı için optimize edilmiş bir rota planlama sistemidir. Bu doküman, **Split entegrasyonu ile yeni hibrit mimariyi** açıklamaktadır.

### 1.1 Temel İlkeler

| İlke | Açıklama |
|------|----------|
| **Modülerlik** | Her algoritma bağımsız modül |
| **Genişletilebilirlik** | Yeni algoritma eklemek kolay |
| **Test Edilebilirlik** | Her bileşen izole test edilebilir |
| **Performans** | N≥300 öğrenci için optimize |

### 1.2 Mimari Diyagramı

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Admin     │  │  Driver     │  │  Student    │  │  Reports    │       │
│  │  Dashboard  │  │  Dashboard  │  │  Dashboard  │  │  Dashboard  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (Next.js API Routes)                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  /api/calculate-vehicles  →  Optimizer Service                      │   │
│  │  /api/route-plans         →  Route Plan CRUD                        │   │
│  │  /api/admin/*             →  Admin Operations                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PYTHON OPTIMIZER API                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         STRATEGY REGISTRY                            │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │GA-Split │ │PSO-Split│ │HHO-Split│ │GWO-Split│ │OR-Tools │       │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │   │
│  │       │           │           │           │           │             │   │
│  │       └───────────┴───────────┴───────────┴───────────┘             │   │
│  │                               │                                     │   │
│  │                               ▼                                     │   │
│  │                    ┌─────────────────┐                              │   │
│  │                    │  SPLIT DECODER  │  ← Optimal Route Split      │   │
│  │                    └─────────────────┘                              │   │
│  │                               │                                     │   │
│  │                               ▼                                     │   │
│  │                    ┌─────────────────┐                              │   │
│  │                    │  LOCAL SEARCH   │  ← 2-opt, Or-opt            │   │
│  │                    └─────────────────┘                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ Time Matrix │  │ Coordinates │  │   Students  │                  │   │
│  │  │   Loader    │  │   Loader    │  │   Loader    │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUPABASE (PostgreSQL)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   users     │  │   vehicles  │  │ route_plans │  │ time_matrix │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Bileşen Detayları

### 2.1 Strategy Pattern

Tüm optimizasyon algoritmaları **Strategy Pattern** ile tasarlanmıştır.

```python
# Base Strategy Interface
class BaseRoutingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Algorithm identifier"""
        pass
    
    @abstractmethod
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Main optimization method"""
        pass
```

#### Strategy Registry

```python
# optimizer_api/strategies/__init__.py
STRATEGY_REGISTRY = {
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    "hho": HarrisHawksOptimizerStrategy,
    "gwo": GreyWolfOptimizerStrategy,
    "ortools": ORToolsStrategy,
    # YENİ: Split tabanlı stratejiler
    "ga_split": GASplitStrategy,
    "pso_split": PSOSplitStrategy,
    "hho_split": HHOSplitStrategy,
    "gwo_split": GWOSplitStrategy,
}

def get_strategy(name: str) -> BaseRoutingStrategy:
    """Factory method for strategies"""
    return STRATEGY_REGISTRY.get(name, GeneticAlgorithmStrategy)()
```

### 2.2 Split Decoder

Split Decoder, giant tour'u optimal rotalara bölen kritik bileşendir.

```python
# optimizer_api/utils/split_decoder.py
class SplitDecoder:
    """
    Optimal split decoder using dynamic programming.
    
    Converts giant tour → multiple vehicle routes
    while respecting all constraints.
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
        giant_tour: List[str],      # Tüm öğrencilerin permütasyonu
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        student_data: Dict
    ) -> Tuple[List[List[str]], float]:
        """
        Decode giant tour into optimal routes.
        
        Returns:
            (routes, total_cost)
        """
        # DP implementation
        pass
```

#### Split Algoritması Akışı

```
Giant Tour: [3, 1, 4, 8, 2, 5, 7, 6, 9, 10]
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  DİNAMİK PROGRAMLAMA TABLOSU                │
├─────────────────────────────────────────────────────────────┤
│  i=0:                                                       │
│    j=0: [3]       → Sw=1, So=0, Time=15min → ✓ dp[1]=15    │
│    j=1: [3,1]     → Sw=1, So=1, Time=28min → ✓ dp[2]=28    │
│    j=2: [3,1,4]   → Sw=2, So=1, Time=42min → ✓ dp[3]=42    │
│    j=3: [3,1,4,8] → Sw=5, So=1 → ✗ Capacity exceeded!      │
│                                                             │
│  i=3:                                                       │
│    j=3: [8]       → Sw=1, So=0, Time=12min → ✓ dp[4]=54    │
│    j=4: [8,2]     → Sw=1, So=1, Time=25min → ✓ dp[5]=67    │
│    j=5: [8,2,5]   → Sw=1, So=2, Time=38min → ✓ dp[6]=80    │
│    ...                                                       │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
Route 1: [3, 1, 4]    → 42 dakika
Route 2: [8, 2, 5]    → 38 dakika
Route 3: [7, 6, 9, 10] → 55 dakika
Total: 135 dakika, 3 araç
```

### 2.3 Hybrid Base Strategy

Tüm Split tabanlı algoritmalar bu temel sınıftan türer.

```python
# optimizer_api/strategies/hybrid_base_strategy.py
class HybridSplitStrategy(BaseRoutingStrategy):
    """
    Base class for hybrid meta-heuristic + split algorithms.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__()
        self.config = config or {}
        self.split_decoder = None
    
    def _initialize_split_decoder(self, request):
        """Initialize split decoder with request constraints"""
        self.split_decoder = SplitDecoder(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time
        )
    
    def decode_tour(
        self, 
        giant_tour: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        student_data: Dict
    ) -> Tuple[List[List[str]], float]:
        """Decode giant tour using optimal split"""
        return self.split_decoder.decode(
            giant_tour, depot, time_matrix, 
            coordinates, student_data
        )
    
    @abstractmethod
    def _optimize_giant_tour(
        self, 
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        student_data: Dict
    ) -> List[str]:
        """
        Meta-heuristic optimization of giant tour.
        Subclasses implement this method.
        """
        pass
    
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Main optimization using hybrid approach"""
        # 1. Initialize
        self._initialize_split_decoder(request)
        
        # 2. Build data structures
        time_matrix, coordinates, student_data = self._build_data(request)
        
        # 3. Optimize giant tour (meta-heuristic)
        best_tour = self._optimize_giant_tour(...)
        
        # 4. Decode with split
        routes, total_cost = self.decode_tour(best_tour, ...)
        
        # 5. Apply local search (optional)
        routes = self._local_search(routes)
        
        # 6. Build response
        return self._build_response(routes, total_cost)
```

---

## 3. Algoritma Detayları

### 3.1 PSO-Split

```python
class PSOSplitStrategy(HybridSplitStrategy):
    """
    Particle Swarm Optimization with Optimal Split.
    
    Particle position = Giant tour (all students)
    Fitness = Split decoder → Total cost
    """
    
    DEFAULT_CONFIG = {
        "swarm_size": 30,
        "max_iterations": 100,
        "inertia_weight": 0.729,
        "cognitive_weight": 1.49445,
        "social_weight": 1.49445,
    }
    
    def _optimize_giant_tour(self, waypoints, depot, time_matrix, 
                             coordinates, student_data):
        # Initialize swarm
        swarm = self._initialize_swarm(waypoints)
        global_best = None
        global_best_cost = float('inf')
        
        for iteration in range(self.max_iterations):
            for particle in swarm:
                # Evaluate fitness using Split decoder
                _, cost = self.decode_tour(
                    particle.position, depot, 
                    time_matrix, coordinates, student_data
                )
                
                # Update personal/global best
                if cost < particle.personal_best_cost:
                    particle.personal_best = particle.position.copy()
                    particle.personal_best_cost = cost
                    
                    if cost < global_best_cost:
                        global_best = particle.position.copy()
                        global_best_cost = cost
                
                # Update velocity and position
                particle.velocity = self._update_velocity(
                    particle, global_best
                )
                particle.position = self._apply_velocity(
                    particle.position, particle.velocity
                )
        
        return global_best
```

### 3.2 HHO-Split

```python
class HHOSplitStrategy(HybridSplitStrategy):
    """
    Harris Hawks Optimization with Optimal Split.
    
    Hawk position = Giant tour
    Prey = Best solution
    Siege strategies based on escape energy
    """
    
    def _optimize_giant_tour(self, waypoints, depot, time_matrix,
                             coordinates, student_data):
        # Initialize hawks
        hawks = self._initialize_hawks(waypoints)
        prey = None  # Best solution
        
        for iteration in range(self.max_iterations):
            # Escape energy decreases over iterations
            E = 2 * E0 * (1 - iteration / self.max_iterations)
            
            for hawk in hawks:
                # Evaluate fitness
                _, cost = self.decode_tour(hawk.position, ...)
                
                if cost < prey_cost:
                    prey = hawk.position.copy()
                    prey_cost = cost
                
                # Select siege strategy based on E and r
                if abs(E) >= 1:
                    # Exploration: random perching
                    new_position = self._explore(hawk, prey)
                else:
                    # Exploitation: siege
                    if r < 0.5:
                        new_position = self._soft_besiege(hawk, prey, E)
                    else:
                        new_position = self._hard_besiege_with_dives(hawk, prey, E)
                
                hawk.position = new_position
        
        return prey
```

### 3.3 GWO-Split

```python
class GWOSplitStrategy(HybridSplitStrategy):
    """
    Grey Wolf Optimizer with Optimal Split.
    
    Wolf position = Giant tour
    Alpha, Beta, Delta = Top 3 solutions
    Omega = Rest of pack
    """
    
    def _optimize_giant_tour(self, waypoints, depot, time_matrix,
                             coordinates, student_data):
        # Initialize pack
        pack = self._initialize_pack(waypoints)
        
        # Identify hierarchy
        pack.sort(key=lambda w: self._evaluate(w))
        alpha, beta, delta = pack[0], pack[1], pack[2]
        
        for iteration in range(self.max_iterations):
            # Parameter 'a' decreases linearly
            a = 2.0 * (1 - iteration / self.max_iterations)
            
            for wolf in pack:
                # Update position toward leaders
                new_position = self._update_position(
                    wolf, alpha, beta, delta, a
                )
                
                # Evaluate
                _, cost = self.decode_tour(new_position, ...)
                wolf.position = new_position
                wolf.cost = cost
            
            # Update hierarchy
            pack.sort(key=lambda w: w.cost)
            alpha, beta, delta = pack[0], pack[1], pack[2]
        
        return alpha.position
```

---

## 4. Veri Akışı

### 4.1 Request/Response Modeli

```python
# Request
class OptimizationRequest(BaseModel):
    students: List[StudentNode]
    depot: DepotNode
    sw_capacity: int = 4
    so_capacity: int = 5
    max_travel_time: float = 180.0
    algorithm: str = "pso_split"
    
    class StudentNode(BaseModel):
        id: str
        name: str
        location_code: str
        coordinates: Optional[Dict]
        disability_type: str  # 'Sw' or 'So'
    
    class DepotNode(BaseModel):
        id: str
        lat: float
        lng: float

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

### 4.2 Veri Akış Diyagramı

```
┌──────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend                                                        │
│      │                                                           │
│      │ POST /api/calculate-vehicles                             │
│      │ { students[], algorithm: "pso_split" }                   │
│      ▼                                                           │
│  Next.js API Route                                               │
│      │                                                           │
│      │ HTTP POST to Python API                                  │
│      ▼                                                           │
│  Python Optimizer API                                            │
│      │                                                           │
│      ├─→ DataLoader.get_instance()                              │
│      │       │                                                   │
│      │       ├─→ time_matrix (from Supabase)                    │
│      │       └─→ coordinates                                     │
│      │                                                           │
│      ├─→ StrategyFactory.get("pso_split")                       │
│      │       │                                                   │
│      │       └─→ PSOSplitStrategy()                             │
│      │               │                                           │
│      │               ├─→ Initialize swarm (giant tours)         │
│      │               ├─→ For each particle:                     │
│      │               │       └─→ SplitDecoder.decode()          │
│      │               │               └─→ DP calculation         │
│      │               └─→ Return best tour + routes              │
│      │                                                           │
│      └─→ OptimizationResponse                                   │
│              │                                                   │
│              │ JSON Response                                    │
│              ▼                                                   │
│  Next.js API Route                                               │
│      │                                                           │
│      │ Transform to UI format                                   │
│      ▼                                                           │
│  Frontend                                                        │
│      │                                                           │
│      └─→ Display routes, metrics                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Performans Optimizasyonları

### 5.1 Caching

```python
# DataLoader Singleton
class DataLoader:
    _instance = None
    _time_matrix_cache = None
    _coordinates_cache = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_time_matrix(self):
        if self._time_matrix_cache is None:
            self._time_matrix_cache = self._load_from_supabase()
        return self._time_matrix_cache
```

### 5.2 Parallel Evaluation

```python
from concurrent.futures import ThreadPoolExecutor

class PSOSplitStrategy:
    def _evaluate_swarm_parallel(self, swarm, depot, time_matrix, 
                                  coordinates, student_data):
        """Evaluate all particles in parallel"""
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
        
        for particle, (routes, cost) in zip(swarm, results):
            particle.current_cost = cost
```

### 5.3 Early Termination

```python
class HybridSplitStrategy:
    def optimize(self, request):
        # ...
        no_improvement = 0
        best_cost = float('inf')
        
        for iteration in range(max_iterations):
            # ...
            if current_cost < best_cost:
                best_cost = current_cost
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= max_no_improvement:
                break  # Early termination
```

---

## 6. Hata Yönetimi

### 6.1 Constraint Violation

```python
class SplitDecoder:
    def decode(self, giant_tour, ...):
        # ... DP calculation
        
        # Check if solution is complete
        if dp[n] == float('inf'):
            # No feasible solution found
            # Fallback: force split with penalty
            return self._fallback_split(giant_tour)
```

### 6.2 Empty/Invalid Input

```python
class HybridSplitStrategy:
    def optimize(self, request):
        if not request.students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                total_duration_minutes=0
            )
```

---

## 7. Test Stratejisi

### 7.1 Unit Tests

```python
# tests/test_split_decoder.py
def test_split_single_route():
    """Single student should create single route"""
    tour = ["LOC1"]
    routes, cost = decoder.decode(tour, "DEPOT", time_matrix, ...)
    assert len(routes) == 1
    assert routes[0] == ["LOC1"]

def test_split_capacity_constraint():
    """Should not exceed capacity"""
    tour = ["SW1", "SW2", "SW3", "SW4", "SW5"]  # 5 wheelchair
    routes, cost = decoder.decode(tour, ...)
    # Should split because max 4 Sw
    assert len(routes) >= 2

def test_split_time_constraint():
    """Should respect max tour time"""
    # ... test with long duration locations
```

### 7.2 Integration Tests

```python
# tests/test_pso_split.py
def test_pso_split_optimize():
    """Full optimization pipeline"""
    request = OptimizationRequest(
        students=[...],
        depot=DepotNode(...),
        algorithm="pso_split"
    )
    
    strategy = PSOSplitStrategy()
    response = strategy.optimize(request)
    
    assert response.success
    assert response.total_vehicles > 0
    assert all(r.sw_count <= 4 for r in response.routes)
    assert all(r.so_count <= 5 for r in response.routes)
```

### 7.3 Benchmark Tests

```python
# tests/benchmark.py
@pytest.mark.parametrize("n_students", [30, 100, 300])
@pytest.mark.parametrize("algorithm", ["ga_split", "pso_split", "hho_split"])
def test_benchmark(n_students, algorithm):
    students = generate_random_students(n_students)
    
    start = time.time()
    response = optimize(students, algorithm)
    duration = time.time() - start
    
    print(f"{algorithm} @ N={n_students}: {duration:.2f}s, "
          f"vehicles={response.total_vehicles}")
```

---

## 8. Deployment

### 8.1 Docker Configuration

```dockerfile
# Dockerfile.optimizer
FROM python:3.11-slim

WORKDIR /app

COPY optimizer_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY optimizer_api/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 Environment Variables

```bash
# .env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
PYTHON_API_URL=http://localhost:8000
```

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
