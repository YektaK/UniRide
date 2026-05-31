"""Helpers for per-request SOTA dataclass config overrides."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")


def merge_sota_config(base_config: T, overrides: Optional[Dict[str, Any]]) -> T:
    """Return a request-local dataclass config with valid override keys applied."""
    if not overrides:
        return base_config

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


__all__ = ["merge_sota_config"]
