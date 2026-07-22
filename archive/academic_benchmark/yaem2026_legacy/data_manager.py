#!/usr/bin/env python3
"""
Data Manager for YAEM 2026 Portable Benchmark Framework.
"""
import os
import shutil
from typing import Iterable, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(SCRIPT_DIR, "data")
LOCAL_TSPLIB_DIR = os.path.join(LOCAL_DATA_DIR, "tsplib")

DEFAULT_TSPLIB_SOURCE_DIRS = (
    LOCAL_TSPLIB_DIR,
    os.path.normpath(os.path.join(SCRIPT_DIR, "..", "datasets", "raw", "tsplib")),
    os.path.normpath(os.path.join(SCRIPT_DIR, "..", "bildiri2026", "data", "tsplib")),
)


def _iter_tsp_files(directory: str) -> Iterable[str]:
    if not os.path.isdir(directory):
        return ()
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(".tsp")
    )


def _find_tsplib_source(source_dir: Optional[str]) -> Optional[str]:
    candidates = (source_dir,) if source_dir else DEFAULT_TSPLIB_SOURCE_DIRS
    for candidate in candidates:
        if candidate and list(_iter_tsp_files(candidate)):
            return candidate
    return None


def localize_tsplib(source_dir: Optional[str] = None) -> int:
    print("=" * 60)
    print("TSPLIB Veri Yöneticisi Başlatıldı — YAEM 2026")
    print("=" * 60)
    
    os.makedirs(LOCAL_TSPLIB_DIR, exist_ok=True)

    selected_source = _find_tsplib_source(source_dir)
    if not selected_source:
        print("[HATA] Kopyalanacak TSPLIB dizini bulunamadı.")
        return 0

    tsp_files = list(_iter_tsp_files(selected_source))
    if not tsp_files:
        print("[HATA] TSPLIB dizininde .tsp dosyası bulunamadı.")
        return 0
        
    copied = 0
    for src in tsp_files:
        dst = os.path.join(LOCAL_TSPLIB_DIR, os.path.basename(src))
        if os.path.abspath(src) == os.path.abspath(dst):
            continue
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied += 1
            
    print(f"[✓] {copied} yeni .tsp dosyası yerel dizine kopyalandı.")
    print(f"Yerel dizin: {LOCAL_TSPLIB_DIR}")
    return copied

def list_local_problems():
    problems = []
    
    if os.path.exists(LOCAL_TSPLIB_DIR):
        for f in os.listdir(LOCAL_TSPLIB_DIR):
            if f.endswith(".tsp"):
                problems.append({
                    "type": "tsplib",
                    "name": f.replace(".tsp", ""),
                    "path_relative": f"data/tsplib/{f}"
                })
                
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
