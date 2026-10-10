"""WP-E0 of docs/designs/EXACT_SOLVER_AMPL_DESIGN.md: wave contract, offline loader, peak waves, guards."""
from __future__ import annotations

import ast
import dataclasses
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
SW5SO = RESULTS / "week-2026-10-05-4sw5so"


def _load_loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader", REPO / "scripts" / "exact_archive_loader.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def loader():
    return _load_loader()


@pytest.fixture(scope="module")
def all_campaigns(loader):
    return loader.load_all_valid(RESULTS)


def _tiny(**over):
    from uniride_core.exact import WaveInstance, compute_matrix_sha256

    matrix = ((0, 5, 6), (4, 0, 3), (7, 2, 0))
    base = dict(
        wave_id="2026-10-05:pickup:525", service_date="2026-10-05", direction="pickup", anchor_minutes=525,
        max_ride_minutes=50, max_tour_minutes=150, depot_code="D.Kampus",
        occurrence_ids=("a~1", "b~1"), location_codes=("Sw1", "So1"), classes=("Sw", "So"),
        matrix=matrix, matrix_sha256=compute_matrix_sha256(matrix),
        arc_slice_sha256="s" * 64, declared_snapshot_sha256="d" * 64,
    )
    base.update(over)
    return WaveInstance(**base)


# ---------- contract ----------
def test_wave_instance_is_frozen_and_valid():
    inst = _tiny()
    assert inst.legs == 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        inst.direction = "dropoff"  # type: ignore[misc]


@pytest.mark.parametrize("bad", [-1, 2.5, 3.0, True, None])
def test_wave_instance_rejects_non_integer_or_negative_arc(bad):
    m = [list(r) for r in ((0, 5, 6), (4, 0, 3), (7, 2, 0))]
    m[0][1] = bad
    m = tuple(tuple(r) for r in m)
    # the hash is computed over a valid twin so only the arc check can fire
    from uniride_core.exact import compute_matrix_sha256

    with pytest.raises(ValueError):
        _tiny(matrix=m, matrix_sha256=compute_matrix_sha256(((0, 5, 6), (4, 0, 3), (7, 2, 0))))


def test_wave_instance_rejects_wrong_shape_class_and_hash():
    with pytest.raises(ValueError):
        _tiny(matrix=((0, 1), (1, 0)))
    with pytest.raises(ValueError):
        _tiny(classes=("Sw", "Xx"))
    with pytest.raises(ValueError):
        _tiny(matrix_sha256="0" * 64)


def test_vehicle_type_spec_and_exact_result_are_frozen():
    from uniride_core.exact import ExactResult, VehicleTypeSpec

    v = VehicleTypeSpec(type_id="large", sw_capacity=4, so_capacity=5, cooldown_minutes=10, total_capacity=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.sw_capacity = 1  # type: ignore[misc]
    r = ExactResult(wave_id="w", status="not_run", routes=(), route_count=None, total_cost=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.status = "optimal"  # type: ignore[misc]


def test_matrix_sha256_is_stable_and_sensitive():
    from uniride_core.exact import compute_matrix_sha256

    a = compute_matrix_sha256(((0, 1), (2, 0)))
    assert a == compute_matrix_sha256(((0, 1), (2, 0)))
    assert a != compute_matrix_sha256(((0, 2), (1, 0)))
    assert len(a) == 64


# ---------- guards (design section 2) ----------
def test_importing_exact_does_not_import_amplpy():
    code = "import sys, uniride_core.exact; sys.exit(1 if 'amplpy' in sys.modules else 0)"
    res = subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            yield base
            yield from (f"{base}.{a.name}" for a in node.names)


def test_production_code_never_imports_uniride_core_exact():
    assert (REPO / "uniride_core" / "exact" / "wave_instance.py").exists()  # the guard is not vacuous
    offenders = []
    for top in ("optimizer_api", "src"):
        for path in (REPO / top).rglob("*.py"):
            for name in _imports(path):
                if name == "uniride_core.exact" or name.startswith("uniride_core.exact."):
                    offenders.append(f"{path.relative_to(REPO)} imports {name}")
    assert offenders == []


def test_exact_is_not_in_production_registry():
    from uniride_core.algorithms.registry import alias_map, list_algorithm_names

    names = [n.lower() for n in list_algorithm_names()] + [k.lower() for k in alias_map()]
    assert not [n for n in names if "exact" in n]
    registry_src = (REPO / "uniride_core" / "algorithms" / "registry.py").read_text(encoding="utf-8")
    assert ".exact" not in registry_src


# ---------- loader: refusal ----------
@pytest.mark.parametrize("rel", ["week-2026-10-05", "week-2026-10-05-fleet/extra/L4", "week-2026-10-05-fleet/extra/minivan"])
def test_loader_refuses_invalid_campaigns(loader, rel):
    with pytest.raises(loader.CampaignRefused):
        loader.load_campaign(RESULTS / rel)


def test_loader_refuses_unknown_directory(loader, tmp_path):
    with pytest.raises(loader.CampaignRefused):
        loader.load_campaign(tmp_path)


def test_loader_is_offline():
    names = {n.split(".")[0] for n in _imports(REPO / "scripts" / "exact_archive_loader.py")}
    banned = {"requests", "urllib", "http", "supabase", "sqlite3", "socket", "httpx", "amplpy"}
    assert not (names & banned), names & banned


# ---------- loader: acceptance ----------
def test_all_valid_campaigns_loaded_with_archived_counts(all_campaigns):
    assert set(all_campaigns) == {"4sw5so", "fleet", "minivan-cap3"}
    for camp in all_campaigns.values():
        assert sorted(camp.rides) == [50, 60, 70, 90]
        for r in (50, 60, 70, 90):
            waves = camp.waves_for(r)
            assert len(waves) == 57
            assert sum(w.legs for w in waves) == 226
            per_date: dict[str, int] = {}
            for w in waves:
                per_date[w.service_date] = per_date.get(w.service_date, 0) + 1
            assert [per_date[d] for d in sorted(per_date)] == [12, 13, 11, 13, 8]


def test_fleet_types_follow_the_manifests(all_campaigns):
    t = {x.type_id: x for x in all_campaigns["fleet"].fleet_types}
    assert (t["large"].sw_capacity, t["large"].so_capacity) == (4, 5)
    assert (t["sedan"].sw_capacity, t["sedan"].so_capacity) == (0, 4)
    m = {x.type_id: x for x in all_campaigns["minivan-cap3"].fleet_types}
    assert (m["minivan"].sw_capacity, m["minivan"].so_capacity, m["minivan"].total_capacity) == (1, 3, 3)
    assert len(all_campaigns["4sw5so"].fleet_types) == 1


def test_matrix_properties_and_separate_slice_hash(all_campaigns):
    w = all_campaigns["4sw5so"].waves_for(50)[0]
    n = w.legs + 1
    assert len(w.matrix) == n and all(len(r) == n for r in w.matrix)
    assert all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for r in w.matrix for x in r)
    assert all(w.matrix[i][i] == 0 for i in range(n))
    assert w.declared_snapshot_sha256.startswith("bfb2dd85")
    assert w.arc_slice_sha256 != w.declared_snapshot_sha256  # the slice is never claimed to hash to the snapshot sha


def test_peak_waves_are_the_five_0845_pickup_waves(loader, all_campaigns):
    expected = {
        "2026-10-05": (20, ["2026-10-05:pickup:525"]),
        "2026-10-06": (11, ["2026-10-06:pickup:525"]),
        "2026-10-07": (11, ["2026-10-07:pickup:525"]),
        "2026-10-08": (10, ["2026-10-08:pickup:525"]),
        "2026-10-09": (13, ["2026-10-09:pickup:525"]),
    }
    peaks = loader.peak_waves(all_campaigns)
    assert {d: (v["legs"], v["wave_ids"]) for d, v in peaks.items()} == expected


def test_peak_waves_include_all_ties(loader):
    class W:
        def __init__(self, d, i, legs):
            self.service_date, self.wave_id, self.legs = d, i, legs

    tied = loader.peak_wave_ids([W("d", "x", 5), W("d", "y", 5), W("d", "z", 2)])
    assert tied == {"d": (5, ["x", "y"])}


# ---------- loader: integrity checks on tampered copies ----------
def _copy_4sw5so(tmp_path):
    dst = tmp_path / "results" / "week-2026-10-05-4sw5so"
    dst.mkdir(parents=True)
    for suf in ("matrix", "response"):
        shutil.copy(SW5SO / f"2026-10-05_R50_repeat1.{suf}.json", dst)
    shutil.copy(SW5SO / "run_manifest.json", dst)
    return dst


def test_untouched_copy_loads(loader, tmp_path):
    camp = loader.load_campaign(_copy_4sw5so(tmp_path))
    assert sum(w.legs for w in camp.waves_for(50)) > 0


def test_sha_mismatch_between_matrix_and_response_is_rejected(loader, tmp_path):
    dst = _copy_4sw5so(tmp_path)
    p = dst / "2026-10-05_R50_repeat1.response.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["matrix"]["sha256"] = "0" * 64
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(loader.InputRejected, match="sha256"):
        loader.load_campaign(dst)


@pytest.mark.parametrize("bad", [-3, 2.5])
def test_bad_arc_is_rejected(loader, tmp_path, bad):
    dst = _copy_4sw5so(tmp_path)
    p = dst / "2026-10-05_R50_repeat1.matrix.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["arcs"][0]["duration_minutes"] = bad
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(loader.InputRejected, match="arc"):
        loader.load_campaign(dst)


def test_class_cross_check_mismatch_is_rejected(loader, tmp_path):
    dst = _copy_4sw5so(tmp_path)
    p = dst / "2026-10-05_R50_repeat1.response.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    route = doc["jobs"][0]["result"]["routes"][0]
    route["sw_count"] = route["sw_count"] + 1
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(loader.InputRejected, match="class"):
        loader.load_campaign(dst)
