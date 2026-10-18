# TSPLIB exact reference, stage 1 verification

Facts of one run of `scripts/run_exact_tsp_reference.py` (WP-E7, DECISION_LOG E09). This is a verification subset, not a paper instance set: the 16 TSPLIB TSP instances with n <= 100 and a published optimum, plus the ATSP instance ft53. Its purpose is to check the exact cut-loop solver and the TSPLIB distance convention against published optima. No superiority claim is made.

- Commit `461117c5f4e3`, working tree dirty: false.
- Solvers: Gurobi 13.0.3 (primary), HiGHS 1.15.1 (re-solve of every instance Gurobi proved optimal), AMPL Version 20260809 (MSVC 19.44.35228.0, 64-bit), amplpy 0.18.0.
- Limits: 600 s wall time in total per instance and solver (all cut-loop re-solves together), 1 thread, seed 0. MTZ (a single solve) cross-checks instances with n <= 40.
- Model: DFJ subtour cuts added iteratively; edge variables for symmetric instances, arc variables for ft53.
- The published value is a reference value (`reference_optimum`, source `tsplib`); a row is `optimal` only when the solver proved it. `reference.csv` has one row per instance; `tours.json` holds the tours (`--verify-tours` re-checks them without a solver); `manifest.json` holds versions, option strings, the sha256 of every instance input and the published-value sources.
- Instances in this run: 17. Instance data: 5 from `.tsp` files, 1 from `.atsp` files, 11 from the node coordinates in the read-only database (no `.tsp` file in the checkout; the manifest records the sha256 of the canonical coordinate text instead of a file hash).
- Verdicts: {"reproduced": 17}; blocking errors: 0.

| instance | n | published | status | UB | LB | verdict | HiGHS | rounds | cuts | wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| burma14 | 14 | 3323 | optimal | 3323 | 3323 | reproduced | agree | 2 | 3 | 1.31 |
| ulysses16 | 16 | 6859 | optimal | 6859 | 6859 | reproduced | agree | 4 | 8 | 2.437 |
| ulysses22 | 22 | 7013 | optimal | 7013 | 7013 | reproduced | agree | 5 | 14 | 2.951 |
| att48 | 48 | 10628 | optimal | 10628 | 10628 | reproduced | agree | 7 | 22 | 4.641 |
| eil51 | 51 | 426 | optimal | 426 | 426 | reproduced | agree | 2 | 3 | 1.326 |
| berlin52 | 52 | 7542 | optimal | 7542 | 7542 | reproduced | agree | 2 | 7 | 1.204 |
| ft53 | 53 | 6905 | optimal | 6905 | 6905 | reproduced | agree | 7 | 26 | 5.867 |
| st70 | 70 | 675 | optimal | 675 | 675 | reproduced | agree | 5 | 24 | 3.443 |
| eil76 | 76 | 538 | optimal | 538 | 538 | reproduced | agree | 2 | 3 | 1.318 |
| pr76 | 76 | 108159 | optimal | 108159 | 108159 | reproduced | agree | 10 | 44 | 14.028 |
| gr96 | 96 | 55209 | optimal | 55209 | 55209 | reproduced | agree | 10 | 39 | 14.36 |
| kroa100 | 100 | 21282 | optimal | 21282 | 21282 | reproduced | agree | 8 | 44 | 7.832 |
| krob100 | 100 | 22141 | optimal | 22141 | 22141 | reproduced | agree | 9 | 56 | 14.499 |
| kroc100 | 100 | 20749 | optimal | 20749 | 20749 | reproduced | agree | 8 | 42 | 8.912 |
| krod100 | 100 | 21294 | optimal | 21294 | 21294 | reproduced | agree | 8 | 45 | 8.557 |
| kroe100 | 100 | 22068 | optimal | 22068 | 22068 | reproduced | agree | 7 | 41 | 8.073 |
| rd100 | 100 | 7910 | optimal | 7910 | 7910 | reproduced | agree | 6 | 38 | 6.516 |

Published-value sources: the table `problems.optimal` of the local TSPLIB database (read-only), cross-checked against `TSPLIB_OPTIMALS` in the repo's TSPLIB parser module and, for ft53, the ATSP collection manifest.
