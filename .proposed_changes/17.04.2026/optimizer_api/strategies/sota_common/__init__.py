"""
SOTA Common Infrastructure (FAZ 0)

Shared modules used by all improved algorithms (E²BSO, R²DMA, P-AOEA).

Modules:
    multi_start_initializer  — Multi-start population generator (DNA #6)
    multi_layer_ls           — Multi-layer local search engine (DNA #3)
    penalty_manager          — Adaptive penalty manager (DNA #9)
    acceptance_criteria      — SA, LAHC, RTR acceptance (DNA #7)
    destroy_operators        — ALNS destroy operators (DNA #1 + #2)
    repair_operators         — ALNS repair operators (DNA #1 + #2)
    diversity_controller     — Population diversity management (DNA #8)
"""

import random as _random

from .multi_start_initializer import MultiStartInitializer
from .multi_layer_ls import MultiLayerLS
from .penalty_manager import PenaltyManager, PenaltyState
from .acceptance_criteria import (
    AcceptResult,
    AcceptanceCriterion,
    LateAcceptanceHC,
    RecordToRecordTravel,
    SimulatedAnnealing,
)
from .destroy_operators import (
    DestroyOperator,
    RandomRemoval,
    WorstRemoval,
    ShawRemoval,
    RelatedRemoval,
)
from .repair_operators import (
    RepairOperator,
    GreedyInsertion,
    Regret2Insertion,
    Regret3Insertion,
)
from .diversity_controller import DiversityController, DiversityState
from .e2bso import E2BSO, E2BSOConfig, E2BSOResult
from .r2dma import R2DMA, R2DMAConfig, R2DMAResult
from .paoea import PAOEA, PAOEAConfig, PAOEAResult

SOTA_INFRA_VERSION = "3.0.0"

__all__ = [
    # Version
    "SOTA_INFRA_VERSION",
    # Initializer
    "MultiStartInitializer",
    # Local Search
    "MultiLayerLS",
    # Penalty
    "PenaltyManager",
    "PenaltyState",
    # Acceptance
    "AcceptResult",
    "AcceptanceCriterion",
    "SimulatedAnnealing",
    "LateAcceptanceHC",
    "RecordToRecordTravel",
    # Destroy
    "DestroyOperator",
    "RandomRemoval",
    "WorstRemoval",
    "ShawRemoval",
    "RelatedRemoval",
    # Repair
    "RepairOperator",
    "GreedyInsertion",
    "Regret2Insertion",
    "Regret3Insertion",
    # Diversity
    "DiversityController",
    "DiversityState",
    # E²BSO (FAZ 1)
    "E2BSO",
    "E2BSOConfig",
    "E2BSOResult",
    # R²DMA (FAZ 2)
    "R2DMA",
    "R2DMAConfig",
    "R2DMAResult",
    # P-AOEA (FAZ 3)
    "PAOEA",
    "PAOEAConfig",
    "PAOEAResult",
]


# ================================================================== #
# Smoke test — run:  python -m strategies.sota_common
# ================================================================== #
if __name__ == "__main__":
    import sys

    print(f"SOTA Common Infrastructure v{SOTA_INFRA_VERSION}")
    print("=" * 55)

    errors: list = []

    # -- 1. MultiStartInitializer --
    try:
        rng = _random.Random(42)
        waypoints = [f"c{i}" for i in range(10)]
        dm = {w: {f"c{j}": float(abs(i - j)) for j in range(10)} for i, w in enumerate(waypoints)}
        pop = MultiStartInitializer.generate_population(
            waypoints, dm, pop_size=8, rng=rng, depot="c0"
        )
        assert len(pop) == 8, f"Expected 8, got {len(pop)}"
        assert all(isinstance(t, list) for t in pop)
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
        print(f"[OK] PenaltyManager  (phase={state.phase}, α_tw={state.alpha_tw:.2f})")
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
        dm = {w: {f"c{j}": float(abs(i - j)) for j in range(10)} for i, w in enumerate(tour)}

        rr = RandomRemoval()
        removed, remaining = rr.destroy(tour, 3, rng)
        assert len(removed) == 3 and len(remaining) == 7

        wr = WorstRemoval()
        removed2, remaining2 = wr.destroy(tour, 3, rng, distance_matrix=dm)
        assert len(removed2) == 3 and len(remaining2) == 7

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
        pop = [[f"c{i}" for i in range(10)], [f"c{i}" for i in reversed(range(10))]]
        entropy = dc.compute_population_entropy(pop)
        avg_dist = dc.compute_average_distance(pop)
        state = dc.get_state(pop)
        assert state.entropy >= 0.0
        assert state.avg_distance > 0.0
        inject = dc.should_inject_diversity(pop, threshold=0.3)
        print(f"[OK] DiversityController  (entropy={entropy:.3f}, avg_dist={avg_dist:.1f})")
    except Exception as exc:
        errors.append(f"DiversityController: {exc}")
        print(f"[FAIL] DiversityController: {exc}")

    # -- 8. R²DMA import --
    try:
        from .r2dma import R2DMA, R2DMAConfig, R2DMAResult
        assert hasattr(R2DMA, 'solve')
        assert hasattr(R2DMAConfig, 'population_size')
        assert hasattr(R2DMAResult, 'cost')
        print("[OK] R²DMA (FAZ 2)")
    except Exception as exc:
        errors.append(f"R2DMA: {exc}")
        print(f"[FAIL] R2DMA: {exc}")

    # -- 9. P-AOEA import --
    try:
        from .paoea import PAOEA, PAOEAConfig, PAOEAResult
        assert hasattr(PAOEA, 'solve')
        assert hasattr(PAOEAConfig, 'population_size')
        assert hasattr(PAOEAResult, 'cost')
        print("[OK] P-AOEA (FAZ 3)")
    except Exception as exc:
        errors.append(f"PAOEA: {exc}")
        print(f"[FAIL] PAOEA: {exc}")

    # -- Summary --
    print("=" * 55)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL 9 MODULES PASSED SMOKE TESTS (FAZ 0 + FAZ 1 + FAZ 2 + FAZ 3)")
        sys.exit(0)
