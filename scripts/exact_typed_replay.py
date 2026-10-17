#!/usr/bin/env python3
"""WP-E4a part 1: replay of the WP-E10 day selections (acceptance gate of the Python interval port).

For one typed fleet archive (``week-2026-10-05-fleet-rerun-*``) and every (date, R, L):

1. rebuild the ``/internal/fleet-selection`` request from the archived ``menu_options.json`` routes with
   ``uniride_core.planning.fleet_selection_request`` (the port of ``fleet-scenario-run.ts``) and require it
   equal to ``selection_exchange.request`` field by field;
2. apply the router's checks (``optimizer_api.routers.fleet_selection.FleetSelectionRequest``, the policy
   time limit) and call ``solve_day_selection`` with the router's effective parameters;
3. compare the result with ``selection_exchange.response``: ``status``, ``cars``, ``large_peak``,
   ``car_minutes``, ``total_minutes`` and the ``selection`` with its labels.

Offline: reads only the archive directory (never the DB or HTTP). A mismatch is reported, never tolerated or
special-cased. Labels: ``match``, ``match_not_optimal`` (identical, CP-SAT not optimal in the archive and the
replay), ``request_mismatch``, ``response_mismatch``, ``archived_http_error``, ``router_refused``.

Run: python scripts/exact_typed_replay.py <fleet archive dir>
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO / "optimizer_api"), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from uniride_core.planning import fleet_selection_request as fsr  # noqa: E402

COMPARED_FIELDS = ("status", "cars", "large_peak", "car_minutes", "total_minutes")
MATCH_LABELS = ("match", "match_not_optimal")


def _load_loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader", REPO / "scripts" / "exact_archive_loader.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("exact_archive_loader", mod)
    spec.loader.exec_module(mod)
    return sys.modules["exact_archive_loader"]


loader = _load_loader()


@dataclass(frozen=True)
class Fleet:
    path: Path
    name: str
    campaign: object
    manifest: dict
    fixed: fsr.TypeLimits
    minimise: fsr.TypeLimits
    selection_time_limit: float
    max_cars: object
    solver: dict

    @property
    def l_values(self) -> tuple:
        return tuple(sorted(int(s[1:]) for s in self.campaign.scenarios if s[:1] == "L" and s[1:].isdigit()))


def _limits(spec) -> fsr.TypeLimits:
    return fsr.TypeLimits(spec.type_id, spec.sw_capacity, spec.so_capacity, spec.total_capacity,
                          spec.ride_limit_minutes, spec.tour_limit_minutes)


def load_fleet(path) -> Fleet:
    path = Path(path)
    camp = loader.load_campaign(path)
    manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf-8"))
    by_id = {t.type_id: t for t in camp.fleet_types}
    params = manifest["parameters"]
    return Fleet(path, path.name, camp, manifest, _limits(by_id[manifest["fixed_type"]]),
                 _limits(by_id[manifest["minimize_type"]]),
                 params.get("selection_time_limit_seconds") or fsr.DEFAULT_SELECTION_TIME_LIMIT_S,
                 params.get("max_cars"), manifest["selection_solver"])


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_cell(fleet: Fleet, date: str, ride: int, limit: int) -> dict:
    return {"date": date, "R": ride, "L": limit,
            "menu": _read(fleet.path / f"{date}_R{ride}.menu_options.json"),
            "exchange": _read(fleet.path / f"{date}_R{ride}_L{limit}.selection_exchange.json")}


def route_facts(route: dict, direction: str) -> fsr.RouteFacts:
    interval = route["interval"]
    return fsr.RouteFacts(interval["startMinutes"], interval["endMinutes"],
                          tuple(step["duration"] for step in route["steps"]), direction, route["swCount"],
                          route["soCount"])


def menu_waves(menu: dict) -> list:
    """The producer's menu: per wave ``base`` first, then every ``included`` quota option, in archive order."""
    waves = []
    for wave in menu["waves"]:
        options = [(o["optionId"], o["kind"] == "baseline", [route_facts(r, wave["direction"]) for r in o["routes"]])
                   for o in wave["options"] if o["status"] == "included"]
        waves.append((wave["waveId"], options))
    return waves


def rebuild_request(fleet: Fleet, menu: dict, limit: int) -> dict:
    return fsr.build_selection_request(
        menu_waves(menu), fixed_type=fleet.fixed, minimise_type=fleet.minimise, max_large=limit,
        ride_default=menu["limits"]["maxRideTimeMinutes"], tour_default=menu["limits"]["maxTourMinutes"],
        cooldown_large_minutes=_cooldown(fleet, fleet.fixed), cooldown_car_minutes=_cooldown(fleet, fleet.minimise),
        max_cars=fleet.max_cars, time_limit_seconds=fleet.selection_time_limit)


def _cooldown(fleet: Fleet, type_: fsr.TypeLimits) -> int:
    spec = next(t for t in fleet.campaign.fleet_types if t.type_id == type_.type_id)
    return spec.cooldown_minutes


def diff_json(a, b, path: str = "") -> list:
    """Every difference between two parsed JSON values, with its path (numbers compare by value)."""
    out: list = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in a:
            if key not in b:
                out.append(f"{path}.{key}: only in the archive")
        for key in b:
            if key not in a:
                out.append(f"{path}.{key}: only in the replay")
        for key in a:
            if key in b:
                out.extend(diff_json(a[key], b[key], f"{path}.{key}" if path else key))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} (archive) vs {len(b)} (replay)")
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_json(x, y, f"{path}[{i}]"))
    elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        if a is not b and a != b:
            out.append(f"{path}: {a!r} (archive) vs {b!r} (replay)")
    elif a != b:
        out.append(f"{path}: {a!r} (archive) vs {b!r} (replay)")
    return out


def compare_response(archived: dict, replayed: dict) -> list:
    """Differences in the six compared parts: the five scalar fields and the selection with its labels."""
    diffs = []
    for field in COMPARED_FIELDS:
        diffs.extend(diff_json(archived.get(field), replayed.get(field), field))
    diffs.extend(diff_json(archived.get("selection"), replayed.get("selection"), "selection"))
    return diffs


def _router():
    import routers.fleet_selection as router

    return router


def replay_loaded_cell(fleet: Fleet, cell: dict) -> dict:
    exchange, menu = cell["exchange"], cell["menu"]
    row = {"fleet": fleet.name, "date": cell["date"], "R": cell["R"], "L": cell["L"], "label": "match",
           "request_diffs": [], "response_diffs": [], "archived_status": None, "replay_status": None,
           "solver_version": None, "replay_seconds": None, "router_checks": "ok", "diagnostics_equal": None,
           "seed_workers_equal": None, "http_status": exchange.get("httpStatus")}
    import ortools

    row["solver_version"] = ortools.__version__
    if ortools.__version__ != fleet.solver["version"]:
        raise RuntimeError(f"CP-SAT {ortools.__version__} differs from the archived {fleet.solver['version']}")
    request = rebuild_request(fleet, menu, cell["L"])
    row["request_diffs"] = diff_json(exchange["request"], request)
    if exchange.get("httpStatus") != 200 or not isinstance(exchange.get("response"), dict):
        row["label"] = "archived_http_error"
        return row
    router = _router()
    try:
        parsed = router.FleetSelectionRequest.model_validate(request)
    except Exception:  # noqa: BLE001 - the router answers every malformed body with its fixed 422
        row["label"], row["router_checks"] = "router_refused", "request_invalid"
        return row
    limit = router._policy_time_limit(parsed.time_limit_seconds)
    if limit is None:
        row["label"], row["router_checks"] = "router_refused", "time_limit_above_policy"
        return row
    t0 = time.perf_counter()
    result = fsr.result_body(fsr.solve_request(request, time_limit_s=limit))
    row["replay_seconds"] = round(time.perf_counter() - t0, 3)
    archived = exchange["response"]
    row["archived_status"], row["replay_status"] = archived.get("status"), result["status"]
    row["response_diffs"] = compare_response(archived, result)
    row["diagnostics_equal"] = not diff_json(archived.get("diagnostics"), result.get("diagnostics"))
    a_stats, r_stats = archived.get("stats") or {}, result.get("stats") or {}
    row["seed_workers_equal"] = all(a_stats.get(k) == r_stats.get(k) for k in ("random_seed", "num_workers"))
    if row["request_diffs"]:
        row["label"] = "request_mismatch"
    elif row["response_diffs"]:
        row["label"] = "response_mismatch"
    elif row["archived_status"] != "optimal":
        row["label"] = "match_not_optimal"
    return row


def replay_cell(fleet: Fleet, date: str, ride: int, limit: int) -> dict:
    return replay_loaded_cell(fleet, load_cell(fleet, date, ride, limit))


def fleet_cells(fleet: Fleet) -> list:
    dates = sorted({w.service_date for w in fleet.campaign.waves_for(fleet.campaign.rides[0])})
    return [(d, r, limit) for d in dates for r in fleet.campaign.rides for limit in fleet.l_values]


def replay_fleet(fleet: Fleet) -> list:
    return [replay_cell(fleet, d, r, limit) for d, r, limit in fleet_cells(fleet)]


def main(argv) -> int:
    fleet = load_fleet(argv[1])
    rows = replay_fleet(fleet)
    bad = [r for r in rows if r["label"] not in MATCH_LABELS]
    print(f"{fleet.name}: {len(rows) - len(bad)}/{len(rows)} cells reproduced")
    for r in bad[:20]:
        print(r["date"], r["R"], r["L"], r["label"], r["request_diffs"][:3], r["response_diffs"][:3])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
