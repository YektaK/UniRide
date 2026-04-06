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
        """Helper to get time windows from students if applicable"""
        return {}

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