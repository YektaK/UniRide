import os
import sys
import json
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(SCRIPT_DIR, "configs")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
TSPLIB_DIR = os.path.join(DATA_DIR, "tsplib")

def run_cmd(cmd):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ÇALIŞTIRILIYOR: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def generate_tuning_config():
    print("--- 1. TUNING KONFİGÜRASYONLARI OLUŞTURULUYOR ---")
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    
    # Eski konfigürasyonları temizle
    for f in os.listdir(CONFIGS_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(CONFIGS_DIR, f))
    
    sys.path.insert(0, SCRIPT_DIR)
    import data_manager
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gen_config", os.path.join(SCRIPT_DIR, "1_generate_config.py"))
        gen_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_config)
        DEFAULT_ALGORITHMS = gen_config.DEFAULT_ALGORITHMS
    except Exception as e:
        print(f"Konfigürasyon varsayılanları yüklenemedi: {e}")
        return None

    data_manager.localize_tsplib()
    problems = data_manager.list_local_problems()
    
    # 4 TSPLIB problemi için Evrensel Optimizasyon config'leri üret
    target_tune_problems = ["berlin52", "eil51", "st70", "kroA100"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for p_name in target_tune_problems:
        prob = next((p for p in problems if p["name"] == p_name), None)
        if not prob:
            print(f"[UYARI] {p_name} bulunamadı, atlanıyor.")
            continue

        config = {
            "problem": prob,
            "tuning_settings": {
                "runs_per_combination": 5,
                "max_combinations_per_algo": 30, # Optuna n_trials
                "strategy": "optuna_tpe"
            },
            "algorithms": DEFAULT_ALGORITHMS
        }
        
        file_name = f"config_{p_name}_{timestamp}.json"
        file_path = os.path.join(CONFIGS_DIR, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        print(f"Konfigürasyon kaydedildi: {file_name}")
    return True


def main():
    print("="*70)
    print("YAEM 2026 TOPLU DENEY KOŞUCUSU")
    print("="*70)
    
    # Adım 1: Config Üret
    generate_tuning_config()
    
    # Adım 2: Tuning
    print("\n--- 2. OPTUNA TPE PARAMETRE OPTİMİZASYONU ---")
    print("Bu işlem algoritmaların (GWO-ALNS, vb.) ağır doğası ve 4 farklı TSPLIB seti gereği BİRKAÇ SAAT sürebilir.")
    run_cmd([sys.executable, "2_run_tuning.py", "all"])
    
    # Adım 2.5: Universal Params Extraction
    print("\n--- 2.5. EVRENSEL PARAMETRE SETİ ÇIKARIMI (MODAL ANALİZ) ---")
    run_cmd([sys.executable, "extract_universal_params.py"])
    
    # Adım 3: Tuning Analizi
    print("\n--- 3. ANOVA VE TAGUCHI ANALİZİ (Tüm Optuna Logları) ---")
    run_cmd([sys.executable, "analyze_tuning.py"])
    
    # Adım 4 & 5 & 6: Her problem için sıralı Benchmark -> Analiz -> Grafik
    print("\n--- 4, 5, 6. GENİŞ ÇAPLI BENCHMARK VE RAPORLAMA (Problemlere Göre Sıralı) ---")
    print("Sistem her problem için koşuyu yapıp hemen raporunu üretecek, böylece erkenden sonuçları görebileceksiniz.")
    
    import data_manager
    problems = data_manager.list_local_problems()
    target_names = ["berlin52", "eil51", "st70", "kroA100", "student_matrix"]
    
    for p_name in target_names:
        print(f"\n{'='*50}")
        print(f">>> ŞU ANKİ HEDEF: {p_name} <<<")
        print(f"{'='*50}")
        
        prob_index = next((str(i + 1) for i, p in enumerate(problems) if p["name"] == p_name), None)
        if not prob_index:
            continue
            
        print(f"\n--- [ {p_name} ] Benchmark ---")
        run_cmd([sys.executable, "3_run_benchmark.py", "all", prob_index, "30"])
        
        print(f"\n--- [ {p_name} ] İstatistiksel Analiz ---")
        run_cmd([sys.executable, "analyze_benchmark.py"])
        
        print(f"\n--- [ {p_name} ] Görselleştirme ---")
        run_cmd([sys.executable, "5_visualize.py"])
        
    print("\n" + "="*70)
    print("TÜM SÜREÇ BAŞARIYLA TAMAMLANDI!")
    print("="*70)

if __name__ == "__main__":
    main()
