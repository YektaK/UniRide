import json
import os

DB_FILE = r"C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\yaem2026\data\tuned_parameters_db.json"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Keep only the latest entry for each algorithm
    # Sort by id (or timestamp) descending, so the newest is first
    data.sort(key=lambda x: x.get("id", 0), reverse=True)
    
    seen_algos = set()
    cleaned_data = []
    
    for entry in data:
        algo = entry.get("algorithm")
        if algo not in seen_algos:
            seen_algos.add(algo)
            cleaned_data.append(entry)
            
    # Restore ascending order by ID
    cleaned_data.sort(key=lambda x: x.get("id", 0))
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=4, ensure_ascii=False)
        
    print(f"Veritabanı temizlendi! Toplam tekil algoritma sayısı: {len(cleaned_data)}")
else:
    print("Veritabanı bulunamadı.")
