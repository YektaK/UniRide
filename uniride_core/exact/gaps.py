"""Gap arithmetic and the exact-vs-GA checks (design EXACT_SOLVER_AMPL_DESIGN.md sections 1.2 and 8; WP-E3).

Pure functions over integers. ``K`` is the route count of the single-type wave; ``D`` the sum of tour
minutes. ``K_LB`` bounds ``K``; ``D_LB`` is valid only conditional on ``K = K*``; ``D_LB_free`` is
valid for any route count.
"""
from __future__ import annotations

from typing import List, Optional

NOT_COMPARABLE = "not_comparable_K_GA_gt_Kstar"


def gap_fields(*, k_ga: int, d_ga: int, k_lb: Optional[int], k_star: Optional[int], d_lb: Optional[int],
               d_lb_free: Optional[int]) -> dict:
    """``dK``, ``gD`` (with ``gD_note``) and ``gD_free`` of one wave (section 1.2).

    ``k_star`` is given only when stage 1 is proven (``K*`` known). ``gD = (D_GA - D_LB) / D_LB`` is
    defined only when ``K_GA = K*``; when ``K_GA > K*`` it is "not comparable" and only the
    informative ``gD_free = (D_GA - D_LB_free) / D_LB_free`` is shown.
    """
    d_k = None if k_lb is None else k_ga - k_lb
    g_free = None if not d_lb_free or d_lb_free <= 0 else (d_ga - d_lb_free) / d_lb_free
    g_d: Optional[float] = None
    if k_star is None:
        note = "unavailable_stage1_not_proven"
    elif k_ga > k_star:
        note = NOT_COMPARABLE
    elif k_ga < k_star:
        note = "invalid_K_GA_lt_Kstar"
    elif d_lb is None:
        note = "unavailable_no_D_LB"
    elif d_lb <= 0:
        note = "unavailable_D_LB_zero"
    else:
        note, g_d = "comparable", (d_ga - d_lb) / d_lb
    return {"dK": d_k, "gD": g_d, "gD_note": note, "gD_free": g_free}


def exact_vs_ga_violations(*, exact_optimal: bool, k_star: Optional[int], d_star: Optional[int], k_ga: int,
                           d_ga: int, k_lb: Optional[int], d_lb: Optional[int]) -> List[str]:
    """Blocking inconsistencies between the exact result and the GA (section 8 rows "Exact <= GA").

    * Only when the exact stages are proven optimal: ``K* <= K_GA`` and, at equal ``K``, ``D* <= D_GA``.
    * Always: ``K_GA < K_LB`` is an error, and so is ``D_GA < D_LB`` at ``K_GA = K*`` (``d_lb`` and
      ``k_star`` are passed only when stage 1 is proven). A model or semantics mismatch, never a result.
    """
    errors = []
    if exact_optimal and k_star is not None and d_star is not None:
        if k_star > k_ga:
            errors.append(f"exact K* {k_star} exceeds the GA route count {k_ga}")
        elif k_star == k_ga and d_star > d_ga:
            errors.append(f"exact D* {d_star} exceeds the GA duration {d_ga} at equal K {k_ga}")
    if k_lb is not None and k_ga < k_lb:
        errors.append(f"GA route count {k_ga} is below the proven lower bound K_LB {k_lb}")
    if k_star is not None and d_lb is not None and k_ga == k_star and d_ga < d_lb:
        errors.append(f"GA duration {d_ga} is below the proven lower bound D_LB {d_lb} at K_GA = K* = {k_star}")
    return errors
