"""Mechanism instrumentation for E2BSO / R2DMA / P-AOEA (repo code untouched).
The _solve source is copied in memory, logging lines are inserted, and the patched
function is bound to a subclass. Usage: python instrument.py <instance> <config:default|prod> <seed> <out.json>
"""
import sys, re, json, inspect, textwrap, random, math, time
import bench_common as bc
import uniride_core.algorithms.sota_tsp.e2bso_tsp as E
import uniride_core.algorithms.sota_tsp.r2dma_tsp as R
import uniride_core.algorithms.sota_tsp.paoea_tsp as P


def patched(cls, module, edits):
    src = textwrap.dedent(inspect.getsource(cls._solve))
    for pat, rep in edits:
        new, k = re.subn(pat, rep, src, count=1, flags=re.M)
        assert k == 1, ("pattern not found", pat)
        src = new
    ns = {}
    exec(compile(src, f"<patched {cls.__name__}>", "exec"), module.__dict__, ns)
    return ns["_solve"]


# ---------------- E2BSO ----------------
class E2BSO_I(E.E2BSO_TSP):
    def __init__(self, cfg):
        super().__init__(cfg)
        self._log, self._inj, self._edges = [], [], [0, 0, 0]  # forced attempted, applied, skipped(ia>ib)

    def _inject_diversity(self, population, pop_costs, rng):
        self._inj.append(len(self._log))
        return super()._inject_diversity(population, pop_costs, rng)

    def _swarm_update(self, individual, pbest, gbest, rng, n_edges, p_best, p_gbest):
        # replica of E2BSO_TSP._swarm_update with counters (same RNG call order)
        r = rng.random()
        if r < p_gbest: target = gbest
        elif r < p_gbest + p_best: target = pbest
        else: return self._perturb(individual, rng)
        te = {(min(target[i], target[(i + 1) % len(target)]), max(target[i], target[(i + 1) % len(target)])) for i in range(len(target))}
        ie = {(min(individual[i], individual[(i + 1) % len(individual)]), max(individual[i], individual[(i + 1) % len(individual)])) for i in range(len(individual))}
        new_edges = list(te - ie); rng.shuffle(new_edges)
        result = list(individual)
        for a, b in new_edges[:n_edges]:
            self._edges[0] += 1
            ia, ib = result.index(a), result.index(b)
            if abs(ia - ib) != 1 and not (ia == 0 and ib == len(result) - 1):
                if ia < ib:
                    result[ia + 1:ib + 1] = reversed(result[ia + 1:ib + 1]); self._edges[1] += 1
                else:
                    self._edges[2] += 1
        return result

E2BSO_I._solve = patched(E.E2BSO_TSP, E, [
    (r'^(\s*)if phase != "inject":', r'\1self._log.append((t, current_entropy, h_min, h_max, phase))\n\1if phase != "inject":'),
])

_lahc_stats = {"calls": 0, "acc": 0, "acc_worse": 0, "acc_by_inf": 0}
_orig_decide = E._LAHC.decide
def _decide(self, current_cost, new_cost, iteration, rng):
    ok = _orig_decide(self, current_cost, new_cost, iteration, rng)
    _lahc_stats["calls"] += 1
    if ok:
        _lahc_stats["acc"] += 1
        if new_cost > current_cost: _lahc_stats["acc_worse"] += 1
        if self._history[self._pos % len(self._history)] == float("inf") and new_cost >= current_cost: _lahc_stats["acc_by_inf"] += 1
    return ok
E._LAHC.decide = _decide


# ---------------- R2DMA ----------------
class R2DMA_I(R.R2DMA_TSP):
    def __init__(self, cfg):
        super().__init__(cfg); self._modes, self._acc = [], []

R2DMA_I._solve = patched(R.R2DMA_TSP, R, [
    (r'^(\s*)child_cost = _tour_cost\(child, self\._dist_matrix\)',
     r'\1self._modes.append((t, best_resonance, theta, mode))\n\1child_cost = _tour_cost(child, self._dist_matrix)'),
    (r'^(\s*)accepted = sa\.decide\(pop_costs\[i\], child_cost, rng\) and not is_dissonant',
     r'\1_sa_ok = sa.decide(pop_costs[i], child_cost, rng)\n\1accepted = _sa_ok and not is_dissonant\n\1self._acc.append((t, mode, bool(_sa_ok), bool(is_dissonant), child_cost / pop_costs[i], sa._temp / gbest_cost))'),
])


# ---------------- P-AOEA ----------------
class PAOEA_I(P.PAOEA_TSP):
    def __init__(self, cfg):
        super().__init__(cfg); self._acc, self._gen = [], []

PAOEA_I._solve = patched(P.PAOEA_TSP, P, [
    (r'^(\s*)improved = child_cost < pop_costs\[i\] - 1e-10',
     r'\1improved = child_cost < pop_costs[i] - 1e-10\n\1self._acc.append((t, genome.acceptance_type, bool(accepted), bool(improved), child_cost / pop_costs[i], id(genome)))'),
    (r'^(\s*)genomes = self\._evolve_genomes\(genomes, rng\)',
     r'\1self._gen.append((t, "before", [(id(g), g.fitness, g.total_trials, list(g.destroy_ops), list(g.repair_ops), g.acceptance_type, g.ls_intensity) for g in genomes]))\n\1genomes = self._evolve_genomes(genomes, rng)\n\1self._gen.append((t, "after", [(id(g), g.fitness, g.total_trials, list(g.destroy_ops), list(g.repair_ops), g.acceptance_type, g.ls_intensity) for g in genomes]))'),
])


def main(inst, conf, seed, out):
    dm, opt = bc.load_instance(inst)
    kw = dict(population_size=24, max_iterations=200) if conf == "prod" else {}
    res = {"instance": inst, "config": conf, "seed": seed, "opt": opt}

    _lahc_stats.update(calls=0, acc=0, acc_worse=0, acc_by_inf=0)
    s = E2BSO_I(E.E2BSOTSPConfig(seed=seed, time_limit=1e9, **kw)); t0 = time.monotonic(); r = s.solve_with_matrix(dm)
    res["E2BSO"] = dict(cost=r.tour_length, gap=100 * (r.tour_length - opt) / opt, time=time.monotonic() - t0,
                        log=s._log, inj_at=s._inj, edges=s._edges, lahc=dict(_lahc_stats), pop=s.cfg.population_size)

    s = R2DMA_I(R.R2DMATSPConfig(seed=seed, time_limit=1e9, **kw)); t0 = time.monotonic(); r = s.solve_with_matrix(dm)
    res["R2DMA"] = dict(cost=r.tour_length, gap=100 * (r.tour_length - opt) / opt, time=time.monotonic() - t0,
                        modes=s._modes, acc=s._acc, params=r.params)

    s = PAOEA_I(P.PAOEAConfig(seed=seed, time_limit=1e9, **kw)); t0 = time.monotonic(); r = s.solve_with_matrix(dm)
    res["P-AOEA"] = dict(cost=r.tour_length, gap=100 * (r.tour_length - opt) / opt, time=time.monotonic() - t0,
                         acc=s._acc, gen=s._gen)
    json.dump(res, open(out, "w"))
    print("done", inst, conf, seed, {k: round(res[k]["gap"], 3) for k in ["E2BSO", "R2DMA", "P-AOEA"]})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
