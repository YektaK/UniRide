"""Gate D D-14: packaging and import smoke (design ACADEMIC_STUDY_UNIFICATION_DESIGN.md :371, :414).

The wheel is built offline from a throwaway copy of the packaging inputs
(``pip wheel . --no-deps --no-build-isolation``), so no ``build/`` or
``*.egg-info`` folder ever appears in the repository and nothing is written
outside ``tmp_path``.

The copy never contains a real ``tsplib.db``. Instead it holds sentinel files
that a correct wheel must not pick up: a fake ``tsplib.db`` inside the package
tree and a fake ``archive`` package at the copy root. A missing build backend
is a named failure, never a skip.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from importlib.util import find_spec
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PACKAGE_DIRS = ("uniride_core", "optimizer_api", "academic_benchmark")
STUDY_PROFILES = (
    "academic_benchmark/studies/bildiri2026/study.json",
    "academic_benchmark/studies/yaem2026/study.json",
)
BUILD_TIMEOUT_SECONDS = 600
IMPORT_TIMEOUT_SECONDS = 120

IMPORT_PROBE = """\
import json
import sys

wheel_root = sys.argv[1]
sys.path.insert(0, wheel_root)

import academic_benchmark
import academic_benchmark.contracts
import academic_benchmark.studies

loaded_from = {
    name: getattr(sys.modules[name], "__file__", None)
    for name in ("academic_benchmark", "academic_benchmark.contracts", "academic_benchmark.studies")
}
archive_modules = sorted(
    name
    for name in sys.modules
    if name == "archive" or name.startswith("archive.") or "_legacy" in name
)
print(json.dumps({"loaded_from": loaded_from, "archive_modules": archive_modules}))
"""


def _require_build_backend() -> None:
    missing = [name for name in ("setuptools", "pip") if find_spec(name) is None]
    if missing:
        pytest.fail(
            "D-14 packaging smoke cannot run: build backend module(s) "
            f"{', '.join(missing)} not importable in {sys.executable}. "
            "Install the pinned build requirements (OQ-17); this test never skips.",
            pytrace=False,
        )


def _ignore_generated(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name == "__pycache__"
        or name.endswith((".pyc", ".db", ".db-wal", ".db-shm"))
        or ".db.bak" in name
        or name.endswith(".egg-info")
    }


def _build_wheel(workdir: Path) -> Path:
    source = workdir / "src"
    source.mkdir()
    shutil.copy2(REPO / "pyproject.toml", source / "pyproject.toml")
    for package in PACKAGE_DIRS:
        shutil.copytree(REPO / package, source / package, ignore=_ignore_generated)
    # Sentinels: a correct wheel contains neither of them.
    (source / "academic_benchmark" / "tsplib_data").mkdir(parents=True, exist_ok=True)
    (source / "academic_benchmark" / "tsplib_data" / "tsplib.db").write_bytes(b"sentinel")
    (source / "archive").mkdir()
    (source / "archive" / "__init__.py").write_text("SENTINEL = True\n", encoding="utf-8")

    out = workdir / "wheelhouse"
    out.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--disable-pip-version-check",
            "-w",
            str(out),
        ],
        cwd=source,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, (
        "wheel build failed\n--- stdout ---\n"
        f"{result.stdout[-4000:]}\n--- stderr ---\n{result.stderr[-4000:]}"
    )
    wheels = sorted(out.glob("uniride-*.whl"))
    assert len(wheels) == 1, f"expected exactly one uniride wheel, found {wheels}"
    return wheels[0]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    _require_build_backend()
    return _build_wheel(tmp_path_factory.mktemp("d14_wheel"))


@pytest.fixture(scope="module")
def wheel_names(built_wheel: Path) -> set[str]:
    with zipfile.ZipFile(built_wheel) as archive:
        return set(archive.namelist())


def _referenced_dataset_manifests() -> set[str]:
    refs: set[str] = set()
    for profile in STUDY_PROFILES:
        document = json.loads((REPO / profile).read_text(encoding="utf-8"))
        refs.update(document["dataset_manifest_refs"])
    return refs


def test_missing_build_backend_is_a_named_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    module = sys.modules[__name__]

    monkeypatch.setattr(module, "find_spec", lambda name: None)
    with pytest.raises(pytest.fail.Exception, match="build backend module"):
        module._require_build_backend()


def test_wheel_contains_no_archive_path_and_no_tsplib_db(wheel_names: set[str]) -> None:
    archive_paths = sorted(
        name for name in wheel_names if name.split("/")[0] == "archive" or "/archive/" in name
    )
    assert archive_paths == []
    legacy_paths = sorted(
        name
        for name in wheel_names
        if any(part.endswith("_legacy") for part in name.split("/")[:-1])
    )
    assert legacy_paths == []
    database_paths = sorted(name for name in wheel_names if ".db" in Path(name).name)
    assert database_paths == []


def test_wheel_ships_both_study_profiles(wheel_names: set[str]) -> None:
    missing = [profile for profile in STUDY_PROFILES if profile not in wheel_names]
    assert missing == []


def test_wheel_ships_every_referenced_dataset_manifest(wheel_names: set[str]) -> None:
    referenced = _referenced_dataset_manifests()
    assert referenced, "study profiles reference no dataset manifests"
    missing = sorted(ref for ref in referenced if ref not in wheel_names)
    assert missing == []


def test_wheel_ships_no_unreferenced_profile_or_dataset_files(wheel_names: set[str]) -> None:
    """Inclusion is limited to what design :371 names: profiles and their manifests."""
    shipped_studies = {
        name
        for name in wheel_names
        if name.startswith("academic_benchmark/studies/") and name.endswith(".json")
    }
    assert shipped_studies == set(STUDY_PROFILES)
    shipped_datasets = {
        name for name in wheel_names if name.startswith("academic_benchmark/datasets/")
    }
    assert shipped_datasets == _referenced_dataset_manifests()


def test_wheel_imports_studies_and_contracts_without_archive_modules(
    built_wheel: Path, tmp_path: Path
) -> None:
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(built_wheel) as archive:
        archive.extractall(extracted)
    probe = tmp_path / "import_probe.py"
    probe.write_text(IMPORT_PROBE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", str(probe), str(extracted)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=IMPORT_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, f"import probe failed\n{result.stderr[-4000:]}"
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["archive_modules"] == []
    for module_name, location in report["loaded_from"].items():
        assert location is not None, module_name
        assert Path(location).resolve().is_relative_to(extracted.resolve()), (
            f"{module_name} was imported from {location}, not from the wheel"
        )
