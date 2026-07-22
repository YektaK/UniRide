#!/usr/bin/env python3
import json
import os
from collections import defaultdict, Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "data", "tuned_parameters_db.json")
UNIVERSAL_DB = os.path.join(SCRIPT_DIR, "data", "universal_parameters_db.json")

def main():
    if not os.path.exists(DB_FILE):
        print(f"[HATA] {DB_FILE} bulunamadı.")
        return

    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Group by algorithm
    algo_params = defaultdict(list)
    for entry in data:
        # We only consider TSPLIB datasets for tuning (student_matrix should not be here, but just in case)
        if entry["problem"] != "student_matrix":
            algo_params[entry["algorithm"]].append(entry)

    universal_entries = []
    uid = 1

    for algo, entries in algo_params.items():
        print(f"\n[{algo}] Analiz ediliyor... (Toplam Problem: {len(entries)})")
        
        # We need to find the mode (most frequent) of each parameter
        param_counts = defaultdict(list)
        for entry in entries:
            params = entry["parameters"]
            for k, v in params.items():
                param_counts[k].append(v)
                
        universal_params = {}
        for k, values in param_counts.items():
            # If values are lists or dicts, make them hashable for Counter
            try:
                counter = Counter(values)
                # most_common(1) returns [(value, count)]
                most_freq_val, count = counter.most_common(1)[0]
                
                # Tie-breaking logic: If there are multiple values with the same max count,
                # we prefer the larger one (e.g., larger population, more iterations).
                max_count = count
                tied_values = [v for v, c in counter.items() if c == max_count]
                
                if len(tied_values) > 1:
                    try:
                        # Try to pick the maximum numeric value
                        best_val = max(tied_values)
                    except TypeError:
                        # Fallback for strings
                        best_val = most_freq_val
                else:
                    best_val = most_freq_val
                    
                universal_params[k] = best_val
                print(f"  - {k}: {best_val} (Frekans: {count}/{len(values)})")
            except Exception as e:
                # Fallback if unhashable
                universal_params[k] = values[0]
                print(f"  - {k}: {values[0]} (Fallback)")
                
        universal_entries.append({
            "id": uid,
            "algorithm": algo,
            "problem": "Universal_Scale_Independent",
            "dimension": "Mixed",
            "best_mean_length": "N/A",
            "parameters": universal_params
        })
        uid += 1

    with open(UNIVERSAL_DB, "w", encoding="utf-8") as f:
        json.dump(universal_entries, f, indent=4, ensure_ascii=False)
        
    print(f"\n[OK] {UNIVERSAL_DB} başarıyla oluşturuldu! Toplam Evrensel Algoritma: {len(universal_entries)}")

if __name__ == "__main__":
    main()
