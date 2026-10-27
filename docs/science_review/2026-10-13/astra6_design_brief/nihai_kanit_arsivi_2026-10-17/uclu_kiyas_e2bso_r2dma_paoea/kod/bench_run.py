"""Benchmark worker. Usage: python bench_run.py <jobs.json> <worker_id> <n_workers> <out.jsonl>
Each job: {"alg","inst","seed","budget", optional "kw"}. Appends one JSON line per finished job."""
import sys, json, time, os
import bench_common as bc

_cache = {}
def inst(name):
    if name not in _cache: _cache[name] = bc.load_instance(name)
    return _cache[name]

def run(job):
    dm, opt = inst(job["inst"]); B = job["budget"]; seed = job["seed"]; alg = job["alg"]; kw = job.get("kw", {})
    if alg in ("E2BSO", "R2DMA", "P-AOEA"):
        t, c, el, it = bc.run_sota(alg, dm, B, seed, **kw)
    elif alg == "ILS":
        t, c, el, it = bc.ils(dm, B, seed)
    elif alg == "GLS":
        t, c, el = bc.ortools_gls(dm, B, seed); it = None
    elif alg == "LKH":
        t, c, el = bc.lkh(dm, job.get("runs", 10), seed); it = None
    else:
        raise ValueError(alg)
    return dict(job, cost=c, opt=opt, gap=100 * (c - opt) / opt, elapsed=el, iterations=it)

if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1])); wid, nw = int(sys.argv[2]), int(sys.argv[3]); out = sys.argv[4]
    done = set()
    if os.path.exists(out):
        for l in open(out):
            r = json.loads(l); done.add((r["alg"], r["inst"], r["seed"], r.get("tag", "")))
    for k, job in enumerate(jobs):
        if k % nw != wid or (job["alg"], job["inst"], job["seed"], job.get("tag", "")) in done: continue
        r = run(job)
        with open(out, "a") as f: f.write(json.dumps(r) + "\n")
        print(wid, job["alg"], job["inst"], job["seed"], round(r["gap"], 3), round(r["elapsed"], 1), flush=True)
