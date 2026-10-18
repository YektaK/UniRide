# Gap table per fleet, R and option kind

Rows are waves (`base`; the single type has only `base`) or options (`q`: the typed options `xq0..xqQ`, one per wave and quota). Fleets are never pooled and exact rows (`exact_reference_v1`) are never mixed into heuristic statistics.

Denominators: `rows` = every source row of the group; `compared` = rows with a feasible exact result and a feasible GA result of the same kind; `dK_zero_share` = `dK_zero / compared`; `gD_comparable` = compared rows with `K_GA = K*` (the only rows `gD_mean` and `gD_max` use; a `K_GA > K*` row has no `gD`); `exact_infeasible_proven`, `both_infeasible` and `ga_infeasible_exact_feasible` rows are outside `compared`. HiGHS cross-check: `highs_same_K_D_optimal` = optimal rows (denominator `exact_feasible`) whose (K, D) in HiGHS equal Gurobi's; `highs_both_infeasible` = proven-infeasible rows (denominator `exact_infeasible_proven`) that HiGHS also proves infeasible; `highs_free_same_optimal` = optimal rows whose free-stage optimum `D_LB_free` is equal in HiGHS and Gurobi.

| fleet | R | option_kind | rows | exact_feasible | exact_infeasible_proven | compared | both_infeasible | ga_infeasible_exact_feasible | dK_zero | dK_zero_share | dK_positive | dK_max | gD_comparable | gD_positive | gD_mean | gD_max | gD_not_comparable | status_counts | highs_same_K_D_optimal | highs_both_infeasible | highs_free_same_optimal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_4sw5so | 50 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.000552 | 0.018462 | 1 | optimal=57 | 57 | 0 | 57 |
| single_4sw5so | 60 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 6 | 0.004200 | 0.089947 | 1 | optimal=57 | 57 | 0 | 57 |
| single_4sw5so | 70 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.001067 | 0.027778 | 1 | optimal=57 | 57 | 0 | 57 |
| single_4sw5so | 90 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.001135 | 0.034146 | 1 | optimal=57 | 57 | 0 | 57 |
| large+sedan | 50 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.000552 | 0.018462 | 1 | optimal=57 | 57 | 0 | 57 |
| large+sedan | 50 | q | 194 | 148 | 46 | 147 | 46 | 1 | 144 | 0.979592 | 3 | 1 | 144 | 5 | 0.000339 | 0.018462 | 3 | infeasible_proven=46;optimal=148 | 148 | 46 | 148 |
| large+sedan | 60 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 6 | 0.004200 | 0.089947 | 1 | optimal=57 | 57 | 0 | 57 |
| large+sedan | 60 | q | 194 | 153 | 41 | 152 | 41 | 1 | 149 | 0.980263 | 3 | 1 | 149 | 16 | 0.003823 | 0.117318 | 3 | infeasible_proven=41;optimal=153 | 153 | 41 | 153 |
| large+sedan | 70 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.001067 | 0.027778 | 1 | optimal=57 | 57 | 0 | 57 |
| large+sedan | 70 | q | 194 | 154 | 40 | 154 | 40 | 0 | 151 | 0.980519 | 3 | 1 | 151 | 6 | 0.000803 | 0.044521 | 3 | infeasible_proven=40;optimal=154 | 154 | 40 | 154 |
| large+sedan | 90 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.001135 | 0.034146 | 1 | optimal=57 | 57 | 0 | 57 |
| large+sedan | 90 | q | 194 | 154 | 40 | 154 | 40 | 0 | 153 | 0.993506 | 1 | 1 | 153 | 7 | 0.001793 | 0.131737 | 1 | infeasible_proven=40;optimal=154 | 154 | 40 | 154 |
| large+doblo_cap3 | 50 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.000552 | 0.018462 | 1 | optimal=57 | 57 | 0 | 57 |
| large+doblo_cap3 | 50 | q | 160 | 160 | 0 | 160 | 0 | 0 | 154 | 0.962500 | 6 | 1 | 154 | 5 | 0.000438 | 0.023438 | 6 | optimal=160 | 160 | 0 | 160 |
| large+doblo_cap3 | 60 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 6 | 0.004200 | 0.089947 | 1 | optimal=57 | 57 | 0 | 57 |
| large+doblo_cap3 | 60 | q | 160 | 160 | 0 | 160 | 0 | 0 | 158 | 0.987500 | 2 | 1 | 158 | 16 | 0.002672 | 0.089947 | 2 | optimal=160 | 160 | 0 | 160 |
| large+doblo_cap3 | 70 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.001067 | 0.027778 | 1 | optimal=57 | 57 | 0 | 57 |
| large+doblo_cap3 | 70 | q | 160 | 160 | 0 | 160 | 0 | 0 | 159 | 0.993750 | 1 | 1 | 159 | 8 | 0.000597 | 0.022523 | 1 | optimal=160 | 160 | 0 | 160 |
| large+doblo_cap3 | 90 | base | 57 | 57 | 0 | 57 | 0 | 0 | 56 | 0.982456 | 1 | 1 | 56 | 3 | 0.001135 | 0.034146 | 1 | optimal=57 | 57 | 0 | 57 |
| large+doblo_cap3 | 90 | q | 160 | 160 | 0 | 160 | 0 | 0 | 159 | 0.993750 | 1 | 1 | 159 | 10 | 0.002229 | 0.099730 | 1 | optimal=160 | 160 | 0 | 160 |

# Day level over the union menu (`union_day_v1`), per fleet and L

One row per (fleet, L); cells are (date, R) pairs (20 per row). The cars columns count `proven_over_union_menu` cells by the sign of union cars minus GA-menu cars. Not a global day optimum (EQ3).

| fleet | L | cells | proven_over_union_menu | ga_menu_infeasible_for_L | both_infeasible_for_L | union_not_proven | not_independently_confirmed | verification_failed | union_cars_below_ga | union_cars_equal_ga | union_cars_above_ga |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| large+sedan | 1 | 20 | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 |
| large+sedan | 2 | 20 | 11 | 1 | 8 | 0 | 0 | 0 | 1 | 10 | 0 |
| large+sedan | 3 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 3 | 17 | 0 |
| large+doblo_cap3 | 0 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 3 | 17 | 0 |
| large+doblo_cap3 | 1 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 2 | 18 | 0 |
| large+doblo_cap3 | 2 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 2 | 18 | 0 |
