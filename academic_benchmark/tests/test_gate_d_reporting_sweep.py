"""Gate D, D-08b: reporting sweep. No invalid evidence is reachable from active reporting.

Rules checked here (DECISION_LOG A13, A06/A07, E12, A16; plan 2026-10-23 D-08b):

* ``INVALID`` rows (A06: ``metadata.obsolete``) are never returned by a default reader, aggregate, statistic or report.
* ``HISTORICAL_UNVERIFIED`` rows (A13) appear only in the explicitly labelled historical view, never in an aggregate, a
  statistic or a report, and never next to current rows.
* Exact rows are never pooled with fixed or native rows (E12).
* Archived / quarantined paths are never discovered as default input.

The existing quarantine tests (``test_historical_quarantine.py``, ``test_quarantine_round2.py``, ``test_legacy_obsolete.py``) check the
filters themselves and are not repeated. This file feeds ONE mixed fixture (``fixtures/reporting_sweep/mixed_rows.json``) through every
active reporting entry point, and pins the entry-point list against a scan of the code so that a new reader cannot escape the sweep.

How "reads result rows" is detected (``module_reads_result_rows``): the module is parsed with ``ast`` and counts as a row reader or
aggregator when ANY of these holds:

1. it names (imports, defines, calls or references) a row source or aggregator in ``ROW_SOURCE_NAMES`` (``query_benchmark_results``,
   ``get_benchmark_rows``, ``load_csv_frames``, ``summarize_benchmark_rows``, ``analyse_family``, ...);
2. it calls ``csv.DictReader`` or ``read_csv`` (any ``*.read_csv``);
3. a string constant in it names a result file (``benchmark_progress.csv`` ...) or is SQL reading ``benchmark_results`` / ``best_solutions``.

The scan covers non-test ``.py`` files of ``academic_benchmark``, ``optimizer_api``, ``uniride_core`` and ``scripts``. Every detected
module must be in ``SWEPT`` (exercised below), ``COVERED_VIA`` (reached only through a swept module, with the reason) or ``EXEMPT`` (not
a reporting path, with the reason); a module in none of them fails ``test_no_unlisted_row_reader``. The reverse check fails when a
listed module is no longer detected (stale list).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List

import pytest

REPO = Path(__file__).resolve().parents[2]
SCAN_ROOTS = ("academic_benchmark", "optimizer_api", "uniride_core", "scripts")
SKIP_DIRS = {"tests", "__pycache__", "tsplib_data", "numba_results", "sota_results", "results", "paper_prompts", "fixtures"}

ROW_SOURCE_NAMES = frozenset({
    "query_benchmark_results", "query_best_solutions", "get_best_solution", "get_best_solutions",
    "get_benchmark_rows", "get_leaderboard", "get_best_result",
    "load_csv_frames", "load_tuning_frames", "load_history_frames", "load_verified_campaign",
    "filter_obsolete_rows", "filter_obsolete_csv_rows", "filter_obsolete_frame",
    "summarize_benchmark_rows", "summarize_run", "analyse_family", "build_report", "build_descriptive_table",
})
_FILE_CONSTANT = re.compile(r"(benchmark_progress|benchmark_summary|tuning_progress)\.csv")
_SQL_CONSTANT = re.compile(r"\bFROM\s+(benchmark_results|best_solutions)\b", re.IGNORECASE)


def module_reads_result_rows(source: str) -> bool:
    """True when ``source`` reads or aggregates result rows (see the module docstring for the three rules)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        names = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
            if node.attr in ("DictReader", "read_csv"):
                return True
        elif isinstance(node, (ast.ImportFrom, ast.Import)):
            names.extend(alias.name.split(".")[-1] for alias in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _FILE_CONSTANT.search(node.value) or _SQL_CONSTANT.search(node.value):
                return True
        if any(name in ROW_SOURCE_NAMES for name in names):
            return True
        if isinstance(node, ast.Name) and node.id == "read_csv":
            return True
    return False


def scan_row_readers(repo_root: Path) -> List[str]:
    """Repository-relative posix paths of every non-test module under ``SCAN_ROOTS`` that reads or aggregates result rows."""
    found = []
    for top in SCAN_ROOTS:
        base = Path(repo_root) / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            relative = path.relative_to(repo_root)
            if SKIP_DIRS & set(relative.parts) or path.name.startswith("test_") or path.name == "conftest.py":
                continue
            if module_reads_result_rows(path.read_text(encoding="utf-8")):
                found.append(relative.as_posix())
    return found


# Modules exercised by a behavioural test below with the mixed fixture.
SWEPT: Dict[str, str] = {
    "academic_benchmark/analysis/statistics.py": "D-05 analyse_family",
    "academic_benchmark/analysis/report.py": "D-07 build_report / build_descriptive_table",
    "academic_benchmark/analysis/campaign_report.py": "D-07 write_smoke_descriptive_report",
    "academic_benchmark/matrix_run_summary.py": "summarize_run / summarize_benchmark_rows",
    "academic_benchmark/results_reader.py": "get_leaderboard / get_best_result / get_benchmark_rows / get_academic_problems",
    "academic_benchmark/dashboard_utils.py": "load_csv_frames / load_tuning_frames / load_history_frames",
    "academic_benchmark/obsolete_results.py": "filter_obsolete_rows / _csv_rows / _frame",
    "optimizer_api/routers/benchmark.py": "/academic/* readers",
}
SWEPT["academic_benchmark/promoted_configs.py"] = "build_promoted_configs (promotion reads benchmark rows)"
COVERED_VIA: Dict[str, str] = {
    "academic_benchmark/tsplib_manager.py": "primitive SQL layer (query_*/get_best_solution); every default view is reached through results_reader, "
    "dashboard_utils, matrix_run_summary and promoted_configs, which are swept",
    "academic_benchmark/analysis/manifests.py": "load_verified_campaign: campaign rows reach reporting only through campaign_report / the analysis service (swept)",
    "academic_benchmark/dashboard.py": "Streamlit UI (cannot be imported without streamlit): its row reads go through dashboard_utils and "
    "filter_obsolete_rows, checked statically in test_dashboard_reads_only_through_the_filters",
    "academic_benchmark/matrix_validation_plan.py": "only calls summarize_run (swept)",
}
_SCRIPTS_REASON = (
    "plan-experiment archive tooling (exact-day / fleet archives under docs/paper/results); it does not read the TSPLIB benchmark evidence "
    "classes (A06/A13) and is outside D-08b's entry-point list; not exercised here"
)
EXEMPT: Dict[str, str] = {
    "academic_benchmark/benchmark_utils.py": "CSV append helper (header widening) and warm-start lookup; not a report. Warm-start history is quarantined (A13 D2)",
    "academic_benchmark/cli_engine.py": "CLI runner: writes the result CSVs and reads only its own tuning_progress.csv keys for resume; not a report",
    "academic_benchmark/sota_engine.py": "runner that writes benchmark_progress/summary CSVs; not a report",
    "academic_benchmark/smart_benchmark.py": "runner: warm-start lookup of the best stored solution; not a report",
    "academic_benchmark/tools/mark_obsolete_ga_split_variant_results.py": "marker tool: reads rows only to set metadata.obsolete (the INVALID writer); not a report",
    **{f"scripts/{name}": _SCRIPTS_REASON for name in (
        "compare_exact_day_joint_runs.py", "plan_exact_gap_report.py", "plan_fleet_pareto.py", "plan_fleet_scenarios.py",
        "plan_resource_profile.py", "plan_schedule_report.py", "probe_exact_enumeration_scaling.py", "report_exact_day_joint.py",
        "run_exact_union_day.py",
    )},
}


def unlisted_row_readers(repo_root: Path) -> List[str]:
    known = set(SWEPT) | set(COVERED_VIA) | set(EXEMPT)
    return [path for path in scan_row_readers(repo_root) if path not in known]


def test_no_unlisted_row_reader():
    assert unlisted_row_readers(REPO) == [], (
        "these modules read or aggregate result rows but are not in the D-08b sweep lists (SWEPT / COVERED_VIA / EXEMPT)"
    )


def test_listed_modules_are_still_row_readers():
    detected = set(scan_row_readers(REPO))
    stale = sorted(path for path in (*SWEPT, *COVERED_VIA, *EXEMPT) if path not in detected)
    assert stale == [], f"listed but no longer detected as row readers (delete from the list): {stale}"
    for path in (*SWEPT, *COVERED_VIA, *EXEMPT):
        assert (REPO / path).is_file(), path


def test_the_scanner_flags_a_dummy_reader_in_a_temporary_scan_root(tmp_path):
    """A new reader module makes ``unlisted_row_readers`` fail: shown on a temporary copy of the scan root."""
    package = tmp_path / "academic_benchmark"
    package.mkdir()
    (package / "quiet.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    assert unlisted_row_readers(tmp_path) == []
    readers = {
        "dummy_db.py": "from academic_benchmark.tsplib_manager import query_benchmark_results\n",
        "dummy_csv.py": "import csv\n\ndef load(handle):\n    return list(csv.DictReader(handle))\n",
        "dummy_pandas.py": "import pandas as pd\n\ndef load(p):\n    return pd.read_csv(p)\n",
        "dummy_file.py": "PATH = 'results/benchmark_progress.csv'\n",
        "dummy_sql.py": "SQL = 'SELECT * FROM benchmark_results WHERE 1=1'\n",
    }
    for name, text in readers.items():
        (package / name).write_text(text, encoding="utf-8")
    assert sorted(unlisted_row_readers(tmp_path)) == sorted(f"academic_benchmark/{name}" for name in readers)
    # a listed module is no longer reported
    SWEPT_BACKUP = dict(SWEPT)
    try:
        SWEPT["academic_benchmark/dummy_db.py"] = "test"
        assert "academic_benchmark/dummy_db.py" not in unlisted_row_readers(tmp_path)
    finally:
        SWEPT.clear()
        SWEPT.update(SWEPT_BACKUP)


# ============================================================================================================================
# Behavioural sweep: the mixed fixture through every swept entry point
# ============================================================================================================================
import csv  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402

import pandas as pd  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import test_analysis_statistics as fx  # noqa: E402
from academic_benchmark import obsolete_results as orr  # noqa: E402
from academic_benchmark import results_reader  # noqa: E402
from academic_benchmark.analysis import campaign_report as cr  # noqa: E402
from academic_benchmark.analysis.gaps import ExactReferenceTable  # noqa: E402
from academic_benchmark.analysis.manifests import VerifiedCampaign  # noqa: E402
from academic_benchmark.analysis.report import ReportError, build_descriptive_table, build_report  # noqa: E402
from academic_benchmark.analysis.statistics import StatisticsRefusal  # noqa: E402
from academic_benchmark.dashboard_utils import (  # noqa: E402
    benchmark_rows_to_progress_frame,
    load_csv_frames,
    load_history_frames,
    load_tuning_frames,
)
from academic_benchmark.matrix_run_summary import summarize_benchmark_rows, summarize_run  # noqa: E402
from academic_benchmark.promoted_configs import build_promoted_configs  # noqa: E402
from academic_benchmark.studies.service import load_study_with_plan  # noqa: E402
from academic_benchmark.tsplib_manager import get_db, init_db, save_benchmark_result, save_benchmark_run  # noqa: E402
import importlib  # noqa: E402
import sys  # noqa: E402

FIXTURE_FILE = Path(__file__).parent / "fixtures" / "reporting_sweep" / "mixed_rows.json"
ROWS = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))["rows"]


def _algorithms(*labels):
    return {row["algorithm"] for row in ROWS if row["label"] in labels}


CURRENT = _algorithms("current_fixed", "current_native", "exact")
HISTORICAL = _algorithms("historical_unverified")
INVALID = _algorithms("invalid", "invalid_and_historical")
HIST_LABEL = "historical_unverified"
NEW = "2026-10-21T10:00:00"


@pytest.fixture(autouse=True)
def _real_cutoff(monkeypatch):
    monkeypatch.setattr(orr, "LEGACY_CUTOFF", "2026-10-13")


def _names(rows):
    return {row["algorithm"] for row in rows}


def _result(row, number):
    return {
        "problem": row["problem"], "algorithm": row["algorithm"], "run_number": number, "problem_type": "tsp",
        "objective_cost": row["objective_cost"], "tour_cost": row["objective_cost"], "params": {"k": 1},
        "metadata": row["metadata"], "timestamp": row["timestamp"],
    }


@pytest.fixture
def db(tmp_path):
    """Temporary SQLite database holding every fixture row in benchmark_results; best_solutions has no metadata column, so it holds
    the non-INVALID rows only (INVALID is a benchmark_results class)."""
    path = str(tmp_path / "sweep.db")
    conn = get_db(path)
    init_db(conn)
    conn.execute("INSERT INTO problems (name, dimension, category) VALUES ('tiny', 3, 'small')")
    for row in ROWS:
        if row["label"] in ("current_fixed", "historical_unverified"):
            conn.execute(
                "INSERT INTO best_solutions (problem_name, algorithm, params_json, tour_nodes, tour_length, gap, timestamp)"
                " VALUES ('tiny', ?, '{\"k\": 1}', '[0,1,2]', ?, 0.0, ?)", (row["algorithm"], row["objective_cost"], row["timestamp"]),
            )
    conn.commit()
    conn.close()
    for run_id in sorted({row["run_id"] for row in ROWS}):
        save_benchmark_run(run_id, source="web", db_path=path)
    for number, row in enumerate(ROWS, 1):
        save_benchmark_result(row["run_id"], _result(row, number), db_path=path)
    return path


CSV_FIELDS = ["timestamp", "problem", "strategy", "avg_length", "objective_cost", "avg_gap", "avg_time_ms", "n_runs", "obsolete"]


def _csv_row(row, obsolete=""):
    return {
        "timestamp": row["timestamp"], "problem": row["problem"], "strategy": row["algorithm"], "avg_length": row["objective_cost"],
        "objective_cost": row["objective_cost"], "avg_gap": 0.0, "avg_time_ms": 1.0, "n_runs": 1, "obsolete": obsolete,
    }


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def results_dir(tmp_path):
    """A results folder: current file with all classes (INVALID by a row column, and by the OBSOLETE.md marker), plus a quarantine
    sub-folder that holds one more historical row. Markers are written here, not committed in the fixtures folder."""
    root = tmp_path / "numba_results"
    marker_only = dict(BY_LABEL["invalid"], algorithm="ga_split_enhanced", timestamp=NEW)
    rows = [_csv_row(row, obsolete="true" if row["label"].startswith("invalid") else "") for row in ROWS]
    rows.append(_csv_row(marker_only))  # INVALID by the OBSOLETE.md marker + affected algorithm only
    for name in ("benchmark_progress.csv", "benchmark_summary.csv"):
        _write_csv(root / name, rows)
    (root / orr.OBSOLETE_MARKER_FILE).write_text("A06 marker (test)\n", encoding="utf-8")
    quarantined = _csv_row(dict(BY_LABEL["historical_unverified"], algorithm="HIST-QUARANTINED"))
    _write_csv(root / orr.LEGACY_RESULTS_DIRNAME / "benchmark_progress.csv", [quarantined])
    _write_csv(root / orr.LEGACY_RESULTS_DIRNAME / "benchmark_summary.csv", [quarantined])
    tuning = {"timestamp": NEW, "problem": "tiny", "strategy": "TUNE-CURRENT", "param_signature": "k=1"}
    old_tuning = dict(tuning, timestamp="2026-06-30T10:00:00", strategy="TUNE-OLD")
    quarantined_tuning = dict(tuning, strategy="TUNE-QUARANTINED")
    for folder, items in ((root, [tuning, old_tuning]), (root / orr.LEGACY_RESULTS_DIRNAME, [quarantined_tuning])):
        folder.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(items).to_csv(folder / "tuning_progress.csv", index=False)
    return root


BY_LABEL = {row["label"]: row for row in ROWS}
CSV_CURRENT = CURRENT
CSV_HISTORICAL = HISTORICAL | {"HIST-QUARANTINED"}


# ---------------------------------------------------------------------------------------------------- results_reader
def test_results_reader_db_views(db):
    board = results_reader.get_leaderboard(db_path=db)
    assert _names(board["results"]) == {"CUR-FIXED-GA"} and "historical_unverified" not in board
    assert board["historical_unverified_available"] is True
    both = results_reader.get_leaderboard(db_path=db, include_historical=True)
    assert _names(both["results"]) == {"CUR-FIXED-GA"}  # never pooled
    assert _names(both["historical_unverified"]["results"]) == HISTORICAL
    assert all(r["evidence_class"] == HIST_LABEL for r in both["historical_unverified"]["results"])

    assert results_reader.get_best_result("tiny", "HIST-OLD-GA", db_path=db)["result"] is None
    best = results_reader.get_best_result("tiny", "HIST-OLD-GA", db_path=db, include_historical=True)
    assert best["result"] is None and best["historical_unverified"]["result"]["evidence_class"] == HIST_LABEL

    rows = results_reader.get_benchmark_rows(results_dir=str(db) + ".none", db_path=db, limit=100)
    assert _names(rows["results"]) == CURRENT and rows["evidence_class"] == "current"
    assert not (_names(rows["results"]) & (INVALID | HISTORICAL)) and "historical_unverified" not in rows
    both = results_reader.get_benchmark_rows(results_dir=str(db) + ".none", db_path=db, limit=100, include_historical=True)
    assert _names(both["results"]) == CURRENT
    section = both["historical_unverified"]
    assert _names(section["results"]) == HISTORICAL  # INVALID-and-historical stays hidden in the historical view too
    assert all(r["evidence_class"] == HIST_LABEL for r in section["results"])
    # the explicit INVALID switch of the reader adds the INVALID current row only and never lifts the historical exclusion
    opted = results_reader.get_benchmark_rows(results_dir=str(db) + ".none", db_path=db, limit=100, include_obsolete=True)
    assert _names(opted["results"]) == CURRENT | {"ga_split_hf"}

    problems = results_reader.get_academic_problems(db_path=db)
    assert problems["count"] == 1 and not any({"algorithm", "objective_cost", "evidence_class"} & set(p) for p in problems["results"])


def test_results_reader_csv_views_and_quarantine_folder_is_not_default_input(results_dir):
    kwargs = dict(results_dir=str(results_dir), prefer_db=False, limit=100)
    default = results_reader.get_benchmark_rows(**kwargs)
    assert default["source"] == "academic_csv" and _names(default["results"]) == CSV_CURRENT
    assert default["historical_unverified_available"] is True and "historical_unverified" not in default
    both = results_reader.get_benchmark_rows(include_historical=True, **kwargs)
    assert _names(both["results"]) == CSV_CURRENT
    assert _names(both["historical_unverified"]["results"]) == CSV_HISTORICAL
    assert all(r["evidence_class"] == HIST_LABEL for r in both["historical_unverified"]["results"])
    assert not (_names(both["historical_unverified"]["results"]) & INVALID)


# ---------------------------------------------------------------------------------------------------- dashboard_utils
def test_dashboard_utils_views(results_dir):
    summaries, progress, sources = load_csv_frames([str(results_dir)])
    for frames in (summaries, progress):
        assert set(pd.concat(frames)["strategy"]) == CSV_CURRENT
    assert not any(orr.LEGACY_RESULTS_DIRNAME in path for path in sources["summary"] + sources["progress"])  # quarantine folder not read
    summaries, progress, sources = load_csv_frames([str(results_dir)], evidence="historical")
    historical = pd.concat(progress)
    assert set(historical["strategy"]) == CSV_HISTORICAL and set(historical["evidence_class"]) == {HIST_LABEL}
    assert not (set(historical["strategy"]) & INVALID)

    tuning, _ = load_tuning_frames([str(results_dir)])  # glob is recursive: the quarantine folder is found, then filtered out
    assert set(pd.concat(tuning)["strategy"]) == {"TUNE-CURRENT"}
    tuning, _ = load_tuning_frames([str(results_dir)], evidence="historical")
    assert set(pd.concat(tuning)["strategy"]) == {"TUNE-OLD", "TUNE-QUARANTINED"}

    history = results_dir / "history"
    _write_csv(history / "smart_tiny.csv", [_csv_row(row, "true" if row["label"].startswith("invalid") else "") for row in ROWS])
    assert set(pd.concat(load_history_frames(str(history)))["strategy"]) == CURRENT
    assert set(pd.concat(load_history_frames(str(history), evidence="historical"))["strategy"]) == HISTORICAL


def test_dashboard_progress_frame_keeps_only_what_the_reader_returned(db):
    rows = results_reader.get_benchmark_rows(results_dir=str(db) + ".none", db_path=db, limit=100)["results"]
    frame = benchmark_rows_to_progress_frame(rows)
    assert set(frame["strategy"]) == CURRENT


def test_dashboard_reads_only_through_the_filters():
    """dashboard.py cannot be imported without streamlit: check its source. Every ``query_benchmark_results`` call is an argument of
    ``filter_obsolete_rows`` and names the ``evidence`` view; ``load_*_frames`` receive the evidence view; ``RESULT_DIRS`` has no
    archived or quarantine path."""
    tree = ast.parse((REPO / "academic_benchmark" / "dashboard.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    queries = [c for c in calls if c.func.id == "query_benchmark_results"]
    assert queries and all("evidence" in {k.arg for k in c.keywords} for c in queries)
    wrapped = [a for c in calls if c.func.id == "filter_obsolete_rows" for a in c.args if isinstance(a, ast.Call)]
    assert all(q in wrapped for q in queries), "a query_benchmark_results call is not wrapped by filter_obsolete_rows"
    for name in ("load_csv_frames", "load_tuning_frames"):
        loaders = [c for c in calls if c.func.id == name]
        assert loaders and all(len(c.args) == 3 for c in loaders), f"{name} must receive (dirs, include_obsolete, evidence)"
    assigned = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "RESULT_DIRS")
    constants = [n.value for n in ast.walk(assigned.value) if isinstance(n, ast.Constant)]
    assert constants and not any("archive" in c.lower() or "legacy" in c.lower() for c in constants), constants


def test_default_input_locations_are_not_archived_or_quarantined(router):
    defaults = [Path(results_reader.DEFAULT_NUMBA_RESULTS_DIR), Path(router.CLI_RESULTS_DIR), Path(router.CLI_RESULTS_NUMBA_DIR)]
    for path in defaults:
        parts = {p.lower() for p in path.resolve().parts}
        assert "archive" not in parts and orr.LEGACY_RESULTS_DIRNAME.lower() not in parts, path
        assert not any(part.endswith("_legacy") for part in parts), path
    assert Path(results_reader.DEFAULT_NUMBA_RESULTS_DIR).resolve().is_relative_to(REPO)
    # the CLI import lists top-level *.json only: a quarantine sub-folder of a CLI results folder is never discovered
    assert "glob(os.path.join(search_dir, \"*.json\"))" in inspect.getsource(router._find_cli_json_files)


# ---------------------------------------------------------------------------------------------------- obsolete_results
def test_obsolete_results_filters_on_the_mixed_fixture(tmp_path, results_dir):
    rows = [dict(row) for row in ROWS]
    assert _names(orr.filter_obsolete_rows(rows)) == CURRENT
    hist = orr.filter_obsolete_rows(rows, evidence="historical")
    assert _names(hist) == HISTORICAL and all(r["evidence_class"] == HIST_LABEL for r in hist)
    assert _names(orr.filter_obsolete_rows(rows, include_obsolete=True)) == CURRENT | {"ga_split_hf"}
    csv_rows = [_csv_row(row, "true" if row["label"].startswith("invalid") else "") for row in ROWS]
    assert {r["strategy"] for r in orr.filter_obsolete_csv_rows(csv_rows, str(results_dir))} == CURRENT
    quarantine = results_dir / orr.LEGACY_RESULTS_DIRNAME  # a row in a quarantine folder is historical whatever its stamp
    assert orr.filter_obsolete_csv_rows([_csv_row(BY_LABEL["current_fixed"])], str(quarantine)) == []
    frame = orr.filter_obsolete_frame(pd.DataFrame(csv_rows), str(results_dir))
    assert set(frame["strategy"]) == CURRENT
    for bad in ("both", "all", ""):
        with pytest.raises(ValueError):
            orr.filter_obsolete_rows(rows, evidence=bad)  # there is no way to ask for a merged view


# ---------------------------------------------------------------------------------------------------- matrix_run_summary
def test_summarize_run_counts_current_rows_only(db):
    fixed = summarize_run("run-fixed", db_path=db)
    assert fixed["total_rows"] == 1 and set(k[1] for k in fixed["best_feasible"]) == {"CUR-FIXED-GA"}
    assert summarize_run("run-native", db_path=db)["total_rows"] == 1
    assert summarize_run("run-exact", db_path=db)["total_rows"] == 1  # an exact run is summarized alone, never pooled
    opted = summarize_run("run-fixed", db_path=db, include_obsolete=True)
    assert {k[1] for k in opted["best_feasible"]} == {"CUR-FIXED-GA", "ga_split_hf"}  # explicit INVALID switch; historical stays out


FIXED = {"comparison_regime": "fixed_evaluation_budget", "protocol_version": "uniride-fair-tsp-v2", "problem": "tiny"}
NATIVE = {"comparison_regime": "native_termination", "protocol_version": "uniride-native-tsp-v1", "problem": "tiny"}
EXACT = {"protocol": "exact_reference_v1", "problem": "tiny"}


def test_summarize_benchmark_rows_refuses_mixed_protocols():
    ok = {"algorithm": "A", "objective_cost": 1.0}
    fixed = dict(FIXED, **ok)
    for other in (dict(NATIVE, **ok), dict(EXACT, **ok), {"problem": "tiny", **ok}):
        with pytest.raises(ValueError):
            summarize_benchmark_rows([fixed, other])
    assert summarize_benchmark_rows([fixed, dict(FIXED, **ok)])["total_rows"] == 2


@pytest.mark.parametrize("contaminant", [
    {"evidence_class": "historical_unverified"},
    {"evidence_class": "invalid"},
    {"metadata": {"obsolete": True}},
    {"obsolete": True},
])
def test_summarize_benchmark_rows_never_aggregates_historical_or_invalid_rows(contaminant):
    clean = dict(FIXED, algorithm="A", objective_cost=1.0)
    assert summarize_benchmark_rows([clean])["total_rows"] == 1  # positive control
    with pytest.raises(ValueError, match="evidence|obsolete|historical|invalid"):
        summarize_benchmark_rows([clean, dict(clean, **contaminant)])


# ---------------------------------------------------------------------------------------------------- promoted_configs
def test_promotion_never_uses_historical_or_invalid_rows(db):
    for kwargs in ({}, {"include_obsolete": True}):
        configs = build_promoted_configs(db_path=db, include_empty_params=True, **kwargs)["configs"]
        assert not ({c["algorithm"] for c in configs} & HISTORICAL), kwargs
    default = build_promoted_configs(db_path=db, include_empty_params=True)["configs"]
    assert not ({c["algorithm"] for c in default} & INVALID)


# ---------------------------------------------------------------------------------------------------- /academic/* readers
@pytest.fixture
def patched_reader(db, monkeypatch):
    for name in ("get_leaderboard", "get_best_result", "get_benchmark_rows", "get_academic_problems"):
        real = getattr(results_reader, name)
        monkeypatch.setattr(results_reader, name, lambda *a, _real=real, **kw: _real(*a, db_path=db, **kw))
    monkeypatch.setattr(results_reader, "DEFAULT_NUMBA_RESULTS_DIR", str(db) + ".none")
    original = results_reader.get_benchmark_rows
    monkeypatch.setattr(results_reader, "get_benchmark_rows", lambda *a, **kw: original(*a, results_dir=str(db) + ".none", **kw))
    return db


@pytest.fixture(scope="module")
def router():
    """``optimizer_api.routers.benchmark`` imported in-process (no app, no network). The module imports its siblings by bare name
    (``models``, ``strategies``, ...), so ``optimizer_api/`` is put on ``sys.path`` for the import, exactly like
    ``optimizer_api/conftest.py``. Afterwards sys.path is restored and the bare-name modules this import loaded FROM that folder are
    dropped. Modules of ``academic_benchmark`` / ``uniride_core`` / ``optimizer_api.*`` are deliberately kept: dropping them made a
    later test re-import a second copy of the capability catalog (``CapabilityEvidenceError`` in ``test_analysis_report.py``)."""
    before = set(sys.modules)
    folder = (REPO / "optimizer_api").resolve()
    sys.path.insert(0, str(folder))
    try:
        module = importlib.import_module("optimizer_api.routers.benchmark")
        yield module
    finally:
        if str(folder) in sys.path:
            sys.path.remove(str(folder))
        for name in set(sys.modules) - before:
            origin = getattr(sys.modules.get(name), "__file__", None)
            if origin and "." not in name and Path(origin).resolve().is_relative_to(folder):
                sys.modules.pop(name, None)


def _academic_routes(router):
    return {
        "leaderboard": router.get_academic_leaderboard,
        "best": router.get_academic_best_result,
        "benchmark-results": router.get_academic_benchmark_results,
        "problems": router.get_academic_problems,
    }


def test_academic_routes_are_all_swept_and_never_offer_the_invalid_switch(router):
    """The router is mounted only with UNIRIDE_ACADEMIC_PROCESS=1 (A16); the reader functions are called in-process, no network."""
    routes = _academic_routes(router)
    paths = {route.path.split("/academic/", 1)[1] for route in router.router.routes if "/academic/" in route.path}
    assert paths == set(routes), "a new /academic/* route must be added to the sweep"
    for name, function in routes.items():
        assert "include_obsolete" not in inspect.signature(function).parameters, name


def test_academic_routes_return_current_by_default_and_labelled_history_on_request(patched_reader, router):
    board = router.get_academic_leaderboard()
    assert _names(board["results"]) == {"CUR-FIXED-GA"} and "historical_unverified" not in board
    both = router.get_academic_leaderboard(include_historical=True)
    assert _names(both["results"]) == {"CUR-FIXED-GA"} and _names(both["historical_unverified"]["results"]) == HISTORICAL

    with pytest.raises(HTTPException) as refused:
        router.get_academic_best_result(problem="tiny", algorithm="HIST-OLD-GA")
    assert refused.value.status_code == 404
    best = router.get_academic_best_result(problem="tiny", algorithm="HIST-OLD-GA", include_historical=True)
    assert best["historical_unverified"]["result"]["evidence_class"] == HIST_LABEL

    rows = router.get_academic_benchmark_results(limit=100, feasible_only=False)
    assert _names(rows["results"]) == CURRENT and "historical_unverified" not in rows
    both = router.get_academic_benchmark_results(limit=100, feasible_only=False, include_historical=True)
    assert _names(both["results"]) == CURRENT and _names(both["historical_unverified"]["results"]) == HISTORICAL
    assert not (_names(rows["results"]) & INVALID) and not (_names(both["historical_unverified"]["results"]) & INVALID)

    problems = router.get_academic_problems(problem_type=None, category=None, max_dim=0, limit=100)
    assert problems["count"] == 1 and not any({"algorithm", "objective_cost"} & set(p) for p in problems["results"])


# ---------------------------------------------------------------------------------------------------- analysis (D-05, D-07)
@pytest.fixture(scope="module")
def draft_plan():
    return load_study_with_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=fx.REPO, mode="smoke").analysis_plan.plan


@pytest.fixture(scope="module")
def active_plan(draft_plan):
    return fx.activate(draft_plan)


CONTAMINANTS = {
    "historical_unverified": dict(evidence="historical_unverified"),
    "invalid_label": dict(evidence="invalid"),
    "obsolete_flag": dict(obsolete=True),
    "obsolete_metadata": dict(metadata={"obsolete": True}),
}




def _item(algorithm, replicate, gap, **extra):
    budget = fx._levels("eil51")[0]
    return fx.make_item("eil51", algorithm, replicate, gap, objective_evaluations=budget - replicate, termination_reason="budget_exhausted", **extra)


def _clean_items():
    return [_item(algorithm, r, gap) for algorithm, values in fx.SEPARATED.items() for r, gap in enumerate(values)]


def _contaminated(kind):
    items = _clean_items()
    items[0] = _item("Core-GA-TSP", 0, 1.0, **CONTAMINANTS[kind])
    return items


EXACT_ROW = ({"protocol": "exact_reference_v1", "problem": "eil51", "algorithm_id": "EXACT-HIGHS"}, None)
REFUSAL = "evidence_class|obsolete|historical|invalid"


def _analyse(items, plan, clean):
    return fx.analyse_family(
        items, study=fx.study_for(clean, plan), plan=plan, family_id=fx.PER_INSTANCE, run_index=fx.index_for(clean, "paper"),
    )


def test_statistics_service_analyses_the_clean_fixture(active_plan):
    clean = _clean_items()
    result = _analyse(clean, active_plan, clean)  # positive control: the fixture itself is analysable
    assert result is not None


@pytest.mark.parametrize("kind", sorted(CONTAMINANTS))
def test_statistics_service_refuses_historical_and_invalid_rows(active_plan, kind):
    clean = _clean_items()
    with pytest.raises(StatisticsRefusal, match=REFUSAL):
        _analyse(_contaminated(kind), active_plan, clean)


def test_statistics_service_refuses_exact_and_mixed_protocol_rows(active_plan):
    clean = _clean_items()
    with pytest.raises(StatisticsRefusal):
        _analyse(clean + [EXACT_ROW], active_plan, clean)
    native = clean[:-1] + [_item(
        "Core-GWO-TSP-Pure", 4, 15.0, comparison_regime="native_termination", protocol_version="uniride-native-tsp-v1",
    )]
    with pytest.raises(StatisticsRefusal):
        _analyse(native, active_plan, clean)  # fixed and native rows are never in one analysis


def _report(items, plan, index_items):
    return build_report(items, study=fx.study_for(index_items, plan), plan=plan, run_index=fx.index_for(index_items, "smoke"), index_sha256="a" * 64)


def test_report_builder_reports_the_clean_fixture(draft_plan):
    clean = _clean_items()
    report = _report(clean, draft_plan, clean)
    assert {a["algorithm_id"] for table in report.data["tables"] for a in table["algorithms"]} == set(fx.SEPARATED)


@pytest.mark.parametrize("kind", sorted(CONTAMINANTS))
def test_report_builder_refuses_historical_and_invalid_rows(draft_plan, kind):
    clean = _clean_items()
    with pytest.raises(ReportError, match=REFUSAL):
        _report(_contaminated(kind), draft_plan, clean)
    with pytest.raises(ReportError, match=REFUSAL):
        build_descriptive_table(_contaminated(kind), draft_plan)


def test_report_builder_refuses_exact_rows(draft_plan):
    clean = _clean_items()
    with pytest.raises(ReportError):
        _report(clean + [EXACT_ROW], draft_plan, clean)


GAP_COLUMNS = ("gap_to_exact_reference", "gap_unit", "exact_reference_value", "gap_missing_reason")


def _write_campaign_report(monkeypatch, items, folder, plan):
    clean = _clean_items()
    stripped = [({k: v for k, v in row.items() if k not in GAP_COLUMNS}, manifest) for row, manifest in items]  # rows as read: no gap columns
    campaign = VerifiedCampaign(index=fx.index_for(clean, "smoke"), index_sha256="a" * 64, items=stripped, failed=[])
    monkeypatch.setattr(cr, "load_verified_campaign", lambda directory: campaign)
    return cr.write_smoke_descriptive_report(
        folder, study=fx.study_for(clean, plan), plan=plan, plan_problem=None, root=REPO, run_index={"sha256": "a" * 64},
        reference_table_provider=lambda root: ExactReferenceTable(),  # no exact reference: every gap is null with its reason
    )


def test_campaign_report_writes_the_clean_fixture(tmp_path, monkeypatch, draft_plan):
    lines = _write_campaign_report(monkeypatch, _clean_items(), tmp_path, draft_plan)
    assert any("Descriptive report:" in line for line in lines)
    written = json.loads((tmp_path / "descriptive_report.json").read_text(encoding="utf-8"))
    assert {a["algorithm_id"] for table in written["tables"] for a in table["algorithms"]} == set(fx.SEPARATED)


@pytest.mark.parametrize("kind", sorted(CONTAMINANTS))
def test_campaign_report_refuses_historical_and_invalid_rows(tmp_path, monkeypatch, draft_plan, kind):
    with pytest.raises(cr.CampaignReportError, match=REFUSAL):
        _write_campaign_report(monkeypatch, _contaminated(kind), tmp_path, draft_plan)
    assert not (tmp_path / "descriptive_report.txt").exists()  # a refused report leaves no file
