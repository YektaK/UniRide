# Prompt for State-of-the-Art (SOTA) Algorithms

**TASK:** Write a detailed academic section titled "3. Experimental Framework and SOTA Evaluation Methodology" for a research paper focusing on high-performance State-of-the-Art (SOTA) TSP algorithms such as E²BSO, R²DMA, and P-AOEA.

**CONTEXT & ARCHITECTURE:**
- **Framework:** The research employs a "Unified SOTA Benchmark Engine" (`master_sota_engine.py`) designed for high-fidelity evaluation of complex, modern TSP solvers.
- **Scalability:** The framework utilizes a "Consolidated Architecture" that manages computational resource allocation through a `ProcessPoolExecutor`, specifically optimized for large-scale TSPLIB instances (up to pr2392) on Windows-based workstations.
- **Adaptive Evaluation:** The methodology includes adaptive local search budgets and time-matrix integrations, ensuring that algorithms are tested under realistic and varied constraint scenarios.

**SCIENTIFIC PRINCIPLES TO EMPHASIZE:**
1. **Comparative Benchmarking Rigor:** Emphasize the standardized environment where SOTA algorithms are compared against each other using synchronized seed management and identical computational budgets to ensure fairness.
2. **Robustness & Stability:** Highlight the framework's ability to handle high-complexity solvers without memory leaks or synchronization deadlocks, even during extended benchmark cycles on massive problem dimensions.
3. **Incremental Data Persistence:** Detail the real-time logging mechanism where each trial's results are cached and verified against historical metadata, allowing for multi-stage experimental verification without data loss.

**STYLE & FORMAT:**
- **Language:** High-level Academic English (IEEE/Elsevier standard).
- **Voice:** Passive voice, objective tone.
- **Structure:** Use subheadings like:
  - 3.1. Unified Evaluation Framework for SOTA Solvers
  - 3.2. Scalability Management and Multi-Core Distribution
  - 3.3. Algorithmic Comparison Protocols and Data Integrity
