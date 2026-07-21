# Academic Algorithm Validation Audit — GWO, HHO, 2-opt, and 3-opt

**Audit date:** 2026-07-17  
**Scope:** `academic_benchmark`, `academic_benchmark/bildiri2026`, relevant `uniride_core` registry/local-search paths, and Git history.  
**Status:** Evidence-based reconciliation of the existing Ultimate Audit and an independent external review. No source-code changes were made as part of this audit.

## Executive decision

The current repository must **not** be used to publish a GWO-vs-HHO-vs-2-opt-vs-3-opt TSPLIB comparison.

This is not because GWO/HHO omit a TSP city: that external finding is incorrect. In the matrix-native path, node `0` is an intentionally fixed cycle anchor (or a depot for routing instances); the returned working tour omits the anchor but the scored closed cycle includes it. Fixing one city at the start of a Hamiltonian cycle does not remove it from the search space because cyclic tours are rotation-invariant.

The comparison remains scientifically invalid for other, confirmed reasons: the only registry 3-opt entry crashes on matrix-native TSP instances; GWO/HHO are memetic 2-opt hybrids; budgets, seeds, and initialization policies differ; direct `bildiri2026` scripts bypass central TSPLIB distance handling; and the accelerated and fallback 3-opt implementations do not execute the same neighborhood.

## Evidence and verification performed

The following checks were run against the current `WIP` checkout.

| Check | Result | Interpretation |
|---|---:|---|
| Focused academic registry, ATSP, and 3-opt tests | 25 passed, 1 skipped | Registry smoke coverage is present; the sole Numba 3-opt test is skipped without Numba. |
| Shared-core TSP and local-search tests | 24 passed | Core TSP/local-search behavior is covered at a basic level. |
| TSPLIB distance-property tests | 45 passed | Central EUC_2D/ATT/GEO/CEIL_2D helper properties pass. |
| Controlled 8-node asymmetric matrix probe | GWO/HHO registry tours were full valid permutations and costs recomputed exactly | Refutes the alleged missing-node/fabricated-tour defect. |
| Same probe for `Numba-2-opt` and `Numba-3-opt-bounded` | Both raised `IndexError: index 0 is out of bounds for axis 0 with size 0` | Confirms the registry local-search blocker. |
| Runtime environment probe | Python 3.14.3, NumPy 2.5.1; Numba import fails because NumPy must be <= 2.4 | JIT-specific evidence cannot be claimed in this environment. |

The focused tests establish implementation facts, not comparative algorithm superiority. Existing tests do not record objective-evaluation counts, validate a complete 3-opt neighborhood, or establish a fair study protocol.

## Reconciliation of the external audit

| External claim | Reconciliation | Evidence |
|---|---|---|
| F1: GWO/HHO omit node 0 and therefore solve an incomplete TSP | **Rejected.** The raw solver deliberately returns customer nodes only for matrix/depot representation. Its evaluated cycle is `[0] + tour + [0]`; all nodes are present exactly once. Fixing the cycle anchor is valid for both symmetric TSP and ATSP. | `BaseTSPSolver._initial_tour_nodes`, `_tour_length_matrix`, and `solve_with_matrix` in [`base_solver.py`](./bildiri2026/core/base_solver.py:39). |
| F2: Registry fabricates a different full tour | **Rejected.** Registry conversion prepends the one-indexed anchor to serialize the exact same cycle. Live recomputation of the converted tour matched `tour_cost` for GWO/HHO. | [`registry_setup.py`](./core/registry_setup.py:437). |
| F3: `Numba-2-opt` and `Numba-3-opt-bounded` crash on matrix-native TSP | **Confirmed.** Both entries reproduced the zero-size distance-matrix `IndexError`. | Legacy registration/execution path in [`registry_setup.py`](./core/registry_setup.py:178); local-search matrix handling in [`local_search_numba.py`](../uniride_core/algorithms/local_search_numba.py:131). |
| F4: Direct Bildiri and registry paths differ | **Partly confirmed.** They are distinct paths and do not form one reproducible experiment. However, anchoring node 0 in the matrix path is not itself a TSP defect. | [`3_run_benchmark.py`](./bildiri2026/3_run_benchmark.py:42), [`registry_setup.py`](./core/registry_setup.py:404). |
| F5: GWO/HHO embed 2-opt and are unfairly compared to bare local search | **Confirmed.** They are memetic hybrids, not pure GWO/HHO. | [`gwo_solver.py`](./bildiri2026/core/gwo_solver.py:119), [`hho_solver.py`](./bildiri2026/core/hho_solver.py:189). |
| F6: No working registry 3-opt is reachable for the target study | **Confirmed for the registry path.** The exposed `Numba-3-opt-bounded` entry crashes; the standalone `ThreeOptSolver` is direct-script only and is not a correct complete 3-opt implementation. | [`registry_setup.py`](./core/registry_setup.py:659), [`three_opt.py`](./bildiri2026/core/three_opt.py:33). |
| F7: Central TSPLIB rounding is correct | **Confirmed with an important boundary.** The shared helper now implements EUC_2D NINT, ATT, GEO, and CEIL_2D correctly. Standalone Bildiri scripts do not consistently use it. | [`distance.py`](../uniride_core/algorithms/distance.py:67), [`tsplib_benchmark.py`](./bildiri2026/benchmarks/tsplib_benchmark.py:75). |
| No-Numba fallback scores dummy `(0,0)` coordinates | **Rejected.** With a matrix installed, `_tour_length_fast` uses the matrix kernel path; if it must fall back, `tour_length()` dispatches to `_tour_length_matrix`, not Euclidean dummy coordinates. | [`base_solver.py`](./bildiri2026/core/base_solver.py:96). |

## Verified execution-path reality

| Study label | Actual current path | Experimental status |
|---|---|---|
| `Core-GWO-TSP`, `Core-HHO-TSP`, `Numba-GWO`, `Numba-HHO` | Registry override -> Bildiri `GWOOptimizer`/`HHOOptimizer` -> `solve_with_matrix()` -> anchored closed cycle | Mechanically valid cycle representation; unsuitable for a fair four-way paper as currently configured. |
| `Core-TwoOpt-TSP` | Shared-core `solve_two_opt_tsp()` through a matrix engine | A different implementation and search budget from Bildiri `TwoOptSolver`. |
| `Numba-2-opt`, `Numba-3-opt-bounded` | Legacy registry executor -> Numba local-search adapter | Broken on the reproduced matrix-native TSP case. |
| `bildiri2026/3_run_benchmark.py` | Direct `solve(coordinates)` with `TwoOptSolver`, `ThreeOptSolver`, Or-opt, GA, PSO | Does not register GWO or HHO. |
| `bildiri2026/benchmarks/tsplib_benchmark.py` | Direct coordinate solver calls | Does not register GWO/HHO and is safe only for explicitly controlled EUC_2D data. |

The shared engine factory registers `Core-TwoOpt-TSP`, GA, PSO, GWO, and HHO but no core 3-opt solver: [`engine_factory.py`](../uniride_core/algorithms/engine_factory.py:28). The routing alias for `Numba-3-opt-bounded` also maps to `Core-TwoOpt-TSP` for CVRP/CVRPTW aliases, which makes that label unsuitable for methodological claims outside a narrowly documented context: [`registry_setup.py`](./core/registry_setup.py:659).

## Confirmed algorithm and protocol defects

### 1. Registry 2-opt and 3-opt blocker

`Numba-2-opt` and `Numba-3-opt-bounded` fail before solving matrix-native TSP input. This is a release-blocking defect for any benchmark configuration that selects them. Smoke tests miss it because they do not exercise this exact legacy matrix route.

**Publication effect:** no registry result set containing either label is usable until the adapter receives a correctly shaped matrix and a regression test reproduces the former failure.

### 2. The Bildiri 3-opt neighborhood is not complete 3-opt

The direct Bildiri implementation generates seven reconnection cases in [`three_opt.py`](./bildiri2026/core/three_opt.py:33). Structural inspection and a symbolic edge-change probe show that this set includes 2-opt moves, only a subset of genuine 3-opt moves, and moves altering four edges. It omits the required segment-order exchange cases that make a complete 3-opt neighborhood.

The Numba implementation mirrors this definition: [`numba_accel.py`](./bildiri2026/core/numba_accel.py:162). It must be renamed as a custom bounded reconnection heuristic or replaced with a verified complete 3-opt implementation. It must not be reported as standard 3-opt.

The shared-core implementation has broader coverage of genuine 3-opt moves, but it is a separate implementation and cannot silently substitute for the Bildiri algorithm: [`local_search.py`](../uniride_core/algorithms/local_search.py:143).

### 3. GWO and HHO are memetic hybrid methods

Both optimizers apply 2-opt at initialization, periodically, and after termination:

- GWO initialization, periodic polishing, and final polish: [`gwo_solver.py`](./bildiri2026/core/gwo_solver.py:119), [`gwo_solver.py`](./bildiri2026/core/gwo_solver.py:200), [`gwo_solver.py`](./bildiri2026/core/gwo_solver.py:214).
- HHO initialization, periodic polishing, and final polish: [`hho_solver.py`](./bildiri2026/core/hho_solver.py:189), [`hho_solver.py`](./bildiri2026/core/hho_solver.py:257), [`hho_solver.py`](./bildiri2026/core/hho_solver.py:270).

This is a legitimate design if declared as **Memetic GWO-2opt** and **Memetic HHO-2opt**. It is not legitimate to attribute their outcome to bare GWO/HHO or compare them to an unpolished baseline without an ablation.

### 4. Budget, seed, and implementation inequity

The current methods do not consume comparable effort:

- Bildiri 2-opt defaults to ten starts and up to 10,000 passes: [`two_opt.py`](./bildiri2026/core/two_opt.py:25).
- Bildiri 3-opt defaults to a single start: [`three_opt.py`](./bildiri2026/core/three_opt.py:23).
- GWO/HHO use populations, iteration caps, early stopping, periodic 2-opt, and a final 2-opt budget.
- HHO rapid dives can evaluate several candidates for one hawk update.
- `RunResult.evaluations` exists but is not populated by the relevant executors: [`engine_core.py`](./engine_core.py:19).

The direct benchmark also derives its seed from the tuned model ID, so algorithms do not receive common random-number streams: [`3_run_benchmark.py`](./bildiri2026/3_run_benchmark.py:180). Paired statistical tests are not defensible unless runs are paired by an identical seed and, for local search, an identical initial permutation.

### 5. TSPLIB distance semantics are split

The central distance helper is the correct authority for supported TSPLIB types: [`distance.py`](../uniride_core/algorithms/distance.py:120). The CLI worker also has a corrective matrix-loading path for non-EUC instances: [`cli_engine.py`](./cli_engine.py:645).

The standalone Bildiri scripts parse `EDGE_WEIGHT_TYPE` but pass coordinates to solvers that build EUC_2D matrices themselves. Therefore ATT, GEO, CEIL_2D, EXPLICIT, and unsupported forms must be rejected or routed through the central matrix loader, not silently benchmarked as Euclidean coordinates.

### 6. Environment-dependent algorithm definition

Without Numba, the direct 3-opt implementation takes a Python fallback that ignores its `window` parameter and scans a different neighborhood: [`three_opt.py`](./bildiri2026/core/three_opt.py:51). With Numba, it executes a bounded-window kernel. The result quality and runtime are therefore machine-dependent even when parameters and seeds match.

The current environment is not eligible for acceleration claims. It must be replaced by a pinned, tested environment before collecting new results.

## Historical-result admissibility

| Result category | Decision | Reason |
|---|---|---|
| Old direct Bildiri GA/PSO/2-opt/3-opt reports | Historical context only | They do not include GWO/HHO and use an older direct pipeline. |
| Pre-distance-fix TSPLIB reports | Revalidate before any reuse | Distance formulas and dispatch changed in commits `c59a2bb`, `7aedc56`, and `3534ae8`. |
| Fresh registry GWO/HHO rows after PR #23 | Not paper evidence yet | The registry path now runs, but no fair working 3-opt comparator or common budget exists. |
| Claims such as an `eil51` GWO/HHO gap without a preserved raw result and environment manifest | Unverified | The figure must not be cited until reproduced from a versioned input, command, and output set. |

## Minimum defensible experiment redesign

### Study boundary

Create a new, isolated paper runner. Do not extend `3_run_benchmark.py` as the canonical study harness; preserve it as historical work. A suitable location is `academic_benchmark/studies/gwo_hho_local_search_2026/`.

The runner must accept a prebuilt TSPLIB matrix and a canonical `Tour` contract:

```text
TSP/ATSP: a closed Hamiltonian cycle represented as a permutation of all nodes.
Matrix/depot route: node 0 is a fixed anchor, with customer permutation [1..n-1].
Serialized output: include anchor once, report whether it is fixed, and recompute cost from the emitted cycle.
```

### Treatments

Run and name these as separate treatments:

1. Pure GWO.
2. GWO-2opt (memetic).
3. Pure HHO.
4. HHO-2opt (memetic).
5. Multi-start 2-opt.
6. Complete 3-opt.

If a hybrid is the research contribution, include a direct ablation proving the marginal value of every polishing stage.

### Fairness rules

- Use the same canonical distance matrix, objective function, optimum/BKS source, and tour validator for every treatment.
- Use a common objective-evaluation budget. Record every objective evaluation, including 2-opt trial moves and HHO dive candidates.
- Use common paired seeds. For local search, generate and save the same initial permutations for each paired run.
- Separate tuning instances from held-out reporting instances.
- Warm up compiled kernels before timing and record hardware, Python, NumPy, Numba, package lockfile, commit SHA, and command line.
- Report best, mean, median, standard deviation, IQR, BKS gap, elapsed time, evaluations, and convergence AUC.
- Apply paired Wilcoxon tests with Holm correction and report an effect size such as Vargha-Delaney A12 or Cliff's delta.

### Required regression tests before data collection

1. Every returned tour is a valid permutation under its declared tour contract.
2. Returned objective equals independent matrix recomputation for symmetric and asymmetric matrices.
3. A known small TSP has the same exact optimum under anchored and unanchored cycle representations.
4. `Numba-2-opt` and the repaired 3-opt run on a matrix-native `ProblemInstance` without exception.
5. Python and Numba implementations produce equal objective values for the same input and neighborhood definition.
6. 3-opt tests verify coverage of all genuine 3-opt reconnections, not merely that one artificial case improves.
7. Evaluation counts are nonzero, monotone, and comparable across all treatments.
8. Pure and memetic GWO/HHO differ only by explicitly declared polishing parameters.

## Prioritized repair roadmap

1. **Block invalid registry labels:** fix or temporarily disable `Numba-2-opt` and `Numba-3-opt-bounded` for matrix-native TSP; add the regression test first.
2. **Correct 3-opt:** replace the Bildiri neighborhood with a complete, tested implementation; define one identical Python/Numba neighborhood.
3. **Create one matrix-native study runner:** add GWO, HHO, 2-opt, and 3-opt through the same execution interface and tour contract.
4. **Instrument fairness:** implement objective-evaluation counting and paired seed/initial-tour manifests.
5. **Split pure and memetic variants:** expose all 2-opt polishing controls and make defaults explicit in result metadata.
6. **Pin the research environment:** use a known compatible Python/NumPy/Numba lockfile and fail fast when the requested execution mode is unavailable.
7. **Rebuild results from scratch:** retain raw CSVs as reproducibility artifacts outside source commits unless a release policy explicitly requires them; publish a generated methods-and-results report with hashes.

## Final conclusion

The external review correctly identified the most urgent executable failure: matrix-native registry 2-opt/3-opt is broken. It also correctly identified the study-design inequities. Its central claim that anchored GWO/HHO tours omit a city is mathematically incorrect; the implementation represents a full closed cycle with a fixed anchor and live cost checks verify that representation.

The decisive scientific conclusion is unchanged: **there is no current, reproducible, fair, working four-way GWO/HHO/2-opt/3-opt TSPLIB experiment in this repository.** The next paper must use the redesign above and regenerate all reported results.
