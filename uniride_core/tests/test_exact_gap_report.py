"""WP-E6: the gap report generator (scripts/plan_exact_gap_report.py) and its figure writer.

Offline: the report reads only committed results and the GA source manifests; no AMPL, no solver, no DB. Every expected
number below is recomputed from the source files here, independently of the report code.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import shutil
import statistics
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import pytest

matplotlib = pytest.importorskip(
    "matplotlib", reason="matplotlib is the optional paper-figure dependency (requirements-paper.txt)")

REPO = Path(__file__).resolve().parents[2]
for _p in (REPO / "optimizer_api", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

RESULTS = REPO / "docs" / "paper" / "results"
EXACT = RESULTS / "week-2026-10-05-exact"
E3, E4A, E4B = EXACT / "wp-e3-goal1-single", EXACT / "wp-e4a-typed-options", EXACT / "wp-e4b-union-day"
GA_DIRS = {"single_4sw5so": "week-2026-10-05-4sw5so", "large+sedan": "week-2026-10-05-fleet-rerun-large-sedan",
           "large+doblo_cap3": "week-2026-10-05-fleet-rerun-doblo-cap3"}
FLEETS = ("single_4sw5so", "large+sedan", "large+doblo_cap3")


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gr = _load("plan_exact_gap_report")
fig = _load("exact_gap_figure")


def _csv(path):
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _outputs(out):
    return {p.name: p.read_bytes() for p in sorted(Path(out).iterdir()) if p.is_file()}


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("gap_report") / "out"
    gr.build_report(out)
    return out


def _mirror(tmp_path: Path) -> dict:
    """A minimal copy of the inputs under a fake repo root, so that tests can alter an input file."""
    root = tmp_path / "repo"
    res = root / "docs" / "paper" / "results"
    for rel in [GA_DIRS[f] + "/run_manifest.json" for f in FLEETS]:
        (res / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RESULTS / rel, res / rel)
    dirs = {}
    for key, src, names in (("e3", E3, ("wave_gaps.csv", "exact_manifest.json", "exact_routes.json")),
                            ("e4a", E4A, ("option_gaps.csv", "replay.csv", "exact_manifest.json", "exact_routes.json")),
                            ("e4b", E4B, ("day_gaps.csv", "day_sums.csv", "union_day_manifest.json"))):
        dst = res / "week-2026-10-05-exact" / src.name
        dst.mkdir(parents=True)
        for name in names:
            shutil.copyfile(src / name, dst / name)
        dirs[key] = dst
    return {"root": root, "res": res, **dirs}


def _build_mirror(m, out):
    return gr.build_report(out, repo=m["root"], e3_dir=m["e3"], e4a_dir=m["e4a"], e4b_dir=m["e4b"])


def _rewrite_json(path: Path, mutate):
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))


# ---------------------------------------------------------------------------------------------------------- schema
SECTION9_COLUMNS = (
    "date", "R", "fleet", "option", "quota", "wave_id", "direction", "anchor", "students", "peak", "model", "columns",
    "K_GA", "K_LB", "K_star", "D_GA", "D_LB", "D_star", "D_LB_free", "dK", "gD", "gD_free", "status",
    "stage1_status", "stage1_stop_reason", "stage1_timing_dependent",
    "stage2_status", "stage2_stop_reason", "stage2_timing_dependent", "stage2_non_lexicographic",
    "free_status", "free_stop_reason", "free_timing_dependent",
    "solver", "solver_version", "enumeration_seconds", "solve_seconds",
    "ga_protocol", "ga_seed", "ga_commit", "ga_dirty_tree")


def test_outputs_are_written_with_lf_only(report):
    names = set(_outputs(report))
    assert names == set(gr.OUTPUT_FILES) | {"manifest.json"}
    for name, data in _outputs(report).items():
        if name.endswith((".csv", ".md", ".json", ".svg")):
            assert b"\r" not in data, name


def test_wave_gaps_schema_and_section9_columns(report):
    rows = _csv(report / "wave_gaps.csv")
    header = tuple(rows[0].keys())
    assert header == gr.WAVE_FIELDS
    assert set(SECTION9_COLUMNS) <= set(header)
    assert len(rows) == 228 + 1004 + 868
    assert {r["fleet"] for r in rows} == set(FLEETS)
    assert {r["option"] for r in rows} == {"base", "q"}
    assert all(r["protocol"] == "exact_reference_v1" for r in rows)
    assert all((r["quota"] == "") == (r["option"] == "base" or r["fleet"] == "single_4sw5so") for r in rows)
    assert all(r["option"] == "base" and r["quota"] == "" for r in rows if r["fleet"] == "single_4sw5so")
    assert not any("min" in c.lower().split("_") or c.lower().startswith("min(") for c in header)


def test_wave_rows_equal_their_sources_value_by_value(report):
    out = {(r["fleet"], r["date"], r["R"], r["wave_id"], r["option"] + r["quota"]): r for r in _csv(report / "wave_gaps.csv")}
    src = {}
    for r in _csv(E3 / "wave_gaps.csv"):
        src[(r["fleet"], r["date"], r["R"], r["wave_id"], "base")] = r
    for r in _csv(E4A / "option_gaps.csv"):
        src[(r["fleet"], r["date"], r["R"], r["wave_id"], r["option"])] = r
    assert out.keys() == src.keys()
    same = ("direction", "anchor", "students", "peak", "model", "columns", "K_GA", "K_LB", "K_star", "D_GA", "D_LB", "D_star",
            "D_LB_free", "dK", "gD", "gD_free", "status", "stage1_status", "stage1_stop_reason", "stage1_timing_dependent",
            "stage2_status", "stage2_stop_reason", "stage2_timing_dependent", "stage2_non_lexicographic", "free_status",
            "free_stop_reason", "free_timing_dependent", "solver", "solver_version", "enumeration_seconds", "solve_seconds",
            "highs_status", "highs_agrees")
    for key, row in out.items():
        for col in same:
            assert row[col] == src[key][col], (key, col)


def test_ga_labels_come_from_the_source_manifests(report):
    for fleet in FLEETS:
        manifest = json.loads((RESULTS / GA_DIRS[fleet] / "run_manifest.json").read_text(encoding="utf-8"))
        want = {"ga_protocol": manifest["termination_protocol"], "ga_seed": str(manifest["effective_seed"]),
                "ga_commit": manifest["git_commit"][:7], "ga_dirty_tree": str(manifest["dirty_working_tree"])}
        rows = [r for r in _csv(report / "wave_gaps.csv") if r["fleet"] == fleet]
        assert rows and all({k: r[k] for k in want} == want for r in rows), fleet
    single = [r for r in _csv(report / "wave_gaps.csv") if r["fleet"] == "single_4sw5so"][0]
    assert (single["ga_commit"], single["ga_dirty_tree"]) == ("6be127d", "True")


def test_ga_labels_are_not_hard_coded(tmp_path):
    """Change the seed consistently in the GA manifest, the recorded sha, the exact manifest and the CSV: the output follows."""
    m = _mirror(tmp_path)
    ga = m["res"] / GA_DIRS["single_4sw5so"] / "run_manifest.json"
    _rewrite_json(ga, lambda d: d.__setitem__("effective_seed", 43))
    _rewrite_json(m["e3"] / "exact_manifest.json", lambda d: (d["source_campaign"].__setitem__("manifest_sha256", _sha(ga)),
                                                              d["source_campaign"].__setitem__("effective_seed", 43),
                                                              d["ga_labels"].__setitem__("ga_seed", 43)))
    text = (m["e3"] / "wave_gaps.csv").read_bytes().decode("utf-8")
    (m["e3"] / "wave_gaps.csv").write_bytes(re.sub(r",native,42,", ",native,43,", text).encode("utf-8"))
    _build_mirror(m, tmp_path / "out")
    rows = [r for r in _csv(tmp_path / "out" / "wave_gaps.csv") if r["fleet"] == "single_4sw5so"]
    assert {r["ga_seed"] for r in rows} == {"43"}
    assert {r["ga_seed"] for r in _csv(tmp_path / "out" / "wave_gaps.csv") if r["fleet"] != "single_4sw5so"} == {"42"}


def test_report_refuses_a_csv_whose_ga_labels_differ_from_the_source_manifest(tmp_path):
    m = _mirror(tmp_path)
    text = (m["e3"] / "wave_gaps.csv").read_bytes().decode("utf-8")
    (m["e3"] / "wave_gaps.csv").write_bytes(text.replace(",native,42,6be127d,True", ",native,42,6be127d,False", 1).encode("utf-8"))
    with pytest.raises(gr.ReportRefused, match="ga_dirty_tree"):
        _build_mirror(m, tmp_path / "out")


# ---------------------------------------------------------------------------------------------------- day files
def test_day_gaps_are_the_wp_e4b_rows_unchanged_and_have_no_min_column(report):
    out, src = _csv(report / "day_gaps.csv"), _csv(E4B / "day_gaps.csv")
    assert out == src and len(out) == 120
    assert not any("min(" in c.lower() or c.lower().startswith("min") for c in out[0])
    labels = {k: sum(r["label"] == k for r in out) for k in ("proven_over_union_menu", "both_infeasible_for_L", "ga_menu_infeasible_for_L")}
    assert labels == {"proven_over_union_menu": 91, "both_infeasible_for_L": 28, "ga_menu_infeasible_for_L": 1}


def test_day_sums_typed_rows_unchanged_and_single_rows_recomputed(report):
    out = _csv(report / "day_sums.csv")
    assert tuple(out[0].keys()) == gr.DAY_SUMS_FIELDS
    typed_src = _csv(E4B / "day_sums.csv")
    assert [r for r in out if r["fleet"] != "single_4sw5so"] == typed_src
    single = {(r["date"], r["R"]): r for r in out if r["fleet"] == "single_4sw5so"}
    assert len(single) == 20
    waves: dict = {}
    for r in _csv(E3 / "wave_gaps.csv"):
        waves.setdefault((r["date"], r["R"]), []).append(r)
    for key, rs in waves.items():
        defined = [r for r in rs if r["gD"] != ""]
        d_ga, d_lb = sum(int(r["D_GA"]) for r in defined), sum(int(r["D_LB"]) for r in defined)
        row = single[key]
        assert int(row["base_waves_compared"]) == len(rs)
        assert int(row["dK_day_base"]) == sum(int(r["dK"]) for r in rs)
        assert float(row["gD_day_base"]) == pytest.approx(round((d_ga - d_lb) / d_lb, 6), abs=1e-9)
        assert int(row["gD_excluded_waves_base"]) == len(rs) - len(defined)
        assert row["q_options_compared"] == "" and row["dK_sum_over_q_options"] == ""


# --------------------------------------------------------------------------------------------------------- table
def _expected_table():
    """Independent recomputation of table_by_R.csv from the two source files."""
    rows = []
    for r in _csv(E3 / "wave_gaps.csv"):
        rows.append(dict(r, kind="base", comparison="compared"))
    for r in _csv(E4A / "option_gaps.csv"):
        rows.append(dict(r))
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["fleet"], int(r["R"]), r["kind"]), []).append(r)
    out = {}
    for key, rs in groups.items():
        compared = [r for r in rs if r["comparison"] == "compared"]
        comparable = [r for r in compared if r["gD_note"] == "comparable"]
        gd = [float(r["gD"]) for r in comparable]
        out[key] = {
            "rows": len(rs), "exact_feasible": sum(r["status"] in ("optimal", "feasible_with_gap") for r in rs),
            "exact_infeasible_proven": sum(r["status"] == "infeasible_proven" for r in rs), "compared": len(compared),
            "both_infeasible": sum(r["comparison"] == "both_infeasible" for r in rs),
            "ga_infeasible_exact_feasible": sum(r["comparison"] == "ga_infeasible_exact_feasible" for r in rs),
            "dK_zero": sum(r["dK"] == "0" for r in compared), "dK_positive": sum(int(r["dK"]) > 0 for r in compared),
            "gD_comparable": len(comparable), "gD_positive": sum(v > 0 for v in gd), "gD_mean": statistics.fmean(gd),
            "gD_max": max(gd), "gD_not_comparable": sum(r["gD_note"] == "not_comparable_K_GA_gt_Kstar" for r in compared),
            "highs_same_K_D_optimal": sum(r["status"] == "optimal" and r["highs_status"] == "optimal"
                                          and r["highs_agrees"] == "True" for r in rs),
            "highs_both_infeasible": sum(r["status"] == "infeasible_proven" and r["highs_status"] == "infeasible_proven"
                                         and r["highs_agrees"] == "True" for r in rs),
            "highs_free_same_optimal": sum(r["status"] == "optimal" and r["highs_free_agrees"] == "True" for r in rs)}
    return out


def test_table_by_R_matches_an_independent_recomputation_and_never_pools_fleets(report):
    table = _csv(report / "table_by_R.csv")
    assert tuple(table[0].keys()) == gr.TABLE_FIELDS
    expected = _expected_table()
    assert len(table) == len(expected) == 4 * (1 + 2 * 2)
    seen = set()
    for row in table:
        key = (row["fleet"], int(row["R"]), row["option_kind"])
        assert key in expected and key not in seen
        seen.add(key)
        want = expected[key]
        for col in ("rows", "exact_feasible", "exact_infeasible_proven", "compared", "both_infeasible",
                    "ga_infeasible_exact_feasible", "dK_zero", "dK_positive", "gD_comparable", "gD_positive",
                    "gD_not_comparable", "highs_same_K_D_optimal", "highs_both_infeasible", "highs_free_same_optimal"):
            assert int(row[col]) == want[col], (key, col)
        assert float(row["dK_zero_share"]) == pytest.approx(want["dK_zero"] / want["compared"], abs=5e-7)
        assert float(row["gD_mean"]) == pytest.approx(want["gD_mean"], abs=5e-7), key
        assert float(row["gD_max"]) == pytest.approx(want["gD_max"], abs=5e-7), key
        assert row["fleet"] in FLEETS and row["option_kind"] in ("base", "q")
    assert {k[0] for k in seen} == set(FLEETS)  # one row set per fleet, never an all-fleet row


def test_table_denominators_include_no_infeasible_or_uncompared_rows(report):
    expected = _expected_table()
    infeasible_seen = False
    for row in _csv(report / "table_by_R.csv"):
        key = (row["fleet"], int(row["R"]), row["option_kind"])
        assert int(row["compared"]) == expected[key]["compared"] <= int(row["rows"])
        assert int(row["gD_comparable"]) <= int(row["compared"])
        infeasible_seen |= int(row["exact_infeasible_proven"]) > 0
        assert float(row["dK_zero_share"]) == pytest.approx(int(row["dK_zero"]) / int(row["compared"]), abs=5e-7)
        # each HiGHS count stays inside its own denominator (optimal rows / proven-infeasible rows)
        assert int(row["highs_same_K_D_optimal"]) <= int(row["exact_feasible"])
        assert int(row["highs_free_same_optimal"]) <= int(row["exact_feasible"])
        assert int(row["highs_both_infeasible"]) <= int(row["exact_infeasible_proven"])
    assert infeasible_seen  # the q rows of large+sedan hold proven-infeasible options; they must stay out of 'compared'


def test_markdown_table_renders_every_row(report):
    text = (report / "table_by_R.md").read_text(encoding="utf-8")
    table = _csv(report / "table_by_R.csv")
    lines = [ln for ln in text.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert any(ln.startswith("| fleet |") for ln in lines)
    for row in table:
        assert any(ln.startswith(f"| {row['fleet']} | {row['R']} | {row['option_kind']} |") for ln in lines), row
    assert "denominator" in text.lower()


def test_day_label_table_counts_the_day_rows(report):
    rows = _csv(report / "table_day_labels.csv")
    src = _csv(E4B / "day_gaps.csv")
    assert tuple(rows[0].keys()) == gr.DAY_LABEL_FIELDS
    for row in rows:
        mine = [r for r in src if r["fleet"] == row["fleet"] and r["L"] == row["L"]]
        assert int(row["cells"]) == len(mine)
        for label in ("proven_over_union_menu", "ga_menu_infeasible_for_L", "both_infeasible_for_L", "union_not_proven"):
            assert int(row[label]) == sum(r["label"] == label for r in mine)
        diffs = [int(r["cars_difference_union_minus_ga"]) for r in mine if r["label"] == "proven_over_union_menu"]
        assert int(row["union_cars_below_ga"]) == sum(d < 0 for d in diffs)
        assert int(row["union_cars_equal_ga"]) == sum(d == 0 for d in diffs)
        assert int(row["union_cars_above_ga"]) == sum(d > 0 for d in diffs)
        assert (int(row["union_cars_below_ga"]) + int(row["union_cars_equal_ga"]) + int(row["union_cars_above_ga"])
                == int(row["proven_over_union_menu"]))
    by = {(r["fleet"], r["L"]): r for r in rows}
    doblo2 = by[("large+doblo_cap3", "2")]
    assert (doblo2["union_cars_below_ga"], doblo2["union_cars_equal_ga"]) == ("2", "18")  # counted by cars, not car-minutes
    assert sum(int(r["cells"]) for r in rows) == 120


# ---------------------------------------------------------------------------------------------------- manifest
def test_manifest_lists_every_input_with_its_sha_and_every_output(report):
    manifest = json.loads((report / "manifest.json").read_text(encoding="utf-8"))
    expected_inputs = {
        "docs/paper/results/week-2026-10-05-exact/wp-e3-goal1-single/" + n for n in ("wave_gaps.csv", "exact_manifest.json", "exact_routes.json")
    } | {"docs/paper/results/week-2026-10-05-exact/wp-e4a-typed-options/" + n
         for n in ("option_gaps.csv", "replay.csv", "exact_manifest.json", "exact_routes.json")
         } | {"docs/paper/results/week-2026-10-05-exact/wp-e4b-union-day/" + n
              for n in ("day_gaps.csv", "day_sums.csv", "union_day_manifest.json")
              } | {f"docs/paper/results/{d}/run_manifest.json" for d in GA_DIRS.values()}
    inputs = manifest["inputs"]
    assert set(inputs) == expected_inputs
    for rel, sha in inputs.items():
        assert sha == _sha(REPO / rel), rel
    outs = _outputs(report)
    assert set(manifest["outputs"]) == set(outs) - {"manifest.json"}
    for name, sha in manifest["outputs"].items():
        assert sha == hashlib.sha256(outs[name]).hexdigest(), name
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["git_commit"]) and isinstance(manifest["dirty_working_tree"], bool)
    assert manifest["work_package"] == "WP-E6"
    assert set(manifest["python_provenance"]) == {"uniride_core", "academic_benchmark"}
    assert all(not Path(v).is_absolute() for v in manifest["python_provenance"].values())
    assert manifest["versions"]["python"] and manifest["versions"]["zlib"] == zlib.ZLIB_VERSION
    assert manifest["protocols"]["wave_gaps.csv"] == "exact_reference_v1" and manifest["protocols"]["day_gaps.csv"] == "union_day_v1"
    assert gr.protocol.private_data_errors(manifest) == []  # protocol module via the script (core tests import no academic_benchmark)


# ---------------------------------------------------------------------------------------------------- refusals
@pytest.mark.parametrize("which,name", [("e3", "exact_routes.json"), ("e4a", "exact_routes.json")])
def test_report_refuses_exact_routes_whose_sha_differs_from_the_manifest(tmp_path, which, name):
    m = _mirror(tmp_path)
    path = m[which] / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(gr.ReportRefused, match="exact_routes"):
        _build_mirror(m, tmp_path / "out")


def test_report_refuses_a_ga_manifest_whose_sha_differs_from_the_recorded_one(tmp_path):
    m = _mirror(tmp_path)
    path = m["res"] / GA_DIRS["large+sedan"] / "run_manifest.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(gr.ReportRefused, match="run_manifest"):
        _build_mirror(m, tmp_path / "out")


def test_report_refuses_e4a_option_gaps_that_differ_from_the_hash_the_union_manifest_recorded(tmp_path):
    m = _mirror(tmp_path)
    path = m["e4a"] / "option_gaps.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(gr.ReportRefused, match="option_gaps"):
        _build_mirror(m, tmp_path / "out")


def test_report_refuses_an_invalid_union_manifest_and_unclean_sources(tmp_path):
    m = _mirror(tmp_path)
    _rewrite_json(m["e4b"] / "union_day_manifest.json", lambda d: d.__setitem__("time_scale", 1))
    with pytest.raises(gr.ReportRefused, match="union_day_v1"):
        _build_mirror(m, tmp_path / "out")
    m2 = _mirror(tmp_path / "second")
    _rewrite_json(m2["e3"] / "exact_manifest.json", lambda d: d.__setitem__("blocking_errors", ["boom"]))
    with pytest.raises(gr.ReportRefused, match="blocking"):
        _build_mirror(m2, tmp_path / "second" / "out")


@pytest.mark.parametrize("which,name", [("e3", "exact_manifest.json"), ("e4a", "exact_manifest.json"),
                                        ("e4b", "union_day_manifest.json")])
def test_report_refuses_a_source_run_made_on_a_dirty_tree(tmp_path, which, name):
    m = _mirror(tmp_path)
    _rewrite_json(m[which] / name, lambda d: d.__setitem__("dirty_working_tree", True))
    with pytest.raises(gr.ReportRefused, match="dirty tree"):
        _build_mirror(m, tmp_path / "out")


def test_report_refuses_day_sums_that_disagree_with_the_option_rows(tmp_path):
    m = _mirror(tmp_path)
    path = m["e4b"] / "day_sums.csv"
    lines = path.read_bytes().decode("utf-8").split("\n")
    cells = lines[1].split(",")
    cells[4] = str(int(cells[4]) + 1)  # dK_day_base
    lines[1] = ",".join(cells)
    path.write_bytes("\n".join(lines).encode("utf-8"))
    with pytest.raises(gr.ReportRefused, match="day_sums"):
        _build_mirror(m, tmp_path / "out")


def test_output_directory_rule(tmp_path):
    with pytest.raises(gr.ReportRefused, match="--out"):
        gr.build_report(RESULTS)  # not strictly below docs/paper/results
    with pytest.raises(gr.ReportRefused, match="--out"):
        gr.build_report(E4B / "inside")  # inside a source campaign


# -------------------------------------------------------------------------------------------------- determinism
def test_two_runs_give_byte_identical_outputs_including_figures(report, tmp_path):
    gr.build_report(tmp_path / "second")
    first, second = _outputs(report), _outputs(tmp_path / "second")
    assert first.keys() == second.keys()
    for name in first:
        assert first[name] == second[name], name


# ----------------------------------------------------------------------------------------------------- figures
def _png_tags(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, tags = 8, []
    while pos < len(data):
        n, tag = struct.unpack(">I4s", data[pos:pos + 8])
        tags.append(tag)
        pos += 12 + n
    return tags


def _expected_drawn(rows, fleet_set, ride, kind=None):
    """Distinct (students, gD, option) of the rows with a gD, plus the dK >= 1 count, from the CSV only."""
    mine = [r for r in rows if r["fleet"] in fleet_set and r["R"] == str(ride) and (kind is None or r["option"] == kind)]
    keys = {(int(r["students"]), round(float(r["gD"]), 6), r["option"]) for r in mine if r["gD"] != ""}
    return keys, sum(r["dK"] != "" and int(r["dK"]) >= 1 for r in mine)


def _all_text(figure) -> str:
    return " ".join(t.get_text() for t in figure.findobj(matplotlib.text.Text))


def test_figures_are_valid_svg_and_png_without_dates_or_software_metadata(report):
    for stem in ("figure_gap_single", "figure_gap_typed"):
        svg = (report / f"{stem}.svg").read_text(encoding="utf-8")
        assert ET.fromstring(svg).tag.endswith("svg")
        assert not re.search(r"<dc:date|Created|Matplotlib v|\d{4}-\d{2}-\d{2}T", svg), stem
        png = (report / f"{stem}.png").read_bytes()
        assert b"tEXt" not in set(_png_tags(png)) and b"Software" not in png, stem


def test_panels_draw_distinct_gd_points_only_and_state_the_excluded_counts(report):
    rows = _csv(report / "wave_gaps.csv")
    figs = gr.figure_objects(rows)
    single, typed = figs["single"], figs["typed"]
    assert len(single.axes) == 4 and len(typed.axes) == 8
    for ax, ride in zip(single.axes, gr.RIDES):
        keys, n_pos = _expected_drawn(rows, {"single_4sw5so"}, ride)
        assert n_pos > 0 and sum(len(c.get_offsets()) for c in ax.collections) == len(keys)
        assert f"dK \u2265 1: {n_pos} waves (gD undefined, not drawn)" in [t.get_text() for t in ax.texts]
    i = 0
    for fleet in gr.TYPED_FLEETS:
        for ride in gr.RIDES:
            ax = typed.axes[i]
            i += 1
            keys, _ = _expected_drawn(rows, {fleet}, ride)
            assert sum(len(c.get_offsets()) for c in ax.collections) == len(keys)
            nb, nq = (_expected_drawn(rows, {fleet}, ride, k)[1] for k in ("base", "q"))
            assert f"dK \u2265 1: {nb} base waves, {nq} q options (gD undefined, not drawn)" in [t.get_text() for t in ax.texts]


def test_y_axis_is_scaled_on_the_drawn_gd_values_only(report):
    rows = _csv(report / "wave_gaps.csv")
    figs = gr.figure_objects(rows)
    for name, fleets in (("single", {"single_4sw5so"}), ("typed", set(gr.TYPED_FLEETS))):
        top = max(float(r["gD"]) for r in rows if r["fleet"] in fleets and r["gD"] != "")
        free_top = max(float(r["gD_free"]) for r in rows if r["fleet"] in fleets and r["gD_free"] != "")
        assert free_top > 1.05 * top  # plotting the gD_free of dK >= 1 rows would stretch the axis beyond the gD values
        for ax in figs[name].axes:
            assert top <= ax.get_ylim()[1] <= 1.2 * top and ax.get_ylim()[1] < free_top, name
            assert all(y <= top + 1e-9 for c in ax.collections for y in c.get_offsets()[:, 1])


def test_figure_text_uses_the_notation_and_has_no_count_labels_or_stale_notes(report):
    rows = _csv(report / "wave_gaps.csv")
    figs = gr.figure_objects(rows)
    for name, fg in figs.items():
        blob = _all_text(fg)
        assert not re.search(r"\bGD\b|\bDK\b|GD_FREE", blob), name
        assert not re.search(r"(^|\s)x\d+(\s|$)", blob), name  # no 'x11' labels that look like data
        assert "gD" in blob and "dK" in blob and "gD_free" not in blob
    single = _all_text(figs["single"])
    assert "0.14" not in single and "offset" not in single.lower()
    typed = _all_text(figs["typed"])
    assert "base" in typed and "marker area" in typed.lower()


def test_matplotlib_is_pinned_for_paper_scripts_only_and_its_version_is_recorded(report):
    manifest = json.loads((report / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["versions"]["matplotlib"] == matplotlib.__version__
    req = (REPO / "requirements-paper.txt").read_text(encoding="utf-8")
    assert f"matplotlib=={matplotlib.__version__}" in req and "paper scripts only" in req.lower()
    for name in ("pyproject.toml", "requirements.txt", "optimizer_api/requirements.txt", "requirements-exact.txt"):
        path = REPO / name
        if path.is_file():
            assert "matplotlib" not in path.read_text(encoding="utf-8").lower(), name
    figure_src = (REPO / "scripts" / "exact_gap_figure.py").read_text(encoding="utf-8")
    assert "matplotlib" in figure_src and "def to_png" not in figure_src and "zlib" not in figure_src  # no hand-written writers
    assert "svg.hashsalt" in figure_src and '"Date": None' in figure_src


# ------------------------------------------------------------------------------------------------------ README
def test_readme_states_the_wording_rule_and_labels(report):
    text = (report / "README.md").read_text(encoding="utf-8")
    for needle in ("single snapshot week", "seed 42", "exact_reference_v1", "native", "EQ3", "never `min(GA, union)`",
                   "both_infeasible_for_L", "ga_menu_infeasible_for_L", "proven_over_union_menu", "HiGHS", "not a global day optimum",
                   "never pooled"):
        assert needle in text, needle
    for banned in (r"\bsuperior\b", r"\boutperform", r"better than"):  # "superiority" (negated) is allowed
        assert not re.search(banned, text), banned


def test_readme_highs_summary_separates_optimal_rows_from_proven_infeasible_rows(report):
    text = (report / "README.md").read_text(encoding="utf-8")
    src = [dict(r, fleet="single_4sw5so") for r in _csv(E3 / "wave_gaps.csv")] + _csv(E4A / "option_gaps.csv")
    for fleet in FLEETS:
        rs = [r for r in src if r["fleet"] == fleet]
        opt = [r for r in rs if r["status"] == "optimal"]
        inf = [r for r in rs if r["status"] == "infeasible_proven"]
        same = sum(r["highs_status"] == "optimal" and r["highs_agrees"] == "True" for r in opt)
        both = sum(r["highs_status"] == "infeasible_proven" and r["highs_agrees"] == "True" for r in inf)
        free = sum(r["highs_free_agrees"] == "True" for r in opt)
        line = (f"{fleet}: {same} of {len(opt)} optimal rows have the same (K, D) in HiGHS and Gurobi; {both} of {len(inf)} "
                f"proven-infeasible rows are proven infeasible by both; the free-stage optimum is equal in {free} of {len(opt)} optimal rows")
        assert line in text, line
    assert "re-solves equal the Gurobi (K, D)" not in text


def test_readme_label_meanings_follow_decision_log_e07(report):
    text = (report / "README.md").read_text(encoding="utf-8")
    assert "### E07" in (REPO / "docs" / "DECISION_LOG.md").read_text(encoding="utf-8") and "DECISION_LOG E07" in text
    for needle in ("`union_not_proven` also covers a time-limited GA-menu run with an optimal union run",
                   "`verification_failed` also covers the impossible state",
                   "`both_infeasible_for_L` and `ga_menu_infeasible_for_L` also cover `infeasible_data`",
                   "no \"never above the GA-menu result\" claim and no GA-vs-union difference"):
        assert needle in text, needle


def test_readme_notes_base_rows_repeat_and_unhashed_inputs(report):
    text = (report / "README.md").read_text(encoding="utf-8")
    assert "not independent results" in text and "228" in text and "same GA base routes" in text
    assert "not hashed by their own manifests" in text and "WP-E6 pins them" in text
