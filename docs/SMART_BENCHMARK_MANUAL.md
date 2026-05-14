# 🎓 UniRide Smart Benchmark Engine - Official Manual & Academic Guide

This document serves as both a practical "How-To" guide for developers/researchers and a comprehensive methodological reference for academic paper writing. The **Smart Benchmark Engine** is a high-performance, strictly typed, configuration-driven evaluation framework designed specifically for meta-heuristic optimizations (e.g., TSP/ATSP variants).

---

## 1. 🚀 How to Use the Engine

### Starting the Engine
Launch the benchmark engine via the terminal:
```bash
python academic_benchmark/smart_benchmark.py
```

### Execution Modes
Upon launching, you will be presented with a menu containing 4 distinct operational modes:

#### Mode 1: Interactive Benchmark
* **Use Case:** Standard testing and quick evaluation.
* **Flow:** Prompts you to select problems (e.g., `1,2,5-8` or aliases like `small`), select algorithms, and evaluates them immediately using a multiprocessing pool.
* **Smart Caching:** It automatically detects if a specific algorithm-problem combination has already been evaluated and prompts you to either **[S]kip** or **[R]e-run** to save computational time.

#### Mode 2: Generate Config Only (Configuration-as-Code)
* **Use Case:** Setting up strictly reproducible, long-running batch experiments.
* **Flow:** Allows you to select problems and algorithms, but *does not run them*. Instead, it generates a mathematically precise `run_config.json` file in the `benchmark_db/configs` directory. You can manually edit this JSON to force specific hyperparameters (e.g., forcing `pop_size: 200` on a single specific problem).

#### Mode 3: Run from Config
* **Use Case:** Executing the reproducible pipelines generated in Mode 2, or running the engine headlessly on a remote server.
* **Flow:** Instantly reads `run_config.json`, calculates the task graph, and distributes the exact predefined tasks across the multiprocessing worker pool. 

#### Mode 4: Optuna Parameter Tuning (Bayesian Optimization)
* **Use Case:** Automatically discovering the mathematical limits of an algorithm.
* **Flow:** Uses **Bayesian Optimization** (`optuna`) instead of brute-force Grid Search. It dynamically prunes bad hyperparameter combinations and searches the hyper-dimensional parameter space to find the optimal configuration (e.g., `mutation_rate`, `pop_size`) in significantly fewer iterations.

---

## 2. 📊 The Academic Web Dashboard

The framework includes a fully interactive web dashboard designed to output publication-ready statistics.

To launch the dashboard:
```bash
streamlit run academic_benchmark/dashboard.py
```

### Dashboard Tabs
1. **🏆 Leaderboard & LaTeX:** Displays the aggregated performance (Avg Gap, Avg Time) of all algorithms. It features a one-click **"Generate Academic LaTeX Code"** button that automatically bold-faces the best performing metrics according to academic journal standards.
2. **📊 Statistical Robustness (Box Plots):** Visualizes the stochastic variance of algorithms across multiple independent runs, proving stability over time.
3. **🎛️ DoE Parameter Analysis:** Plots the hyperparameter grid searches, correlating parameter sensitivity directly to optimality gaps.
4. **🔬 Statistical Significance (Wilcoxon Test):** Performs automated pairwise **Wilcoxon Signed-Rank** non-parametric tests ($p < 0.05$) between a baseline and a proposed algorithm. It outputs a literal text statement ready for your methodology section (e.g., *"\textbf{Proposed-GA} statistically significantly outperforms Baseline-PSO..."*).
5. **📉 Convergence Curves:** Parses `convergence_profile` arrays from raw logs to plot Exploration vs. Exploitation line charts, visualizing exactly *when* an algorithm converges to local optima.

---

## 3. ✍️ Academic Methodology (Copy-Paste for Papers)

The following sections detail the strict architectural and mathematical mechanisms implemented in the engine. You may adapt these texts directly into the **Methodology** or **Experimental Setup** sections of your academic papers.

### 3.1. Unified Strategy & Registry Architecture
**Text for Paper:**
> "To ensure rigorous, identical-condition comparisons between competing algorithms, the experimental framework was centralized using a strict Strategy and Registry software pattern. All meta-heuristics (e.g., Memetic GA, PSO, E2BSO) were constrained to a canonical `ProblemInstance` and `RunResult` dataclass signature. This architectural decoupling guarantees that variations in performance are strictly algorithmic, completely eliminating latent schema-drift or parser-level biases that commonly plague fragmented multi-engine benchmarks."

### 3.2. Hardware-Independent Metrics (MaxFE)
**Text for Paper:**
> "Recognizing that raw execution time (CPU seconds) is highly sensitive to hardware architectures, thermal throttling, and background OS interrupts, this framework utilizes Maximum Function Evaluations (MaxFE) as the primary hardware-independent metric of computational complexity. The evaluation engine incrementally tracks distance-matrix lookups and kernel execution counts, allowing for a pure mathematical comparison of convergence efficiency decoupled from hardware speeds."

### 3.3. Asynchronous Warmup & Lock-Free Multiprocessing
**Text for Paper:**
> "Meta-heuristics evaluated in this study rely on strict Just-In-Time (JIT) compilation vectors (via LLVM/Numba). To overcome the severe process-locking and cache contention artifacts inherent to concurrent process spawning in Windows OS environments, the benchmark engine implements an asymmetrical 'Warmup Phase'. The main thread forces a sequential JIT compilation of all requested algorithmic kernels against a minimal dummy dataset (e.g., `burma14`, $N=14$). This pre-compilation guarantees that subsequent multiprocessing worker pools execute entirely in lock-free $O(1)$ load time, maximizing CPU utilization to near 100%."

### 3.4. $O(N \cdot K)$ KNN Subgraph Sparsification
**Text for Paper:**
> "Standard combinatorial local search mechanisms (e.g., 2-opt, 3-opt) exhibit $O(N^2)$ or $O(N^3)$ computational complexity, becoming computationally intractable for large-scale instances ($N > 500$). To mitigate this, our framework implements an advanced $K$-Nearest Neighbor (KNN) geographical sparsification mask. During problem initialization, the engine pre-computes an optimal localized subgraph ($K=20$) for every node. Exploitation operators limit their stochastic edge-swap attempts exclusively to these geographic neighbors, effectively bounding local search complexity to $O(N \cdot K)$ without sacrificing global optimality."

### 3.5. Bayesian Hyperparameter Tuning (Optuna)
**Text for Paper:**
> "Traditional Cartesian Grid Search Design of Experiments (DoE) scales exponentially and frequently misses optimal floating-point regions. In this methodology, algorithmic hyperparameters (e.g., population sizes, mutation rates, constriction coefficients) were tuned using Tree-structured Parzen Estimator (TPE) based Bayesian Optimization. This dynamic approach models the hyperparameter space probabilistically, directing search efforts toward highly promising parameter regions and aggressively pruning poor configurations, yielding highly optimized solvers in a fraction of standard computational time."
