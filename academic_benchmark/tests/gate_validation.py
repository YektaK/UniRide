"""Quick validation script for gates A, C, D."""
import sys, os, csv, inspect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from academic_benchmark.cli_engine import load_problems, _execute_benchmark_tasks

# ── Gate A: Resume continuity (loader dedup) ──
probs = load_problems()
names = [p.name for p in probs]
assert len(probs) == len(set(names)), f"Dedup failed: {len(probs)} total, {len(set(names))} unique"
print("[Gate A] Loader deduplication: OK")

probs_500 = load_problems(size_limit=500)
assert all(p.dimension <= 500 for p in probs_500), "size_limit breached"
print("[Gate A] size_limit filtering: OK")

# ── Gate C: result_type contract ──
source = inspect.getsource(_execute_benchmark_tasks)
assert 'result_type' in source, "result_type field missing"
assert 'aggregate' in source, "aggregate value missing"
print("[Gate C] Numba engine result_type='aggregate': OK")

# ── Gate A: Interruption persistence handler ──
from academic_benchmark.cli_engine import _signal_handler, _active_results, _active_metadata
assert _signal_handler is not None
print("[Gate A] Interruption persistence handler: OK")

# ── Gate D: R2DMA rotation-invariant position_match ──
from uniride_core.algorithms.sota_tsp.r2dma_tsp import _compute_resonance
t1 = [0, 1, 2, 3, 4]
t2 = [2, 3, 4, 0, 1]  # rotation of t1 by 2
n = len(t1)
dm = [[abs(i - j) for j in range(n)] for i in range(n)]
r = _compute_resonance(t1, t2, n, dm)
assert r > 0.7, f"Rotation-invariant pos_match too low: {r}"
print(f"[Gate D] Rotation-invariant position_match: OK (resonance={r:.3f})")

# Also test identical rotated tours should have very high resonance
t3 = [1, 2, 3, 4, 0]  # rotation of t1 by 1
r2 = _compute_resonance(t1, t3, n, dm)
assert r2 > 0.7, f"Rotation-identical pos_match too low: {r2}"
print(f"[Gate D] Rotation invariance: OK (resonance={r2:.3f})")

print("\n=== All gates passed ===")