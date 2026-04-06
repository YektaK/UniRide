"""
Test suite for CVRPTW Phase 3: SplitDecoder Backward/Forward Scheduling

Tests:
1. Backward scheduling for PICKUP direction
2. Forward scheduling for DROPOFF direction
3. Time window violation detection
4. Departure time calculation with offset
5. Split strategies with time windows
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.split_decoder import (
    SplitDecoder, Direction, Trip, RouteSchedule,
    decode_giant_tour, decode_with_time_windows
)
from models.schemas import (
    OptimizationRequest, StudentNode, LocationNode, 
    TimeWindow, Direction as SchemaDirection
)


class TestSplitDecoderBackwardScheduling:
    """Test backward scheduling for PICKUP direction"""
    
    @pytest.fixture
    def distance_matrix(self):
        """Sample distance matrix (travel times in minutes)"""
        return {
            "D.Kampus": {"Sw1": 20, "Sw2": 25, "So1": 30, "So2": 35},
            "Sw1": {"D.Kampus": 20, "Sw2": 10, "So1": 15, "So2": 20},
            "Sw2": {"D.Kampus": 25, "Sw1": 10, "So1": 8, "So2": 12},
            "So1": {"D.Kampus": 30, "Sw1": 15, "Sw2": 8, "So2": 6},
            "So2": {"D.Kampus": 35, "Sw1": 20, "Sw2": 12, "So1": 6}
        }
    
    @pytest.fixture
    def demands(self):
        """Student demands (wheelchair, other)"""
        return {
            "Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1), "So2": (0, 1)
        }
    
    def test_backward_scheduling_basic(self, distance_matrix, demands):
        """Test basic backward scheduling from target arrival time"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            time_windows={"Sw1": (480, 540), "Sw2": (510, 540)},
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=540,  # 09:00
            offset_minutes=10
        )
        
        giant_tour = ["Sw1", "Sw2"]
        result = decoder.decode(giant_tour, "D.Kampus", distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1
        assert result["total_cost"] > 0
        # Check departure time is before target
        if "schedules" in result and result["schedules"]:
            departure = result["schedules"][0].get("departure_time", 0)
            assert departure < 540, "Departure should be before target time"
    
    def test_backward_scheduling_with_offset(self, distance_matrix, demands):
        """Test that offset is correctly applied to departure time"""
        offset = 15
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=540,  # 09:00
            offset_minutes=offset
        )
        
        giant_tour = ["Sw1", "Sw2"]
        result = decoder.decode(giant_tour, "D.Kampus", distance_matrix, demands)
        
        if "schedules" in result and result["schedules"]:
            departure = result["schedules"][0].get("departure_time", 0)
            # Departure should be at least offset minutes before needed
            assert departure <= 540 - offset
    
    def test_backward_scheduling_multiple_students(self, distance_matrix, demands):
        """Test backward scheduling with multiple students"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            time_windows={
                "Sw1": (510, 540),
                "Sw2": (510, 540),
                "So1": (510, 540),
                "So2": (510, 540)
            },
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=540,
            offset_minutes=10
        )
        
        giant_tour = ["Sw1", "Sw2", "So1", "So2"]
        result = decoder.decode(giant_tour, "D.Kampus", distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1
        assert result["total_cost"] > 0


class TestSplitDecoderForwardScheduling:
    """Test forward scheduling for DROPOFF direction"""
    
    @pytest.fixture
    def distance_matrix(self):
        """Sample distance matrix"""
        return {
            "D.Kampus": {"Sw1": 20, "Sw2": 25, "So1": 30},
            "Sw1": {"D.Kampus": 20, "Sw2": 10, "So1": 15},
            "Sw2": {"D.Kampus": 25, "Sw1": 10, "So1": 8},
            "So1": {"D.Kampus": 30, "Sw1": 15, "Sw2": 8}
        }
    
    @pytest.fixture
    def demands(self):
        return {"Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1)}
    
    def test_forward_scheduling_basic(self, distance_matrix, demands):
        """Test basic forward scheduling for dropoff"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            time_windows={"Sw1": (840, 900), "Sw2": (840, 900)},
            use_time_windows=True,
            direction=Direction.DROPOFF,
            target_time=840,  # 14:00
            offset_minutes=10
        )
        
        giant_tour = ["Sw1", "Sw2"]
        result = decoder.decode(giant_tour, "D.Kampus", distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1
        assert result["total_cost"] > 0
    
    def test_forward_scheduling_departure_from_school(self, distance_matrix, demands):
        """Test that forward scheduling starts from school departure time"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            use_time_windows=True,
            direction=Direction.DROPOFF,
            target_time=840,  # 14:00
            offset_minutes=10
        )
        
        giant_tour = ["Sw1", "Sw2", "So1"]
        result = decoder.decode(giant_tour, "D.Kampus", distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1


class TestTimeWindowViolations:
    """Test time window violation detection and counting"""
    
    @pytest.fixture
    def tight_time_windows(self):
        """Tight time windows that may cause violations"""
        return {
            "Sw1": (500, 510),  # Very tight: 08:20-08:30
            "Sw2": (520, 530),  # 08:40-08:50
            "So1": (540, 550),  # 09:00-09:10
        }
    
    @pytest.fixture
    def distance_matrix(self):
        """Distance matrix with longer travel times"""
        return {
            "D.Kampus": {"Sw1": 30, "Sw2": 40, "So1": 50},
            "Sw1": {"D.Kampus": 30, "Sw2": 25, "So1": 35},
            "Sw2": {"D.Kampus": 40, "Sw1": 25, "So1": 20},
            "So1": {"D.Kampus": 50, "Sw1": 35, "Sw2": 20}
        }
    
    @pytest.fixture
    def demands(self):
        return {"Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1)}
    
    def test_time_window_violation_counting(self, distance_matrix, demands, tight_time_windows):
        """Test that time window violations are counted correctly"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            time_windows=tight_time_windows,
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=550,
            offset_minutes=10
        )
        
        giant_tour = ["Sw1", "Sw2", "So1"]
        result = decoder.decode(giant_tour, "D.Kampus", distance_matrix, demands)
        
        # Result should include time window violations count
        assert "time_window_violations" in result
        # Violations might be 0 if schedule is feasible, or > 0 if not


class TestConvenienceFunctions:
    """Test convenience functions decode_giant_tour and decode_with_time_windows"""
    
    @pytest.fixture
    def distance_matrix(self):
        return {
            "D.Kampus": {"Sw1": 20, "Sw2": 25},
            "Sw1": {"D.Kampus": 20, "Sw2": 10},
            "Sw2": {"D.Kampus": 25, "Sw1": 10}
        }
    
    @pytest.fixture
    def demands(self):
        return {"Sw1": (1, 0), "Sw2": (1, 0)}
    
    def test_decode_giant_tour_basic(self, distance_matrix, demands):
        """Test basic decode_giant_tour function"""
        result = decode_giant_tour(
            giant_tour=["Sw1", "Sw2"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands
        )
        
        assert "routes" in result
        assert "costs" in result
        assert "total_cost" in result
        assert "num_vehicles" in result
    
    def test_decode_with_time_windows_pickup(self, distance_matrix, demands):
        """Test decode_with_time_windows for PICKUP"""
        result = decode_with_time_windows(
            giant_tour=["Sw1", "Sw2"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands,
            time_windows={"Sw1": (510, 540), "Sw2": (510, 540)},
            direction=Direction.PICKUP,
            target_time=540,
            offset_minutes=10
        )
        
        assert "routes" in result
        assert "time_window_violations" in result
    
    def test_decode_with_time_windows_dropoff(self, distance_matrix, demands):
        """Test decode_with_time_windows for DROPOFF"""
        result = decode_with_time_windows(
            giant_tour=["Sw1", "Sw2"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands,
            time_windows={"Sw1": (840, 870), "Sw2": (840, 870)},
            direction=Direction.DROPOFF,
            target_time=840,
            offset_minutes=10
        )
        
        assert "routes" in result
        assert "time_window_violations" in result


class TestSplitDecoderWithDetails:
    """Test decode_with_details method"""
    
    @pytest.fixture
    def distance_matrix(self):
        return {
            "D.Kampus": {"Sw1": 20, "Sw2": 25, "So1": 30},
            "Sw1": {"D.Kampus": 20, "Sw2": 10, "So1": 15},
            "Sw2": {"D.Kampus": 25, "Sw1": 10, "So1": 8},
            "So1": {"D.Kampus": 30, "Sw1": 15, "Sw2": 8}
        }
    
    @pytest.fixture
    def demands(self):
        return {"Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1)}
    
    def test_decode_with_details_structure(self, distance_matrix, demands):
        """Test that decode_with_details returns detailed structure"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0
        )
        
        result = decoder.decode_with_details(
            giant_tour=["Sw1", "Sw2", "So1"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands
        )
        
        assert "detailed_routes" in result
        if result["detailed_routes"]:
            detail = result["detailed_routes"][0]
            assert "locations" in detail
            assert "cost" in detail
            assert "sw_count" in detail
            assert "so_count" in detail
            assert "segments" in detail
    
    def test_decode_with_details_time_windows(self, distance_matrix, demands):
        """Test decode_with_details with time windows"""
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120.0,
            time_windows={"Sw1": (510, 540), "Sw2": (510, 540), "So1": (510, 540)},
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=540,
            offset_minutes=10
        )
        
        result = decoder.decode_with_details(
            giant_tour=["Sw1", "Sw2", "So1"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands
        )
        
        assert "time_window_violations" in result
        if result["detailed_routes"]:
            detail = result["detailed_routes"][0]
            # Should have departure time if time windows are used
            if "departure_time_str" in detail:
                assert detail["departure_time_str"] is not None


class TestMinutesToTimeConversion:
    """Test time conversion utility"""
    
    def test_minutes_to_time_conversion(self):
        """Test minutes to HH:MM conversion"""
        decoder = SplitDecoder()
        
        # Test various times
        assert decoder._minutes_to_time(540) == "09:00"
        assert decoder._minutes_to_time(480) == "08:00"
        assert decoder._minutes_to_time(0) == "00:00"
        assert decoder._minutes_to_time(720) == "12:00"
        assert decoder._minutes_to_time(1440) == "00:00"  # Wraps around


class TestEmptyAndEdgeCases:
    """Test edge cases and empty inputs"""
    
    def test_empty_giant_tour(self):
        """Test with empty giant tour"""
        decoder = SplitDecoder()
        result = decoder.decode(
            giant_tour=[],
            depot="D.Kampus",
            distance_matrix={},
            demands={}
        )
        
        assert result["routes"] == []
        assert result["num_vehicles"] == 0
        assert result["total_cost"] == 0
    
    def test_single_location(self):
        """Test with single location"""
        distance_matrix = {
            "D.Kampus": {"Sw1": 20},
            "Sw1": {"D.Kampus": 20}
        }
        demands = {"Sw1": (1, 0)}
        
        decoder = SplitDecoder()
        result = decoder.decode(
            giant_tour=["Sw1"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands
        )
        
        assert result["num_vehicles"] == 1
        assert len(result["routes"]) == 1
    
    def test_capacity_violation(self):
        """Test that capacity violations are handled"""
        distance_matrix = {
            "D.Kampus": {"Sw1": 20, "Sw2": 25, "Sw3": 30, "Sw4": 35, "Sw5": 40},
            "Sw1": {"D.Kampus": 20, "Sw2": 10, "Sw3": 15, "Sw4": 20, "Sw5": 25},
            "Sw2": {"D.Kampus": 25, "Sw1": 10, "Sw3": 8, "Sw4": 12, "Sw5": 15},
            "Sw3": {"D.Kampus": 30, "Sw1": 15, "Sw2": 8, "Sw4": 6, "Sw5": 10},
            "Sw4": {"D.Kampus": 35, "Sw1": 20, "Sw2": 12, "Sw3": 6, "Sw5": 5},
            "Sw5": {"D.Kampus": 40, "Sw1": 25, "Sw2": 15, "Sw3": 10, "Sw4": 5}
        }
        demands = {
            "Sw1": (1, 0), "Sw2": (1, 0), "Sw3": (1, 0), 
            "Sw4": (1, 0), "Sw5": (1, 0)
        }
        
        # With capacity of 2 wheelchair, should need multiple vehicles
        decoder = SplitDecoder(sw_capacity=2, so_capacity=5)
        result = decoder.decode(
            giant_tour=["Sw1", "Sw2", "Sw3", "Sw4", "Sw5"],
            depot="D.Kampus",
            distance_matrix=distance_matrix,
            demands=demands
        )
        
        # Should have multiple vehicles due to capacity
        assert result["num_vehicles"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
