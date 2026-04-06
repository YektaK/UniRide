"""
Centralized Local Search Module for TSP/CVRP
Implements multiple local search algorithms for route optimization.

This module eliminates code duplication by providing a single source of truth
for local search implementations used by various meta-heuristic algorithms.

Algorithms implemented:
- 2-opt: Classic edge exchange (Croes, 1958)
- 3-opt: Three-edge exchange (Lin, 1965)
- Or-opt: Node relocation (Or, 1976)
- Hybrid: Combination of multiple methods

Reference:
- Croes, G. (1958). A method for solving traveling salesman problems.
- Lin, S. (1965). Computer solutions of the traveling salesman problem.
- Or, I. (1976). Traveling salesman-type combinatorial problems.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Callable
from enum import Enum
import random
import time


class LocalSearchType(str, Enum):
    """Available local search types"""
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    HYBRID = "hybrid"


class BaseLocalSearch(ABC):
    """Abstract base class for local search algorithms"""

    @abstractmethod
    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """
        Improve a route using local search.

        Args:
            route: Current route as list of location codes
            duration_func: Function that calculates route duration

        Returns:
            Tuple of (improved_route, improved_duration)
        """
        pass


class TwoOptLocalSearch(BaseLocalSearch):
    """
    2-opt Local Search Algorithm.

    2-opt works by removing two edges from the tour and reconnecting
    the two paths created. This is repeated until no improvement can
    be made. Time complexity is O(n²) per iteration.

    Best for: Medium-sized problems, quick improvements
    Reference: Croes, G. (1958). A method for solving traveling salesman problems.
    """

    def __init__(self, max_iterations: int = 1000, first_improvement: bool = False):
        """
        Initialize 2-opt local search.

        Args:
            max_iterations: Maximum number of improvement iterations
            first_improvement: If True, accept first improvement found (faster but lower quality)
        """
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement

    def _two_opt_swap(self, route: List[str], i: int, j: int) -> List[str]:
        """
        Perform 2-opt swap.

        Reverse the segment between indices i and j.
        Original: ... A -> B -> ... -> C -> D ...
        After swap: ... A -> C -> ... -> B -> D ...
        """
        new_route = route[:i]
        new_route.extend(reversed(route[i:j + 1]))
        new_route.extend(route[j + 1:])
        return new_route

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using 2-opt"""
        if len(route) < 3:
            return route, duration_func(route)

        best_route = route.copy()
        best_duration = duration_func(best_route)
        improved = True
        iterations = 0

        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            for i in range(len(best_route) - 1):
                for j in range(i + 2, len(best_route)):
                    # Skip adjacent edges (no improvement possible)
                    if j == i + 1:
                        continue

                    # Create new route with 2-opt swap
                    new_route = self._two_opt_swap(best_route, i, j)
                    new_duration = duration_func(new_route)

                    if new_duration < best_duration:
                        best_route = new_route
                        best_duration = new_duration
                        improved = True

                        if self.first_improvement:
                            break

                if improved and self.first_improvement:
                    break

        return best_route, best_duration


class ThreeOptLocalSearch(BaseLocalSearch):
    """
    3-opt Local Search Algorithm.

    3-opt extends 2-opt by considering three edges instead of two.
    It creates 7 different reconnection patterns and picks the best.
    Time complexity is O(n³) per iteration.

    Best for: High-quality solutions, when runtime is not critical
    Reference: Lin, S. (1965). Computer solutions of the traveling salesman problem.
    """

    def __init__(self, max_iterations: int = 500, first_improvement: bool = False):
        """
        Initialize 3-opt local search.

        Args:
            max_iterations: Maximum number of improvement iterations
            first_improvement: If True, accept first improvement found
        """
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement

    def _three_opt_cases(
        self,
        route: List[str],
        i: int,
        j: int,
        k: int
    ) -> List[List[str]]:
        """
        Generate all 7 3-opt reconnection patterns.

        Given breakpoints i, j, k, we have segments:
        A = route[0:i+1], B = route[i+1:j+1], C = route[j+1:k+1], D = route[k+1:]

        The 7 reconnection patterns are:
        1. A-B'-C'-D (2-opt between i and j)
        2. A-B'-C-D' (2-opt between i and j, reverse end)
        3. A-B-C'-D' (2-opt between j and k)
        4. A-B-C-D (original)
        5. A-B'-C-D (reverse B)
        6. A-B-C'-D (reverse C)
        7. A-B'-C'-D (reverse B and C)
        """
        # Segments
        A = route[:i + 1]
        B = route[i + 1:j + 1]
        C = route[j + 1:k + 1]
        D = route[k + 1:]

        # Reversed segments
        B_rev = list(reversed(B))
        C_rev = list(reversed(C))

        cases = [
            A + B_rev + C_rev + D,      # Case 1
            A + B_rev + C + D,          # Case 5
            A + B + C_rev + D,          # Case 6
            A + B_rev + C_rev + D,      # Case 7
            A + B + C_rev + D,          # Case 3 variant
            A + B_rev + C + D,          # Case 2 variant
            A + B + C + D,              # Original
        ]

        return cases

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using 3-opt"""
        if len(route) < 4:
            # Fall back to 2-opt for small routes
            two_opt = TwoOptLocalSearch(self.max_iterations)
            return two_opt.improve(route, duration_func)

        best_route = route.copy()
        best_duration = duration_func(best_route)
        improved = True
        iterations = 0

        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            for i in range(len(best_route) - 3):
                for j in range(i + 2, len(best_route) - 1):
                    for k in range(j + 2, len(best_route)):
                        # Try all reconnection patterns
                        candidates = self._three_opt_cases(best_route, i, j, k)

                        for candidate in candidates:
                            candidate_duration = duration_func(candidate)

                            if candidate_duration < best_duration:
                                best_route = candidate
                                best_duration = candidate_duration
                                improved = True

                                if self.first_improvement:
                                    break

                        if improved and self.first_improvement:
                            break
                    if improved and self.first_improvement:
                        break

        return best_route, best_duration


class OrOptLocalSearch(BaseLocalSearch):
    """
    Or-opt Local Search Algorithm.

    Or-opt relocates sequences of 1, 2, or 3 consecutive nodes to
    different positions in the tour. This is effective for problems
    where clusters of customers need to be moved together.

    Best for: Problems with clustered customers
    Reference: Or, I. (1976). Traveling salesman-type combinatorial problems.
    """

    def __init__(self, max_iterations: int = 500, max_segment_size: int = 3):
        """
        Initialize Or-opt local search.

        Args:
            max_iterations: Maximum number of improvement iterations
            max_segment_size: Maximum number of consecutive nodes to relocate (1-3)
        """
        self.max_iterations = max_iterations
        self.max_segment_size = min(max_segment_size, 3)

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using Or-opt"""
        if len(route) < 4:
            return route, duration_func(route)

        best_route = route.copy()
        best_duration = duration_func(best_route)
        improved = True
        iterations = 0

        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            # Try relocating segments of different sizes
            for segment_size in range(1, self.max_segment_size + 1):
                for i in range(len(best_route) - segment_size + 1):
                    # Extract segment
                    segment = best_route[i:i + segment_size]
                    remaining = best_route[:i] + best_route[i + segment_size:]

                    # Try inserting at each position
                    for j in range(len(remaining) + 1):
                        if j == i:
                            continue  # Skip original position

                        new_route = remaining[:j] + segment + remaining[j:]
                        new_duration = duration_func(new_route)

                        if new_duration < best_duration:
                            best_route = new_route
                            best_duration = new_duration
                            improved = True
                            break

                    if improved:
                        break
                if improved:
                    break

        return best_route, best_duration


class HybridLocalSearch(BaseLocalSearch):
    """
    Hybrid Local Search combining multiple methods.

    Applies multiple local search methods in sequence or iteratively
    to achieve better solutions. The combination of methods can escape
    local optima that a single method might get stuck in.

    Best for: When solution quality is critical
    """

    def __init__(
        self,
        methods: Optional[List[LocalSearchType]] = None,
        max_iterations: int = 100,
        use_random_order: bool = False
    ):
        """
        Initialize hybrid local search.

        Args:
            methods: List of local search methods to use (default: all)
            max_iterations: Maximum total iterations across all methods
            use_random_order: If True, randomize order of methods
        """
        self.methods = methods or [
            LocalSearchType.TWO_OPT,
            LocalSearchType.OR_OPT,
            LocalSearchType.THREE_OPT
        ]
        self.max_iterations = max_iterations
        self.use_random_order = use_random_order
        self.rng = random.Random()

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using hybrid approach"""
        if len(route) < 3:
            return route, duration_func(route)

        current_route = route.copy()
        current_duration = duration_func(current_route)

        methods = list(self.methods)
        if self.use_random_order:
            self.rng.shuffle(methods)

        for iteration in range(self.max_iterations):
            improved_this_round = False

            for method in methods:
                if method == LocalSearchType.TWO_OPT:
                    ls = TwoOptLocalSearch(max_iterations=50)
                elif method == LocalSearchType.THREE_OPT:
                    ls = ThreeOptLocalSearch(max_iterations=25)
                elif method == LocalSearchType.OR_OPT:
                    ls = OrOptLocalSearch(max_iterations=50)
                else:
                    continue

                new_route, new_duration = ls.improve(current_route, duration_func)

                if new_duration < current_duration:
                    current_route = new_route
                    current_duration = new_duration
                    improved_this_round = True

            if not improved_this_round:
                break

        return current_route, current_duration


def get_local_search(
    local_search_type: LocalSearchType = LocalSearchType.TWO_OPT,
    **kwargs
) -> BaseLocalSearch:
    """
    Factory function to get local search instance.

    Args:
        local_search_type: Type of local search algorithm
        **kwargs: Additional parameters for the local search

    Returns:
        Instance of the requested local search algorithm
    """
    ls_map = {
        LocalSearchType.NONE: None,
        LocalSearchType.TWO_OPT: TwoOptLocalSearch,
        LocalSearchType.THREE_OPT: ThreeOptLocalSearch,
        LocalSearchType.OR_OPT: OrOptLocalSearch,
        LocalSearchType.HYBRID: HybridLocalSearch,
    }

    ls_class = ls_map.get(local_search_type)

    if ls_class is None:
        return None

    return ls_class(**kwargs)


def apply_local_search(
    route: List[str],
    duration_func: Callable[[List[str]], float],
    local_search_type: LocalSearchType = LocalSearchType.TWO_OPT,
    **kwargs
) -> Tuple[List[str], float]:
    """
    Convenience function to apply local search to a route.

    Args:
        route: Route to improve
        duration_func: Function to calculate route duration
        local_search_type: Type of local search to apply
        **kwargs: Additional parameters

    Returns:
        Tuple of (improved_route, improved_duration)
    """
    if local_search_type == LocalSearchType.NONE:
        return route, duration_func(route)

    ls = get_local_search(local_search_type, **kwargs)

    if ls is None:
        return route, duration_func(route)

    return ls.improve(route, duration_func)


# Export all classes and functions
__all__ = [
    'LocalSearchType',
    'BaseLocalSearch',
    'TwoOptLocalSearch',
    'ThreeOptLocalSearch',
    'OrOptLocalSearch',
    'HybridLocalSearch',
    'get_local_search',
    'apply_local_search',
]
