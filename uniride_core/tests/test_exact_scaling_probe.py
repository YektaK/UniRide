"""Scaling probe of the exact route enumeration (scripts/probe_exact_enumeration_scaling.py).

Offline. The probe is a scoping measurement; these tests pin the synthetic-wave generator, the subprocess wrapper, the
early-stop logic, the output-directory rule and the summary arithmetic. No AMPL, no DB, no network.
"""
from __future__ import annotations

import importlib.util
import itertools
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = _load("probe_exact_enumeration_scaling")

USABLE = tuple(f"L{i:02d}" for i in range(26))


# ------------------------------------------------------------------------------------------------ generator
def test_generator_is_deterministic_per_seed_and_differs_between_seeds():
    a = probe.generate_students(USABLE, 50, 20, 1, 16, 54)
    b = probe.generate_students(USABLE, 50, 20, 1, 16, 54)
    c = probe.generate_students(USABLE, 50, 20, 2, 16, 54)
    assert a == b
    assert a != c


@pytest.mark.parametrize("n,k", [(20, 10), (20, 20), (30, 26), (50, 10), (80, 26), (80, 20)])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_chosen_location_gets_at_least_one_student(n, k, seed):
    codes, classes = probe.generate_students(USABLE, n, k, seed, 16, 54)
    assert len(codes) == len(classes) == n
    assert len(set(codes)) == k
    assert set(codes) <= set(USABLE)
    counts = {c: codes.count(c) for c in set(codes)}
    assert min(counts.values()) >= 1
    assert sum(counts.values()) == n


@pytest.mark.parametrize("n", [20, 30, 50, 80])
def test_class_share_is_the_real_share_rounded_half_up(n):
    codes, classes = probe.generate_students(USABLE, n, 10, 3, 16, 54)
    assert classes.count("Sw") == (2 * n * 16 + 54) // (2 * 54)
    assert set(classes) == {"Sw", "So"}


def test_class_share_edge_cases():
    _, none = probe.generate_students(USABLE, 20, 10, 1, 0, 54)
    _, every = probe.generate_students(USABLE, 20, 10, 1, 54, 54)
    assert set(none) == {"So"} and set(every) == {"Sw"}


def test_generator_rejects_k_above_n_or_above_the_available_stops():
    with pytest.raises(ValueError):
        probe.generate_students(USABLE, 10, 20, 1, 16, 54)
    with pytest.raises(ValueError):
        probe.generate_students(USABLE, 80, 27, 1, 16, 54)


def test_instance_does_not_depend_on_ride_or_fleet():
    # the same (seed, n, k) is the instance for every R, fleet and direction (the generator has no such argument)
    import inspect

    assert list(inspect.signature(probe.generate_students).parameters) == [
        "usable", "n", "k", "seed", "sw_num", "sw_den"]


def test_usable_stops_drops_stops_with_a_missing_arc():
    stops = ["A", "B", "C"]
    arcs = {}
    for x, y in itertools.permutations(["D"] + stops, 2):
        arcs[(x, y)] = 5
    del arcs[("B", "C")]  # one missing arc: B and C both lack a full arc set
    all_stops, usable = probe.usable_stops(arcs, "D")
    assert all_stops == ["A", "B", "C"]
    assert usable == ["A"]


def test_build_wave_matrix_is_zero_exactly_for_equal_codes_and_valid():
    arcs = {}
    for x, y in itertools.permutations(["D", "A", "B"], 2):
        arcs[(x, y)] = 7 if (x, y) != ("A", "B") else 3
    wave = probe.build_wave(arcs, "D", ("A", "A", "B"), ("Sw", "So", "So"), "pickup", 50, 150, 525, "snap")
    assert wave.matrix[1][2] == 0 and wave.matrix[2][1] == 0
    assert wave.matrix[1][3] == 3 and wave.matrix[3][1] == 7
    assert wave.legs == 3


# ------------------------------------------------------------------------------------------------ subprocess wrapper
def _py(code):
    return [sys.executable, "-c", code]


def test_wrapper_reports_a_timeout_as_a_status_and_does_not_hang():
    t0 = time.perf_counter()
    res = probe.run_subprocess(_py("import time; time.sleep(120)"), timeout=2)
    assert res["status"] == "subprocess_timeout"
    assert time.perf_counter() - t0 < 60


def test_wrapper_reports_a_crash_as_a_status():
    res = probe.run_subprocess(_py("import sys; sys.stderr.write('boom'); sys.exit(3)"), timeout=30)
    assert res["status"] == "subprocess_crash"
    assert res["returncode"] == 3
    assert "boom" in res["stderr_tail"]


def test_wrapper_reports_unparsable_output_as_a_crash():
    res = probe.run_subprocess(_py("print('not json')"), timeout=30)
    assert res["status"] == "subprocess_crash"


def test_wrapper_returns_the_last_json_line_of_a_clean_run():
    res = probe.run_subprocess(_py("print('noise'); print('{\"status\": \"complete\", \"labels\": 5}')"), timeout=30)
    assert res["status"] == "complete" and res["labels"] == 5
    assert res["wall_seconds"] >= 0


def test_real_worker_run_completes_and_a_forced_label_cap_is_reported():
    base = dict(fleet="single_4sw5so", direction="pickup", n=20, k=10, k_label="10", R=50, seed=1, anchor=525, tour=150)
    ok = probe.run_enumeration_subprocess(base, timeout=300)
    assert ok["status"] == "complete", ok
    assert ok["labels"] > 0 and ok["columns"] > 0 and ok["peak_mem_mb"] >= 0
    capped = probe.run_enumeration_subprocess({**base, "label_cap": 50}, timeout=300)
    assert capped["status"] == "label_cap", capped
    assert capped["cap_fired"] == "label_cap" and capped["labels"] == 51
    col = probe.run_enumeration_subprocess({**base, "column_cap": 10}, timeout=300)
    assert col["status"] == "column_cap" and col["columns"] == 11


@pytest.mark.skipif(probe.current_rss_bytes() is None, reason="no process memory reading on this host")
def test_memory_guard_turns_an_overshoot_into_a_status():
    spec = dict(fleet="single_4sw5so", direction="pickup", n=20, k=10, k_label="10", R=90, seed=1, anchor=525,
                tour=150, mem_limit_mb=1)
    res = probe.run_enumeration_subprocess(spec, timeout=300)
    assert res["status"] == "memory_guard_abort", res


# ------------------------------------------------------------------------------------------------ early stop
def _fake(cap_from, calls, *, typed_cap_from=None):
    def runner(spec):
        calls.append(dict(spec))
        limit = cap_from if spec["fleet"] == "single_4sw5so" else (typed_cap_from or cap_from)
        status = "complete" if spec["n"] < limit else "label_cap"
        return {"status": status, "labels": spec["n"], "columns": spec["n"] * 2, "cap_fired": "" if status == "complete" else status}
    return runner


def _grid(runner, **kw):
    cfg = dict(sizes=(20, 30, 50, 80), k_choices=[("10", 10), ("20", 20), ("all", 26)], rides=(50, 90), seeds=(1, 2),
               typed_fleets=("large+sedan",), dropoff_cells=[(50, "all")])
    cfg.update(kw)
    return probe.run_grid(runner, **cfg)


def test_early_stop_marks_larger_sizes_as_not_run_once_a_size_capped():
    calls = []
    rows = _grid(_fake(50, calls))
    single_pick = [c for c in calls if c["fleet"] == "single_4sw5so" and c["direction"] == "pickup"]
    assert not [c for c in single_pick if c["n"] == 80]  # n = 50 capped, n = 80 never ran
    skipped = [r for r in rows if r["fleet"] == "single_4sw5so" and r["direction"] == "pickup" and r["n"] == 80]
    assert skipped and all(r["status"] == "not_run_smaller_capped" for r in skipped)
    assert all(r["seed"] in (1, 2) for r in skipped)
    # the capped size itself ran all its seeds
    at50 = [c for c in single_pick if c["n"] == 50 and c["k"] == 10 and c["R"] == 50]
    assert sorted(c["seed"] for c in at50) == [1, 2]


def test_a_size_is_capped_when_any_seed_does_not_complete():
    calls = []

    def runner(spec):
        calls.append(dict(spec))
        bad = spec["n"] == 30 and spec["seed"] == 2
        return {"status": "subprocess_timeout" if bad else "complete", "labels": 1, "columns": 1, "cap_fired": ""}

    rows = _grid(runner, typed_fleets=(), dropoff_cells=[])
    assert not [c for c in calls if c["n"] >= 50]
    assert {r["status"] for r in rows if r["n"] == 50} == {"not_run_smaller_capped"}


def test_impossible_combinations_k_above_n_are_not_generated():
    calls = []
    rows = _grid(_fake(10 ** 9, calls), typed_fleets=(), dropoff_cells=[])
    assert not [r for r in rows if r["k"] > r["n"]]
    assert not [c for c in calls if c["k"] > c["n"]]
    # n = 20 has no k = all (26 > 20) cell; n = 30 does
    assert not [r for r in rows if r["n"] == 20 and r["k_label"] == "all"]
    assert [r for r in rows if r["n"] == 30 and r["k_label"] == "all"]


def test_typed_fleets_run_only_where_the_single_type_completed():
    calls = []
    rows = _grid(_fake(50, calls))
    typed = [c for c in calls if c["fleet"] == "large+sedan" and c["direction"] == "pickup"]
    assert typed and max(c["n"] for c in typed) < 50  # single capped at 50: typed never ran there
    typed_skipped = [r for r in rows if r["fleet"] == "large+sedan" and r["direction"] == "pickup" and r["n"] >= 50]
    assert typed_skipped and {r["status"] for r in typed_skipped} <= {"not_run_single_not_complete",
                                                                       "not_run_smaller_capped"}


def test_typed_early_stop_also_applies_along_n():
    calls = []
    rows = _grid(_fake(10 ** 9, calls, typed_cap_from=30), dropoff_cells=[])
    typed = [c for c in calls if c["fleet"] == "large+sedan"]
    assert max(c["n"] for c in typed) == 30  # capped at 30 -> 50 and 80 not run
    assert {r["status"] for r in rows if r["fleet"] == "large+sedan" and r["n"] == 80} == {"not_run_smaller_capped"}


def test_dropoff_check_runs_the_named_cell_only_and_typed_follow_single():
    calls = []
    _grid(_fake(10 ** 9, calls))
    drop = [c for c in calls if c["direction"] == "dropoff"]
    assert {(c["n"], c["k_label"]) for c in drop} == {(50, "all")}
    assert {c["fleet"] for c in drop} == {"single_4sw5so", "large+sedan"}


def test_grid_is_deterministic_in_order():
    a, b = [], []
    _grid(_fake(50, a))
    _grid(_fake(50, b))
    assert a == b


# ------------------------------------------------------------------------------------------------ out dir, summary
def test_out_dir_must_lie_strictly_below_results(tmp_path):
    results = REPO / "docs" / "paper" / "results"
    probe.check_out_dir(results / "week-x" / "probe", REPO)  # fine
    with pytest.raises(probe.ProbeRefused):
        probe.check_out_dir(results, REPO)
    with pytest.raises(probe.ProbeRefused):
        probe.check_out_dir(REPO / "docs" / "elsewhere", REPO)
    probe.check_out_dir(tmp_path / "outside", REPO)  # outside the repository: no dirty-check exclusion at stake


def test_summary_reports_largest_complete_and_first_capped_size():
    rows = []
    for n, status, labels in [(20, "complete", 10), (30, "complete", 100), (50, "label_cap", 5000001)]:
        for seed in (1, 2):
            rows.append(dict(fleet="single_4sw5so", direction="pickup", n=n, k_label="10", k=10, R=50, seed=seed,
                             status=status, labels=labels + seed, columns=n, cap_fired="" if status == "complete" else status))
    rows.append(dict(fleet="single_4sw5so", direction="pickup", n=80, k_label="10", k=10, R=50, seed=1,
                     status="not_run_smaller_capped", labels="", columns="", cap_fired=""))
    cells = probe.summarize_cells(rows)
    assert len(cells) == 1
    c = cells[0]
    assert c["largest_complete_n"] == 30
    assert c["first_capped_n"] == 50 and c["first_capped_status"] == "label_cap"
    assert c["by_n"][30]["labels_max"] == 102
    md = probe.summary_markdown(rows, {"sw_num": 16, "sw_den": 54})
    assert "single_4sw5so" in md and "30" in md and "label_cap" in md
