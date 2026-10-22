#!/usr/bin/env python3
"""WP-E11 J12: per-cell comparison of two runs of the joint day campaign (rerun against first run).

OFFLINE, read only, no solver. Takes two run folders, each holding the raw runner files ``day_joint.csv``,
``day_joint_stages.csv``, ``lb0.csv``, ``day_joint_plans.json``, ``day_joint_week.csv`` and ``day_joint_manifest.json``
(see ``scripts/run_exact_day_joint.py``), and writes one CSV row per cell (DECISION_LOG E14, J11 results note; the
README of the J11 record describes the columns).

Compared per cell: every ``day_joint.csv`` column except the timing column ``wall_seconds``; every stage field except the
timing columns ``wall_seconds`` and ``work_units``; the plan (parsed JSON); the ``lb0.csv`` rows; the MPS sha256 of every
stage from the manifests. A cell present in only one run is a refusal (exit 2), never a row.

Classification of a cell (printed summary and exit code):

* ``identical``: nothing but timing columns differs;
* ``bound_only``: the only differences are in the raw ``bound`` column of stage rows, while the plan, the ``lb0.csv`` rows
  and the MPS hashes are equal and no ``day_joint.csv`` column differs. This is the effect of the snapping of Gurobi day
  bounds (E14, integrality-fix note): ``bound_ceil``, ``status``, ``objective`` and ``bound_source`` do not change;
* ``other``: anything else (a label, a value, a stage status, a ``bound_ceil``, a plan, a bound row, a model hash, a
  missing stage row). Each such cell is listed.

The output file must lie outside ``docs/paper/results`` and must not exist yet (results are never overwritten).

Run: python scripts/compare_exact_day_joint_runs.py FIRST_DIR RERUN_DIR --out OUT.csv
Exit codes: 0 every cell is identical or bound_only; 1 at least one cell is ``other`` (the CSV is still written);
2 refused arguments, files or cell sets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "docs" / "paper" / "results"

RUN_FILES = ("day_joint.csv", "day_joint_stages.csv", "lb0.csv", "day_joint_plans.json", "day_joint_week.csv",
             "day_joint_manifest.json")
TIMING_DAY = frozenset({"wall_seconds"})
TIMING_STAGE = frozenset({"wall_seconds", "work_units"})
BOUND_COLUMN = "bound"

OUT_FIELDS = ("cell", "fleet", "date", "R", "L", "first_day_status", "rerun_day_status", "first_K_or_S", "rerun_K_or_S",
              "first_proof_claim_allowed", "rerun_proof_claim_allowed", "day_status_equal", "K_or_S_equal", "minutes_equal",
              "plan_equal", "lb0_rows_equal", "mps_sha256_equal", "mps_stages", "day_joint_columns_differing",
              "stage_fields_differing")
IDENTICAL, BOUND_ONLY, OTHER = "identical", "bound_only", "other"


class Refusal(Exception):
    """Unusable arguments, files or cell sets (exit code 2)."""


@dataclass
class Run:
    path: Path
    day: dict
    stages: dict   # cell -> {(solver, stage): row}
    lb0: dict      # cell -> list of sorted item tuples
    plans: dict
    manifest: dict


@dataclass
class CellResult:
    row: dict
    kind: str
    stage_diffs: list = field(default_factory=list)  # (solver, stage, column or None, old, new)


def _rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def cell_key(r: dict) -> str:
    return f"{r['fleet']}|{r['date']}|R{r['R']}|L{r['L'] if r['L'] != '' else '-'}"


def load_run(path: Path) -> Run:
    path = Path(path)
    missing = [name for name in RUN_FILES if not (path / name).is_file()]
    if missing:
        raise Refusal(f"{path} lacks run file(s): {', '.join(missing)}")
    day = {cell_key(r): r for r in _rows(path / "day_joint.csv")}
    stages: dict = {}
    for r in _rows(path / "day_joint_stages.csv"):
        stages.setdefault(cell_key(r), {})[(r["solver"], r["stage"])] = r
    lb0: dict = {}
    for r in _rows(path / "lb0.csv"):
        lb0.setdefault(cell_key(r), []).append(tuple(sorted(r.items())))
    return Run(path, day, stages, lb0,
               json.loads((path / "day_joint_plans.json").read_text(encoding="utf-8")),
               json.loads((path / "day_joint_manifest.json").read_text(encoding="utf-8")))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _stage_diffs(first: Run, rerun: Run, key: str) -> list:
    out = []
    s1, s2 = first.stages.get(key, {}), rerun.stages.get(key, {})
    for sk in sorted(set(s1) | set(s2)):
        x, y = s1.get(sk), s2.get(sk)
        if x is None or y is None:
            out.append((sk[0], sk[1], None, "missing_first" if x is None else "missing_rerun", ""))
            continue
        for c in y:
            if c not in TIMING_STAGE and x.get(c) != y.get(c):
                out.append((sk[0], sk[1], c, x.get(c), y.get(c)))
    return out


def _stage_text(d: tuple) -> str:
    solver, stage, column, old, new = d
    if column is None:
        return f"{solver}{stage}:{old}"
    return f"{solver}{stage}.{column}:{old}->{new}"


def compare_cell(first: Run, rerun: Run, key: str) -> CellResult:
    a, b = first.day[key], rerun.day[key]
    columns = [c for c in b if c not in TIMING_DAY and a.get(c) != b.get(c)]
    diffs = _stage_diffs(first, rerun, key)
    mps1, mps2 = first.manifest.get("mps_sha256", {}), rerun.manifest.get("mps_sha256", {})
    mps_keys = [m for m in set(mps1) | set(mps2) if m.startswith(key + "|")]
    mps_equal = all(mps1.get(m) == mps2.get(m) for m in mps_keys)
    plan_equal = first.plans.get(key) == rerun.plans.get(key)
    lb0_equal = sorted(first.lb0.get(key, [])) == sorted(rerun.lb0.get(key, []))
    row = {"cell": key, "fleet": b["fleet"], "date": b["date"], "R": b["R"], "L": b["L"],
           "first_day_status": a["day_status"], "rerun_day_status": b["day_status"],
           "first_K_or_S": a["K_or_S"], "rerun_K_or_S": b["K_or_S"],
           "first_proof_claim_allowed": a["proof_claim_allowed"], "rerun_proof_claim_allowed": b["proof_claim_allowed"],
           "day_status_equal": a["day_status"] == b["day_status"], "K_or_S_equal": a["K_or_S"] == b["K_or_S"],
           "minutes_equal": ((a["total_minutes"], a["car_minutes"], a["large_peak"])
                             == (b["total_minutes"], b["car_minutes"], b["large_peak"])),
           "plan_equal": plan_equal, "lb0_rows_equal": lb0_equal, "mps_sha256_equal": mps_equal, "mps_stages": len(mps_keys),
           "day_joint_columns_differing": ";".join(f"{c}:{a.get(c)}->{b.get(c)}" for c in columns),
           "stage_fields_differing": ";".join(_stage_text(d) for d in diffs)}
    if not (columns or diffs or not (plan_equal and lb0_equal and mps_equal)):
        kind = IDENTICAL
    elif (not columns and diffs and all(d[2] == BOUND_COLUMN for d in diffs)
          and plan_equal and lb0_equal and mps_equal):
        kind = BOUND_ONLY
    else:
        kind = OTHER
    return CellResult(row, kind, diffs)


def compare_runs(first: Run, rerun: Run) -> list:
    only1, only2 = sorted(set(first.day) - set(rerun.day)), sorted(set(rerun.day) - set(first.day))
    if only1 or only2:
        raise Refusal("cell sets differ: only in first run: " + (", ".join(only1) or "-")
                      + "; only in rerun: " + (", ".join(only2) or "-"))
    if not rerun.day:
        raise Refusal("the runs have no cells")
    return [compare_cell(first, rerun, key) for key in sorted(rerun.day)]


def check_out(out: Path) -> None:
    out_r = Path(out).resolve()
    results = RESULTS.resolve()
    if out_r == results or results in out_r.parents:
        raise Refusal("--out lies inside docs/paper/results; write the comparison elsewhere")
    if out_r.exists():
        raise Refusal("--out exists; results are never overwritten")


def write_csv(path: Path, results: list) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(OUT_FIELDS), lineterminator="\n", extrasaction="raise")
        w.writeheader()
        w.writerows(r.row for r in results)


def summary_lines(first: Run, rerun: Run, results: list) -> list:
    n = len(results)
    lines = [f"cells {n}"]
    for name in ("day_status_equal", "K_or_S_equal", "minutes_equal", "plan_equal", "lb0_rows_equal", "mps_sha256_equal"):
        equal = sum(1 for r in results if r.row[name] is True)
        lines.append(f"{name}: equal {equal}, differing {n - equal}")
    kinds = {k: sum(1 for r in results if r.kind == k) for k in (IDENTICAL, BOUND_ONLY, OTHER)}
    lines.append(f"identical {kinds[IDENTICAL]}, bound_only {kinds[BOUND_ONLY]}, other {kinds[OTHER]}")
    bound_rows = sum(1 for r in results if r.kind == BOUND_ONLY for d in r.stage_diffs)
    lines.append(f"stage rows with a changed raw bound in bound_only cells: {bound_rows}")
    for r in results:
        if r.kind == OTHER:
            lines.append(f"other: {r.row['cell']} | day_joint: {r.row['day_joint_columns_differing'] or '-'}"
                         f" | stages: {r.row['stage_fields_differing'] or '-'}")
    for name in ("day_joint_plans.json", "day_joint_week.csv", "lb0.csv"):
        same = sha256_file(first.path / name) == sha256_file(rerun.path / name)
        lines.append(f"{name} byte-identical: {same}")
    m1, m2 = first.manifest, rerun.manifest
    lines.append(f"manifest git_commit {str(m1.get('git_commit', ''))[:8]} -> {str(m2.get('git_commit', ''))[:8]}; "
                 f"mps_sha256 entries {len(m1.get('mps_sha256', {}))} / {len(m2.get('mps_sha256', {}))}, "
                 f"all equal: {m1.get('mps_sha256', {}) == m2.get('mps_sha256', {})}")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("first_dir", help="run folder of the first run")
    ap.add_argument("rerun_dir", help="run folder of the rerun")
    ap.add_argument("--out", required=True, help="comparison CSV to write (outside docs/paper/results, must not exist)")
    args = ap.parse_args(argv)
    try:
        check_out(Path(args.out))
        first, rerun = load_run(Path(args.first_dir)), load_run(Path(args.rerun_dir))
        results = compare_runs(first, rerun)
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    write_csv(Path(args.out), results)
    for line in summary_lines(first, rerun, results):
        print(line)
    return 1 if any(r.kind == OTHER for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
