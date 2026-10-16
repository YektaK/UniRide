# Set-partitioning model of one wave (design EXACT_SOLVER_AMPL_DESIGN.md section 1.1 Step B, WP-E2).
#
# Columns come from uniride_core/exact/route_enumeration.py: one column per (multiset over
# (location, class) items, vehicle type); a column is a complete feasible route with integer cost.
# Data are written through the amplpy API by uniride_core/exact/ampl_backend.py (no .dat file).
#
# lam[r] is a NON-NEGATIVE INTEGER (owner decision 2026-10-15, DECISION_LOG E02): two routes of a
# wave can need the same aggregated column, so a binary variable is not enough. It is bounded by
# the cover rows: lam[r] <= min over the items of r of floor(demand[i] / a[r, i]).
#
# Stage 1: minimise RouteCount (K, or K_m of the minimised type) without FixCount.
# Stage 2: minimise Duration with FixCount active (k_fix = stage-1 value).
# D_LB_free: minimise Duration without FixCount.

set COLS;                                  # column indices (enumeration order)
set ITEMS;                                 # (location, class) items of the wave
set NZ within {COLS, ITEMS};               # (r, i) with a[r, i] > 0
suffix bestbound OUT;                      # solver best bound; reset by the backend before every solve

param a {NZ} integer > 0;                  # students of item i served by column r
param demand {ITEMS} integer > 0;          # n_(loc,cls)
param cost {COLS} integer >= 0;            # d_r = tour minutes
param counted {COLS} binary;               # 1 if r counts in the stage-1 objective
param in_quota {COLS} binary default 0;    # 1 if r has the quota type
param quota_on binary default 0;
param quota integer >= 0 default 0;
param v_max integer >= 0;                  # fleet limit min(legs, 50) (F5)
param k_fix integer >= 0 default 0;

param lam_ub {r in COLS} := min {(r, i) in NZ} floor(demand[i] / a[r, i]);

var lam {r in COLS} integer >= 0, <= lam_ub[r];

minimize RouteCount: sum {r in COLS: counted[r] = 1} lam[r];
minimize Duration: sum {r in COLS} cost[r] * lam[r];

subject to Cover {i in ITEMS}:
    sum {(r, i) in NZ} a[r, i] * lam[r] = demand[i];

subject to Quota {if quota_on = 1}:
    sum {r in COLS: in_quota[r] = 1} lam[r] <= quota;

subject to Fleet:
    sum {r in COLS} lam[r] <= v_max;

subject to FixCount:
    sum {r in COLS: counted[r] = 1} lam[r] = k_fix;
