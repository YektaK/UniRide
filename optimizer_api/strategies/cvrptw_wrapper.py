"""
CVRPTW (Capacitated Vehicle Routing Problem with Time Windows) Wrapper
Provides time window support for the optimization pipeline.

This module wraps existing strategies to add time window constraints.
"""

from utils.split_decoder import SplitDecoder, Direction
from utils.linear_split_decoder import LinearSplitDecoder, PenaltyConfig


class CVRPTWDecoder:
    """
    CVRPTW Decoder that extends SplitDecoder with time window support.
    
    Usage:
        decoder = CVRPTWDecoder(
            sw_capacity=4,
            so_capacity=5,
            max_tour_duration=120,
            time_windows={
                "Sw1": (480, 540),  # 8:00-9:00
                "Sw2": (540, 600),  # 9:00-10:00
            },
            use_time_windows=True
        )
        result = decoder.decode(giant_tour, depot, distance_matrix, demands)
    """
    
    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_duration: float = 120.0,
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        use_time_windows: bool = True,
        use_sota_engine: bool = False,
        direction: Direction = Direction.PICKUP,
        is_asymmetric: bool = False
    ):
        """
        Initialize CVRPTW Decoder.
        
        Args:
            sw_capacity: Maximum wheelchair passengers per vehicle
            so_capacity: Maximum other disability passengers per vehicle
            max_tour_duration: Maximum tour duration in minutes
            time_windows: Dict mapping location -> (earliest, latest) in minutes from start
            use_time_windows: Whether to enforce time window constraints
            use_sota_engine: Whether to use experimental LinearSplitDecoder (SOTA) or stable SplitDecoder
            direction: PICKUP (backward from school arrival) or DROPOFF (forward from school departure)
            is_asymmetric: When True, respects asymmetric distance matrix (d(i,j) != d(j,i))
        """
        self.time_windows = time_windows or {}
        self.use_time_windows = use_time_windows
        self.use_sota_engine = use_sota_engine
        
        if use_sota_engine:
            self.decoder = LinearSplitDecoder(
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                max_tour_duration=max_tour_duration,
                time_windows=time_windows,
                direction=direction,
                penalty_config=PenaltyConfig(allow_time_warp=True, allow_capacity_overflow=True)
            )
        else:
            self.decoder = SplitDecoder(
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                max_tour_duration=max_tour_duration,
                time_windows=time_windows,
                use_time_windows=use_time_windows,
                direction=direction,
                is_asymmetric=is_asymmetric
            )
    
    def decode(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict:
        """
        Decode giant tour with time window constraints.
        
        Args:
            giant_tour: Ordered list of location codes
            depot: Depot location code
            distance_matrix: Travel time/distance between locations
            demands: Dict mapping location -> (sw_demand, so_demand)
        
        Returns:
            Dict with routes, costs, and feasibility info
        """
        if self.use_sota_engine:
            # SOTA LinearSplitDecoder returns an object with attributes
            res = self.decoder.decode(giant_tour, depot, distance_matrix, demands)
            return {
                "routes": res.routes,
                "total_cost": res.final_objective,
                "num_vehicles": res.num_vehicles,
                "time_window_violations": res.time_window_violations,
                "capacity_violations": getattr(res, 'capacity_violations', 0),
                "schedules": getattr(res, 'schedules', [])
            }
        else:
            # Stable SplitDecoder returns a dictionary
            res = self.decoder.decode(giant_tour, depot, distance_matrix, demands)
            return {
                "routes": res.get("routes", []),
                "total_cost": res.get("total_cost", float('inf')),
                "num_vehicles": res.get("num_vehicles", 0),
                "time_window_violations": res.get("time_window_violations", 0),
                "capacity_violations": res.get("capacity_violations", 0),
                "schedules": res.get("schedules", [])
            }
    
    def is_feasible(
        self,
        route: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]]
    ) -> Tuple[bool, str]:
        """
        Check if a route satisfies time window constraints.
        
        Args:
            route: Ordered list of location codes (starting and ending at depot)
            depot: Depot location code
            distance_matrix: Travel time/distance matrix
        
        Returns:
            (is_feasible, reason)
        """
        if not self.use_time_windows:
            return True, ""
        
        current_time = 0.0
        prev = depot
        
        for loc in route:
            if loc == depot:
                continue
            
            # Get travel time
            travel_time = 0.0
            if prev in distance_matrix and loc in distance_matrix[prev]:
                travel_time = distance_matrix[prev][loc]
            current_time += travel_time
            
            # Check time window
            if loc in self.time_windows:
                earliest, latest = self.time_windows[loc]
                if current_time > latest:
                    return False, f"Arrival at {loc} at {current_time:.0f}min exceeds latest {latest}min"
                if current_time < earliest:
                    current_time = earliest  # Wait until window opens
            
            prev = loc
        
        # Add return to depot
        if prev in distance_matrix and depot in distance_matrix[prev]:
            current_time += distance_matrix[prev][depot]
        
        return True, f"Feasible (total time: {current_time:.0f}min)"


def parse_time_windows(
    pickup_times: List[str],
    dropoff_times: List[str]
) -> Dict[str, Tuple[int, int]]:
    """
    Parse time windows from string times (e.g., "08:00") to minutes from midnight.
    
    Args:
        pickup_times: List of pickup time strings
        dropoff_times: List of dropoff time strings
    
    Returns:
        Dict mapping location -> (earliest, latest) in minutes
    """
    def parse_time(time_str: str) -> int:
        """Parse HH:MM to minutes from midnight"""
        try:
            parts = time_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0
    
    time_windows = {}
    
    for t in pickup_times:
        time_windows[t] = (parse_time(t), parse_time(t) + 30)  # 30 min window
    
    for t in dropoff_times:
        time_windows[t] = (parse_time(t), parse_time(t) + 30)
    
    return time_windows


def create_time_windows_from_students(
    students: List[Dict],
    time_column: str = "pickup_time"
) -> Dict[str, Tuple[int, int]]:
    """
    Create time windows from student data.
    
    Args:
        students: List of student dicts with time columns
        time_column: Column name for pickup time
    
    Returns:
        Dict mapping location -> (earliest, latest) in minutes
    """
    time_windows: Dict[str, Tuple[int, int]] = {}
    
    for student in students:
        location = student.get("location_code", "")
        if not location:
            continue
        
        time_str = student.get(time_column, "")
        if not time_str:
            continue
        
        # Parse time
        try:
            minutes = int(time_str.split(":")[0]) * 60 + int(time_str.split(":")[1])
        except (ValueError, IndexError, KeyError):
            continue
        
        # Add 30 minute window
        if location in time_windows:
            existing = time_windows[location]
            time_windows[location] = (
                min(existing[0], minutes),
                max(existing[1], minutes + 30)
            )
        else:
            time_windows[location] = (minutes, minutes + 30)
    
    return time_windows