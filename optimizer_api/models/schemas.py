from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

# --- Enums ---
class Direction(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"

class DisabilityType(str, Enum):
    SW = "Sw"
    SO = "So"

class OptimizationMode(str, Enum):
    BENCHMARK = "benchmark"
    SANDBOX = "sandbox"

class LocalSearchType(str, Enum):
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    HYBRID = "hybrid"

# --- Models ---
class LocationNode(BaseModel):
    id: str
    lat: float
    lng: float
    type: str = "So"

class StudentNode(BaseModel):
    id: str
    name: str = ""
    location_code: str
    coordinates: Optional[Dict[str, float]] = None
    disability_type: str = "So"
    pickup_time: Optional[str] = None
    dropoff_time: Optional[str] = None

class TimeWindow(BaseModel):
    earliest: int
    latest: int

class VehicleConfig(BaseModel):
    """Vehicle configuration for heterogeneous fleet support"""
    vehicle_id: str
    sw_capacity: int = 4
    so_capacity: int = 5
    cooldown_minutes: int = 15

class WeeklyScheduleEntry(BaseModel):
    id: str
    dayOfWeek: str
    startTime: str
    endTime: str
    location_code: Optional[str] = None

class WeeklyScheduleRequest(BaseModel):
    entries: List[WeeklyScheduleEntry]
    target_day: str
    direction: Direction

class RouteStep(BaseModel):
    location1: str
    location2: str
    duration: float
    distance: float = 0.0

class VehicleRoute(BaseModel):
    vehicle_id: str
    route_details: List[RouteStep]
    total_duration_minutes: float
    total_distance_km: float = 0.0
    sw_count: int = 0
    so_count: int = 0
    student_ids: List[str] = []
    departure_time: Optional[str] = None
    arrival_times: Optional[Dict[str, str]] = None

class BottleneckInfo(BaseModel):
    time: str
    type: str
    reason: str
    affected_students: Optional[List[str]] = None

class TimeShiftSuggestion(BaseModel):
    student_id: str
    current_time: str
    suggested_time: str
    savings_vehicles: float

class IEResponseData(BaseModel):
    standard_vehicles_needed: int = 0
    hourly_demand: Dict[str, Any] = {}
    bottlenecks: List[BottleneckInfo] = []
    time_shift_suggestions: List[TimeShiftSuggestion] = []

# --- Request / Response ---
class OptimizationRequest(BaseModel):
    algorithm: str = "ga_split"
    students: List[StudentNode]
    depot: LocationNode
    max_travel_time: int = 120
    sw_capacity: int = 4
    so_capacity: int = 5
    direction: Direction = Direction.PICKUP
    use_time_windows: bool = False
    target_time: Optional[str] = None
    offset_minutes: int = 15
    allow_time_shift: bool = False
    slack_window_minutes: int = 60
    vehicles: Optional[List[VehicleConfig]] = None
    mode: OptimizationMode = OptimizationMode.BENCHMARK
    local_search_type: Optional[str] = "two_opt"
    use_sota_engine: bool = False
    ga_config: Optional[Dict[str, Any]] = None
    pso_config: Optional[Dict[str, Any]] = None
    gwo_config: Optional[Dict[str, Any]] = None
    hho_config: Optional[Dict[str, Any]] = None
    two_opt_config: Optional[Dict[str, Any]] = None
    clustering_algorithm: Optional[str] = "sweep"

    def get_time_windows(self) -> Dict[str, TimeWindow]:
        """Helper to get time windows from students if applicable
        
        Parses pickup_time and dropoff_time from StudentNode objects
        into TimeWindow dicts keyed by student location_code.
        
        Time format: HH:MM (e.g., "08:30", "14:00")
        Returns: Dict mapping location_code -> TimeWindow(earliest, latest)
        """
        time_windows: Dict[str, TimeWindow] = {}
        
        for student in self.students:
            # Use pickup_time for PICKUP direction, dropoff_time for DROPOFF
            time_str = None
            if self.direction == Direction.PICKUP and student.pickup_time:
                time_str = student.pickup_time
            elif self.direction == Direction.DROPOFF and student.dropoff_time:
                time_str = student.dropoff_time
            elif student.pickup_time:
                time_str = student.pickup_time
            elif student.dropoff_time:
                time_str = student.dropoff_time
            
            if time_str and isinstance(time_str, str) and ':' in time_str:
                try:
                    parts = time_str.strip().split(':')
                    total_minutes = int(parts[0]) * 60 + int(parts[1])
                    # Default window: ±15 minutes around the target time
                    window_size = 30  # 30 minute window
                    time_windows[student.location_code] = TimeWindow(
                        earliest=max(0, total_minutes - window_size // 2),
                        latest=total_minutes + window_size // 2
                    )
                except (ValueError, IndexError):
                    pass
        
        return time_windows

class OptimizationResponse(BaseModel):
    algorithm_used: str
    success: bool
    routes: List[VehicleRoute]
    total_vehicles: int = 0
    total_duration_minutes: float = 0.0
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    direction: Optional[Direction] = None
    time_windows_used: bool = False
    ie_data: Optional[IEResponseData] = None
    total_time_window_violations: Optional[int] = None

class AlgorithmResult(BaseModel):
    algorithm: str
    success: bool
    total_vehicles: int
    total_duration_minutes: float
    execution_time_seconds: float
    routes: List[VehicleRoute]
    error_message: Optional[str] = None

class CompareRequest(BaseModel):
    students: List[StudentNode]
    depot: LocationNode
    max_travel_time: int = 120
    sw_capacity: int = 4
    so_capacity: int = 5
    direction: Direction = Direction.PICKUP
    use_time_windows: bool = False
    algorithms: Optional[List[str]] = None

class CompareResponse(BaseModel):
    success: bool
    results: List[AlgorithmResult]
    best_algorithm: str
    fastest_algorithm: str
    summary: Dict[str, Any]

class StrategyInfo(BaseModel):
    name: str
    display_name: str
    description: str
    complexity: str
    recommended: bool = False


class BenchmarkRunRequest(BaseModel):
    """Request body for POST /api/v1/benchmark/run"""
    run_id: str
    algorithms: List[Dict[str, Any]]
    problems: List[str]
    settings: Dict[str, Any] = {}