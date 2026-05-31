"""Optional promoted-config lookup for production strategy construction."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional

from academic_benchmark.promoted_configs import (
    DEFAULT_PROMOTED_CONFIG_PATH,
    load_promoted_configs,
    resolve_promoted_params,
)

PROMOTED_CONFIG_PATH_ENV = "UNIRIDE_PROMOTED_CONFIG_PATH"


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
    """Return promoted params for the first matching algorithm alias."""
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


def clear_promoted_config_cache() -> None:
    load_runtime_promoted_configs.cache_clear()


__all__ = [
    "PROMOTED_CONFIG_PATH_ENV",
    "clear_promoted_config_cache",
    "get_promoted_config_path",
    "get_promoted_params",
    "load_runtime_promoted_configs",
]
