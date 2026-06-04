"""
Time Window Extractor for CVRPTW
Converts weekly schedule entries to time windows for optimization

Version: 1.0.0
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class TimeWindow:
    """Time window in minutes from midnight"""
    earliest: int  # Earliest arrival time (minutes from midnight)
    latest: int    # Latest arrival time (minutes from midnight)
    
    def __post_init__(self):
        """Validate time window"""
        if self.earliest > self.latest:
            self.earliest, self.latest = self.latest, self.earliest
        self.earliest = max(0, min(self.earliest, 24 * 60))
        self.latest = max(0, min(self.latest, 24 * 60))
    
    def to_dict(self) -> Dict[str, int]:
        return {"earliest": self.earliest, "latest": self.latest}
    
    def to_time_strings(self) -> tuple:
        """Convert to (earliest_str, latest_str) in HH:MM format"""
        def to_str(minutes: int) -> str:
            h = minutes // 60
            m = minutes % 60
            return f"{h:02d}:{m:02d}"
        return to_str(self.earliest), to_str(self.latest)


class TimeWindowExtractor:
    """
    Extract time windows from weekly schedule entries.
    
    Handles two scenarios:
    1. PICKUP (Geliş): Student must arrive at school by class start time
       - Backward scheduling from startTime
       - Time window ends at startTime
    
    2. DROPOFF (Gidiş): Student leaves school after class ends
       - Forward scheduling from endTime (rounded up to next hour)
       - Time window starts at endTime
    """
    
    # Day name mappings
    DAY_NAMES = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    def __init__(self, window_minutes: int = 30):
        """
        Initialize extractor.
        
        Args:
            window_minutes: Default time window size in minutes
        """
        self.window_minutes = window_minutes
    
    def parse_time(self, time_str: str) -> int:
        """
        Parse time string to minutes from midnight.
        
        Args:
            time_str: Time in HH:MM format
            
        Returns:
            Minutes from midnight
        """
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 60 + minutes
        except (ValueError, IndexError):
            return 0
    
    def round_up_to_hour(self, minutes: int) -> int:
        """
        Round up to next full hour.
        
        Args:
            minutes: Minutes from midnight
            
        Returns:
            Rounded minutes
        """
        hours = minutes // 60
        remainder = minutes % 60
        if remainder > 0:
            return (hours + 1) * 60
        return minutes
    
    def extract(
        self, 
        entry: Dict, 
        direction: str = "pickup"
    ) -> Optional[TimeWindow]:
        """
        Extract time window from a schedule entry.
        
        Args:
            entry: Schedule entry dict with startTime, endTime
            direction: "pickup" or "dropoff"
            
        Returns:
            TimeWindow or None if invalid
        """
        if direction == "pickup":
            # For pickup: use startTime (class start)
            # Student must be at school BY startTime
            time_str = entry.get("startTime")
            if not time_str:
                return None
            
            target_minutes = self.parse_time(time_str)
            
            # Time window: arrive within window_minutes before start
            # latest = target time (no late arrival)
            # earliest = target - window (can arrive early)
            return TimeWindow(
                earliest=max(0, target_minutes - self.window_minutes),
                latest=target_minutes
            )
        
        else:  # dropoff
            # For dropoff: use endTime (class end)
            # Student leaves AFTER endTime (rounded up to next hour)
            time_str = entry.get("endTime")
            if not time_str:
                return None
            
            end_minutes = self.parse_time(time_str)
            
            # Round up to next full hour for departure
            departure_minutes = self.round_up_to_hour(end_minutes)
            
            # Time window: leave within window_minutes after departure time
            # earliest = departure time (can't leave before)
            # latest = departure + window (flexible)
            return TimeWindow(
                earliest=departure_minutes,
                latest=min(24 * 60, departure_minutes + self.window_minutes)
            )
    
    def extract_batch(
        self,
        entries: List[Dict],
        direction: str = "pickup",
        target_day: Optional[str] = None
    ) -> Dict[str, TimeWindow]:
        """
        Extract time windows from multiple entries.
        
        Args:
            entries: List of schedule entries
            direction: "pickup" or "dropoff"
            target_day: Filter by day of week (optional)
            
        Returns:
            Dict mapping entry_id -> TimeWindow
        """
        time_windows = {}
        
        for entry in entries:
            # Filter by day if specified
            if target_day:
                entry_day = entry.get("dayOfWeek", "").lower()
                if entry_day != target_day.lower():
                    continue
            
            entry_id = entry.get("id") or entry.get("user_id", str(hash(str(entry))))
            tw = self.extract(entry, direction)
            
            if tw:
                time_windows[entry_id] = tw
        
        return time_windows
    
    def get_day_from_date(self, date_str: str) -> str:
        """
        Get day of week from date string.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Day name (monday, tuesday, etc.)
        """
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            return date.strftime("%A").lower()
        except ValueError:
            return ""
    
    def calculate_departure_time(
        self,
        arrival_target: int,
        tour_duration: int,
        offset: int = 10
    ) -> int:
        """
        Calculate vehicle departure time using backward scheduling.
        
        Args:
            arrival_target: Target arrival time (minutes from midnight)
            tour_duration: Estimated tour duration (minutes)
            offset: Buffer time to add (minutes)
            
        Returns:
            Departure time in minutes from midnight
        """
        departure = arrival_target - tour_duration - offset
        return max(0, departure)
    
    def calculate_arrival_times(
        self,
        departure_time: int,
        locations: List[str],
        travel_times: Dict[str, Dict[str, float]]
    ) -> Dict[str, int]:
        """
        Calculate arrival time at each location using forward scheduling.
        
        Args:
            departure_time: Vehicle departure time (minutes from midnight)
            locations: List of locations in route order
            travel_times: Dict of {from: {to: duration}}
            
        Returns:
            Dict mapping location -> arrival time
        """
        arrival_times = {}
        current_time = departure_time
        
        for i, loc in enumerate(locations):
            arrival_times[loc] = current_time
            
            if i < len(locations) - 1:
                next_loc = locations[i + 1]
                travel = travel_times.get(loc, {}).get(next_loc, 15.0)
                current_time += int(travel)
        
        return arrival_times


def weekly_schedule_to_optimization_input(
    schedules: List[Dict],
    users: Dict[str, Dict],
    target_date: str,
    direction: str = "pickup"
) -> Dict:
    """
    Convert weekly schedules to optimization input format.
    
    This is the main bridge between Supabase data and the optimizer.
    
    Args:
        schedules: List of weekly schedule dicts from Supabase
            [{user_id, entries: [{dayOfWeek, startTime, endTime, ...}]}]
        users: Dict mapping user_id -> user info
            {user_id: {location_code, disability_type, name}}
        target_date: Target date (YYYY-MM-DD)
        direction: "pickup" or "dropoff"
        
    Returns:
        Dict with students list and time_windows
    """
    extractor = TimeWindowExtractor()
    target_day = extractor.get_day_from_date(target_date)
    
    students = []
    time_windows = {}
    
    for schedule in schedules:
        user_id = schedule.get("user_id")
        entries = schedule.get("entries", [])
        
        # Get user info
        user_info = users.get(user_id, {})
        
        # Find entry for target day
        for entry in entries:
            if entry.get("dayOfWeek", "").lower() == target_day:
                # Extract time window
                tw = extractor.extract(entry, direction)
                
                location_code = user_info.get("location_code", "So1")
                
                student = {
                    "id": user_id,
                    "name": user_info.get("name", ""),
                    "location_code": location_code,
                    "disability_type": user_info.get("disability_type", "So"),
                    "pickup_time": entry.get("startTime") if direction == "pickup" else None,
                    "dropoff_time": entry.get("endTime") if direction == "dropoff" else None,
                    "direction": direction
                }
                
                students.append(student)
                
                if tw:
                    time_windows[location_code] = tw.to_dict()
                
                break  # One entry per day per user
    
    return {
        "students": students,
        "time_windows": time_windows,
        "target_day": target_day,
        "direction": direction
    }


# Example usage and testing
if __name__ == "__main__":
    # Test data
    test_entry = {
        "id": "entry_001",
        "dayOfWeek": "monday",
        "startTime": "09:00",
        "endTime": "14:00",
        "location": "Dogus Kampus",
        "courseName": "Ders Programı"
    }
    
    extractor = TimeWindowExtractor(window_minutes=30)
    
    # Test pickup extraction
    pickup_tw = extractor.extract(test_entry, "pickup")
    print(f"Pickup Time Window: {pickup_tw.to_time_strings()}")
    # Expected: ('08:30', '09:00')
    
    # Test dropoff extraction
    dropoff_tw = extractor.extract(test_entry, "dropoff")
    print(f"Dropoff Time Window: {dropoff_tw.to_time_strings()}")
    # Expected: ('14:00', '14:30') - rounded up from 14:00
    
    # Test backward scheduling
    departure = extractor.calculate_departure_time(
        arrival_target=540,  # 09:00
        tour_duration=90,
        offset=10
    )
    print(f"Departure time: {departure // 60:02d}:{departure % 60:02d}")
    # Expected: 07:20
