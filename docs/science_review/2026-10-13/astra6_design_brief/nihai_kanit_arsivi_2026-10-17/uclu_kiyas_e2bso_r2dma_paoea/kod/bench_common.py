
import os, sys, math, time, random, sqlite3
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.abspath("numba_cache"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
ROOT = r"C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide"
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import numpy as np
from uniride_core.algorithms.sota_tsp import (E2BSO_TSP, E2BSOTSPConfig, R2DMA_TSP, R2DMATSPConfig,
    PAOEA_TSP, PAOEAConfig, ALNS_TSP, ALNSConfig)
from uniride_core.algorithms.sota_tsp.ls_engine import MultiLayerLS, _tour_cost
from uniride_core.algorithms import numba_accel as _nb

def load_instance(name):
    path = os.path.join(ROOT, "academic_benchmark", "tsplib_data", name + ".tsp")
    coords, ewt, sec = [], None, False
    for line in open(path, encoding="utf-8", errors="ignore"):
        s = line.strip()
        if s.startswith("EDGE_WEIGHT_TYPE"): ewt = s.split(":")[-1].strip()
        if s.startswith("NODE_COORD_SECTION"): sec = True; continue
        if s.startswith("EOF"): break
        if sec and s:
            p = s.split(); coords.append((float(p[1]), float(p[2])))
    assert ewt == "EUC_2D", (name, ewt)
    xy = np.array(coords)
    d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1))
    dm = np.floor(d + 0.5)
    np.fill_diagonal(dm, 0.0)
    con = sqlite3.connect("file:" + os.path.join(ROOT, "academic_benchmark", "tsplib_data", "tsplib.db") + "?mode=ro", uri=True)
    opt = con.execute("select optimal from problems where name=?", (name,)).fetchone()[0]
    con.close()
    return dm, float(opt)

def tour_len(t, dm):
    t = np.asarray(t); return float(dm[t, np.roll(t, -1)].sum())

def ls_moderate(t, dm_list, dm_np):
    t2, c2, _ = MultiLayerLS.improve(t, dm_list, dm_np, "moderate", 200, 1e9, 12)
    return t2, c2

def ils(dm, time_limit, seed):
    """Plain ILS: random start, same LS as SOTA family (2-opt + Or-opt, repo numba kernels),
    double-bridge kick, accept if not worse. Control arm with identical components."""
    rng = random.Random(seed); n = len(dm); dm_list = dm.tolist()
    t0 = time.monotonic()
    tour = list(range(n)); rng.shuffle(tour)
    cur, cc = ls_moderate(tour, dm_list, dm)
    best, bc = list(cur), cc; it = 0
    while time.monotonic() - t0 < time_limit:
        it += 1
        i, j, k = sorted(rng.sample(range(1, n), 3))
        cand = cur[:i] + cur[j:k] + cur[i:j] + cur[k:]
        cand, c = ls_moderate(cand, dm_list, dm)
        if c <= cc:
            cur, cc = cand, c
            if c < bc: best, bc = list(cand), c
    return best, bc, time.monotonic() - t0, it

def lkh(dm, runs, seed):
    import elkai
    t0 = time.monotonic()
    m = elkai.DistanceMatrix(dm.astype(int).tolist())
    tour = m.solve_tsp(runs=runs)
    tour = tour[:-1] if len(tour) > len(dm) else tour
    return tour, tour_len(tour, dm), time.monotonic() - t0

def ortools_gls(dm, time_limit, seed):
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    n = len(dm); D = dm.astype(int).tolist()
    mgr = pywrapcp.RoutingIndexManager(n, 1, 0); rt = pywrapcp.RoutingModel(mgr)
    cb = rt.RegisterTransitCallback(lambda a, b: D[mgr.IndexToNode(a)][mgr.IndexToNode(b)])
    rt.SetArcCostEvaluatorOfAllVehicles(cb)
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.FromMilliseconds(int(time_limit * 1000))
    t0 = time.monotonic(); sol = rt.SolveWithParameters(p)
    idx = rt.Start(0); tour = []
    while not rt.IsEnd(idx): tour.append(mgr.IndexToNode(idx)); idx = sol.Value(rt.NextVar(idx))
    return tour, tour_len(tour, dm), time.monotonic() - t0

def run_sota(alg, dm, time_limit, seed, max_iterations=500, **kw):
    if alg == "E2BSO": s = E2BSO_TSP(E2BSOTSPConfig(seed=seed, time_limit=time_limit, max_iterations=max_iterations, **kw))
    elif alg == "R2DMA": s = R2DMA_TSP(R2DMATSPConfig(seed=seed, time_limit=time_limit, max_iterations=max_iterations, **kw))
    elif alg == "P-AOEA": s = PAOEA_TSP(PAOEAConfig(seed=seed, time_limit=time_limit, max_iterations=max_iterations, **kw))
    elif alg == "ALNS": s = ALNS_TSP(ALNSConfig(seed=seed, **kw))
    t0 = time.monotonic(); r = s.solve_with_matrix(dm); el = time.monotonic() - t0
    assert sorted(r.tour) == list(range(len(dm)))
    return r.tour, tour_len(r.tour, dm), el, r.iterations
