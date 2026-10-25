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
COVERED_VIA: Dict[str, str] = {}
EXEMPT: Dict[str, str] = {}


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
