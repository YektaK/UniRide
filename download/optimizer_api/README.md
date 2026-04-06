# UniRide Optimizer API

Python FastAPI tabanlı araç rotalama optimizasyon servisi.

## 🚀 Özellikler

- **Genetik Algoritma (GA)**: Popülasyon tabanlı meta-sezgisel optimizasyon
- **PSO**: Parçacık Sürü Optimizasyonu
- **Greedy Heuristic**: Hızlı en yakın komşu algoritması
- **Permutation TSP**: Optimal çözüm (n ≤ 10 için)
- **OR-Tools CVRP**: Google OR-Tools entegrasyonu

## 📁 Proje Yapısı

```
optimizer_api/
├── main.py                      # FastAPI ana dosyası
├── requirements.txt             # Python bağımlılıkları
├── models/
│   └── schemas.py              # Pydantic veri modelleri
├── strategies/
│   ├── __init__.py             # Strateji registry
│   ├── base_strategy.py        # Abstract base sınıf
│   ├── ga_strategy.py          # Genetik Algoritma
│   ├── pso_strategy.py         # PSO
│   ├── greedy_heuristic.py     # Greedy Heuristic
│   ├── permutation_tsp.py      # Permutation TSP
│   └── ortools_cvrp.py         # OR-Tools CVRP
├── utils/
│   ├── data_loader.py          # Supabase time matrix loader
│   └── clustering.py           # K-Means clustering + Vehicle Calculator
└── test_strategies.py          # Test suite
```

## 🔧 Kurulum

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Environment variables (.env)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...

# Sunucuyu başlat
python main.py
# veya
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Endpoints

### `GET /health`
Sağlık kontrolü.

### `GET /api/v1/strategies`
Kullanılabilir algoritmaları listeler.

### `POST /api/v1/optimize`
Tek bir algoritma ile optimizasyon.

**Request:**
```json
{
  "algorithm": "genetic_algorithm",
  "students": [
    {
      "id": "s1",
      "name": "Öğrenci 1",
      "location_code": "Sw1",
      "coordinates": {"lat": 40.8412, "lng": 31.1456},
      "disability_type": "Sw"
    }
  ],
  "depot": {
    "id": "D.Kampus",
    "lat": 40.8410,
    "lng": 31.1478,
    "type": "depot"
  },
  "max_travel_time": 120,
  "sw_capacity": 4,
  "so_capacity": 5,
  "ga_config": {
    "population_size": 50,
    "max_iterations": 100
  }
}
```

**Response:**
```json
{
  "algorithm_used": "genetic_algorithm",
  "success": true,
  "routes": [
    {
      "vehicle_id": "Araç 1 (GA)",
      "route_details": [
        {"location1": "D.Kampus", "location2": "Sw1", "duration": 12.5, "distance": 0}
      ],
      "total_duration_minutes": 45.2,
      "sw_count": 2,
      "so_count": 3,
      "student_ids": ["s1", "s2", "s3", "s4", "s5"]
    }
  ],
  "total_vehicles": 2,
  "total_duration_minutes": 85.4,
  "execution_time_seconds": 0.234
}
```

### `POST /api/v1/compare`
Tüm algoritmaları karşılaştır.

**Request:**
```json
{
  "students": [...],
  "depot": {...},
  "algorithms": ["genetic_algorithm", "pso", "greedy"]
}
```

**Response:**
```json
{
  "success": true,
  "results": [...],
  "best_algorithm": "genetic_algorithm",
  "fastest_algorithm": "greedy",
  "summary": {
    "genetic_algorithm": {"total_vehicles": 2, "total_duration_minutes": 85.4, "execution_time_seconds": 0.234},
    "pso": {"total_vehicles": 2, "total_duration_minutes": 87.1, "execution_time_seconds": 0.189},
    "greedy": {"total_vehicles": 3, "total_duration_minutes": 102.3, "execution_time_seconds": 0.001}
  }
}
```

## 🧪 Test

```bash
python test_strategies.py
```

## 📊 Algoritmalar

| Algoritma | Karmaşıklık | Kullanım |
|-----------|-------------|----------|
| Genetic Algorithm | O(g × p × n²) | Büyük problemler |
| PSO | O(i × s × n²) | Hızlı yakınsama |
| Greedy | O(n²) | Hızlı çözüm |
| Permutation TSP | O(n!) | n ≤ 10 optimal |
| OR-Tools CVRP | O(n³) | Endüstri standardı |

## 🔗 Next.js Entegrasyonu

`optimizer-service.ts` dosyasını Next.js projenize kopyalayın:

```typescript
import { optimizeRoutes, compareAllAlgorithms } from "@/services/optimizer-service";

// Tek algoritma
const result = await optimizeRoutes(students, depot, {
    algorithm: "genetic_algorithm",
    max_travel_time: 120
});

// Karşılaştır
const comparison = await compareAllAlgorithms(students, depot);
console.log("En iyi:", comparison.best_algorithm);
```

## ⚙️ Yapılandırma

### GA Parametreleri
- `population_size`: 50 (popülasyon boyutu)
- `max_iterations`: 100 (maksimum iterasyon)
- `crossover_rate`: 0.85 (çaprazlama oranı)
- `mutation_rate`: 0.15 (mutasyon oranı)
- `elite_count`: 2 (elit birey sayısı)
- `tournament_size`: 3 (turnuva boyutu)

### PSO Parametreleri
- `swarm_size`: 30 (sürü boyutu)
- `max_iterations`: 100
- `inertia_weight`: 0.729 (Clerc's constriction)
- `cognitive_weight`: 1.49445
- `social_weight`: 1.49445

## 📝 Lisans

Bu proje sosyal sorumluluk projesi olarak geliştirilmiştir.
