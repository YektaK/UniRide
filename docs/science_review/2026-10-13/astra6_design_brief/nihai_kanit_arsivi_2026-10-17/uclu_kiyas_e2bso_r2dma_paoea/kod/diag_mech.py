"""Isolated diagnostics: R2DMA resonance + constructive crossover, E2BSO entropy floor,
compute_population_diversity sampling. Usage: python diag_mech.py <instance> <n_lo> <out.json>"""
import sys, json, random, itertools, statistics as st
import numpy as np
import bench_common as bc
import uniride_core.algorithms.sota_tsp.r2dma_tsp as R
import uniride_core.algorithms.sota_tsp.e2bso_tsp as E
from uniride_core.algorithms.sota_tsp.ls_engine import improve_2opt, MultiLayerLS, _tour_cost
from uniride_core.algorithms.utils import compute_population_diversity


def edges(t):
    n = len(t); return {(min(t[i], t[(i + 1) % n]), max(t[i], t[(i + 1) % n])) for i in range(n)}


def main(inst, n_lo, out):
    dm, opt = bc.load_instance(inst); n = len(dm); dml = dm.tolist(); rng = random.Random(7)
    res = {"instance": inst, "n": n}
    rnd = []
    los = []
    for k in range(n_lo):
        t = list(range(n)); rng.shuffle(t); rnd.append(list(t))
        lo, c = improve_2opt(t, dml, dm, 1000, False); los.append(list(lo))
    lo_cost = [_tour_cost(t, dml) for t in los]
    res["lo_gap_mean"] = 100 * (st.mean(lo_cost) - opt) / opt

    def reso(a, b): return R._compute_resonance(a, b, n, dml)
    base = los[0]
    rot = base[n // 3:] + base[:n // 3]
    rev = list(reversed(base))
    res["resonance_identical"] = reso(base, list(base))
    res["resonance_rotated_same_tour"] = reso(base, rot)
    res["resonance_reversed_same_tour"] = reso(base, rev)
    pairs = list(itertools.combinations(range(n_lo), 2))
    rr = [reso(rnd[i], rnd[j]) for i, j in pairs]
    ll = [reso(los[i], los[j]) for i, j in pairs]
    jac = [len(edges(los[i]) & edges(los[j])) / len(edges(los[i]) | edges(los[j])) for i, j in pairs]
    res["resonance_random_pairs"] = dict(mean=st.mean(rr), min=min(rr), max=max(rr))
    res["resonance_lo_pairs"] = dict(mean=st.mean(ll), min=min(ll), max=max(ll),
                                     frac_lt_0_3=sum(x < 0.3 for x in ll) / len(ll),
                                     frac_ge_0_7=sum(x >= 0.7 for x in ll) / len(ll))
    res["edge_jaccard_lo_pairs_mean"] = st.mean(jac)

    # constructive crossover: preservation of common edges and child quality
    s = R.R2DMA_TSP(R.R2DMATSPConfig(seed=1)); s._n = n; s._dist_matrix = dml; s._dist_matrix_np = dm
    pres, cr_before, cr_after, ox_before, ox_after = [], [], [], [], []
    rnd_after = []
    for (i, j) in pairs[:60]:
        p1, p2 = los[i], los[j]
        common = edges(p1) & edges(p2)
        child = s._constructive_crossover(p1, p2, rng)
        assert sorted(child) == list(range(n))
        pres.append(len(edges(child) & common) / max(1, len(common)))
        worse = max(_tour_cost(p1, dml), _tour_cost(p2, dml))
        cr_before.append(_tour_cost(child, dml) / worse)
        cr_after.append(MultiLayerLS.improve(child, dml, dm, "moderate", 200, 1e9, 12)[1] / worse)
        ox = s._ox_crossover(p1, p2, rng)
        ox_before.append(_tour_cost(ox, dml) / worse)
        ox_after.append(MultiLayerLS.improve(ox, dml, dm, "light", 100, 1e9, 12)[1] / worse)
        t = list(range(n)); rng.shuffle(t)
        rnd_after.append(MultiLayerLS.improve(t, dml, dm, "moderate", 200, 1e9, 12)[1] / worse)
    res["constructive"] = dict(common_edge_preserved_mean=st.mean(pres), child_cost_ratio_before_ls=st.mean(cr_before),
                               child_cost_ratio_after_ls=st.mean(cr_after),
                               frac_after_ls_better_than_worse_parent=sum(x < 1 for x in cr_after) / len(cr_after))
    res["ox_moderate"] = dict(child_cost_ratio_before_ls=st.mean(ox_before), child_cost_ratio_after_ls=st.mean(ox_after))
    res["random_restart_plus_ls_ratio"] = st.mean(rnd_after)

    # E2BSO entropy: floor (all-identical population) vs fully random population
    e = E.E2BSO_TSP(E.E2BSOTSPConfig()); e._n = n
    for P in (24, 40):
        res[f"entropy_identical_P{P}"] = e._edge_entropy([list(base) for _ in range(P)])
        res[f"entropy_lo_P{P}"] = e._edge_entropy([los[k % n_lo] for k in range(P)])
        res[f"entropy_floor_formula_P{P}"] = float(np.log2(n) / np.log2(P * n))
    # compute_population_diversity: uses only the first int(sqrt(P))+1 individuals
    pop = [list(base) for _ in range(7)] + [los[k % n_lo] for k in range(33)]
    res["diversity_first7_identical_rest_diverse"] = compute_population_diversity(pop, n)
    res["diversity_shuffled_order"] = compute_population_diversity(random.Random(3).sample(pop, len(pop)), n)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
