"""
TSPLIB Problem Parser and Registry — re-export from canonical location.

All implementation lives in uniride_core. This file exists for backward
compatibility with existing imports from optimizer_api.
"""

from uniride_core.algorithms.tsplib_parser import (
    ProblemInstance,
    TSPLIB_OPTIMALS,
    TSPLIB_DATA_DIR,
    TSPLIB_DOWNLOAD_URL,
    parse_tsplib_file,
    parse_tsplib_text,
    parse_opt_tour_text,
    parse_atsp_text,
    euclidean_distance_2d,
    tsplib_euc_2d_distance,
    tsplib_ceil_2d_distance,
    tsplib_att_distance,
    tsplib_geo_distance,
    tsplib_distance_by_type,
    tsplib_tour_distance,
    get_available_problems,
    get_problem_by_name,
    load_problem_coordinates,
    download_tsplib_problem,
    ensure_tsplib_problems,
)

__all__ = [
    'ProblemInstance',
    'TSPLIB_OPTIMALS',
    'TSPLIB_DATA_DIR',
    'TSPLIB_DOWNLOAD_URL',
    'parse_tsplib_file',
    'euclidean_distance_2d',
    'tsplib_tour_distance',
    'get_available_problems',
    'get_problem_by_name',
    'load_problem_coordinates',
    'download_tsplib_problem',
    'ensure_tsplib_problems',
]
