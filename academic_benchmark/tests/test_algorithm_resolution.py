from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from academic_benchmark.core.algorithm_errors import (
    DeprecatedManifestIdentifierError,
    ForbiddenAliasError,
    UnknownAlgorithmError,
)
from academic_benchmark.core.algorithm_resolution import (
    CLI_ALIAS_POLICIES,
    CLI_ALIAS_TARGETS,
    FORBIDDEN_ALGORITHM_REPLACEMENTS,
    AliasPolicy,
    IdentifierSource,
    resolve_algorithm_id,
    validate_alias_catalog_compatibility,
)
from uniride_core.algorithms.capabilities import CAPABILITY_CATALOG


EXPECTED_CLI_MAPPINGS = {
    "Numba-2-opt": "Core-TwoOpt-TSP",
    "Numba-3-opt-bounded": "Core-ThreeOpt-TSP",
    "Numba-Or-opt": "Core-OrOpt-TSP",
    "Numba-GA": "Core-GA-TSP",
    "Numba-PSO": "Core-PSO-TSP",
    "GWO": "Core-GWO-TSP-Pure",
    "HHO": "Core-HHO-TSP-Pure",
    "Numba-GWO": "Core-GWO-TSP-Memetic-2opt",
    "Core-GWO-TSP": "Core-GWO-TSP-Memetic-2opt",
    "Numba-HHO": "Core-HHO-TSP-Memetic-2opt",
    "Core-HHO-TSP": "Core-HHO-TSP-Memetic-2opt",
    "SOTA-ALNS-TSP": "ALNS-TSP",
}


@pytest.mark.parametrize("requested_id,canonical_id", EXPECTED_CLI_MAPPINGS.items())
def test_cli_aliases_resolve_to_their_exact_canonical_targets(requested_id, canonical_id):
    result = resolve_algorithm_id(requested_id, IdentifierSource.CLI)

    assert result.requested_id == requested_id
    assert result.canonical_id == canonical_id
    assert result.source is IdentifierSource.CLI
    assert result.alias_used is True


@pytest.mark.parametrize("requested_id", ("GWO", "HHO"))
def test_active_short_cli_labels_do_not_emit_a_deprecation_warning(requested_id):
    result = resolve_algorithm_id(requested_id, IdentifierSource.CLI)

    assert result.alias_policy is AliasPolicy.ACTIVE
    assert result.warning_code is None
    assert result.warning_message is None


@pytest.mark.parametrize(
    "requested_id",
    tuple(key for key in EXPECTED_CLI_MAPPINGS if key not in {"GWO", "HHO"}),
)
def test_deprecated_cli_aliases_emit_stable_warning_details(requested_id):
    result = resolve_algorithm_id(requested_id, IdentifierSource.CLI)

    assert result.alias_policy is AliasPolicy.DEPRECATED
    assert result.warning_code == "deprecated_algorithm_alias"
    assert result.warning_message == (
        f"Algorithm identifier '{requested_id}' is deprecated; use "
        f"'{result.canonical_id}' instead."
    )


@pytest.mark.parametrize("requested_id", EXPECTED_CLI_MAPPINGS)
def test_manifests_reject_every_noncanonical_identifier(requested_id):
    with pytest.raises(DeprecatedManifestIdentifierError) as exc_info:
        resolve_algorithm_id(requested_id, IdentifierSource.MANIFEST)

    assert exc_info.value.code == "deprecated_manifest_identifier"
    assert exc_info.value.replacement_id == EXPECTED_CLI_MAPPINGS[requested_id]


def test_sota_alns_alias_is_deprecated_cli_only_and_canonical_stays_exact() -> None:
    with pytest.warns(DeprecationWarning, match="SOTA-ALNS-TSP"):
        cli = resolve_algorithm_id("SOTA-ALNS-TSP", IdentifierSource.CLI)
    assert cli.canonical_id == "ALNS-TSP"
    assert cli.alias_policy is AliasPolicy.DEPRECATED
    assert cli.warning_code == "deprecated_algorithm_alias"

    with pytest.raises(DeprecatedManifestIdentifierError):
        resolve_algorithm_id("SOTA-ALNS-TSP", IdentifierSource.MANIFEST)

    canonical = resolve_algorithm_id("ALNS-TSP", IdentifierSource.MANIFEST)
    assert canonical.requested_id == canonical.canonical_id == "ALNS-TSP"
    assert canonical.alias_used is False


@pytest.mark.parametrize(
    "requested_id",
    ("core-twoopt-tsp", "gwo", "NUMBA-GWO", "sota-alns-tsp"),
)
def test_case_variants_fail_instead_of_normalizing(requested_id):
    with pytest.raises(UnknownAlgorithmError) as exc_info:
        resolve_algorithm_id(requested_id, IdentifierSource.CLI)

    assert exc_info.value.code == "unknown_algorithm"


@pytest.mark.parametrize(
    "requested_id,replacement_id", FORBIDDEN_ALGORITHM_REPLACEMENTS.items()
)
def test_forbidden_pseudo_and_legacy_ids_fail_with_replacement_hints(
    requested_id, replacement_id
):
    with pytest.raises(ForbiddenAliasError) as exc_info:
        resolve_algorithm_id(requested_id, IdentifierSource.CLI)

    assert exc_info.value.code == "forbidden_alias"
    assert exc_info.value.replacement_id == replacement_id


@pytest.mark.parametrize(
    "canonical_id",
    (
        "Core-TwoOpt-TSP",
        "Core-GWO-TSP-Memetic-3opt",
    ),
)
def test_candidate_and_planned_canonical_ids_resolve_identity_without_selectability(
    canonical_id,
):
    result = resolve_algorithm_id(canonical_id, IdentifierSource.MANIFEST)

    assert result.canonical_id == canonical_id
    assert result.alias_used is False
    assert result.alias_policy is None


def test_canonical_identity_is_accepted_from_all_sources():
    for source in IdentifierSource:
        result = resolve_algorithm_id("Core-GA-TSP", source)
        assert result.canonical_id == "Core-GA-TSP"
        assert result.source is source
        assert result.alias_used is False
        assert result.warning_code is None


def test_resolution_tables_are_immutable_and_validate_against_the_catalog():
    assert isinstance(CLI_ALIAS_TARGETS, MappingProxyType)
    assert isinstance(CLI_ALIAS_POLICIES, MappingProxyType)
    assert isinstance(FORBIDDEN_ALGORITHM_REPLACEMENTS, MappingProxyType)
    with pytest.raises(TypeError):
        CLI_ALIAS_TARGETS["new"] = "Core-TwoOpt-TSP"

    validate_alias_catalog_compatibility(CAPABILITY_CATALOG, CLI_ALIAS_TARGETS)
    with pytest.raises(ValueError, match="collides with canonical"):
        validate_alias_catalog_compatibility(
            CAPABILITY_CATALOG,
            MappingProxyType({"Core-TwoOpt-TSP": "Core-GA-TSP"}),
        )


def test_resolution_result_is_frozen():
    result = resolve_algorithm_id("Core-GA-TSP", IdentifierSource.INTERNAL)

    with pytest.raises(FrozenInstanceError):
        result.canonical_id = "Core-PSO-TSP"
