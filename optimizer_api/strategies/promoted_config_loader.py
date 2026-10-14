"""Optional promoted-config lookup for production strategy construction."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional

from academic_benchmark.promoted_configs import (
    DEFAULT_PROMOTED_CONFIG_PATH,
    resolve_promoted_params,
)

logger = logging.getLogger(__name__)

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
    ``promoted_config_sha256``: SHA-256 of the promoted_configs.json as it was
    loaded (same cache lifetime as the loaded document), or None when the file
    does not exist or is unreadable. Pure metadata: it never changes a result.
    """
    path = get_promoted_config_path()
    # Same explicit cache key as get_promoted_params; never raises (see loader).
    load_runtime_promoted_configs(path)
    digest = _LOADED_SHA256.get(path)
    return {
        "promoted_config_flag": promoted_config_enabled(),
        "promoted_config_sha256": digest,
    }


def get_promoted_config_path() -> str:
    return os.environ.get(PROMOTED_CONFIG_PATH_ENV, DEFAULT_PROMOTED_CONFIG_PATH)


# SHA-256 of the file bytes read when load_runtime_promoted_configs last loaded
# each path. Filled at load time and cleared with the lru_cache, so the reported
# hash always matches the document that is actually in use.
_LOADED_SHA256: Dict[str, Optional[str]] = {}


def load_runtime_promoted_configs(path: Optional[str] = None) -> Dict[str, object]:
    """Promoted-config document for ``path`` (default: the env/default path).

    The path is resolved BEFORE the cached call, so the cache key is always the
    explicit resolved path and a later path change is never masked.
    """
    return _load_cached(path or get_promoted_config_path())


def _empty_document(source: str) -> Dict[str, object]:
    return {"schema_version": 1, "source": source, "configs": []}


def _validate_document_shape(document: object) -> None:
    """Raise ValueError unless ``document`` is {"configs": [dict, ...]} with dict params."""
    if not isinstance(document, dict):
        raise ValueError("top-level JSON value is not an object")
    configs = document.get("configs", [])
    if not isinstance(configs, list):
        raise ValueError("configs is not a list")
    for config in configs:
        if not isinstance(config, dict):
            raise ValueError("a config entry is not an object")
        if "params" in config and not isinstance(config["params"], dict):
            raise ValueError("params is not an object")


@lru_cache(maxsize=4)
def _load_cached(resolved_path: str) -> Dict[str, object]:
    if not os.path.exists(resolved_path):
        _LOADED_SHA256[resolved_path] = None
        return _empty_document("missing")
    # Production must never fail because of this optional file: an unreadable or
    # malformed file yields no configs (defaults apply), a logged warning and no
    # hash. The hash and the parsed document come from the same bytes.
    try:
        with open(resolved_path, "rb") as handle:
            raw = handle.read()
        document = json.loads(raw.decode("utf-8"))
        _validate_document_shape(document)
    except (OSError, ValueError, RecursionError) as exc:  # JSON syntax/encoding, wrong shape, deep nesting
        logger.warning(
            "Ignoring promoted-config file %s (%s); built-in defaults apply.",
            resolved_path,
            type(exc).__name__,
        )
        _LOADED_SHA256[resolved_path] = None
        return _empty_document("unreadable")
    _LOADED_SHA256[resolved_path] = hashlib.sha256(raw).hexdigest()
    return document


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
    document = load_runtime_promoted_configs(path or get_promoted_config_path())
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
    _load_cached.cache_clear()
    _LOADED_SHA256.clear()


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
