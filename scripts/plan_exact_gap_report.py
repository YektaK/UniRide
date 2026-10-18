#!/usr/bin/env python3
"""WP-E6: the gap report of the exact-solver study (tables, a figure, README and manifest).

Design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 1.2 (gaps, day aggregation), section 4 (protocol separation),
section 9 ("Paper deliverable (WP-E6)"). OFFLINE and archive-only: it reads ONLY the committed result directories

* ``wp-e3-goal1-single``   single type 4 Sw / 5 So (``wave_gaps.csv``, manifest, ``exact_routes.json``);
* ``wp-e4a-typed-options`` typed fleets (``option_gaps.csv``, ``replay.csv``, manifest, ``exact_routes.json``);
* ``wp-e4b-union-day``     union-menu day level (``day_gaps.csv``, ``day_sums.csv``, ``union_day_manifest.json``);

and the GA source manifests those manifests name (the 4sw5so archive and the two WP-E10 re-runs). It never solves anything:
no AMPL, no solver, no DB, no HTTP. Standard library only (see ``exact_gap_figure.py`` for the figures).

Every input file is read once through one registry that records its sha256. The report REFUSES (``ReportRefused``) inputs
whose sha256 differs from what the source manifests record (``exact_routes.json``, the GA ``run_manifest.json`` files, the
WP-E4a files named by the union manifest), a manifest that is not valid under its protocol schema, blocking errors, a dirty
source run, GA labels that differ between the source manifest and a source row, day sums that differ from a recomputation
from the option rows, and an unsafe output directory.

Rows of ``exact_reference_v1`` (wave and option level) and of ``union_day_v1`` (day level) stay in their own files and are
never pooled with each other or with heuristic rows; there is no all-fleet row and no ``min(GA, union)`` column.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
import subprocess
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO / "scripts"), str(REPO / "optimizer_api"), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from academic_benchmark.exact_reference import protocol  # noqa: E402
import exact_gap_figure as figure  # noqa: E402  (same directory)

RESULTS_REL = "docs/paper/results"
EXACT_REL = f"{RESULTS_REL}/week-2026-10-05-exact"
E3_DIR, E4A_DIR, E4B_DIR = (REPO / EXACT_REL / n for n in ("wp-e3-goal1-single", "wp-e4a-typed-options", "wp-e4b-union-day"))
DEFAULT_OUT = REPO / EXACT_REL / "wp-e6-gap-report"
WORK_PACKAGE = "WP-E6"
SINGLE_FLEET = "single_4sw5so"
TYPED_FLEETS = ("large+sedan", "large+doblo_cap3")
FLEETS = (SINGLE_FLEET,) + TYPED_FLEETS
RIDES = (50, 60, 70, 90)
UNION_LABELS = ("proven_over_union_menu", "ga_menu_infeasible_for_L", "both_infeasible_for_L", "union_not_proven",
                "not_independently_confirmed", "verification_failed")

WAVE_FIELDS = (
    "protocol", "fleet", "date", "R", "option", "option_id", "quota", "k_kind", "wave_id", "direction", "anchor", "students",
    "peak", "model", "columns", "enumeration_labels", "ga_option_status", "comparison",
    "K_GA", "K_LB", "K_LB_source", "K_star", "D_GA", "D_LB", "D_star", "D_LB_free", "dK", "gD", "gD_note", "gD_free",
    "status", "note",
    "stage1_status", "stage1_stop_reason", "stage1_timing_dependent",
    "stage2_status", "stage2_stop_reason", "stage2_timing_dependent", "stage2_non_lexicographic",
    "free_status", "free_stop_reason", "free_timing_dependent",
    "solver", "solver_version", "enumeration_seconds", "solve_seconds",
    "exact_certified", "ga_recertified", "ga_cert_archived", "ga_cert_agree", "objective_check", "exact_le_ga",
    "highs_status", "highs_K", "highs_D", "highs_agrees", "highs_free_status", "highs_D_LB_free", "highs_free_agrees",
    "highs_seconds", "ga_protocol", "ga_seed", "ga_commit", "ga_dirty_tree", "source_result")

# wave_gaps.csv column -> source column (the E4a/E3 names), where they differ
_RENAMED = {"enumeration_labels": "labels"}
GA_LABEL_COLUMNS = ("ga_protocol", "ga_seed", "ga_commit", "ga_dirty_tree")

DAY_SUMS_FIELDS = (
    "fleet", "date", "R",
    "base_waves_compared", "dK_day_base", "gD_day_base", "gD_excluded_waves_base", "base_options_not_compared",
    "q_options_compared", "dK_sum_over_q_options", "gD_over_q_options", "gD_excluded_q_options", "q_options_not_compared")

TABLE_FIELDS = (
    "fleet", "R", "option_kind", "rows", "exact_feasible", "exact_infeasible_proven", "compared", "both_infeasible",
    "ga_infeasible_exact_feasible", "dK_zero", "dK_zero_share", "dK_positive", "dK_max", "gD_comparable", "gD_positive",
    "gD_mean", "gD_max", "gD_not_comparable", "status_counts", "highs_rows", "highs_agrees")

DAY_LABEL_FIELDS = ("fleet", "L", "cells") + UNION_LABELS + (
    "union_cars_below_ga", "union_cars_equal_ga", "union_cars_above_ga")

OUTPUT_FILES = ("wave_gaps.csv", "day_gaps.csv", "day_sums.csv", "table_by_R.csv", "table_by_R.md", "table_day_labels.csv",
                "figure_gap_single.svg", "figure_gap_single.png", "figure_gap_typed.svg", "figure_gap_typed.png", "README.md")
OUTPUT_PROTOCOLS = {
    "wave_gaps.csv": protocol.PROTOCOL_ID, "table_by_R.csv": protocol.PROTOCOL_ID, "table_by_R.md": protocol.PROTOCOL_ID,
    "figure_gap_single.svg": protocol.PROTOCOL_ID, "figure_gap_single.png": protocol.PROTOCOL_ID,
    "figure_gap_typed.svg": protocol.PROTOCOL_ID, "figure_gap_typed.png": protocol.PROTOCOL_ID,
    "day_gaps.csv": protocol.UNION_DAY_PROTOCOL_ID, "table_day_labels.csv": protocol.UNION_DAY_PROTOCOL_ID,
    "day_sums.csv": "exact_reference_v1 (per-wave sums, fleets separate); day level over the union menu is union_day_v1 (day_gaps.csv)",
    "README.md": "descriptive",
}


class ReportRefused(Exception):
    """An input or the output location is not acceptable; nothing is written."""


# ---------------------------------------------------------------------------------------------------- reading
class Inputs:
    """Reads every input file once and records its sha256 (repo-relative key)."""

    def __init__(self, repo: Path):
        self.repo = Path(repo).resolve()
        self.shas: dict = {}
        self._cache: dict = {}

    def rel(self, path: Path) -> str:
        try:
            return Path(path).resolve().relative_to(self.repo).as_posix()
        except ValueError:
            return Path(path).name

    def read(self, path: Path) -> bytes:
        key = self.rel(path)
        if key not in self._cache:
            try:
                data = Path(path).read_bytes()
            except OSError as exc:
                raise ReportRefused(f"cannot read input {key}: {exc}") from exc
            self._cache[key] = data
            self.shas[key] = hashlib.sha256(data).hexdigest()
        return self._cache[key]

    def sha(self, path: Path) -> str:
        self.read(path)
        return self.shas[self.rel(path)]

    def json(self, path: Path) -> dict:
        try:
            return json.loads(self.read(path).decode("utf-8"))
        except ValueError as exc:
            raise ReportRefused(f"{self.rel(path)} is not valid JSON: {exc}") from exc

    def csv(self, path: Path) -> tuple:
        reader = csv.DictReader(io.StringIO(self.read(path).decode("utf-8"), newline=""))
        rows = list(reader)
        return tuple(reader.fieldnames or ()), rows


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ReportRefused(message)


def ga_labels_of(manifest: dict) -> dict:
    """The GA labels of a GA source manifest (the 4sw5so archive or a WP-E10 re-run)."""
    return {"ga_protocol": str(manifest["termination_protocol"]), "ga_seed": str(manifest["effective_seed"]),
            "ga_commit": str(manifest["git_commit"])[:7], "ga_dirty_tree": str(bool(manifest["dirty_working_tree"]))}


def _load_ga(inputs: Inputs, src: dict, label: str) -> dict:
    """The GA source manifest named by an exact/union manifest, checked against the recorded sha256."""
    path = inputs.repo / src["path"] / "run_manifest.json"
    _need(inputs.sha(path) == src.get("manifest_sha256"),
          f"{label}: GA run_manifest.json sha256 differs from the recorded manifest_sha256 ({inputs.rel(path)})")
    return inputs.json(path)


def _check_exact_manifest(inputs: Inputs, directory: Path, work_package: str, routes_name: str = "exact_routes.json") -> dict:
    manifest = inputs.json(directory / protocol.MANIFEST_FILENAME)
    errors = protocol.validate_manifest(manifest)
    _need(not errors, f"{work_package} exact_manifest.json is not valid under exact_reference_v1: {errors[:3]}")
    _need(manifest.get("work_package") == work_package, f"exact_manifest.json work_package is not {work_package}")
    _need(manifest.get("blocking_errors") == [], f"{work_package} manifest records blocking errors")
    _need(manifest.get("dirty_working_tree") is False, f"{work_package} run was made on a dirty tree")
    recorded = (manifest.get("exact_routes") or {}).get("sha256")
    _need(inputs.sha(directory / routes_name) == recorded,
          f"{work_package} exact_routes.json sha256 differs from the manifest ({recorded})")
    return manifest


def _check_row_labels(rows: list, labels: dict, where: str) -> None:
    for i, row in enumerate(rows):
        for col in GA_LABEL_COLUMNS:
            _need(row.get(col) == labels[col], f"{where} row {i + 2}: {col} {row.get(col)!r} differs from the source manifest {labels[col]!r}")


def _blank(value) -> str:
    return "" if value is None else str(value)


def _float(text: str):
    return None if text == "" else float(text)


def wave_rows(e3_rows: list, e4a_rows: list, labels: dict) -> list:
    """Merge the single-type rows (WP-E3) and the typed option rows (WP-E4a) into the wave_gaps.csv rows."""
    out = []
    for r in e3_rows:
        out.append(_row(r, fleet=SINGLE_FLEET, option="base", option_id="base", quota="", k_kind="K",
                        comparison="compared" if r["K_GA"] != "" and r["K_star"] != "" else "", source="wp-e3-goal1-single",
                        labels=labels[SINGLE_FLEET]))
    for r in e4a_rows:
        out.append(_row(r, fleet=r["fleet"], option=r["kind"], option_id=r["option"], quota=r["quota"], k_kind=r["k_kind"],
                        comparison=r["comparison"], source="wp-e4a-typed-options", labels=labels[r["fleet"]]))
    return out


def _row(src: dict, *, fleet, option, option_id, quota, k_kind, comparison, source, labels) -> dict:
    row = {"protocol": protocol.PROTOCOL_ID, "fleet": fleet, "option": option, "option_id": option_id, "quota": quota,
           "k_kind": k_kind, "comparison": comparison, "source_result": source}
    for col in WAVE_FIELDS:
        if col in row or col in GA_LABEL_COLUMNS:
            continue
        row[col] = src.get(_RENAMED.get(col, col), "")
    row.update(labels)
    return {col: row[col] for col in WAVE_FIELDS}


# ------------------------------------------------------------------------------------------------ aggregation
def _gd_day(rows: list) -> tuple:
    defined = [r for r in rows if r["gD"] != ""]
    d_ga, d_lb = sum(int(r["D_GA"]) for r in defined), sum(int(r["D_LB"]) for r in defined)
    return (None if d_lb == 0 else round((d_ga - d_lb) / d_lb, 6)), len(rows) - len(defined)


def day_sum_values(rows: list) -> dict:
    """Design 1.2 'Day aggregation' over the rows of one (fleet, date, R) and one option kind."""
    compared = [r for r in rows if r["comparison"] == "compared"]
    gd_day, excluded = _gd_day(compared)
    return {"compared": len(compared), "dK_day": sum(int(r["dK"]) for r in compared), "gD_day": gd_day, "gD_excluded": excluded,
            "not_compared": len(rows) - len(compared)}


def single_day_sums(rows: list) -> list:
    groups: dict = {}
    for r in rows:
        if r["fleet"] == SINGLE_FLEET:
            groups.setdefault((r["date"], int(r["R"])), []).append(r)
    out = []
    for (date, ride), rs in sorted(groups.items()):
        v = day_sum_values(rs)
        row = {c: "" for c in DAY_SUMS_FIELDS}
        row.update(fleet=SINGLE_FLEET, date=date, R=ride, base_waves_compared=v["compared"], dK_day_base=v["dK_day"],
                   gD_day_base=_blank(v["gD_day"]), gD_excluded_waves_base=v["gD_excluded"], base_options_not_compared=v["not_compared"])
        out.append(row)
    return out


def check_e4b_day_sums(typed_rows: list, day_sums: list) -> None:
    """The WP-E4b day sums must equal a recomputation from the WP-E4a option rows."""
    groups: dict = {}
    for r in typed_rows:
        groups.setdefault((r["fleet"], r["date"], int(r["R"])), {"base": [], "q": []})[r["option"]].append(r)
    _need({(r["fleet"], r["date"], int(r["R"])) for r in day_sums} == set(groups), "day_sums.csv rows differ from the (fleet, date, R) set of the option rows")
    for r in day_sums:
        g = groups[(r["fleet"], r["date"], int(r["R"]))]
        for kind, cols in (("base", ("base_waves_compared", "dK_day_base", "gD_day_base", "gD_excluded_waves_base", "base_options_not_compared")),
                           ("q", ("q_options_compared", "dK_sum_over_q_options", "gD_over_q_options", "gD_excluded_q_options", "q_options_not_compared"))):
            v = day_sum_values(g[kind])
            want = (v["compared"], v["dK_day"], v["gD_day"], v["gD_excluded"], v["not_compared"])
            have = (int(r[cols[0]]), int(r[cols[1]]), _float(r[cols[2]]), int(r[cols[3]]), int(r[cols[4]]))
            same = have[:2] == want[:2] and have[3:] == want[3:] and (
                (have[2] is None and want[2] is None) or (have[2] is not None and want[2] is not None and abs(have[2] - want[2]) < 1e-9))
            _need(same, f"day_sums.csv {r['fleet']} {r['date']} R{r['R']} {kind}: {have} differs from the recomputation {want}")


def table_rows(rows: list) -> list:
    groups: dict = {}
    for r in rows:
        groups.setdefault((FLEETS.index(r["fleet"]), int(r["R"]), r["option"]), []).append(r)
    out = []
    for (fleet_i, ride, kind), rs in sorted(groups.items()):
        compared = [r for r in rs if r["comparison"] == "compared"]
        comparable = [r for r in compared if r["gD_note"] == "comparable"]
        gd = [float(r["gD"]) for r in comparable]
        statuses: dict = {}
        for r in rs:
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        dk_zero = sum(r["dK"] == "0" for r in compared)
        out.append({
            "fleet": FLEETS[fleet_i], "R": ride, "option_kind": kind, "rows": len(rs),
            "exact_feasible": sum(r["status"] in ("optimal", "feasible_with_gap") for r in rs),
            "exact_infeasible_proven": sum(r["status"] == "infeasible_proven" for r in rs), "compared": len(compared),
            "both_infeasible": sum(r["comparison"] == "both_infeasible" for r in rs),
            "ga_infeasible_exact_feasible": sum(r["comparison"] == "ga_infeasible_exact_feasible" for r in rs),
            "dK_zero": dk_zero, "dK_zero_share": f"{dk_zero / len(compared):.6f}" if compared else "",
            "dK_positive": sum(int(r["dK"]) > 0 for r in compared),
            "dK_max": max((int(r["dK"]) for r in compared), default=""),
            "gD_comparable": len(comparable), "gD_positive": sum(v > 0 for v in gd),
            "gD_mean": f"{sum(gd) / len(gd):.6f}" if gd else "", "gD_max": f"{max(gd):.6f}" if gd else "",
            "gD_not_comparable": sum(r["gD_note"] == "not_comparable_K_GA_gt_Kstar" for r in compared),
            "status_counts": ";".join(f"{k}={statuses[k]}" for k in sorted(statuses)),
            "highs_rows": sum(r["highs_status"] != "" for r in rs), "highs_agrees": sum(r["highs_agrees"] == "True" for r in rs)})
    return out


def day_label_rows(day_rows: list) -> list:
    groups: dict = {}
    for r in day_rows:
        groups.setdefault((TYPED_FLEETS.index(r["fleet"]), int(r["L"])), []).append(r)
    out = []
    for (fleet_i, limit), rs in sorted(groups.items()):
        row = {"fleet": TYPED_FLEETS[fleet_i], "L": limit, "cells": len(rs)}
        row.update({label: sum(r["label"] == label for r in rs) for label in UNION_LABELS})
        diffs = [int(r["cars_difference_union_minus_ga"]) for r in rs if r["label"] == "proven_over_union_menu"]
        row.update(union_cars_below_ga=sum(d < 0 for d in diffs), union_cars_equal_ga=sum(d == 0 for d in diffs),
                   union_cars_above_ga=sum(d > 0 for d in diffs))
        out.append(row)
    return out


def markdown_tables(table: list, labels: list) -> str:
    def md(fields, rows):
        lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
        lines += ["| " + " | ".join(str(r[f]) for f in fields) + " |" for r in rows]
        return "\n".join(lines)

    return "\n".join([
        "# Gap table per fleet, R and option kind",
        "",
        "Rows are waves (`base`; the single type has only `base`) or options (`q`: the typed options `xq0..xqQ`, one per wave and "
        "quota). Fleets are never pooled and exact rows (`exact_reference_v1`) are never mixed into heuristic statistics.",
        "",
        "Denominators: `rows` = every source row of the group; `compared` = rows with a feasible exact result and a feasible GA "
        "result of the same kind; `dK_zero_share` = `dK_zero / compared`; `gD_comparable` = compared rows with `K_GA = K*` "
        "(the only rows `gD_mean` and `gD_max` use; a `K_GA > K*` row has no `gD`); `exact_infeasible_proven`, `both_infeasible` "
        "and `ga_infeasible_exact_feasible` rows are outside `compared`. `highs_rows` = rows re-solved with HiGHS, "
        "`highs_agrees` = those whose (K, D) equal Gurobi's.",
        "",
        md(TABLE_FIELDS, table),
        "",
        "# Day level over the union menu (`union_day_v1`), per fleet and L",
        "",
        "One row per (fleet, L); cells are (date, R) pairs (20 per row). The cars columns count `proven_over_union_menu` cells by the "
        "sign of union cars minus GA-menu cars. Not a global day optimum (EQ3).",
        "",
        md(DAY_LABEL_FIELDS, labels),
        ""])


# ------------------------------------------------------------------------------------------------------ output
def csv_bytes(fields, rows) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(fields), lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def json_bytes(doc) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")


def check_out_dir(out: Path, protected: list, repo: Path) -> None:
    out_r, repo_r = Path(out).resolve(), Path(repo).resolve()
    try:
        rel = out_r.relative_to(repo_r)
    except ValueError:
        return  # outside the repository: excludes nothing from the dirty check
    results = repo_r / RESULTS_REL
    _need(out_r != results and results in out_r.parents,
          f"--out must lie strictly below {RESULTS_REL}/ when inside the repository (got {rel.as_posix() or '.'})")
    for src in protected:
        src_r = Path(src).resolve()
        _need(not (out_r == src_r or out_r in src_r.parents or src_r in out_r.parents),
              f"--out must not contain or lie inside a source result directory ({src_r.name})")


def _git(repo: Path, *args) -> str:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReportRefused(f"git {' '.join(args[:2])} failed: {exc}") from exc
    return done.stdout.strip()


def git_state(out: Path, git_repo: Path) -> tuple:
    spec = ["status", "--porcelain"]
    try:
        spec += ["--", ".", f":(exclude){Path(out).resolve().relative_to(Path(git_repo).resolve()).as_posix()}"]
    except ValueError:
        pass
    return _git(git_repo, "rev-parse", "HEAD"), bool(_git(git_repo, *spec))


def python_provenance(git_repo: Path) -> dict:
    import academic_benchmark
    import uniride_core

    out = {}
    for name, mod in (("uniride_core", uniride_core), ("academic_benchmark", academic_benchmark)):
        try:
            out[name] = Path(mod.__file__).resolve().relative_to(Path(git_repo).resolve()).as_posix()
        except ValueError as exc:
            raise ReportRefused(f"{name} is imported from outside this checkout; set PYTHONPATH to the repo root") from exc
    return out


# ------------------------------------------------------------------------------------------------------ figures
def figures(rows: list) -> dict:
    single = [r for r in rows if r["fleet"] == SINGLE_FLEET]
    scene1 = figure.build_gap_figure(
        [[r for r in single if int(r["R"]) == ride] for ride in RIDES], [f"R = {ride} min" for ride in RIDES], 2,
        "Gap of the GA wave routes to the exact reference, single type 4 Sw / 5 So (WP-E3)",
        "Snapshot week 2026-10-05, 57 waves per R; GA = one seed-42 native run; exact_reference_v1; descriptive gap", ("base",),
        "Per-wave duration gap gD against students per wave, one panel per R, marker by dK (single type).")
    panels, titles = [], []
    for fleet in TYPED_FLEETS:
        for ride in RIDES:
            panels.append([r for r in rows if r["fleet"] == fleet and int(r["R"]) == ride])
            titles.append(f"{fleet}, R = {ride}")
    scene2 = figure.build_gap_figure(
        panels, titles, 4, "Gap of the GA menu options to the exact options, typed fleets (WP-E4a)",
        "Snapshot week 2026-10-05; GA = one seed-42 native run (WP-E10 re-run); exact_reference_v1; fleets in separate panels",
        ("base", "q"), "Per-option duration gap gD against students per wave, one panel per fleet and R, marker by dK, colour by option kind.")
    return {"figure_gap_single.svg": scene1.to_svg().encode("utf-8"), "figure_gap_single.png": scene1.to_png(),
            "figure_gap_typed.svg": scene2.to_svg().encode("utf-8"), "figure_gap_typed.png": scene2.to_png()}


# ------------------------------------------------------------------------------------------------------ README
def readme_text(ctx: dict) -> str:
    t, d = ctx["table"], ctx["day"]
    by = {(r["fleet"], int(r["R"]), r["option_kind"]): r for r in t}

    def line(fleet, kind):
        parts = []
        for ride in RIDES:
            r = by[(fleet, ride, kind)]
            parts.append(f"R = {ride}: dK = 0 in {r['dK_zero']} of {r['compared']} compared; gD defined in {r['gD_comparable']}, "
                         f"positive in {r['gD_positive']}, mean {r['gD_mean']}, max {r['gD_max']}")
        return "; ".join(parts)

    highs = {f: (sum(int(r["highs_rows"]) for r in t if r["fleet"] == f), sum(int(r["highs_agrees"]) for r in t if r["fleet"] == f)) for f in FLEETS}
    labels = ctx["day_label_counts"]
    lines = [
        "# WP-E6 gap report: the exact references against the GA, week of 2026-10-05",
        "",
        "Generated by `scripts/plan_exact_gap_report.py` from committed results only (no solver, no AMPL, no DB). `manifest.json` lists "
        "every input file with its sha256, the git commit and dirty flag, the Python and library versions and every output with its "
        "sha256. Facts and numbers only; the paper text is written separately.",
        "",
        "## Wording rule",
        "",
        "- A single snapshot week (service dates 2026-10-05 to 2026-10-09).",
        "- A descriptive gap measurement, not a superiority claim.",
        f"- The GA side is one run at seed 42 under the native termination protocol (secondary protocol); the gap is the gap of that "
        f"run, not of the GA in general. GA labels per row come from the GA source manifests: {ctx['ga_label_text']}.",
        "- Exact rows (waves and options) carry their own protocol `exact_reference_v1` and are never pooled with heuristic rows, with "
        "fixed-budget rows or with each other across fleets.",
        "- The day level over the union menu (`union_day_v1`) is the minimum number of cars over the union of the GA and the per-wave "
        "exact menus; it is not a global day optimum (EQ3). The day-level value is never `min(GA, union)`: the report shows no such value.",
        "- HiGHS cross-check (EQ4): "
        + "; ".join(f"{f}: {highs[f][1]} of {highs[f][0]} HiGHS re-solves equal the Gurobi (K, D)" for f in FLEETS) + ".",
        "",
        "## Files",
        "",
        "| file | content |",
        "|---|---|",
        f"| `wave_gaps.csv` | {len(ctx['wave_rows'])} rows, protocol `exact_reference_v1`: single type 4 Sw / 5 So (WP-E3, {ctx['n_single']} rows, "
        f"`option` `base`) and the typed fleets (WP-E4a, {ctx['n_typed']} rows: `base` = `xbase` against the GA `base`, `q` = the typed "
        "option `xq<quota>` against the GA `q<quota>`) |",
        f"| `day_gaps.csv` | the {len(ctx['day_rows'])} WP-E4b rows (`union_day_v1`) copied unchanged: per (fleet, date, R, L) cars over the GA menus "
        "and over the union menu with the label and both CP-SAT statuses |",
        f"| `day_sums.csv` | per (fleet, date, R) the day aggregation of design 1.2: the {len(ctx['typed_sum_rows'])} WP-E4b rows unchanged "
        f"(typed fleets) and {len(ctx['single_sum_rows'])} rows recomputed from WP-E3 for the single type (`dK_day_base` is `dK_day`, "
        "`gD_day_base` is `gD_day`, `gD_excluded_waves_base` the excluded waves; the `q_*` columns are empty for the single type) |",
        "| `table_by_R.csv`, `table_by_R.md` | per fleet x R x option kind: counts, shares and gap statistics (denominators below) |",
        "| `table_day_labels.csv` | per fleet x L: counts of the day-level labels |",
        "| `figure_gap_single.svg/.png` | per-wave gD against students per wave, one panel per R, single type |",
        "| `figure_gap_typed.svg/.png` | per-option gD against students per wave, panels per fleet and R, typed fleets |",
        "| `manifest.json` | inputs with sha256, outputs with sha256, commit, dirty flag, versions, `python_provenance` |",
        "",
        "## Columns of `wave_gaps.csv`",
        "",
        "`protocol` (always `exact_reference_v1`), `fleet` (`single_4sw5so`, `large+sedan`, `large+doblo_cap3`), `date`, `R`, `option` "
        "(`base` or `q`), `option_id` (`base`, `q0`..`q3`), `quota` (empty for `base` and for the single type), `k_kind` (`K` or `K_m`: "
        "the route count of the whole wave or of the minimised type), wave columns (`wave_id`, `direction`, `anchor`, `students`, `peak`), "
        "`model` (SP), `columns`, `enumeration_labels` (the column and label counts of the enumeration), `ga_option_status`, `comparison` "
        "(`compared`, `both_infeasible`, `ga_infeasible_exact_feasible`; for the single type `compared` when K_GA and K* exist), "
        "`K_GA`, `K_LB` (+ `K_LB_source`), `K_star`, `D_GA`, `D_LB`, `D_star`, `D_LB_free`, `dK` = `K_GA - K_LB`, `gD` = (D_GA - D_LB) / "
        "D_LB when `K_GA = K*` (else empty, `gD_note` `not_comparable_K_GA_gt_Kstar`), `gD_free` = (D_GA - D_LB_free) / D_LB_free, "
        "`status` and per stage (`stage1`, `stage2`, `free`) `*_status`, `*_stop_reason`, `*_timing_dependent`, plus "
        "`stage2_non_lexicographic` (the design defines it for stage 2 only), `solver`, `solver_version`, `enumeration_seconds`, "
        "`solve_seconds`, certificate and cross-check columns (`exact_certified`, `ga_recertified`, `ga_cert_archived`, `ga_cert_agree`, "
        "`objective_check`, `exact_le_ga`), the HiGHS columns, the GA labels `ga_protocol`, `ga_seed`, `ga_commit`, `ga_dirty_tree` and "
        "`source_result`. Values are copied from the source files as written; no value is invented.",
        "",
        "Not available from a source (left empty): " + ctx["empty_text"] + ".",
        "",
        "## Denominators of the table",
        "",
        "`rows` = every source row of (fleet, R, option kind); `compared` = rows with a feasible exact result and a feasible GA result of "
        "the same kind (`comparison` = `compared`); `dK_zero_share` = `dK_zero / compared`; `gD_mean` and `gD_max` use only the "
        "`gD_comparable` rows (compared rows with `K_GA = K*`); proven-infeasible exact options (`exact_infeasible_proven`), "
        "`both_infeasible` and `ga_infeasible_exact_feasible` rows are outside `compared`. Waves (`base`) and options (`q`) are "
        "different units and are never summed together; the `q` rows weight the quotas equally.",
        "",
        "## Measured values (copied from `table_by_R.csv`)",
        "",
        f"- single type, `base`: {line(SINGLE_FLEET, 'base')}.",
        f"- large+sedan, `base`: {line('large+sedan', 'base')}.",
        f"- large+sedan, `q`: {line('large+sedan', 'q')}.",
        f"- large+doblo_cap3, `base`: {line('large+doblo_cap3', 'base')}.",
        f"- large+doblo_cap3, `q`: {line('large+doblo_cap3', 'q')}.",
        "",
        "## Day level (`union_day_v1`)",
        "",
        f"Labels over the {len(ctx['day_rows'])} cells: " + ", ".join(f"{k} {labels[k]}" for k in UNION_LABELS) + ". Meanings:",
        "",
        "- `proven_over_union_menu`: both CP-SAT runs `optimal` and the TypeScript assignment confirms: minimum cars over the union of the "
        "GA and per-wave exact menus; never above the GA-menu result (when both runs are optimal); not a global day optimum (EQ3).",
        "- `both_infeasible_for_L`: both runs proven infeasible for the limit L; nothing to compare, no claim (owner label 2026-10-18).",
        "- `ga_menu_infeasible_for_L`: the GA-menu run is proven infeasible and the union run is optimal and confirmed: union cars proven over "
        "the union menu, no GA-vs-union difference shown (owner label 2026-10-18).",
        "- `union_not_proven`: only when the union run still stopped on its time limit after the 60 s re-run (timing dependent).",
        "- `not_independently_confirmed`, `verification_failed`: the TypeScript confirmation is missing or failed.",
        "",
        f"Replay gate (WP-E4a `replay.csv`): {ctx['replay_text']}.",
        "",
        "## Figures",
        "",
        "x = students per wave (0 to 21), y = `gD` for rows with `dK = 0` (filled circle) and `gD_free` for rows with `dK >= 1` (hollow "
        "triangle: `gD` is not defined there because `K_GA > K*`). One panel per R for the single type; for the typed fleets one panel "
        "per fleet and R, colour = option kind (`base`, `q`; at the same coordinates `base` and `q` are offset by 0.14 students). One "
        "marker per distinct (students, y, kind); `xN` marks N coincident rows. Rows without a GA answer or without an exact result are "
        "not drawn. Standard-library SVG and PNG writer (no plotting dependency); no timestamps; PNG at 2x pixels, 192 dpi.",
        "",
        "## Reproduce",
        "",
        "`PYTHONPATH=<repo root> python scripts/plan_exact_gap_report.py` from a clean commit; the output directory must lie below "
        "`docs/paper/results/` and outside the source result directories. Two runs give byte-identical files.",
        ""]
    return "\n".join(lines)


def empty_columns_text(rows: list) -> str:
    parts = []
    for fleet in FLEETS:
        rs = [r for r in rows if r["fleet"] == fleet]
        empty = [c for c in WAVE_FIELDS if c not in GA_LABEL_COLUMNS and all(r[c] == "" for r in rs)]
        parts.append(f"{fleet}: {', '.join(empty) if empty else 'none'}")
    return "; ".join(parts) + " (a column empty in every row of a fleet is not recorded by its source, or does not apply there)"


# ------------------------------------------------------------------------------------------------------- build
def build_report(out: Path, *, repo: Path = REPO, e3_dir: Path = E3_DIR, e4a_dir: Path = E4A_DIR, e4b_dir: Path = E4B_DIR,
                 git_repo: Path = REPO) -> dict:
    out, repo = Path(out), Path(repo)
    check_out_dir(out, [e3_dir, e4a_dir, e4b_dir], repo)
    inputs = Inputs(repo)

    e3 = _check_exact_manifest(inputs, Path(e3_dir), "WP-E3")
    e4a = _check_exact_manifest(inputs, Path(e4a_dir), "WP-E4a")
    union = inputs.json(Path(e4b_dir) / protocol.UNION_DAY_MANIFEST_FILENAME)
    errors = protocol.validate_union_day_manifest(union)
    _need(not errors, f"WP-E4b manifest is not valid under union_day_v1: {errors[:3]}")
    _need(union.get("blocking_errors") == [] and union.get("dirty_working_tree") is False, "WP-E4b manifest records blocking errors or a dirty tree")

    # the union manifest records the WP-E4a files it used
    exact_src = union["exact_options_source"]
    for key, path in (("exact_routes_sha256", Path(e4a_dir) / "exact_routes.json"), ("option_gaps_sha256", Path(e4a_dir) / "option_gaps.csv"),
                      ("manifest_sha256", Path(e4a_dir) / protocol.MANIFEST_FILENAME)):
        _need(inputs.sha(path) == exact_src[key], f"WP-E4a {path.name} sha256 differs from the union manifest ({key[:-7]})")

    # GA labels from the GA source manifests (sha-checked against every manifest that names them)
    ga_manifests = {SINGLE_FLEET: _load_ga(inputs, e3["source_campaign"], "WP-E3")}
    for fleet in TYPED_FLEETS:
        ga_manifests[fleet] = _load_ga(inputs, e4a["source_campaigns"][fleet], f"WP-E4a {fleet}")
        _load_ga(inputs, union["source_campaigns"][fleet], f"WP-E4b {fleet}")
        _need(union["source_campaigns"][fleet]["manifest_sha256"] == e4a["source_campaigns"][fleet]["manifest_sha256"],
              f"{fleet}: the union and WP-E4a manifests name different GA manifests")
    labels = {f: ga_labels_of(m) for f, m in ga_manifests.items()}
    for fleet, block in ((SINGLE_FLEET, e3.get("ga_labels")), *((f, (e4a.get("ga_labels") or {}).get(f)) for f in TYPED_FLEETS)):
        _need(isinstance(block, dict) and all(str(block.get(c)) == labels[fleet][c] for c in GA_LABEL_COLUMNS),
              f"{fleet}: ga_labels of the exact manifest differ from the GA source manifest (ga_protocol/ga_seed/ga_commit/ga_dirty_tree)")

    e3_fields, e3_rows = inputs.csv(Path(e3_dir) / "wave_gaps.csv")
    e4a_fields, e4a_rows = inputs.csv(Path(e4a_dir) / "option_gaps.csv")
    _need({r["fleet"] for r in e3_rows} == {SINGLE_FLEET}, "WP-E3 wave_gaps.csv must hold only the single type")
    _need({r["fleet"] for r in e4a_rows} == set(TYPED_FLEETS), "WP-E4a option_gaps.csv must hold exactly the two typed fleets")
    _check_row_labels(e3_rows, labels[SINGLE_FLEET], "wave_gaps.csv (WP-E3)")
    for fleet in TYPED_FLEETS:
        _check_row_labels([r for r in e4a_rows if r["fleet"] == fleet], labels[fleet], f"option_gaps.csv (WP-E4a, {fleet})")
    day_fields, day_rows = inputs.csv(Path(e4b_dir) / "day_gaps.csv")
    for fleet in TYPED_FLEETS:
        _check_row_labels([r for r in day_rows if r["fleet"] == fleet], labels[fleet], f"day_gaps.csv ({fleet})")
    counts = {k: sum(r["label"] == k for r in day_rows) for k in UNION_LABELS}
    _need(counts == union["labels"], "day_gaps.csv label counts differ from the union manifest")
    sums_fields, sums_rows = inputs.csv(Path(e4b_dir) / "day_sums.csv")
    _need(tuple(sums_fields) == DAY_SUMS_FIELDS, "day_sums.csv columns differ from the WP-E4b schema")
    replay_fields, replay_rows = inputs.csv(Path(e4a_dir) / "replay.csv")
    _need(len(replay_rows) == 120 and all(r["request_diff_count"] == "0" and r["response_diff_count"] == "0" for r in replay_rows),
          "WP-E4a replay.csv does not show 120 reproduced cells")

    rows = wave_rows(e3_rows, e4a_rows, labels)
    protocol.assert_not_pooled(rows)
    typed = [r for r in rows if r["fleet"] in TYPED_FLEETS]
    check_e4b_day_sums(typed, sums_rows)
    single_sums = single_day_sums(rows)
    table = table_rows(rows)
    day_labels = day_label_rows(day_rows)
    replay_counts: dict = {}
    for r in replay_rows:
        replay_counts[r["label"]] = replay_counts.get(r["label"], 0) + 1

    ctx = {"table": table, "day": day_labels, "wave_rows": rows, "day_rows": day_rows, "typed_sum_rows": sums_rows,
           "single_sum_rows": single_sums, "n_single": len(e3_rows), "n_typed": len(e4a_rows), "day_label_counts": counts,
           "ga_label_text": "; ".join(f"{f}: {labels[f]['ga_protocol']}, seed {labels[f]['ga_seed']}, commit {labels[f]['ga_commit']}, "
                                      f"dirty tree {labels[f]['ga_dirty_tree']}" for f in FLEETS),
           "empty_text": empty_columns_text(rows),
           "replay_text": f"{len(replay_rows)} (fleet, date, R, L) cells, request and response differences 0 in all; labels "
                          + ", ".join(f"{k} {replay_counts[k]}" for k in sorted(replay_counts))}
    outputs = {
        "wave_gaps.csv": csv_bytes(WAVE_FIELDS, rows),
        "day_gaps.csv": csv_bytes(day_fields, day_rows),
        "day_sums.csv": csv_bytes(DAY_SUMS_FIELDS, single_sums + sums_rows),
        "table_by_R.csv": csv_bytes(TABLE_FIELDS, table),
        "table_by_R.md": markdown_tables(table, day_labels).encode("utf-8"),
        "table_day_labels.csv": csv_bytes(DAY_LABEL_FIELDS, day_labels),
        "README.md": readme_text(ctx).encode("utf-8"),
    }
    outputs.update(figures(rows))
    assert set(outputs) == set(OUTPUT_FILES)

    commit, dirty = git_state(out, git_repo)
    manifest = {
        "work_package": WORK_PACKAGE, "git_commit": commit, "dirty_working_tree": dirty,
        "inputs": dict(sorted(inputs.shas.items())),
        "outputs": {name: hashlib.sha256(outputs[name]).hexdigest() for name in sorted(outputs)},
        "protocols": {name: OUTPUT_PROTOCOLS[name] for name in sorted(OUTPUT_PROTOCOLS)},
        "source_results": {"wp-e3-goal1-single": inputs.rel(e3_dir), "wp-e4a-typed-options": inputs.rel(e4a_dir),
                           "wp-e4b-union-day": inputs.rel(e4b_dir)},
        "ga_labels": labels,
        "versions": {"python": platform.python_version(), "zlib": zlib.ZLIB_VERSION, "csv_json_svg_png": "standard library only",
                     "plotting": "scripts/exact_gap_figure.py (no matplotlib)"},
        "python_provenance": python_provenance(git_repo),
        "host_os": platform.system() + "-" + platform.release(),
        "row_counts": {"wave_gaps.csv": len(rows), "day_gaps.csv": len(day_rows), "day_sums.csv": len(single_sums) + len(sums_rows),
                       "table_by_R.csv": len(table), "table_day_labels.csv": len(day_labels)},
        "day_label_counts": counts,
        "replay_gate": {"cells": len(replay_rows), "labels": replay_counts},
    }
    problems = protocol.private_data_errors(manifest)
    _need(not problems, f"report manifest holds private data: {problems[:3]}")
    out.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (out / name).write_bytes(data)
    (out / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--e3-dir", default=str(E3_DIR))
    ap.add_argument("--e4a-dir", default=str(E4A_DIR))
    ap.add_argument("--e4b-dir", default=str(E4B_DIR))
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        manifest = build_report(Path(args.out), e3_dir=Path(args.e3_dir), e4a_dir=Path(args.e4a_dir), e4b_dir=Path(args.e4b_dir))
    except ReportRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"outputs": len(manifest["outputs"]), "dirty_working_tree": manifest["dirty_working_tree"],
                      "row_counts": manifest["row_counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
