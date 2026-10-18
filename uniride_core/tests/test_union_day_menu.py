"""WP-E4b: union-menu construction, router-cap flags, the proof rule and the label logic (pure, no solver, no AMPL)."""
from __future__ import annotations

import pytest

from uniride_core.planning import union_day_menu as udm
from uniride_core.planning.fleet_selection_request import RouteFacts, TypeLimits, build_selection_request


def facts(start=100.0, end=121.0, sw=0, so=1, steps=(10, 11)):
    return RouteFacts(start, end, tuple(steps), "pickup", sw, so)


def option(option_id, origin, routes, stops=None, baseline=False):
    stops = stops if stops is not None else tuple((f"{option_id}-s{i}",) for i in range(len(routes)))
    return udm.MenuOption(option_id, baseline, tuple(routes), origin, tuple(tuple(s) for s in stops), ())


def wave(wave_id, *options):
    return udm.WaveMenu(wave_id, "pickup", 765.0, tuple(options))


# ---------------------------------------------------------------- menu construction
def test_union_menu_keeps_the_ga_order_and_appends_the_exact_options_in_their_order():
    ga = [wave("w1", option("base", "ga", [facts()], [("a",)], True), option("q1", "ga", [facts()], [("b",)]))]
    exact = {"w1": [option("xbase", "exact", [facts()], [("c",)]), option("xq0", "exact", [facts()], [("d",)]),
                    option("xq1", "exact", [facts()], [("e",)])]}
    union, log = udm.build_union_menu(ga, exact)
    assert [o.option_id for o in union[0].options] == ["base", "q1", "xbase", "xq0", "xq1"]
    assert log == []
    assert [o.baseline for o in union[0].options] == [True, False, False, False, False]


def test_an_exact_option_is_never_deduped_against_a_ga_option_even_with_the_same_routes_and_partition():
    same = [facts()]
    ga = [wave("w1", option("base", "ga", same, [("a", "b")], True))]
    exact = {"w1": [option("xbase", "exact", same, [("a", "b")])]}
    union, log = udm.build_union_menu(ga, exact)
    assert [o.option_id for o in union[0].options] == ["base", "xbase"]
    assert log == []


def test_exact_options_are_deduped_among_themselves_only_when_routes_are_identical():
    r1, r2 = facts(100, 121), facts(200, 230, steps=(15, 15))
    ga = [wave("w1", option("base", "ga", [r1], [("a",)], True))]
    exact = {"w1": [
        option("xbase", "exact", [r1, r2], [("a",), ("b", "c")]),
        option("xq0", "exact", [r2, r1], [("b", "c"), ("a",)]),  # same routes, other route order: identical
        option("xq1", "exact", [r1, r2], [("a",), ("c", "b")]),  # same partition, other stop order: kept
        option("xq2", "exact", [r1, facts(200, 231, steps=(15, 16))], [("a",), ("b", "c")]),  # same stops, other minutes: kept
    ]}
    union, log = udm.build_union_menu(ga, exact)
    assert [o.option_id for o in union[0].options] == ["base", "xbase", "xq1", "xq2"]
    assert log == [{"wave_id": "w1", "dropped": "xq0", "kept": "xbase"}]


def test_exact_waves_unknown_to_the_ga_menu_are_refused():
    with pytest.raises(ValueError, match="not in the GA menu"):
        udm.build_union_menu([wave("w1", option("base", "ga", [facts()]))], {"w9": []})


def test_the_union_request_is_the_ga_request_plus_exact_options_with_the_same_port():
    fixed, minimise = TypeLimits("large", 4, 5), TypeLimits("sedan", 0, 4)
    ga = [wave("w1", option("base", "ga", [facts()], baseline=True))]
    union, _ = udm.build_union_menu(ga, {"w1": [option("xbase", "exact", [facts()])]})
    kwargs = dict(fixed_type=fixed, minimise_type=minimise, max_large=1, ride_default=90, tour_default=120)
    ga_req = build_selection_request(udm.request_waves(ga), **kwargs)
    union_req = build_selection_request(udm.request_waves(union), **kwargs)
    assert union_req["waves"][0]["options"][0] == ga_req["waves"][0]["options"][0]
    assert [o["option_id"] for o in union_req["waves"][0]["options"]] == ["base", "xbase"]
    assert union_req["time_scale"] == 100


def test_a_zero_length_exact_route_keeps_start_plus_one_in_the_request():
    fixed, minimise = TypeLimits("large", 4, 5), TypeLimits("sedan", 0, 4)
    zero = RouteFacts(525.0, 525.0, (0, 0), "pickup", 0, 1)
    union, _ = udm.build_union_menu([wave("w1", option("base", "ga", [facts()], baseline=True))],
                                    {"w1": [option("xbase", "exact", [zero])]})
    req = build_selection_request(udm.request_waves(union), fixed_type=fixed, minimise_type=minimise, max_large=1,
                                  ride_default=90, tour_default=120)
    route = req["waves"][0]["options"][1]["routes"][0]
    assert (route["start"], route["end"]) == (52500, 52501)


# ---------------------------------------------------------------- router caps
def _request(options_per_wave, routes_per_option):
    return {"waves": [{"wave_id": f"w{i}", "options": [{"option_id": f"o{j}", "routes": [{}] * r}
                                                       for j, r in enumerate(routes_per_option)]}
                      for i in range(options_per_wave)]}


CAPS = dict(max_options_per_wave=6, max_routes_per_option=40, max_total_routes=1000)


def test_router_cap_flags_report_each_cap_that_would_be_exceeded():
    ok = udm.router_cap_flags(_request(2, [3] * 6), **CAPS)
    assert (ok["cap_options_per_wave"], ok["cap_routes_per_option"], ok["cap_total_routes"]) == (False, False, False)
    options = udm.router_cap_flags(_request(2, [1] * 7), **CAPS)
    assert (options["cap_options_per_wave"], options["waves_over_options_cap"], options["max_options_per_wave"]) == (True, 2, 7)
    assert options["cap_routes_per_option"] is False
    routes = udm.router_cap_flags(_request(1, [41, 2]), **CAPS)
    assert (routes["cap_routes_per_option"], routes["options_over_routes_cap"], routes["max_routes_per_option"]) == (True, 1, 41)
    total = udm.router_cap_flags(_request(5, [40, 40, 40, 40, 40, 1]), **CAPS)  # 5 * 201 = 1005
    assert (total["cap_total_routes"], total["total_routes"]) == (True, 1005)
    edge = udm.router_cap_flags(_request(5, [40, 40, 40, 40, 40]), **CAPS)  # exactly 1000: not exceeded
    assert edge["cap_total_routes"] is False


# ---------------------------------------------------------------- the two runs and the proof rule
def body(status, cars=None, large_peak=0, selection=None):
    return {"status": status, "cars": cars, "large_peak": large_peak, "car_minutes": 1.0, "total_minutes": 2.0,
            "selection": selection if selection is not None else {"w1": {"option_id": "base", "option_index": 0, "labels": ["car"]}}}


class FakeSolver:
    """Answers per call from a script; records (request name, time limit)."""

    def __init__(self, script):
        self.script, self.calls = list(script), []

    def __call__(self, request, *, time_limit_s):
        self.calls.append((request["name"], time_limit_s))
        return self.script.pop(0)


def solve(ga_body, *union_bodies):
    solver = FakeSolver([ga_body, *union_bodies])
    ticks = iter(range(0, 1000, 5))
    cell = udm.solve_cell({"name": "ga"}, {"name": "union"}, producer_limit_s=30, rerun_limit_s=60, solve=solver,
                          to_body=lambda r: r, clock=lambda: next(ticks))
    return cell, solver


def test_both_runs_at_the_producer_limit_and_no_rerun_when_the_union_is_optimal():
    cell, solver = solve(body("optimal", 4), body("optimal", 3))
    assert solver.calls == [("ga", 30), ("union", 30)]
    assert cell.rerun is False and cell.union.time_limit_s == 30 and cell.ga.time_limit_s == 30


def test_a_union_run_on_its_time_limit_is_rerun_once_at_60_seconds_and_only_the_union():
    cell, solver = solve(body("optimal", 4), body("feasible", 4), body("optimal", 3))
    assert solver.calls == [("ga", 30), ("union", 30), ("union", 60)]
    assert cell.rerun is True and cell.union.status == "optimal" and cell.union.time_limit_s == 60
    assert cell.union_first.status == "feasible" and cell.union_first.time_limit_s == 30


def test_a_union_run_that_is_still_not_optimal_after_the_rerun_is_not_proven_and_timing_dependent():
    cell, solver = solve(body("optimal", 4), body("feasible", 4), body("feasible", 4))
    assert solver.calls == [("ga", 30), ("union", 30), ("union", 60)]  # once, never a third call
    verdict = udm.classify(cell, udm.Confirmation(udm.CONFIRMED), udm.Confirmation(udm.CONFIRMED))
    assert verdict.label == udm.LABEL_NOT_PROVEN and verdict.timing_dependent is True and verdict.claim == ""
    assert "60" in verdict.reason and verdict.blocking_errors == ()


def test_a_proven_infeasibility_of_the_union_is_final_and_never_rerun():
    cell, solver = solve(body("infeasible_for_L", None, selection={}), body("infeasible_for_L", None, selection={}))
    assert solver.calls == [("ga", 30), ("union", 30)]
    assert cell.rerun is False


def test_union_above_ga_blocks_only_when_both_runs_are_optimal():
    cell, _ = solve(body("optimal", 3), body("optimal", 4))
    verdict = udm.classify(cell, udm.Confirmation(udm.CONFIRMED), udm.Confirmation(udm.CONFIRMED))
    assert len(verdict.blocking_errors) == 1 and "exceed" in verdict.blocking_errors[0]
    # not both optimal: a larger union value is not a defect and nothing is claimed or checked
    for ga_status, union_statuses in (("optimal", ("feasible", "feasible")), ("feasible", ("optimal",))):
        cell, _ = solve(body(ga_status, 3), *[body(s, 4) for s in union_statuses])
        verdict = udm.classify(cell, udm.Confirmation(udm.CONFIRMED), udm.Confirmation(udm.CONFIRMED))
        assert verdict.blocking_errors == () and verdict.label == udm.LABEL_NOT_PROVEN


def test_union_not_above_ga_error_function():
    mk = lambda status, cars: udm.RunRecord(status, cars, 0, 0.0, 0.0, {}, 30, 0.0)  # noqa: E731
    assert udm.union_not_above_ga_error(mk("optimal", 3), mk("optimal", 3)) is None
    assert udm.union_not_above_ga_error(mk("optimal", 3), mk("optimal", 2)) is None
    assert udm.union_not_above_ga_error(mk("optimal", 3), mk("optimal", 4)) is not None
    assert udm.union_not_above_ga_error(mk("optimal", 3), mk("feasible", 4)) is None
    assert udm.union_not_above_ga_error(mk("infeasible_for_L", None), mk("optimal", 4)) is None


# ---------------------------------------------------------------- labels
C_OK, C_FAIL = udm.Confirmation(udm.CONFIRMED), udm.Confirmation(udm.CONFIRM_FAILED, "x")
C_MISSING, C_NA = udm.Confirmation(udm.CONFIRM_MISSING, "no CLI result"), udm.Confirmation(udm.CONFIRM_NOT_NEEDED)


def test_label_proven_needs_both_runs_optimal_and_both_confirmed_and_carries_the_claim():
    cell, _ = solve(body("optimal", 4), body("optimal", 3))
    verdict = udm.classify(cell, C_OK, C_OK)
    assert verdict.label == udm.LABEL_PROVEN and verdict.claim == udm.CLAIM and verdict.timing_dependent is False
    assert "not a global day optimum (EQ3)" in udm.CLAIM and "never above the GA-menu result" in udm.CLAIM


def test_a_missing_cli_check_gives_not_independently_confirmed_even_when_both_runs_are_optimal():
    cell, _ = solve(body("optimal", 4), body("optimal", 3))
    for ga_c, union_c in ((C_MISSING, C_OK), (C_OK, C_MISSING)):
        assert udm.classify(cell, ga_c, union_c).label == udm.LABEL_NOT_CONFIRMED


def test_a_failed_cli_check_gives_verification_failed_and_wins_over_a_missing_one():
    cell, _ = solve(body("optimal", 4), body("optimal", 3))
    for ga_c, union_c in ((C_FAIL, C_OK), (C_OK, C_FAIL), (C_FAIL, C_MISSING), (C_MISSING, C_FAIL)):
        verdict = udm.classify(cell, ga_c, union_c)
        assert verdict.label == udm.LABEL_FAILED and verdict.claim == ""


def test_confirmation_from_cli_result():
    run = udm.RunRecord("optimal", 3, 1, 1.0, 2.0, {}, 30, 0.1)
    good = {"ok": True, "assignment": {"status": "proven", "cars": 3}, "problems": [], "recheck": {"failures": []}, "intervalDifferences": []}
    assert udm.confirmation_from_cli(good, run).status == udm.CONFIRMED
    assert udm.confirmation_from_cli(None, run).status == udm.CONFIRM_MISSING
    assert udm.confirmation_from_cli(None, udm.RunRecord("infeasible_for_L", None, None, None, None, {}, 30, 0)).status == udm.CONFIRM_NOT_NEEDED
    bad = dict(good, ok=False, intervalDifferences=[{"field": "start"}])
    assert udm.confirmation_from_cli(bad, run).status == udm.CONFIRM_FAILED
    disagree = dict(good, assignment={"status": "proven", "cars": 2})
    got = udm.confirmation_from_cli(disagree, run)
    assert got.status == udm.CONFIRM_FAILED and "differs" in got.detail
    witness = dict(good, assignment={"status": "witness", "cars": 2})
    assert udm.confirmation_from_cli(witness, run).status == udm.CONFIRMED  # a witness is not a proven minimum
    infeasible = dict(good, ok=False, assignment={"status": "infeasible_for_L", "cars": None})
    assert udm.confirmation_from_cli(infeasible, run).status == udm.CONFIRM_FAILED


def test_the_result_never_carries_a_min_of_ga_and_union():
    cell, _ = solve(body("optimal", 4), body("optimal", 3))
    names = set(udm.Verdict.__dataclass_fields__) | set(udm.CellSolve.__dataclass_fields__) | set(dir(udm))
    assert not [n for n in names if n.lower() in ("min_cars", "best_cars", "min_ga_union", "best_of")]
    assert not hasattr(cell, "min_cars")


# ---------------------------------------------------------------- owner decision 2026-10-18: labels for proven infeasibility
def infeasible(status="infeasible_for_L"):
    return body(status, None, selection={})


@pytest.mark.parametrize("ga_status,union_status", [("infeasible_for_L", "infeasible_for_L"), ("infeasible_data", "infeasible_for_L"),
                                                    ("infeasible_for_L", "infeasible_data"), ("infeasible_data", "infeasible_data")])
def test_both_runs_proven_infeasible_is_both_infeasible_for_L_with_no_claim(ga_status, union_status):
    cell, solver = solve(infeasible(ga_status), infeasible(union_status))
    verdict = udm.classify(cell, C_NA, C_NA)
    assert verdict.label == udm.LABEL_BOTH_INFEASIBLE == "both_infeasible_for_L"
    assert verdict.claim == "" and verdict.timing_dependent is False and verdict.blocking_errors == ()
    assert ga_status in verdict.reason and union_status in verdict.reason


@pytest.mark.parametrize("ga_status", ["infeasible_for_L", "infeasible_data"])
def test_ga_menu_infeasible_and_union_optimal_confirmed_is_ga_menu_infeasible_for_L_without_the_never_above_ga_claim(ga_status):
    cell, _ = solve(infeasible(ga_status), body("optimal", 3))
    verdict = udm.classify(cell, C_NA, C_OK)
    assert verdict.label == udm.LABEL_GA_INFEASIBLE == "ga_menu_infeasible_for_L"
    assert verdict.claim == udm.CLAIM_UNION_ONLY and verdict.timing_dependent is False and verdict.blocking_errors == ()
    assert "never above" not in udm.CLAIM_UNION_ONLY and "not a global day optimum (EQ3)" in udm.CLAIM_UNION_ONLY
    assert "minimum cars over the union of the GA and per-wave exact menus" in udm.CLAIM_UNION_ONLY


def test_ga_menu_infeasible_union_optimal_needs_the_union_confirmation():
    cell, _ = solve(infeasible(), body("optimal", 3))
    assert udm.classify(cell, C_NA, C_MISSING).label == udm.LABEL_NOT_CONFIRMED
    assert udm.classify(cell, C_NA, C_FAIL).label == udm.LABEL_FAILED


def test_union_not_proven_is_only_the_union_still_on_its_time_limit_after_the_rerun():
    cell, _ = solve(body("optimal", 4), body("feasible", 4), body("feasible", 4))
    verdict = udm.classify(cell, C_OK, C_OK)
    assert (verdict.label, verdict.timing_dependent, verdict.claim) == (udm.LABEL_NOT_PROVEN, True, "")
    cell, _ = solve(body("optimal", 4), body("indeterminate", None, selection={}), body("indeterminate", None, selection={}))
    verdict = udm.classify(cell, C_OK, C_NA)
    assert (verdict.label, verdict.timing_dependent) == (udm.LABEL_NOT_PROVEN, True)


def test_mirror_cases_ga_not_optimal_with_an_optimal_union_is_not_a_ga_menu_infeasible_row():
    # the GA-menu run stopped on its clock (feasible): not a proven infeasibility, nothing is claimed
    cell, _ = solve(body("feasible", 4), body("optimal", 3))
    verdict = udm.classify(cell, C_OK, C_OK)
    assert verdict.label == udm.LABEL_NOT_PROVEN and verdict.timing_dependent is True and verdict.claim == ""


def test_the_label_set_has_six_values():
    assert udm.LABELS == ("proven_over_union_menu", "ga_menu_infeasible_for_L", "both_infeasible_for_L", "union_not_proven",
                          "not_independently_confirmed", "verification_failed")


# ---------------------------------------------------------------- P2: impossible state
@pytest.mark.parametrize("ga_status", ["optimal", "feasible"])
@pytest.mark.parametrize("union_status", ["infeasible_for_L", "infeasible_data"])
def test_a_ga_selection_with_a_proven_infeasible_union_is_a_blocking_impossible_state(ga_status, union_status):
    cell, _ = solve(body(ga_status, 3), infeasible(union_status))
    verdict = udm.classify(cell, C_OK, C_NA)
    assert len(verdict.blocking_errors) == 1 and "impossible" in verdict.blocking_errors[0]
    assert verdict.label == udm.LABEL_FAILED and verdict.claim == ""


def test_no_impossible_state_error_for_the_possible_combinations():
    for ga, union, conf in ((infeasible(), infeasible(), (C_NA, C_NA)), (infeasible(), body("optimal", 3), (C_NA, C_OK)),
                            (body("optimal", 3), body("optimal", 3), (C_OK, C_OK))):
        cell, _ = solve(ga, union)
        assert udm.classify(cell, *conf).blocking_errors == ()


# ---------------------------------------------------------------- P1: TS vs CP-SAT car count
def _cli(status, cars):
    return {"ok": True, "assignment": {"status": status, "cars": cars}, "problems": [], "recheck": {"failures": []}, "intervalDifferences": []}


def test_ts_car_count_must_equal_cp_sat_only_for_an_optimal_run_and_may_not_exceed_it_for_a_witness():
    optimal = udm.RunRecord("optimal", 3, 1, 1.0, 2.0, {}, 30, 0.1)
    feasible = udm.RunRecord("feasible", 3, 1, 1.0, 2.0, {}, 30, 0.1)
    assert udm.confirmation_from_cli(_cli("proven", 3), optimal).status == udm.CONFIRMED
    assert udm.confirmation_from_cli(_cli("proven", 2), optimal).status == udm.CONFIRM_FAILED  # optimal: must be equal
    assert udm.confirmation_from_cli(_cli("proven", 4), optimal).status == udm.CONFIRM_FAILED
    assert udm.confirmation_from_cli(_cli("proven", 3), feasible).status == udm.CONFIRMED
    assert udm.confirmation_from_cli(_cli("proven", 2), feasible).status == udm.CONFIRMED  # a witness is an upper bound
    got = udm.confirmation_from_cli(_cli("proven", 4), feasible)
    assert got.status == udm.CONFIRM_FAILED and "exceeds" in got.detail
