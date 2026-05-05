# ── Re-export from benchmark_utils.py ────────────────────────────────────────
# All utilities have been unified into benchmark_utils.py.
# This file remains as a compatibility shim for legacy imports.

try:
    from .benchmark_utils import (
        check_algorithms_status,
        compute_population_diversity,
        get_file_hash,
        load_metadata as get_latest_metadata,
        save_metadata,
    )
except ImportError:
    from benchmark_utils import (
        check_algorithms_status,
        compute_population_diversity,
        get_file_hash,
        load_metadata as get_latest_metadata,
        save_metadata,
    )
