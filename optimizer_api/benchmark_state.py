"""
Benchmark State Management - Thread-Safe Progress Tracking

ARCHITECTURE (13.04.2026):
- Used by main.py HTTP endpoints: /api/v1/benchmark/run, /api/v1/benchmark/status
- Updated by benchmark_runner.py in daemon thread: update_progress(), complete_run()
- Thread-safety: threading.Lock() protects all state mutations

FLOW:
- HTTP Thread (Uvicorn): POST /api/v1/benchmark/run
  ├─ create_run() → BenchmarkRunState (with lock)
  └─ Spawn daemon thread → return 200 OK

- Daemon Thread: run_benchmark_task() (background)
  ├─ BenchmarkRunner.run(state_manager=..., run_id=...)
  ├─ update_progress() every N experiments (with lock)
  └─ complete_run() or fail_run() at end (with lock)

- HTTP Thread (Uvicorn): GET /api/v1/benchmark/status (polling every 1s)
  ├─ get_run() reads state (with lock)
  └─ Return progress_percent, completed_experiments, status

THREAD SAFETY:
- All writes: protected by self._lock (threading.Lock)
- All reads: protected by self._lock
- No race conditions: lock acquired during mutation

See: docs/BENCHMARK_ARCHITECTURE_DEBT.md for full architecture
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
from enum import Enum
import threading


# Concurrent benchmark limit (soft limit - returns 429 if exceeded)
MAX_CONCURRENT_BENCHMARKS = 3


class BenchmarkStatus(str, Enum):
    """Benchmark run status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class BenchmarkRunState:
    """State of a single benchmark run"""
    run_id: str
    status: BenchmarkStatus = BenchmarkStatus.RUNNING
    total_experiments: int = 0
    completed_experiments: int = 0
    results_count: int = 0
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    message: str = "Başlatılıyor..."
    parameters: Dict = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)


class BenchmarkStateManager:
    """Thread-safe manager for benchmark runs with concurrent limit enforcement."""
    
    def __init__(self):
        self._runs: Dict[str, BenchmarkRunState] = {}
        self._lock = threading.Lock()
    
    def can_start_run(self) -> bool:
        """
        Check if a new benchmark run can start without exceeding concurrent limit.
        
        Returns:
            True if running count < MAX_CONCURRENT_BENCHMARKS, False otherwise
        """
        with self._lock:
            running_count = len([
                s for s in self._runs.values()
                if s.status == BenchmarkStatus.RUNNING
            ])
            return running_count < MAX_CONCURRENT_BENCHMARKS
    
    def create_run(self, run_id: str, total_experiments: int, parameters: Dict) -> BenchmarkRunState:
        """Create a new benchmark run"""
        with self._lock:
            state = BenchmarkRunState(
                run_id=run_id,
                total_experiments=total_experiments,
                parameters=parameters
            )
            self._runs[run_id] = state
            return state
    
    def get_run(self, run_id: str) -> Optional[BenchmarkRunState]:
        """Get a benchmark run state"""
        with self._lock:
            return self._runs.get(run_id)
    
    def update_progress(self, run_id: str, completed: int, message: str = ""):
        """Update progress of a run"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].completed_experiments = completed
                if message:
                    self._runs[run_id].message = message
    
    def add_result(self, run_id: str, result: Dict[str, Any]):
        """Append a single experiment result to the run's results list."""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].results.append(result)
                self._runs[run_id].results_count = len(self._runs[run_id].results)

    def complete_run(self, run_id: str, results_count: int, message: str = ""):
        """Mark a run as completed"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = BenchmarkStatus.COMPLETED
                self._runs[run_id].results_count = results_count
                self._runs[run_id].end_time = datetime.now(timezone.utc).isoformat()
                self._runs[run_id].completed_experiments = self._runs[run_id].total_experiments
                if message:
                    self._runs[run_id].message = message
    
    def fail_run(self, run_id: str, message: str = ""):
        """Mark a run as failed"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = BenchmarkStatus.FAILED
                self._runs[run_id].end_time = datetime.now(timezone.utc).isoformat()
                if message:
                    self._runs[run_id].message = message
    
    def stop_run(self, run_id: str, message: str = ""):
        """Stop a running benchmark"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = BenchmarkStatus.STOPPED
                self._runs[run_id].end_time = datetime.now(timezone.utc).isoformat()
                if message:
                    self._runs[run_id].message = message
    
    def list_runs(self) -> List[BenchmarkRunState]:
        """List all benchmark runs"""
        with self._lock:
            return list(self._runs.values())

    def import_run(self, run_id: str, data: Dict[str, Any]):
        """
        Import a complete benchmark run results into the state manager.
        Used for CLI -> Web sync.
        """
        with self._lock:
            # Determine status based on data or default to COMPLETED
            status_val = data.get("status", "completed")
            try:
                status = BenchmarkStatus(status_val)
            except ValueError:
                status = BenchmarkStatus.COMPLETED

            state = BenchmarkRunState(
                run_id=run_id,
                status=status,
                total_experiments=data.get("total_experiments", len(data.get("results", []))),
                completed_experiments=data.get("total_experiments", len(data.get("results", []))),
                results_count=len(data.get("results", [])),
                start_time=data.get("start_time", datetime.now(timezone.utc).isoformat()),
                end_time=data.get("end_time", datetime.now(timezone.utc).isoformat()),
                parameters=data.get("parameters", {}),
                results=data.get("results", []),
                message=f"Içe aktarıldı: {len(data.get('results', []))} sonuç"
            )
            self._runs[run_id] = state
            return state


# Global instance
benchmark_state_manager = BenchmarkStateManager()


__all__ = [
    "BenchmarkStatus",
    "BenchmarkRunState",
    "BenchmarkStateManager",
    "benchmark_state_manager"
]
