# The Meta-Architect's Decision: Unified Core Consolidation Blueprint

**Date:** May 25, 2026  
**Time:** 22:55:16 (Local Time: UTC+3)  
**Author/Creator:** Antigravity, a powerful agentic AI coding assistant designed by the Google DeepMind team working on Advanced Agentic Coding.  
**Role:** Senior Systems Architect, Principal Engineer, and Academic Research Lead  

---

## 0. Exact User Request (Prompt)

The following is the exact prompt that initiated this unified synthesis:

```markdown
with these reports from different ai agents in hand 
You are an expert Senior Systems Architect, Principal Engineer, and Academic Research Lead with 15+ years of experience in enterprise backend development (FastAPI/Node.js) and metaheuristic optimization algorithms (CVRPTW/TSP).

We have an uploaded Code Review report (`UniRide Dual-Engine — Post-Refactoring Code Review (v5 — Final) 25.05.2026.md`) that claims several critical flaws exist in our repository. This codebase is a "Dual-Engine" system:
1. **Engine A (UniRide):** Production-grade student transportation API, routing engines, and live database matching.
2. **Engine B (Academic Benchmark):** Research harness for DOE (Design of Experiments) and metaheuristic validation against TSPLIB.
Both engines share a common core named `uniride_core`.

Your main task is to validate or debunk the findings of this uploaded report by investigating the code directly, and provide an actionable strategy to decouple/clean the codebase without breaking either of the workflows.

### 0. CRITICAL: Mandatory CodeGraph Usage (Token & Accuracy Rule)
This project is indexed via CodeGraph MCP. You MUST NOT blindly accept the claims in the report. You must personally verify them using structural analysis.
- Use `codegraph_search` and `codegraph_node` to find exact definitions and signatures.
- Use `codegraph_callers` or `codegraph_callees` to trace dependencies.
- Do NOT loop manual file reads or use broad text greps first; rely on the AST index to verify architecture instantly.

### 1. Investigation & Cross-Verification Guidelines
For each "Critical" and "Significant" finding in the report, use CodeGraph to check the truth:

- **Finding 3.1 (Dual SOTA Implementations):** Investigate `uniride_core/algorithms/sota_tsp/` and `optimizer_api/strategies/sota_common/`. Are these actually redundant code duplications, or are they mathematically distinct implementations (e.g., Integer-indexed pure TSP vs. String-indexed production data structures)? 
- **Finding 3.2 (Broken Import):** Check if `optimizer_api/run_sota_benchmark.py` really tries to import a non-existent module from `academic_benchmark`.
- **Finding 3.4 (Hidden Reverse Dependency):** Inspect `uniride_core/algorithms/tsplib_parser.py`. Does it explicitly hardcode a path going up and into `optimizer_api`?
- **Finding 3.6 & 3.9 (Singleton Mutation & Triple Local Search):** Verify if the strategy registries run a risk of race conditions under parallel FastAPI requests, and check if the local search modules can be merged into the shared kernel.

### 2. Core Goal: Better Cohabitation (No Breaking Changes)
Since UniRide (Production) and Academic Benchmark (Research) MUST live together and share logic, design an architecture that allows them to co-exist cleanly. 
- How should `uniride_core` be structured so that it acts as a true pure mathematical/model layer without knowing about `optimizer_api` or `academic_benchmark` deployment specifics?
- How should `ProblemInstance` or data models be refactored (e.g., via inheritance or protocols) so that TSPLIB fields don't pollute production CVRPTW models, without breaking the benchmark engine?

### 3. Expected Output Structure
Provide your independent verification and architectural proposal in this format:

1. **Fact-Check Matrix:** A table listing the report's main findings, your verdict (VERIFIED / FALSE ALARM / INTENTIONAL DESIGN), and your brief structural evidence based on CodeGraph.
2. **The Dual-Engine Cohabitation Blueprint:** A clear architectural proposal on how to organize the shared kernel (`uniride_core`) and the two engines so they can scale together without cross-contamination.
3. **Safe Refactoring Recommendations:** High-level "Before vs. After" code or structural layouts showing how to solve the *validated* issues safely, ensuring neither the production API nor the academic DOE workflows break.
```

---

## 1. Fact-Check Matrix Harmonization (The Ultimate Verdict)

By synthesizing reports `decoupling_strategy_report_2026_05_25_1740.md`, `architectural_verification_and_consolidation_report_2026_05_25_1820.md`, `UniRide_Architectural_Verification_2026-05-25_143000.md`, and `UniRide Dual-Engine — Independent Verification & Architectural Blueprint 25.05.2026.md`, we establish the definitive truth:

| Finding | Definitive Verdict | Architectural Nuance & Evidence |
| :--- | :--- | :--- |
| **3.1 Dual SOTA Implementations** | **PARTIALLY VERIFIED (NUANCED)** | **The Nuance:** The SOTA algorithms (`E2BSO_TSP`, `R2DMA_TSP`, etc.) in `uniride_core` are mathematically distinct from `optimizer_api` wrappers because they run JIT-accelerated integer-indexed pure TSP structures. However, the **underlying infrastructure** (destroy/repair operators, simulated annealing criteria, local search layers) is heavily duplicated between `sota_common` and `sota_tsp` in active code. The non-TSP algorithm variants only exist in `.proposed_changes/`. |
| **3.2 Broken Import** | **VERIFIED** | **Evidence:** `optimizer_api/run_sota_benchmark.py` imports a non-existent `run_sota_benchmark` module from `academic_benchmark`. It crashes immediately upon import. |
| **3.3 Hardcoded API Key** | **VERIFIED (CRITICAL SECURITY)** | **Evidence:** `test_direct.py` contains a live plaintext Azure OpenAI model key (`YF7tYODTYg...`). **Action:** Must be rotated immediately and bound to `os.environ`. |
| **3.4 Hidden Reverse Dependency** | **VERIFIED** | **Evidence:** `uniride_core/algorithms/tsplib_parser.py` hardcodes paths going up and into the production package (`../../optimizer_api/tests/tsplib_data`), violating core encapsulation. |
| **3.6 Singleton Mutation Risk** | **VERIFIED** | **Evidence:** `STRATEGY_REGISTRY` instantiates stateful strategies as module-level singletons. Mutating options inside `self.config` during request optimization under parallel FastAPI tasks will trigger race conditions. |
| **3.8 ALNS Missing Param Space** | **VERIFIED** | **Evidence:** `ALNS-TSP` is present in `sota_engine.py` maps but has no corresponding entry in `SOTA_PARAM_SPACES` inside `academic_benchmark/param_spaces.py`, leading to silent empty parameter defaults. |
| **3.9 Triple Local Search** | **VERIFIED** | **Evidence:** Local search logic exists in three distinct files: `optimizer_api/utils/local_search.py` (String-indexed ABCs), `sota_common/multi_layer_ls.py` (String-indexed, callable cost functions), and `sota_tsp/ls_engine.py` (Integer-indexed Numba arrays). While conceptually serving three different layers, they represent a significant maintenance overhead. |
| **3.10 Signal Handler Conflict** | **VERIFIED** | **Evidence:** When `smart_benchmark.py` imports from `cli_engine.py`, both try to overwrite the active `signal.SIGINT` handler, leading to silent signal interception races. |
| **3.11 Routing Scheduling Logic** | **VERIFIED** | **Evidence:** `routers/optimization.py` has ~120 lines of complex forward and backward arrival scheduling logic (`_calculate_scheduled_times`) that belongs in a separate utility module. |
| **3.12 ProblemInstance Pollution** | **VERIFIED** | **Evidence:** `ProblemInstance` in `uniride_core/models.py` mixes TSPLIB research fields (`edge_weight_type`, `source`) with CVRPTW production fields (`capacity`, `time_windows`, `depot_index`). |
| **3.13 TSPLIB_OPTIMALS Divergence** | **VERIFIED** | **Evidence:** The core has ~80 optimal values, whereas the academic benchmark utilities file maintains 129 comprehensive values. |
| **NEW: Legacy Broken Scripts** | **VERIFIED** | **Evidence:** `optimizer_api/faz0_interactive.py` tries to import algorithm classes from `sota_common`, but `sota_common/__init__.py` only contains infrastructure. This script will crash immediately on launch. |

---

## 2. The Dual-Engine Cohabitation Blueprint

We propose a strict **Three-Layer Pure Abstraction Strategy** where `uniride_core` contains all algorithms and mathematical structures as a pure Python package with no external dependencies or environmental path assumptions.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      1. PRESENTATION & HARNESS LAYER                   │
│                                                                        │
│   ┌───────────────────────────────────┐    ┌───────────────────────┐   │
│   │    Engine A: Production API       │    │  Engine B: Academic   │   │
│   │        (FastAPI Routing)          │    │   Benchmark (CLI)     │   │
│   └─────────────────┬─────────────────┘    └───────────┬───────────┘   │
└─────────────────────┼──────────────────────────────────┼───────────────┘
                      │                                  │
                      ▼                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   2. ADAPTER LAYER (Project Specific)                  │
│                                                                        │
│   ┌───────────────────────────────────┐    ┌───────────────────────┐   │
│   │    Production Strategy Adapters   │    │  Benchmark Orchestr.  │   │
│   │  (Time Window Slicing, K-Means)   │    │  (Optuna Tuning, SQL) │   │
│   └─────────────────┬─────────────────┘    └───────────┬───────────┘   │
└─────────────────────┼──────────────────────────────────┼───────────────┘
                      │                                  │
                      └─────────────────┬────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  3. PURE KERNEL LAYER (uniride_core)                   │
│                                                                        │
│  (Zero environment variable leaks, Pure mathematical types, Numba JIT) │
│                                                                        │
│  ├── models/                                                           │
│  │   ├── base.py       - BaseProblem (name, dimension, coords)         │
│  │   ├── tsp.py        - TSPProblem (inherits BaseProblem)             │
│  │   └── cvrptw.py     - CVRPTWProblem (inherits BaseProblem)          │
│  ├── solvers/                                                          │
│  │   ├── classical/    - Pure GA, PSO solvers                          │
│  │   ├── sota/         - Pure JIT E2BSO, R2DMA solvers                 │
│  │   └── infra/        - Unified Destroy/Repair/SA operators           │
│  └── tsplib/                                                           │
│      ├── parser.py     - Pure pathless parser                          │
│      └── optimals.py   - Comprehensive 129 TSPLIB optimals             │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Key Architectural Principles

1. **`uniride_core` is a pure math/model layer**: No imports from `optimizer_api` or `academic_benchmark`. No hardcoded paths to either package. No web framework dependencies.
2. **Infrastructure lives in `uniride_core`**: The destroy/repair operators, acceptance criteria, local search, etc. belong in `uniride_core/solvers/infrastructure/` — NOT duplicated in `optimizer_api/strategies/sota_common/`.
3. **Each engine has its own adapter layer**: `optimizer_api` adapts core to web/Supabase/CVRPTW. `academic_benchmark` adapts core to CLI/DOE/TSPLIB. Neither adapter should contain algorithm logic — only orchestration and I/O.
4. **Data models use inheritance, not monolithic dataclasses**: `BaseProblem` → `TSPProblem` / `CVRPTWProblem` keeps concerns separated while sharing common fields.
5. **Strategy registry uses factory pattern, not singletons**: Thread-safe per-request instantiation prevents config mutation races.

---

## 3. Safe Refactoring Recommendations

Below are the exact transition steps and "Before vs. After" structural layout changes required to achieve clean, unified cohabitation without breaking either Engine A or Engine B.

### 3.1 Unifying Data Models via Polymorphic Inheritance (Solving 3.12)

We decouple `ProblemInstance` to separate TSPLIB fields from production-level time-window constraints while preserving polymorphism.

**Before:**
```python
# uniride_core/models.py
@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    source: str = "tsplib"
    edge_weight_type: str = "EUC_2D"
    capacity: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
```

**After:**
```python
# uniride_core/models/base.py
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class BaseProblem:
    """Core mathematical representation of a node routing layout."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]] = field(default_factory=list)
    optimal: Optional[float] = None

# uniride_core/models/tsp.py
@dataclass
class TSPProblem(BaseProblem):
    """Academic benchmark representation (TSPLIB)."""
    edge_weight_type: str = "EUC_2D"
    category: str = "small"  # small, medium, large
    source: str = "tsplib"
    file_path: Optional[str] = None

# uniride_core/models/cvrptw.py
@dataclass
class CVRPTWProblem(BaseProblem):
    """Production routing representation (School Bus routes)."""
    capacity: int = 0
    num_vehicles: int = 1
    time_windows: List[Tuple[int, int]] = field(default_factory=list)
    depot_index: int = 0
```

---

### 3.2 Thread-Safe strategy Lookup via Registry Factories (Solving 3.6)

Instead of using module-level stateful singletons, we transition to an on-demand thread-local lookup function.

**Before:**
```python
# optimizer_api/strategies/__init__.py
_ga_strategy = GeneticAlgorithmStrategy()
STRATEGY_REGISTRY = {
    "genetic_algorithm": _ga_strategy,
}
```

**After:**
```python
# optimizer_api/strategies/__init__.py
import threading
from typing import Dict, Type, Optional

STRATEGY_CLASSES: Dict[str, Type[BaseRoutingStrategy]] = {
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "ga": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    "e2bso": E2BSoStrategy,
}

_thread_local = threading.local()

def get_strategy(name: str) -> Optional[BaseRoutingStrategy]:
    """Dynamically gets a thread-safe strategy instance isolated per-request thread."""
    name_lower = name.lower()
    if name_lower not in STRATEGY_CLASSES:
        return None
        
    if not hasattr(_thread_local, 'strategies'):
        _thread_local.strategies = {}
        
    if name_lower not in _thread_local.strategies:
        cls = STRATEGY_CLASSES[name_lower]
        # Fresh initialization avoids config mutation races across requests
        _thread_local.strategies[name_lower] = cls()
        
    return _thread_local.strategies[name_lower]
```

---

### 3.3 Eliminating Core Reverse Dependencies (Solving 3.4)

Remove the hardcoded `optimizer_api` relative paths inside `uniride_core` and fallback to path-agnostic environment configurations.

**Before:**
```python
# uniride_core/algorithms/tsplib_parser.py
TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..',
                                'optimizer_api', 'tests', 'tsplib_data')
```

**After:**
```python
# uniride_core/algorithms/tsplib_parser.py
import os

# Pure core fallback: can be dynamically overridden by env context
TSPLIB_DATA_DIR = os.environ.get(
    "TSPLIB_DATA_DIR",
    os.path.join(os.path.dirname(__file__), '..', '..', 'tsplib_data')
)
```

---

### 3.4 Consolidating TSPLIB Optimals (Solving 3.13)

We merge the different optimal value dictionaries into a single database mapping in the shared core.

**Before:** Distinct dictionaries inside `tsplib_parser.py` (~80 entries) and `benchmark_utils.py` (129 entries).

**After:** Move the unified 129 entries to a core module and import them elsewhere:
```python
# In uniride_core/tsplib/optimals.py
TSPLIB_OPTIMALS: Dict[str, int] = {
    "berlin52": 7542,
    "eil51": 426,
    # ... all 129 entries ...
}

# In academic_benchmark/benchmark_utils.py
from uniride_core.tsplib.optimals import TSPLIB_OPTIMALS
```

---

### 3.5 Resolving Broken Benchmarks (Solving 3.2)

Correct the entry path of the SOTA benchmark script inside the API suite:

**Before:**
```python
# optimizer_api/run_sota_benchmark.py
from academic_benchmark.run_sota_benchmark import main
```

**After:**
```python
# optimizer_api/run_sota_benchmark.py
"""SOTA Benchmark Gateway — delegates execution safely to sota_engine."""
import sys
from academic_benchmark.sota_engine import run_engine_default
from academic_benchmark.cli_engine import load_problems

def main():
    problems = load_problems()
    # Execute default benchmark run on E2BSO-TSP
    run_engine_default(problems, ["E2BSO-TSP"], n_runs=3, workers=4, metadata={})

if __name__ == "__main__":
    sys.exit(main())
```

---

### 3.6 Cleaning Route Handlers (Solving 3.11)

Extract route scheduling logic from FastAPI handlers into a clean utility module.

**Before:** `_calculate_scheduled_times` (~120 lines of calculations) nested directly inside `routers/optimization.py`.

**After:**
```python
# In optimizer_api/utils/scheduling.py
from typing import List, Dict
from models.schemas import VehicleRoute, OptimizationRequest

def calculate_scheduled_times(
    routes: List[VehicleRoute],
    request: OptimizationRequest,
    distance_matrix: Dict[str, Dict[str, float]]
) -> List[VehicleRoute]:
    """Utility helper to process forward/backward arrival schedule times."""
    # ... extraction of the exact scheduling logic ...
    return routes
```

---

## 4. Immediate Action Fix Plan Checklist

Below is the prioritized actionable checklist to apply these changes securely:

- [ ] **Phase 1: Security & Dead Script Clean-up (Priority: Critical)**
  - [ ] Rotate the plaintext Azure OpenAI model key in cloud portal.
  - [ ] Secure `test_direct.py` to fetch via `os.environ.get("AZURE_OPENAI_API_KEY")`.
  - [ ] Apply the delegator gateway fix in `optimizer_api/run_sota_benchmark.py`.
  - [ ] Drop or correct legacy `optimizer_api/faz0_interactive.py` dependencies.
  - [ ] Fix `TSPLIB_DATA_DIR` inside `uniride_core` using fallback configuration.
- [ ] **Phase 2: Mathematical Infrastructure Extraction (Priority: High)**
  - [ ] Group ALNS, destroy, repair, and SA parameters inside `uniride_core/solvers/infra/`.
  - [ ] Re-export SOTA constants inside `sota_common/__init__.py` with deprecation notices.
  - [ ] Inject `ALNS-TSP` param settings into `academic_benchmark/param_spaces.py`.
  - [ ] Consolidate `TSPLIB_OPTIMALS` to `uniride_core/tsplib/optimals.py`.
- [ ] **Phase 3: Class Inheritance & Thread-Safety (Priority: Medium)**
  - [ ] Decouple `ProblemInstance` into pure polymorphic schemas inside `uniride_core/models/`.
  - [ ] Implement `get_strategy()` thread-local factories in strategies lookup.
  - [ ] Move CVRPTW arrival scheduling calculations to `optimizer_api/utils/scheduling.py`.
