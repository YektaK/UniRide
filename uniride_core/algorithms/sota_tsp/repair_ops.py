"""
ALNS Repair Operators — TSP variant.

Adapted from optimizer_api/strategies/sota_common/repair_operators.py.
Works on List[int] tours with List[List[float]] distance matrix.
"""

import random
from typing import List, Optional


class GreedyInsertion:
    def repair(self, partial: List[int], removed: List[int],
               dm: Optional[List[List[float]]] = None) -> List[int]:
        if dm is None:
            return partial + removed
        result = list(partial)
        for node in removed:
            best_pos = 0
            best_cost = float("inf")
            for pos in range(len(result) + 1):
                prev_node = result[pos - 1] if pos > 0 else result[-1] if result else node
                next_node = result[pos] if pos < len(result) else result[0] if result else node
                if not result:
                    cost = 0.0
                else:
                    cost = dm[prev_node][node] + dm[node][next_node]
                    if pos > 0 and pos < len(result):
                        cost -= dm[prev_node][next_node]
                if cost < best_cost:
                    best_cost = cost
                    best_pos = pos
            result.insert(best_pos, node)
        return result


class RegretKInsertion:
    def __init__(self, k: int):
        self.k = k

    def repair(self, partial: List[int], removed: List[int],
               dm: Optional[List[List[float]]] = None) -> List[int]:
        if dm is None:
            return partial + removed
        result = list(partial)
        uninserted = list(removed)
        while uninserted:
            best_node = None
            best_regret = -float("inf")
            for node in uninserted:
                costs = []
                for pos in range(len(result) + 1):
                    prev_node = result[pos - 1] if pos > 0 else result[-1] if result else node
                    next_node = result[pos] if pos < len(result) else result[0] if result else node
                    if not result:
                        costs.append(0.0)
                    else:
                        c = dm[prev_node][node] + dm[node][next_node]
                        if pos > 0 and pos < len(result):
                            c -= dm[prev_node][next_node]
                        costs.append(c)
                costs.sort()
                
                if len(costs) >= self.k:
                    regret = costs[self.k - 1] - costs[0]
                elif len(costs) > 1:
                    regret = costs[-1] - costs[0]
                else:
                    regret = costs[0]
                    
                if regret > best_regret:
                    best_regret = regret
                    best_node = node
                    
            if best_node is None:
                break
            best_node_idx = uninserted.index(best_node)
            uninserted.pop(best_node_idx)
            
            best_pos = 0
            best_cost = float("inf")
            for pos in range(len(result) + 1):
                prev_node = result[pos - 1] if pos > 0 else result[-1] if result else best_node
                next_node = result[pos] if pos < len(result) else result[0] if result else best_node
                if not result:
                    cost = 0.0
                else:
                    cost = dm[prev_node][best_node] + dm[best_node][next_node]
                    if pos > 0 and pos < len(result):
                        cost -= dm[prev_node][next_node]
                if cost < best_cost:
                    best_cost = cost
                    best_pos = pos
            result.insert(best_pos, best_node)
        return result


def _regret_k_insertion(k: int) -> RegretKInsertion:
    return RegretKInsertion(k=k)


class Regret2Insertion(RegretKInsertion):
    def __init__(self):
        super().__init__(k=2)


class Regret3Insertion(RegretKInsertion):
    def __init__(self):
        super().__init__(k=3)
