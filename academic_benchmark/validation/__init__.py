"""Independent validators of the academic benchmark layer (WP-E8).

``hamiltonian_cycle``: TSP/ATSP tour validation from dataset artifacts under the TSPLIB convention. It is separate from the
solver path (``uniride_core.exact``) and from multi-route (VRP) validation, which is another contract (DECISION_LOG A04).
"""
from academic_benchmark.validation.hamiltonian_cycle import (
    SUPPORTED_EDGE_WEIGHT_TYPES,
    closed_length,
    coordinate_cost,
    matrix_cost,
    parse_coordinates,
    parse_full_matrix,
    parse_header,
    tsplib_distance,
    validate_hamiltonian_cycle,
)

__all__ = [
    "SUPPORTED_EDGE_WEIGHT_TYPES", "closed_length", "coordinate_cost", "matrix_cost", "parse_coordinates",
    "parse_full_matrix", "parse_header", "tsplib_distance", "validate_hamiltonian_cycle",
]
