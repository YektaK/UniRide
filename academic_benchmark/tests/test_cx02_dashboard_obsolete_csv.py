"""CX-02: dashboard CSV ingestion must honour the obsolete-result guard."""

import csv
import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from academic_benchmark.dashboard_utils import load_csv_frames
from academic_benchmark.obsolete_results import filter_obsolete_csv_rows, filter_obsolete_frame
from academic_benchmark.results_reader import get_benchmark_rows

BENCH_DIR = str(Path(__file__).resolve().parents[1])


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path, marker=True, flag=True):
    if marker:
        (tmp_path / "OBSOLETE.md").write_text("obsolete", encoding="utf-8")
    meta = json.dumps({"obsolete": True}) if flag else "{}"
    _write(tmp_path / "benchmark_progress.csv", [
        {"problem": "p", "algorithm": "ga_split_hf", "tour_cost": 1, "metadata": meta},
        {"problem": "p", "algorithm": "GA-Split-Enhanced", "tour_cost": 2, "metadata": "{}"},
        {"problem": "p", "algorithm": "ga_split", "tour_cost": 3, "metadata": "{}"},
    ])
    _write(tmp_path / "benchmark_summary.csv", [
        {"strategy": "ga_split_hf", "avg_length": 1},
        {"strategy": "ga split enhanced", "avg_length": 2},
        {"strategy": "ga_split", "avg_length": 3},
    ])
    return str(tmp_path)


@pytest.fixture
def dashboard(monkeypatch):
    pytest.importorskip("streamlit")
    monkeypatch.syspath_prepend(BENCH_DIR)
    sys.modules.pop("dashboard", None)
    module = importlib.import_module("dashboard")
    monkeypatch.setattr(module, "query_benchmark_results", lambda **kw: [])
    yield module
    sys.modules.pop("dashboard", None)


def test_dashboard_load_data_excludes_marked_rows(dashboard, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "RESULT_DIRS", [_fixture(tmp_path)])
    summary, progress, *_ = dashboard.load_data.__wrapped__(False)
    assert list(summary["strategy"]) == ["ga_split"]
    assert list(progress["algorithm"]) == ["ga_split"]


def test_dashboard_include_obsolete_override(dashboard, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "RESULT_DIRS", [_fixture(tmp_path)])
    summary, progress, *_ = dashboard.load_data.__wrapped__(True)
    assert len(summary) == 3 and len(progress) == 3


def test_dashboard_row_metadata_alone_excludes_without_marker(dashboard, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "RESULT_DIRS", [_fixture(tmp_path, marker=False)])
    summary, progress, *_ = dashboard.load_data.__wrapped__(False)
    # no sibling marker: affected algorithm names are kept, only flagged rows go
    assert len(summary) == 3
    assert list(progress["algorithm"]) == ["GA-Split-Enhanced", "ga_split"]


def test_frame_filter_mixed_and_noop_cases(tmp_path):
    d = _fixture(tmp_path)
    frame = pd.read_csv(Path(d) / "benchmark_progress.csv")
    assert list(filter_obsolete_frame(frame, d)["algorithm"]) == ["ga_split"]
    assert len(filter_obsolete_frame(frame, d, include_obsolete=True)) == 3
    assert filter_obsolete_frame(pd.DataFrame(), d).empty


def test_csv_row_filter_matches_shared_reader(tmp_path):
    d = _fixture(tmp_path)
    via_reader = get_benchmark_rows(
        results_dir=d, filename="benchmark_summary.csv", prefer_db=False, include_obsolete=False
    )
    assert [r["algorithm"] for r in via_reader["results"]] == ["ga_split"]
    rows = [{"strategy": "ga_hf", "x": 1}, {"strategy": "GA-Split-HF"}, {"algorithm": "ga_split"}]
    kept = filter_obsolete_csv_rows(rows, d)
    assert [r.get("strategy", r.get("algorithm")) for r in kept] == ["ga_hf", "ga_split"]


def _concat(frames):
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def test_load_csv_frames_filters_summary_and_progress_before_concat(tmp_path):
    d = _fixture(tmp_path)
    clean = tmp_path / "clean"
    clean.mkdir()
    _write(clean / "benchmark_summary.csv", [{"strategy": "ga_split_hf", "avg_length": 9}])
    summaries, progress, sources = load_csv_frames([d, str(clean)])
    # the clean directory has no marker, so its row is kept; the marked directory keeps only ga_split
    assert sorted(_concat(summaries)["strategy"]) == ["ga_split", "ga_split_hf"]
    assert list(_concat(progress)["algorithm"]) == ["ga_split"]
    assert len(sources["summary"]) == 2 and len(sources["progress"]) == 1
    s_all, p_all, _ = load_csv_frames([d], include_obsolete=True)
    assert len(_concat(s_all)) == 3 and len(_concat(p_all)) == 3


def test_reader_csv_path_honours_row_metadata_without_marker(tmp_path):
    d = _fixture(tmp_path, marker=False)
    _write(tmp_path / "bm.csv", [
        {"strategy": "ga_split_hf", "metadata": json.dumps({"obsolete": True})},
        {"strategy": "ga_split_hf", "metadata": "{}"},
    ])
    out = get_benchmark_rows(results_dir=d, filename="bm.csv", prefer_db=False)
    assert len(out["results"]) == 1
