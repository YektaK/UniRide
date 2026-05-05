# Benchmark Web Integration - Architecture Debt & Critical Issues

**Date:** 13 Nisan 2026, 20:00  
**Updated:** 06 Mayıs 2026 — Status changed to IMPLEMENTED  
**Priority:** ~~🔴 CRITICAL (P0)~~ → ✅ RESOLVED  
**Status:** ✅ IMPLEMENTED — Daemon thread + state manager fully operational  
**Impact:** Benchmark endpoint fully functional with non-blocking execution

---

## 📋 Executive Summary

Benchmark Studio web integration'ın **backend puzzle eksik bir parça var**: Frontend ve State Manager hazır ama **actual benchmark runner hiçbir zaman çalıştırılmıyor**. 

**Result:**
- ❌ `POST /api/v1/benchmark/run` çağırılınca hiçbir şey yapılmıyor
- ⏳ Frontend polling yapıyor ama state asla update olmaz
- ❌ 2-3 saatlik benchmark işleri blocking olur (eğer eklenirse)
- 🔴 Uvicorn worker stuck kalabilir

---

## 🎯 Issue Breakdown

### Issue #1: ~~Missing Benchmark Executor~~ ✅ RESOLVED

**File:** `optimizer_api/main.py` — Lines 804-1008 (as of May 2026)

**Resolution:** `BenchmarkRunner` is now fully integrated with daemon thread execution:
- `main.py:937-979`: Daemon thread spawns `run_benchmark_task()` 
- `benchmark_runner.py:92-98`: `__init__` accepts `state_manager` and `run_id`
- `benchmark_runner.py:302-311`: `update_progress()` called after each experiment
- `benchmark_runner.py:341-347`: `complete_run()` called in `finally` block
- `benchmark_state.py:72-84`: `can_start_run()` enforces max 3 concurrent

---

### Issue #2: ~~Synchronous vs Asynchronous Execution Risk~~ ✅ RESOLVED

**Resolution:** Daemon Thread pattern implemented in `main.py:972-979`:
```python
executor_thread = threading.Thread(
    target=run_benchmark_task,
    daemon=True,
    name=f"benchmark-executor-{run_id}"
)
executor_thread.start()
```

---

### Issue #3: ~~State Updates Not Connected to Runner~~ ✅ RESOLVED

**Resolution:** `BenchmarkRunner` now accepts and uses `state_manager`:
- `benchmark_runner.py:92-98`: `__init__` stores `state_manager` and `run_id`
- `benchmark_runner.py:302-311`: Progress updates after each experiment
- `benchmark_runner.py:341-347`: `complete_run()` in finally block
- `benchmark_state.py:110-115`: `add_result()` appends individual results

---

## 🔧 Solution Architecture

### Recommended Approach: Daemon Thread + State Updates

```
Frontend (Next.js)
    │
    ├─ POST /api/benchmark/run
    │  └─ Returns 200 immediately with run_id
    │     (Spawns daemon thread, doesn't wait)
    │
    └─ GET /api/benchmark/status (polling every 1s)
       └─ Reads thread-safe state_manager
       
Backend (FastAPI + Daemon Thread)
    │
    ├─ HTTP Thread (Uvicorn worker)
    │  ├─ Handles POST → Creates state → Spawns daemon
    │  ├─ Handles GET → Reads state (thread-safe lock)
    │  └─ RETURNS IMMEDIATELY
    │
    └─ Daemon Thread (Benchmark Executor)
       ├─ Fetches problems + algorithms from state
       ├─ Runs BenchmarkRunner.run() (2-3 hours)
       ├─ Updates state_manager.update_progress() every N experiments
       ├─ Catches exceptions → benchmark_state_manager.fail_run()
       └─ Final: benchmark_state_manager.complete_run()
```

### Implementation Steps

#### Step 1: Modify BenchmarkRunner to Accept State Manager

**File:** `optimizer_api/benchmark_runner.py`

```python
class BenchmarkRunner:
    def __init__(self, strategies_registry=None, state_manager=None, run_id=None):
        self.strategies_registry = strategies_registry
        self.state_manager = state_manager
        self.run_id = run_id
        self.results: List[ExperimentResult] = []
        self.start_time: Optional[float] = None
        self.running = False
    
    def run(self, problems, algorithms, n_runs=3, ...):
        self.running = True
        self.start_time = time.time()
        
        metadata = {...}
        completed = 0
        
        try:
            for problem in problems:
                for algorithm in algorithms:
                    for run_num in range(1, n_runs + 1):
                        if not self.running:
                            break
                        
                        result = self._run_single_experiment(problem, algorithm, run_num)
                        self.results.append(result)
                        completed += 1
                        
                        # ✅ UPDATE STATE (NEW)
                        if self.state_manager and self.run_id:
                            self.state_manager.update_progress(
                                self.run_id,
                                completed,
                                f"Completed {completed}/{len(problems)*len(algorithms)*n_runs} experiments"
                            )
                        
                        logger.info(f"[{completed}/{metadata['total_experiments']}] ...")
        
        finally:
            self.running = False
            if self.state_manager and self.run_id:
                self.state_manager.complete_run(
                    self.run_id,
                    len(self.results),
                    f"Benchmark completed: {len(self.results)} results"
                )
```

#### Step 2: Modify main.py Endpoint to Use Daemon Thread

**File:** `optimizer_api/main.py`

```python
import threading
from benchmark_state import benchmark_state_manager, BenchmarkStatus

@app.post("/api/v1/benchmark/run")
def start_benchmark(
    run_id: str,
    algorithms: List[Dict],
    problems: List[str],
    settings: Dict
) -> Dict:
    """
    Start a new benchmark run (non-blocking, daemon thread).
    
    ARCHITECTURE:
    - Creates state immediately
    - Spawns daemon thread to run benchmark
    - Returns 200 OK (doesn't wait for benchmark completion)
    - Frontend polls /api/v1/benchmark/status for progress
    
    See: docs/BENCHMARK_ARCHITECTURE_DEBT.md for details
    """
    try:
        n_runs = settings.get("n_runs", 3)
        total_experiments = len(algorithms) * len(problems) * n_runs
        
        # ✅ Step 1: Create state
        state = benchmark_state_manager.create_run(
            run_id=run_id,
            total_experiments=total_experiments,
            parameters={
                "algorithms": algorithms,
                "problems": problems,
                "settings": settings
            }
        )
        
        # ✅ Step 2: Define benchmark task to run in background
        def run_benchmark_task():
            """Background task that runs benchmark and updates state"""
            try:
                logger.info(f"[Benchmark] Executor thread started for {run_id}")
                
                runner = BenchmarkRunner(
                    strategies_registry=STRATEGY_REGISTRY,
                    state_manager=benchmark_state_manager,
                    run_id=run_id
                )
                
                runner.run(
                    problems=problems,
                    algorithms=algorithms,
                    n_runs=n_runs,
                    seed=settings.get("seed", 42),
                    skip_cached=settings.get("skip_cached", False)
                )
                
                logger.info(f"[Benchmark] Completed {run_id}: {len(runner.results)} results")
                
            except Exception as e:
                logger.error(f"[Benchmark] Error in {run_id}: {e}", exc_info=True)
                benchmark_state_manager.fail_run(run_id, f"Error: {str(e)}")
        
        # ✅ Step 3: Spawn daemon thread (doesn't block HTTP)
        executor_thread = threading.Thread(
            target=run_benchmark_task,
            daemon=True,
            name=f"benchmark-executor-{run_id}"
        )
        executor_thread.start()
        
        logger.info(f"[Benchmark] Started run {run_id}: {total_experiments} experiments")
        
        return {
            "run_id": run_id,
            "status": "running",
            "total_experiments": total_experiments,
            "problems_count": len(problems),
            "algorithms_count": len(algorithms),
            "message": f"Benchmark run {run_id} başlatıldı (arka planda çalışıyor)",
            "start_time": state.start_time
        }
    
    except Exception as e:
        logger.error(f"[Benchmark] Error starting run: {e}", exc_info=True)
        return {
            "run_id": run_id,
            "status": "error",
            "error": str(e)
        }
```

#### Step 3: Update Status Endpoint (Already Good)

**File:** `optimizer_api/main.py` - Line 752-787

```python
@app.get("/api/v1/benchmark/status")
def get_benchmark_status(run_id: str) -> Dict:
    """
    Get status of a benchmark run.
    
    This endpoint is called by frontend polling (every 1 second).
    Thread-safe: Uses benchmark_state_manager._lock internally.
    
    Returns:
        {
            "run_id": "...",
            "status": "running|completed|failed|stopped",
            "total_experiments": int,
            "completed_experiments": int,
            "results_count": int,
            "message": "...",
            "progress_percent": float
        }
    """
    state = benchmark_state_manager.get_run(run_id)
    
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    
    progress_percent = 0.0
    if state.total_experiments > 0:
        progress_percent = (state.completed_experiments / state.total_experiments) * 100
    
    return {
        "run_id": run_id,
        "status": state.status.value,
        "total_experiments": state.total_experiments,
        "completed_experiments": state.completed_experiments,
        "results_count": state.results_count,
        "message": state.message,
        "progress_percent": min(100.0, progress_percent),
        "start_time": state.start_time,
        "end_time": state.end_time
    }
```

---

## 📊 Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Benchmark starts** | ❌ NO | ✅ YES (daemon thread) |
| **HTTP endpoint** | 200 OK but nothing happens | 200 OK + background execution |
| **Frontend polling** | Infinite "running" | Real-time progress 0→100% |
| **Worker threads** | Free (no benchmark) | Still free (daemon) |
| **UI responsiveness** | Good (but fake) | Good (real work) |
| **2-3 hour runtime** | N/A | Non-blocking ✅ |
| **State updates** | Never | Every experiment |
| **Error handling** | N/A | Proper exception catch + fail_run |

---

## 🚨 Risks & Mitigations

### Risk 1: Multiple Benchmarks Running Simultaneously

**Issue:** User starts 10 benchmarks → 10 daemon threads consuming CPU

**Mitigation:**
```python
# Add limit check in endpoint
active_runs = len([r for r in benchmark_state_manager.list_runs() 
                   if r.status == BenchmarkStatus.RUNNING])

if active_runs >= 3:  # Max 3 concurrent
    return {
        "status": "error",
        "error": f"Max 3 concurrent benchmarks allowed ({active_runs} running)"
    }
```

### Risk 2: Long-running Without Progress

**Issue:** UI doesn't update for 5 minutes

**Mitigation:** Add `update_progress()` calls in `_run_single_experiment()`
```python
def _run_single_experiment(self, problem, algorithm, run_num):
    result = self._run_and_time_algorithm(...)
    
    # ✅ Update state every experiment
    if self.state_manager and self.run_id:
        completed = len(self.results)
        self.state_manager.update_progress(
            self.run_id,
            completed,
            f"Running: {algorithm.algorithm_id} on {problem.name}"
        )
    
    return result
```

### Risk 3: Memory Leak from Daemon Thread

**Issue:** Thread runs forever even if app restarts

**Mitigation:** Daemon threads are killed on app exit. For graceful shutdown:
```python
# Add shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    all_runs = benchmark_state_manager.list_runs()
    for run in all_runs:
        if run.status == BenchmarkStatus.RUNNING:
            benchmark_state_manager.stop_run(run.run_id, "Server shutdown")
```

---

## 📝 Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `optimizer_api/main.py` | Add daemon thread logic to `/api/v1/benchmark/run` | 🔴 P0 |
| `optimizer_api/benchmark_runner.py` | Add state_manager callbacks + run_id param | 🔴 P0 |
| `optimizer_api/benchmark_state.py` | Add concurrent run limit (optional) | 🟡 P1 |
| `docs/BENCHMARK_ARCHITECTURE_DEBT.md` | This document | ✅ DONE |

---

## ✅ Testing Checklist

- [x] `POST /api/v1/benchmark/run` returns 200 immediately
- [x] `GET /api/v1/benchmark/status` shows progress 0→100%
- [x] Multiple `/status` calls return consistent data (thread-safe)
- [x] Exception in runner → state shows "failed" status
- [x] Other API endpoints still respond during benchmark (daemon thread)
- [x] Concurrent limit enforced (max 3 → 429 response)

---

## 🔗 Related Files

- `optimizer_api/main.py` - HTTP endpoints (lines 688-815)
- `optimizer_api/benchmark_runner.py` - Runner logic (lines 1-200+)
- `optimizer_api/benchmark_state.py` - State manager (lines 1-110)
- `src/app/api/benchmark/run/route.ts` - Frontend (working correctly ✅)
- `src/app/api/benchmark/run/status/route.ts` - Status endpoint (working correctly ✅)

---

## 📞 Questions to Resolve

1. **What is max concurrent benchmark limit?** → Suggest 3
2. **Should stop during app shutdown?** → Implement graceful shutdown
3. **Storage for results?** → Currently in-memory, should persist to DB
4. **Retry on failure?** → Not implemented yet

---

**Last Updated:** 06 Mayıs 2026  
**Status:** ✅ IMPLEMENTED — All 3 issues resolved  
**Assignee:** Backend Developer  
**Reviewer:** Tech Lead
