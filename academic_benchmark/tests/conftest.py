import sys
import os

# Uniride is installed via pip install -e . so we don't need sys.path hacks anymore.


import pytest


@pytest.fixture(autouse=True)
def _neutralise_legacy_cutoff(monkeypatch):
    """Legacy rule (DECISION_LOG A10/A11): rows stamped before 2026-10-13 are hidden by default.

    Pre-existing fixtures seed older timestamps and test other behaviour, so the suite runs with
    the cutoff disabled; test_legacy_obsolete.py restores the real cutoff for itself.
    """
    import sys

    for name in ("academic_benchmark.obsolete_results", "obsolete_results"):
        module = sys.modules.get(name)
        if module is not None:
            monkeypatch.setattr(module, "LEGACY_CUTOFF", "0001-01-01", raising=False)
    from academic_benchmark import obsolete_results

    monkeypatch.setattr(obsolete_results, "LEGACY_CUTOFF", "0001-01-01")
