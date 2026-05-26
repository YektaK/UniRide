# UniRide Dual-Engine — Fact-Check & Decoupling Strategy Report

**Date:** May 25, 2026  
**Time:** 17:40:33 (Local Time: UTC+3)  
**Author/Creator:** Antigravity, a powerful agentic AI coding assistant designed by the Google DeepMind team working on Advanced Agentic Coding.  
**Role:** Senior Systems Architect, Principal Engineer, and Academic Research Lead  

---

## 0. Original User Prompt

Below is the exact original prompt that initiated this investigation:

```markdown
@[c:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\UniRide Dual-Engine — Post-Refactoring Code Review (v5 — Final) 25.05.2026.md] You are an expert Senior Systems Architect, Principal Engineer, and Academic Research Lead with 15+ years of experience in enterprise backend development (FastAPI/Node.js) and metaheuristic optimization algorithms (CVRPTW/TSP).

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

## 1. Fact-Check Matrix

Following structural investigation, here are the direct verifications of the findings:

| Finding ID | Report Finding Title | Verdict | Codebase Evidence & Verification Details |
| :--- | :--- | :--- | :--- |
| **Finding 3.1** | **Dual SOTA Implementations** | **VERIFIED** | **Evidence:** [destroy_ops.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/sota_tsp/destroy_ops.py) and [destroy_operators.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/strategies/sota_common/destroy_operators.py).<br>• The `sota_tsp` variant is mathematically adapted for Numba-accelerated pure TSP operations using integer-indexed `List[int]` representations and float-matrix indices.<br>• The `sota_common` variant operates on string-indexed `List[str]` tours using dictionaries (`Dict[str, Dict[str, float]]`).<br>• `faz0_interactive.py` still relies heavily on the `sota_common` infrastructure, meaning two duplicate math stacks exist in parallel. |
| **Finding 3.2** | **Broken Integration Path** | **VERIFIED** | **Evidence:** [run_sota_benchmark.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/run_sota_benchmark.py#L3).<br>• It attempts to run `from academic_benchmark.run_sota_benchmark import main`. No such module exists in the `academic_benchmark` package. It is completely broken and crashes instantly at import time. |
| **Finding 3.3** | **Hardcoded API Key** | **VERIFIED** | **Evidence:** [test_direct.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/test_direct.py#L5).<br>• A live Azure OpenAI API key (`YF7tYODTYg...`) is hardcoded in the file. **This key must be rotated immediately** and the file must be removed or configured to use environment variables. |
| **Finding 3.4** | **Hidden Reverse Dependency** | **VERIFIED** | **Evidence:** [tsplib_parser.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/tsplib_parser.py#L35-L36).<br>• The shared kernel `uniride_core` explicitly hardcodes `TSPLIB_DATA_DIR` pointing to `../../optimizer_api/tests/tsplib_data`, violating package encapsulation. |
| **Finding 3.6** | **Singleton Config Mutation** | **VERIFIED** | **Evidence:** [strategies/\_\_init\_\_.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/strategies/__init__.py#L79-L98).<br>• Strategies are instantiated as module-level global singletons (e.g., `_ga_strategy = GeneticAlgorithmStrategy()`). If a strategy mutates `self.config` or internal state during a request under concurrent FastAPI workloads, race conditions will occur. |
| **Finding 3.8** | **ALNS Missing DoE Param Space** | **VERIFIED** | **Evidence:** [param_spaces.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/param_spaces.py#L20-L70).<br>• While `"E2BSO-TSP"`, `"R2DMA-TSP"`, `"P-AOEA-TSP"`, etc. are defined, `"ALNS-TSP"` is completely absent in `SOTA_PARAM_SPACES`, resulting in empty parameter sweeps during tuning. |
| **Finding 3.9** | **Triple Local Search** | **VERIFIED** | **Evidence:** Local search is duplicated across three files:<br>1. [local_search.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/utils/local_search.py) (Production wrapper layer)<br>2. [multi_layer_ls.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/strategies/sota_common/multi_layer_ls.py) (Research FAZ 0 SOTA)<br>3. [ls_engine.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/sota_tsp/ls_engine.py) (SOTA TSP core kernel) |
| **Finding 3.10** | **Signal Handler Conflict** | **VERIFIED** | **Evidence:** Both `cli_engine.py` and `smart_benchmark.py` register their own `signal.SIGINT` handlers at import time. This causes registration conflicts where the last imported module overrides the active handler. |
| **Finding 3.11** | **Scheduling Logic in Route Handler** | **VERIFIED** | **Evidence:** [optimization.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/routers/optimization.py).<br>• The helper `_calculate_scheduled_times` (~120 lines of complex forward/backward scheduling) is nested directly inside the FastAPI route handler file. |
| **Finding 3.12** | **ProblemInstance Mixed Concerns** | **VERIFIED** | **Evidence:** [models.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/models.py#L5-L25).<br>• The single `ProblemInstance` dataclass contains both TSPLIB-specific fields (`edge_weight_type`, `optimal`, `category`) and CVRPTW-specific production fields (`capacity`, `time_windows`, `num_vehicles`). |
| **Finding 3.13** | **Optimals Dictionary Divergence** | **VERIFIED** | **Evidence:** [tsplib_parser.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/tsplib_parser.py#L43-L63) (63 entries) vs. [benchmark_utils.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/benchmark_utils.py#L29-L68) (129 entries).<br>• The shared kernel possesses a limited subset of optimals, which can result in divergent benchmark gaps when validated against the different scopes. |

---

## 2. The Dual-Engine Cohabitation Blueprint

To ensure clean, scalable cohabitation of the production-grade API and the academic DOE benchmark workflows, we propose a strict, layered architectural blueprint centered around the shared kernel (`uniride_core`) acting as a **pure mathematical optimization layer**.

### 2.1 Decoupled Layered Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                         │
│                                                                        │
│   ┌───────────────────────────────────┐    ┌───────────────────────┐   │
│   │    Engine A: Production API       │    │  Engine B: Academic   │   │
│   │    (FastAPI + Supabase Hooks)     │    │  Benchmark (CLI/UI)   │   │
│   └─────────────────┬─────────────────┘    └───────────┬───────────┘   │
└─────────────────────┼──────────────────────────────────┼───────────────┘
                      │                                  │
                      ▼                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            ADAPTER/SERVICE LAYER                       │
│                                                                        │
│   ┌───────────────────────────────────┐    ┌───────────────────────┐   │
│   │      Production Adapters          │    │   Research Harness    │   │
│   │   (e.g., CVRPTW Split Decoders,   │    │  (Optuna Tuning, SQL  │   │
│   │   String-to-Int Map Adapters)     │    │  TSPLIB Cache Sync)   │   │
│   └─────────────────┬─────────────────┘    └───────────┬───────────┘   │
└─────────────────────┼──────────────────────────────────┼───────────────┘
                      │                                  │
                      └─────────────────┬────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   PURE CORE KERNEL LAYER (uniride_core)                │
│                                                                        │
│   ┌───────────────────────────┐             ┌──────────────────────┐   │
│   │    Canonical Math Models  │             │ Numba Metaheuristics │   │
│   │   (Inherited / Protocols) │             │ (E2BSO, R2DMA, etc.) │   │
│   └───────────────────────────┘             └──────────────────────┘   │
│                                                                        │
│   (Zero external framework imports, Zero deployment package knowledge) │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Architectural Principles

1. **Pure Kernel Isolation (`uniride_core`):** The shared kernel must be fully self-contained. It should have absolutely no knowledge of how `optimizer_api` or `academic_benchmark` organizes their configurations, database, or test files. 
2. **Standardized Optimization Contracts:** Core algorithms operate exclusively on mathematical abstractions—integer-indexed adjacency matrices (`List[List[float]]`) and integer arrays (`List[int]`).
3. **Encapsulated Data Mapping:**
   - **Production (CVRPTW):** The production adapters in `optimizer_api/strategies/` map student location string IDs to pure integers, execute the underlying metaheuristic via the kernel, and decode the resulting integer tour into vehicle routes with arrival windows using split decoders.
   - **Academic (TSP Benchmark):** The academic benchmark engine loads TSPLIB files, builds integer-indexed coordinates, and pipes them directly to the exact same core metaheuristic kernel, ensuring 100% mathematical reproducibility.
4. **Data Model Decoupling via Inheritance:** `ProblemInstance` is split into clean, single-concern subclasses inheriting from a base model.

---

## 3. Safe Refactoring Recommendations

These concrete "Before vs. After" structural changes solve the verified issues safely, ensuring backward compatibility.

### 3.1 Decouple `ProblemInstance` (Solving 3.12)

**Before:** A single monolithic class containing mixed attributes.
```python
# uniride_core/models.py
@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    
    # TSPLIB specific
    edge_weight_type: str = "EUC_2D"
    optimal: Optional[float] = None
    
    # Production CVRPTW specific
    capacity: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
```

**After:** Clean inheritance model preserving polymorphic properties.
```python
# uniride_core/models.py
@dataclass
class BaseProblemInstance:
    """Core mathematical problem representation."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]] = field(default_factory=list)
    dist_matrix: Optional[List[List[float]]] = None
    knn_mask: Optional[Dict[int, List[int]]] = None

@dataclass
class TSPProblemInstance(BaseProblemInstance):
    """Academic TSPLIB benchmark instance."""
    optimal: Optional[float] = None
    category: str = "small"
    source: str = "tsplib"
    problem_type: str = "tsp"
    edge_weight_type: str = "EUC_2D"
    file_path: Optional[str] = None

@dataclass
class CVRPTWProblemInstance(BaseProblemInstance):
    """Production-grade school bus routing instance."""
    capacity: Optional[int] = None
    num_vehicles: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
    depot_index: int = 0
    problem_type: str = "cvrptw"
```

---

### 3.2 Thread-Safe Strategy Factory (Solving 3.6)

**Before:** Stateful objects instantiated as global module singletons.
```python
# optimizer_api/strategies/__init__.py
_ga_strategy = GeneticAlgorithmStrategy()
STRATEGY_REGISTRY = {
    "genetic_algorithm": _ga_strategy,
}
```

**After:** Instantiate fresh, stateless instances per request, or implement thread-local storage to prevent race conditions.
```python
# optimizer_api/strategies/__init__.py
from typing import Dict, Type, Optional
import threading

STRATEGY_CLASSES: Dict[str, Type[BaseRoutingStrategy]] = {
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "ga": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    "e2bso": E2BSoStrategy,
}

_thread_local = threading.local()

def get_strategy(name: str) -> Optional[BaseRoutingStrategy]:
    """Retrieves a thread-safe, isolated instance of the requested strategy."""
    name_lower = name.lower()
    if name_lower not in STRATEGY_CLASSES:
        return None
        
    if not hasattr(_thread_local, 'strategies'):
        _thread_local.strategies = {}
        
    if name_lower not in _thread_local.strategies:
        cls = STRATEGY_CLASSES[name_lower]
        # Fresh instantiation ensures no shared-state mutation
        _thread_local.strategies[name_lower] = cls()
        
    return _thread_local.strategies[name_lower]
```

---

### 3.3 Dynamic Env-Based Pathing in parser (Solving 3.4)

**Before:** Reverse-dependent hardcoded relative paths.
```python
# uniride_core/algorithms/tsplib_parser.py
TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..',
                                'optimizer_api', 'tests', 'tsplib_data')
```

**After:** Decoupled config falling back to a clean top-level directory or environment variables.
```python
# uniride_core/algorithms/tsplib_parser.py
import os

# Eliminates reverse dependency: allows environment override, defaults to top-level folder
TSPLIB_DATA_DIR = os.environ.get(
    "TSPLIB_DATA_DIR",
    os.path.join(os.path.dirname(__file__), '..', '..', 'tsplib_data')
)
```

---

### 3.4 Fix SOTA Benchmark Orchestration (Solving 3.2)

**Before:** Attempting to import non-existent file.
```python
# optimizer_api/run_sota_benchmark.py
from academic_benchmark.run_sota_benchmark import main
```

**After:** Properly delegate to the consolidated `sota_engine.py` in `academic_benchmark`.
```python
# optimizer_api/run_sota_benchmark.py
"""
SOTA Benchmark Runner — delegates execution to the consolidated academic_benchmark engine.
"""
import sys
import argparse
from academic_benchmark.sota_engine import run_engine_default, run_engine_tuning, ALL_ALGOS

def main():
    parser = argparse.ArgumentParser(description="UniRide SOTA Benchmark Gateway")
    parser.add_argument("--algo", nargs="+", default=ALL_ALGOS, help="Algorithms to benchmark.")
    parser.add_argument("--problems", nargs="+", default=None, help="TSPLIB problem names.")
    parser.add_argument("--runs", type=int, default=3, help="Runs per configuration.")
    args = parser.parse_args()

    # Load problem instances via academic loader
    from academic_benchmark.cli_engine import load_problems
    all_problems = load_problems()
    
    selected_problems = all_problems
    if args.problems:
        wanted = {p.strip().lower() for p in args.problems}
        selected_problems = [p for p in all_problems if p.name.lower() in wanted]

    print(f"Executing SOTA benchmarks on {len(selected_problems)} instances...")
    metadata = {"best_params": {}}
    run_engine_default(selected_problems, args.algo, n_runs=args.runs, workers=4, metadata=metadata)

if __name__ == "__main__":
    sys.exit(main())
```

---

### 3.5 Consolidate Optimals (Solving 3.13)

**Before:** Two distinct dictionaries with divergent counts.

**After:** Unify all optimal mappings into `uniride_core` and import them back into `academic_benchmark` to ensure a single source of truth.
```python
# In uniride_core/algorithms/tsplib_parser.py
# Move the complete 129-entry dictionary here
TSPLIB_OPTIMALS: Dict[str, int] = {
    "berlin52": 7542,
    # ... all 129 entries ...
}

# In academic_benchmark/benchmark_utils.py
# Import from shared kernel to keep DRY and unified
from uniride_core.algorithms.tsplib_parser import TSPLIB_OPTIMALS
```

---

### 3.6 Extract Scheduling Router Logic (Solving 3.11)

**Before:** High-complexity helper embedded directly inside `optimization.py` route handler.

**After:** Create `optimizer_api/utils/scheduling.py` and move `_calculate_scheduled_times` there, keeping routes clean and purely focused on request validation and response mapping.
```python
# optimizer_api/utils/scheduling.py
from typing import List, Dict
from models.schemas import VehicleRoute, OptimizationRequest

def calculate_scheduled_times(
    routes: List[VehicleRoute],
    request: OptimizationRequest,
    distance_matrix: Dict[str, Dict[str, float]]
) -> List[VehicleRoute]:
    """Calculates optimal drop-off/pick-up arrival times based on constraints."""
    # ... Move the 120-line logic here ...
    return routes
```

---

### 3.7 Add ALNS Parameter Space (Solving 3.8)

**Before:** ALNS-TSP had no dictionary entry.

**After:** Append ALNS configuration properties into `SOTA_PARAM_SPACES` within `academic_benchmark/param_spaces.py`.
```python
# academic_benchmark/param_spaces.py
SOTA_PARAM_SPACES.update({
    "ALNS-TSP": {
        "max_iterations":       {"type": "int",   "doe": [500, 1000, 2000],   "optuna": (200, 3000)},
        "remove_ratio":         {"type": "float", "doe": [0.10, 0.20, 0.30],  "optuna": (0.05, 0.40)},
        "weight_update_factor": {"type": "float", "doe": [0.1, 0.3, 0.5],     "optuna": (0.05, 0.7)},
        "sa_initial_temp":      {"type": "float", "doe": [100.0, 500.0],      "optuna": (50.0, 1000.0)},
        "sa_cooling_rate":      {"type": "float", "doe": [0.95, 0.98, 0.99],  "optuna": (0.90, 0.995)},
    }
})
```

---

## 4. Actionable Fix Plan

Below is the structured, step-by-step checklist plan to apply these refactorings safely without disrupting running services:

### Phase 1: Security & Immediate Blocker Resolution (Priority: Critical)
- [ ] **Rotate compromised API key:** Deactivate the current compromised Azure OpenAI key in the cloud dashboard.
- [ ] **Secure `test_direct.py`:** Update `test_direct.py` to use environment variable bindings (`AZURE_OPENAI_API_KEY`).
- [ ] **Repair broken benchmark script:** Apply the fix to `optimizer_api/run_sota_benchmark.py` so it properly routes calls to `academic_benchmark/sota_engine.py` instead of the non-existent package.
- [ ] **Remove Reverse Dependency:** Change the hardcoded data directory in `uniride_core/algorithms/tsplib_parser.py` to use environment variable defaults.

### Phase 2: Decoupling and Architecture Cleanliness (Priority: High)
- [ ] **Decouple ProblemInstance:** Split `ProblemInstance` in `uniride_core/models.py` into a polymorphic structure with subclasses for TSP (benchmarks) and CVRPTW (production) models. Update reference types across academic engine loaders.
- [ ] **Thread-Safe Strategies:** Replace the strategy instantiations inside `optimizer_api/strategies/__init__.py` with a thread-local factory lookup function `get_strategy()` to eliminate FastAPI singleton race risks.
- [ ] **Consolidate TSPLIB Optimals:** Re-export the 129-entry TSPLIB optima dictionary from the shared kernel as the single source of truth, and make `academic_benchmark/benchmark_utils.py` import from the core.
- [ ] **Extract scheduling helper:** Create `optimizer_api/utils/scheduling.py` and move `_calculate_scheduled_times` out of the route handler file `optimizer_api/routers/optimization.py`.

### Phase 3: SOTA Harmonization & Clean-up (Priority: Medium)
- [ ] **ALNS Param Spaces:** Insert the `ALNS-TSP` parameters into `academic_benchmark/param_spaces.py` so that ALNS tuning sweeps are fully operational.
- [ ] **Consolidate SOTA duplicate folders:** Migrate any remaining localized logic in `optimizer_api/strategies/sota_common/` into the consolidated kernel folder `uniride_core/algorithms/sota_tsp/`. 
- [ ] **Deprecate sota_common:** Update `faz0_interactive.py` to import from the core `uniride_core.algorithms.sota_tsp` package instead of `sota_common` and delete `optimizer_api/strategies/sota_common/`.
- [ ] **Unify Local Search:** Ensure the wrappers in `optimizer_api/strategies/` use `uniride_core/algorithms/sota_tsp/ls_engine.py` directly for optimization loops.

### Phase 4: Verification and Quality Assurance (Priority: Low)
- [ ] **FastAPI Integration Tests:** Run optimization test queries concurrently using tools like Apache Bench to verify the thread-safety of strategy instances.
- [ ] **DOE Validation Runs:** Run `python run_sota_benchmark.py --algo E2BSO-TSP` to verify the benchmark pipeline runs perfectly end-to-end.
- [ ] **Gradual TypeScript Linting migration:** Change ESLint rules from "off" to "warn" as defined in the review to begin gradually migrating the frontend towards standard compliance.
