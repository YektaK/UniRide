import os, time, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

t0 = time.time()
from academic_benchmark.run_sota_benchmark import parse_tsplib, load_problems
print(f"Import: {time.time()-t0:.2f}s")

tsplib_dir = os.path.join(os.path.dirname(__file__), "tsplib_data")
t0 = time.time()
p = parse_tsplib(os.path.join(tsplib_dir, "a280.tsp"))
print(f"Parse a280: {time.time()-t0:.3f}s, n={p['dimension']}, coords={len(p['coordinates'])}")

print("Loading problems (size_limit=300)...")
t0 = time.time()
probs = load_problems(300)
elapsed = time.time() - t0
print(f"Load: {elapsed:.2f}s, {len(probs)} problems")
for name in sorted(probs):
    info = probs[name]
    print(f"  {name}: n={info['dimension']}, optimal={info.get('optimal')}")

print("Testing _run_solver_task subprocess function...")
from academic_benchmark.run_sota_benchmark import _run_solver_task
coords = probs["a280"]["coordinates"]
task = ("P-AOEA-TSP", coords, 42, 0, 280, 2579)
t0 = time.time()
res = _run_solver_task(task)
elapsed = time.time() - t0
if "error" in res:
    print(f"ERROR: {res['error'][:200]}")
else:
    print(f"OK: cost={res['tour_cost']} gap={res['gap_pct']}% time={elapsed:.1f}s")
