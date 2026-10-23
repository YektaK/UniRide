"""Pinned statistics environment of the analysis layer (Gate D, D-04a).

The statistics libraries (SciPy, statsmodels) are an academic-only extra pinned in ``requirements-analysis.txt``; they are
never an operational dependency. This module imports neither at module level, so the rest of the analysis layer (identity,
manifests, gap columns) keeps working in an environment without them. ``require_analysis_environment`` is the guard that
the statistics service calls first: a missing, unimportable or wrong-version library raises ``AnalysisEnvironmentError``
with the install command instead of a bare ``ImportError`` trace. ``statistics_library_identifier`` is the value for
``EnvironmentV1.statistics_library`` in every run manifest that comes from an environment with the libraries."""
from __future__ import annotations

import importlib
from importlib import metadata
from types import MappingProxyType
from typing import Mapping

# Keep equal to the scipy and statsmodels lines of requirements-analysis.txt (test_analysis_environment.py checks it).
PINNED_STATISTICS_LIBRARIES: Mapping[str, str] = MappingProxyType({"scipy": "1.18.1", "statsmodels": "0.15.0"})

INSTALL_HINT = ("pip install -r requirements-analysis.txt -c academic_benchmark/jit-benchmark-constraints.txt "
                "(academic extra, not an operational dependency)")


class AnalysisEnvironmentError(RuntimeError):
    """The pinned statistics environment is missing, broken or at the wrong version."""


def _distribution_version(name: str) -> str:
    return metadata.version(name)


def _import_module(name: str):
    return importlib.import_module(name)


def installed_statistics_versions() -> dict[str, str]:
    """Installed version of each pinned statistics library; raises ``AnalysisEnvironmentError`` if one is absent."""
    versions: dict[str, str] = {}
    for name in PINNED_STATISTICS_LIBRARIES:
        try:
            versions[name] = _distribution_version(name)
        except metadata.PackageNotFoundError as exc:
            raise AnalysisEnvironmentError(
                f"analysis library '{name}' is not installed (pin {PINNED_STATISTICS_LIBRARIES[name]}); "
                f"install it with: {INSTALL_HINT}") from exc
    return versions


def require_analysis_environment() -> dict[str, str]:
    """Guard for the statistics service: every pinned library is installed, importable and at its pinned version.

    Returns the installed versions."""
    versions = installed_statistics_versions()
    wrong = [f"{name} {versions[name]} (pinned {pin})" for name, pin in PINNED_STATISTICS_LIBRARIES.items()
             if versions[name] != pin]
    if wrong:
        raise AnalysisEnvironmentError(
            "analysis library version differs from the pin: " + "; ".join(wrong) + f". Reinstall with: {INSTALL_HINT}")
    for name in PINNED_STATISTICS_LIBRARIES:
        try:
            _import_module(name)
        except ImportError as exc:
            raise AnalysisEnvironmentError(
                f"analysis library '{name}' {versions[name]} is installed but cannot be imported ({exc}); "
                f"reinstall with: {INSTALL_HINT}") from exc
    return versions


def statistics_library_identifier() -> str:
    """Value for ``EnvironmentV1.statistics_library``: the pinned libraries with their installed versions, for example
    ``scipy==1.18.1+statsmodels==0.15.0``. Raises ``AnalysisEnvironmentError`` when the environment is not the pinned one."""
    versions = require_analysis_environment()
    return "+".join(f"{name}=={versions[name]}" for name in PINNED_STATISTICS_LIBRARIES)
