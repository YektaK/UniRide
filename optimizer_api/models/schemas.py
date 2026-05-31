from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
from enum import Enum

# --- Enums ---
class TripDirection(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"


# Backward-compatible alias. Prefer TripDirection in new optimizer_api code.
Direction = TripDirection

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
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)")
    type: str = "So"

class StudentNode(BaseModel):
    id: str
    name: str = ""
    location_code: str
    coordinates: Optional[Dict[str, float]] = None
    disability_type: str = "So"
    pickup_time: Optional[str] = None
    dropoff_time: Optional[str] = None

    @model_validator(mode="after")
    def validate_coordinates(self) -> "StudentNode":
        """Validate that student coordinates are within geographic bounds."""
        if self.coordinates is not None:
            lat = self.coordinates.get("lat")
            lng = self.coordinates.get("lng")
            if lat is not None and not (-90.0 <= lat <= 90.0):
                raise ValueError(
                    f"Student {self.id}: latitude {lat} out of range [-90, 90]"
                )
            if lng is not None and not (-180.0 <= lng <= 180.0):
                raise ValueError(
                    f"Student {self.id}: longitude {lng} out of range [-180, 180]"
                )
        return self

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
    direction: TripDirection

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


def _matrix_is_asymmetric(matrix: Any) -> bool:
    if not isinstance(matrix, dict):
        return False
    for origin, row in matrix.items():
        if not isinstance(row, dict):
            continue
        for destination, value in row.items():
            reverse = matrix.get(destination, {}).get(origin) if isinstance(matrix.get(destination), dict) else value
            if reverse != value:
                return True
    return False

# --- Request / Response ---
class OptimizationRequest(BaseModel):
    algorithm: str = "ga_split"
    students: List[StudentNode]
    depot: LocationNode
    max_travel_time: int = 120
    sw_capacity: int = 4
    so_capacity: int = 5
    direction: TripDirection = TripDirection.PICKUP
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
    sota_config: Optional[Dict[str, Any]] = None
    clustering_algorithm: Optional[str] = "sweep"
    is_asymmetric: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        """Accept old benchmark/smoke-test payloads and map them to current schema."""
        if not isinstance(data, dict):
            return data
        if "students" in data and isinstance(data.get("depot"), dict):
            return data

        locations = data.get("locations")
        depot = data.get("depot")
        if not isinstance(locations, list) or not isinstance(depot, str):
            return data

        distance_matrix = data.get("distance_matrix") or {}
        all_locations = [depot] + [str(loc) for loc in locations]
        coords = {
            loc: {"lat": float(idx), "lng": 0.0}
            for idx, loc in enumerate(all_locations)
        }
        demands = data.get("demands") or {}
        students = []
        for loc in locations:
            loc_code = str(loc)
            demand = demands.get(loc_code, (0, 1))
            sw_count = demand[0] if isinstance(demand, (list, tuple)) and demand else 0
            disability_type = "Sw" if sw_count else "So"
            students.append({
                "id": loc_code,
                "name": loc_code,
                "location_code": loc_code,
                "coordinates": coords[loc_code],
                "disability_type": disability_type,
            })

        vehicles = []
        for vehicle in data.get("vehicles") or []:
            if isinstance(vehicle, dict):
                vehicles.append({
                    "vehicle_id": vehicle.get("vehicle_id") or vehicle.get("id") or f"V{len(vehicles) + 1}",
                    "sw_capacity": vehicle.get("sw_capacity", vehicle.get("capacity_sw", 4)),
                    "so_capacity": vehicle.get("so_capacity", vehicle.get("capacity_so", 5)),
                    "cooldown_minutes": vehicle.get("cooldown_minutes", 15),
                })

        target_time = data.get("target_time")
        if isinstance(target_time, int):
            target_time = f"{target_time // 60:02d}:{target_time % 60:02d}"

        normalized = dict(data)
        normalized["depot"] = {"id": depot, **coords[depot]}
        normalized["students"] = students
        normalized["vehicles"] = vehicles or None
        normalized["target_time"] = target_time
        normalized["algorithm"] = data.get("algorithm") or data.get("strategy") or "ga_split"
        normalized["is_asymmetric"] = bool(normalized.get("is_asymmetric") or _matrix_is_asymmetric(distance_matrix))
        return normalized

    @model_validator(mode="after")
    def validate_students(self) -> "OptimizationRequest":
        """Validate student data integrity."""
        if self.students:
            for student in self.students:
                if student.coordinates is None:
                    raise ValueError(
                        f"Student {student.id} ({student.location_code}) "
                        f"has no coordinates — all students must have valid coordinates"
                    )
        return self

    @property
    def strategy(self) -> str:
        return self.algorithm

    @strategy.setter
    def strategy(self, value: str) -> None:
        self.algorithm = value

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
            if self.direction == TripDirection.PICKUP and student.pickup_time:
                time_str = student.pickup_time
            elif self.direction == TripDirection.DROPOFF and student.dropoff_time:
                time_str = student.dropoff_time
            elif student.pickup_time:
                time_str = student.pickup_time
            elif student.dropoff_time:
                time_str = student.dropoff_time
            
            if time_str and isinstance(time_str, str) and ':' in time_str:
                try:
                    parts = time_str.strip().split(':')
                    total_minutes = int(parts[0]) * 60 + int(parts[1])
                    # Asymmetric windows based on direction:
                    # PICKUP: (target-30, target) — must arrive by target
                    # DROPOFF: (target, target+30) — can depart after target
                    if self.direction == TripDirection.PICKUP:
                        time_windows[student.location_code] = TimeWindow(
                            earliest=max(0, total_minutes - 30),
                            latest=total_minutes,
                        )
                    else:
                        time_windows[student.location_code] = TimeWindow(
                            earliest=total_minutes,
                            latest=total_minutes + 30,
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
    direction: Optional[TripDirection] = None
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
    direction: TripDirection = TripDirection.PICKUP
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
    available: bool = True


class BenchmarkRunRequest(BaseModel):
    """Request body for POST /api/v1/benchmark/run"""
    run_id: str
    algorithms: List[Dict[str, Any]]
    problems: List[str]
    settings: Dict[str, Any] = {}
class BenchmarkResult(BaseModel):
    """Single experiment result for import"""
    algorithm: str
    problem: str
    run_number: int
    tour_length: float
    elapsed_ms: float
    gap_percent: Optional[float] = None
    timestamp: str
    metadata: Dict[str, Any] = {}

class BenchmarkImportRequest(BaseModel):
    """Request body for POST /api/v1/benchmark/import"""
    run_id: str
    status: str = "completed"
    results: List[BenchmarkResult]
    parameters: Dict[str, Any] = {}
    total_experiments: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
