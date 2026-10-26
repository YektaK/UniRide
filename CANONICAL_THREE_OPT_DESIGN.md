# Canonical 3-opt Design for Symmetric TSP and Directed ATSP

**Date:** 2026-07-17  
**Status:** Approved design; implementation pending  
**Scope:** Academic benchmark 3-opt execution and the shared `uniride_core` local-search kernel

## Objective

Provide one authoritative, matrix-native 3-opt implementation for the UniRide academic benchmark. The implementation must support symmetric TSP and directed ATSP with mathematically distinct neighborhoods, preserve exact closed-tour matrix costs, and eliminate semantic divergence between the registry and `bildiri2026` execution paths.

The public registry name `Numba-3-opt-bounded` remains available for compatibility. Until a JIT implementation passes semantic-parity tests, that name delegates to the correctness-first canonical implementation and does not imply that Numba executed.

## Current problem

The repository currently contains multiple 3-opt implementations with different behavior:

- `uniride_core/algorithms/local_search.py`
- `uniride_core/algorithms/local_search_numba.py`
- `academic_benchmark/bildiri2026/core/three_opt.py`
- `academic_benchmark/bildiri2026/core/numba_accel.py`

The Bildiri and accelerated paths do not expose a complete, consistently defined 3-opt neighborhood. Segment reversals are also unsafe as an implicit ATSP operation because reversing a directed path changes all internal arcs, not merely the three cut arcs.

## Architecture

Create one canonical matrix-native engine under `uniride_core`. Registry and standalone academic adapters delegate to this engine. The engine owns:

- valid cut-triple enumeration;
- symmetric and directed candidate generation;
- full closed-cycle objective evaluation;
- bounded-window behavior;
- deterministic improvement and tie-breaking;
- iteration accounting.

Existing Numba kernels cease to be authoritative. They remain unreachable from the public academic 3-opt path until a separate optimization task proves candidate-set and result parity against the canonical engine.

## Algorithm contract

### Common tour and cut model

A tour is a Hamiltonian cycle represented by a permutation of matrix indices. Three non-adjacent cycle edges are selected as cuts. Cut triples that share endpoints or create empty/degenerate segments are excluded.

Every candidate must:

- contain every input node exactly once;
- use the supplied matrix direction exactly;
- include the closing last-to-first edge in its objective;
- be evaluated against the full matrix objective rather than a symmetric-only delta formula.

### Symmetric TSP neighborhood

For a symmetric matrix, enumerate all seven non-identity reconnections associated with a valid three-cut decomposition:

- three 2-opt-equivalent reconnections;
- four genuine 3-opt reconnections.

Duplicates caused by rotationally equivalent representations are removed without removing a distinct edge set. Since MT6-01 the duplicates are avoided by construction rather than detected: for an admitted cut triple the seven symmetric reconnections are pairwise distinct, so no per-candidate cycle key is needed; the neighbourhood content is unchanged.

### Directed ATSP neighborhood

For an asymmetric matrix, a valid directed three-edge exchange preserves the internal orientation of each directed path segment. Candidate construction may reorder the three directed path segments, but it must not reverse a segment.

Only reconnections that produce one Hamiltonian cycle are admissible. Subtours, self-connections, and the identity reconnection are rejected. This contract provides a true directed three-arc exchange instead of applying an undirected reversal rule to an asymmetric objective.

### Matrix-mode selection

The engine selects directed semantics when the supplied matrix is asymmetric within a documented numerical tolerance. Explicit ATSP metadata may force directed mode. Symmetric mode must never be selected for an asymmetric matrix merely because a caller labels the problem as TSP.

### Bounded behavior

`window` limits the separation between successive cut positions. It does not reduce the reconnection cases evaluated for an admitted cut triple.

`max_iterations` limits complete improvement passes. `first_improvement` accepts the first strictly improving candidate in deterministic cut/case order; otherwise the best candidate in the pass is selected.

Objective comparisons use a scale-aware tolerance. Equal-cost candidates do not replace the incumbent, which preserves deterministic tie behavior.

## Integration

### Shared core

The canonical engine accepts a route, matrix, problem mode, maximum iterations, bounded window, and improvement policy. It returns the improved route, exact objective, iteration count, and optionally evaluation count.

### Registry

`academic_benchmark/core/registry_setup.py` routes `Numba-3-opt-bounded` to the canonical engine while preserving its compatibility name and `RunResult` contract. Returned tours remain complete one-indexed permutations at the registry boundary.

### Local-search compatibility

The 3-opt wrapper in `uniride_core/algorithms/local_search_numba.py` delegates to the canonical engine. Other local-search operators remain unchanged.

### Bildiri solver

`academic_benchmark/bildiri2026/core/three_opt.py` delegates its improvement work to the canonical engine. Its initialization and multi-start orchestration remain adapter concerns, but neighborhood semantics and objective evaluation are core-owned.

### Legacy accelerated implementation

The old 3-opt kernel in `academic_benchmark/bildiri2026/core/numba_accel.py` and the old `_three_opt_improve_numba` path are marked non-canonical and removed from public execution. They may be re-enabled only after dedicated JIT parity tests pass in an environment where Numba imports successfully.

## Path neighbourhood for production local search

**Added 2026-10-26 (audit M14, MT6-04; DECISION_LOG A19, owner answer OQ-MT6-3 b). Production only, never used for paper claims.**

The production hybrid local search (`uniride_core/algorithms/local_search.py`) does not optimise a Hamiltonian cycle over a matrix. It improves an open sequence that a caller costs with a black-box objective; in `ga_split` the objective is the cost of a depot-to-depot giant tour with the depot outside the sequence (`educate_individual` in `ga_split_engine.py`, `giant_tour_cost` in `meta_split_common.py`; the chromosome is not Split-decoded for this cost). The sequence is open between two fixed depot ends, and rotating it changes the cost. A cycle candidate rotated to the first node is neutral for a cycle and wrong for such a sequence, so the canonical cycle engine above cannot be used there. `uniride_core/algorithms/three_opt.py` therefore owns a second, separately named neighbourhood, **path 3-opt, reversals fully costed**:

- **Cuts.** `-1 <= i < j < k <= n - 1`, `A = route[:i + 1]`, `B = route[i + 1:j + 1]`, `C = route[j + 1:k + 1]`, `D = route[k + 1:]`, with `B` and `C` non-empty. `A` and `D` are fixed; an empty `A` (`i = -1`) lets the first position move, an empty `D` (`k = n - 1`) the last. Cuts are enumerated in lexicographic `(i, j, k)` order (`iter_path_three_opt_cuts`).
- **Window.** The canonical rule, applied to the same indices: `j - i <= window` and `k - j <= window` (`window=None` admits every cut). The window bounds the cuts, not the arrangements tried for an admitted cut.
- **Candidates.** The 7 non-identity arrangements of `(B, C)` by order and reversal, in this fixed order: `B'C'`, `B'C`, `BC'`, `CB`, `C'B`, `CB'`, `C'B'` (the legacy production order with the formerly missing `C'B'` appended). A candidate equal as a sequence to the input or to an earlier candidate of the same cut is dropped (a one-node segment makes `B' = B`); duplicates across different cuts are not removed (`generate_path_three_opt_candidates`).
- **Costing.** Every candidate, reversed segments included, is costed in full by the caller's objective; there is no delta evaluation and no symmetric-matrix assumption. The caller's objective, not a matrix, defines whether a reversal is cost-neutral.
- **Acceptance.** Strict improvement of the objective (`candidate < incumbent`, no tolerance, equal or NaN costs never replace the incumbent); this is the semantics the production class already had. The default pass is a true best-improvement pass: every candidate is compared against the best of the pass so far, and the best (first in scan order among equal costs) replaces the incumbent once, at the end of the pass. `first_improvement=True` takes the first strictly improving candidate in (cut, arrangement) order. `max_iterations` bounds complete passes. This is stricter than the scale-aware tolerance of the cycle engine on purpose: a black-box objective has no known scale (see N-1 in the MT6 plan for the cycle controllers).
- **Small routes.** `ThreeOptLocalSearch` returns a route with fewer than 4 nodes unchanged; it never runs 2-opt under the 3-opt name.
- **Hybrid configuration.** The hybrid keeps `max_iterations = 15` and `window = 12` for this step.
- **Name.** Code and documents call it "path 3-opt, reversals fully costed". It is not the canonical 3-opt of the sections above, it has no academic registry entry, and no academic result may cite it.

`ThreeOptLocalSearch._three_opt_cases` is deleted; `ThreeOptLocalSearch.improve` delegates to `improve_path_three_opt`. Tests: `uniride_core/tests/test_mt6_path_three_opt.py` (independent brute-force enumerator that does not import the generator) and additions to `uniride_core/tests/test_local_search_core.py`.

## Error handling

- Reject a non-square matrix or a matrix whose dimension differs from the route.
- Reject duplicate or out-of-range route indices.
- Reject an explicit symmetric-mode request for an asymmetric matrix.
- Return the unchanged tour for instances too small to admit three non-adjacent cuts; do not silently relabel a 2-opt fallback as 3-opt work.
- Surface unsupported inputs as clear `ValueError` exceptions at the shared-core boundary.

## Verification strategy

Tests must use an independent reference enumerator that does not import the production candidate generator.

Required coverage:

1. All seven symmetric non-identity reconnections are enumerated, including all four genuine 3-opt edge sets.
2. Directed candidates preserve each path segment's internal orientation.
3. Directed candidates form one Hamiltonian cycle and contain no subtours.
4. Production and exhaustive-reference best moves agree on small symmetric and asymmetric matrices.
5. Every returned tour is a complete permutation.
6. Reported cost equals an independent closed-cycle matrix recomputation.
7. Identical input and configuration produce identical output.
8. Registry and standalone Bildiri paths use equivalent neighborhood semantics.
9. Window bounds cut selection but not reconnection-case coverage.
10. Small and invalid inputs follow the documented error contract.

The minimum regression command is:

```powershell
python -m pytest academic_benchmark/tests/test_numba_registry_matrix.py academic_benchmark/tests/test_numba_three_opt.py academic_benchmark/tests/test_core_tsp_registry.py uniride_core/tests/test_local_search_core.py uniride_core/tests/test_tsp_meta_engines.py uniride_core/tests/test_three_opt_candidate_parity.py uniride_core/tests/test_mt6_no_forbidden_three_opt.py uniride_core/tests/test_mt6_budgeted_tolerance.py academic_benchmark/tests/test_mt6_sota_executors_no_forbidden_kernel.py uniride_core/tests/test_mt6_path_three_opt.py -q -p no:cacheprovider --tb=short
```

Any new focused canonical-3-opt test modules must be added to that verification run.

## Non-goals

- Changing GWO/HHO or their embedded 2-opt behavior.
- Equalizing DOE or paper experiment budgets.
- Generating or modifying benchmark results.
- Installing or changing NumPy/Numba dependencies.
- Claiming JIT acceleration before parity is demonstrated.

## Acceptance criteria

The design is complete when one public academic 3-opt path implements the contracts above, all new reference-based tests pass, the existing focused suite has no regressions, and any unverified JIT behavior is reported explicitly.
