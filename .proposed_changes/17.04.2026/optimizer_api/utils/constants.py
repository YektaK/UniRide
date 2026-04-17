"""
Shared constants for the optimizer API.

Centralizes magic numbers to improve traceability and debugging.
All strategy files should import from here instead of using inline literals.
"""

# Default travel time (in minutes) used when the distance matrix does not
# contain an entry for a given origin-destination pair.
# WARNING: If this value appears frequently in route solutions, investigate
# the completeness of the time_matrix in Supabase.
DEFAULT_TRAVEL_FALLBACK_MINUTES: float = 15.0
