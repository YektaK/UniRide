"""Gate D, D-01: the comparison identity below the pooling group (plan section 3, D-01; DECISION_LOG A18, A17).

``assert_single_pooling_group`` only separates fixed / native / exact rows. Rows may be aggregated or tested together
only when their ``ComparisonCellKey`` is equal, except for the dimension being compared. The tests build real
``RunManifestV1`` objects (the contract exists; its writer is D-02) and minimal protocol rows.
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from academic_benchmark import protocol_registry
from academic_benchmark.analysis import identity
from academic_benchmark.analysis.identity import (
    ComparisonIdentityError,
    assert_single_comparison_family,
    comparison_cell_key,
    configuration_hash,
    normalise_termination_policy,
)
from academic_benchmark.contracts import RunManifestV1

REPO = Path(__file__).resolve().parents[2]
COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
FAIR_V2 = "uniride-fair-tsp-v2"
FAIR_V1 = "uniride-fair-tsp-v1"
NATIVE = "uniride-native-tsp-v1"
PSO_POLICY = (
    "atomic_upper_bound_v1;max_iterations=1237500;max_no_improvement=1237500;reinit_interval=50;"
    "reinit_random_fraction=0.1;reinit_max_swaps=3"
)


def _dataset(dataset_id="tsplib-eil51", dimension=51):
    return {
        "schema_version": "uniride-dataset/v1", "dataset_id": dataset_id,
        "artifact_path": f"academic_benchmark/tsplib_data/tsp/{dataset_id}.tsp",
        "source": {"authority_url": "https://example.invalid/x", "retrieved_on": "2026-10-19"},
        "checksum": {"algorithm": "sha256", "value": "0" * 64}, "problem_type": "TSP", "dimension": dimension,
        "matrix_semantics": {"directed": False, "edge_weight_type": "EUC_2D", "diagonal_semantics": "zero"},
        "best_known": {"status": "optimal", "value": 426.0, "provenance": "fixture"},
    }


def make_manifest(*, study_id="bildiri2026", protocol_version=FAIR_V2, algorithm_id="Core-PSO-TSP",
                  configuration=None, levels=(63750, 318750), policy="atomic_upper_bound_v1", base_seed=2026,
                  commit=COMMIT_A, dirty=False, dataset_id="tsplib-eil51", dimension=51,
                  backend_policy="prefer_numba", backend_profile=None) -> RunManifestV1:
    return RunManifestV1.model_validate({
        "schema_version": "uniride-run/v1", "run_id": "run-0001", "study_id": study_id,
        "protocol_version": protocol_version, "git": {"commit": commit, "dirty": dirty},
        "environment": {"python": "3.13", "operating_system": "test", "cpu": "test", "numpy": "2.4.6",
                        "numba": "0.66.0", "llvmlite": "0.48.0", "statistics_library": "none"},
        "dataset": _dataset(dataset_id, dimension),
        "algorithm": {
            "algorithm_id": algorithm_id, "capabilities": {}, "backend_policy": backend_policy,
            "backend_profile": backend_profile or {"objective": "numba", "polish": "none"},
            "capability_evidence_ids": ["fixture"],
            "configuration": configuration if configuration is not None
            else {"swarm_size": 50, "max_iterations": 1237500, "reinit_interval": 50},
            "composition_stages": [],
        },
        "seeds": {"base_seed": base_seed, "derived": {"0": 1}},
        "budget": {"levels": list(levels), "policy": policy, "objective_evaluations": 5, "stage_allocation": {}},
        "termination": {"reason": "evaluation_budget_exhausted", "runtime_seconds": 0.1},
        "validation": {"passed": True, "checks": ["hamiltonian"]}, "outputs": [],
    })


def make_row(*, protocol_version=FAIR_V2, algorithm_id="Core-PSO-TSP", problem="eil51", budget=63750,
             termination_policy=PSO_POLICY, study_id="bildiri2026", **extra):
    native = protocol_version == NATIVE
    row = {
        "protocol_version": protocol_version,
        "comparison_regime": "algorithm_native_termination" if native else "fixed_evaluation_budget",
        "problem": problem, "algorithm_id": algorithm_id, "variant": "pure", "study_id": study_id,
        "evaluation_budget": None if native else budget, "termination_policy": termination_policy,
        "polish_policy": {"enabled": False, "initial": False, "periodic": False, "final": False, "operator": None},
        "objective_cost": 430.0, "elapsed_ms": 12.5, "replicate": 0,
    }
    row.update(extra)
    return row


def native_pair(**overrides):
    return make_row(protocol_version=NATIVE, termination_policy="algorithm_native_termination;max_iterations=2",
                    **overrides), make_manifest(protocol_version=NATIVE, policy="native_uncapped",
                                                levels=(1,))


def pair(row_kw=None, manifest_kw=None):
    return make_row(**(row_kw or {})), make_manifest(**(manifest_kw or {}))


# ------------------------------------------------------------------ the five red tests named in the plan
def test_fair_v1_and_fair_v2_rows_are_one_pooling_group_but_not_one_comparison_cell():
    v1, v2 = pair({"protocol_version": FAIR_V1}, {"protocol_version": FAIR_V1}), pair()
    # the registry still lumps them (protocol_registry.py:88-89; D-01 does not change it) ...
    assert protocol_registry.assert_single_pooling_group([v1[0], v2[0]]) == "fixed_budget"
    # ... so the comparison identity must separate them
    assert comparison_cell_key(*v1) != comparison_cell_key(*v2)
    with pytest.raises(ComparisonIdentityError, match="protocol_version"):
        assert_single_comparison_family([v1, v2])


def test_rows_that_differ_only_in_timing_have_the_same_key_and_digest():
    base_row = make_row(composition={"stages": [{"name": "global", "elapsed_sec": 0.5}]})
    other_row = make_row(elapsed_ms=999.0, composition={"stages": [{"name": "global", "elapsed_sec": 7.25}]})
    manifest = make_manifest()
    a, b = comparison_cell_key(base_row, manifest), comparison_cell_key(other_row, manifest)
    assert a == b and a.digest() == b.digest()
    assert configuration_hash(base_row, manifest) == configuration_hash(other_row, manifest)
    assert assert_single_comparison_family([(base_row, manifest), (other_row, manifest)]).size == 2


def test_a_changed_pso_termination_constant_gives_a_different_key():
    changed = PSO_POLICY.replace("reinit_random_fraction=0.1", "reinit_random_fraction=0.2")
    assert changed != PSO_POLICY
    a, b = pair(), pair({"termination_policy": changed})
    assert configuration_hash(*a) != configuration_hash(*b)
    assert comparison_cell_key(*a) != comparison_cell_key(*b)
    with pytest.raises(ComparisonIdentityError, match="configuration_hash"):
        assert_single_comparison_family([a, b])


def test_the_real_bildiri_levels_give_eil51_and_kroa100_the_same_level_index_zero():
    profile = json.loads((REPO / "academic_benchmark/studies/bildiri2026/study.json").read_text(encoding="utf-8"))
    table = profile["scaled_fixed_budget_levels"]["levels_by_dataset"]
    eil51, kroa100 = table["tsplib-eil51"], table["tsplib-kroa100"]
    assert (eil51[0], kroa100[0]) == (63750, 247500)
    a = pair({"problem": "eil51", "budget": eil51[0]}, {"levels": eil51})
    b = pair({"problem": "kroA100", "budget": kroa100[0]},
             {"levels": kroa100, "dataset_id": "tsplib-kroa100", "dimension": 100})
    key_a, key_b = comparison_cell_key(*a), comparison_cell_key(*b)
    assert key_a.budget_level_index == key_b.budget_level_index == 0
    assert key_a.dataset_identity == "eil51" and key_b.dataset_identity == "kroa100"
    family = assert_single_comparison_family([a, b], vary=("dataset",))  # one cross-instance family
    assert family.size == 2
    with pytest.raises(ComparisonIdentityError, match="dataset_identity"):
        assert_single_comparison_family([a, b])  # but never one cell
    # level 1 of one instance is not level 0 of the other, whatever the raw numbers
    c = pair({"problem": "eil51", "budget": eil51[1]}, {"levels": eil51})
    with pytest.raises(ComparisonIdentityError, match="budget_level_index"):
        assert_single_comparison_family([c, b], vary=("dataset",))


def test_a_row_without_a_run_manifest_such_as_a_pre_c16a_core_ga_row_is_refused():
    row = make_row(algorithm_id="Core-GA-TSP")
    with pytest.raises(ComparisonIdentityError, match="no run manifest"):
        comparison_cell_key(row, None)
    with pytest.raises(ComparisonIdentityError, match="no run manifest"):
        assert_single_comparison_family([(row, None)])


# ------------------------------------------------------------------ every key field splits a cell
CHANGES = {
    "protocol_version": ({"protocol_version": FAIR_V1}, {"protocol_version": FAIR_V1}),
    "study_id": ({"study_id": "yaem2026"}, {"study_id": "yaem2026"}),
    "dataset_identity": ({"problem": "st70"}, {"dataset_id": "tsplib-st70", "dimension": 70}),
    "backend_policy": ({}, {"backend_policy": "python_only"}),
    "backend_profile": ({}, {"backend_profile": {"objective": "python", "polish": "none"}}),
    "budget_level_index": ({"budget": 318750}, {}),
    "algorithm_id": ({"algorithm_id": "Core-GA-TSP"}, {"algorithm_id": "Core-GA-TSP"}),
    "configuration_hash": ({}, {"configuration": {"swarm_size": 20, "max_iterations": 1237500}}),
    "base_seed": ({}, {"base_seed": 2027}),
    "code_commit": ({}, {"commit": COMMIT_B}),
}


@pytest.mark.parametrize("field", sorted(CHANGES))
def test_each_key_field_splits_a_comparison_cell_and_equal_rows_are_accepted(field):
    row_kw, manifest_kw = CHANGES[field]
    base, changed = pair(), pair(row_kw, manifest_kw)
    assert comparison_cell_key(*base) != comparison_cell_key(*changed)
    with pytest.raises(ComparisonIdentityError, match=field):
        assert_single_comparison_family([base, changed])
    assert assert_single_comparison_family([base, pair()]).size == 2


def test_the_evidence_class_splits_a_cell_and_an_unknown_class_is_refused():
    current = pair()
    historical = (make_row(evidence_class="historical_unverified"), make_manifest())
    assert comparison_cell_key(*historical).evidence_class == "historical_unverified"
    assert comparison_cell_key(*current).evidence_class == "current"
    assert comparison_cell_key(make_row(evidence_class="current"), make_manifest()) == comparison_cell_key(*current)
    with pytest.raises(ComparisonIdentityError, match="evidence_class"):
        assert_single_comparison_family([current, historical])
    for label in ("INVALID", "REFERENCE_ONLY", "", 7):
        with pytest.raises(ComparisonIdentityError, match="evidence_class"):
            comparison_cell_key(make_row(evidence_class=label), make_manifest())


# ------------------------------------------------------------------ what is part of the configuration
def test_outcome_valued_policy_segments_do_not_split_a_configuration():
    """``budget_exhausted``, ``polish_derived_seed`` and ``global_cap`` describe the run or the level, not the
    configuration (registry_setup.py local-search and composite termination_policy); without this a cell would
    fall apart per replicate and per instance."""
    ls = "atomic_upper_bound_v1;max_iterations=1000;budget_exhausted={}"
    assert (normalise_termination_policy(ls.format(True)) == normalise_termination_policy(ls.format(False))
            == "atomic_upper_bound_v1;max_iterations=1000")
    composite = ("atomic_upper_bound_v1;composition=global_then_final_alns;global_fraction=0.8;global_cap={cap};"
                 "global_max_iterations=60000;polish_alns_params=a=1;polish_derived_seed={seed};x=1")
    one, two = composite.format(cap=1000, seed=11), composite.format(cap=2000, seed=99)
    assert normalise_termination_policy(one) == normalise_termination_policy(two)
    a = pair({"termination_policy": one})
    b = pair({"termination_policy": two})
    assert configuration_hash(*a) == configuration_hash(*b)
    # but a changed configured value still splits (global_fraction is configuration)
    c = pair({"termination_policy": one.replace("global_fraction=0.8", "global_fraction=0.7")})
    assert configuration_hash(*a) != configuration_hash(*c)


def test_protocol_comparison_blocks_in_the_configuration_do_not_split_levels_or_instances():
    """The protocol manifest echoed into the parameters carries the level and base seed, which have their own key fields."""
    fair = {"protocol_version": FAIR_V2, "base_seed": 2026, "evaluation_budget": 63750, "budget_policy": "x"}
    other = {**fair, "evaluation_budget": 247500}
    a = pair(manifest_kw={"configuration": {"swarm_size": 50, "fair_comparison": fair}})
    b = pair(manifest_kw={"configuration": {"swarm_size": 50, "fair_comparison": other}})
    assert configuration_hash(*a) == configuration_hash(*b)
    c = pair(manifest_kw={"configuration": {"swarm_size": 51, "fair_comparison": fair}})
    assert configuration_hash(*a) != configuration_hash(*c)


def test_the_polish_policy_outcome_flags_are_not_a_grouping_key():
    """A17 C-04: ``polish_policy.final`` varies by replicate; the other flags and counts are results too."""
    a = pair({"polish_policy": {"enabled": True, "initial": True, "periodic": True, "final": True,
                                "operator": "2-opt", "executed": {"final": 1}, "evaluations": {"final": 9}}})
    b = pair({"polish_policy": {"enabled": True, "initial": True, "periodic": True, "final": False,
                                "operator": "2-opt", "executed": {"final": 0}, "evaluations": {"final": 0}}})
    assert comparison_cell_key(*a) == comparison_cell_key(*b)


# ------------------------------------------------------------------ families
def test_an_algorithm_family_allows_different_algorithms_but_one_configuration_per_algorithm():
    pso = pair()
    ga = pair({"algorithm_id": "Core-GA-TSP"},
              {"algorithm_id": "Core-GA-TSP", "configuration": {"population_size": 20}})
    family = assert_single_comparison_family([pso, ga, pair()], vary=("algorithm",))
    assert family.size == 3 and family.pooling_group == "fixed_budget"
    assert "algorithm_id" not in family.shared and family.shared["code_commit"] == COMMIT_A
    pso_other = pair(manifest_kw={"configuration": {"swarm_size": 20}})
    with pytest.raises(ComparisonIdentityError, match="more than one configuration"):
        assert_single_comparison_family([pso, ga, pso_other], vary=("algorithm",))
    # the other fields stay equal inside the family
    other_commit = pair({"algorithm_id": "Core-GA-TSP"},
                        {"algorithm_id": "Core-GA-TSP", "configuration": {"population_size": 20}, "commit": COMMIT_B})
    with pytest.raises(ComparisonIdentityError, match="code_commit"):
        assert_single_comparison_family([pso, other_commit], vary=("algorithm",))


def test_a_friedman_style_family_varies_algorithm_and_dataset_together_but_nothing_else():
    cells = [
        pair({"problem": p, "algorithm_id": a, "budget": 1 if p == "eil51" else 5},
             {"algorithm_id": a, "configuration": {"k": a}, "levels": (1, 2) if p == "eil51" else (5, 6),
              "dataset_id": f"tsplib-{p}"})
        for p in ("eil51", "st70") for a in ("Core-PSO-TSP", "Core-GA-TSP")
    ]
    assert assert_single_comparison_family(cells, vary=("algorithm", "dataset")).size == 4
    with pytest.raises(ComparisonIdentityError, match="dataset_identity"):
        assert_single_comparison_family(cells, vary=("algorithm",))
    with pytest.raises(ComparisonIdentityError, match="algorithm_id"):
        assert_single_comparison_family(cells, vary=("dataset",))


def test_an_unknown_vary_dimension_and_no_rows_are_handled_explicitly():
    with pytest.raises(ValueError, match="vary"):
        assert_single_comparison_family([pair()], vary=("seed",))
    assert assert_single_comparison_family([]) is None


# ------------------------------------------------------------------ the pooling-group guard stays first
def test_mixed_fixed_and_native_rows_fail_on_the_pooling_group_before_any_key_is_built():
    with pytest.raises(ValueError, match="different pooling groups") as caught:
        assert_single_comparison_family([pair(), native_pair()])
    assert not isinstance(caught.value, ComparisonIdentityError)


def test_assert_single_comparison_family_calls_the_pooling_group_guard_before_building_any_key():
    tree = ast.parse(Path(identity.__file__).read_text(encoding="utf-8"))
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "assert_single_comparison_family")
    calls = sorted(
        ((c.lineno, c.col_offset, c.func.id if isinstance(c.func, ast.Name) else getattr(c.func, "attr", ""))
         for c in ast.walk(func) if isinstance(c, ast.Call)),
    )
    names = [name for _, _, name in calls]
    assert "assert_single_pooling_group" in names and "comparison_cell_key" in names
    assert names.index("assert_single_pooling_group") < names.index("comparison_cell_key")


def test_exact_union_and_joint_rows_never_get_a_comparison_key():
    for row in ({"protocol": "exact_reference_v1"}, {"protocol": "union_day_v1"}, {"protocol": "exact_day_joint_v1"}):
        with pytest.raises(ComparisonIdentityError, match="never ranked|rankable"):
            comparison_cell_key(row, make_manifest())


# ------------------------------------------------------------------ the row must match its manifest
@pytest.mark.parametrize("row_kw, manifest_kw, text", [
    ({"algorithm_id": "Core-GA-TSP"}, {}, "algorithm_id"),
    ({"protocol_version": FAIR_V1}, {}, "protocol_version"),
    ({"study_id": "yaem2026"}, {}, "study_id"),
    ({"budget": 12345}, {}, "not one of the manifest levels"),
    ({"budget": True}, {}, "integer"),
    ({"budget": None}, {}, "evaluation_budget"),
    ({}, {"levels": (7, 7)}, "unique"),
    ({"dataset_id": "tsplib-st70"}, {}, "dataset_id"),
    ({"problem": ""}, {}, "problem"),
])
def test_a_row_that_disagrees_with_its_manifest_is_refused(row_kw, manifest_kw, text):
    with pytest.raises(ComparisonIdentityError, match=text):
        comparison_cell_key(*pair(row_kw, manifest_kw))


def test_native_rows_carry_no_level_and_a_budget_on_a_native_row_is_refused():
    row, manifest = native_pair()
    key = comparison_cell_key(row, manifest)
    assert key.pooling_group == "native" and key.budget_level_index is None
    bad_row, bad_manifest = native_pair(evaluation_budget=5)
    with pytest.raises(ComparisonIdentityError, match="native"):
        comparison_cell_key(bad_row, bad_manifest)


def test_a_dirty_tree_has_no_code_identity_unless_the_caller_allows_it():
    row, manifest = make_row(), make_manifest(dirty=True)
    with pytest.raises(ComparisonIdentityError, match="dirty"):
        comparison_cell_key(row, manifest)
    key = comparison_cell_key(row, manifest, allow_dirty=True)
    assert key.tree_dirty is True and key != comparison_cell_key(make_row(), make_manifest())
    with pytest.raises(ComparisonIdentityError, match="dirty"):
        assert_single_comparison_family([(row, manifest)])


def test_the_key_is_deterministic_hashable_and_does_not_mutate_its_inputs():
    row, manifest = make_row(), make_manifest()
    before = copy.deepcopy(row)
    key = comparison_cell_key(row, manifest)
    assert row == before
    assert len({key, comparison_cell_key(row, manifest)}) == 1
    assert key.seed_protocol_version == identity.SEED_PROTOCOL_VERSION
    assert len(key.digest()) == 64 and key.digest() == comparison_cell_key(row, manifest).digest()
    assert key.as_dict()["code_commit"] == COMMIT_A


def test_the_seed_protocol_constant_equals_the_one_the_study_service_implements():
    from academic_benchmark.studies.service import SUPPORTED_SEED_PROTOCOL
    assert identity.SEED_PROTOCOL_VERSION == SUPPORTED_SEED_PROTOCOL


# ------------------------------------------------------------------ DUZELT round 1 (Opus review of D-01)
def test_a_row_for_one_instance_with_another_instances_manifest_is_refused():
    """Pilot and CLI rows carry no dataset_id; the problem name must match the manifest's dataset (tsplib-<name>)."""
    with pytest.raises(ComparisonIdentityError, match="dataset"):
        comparison_cell_key(make_row(problem="st70"), make_manifest())  # eil51 manifest, st70 row
    with pytest.raises(ComparisonIdentityError, match="dataset"):
        assert_single_comparison_family([pair({"problem": "st70"})], vary=("dataset",))


def test_a_row_without_dataset_id_is_matched_to_its_manifest_by_the_normalised_tsplib_name():
    row = make_row(problem="kroA100")
    assert "dataset_id" not in row
    key = comparison_cell_key(row, make_manifest(dataset_id="tsplib-kroa100", dimension=100))
    assert key.dataset_identity == "kroa100"
    # a manifest dataset id that is not tsplib-<name> cannot be verified from the problem name alone
    with pytest.raises(ComparisonIdentityError, match="dataset"):
        comparison_cell_key(row, make_manifest(dataset_id="my-own-set", dimension=100))
    # an explicit row dataset_id that equals the manifest's is the check (smoke rows)
    assert comparison_cell_key(make_row(dataset_id="my-own-set"), make_manifest(dataset_id="my-own-set"))


def test_a_fixed_budget_row_needs_the_atomic_upper_bound_budget_policy():
    """``RunManifestV1.budget.policy`` allows two values; a fixed row under the native one is a contradiction."""
    with pytest.raises(ComparisonIdentityError, match="budget.policy"):
        comparison_cell_key(*pair(manifest_kw={"policy": "native_uncapped"}))
    assert comparison_cell_key(*pair(manifest_kw={"policy": "atomic_upper_bound_v1"}))


def test_a_native_row_needs_the_native_uncapped_budget_policy():
    row, manifest = native_pair()
    bad = make_manifest(protocol_version=NATIVE, policy="atomic_upper_bound_v1", levels=(1,))
    with pytest.raises(ComparisonIdentityError, match="budget.policy"):
        comparison_cell_key(row, bad)
    assert comparison_cell_key(row, manifest).budget_level_index is None


def test_python_and_numba_backend_rows_never_share_a_cell_until_the_owner_decides_otherwise():
    numba = pair()
    python = pair(manifest_kw={"backend_policy": "python_only", "backend_profile": {"objective": "python", "polish": "none"}})
    key_n, key_p = comparison_cell_key(*numba), comparison_cell_key(*python)
    assert key_n.backend_policy == "prefer_numba" and key_n.backend_profile == "objective=numba;polish=none"
    assert key_p.backend_profile == "objective=python;polish=none"
    with pytest.raises(ComparisonIdentityError, match="backend"):
        assert_single_comparison_family([numba, python], vary=("algorithm",))


def test_a_family_built_with_allow_dirty_says_so():
    clean = assert_single_comparison_family([pair(), pair()])
    assert clean.contains_dirty is False
    dirty = [(make_row(), make_manifest(dirty=True)), (make_row(replicate=1), make_manifest(dirty=True))]
    family = assert_single_comparison_family(dirty, allow_dirty=True)
    assert family.contains_dirty is True and family.shared["tree_dirty"] is True
    with pytest.raises(ComparisonIdentityError, match="dirty"):
        assert_single_comparison_family(dirty)


@pytest.mark.parametrize("marker", [{"record_kind": "failed_run"}, {"validation_status": "failed"}])
def test_a_failed_run_row_is_refused_with_its_own_message(marker):
    row = make_row(**marker)
    with pytest.raises(ComparisonIdentityError, match="failed run"):
        comparison_cell_key(row, make_manifest())
    with pytest.raises(ComparisonIdentityError, match="failed run"):
        assert_single_comparison_family([(row, make_manifest())])
    # a failed-run record from the smoke runner has no termination_policy at all; the message must still name the failure
    bare = {**marker, "protocol_version": FAIR_V2, "comparison_regime": "fixed_evaluation_budget",
            "problem": "eil51", "algorithm_id": "Core-PSO-TSP"}
    with pytest.raises(ComparisonIdentityError, match="failed run"):
        comparison_cell_key(bare, make_manifest())


# ------------------------------------------------------------------ DUZELT round 2
PY_NONE = {"objective": "python", "polish": "none"}
NUMBA_NONE = {"objective": "numba", "polish": "none"}
NUMBA_PY = {"objective": "numba", "polish": "python"}


def _algo(algorithm_id, profile, configuration):
    return pair({"algorithm_id": algorithm_id},
                {"algorithm_id": algorithm_id, "backend_profile": profile, "configuration": configuration})


def test_an_algorithm_family_over_algorithms_with_different_backends_is_accepted():
    """Local search runs on Python, GA/PSO on a Numba objective, memetic IDs add a Python polish (registry_setup.py);
    a cross-algorithm family over the real Bildiri set must not be refused on the backend profile."""
    items = [
        _algo("Core-TwoOpt-TSP", PY_NONE, {"max_iterations": 1000}),
        _algo("Core-GA-TSP", NUMBA_NONE, {"population_size": 20}),
        _algo("Core-GA-TSP-Memetic-2opt", NUMBA_PY, {"population_size": 20, "initial_polish_iters": 1}),
    ]
    family = assert_single_comparison_family(items, vary=("algorithm",))
    assert family.size == 3
    assert {"algorithm_id", "configuration_hash", "backend_profile"} <= set(family.varied)
    assert "backend_profile" not in family.shared and family.shared["backend_policy"] == "prefer_numba"
    # the Friedman design (algorithm and instance) works the same way
    st70 = [_algo_on("st70", *item) for item in (
        ("Core-TwoOpt-TSP", PY_NONE, {"max_iterations": 1000}),
        ("Core-GA-TSP", NUMBA_NONE, {"population_size": 20}),
    )]
    eil = [_algo_on("eil51", *item) for item in (
        ("Core-TwoOpt-TSP", PY_NONE, {"max_iterations": 1000}),
        ("Core-GA-TSP", NUMBA_NONE, {"population_size": 20}),
    )]
    assert assert_single_comparison_family(st70 + eil, vary=("algorithm", "dataset")).size == 4


def _algo_on(problem, algorithm_id, profile, configuration):
    return pair({"algorithm_id": algorithm_id, "problem": problem, "budget": 1},
                {"algorithm_id": algorithm_id, "backend_profile": profile, "configuration": configuration,
                 "dataset_id": f"tsplib-{problem}", "levels": (1, 2)})


def test_one_algorithm_with_two_backend_profiles_is_still_refused_in_an_algorithm_family():
    ga_numba = _algo("Core-GA-TSP", NUMBA_NONE, {"population_size": 20})
    ga_python = _algo("Core-GA-TSP", PY_NONE, {"population_size": 20})
    two_opt = _algo("Core-TwoOpt-TSP", PY_NONE, {"max_iterations": 1000})
    with pytest.raises(ComparisonIdentityError, match="backend profile"):
        assert_single_comparison_family([ga_numba, ga_python, two_opt], vary=("algorithm",))
    with pytest.raises(ComparisonIdentityError, match="backend_profile"):
        assert_single_comparison_family([ga_numba, ga_python])  # and never one cell


def test_a_backend_policy_difference_still_splits_an_algorithm_family():
    a = _algo("Core-GA-TSP", NUMBA_NONE, {"population_size": 20})
    b = pair({"algorithm_id": "Core-TwoOpt-TSP"},
             {"algorithm_id": "Core-TwoOpt-TSP", "backend_policy": "python_only", "backend_profile": PY_NONE})
    with pytest.raises(ComparisonIdentityError, match="backend_policy"):
        assert_single_comparison_family([a, b], vary=("algorithm",))


def test_a_row_dataset_id_in_tsplib_form_must_also_match_the_problem_name():
    with pytest.raises(ComparisonIdentityError, match="problem"):
        comparison_cell_key(make_row(problem="st70", dataset_id="tsplib-eil51"), make_manifest())
    ok = comparison_cell_key(make_row(problem="eil51", dataset_id="tsplib-eil51"), make_manifest())
    assert ok.dataset_identity == "eil51"
