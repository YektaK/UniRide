"""
Unit Tests for IE Resource Profiler

Test scenarios based on IE_RESOURCE_MODEL.md specifications
"""

import unittest
from datetime import datetime
from typing import List

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.resource_profiler import (
    ResourceProfiler, ResourceBlock, HourlyDemand,
    Bottleneck, TimeShiftSuggestion,
    minutes_to_time_str, time_str_to_minutes
)
from models.schemas import StudentNode, VehicleConfig


class TestResourceProfiler(unittest.TestCase):
    """Test cases for ResourceProfiler class"""

    def setUp(self):
        """Set up test fixtures"""
        self.profiler = ResourceProfiler(
            standard_sw_capacity=4,
            standard_so_capacity=5,
            max_tour_duration=120,
            cooldown_minutes=15
        )

    def test_initialization(self):
        """Test profiler initialization"""
        self.assertEqual(self.profiler.standard_sw_cap, 4)
        self.assertEqual(self.profiler.standard_so_cap, 5)
        self.assertEqual(self.profiler.max_tour_duration, 120)
        self.assertEqual(self.profiler.cooldown, 15)

    def test_calculate_standard_vehicle_needs_all_sw(self):
        """Test standard vehicle needs calculation - all Sw students"""
        students = [
            StudentNode(
                id=f"sw_{i}",
                name=f"Sw Student {i}",
                location_code=f"Sw{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="Sw"
            )
            for i in range(9)  # 9 Sw students
        ]

        result = self.profiler.calculate_standard_vehicle_needs(students)

        self.assertEqual(result['total_students'], 9)
        self.assertEqual(result['sw_count'], 9)
        self.assertEqual(result['so_count'], 0)
        # 9 Sw / 4 per vehicle = 3 vehicles
        self.assertEqual(result['standard_vehicles_needed'], 3)
        self.assertEqual(result['by_capacity']['by_sw'], 3)
        self.assertEqual(result['by_capacity']['by_so'], 0)

    def test_calculate_standard_vehicle_needs_all_so(self):
        """Test standard vehicle needs calculation - all So students"""
        students = [
            StudentNode(
                id=f"so_{i}",
                name=f"So Student {i}",
                location_code=f"So{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="So"
            )
            for i in range(10)  # 10 So students
        ]

        result = self.profiler.calculate_standard_vehicle_needs(students)

        self.assertEqual(result['total_students'], 10)
        self.assertEqual(result['sw_count'], 0)
        self.assertEqual(result['so_count'], 10)
        # 10 So / 5 per vehicle = 2 vehicles
        self.assertEqual(result['standard_vehicles_needed'], 2)
        self.assertEqual(result['by_capacity']['by_sw'], 0)
        self.assertEqual(result['by_capacity']['by_so'], 2)

    def test_calculate_standard_vehicle_needs_mixed(self):
        """Test standard vehicle needs calculation - mixed Sw/So"""
        students = []
        # 8 Sw students
        for i in range(8):
            students.append(StudentNode(
                id=f"sw_{i}",
                name=f"Sw Student {i}",
                location_code=f"Sw{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="Sw"
            ))
        # 10 So students
        for i in range(10):
            students.append(StudentNode(
                id=f"so_{i}",
                name=f"So Student {i}",
                location_code=f"So{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="So"
            ))

        result = self.profiler.calculate_standard_vehicle_needs(students)

        self.assertEqual(result['total_students'], 18)
        self.assertEqual(result['sw_count'], 8)
        self.assertEqual(result['so_count'], 10)
        # 8 Sw / 4 = 2 vehicles, 10 So / 5 = 2 vehicles
        # max(2, 2) = 2 vehicles
        self.assertEqual(result['standard_vehicles_needed'], 2)
        self.assertEqual(result['by_capacity']['by_sw'], 2)
        self.assertEqual(result['by_capacity']['by_so'], 2)

    def test_calculate_standard_vehicle_needs_imbalanced(self):
        """Test with imbalanced Sw/So requiring more vehicles for Sw"""
        students = []
        # 12 Sw students (needs 3 vehicles)
        for i in range(12):
            students.append(StudentNode(
                id=f"sw_{i}",
                name=f"Sw Student {i}",
                location_code=f"Sw{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="Sw"
            ))
        # 5 So students (needs 1 vehicle)
        for i in range(5):
            students.append(StudentNode(
                id=f"so_{i}",
                name=f"So Student {i}",
                location_code=f"So{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="So"
            ))

        result = self.profiler.calculate_standard_vehicle_needs(students)

        # Sw needs 3 vehicles (12/4), So needs 1 (5/5)
        self.assertEqual(result['standard_vehicles_needed'], 3)


class TestHourlyDemand(unittest.TestCase):
    """Test cases for hourly demand generation"""

    def setUp(self):
        self.profiler = ResourceProfiler()

    def test_generate_hourly_demand_empty(self):
        """Test with no students"""
        result = self.profiler.generate_hourly_demand([], {}, {})

        # Should return all hours with zero demand
        self.assertIn("08:00", result)
        self.assertIn("09:00", result)
        self.assertEqual(result["08:00"].total_pickup, 0)
        self.assertEqual(result["08:00"].total_dropoff, 0)

    def test_generate_hourly_demand_pickup_only(self):
        """Test pickup demand only"""
        students = [
            StudentNode(
                id="s1",
                name="Student 1",
                location_code="Loc1",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="Sw"
            ),
            StudentNode(
                id="s2",
                name="Student 2",
                location_code="Loc2",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="So"
            ),
        ]

        pickup_times = {
            "s1": "08:30",  # Sw at 08:30
            "s2": "09:15",  # So at 09:15
        }

        result = self.profiler.generate_hourly_demand(students, pickup_times, {})

        self.assertEqual(result["08:00"].pickup_sw, 1)
        self.assertEqual(result["08:00"].pickup_so, 0)
        self.assertEqual(result["09:00"].pickup_sw, 0)
        self.assertEqual(result["09:00"].pickup_so, 1)

    def test_generate_hourly_demand_both_directions(self):
        """Test both pickup and dropoff demand"""
        students = [
            StudentNode(
                id="s1",
                name="Student 1",
                location_code="Loc1",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="Sw"
            ),
            StudentNode(
                id="s2",
                name="Student 2",
                location_code="Loc2",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="So"
            ),
        ]

        pickup_times = {"s1": "08:00", "s2": "08:00"}
        dropoff_times = {"s1": "17:00", "s2": "17:00"}

        result = self.profiler.generate_hourly_demand(students, pickup_times, dropoff_times)

        # 08:00 - both pickup
        self.assertEqual(result["08:00"].pickup_sw, 1)
        self.assertEqual(result["08:00"].pickup_so, 1)
        self.assertEqual(result["08:00"].dropoff_sw, 0)
        self.assertEqual(result["08:00"].dropoff_so, 0)

        # 17:00 - both dropoff
        self.assertEqual(result["17:00"].pickup_sw, 0)
        self.assertEqual(result["17:00"].pickup_so, 0)
        self.assertEqual(result["17:00"].dropoff_sw, 1)
        self.assertEqual(result["17:00"].dropoff_so, 1)


class TestBottleneckIdentification(unittest.TestCase):
    """Test cases for bottleneck detection"""

    def setUp(self):
        self.profiler = ResourceProfiler(
            standard_sw_capacity=4,
            standard_so_capacity=5
        )

        # Create 2 standard vehicles
        self.available_vehicles = [
            VehicleConfig(vehicle_id="v1", sw_capacity=4, so_capacity=5),
            VehicleConfig(vehicle_id="v2", sw_capacity=4, so_capacity=5),
        ]

    def test_no_bottleneck(self):
        """Test when capacity is sufficient"""
        hourly_demand = {
            "08:00": HourlyDemand(hour="08:00", pickup_sw=4, pickup_so=5),
            "09:00": HourlyDemand(hour="09:00", pickup_sw=3, pickup_so=4),
        }

        bottlenecks = self.profiler.identify_bottlenecks(
            hourly_demand, self.available_vehicles, 'pickup'
        )

        self.assertEqual(len(bottlenecks), 0)

    def test_bottleneck_infeasible(self):
        """Test infeasible bottleneck detection"""
        # 10 Sw students but only 8 Sw capacity (2 vehicles x 4)
        hourly_demand = {
            "08:00": HourlyDemand(hour="08:00", pickup_sw=10, pickup_so=5),
        }

        bottlenecks = self.profiler.identify_bottlenecks(
            hourly_demand, self.available_vehicles, 'pickup'
        )

        self.assertEqual(len(bottlenecks), 1)
        self.assertEqual(bottlenecks[0].type, 'infeasible')
        self.assertEqual(bottlenecks[0].severity, 'high')
        self.assertIn("08:00", bottlenecks[0].hour)

    def test_bottleneck_low_efficiency(self):
        """Test low efficiency bottleneck detection"""
        # Very few students = low utilization
        hourly_demand = {
            "08:00": HourlyDemand(hour="08:00", pickup_sw=1, pickup_so=1),
        }

        bottlenecks = self.profiler.identify_bottlenecks(
            hourly_demand, self.available_vehicles, 'pickup'
        )

        # Should detect low efficiency (< 50% utilization)
        low_eff = [b for b in bottlenecks if b.type == 'low_efficiency']
        self.assertEqual(len(low_eff), 1)


class TestDirectionalConflict(unittest.TestCase):
    """Test cases for directional blocking logic"""

    def setUp(self):
        self.profiler = ResourceProfiler(max_tour_duration=120)

    def test_no_conflict_different_vehicles(self):
        """Test no conflict for different vehicles"""
        pickup = ResourceBlock(
            vehicle_id="v1",
            start_time=8*60,  # 08:00
            end_time=10*60,   # 10:00
            direction='pickup'
        )
        dropoff = ResourceBlock(
            vehicle_id="v2",  # Different vehicle
            start_time=9*60,  # 09:00
            end_time=11*60,   # 11:00
            direction='dropoff'
        )

        # Should not conflict (different vehicles)
        conflict = self.profiler.check_directional_conflict(pickup, dropoff)
        self.assertFalse(conflict)

    def test_conflict_same_vehicle(self):
        """Test conflict detection for same vehicle"""
        pickup = ResourceBlock(
            vehicle_id="v1",
            start_time=8*60,   # 08:00
            end_time=10*60,    # 10:00 (plus cooldown)
            direction='pickup'
        )
        dropoff = ResourceBlock(
            vehicle_id="v1",   # Same vehicle
            start_time=9*60,   # 09:00 (overlaps with pickup)
            end_time=11*60,    # 11:00
            direction='dropoff'
        )

        conflict = self.profiler.check_directional_conflict(pickup, dropoff)
        self.assertTrue(conflict)

    def test_no_conflict_separate_times(self):
        """Test no conflict when times don't overlap"""
        pickup = ResourceBlock(
            vehicle_id="v1",
            start_time=8*60,   # 08:00
            end_time=10*60,    # 10:00
            direction='pickup'
        )
        dropoff = ResourceBlock(
            vehicle_id="v1",   # Same vehicle
            start_time=11*60,  # 11:00 (after pickup ends)
            end_time=13*60,    # 13:00
            direction='dropoff'
        )

        conflict = self.profiler.check_directional_conflict(pickup, dropoff)
        self.assertFalse(conflict)


class TestResourceBlocks(unittest.TestCase):
    """Test cases for resource block calculation"""

    def setUp(self):
        self.profiler = ResourceProfiler(max_tour_duration=120, cooldown_minutes=15)

    def test_calculate_pickup_blocks(self):
        """Test pickup block calculation"""
        routes = [
            {
                'vehicle_id': 'v1',
                'students': [
                    {'id': 's1', 'disability_type': 'Sw'},
                    {'id': 's2', 'disability_type': 'So'},
                ]
            }
        ]

        blocks = self.profiler.calculate_resource_blocks(
            routes, 'pickup', {'v1': '09:00'}
        )

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].vehicle_id, 'v1')
        self.assertEqual(blocks[0].direction, 'pickup')
        # Pickup: T-120 to T (09:00 = 540 min)
        self.assertEqual(blocks[0].start_time, 540 - 120)  # 07:00
        self.assertEqual(blocks[0].end_time, 540 + 15)     # 09:15 (with cooldown)

    def test_calculate_dropoff_blocks(self):
        """Test dropoff block calculation"""
        routes = [
            {
                'vehicle_id': 'v1',
                'students': [{'id': 's1', 'disability_type': 'Sw'}]
            }
        ]

        blocks = self.profiler.calculate_resource_blocks(
            routes, 'dropoff', {'v1': '17:00'}
        )

        self.assertEqual(len(blocks), 1)
        # Dropoff: T to T+120 (17:00 = 1020 min)
        self.assertEqual(blocks[0].start_time, 1020)       # 17:00
        self.assertEqual(blocks[0].end_time, 1020 + 120 + 15)  # 19:15 (with cooldown)


class TestTimeShiftSuggestions(unittest.TestCase):
    """Test cases for time shift suggestions"""

    def setUp(self):
        self.profiler = ResourceProfiler(
            standard_sw_capacity=4,
            standard_so_capacity=5
        )

    def test_suggest_shifts_for_bottleneck(self):
        """Test shift suggestions for bottleneck hours"""
        hourly_demand = {
            "08:00": HourlyDemand(hour="08:00", pickup_sw=2, pickup_so=3),  # Normal
            "09:00": HourlyDemand(hour="09:00", pickup_sw=8, pickup_so=10), # Bottleneck (18 students!)
            "10:00": HourlyDemand(hour="10:00", pickup_sw=2, pickup_so=2),  # Available
        }

        suggestions = self.profiler.suggest_time_shifts(
            hourly_demand,
            bottleneck_hours=["09:00"]
        )

        # Should suggest shifting to 10:00
        self.assertTrue(any(s.suggested_time == "10:00" for s in suggestions))


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""

    def test_minutes_to_time_str(self):
        """Test minutes to time string conversion"""
        self.assertEqual(minutes_to_time_str(0), "00:00")
        self.assertEqual(minutes_to_time_str(60), "01:00")
        self.assertEqual(minutes_to_time_str(540), "09:00")
        self.assertEqual(minutes_to_time_str(1439), "23:59")

    def test_time_str_to_minutes(self):
        """Test time string to minutes conversion"""
        self.assertEqual(time_str_to_minutes("00:00"), 0)
        self.assertEqual(time_str_to_minutes("01:00"), 60)
        self.assertEqual(time_str_to_minutes("09:00"), 540)
        self.assertEqual(time_str_to_minutes("23:59"), 1439)


class TestIEReport(unittest.TestCase):
    """Test comprehensive IE report generation"""

    def setUp(self):
        self.profiler = ResourceProfiler()

    def test_generate_full_report(self):
        """Test full IE report generation"""
        students = [
            StudentNode(
                id=f"s_{i}",
                name=f"Student {i}",
                location_code=f"Loc{i}",
                coordinates={"lat": 40.84, "lng": 31.15},
                disability_type="Sw" if i < 5 else "So"
            )
            for i in range(10)
        ]

        vehicles = [
            VehicleConfig(vehicle_id="v1", sw_capacity=4, so_capacity=5),
            VehicleConfig(vehicle_id="v2", sw_capacity=4, so_capacity=5),
        ]

        pickup_times = {f"s_{i}": "08:00" for i in range(10)}
        dropoff_times = {f"s_{i}": "17:00" for i in range(10)}

        report = self.profiler.generate_ie_report(
            students, vehicles, pickup_times, dropoff_times
        )

        # Check report structure
        self.assertIn('summary', report)
        self.assertIn('standard_needs', report)
        self.assertIn('hourly_demand', report)
        self.assertIn('bottlenecks', report)
        self.assertIn('shift_suggestions', report)

        # Check summary
        self.assertEqual(report['summary']['total_students'], 10)
        self.assertEqual(report['summary']['available_vehicles'], 2)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
