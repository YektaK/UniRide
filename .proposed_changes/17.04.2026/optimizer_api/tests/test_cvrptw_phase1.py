"""
Tests for CVRPTW Phase 1 - Data Models and Time Window Extraction

Run with: pytest test_cvrptw_phase1.py -v
"""

import pytest
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import (
    StudentNode, Direction, TimeWindow, OptimizationRequest,
    OptimizationResponse, LocationNode, WeeklyScheduleEntry
)
from utils.time_window_extractor import (
    TimeWindowExtractor, TimeWindow as TWExtractor,
    weekly_schedule_to_optimization_input
)


class TestTimeWindow:
    """Test TimeWindow model"""
    
    def test_time_window_creation(self):
        """Test basic time window creation"""
        tw = TimeWindow(earliest=510, latest=540)  # 08:30 - 09:00
        assert tw.earliest == 510
        assert tw.latest == 540
    
    def test_from_time_string(self):
        """Test creating time window from HH:MM string"""
        tw = TimeWindow.from_time_string("09:00", window_minutes=30)
        assert tw.earliest == 525  # 08:45
        assert tw.latest == 555    # 09:15
    
    def test_from_time_string_small_window(self):
        """Test time window with small window size"""
        tw = TimeWindow.from_time_string("09:00", window_minutes=10)
        assert tw.earliest == 535  # 08:55
        assert tw.latest == 545    # 09:05
    
    def test_to_time_string(self):
        """Test converting time window to strings"""
        tw = TimeWindow(earliest=510, latest=540)
        earliest, latest = tw.to_time_string()
        assert earliest == "08:30"
        assert latest == "09:00"


class TestStudentNode:
    """Test StudentNode with CVRPTW fields"""
    
    def test_basic_student(self):
        """Test basic student creation"""
        student = StudentNode(
            id="student_1",
            location_code="Sw1",
            disability_type="Sw"
        )
        assert student.id == "student_1"
        assert student.pickup_time is None
        assert student.dropoff_time is None
    
    def test_student_with_time_windows(self):
        """Test student with pickup/dropoff times"""
        student = StudentNode(
            id="student_1",
            location_code="Sw1",
            disability_type="Sw",
            pickup_time="09:00",
            dropoff_time="14:00",
            direction=Direction.PICKUP
        )
        assert student.pickup_time == "09:00"
        assert student.dropoff_time == "14:00"
        assert student.direction == Direction.PICKUP
    
    def test_time_format_validation_valid(self):
        """Test valid time format validation"""
        student = StudentNode(
            id="student_1",
            location_code="Sw1",
            pickup_time="09:00"
        )
        assert student.pickup_time == "09:00"
    
    def test_time_format_validation_invalid(self):
        """Test invalid time format raises error"""
        with pytest.raises(ValueError):
            StudentNode(
                id="student_1",
                location_code="Sw1",
                pickup_time="25:00"  # Invalid hour
            )
    
    def test_get_time_window_pickup(self):
        """Test getting time window for pickup"""
        student = StudentNode(
            id="student_1",
            location_code="Sw1",
            pickup_time="09:00"
        )
        tw = student.get_time_window(Direction.PICKUP)
        assert tw is not None
        assert tw.earliest == 525  # 08:45
        assert tw.latest == 555    # 09:15
    
    def test_get_time_window_dropoff(self):
        """Test getting time window for dropoff"""
        student = StudentNode(
            id="student_1",
            location_code="Sw1",
            dropoff_time="14:00"
        )
        tw = student.get_time_window(Direction.DROPOFF)
        assert tw is not None
        assert tw.earliest == 825  # 13:45
        assert tw.latest == 855    # 14:15


class TestOptimizationRequest:
    """Test OptimizationRequest with CVRPTW fields"""
    
    def test_basic_request(self):
        """Test basic optimization request"""
        request = OptimizationRequest(
            algorithm="ga_split",
            students=[
                StudentNode(id="s1", location_code="Sw1", disability_type="Sw")
            ],
            depot=LocationNode(id="D.Kampus", lat=0, lng=0)
        )
        assert request.direction == Direction.PICKUP
        assert request.use_time_windows == False
    
    def test_cvrptw_request(self):
        """Test CVRPTW optimization request"""
        request = OptimizationRequest(
            algorithm="ga_split",
            students=[
                StudentNode(
                    id="s1", 
                    location_code="Sw1", 
                    disability_type="Sw",
                    pickup_time="09:00"
                )
            ],
            depot=LocationNode(id="D.Kampus", lat=0, lng=0),
            direction=Direction.PICKUP,
            use_time_windows=True,
            time_window_size=30,
            offset_minutes=10
        )
        assert request.use_time_windows == True
        assert request.direction == Direction.PICKUP
        assert request.offset_minutes == 10
    
    def test_get_time_windows(self):
        """Test extracting time windows from request"""
        request = OptimizationRequest(
            algorithm="ga_split",
            students=[
                StudentNode(
                    id="s1", 
                    location_code="Sw1", 
                    disability_type="Sw",
                    pickup_time="09:00"
                ),
                StudentNode(
                    id="s2", 
                    location_code="So1", 
                    disability_type="So",
                    pickup_time="10:00"
                )
            ],
            depot=LocationNode(id="D.Kampus", lat=0, lng=0),
            direction=Direction.PICKUP,
            use_time_windows=True
        )
        
        time_windows = request.get_time_windows()
        assert "Sw1" in time_windows
        assert "So1" in time_windows
    
    def test_global_target_time(self):
        """Test using global target time for students without specific times"""
        request = OptimizationRequest(
            algorithm="ga_split",
            students=[
                StudentNode(id="s1", location_code="Sw1", disability_type="Sw"),
                StudentNode(id="s2", location_code="So1", disability_type="So")
            ],
            depot=LocationNode(id="D.Kampus", lat=0, lng=0),
            use_time_windows=True,
            target_time="09:00"
        )
        
        time_windows = request.get_time_windows()
        assert len(time_windows) == 2


class TestTimeWindowExtractor:
    """Test TimeWindowExtractor utility"""
    
    def test_parse_time(self):
        """Test time parsing"""
        extractor = TimeWindowExtractor()
        assert extractor.parse_time("09:00") == 540
        assert extractor.parse_time("00:00") == 0
        assert extractor.parse_time("23:59") == 1439
    
    def test_round_up_to_hour(self):
        """Test rounding up to next hour"""
        extractor = TimeWindowExtractor()
        assert extractor.round_up_to_hour(540) == 540   # 09:00 -> 09:00
        assert extractor.round_up_to_hour(590) == 600   # 09:50 -> 10:00
        assert extractor.round_up_to_hour(890) == 900   # 14:50 -> 15:00
    
    def test_extract_pickup(self):
        """Test extracting time window for pickup"""
        extractor = TimeWindowExtractor(window_minutes=30)
        entry = {
            "startTime": "09:00",
            "endTime": "14:00"
        }
        
        tw = extractor.extract(entry, "pickup")
        assert tw.earliest == 510  # 08:30
        assert tw.latest == 540    # 09:00
    
    def test_extract_dropoff(self):
        """Test extracting time window for dropoff"""
        extractor = TimeWindowExtractor(window_minutes=30)
        entry = {
            "startTime": "09:00",
            "endTime": "14:00"
        }
        
        tw = extractor.extract(entry, "dropoff")
        assert tw.earliest == 840  # 14:00 (already on the hour)
        assert tw.latest == 870    # 14:30
    
    def test_extract_dropoff_rounded(self):
        """Test extracting dropoff time window with rounding"""
        extractor = TimeWindowExtractor(window_minutes=30)
        entry = {
            "startTime": "09:00",
            "endTime": "10:50"  # Should round to 11:00
        }
        
        tw = extractor.extract(entry, "dropoff")
        assert tw.earliest == 660  # 11:00
        assert tw.latest == 690    # 11:30
    
    def test_calculate_departure_time(self):
        """Test backward scheduling calculation"""
        extractor = TimeWindowExtractor()
        
        # Target arrival 09:00, tour 90 min, offset 10 min
        departure = extractor.calculate_departure_time(
            arrival_target=540,
            tour_duration=90,
            offset=10
        )
        assert departure == 440  # 07:20
    
    def test_get_day_from_date(self):
        """Test getting day name from date"""
        extractor = TimeWindowExtractor()
        
        assert extractor.get_day_from_date("2026-03-30") == "monday"
        assert extractor.get_day_from_date("2026-03-31") == "tuesday"
        assert extractor.get_day_from_date("2026-04-01") == "wednesday"


class TestWeeklyScheduleEntry:
    """Test WeeklyScheduleEntry model"""
    
    def test_entry_creation(self):
        """Test creating schedule entry"""
        entry = WeeklyScheduleEntry(
            id="entry_001",
            dayOfWeek="monday",
            startTime="09:00",
            endTime="14:00"
        )
        assert entry.dayOfWeek == "monday"
        assert entry.startTime == "09:00"
    
    def test_get_pickup_time_window(self):
        """Test getting pickup time window from entry"""
        entry = WeeklyScheduleEntry(
            id="entry_001",
            dayOfWeek="monday",
            startTime="09:00",
            endTime="14:00"
        )
        
        tw = entry.get_pickup_time_window(window_minutes=30)
        # Window is centered on time: 09:00 ± 15 min
        assert tw.earliest == 525  # 08:45 (09:00 - 15)
        assert tw.latest == 555    # 09:15 (09:00 + 15)
    
    def test_get_dropoff_time_window(self):
        """Test getting dropoff time window with rounding"""
        entry = WeeklyScheduleEntry(
            id="entry_001",
            dayOfWeek="monday",
            startTime="09:00",
            endTime="10:50"
        )
        
        tw = entry.get_dropoff_time_window(window_minutes=30)
        # 10:50 rounded up to 11:00, window centered: 11:00 ± 15
        assert tw.earliest == 645  # 10:45 (11:00 - 15)
        assert tw.latest == 675    # 11:15 (11:00 + 15)


class TestDirection:
    """Test Direction enum"""
    
    def test_direction_values(self):
        """Test direction enum values"""
        assert Direction.PICKUP.value == "pickup"
        assert Direction.DROPOFF.value == "dropoff"
    
    def test_direction_in_request(self):
        """Test using direction in request"""
        request = OptimizationRequest(
            algorithm="ga_split",
            students=[],
            depot=LocationNode(id="D.Kampus", lat=0, lng=0),
            direction=Direction.DROPOFF
        )
        assert request.direction == Direction.DROPOFF


# Integration test
class TestIntegration:
    """Integration tests for CVRPTW Phase 1"""
    
    def test_full_flow(self):
        """Test full flow from schedule to optimization request"""
        # 1. Create schedule entries (simulating Supabase data)
        schedules = [
            {
                "user_id": "user_1",
                "entries": [
                    {
                        "id": "entry_1",
                        "dayOfWeek": "monday",
                        "startTime": "09:00",
                        "endTime": "14:00"
                    }
                ]
            }
        ]
        
        users = {
            "user_1": {
                "location_code": "Sw1",
                "disability_type": "Sw",
                "name": "Test Student"
            }
        }
        
        # 2. Convert to optimization input
        result = weekly_schedule_to_optimization_input(
            schedules=schedules,
            users=users,
            target_date="2026-03-30",  # Monday
            direction="pickup"
        )
        
        # 3. Verify results
        assert len(result["students"]) == 1
        assert result["students"][0]["location_code"] == "Sw1"
        assert result["students"][0]["pickup_time"] == "09:00"
        assert result["target_day"] == "monday"
        assert result["direction"] == "pickup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
