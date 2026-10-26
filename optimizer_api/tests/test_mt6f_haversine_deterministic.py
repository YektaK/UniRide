"""MT6F-05 (audit L10-a/L10-b, DECISION_LOG A21 OQ-F3 a).

The ``geo_coords=True`` haversine stand-in must be a pure function of the
coordinates: no per-process salted ``hash()`` factors and no forced synthetic
asymmetry. It is exercised in two child processes with different
``PYTHONHASHSEED`` values, in both places that build it: the academic
coordinate scope and the opt-in coordinate fallback. Offline, no database.
"""

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from utils.data_loader import DataLoader
from utils.matrix_repository import TimeMatrixRepository

_PROBE = Path(__file__).with_name("_mt6f_haversine_probe.py")
_API_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _API_DIR.parent
_FLAG = "UNIRIDE_ALLOW_COORDINATE_FALLBACK"


def _run_probe(mode: str, hash_seed: str):
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_API_DIR), str(_REPO_ROOT), env.get("PYTHONPATH", "")]
    )
    env.pop(_FLAG, None)
    if mode == "fallback":
        env[_FLAG] = "1"
    result = subprocess.run(
        [sys.executable, str(_PROBE), mode],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


@pytest.mark.parametrize("mode", ["academic", "fallback"])
def test_haversine_stand_in_is_identical_across_hash_seeds(mode):
    first = _run_probe(mode, "1")
    second = _run_probe(mode, "2")
    assert first == second


@pytest.mark.parametrize("mode", ["academic", "fallback"])
def test_haversine_stand_in_is_symmetric_with_zero_diagonal(mode):
    matrix = _run_probe(mode, "7")
    n = len(matrix)
    assert n == 5
    for i in range(n):
        assert matrix[i][i] == 0.0
        for j in range(n):
            assert matrix[i][j] == matrix[j][i]
            if i != j:
                assert matrix[i][j] > 0.0


def test_synthetic_asymmetry_parameters_are_gone():
    for func in (
        TimeMatrixRepository.get_submatrix,
        DataLoader.get_submatrix,
        TimeMatrixRepository.build_haversine_matrix,
        DataLoader.build_haversine_matrix,
    ):
        names = set(inspect.signature(func).parameters)
        assert not names & {"asymmetric", "asymmetry_range", "asymmetric_haversine"}, func
