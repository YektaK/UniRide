"""
Tests for CVRPTW Phase 2 - SplitDecoder Time Window Support

Run with: pytest tests/test_cvrptw_phase2.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.split_decoder import (
    SplitDecoder, Direction, Trip, decode_giant_tour,
    decode_with_time_windows
)


class TestSplitDecoderBasic:
    """Test basic SplitDecoder functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Sample test data"""
        depot = "D.Kampus"
        giant_tour = ["Sw1", "Sw2", "So1", "So2"]
        
        distance_matrix = {
            "D.Kampus": {"Sw1": 20, "Sw2": 25, "So1": 30, "So2": 35},
            "Sw1": {"D.Kampus": 20, "Sw2": 10, "So1": 15, "So2": 20},
            "Sw2": {"D.Kampus": 25, "Sw1": 10, "So1": 8, "So2": 12},
            "So1": {"D.Kampus": 30, "Sw1": 15, "Sw2": 8, "So2": 6},
            "So2": {"D.Kampus": 35, "Sw1": 20, "Sw2": 12, "So1": 6}
        }
        
        demands = {
            "Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1), "So2": (0, 1)
        }
        
        return depot, giant_tour, distance_matrix, demands
    
    def test_basic_decode(self, sample_data):
        """Test basic decoding without time windows"""
        depot, giant_tour, distance_matrix, demands = sample_data
        
        decoder = SplitDecoder(sw_capacity=4, so_capacity=5)
        result = decoder.decode(giant_tour, depot, distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1
        assert result["total_cost"] > 0
        assert len(result["routes"]) == result["num_vehicles"]
    
    def test_capacity_constraint(self, sample_data):
        """Test capacity constraints are respected"""
        depot, giant_tour, distance_matrix, demands = sample_data
        
        # Small capacity should split into more vehicles
        decoder = SplitDecoder(sw_capacity=1, so_capacity=2)
        result = decoder.decode(giant_tour, depot, distance_matrix, demands)
        
        # Verify each route respects capacity
        for route in result["routes"]:
            sw_count = sum(demands.get(loc, (0, 0))[0] for loc in route)
            so_count = sum(demands.get(loc, (0, 0))[1] for loc in route)
            assert sw_count <= 1
            assert so_count <= 2
    
    def test_empty_tour(self, sample_data):
        """Test with empty giant tour"""
        depot, _, distance_matrix, demands = sample_data
        
        decoder = SplitDecoder()
        result = decoder.decode([], depot, distance_matrix, demands)
        
        assert result["num_vehicles"] == 0
        assert result["total_cost"] == 0
        assert result["routes"] == []


class TestSplitDecoderTimeWindows:
    """Test SplitDecoder with time windows"""
    
    @pytest.fixture
    def tw_data(self):
        """Test data with time windows"""
        depot = "D.Kampus"
        giant_tour = ["Sw1", "Sw2", "So1"]
        
        distance_matrix = {
            "D.Kampus": {"Sw1": 20, "Sw2": 30, "So1": 25},
            "Sw1": {"D.Kampus": 20, "Sw2": 15, "So1": 10},
            "Sw2": {"D.Kampus": 30, "Sw1": 15, "So1": 8},
            "So1": {"D.Kampus": 25, "Sw1": 10, "Sw2": 8}
        }
        
        demands = {
            "Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1)
        }
        
        # Time windows: (earliest, latest) in minutes from midnight
        # All need to be at school by 09:00 (540 min)
        time_windows = {
            "Sw1": (480, 540),  # 08:00 - 09:00
            "Sw2": (510, 540),  # 08:30 - 09:00
            "So1": (480, 540)   # 08:00 - 09:00
        }
        
        return depot, giant_tour, distance_matrix, demands, time_windows
    
    def test_pickup_backward_scheduling(self, tw_data):
        """Test pickup with backward scheduling"""
        depot, giant_tour, distance_matrix, demands, time_windows = tw_data
        
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            time_windows=time_windows,
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=540,  # 09:00
            offset_minutes=10
        )
        
        result = decoder.decode_with_details(giant_tour, depot, distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1
        assert result["time_window_violations"] >= 0
        
        # Check that departure times are calculated
        if "schedules" in result and result["schedules"]:
            for schedule in result["schedules"]:
                assert "departure_time" in schedule
    
    def test_dropoff_forward_scheduling(self, tw_data):
        """Test dropoff with forward scheduling"""
        depot, giant_tour, distance_matrix, demands, time_windows = tw_data
        
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            time_windows=time_windows,
            use_time_windows=True,
            direction=Direction.DROPOFF,
            target_time=480,  # 08:00 - start of school day
            offset_minutes=10
        )
        
        result = decoder.decode(giant_tour, depot, distance_matrix, demands)
        
        assert result["num_vehicles"] >= 1
        assert result["total_cost"] > 0
    
    def test_time_window_violation_detection(self, tw_data):
        """Test that time window violations are detected"""
        depot, giant_tour, distance_matrix, demands, time_windows = tw_data
        
        # Very tight time windows that will cause violations
        tight_tw = {
            "Sw1": (500, 505),  # Only 5 min window
            "Sw2": (505, 510),
            "So1": (510, 515)
        }
        
        decoder = SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            time_windows=tight_tw,
            use_time_windows=True,
            direction=Direction.PICKUP
        )
        
        result = decoder.decode(giant_tour, depot, distance_matrix, demands)
        
        # May have violations due to tight windows
        assert "time_window_violations" in result
    
    def test_decode_with_time_windows_function(self, tw_data):
        """Test convenience function for CVRPTW"""
        depot, giant_tour, distance_matrix, demands, time_windows = tw_data
        
        result = decode_with_time_windows(
            giant_tour=giant_tour,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            time_windows=time_windows,
            direction=Direction.PICKUP,
            target_time=540,
            offset_minutes=10
        )
        
        assert result["num_vehicles"] >= 1
        assert "detailed_routes" in result
        assert "time_window_violations" in result


class TestDirection:
    """Test Direction enum"""
    
    def test_direction_values(self):
        """Test direction enum values"""
        assert Direction.PICKUP.value == "pickup"
        assert Direction.DROPOFF.value == "dropoff"
    
    def test_direction_in_decoder(self):
        """Test direction in decoder initialization"""
        decoder = SplitDecoder(direction=Direction.PICKUP)
        assert decoder.direction == Direction.PICKUP
        
        decoder = SplitDecoder(direction=Direction.DROPOFF)
        assert decoder.direction == Direction.DROPOFF


class TestTrip:
    """Test Trip dataclass"""
    
    def test_trip_creation(self):
        """Test creating a trip"""
        trip = Trip(
            start_idx=0,
            end_idx=2,
            cost=45.5,
            sw_count=2,
            so_count=1,
            is_feasible=True
        )
        
        assert trip.start_idx == 0
        assert trip.end_idx == 2
        assert trip.cost == 45.5
        assert trip.sw_count == 2
        assert trip.so_count == 1
        assert trip.is_feasible == True
        assert trip.time_window_violations == 0
    
    def test_trip_with_violations(self):
        """Test trip with time window violations"""
        trip = Trip(
            start_idx=0,
            end_idx=1,
            cost=30.0,
            sw_count=1,
            so_count=1,
            is_feasible=True,
            time_window_violations=1,
            departure_time=440  # 07:20
        )
        
        assert trip.time_window_violations == 1
        assert trip.departure_time == 440


class TestBackwardScheduling:
    """Test backward scheduling calculations"""
    
    @pytest.fixture
    def decoder(self):
        return SplitDecoder(
            sw_capacity=4,
            so_capacity=5,
            use_time_windows=True,
            direction=Direction.PICKUP,
            target_time=540,  # 09:00
            offset_minutes=10
        )
    
    def test_target_arrival_time(self, decoder):
        """Test target arrival time calculation"""
        time_windows = {
            "Sw1": (480, 540),  # latest = 540
            "Sw2": (510, 555)   # latest = 555
        }
        decoder.time_windows = time_windows
        
        target = decoder._get_target_arrival_time(["Sw1", "Sw2"], "D.Kampus")
        
        # Should use the latest time window (555)
        assert target == 555
    
    def test_minutes_to_time(self, decoder):
        """Test minutes to time string conversion"""
        assert decoder._minutes_to_time(540) == "09:00"
        assert decoder._minutes_to_time(480) == "08:00"
        assert decoder._minutes_to_time(0) == "00:00"
        assert decoder._minutes_to_time(720) == "12:00"


class TestForwardScheduling:
    """Test forward scheduling for dropoff"""
    
    def test_target_departure_time(self):
        """Test target departure time calculation"""
        decoder = SplitDecoder(
            use_time_windows=True,
            direction=Direction.DROPOFF,
            target_time=480
        )
        
        time_windows = {
            "Sw1": (480, 540),  # earliest = 480
            "Sw2": (450, 510)   # earliest = 450
        }
        decoder.time_windows = time_windows
        
        target = decoder._get_target_departure_time(["Sw1", "Sw2"], "D.Kampus")
        
        # Should use the earliest time window (450)
        assert target == 450


class TestIntegration:
    """Integration tests"""
    
    def test_full_cvrptw_scenario(self):
        """Test complete CVRPTW scenario"""
        depot = "D.Kampus"
        
        # Realistic scenario: 5 students, all need to be at school by 09:00
        giant_tour = ["Sw1", "Sw2", "Sw3", "So1", "So2"]
        
        distance_matrix = {
            "D.Kampus": {"Sw1": 15, "Sw2": 20, "Sw3": 25, "So1": 30, "So2": 35},
            "Sw1": {"D.Kampus": 15, "Sw2": 8, "Sw3": 12, "So1": 18, "So2": 22},
            "Sw2": {"D.Kampus": 20, "Sw1": 8, "Sw3": 6, "So1": 14, "So2": 18},
            "Sw3": {"D.Kampus": 25, "Sw1": 12, "Sw2": 6, "So1": 8, "So2": 12},
            "So1": {"D.Kampus": 30, "Sw1": 18, "Sw2": 14, "Sw3": 8, "So2": 6},
            "So2": {"D.Kampus": 35, "Sw1": 22, "Sw2": 18, "Sw3": 12, "So1": 6}
        }
        
        demands = {
            "Sw1": (1, 0), "Sw2": (1, 0), "Sw3": (1, 0),
            "So1": (0, 1), "So2": (0, 1)
        }
        
        # All students need to arrive by 09:00
        time_windows = {
            "Sw1": (510, 540), "Sw2": (510, 540), "Sw3": (510, 540),
            "So1": (510, 540), "So2": (510, 540)
        }
        
        result = decode_with_time_windows(
            giant_tour=giant_tour,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            time_windows=time_windows,
            direction=Direction.PICKUP,
            target_time=540,
            offset_minutes=10
        )
        
        # Verify result structure
        assert "routes" in result
        assert "total_cost" in result
        assert "num_vehicles" in result
        assert "time_window_violations" in result
        assert "detailed_routes" in result
        
        # All students should be assigned
        total_students = sum(len(route["locations"]) for route in result["detailed_routes"])
        assert total_students == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
