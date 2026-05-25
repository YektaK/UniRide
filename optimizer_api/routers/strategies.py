from typing import List
from fastapi import APIRouter

from models.schemas import StrategyInfo
from strategies import get_strategy_info

router = APIRouter(prefix="/api/v1", tags=["Strategies"])

def _get_complexity(name: str) -> str:
    complexities = {
        "genetic_algorithm": "O(generations × population × n²)",
        "ga_split": "O(generations × population × n²)",
        "pso": "O(iterations × swarm × n²)",
        "pso_split": "O(iterations × swarm × n²)",
        "gwo": "O(iterations × pack × n²)",
        "gwo_split": "O(iterations × pack × n²)",
        "hho": "O(iterations × hawks × n²)",
        "hho_split": "O(iterations × hawks × n²)",
        "two_opt": "O(n²) per improvement",
        "greedy": "O(n²)",
        "permutation_tsp": "O(n!)",
        "ortools_cvrp": "O(n³) worst case"
    }
    return complexities.get(name, "Unknown")

@router.get("/strategies", response_model=List[StrategyInfo])
def list_strategies() -> List[StrategyInfo]:
    strategies = get_strategy_info()
    recommended = ["ga_split", "pso_split", "genetic_algorithm", "pso", "gwo", "hho"]

    return [
        StrategyInfo(
            name=s["name"],
            display_name=s["display_name"],
            description=s["description"],
            complexity=_get_complexity(s["name"]),
            recommended=s["name"] in recommended,
            available=s.get("available", True),
        )
        for s in strategies
    ]
