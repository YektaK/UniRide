import numpy as np
from typing import List, Tuple, Callable, Dict

# Re-export from consolidated distance module for backward compatibility
from uniride_core.algorithms.distance import create_np_distance_matrix


def create_np_duration_func(
    dist_matrix_np: np.ndarray,
    unique_locs: List[str],
) -> Callable[[List[str]], float]:
    index_map: Dict[str, int] = {loc: i for i, loc in enumerate(unique_locs)}
    _dm = dist_matrix_np

    def duration_func(route: List[str]) -> float:
        if not route:
            return 0.0
        try:
            total = 0.0
            prev_idx = index_map[route[0]]
            for loc in route[1:]:
                curr_idx = index_map[loc]
                total += _dm[prev_idx, curr_idx]
                prev_idx = curr_idx
            total += _dm[prev_idx, index_map[route[0]]]
            return total
        except KeyError:
            return 0.0

    duration_func._np_dist_matrix = dist_matrix_np
    duration_func._np_unique_locs = unique_locs
    return duration_func


def convert_route_to_indices(route: List[str]) -> List[int]:
    return [int(loc[1:]) for loc in route]
