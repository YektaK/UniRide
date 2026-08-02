"""Invariant tests for the immutable academic capability catalog."""

from dataclasses import FrozenInstanceError

import pytest

from uniride_core.algorithms.capabilities import (
    AlgorithmCapability,
    BackendKind,
    CapabilityClaim,
    CompositionKind,
    ExecutionBackendProfile,
    ExecutionProtocol,
    LifecycleStatus,
    ProblemContract,
    build_capability_catalog,
    find_capability_claim,
    get_algorithm_capability,
    list_algorithm_capabilities,
)


def _academic_registry_ids() -> frozenset[str]:
    """Return academic executor keys after canonical setup registration."""
    from academic_benchmark.core import registry_setup  # noqa: F401
    from academic_benchmark.engine_core import AlgorithmRegistry

    return frozenset(AlgorithmRegistry.list_algorithms())


def valid_claim(**overrides):
    values = {
        "problem": ProblemContract.TSP,
        "protocol": ExecutionProtocol.FIXED_BUDGET,
        "backend_profile": ExecutionBackendProfile(BackendKind.PYTHON),
        "composition": CompositionKind.PURE,
        "directed_cost_preserved": False,
        "exact_objective_accounting": True,
        "fixed_seed_deterministic": True,
        "truthful_result_reporting": True,
        "evidence_ids": ("test_capability_contract",),
    }
    values.update(overrides)
    return CapabilityClaim(**values)


def verified_capability(**overrides):
    values = {
        "canonical_id": "Core-X-TSP",
        "family": "X",
        "label": "X",
        "lifecycle": LifecycleStatus.VERIFIED,
        "claims": (valid_claim(),),
    }
    values.update(overrides)
    return AlgorithmCapability(**values)


@pytest.mark.parametrize("entries", [
    (verified_capability(), verified_capability()),
])
def test_catalog_rejects_duplicate_canonical_ids(entries):
    with pytest.raises(ValueError, match="unique"):
        build_capability_catalog(entries)


def test_verified_requires_a_claim():
    with pytest.raises(ValueError, match="require at least one claim"):
        build_capability_catalog([
            verified_capability(claims=()),
        ])


@pytest.mark.parametrize("lifecycle", [LifecycleStatus.CANDIDATE, LifecycleStatus.PLANNED])
def test_unverified_lifecycle_cannot_publish_claims(lifecycle):
    with pytest.raises(ValueError, match="cannot publish claims"):
        build_capability_catalog([
            verified_capability(lifecycle=lifecycle),
        ])


def test_claim_requires_executable_evidence():
    with pytest.raises(ValueError, match="evidence"):
        build_capability_catalog([
            verified_capability(claims=(valid_claim(evidence_ids=()),)),
        ])


def test_claim_objective_cannot_be_none():
    with pytest.raises(ValueError, match="objective backend"):
        build_capability_catalog([
            verified_capability(
                claims=(valid_claim(
                    backend_profile=ExecutionBackendProfile(BackendKind.NONE),
                ),),
            ),
        ])


def test_pure_claim_cannot_include_polish_backend():
    with pytest.raises(ValueError, match="pure composition"):
        build_capability_catalog([
            verified_capability(
                claims=(valid_claim(
                    backend_profile=ExecutionBackendProfile(
                        BackendKind.PYTHON, BackendKind.PYTHON,
                    ),
                ),),
            ),
        ])


def test_atsp_claim_requires_directed_cost_preservation():
    with pytest.raises(ValueError, match="ATSP"):
        build_capability_catalog([
            verified_capability(
                claims=(valid_claim(problem=ProblemContract.ATSP),),
            ),
        ])


def test_fixed_budget_claim_requires_exact_accounting():
    with pytest.raises(ValueError, match="fixed-budget"):
        build_capability_catalog([
            verified_capability(
                claims=(valid_claim(exact_objective_accounting=False),),
            ),
        ])


def test_catalog_rejects_production_ready_entries():
    with pytest.raises(ValueError, match="production_ready"):
        build_capability_catalog([
            verified_capability(production_ready=True),
        ])


def test_planned_entry_requires_a_note():
    with pytest.raises(ValueError, match="planning note"):
        build_capability_catalog([
            AlgorithmCapability(
                canonical_id="Core-X-TSP-Planned",
                family="X",
                label="X",
                lifecycle=LifecycleStatus.PLANNED,
            ),
        ])


def test_catalog_and_nested_values_are_immutable():
    capability = verified_capability()
    catalog = build_capability_catalog([capability])

    with pytest.raises(TypeError):
        catalog["Core-Y-TSP"] = capability
    with pytest.raises(FrozenInstanceError):
        capability.label = "changed"
    with pytest.raises(FrozenInstanceError):
        capability.claims[0].backend_profile.objective = BackendKind.NUMBA_NOPYTHON


def test_catalog_rejects_mutable_claim_and_evidence_collections():
    mutable_evidence = ["test_capability_contract"]
    claim = valid_claim(evidence_ids=mutable_evidence)
    mutable_claims = [claim]
    capability = verified_capability(claims=mutable_claims)

    with pytest.raises(ValueError, match="tuple"):
        build_capability_catalog([capability])

    mutable_evidence.append("later_evidence")
    mutable_claims.clear()
    assert claim.evidence_ids == ["test_capability_contract", "later_evidence"]
    assert capability.claims == []


def test_catalog_rejects_mutable_evidence_collection_with_tuple_claims():
    claim = valid_claim(evidence_ids=["test_capability_contract"])
    capability = verified_capability(claims=(claim,))

    with pytest.raises(ValueError, match="tuple"):
        build_capability_catalog([capability])


def test_default_catalog_contains_only_evidence_gated_lifecycles():
    catalog = list_algorithm_capabilities()

    assert isinstance(catalog, tuple)
    assert {capability.canonical_id for capability in catalog} == {
        "Core-TwoOpt-TSP",
        "Core-ThreeOpt-TSP",
        "Core-OrOpt-TSP",
        "Core-GA-TSP",
        "Core-PSO-TSP",
        "Core-GWO-TSP-Pure",
        "Core-HHO-TSP-Pure",
        "Core-GWO-TSP-Memetic-2opt",
        "Core-HHO-TSP-Memetic-2opt",
        "ALNS-TSP",
        "Core-GWO-TSP-Memetic-3opt",
        "Core-HHO-TSP-Memetic-3opt",
        "Core-GWO-TSP-Memetic-ALNS",
        "Core-HHO-TSP-Memetic-ALNS",
    }
    verified = {
        capability.canonical_id
        for capability in catalog
        if capability.lifecycle is LifecycleStatus.VERIFIED
    }
    assert verified == {
        "Core-TwoOpt-TSP",
        "Core-ThreeOpt-TSP",
        "Core-GWO-TSP-Pure",
        "Core-HHO-TSP-Pure",
        "Core-GWO-TSP-Memetic-2opt",
        "Core-HHO-TSP-Memetic-2opt",
        "Core-OrOpt-TSP",
    }
    assert all(
        bool(capability.claims) is (capability.canonical_id in verified)
        for capability in catalog
    )
    assert get_algorithm_capability("Core-TwoOpt-TSP") is not None
    assert find_capability_claim(
        "Core-TwoOpt-TSP",
        problem=ProblemContract.TSP,
        protocol=ExecutionProtocol.FIXED_BUDGET,
        backend_profile=ExecutionBackendProfile(BackendKind.PYTHON),
        composition=CompositionKind.LOCAL_SEARCH,
    ) is not None


@pytest.mark.parametrize(
    ("algorithm_id", "evidence_function"),
    [
        (
            "Core-TwoOpt-TSP",
            "test_core_two_opt_direct_native_tsp_and_atsp_evidence",
        ),
        (
            "Core-ThreeOpt-TSP",
            "test_core_three_opt_direct_native_tsp_and_atsp_evidence",
        ),
    ],
)
def test_canonical_local_search_native_claims_are_evidence_gated(
    algorithm_id, evidence_function
):
    capability = get_algorithm_capability(algorithm_id)
    assert capability is not None

    native_claims = [
        claim
        for claim in capability.claims
        if claim.protocol is ExecutionProtocol.NATIVE_TERMINATION
    ]
    assert {claim.problem for claim in native_claims} == {
        ProblemContract.TSP,
        ProblemContract.ATSP,
    }
    for claim in native_claims:
        assert claim.backend_profile == ExecutionBackendProfile(BackendKind.PYTHON)
        assert claim.composition is CompositionKind.LOCAL_SEARCH
        assert claim.directed_cost_preserved is (claim.problem is ProblemContract.ATSP)
        assert claim.exact_objective_accounting is True
        assert claim.fixed_seed_deterministic is True
        assert claim.truthful_result_reporting is True
        assert claim.evidence_ids == (
            "academic_benchmark/tests/test_native_termination_protocol.py::"
            + evidence_function,
        )


def test_verified_capabilities_have_exact_canonical_academic_executors():
    """Selectable catalog identities must remain direct academic registry keys."""
    from academic_benchmark.engine_core import AlgorithmRegistry

    registry_ids = _academic_registry_ids()
    verified_ids = {
        capability.canonical_id
        for capability in list_algorithm_capabilities()
        if capability.lifecycle is LifecycleStatus.VERIFIED
    }

    assert verified_ids == {
        "Core-TwoOpt-TSP",
        "Core-ThreeOpt-TSP",
        "Core-GWO-TSP-Pure",
        "Core-HHO-TSP-Pure",
        "Core-GWO-TSP-Memetic-2opt",
        "Core-HHO-TSP-Memetic-2opt",
        "Core-OrOpt-TSP",
    }
    assert verified_ids <= registry_ids
    for canonical_id in verified_ids:
        assert callable(AlgorithmRegistry.get_executor(canonical_id))


def test_catalog_lifecycle_truth_matches_academic_executor_availability():
    """C1 candidates are implemented but unselectable; C2 reservations are absent."""
    registry_ids = _academic_registry_ids()
    lifecycle_by_id = {
        capability.canonical_id: capability.lifecycle
        for capability in list_algorithm_capabilities()
    }

    assert lifecycle_by_id == {
        "Core-TwoOpt-TSP": LifecycleStatus.VERIFIED,
        "Core-ThreeOpt-TSP": LifecycleStatus.VERIFIED,
        "Core-OrOpt-TSP": LifecycleStatus.VERIFIED,
        "Core-GA-TSP": LifecycleStatus.CANDIDATE,
        "Core-PSO-TSP": LifecycleStatus.CANDIDATE,
        "Core-GWO-TSP-Pure": LifecycleStatus.VERIFIED,
        "Core-HHO-TSP-Pure": LifecycleStatus.VERIFIED,
        "Core-GWO-TSP-Memetic-2opt": LifecycleStatus.VERIFIED,
        "Core-HHO-TSP-Memetic-2opt": LifecycleStatus.VERIFIED,
        "ALNS-TSP": LifecycleStatus.CANDIDATE,
        "Core-GWO-TSP-Memetic-3opt": LifecycleStatus.PLANNED,
        "Core-HHO-TSP-Memetic-3opt": LifecycleStatus.PLANNED,
        "Core-GWO-TSP-Memetic-ALNS": LifecycleStatus.PLANNED,
        "Core-HHO-TSP-Memetic-ALNS": LifecycleStatus.PLANNED,
    }

    candidate_ids = {
        canonical_id
        for canonical_id, lifecycle in lifecycle_by_id.items()
        if lifecycle is LifecycleStatus.CANDIDATE
    }
    planned_ids = {
        canonical_id
        for canonical_id, lifecycle in lifecycle_by_id.items()
        if lifecycle is LifecycleStatus.PLANNED
    }

    missing_candidate_executors = candidate_ids - registry_ids
    unexpected_planned_executors = planned_ids & registry_ids
    assert not missing_candidate_executors, (
        "implemented CANDIDATE canonical IDs must retain academic executors: "
        f"{sorted(missing_candidate_executors)}"
    )
    assert not unexpected_planned_executors, (
        "PLANNED canonical IDs must not acquire academic executors: "
        f"{sorted(unexpected_planned_executors)}"
    )
