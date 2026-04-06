"""
Local Search Algorithms for TSP/CVRP Optimization

Implements:
- 2-opt: Classic edge exchange heuristic (Croes, 1958)
- 3-opt: Extended edge exchange (Lin, 1965)
- Or-opt: Node relocation heuristic (Or, 1976)

These are used as intensification/local search operators within
meta-heuristic algorithms to improve solution quality.

References:
- Croes, G. A. (1958). A method for solving traveling-salesman problems.
  Operations Research, 6(6), 791-812.
- Lin, S. (1965). Computer solutions of the traveling salesman problem.
  Bell System Technical Journal, 44(10), 2245-2269.
- Or, I. (1976). Traveling salesman-type combinatorial problems and their
  relation to the logistics of regional blood banking. PhD thesis.
"""

import random
from typing import List, Dict, Tuple, Callable, Optional
from dataclasses import dataclass
from enum import Enum


class LocalSearchType(Enum):
    """Available local search types"""
    TWO_OPT = "2opt"
    THREE_OPT = "3opt"
    OR_OPT = "or_opt"
    HYBRID = "hybrid"


@dataclass
class LocalSearchConfig:
    """Configuration for local search algorithms"""
    max_iterations: int = 20
    first_improvement: bool = False  # False = best improvement
    use_3opt: bool = False
    use_or_opt: bool = False
    time_limit_seconds: float = 5.0


class TwoOpt:
    """
    2-opt Local Search for TSP.
    
    The 2-opt algorithm iteratively removes two edges from the tour
    and reconnects the resulting two paths in the other possible way.
    If this improves the tour, the change is accepted.
    
    Time Complexity: O(n²) per iteration
    Space Complexity: O(n)
    
    Best for: Final refinement, small to medium instances
    """
    
    @staticmethod
    def improve(
        route: List[str],
        cost_function: Callable[[List[str]], float],
        max_iterations: int = 20,
        first_improvement: bool = False
    ) -> Tuple[List[str], float]:
        """
        Improve a route using 2-opt local search.
        
        Args:
            route: Ordered list of location codes
            cost_function: Function that calculates total route cost
            max_iterations: Maximum number of improvement iterations
            first_improvement: If True, accept first improvement found (faster)
                              If False, find best improvement in each iteration
        Returns:
            Tuple of (improved_route, best_cost)
        """
        if len(route) < 3:
            return route.copy(), cost_function(route)
        
        best_route = route.copy()
        best_cost = cost_function(best_route)
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            n = len(best_route)
            
            # Try all possible 2-opt moves
            for i in range(n - 1):
                # Early termination if we found improvement in first-improvement mode
                if improved and first_improvement:
                    break
                    
                for j in range(i + 2, n):
                    # Skip adjacent edges (no real 2-opt move)
                    if i == 0 and j == n - 1:
                        continue
                    
                    # Create new route by reversing segment [i+1, j]
                    new_route = TwoOpt._two_opt_swap(best_route, i, j)
                    new_cost = cost_function(new_route)
                    
                    if new_cost < best_cost:
                        best_route = new_route
                        best_cost = new_cost
                        improved = True
                        
                        if first_improvement:
                            break
            
            # If best-improvement mode, we need to restart after each improvement
            # In first-improvement mode, we continue from where we are
        
        return best_route, best_cost
    
    @staticmethod
    def _two_opt_swap(route: List[str], i: int, j: int) -> List[str]:
        """
        Perform 2-opt swap: reverse segment between indices i and j.
        
        Before: ... A -> B -> ... -> C -> D ...
        After:  ... A -> C -> ... -> B -> D ...
        
        Where: A = route[i], B = route[i+1], C = route[j], D = route[j+1]
        """
        new_route = route[:i + 1]  # Keep first part
        new_route.extend(route[i + 1:j + 1][::-1])  # Reverse middle
        new_route.extend(route[j + 1:])  # Keep last part
        return new_route
    
    @staticmethod
    def get_delta_cost(
        route: List[str],
        i: int,
        j: int,
        cost_matrix: Dict[str, Dict[str, float]],
        depot: str
    ) -> float:
        """
        Calculate cost difference for 2-opt move without full recomputation.
        
        This is O(1) instead of O(n) - much faster for large routes.
        
        Args:
            route: Current route
            i, j: Indices for 2-opt move
            cost_matrix: Pre-computed cost matrix
            depot: Depot location for closed tour
        
        Returns:
            Delta cost (negative means improvement)
        """
        n = len(route)
        if i < 0 or j >= n or i >= j:
            return 0.0
        
        # Handle wraparound for closed tour
        # Edges being removed: (i, i+1) and (j, j+1)
        # Edges being added: (i, j) and (i+1, j+1)
        
        # Get locations
        if i >= 0:
            loc_i = route[i]
        else:
            loc_i = depot
        
        loc_i1 = route[(i + 1) % n] if i + 1 < n else depot
        loc_j = route[j]
        loc_j1 = route[(j + 1) % n] if j + 1 < n else depot
        
        # Handle depot connections
        if i < 0:
            loc_i = depot
        if j + 1 >= n:
            loc_j1 = depot
        
        # Calculate edge costs
        try:
            old_cost = (
                cost_matrix.get(loc_i, {}).get(loc_i1, 0) +
                cost_matrix.get(loc_j, {}).get(loc_j1, 0)
            )
            new_cost = (
                cost_matrix.get(loc_i, {}).get(loc_j, 0) +
                cost_matrix.get(loc_i1, {}).get(loc_j1, 0)
            )
            return new_cost - old_cost
        except (KeyError, TypeError):
            return 0.0


class ThreeOpt:
    """
    3-opt Local Search for TSP.
    
    Extends 2-opt by considering removing three edges.
    More powerful but slower than 2-opt.
    
    Time Complexity: O(n³) per iteration
    Space Complexity: O(n)
    
    There are 7 ways to reconnect after removing 3 edges
    (one is the original, 2 are equivalent to 2-opt moves).
    
    Best for: Final refinement, when 2-opt reaches local optimum
    """
    
    @staticmethod
    def improve(
        route: List[str],
        cost_function: Callable[[List[str]], float],
        max_iterations: int = 10,
        first_improvement: bool = False
    ) -> Tuple[List[str], float]:
        """
        Improve a route using 3-opt local search.
        """
        if len(route) < 4:
            return route.copy(), cost_function(route)
        
        best_route = route.copy()
        best_cost = cost_function(best_route)
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            n = len(best_route)
            
            for i in range(n - 3):
                if improved and first_improvement:
                    break
                for j in range(i + 2, n - 2):
                    if improved and first_improvement:
                        break
                    for k in range(j + 2, n):
                        # Try all 7 reconnection patterns
                        for pattern in range(1, 8):
                            new_route = ThreeOpt._three_opt_swap(
                                best_route, i, j, k, pattern
                            )
                            new_cost = cost_function(new_route)
                            
                            if new_cost < best_cost:
                                best_route = new_route
                                best_cost = new_cost
                                improved = True
                                
                                if first_improvement:
                                    break
                                
                                # Pattern 0 is original, patterns 1-7 are moves
                                # Patterns 5 and 6 are equivalent to 2-opt
        
        return best_route, best_cost
    
    @staticmethod
    def _three_opt_swap(
        route: List[str],
        i: int,
        j: int,
        k: int,
        pattern: int
    ) -> List[str]:
        """
        Perform 3-opt swap with given reconnection pattern.
        
        Segments: A = [0:i+1], B = [i+1:j+1], C = [j+1:k+1], D = [k+1:]
        
        Patterns:
        0: A-B-C-D (original, no change)
        1: A-B'-C-D (2-opt on B)
        2: A-B-C'-D (2-opt on C)
        3: A-B'-C'-D (2-opt on both)
        4: A-C-B-D (reorder segments)
        5: A-C-B'-D
        6: A-C'-B-D
        7: A-C'-B'-D
        """
        A = route[:i + 1]
        B = route[i + 1:j + 1]
        C = route[j + 1:k + 1]
        D = route[k + 1:]
        
        if pattern == 0:
            return A + B + C + D
        elif pattern == 1:
            return A + B[::-1] + C + D
        elif pattern == 2:
            return A + B + C[::-1] + D
        elif pattern == 3:
            return A + B[::-1] + C[::-1] + D
        elif pattern == 4:
            return A + C + B + D
        elif pattern == 5:
            return A + C + B[::-1] + D
        elif pattern == 6:
            return A + C[::-1] + B + D
        elif pattern == 7:
            return A + C[::-1] + B[::-1] + D
        else:
            return route.copy()


class OrOpt:
    """
    Or-opt Local Search for TSP.
    
    Relocates sequences of 1, 2, or 3 consecutive nodes.
    Simpler than 2-opt/3-opt but can find improvements they miss.
    
    Time Complexity: O(n²) per iteration
    Space Complexity: O(n)
    
    Best for: Route refinement, combined with 2-opt
    """
    
    @staticmethod
    def improve(
        route: List[str],
        cost_function: Callable[[List[str]], float],
        max_iterations: int = 10,
        sequence_lengths: List[int] = None,
        first_improvement: bool = False
    ) -> Tuple[List[str], float]:
        """
        Improve a route using Or-opt (node relocation).
        """
        if len(route) < 4:
            return route.copy(), cost_function(route)
        
        if sequence_lengths is None:
            sequence_lengths = [1, 2, 3]
        
        best_route = route.copy()
        best_cost = cost_function(best_route)
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            n = len(best_route)
            
            for seq_len in sequence_lengths:
                if improved and first_improvement:
                    break
                    
                for i in range(n - seq_len + 1):
                    if improved and first_improvement:
                        break
                    
                    # Extract sequence
                    seq = best_route[i:i + seq_len]
                    remaining = best_route[:i] + best_route[i + seq_len:]
                    
                    # Try inserting at each position
                    for j in range(len(remaining) + 1):
                        if j == i:
                            continue  # Skip original position
                        
                        new_route = remaining[:j] + seq + remaining[j:]
                        new_cost = cost_function(new_route)
                        
                        if new_cost < best_cost:
                            best_route = new_route
                            best_cost = new_cost
                            improved = True
                            
                            if first_improvement:
                                break
        
        return best_route, best_cost


class HybridLocalSearch:
    """
    Combines multiple local search operators for better results.
    
    Strategy: Apply 2-opt first (fast), then Or-opt, then optionally 3-opt.
    This provides good balance between speed and solution quality.
    """
    
    @staticmethod
    def improve(
        route: List[str],
        cost_function: Callable[[List[str]], float],
        config: Optional[LocalSearchConfig] = None
    ) -> Tuple[List[str], float]:
        """
        Apply hybrid local search strategy.
        """
        if config is None:
            config = LocalSearchConfig()
        
        current_route = route.copy()
        current_cost = cost_function(current_route)
        
        # Phase 1: 2-opt (most effective for TSP)
        current_route, current_cost = TwoOpt.improve(
            current_route,
            cost_function,
            max_iterations=config.max_iterations,
            first_improvement=config.first_improvement
        )
        
        # Phase 2: Or-opt (finds improvements 2-opt misses)
        if config.use_or_opt:
            current_route, current_cost = OrOpt.improve(
                current_route,
                cost_function,
                max_iterations=config.max_iterations // 2,
                first_improvement=config.first_improvement
            )
        
        # Phase 3: 3-opt (optional, for final refinement)
        if config.use_3opt and len(current_route) <= 50:  # Limit for performance
            current_route, current_cost = ThreeOpt.improve(
                current_route,
                cost_function,
                max_iterations=config.max_iterations // 2,
                first_improvement=config.first_improvement
            )
        
        # Phase 4: Final 2-opt pass
        current_route, current_cost = TwoOpt.improve(
            current_route,
            cost_function,
            max_iterations=5,
            first_improvement=False
        )
        
        return current_route, current_cost


def create_cost_function(
    depot: str,
    time_matrix: Dict[str, Dict[str, float]],
    coordinates: Dict[str, Dict[str, float]]
) -> Callable[[List[str]], float]:
    """
    Create a cost function for local search.
    
    This function creates a closure that captures the depot,
    time matrix, and coordinates, returning a function that
    calculates total route duration for a given permutation.
    """
    from utils.data_loader import haversine_distance, estimate_travel_time
    
    def get_duration(from_loc: str, to_loc: str) -> float:
        """Get duration between two locations"""
        if from_loc in time_matrix and to_loc in time_matrix.get(from_loc, {}):
            return time_matrix[from_loc][to_loc]
        
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)
        
        return 15.0  # Default fallback
    
    def cost_function(route: List[str]) -> float:
        """Calculate total route duration"""
        if not route:
            return 0.0
        
        total = get_duration(depot, route[0])
        
        for i in range(len(route) - 1):
            total += get_duration(route[i], route[i + 1])
        
        total += get_duration(route[-1], depot)
        return total
    
    return cost_function


# Convenience function for easy import
def apply_local_search(
    route: List[str],
    depot: str,
    time_matrix: Dict[str, Dict[str, float]],
    coordinates: Dict[str, Dict[str, float]],
    search_type: LocalSearchType = LocalSearchType.TWO_OPT,
    max_iterations: int = 20,
    first_improvement: bool = False
) -> Tuple[List[str], float]:
    """
    Apply local search to improve a route.
    
    This is the main entry point for local search operations.
    
    Args:
        route: Current route as ordered list of location codes
        depot: Depot location code
        time_matrix: Dictionary of travel times between locations
        coordinates: Dictionary of location coordinates
        search_type: Type of local search to apply
        max_iterations: Maximum iterations
        first_improvement: Use first-improvement strategy
    
    Returns:
        Tuple of (improved_route, best_cost)
    """
    cost_function = create_cost_function(depot, time_matrix, coordinates)
    
    if search_type == LocalSearchType.TWO_OPT:
        return TwoOpt.improve(route, cost_function, max_iterations, first_improvement)
    elif search_type == LocalSearchType.THREE_OPT:
        return ThreeOpt.improve(route, cost_function, max_iterations, first_improvement)
    elif search_type == LocalSearchType.OR_OPT:
        return OrOpt.improve(route, cost_function, max_iterations, first_improvement=first_improvement)
    elif search_type == LocalSearchType.HYBRID:
        config = LocalSearchConfig(
            max_iterations=max_iterations,
            first_improvement=first_improvement,
            use_3opt=False,
            use_or_opt=True
        )
        return HybridLocalSearch.improve(route, cost_function, config)
    else:
        return TwoOpt.improve(route, cost_function, max_iterations, first_improvement)
