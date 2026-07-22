#!/usr/bin/env python3
"""
ANOVA + Taguchi Statistical Analysis for Parameter Optimization — YAEM 2026
"""
import sys
import os
import json
import csv
import math
import glob
from collections import defaultdict
import statistics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
REPORTS_DIR = os.path.join(RESULTS_DIR, "reports")


def one_way_anova(group_means, group_vars, group_ns):
    groups = list(group_means.keys())
    k = len(groups)
    N = sum(group_ns[g] for g in groups)
    if N <= k:
        return {"F": 0.0, "significant_0.05": False, "significant_0.01": False}
    grand_mean = sum(group_ns[g] * group_means[g] for g in groups) / N
    ssb = sum(group_ns[g] * (group_means[g] - grand_mean) ** 2 for g in groups)
    dfb = k - 1
    msb = ssb / dfb if dfb > 0 else 0
    ssw = sum((group_ns[g] - 1) * group_vars[g] for g in groups)
    dfw = N - k
    msw = ssw / dfw if dfw > 0 else 0
    F = msb / msw if msw > 0 else 0.0
    return {
        "F": round(F, 4),
        "significant_0.05": F > 3.0,
        "significant_0.01": F > 4.0,
    }

def taguchi_sn_smaller_better(values):
    if not values:
        return 0.0
    n = len(values)
    mse = sum(v ** 2 for v in values) / n
    if mse == 0:
        return 0.0
    sn = -10 * math.log10(mse)
    return round(sn, 4)


def analyze_algorithm(records, algorithm, problem):
    if not records:
        return None
    best = min(records, key=lambda r: r["mean_duration"])
    param_effects = defaultdict(lambda: defaultdict(list))
    for r in records:
        params = r["params"]
        mean_dur = r["mean_duration"]
        for k, v in params.items():
            param_effects[k][str(v)].append(mean_dur)
    param_level_means = {}
    F_values = {}
    for param_name, level_dict in param_effects.items():
        level_means = {lvl: statistics.mean(vals) for lvl, vals in level_dict.items()}
        param_level_means[param_name] = level_means
        group_means = {f"L{i+1}": statistics.mean(vals) for i, (lvl, vals) in enumerate(level_dict.items())}
        group_vars = {f"L{i+1}": statistics.variance(vals) if len(vals) > 1 else 0.0 for i, (lvl, vals) in enumerate(level_dict.items())}
        group_ns = {f"L{i+1}": len(vals) for i, (lvl, vals) in enumerate(level_dict.items())}
        anova_res = one_way_anova(group_means, group_vars, group_ns)
        F_values[param_name] = anova_res
    all_means = [r["mean_duration"] for r in records]
    sn_value = taguchi_sn_smaller_better(all_means)
    return {
        "algorithm": algorithm,
        "problem": problem,
        "total_combinations": len(records),
        "best_params": best["params"],
        "best_mean": round(best["mean_duration"], 4),
        "overall_mean": round(statistics.mean(all_means), 4),
        "overall_std": round(statistics.stdev(all_means), 4) if len(all_means) > 1 else 0.0,
        "taguchi_sn": sn_value,
        "param_effects": param_level_means,
        "anova_per_param": F_values,
    }

def rank_params_by_importance(anova_results):
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


def generate_report(all_analyses, output_path, is_master=False):
    lines = []
    if is_master:
        lines.append("# Master Akademik Parametre Optimizasyonu Raporu — YAEM 2026\n\n")
        lines.append("> Bu rapor tüm geçmiş koşu dosyalarındaki verilerin kümülatif birleştirilmesiyle oluşturulmuştur.\n")
    else:
        lines.append("# Bireysel Akademik Parametre Optimizasyonu Raporu — YAEM 2026\n\n")
    lines.append("---\n")
    lines.append("## Elde Edilen Bulgular\n")

    for key, analysis in sorted(all_analyses.items()):
        prob_name = analysis['problem']
        algo_name = analysis['algorithm']
        lines.append(f"\n### {algo_name} (Problem: {prob_name})\n")
        lines.append(f"- **Toplam Kombinasyon Kaydı**: {analysis['total_combinations']}\n")
        lines.append(f"- **En İyi Ortalama Sonuç**: {analysis['best_mean']}\n")
        lines.append(f"- **Taguchi S/N Oranı**: {analysis['taguchi_sn']} dB\n")
        lines.append(f"\n**En İyi Parametre Seti**:\n```json\n{json.dumps(analysis['best_params'], indent=2)}\n```\n")
        lines.append("\n**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:\n")
        ranking = rank_params_by_importance(analysis['anova_per_param'])
        lines.append("| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |\n")
        lines.append("|----------|-----------|----------|---------------|---------------|\n")
        for i, r in enumerate(ranking, 1):
            sig05 = "Evet" if r["significant"] else "Hayır"
            sig01 = "Evet" if r["significant_0.01"] else "Hayır"
            lines.append(f"| {i} | {r['parameter']} | {r['F_value']} | {sig05} | {sig01} |\n")
        lines.append("\n**Parametre Seviye Etkileri**:\n")
        for param_name, level_means in analysis['param_effects'].items():
            lines.append(f"\n*{param_name}*:\n")
            levels = sorted(level_means.keys(), key=lambda x: (isinstance(x, str), x))
            for lvl in levels:
                lines.append(f"  - Seviye {lvl}: {level_means[lvl]:.2f}\n")

    lines.append("\n---\n")
    lines.append("## Yorum ve Sonuç\n")
    lines.append("En yüksek F değerine sahip parametre, sonucu en fazla etkileyen faktördür. "
                 "Taguchi S/N oranı yüksek olan kombinasyonlar, hem düşük ortalama hem de "
                 "düşük değişkenlik sağlar.\n")

    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.writelines(lines)
    print(f"  [OK] Rapor oluşturuldu: {os.path.basename(output_path)}")


def process_csv(filepath, records_dict):
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            algo = row.get("algorithm")
            prob = row.get("problem")
            if not algo or not prob:
                continue
            try:
                mean_dur = float(row.get("mean_duration", 0))
                params = json.loads(row.get("params", "{}"))
                records_dict[(prob, algo)].append({
                    "params": params,
                    "mean_duration": mean_dur
                })
                count += 1
            except Exception:
                pass
    return count


def main():
    print("=" * 70)
    print("Kümülatif Deney Tasarımı Rapor Oluşturucu — YAEM 2026")
    print("=" * 70)

    os.makedirs(REPORTS_DIR, exist_ok=True)

    csv_pattern = os.path.join(RESULTS_DIR, "tuning_progress_*.csv")
    csv_files = sorted(glob.glob(csv_pattern))
    
    if not csv_files:
        print("[HATA] 'results/' klasöründe 'tuning_progress_*.csv' dosyası bulunamadı.")
        sys.exit(1)

    print(f"[BİLGİ] {len(csv_files)} adet CSV dosyası tespit edildi.")

    master_records = defaultdict(list)

    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        timestamp = filename.replace("tuning_progress_", "").replace(".csv", "")
        report_name = f"DENEY_TASARIMI_{timestamp}.md"
        report_path = os.path.join(REPORTS_DIR, report_name)
        
        local_records = defaultdict(list)
        valid_rows = process_csv(csv_file, local_records)
        
        for key, recs in local_records.items():
            master_records[key].extend(recs)
            
        if not os.path.exists(report_path) and valid_rows > 0:
            print(f"  -> {filename} analiz ediliyor...")
            local_analyses = {}
            for (prob, algo), recs in local_records.items():
                analysis = analyze_algorithm(recs, algo, prob)
                if analysis:
                    local_analyses[(prob, algo)] = analysis
            generate_report(local_analyses, report_path, is_master=False)

    print("\n[BİLGİ] Tüm veriler MASTER havuzunda birleştirildi.")
    print("        Master Rapor ANOVA / Taguchi analizi başlatılıyor...")

    if not master_records:
        print("[HATA] CSV dosyalarından hiç veri okunamadı.")
        sys.exit(1)

    master_analyses = {}
    for (prob, algo), recs in master_records.items():
        analysis = analyze_algorithm(recs, algo, prob)
        if analysis:
            master_analyses[(prob, algo)] = analysis

    master_report_path = os.path.join(REPORTS_DIR, "MASTER_DENEY_TASARIM_RAPORU.md")
    generate_report(master_analyses, master_report_path, is_master=True)

    print("\n" + "=" * 70)
    print("TÜM İŞLEMLER BAŞARIYLA TAMAMLANDI.")
    print(f"Raporlar klasörü: {REPORTS_DIR}")

if __name__ == "__main__":
    main()
