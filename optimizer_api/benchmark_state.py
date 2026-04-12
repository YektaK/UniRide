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
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import threading


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
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    message: str = "Başlatılıyor..."
    parameters: Dict = field(default_factory=dict)


class BenchmarkStateManager:
    """Thread-safe manager for benchmark runs"""
    
    def __init__(self):
        self._runs: Dict[str, BenchmarkRunState] = {}
        self._lock = threading.Lock()
    
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
    
    def complete_run(self, run_id: str, results_count: int, message: str = ""):
        """Mark a run as completed"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = BenchmarkStatus.COMPLETED
                self._runs[run_id].results_count = results_count
                self._runs[run_id].end_time = datetime.utcnow().isoformat()
                self._runs[run_id].completed_experiments = self._runs[run_id].total_experiments
                if message:
                    self._runs[run_id].message = message
    
    def fail_run(self, run_id: str, message: str = ""):
        """Mark a run as failed"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = BenchmarkStatus.FAILED
                self._runs[run_id].end_time = datetime.utcnow().isoformat()
                if message:
                    self._runs[run_id].message = message
    
    def stop_run(self, run_id: str, message: str = ""):
        """Stop a running benchmark"""
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = BenchmarkStatus.STOPPED
                self._runs[run_id].end_time = datetime.utcnow().isoformat()
                if message:
                    self._runs[run_id].message = message
    
    def list_runs(self) -> List[BenchmarkRunState]:
        """List all benchmark runs"""
        with self._lock:
            return list(self._runs.values())


# Global instance
benchmark_state_manager = BenchmarkStateManager()


__all__ = [
    "BenchmarkStatus",
    "BenchmarkRunState",
    "BenchmarkStateManager",
    "benchmark_state_manager"
]
