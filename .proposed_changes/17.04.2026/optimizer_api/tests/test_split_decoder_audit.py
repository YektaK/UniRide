
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer_api.utils.split_decoder import SplitDecoder, Direction, Trip

def test_fix01_negative_departure_skip():
    """FIX-01: Ensure that departure_time < 0 trips are marked infeasible/skipped."""
    decoder = SplitDecoder(
        sw_capacity=2,
        so_capacity=2,
        max_tour_duration=600,
        time_windows={"L1": (0, 30)},
        use_time_windows=True,
        direction=Direction.PICKUP,
        target_time=30, # Target is 30m after midnight
        offset_minutes=10
    )
    
    # Very long trip from depot -> L1 -> depot (takes 50 minutes)
    giant_tour = ["L1"]
    depot = "DEPOT"
    distance_matrix = {
        "DEPOT": {"L1": 25},
        "L1": {"DEPOT": 25}
    }
    demands = {"L1": (1, 0)}
    
    trips = decoder._build_trips_with_tw(giant_tour, depot, distance_matrix, demands)
    
    # target arrival is 30. total_trip_cost is 50. offset is 10.
    # departure_time = 30 - 50 - 10 = -30. Should be skipped.
    assert len(trips[1]) == 0, "Trip with negative departure time should be skipped"


def test_fix02_dropoff_time_violations_accumulation_and_wait():
    """FIX-02: Check that DROPOFF scheduling properly waits, and accumulates violations."""
    decoder = SplitDecoder(
        sw_capacity=5,
        so_capacity=5,
        max_tour_duration=600,
        time_windows={
            "L1": (100, 150),  # L1 wait time needed if arrival < 100
            "L2": (50, 80),    # Will be a violation since we arrive after 100
            "L3": (10, 20)     # Further violation
        },
        use_time_windows=True,
        direction=Direction.DROPOFF,
        target_time=50, # Target departure time from depot
        offset_minutes=0
    )
    
    giant_tour = ["L1", "L2", "L3"]
    depot = "DEPOT"
    # D -> L1 = 10 (arrival = 60). window L1 = 100-150. Waits until 100!
    # L1 -> L2 = 20 (arrival = 120). window L2 = 50-80. Vio += 1!
    # L2 -> L3 = 10 (arrival = 130). window L3 = 10-20. Vio += 1! Total vio = 2.
    distance_matrix = {
        "DEPOT": {"L1": 10},
        "L1": {"L2": 20},
        "L2": {"L3": 10},
        "L3": {"DEPOT": 10}
    }
    demands = {"L1": (1, 0), "L2": (1, 0), "L3": (1, 0)}
    
    trips = decoder._build_trips_with_tw(giant_tour, depot, distance_matrix, demands)
    
    valid_trip = next((t for t in trips[3] if t.start_idx == 0 and t.end_idx == 2), None)
    assert valid_trip is not None
    assert valid_trip.time_window_violations == 2, "Violations should accumulate to 2"
    

def test_fix03_trip_end_boundary():
    """FIX-03: Ensure target arrival time computation only considers committed stops in the trip bounds."""
    decoder = SplitDecoder(
        sw_capacity=2, # limits the trip
        so_capacity=2,
        max_tour_duration=600,
        time_windows={
            "L1": (0, 100),
            "L2": (0, 200),
            "L3": (0, 300) # This should NOT affect the L1-L2 trip!
        },
        use_time_windows=True,
        direction=Direction.PICKUP,
        target_time=50,
        offset_minutes=0
    )
    
    # L1 and L2 fit in one trip. L3 does not due to capacity (2+1 = 3 > 2)
    giant_tour = ["L1", "L2", "L3"]
    depot = "DEPOT"
    distance_matrix = {
        "DEPOT": {"L1": 10, "L3": 10},
        "L1": {"L2": 10},
        "L2": {"L3": 10, "DEPOT": 10},
        "L3": {"DEPOT": 10}
    }
    demands = {"L1": (1, 0), "L2": (1, 0), "L3": (1, 0)}
    
    # Target arrival time of a subset is the max `latest` bound in that subset
    # for ["L1", "L2"], max is 200.
    # If the bug was present (using loop var j instead of trip_end), it might have included L3's time (300).
    
    trips = decoder._build_trips_with_tw(giant_tour, depot, distance_matrix, demands)
    
    # Look for trip [L1, L2] (start_idx=0, end_idx=1)
    trip_1_2 = next((t for t in trips[2] if t.start_idx == 0 and t.end_idx == 1), None)
    assert trip_1_2 is not None
    
    # departure time = target_arrival - total_cost - offset
    # Target arrival for L1, L2 should be 200 (not 300)
    # total_cost = 10(D->L1) + 10(L1->L2) + 10(L2->D) = 30
    # departure = 200 - 30 - 0 = 170
    assert trip_1_2.departure_time == 170, f"Expected 170, got {trip_1_2.departure_time}"


if __name__ == '__main__':
    test_fix01_negative_departure_skip()
    test_fix02_dropoff_time_violations_accumulation_and_wait()
    test_fix03_trip_end_boundary()
    print('All Split Decoder regression tests passed successfully!')
