"""Allow running ``python -m uniride_core.algorithms.sota_common`` for smoke tests."""

from uniride_core.algorithms.sota_common import *  # noqa: F401, F403
from uniride_core.algorithms.sota_common.__init__ import SOTA_INFRA_VERSION  # type: ignore

if __name__ == "__main__":
    import importlib
    import sys

    # Re-run the __init__ smoke test block
    mod = importlib.import_module("uniride_core.algorithms.sota_common")
    # The __init__.py __name__ == "__main__" won't trigger via -m,
    # so we execute the test code here.
    import random as _random

    print(f"SOTA Common Infrastructure v{SOTA_INFRA_VERSION}")
    print("=" * 55)

    errors: list = []

    # -- 1. MultiStartInitializer --
    try:
        rng = _random.Random(42)
        waypoints = [f"c{i}" for i in range(10)]
        dm = {
            w: {f"c{j}": float(abs(i - j)) for j in range(10)}
            for i, w in enumerate(waypoints)
        }
        pop = MultiStartInitializer.generate_population(
            waypoints, dm, pop_size=8, rng=rng, depot="c0"
        )
        assert len(pop) == 8, f"Expected 8, got {len(pop)}"
        print("[OK] MultiStartInitializer")
    except Exception as exc:
        errors.append(f"MultiStartInitializer: {exc}")
        print(f"[FAIL] MultiStartInitializer: {exc}")

    # -- 2. MultiLayerLS --
    try:
        rng = _random.Random(42)
        tour = [f"c{i}" for i in range(10)]
        cost_fn = lambda t: sum(1 for i in range(len(t) - 1) if t[i] != t[i + 1])
        improved_tour, cost, stats = MultiLayerLS.improve(
            tour, cost_fn, rng, intensity="light"
        )
        assert isinstance(improved_tour, list)
        assert isinstance(stats, dict)
        print(f"[OK] MultiLayerLS  (cost {cost}, stats keys: {list(stats.keys())})")
    except Exception as exc:
        errors.append(f"MultiLayerLS: {exc}")
        print(f"[FAIL] MultiLayerLS: {exc}")

    # -- 3. PenaltyManager --
    try:
        pm = PenaltyManager()
        pc = pm.compute_penalized_cost(100.0, 5.0, 2.0)
        assert pc == 100.0 + 10.0 * 5.0 + 5.0 * 2.0
        pm.update(iteration=100, current_cost=90.0, is_feasible=True)
        state = pm.get_state()
        assert state.phase == "relax"
        print(f"[OK] PenaltyManager  (phase={state.phase}, alpha_tw={state.alpha_tw:.2f})")
    except Exception as exc:
        errors.append(f"PenaltyManager: {exc}")
        print(f"[FAIL] PenaltyManager: {exc}")

    # -- 4. AcceptanceCriteria --
    try:
        rng = _random.Random(42)
        sa = SimulatedAnnealing()
        r1 = sa.decide(100.0, 95.0, 95.0, 10, rng)
        assert r1.accepted and r1.improved
        lahc = LateAcceptanceHC(history_length=10, warmup=2)
        r2 = lahc.decide(100.0, 105.0, 95.0, 5, rng)
        assert isinstance(r2, AcceptResult)
        rtr = RecordToRecordTravel()
        r3 = rtr.decide(100.0, 101.0, 95.0, 10, rng)
        assert isinstance(r3, AcceptResult)
        print("[OK] AcceptanceCriteria (SA + LAHC + RTR)")
    except Exception as exc:
        errors.append(f"AcceptanceCriteria: {exc}")
        print(f"[FAIL] AcceptanceCriteria: {exc}")

    # -- 5. DestroyOperators --
    try:
        rng = _random.Random(42)
        tour = [f"c{i}" for i in range(10)]
        dm = {
            w: {f"c{j}": float(abs(i - j)) for j in range(10)}
            for i, w in enumerate(tour)
        }
        rr = RandomRemoval()
        removed, remaining = rr.destroy(tour, 3, rng)
        assert len(removed) == 3 and len(remaining) == 7
        wr = WorstRemoval()
        removed2, remaining2 = wr.destroy(tour, 3, rng, distance_matrix=dm)
        assert len(removed2) == 3
        sr = ShawRemoval()
        removed3, remaining3 = sr.destroy(tour, 3, rng, distance_matrix=dm)
        assert len(removed3) == 3
        relr = RelatedRemoval()
        removed4, remaining4 = relr.destroy(tour, 3, rng, distance_matrix=dm)
        assert len(removed4) == 3
        print("[OK] DestroyOperators (Random + Worst + Shaw + Related)")
    except Exception as exc:
        errors.append(f"DestroyOperators: {exc}")
        print(f"[FAIL] DestroyOperators: {exc}")

    # -- 6. RepairOperators --
    try:
        rng = _random.Random(42)
        partial = [f"c{i}" for i in range(7)]
        removed = ["c3", "c5"]
        dm = {
            f"c{i}": {f"c{j}": float(abs(i - j)) for j in range(10)}
            for i in range(10)
        }
        gi = GreedyInsertion()
        repaired1 = gi.repair(partial, removed, distance_matrix=dm)
        assert len(repaired1) == 9
        r2i = Regret2Insertion()
        repaired2 = r2i.repair(partial, removed, distance_matrix=dm)
        assert len(repaired2) == 9
        r3i = Regret3Insertion()
        repaired3 = r3i.repair(partial, removed, distance_matrix=dm)
        assert len(repaired3) == 9
        print("[OK] RepairOperators (Greedy + Regret-2 + Regret-3)")
    except Exception as exc:
        errors.append(f"RepairOperators: {exc}")
        print(f"[FAIL] RepairOperators: {exc}")

    # -- 7. DiversityController --
    try:
        dc = DiversityController()
        pop = [
            [f"c{i}" for i in range(10)],
            [f"c{i}" for i in reversed(range(10))],
        ]
        entropy = dc.compute_population_entropy(pop)
        avg_dist = dc.compute_average_distance(pop)
        state = dc.get_state(pop)
        assert state.entropy >= 0.0
        assert state.avg_distance > 0.0
        print(f"[OK] DiversityController  (entropy={entropy:.3f}, avg_dist={avg_dist:.1f})")
    except Exception as exc:
        errors.append(f"DiversityController: {exc}")
        print(f"[FAIL] DiversityController: {exc}")

    # -- Summary --
    print("=" * 55)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL 7 MODULES PASSED SMOKE TESTS")
