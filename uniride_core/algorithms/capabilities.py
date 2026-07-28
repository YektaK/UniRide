"""Immutable, evidence-gated algorithm capability declarations.

This catalog deliberately does not inspect registries or construct solvers.  A
catalog entry becomes selectable only after a later package attaches a verified
claim with executable evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping


class ProblemContract(str, Enum):
    TSP = "tsp"
    ATSP = "atsp"


class ExecutionProtocol(str, Enum):
    FIXED_BUDGET = "fixed_budget"
    NATIVE_TERMINATION = "native_termination"


class BackendKind(str, Enum):
    NONE = "none"
    PYTHON = "python"
    NUMBA_NOPYTHON = "numba_nopython"


class BackendPolicy(str, Enum):
    PYTHON_ONLY = "python_only"
    PREFER_NUMBA_OBJECTIVE = "prefer_numba_objective"
    REQUIRE_NUMBA_OBJECTIVE = "require_numba_objective"


class LifecycleStatus(str, Enum):
    VERIFIED = "verified"
    CANDIDATE = "candidate"
    PLANNED = "planned"


class CompositionKind(str, Enum):
    PURE = "pure"
    MEMETIC_2OPT = "memetic_2opt"
    LOCAL_SEARCH = "local_search"
    POPULATION_BASED = "population_based"


@dataclass(frozen=True)
class ExecutionBackendProfile:
    objective: BackendKind
    polish: BackendKind = BackendKind.NONE


@dataclass(frozen=True)
class CapabilityClaim:
    problem: ProblemContract
    protocol: ExecutionProtocol
    backend_profile: ExecutionBackendProfile
    composition: CompositionKind
    directed_cost_preserved: bool
    exact_objective_accounting: bool
    fixed_seed_deterministic: bool
    truthful_result_reporting: bool
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AlgorithmCapability:
    canonical_id: str
    family: str
    label: str
    lifecycle: LifecycleStatus
    claims: tuple[CapabilityClaim, ...] = ()
    production_ready: bool = False
    planning_note: str | None = None


def _validate_claim(claim: CapabilityClaim) -> None:
    if not isinstance(claim.evidence_ids, tuple):
        raise ValueError("claim evidence_ids must be a tuple")
    if not claim.evidence_ids or any(not evidence_id for evidence_id in claim.evidence_ids):
        raise ValueError("capability claims require executable evidence")
    if claim.backend_profile.objective is BackendKind.NONE:
        raise ValueError("objective backend cannot be NONE")
    if claim.composition is CompositionKind.PURE and claim.backend_profile.polish is not BackendKind.NONE:
        raise ValueError("pure composition cannot include a polish backend")
    if claim.problem is ProblemContract.ATSP and not claim.directed_cost_preserved:
        raise ValueError("ATSP claims must preserve directed costs")
    if (
        claim.protocol is ExecutionProtocol.FIXED_BUDGET
        and not claim.exact_objective_accounting
    ):
        raise ValueError("fixed-budget claims require exact objective accounting")


def build_capability_catalog(
    capabilities: Iterable[AlgorithmCapability],
) -> Mapping[str, AlgorithmCapability]:
    """Validate capabilities and expose them through an immutable ID mapping."""
    entries = tuple(capabilities)
    catalog: dict[str, AlgorithmCapability] = {}
    for capability in entries:
        if not isinstance(capability.claims, tuple):
            raise ValueError("capability claims must be a tuple")
        if capability.canonical_id in catalog:
            raise ValueError("canonical capability IDs must be unique")
        if capability.production_ready:
            raise ValueError("production_ready must be False for academic catalog entries")
        if capability.lifecycle is LifecycleStatus.VERIFIED:
            if not capability.claims:
                raise ValueError("VERIFIED capabilities require at least one claim")
            for claim in capability.claims:
                _validate_claim(claim)
        else:
            if capability.claims:
                raise ValueError(f"{capability.lifecycle.name} capabilities cannot publish claims")
            if (
                capability.lifecycle is LifecycleStatus.PLANNED
                and not capability.planning_note
            ):
                raise ValueError("PLANNED capabilities require a planning note")
        catalog[capability.canonical_id] = capability
    return MappingProxyType(catalog)


def _fixed_local_search_claims(
    evidence_function: str,
) -> tuple[CapabilityClaim, ...]:
    evidence_id = (
        "academic_benchmark/tests/test_algorithm_capability_evidence.py::"
        + evidence_function
    )
    return tuple(
        CapabilityClaim(
            problem=problem,
            protocol=ExecutionProtocol.FIXED_BUDGET,
            backend_profile=ExecutionBackendProfile(BackendKind.PYTHON),
            composition=CompositionKind.LOCAL_SEARCH,
            directed_cost_preserved=problem is ProblemContract.ATSP,
            exact_objective_accounting=True,
            fixed_seed_deterministic=True,
            truthful_result_reporting=True,
            evidence_ids=(evidence_id,),
        )
        for problem in (ProblemContract.TSP, ProblemContract.ATSP)
    )


_INITIAL_CAPABILITIES: tuple[AlgorithmCapability, ...] = (
    AlgorithmCapability(
        "Core-TwoOpt-TSP", "TwoOpt", "2-opt", LifecycleStatus.VERIFIED,
        claims=_fixed_local_search_claims(
            "test_core_two_opt_fixed_tsp_and_atsp_evidence"
        ),
    ),
    AlgorithmCapability(
        "Core-ThreeOpt-TSP", "ThreeOpt", "3-opt", LifecycleStatus.VERIFIED,
        claims=_fixed_local_search_claims(
            "test_core_three_opt_fixed_tsp_and_atsp_evidence"
        ),
    ),
    AlgorithmCapability("Core-OrOpt-TSP", "OrOpt", "Or-opt", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-GA-TSP", "GA", "Genetic Algorithm", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-PSO-TSP", "PSO", "Particle Swarm Optimization", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-GWO-TSP-Pure", "GWO", "Grey Wolf Optimizer (pure)", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-HHO-TSP-Pure", "HHO", "Harris Hawks Optimizer (pure)", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-GWO-TSP-Memetic-2opt", "GWO", "Grey Wolf Optimizer (memetic 2-opt)", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-HHO-TSP-Memetic-2opt", "HHO", "Harris Hawks Optimizer (memetic 2-opt)", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("ALNS-TSP", "ALNS", "Adaptive Large Neighborhood Search", LifecycleStatus.CANDIDATE),
    AlgorithmCapability("Core-GWO-TSP-Memetic-3opt", "GWO", "Grey Wolf Optimizer (memetic 3-opt)", LifecycleStatus.PLANNED, planning_note="Reserved for the approved C2 3-opt composition."),
    AlgorithmCapability("Core-HHO-TSP-Memetic-3opt", "HHO", "Harris Hawks Optimizer (memetic 3-opt)", LifecycleStatus.PLANNED, planning_note="Reserved for the approved C2 3-opt composition."),
    AlgorithmCapability("Core-GWO-TSP-Memetic-ALNS", "GWO", "Grey Wolf Optimizer (memetic ALNS)", LifecycleStatus.PLANNED, planning_note="Reserved for the approved C2 ALNS composition."),
    AlgorithmCapability("Core-HHO-TSP-Memetic-ALNS", "HHO", "Harris Hawks Optimizer (memetic ALNS)", LifecycleStatus.PLANNED, planning_note="Reserved for the approved C2 ALNS composition."),
)

CAPABILITY_CATALOG = build_capability_catalog(_INITIAL_CAPABILITIES)


def list_algorithm_capabilities() -> tuple[AlgorithmCapability, ...]:
    """Return all discoverable capabilities as an immutable tuple."""
    return tuple(CAPABILITY_CATALOG.values())


def get_algorithm_capability(canonical_id: str) -> AlgorithmCapability | None:
    """Look up one exact, case-sensitive canonical ID without runtime inspection."""
    return CAPABILITY_CATALOG.get(canonical_id)


def find_capability_claim(
    canonical_id: str,
    *,
    problem: ProblemContract,
    protocol: ExecutionProtocol,
    backend_profile: ExecutionBackendProfile,
    composition: CompositionKind,
) -> CapabilityClaim | None:
    """Find an exact verified claim; candidates and plans always return ``None``."""
    capability = get_algorithm_capability(canonical_id)
    if capability is None or capability.lifecycle is not LifecycleStatus.VERIFIED:
        return None
    for claim in capability.claims:
        if (
            claim.problem is problem
            and claim.protocol is protocol
            and claim.backend_profile == backend_profile
            and claim.composition is composition
        ):
            return claim
    return None
