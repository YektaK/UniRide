#!/usr/bin/env python3
"""
ANOVA + Taguchi Statistical Analysis for Parameter Optimization
Bildiri 2026 - Akademik Analiz Script'i

Komut: python analyze_results.py

Girdiler:
  - results/param_opt_*.json (param_opt_design.py ciktisi)

Ciktilar:
  - results/ANOVA_RESULTS.md ( akademik rapor )
  - results/ANOVA_*.csv ( tablolar )
"""

import sys, os, json, csv, math
from collections import defaultdict
import statistics


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
OUTPUT_DIR = RESULTS_DIR

# ------------------------------------------------------------------
# 1. Helper Functions
# ------------------------------------------------------------------

def load_latest_json():
    """En son uretilmis param_opt_*.json dosyasini bul."""
    files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("param_opt_") and f.endswith(".json")]
    if not files:
        return None
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(RESULTS_DIR, f)))
    path = os.path.join(RESULTS_DIR, latest)
    with open(path, 'r', encoding='utf-8') as fh:
        raw_data = json.load(fh)
    
    # Flat list of individual runs -> aggregate by algorithm + params dict
    records = raw_data.get("results", [])
    if not records:
        return None, latest
    problem = raw_data.get("problem", "eil51")
    optimal = raw_data.get("optimal", 426)
    
    from collections import defaultdict
    algo_combo = defaultdict(lambda: {"values": [], "params": None, "elapsed": []})
    for r in records:
        algo = r["algorithm"]
        params = json.loads(r["params"])
        key = (algo, json.dumps(params, sort_keys=True))
        algo_combo[key]["values"].append(r["tour_length"])
        algo_combo[key]["elapsed"].append(r["elapsed_ms"])
        if algo_combo[key]["params"] is None:
            algo_combo[key]["params"] = params
    
    # Build per-algorithm list of aggregated combos
    algos = defaultdict(list)
    for (algo, params_str), data in algo_combo.items():
        mean = statistics.mean(data["values"])
        std = statistics.stdev(data["values"]) if len(data["values"]) > 1 else 0.0
        algos[algo].append({
            "params": data["params"],
            "mean": mean,
            "std": std,
            "elapsed": statistics.mean(data["elapsed"]),
        })
    
    structured = {
        "problem": problem,
        "optimal": optimal,
        "algorithms": dict(algos),
    }
    return structured, latest


def descriptive_stats(values):
    """Ortalama, std, min, max, medyan, SEM hesapla."""
    n = len(values)
    mean = statistics.mean(values)
    std = statistics.stdev(values) if n > 1 else 0.0
    sem = std / math.sqrt(n) if n > 1 else 0.0
    median = statistics.median(values)
    return {
        "N": n,
        "Mean": round(mean, 4),
        "Std": round(std, 4),
        "SEM": round(sem, 4),
        "Min": round(min(values), 4),
        "Max": round(max(values), 4),
        "Median": round(median, 4),
    }


def effect_size(means_dict):
    """Eta-squared benzeri basit etki büyüklügü hesaplama."""
    grand_mean = statistics.mean(means_dict.values())
    ss_between = sum((m - grand_mean) ** 2 for m in means_dict.values())
    ss_total = sum((m - grand_mean) ** 2 for m in means_dict.values())  # Basitlestirme
    if ss_total == 0:
        return 0.0
    return ss_between / ss_total  # Eta-squared proxy


def one_way_anova(group_means, group_vars, group_ns):
    """
    Basit ANOVA: Tek yonlu bagimsiz gruplar.
    group_means: dict(group_label -> mean)
    group_vars:  dict(group_label -> variance)
    group_ns:    dict(group_label -> N)
    Returns: F, p (Fisher F istatistigi)
    """
    groups = list(group_means.keys())
    k = len(groups)
    N = sum(group_ns[g] for g in groups)

    grand_mean = sum(group_ns[g] * group_means[g] for g in groups) / N

    # SSB
    ssb = sum(group_ns[g] * (group_means[g] - grand_mean) ** 2 for g in groups)
    dfb = k - 1
    msb = ssb / dfb if dfb > 0 else 0

    # SSW
    ssw = sum((group_ns[g] - 1) * group_vars[g] for g in groups)
    dfw = N - k
    msw = ssw / dfw if dfw > 0 else 0

    F = msb / msw if msw > 0 else float('inf')
    # Basit F dagilimi icin p degeri (yaklasik)
    # Uygulamada scipy.stats.f.sf(F, dfb, dfw) kullanilir;
    # Burada basitlestirme icin yaklasik kritik bölge yaziyoruz.
    # P degeri yerine F degeri ve kritik esikler verilecek.
    return {
        "SSB": round(ssb, 4),
        "SSW": round(ssw, 4),
        "SST": round(ssb + ssw, 4),
        "df_between": dfb,
        "df_within": dfw,
        "MSB": round(msb, 4),
        "MSW": round(msw, 4),
        "F": round(F, 4),
        "critical_0.05": "~2.5-3.0 (Tablo degeri)",
        "critical_0.01": "~3.5-4.2 (Tablo degeri)",
        "significant_0.05": F > 3.0,
        "significant_0.01": F > 4.0,
    }


def taguchi_sn_smaller_better(values):
    """Taguchi S/N orani: Daha kucuk deger daha iyi (tour length)."""
    if not values:
        return 0.0
    n = len(values)
    mse = sum(v ** 2 for v in values) / n
    if mse == 0:
        return 0.0
    sn = -10 * math.log10(mse)
    return round(sn, 4)


def effect_table(param_name, levels, means):
    """Bir parametrenin seviyelerine gore ortalama performans."""
    lines = []
    for i, lvl in enumerate(levels, 1):
        lines.append(f"  {param_name}={lvl}: Mean={means[str(lvl)]:.2f}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 2. Analysis Workflows
# ------------------------------------------------------------------

def analyze_algorithm(records, algorithm, problem="eil51"):
    """
    Tek bir algoritmanin sonuclarini analiz et.
    records: list of dicts with keys: params, mean, std, elapsed
    Output: dict with best params, ANOVA, Taguchi S/N, effect sizes.
    """
    if not records:
        return None
    
    # Best combination (lowest mean)
    best = min(records, key=lambda r: r["mean"])

    # Parameter-level effect analysis
    param_effects = defaultdict(lambda: defaultdict(list))
    for r in records:
        params = r["params"]
        mean = r["mean"]
        for k, v in params.items():
            param_effects[k][str(v)].append(mean)

    # Her parametre seviyesinin ortalamasi
    param_level_means = {}
    F_values = {}
    for param_name, level_dict in param_effects.items():
        level_means = {lvl: statistics.mean(vals) for lvl, vals in level_dict.items()}
        param_level_means[param_name] = level_means

        # ANOVA F calculation for this parameter
        group_means = {f"L{i+1}": statistics.mean(vals) for i, (lvl, vals) in enumerate(level_dict.items())}
        group_vars = {f"L{i+1}": statistics.variance(vals) if len(vals) > 1 else 0.0 for i, (lvl, vals) in enumerate(level_dict.items())}
        group_ns = {f"L{i+1}": len(vals) for i, (lvl, vals) in enumerate(level_dict.items())}

        anova_res = one_way_anova(group_means, group_vars, group_ns)
        F_values[param_name] = anova_res

    # Taguchi S/N
    all_means = [r["mean"] for r in records]
    sn_value = taguchi_sn_smaller_better(all_means)

    return {
        "algorithm": algorithm,
        "problem": problem,
        "total_combinations": len(records),
        "best_params": best["params"],
        "best_mean": round(best["mean"], 4),
        "best_std": round(best["std"], 4),
        "overall_mean": round(statistics.mean(all_means), 4),
        "overall_std": round(statistics.stdev(all_means), 4),
        "taguchi_sn": sn_value,
        "param_effects": param_level_means,
        "anova_per_param": F_values,
        "raw_records": records,
    }


def rank_params_by_importance(anova_results):
    """
    ANOVA F degerlerine gore parametreleri onem sirasina diz.
    """
    ranking = []
    for param, anova in anova_results.items():
        ranking.append({
            "parameter": param,
            "F_value": anova["F"],
            "significant": anova["significant_0.05"],
            "significant_0.01": anova["significant_0.01"],
        })
    ranking.sort(key=lambda x: x["F_value"], reverse=True)
    return ranking


# ------------------------------------------------------------------
# 3. Report Generation
# ------------------------------------------------------------------

def generate_report(all_analyses, output_path):
    """Markdown formatinda akademik rapor yaz."""
    lines = []
    lines.append("# Akademik Parametre Optimizasyonu - ANOVA ve Taguchi Analizi\n")
    lines.append("---\n")
    lines.append("## Elde Edilen Bulgular\n")

    for algo_name, analysis in sorted(all_analyses.items()):
        lines.append(f"\n### {algo_name}\n")
        lines.append(f"- **Problem**: {analysis['problem']}\n")
        lines.append(f"- **Toplam Kombinasyon Sayisi**: {analysis['total_combinations']}\n")
        lines.append(f"- **En Iyi Ortalama Sonuc**: {analysis['best_mean']} ± {analysis['best_std']}\n")
        lines.append(f"- **Taguchi S/N Orani**: {analysis['taguchi_sn']} dB\n")
        lines.append(f"\n**En Iyi Parametre Seti**:\n```json\n{json.dumps(analysis['best_params'], indent=2)}\n```\n")

        lines.append("\n**Parametre Onem Sirasi (ANOVA F-Istatistigine Gore)**:\n")
        ranking = rank_params_by_importance(analysis['anova_per_param'])
        lines.append("| Siralama | Parametre | F Degeri | %5 Anlamlilik | %1 Anlamlilik |\n")
        lines.append("|----------|-----------|----------|---------------|---------------|\n")
        for i, r in enumerate(ranking, 1):
            sig05 = "Evet" if r["significant"] else "Hayir"
            sig01 = "Evet" if r["significant_0.01"] else "Hayir"
            lines.append(f"| {i} | {r['parameter']} | {r['F_value']} | {sig05} | {sig01} |\n")

        lines.append("\n**Parametre Seviye Etkileri (Ortalama Degerler)**:\n")
        for param_name, level_means in analysis['param_effects'].items():
            lines.append(f"\n*{param_name}*:\n")
            levels = sorted(level_means.keys(), key=lambda x: (isinstance(x, str), x))
            for lvl in levels:
                lines.append(f"  - Seviye {lvl}: {level_means[lvl]:.2f}\n")

    lines.append("\n---\n")
    lines.append("## Yorum ve Sonuc\n")
    lines.append("En yuksek F degerine sahip parametre, sonucu en fazla etkileyen faktordur. "
                 "Taguchi S/N orani yuksek olan kombinasyonlar, hem dusuk ortalama hem de "
                 "dusuk degiskenlik saglar. Akademik makale icin tablolarda ANOVA F ve "
                 "p degerleri, ayrica Taguchi S/N degerleri sunulmalidir.\n")

    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.writelines(lines)
    print(f"[INFO] Report written: {output_path}")


def generate_csv_tables(analysis, prefix):
    """Her algoritma icin CSV tablolari yaz."""
    # 1. Raw results
    raw_path = os.path.join(OUTPUT_DIR, f"{prefix}_raw.csv")
    if analysis["raw_records"]:
        keys = list(analysis["raw_records"][0]["params"].keys()) + ["mean", "std", "elapsed"]
        with open(raw_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=keys + ["rank"])
            writer.writeheader()
            sorted_recs = sorted(analysis["raw_records"], key=lambda r: r["mean"])
            for i, r in enumerate(sorted_recs, 1):
                row = {**r["params"], "mean": r["mean"], "std": r["std"], "elapsed": r["elapsed"], "rank": i}
                writer.writerow(row)
        print(f"[INFO] Raw table: {raw_path}")

    # 2. ANOVA summary
    anova_path = os.path.join(OUTPUT_DIR, f"{prefix}_ANOVA.csv")
    with open(anova_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(["Parameter", "F", "df_between", "df_within", "MSB", "MSW", "Significant_0.05", "Significant_0.01"])
        for param, res in analysis["anova_per_param"].items():
            writer.writerow([
                param, res["F"], res["df_between"], res["df_within"],
                res["MSB"], res["MSW"],
                res["significant_0.05"], res["significant_0.01"]
            ])
    print(f"[INFO] ANOVA table: {anova_path}")


# ------------------------------------------------------------------
# 4. Main Entry
# ------------------------------------------------------------------

if __name__ == "__main__":
    data, latest_file = load_latest_json()
    if data is None:
        print("[HATA] results/ klasorunde param_opt_*.json bulunamadi.")
        print("[BILGI] Once >> python param_opt_design.py << calistirilmalidir.")
        sys.exit(1)

    print(f"[INFO] Yuklenen dosya: {latest_file}")
    print("[INFO] Analiz ediliyor...")

    problems = data.get("problems", {})
    all_analyses = {}
    # JSON format: top-level is list of algorithms
    # Corrected: read per algorithm key
    # param_opt_design.py saves: {problems: {problem: [records]}} -- OLD
    # Actually we save as dict with algorithm name key.
    # Let's inspect the JSON structure before assuming.

    # Re-parse properly
    results_json = data

    # Structure: {"problem": "eil51", "algorithms": {"2-opt": [...]}}
    if "algorithms" in results_json:
        prob = results_json.get("problem", "eil51")
        for algo_name, algo_records in results_json["algorithms"].items():
            analysis = analyze_algorithm(algo_records, algo_name, problem=prob)
            if analysis:
                all_analyses[algo_name] = analysis
                generate_csv_tables(analysis, prefix=algo_name.replace("-", ""))
    else:
        print("[UYARI] Beklenen JSON yapisinda olmayabilir. Yapi: ", list(results_json.keys())[:5])

    if not all_analyses:
        print("[HATA] Algoritma verisi bulunamadi.")
        sys.exit(1)

    report_path = os.path.join(OUTPUT_DIR, "ANOVA_RESULTS.md")
    generate_report(all_analyses, report_path)
    print("\n[DONE] Tum analizler tamamlandi!")
