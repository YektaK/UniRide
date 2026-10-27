
import os, sys, json, time, math
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.abspath("numba_cache"))
sys.path.insert(0, os.path.abspath("."))
from bench_common import load_instance, tour_len, ROOT
from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig, R2DMA_TSP, R2DMATSPConfig, PAOEA_TSP, PAOEAConfig
import uniride_core.algorithms.sota_tsp.e2bso_tsp as E, uniride_core.algorithms.sota_tsp.r2dma_tsp as R, uniride_core.algorithms.sota_tsp.paoea_tsp as P

def run(alg, inst, seed, pop, iters):
    dm, opt = load_instance(inst)[:2]
    D = dm.tolist()
    ev = []   # (caller_line, injected_min_cost, gbest_at_time or None)
    if alg == "E2BSO":
        s = E2BSO_TSP(E2BSOTSPConfig(seed=seed, population_size=pop, max_iterations=iters, time_limit=3600))
        orig = s._inject_diversity
        def wrap(population, pop_costs, rng):
            line = sys._getframe(1).f_lineno
            before = list(pop_costs)
            popn, pc = orig(population, pop_costs, rng)
            changed = [pc[i] for i in range(len(pc)) if pc[i] != before[i]] or [min(pc)]
            ev.append((line, min(changed), None)); return popn, pc
        s._inject_diversity = wrap
    elif alg == "R2DMA":
        s = R2DMA_TSP(R2DMATSPConfig(seed=seed, population_size=pop, max_iterations=iters, time_limit=3600))
        orig = s._destructive_crossover
        def wrap(tour, rng):
            line = sys._getframe(1).f_lineno
            out = orig(tour, rng)
            ev.append((line, tour_len(out, dm), None)); return out
        s._destructive_crossover = wrap
    else:
        s = PAOEA_TSP(PAOEAConfig(seed=seed, population_size=pop, max_iterations=iters, time_limit=3600))
        orig = s._inject_diversity
        def wrap(population, pop_costs, best_tour, best_cost, rng):
            line = sys._getframe(1).f_lineno
            before = list(pop_costs)
            popn, pc = orig(population, pop_costs, best_tour, best_cost, rng)
            changed = [pc[i] for i in range(len(pc)) if pc[i] != before[i]] or [min(pc)]
            ev.append((line, min(changed), best_cost)); return popn, pc
        s._inject_diversity = wrap
    t0 = time.monotonic(); r = s.solve_with_matrix(dm); el = time.monotonic() - t0
    final = tour_len(r.tour, dm)
    inj = [e for e in ev]
    min_inj = min((e[1] for e in inj), default=None)
    return dict(alg=alg, inst=inst, seed=seed, pop=pop, iters=iters, opt=opt, final=final, elapsed=el,
                iterations=getattr(r, "iterations", None), n_events=len(inj),
                lines=sorted(set(e[0] for e in inj)), min_injected=min_inj,
                lost=(min_inj is not None and min_inj < final - 1e-9),
                strict_impr_events=sum(1 for e in inj if e[2] is not None and e[1] < e[2] - 1e-9),
                events=inj)

if __name__ == "__main__":
    wid, nw, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    jobs = [(a, i, s) for i in ["berlin52", "eil76", "rd100"] for a in ["E2BSO", "R2DMA", "P-AOEA"] for s in range(1, 6)]
    jobs = sorted(jobs, key=lambda j: (j[0] != "P-AOEA", j[1] != "rd100"))
    for k, (a, i, s) in enumerate(jobs):
        if k % nw != wid: continue
        res = run(a, i, s, 24, 200)
        with open(out, "a", encoding="utf-8") as fh: fh.write(json.dumps(res) + "\n")
        print(a, i, s, res["final"], res["n_events"], res["lost"], round(res["elapsed"],1), flush=True)
