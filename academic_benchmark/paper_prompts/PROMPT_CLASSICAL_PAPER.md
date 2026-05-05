# Prompt for Classical Meta-heuristics (Numba-Optimized)

**TASK:** Write a detailed academic section titled "3. Experimental Framework and Computational Methodology" for a research paper focusing on optimized classical meta-heuristic algorithms (GA, PSO, GWO, HHO) for the Traveling Salesman Problem.

**CONTEXT & ARCHITECTURE:**
- **Framework:** The study utilizes a custom-built "Numba-Accelerated Benchmark Engine" (`master_numba_engine.py`).
- **Core Technology:** Just-In-Time (JIT) compilation via the Numba library is employed to eliminate Python's interpreted overhead, achieving execution speeds comparable to C++ while maintaining algorithmic flexibility.
- **Parallelism:** A robust Windows-safe parallel processing architecture using `ProcessPoolExecutor` was implemented to ensure high throughput and stability across multi-core systems.

**SCIENTIFIC PRINCIPLES TO EMPHASIZE:**
1. **Systematic Parameter Tuning (DoE):** Explain that hyperparameters were not manually selected or randomized. Instead, a "Design of Experiments" (DoE) module performed a systematic grid search to identify globally optimal configurations, eliminating human bias and ensuring peak performance across diverse TSPLIB instances.
2. **Computational Rigor:** Detail the "Warm-up" protocol where initial JIT compilation times are excluded from benchmark measurements to ensure that reported time complexities reflect only the algorithmic execution.
3. **Reproducibility & Integrity:** Mention the use of incremental result persistence (CSV) and metadata-driven state management (`metadata.json`), ensuring that every experiment is verifiable and 100% reproducible.

**STYLE & FORMAT:**
- **Language:** High-level Academic English (IEEE/Elsevier standard).
- **Voice:** Passive voice, objective tone.
- **Structure:** Use subheadings like:
  - 3.1. JIT-Optimized Meta-heuristic Implementation
  - 3.2. Parameter Standardization via Design of Experiments
  - 3.3. Parallel Execution and Computational Stability
