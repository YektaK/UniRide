# TSP / ATSP with Dantzig-Fulkerson-Johnson subtour cuts (design EXACT_SOLVER_AMPL_DESIGN.md section 5, WP-E7).
#
# One file for both problem kinds. The cut loop in uniride_core/exact/tsp.py solves this model, finds
# the connected (symmetric) or strongly connected (directed) components of the integer solution and
# adds one subtour cut per component, then solves again; the model is never relaxed by the driver.
# Data go through the amplpy API (no .dat file).
#
# directed = 1 (ATSP): one binary per arc (i, j), i != j; out-degree = in-degree = 1.
# directed = 0 (symmetric TSP): one binary per edge (i, j) with i < j; degree 2.
#
# A cut k is the node set member[k, .] = 1 and reads: arcs (edges) with both ends in S <= |S| - 1.

param n integer >= 3;
param directed binary;
set NODES = 0..n-1;
set ARCS within {NODES, NODES};
param cost {ARCS} integer >= 0;
suffix bestbound OUT;                      # solver best bound; reset by the driver before every solve

var x {ARCS} binary;

minimize Tour: sum {(i, j) in ARCS} cost[i, j] * x[i, j];

subject to Leave {i in NODES}:
    sum {(i, j) in ARCS} x[i, j] + (if directed = 0 then sum {(j, i) in ARCS} x[j, i]) = (if directed = 1 then 1 else 2);

subject to Enter {i in NODES: directed = 1}:
    sum {(j, i) in ARCS} x[j, i] = 1;

set CUTS default {};
param member {CUTS, NODES} binary default 0;
param csize {CUTS} integer >= 2;

subject to Subtour {k in CUTS}:
    sum {(i, j) in ARCS: member[k, i] = 1 and member[k, j] = 1} x[i, j] <= csize[k] - 1;
