"""Lossless TSPLIB matrix storage: v1 (zlib full) and v2 (lzma strict upper triangle)."""
import hashlib
import os
import sqlite3
import sys
import zlib

import numpy as np
import pytest

_AB = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (_AB, os.path.abspath(os.path.join(_AB, ".."))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tsplib_manager as tm  # noqa: E402
from tsplib_matrix_codec import decode_matrix, encode_matrix  # noqa: E402
from tools import compress_tsplib_matrices as conv  # noqa: E402


def _sym(n, dtype, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.integers(1, 10_000, size=(n, n)).astype(dtype)
    if np.issubdtype(np.dtype(dtype), np.floating):
        a = a + 0.123456789
    m = np.triu(a, 1)
    m = m + m.T
    return m.astype(dtype)


def _db(tmp_path):
    path = str(tmp_path / "t.db")
    conn = tm.get_db(path)
    tm.init_db(conn)
    return path, conn


def _problem(conn, name, ewt="EUC_2D", n=5):
    conn.execute(
        "INSERT INTO problems (name, dimension, edge_weight_type) VALUES (?,?,?)", (name, n, ewt)
    )


def _put_v1(conn, name, dm, ewt="EUC_2D"):
    _problem(conn, name, ewt, dm.shape[0])
    conn.execute(
        "INSERT OR REPLACE INTO distance_matrices (problem_name, matrix_blob, dtype, shape_n, "
        "edge_weight_type, computed_at, version) VALUES (?,?,?,?,?,?,1)",
        (name, zlib.compress(dm.tobytes(), 6), str(dm.dtype), dm.shape[0], ewt, "x"),
    )
    conn.commit()


@pytest.mark.parametrize("dtype", ["int32", "float64"])
def test_v2_round_trip_is_bit_identical(dtype):
    dm = _sym(40, dtype)
    blob, version = encode_matrix(dm)
    assert version == 2
    out = decode_matrix(blob, 40, dtype, version)
    assert out.dtype == dm.dtype
    assert out.tobytes() == dm.tobytes()


def test_asymmetric_matrix_stays_v1():
    dm = _sym(10, "int32")
    dm[1, 2] += 7
    blob, version = encode_matrix(dm)
    assert version == 1
    assert decode_matrix(blob, 10, "int32", 1).tobytes() == dm.tobytes()


def test_nonzero_diagonal_stays_v1():
    dm = _sym(10, "int32")
    dm[3, 3] = 5
    assert encode_matrix(dm)[1] == 1


def test_corrupted_v2_blob_raises():
    blob, _ = encode_matrix(_sym(20, "int32"))
    with pytest.raises(Exception):
        decode_matrix(blob[: len(blob) // 2], 20, "int32", 2)
    with pytest.raises(Exception):
        decode_matrix(blob, 21, "int32", 2)  # wrong shape -> length mismatch


def test_readers_load_both_versions(tmp_path):
    path, conn = _db(tmp_path)
    a, b = _sym(12, "int32", 1), _sym(12, "int32", 2)
    _put_v1(conn, "old", a)
    _problem(conn, "new", n=12)
    tm._store_matrix(conn, "new", b, "EUC_2D")  # new writes -> v2
    conn.commit()
    assert conn.execute("SELECT version FROM distance_matrices WHERE problem_name='new'").fetchone()[0] == 2
    conn.close()
    assert tm.get_distance_matrix("old", path).tobytes() == a.tobytes()
    assert tm.get_distance_matrix("new", path).tobytes() == b.tobytes()


def test_atsp_reader_loads_v2(tmp_path):
    path, conn = _db(tmp_path)
    dm = _sym(6, "int32", 3)
    _problem(conn, "atspish", "EXPLICIT", 6)
    conn.execute("UPDATE problems SET problem_type='ATSP' WHERE name='atspish'")
    tm._store_matrix(conn, "atspish", dm, "EXPLICIT")
    conn.commit()
    conn.close()
    got = [p for p in tm.get_all_problems(path) if p["name"] == "atspish"][0]
    assert got["dist_matrix"].tobytes() == dm.tobytes()


def test_conversion_idempotent_and_lossless(tmp_path):
    path, conn = _db(tmp_path)
    sym, f64, asym = _sym(30, "int32", 4), _sym(30, "float64", 5), _sym(30, "int32", 6)
    asym[0, 1] += 1
    _put_v1(conn, "s", sym)
    _put_v1(conn, "f", f64, "GEO")
    _put_v1(conn, "a", asym, "EXPLICIT")
    conn.close()
    r1 = conv.convert(path, vacuum=True)
    assert r1["converted"] == 2 and r1["kept_v1"] == 1
    r2 = conv.convert(path, vacuum=True)
    assert r2["converted"] == 0
    conn = tm.get_db(path)
    vers = dict(conn.execute("SELECT problem_name, version FROM distance_matrices").fetchall())
    conn.close()
    assert vers == {"s": 2, "f": 2, "a": 1}
    for name, ref in (("s", sym), ("f", f64), ("a", asym)):
        got = tm.get_distance_matrix(name, path)
        assert hashlib.sha256(got.tobytes()).hexdigest() == hashlib.sha256(ref.tobytes()).hexdigest()


def test_dry_run_changes_nothing(tmp_path):
    path, conn = _db(tmp_path)
    _put_v1(conn, "s", _sym(30, "int32"))
    conn.close()
    before = open(path, "rb").read()
    r = conv.convert(path, dry_run=True)
    assert r["converted"] == 1
    assert open(path, "rb").read() == before
