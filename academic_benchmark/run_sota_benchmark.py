"""
SOTA Benchmark v5.0 — TSP-native TSPLIB Suite

Solvers: E²BSO, R²DMA, P-AOEA  |  Source: sota_tsp/
Features:
  - ALL TSPLIB problems selectable (optimal shown when known, else N/A)
  - Sequential execution by default on Windows (--parallel for ProcessPool)
  - Numba-adaptive LS time budgets (no more 85-second runs without Numba)
  - Deterministic per-run seeding
  - CRLF-safe TSPLIB parser
  - Rich UI: box-drawing banner, live progress, ETA, ranking table
  - Append-only CSV + JSON + summary text output
  - Ctrl+C saves all completed results
"""

import argparse
import concurrent.futures
import csv
import io
import json
import math
import os
import re
import signal
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

VERSION = "5.0.0"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TSPLIB_DIR = os.path.join(SCRIPT_DIR, "tsplib_data")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "sota_results")

# ── Known TSPLIB optimal values ──────────────────────────────────────────────
TSPLIB_OPTIMALS: Dict[str, int] = {
    "berlin52": 7542, "eil51": 426, "eil76": 538, "st70": 675,
    "kroa100": 21282, "krob100": 22141, "kroc100": 20749, "krod100": 21294,
    "kroe100": 22068, "eil101": 629, "pr107": 44303, "pr124": 59030,
    "bier127": 118282, "ch130": 6110, "ch150": 6528, "kroa150": 26524,
    "krob150": 26130, "pr152": 73682, "u159": 42080, "rat195": 2323,
    "d198": 15780, "kroa200": 29368, "krob200": 29437, "ts225": 126643,
    "tsp225": 3916, "pr226": 80369, "gil262": 2378, "pr264": 49135,
    "a280": 2579, "pr299": 48191, "lin318": 42029, "rd400": 15281,
    "fl417": 11861, "pr439": 107217, "pcb442": 50778, "d493": 35002,
    "u574": 36905, "rat575": 6773, "p654": 34643, "d657": 48912,
    "u724": 41910, "rat783": 8806, "pr1002": 259045, "u1060": 224094,
    "vm1084": 239297, "pcb1173": 56892, "d1291": 50801, "rl1304": 252948,
    "rl1323": 270199, "nrw1379": 56638, "fl1400": 20127, "u1432": 152970,
    "fl1577": 22249, "d1655": 62128, "vm1748": 336556, "u1817": 57201,
    "rl1889": 316536, "d2103": 80450, "u2152": 64253, "u2319": 234256,
    "pr2392": 378032, "pcb3038": 137694, "fl3795": 28772, "fnl4461": 182566,
    # Additional entries for files in tsplib_data/
    "lin105": 14379, "rd100": 7910, "pr136": 96772, "pr144": 58537,
}

_shutdown_requested = False


# ── System capability detection ──────────────────────────────────────────────

def _detect_numba() -> bool:
    try:
        _ls_path = os.path.join(SCRIPT_DIR, "sota_tsp")
        if _ls_path not in sys.path:
            sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
        from academic_benchmark.sota_tsp.ls_engine import _NUMBA_OK
        return bool(_NUMBA_OK)
    except Exception:
        return False


_NUMBA_AVAILABLE = _detect_numba()


# ── TSPLIB Parser ─────────────────────────────────────────────────────────────

def parse_tsplib(filepath: str) -> Optional[Dict[str, Any]]:
    with open(filepath, "r", errors="replace") as f:
        raw = f.read()
    # Normalise line endings (CRLF → LF)
    content = raw.replace("\r\n", "\n").replace("\r", "\n")

    name_m = re.search(r"NAME\s*:\s*(\S+)", content, re.I)
    dim_m = re.search(r"DIMENSION\s*:\s*(\d+)", content, re.I)
    ewt_m = re.search(r"EDGE_WEIGHT_TYPE\s*:\s*(\S+)", content, re.I)
    if not dim_m:
        return None

    name = name_m.group(1).lower() if name_m else os.path.basename(filepath).replace(".tsp", "")
    dimension = int(dim_m.group(1))
    ewt = ewt_m.group(1) if ewt_m else "EUC_2D"

    coords: List[Tuple[float, float]] = []
    coord_m = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:\nEOF|\nDISPLAY_DATA_SECTION|$)",
        content, re.DOTALL | re.I,
    )
    if coord_m:
        for line in coord_m.group(1).strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    coords.append((float(parts[1]), float(parts[2])))
                except ValueError:
                    pass

    if not coords:
        return None

    return {
        "name": name,
        "dimension": dimension,
        "edge_weight_type": ewt,
        "coordinates": coords,
        "optimal": TSPLIB_OPTIMALS.get(name),
    }


def load_problems(size_limit: int = 500) -> Dict[str, Dict[str, Any]]:
    """Load ALL .tsp files up to size_limit nodes — optimal is optional."""
    os.makedirs(TSPLIB_DIR, exist_ok=True)
    problems: Dict[str, Dict[str, Any]] = {}
    for fname in sorted(os.listdir(TSPLIB_DIR)):
        if not fname.endswith(".tsp"):
            continue
        path = os.path.join(TSPLIB_DIR, fname)
        p = parse_tsplib(path)
        if p and p["dimension"] <= size_limit:
            problems[p["name"]] = p
    return problems


# ── Adaptive solver config ────────────────────────────────────────────────────

def _make_solver_config(algo_name: str, n: int, numba_ok: bool) -> Dict[str, Any]:
    """Return keyword args for each solver, tuned for Numba availability."""
    if numba_ok:
        ls_limit = 0.5
        pop = max(20, min(60, n // 2))
        max_iter = max(200, min(500, n * 5))
    else:
        # Python-fallback 2-opt is ~10-50× slower — shrink time budgets
        ls_limit = max(0.02, min(0.12, 0.003 * n))
        pop = max(15, min(35, n // 3))
        max_iter = max(100, min(250, n * 3))

    configs = {
        "E2BSO-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "ls_intensity_normal": "light",
            "ls_intensity_compress": "moderate",
        },
        "R2DMA-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
        },
        "P-AOEA-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
        },
    }
    return configs.get(algo_name, {})


# ── Solver worker (module-level for multiprocessing pickling) ─────────────────

def _run_solver_task(args: Tuple) -> Dict[str, Any]:
    algo_name, coordinates, seed, run_idx, n_nodes, optimal, numba_ok = args
    try:
        _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from academic_benchmark.sota_tsp import (
            E2BSO_TSP, R2DMA_TSP, PAOEA_TSP,
            E2BSOTSPConfig, R2DMATSPConfig, PAOEAConfig,
        )
    except ImportError as exc:
        return {"error": f"Import failed: {exc}", "algorithm": algo_name}

    cfg = _make_solver_config(algo_name, n_nodes, numba_ok)

    def _build(seed_val):
        if algo_name == "E2BSO-TSP":
            return E2BSO_TSP(E2BSOTSPConfig(seed=seed_val, **cfg))
        if algo_name == "R2DMA-TSP":
            return R2DMA_TSP(R2DMATSPConfig(seed=seed_val, **cfg))
        if algo_name == "P-AOEA-TSP":
            return PAOEA_TSP(PAOEAConfig(seed=seed_val, **cfg))
        return None

    solver = _build(seed)
    if solver is None:
        return {"error": f"Unknown algorithm: {algo_name}"}

    try:
        t0 = time.perf_counter()
        result = solver.solve(coordinates)
        elapsed = time.perf_counter() - t0
    except Exception as exc:
        import traceback
        return {"error": f"{algo_name} crashed: {exc}\n{traceback.format_exc()}", "algorithm": algo_name}

    gap = float("nan")
    if optimal and optimal > 0:
        gap = (result.tour_length - optimal) / optimal * 100.0

    return {
        "algorithm": algo_name,
        "run": run_idx + 1,
        "seed": seed,
        "dimension": n_nodes,
        "optimal": optimal,
        "tour_cost": int(result.tour_length),
        "gap_pct": round(gap, 4),
        "elapsed_sec": round(elapsed, 3),
        "iterations": result.iterations,
        "history": result.history,
    }


# ── ETA tracker ───────────────────────────────────────────────────────────────

class _ETATracker:
    def __init__(self):
        self._times: List[float] = []

    def record(self, elapsed: float):
        self._times.append(elapsed)

    def estimate_remaining(self, tasks_left: int) -> Optional[float]:
        if not self._times:
            return None
        avg = sum(self._times) / len(self._times)
        return avg * tasks_left


# ── Signal handler ────────────────────────────────────────────────────────────

def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!] Shutdown requested — saving completed results...")


signal.signal(signal.SIGINT, _signal_handler)


# ── Stat helpers ──────────────────────────────────────────────────────────────

def _stdev(vals: List[float]) -> float:
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


def _fmt_time(s: float) -> str:
    if s < 60:
        return f"{s:.1f}s"
    m = int(s // 60)
    return f"{m}m{int(s % 60):02d}s"


def _gap_str(gap: float) -> str:
    return f"{gap:.2f}%" if not math.isnan(gap) else "  N/A "


# ── UI: Banner ────────────────────────────────────────────────────────────────

def _print_banner(n_problems: int, algos: List[str], runs: int, workers: int, sequential: bool):
    W = 62
    border = "=" * W
    mode = "sequential" if sequential else f"{workers} workers"
    numba_tag = "ACTIVE" if _NUMBA_AVAILABLE else "inactive (slower)"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        border,
        f"  SOTA BENCHMARK v{VERSION} — TSP-native TSPLIB Suite",
        f"  E2BSO  .  R2DMA  .  P-AOEA     {ts}",
        border,
        f"  Numba  : {numba_tag}",
        f"  Mode   : {mode}",
        f"  Problems: {n_problems}  |  Algorithms: {len(algos)}  |  Runs: {runs}",
        border,
    ]
    print("\n" + "\n".join(lines))


# ── UI: Per-problem section header ────────────────────────────────────────────

def _print_problem_header(name: str, dim: int, optimal: Optional[int]):
    opt_str = str(optimal) if optimal else "N/A"
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  Problem : {name}  (n={dim}, optimal={opt_str})")
    print(sep)


# ── UI: Per-result line ───────────────────────────────────────────────────────

def _print_result_line(completed: int, total: int, res: Dict, eta: Optional[float]):
    gap = _gap_str(res["gap_pct"])
    eta_str = f"ETA {_fmt_time(eta)}" if eta else ""
    print(
        f"  [{completed:>{len(str(total))}}/{total}] "
        f"{res['algorithm']:<12} run {res['run']}  "
        f"cost={res['tour_cost']:>8}  gap={gap}  "
        f"{_fmt_time(res['elapsed_sec']):<7}  {eta_str}"
    )


# ── UI: Per-problem mini-summary ──────────────────────────────────────────────

def _print_problem_mini_summary(pname: str, results: List[Dict], algos: List[str]):
    print()
    for algo in algos:
        rs = [r for r in results if r["algorithm"] == algo and r.get("problem") == pname]
        if not rs:
            continue
        costs = [r["tour_cost"] for r in rs]
        gaps = [r["gap_pct"] for r in rs if not math.isnan(r["gap_pct"])]
        star = "*" if (gaps and min(gaps) < 1.0) else " "
        gap_part = f"gap_avg={statistics.mean(gaps):.2f}%" if gaps else "gap=N/A"
        print(
            f"  {star} {algo:<12} best={min(costs)}  mean={statistics.mean(costs):.0f}"
            f"  (+-{_stdev(costs):.0f})  {gap_part}"
        )


# ── UI: Final summary tables ──────────────────────────────────────────────────

def _box_summary(all_results: List[Dict], problems: Dict[str, Dict],
                 algos: List[str], t_total: float, out_dir: str, ts: str):
    W = 82
    sep_top    = "+" + "-" * (W - 2) + "+"
    sep_header = "|" + "-" * (W - 2) + "|"

    col_h = f"{'Algorithm':<13}|{'Best':>8}|{'Mean':>10}|{'StdDev':>8}|{'Gap(B)':>9}|{'Gap(A)':>9}|{'Time':>8}"
    lines = [
        "=" * W,
        f"  SOTA BENCHMARK RESULTS v{VERSION}",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Total time: {_fmt_time(t_total)}  |  Runs: {len(all_results)}",
        "=" * W, "",
    ]

    # Per-problem tables
    for pname, pinfo in problems.items():
        p_results = [r for r in all_results if r.get("problem") == pname]
        if not p_results:
            continue
        opt = pinfo.get("optimal")
        opt_str = str(opt) if opt else "N/A"
        lines.append(sep_top)
        lines.append(f"| {pname} (n={pinfo['dimension']}, optimal={opt_str})" + " " * max(0, W - 4 - len(pname) - len(str(pinfo['dimension'])) - len(opt_str) - 20) + "|")
        lines.append(f"| {col_h} |")
        lines.append(sep_header)
        best_cost_overall = min(r["tour_cost"] for r in p_results)
        for algo in algos:
            rs = [r for r in p_results if r["algorithm"] == algo]
            if not rs:
                continue
            costs = [r["tour_cost"] for r in rs]
            gaps = [r["gap_pct"] for r in rs if not math.isnan(r["gap_pct"])]
            times = [r["elapsed_sec"] for r in rs]
            bc = min(costs)
            mc = statistics.mean(costs)
            sc = _stdev(costs)
            bg = min(gaps) if gaps else float("nan")
            ag = statistics.mean(gaps) if gaps else float("nan")
            at = statistics.mean(times)
            star = "*" if bc <= best_cost_overall else " "
            lines.append(
                f"|{star}{algo:<12}|{bc:>8}|{mc:>10.1f}|{sc:>8.1f}|"
                f"{_gap_str(bg):>9}|{_gap_str(ag):>9}|{at:>7.2f}s|"
            )
        lines.append(sep_top)
        lines.append("")

    # Overall ranking (only for problems with known optimals)
    ranking_data: Dict[str, List[float]] = {a: [] for a in algos}
    for r in all_results:
        if not math.isnan(r["gap_pct"]):
            ranking_data[r["algorithm"]].append(r["gap_pct"])

    ranked = [(a, statistics.mean(g)) for a, g in ranking_data.items() if g]
    ranked.sort(key=lambda x: x[1])

    if ranked:
        lines += ["", "  OVERALL RANKING (avg gap — problems with known optimal)", "-" * 50]
        for pos, (algo, avg_gap) in enumerate(ranked, 1):
            all_gaps = ranking_data[algo]
            best_gap = min(all_gaps)
            lines.append(f"  {pos}. {algo:<13} avg={avg_gap:.2f}%  best={best_gap:.2f}%")
        lines.append("")

    summary_text = "\n".join(lines)
    print("\n" + summary_text)

    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, f"sota_summary_{ts}.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(f"  Summary : {summary_path}")

    json_path = os.path.join(out_dir, f"sota_results_{ts}.json")
    # Build per-problem convergence history (best run per algo)
    convergence: Dict[str, Any] = {}
    for pname in problems:
        p_res = [r for r in all_results if r.get("problem") == pname]
        for algo in algos:
            rs = [r for r in p_res if r["algorithm"] == algo]
            if rs:
                best_run = min(rs, key=lambda r: r["tour_cost"])
                key = f"{pname}_{algo}"
                convergence[key] = {
                    "problem": pname, "algorithm": algo,
                    "best_cost": best_run["tour_cost"],
                    "history": best_run.get("history", []),
                }

    with open(json_path, "w", encoding="utf-8") as f:
        clean = [{k: v for k, v in r.items() if k != "history"} for r in all_results]
        json.dump({
            "version": VERSION, "timestamp": ts, "total_time_sec": t_total,
            "algorithms": algos, "problems": list(problems.keys()),
            "results": clean, "convergence": convergence,
        }, f, indent=2)
    print(f"  JSON    : {json_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    global _shutdown_requested

    parser = argparse.ArgumentParser(description=f"SOTA Benchmark v{VERSION}")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--parallel", action="store_true",
                        help="Use ProcessPoolExecutor (default: sequential on Windows)")
    parser.add_argument("--problems", type=str, default=None,
                        help="Comma-separated problem names")
    parser.add_argument("--algorithms", type=str, default=None,
                        help="Comma-separated algo names")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--size-limit", type=int, default=300)
    parser.add_argument("--time-limit", type=float, default=300.0,
                        help="Per-run wall-clock time limit in seconds (default: 300)")
    args = parser.parse_args()

    ALL_ALGOS = ["E2BSO-TSP", "R2DMA-TSP", "P-AOEA-TSP"]
    SEED_BASE = 1000

    # Sequential by default on Windows unless --parallel given
    use_sequential = (sys.platform == "win32") and not args.parallel
    cpu = os.cpu_count() or 1
    workers = args.workers if args.workers else min(cpu, 4)

    # ── Load problems ──────────────────────────────────────────────────────
    print("  Loading TSPLIB problems...", end="", flush=True)
    problems = load_problems(args.size_limit)
    print(f" {len(problems)} problems loaded.")

    if not problems:
        print("  No .tsp files found in", TSPLIB_DIR)
        return 1

    prob_names = sorted(problems.keys())
    selected_algos = ALL_ALGOS[:]
    runs = args.runs

    # ── Interactive selection ──────────────────────────────────────────────
    if not args.non_interactive:
        _print_banner(len(prob_names), selected_algos, runs, workers, use_sequential)

        print(f"\n  Available problems ({len(prob_names)}):")
        for i, p in enumerate(prob_names, 1):
            info = problems[p]
            opt = info.get("optimal")
            opt_str = str(opt) if opt else "N/A"
            print(f"    {i:>3}. {p:<14} n={info['dimension']:<5} optimal={opt_str}")

        raw = input(
            f"\n  Select problems (1-{len(prob_names)}, range e.g. 1-5, 'all'): "
        ).strip()
        if raw and raw.lower() not in ("all", "a", ""):
            try:
                ids: List[int] = []
                for part in raw.replace(" ", "").split(","):
                    if "-" in part:
                        lo, hi = part.split("-", 1)
                        ids.extend(range(int(lo), int(hi) + 1))
                    else:
                        ids.append(int(part))
                all_keys = sorted(problems.keys())
                prob_names = [all_keys[i - 1] for i in ids if 1 <= i <= len(all_keys)]
            except (ValueError, IndexError):
                pass

        print(f"\n  Algorithms: {', '.join(ALL_ALGOS)}")
        raw = input("  Select algorithms (all / comma-separated): ").strip()
        if raw and raw.lower() not in ("all", "a", ""):
            chosen = [a.strip() for a in raw.split(",") if a.strip() in ALL_ALGOS]
            if chosen:
                selected_algos = chosen

        raw = input(f"  Runs per algorithm [{runs}]: ").strip()
        if raw.isdigit():
            runs = int(raw)

    # ── CLI overrides ──────────────────────────────────────────────────────
    if args.problems:
        prob_names = [p.strip() for p in args.problems.split(",") if p.strip() in problems]
    if args.algorithms:
        selected_algos = [a.strip() for a in args.algorithms.split(",") if a.strip() in ALL_ALGOS]

    if not prob_names:
        print("  No problems selected.")
        return 1
    if not selected_algos:
        print("  No algorithms selected.")
        return 1

    if args.non_interactive:
        _print_banner(len(prob_names), selected_algos, runs, workers, use_sequential)

    if not args.non_interactive:
        print(f"\n  Problems   : {', '.join(prob_names)}")
        print(f"  Algorithms : {', '.join(selected_algos)}")
        print(f"  Runs/algo  : {runs}")
        print(f"  Mode       : {'sequential' if use_sequential else f'parallel ({workers} workers)'}")
        raw = input("\n  Start? [Y/n]: ").strip().lower()
        if raw in ("n", "no"):
            print("  Cancelled.")
            return 0

    # ── Output setup ───────────────────────────────────────────────────────
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(RESULTS_DIR, f"sota_progress_{ts}.csv")
    csv_headers = ["timestamp", "problem", "algorithm", "run", "seed",
                   "dimension", "optimal", "tour_cost", "gap_pct", "elapsed_sec", "iterations"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=csv_headers).writeheader()

    print(f"\n  CSV : {csv_path}")
    print(f"  Ctrl+C to stop — completed runs are saved.\n")

    all_results: List[Dict[str, Any]] = []
    eta_tracker = _ETATracker()
    t0_total = time.perf_counter()
    completed = 0
    total_tasks = len(prob_names) * len(selected_algos) * runs

    for pname in prob_names:
        if _shutdown_requested:
            break
        pinfo = problems[pname]
        coords = pinfo["coordinates"]
        optimal = pinfo.get("optimal")
        _print_problem_header(pname, pinfo["dimension"], optimal)

        # Build task list — deterministic seeds (no hash())
        tasks = []
        for ai, algo in enumerate(selected_algos):
            for run_idx in range(runs):
                seed = SEED_BASE + run_idx * 37 + ai * 100
                tasks.append((
                    algo, coords, seed, run_idx,
                    pinfo["dimension"], optimal, _NUMBA_AVAILABLE,
                ))

        def _save_result(res: Dict):
            nonlocal completed
            res["problem"] = pname
            all_results.append(res)
            completed += 1
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=csv_headers).writerow({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "problem": pname, "algorithm": res["algorithm"],
                    "run": res["run"], "seed": res["seed"],
                    "dimension": res["dimension"], "optimal": res["optimal"] or "",
                    "tour_cost": res["tour_cost"], "gap_pct": res["gap_pct"],
                    "elapsed_sec": res["elapsed_sec"], "iterations": res["iterations"],
                })
            eta_tracker.record(res["elapsed_sec"])
            remaining = total_tasks - completed
            eta = eta_tracker.estimate_remaining(remaining)
            _print_result_line(completed, total_tasks, res, eta)

        if use_sequential:
            for task in tasks:
                if _shutdown_requested:
                    break
                res = _run_solver_task(task)
                if "error" in res:
                    print(f"  ERROR [{res.get('algorithm','?')}]: {res['error'][:120]}")
                    continue
                _save_result(res)
        else:
            try:
                with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
                    futures = {ex.submit(_run_solver_task, t): t for t in tasks}
                    for future in concurrent.futures.as_completed(futures):
                        if _shutdown_requested:
                            break
                        try:
                            res = future.result(timeout=args.time_limit + 30)
                            if "error" in res:
                                print(f"  ERROR [{res.get('algorithm','?')}]: {res['error'][:120]}")
                                continue
                            _save_result(res)
                        except concurrent.futures.TimeoutError:
                            print(f"  TIMEOUT: task exceeded limit")
                        except Exception as exc:
                            print(f"  EXCEPTION: {exc}")
            except Exception as exc:
                print(f"  EXECUTOR ERROR: {exc}")

        # Mini per-problem summary
        p_results = [r for r in all_results if r.get("problem") == pname]
        _print_problem_mini_summary(pname, p_results, selected_algos)

    t_total = time.perf_counter() - t0_total

    if all_results:
        selected_problems = {k: problems[k] for k in prob_names if k in problems}
        _box_summary(all_results, selected_problems, selected_algos, t_total, RESULTS_DIR, ts)
    else:
        print("\n  No results collected.")

    if _shutdown_requested:
        print("\n  Interrupted. Partial results saved.")
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

