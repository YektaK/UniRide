"""Compatibility shim for legacy imports.

The implementation lives in `uniride_core.algorithms.local_search_numba`.
Production/API code may keep importing this module while the app is migrated,
but critical algorithm logic is owned by `uniride_core`.
"""

from uniride_core.algorithms.local_search_numba import *  # noqa: F401,F403
