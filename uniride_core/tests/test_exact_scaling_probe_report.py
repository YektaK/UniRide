"""Report-only mode of the scaling probe (scripts/probe_exact_enumeration_scaling.py --report-only --from DIR).

The mode rewrites README.md and summary.md (and the manifest's report block and output hashes) from an existing
probe.csv without running any enumeration and without writing probe.csv. Offline.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
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
SINGLE, TYPED = "single_4sw5so", "large+sedan"


def _row(fleet, direction, n, kl, kv, ride, seed, status, items, labels, columns=10):
    row = {f: "" for f in probe.ROW_FIELDS}
    row.update(fleet=fleet, direction=direction, n=n, k_label=kl, k=kv, R=ride, seed=seed, anchor=525, tour=150,
               status=status, cap_fired="" if status == "complete" else status, items=items, labels=labels,
               columns=columns, wall_seconds=1.5, peak_mem_mb=40.0)
    return row


def _fixture_rows(typed_labels_shift=0):
    rows = []
    # k = all (26): items per seed 37/31/33 at n = 50 and 42/42/40 at n = 80; one mixed cell at n = 30, R = 90
    for seed, items in zip((1, 2, 3), (37, 31, 33)):
        rows.append(_row(SINGLE, "pickup", 50, "all", 26, 50, seed, "complete", items, 1000 + seed))
    for seed, items in zip((1, 2, 3), (42, 42, 40)):
        rows.append(_row(SINGLE, "pickup", 80, "all", 26, 50, seed, "complete", items, 2000 + seed))
    for seed, items, status, labels in ((1, 26, "complete", 1876915), (2, 26, "complete", 2646967),
                                        (3, 28, "label_cap", 5000001)):
        rows.append(_row(SINGLE, "pickup", 30, "all", 26, 90, seed, status, items, labels))
    # seed spread: 100 / 620 / 300 labels (ratio 6.2) in one cell, a flatter cell elsewhere
    for seed, labels in zip((1, 2, 3), (100, 620, 300)):
        rows.append(_row(SINGLE, "pickup", 20, "10", 10, 70, seed, "complete", 10, labels))
    for seed, labels in zip((1, 2, 3), (500, 600, 700)):
        rows.append(_row(SINGLE, "pickup", 30, "10", 10, 70, seed, "complete", 10, labels))
    typed = [_row(TYPED, r["direction"], r["n"], r["k_label"], r["k"], r["R"], r["seed"], "complete", r["items"],
                  r["labels"] + typed_labels_shift, 12) for r in rows if r["status"] == "complete"]
    return rows + typed


def _fixture_dir(tmp_path, rows=None, name="results"):
    rows = rows if rows is not None else _fixture_rows()
    d = tmp_path / name
    d.mkdir()
    (d / "probe.csv").write_bytes(probe.csv_text(rows).encode("utf-8"))
    _, files = probe.load_union_arcs()
    manifest = {
        "git_commit": "a" * 40, "dirty_working_tree": False,
        "matrix_source": {"declared_snapshot_sha256": files[0]["declared_sha256"]},
        "locations": {"depot": probe.DEPOT, "stops_in_archive": [f"X{i}" for i in range(28)],
                      "usable_stops": [f"X{i}" for i in range(26)]},
        "sw_share": {"sw_legs": 68, "legs": 226}, "seeds": [1, 2, 3],
        "grid": {"sizes": [20, 30, 50, 80], "rides": [50, 70, 90], "dropoff_cells": [[50, "all"]]},
        "caps": {"memory_guard_mb": 2500, "subprocess_timeout_seconds": 660.0},
        "total_wall_seconds": 5322.2,
        "outputs": {"probe.csv": hashlib.sha256((d / "probe.csv").read_bytes()).hexdigest(),
                    "summary.md": "stale", "README.md": "stale"},
        "rows": len(rows), "claim": "none",
    }
    (d / "manifest.json").write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return d


def test_report_only_is_byte_identical_when_run_twice(tmp_path):
    d = _fixture_dir(tmp_path)
    probe.report_only(d)
    first = {n: (d / n).read_bytes() for n in ("README.md", "summary.md", "manifest.json", "probe.csv")}
    probe.report_only(d)
    second = {n: (d / n).read_bytes() for n in first}
    assert first == second
    assert all(b"\r" not in v for v in first.values())


def test_report_only_never_writes_probe_csv_and_refuses_a_changed_one(tmp_path):
    d = _fixture_dir(tmp_path)
    before, mtime = (d / "probe.csv").read_bytes(), (d / "probe.csv").stat().st_mtime_ns
    probe.report_only(d)
    assert (d / "probe.csv").read_bytes() == before and (d / "probe.csv").stat().st_mtime_ns == mtime
    (d / "probe.csv").write_bytes(before + b"\n")  # no longer the file the manifest hashed
    with pytest.raises(probe.ProbeRefused):
        probe.report_only(d)
    assert (d / "probe.csv").read_bytes() == before + b"\n"


def test_report_only_manifest_keeps_the_run_fields_and_refreshes_the_hashes(tmp_path):
    d = _fixture_dir(tmp_path)
    old = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    probe.report_only(d)
    new = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert new["git_commit"] == old["git_commit"] and new["dirty_working_tree"] is False
    assert new["outputs"]["probe.csv"] == old["outputs"]["probe.csv"]
    for name in ("README.md", "summary.md"):
        assert new["outputs"][name] == hashlib.sha256((d / name).read_bytes()).hexdigest()
    block = new["report_regenerated"]
    assert set(block) >= {"git_commit", "dirty_working_tree", "python_provenance"}
    assert len(block["git_commit"]) == 40 and isinstance(block["dirty_working_tree"], bool)
    assert {k: v for k, v in new.items() if k not in ("report_regenerated", "outputs")} == \
        {k: v for k, v in old.items() if k != "outputs"}


def test_report_numbers_equal_a_recomputation_from_the_fixture_csv(tmp_path):
    d = _fixture_dir(tmp_path)
    probe.report_only(d)
    text = (d / "README.md").read_text(encoding="utf-8")
    # items per cell at k = 26: n = 50 -> 31..37, n = 80 -> 40..42; at most 26 items for 26 stops
    assert "At k = 26 and n = 50 the waves have 31 to 37 items and at n = 80 they have 40 to 42 items" in text
    assert "at most 26 items at 26 stops" in text
    # the mixed cell: seed 3 capped with 28 items, seeds 1 and 2 completed with their label counts
    assert ("R = 90, n = 30, k = 26 comes from seed 3, which has 28 items; seeds 1 and 2 have 26 items and "
            "completed with 1 876 915 and 2 646 967 labels") in text
    # seed spread: 620 / 100 = 6.2 in the (k = 10, n = 20, R = 70) cell
    assert "up to about 6.2 times (pickup, single type, k = 10, n = 20, R = 70: 100 to 620 labels)" in text
    assert "label counts equal the single type's in every run that has both" in text
    summary = (d / "summary.md").read_text(encoding="utf-8")
    assert "In capped runs the column count is the count reached before the cap fired" in summary


def test_report_states_typed_label_differences_instead_of_claiming_equality(tmp_path):
    d = _fixture_dir(tmp_path, rows=_fixture_rows(typed_labels_shift=1))
    probe.report_only(d)
    text = (d / "README.md").read_text(encoding="utf-8")
    assert "label counts equal the single type's in every run" not in text
    assert "differ from the single type's in 14 of 14 runs that have both" in text


def test_report_only_cli_flag_and_out_rule(tmp_path):
    d = _fixture_dir(tmp_path)
    assert probe.main(["probe", "--report-only", "--from", str(d)]) == 0
    assert (d / "README.md").exists()
    assert probe.main(["probe", "--report-only", "--from", str(REPO / "docs" / "elsewhere")]) == 2
