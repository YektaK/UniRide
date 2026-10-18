#!/usr/bin/env python3
"""Scaling probe of the exact route enumeration (WP-E1, uniride_core/exact/route_enumeration.py).

Question: how large can ONE wave get before complete enumeration hits its deterministic caps
(2 000 000 columns, 5 000 000 labels; wall-clock safety limit 600 s)? This is a scoping measurement, not a paper
result. The waves are synthetic: students are placed at REAL stop locations of the captured travel-time snapshot of
the 2026-10-05 week (union of the per-date arc slices of week-2026-10-05-4sw5so, one snapshot sha256).

Offline: reads only archive files under docs/paper/results; no AMPL, no DB, no network. Every enumeration runs in its
own subprocess (hard timeout, in-process memory guard) so that a blow-up cannot take the machine down.

Run (from a clean commit, PYTHONPATH = repo root):
    python scripts/probe_exact_enumeration_scaling.py [--out DIR]
Writes DIR/probe.csv, summary.md, README.md, manifest.json (DIR strictly below docs/paper/results, E04 rule).
Internal: ``--worker SPEC_JSON`` runs one enumeration and prints one JSON line.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import platform
import random
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from uniride_core.exact import VehicleTypeSpec, WaveInstance, compute_matrix_sha256  # noqa: E402
from uniride_core.exact.route_enumeration import (  # noqa: E402
    COLUMN_CAP_DEFAULT,
    LABEL_CAP_DEFAULT,
    WALL_CLOCK_LIMIT_DEFAULT,
    enumerate_wave,
)

RESULTS_REL = "docs/paper/results"
RESULTS = REPO / "docs" / "paper" / "results"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "scaling-probe-enumeration"
MATRIX_DIR = "week-2026-10-05-4sw5so"
DEPOT = "D.Kampus"

SIZES = (20, 30, 50, 80)
K_LABELS = ("10", "20", "all")
RIDES = (50, 70, 90)
SEEDS = (1, 2, 3)
TOUR = 150
ANCHOR = 525
SINGLE = "single_4sw5so"
TYPED_FLEETS = ("large+sedan", "large+doblo_cap3")
DROPOFF_CELLS = ((50, "all"),)
SUBPROCESS_TIMEOUT = 660.0  # 600 s wall-clock limit of the enumerator plus margin
MEM_LIMIT_MB = 2500  # in-process guard on the worker's working set (the host had ~3.8 GB free when planned)
SEED_NAMESPACE = "scaling-probe"

FLEET_SOURCES = {
    SINGLE: ("week-2026-10-05-4sw5so", "2026-10-05_R50_repeat1.response.json"),
    "large+sedan": ("week-2026-10-05-fleet-rerun-large-sedan", "run_manifest.json"),
    "large+doblo_cap3": ("week-2026-10-05-fleet-rerun-doblo-cap3", "run_manifest.json"),
}
ROW_FIELDS = ["fleet", "direction", "n", "k_label", "k", "R", "seed", "anchor", "tour", "status", "cap_fired", "items",
              "labels", "columns", "max_labels_per_level", "levels", "seconds", "wall_seconds", "peak_mem_mb", "note"]
NOT_RUN = ("not_run_smaller_capped", "not_run_single_not_complete")


class ProbeRefused(Exception):
    """An input or output rule of the probe is violated."""


# ------------------------------------------------------------------------------------------------ process memory
def current_rss_bytes():
    """Working set of this process in bytes, or None where the host offers no cheap reading."""
    if sys.platform == "win32":
        return _win_memory()[0]
    try:
        with open("/proc/self/statm", encoding="ascii") as fh:
            return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, AttributeError):
        return None


def peak_rss_bytes():
    if sys.platform == "win32":
        return _win_memory()[1]
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak * (1 if sys.platform == "darwin" else 1024)
    except (ImportError, OSError):
        return None


def _win_memory():
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    k32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        return None, None
    return pmc.WorkingSetSize, pmc.PeakWorkingSetSize


class MemoryGuard(Exception):
    pass


# ------------------------------------------------------------------------------------------------ inputs
def _loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader_probe", REPO / "scripts" / "exact_archive_loader.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_union_arcs(source_dir=None):
    """Union of the arcs of every ``*.matrix.json`` slice: ({(o, d): minutes}, [file facts]).

    Refused when the slices declare different snapshots, when two slices disagree on an arc or when an arc is not an
    integer >= 0.
    """
    source_dir = Path(source_dir) if source_dir else RESULTS / MATRIX_DIR
    arcs: dict = {}
    files = []
    for path in sorted(source_dir.glob("*.matrix.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        files.append({"name": path.name, "file_sha256": _sha256_file(path), "declared_sha256": doc["sha256"],
                      "arcs": len(doc["arcs"])})
        for rec in doc["arcs"]:
            value = rec["duration_minutes"]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ProbeRefused(f"{path.name}: arc {rec['origin_code']}->{rec['destination_code']} is not an integer >= 0")
            key = (rec["origin_code"], rec["destination_code"])
            if key in arcs and arcs[key] != value:
                raise ProbeRefused(f"{path.name}: arc {key} disagrees with an earlier slice")
            arcs[key] = value
    if not files:
        raise ProbeRefused(f"no *.matrix.json under {source_dir}")
    if len({f["declared_sha256"] for f in files}) != 1:
        raise ProbeRefused("the matrix slices declare different snapshots")
    return arcs, files


def usable_stops(arcs: dict, depot: str):
    """(every stop that appears, the stops whose full arc set is present).

    A stop is usable when the arcs to and from the depot and from and to every other stop are all in ``arcs``.
    """
    names = {a for a, _ in arcs} | {b for _, b in arcs}
    all_stops = sorted(names - {depot})
    ring = all_stops + [depot]
    usable = [s for s in all_stops
              if all(((s, m) in arcs and (m, s) in arcs) for m in ring if m != s)]
    return all_stops, usable


def real_sw_share(results_root=None):
    """(Sw legs, all legs) over the waves of the single-type archive; identical for every R or refused."""
    loader = _loader()
    camp = loader.load_campaign(Path(results_root or RESULTS) / MATRIX_DIR)
    shares = {}
    for ride in camp.rides:
        waves = camp.waves_for(ride)
        shares[ride] = (sum(w.classes.count("Sw") for w in waves), sum(w.legs for w in waves))
    if len(set(shares.values())) != 1:
        raise ProbeRefused(f"the Sw share differs between R values: {shares}")
    return next(iter(shares.values()))


def fleet_types(fleet: str, results_root=None):
    """(tuple of VehicleTypeSpec, source path) of a fleet as in the archive / WP-E10 manifests."""
    folder, name = FLEET_SOURCES[fleet]
    path = Path(results_root or RESULTS) / folder / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    if fleet == SINGLE:
        tpl = doc["fleet"]["template"]
        return (VehicleTypeSpec("large", tpl["swCapacity"], tpl["soCapacity"], tpl["cooldownMinutes"], None),), path
    out = tuple(VehicleTypeSpec(t["typeId"], t["swCapacity"], t["soCapacity"], t["cooldownMinutes"],
                                t.get("totalCapacity"), t.get("rideLimit"), t.get("tourLimit"))
                for t in doc["fleet_types"])
    return out, path


# ------------------------------------------------------------------------------------------------ synthetic waves
def generate_students(usable, n: int, k: int, seed: int, sw_num: int, sw_den: int):
    """(location_codes, classes) of one synthetic wave: n students at k distinct stops, each stop with >= 1 student.

    The instance depends on (seed, n, k) only, so every R, fleet and direction sees the same students. The k stops are
    a uniform sample without replacement; one student per stop first, the rest spread uniformly at random; the number
    of Sw students is n * sw_num / sw_den rounded half up, placed on uniformly random students.
    """
    usable = tuple(usable)
    if not 1 <= k <= n:
        raise ValueError(f"k must satisfy 1 <= k <= n (k={k}, n={n})")
    if k > len(usable):
        raise ValueError(f"k={k} exceeds the {len(usable)} usable stops")
    rng = random.Random(f"{SEED_NAMESPACE}:{seed}:{n}:{k}")
    chosen = rng.sample(usable, k)
    codes = sorted(chosen + [rng.choice(chosen) for _ in range(n - k)])
    n_sw = (2 * n * sw_num + sw_den) // (2 * sw_den)
    classes = ["Sw"] * n_sw + ["So"] * (n - n_sw)
    rng.shuffle(classes)
    return tuple(codes), tuple(classes)


def build_wave(arcs: dict, depot: str, codes, classes, direction: str, ride: int, tour: int, anchor: int,
               snapshot_sha: str) -> WaveInstance:
    names = [depot] + list(codes)
    matrix = tuple(tuple(0 if (i == j or names[i] == names[j]) else arcs[(names[i], names[j])]
                         for j in range(len(names))) for i in range(len(names)))
    n = len(codes)
    return WaveInstance(
        wave_id=f"synthetic-n{n}", service_date="synthetic", direction=direction, anchor_minutes=anchor,
        max_ride_minutes=ride, max_tour_minutes=tour, depot_code=depot,
        occurrence_ids=tuple(f"s{i + 1}" for i in range(n)), location_codes=tuple(codes), classes=tuple(classes),
        matrix=matrix, matrix_sha256=compute_matrix_sha256(matrix), arc_slice_sha256="synthetic",
        declared_snapshot_sha256=snapshot_sha)


# ------------------------------------------------------------------------------------------------ worker
def worker_main(spec: dict) -> int:
    """Run ONE enumeration and print one JSON line (the parent reads the last line)."""
    arcs, files = load_union_arcs()
    _, usable = usable_stops(arcs, DEPOT)
    sw_num, sw_den = (spec["sw_num"], spec["sw_den"]) if "sw_num" in spec else real_sw_share()
    codes, classes = generate_students(usable, spec["n"], spec["k"], spec["seed"], sw_num, sw_den)
    wave = build_wave(arcs, DEPOT, codes, classes, spec["direction"], spec["R"], spec.get("tour", TOUR),
                      spec.get("anchor", ANCHOR), files[0]["declared_sha256"])
    types, _ = fleet_types(spec["fleet"])
    limit = int(spec.get("mem_limit_mb", MEM_LIMIT_MB)) * 1024 * 1024
    check = current_rss_bytes() is not None

    def clock():
        if check:
            used = current_rss_bytes()
            if used is not None and used > limit:
                raise MemoryGuard(f"working set {used >> 20} MB above the {limit >> 20} MB guard")
        return time.monotonic()

    kwargs = {"clock": clock}
    if "label_cap" in spec:
        kwargs["label_cap"] = spec["label_cap"]
    if "column_cap" in spec:
        kwargs["column_cap"] = spec["column_cap"]
    out = {"items": len({(c, k) for c, k in zip(codes, classes)})}
    try:
        res = enumerate_wave(wave, types, **kwargs)
        out.update(status=res.cap_fired if res.status == "count_cap" else res.status,
                   cap_fired=res.cap_fired or "", labels=res.label_count, columns=res.column_count,
                   max_labels_per_level=max(res.labels_per_level, default=0), levels=len(res.labels_per_level),
                   seconds=round(res.elapsed_seconds, 3))
    except MemoryGuard as exc:
        out.update(status="memory_guard_abort", cap_fired="", note=str(exc))
    except MemoryError:
        out.update(status="memory_error", cap_fired="", note="MemoryError")
    peak = peak_rss_bytes()
    out["peak_mem_mb"] = round(peak / 2 ** 20, 1) if peak is not None else ""
    print(json.dumps(out), flush=True)
    return 0


def _kill_tree(proc: subprocess.Popen) -> None:
    """Stop the subprocess WE started, by PID (the venv launcher has a child on Windows)."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=30)
        proc.kill()
    except (OSError, subprocess.SubprocessError):
        pass


def run_subprocess(argv, timeout: float, env=None) -> dict:
    """Run ``argv``; the last stdout line must be a JSON object. Timeout and crash are reported as a status."""
    t0 = time.perf_counter()
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=30)
        except subprocess.SubprocessError:
            pass
        return {"status": "subprocess_timeout", "wall_seconds": round(time.perf_counter() - t0, 3),
                "note": f"killed after {timeout} s"}
    wall = round(time.perf_counter() - t0, 3)
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    parsed = None
    if proc.returncode == 0 and lines:
        try:
            parsed = json.loads(lines[-1])
        except ValueError:
            parsed = None
        if not isinstance(parsed, dict):
            parsed = None
    if parsed is None:
        return {"status": "subprocess_crash", "returncode": proc.returncode, "wall_seconds": wall,
                "stderr_tail": (stderr or "")[-300:], "note": f"exit {proc.returncode}"}
    parsed["wall_seconds"] = wall
    return parsed


def run_enumeration_subprocess(spec: dict, timeout: float = SUBPROCESS_TIMEOUT) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return run_subprocess([sys.executable, str(Path(__file__).resolve()), "--worker", json.dumps(spec)], timeout, env)


# ------------------------------------------------------------------------------------------------ grid
def _row(spec: dict, result: dict) -> dict:
    row = {f: "" for f in ROW_FIELDS}
    row.update({f: spec[f] for f in ("fleet", "direction", "n", "k_label", "k", "R", "seed", "anchor", "tour")})
    row.update({f: result[f] for f in ROW_FIELDS if f in result})
    return row


def run_grid(runner, *, sizes=SIZES, k_choices, rides=RIDES, seeds=SEEDS, typed_fleets=TYPED_FLEETS,
             dropoff_cells=DROPOFF_CELLS, single_fleet=SINGLE, log=None) -> list:
    """The probe grid; ``runner(spec) -> dict`` measures one enumeration.

    The single type runs the whole grid; typed fleets run only where the single type completed (all seeds). Along n
    (ascending) a cell that did not complete stops every larger size of the same (fleet, direction, k, R). k > n is
    not generated. The dropoff check runs the named (n, k) cells for the same fleets, with the same typed rule.
    """
    sizes = tuple(sorted(sizes))
    rows: list = []
    single_ok: dict = {}

    def emit(spec, result):
        row = _row(spec, result)
        rows.append(row)
        if log:
            log(row)
        return row

    def spec_for(fleet, direction, n, kl, kv, ride, seed):
        return {"fleet": fleet, "direction": direction, "n": n, "k_label": kl, "k": kv, "R": ride, "seed": seed,
                "anchor": ANCHOR, "tour": TOUR}

    def run_cell(fleet, direction, n, kl, kv, ride, blocked, note=""):
        """True when every seed completed."""
        if blocked:
            for seed in seeds:
                emit(spec_for(fleet, direction, n, kl, kv, ride, seed), {"status": blocked, "note": note})
            return False
        ok = True
        for seed in seeds:
            spec = spec_for(fleet, direction, n, kl, kv, ride, seed)
            result = runner(spec)
            emit(spec, result)
            ok = ok and result.get("status") == "complete"
        return ok

    for fleet in (single_fleet,) + tuple(typed_fleets):
        typed = fleet != single_fleet
        for kl, kv in k_choices:
            for ride in rides:
                capped_at = None
                for n in sizes:
                    if kv > n:
                        continue
                    key = ("pickup", n, kl, ride)
                    if capped_at is not None:
                        blocked, note = "not_run_smaller_capped", f"n={capped_at} did not complete"
                    elif typed and not single_ok.get(key, False):
                        blocked, note = "not_run_single_not_complete", "single type did not complete at this size"
                    else:
                        blocked, note = None, ""
                    ok = run_cell(fleet, "pickup", n, kl, kv, ride, blocked, note)
                    if not typed:
                        single_ok[key] = ok
                    if blocked is None and not ok:
                        capped_at = n
    kmap = dict(k_choices)
    for fleet in (single_fleet,) + tuple(typed_fleets):
        typed = fleet != single_fleet
        for n, kl in dropoff_cells:
            kv = kmap[kl]
            if kv > n:
                continue
            for ride in rides:
                key = ("dropoff", n, kl, ride)
                blocked = "not_run_single_not_complete" if typed and not single_ok.get(key, False) else None
                ok = run_cell(fleet, "dropoff", n, kl, kv, ride, blocked,
                              "single type did not complete at this size" if blocked else "")
                if not typed:
                    single_ok[key] = ok
    return rows


# ------------------------------------------------------------------------------------------------ summary
def _fmt(value) -> str:
    return f"{int(value):,}".replace(",", " ")


def summarize_cells(rows: list) -> list:
    """One entry per (fleet, direction, k, R) with the largest complete n and the first capped n."""
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["fleet"], r["direction"], int(r["k"]), r["k_label"], int(r["R"])), []).append(r)
    order = {f: i for i, f in enumerate((SINGLE,) + TYPED_FLEETS)}
    cells = []
    for (fleet, direction, kv, kl, ride), rs in sorted(groups.items(), key=lambda kv_: (
            kv_[0][1] != "pickup", order.get(kv_[0][0], 99), kv_[0][2], kv_[0][4])):
        by_n: dict = {}
        for r in rs:
            by_n.setdefault(int(r["n"]), []).append(r)
        info, complete_ns, capped = {}, [], []
        for n, nr in sorted(by_n.items()):
            ran = [r for r in nr if r["status"] not in NOT_RUN]
            bad = sorted({r["status"] for r in ran if r["status"] != "complete"})
            entry = {"runs": len(ran), "not_run": len(nr) - len(ran),
                     "not_run_status": sorted({r["status"] for r in nr if r["status"] in NOT_RUN}),
                     "bad_seeds": sum(r["status"] != "complete" for r in ran), "bad_statuses": bad}
            for field, name in (("labels", "labels"), ("columns", "columns")):
                vals = [int(r[field]) for r in ran if r[field] != ""]
                entry[f"{name}_max"] = max(vals) if vals else None
                entry[f"{name}_min"] = min(vals) if vals else None
            info[n] = entry
            if ran and not bad:
                complete_ns.append(n)
            if bad:
                capped.append(n)
        first = min(capped) if capped else None
        cells.append({"fleet": fleet, "direction": direction, "k": kv, "k_label": kl, "R": ride, "by_n": info,
                      "largest_complete_n": max(complete_ns) if complete_ns else None, "first_capped_n": first,
                      "first_capped_status": "+".join(info[first]["bad_statuses"]) if first else "",
                      "first_capped_seeds": f"{info[first]['bad_seeds']}/{info[first]['runs']}" if first else ""})
    return cells


def summary_markdown(rows: list, facts: dict) -> str:
    cells = summarize_cells(rows)
    lines = ["# Scaling probe of the exact route enumeration: summary", "",
             "Synthetic waves at real stop locations; scoping measurement, no paper claim. Generated by "
             "`scripts/probe_exact_enumeration_scaling.py` from `probe.csv`.", ""]
    if "sw_num" in facts:
        lines += [f"- Sw share used: {facts['sw_num']}/{facts['sw_den']} of the legs of the week-2026-10-05-4sw5so archive.", ""]
    lines += [f"- Caps: {_fmt(COLUMN_CAP_DEFAULT)} columns, {_fmt(LABEL_CAP_DEFAULT)} labels, wall-clock "
              f"{WALL_CLOCK_LIMIT_DEFAULT:.0f} s; subprocess timeout {SUBPROCESS_TIMEOUT:.0f} s.",
              "- A size counts as completed only when every seed completed; `capped` is any other status of any seed.",
              "- Labels and columns are the maximum over the seeds that ran (one value per n).", ""]
    for direction in ("pickup", "dropoff"):
        sub = [c for c in cells if c["direction"] == direction]
        if not sub:
            continue
        lines += [f"## {direction}", "",
                  "| fleet | k | R | largest n completed | first n capped (status, capped seeds/runs) | not run | "
                  "labels by n (max over seeds) | columns by n (max over seeds) |",
                  "|---|---|---|---|---|---|---|---|"]
        for c in sub:
            ns = sorted(c["by_n"])
            lab = "; ".join(f"{n}: {_fmt(c['by_n'][n]['labels_max'])}" for n in ns if c["by_n"][n]["labels_max"] is not None)
            col = "; ".join(f"{n}: {_fmt(c['by_n'][n]['columns_max'])}" for n in ns if c["by_n"][n]["columns_max"] is not None)
            skipped = ", ".join(f"{n} ({'/'.join(c['by_n'][n]['not_run_status'])})" for n in ns if c["by_n"][n]["not_run"])
            first = (f"{c['first_capped_n']} ({c['first_capped_status']}, {c['first_capped_seeds']})"
                     if c["first_capped_n"] else "none")
            largest = c["largest_complete_n"] if c["largest_complete_n"] is not None else "none"
            lines.append(f"| {c['fleet']} | {c['k_label']} ({c['k']}) | {c['R']} | {largest} | {first} | "
                         f"{skipped or '-'} | {lab or '-'} | {col or '-'} |")
        lines.append("")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------------ outputs
def check_out_dir(out: Path, repo: Path) -> None:
    out_r, repo_r = Path(out).resolve(), Path(repo).resolve()
    try:
        rel = out_r.relative_to(repo_r)
    except ValueError:
        return  # outside the repository: excludes nothing from the dirty check
    results = repo_r / RESULTS_REL
    if out_r == results or results not in out_r.parents:
        raise ProbeRefused(f"--out must lie strictly below {RESULTS_REL}/ when inside the repository "
                           f"(got {rel.as_posix() or '.'})")


def _git(*args) -> str:
    try:
        done = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=120, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProbeRefused(f"git {' '.join(args[:2])} failed: {exc}") from exc
    return done.stdout.strip()


def git_state(out: Path) -> tuple:
    spec = ["status", "--porcelain"]
    try:
        spec += ["--", ".", f":(exclude){Path(out).resolve().relative_to(REPO.resolve()).as_posix()}"]
    except ValueError:
        pass
    return _git("rev-parse", "HEAD"), bool(_git(*spec))


def python_provenance() -> dict:
    import uniride_core

    try:
        return {"uniride_core": Path(uniride_core.__file__).resolve().relative_to(REPO.resolve()).as_posix()}
    except ValueError as exc:
        raise ProbeRefused("uniride_core is imported from outside this checkout; set PYTHONPATH to the repo root") from exc


def _write(path: Path, text: str) -> None:
    Path(path).write_bytes(text.encode("utf-8"))  # LF only


def csv_text(rows: list) -> str:
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=ROW_FIELDS, lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    return buf.getvalue()


def readme_text(facts: dict, rows: list) -> str:
    ran = [r for r in rows if r["status"] not in NOT_RUN]
    counts: dict = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    peaks = [float(r["peak_mem_mb"]) for r in ran if r["peak_mem_mb"] != ""]
    status_line = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    return "\n".join([
        "# Scaling probe: exact route enumeration (scoping measurement)", "",
        "Facts only. The probe makes no paper claim: no superiority, causality or proof statement follows from it.", "",
        "## What was measured",
        "- `uniride_core/exact/route_enumeration.py` (WP-E1) run on synthetic waves, one subprocess per enumeration "
        f"(hard timeout {SUBPROCESS_TIMEOUT:.0f} s, in-process working-set guard {facts['mem_limit_mb']} MB), serially.",
        f"- Caps in force: {_fmt(COLUMN_CAP_DEFAULT)} columns, {_fmt(LABEL_CAP_DEFAULT)} labels, wall-clock limit "
        f"{WALL_CLOCK_LIMIT_DEFAULT:.0f} s. Tour cap {TOUR}; pickup anchor {ANCHOR} (dropoff run with the same anchor).",
        "", "## The waves are synthetic",
        "- Travel times are the REAL captured matrix: the union of the arcs of the per-date `*.matrix.json` slices of "
        f"`week-2026-10-05-4sw5so` (one snapshot, sha256 `{facts['snapshot_sha256']}`), integer minutes, depot {DEPOT}.",
        f"- {len(facts['all_stops'])} distinct stop locations appear in the archive; {len(facts['usable'])} have their full "
        f"arc set (to and from the depot and every other stop) and are used. Excluded: "
        f"{', '.join(sorted(set(facts['all_stops']) - set(facts['usable']))) or 'none'} "
        "(the arcs between them are not in the archive).",
        f"- There are at most {len(facts['usable'])} real locations, so a larger n means more students per location "
        f"(n = 80 on {len(facts['usable'])} locations is about {80 / len(facts['usable']):.1f} students per location).",
        "- Students are placed at k distinct stops (k = 10, 20, all usable; k <= n): a uniform sample without replacement, "
        "one student per chosen stop first, the rest spread uniformly at random.",
        f"- Class: the number of Sw students is n x {facts['sw_num']}/{facts['sw_den']} (the Sw share of the "
        "legs of the archive waves) rounded half up, on uniformly random students. The class is drawn independently of "
        "the stop, so one stop can hold Sw and So students (two items at one location). In the archive a stop code "
        "carries its class.",
        f"- Seeds {', '.join(str(s) for s in facts['seeds'])} per cell; the instance is `random.Random(\"scaling-probe:"
        "<seed>:<n>:<k>\")`, identical for every R, fleet and direction.", "",
        "## Grid and stopping rules",
        f"- n in {', '.join(str(n) for n in facts['sizes'])}; R in {', '.join(str(r) for r in facts['rides'])}; "
        "fleets: single type 4 Sw / 5 So (large); large + sedan (0 Sw / 4 So); large + Doblo (minivan 1 Sw / 3 So, "
        "total capacity 3), types as in the WP-E10 manifests.",
        "- Typed fleets ran only where the single type completed (all seeds) at that (direction, n, k, R).",
        "- Along n, a cell with any seed not complete stops the larger sizes of the same (fleet, direction, k, R): "
        "status `not_run_smaller_capped`; `not_run_single_not_complete` marks typed cells whose single-type cell did "
        "not complete.",
        f"- Dropoff direction check: n = {facts['dropoff'][0][0]}, k = {facts['dropoff'][0][1]}, every fleet under the "
        "same typed rule, no early stop.", "",
        "## Statuses",
        "`complete`; `column_cap`, `label_cap` (deterministic caps); `timing_dependent_abort` (600 s wall-clock "
        "limit); `memory_guard_abort` (probe guard on the working set, not an enumerator cap; labels and columns "
        "unknown); `memory_error`; `subprocess_timeout`, `subprocess_crash` (harness).", "",
        "## Run",
        f"- Rows: {len(rows)} ({len(ran)} enumerations run). Status counts: {status_line}.",
        f"- Peak working set over the runs: {max(peaks) if peaks else 'n/a'} MB.",
        f"- Total wall time of the probe: {facts['total_seconds']:.0f} s.",
        "- Files: `probe.csv` (one row per run), `summary.md`, `manifest.json` (commit, dirty flag, matrix sha256 values, "
        "seeds, caps, versions, `python_provenance`).",
        f"- Reproduce: `PYTHONPATH=<repo root> python scripts/probe_exact_enumeration_scaling.py` from a clean commit.", ""])


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--worker", default=None, help="internal: run one enumeration from a JSON spec")
    ap.add_argument("--timeout", type=float, default=SUBPROCESS_TIMEOUT)
    ap.add_argument("--mem-limit-mb", type=int, default=MEM_LIMIT_MB)
    ap.add_argument("--sizes", default=None)
    ap.add_argument("--rides", default=None)
    ap.add_argument("--seeds", default=None)
    args = ap.parse_args(argv[1:])
    if args.worker is not None:
        return worker_main(json.loads(args.worker))
    out = Path(args.out)
    try:
        check_out_dir(out, REPO)
        provenance = python_provenance()
    except ProbeRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    sizes = tuple(int(x) for x in args.sizes.split(",")) if args.sizes else SIZES
    rides = tuple(int(x) for x in args.rides.split(",")) if args.rides else RIDES
    seeds = tuple(int(x) for x in args.seeds.split(",")) if args.seeds else SEEDS
    overridden = (sizes, rides, seeds) != (SIZES, RIDES, SEEDS)
    arcs, files = load_union_arcs()
    all_stops, usable = usable_stops(arcs, DEPOT)
    sw_num, sw_den = real_sw_share()
    k_choices = [(label, 10 if label == "10" else 20 if label == "20" else len(usable)) for label in K_LABELS]
    print(f"stops in archive {len(all_stops)}, usable {len(usable)}, Sw share {sw_num}/{sw_den} "
          f"({float(Fraction(sw_num, sw_den)):.4f}); grid sizes {sizes} rides {rides} seeds {seeds}", flush=True)
    t0 = time.perf_counter()

    def runner(spec):
        return run_enumeration_subprocess({**spec, "sw_num": sw_num, "sw_den": sw_den, "mem_limit_mb": args.mem_limit_mb},
                                          args.timeout)

    def log(row):
        print(f"{row['fleet']:17s} {row['direction']:7s} n={row['n']:<3} k={row['k_label']:<3} R{row['R']} s{row['seed']} "
              f"{row['status']:26s} labels={row['labels']!s:>9} cols={row['columns']!s:>9} "
              f"{row['wall_seconds']!s:>8}s mem={row['peak_mem_mb']!s}MB", flush=True)

    rows = run_grid(runner, sizes=sizes, k_choices=k_choices, rides=rides, seeds=seeds, log=log)
    total = time.perf_counter() - t0
    facts = {"sw_num": sw_num, "sw_den": sw_den, "all_stops": all_stops, "usable": usable,
             "snapshot_sha256": files[0]["declared_sha256"], "seeds": seeds, "sizes": sizes, "rides": rides,
             "dropoff": list(DROPOFF_CELLS), "mem_limit_mb": args.mem_limit_mb, "total_seconds": total}
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "probe.csv", csv_text(rows))
    _write(out / "summary.md", summary_markdown(rows, facts))
    _write(out / "README.md", readme_text(facts, rows))
    commit, dirty = git_state(out)
    sources = {}
    for fleet in (SINGLE,) + TYPED_FLEETS:
        types, path = fleet_types(fleet)
        sources[fleet] = {"file": path.relative_to(REPO).as_posix(), "sha256": _sha256_file(path),
                          "types": [t.__dict__ for t in types]}
    peaks = [float(r["peak_mem_mb"]) for r in rows if r["peak_mem_mb"] != ""]
    manifest = {
        "work_package": "scaling probe of WP-E1 route enumeration (scoping measurement, no paper claim)",
        "git_commit": commit, "dirty_working_tree": dirty,
        "matrix_source": {"directory": f"{RESULTS_REL}/{MATRIX_DIR}", "declared_snapshot_sha256": files[0]["declared_sha256"],
                          "files": files, "arcs_in_union": len(arcs)},
        "fleet_sources": sources,
        "locations": {"depot": DEPOT, "stops_in_archive": all_stops, "usable_stops": usable},
        "sw_share": {"sw_legs": sw_num, "legs": sw_den},
        "seeds": list(seeds), "seed_rule": f'random.Random("{SEED_NAMESPACE}:<seed>:<n>:<k>")',
        "grid": {"sizes": list(sizes), "k": dict(k_choices), "rides": list(rides), "tour": TOUR, "anchor": ANCHOR,
                 "dropoff_cells": [list(c) for c in DROPOFF_CELLS], "overridden_from_default": overridden},
        "caps": {"column_cap": COLUMN_CAP_DEFAULT, "label_cap": LABEL_CAP_DEFAULT,
                 "wall_clock_limit_seconds": WALL_CLOCK_LIMIT_DEFAULT, "subprocess_timeout_seconds": args.timeout,
                 "memory_guard_mb": args.mem_limit_mb},
        "python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
        "host_os": platform.system(), "host_release": platform.release(), "cpu_count": os.cpu_count(),
        "packages": {"third_party": []}, "python_provenance": provenance,
        "outputs": {n: _sha256_file(out / n) for n in ("probe.csv", "summary.md", "README.md")},
        "rows": len(rows), "enumerations_run": sum(r["status"] not in NOT_RUN for r in rows),
        "total_wall_seconds": round(total, 1), "peak_working_set_mb_max": max(peaks) if peaks else None,
        "claim": "none: synthetic waves, scoping measurement only",
    }
    _write(out / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out} in {total:.0f} s (dirty={dirty}, commit {commit[:8]})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
