# TSP Benchmark Studio Integration - Quick Reference

## 🚀 Quick Start

### 1. Start a Benchmark

**Frontend (TypeScript):**
```typescript
// Option A: Using fetch
const response = await fetch('/api/benchmark/run', {
  method: 'POST',
  body: JSON.stringify({
    algorithms: [
      { id: 'genetic_algorithm', params: {} },
      { id: 'pso', params: {} }
    ],
    problems: ['tsp_50_1', 'tsp_100_1'],
    settings: { nRuns: 3, workers: 4, seed: 42 }
  })
});

const { runId, totalExperiments } = await response.json();
console.log(`Benchmark started: ${runId}`);
```

**Python (FastAPI):**
```python
import requests

response = requests.post('http://localhost:8000/api/v1/benchmark/run', json={
    'run_id': 'my_benchmark_run',
    'algorithms': [{'id': 'genetic_algorithm'}, {'id': 'pso'}],
    'problems': ['tsp_50_1', 'tsp_100_1'],
    'settings': {'n_runs': 3, 'workers': 4, 'seed': 42}
})

run_id = response.json()['run_id']
```

### 2. Monitor Progress

**Frontend:**
```typescript
// Poll every 2 seconds
const status = async () => {
  const res = await fetch(`/api/benchmark/run/status?runId=${runId}`);
  const data = await res.json();
  console.log(`Progress: ${data.progress.percentCompleted}%`);
  console.log(`Status: ${data.status}`);
  return data;
};
```

**Python:**
```python
import time

while True:
    status = requests.get(
        f'http://localhost:8000/api/v1/benchmark/status',
        params={'run_id': run_id}
    ).json()
    
    print(f"Progress: {status['progress_percent']:.1f}%")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(2)
```

### 3. Stop Benchmark (if needed)

**Frontend:**
```typescript
await fetch('/api/benchmark/run/stop', {
  method: 'POST',
  body: JSON.stringify({ runId })
});
```

**Python:**
```python
requests.post(
    'http://localhost:8000/api/v1/benchmark/stop',
    json={'run_id': run_id}
)
```

---

## 📝 Available Algorithms

| Algorithm | ID | Category | Speed | Quality |
|-----------|----|-----------| ------|---------|
| Genetic Algorithm | `genetic_algorithm` | Meta-heuristic | Medium | High |
| PSO | `pso` | Meta-heuristic | Medium | High |
| Grey Wolf | `gwo` | Meta-heuristic | Medium | High |
| Harris Hawks | `hho` | Meta-heuristic | Slow | Very High |
| GA + Split | `ga_split` | Split-based | Faster | Very High |
| PSO + Split | `pso_split` | Split-based | Faster | Very High |
| GWO + Split | `gwo_split` | Split-based | Faster | Very High |
| HHO + Split | `hho_split` | Split-based | Faster | Very High |
| OR-Tools | `ortools_cvrp` | Exact/Heuristic | Very Fast | Medium |
| Two-Opt | `two_opt` | Local Search | Very Fast | Low |
| Greedy | `greedy` | Heuristic | Very Fast | Low |
| Permutation | `permutation_tsp` | Exact | Slow (n≤10) | Optimal |

---

## 📊 Problem Definition

### TSPLIB Format

Problems should have coordinates. When creating `BenchmarkProblem`:

```python
from optimizer_api.benchmark_runner import BenchmarkProblem

problem = BenchmarkProblem(
    name="tsp_50_1",           # Unique name
    dimension=50,              # Number of customers
    coordinates=[              # List of (x, y) tuples
        (0.0, 0.0),
        (1.5, 2.3),
        (5.1, 3.2),
        # ... 50 total
    ],
    optimal_score=1234,        # Optional: known optimal tour length
    category="small"           # small (n≤100), medium (n≤500), large (n>500)
)
```

---

## 📈 Response Format

### Benchmark Start Response
```json
{
  "runId": "benchmark_20260410_144734_abc123",
  "totalExperiments": 12,
  "problemsCount": 2,
  "algorithmsCount": 3,
  "nRuns": 2,
  "status": "running",
  "message": "Benchmark başlatıldı",
  "startTime": "2026-04-10T14:47:34Z"
}
```

### Status Response
```json
{
  "runId": "benchmark_20260410_144734_abc123",
  "status": "running|completed|failed|stopped",
  "totalExperiments": 12,
  "completedExperiments": 8,
  "resultsCount": 8,
  "progress_percent": 66.7,
  "message": "8/12 experiment tamamlandı",
  "startTime": "2026-04-10T14:47:34Z",
  "endTime": null
}
```

### Stop Response
```json
{
  "runId": "benchmark_20260410_144734_abc123",
  "status": "stopped",
  "resultsCollected": 8,
  "message": "Benchmark durduruldu"
}
```

---

## 🔧 Configuration

### Request Settings

```typescript
settings: {
  nRuns: 3,           // Number of runs per algorithm-problem pair (1-10)
  workers: 4,         // Parallel worker threads (1-8)
  seed: 42,           // Random seed for reproducibility
  skipCached: false   // Whether to skip previously cached results
}
```

### Algorithm Parameters (Optional)

Pass algorithm-specific parameters:

```typescript
algorithms: [
  {
    id: 'genetic_algorithm',
    params: {
      population_size: 100,
      max_iterations: 500,
      crossover_rate: 0.85,
      mutation_rate: 0.15
    }
  }
]
```

---

## 🎯 Example Workflows

### Workflow 1: Quick Comparison

Compare 3 algorithms on 1 problem, 1 run each:

```typescript
const result = await fetch('/api/benchmark/run', {
  method: 'POST',
  body: JSON.stringify({
    algorithms: [
      { id: 'genetic_algorithm' },
      { id: 'pso' },
      { id: 'ortools_cvrp' }
    ],
    problems: ['tsp_50_1'],
    settings: { nRuns: 1, workers: 3, seed: 123 }
  })
});
// ~3 experiments, takes ~10-30 seconds
```

### Workflow 2: Statistical Significance

Compare 2 algorithms on 5 problems, 5 runs each (to reduce variance):

```typescript
const result = await fetch('/api/benchmark/run', {
  method: 'POST',
  body: JSON.stringify({
    algorithms: [
      { id: 'genetic_algorithm' },
      { id: 'ga_split' }
    ],
    problems: [
      'tsp_50_1', 'tsp_50_2', 'tsp_100_1', 'tsp_100_2', 'tsp_150_1'
    ],
    settings: { nRuns: 5, workers: 4, seed: 456 }
  })
});
// 50 experiments, takes ~5-10 minutes
```

### Workflow 3: Parameter Tuning

Test different population sizes for GA:

```typescript
// Manual loop - could be automated
for (const popSize of [25, 50, 100, 200]) {
  await fetch('/api/benchmark/run', {
    method: 'POST',
    body: JSON.stringify({
      algorithms: [
        { id: 'genetic_algorithm', params: { population_size: popSize } }
      ],
      problems: ['tsp_100_1', 'tsp_100_2', 'tsp_100_3'],
      settings: { nRuns: 3, workers: 1, seed: 789 }
    })
  });
}
// 36 experiments across 4 parameter values
```

---

## 📍 API Endpoints Reference

### Frontend URLs (Next.js)

```
POST   http://localhost:9002/api/benchmark/run
GET    http://localhost:9002/api/benchmark/run/status?runId=...
POST   http://localhost:9002/api/benchmark/run/stop
```

### Backend URLs (Python)

```
POST   http://localhost:8000/api/v1/benchmark/run
GET    http://localhost:8000/api/v1/benchmark/status?run_id=...
POST   http://localhost:8000/api/v1/benchmark/stop
```

---

## 🐛 Troubleshooting

### Problem: "Benchmark servisine bağlanılamadı"
**Solution:** Ensure Python backend is running on port 8000
```bash
cd optimizer_api
python main.py
```

### Problem: "En az bir algoritma seçilmelidir"
**Solution:** Check that algorithms array is not empty
```typescript
algorithms: [{ id: 'genetic_algorithm' }]  // ✅ Valid
algorithms: []                               // ❌ Invalid
```

### Problem: Status returns 404
**Solution:** Use correct runId from the benchmark start response
```typescript
const { runId } = await startResponse.json();
const status = await fetch(`/api/benchmark/run/status?runId=${runId}`);
```

### Problem: Slow results
**Solution:** 
- Reduce `nRuns` (fewer repetitions)
- Reduce problem sizes (smaller dimensions)
- Use faster algorithms (ortools, greedy, two_opt)
- Increase `workers` for parallelism

---

## 📚 Related Documentation

- Full integration report: `docs/BENCHMARK_STUDIO_INTEGRATION_REPORT.md`
- Architecture guide: `docs/ARCHITECTURE_INTEGRATION_GUIDE.md`
- UniRide API: `optimizer_api/README.md`

---

## 💡 Tips

1. **Always set a `seed`** for reproducible results
2. **Start with `nRuns: 1`** to test configuration, then increase
3. **Use `workers: 4`** as a good balance between speed and resource usage
4. **Poll status every 2-5 seconds** to avoid excessive requests
5. **Store `runId`** in session/database for long-running benchmarks

---

**Last updated:** April 10, 2026
