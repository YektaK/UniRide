"""Shared cases for the GWO/HHO budget-schedule tests (owner decision 2026-10-22).

Imported by ``test_gwo_hho_budget_schedule.py`` and by the one-off script that
captured ``golden/gwo_hho_native_pre_schedule.json`` from the code as it was
BEFORE the schedule change (WIP c49b4bbf). Keep the case definitions stable: the
golden is only meaningful for exactly these inputs.
"""

import random
from typing import Any, Dict, List

from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import GWOOptimizer
from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import HHOOptimizer

SOLVERS = {"GWO": GWOOptimizer, "HHO": HHOOptimizer}


def sym_matrix(n: int = 8, seed: int = 3) -> List[List[float]]:
    rng = random.Random(seed)
    pts = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    return [
        [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts
    ]


def asym_matrix(n: int = 8, seed: int = 5) -> List[List[float]]:
    rng = random.Random(seed)
    return [
        [0.0 if i == j else float(rng.randint(5, 90)) for j in range(n)]
        for i in range(n)
    ]


MATRICES = {"sym": sym_matrix, "asym": asym_matrix}


def swarm_params(algorithm: str, **overrides: Any) -> Dict[str, Any]:
    """Small swarm, stagnation stop effectively off, polish phases short."""
    base: Dict[str, Any] = {
        "max_iterations": 40,
        "max_no_improvement": 10_000,
        "polish_interval": 5,
        "polish_iters": 3,
        "final_polish_iters": 20,
        "random_seed": 11,
    }
    if algorithm == "GWO":
        base.update(pack_size=6, initial_a=2.0, exploration_rate=0.4)
    else:
        base.update(hawks=6, initial_energy=1.0, jump_probability=0.5, dive_count=2)
    base.update(overrides)
    return base


def run_case(algorithm: str, matrix_kind: str, **params: Any) -> Dict[str, Any]:
    solver = SOLVERS[algorithm](**params)
    result = solver.solve_with_matrix(MATRICES[matrix_kind](), recalculate=False, closed_tsp=True)
    stats = result.extra_stats
    return {
        "tour": [int(v) for v in result.tour],
        "tour_length": repr(float(result.tour_length)),
        "iterations": int(result.iterations),
        "history": [repr(float(v)) for v in result.history],
        "objective_evaluations": int(stats["objective_evaluations"]),
        "evaluation_budget": stats["evaluation_budget"],
        "budget_terminated": bool(stats["budget_terminated"]),
        "polish_executed": dict(stats["polish_executed"]),
        "polish_evaluations": stats["polish_evaluations"],
    }


# name -> (algorithm, matrix kind, constructor overrides). ALL native (no budget).
NATIVE_CASES = {}
for _alg in ("GWO", "HHO"):
    for _kind in ("sym", "asym"):
        NATIVE_CASES[f"{_alg}-{_kind}-native-memetic"] = (_alg, _kind, {})
        NATIVE_CASES[f"{_alg}-{_kind}-native-pure"] = (_alg, _kind, {"polish_enabled": False})
        NATIVE_CASES[f"{_alg}-{_kind}-native-memetic-counted"] = (
            _alg, _kind, {"count_polish": True},
        )
        # Early iteration stop: the schedule must still be iteration-based.
        NATIVE_CASES[f"{_alg}-{_kind}-native-pure-short"] = (
            _alg, _kind, {"polish_enabled": False, "max_iterations": 7},
        )

# Fixed-budget cases whose ACCOUNTING does not depend on the search trajectory:
# pure GWO spends pack_size at init and pack_size - 3 per iteration, so budget,
# iteration count and termination are fixed numbers whatever the schedule is.
GWO_FIXED_ACCOUNTING_CASES = {
    "GWO-sym-fixed-pure-B100": ("sym", {"polish_enabled": False, "evaluation_budget": 100,
                                        "max_iterations": 500}),
    "GWO-asym-fixed-pure-B157": ("asym", {"polish_enabled": False, "evaluation_budget": 157,
                                          "max_iterations": 500}),
}
