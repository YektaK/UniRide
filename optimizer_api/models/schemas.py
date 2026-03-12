from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class LocationNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the location, e.g., 'Sw1'")
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    type: str = Field(default="Sw", description="Type of node, e.g., 'Sw' (Wheelchair), 'So' (Walking)")

class RouteStep(BaseModel):
    location1: str
    location2: str
    duration: float = Field(description="Travel time in minutes")
    distance: float = Field(description="Travel distance in meters")

class VehicleRoute(BaseModel):
    vehicle_id: str
    route_details: List[RouteStep]
    total_duration_minutes: float
    total_distance_km: float

class OptimizationRequest(BaseModel):
    algorithm: str = Field(default="ortools_cvrp", description="The routing strategy to use (e.g., kmeans_tsp, ortools_cvrp, greedy_heuristic, permutation_tsp)")
    students: List[LocationNode] = Field(..., description="List of student nodes needing pickup")
    depot: LocationNode = Field(..., description="The depot node (e.g., D.Kampus)")
    max_travel_time: int = Field(default=120, description="Maximum allowed travel time per vehicle in minutes")
    sw_capacity: int = Field(default=4, description="Maximum wheelchair (Sw) student capacity per vehicle")
    so_capacity: int = Field(default=5, description="Maximum walking (So) student capacity per vehicle")

class OptimizationResponse(BaseModel):
    algorithm_used: str
    success: bool
    routes: List[VehicleRoute]
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
