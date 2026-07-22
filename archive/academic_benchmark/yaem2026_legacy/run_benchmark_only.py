import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd):
    print(f"\n[{cmd[1]}] ÇALIŞTIRILIYOR...")
    subprocess.run(cmd, check=True)

def main():
    print("="*70)
    print("SADECE BENCHMARK VE ANALİZ AŞAMASI (Tuning Atlanıyor)")
    print("="*70)
    
    import data_manager
    problems = data_manager.list_local_problems()
    prob_indices = []
    target_names = ["berlin52", "eil51", "st70", "kroA100", "student_matrix"]
    
    for i, p in enumerate(problems):
        if p["name"] in target_names:
            prob_indices.append(str(i + 1))
            
    prob_args = ",".join(prob_indices)
    
    print("\n--- 4. GENİŞ ÇAPLI BENCHMARK ---")
    run_cmd([sys.executable, "3_run_benchmark.py", "all", prob_args, "30"])
    
    print("\n--- 5. BENCHMARK İSTATİSTİKSEL ANALİZİ ---")
    run_cmd([sys.executable, "analyze_benchmark.py"])
    
    print("\n--- 6. GÖRSELLEŞTİRME ---")
    run_cmd([sys.executable, "5_visualize.py"])
    
    print("\n" + "="*70)
    print("TÜM SÜREÇ BAŞARIYLA TAMAMLANDI!")
    print("="*70)

if __name__ == "__main__":
    main()
