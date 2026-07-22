#!/usr/bin/env python3
"""
Final benchmark analyzer for YAEM 2026.
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
REPORTS_DIR = os.path.join(RESULTS_DIR, "reports")


def find_latest_file(pattern: str) -> str:
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No file matches pattern: {pattern}")
    return max(files, key=os.path.getmtime)


def try_load_optimals() -> Dict[str, float]:
    try:
        from benchmarks.tsplib_benchmark import TSPLIB_OPTIMALS
        return {str(k): float(v) for k, v in TSPLIB_OPTIMALS.items()}
    except Exception:
        return {}


def load_progress_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "problem": row["problem"], "model_id": int(row["model_id"]),
                    "algorithm": row["algorithm"], "run_idx": int(row["run_idx"]),
                    "duration": float(row["duration"]), "elapsed_ms": float(row["elapsed_ms"]),
                    "seed": int(row["seed"]),
                })
            except Exception:
                continue
    return rows


def load_summary_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "problem": row["Problem"], "algorithm": row["Algorithm"],
                    "model_id": int(row["ModelID"]), "best": float(row["Best"]),
                    "worst": float(row["Worst"]), "mean": float(row["Mean"]),
                    "std": float(row["StdDev"]), "mean_time_ms": float(row["MeanTimeMS"]),
                })
            except Exception:
                continue
    return rows


def one_way_anova(groups: Dict[str, List[float]]) -> Dict[str, float]:
    clean = {k: v for k, v in groups.items() if len(v) >= 2}
    k = len(clean)
    if k < 2:
        return {"f": 0.0, "df_between": 0.0, "df_within": 0.0, "eta_sq": 0.0}
    all_values: List[float] = []
    for vals in clean.values():
        all_values.extend(vals)
    grand_mean = statistics.mean(all_values)
    ss_between = 0.0
    ss_within = 0.0
    for vals in clean.values():
        m = statistics.mean(vals)
        ss_between += len(vals) * (m - grand_mean) ** 2
        ss_within += sum((x - m) ** 2 for x in vals)
    df_between = float(k - 1)
    df_within = float(len(all_values) - k)
    ms_between = ss_between / df_between if df_between > 0 else 0.0
    ms_within = ss_within / df_within if df_within > 0 else 0.0
    f_value = ms_between / ms_within if ms_within > 0 else 0.0
    eta_sq = ss_between / (ss_between + ss_within) if (ss_between + ss_within) > 0 else 0.0
    return {"f": f_value, "df_between": df_between, "df_within": df_within, "eta_sq": eta_sq}


def average_ranks_abs(values: List[float]) -> List[float]:
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def wilcoxon_signed_rank_paired(a_vals: List[float], b_vals: List[float]) -> Dict[str, float]:
    if len(a_vals) != len(b_vals):
        return {"n": 0.0, "w": 0.0, "z": 0.0, "p": 1.0, "median_delta": 0.0}
    diffs = [a - b for a, b in zip(a_vals, b_vals)]
    non_zero = [d for d in diffs if abs(d) > 1e-12]
    if not non_zero:
        return {"n": 0.0, "w": 0.0, "z": 0.0, "p": 1.0, "median_delta": 0.0}
    abs_vals = [abs(d) for d in non_zero]
    ranks = average_ranks_abs(abs_vals)
    w_plus = sum(r for r, d in zip(ranks, non_zero) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, non_zero) if d < 0)
    w_stat = min(w_plus, w_minus)
    n = float(len(non_zero))
    mean_w = n * (n + 1) / 4.0
    sd_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    z = (w_stat - mean_w) / sd_w if sd_w > 0 else 0.0
    p_two_sided = math.erfc(abs(z) / math.sqrt(2.0))
    return {"n": n, "w": w_stat, "z": z, "p": p_two_sided, "median_delta": statistics.median(non_zero)}


def generate_latex_table(problem: str, quality_table: List[Dict[str, Any]], optimal: float | None) -> str:
    latex = []
    latex.append("\\begin{table}[h]")
    latex.append("  \\centering")
    latex.append("  \\caption{Benchmark Results for Problem: " + problem.replace("_", "\\_") + "}")
    latex.append("  \\label{tab:results_" + problem.lower() + "}")
    latex.append("  \\begin{tabular}{lccccc}")
    latex.append("    \\hline")
    latex.append("    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\\%) \\\\")
    latex.append("    \\hline")
    for row in quality_table:
        algo = row["algorithm"]
        best = f"{row['best']:.2f}"
        mean = f"{row['mean']:.2f}"
        std = f"{row['std']:.2f}"
        time = f"{row['mean_time_ms']:.1f}"
        gap_val = "-"
        if optimal and optimal > 0:
            gap_val = f"{((row['best'] - optimal) / optimal * 100):.2f}"
        latex.append(f"    {algo} & {best} & {mean} & {std} & {time} & {gap_val} \\\\")
    latex.append("    \\hline")
    latex.append("  \\end{tabular}")
    latex.append("\\end{table}")
    return "\n".join(latex)


def holm_correction(pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = sorted(enumerate(pairs), key=lambda x: x[1]["p"])
    m = len(pairs)
    adjusted = [1.0] * m
    prev = 0.0
    for rank, (orig_idx, row) in enumerate(ordered):
        factor = m - rank
        adj = min(1.0, row["p"] * factor)
        adj = max(adj, prev)
        adjusted[orig_idx] = adj
        prev = adj
    out: List[Dict[str, Any]] = []
    for i, row in enumerate(pairs):
        new_row = dict(row)
        new_row["p_holm"] = adjusted[i]
        new_row["significant_0_05"] = adjusted[i] < 0.05
        out.append(new_row)
    return out


def build_report(problem: str, summary_rows: List[Dict[str, Any]], progress_rows: List[Dict[str, Any]],
                 output_path: str, source_summary: str, source_progress: str, optimals: Dict[str, float]) -> None:
    by_algo_runs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in progress_rows:
        by_algo_runs[row["algorithm"]].append(row)
    quality_table = sorted(summary_rows, key=lambda x: x["mean"])
    speed_table = sorted(summary_rows, key=lambda x: x["mean_time_ms"])
    duration_groups = {algo: [r["duration"] for r in runs] for algo, runs in by_algo_runs.items() if len(runs) >= 2}
    anova = one_way_anova(duration_groups)
    pairwise_rows: List[Dict[str, Any]] = []
    algos = sorted(by_algo_runs.keys())
    for i in range(len(algos)):
        for j in range(i + 1, len(algos)):
            a = algos[i]; b = algos[j]
            a_map = {r["run_idx"]: r["duration"] for r in by_algo_runs[a]}
            b_map = {r["run_idx"]: r["duration"] for r in by_algo_runs[b]}
            common = sorted(set(a_map.keys()) & set(b_map.keys()))
            if not common: continue
            a_vals = [a_map[k] for k in common]
            b_vals = [b_map[k] for k in common]
            w = wilcoxon_signed_rank_paired(a_vals, b_vals)
            a_better = sum(1 for av, bv in zip(a_vals, b_vals) if av < bv)
            b_better = sum(1 for av, bv in zip(a_vals, b_vals) if bv < av)
            pairwise_rows.append({"a": a, "b": b, "n": int(w["n"]), "w": w["w"], "z": w["z"],
                                  "p": w["p"], "median_delta": w["median_delta"],
                                  "a_better_runs": a_better, "b_better_runs": b_better})
    pairwise_rows = holm_correction(pairwise_rows)
    best_mean = quality_table[0]
    fastest = speed_table[0]
    optimal = optimals.get(problem)
    lines: List[str] = []
    lines.append(f"# Final Benchmark Analysis — YAEM 2026 — {problem}\n\n")
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    lines.append(f"Source summary: {source_summary}\n\n")
    lines.append(f"Source progress: {source_progress}\n\n")
    lines.append("## Quality Ranking (lower mean is better)\n\n")
    lines.append("| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |\n")
    lines.append("|------|-----------|---------|------|------|--------|------------|-------------|\n")
    for idx, row in enumerate(quality_table, 1):
        gap = "-"
        if optimal and optimal > 0:
            gap = f"{((row['best'] - optimal) / optimal) * 100:.2f}"
        lines.append(f"| {idx} | {row['algorithm']} | {row['model_id']} | {row['best']:.3f} | {row['mean']:.3f} | {row['std']:.3f} | {row['mean_time_ms']:.1f} | {gap} |\n")
    lines.append("\n## Speed Ranking\n\n")
    lines.append("| Rank | Algorithm | MeanTimeMS | MeanQuality |\n")
    lines.append("|------|-----------|------------|-------------|\n")
    for idx, row in enumerate(speed_table, 1):
        lines.append(f"| {idx} | {row['algorithm']} | {row['mean_time_ms']:.1f} | {row['mean']:.3f} |\n")
    lines.append("\n## ANOVA\n\n")
    lines.append(f"F({anova['df_between']:.0f}, {anova['df_within']:.0f}) = {anova['f']:.4f}, eta^2 = {anova['eta_sq']:.4f}\n\n")
    lines.append("## Pairwise Wilcoxon (Holm corrected)\n\n")
    lines.append("| A | B | n | median(A-B) | A better | B better | W | z | p | p_holm | sig(0.05) |\n")
    lines.append("|---|---|---|-------------|----------|----------|---|---|---|--------|-----------|\n")
    for row in sorted(pairwise_rows, key=lambda x: x["p_holm"]):
        lines.append(f"| {row['a']} | {row['b']} | {row['n']} | {row['median_delta']:.3f} | {row['a_better_runs']} | {row['b_better_runs']} | {row['w']:.3f} | {row['z']:.3f} | {row['p']:.6f} | {row['p_holm']:.6f} | {'yes' if row['significant_0_05'] else 'no'} |\n")
    lines.append("\n## Auto Comments\n\n")
    lines.append(f"1. Best average quality: {best_mean['algorithm']} (mean={best_mean['mean']:.3f}, best={best_mean['best']:.3f}).\n")
    lines.append(f"2. Fastest algorithm: {fastest['algorithm']} (mean time={fastest['mean_time_ms']:.1f} ms).\n")
    if best_mean["algorithm"] != fastest["algorithm"]:
        lines.append("3. Quality-speed tradeoff: best quality and best speed belong to different algorithms.\n")
    else:
        lines.append("3. Same algorithm leads in both quality and speed.\n")
    strong_pairs = [r for r in pairwise_rows if r["significant_0_05"]]
    lines.append(f"4. Pairwise: {len(strong_pairs)} significant differences after Holm correction.\n" if strong_pairs else "4. Pairwise: no significant differences after Holm correction.\n")
    lines.append("\n## LaTeX Table\n\n```latex\n")
    lines.append(generate_latex_table(problem, quality_table, optimal))
    lines.append("\n```\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze final benchmark outputs.")
    parser.add_argument("--progress", type=str, default="", help="Path to benchmark_progress_*.csv")
    parser.add_argument("--summary", type=str, default="", help="Path to benchmark_summary_*.csv")
    parser.add_argument("--problem", type=str, default="", help="Problem filter, e.g., eil76")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    progress_path = args.progress or find_latest_file(os.path.join(RESULTS_DIR, "benchmark_progress_*.csv"))
    summary_path = args.summary or find_latest_file(os.path.join(RESULTS_DIR, "benchmark_summary_*.csv"))
    progress_rows = load_progress_csv(progress_path)
    summary_rows = load_summary_csv(summary_path)
    if args.problem:
        progress_rows = [r for r in progress_rows if r["problem"] == args.problem]
        summary_rows = [r for r in summary_rows if r["problem"] == args.problem]
    if not progress_rows or not summary_rows:
        raise RuntimeError("No rows left after filtering.")
    problems_in_summary = sorted(set(r["problem"] for r in summary_rows))
    
    optimals = try_load_optimals()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 70)
    print("FINAL BENCHMARK ANALYSIS COMPLETE — YAEM 2026")
    print("=" * 70)
    
    for problem in problems_in_summary:
        prob_prog = [r for r in progress_rows if r["problem"] == problem]
        prob_sum = [r for r in summary_rows if r["problem"] == problem]
        
        report_path = os.path.join(REPORTS_DIR, f"FINAL_BENCHMARK_ANALYSIS_{problem}_{stamp}.md")
        build_report(problem=problem, summary_rows=prob_sum, progress_rows=prob_prog,
                     output_path=report_path, source_summary=os.path.abspath(summary_path),
                     source_progress=os.path.abspath(progress_path), optimals=optimals)
        print(f"[OK] Report for {problem}: {report_path}")


if __name__ == "__main__":
    main()
