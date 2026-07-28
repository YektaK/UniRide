"""Exact, source-aware canonical algorithm identifier resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from warnings import warn

from academic_benchmark.core.algorithm_errors import (
    DeprecatedManifestIdentifierError,
    ForbiddenAliasError,
    UnknownAlgorithmError,
)
from uniride_core.algorithms.capabilities import (
    CAPABILITY_CATALOG,
    AlgorithmCapability,
)


class IdentifierSource(str, Enum):
    MANIFEST = "manifest"
    CLI = "cli"
    INTERNAL = "internal"


class AliasPolicy(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class ResolutionResult:
    requested_id: str
    canonical_id: str
    source: IdentifierSource
    alias_used: bool
    alias_policy: AliasPolicy | None
    warning_code: str | None
    warning_message: str | None


_ALIAS_ROWS: tuple[tuple[str, str, AliasPolicy], ...] = (
    ("Numba-2-opt", "Core-TwoOpt-TSP", AliasPolicy.DEPRECATED),
    ("Numba-3-opt-bounded", "Core-ThreeOpt-TSP", AliasPolicy.DEPRECATED),
    ("Numba-Or-opt", "Core-OrOpt-TSP", AliasPolicy.DEPRECATED),
    ("Numba-GA", "Core-GA-TSP", AliasPolicy.DEPRECATED),
    ("Numba-PSO", "Core-PSO-TSP", AliasPolicy.DEPRECATED),
    ("GWO", "Core-GWO-TSP-Pure", AliasPolicy.ACTIVE),
    ("HHO", "Core-HHO-TSP-Pure", AliasPolicy.ACTIVE),
    ("Numba-GWO", "Core-GWO-TSP-Memetic-2opt", AliasPolicy.DEPRECATED),
    ("Core-GWO-TSP", "Core-GWO-TSP-Memetic-2opt", AliasPolicy.DEPRECATED),
    ("Numba-HHO", "Core-HHO-TSP-Memetic-2opt", AliasPolicy.DEPRECATED),
    ("Core-HHO-TSP", "Core-HHO-TSP-Memetic-2opt", AliasPolicy.DEPRECATED),
    ("SOTA-ALNS-TSP", "ALNS-TSP", AliasPolicy.DEPRECATED),
)

CLI_ALIAS_TARGETS: Mapping[str, str] = MappingProxyType(
    {requested_id: canonical_id for requested_id, canonical_id, _ in _ALIAS_ROWS}
)
CLI_ALIAS_POLICIES: Mapping[str, AliasPolicy] = MappingProxyType(
    {requested_id: policy for requested_id, _, policy in _ALIAS_ROWS}
)
FORBIDDEN_ALGORITHM_REPLACEMENTS: Mapping[str, str] = MappingProxyType(
    {
        "B" + "-GA": "Core-GA-TSP",
        "B" + "-PSO": "Core-PSO-TSP",
        "GWO-LKH": "Core-GWO-TSP-Memetic-3opt",
        "HHO-LKH": "Core-HHO-TSP-Memetic-3opt",
    }
)


def validate_alias_catalog_compatibility(
    catalog: Mapping[str, AlgorithmCapability],
    aliases: Mapping[str, str],
) -> None:
    """Reject alias tables that shadow canonical IDs or point outside the catalog."""
    canonical_ids = frozenset(catalog)
    for alias, canonical_id in aliases.items():
        if alias in canonical_ids:
            raise ValueError(f"alias '{alias}' collides with canonical capability ID")
        if canonical_id not in canonical_ids:
            raise ValueError(
                f"alias '{alias}' targets unknown canonical capability ID "
                f"'{canonical_id}'"
            )


validate_alias_catalog_compatibility(CAPABILITY_CATALOG, CLI_ALIAS_TARGETS)
if frozenset(CLI_ALIAS_TARGETS) != frozenset(CLI_ALIAS_POLICIES):
    raise ValueError("every CLI alias must have exactly one policy")


def _canonical_result(requested_id: str, source: IdentifierSource) -> ResolutionResult:
    return ResolutionResult(
        requested_id=requested_id,
        canonical_id=requested_id,
        source=source,
        alias_used=False,
        alias_policy=None,
        warning_code=None,
        warning_message=None,
    )


def _alias_result(
    requested_id: str,
    source: IdentifierSource,
    canonical_id: str,
    policy: AliasPolicy,
) -> ResolutionResult:
    warning_code: str | None = None
    warning_message: str | None = None
    if policy is AliasPolicy.DEPRECATED:
        warning_code = "deprecated_algorithm_alias"
        warning_message = (
            f"Algorithm identifier '{requested_id}' is deprecated; use "
            f"'{canonical_id}' instead."
        )
        warn(warning_message, DeprecationWarning, stacklevel=3)
    return ResolutionResult(
        requested_id=requested_id,
        canonical_id=canonical_id,
        source=source,
        alias_used=True,
        alias_policy=policy,
        warning_code=warning_code,
        warning_message=warning_message,
    )


def resolve_algorithm_id(
    requested_id: str,
    source: IdentifierSource,
) -> ResolutionResult:
    """Resolve an exact identifier without registry lookup or lifecycle selection."""
    if requested_id in FORBIDDEN_ALGORITHM_REPLACEMENTS:
        raise ForbiddenAliasError(
            requested_id,
            FORBIDDEN_ALGORITHM_REPLACEMENTS[requested_id],
        )
    if requested_id in CAPABILITY_CATALOG:
        return _canonical_result(requested_id, source)
    if requested_id not in CLI_ALIAS_TARGETS:
        raise UnknownAlgorithmError(requested_id)

    canonical_id = CLI_ALIAS_TARGETS[requested_id]
    if source is not IdentifierSource.CLI:
        raise DeprecatedManifestIdentifierError(requested_id, canonical_id)
    return _alias_result(
        requested_id,
        source,
        canonical_id,
        CLI_ALIAS_POLICIES[requested_id],
    )
