"""Shared native-pilot test configuration (used by the native protocol and C-10 tests)."""

from __future__ import annotations

from typing import Any

from academic_benchmark.native_protocol import NATIVE_PROTOCOL, NATIVE_TERMINATION_REGIME

ALNS_PARAMS = {
    "max_iterations": 8,
    "max_no_improvement": 3,
    "remove_ratio": 0.34,
    "min_remove": 1,
    "segment_length": 2,
    "weight_update_factor": 0.2,
    "use_sa": True,
    "sa_start_temp": 4.0,
    "sa_cooling_rate": 0.9,
}


def algorithm_config() -> dict[str, dict[str, Any]]:
    return {
        "Core-GWO-TSP-Pure": {
            "pack_size": 4,
            "max_iterations": 2,
            "max_no_improvement": 1,
        },
        "Core-HHO-TSP-Pure": {
            "hawks": 4,
            "max_iterations": 2,
            "max_no_improvement": 1,
            "dive_count": 1,
        },
        "Core-TwoOpt-TSP": {
            "max_iterations": 2,
            "first_improvement": False,
        },
        "Core-ThreeOpt-TSP": {
            "max_iterations": 2,
            "first_improvement": True,
            "window": 4,
        },
        "Core-OrOpt-TSP": {
            "max_iterations": 3,
            "first_improvement": False,
            "window": 3,
        },
        "ALNS-TSP": dict(ALNS_PARAMS),
    }


def native_pilot_config() -> dict[str, Any]:
    return {
        "protocol_version": NATIVE_PROTOCOL,
        "comparison_regime": NATIVE_TERMINATION_REGIME,
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": algorithm_config(),
        "runs": 1,
        "base_seed": 71,
        "workers": 1,
        "replay_replicates": [0],
        "allow_repository_output": False,
        "overwrite": False,
    }
