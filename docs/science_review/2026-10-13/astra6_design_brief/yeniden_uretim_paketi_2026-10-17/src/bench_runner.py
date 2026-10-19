"""bench_runner.py -- task-list benchmark runner (<= 3 worker processes).
usage: python bench_runner.py tasks.json out.jsonl n_workers
A task = {"arm":..., "inst":..., "seed":..., "T":..., "params":{...}}.  Completed tasks already
present in out.jsonl are skipped (restartable)."""
import os, sys, json, time, random
sys.dont_write_bytecode = True
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.abspath("numba_cache"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import numpy as np

_BC = None


def _bc():
    global _BC
    if _BC is None:
        import bench_common as bc  # imports repo modules (read-only)
        _BC = bc
    return _BC


def load(inst):
    from inst import load_tsp, load_atsp
    return load_atsp(inst) if inst == "ft53" else load_tsp(inst)


def init_worker(arms):
    from ils_fast import warmup
    warmup()
    if "repo_ils" in arms:
        bc = _bc()
        xy = np.random.RandomState(0).rand(40, 2) * 100
        dm = np.floor(np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1)) + 0.5)
        bc.ils(dm, 0.3, 0)
    if any(a.startswith("px") for a in arms):
        from px_ils import px_ils
        xy = np.random.RandomState(1).rand(60, 2) * 100
        dm = np.floor(np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1)) + 0.5)
        px_ils(dm, 0.3, 0, m=4, epoch_kicks=50)


def tour_ok(t, n):
    return len(t) == n and np.array_equal(np.sort(np.asarray(t)), np.arange(n))


def run_task(task):
    from fast_ls import tour_cost
    arm, inst, seed, T = task["arm"], task["inst"], int(task["seed"]), float(task["T"])
    P = task.get("params", {})
    dm, opt = load(inst)
    n = len(dm)
    rec = dict(arm=arm, inst=inst, n=n, seed=seed, T=T, opt=opt, params=P)
    t0 = time.perf_counter()
    if arm == "ils_fast":
        from ils_fast import ils_fast
        r = ils_fast(dm, T, seed, **P)
        tour = r.pop("tour")
        rec.update({k: v for k, v in r.items()})
        rec["iterations"] = r["kicks"]
    elif arm in ("px_on", "px_off"):
        from px_ils import px_ils
        r = px_ils(dm, T, seed, use_gpx=(arm == "px_on"), **P)
        tour = r.pop("tour")
        rec.update(r)
        rec["iterations"] = r["kicks"]
    elif arm == "repo_ils":
        bc = _bc()
        tour, c, el, it = bc.ils(dm, T, seed)
        rec.update(iterations=int(it), repo_elapsed=el)
    elif arm == "lkh":
        bc = _bc()
        tour, c, el = bc.lkh(dm, int(P.get("runs", 10)), seed)
    elif arm == "lkh_atsp_native":
        import elkai
        m = elkai.DistanceMatrix(dm.astype(int).tolist())
        tour = m.solve_tsp(runs=int(P.get("runs", 10)))
        tour = tour[:-1] if len(tour) > n else tour
        rec["elkai_problem_type"] = "ATSP" if not np.array_equal(dm, dm.T) else "TSP"
    elif arm == "lkh_atsp_2n":
        import elkai
        M = int(dm.max()) * 4 + 1000
        BIG = M * 20
        D = np.full((2 * n, 2 * n), BIG, dtype=np.int64)
        for i in range(n):
            for j in range(n):
                if i != j:
                    D[i, n + j] = D[n + j, i] = int(dm[i, j]) + M   # i -> j  as edge (i, j')
            D[i, n + i] = D[n + i, i] = 0                            # ghost edge (i, i')
        np.fill_diagonal(D, 0)
        t2 = elkai.DistanceMatrix(D.tolist()).solve_tsp(runs=int(P.get("runs", 10)))
        t2 = t2[:-1] if len(t2) > 2 * n else t2
        # orient so that each real city i is followed by its ghost i' ; read cities in order
        k = t2.index(0)
        t2 = t2[k:] + t2[:k]
        if t2[1] != n + 0:
            t2 = [t2[0]] + t2[1:][::-1]
        tour = [v for v in t2 if v < n]
        # directed cost i -> j uses edge (i', j): ghost i' precedes j, so the city order is reversed
        c_fwd = tour_cost(dm, np.asarray(tour, np.int32))
        c_rev = tour_cost(dm, np.asarray(tour[::-1], np.int32))
        if c_rev < c_fwd:
            tour = tour[::-1]
        rec["transform_M"] = M
    else:
        raise ValueError(arm)
    rec["wall"] = time.perf_counter() - t0
    tour = np.asarray(tour, np.int32)
    rec["valid"] = bool(tour_ok(tour, n))
    rec["cost"] = float(tour_cost(dm, tour))
    rec["gap"] = 100.0 * (rec["cost"] / opt - 1.0)
    rec["is_opt"] = bool(rec["cost"] <= opt + 1e-9)
    rec["tour"] = tour.tolist()
    return rec


def _key(t):
    return (t["arm"], t["inst"], int(t["seed"]), json.dumps(t.get("params", {}), sort_keys=True))


def done_keys(prefix):
    import glob
    done = set()
    for f in glob.glob(prefix + "_w*.jsonl"):
        for line in open(f):
            line = line.strip()
            if line:
                done.add(_key(json.loads(line)))
    return done


if __name__ == "__main__":
    # usage: python bench_runner.py tasks.json out_prefix worker_id
    # Independent worker processes (the sandbox forbids multiprocessing pipes).  Tasks are claimed
    # with atomic O_EXCL claim files in <out_prefix>_claims/; results go to <out_prefix>_w<id>.jsonl.
    tasks = json.load(open(sys.argv[1]))
    prefix, wid = sys.argv[2], int(sys.argv[3])
    cdir = prefix + "_claims"
    os.makedirs(cdir, exist_ok=True)
    done = done_keys(prefix)
    todo = [t for t in tasks if _key(t) not in done]
    random.Random(12345).shuffle(todo)         # spread CPU contention over arms
    arms = sorted({t["arm"] for t in todo})
    print(f"worker {wid}: {len(todo)} open tasks ({len(done)} done), arms={arms}", flush=True)
    init_worker(arms)
    import hashlib
    k = 0
    with open(f"{prefix}_w{wid}.jsonl", "a") as fo:
        for t in todo:
            h = hashlib.md5(repr(_key(t)).encode()).hexdigest()
            try:
                fd = os.open(os.path.join(cdir, h + ".claim"), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
            except FileExistsError:
                continue
            rec = run_task(t)
            fo.write(json.dumps(rec) + "\n"); fo.flush()
            k += 1
            print(f"[w{wid} #{k}] {rec['arm']:9s} {rec['inst']:8s} s{rec['seed']} "
                  f"gap={rec['gap']:.3f}% wall={rec['wall']:.1f}s it={rec.get('iterations', '-')}", flush=True)
    print(f"worker {wid} finished", flush=True)
