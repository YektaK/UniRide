import os
import sys
import json
import glob
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

TARGET_ALGOS = ["GWO-ALNS", "HHO-ALNS", "2-opt", "3-opt"]

def plot_student_matrix_convergence():
    history_files = glob.glob(os.path.join(RESULTS_DIR, "histories", "convergence_*.json"))
    if not history_files:
        print("[!] Yakınsama verisi bulunamadı.")
        return

    latest_file = max(history_files, key=os.path.getctime)
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Sadece student_matrix
    student_data = [v for k, v in data.items() if v["problem"] == "student_matrix" and v["algorithm"] in TARGET_ALGOS]
    
    if not student_data:
        print("[!] student_matrix için belirtilen algoritmalara ait veri bulunamadı.")
        return

    plt.figure(figsize=(10, 6))
    for item in student_data:
        plt.plot(item["history"], label=f"{item['algorithm']}")
    
    plt.title("Yakınsama Eğrisi - Problem: student_matrix")
    plt.xlabel("İterasyon")
    plt.ylabel("En İyi Çözüm Değeri")
    plt.legend()
    plt.tight_layout()
    
    save_path = os.path.join(PLOTS_DIR, "convergence_student_matrix.png")
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[*] Kaydedildi: {save_path}")

def plot_student_matrix_boxplot():
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "benchmark_progress_*.csv"))
    if not csv_files:
        print("[!] Benchmark verisi bulunamadı.")
        return

    latest_file = max(csv_files, key=os.path.getctime)
    df = pd.read_csv(latest_file)
    
    prob_df = df[(df['problem'] == 'student_matrix') & (df['algorithm'].isin(TARGET_ALGOS))]
    
    if prob_df.empty:
        print("[!] student_matrix için benchmark verisi bulunamadı.")
        return

    # Sıralamayı sunumdaki gibi yapmak için:
    prob_df['algorithm'] = pd.Categorical(prob_df['algorithm'], categories=TARGET_ALGOS, ordered=True)
    prob_df = prob_df.sort_values('algorithm')

    plt.figure(figsize=(12, 7))
    sns.boxplot(x='algorithm', y='duration', data=prob_df, palette="Set2")
    sns.stripplot(x='algorithm', y='duration', data=prob_df, color=".3", size=5, alpha=0.6)
    
    plt.title("Algoritma Performans Dağılımı (Boxplot) - Problem: student_matrix")
    plt.xlabel("Algoritma")
    plt.ylabel("Tur Uzunluğu / Maliyet")
    plt.tight_layout()
    
    save_path = os.path.join(PLOTS_DIR, "boxplot_student_matrix_sunum.png")
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[*] Kaydedildi: {save_path}")

if __name__ == "__main__":
    plot_student_matrix_convergence()
    plot_student_matrix_boxplot()
