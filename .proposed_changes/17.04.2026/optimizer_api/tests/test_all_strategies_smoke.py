import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer_api.strategies import STRATEGY_REGISTRY, get_strategy
from optimizer_api.models import OptimizationRequest

def test_smoke_all_strategies():
    """Run a small dummy request against EVERY available strategy to ensure no syntax/runtime crashes."""
    
    strategies = list(STRATEGY_REGISTRY.keys())
    print(f"Found {len(strategies)} strategies: {strategies}")
    
    # Generic dummy payload
    payload = OptimizationRequest(
        depot="A",
        locations=["B", "C", "D"],
        distance_matrix={
            "A": {"B": 10, "C": 15, "D": 20, "A": 0},
            "B": {"A": 10, "C": 5, "D": 10, "B": 0},
            "C": {"A": 15, "B": 5, "D": 5, "C": 0},
            "D": {"A": 20, "B": 10, "C": 5, "D": 0}
        },
        demands={"B": (1, 0), "C": (0, 1), "D": (1, 1)},
        vehicles=[
            {"id": "V1", "capacity_sw": 4, "capacity_so": 5},
            {"id": "V2", "capacity_sw": 4, "capacity_so": 5}
        ],
        target_time=8 * 60,
        direction="pickup"
    )


    
    failures = []
    
    for strategy in strategies:
        print(f"Testing {strategy}...", end=" ")
        try:
            # Overwrite the strategy in the payload
            payload.strategy = strategy
            # Run
            alg = get_strategy(strategy)
            result = alg.optimize(payload)
            
            # Since result is a dataclass AlgorithmResult, we just check if there's no exception.
            print("SUCCESS")
        except Exception as e:
            failures.append((strategy, str(e)))
            print(f"FAIL: {e}")
            
    if failures:
        print("\nFailures encountered:")
        for strat, err in failures:
            print(f" - {strat}: {err}")
        assert False, f"{len(failures)} strategies failed."
    else:
        print("\nAll strategies passed the smoke test!")

if __name__ == '__main__':
    test_smoke_all_strategies()
