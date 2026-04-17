"""
Haversine distance and travel time estimation utilities.
"""

import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two geographic points.
    Returns distance in meters.
    Use this for real-world lat/lng coordinates, NOT for TSPLIB abstract X-Y.
    """
    R = 6371000  # Earth radius in meters

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def estimate_travel_time(distance_meters: float, avg_speed_kmh: float = 40.0) -> float:
    """
    Estimate travel time from distance.
    Returns time in minutes.
    """
    distance_km = distance_meters / 1000
    time_hours = distance_km / avg_speed_kmh
    return time_hours * 60  # Convert to minutes
