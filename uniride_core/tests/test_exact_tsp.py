"""WP-E7 (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 2, 4, 5, 6, 8): the exact TSP/ATSP solver
``uniride_core/exact/tsp.py`` (DFJ cut loop over AMPL models ``tsp_dfj.mod`` / ``tsp_mtz.mod``).

The pure parts (component separation, tour validation, cut loop with injected solves, the shared time
budget, solver comparison, module boundary) run without AMPL. Tests that solve carry ``requires_ampl``
and are skipped with a reason ONLY when the backend reports ``backend_unavailable``; any other probe
failure is a backend defect and fails.

The Hamiltonian-cycle validation contract tested here is separate from the VRP multi-route contract
(AGENTS.md).
"""
from __future__ import annotations

import ast
import itertools
import random
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EXACT = REPO / "uniride_core" / "exact"
SOLVERS = ("gurobi", "highs")


# ---------------------------------------------------------------- helpers
def _tsp():
    from uniride_core.exact import tsp

    return tsp


def _edges(*cycles):
    """Undirected edge tuples (i < j) of the given node cycles."""
    out = []
    for cyc in cycles:
        for a, b in zip(cyc, cyc[1:] + cyc[:1]):
            out.append((min(a, b), max(a, b)))
    return tuple(out)


def _arcs(*cycles):
    """Directed arc tuples of the given node cycles."""
    out = []
    for cyc in cycles:
        out.extend(zip(cyc, cyc[1:] + cyc[:1]))
    return tuple(out)


def brute_force_tsp(matrix) -> int:
    """Optimal tour length by full enumeration (n <= 9), node 0 fixed first."""
    n = len(matrix)
    best = None
    for perm in itertools.permutations(range(1, n)):
        path = (0,) + perm
        length = sum(matrix[a][b] for a, b in zip(path, path[1:] + path[:1]))
        best = length if best is None or length < best else best
    return best


def random_matrix(seed: int, n: int, symmetric: bool):
    """Random integer matrix with cheap cycles (cheap 2-cycles / triangles) that attract subtours."""
    rng = random.Random(seed)
    m = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                m[i][j] = rng.randint(5, 40)
    for _ in range(max(2, n // 2)):
        a, b = rng.sample(range(n), 2)
        m[a][b] = rng.randint(1, 3)
        m[b][a] = rng.randint(1, 3)
    if symmetric:
        for i in range(n):
            for j in range(i + 1, n):
                m[j][i] = m[i][j]
        if n >= 6:  # cheap triangles far from each other: the degree-2 relaxation takes them as subtours
            for g in range(0, n - n % 3, 3):
                for a, b in ((g, g + 1), (g + 1, g + 2), (g, g + 2)):
                    m[a][b] = m[b][a] = rng.randint(1, 3)
    return tuple(tuple(r) for r in m)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _ring_matrix(n, symmetric=True):
    m = [[0 if i == j else 5 + ((i * 7 + j * 3) % 11) for j in range(n)] for i in range(n)]
    if symmetric:
        for i in range(n):
            for j in range(i + 1, n):
                m[j][i] = m[i][j]
    return tuple(tuple(r) for r in m)


def _tour_edges(tour):
    return _edges(tuple(tour))


# ---------------------------------------------------------------- components (deterministic separation)
def test_components_of_two_separated_triangles_are_sorted_by_smallest_node():
    tsp = _tsp()
    shuffled = list(_edges((4, 3, 5), (2, 0, 1)))
    random.Random(1).shuffle(shuffled)
    assert tsp.components(6, shuffled, directed=False) == [(0, 1, 2), (3, 4, 5)]
    assert tsp.components(6, list(reversed(shuffled)), directed=False) == [(0, 1, 2), (3, 4, 5)]


def test_strong_components_differ_from_weak_components_for_directed_arcs():
    tsp = _tsp()
    arcs = ((0, 1), (1, 0), (1, 2), (2, 3), (3, 2))  # {0,1} and {2,3} are cycles joined by the one-way arc 1 -> 2
    assert tsp.components(4, arcs, directed=True) == [(0, 1), (2, 3)]  # strong
    assert tsp.components(4, arcs, directed=False) == [(0, 1, 2, 3)]  # weak (undirected view)


def test_arcs_to_tour_returns_the_hamiltonian_cycle_from_node_zero_or_none():
    tsp = _tsp()
    assert tsp.arcs_to_tour(5, _arcs((0, 2, 4, 1, 3)), directed=True) == (0, 2, 4, 1, 3)
    undirected = tsp.arcs_to_tour(5, _edges((0, 2, 4, 1, 3)), directed=False)
    assert undirected[0] == 0 and sorted(undirected) == [0, 1, 2, 3, 4]
    assert undirected == tsp.arcs_to_tour(5, list(reversed(_edges((0, 2, 4, 1, 3)))), directed=False)  # deterministic
    assert tsp.arcs_to_tour(6, _edges((0, 1, 2), (3, 4, 5)), directed=False) is None
    assert tsp.arcs_to_tour(6, _arcs((0, 1, 2), (3, 4, 5)), directed=True) is None


# ---------------------------------------------------------------- tour validation (Hamiltonian-cycle contract)
def test_validate_tour_accepts_a_correct_tour_and_computes_its_length():
    tsp = _tsp()
    m = _ring_matrix(5, symmetric=False)
    tour = (0, 3, 1, 4, 2)
    length = sum(m[a][b] for a, b in zip(tour, tour[1:] + tour[:1]))
    assert tsp.tour_length(m, tour) == length
    assert tsp.validate_tour(m, tour, length) == []
    assert tsp.validate_tour(m, tour) == []


def test_validate_tour_rejects_a_subtour_a_repeated_node_a_bad_node_and_a_wrong_length():
    tsp = _tsp()
    m = _ring_matrix(6, symmetric=False)
    good = (0, 1, 2, 3, 4, 5)
    length = tsp.tour_length(m, good)
    assert tsp.validate_tour(m, (0, 1, 2), None), "a tour over a node subset (a subtour) must be rejected"
    assert tsp.validate_tour(m, (0, 1, 2, 3, 4, 4), None), "a repeated node must be rejected"
    assert tsp.validate_tour(m, (0, 1, 2, 3, 4, 9), None), "a node outside 0..n-1 must be rejected"
    assert tsp.validate_tour(m, good, length + 1), "a claimed length that differs from the recomputed one must be rejected"
    assert tsp.validate_tour(m, good, length - 1)
    assert tsp.validate_tour(m, good, length) == []


# ---------------------------------------------------------------- cycle patching (upper bound without an optimal round)
def test_patch_to_tour_merges_cycles_into_one_valid_tour_deterministically():
    tsp = _tsp()
    for directed, arcs in ((False, _edges((0, 1, 2), (3, 4, 5, 6))), (True, _arcs((0, 1, 2), (3, 4, 5, 6)))):
        m = _ring_matrix(7, symmetric=not directed)
        tour = tsp.patch_to_tour(m, arcs, directed=directed)
        assert tour is not None and tsp.validate_tour(m, tour) == []
        assert tour == tsp.patch_to_tour(m, tuple(reversed(arcs)), directed=directed)


def test_patch_to_tour_gives_none_when_the_arcs_are_not_a_permutation():
    tsp = _tsp()
    m = _ring_matrix(4, symmetric=False)
    assert tsp.patch_to_tour(m, ((0, 1), (1, 0), (1, 2), (2, 3), (3, 2)), directed=True) is None


# ---------------------------------------------------------------- the cut loop with injected solves
def _outcome(tsp, arcs, objective, bound=None, status="optimal", stop="optimal", wall=0.0):
    return tsp.RoundOutcome(status=status, stop_reason=stop, objective=objective,
                            bound_ceil=objective if bound is None else bound, arcs=arcs, wall_seconds=wall)


def test_two_separated_triangles_force_one_subtour_cut_per_component():
    tsp = _tsp()
    n = 6
    m = [[0 if i == j else (1 if (i < 3) == (j < 3) else 10) for j in range(n)] for i in range(n)]
    calls = []

    def solve_round(cuts, time_limit):
        calls.append(cuts)
        if not cuts:
            return _outcome(tsp, _edges((0, 1, 2), (3, 4, 5)), 6)
        return _outcome(tsp, _edges((0, 1, 2, 3, 4, 5)), 24)

    res = tsp.solve_cut_loop(m, solve_round, directed=False, budget_seconds=600.0, clock=FakeClock())
    assert calls == [(), ((0, 1, 2), (3, 4, 5))], "round 1 has no cut; round 2 has exactly the two components, in node order"
    assert (res.status, res.ub, res.lb, res.rounds, res.cuts) == ("optimal", 24, 24, 2, 2)
    assert tsp.validate_tour(m, res.tour, 24) == []


def test_cuts_are_added_in_a_fixed_order_whatever_the_order_of_the_arcs():
    tsp = _tsp()
    m = _ring_matrix(8)
    seen = []
    for perm_seed in (0, 1, 2):
        arcs = list(_edges((5, 3, 4), (2, 0, 1, 7, 6)))
        random.Random(perm_seed).shuffle(arcs)
        calls = []

        def solve_round(cuts, time_limit, arcs=tuple(arcs), calls=calls):
            calls.append(cuts)
            if not cuts:
                return _outcome(tsp, arcs, 1)
            return _outcome(tsp, _edges((0, 1, 2, 3, 4, 5, 6, 7)), tsp.tour_length(m, tuple(range(8))))

        tsp.solve_cut_loop(m, solve_round, directed=False, budget_seconds=600.0, clock=FakeClock())
        seen.append(calls[1])
    assert seen[0] == ((0, 1, 2, 6, 7), (3, 4, 5)) and seen[0] == seen[1] == seen[2]


def test_directed_loop_cuts_the_strong_components_not_the_weak_one():
    tsp = _tsp()
    m = _ring_matrix(4, symmetric=False)
    calls = []

    def solve_round(cuts, time_limit):
        calls.append(cuts)
        if not cuts:  # {0,1} and {2,3} are cycles joined by a one-way arc: weak = 1 component, strong = 2
            return _outcome(tsp, ((0, 1), (1, 0), (1, 2), (2, 3), (3, 2)), 20)
        return _outcome(tsp, _arcs((0, 1, 2, 3)), tsp.tour_length(m, (0, 1, 2, 3)))

    res = tsp.solve_cut_loop(m, solve_round, directed=True, budget_seconds=600.0, clock=FakeClock())
    assert calls[1] == ((0, 1), (2, 3))
    assert res.status == "optimal" and res.cuts == 2 and res.rounds == 2


def test_a_cut_is_added_for_every_component_of_the_solution_and_for_no_other_node_set():
    tsp = _tsp()
    m = _ring_matrix(9)
    calls = []

    def solve_round(cuts, time_limit):
        calls.append(cuts)
        if not cuts:
            return _outcome(tsp, _edges((0, 4, 8), (1, 2, 3), (5, 6, 7)), 1)
        return _outcome(tsp, _edges(tuple(range(9))), tsp.tour_length(m, tuple(range(9))))

    tsp.solve_cut_loop(m, solve_round, directed=False, budget_seconds=600.0, clock=FakeClock())
    assert calls[1] == ((0, 4, 8), (1, 2, 3), (5, 6, 7))


def test_the_time_budget_is_shared_between_the_re_solves():
    tsp = _tsp()
    n = 8
    m = tuple(tuple(10 * v for v in row) for row in _ring_matrix(n))  # every tour is longer than the fake bounds below
    clock = FakeClock()
    limits = []
    splits = [((0, 1, 2), (3, 4, 5, 6, 7)), ((0, 1, 3), (2, 4, 5, 6, 7)), ((0, 1, 4), (2, 3, 5, 6, 7)),
              ((0, 1, 5), (2, 3, 4, 6, 7))]

    def solve_round(cuts, time_limit):
        limits.append(time_limit)
        r = len(limits)
        clock.now += 250.0
        return _outcome(tsp, _edges(*splits[r - 1]), 100 + r, bound=90 + r, status="optimal", stop="optimal", wall=250.0)

    res = tsp.solve_cut_loop(m, solve_round, directed=False, budget_seconds=600.0, clock=clock)
    assert limits == [600.0, 350.0, 100.0], "every re-solve gets only the remaining time"
    assert res.rounds == 3, "no fourth solve once the budget is spent"
    assert res.stop_reason == "wall_limit" and res.timing_dependent is True
    assert res.status == "feasible_with_gap" and res.lb == 93 and res.ub is not None and res.ub >= res.lb
    assert tsp.validate_tour(m, res.tour, res.ub) == [] and res.ub_source == "cycle_patching"
    assert res.wall_seconds >= 750.0 and res.budget_seconds == 600.0


def test_a_solve_that_hits_its_time_limit_without_an_incumbent_is_bound_only_and_timing_dependent():
    tsp = _tsp()
    m = _ring_matrix(6)
    res = tsp.solve_cut_loop(m, lambda cuts, tl: tsp.RoundOutcome("bound_only", "wall_limit", None, 7, None, 600.0),
                             directed=False, budget_seconds=600.0, clock=FakeClock())
    assert (res.status, res.lb, res.ub, res.tour, res.timing_dependent, res.stop_reason) == \
        ("bound_only", 7, None, None, True, "wall_limit")


def test_a_time_limited_round_whose_incumbent_is_a_tour_gives_a_bracket():
    tsp = _tsp()
    m = _ring_matrix(6)
    tour = (0, 1, 2, 3, 4, 5)
    length = tsp.tour_length(m, tour)
    res = tsp.solve_cut_loop(
        m, lambda cuts, tl: tsp.RoundOutcome("feasible_with_gap", "wall_limit", length, length - 3, _edges(tour), 600.0),
        directed=False, budget_seconds=600.0, clock=FakeClock())
    assert (res.status, res.lb, res.ub, res.ub_source, res.timing_dependent) == \
        ("feasible_with_gap", length - 3, length, "solver_incumbent", True)


def test_a_solver_that_ignores_an_existing_cut_is_rejected_instead_of_looping_forever():
    tsp = _tsp()
    m = _ring_matrix(6)
    res = tsp.solve_cut_loop(m, lambda cuts, tl: _outcome(tsp, _edges((0, 1, 2), (3, 4, 5)), 30),
                             directed=False, budget_seconds=600.0, clock=FakeClock())
    assert res.status == "rejected" and "cut" in res.note
    assert res.rounds == 2


def test_the_final_tour_length_is_checked_against_the_objective():
    tsp = _tsp()
    m = _ring_matrix(6)
    tour = (0, 1, 2, 3, 4, 5)
    length = tsp.tour_length(m, tour)
    good = tsp.solve_cut_loop(m, lambda c, t: _outcome(tsp, _edges(tour), length), directed=False,
                              budget_seconds=600.0, clock=FakeClock())
    bad = tsp.solve_cut_loop(m, lambda c, t: _outcome(tsp, _edges(tour), length - 1), directed=False,
                             budget_seconds=600.0, clock=FakeClock())
    assert good.status == "optimal" and good.ub == length
    assert bad.status == "rejected" and "length" in bad.note


def test_proven_infeasible_and_failed_rounds_are_passed_through():
    tsp = _tsp()
    m = _ring_matrix(5)
    inf = tsp.solve_cut_loop(m, lambda c, t: tsp.RoundOutcome("infeasible_proven", "infeasible", None, None, None),
                             directed=False, budget_seconds=600.0, clock=FakeClock())
    bad = tsp.solve_cut_loop(m, lambda c, t: tsp.RoundOutcome("rejected", "solver_failure", None, None, None),
                             directed=False, budget_seconds=600.0, clock=FakeClock())
    assert inf.status == "infeasible_proven" and bad.status == "rejected"


def test_the_loop_validates_its_inputs():
    tsp = _tsp()
    with pytest.raises(ValueError):
        tsp.solve_cut_loop(_ring_matrix(2), lambda c, t: None, directed=False, budget_seconds=10.0)
    with pytest.raises(ValueError):
        tsp.solve_cut_loop(_ring_matrix(5, symmetric=False), lambda c, t: None, directed=False, budget_seconds=10.0)
    with pytest.raises(ValueError):
        tsp.solve_cut_loop(_ring_matrix(5), lambda c, t: None, directed=False, budget_seconds=0.0)
    with pytest.raises(ValueError):
        tsp.solve_cut_loop(((0, 1.5, 2), (1, 0, 3), (2, 3, 0)), lambda c, t: None, directed=False, budget_seconds=10.0)
    with pytest.raises(ValueError):
        tsp.solve_cut_loop(((0, -1, 2), (-1, 0, 3), (2, 3, 0)), lambda c, t: None, directed=False, budget_seconds=10.0)


# ---------------------------------------------------------------- solver comparison (section 6)
def _res(tsp, status, ub, lb, **kw):
    return tsp.TspResult(status=status, ub=ub, lb=lb, **kw)


def test_two_solvers_with_the_same_proven_optimum_agree():
    tsp = _tsp()
    cmp = tsp.compare_solvers(_res(tsp, "optimal", 100, 100, stop_reason="optimal"),
                              _res(tsp, "optimal", 100, 100, stop_reason="optimal"))
    assert (cmp.label, cmp.blocking) == ("agree", False)


def test_a_proven_difference_blocks():
    tsp = _tsp()
    cmp = tsp.compare_solvers(_res(tsp, "optimal", 100, 100), _res(tsp, "optimal", 101, 101))
    assert cmp.label == "disagree" and cmp.blocking is True


def test_a_time_limited_second_solver_is_labelled_and_does_not_block_unless_it_contradicts():
    tsp = _tsp()
    primary = _res(tsp, "optimal", 100, 100)
    slow = tsp.compare_solvers(primary, _res(tsp, "feasible_with_gap", 105, 98, stop_reason="wall_limit", timing_dependent=True))
    assert (slow.label, slow.blocking) == ("secondary_time_limited", False)
    bound_only = tsp.compare_solvers(primary, _res(tsp, "bound_only", None, 60, stop_reason="wall_limit", timing_dependent=True))
    assert (bound_only.label, bound_only.blocking) == ("secondary_time_limited", False)
    assert tsp.compare_solvers(primary, _res(tsp, "feasible_with_gap", 99, 90, stop_reason="wall_limit")).blocking, \
        "a valid tour shorter than the proven optimum is a contradiction"
    assert tsp.compare_solvers(primary, _res(tsp, "feasible_with_gap", 120, 101, stop_reason="wall_limit")).blocking, \
        "a lower bound above the proven optimum is a contradiction"


def test_a_failed_or_infeasible_second_solver_blocks():
    tsp = _tsp()
    primary = _res(tsp, "optimal", 100, 100)
    assert tsp.compare_solvers(primary, _res(tsp, "rejected", None, None)).blocking
    assert tsp.compare_solvers(primary, _res(tsp, "infeasible_proven", None, None)).blocking


# ---------------------------------------------------------------- boundaries
def test_importing_the_tsp_module_does_not_import_amplpy():
    code = ("import sys, uniride_core.exact.tsp; "
            "sys.exit(1 if 'amplpy' in sys.modules else 0)")
    res = subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_tsp_module_imports_neither_amplpy_at_top_level_nor_academic_benchmark_nor_optimizer_api():
    tree = ast.parse((EXACT / "tsp.py").read_text(encoding="utf-8"))
    top = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            top.append(node.module or "")
    assert not any(t.split(".")[0] == "amplpy" for t in top)
    allnames = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            allnames += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            allnames.append(node.module or "")
    banned = {"academic_benchmark", "optimizer_api"}
    assert not [a for a in allnames if a.split(".")[0] in banned]


def test_models_are_shipped_as_package_data_next_to_wave_sp():
    from importlib import resources

    models = resources.files("uniride_core.exact").joinpath("models")
    for name in ("wave_sp.mod", "tsp_dfj.mod", "tsp_mtz.mod"):
        assert models.joinpath(name).is_file(), name
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert '"uniride_core.exact" = ["models/*.mod"]' in pyproject


def test_without_ampl_the_public_entry_points_return_backend_unavailable_instead_of_raising(tmp_path):
    tsp = _tsp()
    m = _ring_matrix(5)
    env = {"UNIRIDE_AMPL_DIR": str(tmp_path)}  # a directory with no AMPL executable
    res = tsp.solve_tsp(m, environ=env)
    assert res.status == "backend_unavailable" and res.ub is None
    mtz = tsp.solve_tsp_mtz(m, environ=env)
    assert mtz.status == "backend_unavailable"


# ---------------------------------------------------------------- requires AMPL
_PROBE: dict = {}


def _require(solver: str) -> None:
    """Skip only for a genuinely absent backend; fail on any other probe problem."""
    from uniride_core.exact import ampl_backend

    if solver not in _PROBE:
        try:
            _PROBE[solver] = ampl_backend.probe_backend(solver)
        except Exception as exc:  # noqa: BLE001 - a backend defect must fail, never skip
            _PROBE[solver] = exc
    res = _PROBE[solver]
    if isinstance(res, Exception):
        pytest.fail(f"AMPL/{solver} probe raised (backend defect, not absence): {type(res).__name__}: {res}")
    if not res.available:
        pytest.skip(f"AMPL/{solver} unavailable: {res.reason}")
    assert (res.status, res.k, res.d, res.routes) == ("optimal", 1, 10, 1), f"AMPL/{solver} probe solve wrong: {res}"


@pytest.fixture(scope="module", params=SOLVERS)
def session(request):
    from uniride_core.exact import ampl_backend

    _require(request.param)
    with ampl_backend.AmplSession(ampl_backend.SolverSettings(solver=request.param, work_limit=None, peak_work_limit=None)) as s:
        yield s


def _check_optimal(tsp, m, res, want):
    assert res.status == "optimal", (res.status, res.note)
    assert res.ub == res.lb == want
    assert res.stop_reason == "optimal" and res.timing_dependent is False
    assert tsp.validate_tour(m, res.tour, res.ub) == []


@pytest.mark.requires_ampl
@pytest.mark.parametrize("symmetric", [True, False], ids=["symmetric", "asymmetric"])
def test_cut_loop_matches_brute_force_on_random_instances(session, symmetric):
    tsp = _tsp()
    rounds_with_cuts = 0
    for seed in range(25):
        n = 3 + seed % 7  # 3..9
        m = random_matrix(1000 * (1 if symmetric else 2) + seed, n, symmetric)
        res = tsp.solve_tsp(m, session=session, budget_seconds=60.0)
        _check_optimal(tsp, m, res, brute_force_tsp(m))
        rounds_with_cuts += res.cuts > 0
    assert rounds_with_cuts >= 3, "the oracle instances must exercise the cut loop"


@pytest.mark.requires_ampl
def test_two_separated_triangles_need_subtour_cuts_with_a_real_solver(session):
    tsp = _tsp()
    n = 6
    m = tuple(tuple(0 if i == j else (1 if (i < 3) == (j < 3) else 10) for j in range(n)) for i in range(n))
    res = tsp.solve_tsp(m, session=session, budget_seconds=60.0)
    _check_optimal(tsp, m, res, 24)
    assert res.rounds >= 2 and res.cuts >= 2


@pytest.mark.requires_ampl
def test_an_asymmetric_instance_with_cheap_two_cycles_needs_cuts(session):
    tsp = _tsp()
    n = 6
    m = [[0 if i == j else 50 for j in range(n)] for i in range(n)]
    for a, b in ((0, 1), (2, 3), (4, 5)):
        m[a][b] = m[b][a] = 1  # cheap 2-cycles: the assignment relaxation takes all three
    m[1][2] = m[3][4] = m[5][0] = 2
    m = tuple(tuple(r) for r in m)
    res = tsp.solve_tsp(m, session=session, budget_seconds=60.0)
    _check_optimal(tsp, m, res, brute_force_tsp(m))
    assert res.cuts >= 1


@pytest.mark.requires_ampl
@pytest.mark.parametrize("symmetric", [True, False], ids=["symmetric", "asymmetric"])
def test_mtz_cross_check_matches_brute_force(session, symmetric):
    tsp = _tsp()
    for seed in range(6):
        n = 3 + seed
        m = random_matrix(77 + seed, n, symmetric)
        res = tsp.solve_tsp_mtz(m, session=session, time_limit=60.0)
        _check_optimal(tsp, m, res, brute_force_tsp(m))


@pytest.mark.requires_ampl
def test_a_real_solve_obeys_a_tiny_total_budget_and_is_labelled_timing_dependent(session):
    tsp = _tsp()
    m = random_matrix(5, 9, True)
    res = tsp.solve_tsp(m, session=session, budget_seconds=0.05)
    assert res.status != "optimal" or res.rounds >= 1  # either it finished within the budget or it says it did not
    if res.status != "optimal":
        assert res.timing_dependent is True and res.stop_reason in ("wall_limit", "other_limit")
