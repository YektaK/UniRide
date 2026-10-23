"""D-04a: the pinned analysis environment (SciPy plus statsmodels, OQ-7 b; A18).

The pin file ``requirements-analysis.txt`` is an academic-only extra (pattern of ``requirements-paper.txt``); the
production requirements never name these libraries. The run environment records the library through
``statistics_library_identifier`` (``EnvironmentV1.statistics_library``); a missing or wrong-version library raises a
named ``AnalysisEnvironmentError`` instead of a bare ``ImportError`` trace."""
from __future__ import annotations

import ast
import re
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

from academic_benchmark.analysis import environment as env
from academic_benchmark.contracts.run import EnvironmentV1

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "requirements-analysis.txt"
CONSTRAINTS = ROOT / "academic_benchmark" / "jit-benchmark-constraints.txt"
_PIN = re.compile(r"^([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.\-+!]+)$")


def _pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _PIN.match(line)
        assert match, f"{path.name}: not an exact pin: {line!r}"
        name = match.group(1).lower().replace("_", "-")
        assert name not in pins, f"{path.name}: duplicate pin for {name}"
        pins[name] = match.group(2)
    return pins


def _canonical(name: str) -> str:
    return name.lower().replace("_", "-")


# ------------------------------------------------------------------------------------------------ the pin file
def test_requirements_file_pins_every_distribution_exactly_and_equals_installed():
    pins = _pins(REQUIREMENTS)
    assert pins, "requirements-analysis.txt has no pins"
    for name, version in pins.items():
        assert metadata.version(name) == version, f"{name}: pinned {version}, installed {metadata.version(name)}"


def test_requirements_file_contains_the_decided_libraries():
    pins = _pins(REQUIREMENTS)
    # OQ-7 b (SciPy + statsmodels) and OQ-17 a (setuptools for the D-14 packaging smoke), A18.
    assert {"scipy", "statsmodels", "setuptools"} <= set(pins)
    # statsmodels' dependencies are pinned explicitly (the resolver otherwise picks a release candidate).
    assert {"patsy", "formulaic", "interface-meta", "narwhals", "wrapt"} <= set(pins)


def test_module_constant_and_requirements_file_agree_on_the_statistics_libraries():
    pins = _pins(REQUIREMENTS)
    assert dict(env.PINNED_STATISTICS_LIBRARIES) == {n: pins[n] for n in ("scipy", "statsmodels")}


def test_numpy_stays_at_the_jit_pin_and_is_not_repinned_here():
    jit = _pins(CONSTRAINTS)
    assert "numpy" not in _pins(REQUIREMENTS), "numpy is held by jit-benchmark-constraints.txt only"
    for name in ("numpy", "numba", "llvmlite"):
        assert metadata.version(name) == jit[name], f"{name} drifted from the JIT constraint"


def test_requirements_file_is_documented_as_academic_only_and_install_with_constraints():
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "NOT an operational" in text
    assert "jit-benchmark-constraints.txt" in text


def test_production_requirements_do_not_name_the_analysis_libraries():
    forbidden = {"scipy", "statsmodels", "patsy", "formulaic", "interface-meta", "narwhals", "wrapt"}
    for path in (ROOT / "optimizer_api" / "requirements.txt", ROOT / "optimizer_api" / "requirements-benchmark.txt"):
        names = {_canonical(re.split(r"[=<>~!\[ ;]", line.strip(), maxsplit=1)[0])
                 for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.lstrip().startswith(("#", "-"))}
        assert not (names & forbidden), f"{path.name} must not depend on {sorted(names & forbidden)}"
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = list(data["project"]["dependencies"])
    for extra in data["project"].get("optional-dependencies", {}).values():
        declared.extend(extra)
    declared_names = {_canonical(re.split(r"[=<>~!\[ ;]", item.strip(), maxsplit=1)[0]) for item in declared}
    assert not (declared_names & forbidden)


# ------------------------------------------------------------------------------------- the recorded identifier
def test_identifier_names_library_and_installed_version_for_the_environment_record():
    identifier = env.statistics_library_identifier()
    assert identifier == (f"scipy=={metadata.version('scipy')}+statsmodels=={metadata.version('statsmodels')}")
    record = EnvironmentV1(python="3", operating_system="x", cpu="y", numpy=metadata.version("numpy"),
                           numba=metadata.version("numba"), llvmlite=metadata.version("llvmlite"),
                           statistics_library=identifier)
    assert record.statistics_library == identifier
    assert identifier != "none"


def test_installed_versions_equal_the_pins():
    assert env.installed_statistics_versions() == dict(env.PINNED_STATISTICS_LIBRARIES)
    env.require_analysis_environment()  # does not raise


def test_missing_library_gives_a_named_error_not_an_import_error(monkeypatch):
    def not_installed(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(env, "_distribution_version", not_installed)
    with pytest.raises(env.AnalysisEnvironmentError) as caught:
        env.require_analysis_environment()
    message = str(caught.value)
    assert "scipy" in message and "requirements-analysis.txt" in message
    assert not isinstance(caught.value, ImportError)
    with pytest.raises(env.AnalysisEnvironmentError):
        env.statistics_library_identifier()


def test_installed_but_not_importable_library_gives_a_named_error(monkeypatch):
    def broken(name: str):
        raise ImportError(f"broken {name}")

    monkeypatch.setattr(env, "_import_module", broken)
    with pytest.raises(env.AnalysisEnvironmentError, match="statsmodels|scipy"):
        env.require_analysis_environment()


def test_wrong_version_gives_a_named_error_that_shows_both_versions(monkeypatch):
    real = env._distribution_version
    monkeypatch.setattr(env, "_distribution_version", lambda name: "0.0.1" if name == "statsmodels" else real(name))
    with pytest.raises(env.AnalysisEnvironmentError) as caught:
        env.require_analysis_environment()
    message = str(caught.value)
    assert "statsmodels" in message and "0.0.1" in message and env.PINNED_STATISTICS_LIBRARIES["statsmodels"] in message


def test_environment_module_imports_no_statistics_library_at_module_level():
    tree = ast.parse(Path(env.__file__).read_text(encoding="utf-8"))
    top_level = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".")[0] for node in top_level if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in top_level if isinstance(node, ast.ImportFrom) and node.module}
    assert not ({"scipy", "statsmodels"} & imported), "importing the analysis layer must not require the libraries"


# ------------------------------------------------------------------- what the libraries do NOT provide (for D-05)
def _public_names(module_name: str) -> list[str]:
    import importlib
    return [n for n in dir(importlib.import_module(module_name)) if not n.startswith("_")]


def test_effect_sizes_epsilon_squared_rank_biserial_and_kendalls_w_are_not_provided_by_the_pinned_libraries():
    """A18 / plan OQ-7: these three are local code in D-05. Fails after an upgrade that adds one, which is the cue to
    reconsider (the pins make that a deliberate act)."""
    import importlib
    import pkgutil

    import statsmodels.stats
    modules = ["scipy.stats", "scipy.stats.contingency"]
    modules += [m.name for m in pkgutil.walk_packages(statsmodels.stats.__path__, "statsmodels.stats.")
                if ".tests" not in m.name]
    pattern = re.compile(r"rank_?biserial|epsilon|kendall_?w|kendalls_?w|concordance_?coef|vargha|delaney|cliff",
                         re.IGNORECASE)
    hits: list[str] = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception:
            continue
        hits += [f"{name}.{n}" for n in _public_names(name) if pattern.search(n)]
    assert hits == []
    # Kendall's tau (a correlation, not the coefficient of concordance W) is the only Kendall name SciPy has.
    assert "kendalltau" in _public_names("scipy.stats")
    assert "kendallw" not in "".join(_public_names("scipy.stats")).lower()


def test_a12_is_available_only_as_the_probability_of_superiority_and_matches_the_u_statistic():
    """Vargha-Delaney A12 = P(X > Y) + 0.5 P(X = Y) = U1 / (n1 n2). statsmodels exposes it as ``prob1`` of
    ``rank_compare_2indep`` and SciPy exposes U; D-05 may use either as a cross-check of its own A12."""
    import numpy as np
    from scipy import stats
    from statsmodels.stats.nonparametric import rank_compare_2indep

    x = np.array([1.0, 2.0, 3.0, 4.0, 9.0])
    y = np.array([2.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    u1 = stats.mannwhitneyu(x, y).statistic
    assert rank_compare_2indep(x, y).prob1 == pytest.approx(u1 / (len(x) * len(y)))
    # Direct definition (ties count one half):
    direct = sum((a > b) + 0.5 * (a == b) for a in x for b in y) / (len(x) * len(y))
    assert direct == pytest.approx(u1 / (len(x) * len(y)))
