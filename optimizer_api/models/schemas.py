from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, model_validator
from enum import Enum

from uniride_core.adapters.demand_builder import student_occurrence_keys

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


def _parse_hhmm(time_str: str) -> int:
    """Parse HH:MM into minutes after midnight."""
    parts = str(time_str).strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str!r}")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time value: {time_str!r}")
    return hour * 60 + minute


def _minutes_to_hhmm(total_minutes: int) -> str:
    """Format minutes after midnight as HH:MM, clamped to one day."""
    clamped = max(0, min(24 * 60, int(total_minutes)))
    if clamped == 24 * 60:
        return "24:00"
    return f"{clamped // 60:02d}:{clamped % 60:02d}"


def _round_up_to_hour(total_minutes: int) -> int:
    if total_minutes % 60 == 0:
        return total_minutes
    return min(24 * 60, ((total_minutes // 60) + 1) * 60)

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
    occurrence_id: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    disability_type: str = "So"
    pickup_time: Optional[str] = None
    dropoff_time: Optional[str] = None
    direction: TripDirection = TripDirection.PICKUP

    @model_validator(mode="after")
    def validate_student_fields(self) -> "StudentNode":
        """Validate optional student fields without requiring app-loaded coordinates."""
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
        for field_name in ("pickup_time", "dropoff_time"):
            value = getattr(self, field_name)
            if value is not None:
                _parse_hhmm(value)
        return self

    def get_time_window(self, direction: TripDirection, window_minutes: int = 30) -> Optional["TimeWindow"]:
        """Return the student's centered pickup/dropoff time window when present."""
        time_str = self.pickup_time if direction == TripDirection.PICKUP else self.dropoff_time
        if not time_str:
            return None
        return TimeWindow.from_time_string(time_str, window_minutes=window_minutes)

class TimeWindow(BaseModel):
    earliest: int
    latest: int

    @classmethod
    def from_time_string(cls, time_str: str, window_minutes: int = 30) -> "TimeWindow":
        """Create a centered time window from an HH:MM target time."""
        total_minutes = _parse_hhmm(time_str)
        half_window = window_minutes // 2
        return cls(
            earliest=max(0, total_minutes - half_window),
            latest=min(24 * 60, total_minutes + half_window),
        )

    def to_time_string(self) -> Tuple[str, str]:
        """Return earliest/latest as HH:MM strings."""
        return _minutes_to_hhmm(self.earliest), _minutes_to_hhmm(self.latest)

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

    @model_validator(mode="after")
    def validate_schedule_times(self) -> "WeeklyScheduleEntry":
        _parse_hhmm(self.startTime)
        _parse_hhmm(self.endTime)
        return self

    def get_pickup_time_window(self, window_minutes: int = 30) -> TimeWindow:
        return TimeWindow.from_time_string(self.startTime, window_minutes=window_minutes)

    def get_dropoff_time_window(self, window_minutes: int = 30) -> TimeWindow:
        rounded_end = _round_up_to_hour(_parse_hhmm(self.endTime))
        return TimeWindow.from_time_string(_minutes_to_hhmm(rounded_end), window_minutes=window_minutes)

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
        """Validate request-level time fields."""
        if self.target_time is not None:
            _parse_hhmm(self.target_time)
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
        into TimeWindow dicts keyed by student occurrence identity.

        Single-customer locations keep their location_code as the key;
        locations served by multiple customers get disambiguated occurrence keys.

        Time format: HH:MM (e.g., "08:30", "14:00")
        Returns: Dict mapping occurrence key -> TimeWindow(earliest, latest)
        """
        time_windows: Dict[str, TimeWindow] = {}
        
        for student, occurrence_key in zip(self.students, student_occurrence_keys(self.students)):
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
            elif self.use_time_windows and self.target_time:
                time_str = self.target_time
            
            if time_str and isinstance(time_str, str) and ":" in time_str:
                try:
                    total_minutes = _parse_hhmm(time_str)
                    # Asymmetric windows based on direction:
                    # PICKUP: (target-30, target) — must arrive by target
                    # DROPOFF: (target, target+30) — can depart after target
                    if self.direction == TripDirection.PICKUP:
                        time_windows[occurrence_key] = TimeWindow(
                            earliest=max(0, total_minutes - 30),
                            latest=total_minutes,
                        )
                    else:
                        time_windows[occurrence_key] = TimeWindow(
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
    run_id: str = Field(..., min_length=1, max_length=128)
    algorithms: List[Dict[str, Any]] = Field(..., min_length=1)
    problems: List[str] = Field(..., min_length=1)
    settings: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_benchmark_contract(self) -> "BenchmarkRunRequest":
        for index, algorithm in enumerate(self.algorithms):
            if not isinstance(algorithm, dict):
                raise ValueError(f"algorithms[{index}] must be an object")
            algorithm_id = algorithm.get("id", algorithm.get("name"))
            if not isinstance(algorithm_id, str) or not algorithm_id.strip():
                raise ValueError(f"algorithms[{index}] must include non-empty id or name")
            params = algorithm.get("params", {})
            if params is not None and not isinstance(params, dict):
                raise ValueError(f"algorithms[{index}].params must be an object when provided")

        for index, problem in enumerate(self.problems):
            if not isinstance(problem, str) or not problem.strip():
                raise ValueError(f"problems[{index}] must be a non-empty string")

        execution_mode = self.settings.get("execution_mode")
        if execution_mode is not None and execution_mode not in {"matrix_native", "academic_matrix"}:
            raise ValueError("settings.execution_mode must be 'matrix_native' or 'academic_matrix' when provided")

        n_runs = self.settings.get("n_runs", 1)
        if not isinstance(n_runs, int) or isinstance(n_runs, bool) or n_runs < 1:
            raise ValueError("settings.n_runs must be an integer greater than or equal to 1")

        workers = self.settings.get("workers")
        if workers is not None and (not isinstance(workers, int) or isinstance(workers, bool) or workers < 1):
            raise ValueError("settings.workers must be an integer greater than or equal to 1 when provided")

        seed = self.settings.get("seed")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError("settings.seed must be an integer when provided")

        skip_cached = self.settings.get("skip_cached")
        if skip_cached is not None and not isinstance(skip_cached, bool):
            raise ValueError("settings.skip_cached must be a boolean when provided")

        return self
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
