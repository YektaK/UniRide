"""Test of scripts/capture_fleet_solver_config.py against the values the WP-E10 preflight pins.

Run: python -m pytest scripts/test_capture_fleet_solver_config.py   (project venv)
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import capture_fleet_solver_config as C  # noqa: E402


REPO = os.path.dirname(HERE)


def run_script():
    # the session wrapper puts the run worktree first on PYTHONPATH; without it an editable install of another checkout may win
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "capture_fleet_solver_config.py")],
        capture_output=True, text=True, timeout=120, check=True, cwd=REPO, env=dict(os.environ, PYTHONPATH=REPO),
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_prints_the_manifest_configuration_as_one_json_line():
    value = run_script()
    assert value["ga"]["seed"] == 42 and value["hf"]["seed"] == 42
    assert value["ga"]["config"]["population_size"] == 50
    assert value["ga"]["config"]["local_search_type"] == "hybrid"
    assert value["hf"]["config"] == value["ga"]["config"]
    assert value["cp"] == {"version": "9.15.6755", "seed": 20261008, "workers": 1}
    for name in ("uniride_core", "optimizer_api", "academic_benchmark"):
        assert value["python_provenance"][name].startswith(name + "/"), value["python_provenance"]  # repo-relative, never absolute
    policy = value["compute_policy"]
    assert policy["profile_id"] == "production-conservative-v1"
    assert policy["rate_limit_requests"] == 30 and policy["rate_limit_window_seconds"] == 60  # defaults without the session env


def test_compute_policy_follows_the_environment_and_refuses_values_above_the_ceiling():
    env = dict(os.environ, UNIRIDE_RATE_LIMIT_WINDOW_SECONDS="1", PYTHONPATH=REPO)
    out = subprocess.run([sys.executable, os.path.join(HERE, "capture_fleet_solver_config.py")], capture_output=True, text=True, timeout=120, check=True, env=env, cwd=os.path.dirname(HERE))
    assert json.loads(out.stdout.strip().splitlines()[-1])["compute_policy"]["rate_limit_window_seconds"] == 1
    bad = subprocess.run([sys.executable, os.path.join(HERE, "capture_fleet_solver_config.py")], capture_output=True, text=True, timeout=120, env=dict(os.environ, UNIRIDE_RATE_LIMIT_REQUESTS="31", PYTHONPATH=REPO), cwd=REPO)
    assert bad.returncode != 0  # the hard ceiling of the requests per window is 30: it cannot be raised


def test_provenance_is_repo_relative_and_refuses_a_module_outside_the_repository():
    inside = {"uniride_core": "/r/uniride_core/__init__.py", "optimizer_api": "/r/optimizer_api/__init__.py", "academic_benchmark": "/r/academic_benchmark/__init__.py"}
    assert C.python_provenance("/r", resolve=lambda name: inside[name]) == {
        "uniride_core": "uniride_core/__init__.py", "optimizer_api": "optimizer_api/__init__.py", "academic_benchmark": "academic_benchmark/__init__.py"}
    outside = dict(inside, uniride_core="/main/uniride_core/__init__.py")
    with pytest.raises(RuntimeError, match="uniride_core.*outside"):
        C.python_provenance("/r", resolve=lambda name: outside[name])
    with pytest.raises(RuntimeError, match="optimizer_api"):
        C.python_provenance("/r", resolve=lambda name: None if name == "optimizer_api" else inside[name])


def test_num_workers_is_read_from_the_source_and_unknown_when_not_unique():
    import tempfile
    import importlib.util

    def module_with(text):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            spec = importlib.util.spec_from_file_location("m_tmp", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            import linecache
            linecache.checkcache(path)
            return C.num_workers(module)

    assert module_with("class S:\n    def f(self, solver):\n        solver.parameters.num_workers = 4\n") == 4
    assert module_with("x = 1\n") is None
    assert module_with("def f(s):\n    s.parameters.num_workers = 1\n    s.parameters.num_workers = 8\n") is None
