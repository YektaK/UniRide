"""2026-10-13 decision 2: legacy parameters must not warm-start tuning/benchmarks (E1),
plus timestamp parsing (fail-closed) and the opt-in legacy CSV scan in results_reader."""

import json
import os

import pytest

from academic_benchmark import obsolete_results as orr
from academic_benchmark import param_db
from academic_benchmark.obsolete_results import is_legacy_timestamp, quarantine_legacy_best_params
from academic_benchmark.results_reader import get_benchmark_rows

OLD = "2026-05-16 03:13:43"
NEW = "2026-10-14T09:00:00"


@pytest.fixture(autouse=True)
def real_cutoff(monkeypatch):
    monkeypatch.setattr(orr, "LEGACY_CUTOFF", "2026-10-13")
    monkeypatch.delenv("UNIRIDE_INCLUDE_OBSOLETE", raising=False)


def _entry(i, ts, score, params):
    e = {"id": i, "problem": "eil51", "algorithm": "GA", "params": params,
         "best_score": score, "gap": 1.0, "runs": 3, "dimension": 51, "category": "small"}
    if ts is not None:
        e["timestamp"] = ts
    return e


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "param_db.json"
    monkeypatch.setattr(param_db, "_PARAM_DB_PATH", str(path))
    return path


def test_param_db_hides_legacy_entry_by_default(db):
    db.write_text(json.dumps([_entry(1, OLD, 1.0, {"p": "old"}), _entry(2, None, 0.5, {"p": "undated"})]))
    assert param_db.get_best_for("eil51", "GA") is None
    assert param_db.get_best_for("eil51", "GA", include_obsolete=True)["params"] == {"p": "undated"}


def test_param_db_env_opt_in(db, monkeypatch):
    db.write_text(json.dumps([_entry(1, OLD, 1.0, {"p": "old"})]))
    monkeypatch.setenv("UNIRIDE_INCLUDE_OBSOLETE", "1")
    assert param_db.get_best_for("eil51", "GA")["params"] == {"p": "old"}


def test_param_db_uses_post_cutoff_entry_even_if_worse(db):
    db.write_text(json.dumps([_entry(1, OLD, 1.0, {"p": "old"}), _entry(2, NEW, 9.0, {"p": "new"})]))
    assert param_db.get_best_for("eil51", "GA")["params"] == {"p": "new"}


def test_param_db_save_entry_writes_iso_timestamp_that_is_not_legacy(db):
    param_db.save_entry("eil51", "GA", {"p": 1}, 5.0, 0.0, 1, 51)
    stamp = param_db.list_entries()[0]["timestamp"]
    assert not is_legacy_timestamp(stamp, "2000-01-01")
    assert param_db.get_best_for("eil51", "GA", include_obsolete=True) is not None


def _meta():
    return {"best_params": {
        "eil51::GA": {"problem": "eil51", "strategy": "GA", "avg_length": 1.0, "params": {"p": "old"}},
        "a280::GA": {"problem": "a280", "strategy": "GA", "timestamp": OLD, "params": {"p": "old2"}},
        "kroA::GA": {"problem": "kroA", "strategy": "GA", "timestamp": NEW, "params": {"p": "new"}},
    }}


def test_quarantine_moves_not_deletes():
    meta = quarantine_legacy_best_params(_meta())
    assert list(meta["best_params"]) == ["kroA::GA"]
    assert set(meta["legacy_best_params"]) == {"eil51::GA", "a280::GA"}


def test_quarantine_opt_in_keeps_everything():
    meta = quarantine_legacy_best_params(_meta(), include_obsolete=True)
    assert len(meta["best_params"]) == 3 and "legacy_best_params" not in meta


def test_numba_tune_does_not_warm_start_from_legacy(monkeypatch):
    from academic_benchmark import cli_engine

    meta = _meta()
    # no problems/specs: returns the warm-start dict untouched (no tuning tasks)
    best = cli_engine._tune_parameters([], [], 1, 1, 1, meta, skip_cached=True)
    assert set(best) == {"kroA::GA"}


def test_sota_tune_does_not_warm_start_from_legacy():
    from academic_benchmark import sota_engine

    meta = _meta()
    best = sota_engine._run_engine_tuning([], [], 1, 1, 1, meta, skip_cached=True)
    assert set(best) == {"kroA::GA"}


@pytest.mark.parametrize("stamp,legacy", [
    ("2026-06-30", True), ("2026-10-13", False), ("2026-10-13T00:00:00", False),
    ("2026-10-12T23:59:59Z", True), ("2026-10-13T00:00:00Z", False),
    ("2026-10-13T01:00:00+02:00", True),   # 23:00 UTC on the 12th
    ("2026-10-12T23:00:00-02:00", False),  # 01:00 UTC on the 13th
    ("2026/06/30", True), ("13.10.2026", True), ("1781000000", True), ("garbage", True),
    ("", True), (None, True), ("   ", True),
])
def test_timestamp_parsing_fail_closed(stamp, legacy):
    assert is_legacy_timestamp(stamp, "2026-10-13") is legacy


def test_empty_timestamp_row_is_hidden_like_sql():
    assert orr.is_obsolete_row({"algorithm": "x", "timestamp": ""})
    assert orr.is_obsolete_row({"algorithm": "x", "timestamp": None})
    assert not orr.is_obsolete_row({"algorithm": "x"})  # no timestamp column: not judgeable


def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = "timestamp,problem,strategy,avg_length\n"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(header + "".join(f"{t},{p},GA,{n}\n" for t, p, n in rows))


def test_results_reader_scans_legacy_subfolder_only_when_asked(tmp_path):
    base = tmp_path / "res"
    _write_csv(str(base / "benchmark_progress.csv"), [(NEW, "newprob", 1)])
    sub = base / orr.LEGACY_RESULTS_DIRNAME
    _write_csv(str(sub / "benchmark_progress.csv"), [("2026-05-01T00:00:00", "oldprob", 2)])
    (sub / "OBSOLETE.md").write_text("Legacy-Cutoff: 2026-10-13\n", encoding="utf-8")
    kw = dict(results_dir=str(base), db_path=str(tmp_path / "none.db"), prefer_db=False)
    hidden = get_benchmark_rows(**kw)["results"]
    assert [r["problem"] for r in hidden] == ["newprob"]
    shown = get_benchmark_rows(include_obsolete=True, **kw)["results"]
    assert [r["problem"] for r in shown] == ["oldprob", "newprob"]


# ---- DUZELT 2: E2 (legacy_best_params must survive reload), call-site pins, param_db views ----

from academic_benchmark.benchmark_utils import load_metadata, save_metadata


def _two_rounds(path):
    """load -> quarantine -> save, twice (the real startup chain)."""
    for _ in range(2):
        meta = load_metadata(path)
        quarantine_legacy_best_params(meta)
        save_metadata(path, meta)
    return json.load(open(path, encoding="utf-8"))


def test_legacy_best_params_survive_second_startup(tmp_path):
    path = str(tmp_path / "meta.json")
    save_metadata(path, _meta())
    data = _two_rounds(path)
    assert set(data["legacy_best_params"]) == {"eil51::GA", "a280::GA"}
    assert set(data["best_params"]) == {"kroA::GA"}
    assert data["legacy_best_params"]["eil51::GA"]["params"] == {"p": "old"}


def test_load_metadata_keeps_unknown_extra_keys(tmp_path):
    path = str(tmp_path / "meta.json")
    save_metadata(path, {"best_params": {}, "custom_extra": {"x": 1}})
    assert load_metadata(path)["custom_extra"] == {"x": 1}


def test_quarantine_does_not_overwrite_existing_legacy_entry():
    meta = {"best_params": {"k": {"params": {"v": "second"}}},
            "legacy_best_params": {"k": {"params": {"v": "first"}}}}
    quarantine_legacy_best_params(meta)
    assert meta["best_params"] == {}
    assert meta["legacy_best_params"]["k"]["params"] == {"v": "first"}
    assert [e["params"]["v"] for e in meta["legacy_best_params"].values()] == ["first", "second"]
    snapshot = json.dumps(meta, sort_keys=True)
    quarantine_legacy_best_params(meta)  # idempotent
    assert json.dumps(meta, sort_keys=True) == snapshot


def test_optuna_flow_quarantines_legacy():
    from academic_benchmark import cli_engine

    meta = _meta()
    try:
        cli_engine._run_optuna_tuning_flow([], [], 1, 1, meta)
    except Exception:
        pass  # only the warm-start guard at the top matters here
    assert set(meta["best_params"]) == {"kroA::GA"} and len(meta["legacy_best_params"]) == 2


def test_sota_optuna_quarantines_legacy():
    from academic_benchmark import sota_engine

    meta = _meta()
    try:
        sota_engine._run_sota_optuna_tuning([], [], 1, 1, 1, meta)
    except Exception:
        pass
    assert set(meta["best_params"]) == {"kroA::GA"} and len(meta["legacy_best_params"]) == 2


def test_main_quarantines_loaded_metadata(tmp_path, monkeypatch):
    from academic_benchmark import cli_engine

    path = str(tmp_path / "master.json")
    save_metadata(path, _meta())
    monkeypatch.setattr(cli_engine, "METADATA_PATH", path)
    monkeypatch.setattr(cli_engine, "_ensure_dirs", lambda: None)
    monkeypatch.setattr(cli_engine, "_param_db_set", lambda p: None)
    monkeypatch.setattr(cli_engine, "load_problems", lambda *a, **k: [])
    assert cli_engine.main([]) == 1
    active = cli_engine._active_metadata
    assert set(active["best_params"]) == {"kroA::GA"} and len(active["legacy_best_params"]) == 2


def test_param_db_views_hide_or_label_legacy(db):
    db.write_text(json.dumps([_entry(1, OLD, 1.0, {"p": "old"}), _entry(2, NEW, 2.0, {"p": "new"})]))
    assert [e["id"] for e in param_db.list_entries()] == [1, 2]  # management view keeps ids deletable
    assert [e["id"] for e in param_db.list_entries(include_obsolete=False)] == [2]
    assert param_db.is_legacy_entry(param_db.list_entries()[0])
    only_new = param_db.analyze_patterns()
    legacy_inc = param_db.analyze_patterns(include_obsolete=True)
    assert "1 entries" in only_new and "2 entries" in legacy_inc
