import sys
import os

# Uniride is installed via pip install -e . so we don't need sys.path hacks anymore.


import pytest


# Only these modules seed pre-2026-10-13 timestamps while testing the A06 marker/reader contract.
_LEGACY_CUTOFF_OFF_MODULES = {"test_obsolete_ga_split_variants"}


@pytest.fixture(autouse=True)
def _neutralise_legacy_cutoff(request, monkeypatch):
    """Legacy rule (DECISION_LOG A10/A11) hides rows stamped before 2026-10-13 by default.

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


@pytest.fixture(autouse=True)
def _no_include_obsolete_env(monkeypatch):
    """Opt-in env var must never leak into tests from the developer shell."""
    monkeypatch.delenv("UNIRIDE_INCLUDE_OBSOLETE", raising=False)
