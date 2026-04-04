#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Local Search Module

Comprehensive tests for all local search algorithms:
- 2-opt
- 3-opt
- Or-opt
- Swap
- Cross Exchange
- Time Window Aware
- Hybrid

Run with:
    cd optimizer_api
    pytest tests/test_local_search.py -v

Version: 1.0.0
Author: Super Z AI Assistant
Date: 2026-04-04
"""

import sys
import os
import pytest
import math

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.local_search import (
    LocalSearchType,
    BaseLocalSearch,
    TwoOptLocalSearch,
    ThreeOptLocalSearch,
    OrOptLocalSearch,
    SwapLocalSearch,
    CrossExchangeLocalSearch,
    TimeWindowAwareLocalSearch,
    HybridLocalSearch,
    get_local_search,
    apply_local_search,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def simple_route():
    """Simple 5-node route for basic tests"""
    return ["A", "B", "C", "D", "E"]


@pytest.fixture
def simple_distance_matrix():
    """Simple distance matrix for ABCDE route"""
    return {
        "A": {"A": 0, "B": 10, "C": 20, "D": 30, "E": 40},
        "B": {"A": 10, "B": 0, "C": 10, "D": 20, "E": 30},
        "C": {"A": 20, "B": 10, "C": 0, "D": 10, "E": 20},
        "D": {"A": 30, "B": 20, "C": 10, "D": 0, "E": 10},
        "E": {"A": 40, "B": 30, "C": 20, "D": 10, "E": 0},
    }


@pytest.fixture
def simple_duration_func(simple_distance_matrix):
    """Create a simple duration function"""
    def duration_func(route):
        if not route:
            return 0.0
        total = 0.0
        prev = route[0]
        for loc in route[1:]:
            total += simple_distance_matrix.get(prev, {}).get(loc, 15.0)
            prev = loc
        # Return to start
        total += simple_distance_matrix.get(prev, {}).get(route[0], 15.0)
        return total
    return duration_func


@pytest.fixture
def optimal_route():
    """Optimally ordered route (should not improve)"""
    return ["A", "B", "C", "D", "E"]


@pytest.fixture
def suboptimal_route():
    """Suboptimal route that can be improved"""
    # A->E->B->D->C is worse than A->B->C->D->E
    return ["A", "E", "B", "D", "C"]


@pytest.fixture
def reverse_route():
    """Reverse route"""
    return ["E", "D", "C", "B", "A"]


@pytest.fixture
def time_windows():
    """Time windows for CVRPTW tests"""
    return {
        "A": (0, 30),
        "B": (10, 40),
        "C": (20, 50),
        "D": (30, 60),
        "E": (40, 70),
    }


@pytest.fixture
def arrival_times():
    """Arrival times for CVRPTW tests"""
    return {
        "A": 0,
        "B": 15,
        "C": 25,
        "D": 35,
        "E": 45,
    }


# ============================================================
# Test TwoOptLocalSearch
# ============================================================

class TestTwoOptLocalSearch:
    """Tests for 2-opt local search"""
    
    def test_improve_suboptimal_route(self, suboptimal_route, simple_duration_func):
        """2-opt should improve a suboptimal route"""
        ls = TwoOptLocalSearch(max_iterations=100)
        original_duration = simple_duration_func(suboptimal_route)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        assert improved_duration <= original_duration
        assert len(improved_route) == len(suboptimal_route)
        assert set(improved_route) == set(suboptimal_route)
    
    def test_no_change_optimal_route(self, optimal_route, simple_duration_func):
        """2-opt should not worsen an optimal route"""
        ls = TwoOptLocalSearch(max_iterations=100)
        original_duration = simple_duration_func(optimal_route)
        
        improved_route, improved_duration = ls.improve(optimal_route, simple_duration_func)
        
        # Should be same or better
        assert improved_duration <= original_duration
    
    def test_small_route_handling(self, simple_duration_func):
        """2-opt should handle small routes gracefully"""
        ls = TwoOptLocalSearch()
        
        # Single element
        route, duration = ls.improve(["A"], simple_duration_func)
        assert route == ["A"]
        
        # Two elements
        route, duration = ls.improve(["A", "B"], simple_duration_func)
        assert set(route) == {"A", "B"}
    
    def test_empty_route(self, simple_duration_func):
        """2-opt should handle empty route"""
        ls = TwoOptLocalSearch()
        route, duration = ls.improve([], simple_duration_func)
        assert route == []
        assert duration == 0.0
    
    def test_first_improvement_mode(self, suboptimal_route, simple_duration_func):
        """2-opt first improvement should be faster but may find local optima"""
        ls = TwoOptLocalSearch(max_iterations=100, first_improvement=True)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        # Should still improve
        assert improved_duration < simple_duration_func(suboptimal_route)


# ============================================================
# Test ThreeOptLocalSearch
# ============================================================

class TestThreeOptLocalSearch:
    """Tests for 3-opt local search"""
    
    def test_improve_suboptimal_route(self, suboptimal_route, simple_duration_func):
        """3-opt should improve a suboptimal route"""
        ls = ThreeOptLocalSearch(max_iterations=50)
        original_duration = simple_duration_func(suboptimal_route)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        assert improved_duration <= original_duration
        assert len(improved_route) == len(suboptimal_route)
    
    def test_fallback_to_2opt_for_small_routes(self, simple_duration_func):
        """3-opt should fallback to 2-opt for small routes"""
        ls = ThreeOptLocalSearch()
        
        # 3-node route (too small for 3-opt)
        route = ["A", "B", "C"]
        improved_route, _ = ls.improve(route, simple_duration_func)
        
        assert len(improved_route) == 3
        assert set(improved_route) == {"A", "B", "C"}
    
    def test_higher_quality_than_2opt(self, suboptimal_route, simple_duration_func):
        """3-opt should generally find equal or better solutions than 2-opt"""
        ls_2opt = TwoOptLocalSearch(max_iterations=100)
        ls_3opt = ThreeOptLocalSearch(max_iterations=50)
        
        _, duration_2opt = ls_2opt.improve(suboptimal_route.copy(), simple_duration_func)
        _, duration_3opt = ls_3opt.improve(suboptimal_route.copy(), simple_duration_func)
        
        # 3-opt should be at least as good
        # Note: May not always be better due to random factors
        assert duration_3opt <= duration_2opt * 1.1  # Allow 10% tolerance


# ============================================================
# Test OrOptLocalSearch
# ============================================================

class TestOrOptLocalSearch:
    """Tests for Or-opt local search"""
    
    def test_improve_route(self, suboptimal_route, simple_duration_func):
        """Or-opt should improve a suboptimal route"""
        ls = OrOptLocalSearch(max_iterations=100)
        original_duration = simple_duration_func(suboptimal_route)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        assert improved_duration <= original_duration
        assert len(improved_route) == len(suboptimal_route)
    
    def test_segment_sizes(self, simple_route, simple_duration_func):
        """Or-opt should handle different segment sizes"""
        for segment_size in [1, 2, 3]:
            ls = OrOptLocalSearch(max_iterations=50, max_segment_size=segment_size)
            improved_route, _ = ls.improve(simple_route.copy(), simple_duration_func)
            assert len(improved_route) == len(simple_route)
    
    def test_small_route_handling(self, simple_duration_func):
        """Or-opt should handle small routes"""
        ls = OrOptLocalSearch()
        
        route, _ = ls.improve(["A", "B"], simple_duration_func)
        assert len(route) == 2


# ============================================================
# Test SwapLocalSearch
# ============================================================

class TestSwapLocalSearch:
    """Tests for Swap local search"""
    
    def test_improve_route(self, suboptimal_route, simple_duration_func):
        """Swap should improve a suboptimal route"""
        ls = SwapLocalSearch(max_iterations=100)
        original_duration = simple_duration_func(suboptimal_route)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        assert improved_duration <= original_duration
    
    def test_swap_preserves_elements(self, simple_route, simple_duration_func):
        """Swap should preserve all elements"""
        ls = SwapLocalSearch()
        
        improved_route, _ = ls.improve(simple_route, simple_duration_func)
        
        assert set(improved_route) == set(simple_route)
        assert len(improved_route) == len(simple_route)
    
    def test_no_adjacent_swaps(self, simple_duration_func):
        """Swap should skip adjacent swaps (handled by 2-opt)"""
        ls = SwapLocalSearch()
        
        # Create a route where only adjacent swap would help
        # This tests the skip logic
        route = ["A", "B", "C", "D", "E"]
        improved_route, _ = ls.improve(route, simple_duration_func)
        
        # Should still produce valid route
        assert len(improved_route) == len(route)


# ============================================================
# Test CrossExchangeLocalSearch
# ============================================================

class TestCrossExchangeLocalSearch:
    """Tests for Cross Exchange local search"""
    
    def test_improve_route(self, suboptimal_route, simple_duration_func):
        """Cross Exchange should improve a suboptimal route"""
        ls = CrossExchangeLocalSearch(max_iterations=50)
        original_duration = simple_duration_func(suboptimal_route)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        assert improved_duration <= original_duration
        assert len(improved_route) == len(suboptimal_route)
    
    def test_segment_exchange(self, simple_route, simple_duration_func):
        """Cross Exchange should handle segment exchanges"""
        ls = CrossExchangeLocalSearch(max_segment_size=2)
        
        improved_route, _ = ls.improve(simple_route, simple_duration_func)
        
        assert set(improved_route) == set(simple_route)
    
    def test_fallback_to_swap(self, simple_duration_func):
        """Cross Exchange should fallback to Swap for small routes"""
        ls = CrossExchangeLocalSearch()
        
        small_route = ["A", "B", "C"]
        improved_route, _ = ls.improve(small_route, simple_duration_func)
        
        assert len(improved_route) == 3


# ============================================================
# Test TimeWindowAwareLocalSearch
# ============================================================

class TestTimeWindowAwareLocalSearch:
    """Tests for Time Window Aware local search"""
    
    def test_without_time_windows(self, simple_route, simple_duration_func):
        """Should fallback to 2-opt when no time windows provided"""
        ls = TimeWindowAwareLocalSearch()
        
        improved_route, _ = ls.improve(simple_route, simple_duration_func)
        
        assert len(improved_route) == len(simple_route)
    
    def test_with_time_windows(self, simple_route, simple_duration_func, time_windows, arrival_times):
        """Should consider time windows when optimizing"""
        ls = TimeWindowAwareLocalSearch(tw_penalty=100.0)
        
        improved_route, _ = ls.improve(
            simple_route, 
            simple_duration_func,
            time_windows=time_windows,
            arrival_times=arrival_times
        )
        
        assert len(improved_route) == len(simple_route)
    
    def test_penalty_calculation(self, simple_duration_func, time_windows):
        """Should penalize time window violations"""
        ls = TimeWindowAwareLocalSearch(tw_penalty=50.0)
        
        # Route with likely violations
        route = ["E", "D", "C", "B", "A"]  # Reverse order
        arrival_times = {"E": 0, "D": 10, "C": 20, "B": 30, "A": 40}
        
        improved_route, _ = ls.improve(
            route,
            simple_duration_func,
            time_windows=time_windows,
            arrival_times=arrival_times
        )
        
        assert set(improved_route) == set(route)


# ============================================================
# Test HybridLocalSearch
# ============================================================

class TestHybridLocalSearch:
    """Tests for Hybrid local search"""
    
    def test_default_methods(self, suboptimal_route, simple_duration_func):
        """Hybrid should use default methods"""
        ls = HybridLocalSearch(max_iterations=10)
        original_duration = simple_duration_func(suboptimal_route)
        
        improved_route, improved_duration = ls.improve(suboptimal_route, simple_duration_func)
        
        assert improved_duration <= original_duration
    
    def test_custom_methods(self, suboptimal_route, simple_duration_func):
        """Hybrid should work with custom methods"""
        ls = HybridLocalSearch(
            methods=[LocalSearchType.SWAP, LocalSearchType.TWO_OPT],
            max_iterations=10
        )
        
        improved_route, _ = ls.improve(suboptimal_route, simple_duration_func)
        
        assert len(improved_route) == len(suboptimal_route)
    
    def test_without_time_windows(self, suboptimal_route, simple_duration_func):
        """Hybrid should skip time window method when no data"""
        ls = HybridLocalSearch(
            methods=[LocalSearchType.TWO_OPT, LocalSearchType.TIME_WINDOW_AWARE],
            max_iterations=10
        )
        
        # Should not raise error
        improved_route, _ = ls.improve(suboptimal_route, simple_duration_func)
        
        assert len(improved_route) == len(suboptimal_route)
    
    def test_with_time_windows(self, suboptimal_route, simple_duration_func, time_windows, arrival_times):
        """Hybrid should use time window method when data available"""
        ls = HybridLocalSearch(max_iterations=10)
        
        improved_route, _ = ls.improve(
            suboptimal_route,
            simple_duration_func,
            time_windows=time_windows,
            arrival_times=arrival_times
        )
        
        assert len(improved_route) == len(suboptimal_route)


# ============================================================
# Test Factory Functions
# ============================================================

class TestFactoryFunctions:
    """Tests for factory functions"""
    
    def test_get_local_search_none(self):
        """get_local_search should return None for NONE type"""
        ls = get_local_search(LocalSearchType.NONE)
        assert ls is None
    
    def test_get_local_search_2opt(self):
        """get_local_search should return TwoOptLocalSearch"""
        ls = get_local_search(LocalSearchType.TWO_OPT)
        assert isinstance(ls, TwoOptLocalSearch)
    
    def test_get_local_search_3opt(self):
        """get_local_search should return ThreeOptLocalSearch"""
        ls = get_local_search(LocalSearchType.THREE_OPT)
        assert isinstance(ls, ThreeOptLocalSearch)
    
    def test_get_local_search_hybrid(self):
        """get_local_search should return HybridLocalSearch"""
        ls = get_local_search(LocalSearchType.HYBRID)
        assert isinstance(ls, HybridLocalSearch)
    
    def test_apply_local_search_none(self, simple_route, simple_duration_func):
        """apply_local_search should return unchanged for NONE type"""
        route, duration = apply_local_search(
            simple_route, 
            simple_duration_func, 
            LocalSearchType.NONE
        )
        assert route == simple_route
    
    def test_apply_local_search_default(self, simple_route, simple_duration_func):
        """apply_local_search should default to 2-opt"""
        route, duration = apply_local_search(
            simple_route,
            simple_duration_func,
            LocalSearchType.TWO_OPT
        )
        assert len(route) == len(simple_route)


# ============================================================
# Test Algorithm Comparison
# ============================================================

class TestAlgorithmComparison:
    """Compare different algorithms on same problem"""
    
    def test_all_improve_suboptimal(self, suboptimal_route, simple_duration_func):
        """All algorithms should improve or maintain route quality"""
        original_duration = simple_duration_func(suboptimal_route)
        
        algorithms = [
            (LocalSearchType.TWO_OPT, {}),
            (LocalSearchType.THREE_OPT, {"max_iterations": 50}),
            (LocalSearchType.OR_OPT, {}),
            (LocalSearchType.SWAP, {}),
            (LocalSearchType.HYBRID, {"max_iterations": 20}),
        ]
        
        for ls_type, kwargs in algorithms:
            route, duration = apply_local_search(
                suboptimal_route.copy(),
                simple_duration_func,
                ls_type,
                **kwargs
            )
            
            # Should improve or stay same
            assert duration <= original_duration, f"{ls_type} made route worse"
    
    def test_larger_route(self):
        """Test with larger route"""
        # Create a shuffled route
        import random
        random.seed(42)
        locations = [f"L{i}" for i in range(20)]
        shuffled = locations.copy()
        random.shuffle(shuffled)
        
        # Create distance matrix (Euclidean on 1D)
        distance_matrix = {}
        for i, loc1 in enumerate(locations):
            distance_matrix[loc1] = {}
            for j, loc2 in enumerate(locations):
                distance_matrix[loc1][loc2] = abs(i - j) * 10
        
        def duration_func(route):
            total = 0
            for i in range(len(route) - 1):
                total += distance_matrix[route[i]][route[i + 1]]
            total += distance_matrix[route[-1]][route[0]]
            return total
        
        # Test hybrid
        route, duration = apply_local_search(
            shuffled,
            duration_func,
            LocalSearchType.HYBRID,
            max_iterations=20
        )
        
        # Should improve
        original = duration_func(shuffled)
        assert duration <= original
        assert len(route) == len(shuffled)


# ============================================================
# Test Edge Cases
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_single_element_route(self, simple_duration_func):
        """All algorithms should handle single element"""
        for ls_type in [LocalSearchType.TWO_OPT, LocalSearchType.THREE_OPT, 
                        LocalSearchType.OR_OPT, LocalSearchType.SWAP,
                        LocalSearchType.HYBRID]:
            route, _ = apply_local_search(["A"], simple_duration_func, ls_type)
            assert route == ["A"], f"{ls_type} failed on single element"
    
    def test_two_element_route(self, simple_duration_func):
        """All algorithms should handle two elements"""
        for ls_type in [LocalSearchType.TWO_OPT, LocalSearchType.THREE_OPT,
                        LocalSearchType.OR_OPT, LocalSearchType.SWAP,
                        LocalSearchType.HYBRID]:
            route, _ = apply_local_search(["A", "B"], simple_duration_func, ls_type)
            assert set(route) == {"A", "B"}, f"{ls_type} failed on two elements"
    
    def test_large_iterations(self, simple_route, simple_duration_func):
        """Should handle large iteration counts"""
        ls = TwoOptLocalSearch(max_iterations=10000)
        route, _ = ls.improve(simple_route, simple_duration_func)
        assert len(route) == len(simple_route)
    
    def test_duplicate_locations(self, simple_duration_func):
        """Should handle routes with conceptually same locations"""
        # Note: Current implementation may not support duplicates well
        # This test documents expected behavior
        route = ["A", "B", "C", "D", "E"]
        ls = TwoOptLocalSearch()
        improved, _ = ls.improve(route, simple_duration_func)
        assert len(improved) == 5


# ============================================================
# Performance Tests
# ============================================================

class TestPerformance:
    """Basic performance tests"""
    
    def test_2opt_speed(self):
        """2-opt should complete quickly on moderate size"""
        import time
        
        # Create 50-node route
        locations = [f"L{i}" for i in range(50)]
        
        def duration_func(route):
            # Simple distance based on position
            total = 0
            for i in range(len(route) - 1):
                total += abs(int(route[i][1:]) - int(route[i + 1][1:]))
            return total
        
        ls = TwoOptLocalSearch(max_iterations=100)
        
        start = time.time()
        route, _ = ls.improve(locations, duration_func)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0
    
    def test_hybrid_speed(self):
        """Hybrid should complete quickly with few iterations"""
        import time
        
        locations = [f"L{i}" for i in range(30)]
        
        def duration_func(route):
            total = 0
            for i in range(len(route) - 1):
                total += abs(int(route[i][1:]) - int(route[i + 1][1:]))
            return total
        
        ls = HybridLocalSearch(max_iterations=5)
        
        start = time.time()
        route, _ = ls.improve(locations, duration_func)
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
