#!/usr/bin/env python3
"""
Aşama 5: Akademik Görselleştirme Paketi
Bildiri 2026 - Grafik Üretim Script'i

Kullanım: python 5_visualize.py
"""

import os
import sys
import json
import glob
from datetime import datetime

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    _VIZ_AVAILABLE = True
except ImportError as _viz_err:
    _VIZ_AVAILABLE = False
    _VIZ_ERROR = str(_viz_err)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")

def ensure_dirs():
    os.makedirs(PLOTS_DIR, exist_ok=True)

def plot_convergence():
    """histories/ klasöründeki JSON dosyalarından yakınsama eğrilerini çizer."""
    history_files = glob.glob(os.path.join(RESULTS_DIR, "histories", "convergence_*.json"))
    if not history_files:
        print("[!] Yakınsama verisi (JSON) bulunamadı. Önce Aşama 3'ü çalıştırın.")
        return

    latest_file = max(history_files, key=os.path.getctime)
    print(f"[*] Yakınsama eğrileri çiziliyor: {os.path.basename(latest_file)}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Problem bazlı grupla
    prob_groups = {}
    for key, val in data.items():
        p = val["problem"]
        if p not in prob_groups: prob_groups[p] = []
        prob_groups[p].append(val)

    for prob, algos in prob_groups.items():
        plt.figure(figsize=(10, 6))
        for item in algos:
            history = item["history"]
            plt.plot(history, label=f"{item['algorithm']} (ID:{item['model_id']})")
        
        plt.title(f"Yakınsama Eğrisi - Problem: {prob}")
        plt.xlabel("İterasyon / Jenerasyon")
        plt.ylabel("En İyi Çözüm Değeri")
        plt.legend()
        plt.tight_layout()
        
        save_path = os.path.join(PLOTS_DIR, f"convergence_{prob}.png")
        plt.savefig(save_path, dpi=300)
        plt.close()
        print(f"  -> Kaydedildi: convergence_{prob}.png")

def plot_boxplots():
    """benchmark_progress_*.csv dosyalarından algoritma karşılaştırma kutu grafikleri çizer."""
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "benchmark_progress_*.csv"))
    if not csv_files:
        print("[!] Benchmark verisi (CSV) bulunamadı.")
        return

    latest_file = max(csv_files, key=os.path.getctime)
    print(f"[*] Benchmark kutu grafikleri (Box-plots) çiziliyor: {os.path.basename(latest_file)}")
    
    df = pd.read_csv(latest_file)
    
    problems = df['problem'].unique()
    for prob in problems:
        prob_df = df[df['problem'] == prob]
        
        plt.figure(figsize=(12, 7))
        sns.boxplot(x='algorithm', y='duration', data=prob_df, palette="viridis")
        sns.stripplot(x='algorithm', y='duration', data=prob_df, color=".3", size=4, alpha=0.5)
        
        plt.title(f"Algoritma Performans Dağılımı - Problem: {prob}")
        plt.xlabel("Algoritma")
        plt.ylabel("Tur Uzunluğu / Süre")
        plt.tight_layout()
        
        save_path = os.path.join(PLOTS_DIR, f"boxplot_{prob}.png")
        plt.savefig(save_path, dpi=300)
        plt.close()
        print(f"  -> Kaydedildi: boxplot_{prob}.png")

def plot_taguchi_effects():
    """tuning_progress_*.csv dosyalarından parametre ana etki grafiklerini çizer."""
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "tuning_progress_*.csv"))
    if not csv_files:
        print("[!] Tuning verisi (CSV) bulunamadı.")
        return

    latest_file = max(csv_files, key=os.path.getctime)
    print(f"[*] Taguchi Ana Etki grafikleri çiziliyor: {os.path.basename(latest_file)}")
    
    df = pd.read_csv(latest_file)
    
    # Parametreleri JSON'dan sütunlara ayır
    params_df = df['params'].apply(lambda x: pd.Series(json.loads(x)))
    full_df = pd.concat([df[['algorithm', 'problem', 'mean_duration']], params_df], axis=1)
    
    # Her algoritma ve problem için ayrı grafik
    algos = full_df['algorithm'].unique()
    probs = full_df['problem'].unique()
    
    for algo in algos:
        for prob in probs:
            subset = full_df[(full_df['algorithm'] == algo) & (full_df['problem'] == prob)]
            if subset.empty: continue
            
            # Parametre sütunlarını bul (numeric veya category olanlar)
            param_cols = [c for c in params_df.columns if c in subset.columns]
            
            n_params = len(param_cols)
            if n_params == 0: continue
            
            fig, axes = plt.subplots(1, n_params, figsize=(5 * n_params, 5), sharey=True)
            if n_params == 1: axes = [axes]
            
            fig.suptitle(f"Parametre Ana Etkileri - {algo} ({prob})")
            
            for i, col in enumerate(param_cols):
                # Seviye ortalamalarını hesapla
                means = subset.groupby(col)['mean_duration'].mean().reset_index()
                sns.lineplot(ax=axes[i], x=col, y='mean_duration', data=means, marker='o', linewidth=2.5)
                axes[i].set_title(f"Etki: {col}")
                axes[i].set_ylabel("Ortalama Sonuç" if i == 0 else "")
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            save_path = os.path.join(PLOTS_DIR, f"taguchi_{algo}_{prob}.png")
            plt.savefig(save_path, dpi=300)
            plt.close()
            print(f"  -> Kaydedildi: taguchi_{algo}_{prob}.png")

def main():
    print("=" * 70)
    print("Aşama 5: Akademik Görselleştirme Paketi Başlatılıyor")
    print("=" * 70)

    if not _VIZ_AVAILABLE:
        print(f"\n[HATA] Görselleştirme kütüphaneleri eksik: {_VIZ_ERROR}")
        print("İpucu: pip install pandas matplotlib seaborn")
        sys.exit(1)
    
    try:
        ensure_dirs()
        plot_convergence()
        plot_boxplots()
        plot_taguchi_effects()
        
        print("\n" + "=" * 70)
        print("TÜM GRAFİKLER BAŞARIYLA ÜRETİLDİ.")
        print(f"Klasör: {PLOTS_DIR}")
        
    except Exception as e:
        print(f"\n[HATA] Görselleştirme sırasında bir sorun oluştu: {e}")
        print("İpucu: 'pandas', 'matplotlib' ve 'seaborn' kütüphanelerinin kurulu olduğundan emin olun.")

if __name__ == "__main__":
    main()
