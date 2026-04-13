import time
import sys
import random

sys.path.append('.')

from utils.split_decoder import SplitDecoder, Direction
from utils.linear_split_decoder import LinearSplitDecoder, PenaltyConfig

def run_performance_test():
    print("Generating Academic Verification Benchmark: 150 Students")
    num_students = 150
    depot = "D.Kampus"
    giant_tour = [f"St_{i}" for i in range(num_students)]
    
    locations = [depot] + giant_tour
    distance_matrix = {}
    for loc1 in locations:
        distance_matrix[loc1] = {}
        for loc2 in locations:
            if loc1 == loc2:
                distance_matrix[loc1][loc2] = 0.0
            else:
                distance_matrix[loc1][loc2] = random.uniform(5.0, 25.0)

    demands = {}
    time_windows = {}
    for st in giant_tour:
        demands[st] = (random.randint(0, 1), random.randint(0, 1))
        tw_start = random.randint(480, 500)
        time_windows[st] = (tw_start, tw_start + 45)

    old_decoder = SplitDecoder(
        sw_capacity=4, so_capacity=5, max_tour_duration=120.0,
        time_windows=time_windows, use_time_windows=True,
        direction=Direction.PICKUP, target_time=540, offset_minutes=10
    )
    
    start_old = time.time()
    res_old = old_decoder.decode(giant_tour, depot, distance_matrix, demands)
    end_old = time.time()
    time_old_ms = (end_old - start_old) * 1000
    print(f"Old Split Decoder Time: {time_old_ms:.2f} ms")
    
    
    # Run New Linear Split Decoder WITHOUT relaxations (Apples to Apples)
    print("Running new O(NB) Linear Split (Strict mode)...")
    penalties = PenaltyConfig(allow_time_warp=False, allow_capacity_overflow=False, max_stops_bounded=10)
    new_decoder = LinearSplitDecoder(
        sw_capacity=4, so_capacity=5, max_tour_duration=120.0,
        time_windows=time_windows, direction=Direction.PICKUP,
        target_time=540, offset_minutes=10, penalty_config=penalties
    )
    
    start_new = time.time()
    res_new = new_decoder.decode(giant_tour, depot, distance_matrix, demands)
    end_new = time.time()
    time_new_ms = (end_new - start_new) * 1000
    print(f"New Linear Split Decoder Time: {time_new_ms:.2f} ms")
    
    print("\n--- PERFORMANCE VERIFICATION ---")
    print(f"O(N^2) Execution: {time_old_ms:.2f} ms")
    print(f"O(NB) Execution : {time_new_ms:.2f} ms")
    if time_old_ms > 0:
        improvement = ((time_old_ms - time_new_ms) / time_old_ms) * 100
        print(f"Performance Improvement: {improvement:.1f}%")

if __name__ == "__main__":
    run_performance_test()
