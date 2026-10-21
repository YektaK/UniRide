"""C-06: improve_three_opt_budgeted moved to uniride_core; fairness re-exports it."""

import academic_benchmark.fairness as fairness
import uniride_core.algorithms.objective_budget as core


def test_fairness_reexports_the_core_three_opt_controller():
    assert fairness.improve_three_opt_budgeted is core.improve_three_opt_budgeted
    assert "improve_three_opt_budgeted" in fairness.__all__
