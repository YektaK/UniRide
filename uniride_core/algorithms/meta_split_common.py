"""Shared helpers for string-keyed metaheuristic split engines."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from uniride_core.algorithms.local_search import LocalSearchType, apply_local_search
from uniride_core.algorithms.string_split_decoder import decode_giant_tour, decode_with_time_windows

logger = logging.getLogger(__name__)

DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0


def shuffle_permutation(items: List[str], rng: random.Random) -> List[str]:
    """Shuffle a permutation using the supplied random generator."""
    result = items.copy()
    for idx in range(len(result) - 1, 0, -1):
        swap_idx = rng.randint(0, idx)
        result[idx], result[swap_idx] = result[swap_idx], result[idx]
    return result


def giant_tour_cost(
    tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
) -> float:
    """Calculate depot-to-depot giant tour travel cost."""
    if not tour:
        return 0.0

    total = distance_matrix.get(depot, {}).get(tour[0], DEFAULT_TRAVEL_FALLBACK_MINUTES)
    for idx in range(len(tour) - 1):
        total += distance_matrix.get(tour[idx], {}).get(tour[idx + 1], DEFAULT_TRAVEL_FALLBACK_MINUTES)
    total += distance_matrix.get(tour[-1], {}).get(depot, DEFAULT_TRAVEL_FALLBACK_MINUTES)
    return float(total)


def split_penalized_cost(
    tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    is_asymmetric: bool = False,
) -> float:
    """Evaluate a giant tour using the split decoder and a vehicle-count penalty."""
    result = decode_giant_tour(
        giant_tour=tour,
        depot=depot,
        distance_matrix=distance_matrix,
        demands=demands,
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        is_asymmetric=is_asymmetric,
    )
    if result["num_vehicles"] == 0:
        return float("inf")
    return float(result["total_cost"]) + int(result["num_vehicles"]) * 50


def local_search_improve(
    tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    local_search_type: str = "hybrid",
) -> List[str]:
    """Improve a giant tour with the configured local-search operator."""

    def cost_func(route: List[str]) -> float:
        return giant_tour_cost(route, depot, distance_matrix)

    try:
        improved_route, _ = apply_local_search(
            tour,
            cost_func,
            LocalSearchType(local_search_type),
        )
        return improved_route
    except Exception as exc:
        logger.debug("Local search failed, returning original tour: %s", exc)
        return tour


def decode_final_tour(
    tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    *,
    use_time_windows: bool = False,
    time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
    direction: Any = "pickup",
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
    is_asymmetric: bool = False,
) -> Dict[str, Any]:
    """Decode a final giant tour with CVRP or CVRPTW split semantics."""
    if use_time_windows and time_windows:
        return decode_with_time_windows(
            giant_tour=tour,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            time_windows=time_windows,
            direction=direction,
            target_time=target_time,
            offset_minutes=offset_minutes,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            max_tour_duration=max_tour_duration,
            is_asymmetric=is_asymmetric,
        )

    return decode_giant_tour(
        giant_tour=tour,
        depot=depot,
        distance_matrix=distance_matrix,
        demands=demands,
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        is_asymmetric=is_asymmetric,
    )


__all__ = [
    "DEFAULT_TRAVEL_FALLBACK_MINUTES",
    "decode_final_tour",
    "giant_tour_cost",
    "local_search_improve",
    "shuffle_permutation",
    "split_penalized_cost",
]
