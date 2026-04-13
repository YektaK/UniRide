"""
Comprehensive tests for Split strategies and Crossover operators
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from models.schemas import OptimizationRequest, StudentNode, LocationNode


# ============================================================================
# CROSSOVER OPERATOR TESTS
# ============================================================================

class TestCrossoverOperators:
    """Test all crossover operators in GA strategies"""

    def test_pmx_basic(self):
        """Test PMX (Partially Mapped Crossover) with basic data"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        import random
        
        strategy = GAEnhancedSplitStrategy()
        strategy.rng = random.Random(42)
        
        parent1 = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        parent2 = ['D', 'E', 'F', 'G', 'A', 'B', 'C']
        
        child = strategy._crossover_pmx(parent1, parent2)
        
        # Verify it's a valid permutation
        assert sorted(child) == sorted(parent1), f"Invalid permutation: {child}"
        assert len(child) == len(parent1)

    def test_pmx_edge_cases(self):
        """Test PMX with edge cases"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        import random
        
        strategy = GAEnhancedSplitStrategy()
        strategy.rng = random.Random(42)
        
        # Empty list
        assert strategy._crossover_pmx([], []) == []
        
        # Single element
        assert strategy._crossover_pmx(['A'], ['A']) == ['A']
        
        # Two elements
        result = strategy._crossover_pmx(['A', 'B'], ['B', 'A'])
        assert sorted(result) == ['A', 'B']

    def test_pmx_large_permutation(self):
        """Test PMX with large permutations"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        import random
        
        strategy = GAEnhancedSplitStrategy()
        strategy.rng = random.Random(42)
        
        parent1 = list(map(str, range(50)))
        parent2 = list(map(str, sorted(range(50), key=lambda x: (x * 7) % 50)))
        
        for _ in range(10):
            child = strategy._crossover_pmx(parent1, parent2)
            assert sorted(child) == sorted(parent1), "PMX produced invalid permutation"

    def test_cx2_basic(self):
        """Test CX2 (Cycle Crossover 2) with basic data"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        import random
        
        strategy = GAEnhancedSplitStrategy()
        strategy.rng = random.Random(42)
        
        parent1 = ['A', 'B', 'C', 'D', 'E']
        parent2 = ['C', 'A', 'E', 'B', 'D']
        
        child = strategy._crossover_cx2(parent1, parent2)
        
        # Verify it's a valid permutation
        assert sorted(child) == sorted(parent1), f"Invalid permutation: {child}"
        assert len(child) == len(parent1)

    def test_cx2_edge_cases(self):
        """Test CX2 with edge cases"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        import random
        
        strategy = GAEnhancedSplitStrategy()
        strategy.rng = random.Random(42)
        
        # Empty list
        assert strategy._crossover_cx2([], []) == []
        
        # Single element
        assert strategy._crossover_cx2(['A'], ['A']) == ['A']
        
        # Two elements
        result = strategy._crossover_cx2(['A', 'B'], ['B', 'A'])
        assert sorted(result) == ['A', 'B']

    def test_ox1_basic(self):
        """Test OX1 (Order Crossover) with basic data"""
        from strategies.ga_strategy import GeneticAlgorithmStrategy
        import random
        
        strategy = GeneticAlgorithmStrategy()
        strategy.rng = random.Random(42)
        
        parent1 = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        parent2 = ['D', 'E', 'F', 'G', 'A', 'B', 'C']
        
        child1, child2 = strategy._order_crossover(parent1, parent2)
        
        # Verify they're valid permutations
        assert sorted(child1) == sorted(parent1), f"Invalid child1: {child1}"
        assert sorted(child2) == sorted(parent2), f"Invalid child2: {child2}"

    def test_ox1_edge_cases(self):
        """Test OX1 with edge cases"""
        from strategies.ga_strategy import GeneticAlgorithmStrategy
        import random
        
        strategy = GeneticAlgorithmStrategy()
        strategy.rng = random.Random(42)
        
        # Empty list
        assert strategy._order_crossover([], []) == ([], [])
        
        # Single element
        assert strategy._order_crossover(['A'], ['A']) == (['A'], ['A'])
        
        # Two elements
        child1, child2 = strategy._order_crossover(['A', 'B'], ['B', 'A'])
        assert sorted(child1) == ['A', 'B']
        assert sorted(child2) == ['A', 'B']


# ============================================================================
# SPLIT STRATEGY TESTS
# ============================================================================

class TestGASplitStrategy:
    """Test GA-Split Strategy"""

    @pytest.fixture
    def basic_request(self):
        """Create a basic optimization request"""
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        students = [
            StudentNode(id=f"S{i}", name=f"Student{i}", location_code=f"L{i}",
                       coordinates={"lat": 37.0667 + i * 0.01, "lng": 37.3833 + i * 0.01},
                       disability_type="Sw" if i % 2 == 0 else "So")
            for i in range(1, 6)
        ]
        
        return OptimizationRequest(
            algorithm="ga-split",
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5
        )

    def test_ga_split_basic(self, basic_request):
        """Test GA-Split with basic data"""
        from strategies.ga_split_strategy import GASplitStrategy
        
        strategy = GASplitStrategy()
        result = strategy.optimize(basic_request)
        
        assert result.success is True
        assert result.total_vehicles >= 1
        assert len(result.routes) >= 1

    def test_ga_split_empty(self):
        """Test GA-Split with no students"""
        from strategies.ga_split_strategy import GASplitStrategy
        
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        request = OptimizationRequest(
            algorithm="ga-split",
            students=[],
            depot=depot
        )
        
        strategy = GASplitStrategy()
        result = strategy.optimize(request)
        
        assert result.success is True
        assert result.total_vehicles == 0


class TestPSOSplitStrategy:
    """Test PSO-Split Strategy"""

    @pytest.fixture
    def basic_request(self):
        """Create a basic optimization request"""
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        students = [
            StudentNode(id=f"S{i}", name=f"Student{i}", location_code=f"L{i}",
                       coordinates={"lat": 37.0667 + i * 0.01, "lng": 37.3833 + i * 0.01},
                       disability_type="Sw" if i % 2 == 0 else "So")
            for i in range(1, 6)
        ]
        
        return OptimizationRequest(
            algorithm="pso-split",
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5
        )

    def test_pso_split_basic(self, basic_request):
        """Test PSO-Split with basic data"""
        from strategies.pso_split_strategy import PSOSplitStrategy
        
        strategy = PSOSplitStrategy()
        result = strategy.optimize(basic_request)
        
        assert result.success is True
        assert result.total_vehicles >= 1

    def test_pso_split_empty(self):
        """Test PSO-Split with no students"""
        from strategies.pso_split_strategy import PSOSplitStrategy
        
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        request = OptimizationRequest(
            algorithm="pso-split",
            students=[],
            depot=depot
        )
        
        strategy = PSOSplitStrategy()
        result = strategy.optimize(request)
        
        assert result.success is True
        assert result.total_vehicles == 0


class TestGWOSplitStrategy:
    """Test GWO-Split Strategy"""

    @pytest.fixture
    def basic_request(self):
        """Create a basic optimization request"""
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        students = [
            StudentNode(id=f"S{i}", name=f"Student{i}", location_code=f"L{i}",
                       coordinates={"lat": 37.0667 + i * 0.01, "lng": 37.3833 + i * 0.01},
                       disability_type="Sw" if i % 2 == 0 else "So")
            for i in range(1, 6)
        ]
        
        return OptimizationRequest(
            algorithm="gwo-split",
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5
        )

    def test_gwo_split_basic(self, basic_request):
        """Test GWO-Split with basic data"""
        from strategies.gwo_split_strategy import GWOSplitStrategy
        
        strategy = GWOSplitStrategy()
        result = strategy.optimize(basic_request)
        
        assert result.success is True
        assert result.total_vehicles >= 1

    def test_gwo_split_empty(self):
        """Test GWO-Split with no students"""
        from strategies.gwo_split_strategy import GWOSplitStrategy
        
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        request = OptimizationRequest(
            algorithm="gwo-split",
            students=[],
            depot=depot
        )
        
        strategy = GWOSplitStrategy()
        result = strategy.optimize(request)
        
        assert result.success is True
        assert result.total_vehicles == 0


class TestHHOSplitStrategy:
    """Test HHO-Split Strategy"""

    @pytest.fixture
    def basic_request(self):
        """Create a basic optimization request"""
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        students = [
            StudentNode(id=f"S{i}", name=f"Student{i}", location_code=f"L{i}",
                       coordinates={"lat": 37.0667 + i * 0.01, "lng": 37.3833 + i * 0.01},
                       disability_type="Sw" if i % 2 == 0 else "So")
            for i in range(1, 6)
        ]
        
        return OptimizationRequest(
            algorithm="hho-split",
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5
        )

    def test_hho_split_basic(self, basic_request):
        """Test HHO-Split with basic data"""
        from strategies.hho_split_strategy import HHOSplitStrategy
        
        strategy = HHOSplitStrategy()
        result = strategy.optimize(basic_request)
        
        assert result.success is True
        assert result.total_vehicles >= 1

    def test_hho_split_empty(self):
        """Test HHO-Split with no students"""
        from strategies.hho_split_strategy import HHOSplitStrategy
        
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        request = OptimizationRequest(
            algorithm="hho-split",
            students=[],
            depot=depot
        )
        
        strategy = HHOSplitStrategy()
        result = strategy.optimize(request)
        
        assert result.success is True
        assert result.total_vehicles == 0


# ============================================================================
# ENHANCED GA-SPLIT STRATEGY TESTS
# ============================================================================

class TestGAEnhancedSplitStrategy:
    """Test GA-Enhanced Split Strategy"""

    @pytest.fixture
    def basic_request(self):
        """Create a basic optimization request"""
        depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
        
        students = [
            StudentNode(id=f"S{i}", name=f"Student{i}", location_code=f"L{i}",
                       coordinates={"lat": 37.0667 + i * 0.01, "lng": 37.3833 + i * 0.01},
                       disability_type="Sw" if i % 2 == 0 else "So")
            for i in range(1, 6)
        ]
        
        return OptimizationRequest(
            algorithm="ga-split-enhanced",
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5
        )

    def test_enhanced_split_basic(self, basic_request):
        """Test GA-Enhanced Split with basic data"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        
        strategy = GAEnhancedSplitStrategy()
        result = strategy.optimize(basic_request)
        
        assert result.success is True
        assert result.total_vehicles >= 1

    def test_enhanced_split_uses_multiple_crossovers(self):
        """Verify that enhanced split uses multiple crossover operators"""
        from strategies.ga_split_strategy import GAEnhancedSplitStrategy
        
        strategy = GAEnhancedSplitStrategy()
        
        # Check that crossover methods exist
        assert hasattr(strategy, '_crossover_pmx')
        assert hasattr(strategy, '_crossover_cx2')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
