"""Gate D, D-02: RunManifestV1 writer, detached .sha256 and verifier (plan 2026-10-23, section 3, D-02; DECISION_LOG A18).

Smoke runs of the synthetic ``tiny10`` study (the C-13 fixture: pure and composite IDs, fixed and native rows) write one
``RunManifestV1`` per run, a campaign index (``uniride-run-index/v2``) and a detached ``<file>.sha256`` for each; the
verifier recomputes every checksum. The fixture repository is a temporary directory, so git state is injected.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

import test_study_smoke_composite as comp
from academic_benchmark.analysis import manifests
from academic_benchmark.analysis.identity import comparison_cell_key
from academic_benchmark.analysis.manifests import (
    ManifestError,
    build_run_manifest,
    comparable_manifest_view,
    verify_campaign,
    write_json_with_sidecar,
)
from academic_benchmark.contracts import OutputChecksumV1, RunManifestV1
from academic_benchmark.contracts.export_schemas import check_schemas, render_schemas
from academic_benchmark.contracts.run_index import RunIndexV2
from academic_benchmark.studies.smoke import run_study_smoke
from academic_benchmark.studies.service import fixed_budget_levels_for
from academic_benchmark.studies.verify_manifests import main as verify_main

COMMIT = "c" * 40
CLEAN = lambda _root: {"revision": COMMIT, "dirty": False}  # noqa: E731
DIRTY = lambda _root: {"revision": COMMIT, "dirty": True}  # noqa: E731
UNKNOWN = lambda _root: {"revision": None, "dirty": None, "git_error": "unavailable"}  # noqa: E731


def _extras(runs: int) -> dict:
    """The campaign fields that D-10 gaps G1, G2, G3, G6 and G7 add to every index (``uniride-run-index/v2``)."""
    return dict(
        profile={"path": "studies/study.json", "sha256": "1" * 64},
        analysis_plan={"analysis_plan_id": "fixture", "path": None, "sha256": None},
        planned={"runs_per_cell": 1, "runs": runs},
        output_location={"path": str(Path("/campaign/out").resolve()),
                         "outside_repository_check": {"result": "outside_repository", "checked_against": ["/repo"]}},
        failed_runs=[],
    )


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _manifests(out: Path) -> dict[str, RunManifestV1]:
    return {
        p.name[: -len(".json")]: RunManifestV1.model_validate_json(p.read_bytes())
        for p in sorted((out / "manifests").glob("*.json"))
    }


def _run(tmp_path: Path, name: str, git=CLEAN, **kwargs):
    root = comp._repository(tmp_path / f"repo-{name}")
    out = tmp_path / f"out-{name}"
    plan = comp._plan(root)
    report = run_study_smoke(
        plan, out, problem_loader=comp._loader(), repository_root=root, replicates=1, git_provider=git, **kwargs
    )
    return plan, report, out


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("d02")
    plan, report, out = _run(tmp, "a")
    return plan, report, out


def _copy(out: Path, tmp_path: Path) -> Path:
    target = tmp_path / "copy"
    shutil.copytree(out, target)
    return target


def _flip_one_byte(path: Path, index: int = 10) -> None:
    data = bytearray(path.read_bytes())
    data[index] ^= 0x01
    path.write_bytes(bytes(data))


# ------------------------------------------------------------------ the run writes valid manifests that verify
def test_smoke_run_writes_valid_manifests_with_detached_checksums_and_they_verify(campaign):
    _plan, report, out = campaign
    assert report.status == "passed", report.text
    found = _manifests(out)
    # 3 pure/composite IDs x1 fixed row + same x1 native row (replicates=1): one manifest per run
    assert len(found) == len(comp.COMPOSITES) * 2
    for name in found:
        assert (out / "manifests" / f"{name}.json.sha256").is_file()
    assert (out / "run_index.json").is_file() and (out / "run_index.json.sha256").is_file()
    assert verify_campaign(out) == []
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert sorted(e.run_id for e in index.runs) == sorted(found)
    assert index.mode == "smoke" and index.status == "passed"


def test_detached_checksum_file_is_a_sha256sum_line_of_the_exact_manifest_bytes(campaign):
    import hashlib

    _plan, _report, out = campaign
    manifest_path = next((out / "manifests").glob("*.json"))
    line = (out / "manifests" / f"{manifest_path.name}.sha256").read_text(encoding="ascii")
    digest, _, name = line.rstrip("\n").partition("  ")
    assert digest == hashlib.sha256(manifest_path.read_bytes()).hexdigest() and name == manifest_path.name


# ------------------------------------------------------------------ tampering is detected
def test_one_changed_byte_in_a_manifest_fails_verification(campaign, tmp_path):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    _flip_one_byte(next((copied / "manifests").glob("*.json")))
    errors = verify_campaign(copied)
    assert errors and any("checksum" in e for e in errors)


def test_one_changed_byte_in_an_output_file_fails_verification(campaign, tmp_path):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    _flip_one_byte(copied / "fixed_runs.jsonl", 20)
    errors = verify_campaign(copied)
    assert errors and any("fixed_runs.jsonl" in e and "checksum" in e for e in errors)


@pytest.mark.parametrize("what", ["manifest_sidecar", "manifest", "index_sidecar", "index", "unlisted_manifest"])
def test_missing_or_extra_files_fail_verification(campaign, tmp_path, what):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    first = next((copied / "manifests").glob("*.json"))
    if what == "manifest_sidecar":
        Path(str(first) + ".sha256").unlink()
    elif what == "manifest":
        first.unlink()
    elif what == "index_sidecar":
        (copied / "run_index.json.sha256").unlink()
    elif what == "index":
        (copied / "run_index.json").unlink()
    else:
        shutil.copy(first, copied / "manifests" / "extra.json")
        shutil.copy(str(first) + ".sha256", copied / "manifests" / "extra.json.sha256")
    assert verify_campaign(copied) != []


@pytest.mark.parametrize("which", ["manifest", "index"])
def test_a_sidecar_with_another_digest_fails_even_when_the_file_is_untouched(campaign, tmp_path, which):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    target = next((copied / "manifests").glob("*.json")) if which == "manifest" else copied / "run_index.json"
    sidecar = Path(str(target) + ".sha256")
    sidecar.write_text(f"{'0' * 64}  {target.name}\n", encoding="ascii")
    errors = verify_campaign(copied)
    assert errors and any("checksum mismatch" in e and target.name in e for e in errors)


def test_a_changed_byte_in_the_index_fails_verification(campaign, tmp_path):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    path = copied / "run_index.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"mode": "smoke"', '"mode": "paper"'), encoding="utf-8", newline="\n")
    errors = verify_campaign(copied)
    assert errors and any("run_index.json" in e and "checksum mismatch" in e for e in errors)


def test_a_sidecar_that_names_another_file_fails(campaign, tmp_path):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    sidecar = Path(str(next((copied / "manifests").glob("*.json"))) + ".sha256")
    digest = sidecar.read_text(encoding="ascii").split()[0]
    sidecar.write_text(f"{digest}  other.json\n", encoding="ascii")
    assert verify_campaign(copied) != []


def test_a_swapped_row_in_the_outputs_is_caught_even_if_all_checksums_are_recomputed(campaign, tmp_path):
    """Row binding: the manifest says which run it describes, the rows file must contain exactly that run."""
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    rows = _read_rows(copied / "fixed_runs.jsonl")
    rows[0]["seed"] += 1  # a different seed than the manifest's seed schedule
    (copied / "fixed_runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    _recompute_all_checksums(copied)
    errors = verify_campaign(copied)
    assert errors and any("row" in e for e in errors)


def _recompute_all_checksums(directory: Path) -> None:
    """Re-seal a tampered campaign: new output checksums in every manifest, new sidecars, new index entries."""
    index_model = RunIndexV2.model_validate_json((directory / "run_index.json").read_bytes())
    outputs = [
        OutputChecksumV1(path=o.path, checksum={"algorithm": "sha256", "value": manifests.file_sha256(directory / o.path)})
        for o in index_model.outputs
    ]
    entries = []
    for entry in index_model.runs:
        path = directory / entry.manifest_path
        raw = json.loads(path.read_bytes())
        for item in raw["outputs"]:
            item["checksum"]["value"] = manifests.file_sha256(directory / item["path"])
        model = RunManifestV1.model_validate(raw)
        checksum = write_json_with_sidecar(path, model)
        entries.append(entry.model_copy(update={"manifest_checksum": checksum}))
    write_json_with_sidecar(directory / "run_index.json", index_model.model_copy(update={"runs": entries, "outputs": outputs}))


def test_a_manifest_that_lists_itself_is_refused_by_writer_and_verifier(campaign, tmp_path):
    _plan, _report, out = campaign
    fixed_row = _read_rows(out / "fixed_runs.jsonl")[0]
    manifest = next(iter(_manifests(out).values()))
    own = OutputChecksumV1(path=f"manifests/{manifest.run_id}.json", checksum={"algorithm": "sha256", "value": "0" * 64})
    with pytest.raises(ManifestError, match="manifest"):
        build_run_manifest(
            fixed_row, study_id=manifest.study_id, dataset=manifest.dataset, base_seed=manifest.seeds.base_seed,
            levels=list(manifest.budget.levels), configuration=dict(manifest.algorithm.configuration),
            git=manifest.git, environment=manifest.environment, outputs=[own],
        )
    copied = _copy(out, tmp_path)
    target = next((copied / "manifests").glob("*.json"))
    raw = json.loads(target.read_bytes())
    raw["outputs"].append({"path": f"manifests/{target.name}", "checksum": {"algorithm": "sha256", "value": "0" * 64}})
    write_json_with_sidecar(target, RunManifestV1.model_validate(raw))
    _recompute_all_checksums(copied)
    errors = verify_campaign(copied)
    assert errors and any("manifest" in e and "list" in e for e in errors)


def test_the_manifests_of_a_run_never_list_manifest_or_sidecar_files(campaign):
    _plan, _report, out = campaign
    for manifest in _manifests(out).values():
        assert manifest.outputs
        for item in manifest.outputs:
            assert not item.path.startswith("manifests/") and not item.path.endswith(".sha256")
            assert item.path in {"fixed_runs.jsonl", "native_runs.jsonl"}


# ------------------------------------------------------------------ manifest content
def test_content_budget_backend_dataset_seeds_and_validation(campaign):
    plan, _report, out = campaign
    dataset = plan.datasets[0]
    own_levels = list(fixed_budget_levels_for(plan.study, dataset))  # the dataset's own level list, not the smoke slice
    assert own_levels == comp.LEVELS and len(own_levels) == 2
    fixed_rows = {(r["algorithm_id"], r["replicate"]): r for r in _read_rows(out / "fixed_runs.jsonl")}
    native_rows = {(r["algorithm_id"], r["replicate"]): r for r in _read_rows(out / "native_runs.jsonl")}
    seen_fixed = seen_native = 0
    for manifest in _manifests(out).values():
        assert manifest.schema_version == "uniride-run/v1" and manifest.study_id == plan.study.study_id
        assert manifest.git.commit == COMMIT and manifest.git.dirty is False
        assert manifest.environment.statistics_library == "none"
        assert manifest.dataset == dataset.manifest and manifest.seeds.base_seed == plan.study.base_seed
        assert manifest.algorithm.backend_policy == "prefer_numba"  # X11: the policy is recorded
        assert manifest.validation.passed is True and "hamiltonian_cycle" in manifest.validation.checks
        native = manifest.protocol_version == "uniride-native-tsp-v1"
        row = (native_rows if native else fixed_rows)[(manifest.algorithm.algorithm_id, 0)]
        assert manifest.seeds.derived["run_seed"] == row["seed"]
        assert manifest.budget.objective_evaluations == row["objective_evaluations"]
        assert manifest.termination.reason == row["termination_reason"]
        assert manifest.termination.runtime_seconds == pytest.approx(row["elapsed_ms"] / 1000.0)
        profile = row["execution_backend"]
        assert f"objective={manifest.algorithm.backend_profile['objective']}" in profile
        assert f"polish={manifest.algorithm.backend_profile['polish']}" in profile
        assert manifest.algorithm.capability_evidence_ids == row["capability_evidence_ids"]
        if native:
            seen_native += 1
            assert manifest.budget.policy == "native_uncapped" and manifest.budget.levels == [0]
        else:
            seen_fixed += 1
            assert manifest.budget.policy == "atomic_upper_bound_v1" and manifest.budget.levels == own_levels
    assert seen_fixed == seen_native == len(comp.COMPOSITES)


def test_every_manifest_gives_its_row_a_comparison_key(campaign):
    _plan, _report, out = campaign
    rows = _read_rows(out / "fixed_runs.jsonl") + _read_rows(out / "native_runs.jsonl")
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    digests = {e.run_id: e.comparison_key_digest for e in index.runs}
    for manifest in _manifests(out).values():
        row = next(
            r for r in rows
            if r["algorithm_id"] == manifest.algorithm.algorithm_id and r["protocol_version"] == manifest.protocol_version
        )
        assert comparison_cell_key(row, manifest).digest() == digests[manifest.run_id]


def test_composite_rows_persist_their_stage_records_and_allocation(campaign):
    _plan, _report, out = campaign
    fixed = {r["algorithm_id"]: r for r in _read_rows(out / "fixed_runs.jsonl")}
    native = {r["algorithm_id"]: r for r in _read_rows(out / "native_runs.jsonl")}
    for manifest in _manifests(out).values():
        algorithm = manifest.algorithm
        row = (native if manifest.protocol_version == "uniride-native-tsp-v1" else fixed)[algorithm.algorithm_id]
        stages = row["composition"]["stages"]
        assert [s["name"] for s in algorithm.composition_stages] == ["global", "polish"]
        assert algorithm.composition_stages == stages  # the persisted record, as exported
        if manifest.protocol_version == "uniride-native-tsp-v1":
            assert manifest.budget.stage_allocation == {}  # a native run allocates nothing
        else:
            assert manifest.budget.stage_allocation == {s["name"]: s["allocated_evaluations"] for s in stages}
        assert manifest.seeds.derived["global_stage_seed"] == stages[0]["seed"]


def test_non_composite_rows_have_no_stage_records(tmp_path):
    plan = comp._plan(comp._repository(tmp_path / "repo"))
    manifest = _first_manifest_of_a_pure_row(tmp_path, plan)
    assert manifest.algorithm.composition_stages == [] and manifest.budget.stage_allocation == {}


def _first_manifest_of_a_pure_row(tmp_path, plan) -> RunManifestV1:
    """A pure-algorithm row built through the public builder (the tiny10 study contains composites only)."""
    row = {
        "protocol_version": "uniride-fair-tsp-v2", "comparison_regime": "fixed_evaluation_budget", "problem": "tiny10",
        "dataset_id": "tiny10", "algorithm_id": "Core-GWO-TSP-Pure", "variant": "pure", "study_id": plan.study.study_id,
        "evaluation_budget": comp.LEVELS[0], "termination_policy": "atomic_upper_bound_v1;max_iterations=60",
        "objective_evaluations": 700, "termination_reason": "max_iterations", "elapsed_ms": 12.0, "seed": 5, "replicate": 0,
        "execution_backend": "objective=numba;polish=none", "backend_policy": "prefer_numba_objective",
        "capability_evidence_ids": ["fixture"], "validation_status": "passed", "hamiltonian_validation": "passed",
        "algorithm_family": "GWO", "problem_type": "tsp", "canonical_algorithm_id": "Core-GWO-TSP-Pure",
    }
    return build_run_manifest(
        row, study_id=plan.study.study_id, dataset=plan.datasets[0].manifest, base_seed=plan.study.base_seed,
        levels=list(comp.LEVELS), configuration={"pack_size": 4}, git={"commit": COMMIT, "dirty": False},
        environment=manifests.collect_environment(), outputs=[],
    )


# ------------------------------------------------------------------ timing never enters an identity
def test_same_seed_runs_differ_only_in_timing_and_have_equal_identity_digests(campaign, tmp_path):
    _plan, _report, out = campaign
    _plan2, _report2, again = _run(tmp_path, "b")
    first, second = _manifests(out), _manifests(again)
    assert sorted(first) == sorted(second)
    for name in first:
        assert comparable_manifest_view(first[name]) == comparable_manifest_view(second[name])
    index_a = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    index_b = RunIndexV2.model_validate_json((again / "run_index.json").read_bytes())
    assert {e.run_id: e.comparison_key_digest for e in index_a.runs} == {e.run_id: e.comparison_key_digest for e in index_b.runs}
    # the comparable view drops exactly the timing: the full records do differ somewhere
    raw_a = {n: m.model_dump(mode="json") for n, m in first.items()}
    raw_b = {n: m.model_dump(mode="json") for n, m in second.items()}
    assert raw_a != raw_b


def test_the_comparable_view_drops_runtime_and_stage_elapsed_and_nothing_else(campaign):
    _plan, _report, out = campaign
    manifest = next(m for m in _manifests(out).values() if m.algorithm.composition_stages)
    view = comparable_manifest_view(manifest)
    assert "runtime_seconds" not in view["termination"] and view["termination"]["reason"] == manifest.termination.reason
    for stage in view["algorithm"]["composition_stages"]:
        assert "elapsed_sec" not in stage and "consumed_evaluations" in stage
    changed = copy.deepcopy(manifest.model_dump(mode="json"))
    changed["termination"]["runtime_seconds"] = 999.0
    for stage in changed["algorithm"]["composition_stages"]:
        stage["elapsed_sec"] = 888.0
    assert comparable_manifest_view(RunManifestV1.model_validate(changed)) == view


def test_the_index_holds_no_timing(campaign):
    _plan, _report, out = campaign
    text = (out / "run_index.json").read_text(encoding="utf-8")
    assert "elapsed" not in text and "runtime" not in text


# ------------------------------------------------------------------ index, git states, report
def test_the_index_records_the_seed_protocol_base_seed_git_and_environment(campaign):
    plan, report, out = campaign
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.seed_protocol_version == plan.study.seed_protocol_version == "sha256-seed-v1"
    assert index.base_seed == plan.study.base_seed and index.study_id == plan.study.study_id
    assert index.git.commit == COMMIT and index.git.dirty is False
    assert {o.path for o in index.outputs} == {"fixed_runs.jsonl", "native_runs.jsonl"}
    sidecar = (out / "run_index.json.sha256").read_text(encoding="ascii").split()[0]
    assert sidecar in report.text and sidecar == json.loads((out / "smoke_report.json").read_text(encoding="utf-8"))["run_index"]["sha256"]


def test_a_dirty_tree_is_recorded_in_manifests_and_index_and_still_verifies(tmp_path):
    _plan, report, out = _run(tmp_path, "dirty", git=DIRTY)
    assert report.status == "passed"
    assert all(m.git.dirty is True for m in _manifests(out).values())
    assert RunIndexV2.model_validate_json((out / "run_index.json").read_bytes()).git.dirty is True
    assert verify_campaign(out) == []
    assert "dirty" in report.text.lower()


def test_unknown_git_state_writes_no_manifests_and_the_report_says_so(tmp_path):
    _plan, report, out = _run(tmp_path, "unknown", git=UNKNOWN)
    assert report.status == "passed"
    assert not (out / "manifests").exists() and not (out / "run_index.json").exists()
    assert "not written" in report.text and "git" in report.text
    assert json.loads((out / "smoke_report.json").read_text(encoding="utf-8"))["run_index"] is None


def test_a_failed_smoke_run_still_writes_a_verifiable_index_marked_failed(tmp_path):
    root = comp._repository(tmp_path / "repo")
    plan = comp._plan(root)
    calls = []

    def failing_gateway(**kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("synthetic failure")
        from academic_benchmark.core.execution_gateway import execute_preflighted

        return execute_preflighted(**kwargs)

    out = tmp_path / "out"
    report = run_study_smoke(
        plan, out, problem_loader=comp._loader(), repository_root=root, replicates=1, git_provider=CLEAN,
        gateway_executor=failing_gateway,
    )
    assert report.status == "failed"
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.status == "failed" and len(index.runs) == 1
    assert "failed_runs.jsonl" in {o.path for o in index.outputs}
    assert verify_campaign(out) == []


# ------------------------------------------------------------------ writer rules and atomicity
def test_a_tsplib_dataset_id_must_match_the_problem_name(campaign):
    plan, _report, out = campaign
    manifest = next(iter(_manifests(out).values()))
    row = _read_rows(out / "fixed_runs.jsonl")[0]
    with pytest.raises(ManifestError, match="differs from the dataset manifest"):  # study rows carry their dataset id
        build_run_manifest(
            row, study_id=manifest.study_id, dataset=manifest.dataset.model_copy(update={"dataset_id": "other"}),
            base_seed=1, levels=list(manifest.budget.levels), configuration={}, git=manifest.git,
            environment=manifest.environment, outputs=[],
        )
    row = {k: v for k, v in row.items() if k != "dataset_id"}  # pilot-style row: matched by its problem name
    tsplib = manifest.dataset.model_copy(update={"dataset_id": "tsplib-kroa100"})
    with pytest.raises(ManifestError, match="tsplib-tiny10"):
        build_run_manifest(
            row, study_id=manifest.study_id, dataset=tsplib, base_seed=manifest.seeds.base_seed,
            levels=list(manifest.budget.levels), configuration={}, git=manifest.git, environment=manifest.environment,
            outputs=[],
        )


def test_a_failed_row_gets_no_manifest(campaign):
    plan, _report, out = campaign
    manifest = next(iter(_manifests(out).values()))
    with pytest.raises(ManifestError, match="failed"):
        build_run_manifest(
            {"record_kind": "failed_run", "validation_status": "failed", "algorithm_id": "x"},
            study_id=manifest.study_id, dataset=manifest.dataset, base_seed=1, levels=[1], configuration={},
            git=manifest.git, environment=manifest.environment, outputs=[],
        )


def test_duplicate_run_ids_are_refused(tmp_path):
    from academic_benchmark.analysis.manifests import write_run_campaign

    plan, _report, out = _run(tmp_path, "dup")
    manifest = next(iter(_manifests(out).values()))
    row = _read_rows(out / "fixed_runs.jsonl")[0]
    target = tmp_path / "dup-out"
    target.mkdir()
    shutil.copy(out / "fixed_runs.jsonl", target / "fixed_runs.jsonl")
    with pytest.raises(ManifestError, match="duplicate"):
        write_run_campaign(
            target, mode="smoke", study_id=manifest.study_id, seed_protocol_version="sha256-seed-v1",
            base_seed=manifest.seeds.base_seed, git=manifest.git, environment=manifest.environment, status="passed",
            runs=[(row, manifest), (row, manifest)], output_files=["fixed_runs.jsonl"], **_extras(2),
        )
    assert not (target / "manifests").exists() or not any((target / "manifests").iterdir())


def test_an_interrupted_write_leaves_no_file_that_verifies(tmp_path, monkeypatch):
    plan, _report, out = _run(tmp_path, "atomic")
    manifest = next(iter(_manifests(out).values()))
    target = tmp_path / "atomic-target" / "m.json"
    target.parent.mkdir()
    real_replace = os.replace
    calls = []

    def dying_replace(src, dst):
        calls.append(dst)
        if len(calls) == 2:  # the sidecar's replace never happens
            raise OSError("simulated crash")
        return real_replace(src, dst)

    monkeypatch.setattr(manifests.os, "replace", dying_replace)
    with pytest.raises(OSError):
        write_json_with_sidecar(target, manifest)
    leftovers = sorted(p.name for p in target.parent.iterdir())
    assert "m.json.sha256" not in leftovers and not any(n.endswith(".tmp") for n in leftovers)


# ------------------------------------------------------------------ CLI and schema snapshot
def test_cli_exit_codes_and_messages(campaign, tmp_path, capsys):
    _plan, _report, out = campaign
    assert verify_main([str(out)]) == 0
    assert "OK" in capsys.readouterr().out
    copied = _copy(out, tmp_path)
    _flip_one_byte(copied / "fixed_runs.jsonl", 20)
    assert verify_main([str(out), str(copied)]) == 1
    captured = capsys.readouterr().out
    assert "FAIL" in captured and "fixed_runs.jsonl" in captured
    assert verify_main([str(tmp_path / "does-not-exist")]) == 1


def test_run_index_schema_snapshot_is_registered_and_current():
    assert check_schemas() == []
    schema = json.loads(render_schemas()["run-index-v2.schema.json"])
    assert schema["$id"] == "uniride-run-index/v2" and schema["additionalProperties"] is False
    assert "seed_protocol_version" in schema["properties"]


def test_run_v1_schema_is_not_changed_by_d02():
    """seed_protocol_version lives in the index; uniride-run/v1 stays as published (design: a schema change is a new version)."""
    schema = json.loads(render_schemas()["run-v1.schema.json"])
    assert "seed_protocol_version" not in schema["properties"]


# ------------------------------------------------------------------ DUZELT r1: levels, completeness, folder allow-list
def _merge_two_levels(tmp_path: Path) -> Path:
    """One campaign with both budget levels of the dataset for one replicate (paired seeds repeat across levels)."""
    from academic_benchmark.analysis.manifests import write_run_campaign

    plan, _r, low = _run(tmp_path, "low")
    root = comp._repository(tmp_path / "repo-high")
    high = tmp_path / "out-high"
    run_study_smoke(
        comp._plan(root), high, problem_loader=comp._loader(), repository_root=root, replicates=1,
        budget_level=comp.LEVELS[1], git_provider=CLEAN,
    )
    rows = _read_rows(low / "fixed_runs.jsonl") + _read_rows(high / "fixed_runs.jsonl")
    assert {r["evaluation_budget"] for r in rows} == set(comp.LEVELS)
    assert len({(r["algorithm_id"], r["seed"]) for r in rows}) == len(comp.COMPOSITES)  # same seed at both levels
    merged = tmp_path / "merged"
    merged.mkdir()
    (merged / "fixed_runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    template = {m.algorithm.algorithm_id: m for m in _manifests(low).values() if m.protocol_version != "uniride-native-tsp-v1"}
    checksum = OutputChecksumV1(
        path="fixed_runs.jsonl", checksum={"algorithm": "sha256", "value": manifests.file_sha256(merged / "fixed_runs.jsonl")}
    )
    pairs = []
    for row in rows:
        base = template[row["algorithm_id"]]
        pairs.append((row, build_run_manifest(
            row, study_id=base.study_id, dataset=base.dataset, base_seed=base.seeds.base_seed, levels=list(comp.LEVELS),
            configuration=dict(base.algorithm.configuration), git=base.git, environment=base.environment, outputs=[checksum],
        )))
    base = next(iter(template.values()))
    write_run_campaign(
        merged, mode="smoke", study_id=base.study_id, seed_protocol_version="sha256-seed-v1", base_seed=base.seeds.base_seed,
        git=base.git, environment=base.environment, status="passed", runs=pairs, output_files=["fixed_runs.jsonl"], **_extras(len(pairs)),
    )
    return merged


def test_a_campaign_with_two_budget_levels_verifies(tmp_path):
    merged = _merge_two_levels(tmp_path)
    assert len(_manifests(merged)) == 2 * len(comp.COMPOSITES)
    assert verify_campaign(merged) == []


def _reseal_index(directory: Path, *, drop_runs=(), **updates) -> None:
    index = RunIndexV2.model_validate_json((directory / "run_index.json").read_bytes())
    runs = [e for e in index.runs if e.run_id not in set(drop_runs)]
    for run_id in drop_runs:
        (directory / "manifests" / f"{run_id}.json").unlink()
        (directory / "manifests" / f"{run_id}.json.sha256").unlink()
    write_json_with_sidecar(directory / "run_index.json", index.model_copy(update={"runs": runs, **updates}))


def test_a_row_without_a_manifest_fails_even_when_the_index_is_resealed(campaign, tmp_path):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    index = RunIndexV2.model_validate_json((copied / "run_index.json").read_bytes())
    _reseal_index(copied, drop_runs=[index.runs[0].run_id])
    errors = verify_campaign(copied)
    assert errors and any("no run manifest" in e for e in errors)


def test_an_index_with_no_runs_does_not_verify_while_result_files_hold_rows(campaign, tmp_path):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    index = RunIndexV2.model_validate_json((copied / "run_index.json").read_bytes())
    _reseal_index(copied, drop_runs=[e.run_id for e in index.runs])
    errors = verify_campaign(copied)
    assert errors and any("no run manifest" in e for e in errors)


def test_two_manifests_for_one_row_fail(campaign, tmp_path):
    """Another manifest bound to the same row (a different run id cannot be minted, so the row is duplicated instead)."""
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    rows = _read_rows(copied / "fixed_runs.jsonl")
    (copied / "fixed_runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows + [rows[0]]), encoding="utf-8")
    _recompute_all_checksums(copied)
    errors = verify_campaign(copied)
    assert errors and any("row" in e for e in errors)


@pytest.mark.parametrize("name", ["extra_runs.jsonl", "notes.txt"])
def test_unexpected_top_level_files_are_reported(campaign, tmp_path, name):
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    (copied / name).write_text("{}\n", encoding="utf-8")
    errors = verify_campaign(copied)
    assert errors and any(name in e and "unexpected" in e for e in errors)


def test_the_report_files_and_the_manifest_folder_are_expected(campaign):
    _plan, _report, out = campaign
    assert {p.name for p in out.iterdir()} >= {"smoke_report.txt", "smoke_report.json", "manifests"}
    assert verify_campaign(out) == []


def test_the_writer_and_the_verifier_require_the_implemented_seed_protocol(campaign, tmp_path):
    from academic_benchmark.analysis.manifests import write_run_campaign

    _plan, _report, out = campaign
    manifest = next(iter(_manifests(out).values()))
    target = tmp_path / "bad-seed-protocol"
    target.mkdir()
    with pytest.raises(ManifestError, match="seed_protocol_version"):
        write_run_campaign(
            target, mode="smoke", study_id=manifest.study_id, seed_protocol_version="other-seed-v9",
            base_seed=manifest.seeds.base_seed, git=manifest.git, environment=manifest.environment, status="passed",
            runs=[], output_files=[], **_extras(1),
        )
    copied = _copy(out, tmp_path)
    _reseal_index(copied, seed_protocol_version="other-seed-v9")
    assert any("seed_protocol_version" in e for e in verify_campaign(copied))


def test_native_manifests_carry_the_sentinel_level_and_the_contract_says_so(campaign, tmp_path):
    schema = json.loads(render_schemas()["run-index-v2.schema.json"])
    assert "sentinel" in schema["description"] and "[0]" in schema["description"]
    _plan, _report, out = campaign
    copied = _copy(out, tmp_path)
    target = next(
        p for p in (copied / "manifests").glob("*.json") if json.loads(p.read_bytes())["budget"]["policy"] == "native_uncapped"
    )
    raw = json.loads(target.read_bytes())
    raw["budget"]["levels"] = [900]
    write_json_with_sidecar(target, RunManifestV1.model_validate(raw))
    _recompute_all_checksums(copied)
    assert any("sentinel" in e or "[0]" in e for e in verify_campaign(copied))


# ------------------------------------------------------------------ the real Bildiri profile (D-01 requirements for D-02)
def test_real_bildiri_ft53_manifests_carry_the_datasets_own_levels_and_tsplib_dataset_id(tmp_path):
    import dataclasses

    import test_study_smoke as ft
    from academic_benchmark.studies import build_study_plan
    from academic_benchmark.studies.smoke import select_smoke_rows

    full = build_study_plan(ft.BILDIRI_STUDY, repository_root=ft.REPOSITORY_ROOT)
    datasets = tuple(d for d in full.datasets if d.dataset_id == "tsplib-ft53")
    rows = tuple(r for r in select_smoke_rows(full, replicates=1) if r.dataset_id == "tsplib-ft53" and r.algorithm_id == "Core-GWO-TSP-Pure")
    assert len(rows) == 2  # one fixed row (lowest level) and one native row
    plan = dataclasses.replace(full, datasets=datasets, rows=rows)
    out = tmp_path / "out"
    from academic_benchmark.committed_bytes import run_git

    before = run_git(["status", "--porcelain"], ft.REPOSITORY_ROOT)
    report = run_study_smoke(
        plan, out, problem_loader=ft._loader(), repository_root=ft.REPOSITORY_ROOT, replicates=1, git_provider=CLEAN
    )
    assert run_git(["status", "--porcelain"], ft.REPOSITORY_ROOT) == before  # the manifests land outside the repository
    assert report.status == "passed", report.text
    found = _manifests(out)
    assert len(found) == 2 and verify_campaign(out) == []
    study_block = plan.study.algorithm_parameters["Core-GWO-TSP-Pure"]
    for manifest in found.values():
        assert manifest.dataset.dataset_id == "tsplib-ft53"
        assert manifest.algorithm.configuration.keys() >= set(study_block) - {"max_iterations", "max_no_improvement"}
        assert "fair_comparison" not in manifest.algorithm.configuration
        assert "native_comparison" not in manifest.algorithm.configuration
        if manifest.budget.policy == "atomic_upper_bound_v1":
            assert manifest.budget.levels == list(ft.FT53_LEVELS)  # the dataset's own list: 50 and 250 scans of ft53
            assert manifest.algorithm.configuration == dict(study_block)
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.seed_protocol_version == "sha256-seed-v1" and index.base_seed == plan.study.base_seed
