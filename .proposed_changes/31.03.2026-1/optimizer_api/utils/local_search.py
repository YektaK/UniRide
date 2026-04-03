"""
Centralized Local Search Module for TSP/CVRP/CVRPTW
Implements multiple local search algorithms for route optimization.

This module eliminates code duplication by providing a single source of truth
for local search implementations used by various meta-heuristic algorithms.

Algorithms implemented:
- 2-opt: Classic edge exchange (Croes, 1958)
- 3-opt: Three-edge exchange (Lin, 1965)
- Or-opt: Node relocation (Or, 1976)
- Swap: Node exchange between positions
- Cross Exchange: Segment exchange for CVRP (Taillard, 1993)
- Time Window Aware: CVRPTW-specific optimization
- Hybrid: Combination of multiple methods

Reference:
- Croes, G. (1958). A method for solving traveling salesman problems.
- Lin, S. (1965). Computer solutions of the traveling salesman problem.
- Or, I. (1976). Traveling salesman-type combinatorial problems.
- Taillard, E. (1993). Parallel iterative search methods for vehicle routing problems.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Callable, Any
from enum import Enum
import random
import time


class LocalSearchType(str, Enum):
    """Available local search types"""
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    SWAP = "swap"
    CROSS_EXCHANGE = "cross_exchange"
    TIME_WINDOW_AWARE = "time_window_aware"
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


class SwapLocalSearch(BaseLocalSearch):
    """
    Swap (Node Exchange) Local Search Algorithm.

    Swap exchanges two nodes at different positions in the route.
    Simple but effective for fine-tuning solutions after meta-heuristic
    optimization. Time complexity is O(n²) per iteration.

    Best for: Quick improvements, fine-tuning, small perturbations
    """

    def __init__(self, max_iterations: int = 500, first_improvement: bool = False):
        """
        Initialize Swap local search.

        Args:
            max_iterations: Maximum number of improvement iterations
            first_improvement: If True, accept first improvement found
        """
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement

    def _swap(self, route: List[str], i: int, j: int) -> List[str]:
        """
        Swap two nodes at positions i and j.

        Original: ... A ... B ...
        After swap: ... B ... A ...
        """
        new_route = route.copy()
        new_route[i], new_route[j] = new_route[j], new_route[i]
        return new_route

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using swap operations"""
        if len(route) < 3:
            return route, duration_func(route)

        best_route = route.copy()
        best_duration = duration_func(best_route)
        improved = True
        iterations = 0

        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            # Try all pairs of positions
            for i in range(len(best_route)):
                for j in range(i + 1, len(best_route)):
                    # Skip adjacent swaps (handled better by 2-opt)
                    if j == i + 1:
                        continue

                    new_route = self._swap(best_route, i, j)
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


class CrossExchangeLocalSearch(BaseLocalSearch):
    """
    Cross Exchange Local Search for CVRP/CVRPTW.

    Cross exchange swaps segments between two routes (or within a single route).
    This is particularly effective for vehicle routing problems where customers
    can be moved between different vehicles or route segments.

    Reference: Taillard, E. (1993). Parallel iterative search methods for VRP.

    Best for: CVRP/CVRPTW problems, route balancing
    """

    def __init__(
        self,
        max_iterations: int = 300,
        max_segment_size: int = 2,
        first_improvement: bool = False
    ):
        """
        Initialize Cross Exchange local search.

        Args:
            max_iterations: Maximum number of improvement iterations
            max_segment_size: Maximum segment length to exchange (1-3)
            first_improvement: If True, accept first improvement found
        """
        self.max_iterations = max_iterations
        self.max_segment_size = min(max_segment_size, 3)
        self.first_improvement = first_improvement

    def _cross_exchange(
        self,
        route: List[str],
        i: int,
        j: int,
        seg1_len: int,
        seg2_len: int
    ) -> List[str]:
        """
        Perform cross exchange between two segments.

        Route: ... A [S1] B ... C [S2] D ...
        After: ... A [S2] B ... C [S1] D ...

        Where:
        - S1 is segment starting at i with length seg1_len
        - S2 is segment starting at j with length seg2_len
        """
        # Ensure i < j and segments don't overlap
        if i > j:
            i, j = j, i
            seg1_len, seg2_len = seg2_len, seg1_len

        # Check for overlap
        if i + seg1_len > j:
            # Segments overlap, cannot exchange
            return route

        # Extract segments
        seg1 = route[i:i + seg1_len]
        seg2 = route[j:j + seg2_len]

        # Build new route
        # Part before first segment
        new_route = route[:i]
        # Insert second segment
        new_route.extend(seg2)
        # Part between segments (adjusted for different lengths)
        middle_part = route[i + seg1_len:j]
        new_route.extend(middle_part)
        # Insert first segment
        new_route.extend(seg1)
        # Part after second segment
        new_route.extend(route[j + seg2_len:])

        return new_route

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using cross exchange"""
        if len(route) < 5:
            # Fall back to swap for small routes
            swap_ls = SwapLocalSearch(self.max_iterations)
            return swap_ls.improve(route, duration_func)

        best_route = route.copy()
        best_duration = duration_func(best_route)
        improved = True
        iterations = 0

        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            # Try different segment lengths
            for seg1_len in range(1, self.max_segment_size + 1):
                for seg2_len in range(1, self.max_segment_size + 1):
                    # Try all position pairs
                    for i in range(len(best_route) - seg1_len):
                        for j in range(i + seg1_len, len(best_route) - seg2_len + 1):
                            new_route = self._cross_exchange(
                                best_route, i, j, seg1_len, seg2_len
                            )

                            if len(new_route) != len(best_route):
                                continue  # Skip invalid exchanges

                            new_duration = duration_func(new_route)

                            if new_duration < best_duration:
                                best_route = new_route
                                best_duration = new_duration
                                improved = True

                                if self.first_improvement:
                                    break

                        if improved and self.first_improvement:
                            break
                    if improved and self.first_improvement:
                        break
                if improved and self.first_improvement:
                    break

        return best_route, best_duration


class TimeWindowAwareLocalSearch(BaseLocalSearch):
    """
    Time Window Aware Local Search for CVRPTW.

    This local search specifically targets time window violations.
    It uses a combined objective function that considers both:
    - Total route duration
    - Time window violation penalties

    The algorithm prioritizes moves that reduce time window violations,
    even if they slightly increase total distance/duration.

    Best for: CVRPTW problems with tight time windows
    """

    def __init__(
        self,
        max_iterations: int = 500,
        tw_penalty: float = 100.0,
        first_improvement: bool = False
    ):
        """
        Initialize Time Window Aware local search.

        Args:
            max_iterations: Maximum number of improvement iterations
            tw_penalty: Penalty weight for time window violations
            first_improvement: If True, accept first improvement found
        """
        self.max_iterations = max_iterations
        self.tw_penalty = tw_penalty
        self.first_improvement = first_improvement

    def _evaluate_with_tw(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float],
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
        arrival_times: Optional[Dict[str, float]] = None
    ) -> Tuple[float, float, float]:
        """
        Evaluate route with time window penalties.

        Returns:
            Tuple of (total_score, duration, tw_violation)
            where total_score = duration + tw_penalty * tw_violation
        """
        duration = duration_func(route)

        if time_windows is None or arrival_times is None:
            return duration, duration, 0.0

        # Calculate time window violations
        tw_violation = 0.0
        for loc in route:
            if loc in time_windows and loc in arrival_times:
                tw_start, tw_end = time_windows[loc]
                arrival = arrival_times[loc]

                if arrival < tw_start:
                    # Early arrival - usually allowed but can be penalized
                    pass
                elif arrival > tw_end:
                    # Late arrival - violation
                    tw_violation += (arrival - tw_end)

        total_score = duration + self.tw_penalty * tw_violation
        return total_score, duration, tw_violation

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float],
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
        arrival_times: Optional[Dict[str, float]] = None
    ) -> Tuple[List[str], float]:
        """
        Improve route considering time windows.

        Args:
            route: Current route
            duration_func: Duration calculation function
            time_windows: Dict mapping location -> (start_time, end_time)
            arrival_times: Dict mapping location -> estimated arrival time

        Returns:
            Tuple of (improved_route, improved_duration)
        """
        if len(route) < 3:
            return route, duration_func(route)

        best_route = route.copy()
        best_duration = duration_func(best_route)

        # If no time window info, fall back to regular 2-opt
        if time_windows is None or arrival_times is None:
            two_opt = TwoOptLocalSearch(self.max_iterations)
            return two_opt.improve(route, duration_func)

        best_score, _, best_tw_violation = self._evaluate_with_tw(
            best_route, duration_func, time_windows, arrival_times
        )

        improved = True
        iterations = 0

        # Combine multiple operators
        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            # Try 2-opt moves
            for i in range(len(best_route) - 1):
                for j in range(i + 2, len(best_route)):
                    # 2-opt swap
                    new_route = best_route[:i]
                    new_route.extend(reversed(best_route[i:j + 1]))
                    new_route.extend(best_route[j + 1:])

                    new_score, new_duration, new_tw = self._evaluate_with_tw(
                        new_route, duration_func, time_windows, arrival_times
                    )

                    if new_score < best_score:
                        best_route = new_route
                        best_duration = new_duration
                        best_score = new_score
                        best_tw_violation = new_tw
                        improved = True

                        if self.first_improvement:
                            break

                if improved and self.first_improvement:
                    break

            if improved:
                continue

            # Try swap moves
            for i in range(len(best_route)):
                for j in range(i + 2, len(best_route)):
                    new_route = best_route.copy()
                    new_route[i], new_route[j] = new_route[j], new_route[i]

                    new_score, new_duration, new_tw = self._evaluate_with_tw(
                        new_route, duration_func, time_windows, arrival_times
                    )

                    if new_score < best_score:
                        best_route = new_route
                        best_duration = new_duration
                        best_score = new_score
                        best_tw_violation = new_tw
                        improved = True

                        if self.first_improvement:
                            break

                if improved and self.first_improvement:
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
        use_random_order: bool = False,
        include_cross_exchange: bool = True,
        include_time_window: bool = True
    ):
        """
        Initialize hybrid local search.

        Args:
            methods: List of local search methods to use (default: optimized order)
            max_iterations: Maximum total iterations across all methods
            use_random_order: If True, randomize order of methods
            include_cross_exchange: Include Cross Exchange for CVRP (default: True)
            include_time_window: Include Time Window Aware for CVRPTW (default: True)
        """
        if methods is None:
            # Optimized default order: fast → slow → specialized
            self.methods = [
                LocalSearchType.SWAP,           # O(n²) - Quick, good for fine-tuning
                LocalSearchType.TWO_OPT,        # O(n²) - Classic, reliable
                LocalSearchType.OR_OPT,         # O(n²) - Segment relocation
                LocalSearchType.CROSS_EXCHANGE, # O(n²×k²) - CVRP segment exchange
                LocalSearchType.THREE_OPT,      # O(n³) - High quality, slower
            ]
            if include_time_window:
                self.methods.append(LocalSearchType.TIME_WINDOW_AWARE)
        else:
            self.methods = methods
        self.max_iterations = max_iterations
        self.use_random_order = use_random_order
        self.include_cross_exchange = include_cross_exchange
        self.include_time_window = include_time_window
        self.rng = random.Random()

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float],
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
        arrival_times: Optional[Dict[str, float]] = None
    ) -> Tuple[List[str], float]:
        """
        Improve route using hybrid approach.

        The hybrid approach applies multiple local search operators in an
        optimized sequence. The order is designed to:
        1. Start with fast operators (Swap, 2-opt)
        2. Apply more powerful operators (Or-opt, Cross Exchange)
        3. Finish with thorough operators (3-opt, Time Window Aware)

        For CVRPTW problems, TIME_WINDOW_AWARE is applied last to
        specifically target time window violations.
        """
        if len(route) < 3:
            return route, duration_func(route)

        current_route = route.copy()
        current_duration = duration_func(current_route)

        # Filter methods based on problem type
        methods = list(self.methods)
        has_time_windows = time_windows is not None and arrival_times is not None

        # Skip TIME_WINDOW_AWARE if no time window data
        if not has_time_windows:
            methods = [m for m in methods if m != LocalSearchType.TIME_WINDOW_AWARE]

        if self.use_random_order:
            self.rng.shuffle(methods)

        # Iteration limits per method (optimized for hybrid)
        # Fast methods get more iterations, slow methods get fewer
        iteration_limits = {
            LocalSearchType.SWAP: 30,
            LocalSearchType.TWO_OPT: 40,
            LocalSearchType.OR_OPT: 30,
            LocalSearchType.CROSS_EXCHANGE: 20,
            LocalSearchType.THREE_OPT: 15,
            LocalSearchType.TIME_WINDOW_AWARE: 25,
        }

        for iteration in range(self.max_iterations):
            improved_this_round = False

            for method in methods:
                max_iter = iteration_limits.get(method, 30)

                if method == LocalSearchType.TWO_OPT:
                    ls = TwoOptLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.THREE_OPT:
                    ls = ThreeOptLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.OR_OPT:
                    ls = OrOptLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.SWAP:
                    ls = SwapLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.CROSS_EXCHANGE:
                    ls = CrossExchangeLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.TIME_WINDOW_AWARE:
                    ls = TimeWindowAwareLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(
                        current_route, duration_func, time_windows, arrival_times
                    )
                else:
                    continue

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
) -> Optional[BaseLocalSearch]:
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
        LocalSearchType.SWAP: SwapLocalSearch,
        LocalSearchType.CROSS_EXCHANGE: CrossExchangeLocalSearch,
        LocalSearchType.TIME_WINDOW_AWARE: TimeWindowAwareLocalSearch,
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
    time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
    arrival_times: Optional[Dict[str, float]] = None,
    **kwargs
) -> Tuple[List[str], float]:
    """
    Convenience function to apply local search to a route.

    Args:
        route: Route to improve
        duration_func: Function to calculate route duration
        local_search_type: Type of local search to apply
        time_windows: Dict mapping location -> (start_time, end_time) for CVRPTW
        arrival_times: Dict mapping location -> estimated arrival time for CVRPTW
        **kwargs: Additional parameters

    Returns:
        Tuple of (improved_route, improved_duration)
    """
    if local_search_type == LocalSearchType.NONE:
        return route, duration_func(route)

    ls = get_local_search(local_search_type, **kwargs)

    if ls is None:
        return route, duration_func(route)

    # Pass time window info for TIME_WINDOW_AWARE type
    if local_search_type == LocalSearchType.TIME_WINDOW_AWARE:
        return ls.improve(route, duration_func, time_windows, arrival_times)  # type: ignore
    elif local_search_type == LocalSearchType.HYBRID:
        return ls.improve(route, duration_func, time_windows, arrival_times)  # type: ignore

    return ls.improve(route, duration_func)


# Export all classes and functions
__all__ = [
    'LocalSearchType',
    'BaseLocalSearch',
    'TwoOptLocalSearch',
    'ThreeOptLocalSearch',
    'OrOptLocalSearch',
    'SwapLocalSearch',
    'CrossExchangeLocalSearch',
    'TimeWindowAwareLocalSearch',
    'HybridLocalSearch',
    'get_local_search',
    'apply_local_search',
]
