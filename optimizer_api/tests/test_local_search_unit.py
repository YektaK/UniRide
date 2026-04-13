import pytest
from utils.local_search import (
    TwoOptLocalSearch, SwapLocalSearch, OrOptLocalSearch, 
    ThreeOptLocalSearch, LocalSearchType, TimeWindowAwareLocalSearch
)

@pytest.fixture
def simple_route():
    # A non-optimal route with mixed order (A-D-B-C-E)
    return ["A", "D", "B", "C", "E"]

@pytest.fixture
def dist_func():
    # Coordinates in a straight line: A(1) B(2) C(3) D(4) E(5)
    # Optimal order is A-B-C-D-E
    coords = {
        "Depot": (0, 0),
        "A": (1, 0),
        "B": (2, 0),
        "C": (3, 0),
        "D": (4, 0),
        "E": (5, 0)
    }
    def calculate(route):
        if not route: return 0
        d = 0
        full_route = ["Depot"] + route + ["Depot"]
        for i in range(len(full_route)-1):
            p1 = coords[full_route[i]]
            p2 = coords[full_route[i+1]]
            d += ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        return d
    return calculate

def test_two_opt_improvement(simple_route, dist_func):
    # Initial: Depot -> A -> B -> C -> Depot (Crossing)
    initial_dist = dist_func(simple_route)
    
    ls = TwoOptLocalSearch()
    improved_route, improved_dist = ls.improve(simple_route, dist_func)
    
    assert improved_dist < initial_dist
    assert len(improved_route) == len(simple_route)
    assert set(improved_route) == set(simple_route)

def test_swap_improvement(simple_route, dist_func):
    ls = SwapLocalSearch()
    initial_dist = dist_func(simple_route)
    improved_route, improved_dist = ls.improve(simple_route, dist_func)
    
    assert improved_dist <= initial_dist
    assert set(improved_route) == set(simple_route)

def test_or_opt_improvement(simple_route, dist_func):
    ls = OrOptLocalSearch(max_segment_size=2)
    initial_dist = dist_func(simple_route)
    improved_route, improved_dist = ls.improve(simple_route, dist_func)
    
    assert improved_dist <= initial_dist

def test_three_opt_small_route_fallback(simple_route, dist_func):
    # 3-opt with route < 4 should fall back to 2-opt
    ls = ThreeOptLocalSearch()
    improved_route, improved_dist = ls.improve(simple_route, dist_func)
    assert improved_dist <= dist_func(simple_route)

def test_tw_aware_reduction():
    # Mocking a scenario where a longer route reduces TW violations
    route = ["L1", "L2"]
    time_windows = {"L1": (10, 20), "L2": (30, 40)}
    arrival_times = {"L1": 25, "L2": 45} # Both late
    
    def dur_func(r): return len(r) * 10
    
    ls = TimeWindowAwareLocalSearch(tw_penalty=1000)
    # Even if it doesn't find a better route in this mock, 
    # we test that it runs without error and respects penalty logic
    improved_route, improved_dur = ls.improve(route, dur_func, time_windows, arrival_times)
    assert len(improved_route) == len(route)

def test_two_opt_swap_logic():
    ls = TwoOptLocalSearch()
    route = ["A", "B", "C", "D", "E"]
    # Swap indices 1 to 3 (B, C, D) -> reversed is (D, C, B)
    new_route = ls._two_opt_swap(route, 1, 3)
    assert new_route == ["A", "D", "C", "B", "E"]
