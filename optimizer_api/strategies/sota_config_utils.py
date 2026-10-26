"""Helpers for per-request SOTA dataclass config overrides."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, Dict, Optional, Tuple, TypeVar

T = TypeVar("T")

#: Old request key mapped to ``deadline_seconds`` for one release (MT6-03 / audit H11).
LEGACY_DEADLINE_KEY = "time_limit"
#: Old per-layer local-search clock. Accepted and ignored: local search no longer has a clock.
LEGACY_IGNORED_KEY = "ls_time_limit"


def split_legacy_sota_keys(
    overrides: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Tuple[str, ...]]:
    """Return ``(overrides without the old clock keys, ignored old keys)``.

    ``time_limit`` becomes ``deadline_seconds`` unless the caller also sent
    ``deadline_seconds`` (the new key wins). ``ls_time_limit`` is dropped and
    reported in the second element so callers can record that it was ignored.
    """
    if not overrides:
        return {}, ()
    clean = dict(overrides)
    ignored = []
    if LEGACY_DEADLINE_KEY in clean:
        legacy = clean.pop(LEGACY_DEADLINE_KEY)
        clean.setdefault("deadline_seconds", legacy)
    if LEGACY_IGNORED_KEY in clean:
        clean.pop(LEGACY_IGNORED_KEY)
        ignored.append(LEGACY_IGNORED_KEY)
    return clean, tuple(ignored)


def merge_sota_config(base_config: T, overrides: Optional[Dict[str, Any]]) -> T:
    """Return a request-local dataclass config with valid override keys applied.

    Old request keys (one release, MT6-03): ``time_limit`` is mapped to
    ``deadline_seconds``; ``ls_time_limit`` is accepted and ignored.
    """
    if not overrides:
        return base_config

    overrides, _ignored = split_legacy_sota_keys(overrides)
    field_map = {field.name: field for field in fields(base_config)}
    clean: Dict[str, Any] = {}
    for key, value in overrides.items():
        field = field_map.get(key)
        if field is None:
            continue
        current = getattr(base_config, key)
        if isinstance(current, tuple) and isinstance(value, list):
            value = tuple(value)
        clean[key] = value
    return replace(base_config, **clean) if clean else base_config


__all__ = ["LEGACY_DEADLINE_KEY", "LEGACY_IGNORED_KEY", "merge_sota_config", "split_legacy_sota_keys"]
