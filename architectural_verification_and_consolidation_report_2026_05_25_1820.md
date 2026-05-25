# Architectural Verification Report: Production Workflows & Consolidation Strategy

**Date:** May 25, 2026  
**Time:** 18:20:24 (Local Time: UTC+3)  
**Author/Creator:** Antigravity, a powerful agentic AI coding assistant designed by the Google DeepMind team working on Advanced Agentic Coding.  
**Model Name:** Gemini 3.5 Flash (High)  
**Role:** Senior Systems Architect, Principal Engineer, and Academic Research Lead  

---

## 1. Executive Summary

This report presents a thorough, direct structural verification of the production workflows in the `UniRide` dual-engine repository and outlines a comprehensive architectural consolidation strategy. 

The primary objective is to verify how **Engine A (Production API)** utilizes "Divide, Optimize, and Combine" (Pipeline A) and "Route-First, Cluster-Second" (Pipeline B) patterns, and how these workflows communicate with the **Next.js Web Display Suite**. Lastly, we propose an elegant consolidation layout where the mathematical models are centralized inside the shared kernel `uniride_core` to achieve 100% DRY compliance and mathematical consistency between research and production execution paths.

---

## 2. The Two Production Workflows (Pipeline A vs. Pipeline B)

Our structural inspection of `optimizer_api` verified the presence of two core optimization workflows designed to solve the Capacitated Vehicle Routing Problem with Time Windows (CVRPTW):

```
                       STUDENTS DATA (JSON/Supabase)
                                     │
             ┌───────────────────────┴───────────────────────┐
             ▼                                               ▼
    [PIPELINE A]                                    [PIPELINE B]
    Cluster-First, Route-Second                     Route-First, Cluster-Second
    (Divide, Optimize, Combine)                     (Giant Tour + Split Decoder)
             │                                               │
  1. DIVIDE: Group students into                  1. ROUTE-FIRST: Solve single giant
     clusters (Sweep / K-Means)                      TSP tour over all students
             │                                               │
  2. OPTIMIZE: Solve TSP per                      2. CLUSTER-SECOND: Partition giant
     cluster (GA / PSO / GWO / HHO)                  tour via Dynamic Programming Split
             │                                       (Prins' DP / Linear Split Decoder)
  3. COMBINE: Assemble routes into                           │
     final vehicle schedule                                  │
             │                                               │
             └───────────────────────┬───────────────────────┘
                                     ▼
                      FINAL ROUTE STEPS + TIME WINDOWS
```

### 2.1 Workflow 1: Pipeline A — "Divide, Optimize, and Combine" (Cluster-First, Route-Second)
* **Divide:** The FastAPI controller parses the student node coordinates. The `VehicleCalculator.calculate` method (in `utils/clustering.py`) groups the students into clusters using the selected clustering algorithm (Sweep, K-Means, or K-Medoids) based on physical student capacities (`sw_capacity`, `so_capacity`) and `max_tour_time` limits.
* **Optimize:** For each cluster, a dedicated `route_optimizer` callback runs a TSP solver (like Genetic Algorithm in `strategies/ga_strategy.py` or PSO in `strategies/pso_strategy.py`) to compute the optimal tour sequence *inside* that cluster.
* **Combine:** The optimized paths of each vehicle are combined into a final `OptimizationResponse` list of vehicle route steps.
* **Algorithms:** `ga`, `pso`, `gwo`, `hho`.

### 2.2 Workflow 2: Pipeline B — "Route-First, Cluster-Second" (Split Decoder Pattern)
* **Route-First:** This paradigm ignores capacities initially and treats all students as one giant TSP problem. It runs a metaheuristic (like GA, PSO, or SOTA solvers) to optimize a single continuous "Giant Tour" over all coordinates.
* **Cluster-Second:** The giant tour is then partitioned (clustered) into multiple valid vehicle routes using an **Optimal Split Decoder** (based on Prins' 2004 Dynamic Programming or the O(n) Linear Split Decoder located in `utils/split_decoder.py` and `utils/linear_split_decoder.py`). This guarantees that routes satisfy student capacities and travel-time constraints.
* **Algorithms:** `ga_split`, `pso_split`, `gwo_split`, `hho_split`.

---

## 3. The Web Display Suite & Server Execution Flow

The codebase implements a complete **Server-Side Optimization & Client-Side Display** model:

```
┌──────────────────────────────────────┐
│       Next.js 16 Web Display         │
│                                      │
│   ┌───────────────┐ ┌────────────┐   │
│   │ SOTA Dashboard│ │ IE Sandbox │   │
│   └───────┬───────┘ └──────┬─────┘   │
└───────────┼────────────────┼─────────┘
            │                │ HTTP REST API (Port 8000)
            ▼                ▼
┌──────────────────────────────────────┐
│        Python FastAPI Server         │
│                                      │
│   ┌───────────────┐ ┌────────────┐   │
│   │   /optimize   │ │  /compare  │   │
│   └───────┬───────┘ └──────┬─────┘   │
└───────────┼────────────────┼─────────┘
            │                │ imports
            ▼                ▼
┌──────────────────────────────────────┐
│     Pure Mathematical Kernels        │
│    (Adjacency Matrices, Numba JIT)   │
└──────────────────────────────────────┘
```

1. **The Server (`optimizer_api`):** Exposes a FastAPI router (`optimization.py`). It receives POST requests at `/api/v1/optimize` and `/api/v1/compare`, loads the student coordinates from the database (Supabase), performs the heavy multi-threaded CPU-bound optimizations, computes travel times and backward/forward schedules, and returns standard JSON payloads.
2. **The Client Display (`src/`):** A Next.js 16 + Tailwind CSS v4 dashboard client.
   - It utilizes `services/optimizer-service.ts` to trigger route optimizations and compare multiple algorithms.
   - Key UI portals include the **SOTA Dashboard** (`src/app/page.tsx`), **IE Sandbox** (`src/app/(app)/admin/sandbox/`), **Algorithm Compare Suite** (`src/app/(app)/admin/compare/`), and the **TSPLIB Benchmark Suite** (`src/app/(app)/admin/benchmark/`).
   - The web app displays the optimized route metrics, path maps, vehicle lists, driver assignments, and hourly bottleneck demand graphs computed by the Python server.

---

## 4. The Unified Consolidation Strategy (under `uniride_core`)

By moving all algorithmic logic into the pure Python shared kernel (`uniride_core`), both production and academic workflows become cleaner, completely eliminating mathematical code duplication:

### 4.1 Proposed Consolidated Dizin Yapısı (Folder Layout)

```directory
uniride_core/
├── __init__.py
├── models.py                       # Inherited CVRPTW & TSP dataclasses
├── algorithms/
│   ├── __init__.py
│   ├── distance.py                 # Single source of truth distance functions
│   │
│   ├── clustering/                 # Workflow A: "DIVIDE" layer
│   │   ├── __init__.py
│   │   ├── vehicle_calculator.py   # Refactored CVRP partitioning engine
│   │   ├── sweep.py
│   │   └── kmeans.py
│   │
│   ├── split/                      # Workflow B: "CLUSTER-SECOND" layer
│   │   ├── __init__.py
│   │   ├── prins_split.py          # Dynamic Programming Split Decoder
│   │   └── linear_split.py         # Bounded linear split
│   │
│   └── solvers/                    # Core TSP/CVRP solvers
│       ├── __init__.py
│       ├── classical/
│       │   ├── ga_solver.py        # Stateless GA
│       │   └── pso_solver.py       # Stateless PSO
│       └── sota/
│           ├── e2bso.py            # Enhanced Entropy-Balanced Swarm (FAZ 1)
│           ├── r2dma.py            # Resonance-Supported Destroy/Merge (FAZ 2)
│           └── paoea.py            # Production Adaptive Operator Evolution (FAZ 3)
```

### 4.2 How Both Projects Share the Consolidated Kernel

#### 1. In Production (`optimizer_api`):
The production environment operates as a high-performance REST delivery shell. Its strategies act as lightweight wrapper adapters:
* **For Pipeline A (e.g., `ga_strategy.py`):** It imports `VehicleCalculator` and `GASolver` from `uniride_core.algorithms`. It runs the *divide* step using the calculator, *optimizes* the routes per cluster using the solver, and *combines* them into the production route steps payload.
* **For Pipeline B (e.g., `ga_split_strategy.py`):** It executes `GASolver` on all nodes collectively to get a giant tour, and then calls `uniride_core.algorithms.split.prins_split` to slice the tour into valid vehicle paths.

#### 2. In Academic Benchmarks (`academic_benchmark`):
The research CLI loads problems directly, queries SQLite parameter sweeps, and invokes the exact same mathematical solvers (`uniride_core.algorithms.solvers`) using identical input signatures (integer-indexed distance matrices). This ensures that any algorithmic improvement made by research is **instantaneously inherited by the production API**.
