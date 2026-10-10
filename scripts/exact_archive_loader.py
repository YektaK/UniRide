#!/usr/bin/env python3
"""Offline archive loader for the exact-solver wave instances (WP-E0).

Reads only archive directories under docs/paper/results (never the DB or HTTP).
Run: python scripts/exact_archive_loader.py [results_dir]
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from uniride_core.exact import VehicleTypeSpec, WaveInstance, compute_matrix_sha256  # noqa: E402

DEPOT = "D.Kampus"
REFERENCE_DIR = "week-2026-10-05-4sw5so"
# allow-list of campaign directories (trailing path parts) -> campaign key
VALID = {
    ("week-2026-10-05-4sw5so",): "4sw5so",
    ("week-2026-10-05-fleet",): "fleet",
    ("week-2026-10-05-fleet", "extra", "minivan-cap3"): "minivan-cap3",
}
# named for a clear refusal message; anything not in VALID is refused as well
INVALID = {
    ("week-2026-10-05",): "INVALID: wrong capacity 4 Sw / 10 So, superseded by week-2026-10-05-4sw5so (X01)",
    ("week-2026-10-05-fleet", "extra", "L4"): "out of scope for the exact study: not an EQ2 source (F10); same large+sedan fleet, other commit afc7208",
    ("week-2026-10-05-fleet", "extra", "minivan"): "superseded (capacity 1 Sw + 3 So), DECISION_LOG H03",
}


class CampaignRefused(Exception):
    """The directory is not one of the valid campaign archives."""


class InputRejected(Exception):
    """The archive violates an input contract (design section 3 step 2)."""


@dataclass(frozen=True)
class Campaign:
    key: str
    fleet_types: tuple
    rides: tuple
    _waves: dict  # ride -> tuple of WaveInstance
    fixed_type: object = None
    minimize_type: object = None
    scenarios: tuple = ()
    max_l: object = None  # largest integer L of the campaign (bounds q, F6)

    def waves_for(self, ride: int) -> tuple:
        return self._waves[ride]


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputRejected(f"missing archive file {path.name}") from exc


def classify(path) -> str:
    parts = Path(path).resolve().parts
    for tail, why in INVALID.items():
        if parts[-len(tail):] == tail:
            raise CampaignRefused(f"{path}: {why}")
    for tail, key in VALID.items():
        if parts[-len(tail):] == tail:
            return key
    raise CampaignRefused(f"{path}: not one of the valid campaign directories {sorted(VALID.values())}")


def _slice_sha(arcs: dict) -> str:
    payload = json.dumps(sorted([o, d, v] for (o, d), v in arcs.items()), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_matrix(path: Path):
    doc = _read(path)
    arcs: dict = {}
    for rec in doc["arcs"]:
        v = rec["duration_minutes"]
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise InputRejected(
                f"{path.name}: arc {rec['origin_code']}->{rec['destination_code']} is not an integer >= 0: {v!r}"
            )
        arcs[(rec["origin_code"], rec["destination_code"])] = v
    return doc["sha256"], arcs


def _cls(code: str) -> str:
    if code.startswith("Sw"):
        return "Sw"
    if code.startswith("So"):
        return "So"
    raise InputRejected(f"cannot classify location code {code!r}")


def _reference_waves(response: dict, name: str) -> list:
    """[(wave_id, date, direction, anchor, sorted [(occurrence, code, class)])] from a single-type response."""
    labels = response["occurrenceLabels"]
    out = []
    for job in response["jobs"]:
        occs = []
        for route in job["result"].get("routes", []):
            sw = so = 0
            for oid in route["student_ids"]:
                c = _cls(labels[oid])
                sw += c == "Sw"
                so += c == "So"
                occs.append((oid, labels[oid], c))
            if (sw, so) != (route["sw_count"], route["so_count"]):
                raise InputRejected(
                    f"{name}: class cross-check failed in {job['id']}: labels give {sw}/{so}, "
                    f"route says {route['sw_count']}/{route['so_count']}"
                )
        out.append((job["id"], job["serviceDate"], job["direction"], job["anchorMinutes"], sorted(occs)))
    return out


def _build(ref, arcs, snap_sha, slice_sha, ride, tour) -> WaveInstance:
    wave_id, date, direction, anchor, occs = ref
    codes = [DEPOT] + [c for _, c, _ in occs]
    n = len(codes)
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j or codes[i] == codes[j]:
                row.append(0)
            elif (codes[i], codes[j]) not in arcs:
                raise InputRejected(f"{wave_id}: arc {codes[i]}->{codes[j]} missing from the archived slice")
            else:
                row.append(arcs[(codes[i], codes[j])])
        matrix.append(tuple(row))
    matrix_t = tuple(matrix)
    return WaveInstance(
        wave_id=wave_id, service_date=date, direction=direction, anchor_minutes=anchor,
        max_ride_minutes=ride, max_tour_minutes=tour, depot_code=DEPOT,
        occurrence_ids=tuple(o for o, _, _ in occs), location_codes=tuple(c for _, c, _ in occs),
        classes=tuple(k for _, _, k in occs), matrix=matrix_t, matrix_sha256=compute_matrix_sha256(matrix_t),
        arc_slice_sha256=slice_sha, declared_snapshot_sha256=snap_sha,
    )


def _check_limits(doc: dict, name: str, ride: int, tour: int) -> None:
    lim = doc.get("limits", {})
    if lim.get("maxRideTimeMinutes") != ride or lim.get("maxTourMinutes") != tour:
        raise InputRejected(
            f"{name}: response limits {lim.get('maxRideTimeMinutes')}/{lim.get('maxTourMinutes')} "
            f"differ from file-name R {ride} / manifest tour_limit {tour}"
        )


_TYPE_KEYS = {"typeId", "swCapacity", "soCapacity", "cooldownMinutes", "totalCapacity", "rideLimit", "tourLimit"}


def _types_from_manifest(manifest: dict) -> tuple:
    out = []
    for t in manifest["fleet_types"]:
        extra = set(t) - _TYPE_KEYS
        if extra:
            raise InputRejected(f"fleet_types: unknown keys {sorted(extra)} (fail closed)")
        out.append(VehicleTypeSpec(t["typeId"], t["swCapacity"], t["soCapacity"], t["cooldownMinutes"],
                                   t.get("totalCapacity"), t.get("rideLimit"), t.get("tourLimit")))
    return tuple(out)


def _check_selected_routes(rdoc: dict, refs: list, name: str) -> None:
    routes = rdoc.get("scenario", {}).get("routes") or []
    if not routes:
        return
    got: dict = {}
    for r in routes:
        got.setdefault(r["jobId"], []).extend(r["occurrenceIds"])
    want = {r[0]: sorted(o for o, _, _ in r[4]) for r in refs}
    if {k: sorted(v) for k, v in got.items()} != want:
        raise InputRejected(f"{name}: occurrence ids of the selected scenario routes differ from the reference waves")


def load_campaign(path, reference_dir=None) -> Campaign:
    path = Path(path)
    key = classify(path)
    manifest = _read(path / "run_manifest.json")
    params = manifest.get("parameters", {})
    tour = params.get("tour_limit")
    if isinstance(tour, bool) or not isinstance(tour, int) or tour <= 0:
        raise InputRejected(f"{path.name}/run_manifest.json: parameters.tour_limit missing or not a positive int: {tour!r}")
    ride_limits = params.get("ride_limits")
    if key == "4sw5so":
        ref_dir = path
    elif reference_dir:
        ref_dir = Path(reference_dir)
    else:
        ref_dir = (path.parent if key == "fleet" else path.parents[2]) / REFERENCE_DIR
    waves: dict = {}
    types: tuple = ()
    for mfile in sorted(path.glob("*.matrix.json")):
        stem = mfile.name[: -len(".matrix.json")]
        date, ride = stem.split("_")[0], int(stem.split("_")[1][1:])
        ref_path = ref_dir / f"{date}_R{ride}_repeat1.response.json"
        snap_sha, arcs = _load_matrix(mfile)
        ref_resp = _read(ref_path)
        if not isinstance(ride_limits, list) or ride not in ride_limits:
            raise InputRejected(f"{mfile.name}: ride_limits {ride_limits!r} in the manifest do not contain R {ride}")
        _check_limits(ref_resp, ref_path.name, ride, tour)
        if ref_resp["matrix"]["sha256"] != snap_sha:
            raise InputRejected(f"{ref_path.name}: reference matrix sha256 differs from {mfile.name}")
        if key == "4sw5so":
            resp_files = [ref_path]
        else:
            resp_files = sorted(path.glob(f"{date}_R{ride}_*.response.json"))
        if not resp_files:
            raise InputRejected(f"{mfile.name}: no response file")
        refs = _reference_waves(ref_resp, ref_path.name)
        for rf in resp_files:
            rdoc = _read(rf)
            if rdoc["matrix"]["sha256"] != snap_sha:
                raise InputRejected(
                    f"{rf.name}: declared matrix sha256 {rdoc['matrix']['sha256'][:8]} differs from "
                    f"{mfile.name} {snap_sha[:8]}"
                )
            _check_limits(rdoc, rf.name, ride, tour)
            if key != "4sw5so":
                _check_selected_routes(rdoc, refs, rf.name)
                menu = {m["waveId"]: m["legs"] for m in rdoc["menu"]}
                if menu != {r[0]: len(r[4]) for r in refs}:
                    raise InputRejected(f"{rf.name}: menu waveIds/legs differ from the single-type archive")
        if key == "4sw5so" and not types:
            tpl = ref_resp.get("fleet", {}).get("template")
            if tpl:
                types = (VehicleTypeSpec("large", tpl["swCapacity"], tpl["soCapacity"], tpl["cooldownMinutes"], None),)
        s_sha = _slice_sha(arcs)
        waves.setdefault(ride, []).extend(_build(r, arcs, snap_sha, s_sha, ride, tour) for r in refs)
    if key != "4sw5so":
        types = _types_from_manifest(manifest)
    if not waves:
        raise InputRejected(f"{path}: no matrix files")
    scenarios = tuple(params.get("scenarios", ())) if key != "4sw5so" else ()
    ls = [int(x[1:]) for x in scenarios if len(x) > 1 and x[0] == "L" and x[1:].isdigit()]
    return Campaign(
        key, types, tuple(sorted(waves)), {r: tuple(w) for r, w in waves.items()},
        fixed_type=manifest.get("fixed_type") if key != "4sw5so" else None,
        minimize_type=manifest.get("minimize_type") if key != "4sw5so" else None,
        scenarios=scenarios, max_l=max(ls) if ls else None,
    )


def load_all_valid(results_root) -> dict:
    root = Path(results_root)
    return {key: load_campaign(root.joinpath(*tail)) for tail, key in VALID.items()}


def peak_wave_ids(waves) -> dict:
    """{date: (max legs, [wave ids tied at the max])} (decision D-B)."""
    best: dict = {}
    for w in waves:
        cur = best.get(w.service_date)
        if cur is None or w.legs > cur[0]:
            best[w.service_date] = (w.legs, [w.wave_id])
        elif w.legs == cur[0]:
            cur[1].append(w.wave_id)
    return {d: (n, sorted(ids)) for d, (n, ids) in sorted(best.items())}


def peak_waves(campaigns: dict) -> dict:
    """Peak waves per date; they must be identical for every R and campaign."""
    ref = None
    for key, camp in campaigns.items():
        for r in camp.rides:
            cur = peak_wave_ids(camp.waves_for(r))
            if ref is None:
                ref = cur
            elif cur != ref:
                raise InputRejected(f"peak waves differ in {key} R{r}: {cur} vs {ref}")
    return {d: {"legs": n, "wave_ids": ids} for d, (n, ids) in ref.items()}


def main(argv) -> int:
    root = Path(argv[1]) if len(argv) > 1 else REPO / "docs" / "paper" / "results"
    campaigns = load_all_valid(root)
    for key, camp in campaigns.items():
        for r in camp.rides:
            ws = camp.waves_for(r)
            per_date: dict = {}
            for w in ws:
                per_date[w.service_date] = per_date.get(w.service_date, 0) + 1
            print(f"{key:13s} R{r}: {len(ws)} waves, {sum(w.legs for w in ws)} legs, per date {[per_date[d] for d in sorted(per_date)]}")
        print(f"{key:13s} fleet types: {[(t.type_id, t.sw_capacity, t.so_capacity, t.total_capacity) for t in camp.fleet_types]}")
    print("peak waves (D-B), identical for all R and campaigns:")
    for d, v in peak_waves(campaigns).items():
        print(f"  {d}: {v['legs']} legs {v['wave_ids']}")
    for tail in INVALID:
        try:
            load_campaign(root.joinpath(*tail))
            print(f"ERROR: {'/'.join(tail)} was NOT refused")
            return 1
        except CampaignRefused as exc:
            print(f"refused: {'/'.join(tail)} ({exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
