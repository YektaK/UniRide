#!/usr/bin/env python3
"""
Data Manager for Portable Benchmark Framework
Ensures TSPLIB and other required datasets are copied locally to bildiri2026/data.
"""
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(SCRIPT_DIR, "data")
LOCAL_TSPLIB_DIR = os.path.join(LOCAL_DATA_DIR, "tsplib")

# Path to the parent project's TSPLIB repository
EXTERNAL_TSPLIB_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "optimizer_api", "tests", "tsplib_data"))

def localize_tsplib():
    print("=" * 60)
    print("TSPLIB Veri Yöneticisi Başlatıldı")
    print("=" * 60)
    
    os.makedirs(LOCAL_TSPLIB_DIR, exist_ok=True)
    
    if not os.path.exists(EXTERNAL_TSPLIB_DIR):
        print(f"[HATA] Dış TSPLIB dizini bulunamadı: {EXTERNAL_TSPLIB_DIR}")
        print("Lütfen dosyaları manuel olarak 'data/tsplib' klasörüne ekleyin.")
        return
        
    files = os.listdir(EXTERNAL_TSPLIB_DIR)
    tsp_files = [f for f in files if f.endswith(".tsp")]
    
    if not tsp_files:
        print("[HATA] Dış dizinde kopyalanacak .tsp dosyası bulunamadı.")
        return
        
    copied = 0
    for f in tsp_files:
        src = os.path.join(EXTERNAL_TSPLIB_DIR, f)
        dst = os.path.join(LOCAL_TSPLIB_DIR, f)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied += 1
            
    print(f"[✓] İşlem tamamlandı. {copied} yeni .tsp dosyası yerel dizine kopyalandı.")
    print(f"Yerel dizin: {LOCAL_TSPLIB_DIR}")

def list_local_problems():
    problems = []
    
    # 1. TSPLIB dosyaları
    if os.path.exists(LOCAL_TSPLIB_DIR):
        for f in os.listdir(LOCAL_TSPLIB_DIR):
            if f.endswith(".tsp"):
                problems.append({
                    "type": "tsplib",
                    "name": f.replace(".tsp", ""),
                    "path_relative": f"data/tsplib/{f}"
                })
                
    # 2. Asimetrik Matrisler
    if os.path.exists(LOCAL_DATA_DIR):
        for f in os.listdir(LOCAL_DATA_DIR):
            if f.endswith(".json") and f != "tuned_parameters_db.json":
                problems.append({
                    "type": "time_matrix",
                    "name": f.replace(".json", ""),
                    "path_relative": f"data/{f}"
                })
                
    return problems

if __name__ == "__main__":
    localize_tsplib()
