"""CX-01: pins the OLD (whole-minute floor/ceil) versus NEW (exact centi-minute) interval builders
used by ``scripts/verify_cx01_archive_replay.py``.

OLD mirrors the pre-fix producer (8ab88ca:src/services/fleet-scenario-run.ts:530-548); NEW mirrors the
current producer (time_scale 100, cooldown x100).
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("ortools")

from uniride_core.planning.typed_day_selection import peak_concurrency, solve_day_selection

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_cx01_archive_replay.py"
_spec = importlib.util.spec_from_file_location("verify_cx01_archive_replay", SCRIPT)
replay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay)


def _route(job, start, end, label="car"):
    return {"jobId": job, "startMinutes": start, "endMinutes": end, "minutes": end - start, "selectionLabel": label}


def _busy(routes, mode):
    """Busy intervals [start, end + cooldown) in the mode's own time units."""
    waves, cooldown, scale = replay.build_input(routes, mode)
    assert scale == (1 if mode == "old" else 100)
    ivs = [(r.start, r.end + cooldown) for w in waves for o in w.options for r in o.routes]
    return waves, cooldown, ivs


def _run(routes, mode):
    waves, cooldown, _ = replay.build_input(routes, mode)
    res = solve_day_selection(waves, 0, cooldown_large=cooldown, cooldown_car=cooldown, time_limit_s=10)
    return res.status, res.cars, res.large_peak


def test_whole_minute_routes_identical_overlap_decisions():
    routes = [_route("a", 600, 602), _route("b", 612, 620), _route("c", 611, 615)]
    _, _, old = _busy(routes, "old")
    _, _, new = _busy(routes, "new")
    assert [(s * 100, e * 100) for s, e in old] == new
    assert peak_concurrency(old) == peak_concurrency(new) == 2
    assert _run(routes, "old") == _run(routes, "new")


def test_whole_minute_back_to_back_stays_one_car():
    routes = [_route("a", 600, 602), _route("b", 612, 620)]
    assert _run(routes, "old") == _run(routes, "new") == ("optimal", 1, 0)


def test_fractional_endpoints_old_widening_overlaps_new_stays_feasible():
    routes = [_route("a", 600, 601.5), _route("b", 611.5, 620)]
    _, _, old = _busy(routes, "old")
    _, _, new = _busy(routes, "new")
    assert old == [(600, 612), (611, 630)]          # end ceil 602 + 10 > start floor 611
    assert new == [(60000, 61150), (61150, 63000)]  # exact: 601.5 + 10 == 611.5
    assert peak_concurrency(old) == 2
    assert peak_concurrency(new) == 1
    assert _run(routes, "old")[1] == 2
    assert _run(routes, "new")[1] == 1


def test_off_grid_endpoint_is_refused_not_rounded():
    with pytest.raises(ValueError):
        replay.build_input([_route("a", 600, 601.505)], "new")
