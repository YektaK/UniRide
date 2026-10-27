"""CI guard for the academic analysis extra (SciPy, statsmodels; requirements-analysis.txt; DECISION_LOG D-04a).

The per-push CI job installs ``.[test]`` without the extra. Its ``pytest --collect-only`` step must still import every test module, so
no test module may import SciPy or statsmodels at module level, and the tests that need the extra at run time carry the
``requires_analysis_extra`` marker: skipped with the install command when the extra is absent, a failure when
``UNIRIDE_REQUIRE_ANALYSIS_EXTRA=1`` (the nightly job, which installs the extra and must never skip silently).

Every test here runs a small pytest in a subprocess in which ``scipy`` and ``statsmodels`` are made unimportable by a
``sys.meta_path`` finder (the development environment has them installed, so blocking is required to model CI).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TESTS = "academic_benchmark/tests"
INSTALL_COMMAND = "pip install -r requirements-analysis.txt -c academic_benchmark/jit-benchmark-constraints.txt"
STRICT_ENV = "UNIRIDE_REQUIRE_ANALYSIS_EXTRA"

# The modules that imported SciPy and statsmodels at module level, directly or through the D-05 helper module.
FORMER_IMPORTERS = (
    "test_analysis_statistics", "test_analysis_report", "test_analysis_failure_scope", "test_family_identity",
    "test_gate_d_reporting_sweep", "test_paper_report_command", "test_campaign_rebuild", "test_campaign_report_integrity",
)

BLOCKER = '''\
"""pytest plugin (-p block_analysis_libs): scipy and statsmodels cannot be imported."""
import importlib.abc
import sys

BLOCKED = ("scipy", "statsmodels")


class _Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ModuleNotFoundError(f"No module named {name!r} (blocked by the test)", name=name)
        return None


for _name in [m for m in sys.modules if m.split(".")[0] in BLOCKED]:
    del sys.modules[_name]
sys.meta_path.insert(0, _Blocker())
'''


def _pytest(tmp_path, args, *, block=True, strict=False):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "block_analysis_libs.py").write_text(BLOCKER, encoding="utf-8")
    env = dict(os.environ)
    env.pop(STRICT_ENV, None)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(plugin_dir), str(REPO), env.get("PYTHONPATH", "")) if p)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if strict:
        env[STRICT_ENV] = "1"
    command = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--tb=short", "-rsfE"]
    if block:
        command[3:3] = ["-p", "block_analysis_libs"]
    proc = subprocess.run([*command, *args], cwd=REPO, env=env, capture_output=True, text=True, timeout=600)
    return proc, proc.stdout + proc.stderr


def _summary(out):
    """The last non-empty line of pytest's output (the counts), so a test name containing a word cannot fool an assertion."""
    return [line for line in out.splitlines() if line.strip()][-1]


def test_the_blocker_really_blocks_the_libraries(tmp_path):
    """Self-check of the harness: without it the other tests would pass in an environment where the libraries import."""
    probe = tmp_path / "probe_import.py"
    probe.write_text("import sys\nsys.path.insert(0, sys.argv[1])\nimport block_analysis_libs\n"
                     "for name in ('scipy', 'statsmodels.api'):\n"
                     "    try:\n        __import__(name)\n    except ModuleNotFoundError:\n        print('blocked', name)\n"
                     "    else:\n        print('IMPORTED', name)\n", encoding="utf-8")
    (tmp_path / "plugin").mkdir()
    (tmp_path / "plugin" / "block_analysis_libs.py").write_text(BLOCKER, encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", str(probe), str(tmp_path / "plugin")], capture_output=True, text=True, timeout=120)
    assert proc.stdout.split() == ["blocked", "scipy", "blocked", "statsmodels.api"], proc.stdout + proc.stderr


def test_every_former_importer_is_collected_without_the_extra(tmp_path):
    """The defect: the CI collect step exited 2 (ModuleNotFoundError: scipy) on these eight modules."""
    paths = [f"{TESTS}/{name}.py" for name in FORMER_IMPORTERS]
    proc, out = _pytest(tmp_path, ["--collect-only", *paths])
    assert proc.returncode == 0, out[-3000:]
    per_module = Counter(line.split("::")[0] for line in out.splitlines() if "::" in line and line.startswith(TESTS))
    for name in FORMER_IMPORTERS:
        assert per_module[f"{TESTS}/{name}.py"] > 0, f"{name} contributes no collected test\n{out[-3000:]}"
    assert re.fullmatch(r"\d+ tests? collected in [\d.]+s", _summary(out)), out[-3000:]


def test_the_marker_is_registered(pytestconfig):
    assert any(line.startswith("requires_analysis_extra:") for line in pytestconfig.getini("markers"))


MARKED = f"{TESTS}/test_analysis_statistics.py::test_epsilon_squared_hand_example"  # compares with sps.kruskal: needs SciPy
UNMARKED = f"{TESTS}/test_analysis_statistics.py::test_significance_is_p_less_than_or_equal_to_alpha_everywhere"  # pure Python


def test_a_marked_test_is_skipped_with_the_install_command_when_the_extra_is_missing(tmp_path):
    proc, out = _pytest(tmp_path, [MARKED])
    assert proc.returncode == 0, out[-3000:]
    assert re.fullmatch(r"1 skipped in [\d.]+s", _summary(out)), out[-3000:]
    assert INSTALL_COMMAND in out, out[-3000:]


def test_the_strict_environment_turns_that_skip_into_a_failure_with_the_install_command(tmp_path):
    proc, out = _pytest(tmp_path, [MARKED], strict=True)
    assert proc.returncode != 0, out[-3000:]
    assert re.fullmatch(r"1 (error|failed) in [\d.]+s", _summary(out)), out[-3000:]
    assert INSTALL_COMMAND in out, out[-3000:]


def test_a_test_that_does_not_need_the_extra_is_not_marked(tmp_path):
    """The marker is applied only where the extra is needed at run time: this test passes without it, strict or not."""
    for strict in (False, True):
        proc, out = _pytest(tmp_path, [UNMARKED], strict=strict)
        assert proc.returncode == 0 and re.fullmatch(r"1 passed in [\d.]+s", _summary(out)), out[-3000:]


def test_with_the_extra_installed_strict_mode_changes_nothing(tmp_path):
    pytest.importorskip("scipy")
    pytest.importorskip("statsmodels")
    proc, out = _pytest(tmp_path, [MARKED, UNMARKED], block=False, strict=True)
    assert proc.returncode == 0 and re.fullmatch(r"2 passed in [\d.]+s", _summary(out)), out[-3000:]
