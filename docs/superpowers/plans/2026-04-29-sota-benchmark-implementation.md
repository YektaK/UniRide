# SOTA Benchmark Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild SOTA benchmark under academic_benchmark using TSPLIB metadata, edge-weight-aware distances, and dynamic optimal computation from .opt.tour with download fallback.

**Architecture:** Move the benchmark entry point to academic_benchmark, reuse the academic loader, and compute distances based on EDGE_WEIGHT_TYPE. Add tour validation and a historical data recalculation policy.

**Tech Stack:** Python 3.x, existing UniRide optimizer_api, academic_benchmark utilities, CSV output

---

### Task 1: Add TSPLIB metric helpers (edge-weight-aware distance)

**Files:**
- Modify: optimizer_api/utils/tsplib_parser.py
- Test: manual (no existing unit tests)

- [ ] **Step 1: Add distance helpers for CEIL_2D/ATT/GEO**

Add these functions below `tsplib_euc_2d_distance` in [optimizer_api/utils/tsplib_parser.py](optimizer_api/utils/tsplib_parser.py#L130):

```python
import math


def tsplib_ceil_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB CEIL_2D distance: ceil(sqrt(dx^2+dy^2))."""
    raw = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    return int(math.ceil(raw))


def tsplib_att_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB ATT distance (pseudo-Euclidean)."""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    rij = math.sqrt((dx * dx + dy * dy) / 10.0)
    tij = int(rij + 0.5)
    return tij if tij >= rij else tij + 1


def tsplib_geo_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB GEO distance (great-circle)."""
    def _to_geo(x: float) -> float:
        deg = int(x)
        minute = x - deg
        return math.pi * (deg + 5.0 * minute / 3.0) / 180.0

    rrr = 6378.388
    lat1 = _to_geo(p1[0])
    lon1 = _to_geo(p1[1])
    lat2 = _to_geo(p2[0])
    lon2 = _to_geo(p2[1])

    q1 = math.cos(lon1 - lon2)
    q2 = math.cos(lat1 - lat2)
    q3 = math.cos(lat1 + lat2)
    return int(rrr * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)
```

- [ ] **Step 2: Add a dispatcher to select distance by EDGE_WEIGHT_TYPE**

Add below the new functions:

```python
def tsplib_distance_by_type(edge_weight_type: str, p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    et = (edge_weight_type or "EUC_2D").upper()
    if et == "EUC_2D":
        return tsplib_euc_2d_distance(p1, p2)
    if et == "CEIL_2D":
        return tsplib_ceil_2d_distance(p1, p2)
    if et == "ATT":
        return tsplib_att_distance(p1, p2)
    if et == "GEO":
        return tsplib_geo_distance(p1, p2)
    raise ValueError(f"Unsupported EDGE_WEIGHT_TYPE: {edge_weight_type}")
```

- [ ] **Step 3: Run a quick sanity check**

Run: `python -c "from optimizer_api.utils.tsplib_parser import tsplib_distance_by_type; print(tsplib_distance_by_type('EUC_2D',(0,0),(3,4)))"`
Expected: prints `5`

- [ ] **Step 4: Commit**

```bash
git add optimizer_api/utils/tsplib_parser.py
git commit -m "feat: add TSPLIB edge weight distance helpers"
```

---

### Task 2: Create a new academic_benchmark SOTA benchmark runner

**Files:**
- Create: academic_benchmark/run_sota_benchmark.py
- Modify: academic_benchmark/dataset_loader.py

- [ ] **Step 1: Extend dataset loader to expose edge_weight_type and opt.tour download**

In [academic_benchmark/dataset_loader.py](academic_benchmark/dataset_loader.py), add a function to download `.opt.tour` using the GitHub mirror and return the path. Add below `parse_opt_tour_file`:

```python
def download_opt_tour(problem_name: str, data_dir: str) -> Optional[str]:
    """Download TSPLIB .opt.tour file from GitHub mirror if missing."""
    import urllib.request
    os.makedirs(data_dir, exist_ok=True)
    filename = f"{problem_name}.opt.tour"
    filepath = os.path.join(data_dir, filename)
    if os.path.exists(filepath):
        return filepath

    url = f"https://raw.githubusercontent.com/mastqe/tsplib/master/{filename}"
    try:
        urllib.request.urlretrieve(url, filepath)
        return filepath
    except Exception:
        return None
```

Also update `parse_tsp_file` to return `edge_weight_type` and store it in the `TSPLIBProblem` dataclass (add field). Add to `TSPLIBProblem`:

```python
edge_weight_type: str
```

And set it in `parse_tsp_file`:

```python
edge_weight_type = "EUC_2D"
if line.startswith("EDGE_WEIGHT_TYPE"):
    edge_weight_type = line.split(":")[-1].strip()
```

Return it in `TSPLIBProblem(...)`.

- [ ] **Step 2: Create new academic_benchmark/run_sota_benchmark.py**

Create the new script with these core pieces (use existing CLI + runner structure from old file):

```python
import os
import sys
import csv
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from academic_benchmark.dataset_loader import (
    BenchmarkDatasetLoader,
    parse_opt_tour_file,
    compute_tour_length,
    download_opt_tour,
)
from optimizer_api.utils.tsplib_parser import tsplib_distance_by_type
from optimizer_api.strategies.sota_common import (
    E2BSO, E2BSOConfig,
    R2DMA, R2DMAConfig,
    PAOEA, PAOEAConfig,
)

logging.basicConfig(level=logging.WARNING)

@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    edge_weight_type: str
    optimal: Optional[int] = None

    def tour_cost(self, tour: List[int]) -> int:
        if not tour or len(tour) < 2:
            return 0
        return sum(
            tsplib_distance_by_type(self.edge_weight_type, self.coordinates[tour[i]], self.coordinates[tour[(i + 1) % len(tour)]])
            for i in range(len(tour))
        )
```

Continue by adapting the old run_sota_benchmark logic (interactive selection, runners). Use the tour validator below before scoring:

```python
def validate_tour(tour: List[int], dimension: int) -> bool:
    if len(tour) != dimension:
        return False
    return len(set(tour)) == dimension and all(0 <= n < dimension for n in tour)
```

Compute optimal:

```python
def compute_optimal_from_opt_tour(problem: ProblemInstance, tsp_dir: str) -> Optional[int]:
    opt_path = os.path.join(tsp_dir, f"{problem.name}.opt.tour")
    if not os.path.exists(opt_path):
        opt_path = download_opt_tour(problem.name, tsp_dir)
    if not opt_path:
        return None
    tour_1_based = parse_opt_tour_file(opt_path)
    if not tour_1_based:
        return None
    # convert to 0-based
    tour = [n - 1 for n in tour_1_based if n > 0]
    if not validate_tour(tour, problem.dimension):
        return None
    return problem.tour_cost(tour)
```

- [ ] **Step 3: Update runner to use computed optimal**

In the runner, after loading a `ProblemInstance`, call `compute_optimal_from_opt_tour(...)`. If it returns None, leave `optimal=None` and mark `optimal_source="unknown"` in CSV.

- [ ] **Step 4: Run a dry run with one problem**

Run: `python academic_benchmark/run_sota_benchmark.py`
Expected: can select one problem; outputs CSV with `edge_weight_type` and `optimal_source` columns.

- [ ] **Step 5: Commit**

```bash
git add academic_benchmark/run_sota_benchmark.py academic_benchmark/dataset_loader.py
git commit -m "feat: rebuild sota benchmark under academic_benchmark"
```

---

### Task 3: Keep compatibility shim at optimizer_api/run_sota_benchmark.py

**Files:**
- Modify: optimizer_api/run_sota_benchmark.py

- [ ] **Step 1: Replace contents with shim**

```python
import sys
from academic_benchmark.run_sota_benchmark import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Commit**

```bash
git add optimizer_api/run_sota_benchmark.py
git commit -m "chore: forward sota benchmark to academic_benchmark"
```

---

### Task 4: Historical data recalculation / deletion

**Files:**
- Modify: academic_benchmark/run_sota_benchmark.py (add a utility to process existing CSVs)
- Delete: unreproducible historical CSV/summary files in optimizer_api/

- [ ] **Step 1: Add recalculation utility**

Add a function `recalc_or_prune_history(history_dir: str)` that:
- Scans `optimizer_api/benchmark_results_*.csv` and `optimizer_api/benchmark_summary_*.txt`.
- For each CSV, check if all problems in file have valid .tsp and .opt.tour available (local or downloadable).
- If yes, rerun benchmark on those problems and write corrected CSV/summary to academic_benchmark/ with `_recalc` suffix.
- If no, delete the original CSV/summary.

- [ ] **Step 2: Run once manually**

Run: `python academic_benchmark/run_sota_benchmark.py --recalc-history`
Expected: prints audit log of recalculated vs deleted files.

- [ ] **Step 3: Commit**

```bash
git add academic_benchmark/run_sota_benchmark.py optimizer_api/benchmark_results_*.csv optimizer_api/benchmark_summary_*.txt
git commit -m "chore: recalc or prune historical sota results"
```

---

### Task 5: Smoke tests

**Files:**
- None (manual)

- [ ] **Step 1: Run small SOTA benchmark**

Run: `python academic_benchmark/run_sota_benchmark.py`
Select 1–2 problems and 1 algorithm.
Expected: no negative gaps, no NaNs when opt.tour exists, valid edge_weight_type recorded.

- [ ] **Step 2: Run compatibility shim**

Run: `python optimizer_api/run_sota_benchmark.py`
Expected: launches the academic_benchmark runner.

- [ ] **Step 3: Commit final adjustments**

```bash
git add -A
git commit -m "test: validate sota benchmark rebuild"
```

---

## Plan Self-Review
- Spec coverage: all requirements mapped to tasks (file move, edge weights, dynamic optimals, history policy, compatibility).
- Placeholder scan: none.
- Type consistency: edge_weight_type flows through ProblemInstance and distance functions.
