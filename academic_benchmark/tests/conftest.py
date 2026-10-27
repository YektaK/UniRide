import importlib
import sys
import os

# Uniride is installed via pip install -e . so we don't need sys.path hacks anymore.


import pytest


# Only these modules seed pre-2026-10-13 timestamps while testing the A06 marker/reader contract.
_LEGACY_CUTOFF_OFF_MODULES = {"test_obsolete_ga_split_variants"}


@pytest.fixture(autouse=True)
def _neutralise_legacy_cutoff(request, monkeypatch):
    """Legacy rule (DECISION_LOG A13) classifies rows stamped before 2026-10-13 by default.

    The A06 test module seeds 2026-10-0x rows to test other behaviour, so the cutoff is disabled
    for it alone; every other module, including the legacy tests, runs with the real cutoff.
    """
    if request.module.__name__.rsplit(".", 1)[-1] not in _LEGACY_CUTOFF_OFF_MODULES:
        return
    import sys

    from academic_benchmark import obsolete_results

    for module in (sys.modules.get("obsolete_results"), obsolete_results):
        if module is not None:
            monkeypatch.setattr(module, "LEGACY_CUTOFF", "0001-01-01", raising=False)


ANALYSIS_EXTRA_INSTALL = "pip install -r requirements-analysis.txt -c academic_benchmark/jit-benchmark-constraints.txt"
STRICT_ANALYSIS_EXTRA_ENV = "UNIRIDE_REQUIRE_ANALYSIS_EXTRA"


def analysis_extra_missing():
    """The reason the academic analysis extra (SciPy, statsmodels) cannot be imported, or None when it can.

    Only a genuine ImportError counts as absent; a wrong version is not hidden here (``require_analysis_environment`` and
    its own tests report it), and a broken install fails the test instead of skipping it."""
    for name in ("scipy", "statsmodels"):
        try:
            importlib.import_module(name)
        except ImportError as exc:
            return f"{name} cannot be imported ({exc})"
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """``requires_analysis_extra``: skipped WITH a reason when the extra is absent (per-push CI installs ``.[test]`` only).

    Same pattern as ``requires_highspy`` (marker plus a skip with the reason, never silent), applied through a setup hook that
    runs before any fixture, because the marker covers whole modules and some of their module fixtures already need the extra.
    With ``UNIRIDE_REQUIRE_ANALYSIS_EXTRA=1`` (the nightly job, which installs the extra) the absence is a failure, so a broken
    extra can never turn the analysis tests into silent skips."""
    if item.get_closest_marker("requires_analysis_extra") is None:
        return
    missing = analysis_extra_missing()
    if missing is None:
        return
    message = f"the academic analysis extra is not available: {missing}; install it with: {ANALYSIS_EXTRA_INSTALL}"
    if os.environ.get(STRICT_ANALYSIS_EXTRA_ENV) == "1":
        pytest.fail(f"{message} ({STRICT_ANALYSIS_EXTRA_ENV}=1: absence is a failure, not a skip)", pytrace=False)
    pytest.skip(message)


@pytest.fixture(autouse=True)
def _no_include_obsolete_env(monkeypatch):
    """Opt-in env var must never leak into tests from the developer shell."""
    monkeypatch.delenv("UNIRIDE_INCLUDE_OBSOLETE", raising=False)
