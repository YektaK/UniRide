"""
Optimization API Schemas
Pydantic models for request/response validation
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class DisabilityType(str, Enum):
    SW = "Sw"  # Wheelchair
    SO = "So"  # Walking


class LocationNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the location, e.g., 'Sw1', 'So5', 'D.Kampus'")
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    type: str = Field(default="So", description="Type of node: 'Sw' (Wheelchair), 'So' (Walking)")


class StudentNode(BaseModel):
    id: str = Field(..., description="Student ID")
    name: str = Field(default="", description="Student name")
    location_code: str = Field(..., description="Location code e.g., 'Sw1', 'So5'")
    coordinates: Optional[Dict[str, float]] = Field(default=None, description="Lat/lng coordinates")
    disability_type: str = Field(default="So", description="'Sw' or 'So'")


class RouteStep(BaseModel):
    location1: str
    location2: str
    duration: float = Field(description="Travel time in minutes")
    distance: float = Field(default=0.0, description="Travel distance in meters")


class VehicleRoute(BaseModel):
    vehicle_id: str
    route_details: List[RouteStep]
    total_duration_minutes: float
    total_distance_km: float = Field(default=0.0)
    sw_count: int = Field(default=0, description="Number of wheelchair students")
    so_count: int = Field(default=0, description="Number of walking students")
    student_ids: List[str] = Field(default_factory=list, description="IDs of students in this route")


class LocalSearchType(str, Enum):
    """Available local search types for strategies"""
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    HYBRID = "hybrid"


class VehicleConfig(BaseModel):
    """Vehicle configuration for heterogeneous fleet support"""
    vehicle_id: str = Field(..., description="Unique vehicle identifier")
    sw_capacity: int = Field(default=4, description="Wheelchair capacity")
    so_capacity: int = Field(default=5, description="Other disability capacity")
    cooldown_minutes: int = Field(default=15, description="Minutes between routes")


class OptimizationMode(str, Enum):
    """IE Engine operating mode"""
    BENCHMARK = "benchmark"  # Ideal mode - standard vehicles
    SANDBOX = "sandbox"      # Fine-tune mode - custom vehicles


class BottleneckInfo(BaseModel):
    """Information about a bottleneck in the schedule"""
    time: str = Field(..., description="Hour identifier (e.g., '12:00')")
    type: str = Field(..., description="Type: infeasible, low_efficiency, resource_conflict")
    reason: str = Field(..., description="Description of the issue")
    affected_students: Optional[List[str]] = Field(default=None, description="Student IDs affected")


class TimeShiftSuggestion(BaseModel):
    """Suggestion for time shifting to reduce resource demand"""
    student_id: str
    current_time: str
    suggested_time: str
    savings_vehicles: float = Field(..., description="Estimated vehicle savings")


class IEResponseData(BaseModel):
    """IE Engine response data"""
    standard_vehicles_needed: int = Field(default=0, description="Number of standard minibusses (4Sw+5So) needed")
    hourly_demand: Dict[str, Dict[str, Dict[str, int]]] = Field(default_factory=dict, description="Hourly Sw/So breakdown")
    bottlenecks: List[BottleneckInfo] = Field(default_factory=list, description="Identified bottlenecks")
    time_shift_suggestions: List[TimeShiftSuggestion] = Field(default_factory=list, description="Slack time suggestions")


class OptimizationRequest(BaseModel):
    algorithm: str = Field(
        default="genetic_algorithm",
        description="Algorithm: genetic_algorithm, ga, pso, gwo, hho, two_opt, greedy, ortools_cvrp, permutation_tsp, pyvrp, vroom, ga_split, pso_split"
    )
    students: List[StudentNode] = Field(..., description="List of students needing pickup")
    depot: LocationNode = Field(..., description="The depot node (e.g., D.Kampus)")
    max_travel_time: int = Field(default=120, description="Maximum tour time per vehicle in minutes")
    sw_capacity: int = Field(default=4, description="Wheelchair capacity per vehicle")
    so_capacity: int = Field(default=5, description="Walking student capacity per vehicle")

    # Local search configuration (applies to GA, PSO, GWO, HHO)
    local_search_type: Optional[str] = Field(
        default="two_opt",
        description="Local search type: none, two_opt, three_opt, or_opt, hybrid"
    )

    # Algorithm-specific parameters
    ga_config: Optional[Dict[str, Any]] = Field(default=None, description="GA parameters")
    pso_config: Optional[Dict[str, Any]] = Field(default=None, description="PSO parameters")
    gwo_config: Optional[Dict[str, Any]] = Field(default=None, description="GWO parameters")
    hho_config: Optional[Dict[str, Any]] = Field(default=None, description="HHO parameters")
    two_opt_config: Optional[Dict[str, Any]] = Field(default=None, description="Two-Opt parameters")

    # IE Engine parameters (Faz 1.5X)
    vehicles: Optional[List[VehicleConfig]] = Field(default=None, description="Available vehicles for sandbox mode")
    allow_time_shift: bool = Field(default=False, description="Allow student time shifting for resource leveling")
    slack_window_minutes: int = Field(default=60, description="Maximum minutes to shift student pickup/dropoff time")
    mode: OptimizationMode = Field(default=OptimizationMode.BENCHMARK, description="Operating mode: benchmark or sandbox")
    clustering_algorithm: Optional[str] = Field(default="sweep", description="Clustering method: kmeans, sweep, clarke_wright")


class OptimizationResponse(BaseModel):
    algorithm_used: str
    success: bool
    routes: List[VehicleRoute]
    total_vehicles: int = Field(default=0)
    total_duration_minutes: float = Field(default=0.0)
    error_message: Optional[str] = None
    execution_time_seconds: float = Field(default=0.0)
    
    # IE Engine response data (Faz 1.5X)
    ie_data: Optional[IEResponseData] = Field(default=None, description="Resource analysis data")


class CompareRequest(BaseModel):
    """Request for comparing all algorithms"""
    students: List[StudentNode] = Field(..., description="List of students needing pickup")
    depot: LocationNode = Field(..., description="The depot node")
    max_travel_time: int = Field(default=120)
    sw_capacity: int = Field(default=4)
    so_capacity: int = Field(default=5)
    algorithms: Optional[List[str]] = Field(default=None, description="Algorithms to compare (default: all)")


class AlgorithmResult(BaseModel):
    """Result from a single algorithm"""
    algorithm: str
    success: bool
    total_vehicles: int
    total_duration_minutes: float
    execution_time_seconds: float
    routes: List[VehicleRoute]
    error_message: Optional[str] = None


class CompareResponse(BaseModel):
    """Response for algorithm comparison"""
    success: bool
    results: List[AlgorithmResult]
    best_algorithm: str = Field(description="Algorithm with lowest total duration")
    fastest_algorithm: str = Field(description="Algorithm with fastest execution")
    summary: Dict[str, Dict[str, float]] = Field(description="Summary comparison table")


class StrategyInfo(BaseModel):
    """Information about an algorithm strategy"""
    name: str
    display_name: str
    description: str
    complexity: str
    recommended: bool = Field(default=False)