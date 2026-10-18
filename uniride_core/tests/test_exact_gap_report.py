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
            "highs_rows": sum(r["highs_status"] != "" for r in rs), "highs_agrees": sum(r["highs_agrees"] == "True" for r in rs)}
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
                    "gD_not_comparable", "highs_rows", "highs_agrees"):
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
    from academic_benchmark.exact_reference import protocol

    assert protocol.private_data_errors(manifest) == []


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
def _png_info(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, {}
    while pos < len(data):
        n, tag = struct.unpack(">I4s", data[pos:pos + 8])
        chunks.setdefault(tag, data[pos + 8:pos + 8 + n])
        assert struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0] == zlib.crc32(tag + data[pos + 8:pos + 8 + n]) & 0xFFFFFFFF
        pos += 12 + n
    w, h = struct.unpack(">II", chunks[b"IHDR"][:8])
    return w, h, chunks


def test_figures_are_valid_svg_and_png_with_one_marker_per_distinct_point(report):
    rows = _csv(report / "wave_gaps.csv")
    for stem, fleets in (("figure_gap_single", {"single_4sw5so"}), ("figure_gap_typed", {"large+sedan", "large+doblo_cap3"})):
        svg = (report / f"{stem}.svg").read_text(encoding="utf-8")
        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"
        markers = len(root.findall(f".//{ns}circle")) + len(root.findall(f".//{ns}polygon"))
        keys = set()
        for r in rows:
            if r["fleet"] not in fleets or r["dK"] == "":
                continue
            y = r["gD_free"] if int(r["dK"]) >= 1 else r["gD"]
            keys.add((r["fleet"], r["R"], int(r["students"]), round(float(y), 6), int(r["dK"]) >= 1, r["option"]))
        legend = 2 if stem == "figure_gap_single" else 3  # legend glyphs: one per series plus the dK >= 1 triangle
        assert markers == len(keys) + legend, stem
        assert not re.search(r"\d{4}-\d{2}-\d{2}T|\bCreated\b|<dc:date", svg)
        w, h, chunks = _png_info((report / f"{stem}.png").read_bytes())
        assert (w, h) == (int(root.get("width")) * fig.PNG_SCALE, int(root.get("height")) * fig.PNG_SCALE)
        assert struct.unpack(">IIB", chunks[b"pHYs"]) == (int(round(fig.PNG_DPI / 0.0254)),) * 2 + (1,)
        raw = zlib.decompress(chunks[b"IDAT"])
        assert len(raw) == h * (1 + 3 * w) and set(raw) - {0xFF} != set()  # not blank


def test_figure_scene_draws_dk_positive_rows_at_gd_free_and_skips_rows_without_ga():
    base = dict(option="base", students="3", dK="0", gD="0.02", gD_free="0.02")
    rows = [base, dict(base, dK="1", gD="", gD_free="0.05"), dict(base, dK="", gD="", gD_free=""), dict(base, students="3")]
    pts = fig.gap_points(rows)
    assert {(p["shape"], p["y"], p["n"]) for p in pts} == {("circle", 0.02, 2), ("triangle", 0.05, 1)}


def test_png_font_covers_the_characters_the_report_uses(report):
    used = set()
    for stem in ("figure_gap_single", "figure_gap_typed"):
        for text in ET.fromstring((report / f"{stem}.svg").read_text(encoding="utf-8")).iter("{http://www.w3.org/2000/svg}text"):
            used |= set((text.text or "").upper())
    assert used - set(fig._GLYPHS) == set()


# ------------------------------------------------------------------------------------------------------ README
def test_readme_states_the_wording_rule_and_labels(report):
    text = (report / "README.md").read_text(encoding="utf-8")
    for needle in ("single snapshot week", "seed 42", "exact_reference_v1", "native", "EQ3", "never `min(GA, union)`",
                   "both_infeasible_for_L", "ga_menu_infeasible_for_L", "proven_over_union_menu", "HiGHS", "not a global day optimum",
                   "never pooled"):
        assert needle in text, needle
    for banned in ("outperform", "superior to", "better than the GA"):  # "not a superiority claim" is the negation
        assert banned not in text
