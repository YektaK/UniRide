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


class OptimizationRequest(BaseModel):
    algorithm: str = Field(default="genetic_algorithm", description="Algorithm: genetic_algorithm, pso, greedy, kmeans_tsp, ortools_cvrp, permutation_tsp")
    students: List[StudentNode] = Field(..., description="List of students needing pickup")
    depot: LocationNode = Field(..., description="The depot node (e.g., D.Kampus)")
    max_travel_time: int = Field(default=120, description="Maximum tour time per vehicle in minutes")
    sw_capacity: int = Field(default=4, description="Wheelchair capacity per vehicle")
    so_capacity: int = Field(default=5, description="Walking student capacity per vehicle")

    # Algorithm-specific parameters
    ga_config: Optional[Dict[str, Any]] = Field(default=None, description="GA parameters")
    pso_config: Optional[Dict[str, Any]] = Field(default=None, description="PSO parameters")


class OptimizationResponse(BaseModel):
    algorithm_used: str
    success: bool
    routes: List[VehicleRoute]
    total_vehicles: int = Field(default=0)
    total_duration_minutes: float = Field(default=0.0)
    error_message: Optional[str] = None
    execution_time_seconds: float = Field(default=0.0)


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
