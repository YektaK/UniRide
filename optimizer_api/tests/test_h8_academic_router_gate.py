"""H8 (audit 2026-10-01): the benchmark/academic router is mounted only when
UNIRIDE_ACADEMIC_PROCESS=1.

Each check runs in a fresh interpreter, so modules imported by earlier tests in
this pytest process cannot pollute sys.modules, and the developer's
optimizer_api/.env is neutralised (it may legitimately set the flag locally).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

ACADEMIC_MODULES = (
    "routers.benchmark",
    "benchmark_runner",
    "benchmark_state",
    "optimizer_api.routers.benchmark",
    "optimizer_api.benchmark_runner",
    "optimizer_api.benchmark_state",
)

_DOTENV_OFF = "dotenv.load_dotenv = lambda *a, **k: False  # never read optimizer_api/.env"

_PROBE = """
import json, sys
import dotenv
__DOTENV__
import optimizer_api.main as m

paths = sorted(m.app.openapi()["paths"])  # FastAPI wraps included routers; openapi lists real paths
print(json.dumps({
    "benchmark_paths": [p for p in paths if "/benchmark" in p or "/academic" in p],
    "other_paths": [p for p in paths if p.startswith("/api/v1/") and "/benchmark" not in p],
    "loaded": sorted(n for n in __MODULES__ if n in sys.modules),
}))
"""


def _script(dotenv_line: str = _DOTENV_OFF) -> str:
    return _PROBE.replace("__DOTENV__", dotenv_line).replace("__MODULES__", repr(ACADEMIC_MODULES))


def _run(script: str, flag: str | None) -> dict:
    # PYTHON_DOTENV_DISABLED (set in CI) would turn load_dotenv into a no-op, hiding the .env case.
    env = {k: v for k, v in os.environ.items() if k not in ("UNIRIDE_ACADEMIC_PROCESS", "PYTHON_DOTENV_DISABLED")}
    env.update({
        "INTERNAL_API_KEY": "h8-test-key",
        "APP_ENV": "development",
        "PYTHONPATH": os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "optimizer_api")]),
        "PYTHON_BASIC_REPL": "1",
    })
    env.pop("UNIRIDE_DISABLE_AUTH", None)
    if flag is not None:
        env["UNIRIDE_ACADEMIC_PROCESS"] = flag
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=240,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("flag", [None, "", "0", "true", "yes", "2", " 1"])
def test_flag_unset_or_not_exactly_1_mounts_no_academic_surface(flag):
    probe = _run(_script(), flag)
    assert probe["benchmark_paths"] == []
    assert probe["loaded"] == [], "academic modules must not even be imported"
    # The production surface is untouched.
    assert "/api/v1/optimize" in probe["other_paths"]


def test_flag_1_mounts_the_benchmark_router_as_before():
    probe = _run(_script(), "1")
    paths = probe["benchmark_paths"]
    for expected in (
        "/api/v1/benchmark/run",
        "/api/v1/benchmark/status",
        "/api/v1/benchmark/academic/leaderboard",
        "/api/v1/benchmark/problems",
    ):
        assert expected in paths
    assert probe["loaded"], "the academic router modules are imported when the flag is 1"
    assert "/api/v1/optimize" in probe["other_paths"]


def test_flag_is_honoured_when_it_comes_from_dotenv(tmp_path):
    """The flag must be read after load_dotenv (audit M22), so .env can set it."""
    env_file = tmp_path / "academic.env"
    env_file.write_text("UNIRIDE_ACADEMIC_PROCESS=1\n", encoding="utf-8")
    line = (
        "_real = dotenv.load_dotenv\n"
        f"dotenv.load_dotenv = lambda *a, **k: _real(dotenv_path={str(env_file)!r}, override=False)"
    )
    probe = _run(_script(line), None)
    assert "/api/v1/benchmark/run" in probe["benchmark_paths"]
