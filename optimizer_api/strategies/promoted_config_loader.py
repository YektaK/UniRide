"""Optional promoted-config lookup for production strategy construction."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional

from academic_benchmark.promoted_configs import (
    DEFAULT_PROMOTED_CONFIG_PATH,
    load_promoted_configs,
    resolve_promoted_params,
)

PROMOTED_CONFIG_PATH_ENV = "UNIRIDE_PROMOTED_CONFIG_PATH"
# Owner decision 2026-10-13 (DECISION_LOG A12): production ignores academic
# promoted configs unless this flag is exactly "1". Default is OFF.
USE_PROMOTED_CONFIG_ENV = "UNIRIDE_USE_PROMOTED_CONFIG"

ACADEMIC_TO_STRATEGY_PARAM_KEYS = {
    "pop_size": "population_size",
    "generations": "max_iterations",
    "iterations": "max_iterations",
    "elite_size": "elite_count",
    "pack_size": "population_size",
    "hawks": "population_size",
}


def promoted_config_enabled() -> bool:
    """True only when UNIRIDE_USE_PROMOTED_CONFIG is exactly "1"."""
    return os.environ.get(USE_PROMOTED_CONFIG_ENV) == "1"


def promoted_config_provenance() -> Dict[str, Any]:
    """Promoted-config provenance for result metadata (owner decision 2026-10-14).

    ``promoted_config_flag``: whether UNIRIDE_USE_PROMOTED_CONFIG=1 is set.
    ``promoted_config_sha256``: SHA-256 of the promoted_configs.json at the
    configured path, or None when the file does not exist or is unreadable.
    Pure metadata: it never changes a result value.
    """
    digest: Optional[str] = None
    path = get_promoted_config_path()
    try:
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        digest = None
    return {
        "promoted_config_flag": promoted_config_enabled(),
        "promoted_config_sha256": digest,
    }


def get_promoted_config_path() -> str:
    return os.environ.get(PROMOTED_CONFIG_PATH_ENV, DEFAULT_PROMOTED_CONFIG_PATH)


@lru_cache(maxsize=4)
def load_runtime_promoted_configs(path: Optional[str] = None) -> Dict[str, object]:
    resolved_path = path or get_promoted_config_path()
    if not os.path.exists(resolved_path):
        return {"schema_version": 1, "source": "missing", "configs": []}
    return load_promoted_configs(resolved_path)


def get_promoted_params(
    algorithms: Iterable[str] | str,
    *,
    problem_type: str = "tsp",
    matrix_kind: str = "distance",
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """Return promoted params for the first matching algorithm alias.

    Returns ``{}`` unless ``UNIRIDE_USE_PROMOTED_CONFIG=1`` (default off).
    """
    if not promoted_config_enabled():
        return {}
    document = load_runtime_promoted_configs(path)
    names = [algorithms] if isinstance(algorithms, str) else list(algorithms)
    for algorithm in names:
        params = resolve_promoted_params(
            document,
            algorithm,
            problem_type=problem_type,
            matrix_kind=matrix_kind,
        )
        if params:
            return params
    return {}


def get_promoted_strategy_params(
    algorithms: Iterable[str] | str,
    *,
    problem_type: str = "tsp",
    matrix_kind: str = "distance",
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """Return promoted params normalized for production strategy config dicts."""
    params = get_promoted_params(
        algorithms,
        problem_type=problem_type,
        matrix_kind=matrix_kind,
        path=path,
    )
    return normalize_strategy_params(params)


def normalize_strategy_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Map academic benchmark parameter names to production strategy names."""
    normalized: Dict[str, Any] = {}
    for key, value in dict(params or {}).items():
        normalized[ACADEMIC_TO_STRATEGY_PARAM_KEYS.get(key, key)] = value
    return normalized


def clear_promoted_config_cache() -> None:
    load_runtime_promoted_configs.cache_clear()


__all__ = [
    "USE_PROMOTED_CONFIG_ENV",
    "promoted_config_enabled",
    "promoted_config_provenance",
    "PROMOTED_CONFIG_PATH_ENV",
    "clear_promoted_config_cache",
    "get_promoted_config_path",
    "get_promoted_params",
    "get_promoted_strategy_params",
    "load_runtime_promoted_configs",
    "normalize_strategy_params",
]
