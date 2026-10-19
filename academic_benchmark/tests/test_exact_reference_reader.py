"""WP-E8 Task 4: the reader of the committed ``exact_reference_v1`` results (``academic_benchmark.exact_reference.reader``).

Red/green tests on the three committed result directories and on tampered copies built in ``tmp_path`` (a fake repository
root; the committed files are never modified). Nothing here opens a database. Archive-like names are built from components.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest

from academic_benchmark.exact_reference import protocol, reader
from academic_benchmark.exact_reference.reader import ExactReferenceRefused, load_exact_reference

REPO = Path(__file__).resolve().parents[2]
STAGE1 = "docs/paper/results/tsplib-exact-reference/stage1-verification"
E3 = "docs/paper/results/week-2026-10-05-exact/wp-e3-goal1-single"
E4A = "docs/paper/results/week-2026-10-05-exact/wp-e4a-typed-options"
E3_SOURCE = "docs/paper/results/week-2026-10-05-4sw5so"
REFUSED = "arch" + "ive"
EXPECTED_TSP = ("burma14", "ulysses16", "ulysses22", "att48", "eil51", "berlin52", "ft53", "st70", "eil76", "pr76", "gr96",
                "kroa100", "krob100", "kroc100", "krod100", "kroe100", "rd100")


# ---------------------------------------------------------------- helpers
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _copy_dir(src_rel: str, root: Path) -> Path:
    target = root / src_rel
    shutil.copytree(REPO / src_rel, target)
    return target


@pytest.fixture()
def stage1_root(tmp_path):
    _copy_dir(STAGE1, tmp_path)
    return tmp_path


@pytest.fixture()
def e3_root(tmp_path):
    _copy_dir(E3, tmp_path)
    source = tmp_path / E3_SOURCE
    source.mkdir(parents=True)
    shutil.copyfile(REPO / E3_SOURCE / "run_manifest.json", source / "run_manifest.json")
    return tmp_path


def _manifest(root: Path, rel: str = STAGE1, name: str = "manifest.json") -> dict:
    return json.loads((root / rel / name).read_text(encoding="utf-8"))


def _write_manifest(root: Path, doc: dict, rel: str = STAGE1, name: str = "manifest.json") -> None:
    (root / rel / name).write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _rewrite_output(root: Path, name: str, data: bytes) -> None:
    """Replace one stage-1 output file and make the manifest ``outputs`` entry agree, so that a later check than the sha256
    one is the one that has to catch the change."""
    directory = root / STAGE1
    (directory / name).write_bytes(data)
    doc = _manifest(root)
    doc["outputs"][name] = _sha(data)
    _write_manifest(root, doc)


def _csv_table(root: Path) -> list:
    return list(csv.reader(io.StringIO((root / STAGE1 / "reference.csv").read_bytes().decode("utf-8"), newline="")))


def _table_bytes(table: list) -> bytes:
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\n").writerows(table)
    return out.getvalue().encode("utf-8")


def _edit_csv(root: Path, instance: str, column: str, value: str) -> None:
    table = _csv_table(root)
    col = table[0].index(column)
    for row in table[1:]:
        if row[table[0].index("instance")] == instance:
            row[col] = value
    _rewrite_output(root, "reference.csv", _table_bytes(table))


# ---------------------------------------------------------------- the committed results
@pytest.fixture(scope="module")
def stage1():
    return load_exact_reference(STAGE1, repo_root=REPO)


@pytest.fixture(scope="module")
def e3():
    return load_exact_reference(E3, repo_root=REPO)


@pytest.fixture(scope="module")
def e4a():
    return load_exact_reference(E4A, repo_root=REPO)


def test_stage1_gives_34_rows_all_optimal_and_equal_to_the_reference(stage1):
    assert stage1.manifest_kind == "tsp_reference" and len(stage1.rows) == 34
    primary = [r for r in stage1.rows if r.solver_role == "primary"]
    verification = [r for r in stage1.rows if r.solver_role == "verification"]
    assert len(primary) == len(verification) == 17
    assert {r.instance_id for r in primary} == set(EXPECTED_TSP) and {r.instance_id for r in verification} == set(EXPECTED_TSP)
    for row in stage1.rows:
        assert row.status == "optimal" and row.stop_reason == "optimal"
        assert row.ub == row.lb == row.reference_optimum
        assert row.timing_dependent is False
        assert row.reference_optimum_source == "tsplib"
        assert row.solution_kind == "hamiltonian_cycle" and row.stage is None and row.protocol == protocol.PROTOCOL_ID
    assert {r.solver_name for r in primary} == {"gurobi"} and {r.solver_name for r in verification} == {"highs"}
    assert {r.problem_contract for r in stage1.rows if r.instance_id == "ft53"} == {"ATSP"}
    assert {r.problem_contract for r in stage1.rows if r.instance_id != "ft53"} == {"TSP"}
    manifest = stage1.manifest
    assert primary[0].option_string == manifest["solvers"]["gurobi"]["option_string"]  # verbatim from the manifest
    assert verification[0].option_string == manifest["solvers"]["highs"]["option_string"]


def test_rows_are_sorted_and_carry_no_gap_algorithm_or_budget_key(stage1):
    keys = [(r.instance_id, r.stage or "", r.solver_role) for r in stage1.rows]
    assert keys == sorted(keys)
    dumped = json.loads(stage1.model_dump_json())
    for row in dumped["rows"]:
        assert not [k for k in row if k.startswith("gap") or k in ("algorithm_id", "evaluation_budget")]


def test_wave_campaigns_load_and_every_stage_row_passes_validate_stage_row(e3, e4a):
    assert len(e3.rows) == 1368 and len(e4a.rows) == 10564
    for loaded in (e3, e4a):
        assert loaded.manifest_kind == "wave_campaign"
        for wave in loaded.manifest["waves"]:
            for stage in list(wave["stages"]) + list(wave.get("highs_stages", [])):
                assert protocol.validate_stage_row(stage) == []
        assert protocol.validate_manifest(loaded.manifest) == []
        keys = [(r.instance_id, r.stage, r.solver_role) for r in loaded.rows]
        assert len(set(keys)) == len(keys), "rows are unique per (instance, stage, solver role)"
        for row in loaded.rows:
            assert row.solution_kind == "vehicle_routes" and row.problem_contract == "uniride_wave"
            assert row.ub_validated is False and row.ub_validation_basis == "certified_by_producing_run"
            assert row.reference_optimum is None
    assert {r.status for r in e4a.rows} == {"optimal", "infeasible_proven"}
    assert {r.solver_name for r in e4a.rows} == {"gurobi", "highs"}


def test_wave_instance_ids_follow_date_ratio_wave_and_for_e4a_fleet_and_option(e3, e4a):
    first = e3.rows[0].instance_id
    assert first.startswith("2026-10-05_R50/2026-10-05:") and first.count("/") == 1
    typed = {r.instance_id for r in e4a.rows}
    assert any(i.endswith("/large+sedan/base") for i in typed) and any(i.endswith("/large+doblo_cap3/q0") for i in typed)


def test_peak_waves_carry_the_peak_option_string(e3):
    peak_ids = {w for v in e3.manifest["peak_waves"].values() for w in v["wave_ids"]}
    solver = e3.manifest["solver"]
    peak_rows = [r for r in e3.rows if r.solver_role == "primary" and r.instance_id.split("/", 1)[1] in peak_ids]
    normal_rows = [r for r in e3.rows if r.solver_role == "primary" and r.instance_id.split("/", 1)[1] not in peak_ids]
    assert peak_rows and normal_rows
    assert {r.option_string for r in peak_rows} == {solver["peak_option_string"]}
    assert {r.option_string for r in normal_rows} == {solver["option_string"]}


def test_discovery_reads_exactly_the_indexed_directories():
    sets = reader.discover_exact_references(REPO)
    assert [s.results_dir for s in sets] == [STAGE1, E3, E4A]
    assert [len(s.rows) for s in sets] == [34, 1368, 10564]
    assert all(r.protocol == "exact_reference_v1" for s in sets for r in s.rows)


def test_two_loads_give_identical_bytes(stage1, e3):
    assert load_exact_reference(STAGE1, repo_root=REPO).model_dump_json() == stage1.model_dump_json()
    assert load_exact_reference(E3, repo_root=REPO).model_dump_json() == e3.model_dump_json()


def test_the_committed_stage1_manifest_has_the_original_run_history_shape(stage1):
    assert "invocations_at_this_commit" in stage1.manifest["run_history"]


# ---------------------------------------------------------------- tampered stage-1 copies
@pytest.mark.parametrize("name", ["reference.csv", "tours.json", "README.md"])
def test_one_changed_byte_in_an_output_is_refused(stage1_root, name):
    path = stage1_root / STAGE1 / name
    data = bytearray(path.read_bytes())
    data[-2] = data[-2] ^ 0x01
    path.write_bytes(bytes(data))
    with pytest.raises(ExactReferenceRefused, match="sha256"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_a_reordered_csv_header_is_refused(stage1_root):
    table = _csv_table(stage1_root)
    table[0][0], table[0][1] = table[0][1], table[0][0]
    _rewrite_output(stage1_root, "reference.csv", _table_bytes(table))
    with pytest.raises(ExactReferenceRefused, match="header"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_a_csv_column_added_is_refused(stage1_root):
    table = [row + ["x"] for row in _csv_table(stage1_root)]
    _rewrite_output(stage1_root, "reference.csv", _table_bytes(table))
    with pytest.raises(ExactReferenceRefused, match="header"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_an_instance_missing_from_tours_json_is_refused(stage1_root):
    doc = json.loads((stage1_root / STAGE1 / "tours.json").read_text(encoding="utf-8"))
    del doc["tours"]["eil51"]
    _rewrite_output(stage1_root, "tours.json", (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    with pytest.raises(ExactReferenceRefused, match="eil51.*no tour"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_a_tour_length_that_differs_from_ub_is_refused(stage1_root):
    doc = json.loads((stage1_root / STAGE1 / "tours.json").read_text(encoding="utf-8"))
    doc["tours"]["eil51"]["length"] += 1
    _rewrite_output(stage1_root, "tours.json", (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    with pytest.raises(ExactReferenceRefused, match="eil51.*length"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_a_tour_for_an_unknown_instance_is_refused(stage1_root):
    doc = json.loads((stage1_root / STAGE1 / "tours.json").read_text(encoding="utf-8"))
    doc["tours"]["nowhere"] = copy.deepcopy(doc["tours"]["eil51"])
    _rewrite_output(stage1_root, "tours.json", (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    with pytest.raises(ExactReferenceRefused, match="absent from reference.csv"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_a_row_of_another_protocol_is_refused(stage1_root):
    _edit_csv(stage1_root, "berlin52", "protocol", "fixed_evaluation_budget")
    with pytest.raises(ExactReferenceRefused, match="protocol"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


@pytest.mark.parametrize("column, value, match", [
    ("gap_to_reference", "1", "gap_to_reference"),
    ("reference_in_bracket", "false", "reference_in_bracket"),
    ("verdict", "defect", "verdict"),
    ("reference_optimum", "7543", "reference_optimum"),
    ("n", "53", "differ from the manifest"),
    ("edge_weight_type", "ATT", "edge_weight_type"),
    ("solver_version", "Gurobi 99", "solver_version"),
    ("highs_agreement", "disagree", "contradiction"),
    ("highs_value", "7541", "HiGHS proved"),
    ("timing_dependent", "maybe", "true/false"),
    ("highs_timing_dependent", "", "highs_timing_dependent.*empty"),  # WP-E8 polish item 2: no silent False
    ("highs_timing_dependent", "maybe", "true/false"),
    ("ub", "seven", "not an integer"),
])
def test_an_inconsistent_csv_cell_is_refused(stage1_root, column, value, match):
    _edit_csv(stage1_root, "berlin52", column, value)
    with pytest.raises(ExactReferenceRefused, match=match):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_an_mtz_contradiction_is_refused(stage1_root):
    _edit_csv(stage1_root, "burma14", "mtz_value", "3000")
    with pytest.raises(ExactReferenceRefused, match="MTZ proved"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_unknown_manifest_schema_version_and_kind_are_refused(stage1_root):
    for field, value in (("schema_version", 2), ("manifest_kind", "tsp_reference_v2"), ("protocol", "fixed_evaluation_budget")):
        doc = _manifest(stage1_root)
        doc[field] = value
        _write_manifest(stage1_root, doc)
        with pytest.raises(ExactReferenceRefused, match="unknown"):
            load_exact_reference(STAGE1, repo_root=stage1_root)


def test_manifest_with_private_data_or_blocking_errors_is_refused(stage1_root):
    doc = _manifest(stage1_root)
    doc["python_provenance"]["uniride_core"] = "C:\\Users\\someone\\uniride_core\\__init__.py"
    _write_manifest(stage1_root, doc)
    with pytest.raises(ExactReferenceRefused, match="absolute path"):
        load_exact_reference(STAGE1, repo_root=stage1_root)
    doc = _manifest(stage1_root)
    doc["python_provenance"]["uniride_core"] = "uniride_core/__init__.py"
    doc["blocking_errors"] = ["x: published optimum neither reproduced nor bracketed"]
    _write_manifest(stage1_root, doc)
    with pytest.raises(ExactReferenceRefused, match="blocking errors"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_the_polished_run_history_shape_is_accepted_and_a_foreign_one_is_refused(stage1_root):
    doc = _manifest(stage1_root)
    doc["run_history"] = {"cache": "none", "ended_utc": "2026-10-19T10:00:00Z", "invocations_in_this_manifest": 1,
                          "retries": 0, "serial": True, "started_utc": "2026-10-19T09:00:00Z"}
    _write_manifest(stage1_root, doc)
    assert len(load_exact_reference(STAGE1, repo_root=stage1_root).rows) == 34
    doc["run_history"] = {"cache": "none", "retries": 0, "serial": True}
    _write_manifest(stage1_root, doc)
    with pytest.raises(ExactReferenceRefused, match="run_history"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


def test_outputs_must_list_exactly_the_three_files(stage1_root):
    doc = _manifest(stage1_root)
    del doc["outputs"]["README.md"]
    _write_manifest(stage1_root, doc)
    with pytest.raises(ExactReferenceRefused, match="outputs"):
        load_exact_reference(STAGE1, repo_root=stage1_root)


# ---------------------------------------------------------------- other manifest kinds and unsafe paths
def test_union_day_and_gap_report_directories_are_refused(tmp_path):
    union = tmp_path / "docs" / "union"
    union.mkdir(parents=True)
    shutil.copyfile(REPO / "docs/paper/results/week-2026-10-05-exact/wp-e4b-union-day/union_day_manifest.json", union / "union_day_manifest.json")
    with pytest.raises(ExactReferenceRefused, match="union_day_v1"):
        load_exact_reference("docs/union", repo_root=tmp_path)
    gap = tmp_path / "docs" / "gap"
    gap.mkdir()
    shutil.copyfile(REPO / "docs/paper/results/week-2026-10-05-exact/wp-e6-gap-report/manifest.json", gap / "manifest.json")
    with pytest.raises(ExactReferenceRefused, match="unknown"):
        load_exact_reference("docs/gap", repo_root=tmp_path)
    with pytest.raises(ExactReferenceRefused, match="union_day_v1"):  # also the committed one, through the real tree
        load_exact_reference("docs/paper/results/week-2026-10-05-exact/wp-e4b-union-day", repo_root=REPO)
    with pytest.raises(ExactReferenceRefused, match="unknown"):
        load_exact_reference("docs/paper/results/week-2026-10-05-exact/wp-e6-gap-report", repo_root=REPO)


@pytest.mark.parametrize("bad", [
    f"{REFUSED}/academic_benchmark/x", f"docs/{REFUSED.upper()}/x", f"./{REFUSED}", "C:/results/x", "/etc/results", "\\\\server\\share",
    "docs/../../outside", "..", "", "docs\\..\\..\\x",
])
def test_unsafe_results_dirs_are_refused(bad):
    with pytest.raises(ExactReferenceRefused):
        load_exact_reference(bad, repo_root=REPO)


def test_a_directory_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(ExactReferenceRefused, match="not a directory"):
        load_exact_reference("docs/none", repo_root=tmp_path)


def test_an_absolute_path_to_a_real_results_dir_is_still_refused():
    with pytest.raises(ExactReferenceRefused, match="repository-relative"):
        load_exact_reference(str(REPO / STAGE1), repo_root=REPO)


# ---------------------------------------------------------------- wave campaigns, tampered copies
def test_an_e3_copy_loads_like_the_original(e3_root, e3):
    assert load_exact_reference(E3, repo_root=e3_root).model_dump_json() == e3.model_dump_json()


def test_a_changed_exact_routes_file_is_refused(e3_root):
    path = e3_root / E3 / "exact_routes.json"
    data = bytearray(path.read_bytes())
    data[10] = data[10] ^ 0x01
    path.write_bytes(bytes(data))
    with pytest.raises(ExactReferenceRefused, match="exact_routes"):
        load_exact_reference(E3, repo_root=e3_root)


def test_a_source_campaign_fingerprint_mismatch_or_missing_file_is_refused(e3_root):
    source = e3_root / E3_SOURCE / "run_manifest.json"
    original = source.read_bytes()
    source.write_bytes(original + b" ")
    with pytest.raises(ExactReferenceRefused, match="fingerprint"):
        load_exact_reference(E3, repo_root=e3_root)
    source.unlink()
    with pytest.raises(ExactReferenceRefused, match="missing"):
        load_exact_reference(E3, repo_root=e3_root)


def test_a_source_campaign_manifest_with_either_line_ending_form_is_accepted(e3_root):
    source = e3_root / E3_SOURCE / "run_manifest.json"
    data = source.read_bytes()
    source.write_bytes(data.replace(b"\r\n", b"\n"))  # a Linux checkout holds the LF form
    assert len(load_exact_reference(E3, repo_root=e3_root).rows) == 1368
    source.write_bytes(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert len(load_exact_reference(E3, repo_root=e3_root).rows) == 1368


def test_a_wave_manifest_that_fails_its_schema_or_has_an_invalid_stage_row_is_refused(e3_root):
    path = e3_root / E3 / "exact_manifest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(doc)
    del broken["solver"]["threads"]
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ExactReferenceRefused, match="schema errors"):
        load_exact_reference(E3, repo_root=e3_root)
    broken = copy.deepcopy(doc)
    broken["waves"][0]["highs_stages"][0]["stop_reason"] = None  # an optimal HiGHS stage without a stop reason
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ExactReferenceRefused, match="HiGHS stage row invalid"):
        load_exact_reference(E3, repo_root=e3_root)
    broken = copy.deepcopy(doc)
    broken["waves"].append(copy.deepcopy(broken["waves"][0]))
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ExactReferenceRefused, match="twice"):
        load_exact_reference(E3, repo_root=e3_root)


def test_a_wave_manifest_with_blocking_errors_is_refused(e3_root):
    path = e3_root / E3 / "exact_manifest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["blocking_errors"] = ["a stage failed"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ExactReferenceRefused, match="blocking errors"):
        load_exact_reference(E3, repo_root=e3_root)


# ---------------------------------------------------------------- the index
def _index_root(tmp_path: Path, entries: list, schema: str = reader.INDEX_SCHEMA) -> Path:
    target = tmp_path / reader.INDEX_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"schema_version": schema, "entries": entries}), encoding="utf-8")
    return tmp_path


def _stage1_entry(root: Path, **changes) -> dict:
    manifest_sha = _sha((root / STAGE1 / "manifest.json").read_bytes())
    entry = {"results_dir": STAGE1, "manifest_file": "manifest.json", "manifest_kind": "tsp_reference",
             "manifest_sha256": manifest_sha, "rows": 34}
    entry.update(changes)
    return entry


def test_the_index_is_checked_against_manifest_sha_kind_and_row_count(stage1_root):
    root = _index_root(stage1_root, [_stage1_entry(stage1_root)])
    assert [len(s.rows) for s in reader.discover_exact_references(root)] == [34]
    for change, match in (({"manifest_sha256": "0" * 64}, "sha256"), ({"manifest_kind": "wave_campaign"}, "kind"), ({"rows": 33}, "rows")):
        root = _index_root(stage1_root, [_stage1_entry(stage1_root, **change)])
        with pytest.raises(ExactReferenceRefused, match=match):
            reader.discover_exact_references(root)


def test_the_index_refuses_an_unknown_schema_and_a_duplicate_entry_and_ignores_unlisted_directories(stage1_root):
    _copy_dir(E3.rsplit("/", 1)[0] + "/wp-e3-goal1-single", stage1_root)  # present on disk but not listed
    root = _index_root(stage1_root, [_stage1_entry(stage1_root)], schema="uniride-exact-results-index/v9")
    with pytest.raises(ExactReferenceRefused, match="schema_version"):
        reader.discover_exact_references(root)
    root = _index_root(stage1_root, [_stage1_entry(stage1_root), _stage1_entry(stage1_root)])
    with pytest.raises(ExactReferenceRefused, match="twice"):
        reader.discover_exact_references(root)
    root = _index_root(stage1_root, [_stage1_entry(stage1_root)])
    assert [s.results_dir for s in reader.discover_exact_references(root)] == [STAGE1], "no glob discovery"


def test_the_index_refuses_an_archive_entry(tmp_path):
    root = _index_root(tmp_path, [{"results_dir": f"{REFUSED}/x", "manifest_file": "manifest.json", "manifest_kind": "tsp_reference",
                                   "manifest_sha256": "0" * 64, "rows": 1}])
    with pytest.raises(ExactReferenceRefused, match=REFUSED):
        reader.discover_exact_references(root)


def test_the_frozen_csv_field_list_matches_the_runner_columns_and_the_committed_header():
    header = next(csv.reader(io.StringIO((REPO / STAGE1 / "reference.csv").read_bytes().decode("utf-8"), newline="")))
    assert tuple(header) == reader.TSP_REFERENCE_CSV_FIELDS_V1 and len(header) == 31


@pytest.mark.parametrize("prefix", [REFUSED, f"docs/{REFUSED}", f"docs/{REFUSED.upper()}/nested"])
def test_a_valid_results_copy_below_an_archive_named_folder_is_refused_by_name(tmp_path, prefix):
    shutil.copytree(REPO / STAGE1, tmp_path / prefix / "stage1")
    with pytest.raises(ExactReferenceRefused, match=REFUSED):
        load_exact_reference(f"{prefix}/stage1", repo_root=tmp_path)
    shutil.copytree(REPO / STAGE1, tmp_path / "docs" / "ok" / "stage1")
    assert len(load_exact_reference("docs/ok/stage1", repo_root=tmp_path).rows) == 34  # same bytes elsewhere: accepted


# ================================================================ Task 5: independent validation of the committed tours
DATA = REPO / "academic_benchmark" / "tsplib_data"


def _dataset_copy(root: Path) -> Path:
    """A fake repository root holding the tracked dataset collections (never the database)."""
    target = root / "academic_benchmark" / "tsplib_data"
    shutil.copytree(DATA, target, ignore=shutil.ignore_patterns("*.db", "*.db-*", "*.bak*"))
    return target


def test_all_17_stage1_tours_are_validated_from_the_tracked_artifacts_with_no_skip(stage1):
    """CI gate: 17 of 17, a missing artifact would fail (there is no skip anywhere in this module)."""
    assert all(not r.ub_validated and r.ub_validation_basis == "not_validated" for r in stage1.rows), "loading validates nothing"
    validated = reader.validate_hamiltonian_rows(stage1, dataset_root=DATA, repo_root=REPO)
    primary = [r for r in validated.rows if r.solver_role == "primary"]
    verification = [r for r in validated.rows if r.solver_role == "verification"]
    assert len(primary) == 17 and all(r.ub_validated and r.ub_validation_basis == "independent_hamiltonian_validator" for r in primary)
    assert {r.instance_id for r in primary} == set(EXPECTED_TSP)
    assert len(verification) == 17 and all(not r.ub_validated and r.ub_validation_basis == "not_validated" for r in verification), \
        "HiGHS rows carry no tour: not validated"
    assert all(r.status == "optimal" and r.ub == r.reference_optimum for r in validated.rows)
    assert all(not r.ub_validated for r in stage1.rows), "the input set is not modified"


def test_validation_is_deterministic(stage1):
    first = reader.validate_hamiltonian_rows(stage1, dataset_root=DATA, repo_root=REPO).model_dump_json()
    assert first == reader.validate_hamiltonian_rows(stage1, dataset_root=DATA, repo_root=REPO).model_dump_json()


def test_the_tracked_artifacts_match_the_stage1_manifest_fingerprints(stage1):
    manifest = stage1.manifest
    collection = {e["name"]: e for e in json.loads((DATA / "tsp" / "MANIFEST.json").read_text(encoding="utf-8"))["instances"]}
    from academic_benchmark.exact_reference import inputs
    from academic_benchmark.validation import hamiltonian_cycle as hc

    kinds = {}
    for name, inst in manifest["instances"].items():
        kinds[inst["data_source"]] = kinds.get(inst["data_source"], 0) + 1
        if inst["data_source"] == "atsp_file":
            assert _sha((DATA / "ft53.atsp").read_bytes()) == inst["sha256"]
            continue
        raw = (DATA / "tsp" / collection[name]["file_name"]).read_bytes()
        if inst["data_source"] == "tsp_file":
            assert _sha(raw) == inst["sha256"], name
        else:
            coords = hc.parse_coordinates(raw.decode("utf-8"))
            assert inputs.coordinate_text_sha256(coords) == inst["sha256"], name
        assert collection[name]["dimension"] == inst["n"] and collection[name]["edge_weight_type"] == inst["edge_weight_type"]
    assert kinds == {"tsp_file": 5, "tsplib_db_coordinates": 11, "atsp_file": 1}


def test_a_swapped_pair_of_nodes_in_a_copied_tours_json_is_detected(stage1_root):
    doc = json.loads((stage1_root / STAGE1 / "tours.json").read_text(encoding="utf-8"))
    tour = doc["tours"]["eil51"]["tour"]
    tour[3], tour[10] = tour[10], tour[3]  # still a permutation, but another length; the recorded length is unchanged
    _rewrite_output(stage1_root, "tours.json", (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    loaded = load_exact_reference(STAGE1, repo_root=stage1_root)  # the Task 4 checks cannot see it
    with pytest.raises(ExactReferenceRefused, match="eil51.*recomputed closed length"):
        reader.validate_hamiltonian_rows(loaded, dataset_root=DATA, repo_root=REPO)


def test_a_repeated_node_and_a_subtour_in_a_copied_tours_json_are_detected(stage1_root):
    for mutate, match in ((lambda t: t.__setitem__(5, t[4]), "repeats a node"), (lambda t: t.pop(), "subtour")):
        doc = json.loads((REPO / STAGE1 / "tours.json").read_text(encoding="utf-8"))
        mutate(doc["tours"]["st70"]["tour"])
        _rewrite_output(stage1_root, "tours.json", (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        loaded = load_exact_reference(STAGE1, repo_root=stage1_root)
        with pytest.raises(ExactReferenceRefused, match=match):
            reader.validate_hamiltonian_rows(loaded, dataset_root=DATA, repo_root=REPO)


def test_a_reversed_atsp_tour_is_a_different_cycle(stage1_root):
    doc = json.loads((REPO / STAGE1 / "tours.json").read_text(encoding="utf-8"))
    doc["tours"]["ft53"]["tour"].reverse()
    _rewrite_output(stage1_root, "tours.json", (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    loaded = load_exact_reference(STAGE1, repo_root=stage1_root)
    with pytest.raises(ExactReferenceRefused, match="ft53.*recomputed closed length"):
        reader.validate_hamiltonian_rows(loaded, dataset_root=DATA, repo_root=REPO)


def _never_compute_a_length(monkeypatch):
    from academic_benchmark.validation import hamiltonian_cycle as hc

    def boom(*args, **kwargs):
        raise AssertionError("a length was computed before the artifact checks finished")

    monkeypatch.setattr(hc, "closed_length", boom)
    monkeypatch.setattr(hc, "validate_hamiltonian_cycle", boom)


def test_a_changed_coordinate_is_refused_by_the_sha_check_before_any_length_is_computed(stage1, tmp_path, monkeypatch):
    data = _dataset_copy(tmp_path)
    path = data / "tsp" / "eil51.tsp"
    text = path.read_bytes().decode("utf-8")
    assert "37 52" in text
    path.write_bytes(text.replace("37 52", "37 53", 1).encode("utf-8"))
    _never_compute_a_length(monkeypatch)
    with pytest.raises(ExactReferenceRefused, match="eil51.*sha256"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


def test_a_changed_coordinate_with_a_rewritten_file_sha_is_refused_by_the_coordinate_fingerprint(stage1, tmp_path, monkeypatch):
    data = _dataset_copy(tmp_path)
    path = data / "tsp" / "eil51.tsp"
    changed = path.read_bytes().decode("utf-8").replace("37 52", "37 53", 1).encode("utf-8")
    path.write_bytes(changed)
    manifest = json.loads((data / "tsp" / "MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["instances"]:
        if entry["name"] == "eil51":
            entry["sha256"] = _sha(changed)  # an attacker also fixes the file sha, not the coordinate fingerprint
    (data / "tsp" / "MANIFEST.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    _never_compute_a_length(monkeypatch)
    with pytest.raises(ExactReferenceRefused, match="eil51.*(fingerprint|sha256)"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


def _consistent_collection_copy_with_other_bytes(manifest_path: Path, instance: str, artifact: Path) -> str:
    """Change the bytes of one tracked artifact WITHOUT changing what it parses to (a trailing blank line) and make the
    collection manifest entry agree (file sha256), so every collection check passes and only the comparison with the
    stage-1 manifest can notice. Returns the new file sha256."""
    changed = artifact.read_bytes() + b"\n"
    artifact.write_bytes(changed)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = [e for e in manifest["instances"] if e["name"] == instance]
    assert len(entries) == 1
    entries[0]["sha256"] = _sha(changed)
    manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return _sha(changed)


@pytest.mark.parametrize("instance, relative, manifest_relative", [
    ("eil51", "tsp/eil51.tsp", "tsp/MANIFEST.json"),  # data_source tsp_file
    ("ft53", "ft53.atsp", "atsp/MANIFEST.json"),      # data_source atsp_file
])
def test_a_consistent_collection_copy_with_another_file_sha_is_refused_against_the_stage1_manifest(
        stage1, tmp_path, instance, relative, manifest_relative):
    """WP-E8 polish item 1 (mutant M15): the collection manifest and the file agree with each other and the parsed content
    is unchanged; only the stage-1 manifest fingerprint of the file differs, and that comparison alone has to refuse."""
    data = _dataset_copy(tmp_path)
    new_sha = _consistent_collection_copy_with_other_bytes(data / manifest_relative, instance, data / relative)
    assert new_sha != stage1.manifest["instances"][instance]["sha256"]
    with pytest.raises(ExactReferenceRefused, match=f"{instance}: the tracked file sha256 {new_sha} differs from the stage-1 manifest"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


def test_a_db_coordinate_instance_with_both_fingerprints_rewritten_still_fails_against_stage1(stage1, tmp_path, monkeypatch):
    data = _dataset_copy(tmp_path)
    from academic_benchmark.exact_reference import inputs
    from academic_benchmark.validation import hamiltonian_cycle as hc

    path = data / "tsp" / "kroA100.tsp"
    text = path.read_bytes().decode("utf-8")
    first = [line for line in text.splitlines() if line.startswith("1 ")][0]
    x, y = first.split()[1:3]
    changed = text.replace(first, f"1 {float(x) + 1!r} {y}", 1).encode("utf-8")
    path.write_bytes(changed)
    manifest = json.loads((data / "tsp" / "MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["instances"]:
        if entry["name"] == "kroa100":
            entry["sha256"] = _sha(changed)
            entry["coordinate_text_sha256"] = inputs.coordinate_text_sha256(hc.parse_coordinates(changed.decode("utf-8")))
    (data / "tsp" / "MANIFEST.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    _never_compute_a_length(monkeypatch)
    with pytest.raises(ExactReferenceRefused, match="kroa100.*stage-1 manifest"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


@pytest.mark.parametrize("victim, relative", [("kroA100", "tsp/kroA100.tsp"), ("ft53", "ft53.atsp")])
def test_a_missing_artifact_fails_it_does_not_skip(stage1, tmp_path, victim, relative):
    data = _dataset_copy(tmp_path)
    (data / relative).unlink()
    with pytest.raises(ExactReferenceRefused, match=f"{victim}.*missing"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


def test_an_altered_ft53_matrix_is_refused_by_its_sha(stage1, tmp_path):
    data = _dataset_copy(tmp_path)
    path = data / "ft53.atsp"
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b"223", b"224", 1))
    with pytest.raises(ExactReferenceRefused, match="ft53.*sha256"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


def test_an_instance_missing_from_the_collection_manifest_fails(stage1, tmp_path):
    data = _dataset_copy(tmp_path)
    manifest = json.loads((data / "tsp" / "MANIFEST.json").read_text(encoding="utf-8"))
    manifest["instances"] = [e for e in manifest["instances"] if e["name"] != "rd100"]
    (data / "tsp" / "MANIFEST.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    with pytest.raises(ExactReferenceRefused, match="rd100.*lists no such instance"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)


def test_wave_sets_are_never_validated_here(e3):
    with pytest.raises(ExactReferenceRefused, match="certified by the producing run"):
        reader.validate_hamiltonian_rows(e3, dataset_root=DATA, repo_root=REPO)


def test_published_tours_where_the_collection_holds_one_have_the_reference_length(stage1):
    checked = reader.cross_check_published_tours(stage1, dataset_root=DATA, repo_root=REPO)
    assert len(checked) == 13
    assert not {"burma14", "ft53", "krob100", "kroe100"} & set(checked)  # no published tour: skipped by design


def test_a_published_tour_with_another_length_is_refused(stage1, tmp_path):
    data = _dataset_copy(tmp_path)
    manifest_path = data / "opt_tours" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(e for e in manifest["instances"] if e["name"].lower() == "eil51")
    tour_path = data / "opt_tours" / entry["file_name"]
    lines = tour_path.read_bytes().decode("utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("TOUR_SECTION")) + 1
    lines[start + 2], lines[start + 9] = lines[start + 9], lines[start + 2]
    changed = "\n".join(lines).encode("utf-8")
    tour_path.write_bytes(changed)
    entry["sha256"] = _sha(changed)
    manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    with pytest.raises(ExactReferenceRefused, match="eil51.*published tour"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=data, repo_root=tmp_path)  # the stage-1 tours are fine ...
        reader.cross_check_published_tours(stage1, dataset_root=data, repo_root=tmp_path)  # ... the published one is not


def test_a_primary_row_without_an_incumbent_is_never_marked_validated(stage1):
    rows = list(stage1.rows)
    index = next(i for i, r in enumerate(rows) if r.solver_role == "primary" and r.instance_id == "eil51")
    rows[index] = rows[index].model_copy(update={"status": "bound_only", "stop_reason": "wall_limit", "timing_dependent": True,
                                                  "ub": None, "lb": 400})
    modified = stage1.model_copy(update={"rows": rows})
    validated = reader.validate_hamiltonian_rows(modified, dataset_root=DATA, repo_root=REPO)
    by_id = {(r.instance_id, r.solver_role): r for r in validated.rows}
    assert not by_id[("eil51", "primary")].ub_validated and by_id[("eil51", "primary")].ub_validation_basis == "not_validated"
    assert sum(r.ub_validated for r in validated.rows) == 16


def test_a_distance_disagreement_between_validator_and_solver_matrix_is_refused_before_the_tours(stage1, monkeypatch):
    """The validator rebuilds the matrix and its sha256 must equal the one the solver run recorded: this proves that both
    sides use one distance convention, and it is checked before any tour is looked at."""
    from academic_benchmark.validation import hamiltonian_cycle as hc

    original = hc.tsplib_distance
    monkeypatch.setattr(hc, "tsplib_distance", lambda ewt, a, b, **kw: original(ewt, a, b, **kw) + 1)
    with pytest.raises(ExactReferenceRefused, match="rebuilt by the independent validator"):
        reader.validate_hamiltonian_rows(stage1, dataset_root=DATA, repo_root=REPO)
