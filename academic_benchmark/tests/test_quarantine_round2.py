"""DUZELT round 2 for A13: manifest vs committed bytes (E-M1/E-M2), INVALID rows stay hidden in the
historical view too (E-M3), no warm-start backdoor (C-a), parent-folder old rows (C-e)."""

import csv
import hashlib
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from academic_benchmark import obsolete_results as orr
from academic_benchmark import param_db
from academic_benchmark.dashboard_utils import load_csv_frames
from academic_benchmark.obsolete_results import filter_obsolete_csv_rows, filter_obsolete_frame, filter_obsolete_rows
from academic_benchmark.results_reader import get_benchmark_rows
from academic_benchmark.tsplib_manager import query_benchmark_results, save_benchmark_result, save_benchmark_run

BENCH = Path(__file__).resolve().parents[1]
ROOT = BENCH.parent
OLD = "2026-06-30T20:05:09"
NEW = "2026-10-14T09:00:00"
HIST = "historical_unverified"

_HAVE_GIT = shutil.which("git") is not None and (ROOT / ".git").exists()
needs_git = pytest.mark.skipif(not _HAVE_GIT, reason="needs a git checkout")


@pytest.fixture(autouse=True)
def real_cutoff(monkeypatch):
    monkeypatch.setattr(orr, "LEGACY_CUTOFF", "2026-10-13")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


# -- E-M1: the manifest must describe the bytes stored in git, on every platform ----------------
@needs_git
@pytest.mark.parametrize("top", ["numba_results", "sota_results"])
def test_manifest_matches_committed_blobs(top):
    legacy = BENCH / top / orr.LEGACY_RESULTS_DIRNAME
    manifest = json.loads((legacy / orr.QUARANTINE_MANIFEST_FILE).read_text(encoding="utf-8"))
    assert manifest["entries"]
    for entry in manifest["entries"]:
        blob = _git("cat-file", "blob", f":{entry['archive_path']}")
        assert hashlib.sha256(blob).hexdigest() == entry["sha256"], entry["archive_path"]
        assert len(blob) == entry["size_bytes"], entry["archive_path"]


# -- E-M2: the moved files are byte-identical to their 2026-08-01 blobs ------------------------
@needs_git
def test_moved_files_keep_their_original_blobs():
    text = (ROOT / "WIP_CONSOLIDATION_MANIFEST_2026-08-01.md").read_text(encoding="utf-8")
    pairs = re.findall(r"`(academic_benchmark/(?:numba|sota)_results/[^`]+)` \| `([0-9a-f]{40})`", text)
    assert len(pairs) == 10
    for original, oid in pairs:
        top, rest = original.split("/", 2)[1], original.split("/", 2)[2]
        moved = f"academic_benchmark/{top}/{orr.LEGACY_RESULTS_DIRNAME}/{rest}"
        staged = _git("ls-files", "-s", "--", moved).decode().split()
        assert staged and staged[1] == oid, f"{moved}: blob {staged[1:2]} != {oid}"


# -- E-M3: INVALID (A06) rows stay hidden in the historical view as well --------------------------
def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_invalid_rows_hidden_in_historical_view_python_filters(tmp_path):
    rows = [
        {"algorithm": "GoodOld", "timestamp": OLD},
        {"algorithm": "BadOld", "timestamp": OLD, "metadata": {"obsolete": True}},
    ]
    assert [r["algorithm"] for r in filter_obsolete_rows(rows, evidence="historical")] == ["GoodOld"]
    assert [r["algorithm"] for r in filter_obsolete_rows(rows, include_obsolete=True, evidence="historical")] == [
        "GoodOld", "BadOld"]
    (tmp_path / "OBSOLETE.md").write_text("A06", encoding="utf-8")
    csv_rows = [
        {"strategy": "ga_split_enhanced", "timestamp": OLD, "problem": "p"},
        {"strategy": "Plain", "timestamp": OLD, "problem": "p"},
    ]
    got = filter_obsolete_csv_rows(csv_rows, str(tmp_path), evidence="historical")
    assert [r["strategy"] for r in got] == ["Plain"]
    import pandas as pd

    frame = filter_obsolete_frame(pd.DataFrame(csv_rows), str(tmp_path), evidence="historical")
    assert list(frame["strategy"]) == ["Plain"]


def test_invalid_rows_hidden_in_historical_view_readers(tmp_path):
    db = str(tmp_path / "r.db")
    save_benchmark_run("r1", source="web", db_path=db)
    for i, (algo, meta) in enumerate([("GoodDB", {}), ("BadDB", {"obsolete": True})], 1):
        save_benchmark_result("r1", {
            "problem": "tiny", "algorithm": algo, "run_number": i, "problem_type": "tsp",
            "objective_cost": 1.0, "tour_cost": 1.0, "params": {}, "metadata": meta, "timestamp": OLD,
        }, db_path=db)
    assert [r["algorithm"] for r in query_benchmark_results(db_path=db, evidence="historical")] == ["GoodDB"]
    out = get_benchmark_rows(db_path=db, results_dir=str(tmp_path), include_historical=True)
    assert [r["algorithm"] for r in out["historical_unverified"]["results"]] == ["GoodDB"]
    shown = get_benchmark_rows(db_path=db, results_dir=str(tmp_path), include_historical=True, include_obsolete=True)
    assert sorted(r["algorithm"] for r in shown["historical_unverified"]["results"]) == ["BadDB", "GoodDB"]

    res = tmp_path / "res"
    legacy = res / orr.LEGACY_RESULTS_DIRNAME
    legacy.mkdir(parents=True)
    (res / "OBSOLETE.md").write_text("A06", encoding="utf-8")
    (legacy / "OBSOLETE.md").write_text("A06", encoding="utf-8")
    rows = [{"timestamp": OLD, "problem": "p", "strategy": "ga_split_enhanced", "avg_length": 1},
            {"timestamp": OLD, "problem": "p", "strategy": "Plain", "avg_length": 2}]
    _write(res / "benchmark_progress.csv", rows)
    _write(legacy / "benchmark_progress.csv", rows)
    _, prog, _ = load_csv_frames([str(res)], evidence="historical")
    assert sorted(x for f in prog for x in f["strategy"]) == ["Plain", "Plain"]
    out = get_benchmark_rows(db_path=str(tmp_path / "none.db"), results_dir=str(res), include_historical=True)
    assert [r["algorithm"] for r in out["historical_unverified"]["results"]] == ["Plain", "Plain"]


# -- C-e: the historical CSV view also takes old-dated rows of the parent folder's current file --------
def test_historical_csv_view_includes_old_rows_of_parent_file(tmp_path):
    _write(tmp_path / "benchmark_progress.csv", [
        {"timestamp": OLD, "problem": "p", "strategy": "OldInParent", "avg_length": 1},
        {"timestamp": NEW, "problem": "p", "strategy": "New", "avg_length": 2},
    ])
    _, cur, _ = load_csv_frames([str(tmp_path)])
    assert [x for f in cur for x in f["strategy"]] == ["New"]
    _, hist, _ = load_csv_frames([str(tmp_path)], evidence="historical")
    assert [x for f in hist for x in f["strategy"]] == ["OldInParent"]
    assert "parent" in inspect.getdoc(load_csv_frames).lower()


# -- C-a: no environment/flag backdoor puts old params back into warm start (owner decision D2) ----
def _entry(i, ts, score, params):
    return {"id": i, "problem": "eil51", "algorithm": "GA", "params": params, "best_score": score,
            "gap": 1.0, "runs": 3, "dimension": 51, "category": "small", "timestamp": ts}


@pytest.mark.parametrize("value", ["1", "true", "yes"])
def test_env_var_does_not_reenable_legacy_warm_start(tmp_path, monkeypatch, value):
    path = tmp_path / "param_db.json"
    path.write_text(json.dumps([_entry(1, OLD, 1.0, {"p": "old"})]), encoding="utf-8")
    monkeypatch.setattr(param_db, "_PARAM_DB_PATH", str(path))
    monkeypatch.setenv("UNIRIDE_INCLUDE_OBSOLETE", value)
    assert param_db.get_best_for("eil51", "GA") is None
    meta = {"best_params": {"eil51::GA": {"params": {"p": "old"}, "timestamp": OLD}}}
    orr.quarantine_legacy_best_params(meta)
    assert meta["best_params"] == {} and "eil51::GA" in meta["legacy_best_params"]
    assert "include_obsolete" not in inspect.signature(orr.quarantine_legacy_best_params).parameters
    assert "include_obsolete" not in inspect.signature(param_db.get_best_for).parameters
    assert not hasattr(orr, "include_obsolete_default")
