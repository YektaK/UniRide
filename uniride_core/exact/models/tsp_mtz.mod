# TSP / ATSP with Miller-Tucker-Zemlin subtour elimination (design EXACT_SOLVER_AMPL_DESIGN.md section 5, WP-E7).
#
# Single solve, small n only: a CROSS-CHECK of the DFJ cut loop, never the primary exact method (its LP
# bound is weak). Directed arc variables serve both symmetric and asymmetric matrices (a symmetric matrix
# simply has each tour in both directions). Data go through the amplpy API (no .dat file).

param n integer >= 3;
set NODES = 0..n-1;
set ARCS within {NODES, NODES};            # every (i, j) with i != j
param cost {ARCS} integer >= 0;
suffix bestbound OUT;

var x {ARCS} binary;
var u {NODES} >= 1, <= n - 1;              # visit position of a node other than node 0

minimize Tour: sum {(i, j) in ARCS} cost[i, j] * x[i, j];

subject to Leave {i in NODES}: sum {(i, j) in ARCS} x[i, j] = 1;
subject to Enter {i in NODES}: sum {(j, i) in ARCS} x[j, i] = 1;
subject to Mtz {(i, j) in ARCS: i > 0 and j > 0}: u[i] - u[j] + (n - 1) * x[i, j] <= n - 2;
