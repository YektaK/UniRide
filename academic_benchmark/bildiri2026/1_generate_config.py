#!/usr/bin/env python3
"""
Aşama 1: İnteraktif Parametre Optimizasyon Konfigüratörü
"""
import os
import sys
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import data_manager

DEFAULT_ALGORITHMS = {
    "2-opt": {
        "max_iterations": [500, 1000, 2000],
        "first_improvement": [True, False],
        "num_starts": [1, 5, 10]
    },
    "3-opt": {
        "max_iterations": [200, 400, 800],
        "first_improvement": [True, False],
        "num_starts": [1, 3, 5]
    },
    "Or-opt": {
        "max_iterations": [300, 600, 1000],
        "max_segment_size": [1, 2, 3],
        "num_starts": [1, 3, 5]
    },
    "GA": {
        "population_size": [40, 80, 120],
        "generations": [100, 200],
        "crossover_rate": [0.75, 0.85],
        "mutation_rate": [0.10, 0.25],
        "elite_count": [1, 3]
    },
    "PSO": {
        "swarm_size": [20, 40, 60],
        "max_iterations": [100, 200, 300],
        "inertia_weight": [0.6, 0.729, 0.9],
        "cognitive_coeff": [1.0, 1.49445, 2.0]
    }
}

def parse_input_list(val_str, current_list):
    """Parses a comma-separated string into a list of appropriate types."""
    if not val_str.strip():
        return current_list
        
    parts = [x.strip() for x in val_str.split(',')]
    result = []
    
    # Try to cast to same type as the original list elements
    sample_type = type(current_list[0]) if current_list else str
    
    for p in parts:
        if sample_type == bool:
            result.append(p.lower() in ['true', 't', '1', 'evet', 'e'])
        elif sample_type == int:
            result.append(int(p))
        elif sample_type == float:
            result.append(float(p))
        else:
            result.append(p)
            
    return result

def main():
    print("=" * 70)
    print("Aşama 1: İnteraktif Konfigürasyon Üretici")
    print("=" * 70)
    
    # 1. Dosyaları Lokalize Et
    data_manager.localize_tsplib()
    
    # 2. Problemleri Listele
    problems = data_manager.list_local_problems()
    if not problems:
        print("[HATA] Hiç problem bulunamadı. Lütfen data/tsplib klasörünü kontrol edin.")
        return
        
    print("\n--- Mevcut Eğitim Problemleri ---")
    for idx, p in enumerate(problems, 1):
        print(f"  [{idx}] {p['name']:<15} (Tipi: {p['type']})")
        
    prob_input = input("\nEğitim yapılacak problem numarası (Örn: 1 veya 3): ").strip()
    try:
        prob_idx = int(prob_input) - 1
        selected_problem = problems[prob_idx]
    except (ValueError, IndexError):
        print("[HATA] Geçersiz problem seçimi. Çıkılıyor.")
        return
        
    print(f"\nSeçilen Problem: {selected_problem['name']}")
    
    # 3. Algoritmaları Seç
    algos = list(DEFAULT_ALGORITHMS.keys())
    print("\n--- Mevcut Algoritmalar ---")
    for idx, a in enumerate(algos, 1):
        print(f"  [{idx}] {a}")
        
    algo_input = input("\nOptimize edilecek algoritmalar (Örn: 1,4,5 veya tümü için 'all'): ").strip()
    selected_algos = {}
    if algo_input.lower() == 'all':
        selected_algos = DEFAULT_ALGORITHMS.copy()
    else:
        try:
            indices = [int(x.strip()) - 1 for x in algo_input.split(',')]
            for i in indices:
                selected_algos[algos[i]] = DEFAULT_ALGORITHMS[algos[i]].copy()
        except (ValueError, IndexError):
            print("[HATA] Geçersiz algoritma seçimi. Çıkılıyor.")
            return

    # 4. Parametre Seviyelerini Ayarla
    print("\n" + "=" * 70)
    print("PARAMETRE SEVİYELERİ AYARLAMA")
    print("Değiştirmek istemediğiniz değerler için doğrudan [ENTER] tuşuna basın.")
    print("Yeni değer girmek için virgülle ayırarak yazın (Örn: 10,20,50)")
    print("=" * 70)
    
    final_algos = {}
    for a_name, a_params in selected_algos.items():
        print(f"\n--- {a_name} Parametreleri ---")
        final_algos[a_name] = {}
        for p_name, p_vals in a_params.items():
            val_str = input(f"  {p_name} Mevcut: {p_vals} -> Yeni: ")
            try:
                final_algos[a_name][p_name] = parse_input_list(val_str, p_vals)
            except ValueError:
                print(f"    [!] Hatalı format, mevcut değer korundu: {p_vals}")
                final_algos[a_name][p_name] = p_vals

    # 5. Diğer Ayarlar
    print("\n--- Çalışma Ayarları ---")
    runs = input("  Kombinasyon başına tekrar sayısı [Varsayılan: 5]: ").strip()
    runs = int(runs) if runs else 5
    
    max_combos = input("  Algoritma başına max kombinasyon (Fractional fallback sınırı) [Varsayılan: 27]: ").strip()
    max_combos = int(max_combos) if max_combos else 27

    config = {
        "problem": selected_problem,
        "tuning_settings": {
            "runs_per_combination": runs,
            "max_combinations_per_algo": max_combos,
            "strategy": "fractional_fallback"
        },
        "algorithms": final_algos
    }
    
    # 6. Kayıt İşlemi
    CONFIG_DIR = os.path.join(SCRIPT_DIR, "configs")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"config_{selected_problem['name']}_{timestamp}.json"
    file_path = os.path.join(CONFIG_DIR, file_name)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
        
    print(f"\n[✓] Konfigürasyon dosyası başarıyla oluşturuldu:")
    print(f"    {file_path}")
    print("\nArtık Aşama 2'ye geçebilirsiniz:")
    print("    python 2_run_tuning.py")

if __name__ == "__main__":
    main()
