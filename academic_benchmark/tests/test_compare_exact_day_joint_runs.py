"""WP-E11 J12: rerun-versus-first-run comparison of the joint day campaign (scripts/compare_exact_day_joint_runs.py).

Synthetic run folders in tmp_path; no solver, no committed result folder is read or written.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("compare_exact_day_joint_runs",
                                               REPO / "scripts" / "compare_exact_day_joint_runs.py")
cmp_ = importlib.util.module_from_spec(_SPEC)
sys.modules["compare_exact_day_joint_runs"] = cmp_
_SPEC.loader.exec_module(cmp_)

DAY_COLUMNS = ("fleet", "date", "R", "L", "day_status", "K_or_S", "large_peak", "total_minutes", "car_minutes",
               "proof_claim_allowed", "proof_claim_reason", "crosscheck_status", "wall_seconds")
STAGE_COLUMNS = ("fleet", "date", "R", "L", "solver", "stage", "status", "stop_reason", "objective", "bound", "bound_ceil",
                 "bound_source", "wall_seconds", "work_units")
LB_COLUMNS = ("fleet", "date", "R", "L", "bound", "value")
CELLS = (("single_4sw5so", "2026-10-05", "50", ""), ("large+sedan", "2026-10-06", "70", "2"))


def make_run(folder: Path, *, day_edit=None, stage_edit=None, lb_edit=None, plan_edit=None, mps_edit=None, drop_cell=None,
             drop_stage=None, wall=1.0, commit="aaaaaaaa", extra_week="") -> Path:
    folder.mkdir(parents=True)
    cells = [c for c in CELLS if c != drop_cell]
    day, stages, lb, plans, mps = [], [], [], {}, {}
    for fleet, date, ride, limit in cells:
        key = f"{fleet}|{date}|R{ride}|L{limit or '-'}"
        d = dict(fleet=fleet, date=date, R=ride, L=limit, day_status="optimal", K_or_S="4", large_peak="", total_minutes="1500",
                 car_minutes="", proof_claim_allowed="True", proof_claim_reason="crosscheck_agree", crosscheck_status="agree",
                 wall_seconds=str(wall))
        for stage in ("1", "2"):
            for solver in ("highs", "gurobi"):
                if drop_stage == (key, solver, stage):
                    continue
                stages.append(dict(fleet=fleet, date=date, R=ride, L=limit, solver=solver, stage=stage, status="optimal",
                                   stop_reason="optimal", objective="4", bound="4.0" if stage == "1" else "1500.0",
                                   bound_ceil="4" if stage == "1" else "1500", bound_source="solver", wall_seconds=str(wall),
                                   work_units="1.5"))
                mps[f"{key}|{solver}{stage}"] = f"hash-{solver}{stage}"
        lb.append(dict(fleet=fleet, date=date, R=ride, L=limit, bound="lb0", value="3"))
        plans[key] = {"w1": [["a", "b"]]}
        if day_edit:
            day_edit(key, d)
        day.append(d)
    for r in stages:
        if stage_edit:
            stage_edit(f"{r['fleet']}|{r['date']}|R{r['R']}|L{r['L'] or '-'}", r)
    for r in lb:
        if lb_edit:
            lb_edit(f"{r['fleet']}|{r['date']}|R{r['R']}|L{r['L'] or '-'}", r)
    if plan_edit:
        plan_edit(plans)
    if mps_edit:
        mps_edit(mps)
    for name, cols, rows in (("day_joint.csv", DAY_COLUMNS, day), ("day_joint_stages.csv", STAGE_COLUMNS, stages),
                             ("lb0.csv", LB_COLUMNS, lb)):
        with (folder / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    (folder / "day_joint_plans.json").write_text(json.dumps(plans), encoding="utf-8")
    (folder / "day_joint_week.csv").write_text("fleet,R\nx,50\n" + extra_week, encoding="utf-8")
    (folder / "day_joint_manifest.json").write_text(json.dumps({"git_commit": commit * 5, "mps_sha256": mps}), encoding="utf-8")
    return folder


def run(tmp_path, first_kw=None, rerun_kw=None, out_name="out.csv"):
    first = make_run(tmp_path / "first", **(first_kw or {}))
    rerun = make_run(tmp_path / "rerun", **(rerun_kw or {"commit": "bbbbbbbb"}))
    out = tmp_path / out_name
    code = cmp_.main([str(first), str(rerun), "--out", str(out)])
    rows = list(csv.DictReader(out.open(encoding="utf-8"))) if out.exists() else []
    return code, {r["cell"]: r for r in rows}


KEY_B = "large+sedan|2026-10-06|R70|L2"
KEY_A = "single_4sw5so|2026-10-05|R50|L-"


def test_identical_runs_differ_only_in_timing(tmp_path, capsys):
    code, rows = run(tmp_path, rerun_kw=dict(wall=99.0, commit="bbbbbbbb",
                                             stage_edit=lambda k, r: r.update(work_units="9.9")))
    assert code == 0
    assert set(rows) == {KEY_A, KEY_B}
    for r in rows.values():
        assert r["day_status_equal"] == r["K_or_S_equal"] == r["minutes_equal"] == "True"
        assert r["plan_equal"] == r["lb0_rows_equal"] == r["mps_sha256_equal"] == "True"
        assert r["day_joint_columns_differing"] == "" and r["stage_fields_differing"] == ""
        assert r["mps_stages"] == "4"
    assert "identical 2, bound_only 0, other 0" in capsys.readouterr().out


def test_changed_label_is_reported(tmp_path):
    def edit(key, d):
        if key == KEY_B:
            d.update(day_status="infeasible_solver_proven", proof_claim_reason="x")
    code, rows = run(tmp_path, rerun_kw=dict(day_edit=edit))
    assert code == 1
    r = rows[KEY_B]
    assert (r["first_day_status"], r["rerun_day_status"]) == ("optimal", "infeasible_solver_proven")
    assert r["day_status_equal"] == "False"
    assert r["day_joint_columns_differing"] == ("day_status:optimal->infeasible_solver_proven;"
                                                "proof_claim_reason:crosscheck_agree->x")
    assert rows[KEY_A]["day_status_equal"] == "True" and rows[KEY_A]["day_joint_columns_differing"] == ""


def test_changed_cell_values_are_reported(tmp_path):
    def edit(key, d):
        if key == KEY_A:
            d.update(K_or_S="5", total_minutes="1600")
    code, rows = run(tmp_path, rerun_kw=dict(day_edit=edit))
    assert code == 1
    r = rows[KEY_A]
    assert (r["K_or_S_equal"], r["minutes_equal"], r["day_status_equal"]) == ("False", "False", "True")
    assert (r["first_K_or_S"], r["rerun_K_or_S"]) == ("4", "5")
    assert r["day_joint_columns_differing"] == "K_or_S:4->5;total_minutes:1500->1600"


def test_snapped_bound_difference_is_expected(tmp_path, capsys):
    def edit(key, r):
        if r["solver"] == "gurobi" and r["stage"] == "2":
            r["bound"] = "1499.99998429"
    code, rows = run(tmp_path, rerun_kw=dict(stage_edit=edit))
    assert code == 0  # bound-only differences do not make the exit code fail
    r = rows[KEY_B]
    assert r["stage_fields_differing"] == "gurobi2.bound:1500.0->1499.99998429"
    assert r["day_status_equal"] == r["plan_equal"] == r["mps_sha256_equal"] == "True"
    assert "identical 0, bound_only 2, other 0" in capsys.readouterr().out


def test_bound_difference_with_changed_bound_ceil_is_not_expected(tmp_path):
    def edit(key, r):
        if r["solver"] == "gurobi" and r["stage"] == "2" and key == KEY_B:
            r.update(bound="1499.5", bound_ceil="1500x")
    code, rows = run(tmp_path, rerun_kw=dict(stage_edit=edit))
    assert code == 1
    assert rows[KEY_B]["stage_fields_differing"] == "gurobi2.bound:1500.0->1499.5;gurobi2.bound_ceil:1500->1500x"


def test_bound_difference_with_changed_plan_is_not_expected(tmp_path, capsys):
    def stage(key, r):
        if r["solver"] == "gurobi" and r["stage"] == "1":
            r["bound"] = "3.99999"

    def plan(plans):
        plans[KEY_A] = {"w1": [["a", "c"]]}
    code, rows = run(tmp_path, rerun_kw=dict(stage_edit=stage, plan_edit=plan))
    assert code == 1
    assert rows[KEY_A]["plan_equal"] == "False" and rows[KEY_B]["plan_equal"] == "True"
    assert "identical 0, bound_only 1, other 1" in capsys.readouterr().out


def test_changed_lb0_row_and_mps_hash_are_reported(tmp_path):
    def lb(key, r):
        if key == KEY_A:
            r["value"] = "4"

    def mps(m):
        m[f"{KEY_B}|highs1"] = "other-hash"
    code, rows = run(tmp_path, rerun_kw=dict(lb_edit=lb, mps_edit=mps))
    assert code == 1
    assert rows[KEY_A]["lb0_rows_equal"] == "False" and rows[KEY_A]["mps_sha256_equal"] == "True"
    assert rows[KEY_B]["mps_sha256_equal"] == "False" and rows[KEY_B]["lb0_rows_equal"] == "True"


def test_missing_stage_row_is_reported(tmp_path):
    code, rows = run(tmp_path, rerun_kw=dict(drop_stage=(KEY_B, "gurobi", "2")))
    assert code == 1
    assert rows[KEY_B]["stage_fields_differing"] == "gurobi2:missing_rerun"
    code, rows = run(tmp_path / "again", first_kw=dict(drop_stage=(KEY_B, "highs", "1")))
    assert rows[KEY_B]["stage_fields_differing"] == "highs1:missing_first"


def test_missing_cell_is_refused_and_writes_nothing(tmp_path, capsys):
    code, rows = run(tmp_path, rerun_kw=dict(drop_cell=CELLS[1]))
    assert code == 2 and rows == {}
    assert not (tmp_path / "out.csv").exists()
    err = capsys.readouterr().err
    assert "cell sets differ" in err and KEY_B in err


def test_missing_run_file_is_refused(tmp_path, capsys):
    first = make_run(tmp_path / "first")
    rerun = make_run(tmp_path / "rerun")
    (rerun / "lb0.csv").unlink()
    assert cmp_.main([str(first), str(rerun), "--out", str(tmp_path / "o.csv")]) == 2
    assert "lb0.csv" in capsys.readouterr().err


def test_out_inside_results_folder_is_refused(tmp_path):
    first, rerun = make_run(tmp_path / "first"), make_run(tmp_path / "rerun")
    target = REPO / "docs" / "paper" / "results" / "week-2026-10-05-exact" / "wp-e11-joint-day" / "never_written.csv"
    assert cmp_.main([str(first), str(rerun), "--out", str(target)]) == 2
    assert not target.exists()


def test_existing_out_is_not_overwritten(tmp_path):
    first, rerun = make_run(tmp_path / "first"), make_run(tmp_path / "rerun")
    out = tmp_path / "o.csv"
    out.write_text("keep", encoding="utf-8")
    assert cmp_.main([str(first), str(rerun), "--out", str(out)]) == 2
    assert out.read_text(encoding="utf-8") == "keep"


def test_output_columns_and_line_endings(tmp_path):
    run(tmp_path)
    raw = (tmp_path / "out.csv").read_bytes()
    assert b"\r" not in raw
    assert raw.decode("utf-8").splitlines()[0] == ",".join(cmp_.OUT_FIELDS)
    assert len(raw.decode("utf-8").splitlines()) == 3


def test_whole_file_identity_and_manifest_are_summarised(tmp_path, capsys):
    run(tmp_path, rerun_kw=dict(commit="bbbbbbbb", extra_week="y,60\n"))
    out = capsys.readouterr().out
    assert "day_joint_plans.json byte-identical: True" in out
    assert "day_joint_week.csv byte-identical: False" in out
    assert "lb0.csv byte-identical: True" in out
    assert "manifest git_commit aaaaaaaa -> bbbbbbbb" in out
