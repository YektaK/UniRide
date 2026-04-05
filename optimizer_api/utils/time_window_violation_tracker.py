"""
Time Window Violation Tracker for CVRPTW
Tracks and reports time window violations in vehicle routes.

This module provides detailed analysis of time window compliance,
including violation types, severity, and suggested corrections.

Version: 1.0.0
Author: Super Z AI Assistant
Date: 2026-04-04
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ViolationType(str, Enum):
    """Types of time window violations"""
    EARLY_ARRIVAL = "early_arrival"      # Arrived before window opens
    LATE_ARRIVAL = "late_arrival"        # Arrived after window closes
    NO_WINDOW = "no_window"              # Location has no time window defined
    WITHIN_WINDOW = "within_window"      # Arrived within time window (no violation)


@dataclass
class TimeWindowViolation:
    """Single time window violation record"""
    location: str
    location_name: str = ""
    arrival_time: float = 0.0  # Minutes from start
    earliest: float = 0.0      # Window start
    latest: float = 0.0        # Window end
    violation_type: ViolationType = ViolationType.WITHIN_WINDOW
    violation_amount: float = 0.0  # Minutes of violation
    severity: str = "none"     # none, minor, moderate, severe
    vehicle_id: str = ""
    route_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "location": self.location,
            "location_name": self.location_name,
            "arrival_time": self.arrival_time,
            "earliest": self.earliest,
            "latest": self.latest,
            "violation_type": self.violation_type.value,
            "violation_amount": self.violation_amount,
            "severity": self.severity,
            "vehicle_id": self.vehicle_id,
            "route_index": self.route_index
        }


@dataclass
class ViolationReport:
    """Complete violation report for a route or solution"""
    total_violations: int = 0
    early_arrivals: int = 0
    late_arrivals: int = 0
    no_window_count: int = 0
    total_violation_minutes: float = 0.0  # Raw violation minutes (sum of actual delays/early arrivals)
    total_penalty: float = 0.0            # Weighted penalty score (minutes * penalty weights)
    compliance_rate: float = 100.0  # Percentage of on-time arrivals
    violations: List[TimeWindowViolation] = field(default_factory=list)
    route_duration: float = 0.0
    vehicle_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_violations": self.total_violations,
            "early_arrivals": self.early_arrivals,
            "late_arrivals": self.late_arrivals,
            "no_window_count": self.no_window_count,
            "total_violation_minutes": self.total_violation_minutes,
            "total_penalty": self.total_penalty,
            "compliance_rate": self.compliance_rate,
            "num_locations": len(self.violations),
            "route_duration": self.route_duration,
            "vehicle_id": self.vehicle_id,
            "violations": [v.to_dict() for v in self.violations]
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        if self.total_violations == 0 and self.no_window_count == 0:
            return f"✅ No violations. Compliance: 100%"
        
        if self.total_violations == 0:
            return f"⚠️ No time violations, but {self.no_window_count} locations without time window defined."
        
        return (
            f"⚠️ {self.total_violations} violations detected:\n"
            f"   - Early arrivals: {self.early_arrivals}\n"
            f"   - Late arrivals: {self.late_arrivals}\n"
            f"   - No window defined: {self.no_window_count}\n"
            f"   - Total violation time: {self.total_violation_minutes:.1f} min\n"
            f"   - Total penalty score: {self.total_penalty:.1f}\n"
            f"   - Compliance rate: {self.compliance_rate:.1f}%"
        )


class TimeWindowViolationTracker:
    """
    Track and analyze time window violations in vehicle routes.
    
    Features:
    - Detect early/late arrivals
    - Calculate violation severity
    - Generate compliance reports
    - Suggest schedule adjustments
    
    Usage:
        tracker = TimeWindowViolationTracker(time_windows)
        report = tracker.analyze_route(route, distance_matrix, depot)
        print(report.get_summary())
    """
    
    # Severity thresholds (in minutes) used by severity classification:
    # minor: 1-5 minutes, moderate: 6-15 minutes, severe: > 15 minutes
    SEVERITY_THRESHOLDS = {
        "minor": 5,      # <= 5 minutes
        "moderate": 15   # <= 15 minutes, > 15 = severe
    }
    
    def __init__(
        self,
        time_windows: Dict[str, Tuple[float, float]],
        service_time: float = 5.0,  # Minutes spent at each location
        wait_penalty: float = 1.0,  # Penalty for waiting (early arrival)
        late_penalty: float = 10.0  # Penalty for late arrival
    ):
        """
        Initialize tracker.
        
        Args:
            time_windows: Dict mapping location -> (earliest, latest) in minutes
            service_time: Time spent at each location for pickup/dropoff
            wait_penalty: Penalty weight for early arrival (waiting)
            late_penalty: Penalty weight for late arrival
        """
        self.time_windows = time_windows
        self.service_time = service_time
        self.wait_penalty = wait_penalty
        self.late_penalty = late_penalty
    
    def set_time_windows(self, time_windows: Dict[str, Tuple[float, float]]):
        """Update time windows"""
        self.time_windows = time_windows
    
    def _get_severity(self, violation_minutes: float) -> str:
        """Determine violation severity"""
        abs_violation = abs(violation_minutes)
        
        if abs_violation == 0:
            return "none"
        elif abs_violation <= self.SEVERITY_THRESHOLDS["minor"]:
            return "minor"
        elif abs_violation <= self.SEVERITY_THRESHOLDS["moderate"]:
            return "moderate"
        else:
            return "severe"
    
    def _format_time(self, minutes: float) -> str:
        """Format minutes to HH:MM"""
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours:02d}:{mins:02d}"
    
    def analyze_route(
        self,
        route: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        depot: str,
        start_time: float = 0.0,
        vehicle_id: str = "",
        route_index: int = 0,
        location_names: Optional[Dict[str, str]] = None
    ) -> ViolationReport:
        """
        Analyze a single route for time window violations.
        
        Args:
            route: List of location codes in visit order
            distance_matrix: Travel time between locations
            depot: Starting/ending location
            start_time: Route start time (minutes from midnight)
            vehicle_id: Vehicle identifier
            route_index: Index of this route in the solution
            location_names: Optional mapping of location codes to names
        
        Returns:
            ViolationReport with detailed violation information
        """
        report = ViolationReport(vehicle_id=vehicle_id)
        current_time = start_time
        prev_location = depot
        
        for loc in route:
            if loc == depot:
                continue
            
            # Calculate arrival time
            if prev_location in distance_matrix and loc in distance_matrix[prev_location]:
                travel_time = distance_matrix[prev_location][loc]
            else:
                travel_time = 15.0  # Default travel time
            
            current_time += travel_time
            
            # Check time window
            if loc in self.time_windows:
                earliest, latest = self.time_windows[loc]
                
                if current_time < earliest:
                    # Early arrival - need to wait
                    violation = TimeWindowViolation(
                        location=loc,
                        location_name=location_names.get(loc, loc) if location_names else loc,
                        arrival_time=current_time,
                        earliest=earliest,
                        latest=latest,
                        violation_type=ViolationType.EARLY_ARRIVAL,
                        violation_amount=earliest - current_time,
                        severity=self._get_severity(earliest - current_time),
                        vehicle_id=vehicle_id,
                        route_index=route_index
                    )
                    report.violations.append(violation)
                    report.early_arrivals += 1
                    report.total_violation_minutes += (earliest - current_time)  # Raw minutes
                    report.total_penalty += (earliest - current_time) * self.wait_penalty  # Weighted
                    
                    # Wait until window opens
                    current_time = earliest
                    
                elif current_time > latest:
                    # Late arrival - violation
                    violation = TimeWindowViolation(
                        location=loc,
                        location_name=location_names.get(loc, loc) if location_names else loc,
                        arrival_time=current_time,
                        earliest=earliest,
                        latest=latest,
                        violation_type=ViolationType.LATE_ARRIVAL,
                        violation_amount=current_time - latest,
                        severity=self._get_severity(current_time - latest),
                        vehicle_id=vehicle_id,
                        route_index=route_index
                    )
                    report.violations.append(violation)
                    report.late_arrivals += 1
                    report.total_violation_minutes += (current_time - latest)  # Raw minutes
                    report.total_penalty += (current_time - latest) * self.late_penalty  # Weighted
                    
                else:
                    # Within window - no violation
                    violation = TimeWindowViolation(
                        location=loc,
                        location_name=location_names.get(loc, loc) if location_names else loc,
                        arrival_time=current_time,
                        earliest=earliest,
                        latest=latest,
                        violation_type=ViolationType.WITHIN_WINDOW,
                        violation_amount=0.0,
                        severity="none",
                        vehicle_id=vehicle_id,
                        route_index=route_index
                    )
                    report.violations.append(violation)
            else:
                # No time window defined
                violation = TimeWindowViolation(
                    location=loc,
                    location_name=location_names.get(loc, loc) if location_names else loc,
                    arrival_time=current_time,
                    violation_type=ViolationType.NO_WINDOW,
                    vehicle_id=vehicle_id,
                    route_index=route_index
                )
                report.violations.append(violation)
                report.no_window_count += 1
            
            # Add service time
            current_time += self.service_time
            prev_location = loc
        
        # Calculate return to depot
        if prev_location in distance_matrix and depot in distance_matrix[prev_location]:
            current_time += distance_matrix[prev_location][depot]
        
        report.route_duration = current_time - start_time
        report.total_violations = report.early_arrivals + report.late_arrivals
        
        # Calculate compliance rate
        total_checks = len([v for v in report.violations if v.violation_type != ViolationType.NO_WINDOW])
        if total_checks > 0:
            compliant = total_checks - report.total_violations
            report.compliance_rate = (compliant / total_checks) * 100
        
        return report
    
    def analyze_solution(
        self,
        routes: List[List[str]],
        distance_matrix: Dict[str, Dict[str, float]],
        depot: str,
        start_times: Optional[List[float]] = None,
        vehicle_ids: Optional[List[str]] = None,
        location_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple routes (full solution) for time window violations.
        
        Args:
            routes: List of routes (each route is a list of location codes)
            distance_matrix: Travel time between locations
            depot: Starting/ending location
            start_times: Optional start time for each vehicle
            vehicle_ids: Optional vehicle identifiers
            location_names: Optional mapping of location codes to names
        
        Returns:
            Dict with summary and per-route reports
        """
        if start_times is None:
            start_times = [0.0] * len(routes)
        
        if vehicle_ids is None:
            vehicle_ids = [f"Vehicle {i+1}" for i in range(len(routes))]
        
        route_reports = []
        total_violations = 0
        total_violation_minutes = 0.0
        total_penalty = 0.0
        total_locations = 0
        total_compliant = 0
        
        for i, route in enumerate(routes):
            report = self.analyze_route(
                route=route,
                distance_matrix=distance_matrix,
                depot=depot,
                start_time=start_times[i] if i < len(start_times) else 0.0,
                vehicle_id=vehicle_ids[i] if i < len(vehicle_ids) else f"Vehicle {i+1}",
                route_index=i,
                location_names=location_names
            )
            route_reports.append(report)
            
            total_violations += report.total_violations
            total_violation_minutes += report.total_violation_minutes
            total_penalty += report.total_penalty
            total_locations += len([v for v in report.violations if v.violation_type != ViolationType.NO_WINDOW])
            total_compliant += len([v for v in report.violations if v.violation_type == ViolationType.WITHIN_WINDOW])
        
        overall_compliance = (total_compliant / total_locations * 100) if total_locations > 0 else 100.0
        
        return {
            "summary": {
                "total_routes": len(routes),
                "total_violations": total_violations,
                "total_violation_minutes": total_violation_minutes,
                "total_penalty": total_penalty,
                "overall_compliance_rate": overall_compliance,
                "timestamp": datetime.now().isoformat()
            },
            "route_reports": [r.to_dict() for r in route_reports],
            "worst_routes": sorted(
                [(r.vehicle_id, r.total_violations, r.total_penalty) for r in route_reports],
                key=lambda x: x[2],
                reverse=True
            )[:5]  # Top 5 worst routes by penalty
        }
    
    def calculate_penalty(self, report: ViolationReport) -> float:
        """
        Calculate total penalty score for a route.
        
        Higher penalty = worse solution. Returns the pre-computed
        total_penalty field from the report (already calculated
        by analyze_route with the configured wait/late penalty weights).
        
        Args:
            report: ViolationReport from analyze_route
        
        Returns:
            Total penalty score
        """
        return report.total_penalty
    
    def suggest_improvements(
        self,
        report: ViolationReport,
        route: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        depot: str
    ) -> List[Dict[str, Any]]:
        """
        Suggest improvements to reduce time window violations.
        
        Args:
            report: ViolationReport from analyze_route
            route: Original route
            distance_matrix: Travel time between locations
            depot: Starting location
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        for violation in report.violations:
            if violation.violation_type == ViolationType.LATE_ARRIVAL:
                # Suggest moving this location earlier in route
                suggestion = {
                    "type": "reschedule",
                    "location": violation.location,
                    "current_arrival": self._format_time(violation.arrival_time),
                    "window_close": self._format_time(violation.latest),
                    "violation_minutes": violation.violation_amount,
                    "suggestion": f"Consider visiting {violation.location} earlier. "
                                  f"Currently arriving {violation.violation_amount:.0f} min late."
                }
                suggestions.append(suggestion)
            
            elif violation.violation_type == ViolationType.EARLY_ARRIVAL:
                # Early arrival means waiting - might be acceptable
                suggestion = {
                    "type": "wait",
                    "location": violation.location,
                    "current_arrival": self._format_time(violation.arrival_time),
                    "window_open": self._format_time(violation.earliest),
                    "wait_time": violation.violation_amount,
                    "suggestion": f"Arriving early at {violation.location}. "
                                  f"Need to wait {violation.violation_amount:.0f} min. "
                                  f"Consider departing later or adding more stops."
                }
                suggestions.append(suggestion)
        
        return suggestions


def create_tracker_from_students(
    students: List[Dict],
    window_size: int = 30,
    direction: str = "pickup"
) -> TimeWindowViolationTracker:
    """
    Create a tracker from student data.
    
    Args:
        students: List of student dicts with pickup_time/dropoff_time
        window_size: Size of time window in minutes
        direction: "pickup" or "dropoff"
    
    Returns:
        Configured TimeWindowViolationTracker
    """
    time_windows = {}
    time_key = "pickup_time" if direction == "pickup" else "dropoff_time"
    
    # Day boundaries (minutes from midnight)
    MINUTES_PER_DAY = 24 * 60
    
    for student in students:
        location = student.get("location_code", "")
        time_str = student.get(time_key, "")
        
        if location and time_str:
            try:
                parts = time_str.split(":")
                minutes = int(parts[0]) * 60 + int(parts[1])
                
                if direction == "pickup":
                    # Pickup: window ends at pickup time
                    earliest = max(0, minutes - window_size)  # Clamp to day start
                    latest = min(MINUTES_PER_DAY, minutes)     # Clamp to day end
                    time_windows[location] = (earliest, latest)
                else:
                    # Dropoff: window starts at dropoff time
                    earliest = max(0, minutes)                  # Clamp to day start
                    latest = min(MINUTES_PER_DAY, minutes + window_size)  # Clamp to day end
                    time_windows[location] = (earliest, latest)
            except (ValueError, IndexError):
                continue
    
    return TimeWindowViolationTracker(time_windows)


# Example usage
if __name__ == "__main__":
    # Test data
    time_windows = {
        "Loc1": (480, 510),   # 08:00 - 08:30
        "Loc2": (510, 540),   # 08:30 - 09:00
        "Loc3": (540, 570),   # 09:00 - 09:30
        "Loc4": (600, 630),   # 10:00 - 10:30
    }
    
    distance_matrix = {
        "Depot": {"Loc1": 20, "Loc2": 35, "Loc3": 45, "Loc4": 50, "Depot": 0},
        "Loc1": {"Depot": 20, "Loc2": 15, "Loc3": 25, "Loc4": 35, "Loc1": 0},
        "Loc2": {"Depot": 35, "Loc1": 15, "Loc3": 10, "Loc4": 25, "Loc2": 0},
        "Loc3": {"Depot": 45, "Loc1": 25, "Loc2": 10, "Loc4": 15, "Loc3": 0},
        "Loc4": {"Depot": 50, "Loc1": 35, "Loc2": 25, "Loc3": 15, "Loc4": 0},
    }
    
    # Create tracker
    tracker = TimeWindowViolationTracker(time_windows)
    
    # Test route 1: Well-timed
    route1 = ["Loc1", "Loc2", "Loc3", "Loc4"]
    report1 = tracker.analyze_route(route1, distance_matrix, "Depot", vehicle_id="V1")
    print("Route 1:", report1.get_summary())
    
    # Test route 2: Late arrivals
    route2 = ["Loc1", "Loc3", "Loc2", "Loc4"]  # Wrong order
    report2 = tracker.analyze_route(route2, distance_matrix, "Depot", vehicle_id="V2")
    print("\nRoute 2:", report2.get_summary())
    
    # Suggestions
    suggestions = tracker.suggest_improvements(report2, route2, distance_matrix, "Depot")
    print("\nSuggestions for Route 2:")
    for s in suggestions:
        print(f"  - {s['suggestion']}")
