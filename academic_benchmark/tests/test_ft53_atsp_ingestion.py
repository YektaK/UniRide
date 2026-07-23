"""Regression tests for the ft53 ATSP instance — fully hermetic.

Every test uses ``tmp_path`` and never touches the developer's production
``tsplib.db``.  The CLI-engine test monkeypatches ``TSPLIB_DB`` so the
real ``load_problems()`` fast-path is exercised against a temporary DB
that satisfies the ``_db_ready`` threshold (≥ 10 problems).

Provenance
----------
- Authoritative URL: https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz
- Mirror used during initial acquisition: https://raw.githubusercontent.com/pdrozdowski/TSPLib.Net/master/TSPLIB95/atsp/ft53.atsp
- Retrieval date: 2026-07-20
- Decompressed SHA-256: 692ae545e226d88aa095e3e726c8a1dadf4ecc9b97852d0cdbb2ca2a98dd2634
- Canonical optimum: 6905
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

import numpy as np
import pytest

from academic_benchmark.seed_ft53 import (
    FT53_ATSP_PATH,
    FT53_AUTHORITY_URL,
    FT53_DIMENSION,
    FT53_MIRROR_URL,
    FT53_OPTIMAL,
    FT53_RETRIEVAL_DATE,
    FT53_SHA256,
    seed_ft53,
)

EXPECTED_OPTIMUM = FT53_OPTIMAL
EXPECTED_DIMENSION = FT53_DIMENSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_TSP_TEMPLATE = (
    "NAME : {name}\n"
    "TYPE : TSP\n"
    "DIMENSION : 4\n"
    "EDGE_WEIGHT_TYPE : EUC_2D\n"
    "NODE_COORD_SECTION\n"
    "1 {x0} 0\n"
    "2 1 0\n"
    "3 1 1\n"
    "4 0 1\n"
    "EOF\n"
)


def _seed_dummy_tsp_problems(db_path: str, count: int) -> None:
    """Insert *count* minimal 4-node TSP problems so ``_db_ready`` passes."""
    from academic_benchmark.tsplib_manager import store_academic_text
    for i in range(count):
        name = f"_dummy_tsp_{i:02d}"
        text = _DUMMY_TSP_TEMPLATE.format(name=name, x0=i)
        store_academic_text(text, "tsp", name=name, db_path=db_path,
                            source_file="test_ft53_fixture")


def _seed_ft53_db(tmp_path) -> str:
    """Create a fresh DB with ft53 + 9 dummy TSPs (≥10 total).  Return path."""
    db = str(tmp_path / "hermetic.db")
    _seed_dummy_tsp_problems(db, count=9)
    result = seed_ft53(db_path=db)
    assert result["stored"] == ["ft53"]
    return db


def _parse_atsp_matrix() -> np.ndarray:
    """Parse ft53.atsp and return the raw NxN cost matrix."""
    from uniride_core.algorithms.tsplib_parser import parse_atsp_text

    with open(FT53_ATSP_PATH, encoding="utf-8") as fh:
        text = fh.read()
    info = parse_atsp_text(text, "ft53")
    assert info is not None, "parse_atsp_text returned None"
    return np.asarray(info["explicit_matrix"], dtype=int)


# ---------------------------------------------------------------------------
# File integrity
# ---------------------------------------------------------------------------

class TestFt53RawFileIntegrity:
    def test_file_exists(self):
        assert os.path.isfile(FT53_ATSP_PATH), f"Missing {FT53_ATSP_PATH}"

    def test_sha256(self):
        with open(FT53_ATSP_PATH, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        assert digest == FT53_SHA256, f"SHA-256 mismatch: {digest}"

    def test_header_lines(self):
        with open(FT53_ATSP_PATH, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh.readlines()[:7]]
        header = {ln.split(":")[0].strip().upper(): ln.split(":", 1)[1].strip()
                  for ln in lines if ":" in ln}
        assert header["NAME"] == "ft53"
        assert header["TYPE"] == "ATSP"
        assert int(header["DIMENSION"]) == EXPECTED_DIMENSION
        assert header["EDGE_WEIGHT_TYPE"] == "EXPLICIT"

    def test_provenance_constants(self):
        assert FT53_AUTHORITY_URL.startswith("https://comopt.ifi.uni-heidelberg.de/")
        assert "ft53.atsp.gz" in FT53_AUTHORITY_URL
        assert FT53_MIRROR_URL.startswith("https://raw.githubusercontent.com/")
        assert FT53_RETRIEVAL_DATE == "2026-07-20"
        assert FT53_SHA256 == "692ae545e226d88aa095e3e726c8a1dadf4ecc9b97852d0cdbb2ca2a98dd2634"
        assert FT53_OPTIMAL == 6905


# ---------------------------------------------------------------------------
# Seed + get_all_problems round-trip (no _db_ready gate)
# ---------------------------------------------------------------------------

class TestFt53SeedAndLoad:
    def test_seed_populates_db(self, tmp_path):
        db = str(tmp_path / "ft53.db")
        result = seed_ft53(db_path=db)
        assert result["stored"] == ["ft53"]
        assert result["skipped"] == []

    def test_seed_is_idempotent(self, tmp_path):
        db = str(tmp_path / "ft53.db")
        first = seed_ft53(db_path=db)
        second = seed_ft53(db_path=db)
        assert first["stored"] == ["ft53"]
        assert second["stored"] == []
        assert second["skipped"] == ["ft53"]

    def test_seed_force_reinserts(self, tmp_path):
        db = str(tmp_path / "ft53.db")
        seed_ft53(db_path=db)
        result = seed_ft53(db_path=db, force=True)
        assert result["stored"] == ["ft53"]
        assert result["skipped"] == []

    def test_get_all_problems_returns_ft53(self, tmp_path):
        db = str(tmp_path / "ft53.db")
        seed_ft53(db_path=db)

        from academic_benchmark.tsplib_manager import (
            get_all_problems, problem_row_to_instance,
        )
        rows = get_all_problems(db_path=db, max_dim=99999, exclude_explicit=False)
        ft53_rows = [r for r in rows if r["name"] == "ft53"]
        assert len(ft53_rows) == 1, f"Expected 1 ft53 row, got {len(ft53_rows)}"

        inst = problem_row_to_instance(ft53_rows[0])
        assert inst.name == "ft53"
        assert inst.dimension == EXPECTED_DIMENSION
        assert inst.problem_type == "atsp"
        assert inst.edge_weight_type == "EXPLICIT"
        assert inst.optimal == EXPECTED_OPTIMUM


# ---------------------------------------------------------------------------
# Hermetic load_problems() test — exercises the real DB fast path
# ---------------------------------------------------------------------------

class TestFt53LoadProblemsHermetic:
    """Uses a temporary DB with ≥10 problems so ``_db_ready()`` returns True.

    Monkeypatches ``cli_engine.TSPLIB_DB`` so the genuine ``load_problems()``
    fast-path is exercised without touching the production database.
    """

    def test_load_problems_returns_ft53(self, tmp_path):
        db = _seed_ft53_db(tmp_path)

        import academic_benchmark.cli_engine as ce
        orig = ce.TSPLIB_DB
        ce.TSPLIB_DB = db
        try:
            problems = ce.load_problems()
        finally:
            ce.TSPLIB_DB = orig

        names = [p.name for p in problems]
        assert "ft53" in names, f"ft53 not in load_problems() (first 10): {names[:10]}"

        ft53 = next(p for p in problems if p.name == "ft53")
        assert ft53.name == "ft53"
        assert ft53.dimension == EXPECTED_DIMENSION
        assert ft53.problem_type == "atsp"
        assert ft53.edge_weight_type == "EXPLICIT"
        assert ft53.optimal == EXPECTED_OPTIMUM
        assert ft53.dist_matrix is not None

    def test_load_problems_directed_matrix_shape(self, tmp_path):
        db = _seed_ft53_db(tmp_path)

        import academic_benchmark.cli_engine as ce
        orig = ce.TSPLIB_DB
        ce.TSPLIB_DB = db
        try:
            problems = ce.load_problems()
        finally:
            ce.TSPLIB_DB = orig

        ft53 = next(p for p in problems if p.name == "ft53")
        m = np.asarray(ft53.dist_matrix, dtype=int)
        assert m.shape == (EXPECTED_DIMENSION, EXPECTED_DIMENSION)

    def test_load_problems_directed_asymmetry(self, tmp_path):
        db = _seed_ft53_db(tmp_path)

        import academic_benchmark.cli_engine as ce
        orig = ce.TSPLIB_DB
        ce.TSPLIB_DB = db
        try:
            problems = ce.load_problems()
        finally:
            ce.TSPLIB_DB = orig

        ft53 = next(p for p in problems if p.name == "ft53")
        m = np.asarray(ft53.dist_matrix, dtype=int)
        asym_count = int(np.sum(m != m.T))
        assert asym_count > 0, "Matrix is symmetric — ft53 should be asymmetric"
        ratio = asym_count / (EXPECTED_DIMENSION * EXPECTED_DIMENSION)
        assert ratio > 0.5, f"Only {ratio:.1%} of entries are asymmetric"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

class TestFt53CliSeeder:
    def test_cli_main_seeds_ft53(self, tmp_path):
        db = str(tmp_path / "cli_test.db")
        from academic_benchmark.seed_ft53 import main
        rc = main(["--db-path", db])
        assert rc == 0

        from academic_benchmark.tsplib_manager import get_all_problems
        rows = get_all_problems(db_path=db, max_dim=99999, exclude_explicit=False)
        assert any(r["name"] == "ft53" for r in rows)

    def test_cli_main_is_idempotent(self, tmp_path):
        db = str(tmp_path / "cli_test.db")
        from academic_benchmark.seed_ft53 import main
        assert main(["--db-path", db]) == 0
        assert main(["--db-path", db]) == 0

    def test_cli_main_force_reinserts(self, tmp_path):
        db = str(tmp_path / "cli_test.db")
        from academic_benchmark.seed_ft53 import main
        assert main(["--db-path", db]) == 0
        rc = main(["--db-path", db, "--force"])
        assert rc == 0

    def test_cli_main_help(self):
        proc = subprocess.run(
            [sys.executable, "-m", "academic_benchmark.seed_ft53", "--help"],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )
        assert proc.returncode == 0
        assert "ft53" in proc.stdout.lower() or "seed" in proc.stdout.lower()


# ---------------------------------------------------------------------------
# Directed matrix integrity (via raw parse — independent of DB)
# ---------------------------------------------------------------------------

class TestFt53DirectedMatrix:
    def test_shape(self):
        m = _parse_atsp_matrix()
        assert m.shape == (EXPECTED_DIMENSION, EXPECTED_DIMENSION)

    def test_genuinely_asymmetric(self):
        m = _parse_atsp_matrix()
        asym_count = int(np.sum(m != m.T))
        assert asym_count > 0, "Matrix is symmetric — ft53 should be asymmetric"

    def test_asymmetry_ratio(self):
        m = _parse_atsp_matrix()
        total = m.shape[0] * m.shape[1]
        asym_count = int(np.sum(m != m.T))
        ratio = asym_count / total
        assert ratio > 0.5, f"Only {ratio:.1%} of entries are asymmetric"

    def test_diagonal_is_large_sentinel(self):
        m = _parse_atsp_matrix()
        diag = np.diag(m)
        assert np.all(diag == 9999999), f"Diagonal not all 9999999: {diag}"

    def test_optimal_is_6905(self):
        from uniride_core.algorithms.tsplib_parser import TSPLIB_OPTIMALS
        assert TSPLIB_OPTIMALS.get("ft53") == EXPECTED_OPTIMUM
