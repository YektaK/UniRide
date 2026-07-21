import json
import os

DB_FILE = r"C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\yaem2026\data\tuned_parameters_db.json"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    updated = False
    for entry in data:
        if entry.get("algorithm") == "GWO":
            entry["algorithm"] = "GWO-2opt"
            updated = True
        elif entry.get("algorithm") == "HHO":
            entry["algorithm"] = "HHO-2opt"
            updated = True
            
    if updated:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Veritabanı güncellendi: GWO -> GWO-2opt, HHO -> HHO-2opt")
    else:
        print("Güncellenecek bir şey bulunamadı.")
else:
    print("Veritabanı bulunamadı.")
