"""Exact TSP / ATSP by an iterative Dantzig-Fulkerson-Johnson cut loop (design EXACT_SOLVER_AMPL_DESIGN.md
sections 2, 4, 5, 6; WP-E7, DECISION_LOG E09).

* The cut loop is solver-agnostic: ``solve_cut_loop`` takes a ``solve_round(cuts, time_limit)`` callable.
  The AMPL implementation (``tsp_dfj.mod``, ``tsp_mtz.mod``) is built on ``AmplSession``; ``amplpy`` is
  imported lazily and never at module import time. Missing AMPL gives a result with status
  ``backend_unavailable``; public entry points do not raise ``ExactBackendUnavailable``.
* Loop: solve the degree-constrained model with the cuts found so far; find the connected (symmetric) or
  strongly connected (directed) components of the integer solution; if it is one Hamiltonian cycle the
  round optimum is the TSP optimum, else add one subtour cut ``arcs inside S <= |S| - 1`` per component and
  solve again. Separation is deterministic: components in sorted node order, cuts in that order.
* One wall-clock budget is shared by all re-solves (default 600 s, EQ6/E09): each solve gets the time that
  remains, and the loop stops before a solve when less than ``MIN_ROUND_SECONDS`` remain.
* A time-limited result is labelled ``feasible_with_gap`` (a valid tour exists, from the solver incumbent or
  from cycle patching) or ``bound_only``, with ``timing_dependent: true``. Every incumbent tour is validated
  as a Hamiltonian cycle and its recomputed length must equal the objective (separate from the VRP
  multi-route contract, AGENTS.md). ``optimal`` is only used for a proof.
* Data are an integer matrix; the diagonal is ignored (TSPLIB marks it "infinite" in some ATSP files).
  Symmetric matrices use edge variables (degree 2), asymmetric ones arc variables (in = out = 1).

Offline research tooling: not imported by optimizer_api or src, not in the production registry.
"""
from __future__ import annotations

import math
import numbers
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence, Tuple

from .ampl_backend import ExactBackendUnavailable

MIN_ROUND_SECONDS = 0.5
DEFAULT_BUDGET_SECONDS = 600.0  # EQ6 / DECISION_LOG E09: in total per instance, all re-solves together
DEFAULT_MTZ_SECONDS = 120.0
_TIMING_REASONS = ("wall_limit", "other_limit")
_INT_TOL = 1e-5
_INCUMBENT_STATUSES = ("optimal", "feasible_with_gap")
_KNOWN_ROUND_STATUSES = ("optimal", "feasible_with_gap", "bound_only", "infeasible_proven", "rejected")


# ---------------------------------------------------------------- result types
@dataclass(frozen=True)
class RoundOutcome:
    """One solve of the cut-loop model (what ``solve_round`` returns)."""

    status: str  # optimal, feasible_with_gap, bound_only, infeasible_proven, rejected
    stop_reason: Optional[str]
    objective: Optional[int]  # incumbent value of the degree-constrained model with the cuts so far
    bound_ceil: Optional[int]  # valid lower bound of this solve (rounded up)
    arcs: Optional[tuple]  # chosen arcs (directed) or edges (i < j, symmetric); None without an incumbent
    wall_seconds: float = 0.0
    solver_message: Optional[str] = None


@dataclass(frozen=True)
class RoundRecord:
    index: int
    status: str
    stop_reason: Optional[str]
    objective: Optional[int]
    bound_ceil: Optional[int]
    components: int
    cuts_added: int
    wall_seconds: float
    time_limit: float


@dataclass(frozen=True)
class TspResult:
    status: str  # optimal, feasible_with_gap, bound_only, infeasible_proven, rejected, backend_unavailable, not_run
    ub: Optional[int] = None  # length of the best tour found (validated)
    lb: Optional[int] = None  # valid lower bound (rounded up)
    tour: Optional[tuple] = None  # 0-based node order starting at node 0
    ub_source: Optional[str] = None  # "solver_incumbent" or "cycle_patching"
    stop_reason: Optional[str] = None
    timing_dependent: bool = False
    rounds: int = 0
    cuts: int = 0
    wall_seconds: float = 0.0  # whole loop, model generation included
    budget_seconds: Optional[float] = None
    round_log: tuple = ()
    note: str = ""
    model: str = "dfj"
    directed: Optional[bool] = None
    solver: Optional[str] = None
    solver_version: Optional[str] = None
    option_string: Optional[str] = None  # the verbatim option string of the first solve
    ampl_version: Optional[str] = None
    amplpy_version: Optional[str] = None
    ampl_location: Optional[str] = None
    threads: Optional[int] = None
    seed: Optional[int] = None


@dataclass(frozen=True)
class SolverComparison:
    label: str  # agree, secondary_time_limited, disagree, secondary_failed
    blocking: bool
    reason: str = ""


# ---------------------------------------------------------------- matrix and tours
def _check_matrix(matrix, directed: Optional[bool]) -> Tuple[int, bool]:
    n = len(matrix)
    if n < 3:
        raise ValueError("a tour needs at least 3 nodes")
    for i, row in enumerate(matrix):
        if len(row) != n:
            raise ValueError("the distance matrix must be square")
        for j, v in enumerate(row):
            if i == j:
                continue
            if isinstance(v, bool) or not isinstance(v, numbers.Integral):
                raise ValueError(f"matrix[{i}][{j}] is not an integer ({v!r})")
            if v < 0:
                raise ValueError(f"matrix[{i}][{j}] is negative")
    symmetric = all(matrix[i][j] == matrix[j][i] for i in range(n) for j in range(i + 1, n))
    if directed is None:
        directed = not symmetric
    elif not directed and not symmetric:
        raise ValueError("a symmetric (undirected) model needs a symmetric matrix")
    return n, bool(directed)


def components(n: int, arcs: Sequence[Tuple[int, int]], directed: bool) -> list:
    """Components of the chosen arcs, each a sorted tuple, ordered by smallest node.

    Directed: strongly connected components (iterative Tarjan); undirected: connected components.
    Nodes without arcs are singleton components.
    """
    succ = {i: [] for i in range(n)}
    for a, b in arcs:
        succ[a].append(b)
        if not directed:
            succ[b].append(a)
    for i in succ:
        succ[i].sort()
    out = []
    if not directed:
        seen = set()
        for s in range(n):
            if s in seen:
                continue
            stack, comp = [s], []
            seen.add(s)
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in succ[u]:
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            out.append(tuple(sorted(comp)))
    else:
        index, low, on_stack, stack, counter = {}, {}, set(), [], [0]
        for root in range(n):
            if root in index:
                continue
            work = [(root, 0)]
            while work:
                u, k = work.pop()
                if k == 0:
                    index[u] = low[u] = counter[0]
                    counter[0] += 1
                    stack.append(u)
                    on_stack.add(u)
                recursed = False
                for idx in range(k, len(succ[u])):
                    v = succ[u][idx]
                    if v not in index:
                        work.append((u, idx + 1))
                        work.append((v, 0))
                        recursed = True
                        break
                    if v in on_stack:
                        low[u] = min(low[u], index[v])
                if recursed:
                    continue
                if low[u] == index[u]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == u:
                            break
                    out.append(tuple(sorted(comp)))
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[u])
    out.sort(key=lambda c: c[0])
    return out


def _cycles_from_arcs(n: int, arcs: Sequence[Tuple[int, int]], directed: bool) -> Optional[list]:
    """The node cycles of a 2-regular (undirected) or permutation (directed) arc set, else None.

    Each cycle starts at its smallest node; undirected cycles go towards the smaller neighbour first, so the
    result does not depend on the order of ``arcs``.
    """
    if len(arcs) != n:
        return None
    if directed:
        nxt = {}
        indeg = [0] * n
        for a, b in arcs:
            if a in nxt or a == b:
                return None
            nxt[a] = b
            indeg[b] += 1
        if len(nxt) != n or any(d != 1 for d in indeg):
            return None
        step = lambda prev, cur: nxt[cur]  # noqa: E731
        start_next = lambda s: nxt[s]  # noqa: E731
    else:
        adj = {i: [] for i in range(n)}
        for a, b in arcs:
            if a == b:
                return None
            adj[a].append(b)
            adj[b].append(a)
        if any(len(v) != 2 for v in adj.values()):
            return None
        for v in adj.values():
            v.sort()
        step = lambda prev, cur: adj[cur][1] if adj[cur][0] == prev else adj[cur][0]  # noqa: E731
        start_next = lambda s: adj[s][0]  # noqa: E731
    seen, cycles = set(), []
    for s in range(n):
        if s in seen:
            continue
        cyc, prev, cur = [s], s, start_next(s)
        seen.add(s)
        while cur != s:
            if cur in seen:
                return None
            seen.add(cur)
            cyc.append(cur)
            prev, cur = cur, step(prev, cur)
        cycles.append(cyc)
    return cycles


def arcs_to_tour(n: int, arcs: Sequence[Tuple[int, int]], directed: bool) -> Optional[tuple]:
    """The Hamiltonian cycle formed by ``arcs`` as a node order from node 0, or None if it is not one."""
    cycles = _cycles_from_arcs(n, arcs, directed)
    if cycles is None or len(cycles) != 1:
        return None
    return tuple(cycles[0])


def tour_length(matrix, tour: Sequence[int]) -> int:
    t = tuple(tour)
    return sum(int(matrix[a][b]) for a, b in zip(t, t[1:] + t[:1]))


def validate_tour(matrix, tour: Sequence[int], objective: Optional[int] = None) -> list:
    """Errors of a claimed Hamiltonian cycle (empty when valid): every node exactly once, in range, and the
    recomputed closed length equals ``objective`` when one is given."""
    n = len(matrix)
    t = tuple(tour)
    errors = []
    if len(t) != n:
        errors.append(f"tour visits {len(t)} nodes, expected {n} (a tour over a subset is a subtour)")
    bad = [v for v in t if not isinstance(v, numbers.Integral) or isinstance(v, bool) or not 0 <= v < n]
    if bad:
        errors.append(f"tour holds nodes outside 0..{n - 1}: {bad[:5]}")
    elif len(set(t)) != len(t):
        errors.append("tour repeats a node")
    elif len(t) == n and objective is not None:
        recomputed = tour_length(matrix, t)
        if recomputed != objective:
            errors.append(f"tour length {recomputed} recomputed from the matrix differs from the claimed {objective}")
    return errors


def patch_to_tour(matrix, arcs: Sequence[Tuple[int, int]], directed: bool) -> Optional[tuple]:
    """Merge the cycles of a degree-feasible solution into one tour by repeated cheapest cycle merging.

    A deterministic upper-bound heuristic, used only when no round ended in a tour. None when ``arcs`` are
    not a permutation (directed) or 2-regular (undirected).
    """
    n = len(matrix)
    cycles = _cycles_from_arcs(n, arcs, directed)
    if cycles is None:
        return None
    m = matrix
    while len(cycles) > 1:
        best = None  # (delta, ia, ib, i, j, reverse)
        for ia in range(len(cycles)):
            for ib in range(ia + 1, len(cycles)):
                a_cyc = cycles[ia]
                for reverse in ((False, True) if not directed else (False,)):
                    b_cyc = cycles[ib][::-1] if reverse else cycles[ib]
                    for i in range(len(a_cyc)):
                        a, a2 = a_cyc[i], a_cyc[(i + 1) % len(a_cyc)]
                        for j in range(len(b_cyc)):
                            b, b2 = b_cyc[j], b_cyc[(j + 1) % len(b_cyc)]
                            delta = m[a][b2] + m[b][a2] - m[a][a2] - m[b][b2]
                            key = (delta, ia, ib, i, j, reverse)
                            if best is None or key < best:
                                best = key
        _, ia, ib, i, j, reverse = best
        a_cyc = cycles[ia]
        b_cyc = cycles[ib][::-1] if reverse else cycles[ib]
        merged = a_cyc[:i + 1] + [b_cyc[(j + 1 + k) % len(b_cyc)] for k in range(len(b_cyc))] + a_cyc[i + 1:]
        cycles = [c for k, c in enumerate(cycles) if k not in (ia, ib)] + [merged]
        cycles.sort(key=lambda c: min(c))
    tour = cycles[0]
    k = tour.index(0)
    tour = tour[k:] + tour[:k]
    if not directed and len(tour) > 2 and tour[1] > tour[-1]:
        tour = [tour[0]] + tour[:0:-1]
    return tuple(tour)


# ---------------------------------------------------------------- the cut loop
def solve_cut_loop(matrix, solve_round: Callable[[tuple, float], RoundOutcome], *, directed: Optional[bool] = None,
                   budget_seconds: float = DEFAULT_BUDGET_SECONDS, clock: Callable[[], float] = time.monotonic) -> TspResult:
    """DFJ cut loop over an integer matrix (see the module docstring).

    ``solve_round(cuts, time_limit)`` solves the degree-constrained model with ``cuts`` (a tuple of sorted node
    tuples) within ``time_limit`` seconds. ``clock`` is injectable for tests.
    """
    n, directed = _check_matrix(matrix, directed)
    if not budget_seconds > 0:
        raise ValueError("budget_seconds must be positive")
    t0 = clock()
    cuts: list = []
    log: list = []
    lb: Optional[int] = None
    best_ub: Optional[int] = None
    best_tour: Optional[tuple] = None
    ub_source: Optional[str] = None
    stop: Optional[str] = None

    def elapsed() -> float:
        return clock() - t0

    def result(status, **kw) -> TspResult:
        timing = kw.get("stop_reason") in _TIMING_REASONS
        return TspResult(status=status, rounds=len(log), cuts=len(cuts), wall_seconds=round(elapsed(), 4),
                         budget_seconds=float(budget_seconds), round_log=tuple(log), directed=directed,
                         timing_dependent=timing, **kw)

    def offer(tour: Optional[tuple], source: str) -> None:
        nonlocal best_ub, best_tour, ub_source
        if tour is None:
            return
        length = tour_length(matrix, tour)
        if best_ub is None or length < best_ub:
            best_ub, best_tour, ub_source = length, tour, source

    while True:
        remaining = budget_seconds - elapsed()
        if remaining < MIN_ROUND_SECONDS:
            stop = "wall_limit"
            break
        limit = math.floor(remaining * 10) / 10  # a one-decimal limit never exceeds what is left
        out = solve_round(tuple(cuts), limit)
        idx = len(log) + 1
        if out.status not in _KNOWN_ROUND_STATUSES:
            log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, 0, 0, out.wall_seconds, limit))
            return result("rejected", lb=lb, stop_reason="solver_failure", note=f"unknown round status {out.status!r}")
        if out.status in ("infeasible_proven", "rejected"):
            log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, 0, 0, out.wall_seconds, limit))
            return result(out.status, lb=lb, stop_reason=out.stop_reason,
                          note=out.solver_message or ("" if out.status == "infeasible_proven" else "solver round failed"))
        if out.bound_ceil is not None:
            lb = out.bound_ceil if lb is None else max(lb, out.bound_ceil)
        comps = []
        tour = None
        if out.arcs is not None and out.objective is not None:
            tour = arcs_to_tour(n, out.arcs, directed)
            if tour is not None:
                errors = validate_tour(matrix, tour, out.objective)
                if errors:
                    log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, 1, 0, out.wall_seconds, limit))
                    return result("rejected", lb=lb, stop_reason="solver_failure", note="tour check failed: " + "; ".join(errors))
                offer(tour, "solver_incumbent")
            else:
                offer(patch_to_tour(matrix, out.arcs, directed), "cycle_patching")
                comps = [c for c in components(n, out.arcs, directed) if 2 <= len(c) < n]
        if out.status == "optimal" and tour is not None:
            log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, 1, 0, out.wall_seconds, limit))
            if lb is not None and lb > out.objective:
                return result("rejected", lb=lb, ub=out.objective, stop_reason="solver_failure",
                              note="a round bound above a later tour length: inconsistent solver results")
            return result("optimal", ub=out.objective, lb=out.objective, tour=tour, ub_source="solver_incumbent",
                          stop_reason="optimal")
        if out.status == "optimal" and tour is None:
            if not comps:
                log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, 0, 0, out.wall_seconds, limit))
                return result("rejected", lb=lb, stop_reason="solver_failure",
                              note="the round solution is neither a tour nor made of cycles with a cut to add")
            existing = set(cuts)
            if any(c in existing for c in comps):
                log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, len(comps), 0, out.wall_seconds, limit))
                return result("rejected", lb=lb, stop_reason="solver_failure",
                              note="the solver returned a solution that violates an existing subtour cut")
            cuts.extend(comps)
            log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, len(comps), len(comps), out.wall_seconds, limit))
            continue
        # a round that did not finish (time or other limit, gap tolerance, no incumbent): the loop ends here
        log.append(RoundRecord(idx, out.status, out.stop_reason, out.objective, out.bound_ceil, len(comps) or (1 if tour else 0), 0,
                               out.wall_seconds, limit))
        stop = out.stop_reason or "other_limit"
        break

    if best_ub is not None and lb is not None and best_ub < lb:
        return result("rejected", lb=lb, ub=best_ub, stop_reason="solver_failure",
                      note="a valid tour is shorter than a reported lower bound: inconsistent solver results")
    if best_ub is not None and lb is not None and best_ub == lb:
        return result("optimal", ub=best_ub, lb=lb, tour=best_tour, ub_source=ub_source, stop_reason="optimal")
    if best_ub is not None:
        return result("feasible_with_gap", ub=best_ub, lb=lb, tour=best_tour, ub_source=ub_source, stop_reason=stop)
    if lb is not None:
        return result("bound_only", lb=lb, stop_reason=stop)
    return result("not_run", stop_reason=stop, note="no solve could start within the budget")


# ---------------------------------------------------------------- two-solver comparison (design section 6)
def compare_solvers(primary: TspResult, secondary: TspResult) -> SolverComparison:
    """Compare a second solver's result with the primary one. A proven difference or any contradiction between
    the two (a tour shorter than the other's bound, a bound above the other's tour) blocks; a time-limited
    second solver that does not contradict is labelled and does not block."""
    if secondary.status in ("rejected", "infeasible_proven", "backend_unavailable", "not_run"):
        if primary.status == "infeasible_proven" and secondary.status == "infeasible_proven":
            return SolverComparison("agree", False, "both proven infeasible")
        return SolverComparison("secondary_failed", True, f"second solver status {secondary.status}")
    if primary.status == "optimal" and secondary.status == "optimal":
        if primary.ub == secondary.ub:
            return SolverComparison("agree", False, "")
        return SolverComparison("disagree", True, f"proven optima differ: {primary.ub} vs {secondary.ub}")
    for a, b, an, bn in ((primary, secondary, "primary", "second solver"), (secondary, primary, "second solver", "primary")):
        if a.ub is not None and b.lb is not None and b.lb > a.ub:
            return SolverComparison("disagree", True, f"{bn} lower bound {b.lb} exceeds the {an} tour length {a.ub}")
    return SolverComparison("secondary_time_limited", False, "second solver not proven within its limit; no contradiction")


# ---------------------------------------------------------------- AMPL implementation
def _model_path(name: str) -> str:
    from importlib import resources

    return str(Path(str(resources.files("uniride_core.exact").joinpath("models", name))))


def _arc_set(n: int, directed: bool) -> list:
    if directed:
        return [(i, j) for i in range(n) for j in range(n) if i != j]
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


class _AmplRounds:
    """``solve_round`` over one AMPL model instance (tsp_dfj.mod, or tsp_mtz.mod when ``mtz``)."""

    def __init__(self, session, matrix, directed: bool, mtz: bool = False):
        a = session.ampl
        self.session, self.mtz, self.n = session, mtz, len(matrix)
        a.reset()
        a.read(_model_path("tsp_mtz.mod" if mtz else "tsp_dfj.mod"))
        a.param["n"] = self.n
        if not mtz:
            a.param["directed"] = int(directed)
        arcs = _arc_set(self.n, directed)
        a.set["ARCS"] = arcs
        a.param["cost"] = {(i, j): int(matrix[i][j]) for i, j in arcs}
        self.installed = 0

    def __call__(self, cuts, time_limit: float) -> RoundOutcome:
        a = self.session.ampl
        if cuts and len(cuts) != self.installed:
            a.set["CUTS"] = list(range(1, len(cuts) + 1))
            a.param["csize"] = {k + 1: len(c) for k, c in enumerate(cuts)}
            a.param["member"] = {(k + 1, i): 1 for k, c in enumerate(cuts) for i in c}
            self.installed = len(cuts)
        res = self.session.solve_objective("Tour", wall_limit=time_limit)
        arcs = None
        status, reason = res.status, res.stop_reason
        if res.objective is not None:
            values = a.var["x"].get_values().to_dict()
            chosen = []
            for key, v in values.items():
                if abs(v - round(v)) > _INT_TOL:
                    return RoundOutcome("rejected", "solver_failure", None, None, None, res.wall_seconds or 0.0,
                                        "fractional incumbent")
                if round(v) > 0:
                    chosen.append((int(key[0]), int(key[1])))
            arcs = tuple(sorted(chosen))
        return RoundOutcome(status, reason, res.objective, res.bound_ceil, arcs, res.wall_seconds or 0.0, res.solver_message)


def _annotate(res: TspResult, session, settings, model: str, budget: float) -> TspResult:
    from dataclasses import replace

    from .ampl_backend import solver_option_string

    first = replace(settings, wall_limit=math.floor(budget * 10) / 10)
    return replace(res, model=model, solver=settings.solver, solver_version=session.solver_version,
                   option_string=solver_option_string(first, peak=False), ampl_version=session.ampl_version,
                   amplpy_version=session.amplpy_version, ampl_location=session.location, threads=settings.threads,
                   seed=settings.seed)


def _default_settings(settings=None):
    from .ampl_backend import SolverSettings

    return settings or SolverSettings(work_limit=None, peak_work_limit=None)


def solve_tsp(matrix, *, settings=None, budget_seconds: float = DEFAULT_BUDGET_SECONDS, session=None,
              directed: Optional[bool] = None, environ: Optional[Mapping[str, str]] = None) -> TspResult:
    """Solve a TSP/ATSP to proven optimality (or a labelled bracket) with the DFJ cut loop in AMPL.

    One shared ``budget_seconds`` covers every re-solve. Never raises ``ExactBackendUnavailable``.
    """
    from .ampl_backend import AmplSession

    n, directed = _check_matrix(matrix, directed)  # input errors are ValueError, before any backend start
    settings = session.settings if session is not None else _default_settings(settings)

    def run(s) -> TspResult:
        rounds = _AmplRounds(s, matrix, directed)
        res = solve_cut_loop(matrix, rounds, directed=directed, budget_seconds=budget_seconds)
        return _annotate(res, s, s.settings, "dfj", budget_seconds)

    try:
        if session is not None:
            return run(session)
        with AmplSession(settings, environ) as s:
            return run(s)
    except ExactBackendUnavailable as exc:
        return TspResult(status="backend_unavailable", note=str(exc), budget_seconds=float(budget_seconds), directed=directed)


def solve_tsp_mtz(matrix, *, settings=None, time_limit: float = DEFAULT_MTZ_SECONDS, session=None,
                  environ: Optional[Mapping[str, str]] = None) -> TspResult:
    """Single MTZ solve (``tsp_mtz.mod``): a small-n cross-check of the cut loop, never the primary method."""
    from .ampl_backend import AmplSession

    _check_matrix(matrix, None)
    settings = session.settings if session is not None else _default_settings(settings)

    def run(s) -> TspResult:
        rounds = _AmplRounds(s, matrix, True, mtz=True)
        res = solve_cut_loop(matrix, rounds, directed=True, budget_seconds=time_limit)
        return _annotate(res, s, s.settings, "mtz", time_limit)

    try:
        if session is not None:
            return run(session)
        with AmplSession(settings, environ) as s:
            return run(s)
    except ExactBackendUnavailable as exc:
        return TspResult(status="backend_unavailable", note=str(exc), budget_seconds=float(time_limit), model="mtz", directed=True)
