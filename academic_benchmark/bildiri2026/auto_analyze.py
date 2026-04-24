#!/usr/bin/env python3
"""Otomatik benchmark analizi ve bildiri doküman güncelleme betiği."""
import json, os, sys, math, glob
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
DOCS_DIR = SCRIPT_DIR


def load_latest_benchmark():
    pattern = RESULTS_DIR / "tsplib_*.json"
    files = sorted(glob.glob(str(pattern)), reverse=True, key=lambda f: os.path.getmtime(f))
    if not files:
        raise FileNotFoundError("Hiç benchmark JSON dosyası bulunamadı!")
    latest = files[0]
    print(f"[ANALYSIS] Kullanılan dosya: {latest}")
    with open(latest, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    return data, latest


def format_gap(g: float) -> str:
    """Gap değerini formatla: 0 ise '0' yoksa '5.20'."""
    return "0" if g < 0.05 else f"{g:.2f}"


def build_summary_tables(data):
    results = data["results"]
    problems = sorted({r["problem"] for r in results})
    algos = sorted({r["algorithm"] for r in results})
    optimals = {p: next(r["optimal"] for r in results if r["problem"] == p) for p in problems}
    dimensions = {p: next(r["dimension"] for r in results if r["problem"] == p) for p in problems}

    rows_by_algo = {}
    for a in algos:
        rows_by_algo[a] = {}
        for p in problems:
            entries = [r for r in results if r["algorithm"] == a and r["problem"] == p]
            lengths = [e["tour_length"] for e in entries]
            times = [e["elapsed_ms"] / 1000 for e in entries]  # saniye
            gaps = [e["gap_percent"] for e in entries if e["gap_percent"] is not None]
            rows_by_algo[a][p] = {
                "best": min(lengths),
                "mean": sum(lengths) / len(lengths),
                "std": stdev(lengths),
                "tbest": min(times),
                "tmean": sum(times) / len(times),
                "tstd": stdev(times),
                "gap_best": min(gaps) if gaps else None,
                "gap_mean": sum(gaps) / len(gaps) if gaps else None,
                "gap_std": stdev(gaps) if gaps else None,
                "n": len(lengths),
            }

    # Markdown tablo oluştur: Algoritmalar satır, Problemler sütun
    md = f"""## 📊 S T S L I B   B e n c h m a r k   S o n u ç l a r ı

*Benchmark tarihi: {data.get('timestamp', '?')}*  
*Çalışma sayısı: {data.get('num_runs', '?')}*

### Tablo 1 – Algoritma x Problem: En İyi Tur Uzunluğu (en yakın optimum)

| Algoritma | n | {' | '.join(problems)} |
"""
    for a in algos:
        row = f"| **{a}** |"
        for p in problems:
            cell = rows_by_algo[a][p]
            opt = optimals[p]
            best = cell["best"]
            gap = ((best - opt) / opt * 100) if opt else 0
            row += f" {best:.2f} ({format_gap(gap)}%) |"
        md += row + "\n"

    md += "\n### Tablo 2 – Algoritma x Problem: Ortalama Tur Uzunluğu (±std)\n\n"
    md += "| Algoritma | n | " + " | ".join(problems) + " |\n"
    for a in algos:
        row = f"| **{a}** |"
        for p in problems:
            cell = rows_by_algo[a][p]
            row += f" {cell['mean']:.2f} (±{cell['std']:.2f}) |"
        md += row + "\n"

    md += "\n### Tablo 3 – Algoritma x Problem: Ortalama Süre sn (±std)\n\n"
    md += "| Algoritma | n | " + " | ".join(problems) + " |\n"
    for a in algos:
        row = f"| **{a}** |"
        for p in problems:
            cell = rows_by_algo[a][p]
            row += f" {cell['tmean']:.3f} (±{cell['tstd']:.3f}) |"
        md += row + "\n"

    # Genel özet
    md += "\n### 📈 Genel Performans Özeti\n\n"
    for a in algos:
        all_gaps = []
        all_times = []
        for p in problems:
            cell = rows_by_algo[a][p]
            if cell["gap_mean"] is not None:
                all_gaps.append(cell["gap_mean"])
            all_times.append(cell["tmean"])
        avg_gap = sum(all_gaps) / len(all_gaps) if all_gaps else 0
        avg_time = sum(all_times) / len(all_times)
        md += f"- **{a}**: Ortalama sapma {avg_gap:.2f}%, Ortalama süre {avg_time:.3f} sn\n"

    return md, optimals, dimensions, rows_by_algo, algos, problems


def stdev(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def write_analysis(md_content, output_path):
    with open(output_path, 'w', encoding='utf-8') as fp:
        fp.write(md_content)
    print(f"[ANALYSIS] Dosya yazıldı: {output_path}")


def main():
    data, json_path = load_latest_benchmark()
    md, optimals, dims, rows_by_algo, algos, problems = build_summary_tables(data)
    out = DOCS_DIR / "performans_analizi.md"
    write_analysis(md, out)
    print("\n✅ Analiz tamamlandı. performans_analizi.md güncellendi.")


if __name__ == "__main__":
    main()
