"""WP-E4a part 2: the typed certification bridge (design section 3: "The typed path uses the same function with
``vehicle_types``, quotas and ``total_capacity``").

Exact and GA typed routes are wrapped in the operational ``ga_split_hf`` request/response and judged by
``certify_optimization_response`` on the archived matrix slice. Each violation below is first shown to be
absent in a control (so the rejection is not vacuous) and then present.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
LARGE_SEDAN = RESULTS / "week-2026-10-05-fleet-rerun-large-sedan"
DOBLO = RESULTS / "week-2026-10-05-fleet-rerun-doblo-cap3"
for _p in (REPO / "optimizer_api", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from uniride_core.exact import certification as cert  # noqa: E402
from uniride_core.exact.wave_instance import VehicleTypeSpec  # noqa: E402


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load("run_exact_wave_gaps")


@pytest.fixture(scope="module")
def ls_campaign(runner):
    return runner.loader.load_campaign(LARGE_SEDAN)


@pytest.fixture(scope="module")
def doblo_campaign(runner):
    return runner.loader.load_campaign(DOBLO)


def _arcs(directory, date="2026-10-05", ride=90):
    return json.loads((directory / f"{date}_R{ride}.matrix.json").read_text(encoding="utf-8"))


def _menu(directory, date="2026-10-05", ride=90):
    return json.loads((directory / f"{date}_R{ride}.menu_options.json").read_text(encoding="utf-8"))


def _types(campaign):
    return {t.type_id: t for t in campaign.fleet_types}


def _wave(campaign, wave_id, ride=90):
    return next(w for w in campaign.waves_for(ride) if w.wave_id == wave_id)


def _ga_option(menu, wave_id, option_id):
    wave = next(w for w in menu["waves"] if w["waveId"] == wave_id)
    return next(o for o in wave["options"] if o["optionId"] == option_id)


def _typed_ga_with_large(menu, campaign, min_large=1):
    """An archived GA quota option with at least ``min_large`` large routes: (wave, option, large route count)."""
    for w in menu["waves"]:
        for o in w["options"]:
            if o["kind"] == "quota" and o["status"] == "included":
                n = sum(r["vehicleType"] == "large" for r in o["routes"])
                if n >= min_large:
                    return _wave(campaign, w["waveId"]), o, n
    raise AssertionError("no archived quota option with a large route")


def _certify(runner, wave, types, minimize, quota, response, arcs_doc):
    spec = [types["large"], types[minimize]]
    request = cert.typed_request_payload(wave, spec, minimize_type=minimize, quota=quota)
    return runner.certificate(request, response, arcs_doc)


def test_archived_ga_quota_option_certifies_through_the_typed_bridge(runner, ls_campaign):
    menu, arcs = _menu(LARGE_SEDAN), _arcs(LARGE_SEDAN)
    wave, option, n_large = _typed_ga_with_large(menu, ls_campaign)
    response = cert.ga_option_response_payload(wave, option, typed=True)
    result = _certify(runner, wave, _types(ls_campaign), "sedan", ("large", option["quota"]), response, arcs)
    assert result["is_feasible"], result["violations"]
    assert result["violation_count"] == 0


def test_quota_violation_is_rejected(runner, ls_campaign):
    menu, arcs = _menu(LARGE_SEDAN), _arcs(LARGE_SEDAN)
    wave, option, n_large = _typed_ga_with_large(menu, ls_campaign)
    response = cert.ga_option_response_payload(wave, option, typed=True)
    assert n_large >= 1
    result = _certify(runner, wave, _types(ls_campaign), "sedan", ("large", n_large - 1), response, arcs)
    assert not result["is_feasible"]
    assert any("quota" in v["type"] for v in result["violations"]), result["violations"]


def _route_with_counts(wave, sw, so, ride_limit, tour_limit):
    """Visiting order of ``sw`` Sw + ``so`` So students of the wave that respects R and T (brute force), or None."""
    sws = [o for o, c in zip(wave.occurrence_ids, wave.classes) if c == "Sw"]
    sos = [o for o, c in zip(wave.occurrence_ids, wave.classes) if c == "So"]
    if len(sws) < sw or len(sos) < so:
        return None
    for chosen in itertools.product(itertools.combinations(sws, sw), itertools.combinations(sos, so)):
        members = chosen[0] + chosen[1]
        for order in itertools.permutations(members):
            index = {occ: i + 1 for i, occ in enumerate(wave.occurrence_ids)}
            path = [0] + [index[o] for o in order] + [0]
            arcs = [wave.matrix[a][b] for a, b in zip(path, path[1:])]
            ride = sum(arcs[1:]) if wave.direction == "pickup" else sum(arcs[:-1])
            if sum(arcs) <= tour_limit and ride <= ride_limit:
                return order
    return None


def _find_one_sw_three_so_route(campaign):
    for wave in campaign.waves_for(90):
        if wave.legs > 12:
            continue
        order = _route_with_counts(wave, 1, 3, 90, 150)
        if order:
            return wave, order
    raise AssertionError("no wave offers a 1 Sw + 3 So route within R and T")


def test_total_capacity_violation_is_rejected(runner, doblo_campaign):
    """A (1 Sw + 3 So) route fits the minivan pools 1/3 but not the shared seat limit total_capacity 3."""
    wave, order = _find_one_sw_three_so_route(doblo_campaign)
    arcs = _arcs(DOBLO)
    types = _types(doblo_campaign)
    assert types["minivan"].total_capacity == 3
    rest = [o for o in wave.occurrence_ids if o not in order]
    routes = [("minivan", order)] + [("large", (o,)) for o in rest]
    response = cert.typed_response_payload(wave, routes)

    no_total = {**types, "minivan": VehicleTypeSpec("minivan", 1, 3, 10, None)}
    control = _certify(runner, wave, no_total, "minivan", None, response, arcs)
    assert control["is_feasible"], control["violations"]  # pools alone accept the route

    result = _certify(runner, wave, types, "minivan", None, response, arcs)
    assert not result["is_feasible"]
    assert any("capacity" in v["type"] for v in result["violations"]), result["violations"]


def test_wrong_vehicle_type_is_rejected(runner, ls_campaign):
    """A route with a Sw student labelled sedan (Sw pool 0) is rejected; an undeclared type is rejected too."""
    wave = next(w for w in ls_campaign.waves_for(90) if "Sw" in w.classes)
    arcs = _arcs(LARGE_SEDAN)
    types = _types(ls_campaign)
    single_routes = [(o,) for o in wave.occurrence_ids]
    sw_first = [o for o, c in zip(wave.occurrence_ids, wave.classes) if c == "Sw"][0]

    control = [("large" if (o,) == (sw_first,) else "large", (o,)) for o in wave.occurrence_ids]
    ok = _certify(runner, wave, types, "sedan", None, cert.typed_response_payload(wave, control), arcs)
    assert ok["is_feasible"], ok["violations"]

    mislabelled = [("sedan" if o == sw_first else "large", (o,)) for o in wave.occurrence_ids]
    bad = _certify(runner, wave, types, "sedan", None, cert.typed_response_payload(wave, mislabelled), arcs)
    assert not bad["is_feasible"]
    assert any("capacity" in v["type"] or "type" in v["type"] for v in bad["violations"]), bad["violations"]

    unknown = [("tractor" if o == sw_first else "large", (o,)) for o in wave.occurrence_ids]
    worse = _certify(runner, wave, types, "sedan", None, cert.typed_response_payload(wave, unknown), arcs)
    assert not worse["is_feasible"]
    assert single_routes  # (control uses singletons)


def test_typed_objective_counts_only_the_minimised_type_and_sums_tour_minutes(ls_campaign):
    wave = next(w for w in ls_campaign.waves_for(90) if w.legs >= 2)
    first, second = wave.occurrence_ids[0], wave.occurrence_ids[1]
    rest = [(o,) for o in wave.occurrence_ids[2:]]
    routes = [("sedan", (first,)), ("large", (second,))] + [("large", r) for r in rest]
    k_m, d, count = cert.recompute_typed_objective(wave, routes, "sedan")
    assert (k_m, count) == (1, len(wave.occurrence_ids))
    assert d == sum(cert.tour_cost(wave, seq) for _, seq in routes)
    assert cert.recompute_typed_objective(wave, routes, "large")[0] == len(wave.occurrence_ids) - 1


def test_typed_request_declares_types_quota_and_total_capacity(ls_campaign, doblo_campaign):
    wave = ls_campaign.waves_for(90)[0]
    spec = [t for t in ls_campaign.fleet_types]
    req = cert.typed_request_payload(wave, spec, minimize_type="sedan", quota=("large", 2))
    assert req["algorithm"] == "ga_split_hf" and req["minimize_type"] == "sedan" and "vehicles" not in req
    by_id = {t["type_id"]: t for t in req["vehicle_types"]}
    assert by_id["large"]["max_routes"] == 2 and "max_routes" not in by_id["sedan"]
    doblo = cert.typed_request_payload(doblo_campaign.waves_for(90)[0], list(doblo_campaign.fleet_types),
                                       minimize_type="minivan", quota=("large", 0))
    by_id = {t["type_id"]: t for t in doblo["vehicle_types"]}
    assert by_id["minivan"]["total_capacity"] == 3 and by_id["large"]["max_routes"] == 0
    assert req["max_travel_time"] == wave.max_tour_minutes and req["max_ride_time"] == wave.max_ride_minutes
